"""Source-free reports and a self-contained read-only inspector."""

from __future__ import annotations

import json
from importlib.resources import files
from pathlib import Path
from typing import Any

from .evaluation import Evaluator
from .registry import atomic_write
from .selection import FrontierPoint, frontier
from .store import Store


def report(store: Store, study: str, evaluator: Evaluator) -> dict[str, Any]:
    with store.transaction():
        return _snapshot(store, study, evaluator)


def _snapshot(store: Store, study: str, evaluator: Evaluator) -> dict[str, Any]:
    config, state, created = store.study(study)
    from .contracts import implementation_identity

    if config.implementation_hash != implementation_identity():
        from .errors import Incompatible

        raise Incompatible("report requires the recorded implementation revision")
    events = store.events(study)
    revisions = [e["body"]["revision"] for e in events if e["kind"] == "candidate"]
    candidates = []
    decisions = [e["body"] for e in events if e["kind"] == "selection"]
    points = []
    for revision in dict.fromkeys(revisions):
        skill = store.skill(revision)
        validation = evaluator.summarize(store, study, revision, "validation")
        development = evaluator.summarize(store, study, revision, "development")
        decision = next(
            (d for d in decisions if d["candidate"] == revision),
            {"outcome": "inconclusive", "reason": "no committed selection"},
        )
        attempts = []
        for a in store.attempts(study):
            if a["revision"] == revision:
                attempts.append(
                    {k: v for k, v in a.items() if k != "body"}
                    | {
                        "evaluation": a["body"]["evaluation"] if a["body"] else None,
                        "trace": a["body"].get("trace", []) if a["body"] else [],
                    }
                )
        candidates.append(
            {
                "revision": revision,
                "parents": list(skill.parents),
                "hypothesis": skill.hypothesis,
                "workflow": skill.workflow.model_dump(mode="json"),
                "decision": decision,
                "validation": {
                    "quality": validation.quality,
                    "calls": validation.calls,
                    "latency_ms": validation.latency_ms,
                    "eligible": validation.eligible,
                    "count": len(validation.evaluations),
                },
                "development": {"quality": development.quality, "eligible": development.eligible},
                "attempts": attempts,
            }
        )
        if validation.eligible and validation.quality >= config.policy.quality_floor:
            points.append(FrontierPoint(validation, skill.family))
    final = store.db.execute("SELECT body FROM final_reports WHERE study=?", (study,)).fetchone()
    unknown = [e for e in events if e["kind"] in ("unknown_usage", "model_unresolved")]
    return {
        "schema_version": 1,
        "study_id": study,
        "created": created,
        "config_hash": config.identity,
        "dataset_hash": config.dataset_hash,
        "evaluator_hash": config.evaluator,
        "family": config.family,
        "state": state,
        "usage": store.usage(study),
        "limits": config.limits.model_dump(mode="json"),
        "events": events,
        "candidates": candidates,
        "frontier": [p.summary.revision for p in frontier(points)],
        "final_test": json.loads(final[0]) if final else None,
        "unknown_usage_events": len(unknown),
        "usage_annotations": [
            e["body"]
            for e in events
            if e["kind"]
            in ("model_completed", "estimated_usage", "unknown_usage", "model_unresolved")
        ],
        "evidence_kind": evaluator.dataset.evidence_kind,
        "limitations": [
            "Validation was used for selection.",
            "Hypotheses are not causal evidence.",
            "Raw inputs, outputs, reference labels and context text are omitted.",
            "No model performance or research superiority is established by the authored demo.",
        ],
    }


def write_report(store: Store, study: str, evaluator: Evaluator, directory: Path) -> dict[str, Any]:
    data = report(store, study, evaluator)
    atomic_write(directory / "report.json", json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    template = files("workevo").joinpath("inspector.html").read_text(encoding="utf-8")
    encoded = (
        json.dumps(data, ensure_ascii=False, allow_nan=False)
        .replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
    )
    atomic_write(directory / "inspector.html", template.replace("__REPORT_JSON__", encoded))
    return data
