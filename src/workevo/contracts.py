"""Versioned JSON contracts. No provider or framework imports."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

Identifier = Annotated[str, Field(min_length=1, max_length=128, pattern=r"^[\w.:-]+$")]
Hash = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]


def canonical(value: Any) -> str:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    return json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    )


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def implementation_identity() -> str:
    return digest(
        {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(Path(__file__).parent.glob("*.py"))
        }
    )


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)
    schema_version: Literal[1] = 1


class Node(Record):
    id: Identifier
    operator: Identifier
    version: str = Field(default="1", min_length=1, max_length=128)
    parameters: dict[str, JsonValue] = Field(default_factory=dict)
    next: Identifier = "done"
    branch_field: Identifier | None = None
    on_false: Identifier | None = None
    max_visits: int = Field(default=1, ge=1, le=1024)

    @model_validator(mode="after")
    def branch(self) -> Node:
        if (self.branch_field is None) != (self.on_false is None):
            raise ValueError("branch_field and on_false must be supplied together")
        if len(canonical(self.parameters).encode()) > 16384:
            raise ValueError("node parameters exceed 16384 bytes")
        return self


class Workflow(Record):
    entry: Identifier
    nodes: tuple[Node, ...] = Field(min_length=1, max_length=64)
    terminals: tuple[Identifier, ...] = ("done",)
    max_steps: int = Field(default=32, ge=1, le=1024)

    @model_validator(mode="after")
    def graph(self) -> Workflow:
        nodes = {n.id: n for n in self.nodes}
        terminal = set(self.terminals)
        if len(nodes) != len(self.nodes) or len(terminal) != len(self.terminals):
            raise ValueError("duplicate graph identifiers")
        if not terminal or terminal & nodes.keys() or self.entry not in nodes:
            raise ValueError("invalid entry or terminals")
        for node in self.nodes:
            if any(t not in nodes and t not in terminal for t in (node.next, node.on_false) if t):
                raise ValueError("dangling graph destination")
        reached: set[str] = set()
        pending = [self.entry]
        while pending:
            at = pending.pop()
            if at in reached:
                continue
            reached.add(at)
            if at in nodes:
                pending.extend(t for t in (nodes[at].next, nodes[at].on_false) if t)
        if set(nodes) - reached or terminal - reached:
            raise ValueError("unreachable nodes or terminals")
        can_exit = terminal.copy()
        for _ in nodes:
            can_exit.update(
                n.id for n in self.nodes if n.next in can_exit or n.on_false in can_exit
            )
        if set(nodes) - can_exit:
            raise ValueError("node has no terminal path")
        return self


class ContextRequirement(Record):
    key: Identifier
    revision: str = Field(min_length=1, max_length=256)
    max_bytes: int = Field(default=4096, ge=1, le=65536)


class Skill(Record):
    skill_id: Identifier
    family: Identifier
    instructions: str = Field(min_length=1, max_length=16000)
    workflow: Workflow
    parents: tuple[Hash, ...] = Field(default=(), max_length=2)
    hypothesis: str = Field(default="Seed", max_length=2000)
    context_requirements: tuple[ContextRequirement, ...] = Field(default=(), max_length=16)
    tags: tuple[Identifier, ...] = ()

    @model_validator(mode="after")
    def bounded(self) -> Skill:
        if len({r.key for r in self.context_requirements}) != len(self.context_requirements):
            raise ValueError("duplicate context requirement keys")
        if len(canonical(self).encode()) > 65536:
            raise ValueError("skill exceeds 65536 bytes")
        return self

    @property
    def revision(self) -> str:
        return digest(self)


class Case(Record):
    id: Identifier
    template: Identifier
    inputs: JsonValue
    expected: JsonValue


class Dataset(Record):
    evidence_kind: Literal["authored_software_fixture", "application_evaluation"] = (
        "application_evaluation"
    )
    name: Identifier
    family: Identifier
    development: tuple[Case, ...] = Field(min_length=1)
    validation: tuple[Case, ...] = Field(min_length=1)
    test: tuple[Case, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def splits(self) -> Dataset:
        seen_ids: set[str] = set()
        seen_inputs: set[str] = set()
        seen_templates: set[str] = set()
        for split in (self.development, self.validation, self.test):
            templates: set[str] = set()
            for case in split:
                key = digest(case.inputs)
                if case.id in seen_ids or key in seen_inputs or case.template in seen_templates:
                    raise ValueError("duplicate case/input or overlapping template families")
                seen_ids.add(case.id)
                seen_inputs.add(key)
                templates.add(case.template)
                if len(canonical(case.inputs).encode()) > 65536:
                    raise ValueError("case input exceeds 65536 bytes")
            seen_templates.update(templates)
        return self

    @property
    def revision(self) -> str:
        return digest(self)

    def cases(self, split: str) -> tuple[Case, ...]:
        if split not in ("development", "validation", "test"):
            raise ValueError("unknown split")
        return getattr(self, split)  # type: ignore[no-any-return]


class Limits(Record):
    candidates: int = Field(default=6, ge=1, le=10000)
    trials: int = Field(default=512, ge=1)
    tool_calls: int = Field(default=4096, ge=1)
    retries: int = Field(default=64, ge=0)
    model_calls: int = Field(default=16, ge=0)
    tokens: int | None = Field(default=None, ge=0)
    micro_usd: int | None = Field(default=None, ge=0)
    validation_looks: int = Field(default=6, ge=1)
    seconds: float = Field(default=120, gt=0)
    artifact_bytes: int = Field(default=65536, ge=128, le=1048576)
    mutation_bytes: int = Field(default=8192, ge=1, le=65536)


class Policy(Record):
    repeats: int = Field(default=1, ge=1, le=100)
    quality_floor: float = Field(default=0, ge=0, le=1)
    min_gain: float = Field(default=0, ge=0, le=1)
    patience: int = Field(default=3, ge=1)


class Evaluation(Record):
    case_id: Identifier
    repeat: int = Field(ge=0)
    correct: bool
    schema_valid: bool
    complete: bool
    reason: str
    calls: int = Field(ge=0)
    latency_ms: float = Field(ge=0)
    output_hash: Hash | None = None


class Summary(Record):
    revision: Hash
    identity: Hash
    split: Literal["development", "validation", "test"]
    evaluations: tuple[Evaluation, ...]
    expected_keys: tuple[str, ...]

    @property
    def complete(self) -> bool:
        keys = [f"{e.case_id}:{e.repeat}" for e in self.evaluations]
        return (
            bool(self.expected_keys)
            and len(self.expected_keys) == len(set(self.expected_keys))
            and len(keys) == len(set(keys))
            and set(keys) == set(self.expected_keys)
            and all(e.complete for e in self.evaluations)
        )

    @property
    def eligible(self) -> bool:
        return self.complete and all(e.schema_valid for e in self.evaluations)

    @property
    def quality(self) -> float:
        return (
            sum(e.correct for e in self.evaluations) / len(self.evaluations)
            if self.evaluations
            else 0
        )

    @property
    def calls(self) -> float:
        return (
            sum(e.calls for e in self.evaluations) / len(self.evaluations)
            if self.evaluations
            else 0
        )

    @property
    def latency_ms(self) -> float:
        return (
            sum(e.latency_ms for e in self.evaluations) / len(self.evaluations)
            if self.evaluations
            else 0
        )


class ModelUsage(Record):
    tokens_kind: Literal["measured", "estimated"] = "measured"
    micro_usd_kind: Literal["measured", "estimated"] = "estimated"
    tokens: int | None = Field(default=None, ge=0)
    micro_usd: int | None = Field(default=None, ge=0)


class ModelResponse(Record):
    candidate: Skill
    usage: ModelUsage = Field(default_factory=ModelUsage)


class StudyConfig(Record):
    implementation_hash: Hash
    dataset_hash: Hash
    family: Identifier
    evaluator: str
    registry_hash: Hash
    proposer: str = Field(min_length=1)
    seed: Hash
    limits: Limits = Field(default_factory=Limits)
    policy: Policy = Field(default_factory=Policy)
    context_hash: Hash
    executor_identity: str = "registered-offline-operators-v1"
    generate_seed: bool = False
    development_keys: tuple[str, ...] = ()
    validation_keys: tuple[str, ...] = ()

    @property
    def identity(self) -> str:
        return digest(self)


class RunResult(Record):
    study_id: str
    status: str
    champion: Hash | None
    candidates: int
    stop_reason: str


class Metric(Record):
    name: str
    weight: float = Field(gt=0, le=1)
    lower: float
    upper: float
    maximize: bool = True

    @model_validator(mode="after")
    def bounds(self) -> Metric:
        if self.lower >= self.upper:
            raise ValueError("metric range must increase")
        return self


def weighted_score(
    values: dict[str, float | None], metrics: tuple[Metric, ...], *, eligible: bool
) -> float | None:
    if not math.isclose(sum(m.weight for m in metrics), 1) or len({m.name for m in metrics}) != len(
        metrics
    ):
        raise ValueError("weights must sum to one with unique metrics")
    if not eligible:
        return None
    total = 0.0
    for metric in metrics:
        value = values.get(metric.name)
        if value is None or not math.isfinite(value):
            return None
        normalized = max(0.0, min(1.0, (value - metric.lower) / (metric.upper - metric.lower)))
        total += metric.weight * (normalized if metric.maximize else 1 - normalized)
    return total
