"""Bounded execution of trusted, explicitly registered async operators."""

from __future__ import annotations

import asyncio
import copy
import inspect
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict, JsonValue, TypeAdapter, ValidationError

from .contracts import Skill, canonical, digest
from .errors import BudgetExceeded, DeadlineExceeded, InvalidCandidate
from .store import Store

JSON: TypeAdapter[JsonValue] = TypeAdapter(JsonValue)  # type: ignore[arg-type]


@dataclass(frozen=True)
class OperatorContext:
    instructions: str
    sources: dict[str, str]
    deadline: float
    store: Store
    study_id: str


Operator = Callable[[JsonValue, dict[str, Any], OperatorContext], Awaitable[JsonValue]]


@dataclass(frozen=True)
class Registration:
    function: Operator
    parameters: type[BaseModel]
    version: str
    source_hash: str


class Registry:
    def __init__(self) -> None:
        self._operators: dict[str, Registration] = {}

    def register(
        self, name: str, function: Operator, parameters: type[BaseModel], *, version: str = "1"
    ) -> None:
        if name in self._operators or not inspect.iscoroutinefunction(function):
            raise ValueError("operator must be unique and async")
        if parameters.model_config.get("extra") != "forbid":
            raise ValueError("operator parameter schema must forbid unknown fields")
        try:
            source = inspect.getsource(function)
        except (OSError, TypeError):
            source = f"{function.__module__}.{function.__qualname__}:{version}"
        self._operators[name] = Registration(function, parameters, version, digest(source))

    @property
    def identity(self) -> str:
        return digest(
            {
                name: {
                    "version": op.version,
                    "source": op.source_hash,
                    "schema": op.parameters.model_json_schema(),
                }
                for name, op in sorted(self._operators.items())
            }
        )

    def validate(self, skill: Skill) -> None:
        # Revalidate nested containers; Pydantic frozen prevents assignment, not nested dict edits.
        Skill.model_validate_json(skill.model_dump_json())
        for node in skill.workflow.nodes:
            operator = self._operators.get(node.operator)
            if operator is None or operator.version != node.version:
                raise InvalidCandidate("unavailable operator/version")
            try:
                operator.parameters.model_validate(node.parameters)
            except ValidationError:
                raise InvalidCandidate("invalid operator parameters") from None

    def get(self, name: str) -> Registration:
        return self._operators[name]


@dataclass(frozen=True)
class Execution:
    output: JsonValue
    complete: bool
    reason: str
    calls: int
    latency_ms: float
    trace: tuple[dict[str, Any], ...]


async def execute(
    skill: Skill,
    inputs: JsonValue,
    registry: Registry,
    store: Store,
    study: str,
    sources: dict[str, str] | None = None,
) -> Execution:
    registry.validate(skill)
    config, _, _ = store.study(study)
    cap = config.limits.artifact_bytes
    start = time.monotonic()
    context = OperatorContext(
        skill.instructions,
        copy.deepcopy(sources or {}),
        time.monotonic() + max(0, store.remaining(study)),
        store,
        study,
    )
    state = JSON.validate_python(copy.deepcopy(inputs))
    nodes = {n.id: n for n in skill.workflow.nodes}
    at = skill.workflow.entry
    visits: dict[str, int] = {}
    trace: list[dict[str, Any]] = []
    calls = 0
    reason = "completed"
    try:
        if len(canonical(state).encode()) > cap:
            state = None
            raise InvalidCandidate("input exceeds artifact cap")
        while at not in skill.workflow.terminals:
            node = nodes[at]
            visits[at] = visits.get(at, 0) + 1
            if calls >= skill.workflow.max_steps or visits[at] > node.max_visits:
                raise BudgetExceeded("workflow step/visit bound exhausted")
            charges = {"tool_calls": 1}
            if visits[at] > 1:
                charges["retries"] = 1
            store.charge(study, charges)
            store.event(
                study,
                "operator_started",
                {"node": at, "operator": node.operator, "input_hash": digest(state)},
            )
            calls += 1
            op = registry.get(node.operator)
            remaining = store.remaining(study)
            if remaining <= 0:
                raise DeadlineExceeded("deadline exceeded")
            stamp = time.monotonic()
            result = await asyncio.wait_for(
                op.function(
                    copy.deepcopy(state),
                    op.parameters.model_validate(node.parameters).model_dump(),
                    context,
                ),
                timeout=remaining,
            )
            if store.remaining(study) <= 0:
                raise DeadlineExceeded("deadline exceeded")
            state = JSON.validate_python(result)
            if len(canonical(state).encode()) > cap:
                state = None
                raise InvalidCandidate("operator artifact exceeds cap")
            trace.append(
                {
                    "node": at,
                    "operator": node.operator,
                    "output_hash": digest(state),
                    "duration_ms": (time.monotonic() - stamp) * 1000,
                }
            )
            if node.branch_field:
                flag = state.get(node.branch_field) if isinstance(state, dict) else None
                if type(flag) is not bool:
                    raise InvalidCandidate("branch result must be a boolean")
                at = node.next if flag else str(node.on_false)
            else:
                at = node.next
    except asyncio.CancelledError:
        raise
    except (TimeoutError, DeadlineExceeded):
        reason = "deadline_exceeded"
    except BudgetExceeded:
        reason = "budget_exhausted"
    except (InvalidCandidate, ValidationError):
        reason = "invalid_candidate"
    except Exception:
        reason = "operator_failed"  # Callback exceptions can contain credentials or task content.
    return Execution(
        state, reason == "completed", reason, calls, (time.monotonic() - start) * 1000, tuple(trace)
    )


class NormalizeParameters(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    aliases: bool = False
    trim: bool = False


class EmptyParameters(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


async def normalize_record(
    state: JsonValue, parameters: dict[str, Any], context: OperatorContext
) -> JsonValue:
    record = state if isinstance(state, dict) else {}
    result: dict[str, JsonValue] = {}
    for field, alias in (("id", "identifier"), ("name", "display_name")):
        value = record.get(field)
        if field not in record and parameters["aliases"]:
            value = record.get(alias)
        if field == "id" and type(value) is int:
            value = str(value)
        if not isinstance(value, str):
            value = None
        if isinstance(value, str) and parameters["trim"]:
            value = value.strip() or None
        result[field] = value
    return result


async def identity(
    state: JsonValue, parameters: dict[str, Any], context: OperatorContext
) -> JsonValue:
    return state


def builtin_registry() -> Registry:
    registry = Registry()
    registry.register("normalize_record", normalize_record, NormalizeParameters)
    registry.register("identity", identity, EmptyParameters)
    return registry
