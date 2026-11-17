"""Application-owned model/context callbacks with explicit capability contracts."""

from __future__ import annotations

import asyncio
import copy
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Protocol

from pydantic import JsonValue

from .contracts import ContextRequirement, ModelUsage, Record, canonical, digest
from .errors import BudgetExceeded, DeadlineExceeded, Incompatible
from .runner import EmptyParameters, OperatorContext, Registry
from .store import Store


class CallResult(Record):
    output: JsonValue
    usage: ModelUsage


# The host adapts its own SDK, request envelope and response fields here.
ModelCallback = Callable[[dict[str, JsonValue], int, float], Awaitable[CallResult]]


class CallableModel:
    def __init__(
        self,
        callback: ModelCallback,
        *,
        identity: str,
        max_output_tokens: int = 1024,
        reservation: ModelUsage | None = None,
        enforceable_caps: bool = False,
    ) -> None:
        if not identity or max_output_tokens < 1:
            raise ValueError("model identity and positive output cap required")
        self.callback = callback
        self.identity = identity
        self.max_output_tokens = max_output_tokens
        self.reservation = reservation or ModelUsage()
        self.enforceable_caps = enforceable_caps

    async def call(self, payload: dict[str, JsonValue], store: Store, study: str) -> JsonValue:
        config, _, _ = store.study(study)
        cap = config.limits
        if len(canonical(payload).encode()) > cap.artifact_bytes:
            raise Incompatible("model request exceeds artifact cap")
        for name in ("tokens", "micro_usd"):
            if getattr(cap, name) is not None and (
                not self.enforceable_caps or getattr(self.reservation, name) is None
            ):
                raise Incompatible("model cannot enforce requested hard usage cap")
        reserved = {
            name: getattr(self.reservation, name)
            for name in ("tokens", "micro_usd")
            if getattr(self.reservation, name) is not None
        }
        store.charge(study, {"model_calls": 1, **reserved})
        store.event(
            study,
            "model_dispatched",
            {"identity": self.identity, "reservation": reserved, "request_hash": digest(payload)},
        )
        try:
            remaining = store.remaining(study)
            if remaining <= 0:
                raise DeadlineExceeded("model deadline exceeded")
            response = await asyncio.wait_for(
                self.callback(copy.deepcopy(payload), self.max_output_tokens, remaining),
                timeout=remaining,
            )
            response = CallResult.model_validate_json(response.model_dump_json())
        except asyncio.CancelledError:
            store.event(
                study, "model_unresolved", {"reason": "cancelled", "reservation_retained": True}
            )
            raise
        except (TimeoutError, DeadlineExceeded):
            store.event(
                study,
                "model_unresolved",
                {"reason": "deadline_exceeded", "reservation_retained": True},
            )
            raise DeadlineExceeded("model deadline exceeded") from None
        except Exception:
            store.event(
                study,
                "model_unresolved",
                {"reason": "callback_failed", "reservation_retained": True},
            )
            raise Incompatible("model callback failed; reservation retained") from None
        actual = {
            name: getattr(response.usage, name)
            for name in ("tokens", "micro_usd")
            if getattr(response.usage, name) is not None
        }
        store.event(
            study,
            "model_completed",
            {
                "identity": self.identity,
                "output_hash": digest(response.output),
                "usage": response.usage.model_dump(mode="json"),
            },
        )
        if response.usage.tokens is not None and response.usage.tokens_kind == "estimated":
            store.event(
                study, "estimated_usage", {"metric": "tokens", "value": response.usage.tokens}
            )
            # Never refund a hard reservation using an estimated count.
            if cap.tokens is not None:
                actual.pop("tokens", None)
                store.reconcile(study, reserved, actual)
                raise BudgetExceeded("hard token cap requires measured usage; reservation retained")
        store.reconcile(study, reserved, actual)
        missing = [name for name in ("tokens", "micro_usd") if name not in actual]
        if missing:
            store.event(study, "unknown_usage", {"metrics": missing, "reservation_retained": True})
            if any(getattr(cap, name) is not None for name in missing):
                raise BudgetExceeded("required model usage missing; reservation retained")
        if store.remaining(study) <= 0:
            raise DeadlineExceeded("model deadline exceeded")
        if len(canonical(response.output).encode()) > cap.artifact_bytes:
            raise Incompatible("model response exceeds artifact cap")
        return response.output


def register_model_operator(
    registry: Registry, model: CallableModel, *, name: str = "model"
) -> str:
    """Register one model execution node; returns its required operator version."""

    async def invoke(
        state: JsonValue, parameters: dict[str, Any], context: OperatorContext
    ) -> JsonValue:
        return await model.call(
            {
                "schema_version": 1,
                "instructions": context.instructions,
                "input": state,
                "context": dict(context.sources),
            },
            context.store,
            context.study_id,
        )

    version = digest(
        {
            "model": model.identity,
            "output_cap": model.max_output_tokens,
            "reservation": model.reservation.model_dump(),
            "caps": model.enforceable_caps,
        }
    )
    registry.register(name, invoke, EmptyParameters, version=version)
    return version


class ContextProvider(Protocol):
    @property
    def identity(self) -> str: ...
    def resolve(self, requirement: ContextRequirement) -> str: ...


@dataclass(frozen=True)
class MappingContext:
    """Pinned application-supplied context; keys are (logical key, source revision)."""

    values: dict[tuple[str, str], str]

    @property
    def identity(self) -> str:
        return digest({f"{k[0]}@{k[1]}": v for k, v in sorted(self.values.items())})

    def resolve(self, requirement: ContextRequirement) -> str:
        try:
            text = self.values[(requirement.key, requirement.revision)]
        except KeyError:
            raise Incompatible("required pinned context is unavailable") from None
        if len(text.encode()) > requirement.max_bytes:
            raise Incompatible("context exceeds declared bound")
        return text


class NavconrContext:
    """Optional adapter around application-owned exact-span reads; no Navconr imports."""

    def __init__(
        self, read: Callable[[str, str], str], *, index_revision: str, spans: dict[str, str]
    ) -> None:
        if not index_revision:
            raise ValueError("pinned index revision required")
        self.read = read
        self.index_revision = index_revision
        self.spans = dict(spans)

    @property
    def identity(self) -> str:
        return digest(
            {"kind": "navconr-exact-span-v1", "revision": self.index_revision, "spans": self.spans}
        )

    def resolve(self, requirement: ContextRequirement) -> str:
        if requirement.revision != self.index_revision or requirement.key not in self.spans:
            raise Incompatible("Navconr context revision/key mismatch")
        text = self.read(self.index_revision, self.spans[requirement.key])
        if not isinstance(text, str) or len(text.encode()) > requirement.max_bytes:
            raise Incompatible("Navconr context is not bounded exact text")
        return text
