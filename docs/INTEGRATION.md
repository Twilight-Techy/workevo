# Embed workevo

The core has one runtime dependency, Pydantic. Your application owns model clients, credentials, request formats, operator permissions, task data, and context access. No model SDK, graph database, server, or Navconr installation is required.

## Local library

```python
import asyncio
from workevo import Optimizer, Store, authored_dataset, builtin_registry, seed_skill
from workevo.optimization import FeedbackProposer


async def main():
    with Store(".workevo/example.sqlite") as store:
        optimizer = Optimizer(store, authored_dataset(), builtin_registry(), FeedbackProposer())
        study = optimizer.create(seed_skill())
        result = await optimizer.run(study)
        print(result.champion, result.stop_reason)
        optimizer.freeze(study)
        print((await optimizer.final_test(study))["quality"])


asyncio.run(main())
```

This is a deterministic fixture policy, not a general intelligence benchmark. The [complete example](../examples/quickstart.py) adds export, reporting and execution on a new input.

## Application-owned models

`CallableModel` accepts an async function `(payload, max_output_tokens, timeout_seconds) -> CallResult`. Put your existing SDK/wire-format mapping inside that function. Return parsed JSON output plus total token usage (including cached/reasoning tokens where applicable) and optional micro-USD cost. `ModelUsage` records whether values are measured or estimated; absent fields are unknown.

Use `register_model_operator(registry, target_model)` for task execution. It returns the operator version that must appear in a workflow node. Use `ModelProposer(optimizer_model)` for seed generation and subsequent mutations. [existing_application.py](../examples/existing_application.py) shows the configuration boundary without importing any vendor SDK or making calls on import.

Model identities must pin model/configuration, prompt wrapper, pricing snapshot and retry policy. The same identity cannot conceal a changed client or model. Disable SDK retries or account for every hidden attempt in an enforceable reservation. The wrapper itself never retries. Set provider output limits and timeout from the supplied arguments.

Hard token/spend caps require `enforceable_caps=True` and declared upper reservations. This is a host capability contract, not proof that an arbitrary SDK enforces limits. Unknown required usage retains the reservation and fails closed. Estimated token usage cannot release a hard reservation. Actual overruns remain recorded even if execution stops. Costs supplied as estimates remain labeled estimates in the model journal. Cancellation cannot guarantee that a remote service stops computing.

The callback receives development feedback and aggregate validation decisions only when used as a proposer. Target callbacks receive instructions, task inputs and bounded context. Neither receives validation/test answers. Keep task-family instructions in the scaffold; a model can generate its first actual workflow with `create(scaffold, generate_seed=True)`, with generation charged to the same study as search. Existing learned revisions can also seed a new study while preserving their ancestry.

## Your own tasks and operators

Create a `Dataset` with separate `Case` records under development, validation and test. Provide JSON inputs and evaluator-owned expected outputs. Split by template/source family and reject canonical duplicate inputs. Supply `Evaluator(dataset, validator=my_schema_validator, identity="my-exact-evaluator-v1")` for another output schema. Correctness is exact JSON equality; richer scoring requires an explicit evaluator extension and a new identity/protocol.

Register async operators with a Pydantic parameter model configured with `extra="forbid"`. An operator receives copied JSON state, validated parameters and an `OperatorContext`; it returns JSON for the next node. It may inspect instructions and pinned sources. Async code must cooperate with cancellation and must not block the event loop. These are trusted host functions, not untrusted generated programs. Node/registry versions and source fingerprints participate in comparison identity; change explicit versions for captured configuration and dependencies not visible in function source.

Pass `Policy` and `Limits` to `create`. Candidate changes cannot rewrite them. The core reference selector uses exact paired outcomes, a correctness floor, zero per-case regression and lower operator-call cost for correctness ties. Optional scalar objectives and Pareto routing are public utilities in `selection` and `contracts`; they do not override hard eligibility gates.

## Optional context

`MappingContext` maps `(key, revision)` to bounded text. A skill declares `ContextRequirement` records. Resolving a requirement never truncates silently. Changes to context identity invalidate comparisons.

`NavconrContext` accepts a host-owned `read(index_revision, span_id) -> str` callback, a pinned index revision, and a key-to-span map. The [real offline example](../examples/navconr_context.py) builds a fictional Navconr index and verifies exact source bytes. Install Navconr only in the host integration environment. Its own read/navigation budgets remain the host's responsibility; context content cannot grant tool permissions or alter evaluation labels.

## CLI factories

Expose `create_optimizer(store)` from an importable application module and return your configured `Optimizer`. Then use:

```bash
workevo run --database .workevo/my.sqlite \
  --factory myapp.workflow_config:create_optimizer --seed seed.json --generate-seed
```

Use the same factory with resume, freeze, test, report, export and execute so registry, proposer, evaluator and context identities remain compatible. CLI import/lookup without a factory support the built-in registry; custom registries use the Python import/lookup APIs. Core async APIs work in existing event loops; only the CLI and standalone examples call `asyncio.run`.
