import asyncio

import pytest

from workevo import (
    CallableModel,
    CallResult,
    Limits,
    ModelProposer,
    ModelUsage,
    Node,
    Optimizer,
    SequenceProposer,
    Skill,
    Workflow,
    builtin_registry,
    register_model_operator,
)
from workevo.contracts import canonical
from workevo.errors import BudgetExceeded, Incompatible


async def test_application_owned_sdk_mapping_and_accounting(system):
    store, optimizer, seed = system
    seen = []

    async def host(payload, cap, timeout):
        # A host can use any SDK request/response format inside this boundary.
        sdk_reply = {
            "text_fields": {"id": "001", "name": "Ada"},
            "bill": {"tokens": 7, "micros": 2},
        }
        seen.append((payload, cap, timeout))
        return CallResult(
            output=sdk_reply["text_fields"],
            usage=ModelUsage(
                tokens=sdk_reply["bill"]["tokens"], micro_usd=sdk_reply["bill"]["micros"]
            ),
        )

    model = CallableModel(
        host,
        identity="application-client-v1",
        reservation=ModelUsage(tokens=20, micro_usd=10),
        enforceable_caps=True,
    )
    study = optimizer.create(seed, limits=Limits(tokens=100, micro_usd=100))
    assert await model.call({"input": "hello"}, store, study) == {"id": "001", "name": "Ada"}
    assert store.usage(study)["tokens"] == 7
    assert store.usage(study)["micro_usd"] == 2
    assert seen[0][1] == 1024 and seen[0][2] > 0
    assert "hello" not in canonical(store.events(study))


async def test_hard_caps_refuse_before_dispatch(system):
    store, optimizer, seed = system

    async def forbidden(*args):
        raise AssertionError("must not dispatch")

    model = CallableModel(forbidden, identity="unknown-usage")
    study = optimizer.create(seed, limits=Limits(tokens=10))
    with pytest.raises(Incompatible):
        await model.call({}, store, study)
    assert store.usage(study) == {}


async def test_missing_usage_retains_reservation_and_known_overrun(system):
    store, optimizer, seed = system

    async def missing(*args):
        return CallResult(output={}, usage=ModelUsage(tokens=4))

    model = CallableModel(
        missing,
        identity="partial",
        reservation=ModelUsage(tokens=10, micro_usd=8),
        enforceable_caps=True,
    )
    study = optimizer.create(seed, limits=Limits(tokens=100, micro_usd=100))
    with pytest.raises(BudgetExceeded):
        await model.call({}, store, study)
    assert store.usage(study)["tokens"] == 4
    assert store.usage(study)["micro_usd"] == 8

    async def overrun(*args):
        return CallResult(output={}, usage=ModelUsage(tokens=50, micro_usd=3))

    model = CallableModel(
        overrun,
        identity="broken-cap",
        reservation=ModelUsage(tokens=10, micro_usd=8),
        enforceable_caps=True,
    )
    study = optimizer.create(seed, limits=Limits(tokens=100, micro_usd=100))
    with pytest.raises(BudgetExceeded):
        await model.call({}, store, study)
    assert store.usage(study)["tokens"] == 50
    assert store.usage(study)["micro_usd"] == 3


async def test_failure_no_retries_and_no_secret_errors(system):
    store, optimizer, seed = system
    count = 0

    async def failure(*args):
        nonlocal count
        count += 1
        raise RuntimeError("SECRET_API_KEY")

    model = CallableModel(failure, identity="failing", reservation=ModelUsage(tokens=20))
    study = optimizer.create(seed)
    with pytest.raises(Incompatible) as error:
        await model.call({}, store, study)
    assert "SECRET" not in str(error.value)
    assert count == 1 and store.usage(study)["tokens"] == 20


async def test_unknown_uncapped_usage_is_explicit(system):
    store, optimizer, seed = system

    async def unknown(*args):
        return CallResult(output={}, usage=ModelUsage())

    study = optimizer.create(seed)
    await CallableModel(unknown, identity="unknown").call({}, store, study)
    assert any(e["kind"] == "unknown_usage" for e in store.events(study))
    assert "tokens" not in store.usage(study)


async def test_recorded_model_execution_operator(system):
    store, original, seed = system

    async def host(payload, cap, timeout):
        assert "expected" not in payload
        return CallResult(
            output={"id": None, "name": None}, usage=ModelUsage(tokens=1, micro_usd=0)
        )

    registry = builtin_registry()
    version = register_model_operator(
        registry,
        CallableModel(
            host,
            identity="target-fixture",
            reservation=ModelUsage(tokens=10, micro_usd=0),
            enforceable_caps=True,
        ),
    )
    skill = Skill(
        skill_id="target",
        family=seed.family,
        instructions="Normalize inputs",
        workflow=Workflow(entry="x", nodes=(Node(id="x", operator="model", version=version),)),
    )
    optimizer = Optimizer(store, original.dataset, registry, SequenceProposer(()))
    study = optimizer.create(skill, limits=Limits(model_calls=20, tokens=200))
    result = await optimizer.run(study)
    assert result.champion == skill.revision
    assert store.usage(study)["model_calls"] == 16 and store.usage(study)["tokens"] == 16


async def test_proposer_cancellation_is_not_silently_replayed(system):
    store, original, seed = system
    started = asyncio.Event()

    async def host(payload, cap, timeout):
        started.set()
        await asyncio.sleep(100)

    model = CallableModel(host, identity="pending", reservation=ModelUsage(tokens=20))
    optimizer = Optimizer(store, original.dataset, original.registry, ModelProposer(model))
    study = optimizer.create(seed)
    task = asyncio.create_task(optimizer.run(study))
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    with pytest.raises(Incompatible, match="unresolved proposal"):
        await optimizer.run(study)
    assert store.usage(study)["model_calls"] == 1
    optimizer.discard_unresolved_proposal(study)
    assert store.study(study)[1]["pending_proposal"] is False
    assert store.usage(study)["tokens"] == 20


async def test_model_proposer_validates_output_and_protected_edit(system):
    store, original, seed = system
    candidate = original.proposer.candidates[0]

    async def host(payload, cap, timeout):
        assert "validation" not in payload and "test" not in payload
        return CallResult(output=candidate.model_dump(mode="json"), usage=ModelUsage(tokens=1))

    model = CallableModel(host, identity="proposer-fixture", reservation=ModelUsage(tokens=10))
    optimizer = Optimizer(store, original.dataset, original.registry, ModelProposer(model))
    study = optimizer.create(seed, limits=Limits(candidates=2))
    result = await optimizer.run(study)
    assert result.champion == candidate.revision
    assert store.usage(study)["model_calls"] == 1


async def test_estimated_tokens_do_not_release_hard_reservation(system):
    store, optimizer, seed = system

    async def host(*args):
        return CallResult(output={}, usage=ModelUsage(tokens=2, tokens_kind="estimated"))

    model = CallableModel(
        host, identity="estimated", reservation=ModelUsage(tokens=10), enforceable_caps=True
    )
    study = optimizer.create(seed, limits=Limits(tokens=100))
    with pytest.raises(BudgetExceeded):
        await model.call({}, store, study)
    assert store.usage(study)["tokens"] == 10
