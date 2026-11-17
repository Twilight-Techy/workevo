"""Evaluator-owned labels and complete paired evidence sets."""

from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import Any, Literal

from pydantic import JsonValue

from .contracts import Case, Dataset, Evaluation, Skill, Summary, digest
from .errors import BudgetExceeded, DeadlineExceeded, Incompatible
from .runner import Registry, execute
from .store import Store

Split = Literal["development", "validation", "test"]
Validator = Callable[[JsonValue], bool]


def record_schema(output: JsonValue) -> bool:
    return (
        isinstance(output, dict)
        and set(output) == {"id", "name"}
        and all(v is None or isinstance(v, str) for v in output.values())
    )


class Evaluator:
    def __init__(
        self,
        dataset: Dataset,
        *,
        validator: Validator = record_schema,
        identity: str = "exact-record-v1",
    ) -> None:
        self.dataset = dataset.model_copy(deep=True)
        self.validator = validator
        try:
            validator_source = inspect.getsource(validator)
        except (OSError, TypeError):
            validator_source = f"{validator.__module__}.{validator.__qualname__}:{identity}"
        self.identity = digest(
            {
                "name": identity,
                "validator": validator_source,
                "scorer": "schema-then-json-equality-v1",
            }
        )

    def comparison_identity(self, store: Store, study: str) -> str:
        config, _, _ = store.study(study)
        if config.dataset_hash != self.dataset.revision or config.evaluator != self.identity:
            raise Incompatible("dataset/evaluator identity changed")
        return config.identity

    def summarize(self, store: Store, study: str, revision: str, split: Split) -> Summary:
        config, _, _ = store.study(study)
        values = []
        keys = []
        for case in self.dataset.cases(split):
            for repeat in range(config.policy.repeats):
                keys.append(f"{case.id}:{repeat}")
                body = store.evidence(study, revision, split, case.id, repeat)
                if body:
                    values.append(Evaluation.model_validate(body["evaluation"]))
        return Summary(
            revision=revision,
            identity=self.comparison_identity(store, study),
            split=split,
            evaluations=tuple(values),
            expected_keys=tuple(keys),
        )

    async def evaluate(
        self,
        store: Store,
        study: str,
        skill: Skill,
        split: Split,
        registry: Registry,
        sources: dict[str, str] | None = None,
    ) -> Summary:
        config, state, _ = store.study(study)
        self.comparison_identity(store, study)
        if registry.identity != config.registry_hash:
            raise Incompatible("operator registry changed")
        if split == "test" and not state["frozen"]:
            raise Incompatible("final test requires a frozen study")
        if split != "test" and state["frozen"]:
            raise Incompatible("frozen study cannot resume optimization")
        for case in self.dataset.cases(split):
            for repeat in range(config.policy.repeats):
                if store.evidence(study, skill.revision, split, case.id, repeat):
                    continue
                store.charge(study, {"trials": 1})
                attempt = store.start_attempt(study, skill.revision, split, case.id, repeat)
                result = await execute(skill, case.inputs, registry, store, study, sources)
                schema_valid = result.complete and self.validator(result.output)
                evaluation = Evaluation(
                    case_id=case.id,
                    repeat=repeat,
                    correct=schema_valid and result.output == case.expected,
                    schema_valid=schema_valid,
                    complete=result.complete,
                    reason=result.reason,
                    calls=result.calls,
                    latency_ms=result.latency_ms,
                    output_hash=digest(result.output),
                )
                # Development outputs only are persisted for proposer feedback; shared reports strip them.
                body: dict[str, Any] = {
                    "evaluation": evaluation.model_dump(mode="json"),
                    "trace": result.trace,
                }
                if split == "development":
                    body["output"] = result.output
                store.finish_attempt(attempt, body)
                if result.reason == "budget_exhausted":
                    raise BudgetExceeded("execution budget exhausted")
                if result.reason == "deadline_exceeded":
                    raise DeadlineExceeded("execution deadline exceeded")
        return self.summarize(store, study, skill.revision, split)

    def development_feedback(
        self, store: Store, study: str, revision: str
    ) -> list[dict[str, JsonValue]]:
        config, _, _ = store.study(study)
        feedback: list[dict[str, JsonValue]] = []
        for case in self.dataset.development:
            for repeat in range(config.policy.repeats):
                body = store.evidence(study, revision, "development", case.id, repeat)
                if body:
                    feedback.append(
                        {
                            "case_id": case.id,
                            "input": case.inputs,
                            "output": body.get("output"),
                            "correct": body["evaluation"]["correct"],
                            "reason": body["evaluation"]["reason"],
                        }
                    )
        return feedback


def authored_dataset() -> Dataset:
    """Labels are literal authored records, never produced by the normalization operator."""

    def cases(prefix: str, suffix: str) -> tuple[Case, ...]:
        rows: list[tuple[JsonValue, JsonValue]] = [
            (
                {"id": "00" + suffix, "name": "Ada" + suffix},
                {"id": "00" + suffix, "name": "Ada" + suffix},
            ),
            (
                {"identifier": "0" + suffix, "display_name": "Zoë" + suffix},
                {"id": "0" + suffix, "name": "Zoë" + suffix},
            ),
            (
                {"id": " 00" + suffix + " ", "name": " Nia" + suffix + "  "},
                {"id": "00" + suffix, "name": "Nia" + suffix},
            ),
            (
                {"identifier": " " + suffix + " ", "display_name": " 李" + suffix + " "},
                {"id": suffix, "name": "李" + suffix},
            ),
            (
                {"id": None, "identifier": "ignore" + suffix, "display_name": "A" + suffix},
                {"id": None, "name": "A" + suffix},
            ),
            (
                {"id": int(suffix), "name": [suffix], "noise": suffix},
                {"id": str(int(suffix)), "name": None},
            ),
            ({"name": "  ", "noise": suffix}, {"id": None, "name": None}),
            (
                {"id": {"bad": suffix}, "name": None, "display_name": "ignore"},
                {"id": None, "name": None},
            ),
        ]
        return tuple(
            Case(id=f"{prefix}-{i}", template=f"{prefix}-template-{i}", inputs=x, expected=y)
            for i, (x, y) in enumerate(rows)
        )

    return Dataset(
        name="authored-normalization-v1",
        evidence_kind="authored_software_fixture",
        family="record-normalization",
        development=cases("dev", "101"),
        validation=cases("val", "202"),
        test=cases("test", "303"),
    )
