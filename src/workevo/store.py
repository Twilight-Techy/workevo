"""Transactional immutable artifacts and an append-only execution journal."""

from __future__ import annotations

import json
import os
import socket
import sqlite3
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from .contracts import Evaluation, Skill, StudyConfig, Summary, canonical, digest
from .errors import BudgetExceeded, Conflict, DeadlineExceeded, Incompatible

DDL = (
    "CREATE TABLE artifacts (hash TEXT PRIMARY KEY, kind TEXT NOT NULL, body TEXT NOT NULL)",
    "CREATE TABLE studies (id TEXT PRIMARY KEY, config TEXT NOT NULL, state TEXT NOT NULL, created REAL NOT NULL, lease TEXT)",
    "CREATE TABLE events (seq INTEGER PRIMARY KEY AUTOINCREMENT, study TEXT NOT NULL REFERENCES studies(id), kind TEXT NOT NULL, body TEXT NOT NULL, created REAL NOT NULL)",
    "CREATE TABLE usage (study TEXT NOT NULL REFERENCES studies(id), kind TEXT NOT NULL, amount INTEGER NOT NULL CHECK(amount>=0), PRIMARY KEY(study,kind))",
    "CREATE TABLE attempts (id TEXT PRIMARY KEY, study TEXT NOT NULL REFERENCES studies(id), revision TEXT NOT NULL REFERENCES artifacts(hash), split TEXT NOT NULL, case_id TEXT NOT NULL, repeat INTEGER NOT NULL, status TEXT NOT NULL, body TEXT)",
    "CREATE INDEX evidence ON attempts(study,revision,split,case_id,repeat,status)",
    "CREATE TABLE final_reports (study TEXT PRIMARY KEY REFERENCES studies(id), body TEXT NOT NULL)",
)


class Store:
    def __init__(self, path: str | Path = ":memory:") -> None:
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(path), isolation_level=None, timeout=5)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.execute("PRAGMA busy_timeout=5000")
        version = self.db.execute("PRAGMA user_version").fetchone()[0]
        if version not in (0, 1):
            self.db.close()
            raise Incompatible(f"database schema {version}; expected 1")
        if version == 0:
            if self.db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall():
                self.db.close()
                raise Incompatible("unversioned nonempty database; explicit migration required")
            with self.transaction():
                for sql in DDL:
                    self.db.execute(sql)
                self.db.execute("PRAGMA user_version=1")
        self.db.execute("PRAGMA journal_mode=WAL")

    def close(self) -> None:
        self.db.close()

    def __enter__(self) -> Store:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    @contextmanager
    def transaction(self) -> Iterator[None]:
        self.db.execute("BEGIN IMMEDIATE")
        try:
            yield
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    def put(self, kind: str, value: Any) -> str:
        if kind == "skill":
            try:
                value = Skill.model_validate_json(canonical(value))
            except ValidationError:
                raise Incompatible("invalid skill artifact") from None
        body = canonical(value)
        key = digest(value)
        self.db.execute("INSERT OR IGNORE INTO artifacts VALUES (?,?,?)", (key, kind, body))
        row = self.db.execute("SELECT kind,body FROM artifacts WHERE hash=?", (key,)).fetchone()
        if row["kind"] != kind or row["body"] != body:
            raise Incompatible("artifact identity collision")
        return key

    def get(self, key: str, kind: str) -> Any:
        row = self.db.execute("SELECT * FROM artifacts WHERE hash=?", (key,)).fetchone()
        if row is None:
            raise Incompatible("artifact does not exist")
        value = json.loads(row["body"])
        if row["kind"] != kind or digest(value) != key:
            raise Incompatible("artifact kind/hash mismatch")
        return value

    def skill(self, revision: str) -> Skill:
        return Skill.model_validate(self.get(revision, "skill"))

    def create(self, config: StudyConfig) -> str:
        seed = self.skill(config.seed)
        if seed.family != config.family:
            raise Incompatible("study seed does not match task family")
        study = uuid.uuid4().hex
        state = {
            "status": "running",
            "champion": None,
            "candidate": config.seed,
            "cursor": 0,
            "phase": "generate_seed" if config.generate_seed else "evaluate",
            "stale": 0,
            "stop_reason": "",
            "frozen": False,
            "test_started": False,
            "pending_proposal": False,
        }
        with self.transaction():
            self.db.execute(
                "INSERT INTO studies VALUES (?,?,?,?,NULL)",
                (study, canonical(config), canonical(state), time.time()),
            )
            self.event(study, "study_created", {"config_hash": config.identity})
        return study

    def study(self, study: str) -> tuple[StudyConfig, dict[str, Any], float]:
        row = self.db.execute("SELECT * FROM studies WHERE id=?", (study,)).fetchone()
        if row is None:
            raise Incompatible("unknown study")
        return (
            StudyConfig.model_validate_json(row["config"]),
            json.loads(row["state"]),
            row["created"],
        )

    def save_state(self, study: str, state: dict[str, Any]) -> None:
        self.db.execute("UPDATE studies SET state=? WHERE id=?", (canonical(state), study))

    def event(self, study: str, kind: str, body: Any) -> None:
        self.db.execute(
            "INSERT INTO events(study,kind,body,created) VALUES (?,?,?,?)",
            (study, kind, canonical(body), time.time()),
        )

    def events(self, study: str) -> list[dict[str, Any]]:
        return [
            {
                "seq": r["seq"],
                "kind": r["kind"],
                "body": json.loads(r["body"]),
                "created": r["created"],
            }
            for r in self.db.execute("SELECT * FROM events WHERE study=? ORDER BY seq", (study,))
        ]

    @contextmanager
    def lease(self, study: str, *, recover: bool = False) -> Iterator[None]:
        token = f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex}"
        with self.transaction():
            row = self.db.execute("SELECT lease FROM studies WHERE id=?", (study,)).fetchone()
            if row is None:
                raise Incompatible("unknown study")
            if row[0] and not recover:
                raise Conflict("study is leased; explicit local recovery required after a crash")
            if row[0] and recover:
                parts = row[0].split(":")
                if len(parts) != 3 or parts[0] != socket.gethostname():
                    raise Conflict("cannot verify abandoned lease on this host")
                try:
                    os.kill(int(parts[1]), 0)
                except ProcessLookupError:
                    pass
                except (PermissionError, ValueError):
                    raise Conflict("cannot verify abandoned lease owner") from None
                else:
                    raise Conflict("lease owner is still running; recovery refused")
            pending = self.db.execute(
                "SELECT COUNT(*) FROM attempts WHERE study=? AND status='started'", (study,)
            ).fetchone()[0]
            if pending and not recover:
                raise Conflict("unresolved attempts require explicit local recovery")
            if recover:
                self.db.execute(
                    "UPDATE attempts SET status='interrupted' WHERE study=? AND status='started'",
                    (study,),
                )
                self.event(study, "local_recovery", {"reservations_retained": True})
            self.db.execute("UPDATE studies SET lease=? WHERE id=?", (token, study))
        try:
            yield
        finally:
            self.db.execute("UPDATE studies SET lease=NULL WHERE id=? AND lease=?", (study, token))

    def usage(self, study: str) -> dict[str, int]:
        return {
            r["kind"]: r["amount"]
            for r in self.db.execute("SELECT * FROM usage WHERE study=?", (study,))
        }

    def remaining(self, study: str) -> float:
        config, _, created = self.study(study)
        return config.limits.seconds - (time.time() - created)

    def charge(self, study: str, amounts: dict[str, int]) -> None:
        with self.transaction():
            config, _, _ = self.study(study)
            if self.remaining(study) <= 0:
                raise DeadlineExceeded("absolute study deadline exceeded")
            usage = self.usage(study)
            for kind, amount in amounts.items():
                if (
                    type(amount) is not int
                    or amount < 0
                    or kind
                    not in (
                        "candidates",
                        "trials",
                        "tool_calls",
                        "retries",
                        "model_calls",
                        "tokens",
                        "micro_usd",
                        "validation_looks",
                    )
                ):
                    raise ValueError("invalid reservation")
                cap = getattr(config.limits, kind)
                if cap is not None and usage.get(kind, 0) + amount > cap:
                    raise BudgetExceeded(f"{kind} budget exhausted")
            for kind, amount in amounts.items():
                self.db.execute(
                    "INSERT INTO usage VALUES (?,?,?) ON CONFLICT(study,kind) DO UPDATE SET amount=amount+excluded.amount",
                    (study, kind, amount),
                )
            self.event(study, "reservation", amounts)

    def reconcile(self, study: str, reserved: dict[str, int], actual: dict[str, int]) -> None:
        violation = False
        with self.transaction():
            config, _, _ = self.study(study)
            usage = self.usage(study)
            for kind, amount in actual.items():
                previous = reserved.get(kind, 0)
                if amount < 0 or kind not in ("tokens", "micro_usd"):
                    raise ValueError("invalid measured usage")
                total = usage.get(kind, 0) + amount - previous
                if total < 0:
                    raise ValueError("reservation was not charged")
                self.db.execute(
                    "INSERT INTO usage VALUES (?,?,?) ON CONFLICT(study,kind) DO UPDATE SET amount=excluded.amount",
                    (study, kind, total),
                )
                cap = getattr(config.limits, kind)
                if (kind in reserved and amount > previous) or (cap is not None and total > cap):
                    violation = True
            self.event(study, "usage_reconciled", {"reserved": reserved, "actual": actual})
        if violation:
            raise BudgetExceeded(
                "adapter exceeded declared usage reservation; measured overrun recorded"
            )

    def start_attempt(self, study: str, revision: str, split: str, case: str, repeat: int) -> str:
        config, state, _ = self.study(study)
        skill = self.skill(revision)
        if skill.family != config.family or split not in (
            "development",
            "validation",
            "test",
            "deployment",
        ):
            raise Incompatible("trial task contract mismatch")
        if type(repeat) is not int or not 0 <= repeat < config.policy.repeats:
            raise Incompatible("invalid trial repeat")
        if split == "test" and (not state["frozen"] or state["champion"] != revision):
            raise Incompatible("test trial requires the frozen champion")
        if split != "test" and state["frozen"]:
            raise Incompatible("frozen study rejects new search trials")
        attempt = uuid.uuid4().hex
        self.db.execute(
            "INSERT INTO attempts VALUES (?,?,?,?,?,?,?,NULL)",
            (attempt, study, revision, split, case, repeat, "started"),
        )
        return attempt

    def finish_attempt(self, attempt: str, body: dict[str, Any]) -> None:
        row = self.db.execute("SELECT * FROM attempts WHERE id=?", (attempt,)).fetchone()
        if row is None or row["status"] != "started":
            raise Conflict("attempt is not pending")
        if row["split"] != "deployment":
            try:
                evaluation = Evaluation.model_validate(body["evaluation"])
            except (KeyError, ValidationError):
                raise Incompatible("invalid trial evaluation") from None
            if evaluation.case_id != row["case_id"] or evaluation.repeat != row["repeat"]:
                raise Incompatible("evaluation belongs to another trial")
        changed = self.db.execute(
            "UPDATE attempts SET status='completed',body=? WHERE id=? AND status='started'",
            (canonical(body), attempt),
        ).rowcount
        if changed != 1:
            raise Conflict("attempt is already committed or interrupted")

    def evidence(
        self, study: str, revision: str, split: str, case: str, repeat: int
    ) -> dict[str, Any] | None:
        rows = self.db.execute(
            "SELECT body FROM attempts WHERE study=? AND revision=? AND split=? AND case_id=? AND repeat=? AND status='completed'",
            (study, revision, split, case, repeat),
        ).fetchall()
        if len(rows) > 1:
            raise Conflict("duplicate completed evidence")
        return json.loads(rows[0][0]) if rows else None

    def attempts(self, study: str) -> list[dict[str, Any]]:
        return [
            dict(r) | {"body": json.loads(r["body"]) if r["body"] else None}
            for r in self.db.execute(
                "SELECT * FROM attempts WHERE study=? ORDER BY rowid", (study,)
            )
        ]

    def select(
        self,
        study: str,
        expected: str | None,
        candidate: str,
        decision: dict[str, Any],
        state: dict[str, Any],
    ) -> None:
        with self.transaction():
            config, current, _ = self.study(study)
            if current["champion"] != expected or current["frozen"]:
                raise Conflict("incumbent changed or study is frozen")
            if decision["outcome"] not in ("accepted", "rejected", "inconclusive"):
                raise Incompatible("invalid selection decision")
            self.skill(candidate)
            if decision["outcome"] == "accepted":
                from .selection import compare

                def summary(revision: str, split: str, keys: tuple[str, ...]) -> Summary:
                    rows = self.db.execute(
                        "SELECT body FROM attempts WHERE study=? AND revision=? AND split=? AND status='completed'",
                        (study, revision, split),
                    ).fetchall()
                    pending = self.db.execute(
                        "SELECT COUNT(*) FROM attempts WHERE study=? AND revision=? AND split=? AND status='started'",
                        (study, revision, split),
                    ).fetchone()[0]
                    if not keys or pending:
                        raise Incompatible("cannot promote missing or unresolved evidence")
                    return Summary.model_validate(
                        {
                            "revision": revision,
                            "identity": config.identity,
                            "split": split,
                            "evaluations": [json.loads(row[0])["evaluation"] for row in rows],
                            "expected_keys": keys,
                        }
                    )

                development = summary(candidate, "development", config.development_keys)
                validation = summary(candidate, "validation", config.validation_keys)
                incumbent = (
                    summary(expected, "validation", config.validation_keys) if expected else None
                )
                if (
                    not development.eligible
                    or compare(validation, incumbent, config.policy)["outcome"] != "accepted"
                ):
                    raise Incompatible("transactional promotion gate rejected evidence")
                state["champion"] = candidate
            self.save_state(study, state)
            self.event(
                study, "selection", decision | {"candidate": candidate, "incumbent": expected}
            )
