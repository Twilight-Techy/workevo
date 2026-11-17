"""Application-owned target and proposer callbacks; importing performs no calls.

Replace the host functions with your existing SDK calls. No SDK or wire format is
required by workevo. Keep credentials in your application.
"""

from workevo import (
    CallableModel,
    ModelProposer,
    Node,
    Optimizer,
    Skill,
    Workflow,
    authored_dataset,
    builtin_registry,
    register_model_operator,
)


async def host_target(payload, max_output_tokens, timeout_seconds):
    # Example mapping for an already-owned SDK:
    # reply = await client.execute(data=payload, limit=max_output_tokens,
    #                              timeout=timeout_seconds, retries=0)
    # return CallResult(output=reply.parsed, usage=ModelUsage(tokens=reply.total_tokens))
    raise NotImplementedError("Configure your application target client")


async def host_proposer(payload, max_output_tokens, timeout_seconds):
    raise NotImplementedError("Configure your application optimizer client")


def create_optimizer(store):
    # Identity must pin model, settings, SDK retry policy, prompt version and any pricing snapshot.
    target = CallableModel(host_target, identity="my-target-model-config-v1", max_output_tokens=256)
    proposer = CallableModel(
        host_proposer, identity="my-optimizer-model-config-v1", max_output_tokens=2048
    )
    registry = builtin_registry()
    register_model_operator(registry, target)
    optimizer = Optimizer(store, authored_dataset(), registry, ModelProposer(proposer))
    return optimizer


def target_scaffold(registry):
    # Obtain the version returned by register_model_operator in your own setup.
    version = registry.get("model").version
    return Skill(
        skill_id="normalize-record",
        family="record-normalization",
        instructions="Return exactly id and name as strings or null; preserve leading zeros.",
        workflow=Workflow(
            entry="model", nodes=(Node(id="model", operator="model", version=version),)
        ),
    )
