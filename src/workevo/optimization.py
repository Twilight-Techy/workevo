"""Sequential search with persisted checkpoints, budgets and validation gating."""

from __future__ import annotations

import asyncio
import difflib
import json
from dataclasses import dataclass
from typing import Any, Protocol

from pydantic import JsonValue, ValidationError

from .adapters import CallableModel, ContextProvider, MappingContext
from .contracts import (
    Dataset,
    Limits,
    Node,
    Policy,
    RunResult,
    Skill,
    StudyConfig,
    Workflow,
    canonical,
    implementation_identity,
)
from .errors import BudgetExceeded, DeadlineExceeded, Incompatible, InvalidCandidate
from .evaluation import Evaluator
from .runner import Registry
from .selection import compare
from .store import Store


@dataclass(frozen=True)
class ProposalRequest:
    parent: Skill
    development: list[dict[str, JsonValue]]
    iteration: int
    history: tuple[dict[str, str], ...]
    edit_bytes: int
    purpose: str = "mutation"


class Proposer(Protocol):
    @property
    def identity(self) -> str: ...
    async def propose(self, request: ProposalRequest, store: Store, study: str) -> Skill | None: ...


class SequenceProposer:
    def __init__(self, candidates: tuple[Skill, ...], *, name: str = "sequence-v1") -> None:
        self.candidates = tuple(s.model_copy(deep=True) for s in candidates)
        self.name = name

    @property
    def identity(self) -> str:
        from .contracts import digest

        return digest({"kind": self.name, "revisions": [s.revision for s in self.candidates]})

    async def propose(self, request: ProposalRequest, store: Store, study: str) -> Skill | None:
        return (
            self.candidates[request.iteration] if request.iteration < len(self.candidates) else None
        )


class ModelProposer:
    def __init__(self, model: CallableModel) -> None:
        self.model = model

    @property
    def identity(self) -> str:
        from .contracts import digest

        return digest(
            {
                "kind": "model-proposer-v1",
                "model": self.model.identity,
                "reservation": self.model.reservation.model_dump(),
                "output_cap": self.model.max_output_tokens,
                "enforceable": self.model.enforceable_caps,
            }
        )

    async def propose(self, request: ProposalRequest, store: Store, study: str) -> Skill | None:
        output = await self.model.call(
            json.loads(
                canonical(
                    {
                        "schema_version": 1,
                        "task": (
                            "Generate a seed skill from the task scaffold. Preserve family, permissions, context requirements and operator versions."
                            if request.purpose == "seed"
                            else "Return a skill JSON object that fixes development failures within the edit budget. Do not modify family, permissions, context requirements or operator versions."
                        ),
                        "parent": request.parent.model_dump(mode="json"),
                        "development": request.development,
                        "history": request.history,
                        "edit_bytes": request.edit_bytes,
                        "skill_schema": Skill.model_json_schema(),
                    }
                )
            ),
            store,
            study,
        )
        try:
            return Skill.model_validate(output)
        except ValidationError:
            raise InvalidCandidate("model returned an invalid skill record") from None


def mutation_size(parent: Skill, candidate: Skill) -> int:
    before = canonical(parent).encode()
    after = canonical(candidate).encode()
    return sum(
        max(i2 - i1, j2 - j1)
        for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(
            None, before, after, autojunk=True
        ).get_opcodes()
        if tag != "equal"
    )


class Optimizer:
    def __init__(
        self,
        store: Store,
        dataset: Dataset,
        registry: Registry,
        proposer: Proposer,
        *,
        evaluator: Evaluator | None = None,
        context: ContextProvider | None = None,
    ) -> None:
        self.store = store
        self.dataset = dataset.model_copy(deep=True)
        self.registry = registry
        self.proposer = proposer
        self.evaluator = evaluator or Evaluator(dataset)
        self.context = context or MappingContext({})
        if self.evaluator.dataset.revision != self.dataset.revision:
            raise Incompatible("optimizer/evaluator dataset mismatch")

    def create(
        self,
        seed: Skill,
        *,
        limits: Limits | None = None,
        policy: Policy | None = None,
        executor_identity: str = "registered-offline-operators-v1",
        generate_seed: bool = False,
    ) -> str:
        self.registry.validate(seed)
        if seed.family != self.dataset.family:
            raise InvalidCandidate("seed must match task family")
        self.store.put("skill", seed)
        config = StudyConfig(
            implementation_hash=implementation_identity(),
            dataset_hash=self.dataset.revision,
            family=self.dataset.family,
            evaluator=self.evaluator.identity,
            registry_hash=self.registry.identity,
            proposer=self.proposer.identity,
            seed=seed.revision,
            limits=limits or Limits(),
            policy=policy or Policy(),
            context_hash=self.context.identity,
            executor_identity=executor_identity,
            generate_seed=generate_seed,
            development_keys=tuple(
                f"{case.id}:{repeat}"
                for case in self.dataset.development
                for repeat in range((policy or Policy()).repeats)
            ),
            validation_keys=tuple(
                f"{case.id}:{repeat}"
                for case in self.dataset.validation
                for repeat in range((policy or Policy()).repeats)
            ),
        )
        study = self.store.create(config)
        return study

    def _check(self, study: str) -> tuple[StudyConfig, dict[str, Any]]:
        config, state, _ = self.store.study(study)
        if (
            config.implementation_hash != implementation_identity()
            or config.registry_hash != self.registry.identity
            or config.proposer != self.proposer.identity
            or config.context_hash != self.context.identity
        ):
            raise Incompatible("runner/proposer/context configuration changed")
        self.evaluator.comparison_identity(self.store, study)
        return config, state

    def _sources(self, skill: Skill) -> dict[str, str]:
        return {r.key: self.context.resolve(r) for r in skill.context_requirements}

    def _history(self, study: str) -> tuple[dict[str, str], ...]:
        # Bounded aggregate selection feedback only; no raw validation artifacts/labels.
        return tuple(
            {"outcome": str(e["body"]["outcome"]), "reason": str(e["body"]["reason"])}
            for e in self.store.events(study)
            if e["kind"] == "selection"
        )[-16:]

    async def run(self, study: str, *, recover: bool = False) -> RunResult:
        config, state = self._check(study)
        if state["frozen"] or state["status"] != "running":
            return self.result(study)
        with self.store.lease(study, recover=recover):
            config, state = self._check(study)
            if state["frozen"] or state["status"] != "running":
                return self.result(study)
            try:
                while state["status"] == "running":
                    if self.store.remaining(study) <= 0:
                        raise DeadlineExceeded("deadline exceeded")
                    if state["phase"] == "generate_seed":
                        if state["pending_proposal"]:
                            raise Incompatible(
                                "unresolved seed proposal; explicit resolution required"
                            )
                        state["pending_proposal"] = True
                        self.store.save_state(study, state)
                        scaffold = self.store.skill(config.seed)
                        generated = await self.proposer.propose(
                            ProposalRequest(
                                scaffold,
                                [],
                                state["cursor"],
                                (),
                                config.limits.artifact_bytes,
                                "seed",
                            ),
                            self.store,
                            study,
                        )
                        if generated is None:
                            state["pending_proposal"] = False
                            self._stop(study, state, "no_valid_skill")
                            break
                        self.registry.validate(generated)
                        if (
                            generated.family != scaffold.family
                            or generated.skill_id != scaffold.skill_id
                            or generated.context_requirements != scaffold.context_requirements
                            or generated.parents not in ((), (scaffold.revision,))
                        ):
                            raise InvalidCandidate("generated seed changed protected task contract")
                        self.store.put("skill", generated)
                        state["candidate"] = generated.revision
                        state["phase"] = "evaluate"
                        state["cursor"] += 1
                        state["pending_proposal"] = False
                        self.store.save_state(study, state)
                        self.store.event(
                            study,
                            "seed_generated",
                            {"scaffold": config.seed, "revision": generated.revision},
                        )
                    if state["phase"] == "evaluate":
                        skill = self.store.skill(state["candidate"])
                        admitted = any(
                            e["kind"] == "candidate" and e["body"]["revision"] == skill.revision
                            for e in self.store.events(study)
                        )
                        if not admitted:
                            self.store.charge(study, {"candidates": 1})
                            self.store.event(
                                study,
                                "candidate",
                                {"revision": skill.revision, "hypothesis": skill.hypothesis},
                            )
                        dev = await self.evaluator.evaluate(
                            self.store,
                            study,
                            skill,
                            "development",
                            self.registry,
                            self._sources(skill),
                        )
                        if dev.eligible:
                            # One validation look reservation per candidate, retained across resume.
                            if not any(
                                e["kind"] == "validation_started"
                                and e["body"]["revision"] == skill.revision
                                for e in self.store.events(study)
                            ):
                                self.store.charge(study, {"validation_looks": 1})
                                self.store.event(
                                    study, "validation_started", {"revision": skill.revision}
                                )
                            validation = await self.evaluator.evaluate(
                                self.store,
                                study,
                                skill,
                                "validation",
                                self.registry,
                                self._sources(skill),
                            )
                            incumbent = (
                                self.evaluator.summarize(
                                    self.store, study, state["champion"], "validation"
                                )
                                if state["champion"]
                                else None
                            )
                            decision = compare(validation, incumbent, config.policy)
                        else:
                            decision = {
                                "outcome": "rejected",
                                "reason": "development hard gates failed",
                            }
                        state["phase"] = "propose"
                        state["stale"] = (
                            0 if decision["outcome"] == "accepted" else state["stale"] + 1
                        )
                        self.store.select(study, state["champion"], skill.revision, decision, state)
                        if state["champion"] is None:
                            self._stop(study, state, "no_valid_skill")
                            break
                    if state["phase"] == "propose":
                        if self.store.usage(study).get("candidates", 0) >= config.limits.candidates:
                            self._stop(study, state, "budget_exhausted")
                            break
                        if state["stale"] >= config.policy.patience:
                            self._stop(study, state, "patience_exhausted")
                            break
                        if state["pending_proposal"]:
                            # An external proposer may have spent resources before crashing. Never replay silently.
                            raise Incompatible(
                                "unresolved proposal; retained reservations require explicit resolution"
                            )
                        parent = self.store.skill(state["champion"])
                        state["pending_proposal"] = True
                        self.store.save_state(study, state)
                        request = ProposalRequest(
                            parent.model_copy(deep=True),
                            self.evaluator.development_feedback(self.store, study, parent.revision),
                            state["cursor"],
                            self._history(study),
                            config.limits.mutation_bytes,
                        )
                        try:
                            candidate = await self.proposer.propose(request, self.store, study)
                            if candidate is not None:
                                self._validate_edit(parent, candidate, config)
                        except InvalidCandidate:
                            self.store.charge(study, {"candidates": 1})
                            state["stale"] += 1
                            state["cursor"] += 1
                            state["pending_proposal"] = False
                            self.store.event(
                                study, "invalid_candidate", {"iteration": state["cursor"] - 1}
                            )
                            self.store.save_state(study, state)
                            continue
                        state["pending_proposal"] = False
                        state["cursor"] += 1
                        if candidate is None:
                            self._stop(study, state, "proposer_exhausted")
                            break
                        if candidate.revision == parent.revision:
                            self.store.charge(study, {"candidates": 1})
                            state["stale"] += 1
                            self.store.event(
                                study, "duplicate_candidate", {"iteration": state["cursor"] - 1}
                            )
                        else:
                            self.store.put("skill", candidate)
                            state["candidate"] = candidate.revision
                            state["phase"] = "evaluate"
                        self.store.save_state(study, state)
            except asyncio.CancelledError:
                self.store.event(study, "cancelled", {"reservations_retained": True})
                raise
            except BudgetExceeded:
                self._stop(study, state, "budget_exhausted")
            except DeadlineExceeded:
                self._stop(study, state, "deadline_exceeded")
            except Exception:
                # Keep checkpoint and original incumbent; caller can inspect/recover.
                self.store.event(study, "run_failed", {"reason": "execution_or_adapter_failure"})
                raise
        return self.result(study)

    def _validate_edit(self, parent: Skill, candidate: Skill, config: StudyConfig) -> None:
        self.registry.validate(candidate)
        if candidate.revision == parent.revision:
            return
        if (
            candidate.family != parent.family
            or candidate.skill_id != parent.skill_id
            or candidate.parents != (parent.revision,)
            or candidate.context_requirements != parent.context_requirements
            or mutation_size(parent, candidate) > config.limits.mutation_bytes
        ):
            raise InvalidCandidate(
                "mutation changed protected fields/lineage or exceeded edit budget"
            )

    def discard_unresolved_proposal(self, study: str) -> None:
        """Explicitly abandon a possibly billed proposal, without replay or refund."""
        _, state = self._check(study)
        if not state["pending_proposal"] or state["frozen"] or state["status"] != "running":
            raise Incompatible("no unresolved running proposal")
        with self.store.lease(study):
            self.store.charge(study, {"candidates": 1})
            state["pending_proposal"] = False
            state["cursor"] += 1
            state["stale"] += 1
            with self.store.transaction():
                self.store.save_state(study, state)
                self.store.event(
                    study,
                    "proposal_abandoned",
                    {"iteration": state["cursor"] - 1, "reservations_retained": True},
                )

    def _stop(self, study: str, state: dict[str, Any], reason: str) -> None:
        state["status"] = "stopped"
        state["stop_reason"] = reason
        with self.store.transaction():
            self.store.save_state(study, state)
            self.store.event(study, "stopped", {"reason": reason, "champion": state["champion"]})

    def result(self, study: str) -> RunResult:
        _, state, _ = self.store.study(study)
        return RunResult(
            study_id=study,
            status=state["status"],
            champion=state["champion"],
            candidates=self.store.usage(study).get("candidates", 0),
            stop_reason=state["stop_reason"],
        )

    def freeze(self, study: str) -> Skill:
        _, state = self._check(study)
        if state["status"] == "running" or state["champion"] is None:
            raise Incompatible("stop optimization with an eligible champion before freezing")
        with self.store.lease(study), self.store.transaction():
            state["frozen"] = True
            self.store.save_state(study, state)
            self.store.event(study, "frozen", {"revision": state["champion"]})
        return self.store.skill(state["champion"])

    async def final_test(self, study: str, *, recover: bool = False) -> dict[str, Any]:
        _, state = self._check(study)
        if not state["frozen"] or state["champion"] is None:
            raise Incompatible("study must be frozen before final test")
        row = self.store.db.execute(
            "SELECT body FROM final_reports WHERE study=?", (study,)
        ).fetchone()
        if row:
            result: dict[str, Any] = json.loads(row[0])
            return result
        with self.store.lease(study, recover=recover):
            state["test_started"] = True
            self.store.save_state(study, state)
            skill = self.store.skill(state["champion"])
            summary = await self.evaluator.evaluate(
                self.store, study, skill, "test", self.registry, self._sources(skill)
            )
            report = {
                "revision": skill.revision,
                "identity": summary.identity,
                "quality": summary.quality,
                "eligible": summary.eligible,
                "summary": summary.model_dump(mode="json"),
                "evidence_kind": self.dataset.evidence_kind,
            }
            with self.store.transaction():
                self.store.db.execute(
                    "INSERT INTO final_reports VALUES (?,?)", (study, canonical(report))
                )
                self.store.event(
                    study,
                    "final_test_completed",
                    {"revision": skill.revision, "quality": summary.quality},
                )
            return report


def seed_skill() -> Skill:
    return Skill(
        skill_id="normalize-record",
        family="record-normalization",
        instructions="Normalize the input record, preserving identifiers and missing values.",
        workflow=Workflow(
            entry="normalize",
            nodes=(
                Node(id="normalize", operator="normalize_record", next="audit"),
                Node(id="audit", operator="identity"),
            ),
        ),
    )


def demo_proposer(seed: Skill) -> SequenceProposer:
    def edit(parent: Skill, *, aliases: bool, trim: bool, audit: bool, hypothesis: str) -> Skill:
        nodes: tuple[Node, ...] = (
            Node(
                id="normalize",
                operator="normalize_record",
                parameters={"aliases": aliases, "trim": trim},
                next="audit" if audit else "done",
            ),
        )
        if audit:
            nodes += (Node(id="audit", operator="identity"),)
        return Skill(
            skill_id=parent.skill_id,
            family=parent.family,
            instructions=parent.instructions,
            parents=(parent.revision,),
            hypothesis=hypothesis,
            workflow=Workflow(entry="normalize", nodes=nodes),
        )

    aliases = edit(
        seed, aliases=True, trim=False, audit=True, hypothesis="Handle documented aliases"
    )
    trimmed = edit(
        aliases,
        aliases=True,
        trim=True,
        audit=True,
        hypothesis="Trim strings while preserving leading zeros",
    )
    efficient = edit(
        trimmed,
        aliases=True,
        trim=True,
        audit=False,
        hypothesis="Remove redundant identity operation",
    )
    bad = edit(
        efficient,
        aliases=False,
        trim=True,
        audit=False,
        hypothesis="Regression probe: remove alias handling",
    )
    return SequenceProposer((aliases, trimmed, efficient, bad))


class FeedbackProposer:
    """Small domain policy using development failures, never reference labels.

    Useful as an offline baseline, not a substitute for a general model proposer.
    """

    identity = "record-feedback-v1"

    async def propose(self, request: ProposalRequest, store: Store, study: str) -> Skill | None:
        parent = request.parent
        nodes = list(parent.workflow.nodes)
        normalizers = [i for i, node in enumerate(nodes) if node.operator == "normalize_record"]
        if len(normalizers) != 1:
            return None
        index = normalizers[0]
        node = nodes[index]
        parameters = dict(node.parameters)
        failed = [f for f in request.development if not f["correct"]]
        if (
            failed
            and not parameters.get("aliases", False)
            and any(
                isinstance(f["input"], dict)
                and any(key in f["input"] for key in ("identifier", "display_name"))
                for f in failed
            )
        ):
            parameters["aliases"] = True
            hypothesis = "Development failures contain alternate field names; enable aliases"
        elif (
            failed
            and not parameters.get("trim", False)
            and any(
                isinstance(f["output"], dict)
                and any(
                    isinstance(value, str) and value != value.strip()
                    for value in f["output"].values()
                )
                for f in failed
            )
        ):
            parameters["trim"] = True
            hypothesis = "Development failures contain padded strings; enable trimming"
        elif (
            not failed
            and node.next != "done"
            and len(nodes) == 2
            and nodes[1].operator == "identity"
        ):
            nodes = [node.model_copy(update={"next": "done"})]
            hypothesis = "All development cases pass; remove redundant identity step"
        else:
            return None
        nodes[0 if len(nodes) == 1 else index] = nodes[0 if len(nodes) == 1 else index].model_copy(
            update={"parameters": parameters}
        )
        return Skill(
            skill_id=parent.skill_id,
            family=parent.family,
            instructions=parent.instructions,
            workflow=Workflow(
                entry=parent.workflow.entry,
                nodes=tuple(nodes),
                terminals=parent.workflow.terminals,
                max_steps=parent.workflow.max_steps,
            ),
            parents=(parent.revision,),
            hypothesis=hypothesis,
            context_requirements=parent.context_requirements,
        )
