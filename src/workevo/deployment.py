"""Execute a portable artifact without loading evaluator labels or optimization data."""

from __future__ import annotations

from pydantic import JsonValue

from .adapters import ContextProvider, MappingContext
from .contracts import Limits, Record, StudyConfig, digest, implementation_identity
from .errors import Incompatible
from .registry import Bundle
from .runner import Registry, execute
from .store import Store


class DeploymentResult(Record):
    study_id: str
    revision: str
    output: JsonValue
    complete: bool
    reason: str
    calls: int
    latency_ms: float


async def run_skill(
    bundle: Bundle,
    inputs: JsonValue,
    registry: Registry,
    store: Store,
    *,
    context: ContextProvider | None = None,
    limits: Limits | None = None,
) -> DeploymentResult:
    context = context or MappingContext({})
    if bundle.config.implementation_hash != implementation_identity():
        raise Incompatible("deployment requires the validated implementation revision")
    if (
        registry.identity != bundle.config.registry_hash
        or context.identity != bundle.config.context_hash
    ):
        raise Incompatible("deployment operator/context environment differs from validated bundle")
    registry.validate(bundle.skill)
    sources = {
        requirement.key: context.resolve(requirement)
        for requirement in bundle.skill.context_requirements
    }
    store.put("skill", bundle.skill)
    config = StudyConfig(
        implementation_hash=implementation_identity(),
        dataset_hash=digest({"deployment_input": inputs}),
        family=bundle.skill.family,
        evaluator="deployment-no-evaluator",
        registry_hash=registry.identity,
        proposer="none",
        seed=bundle.revision,
        context_hash=context.identity,
        limits=limits or Limits(),
    )
    study = store.create(config)
    with store.lease(study):
        store.charge(study, {"candidates": 1, "trials": 1})
        attempt = store.start_attempt(study, bundle.revision, "deployment", "request", 0)
        result = await execute(bundle.skill, inputs, registry, store, study, sources)
        output = DeploymentResult(
            study_id=study,
            revision=bundle.revision,
            output=result.output,
            complete=result.complete,
            reason=result.reason,
            calls=result.calls,
            latency_ms=result.latency_ms,
        )
        store.finish_attempt(
            attempt, {"deployment": output.model_dump(mode="json"), "trace": result.trace}
        )
        _, state, _ = store.study(study)
        state["status"] = "stopped"
        state["stop_reason"] = result.reason
        with store.transaction():
            store.save_state(study, state)
            store.event(
                study,
                "deployment_completed",
                {
                    "revision": bundle.revision,
                    "complete": result.complete,
                    "output_hash": digest(result.output),
                },
            )
    return output
