# workevo — technical README

workevo 0.1.0 is an installable Python library and CLI for bounded search over reusable external agent state. Model weights stay fixed. The core separates execution, evaluation, proposal, selection, and artifact reuse.

[Project introduction](README.md) · [Benchmark report](docs/BENCHMARKS.md) · [API reference](docs/API.md) · [Integration guide](docs/INTEGRATION.md)

## Installation and development

Supported and checked: Python 3.11, 3.12, and 3.13. Pydantic is the only direct runtime dependency. Model SDKs, Navconr, a graph database, and a web server are optional application choices.

```bash
git clone https://github.com/Twilight-Techy/workevo.git
cd workevo
uv sync --locked
uv run workevo --version
```

For a core-only installation from the checkout:

```bash
python3 -m pip install .
workevo --help
```

The distribution is not published to a package registry; `pip install .` installs the checkout. Dependency versions/hashes are recorded in [uv.lock](uv.lock).

## Architecture

```text
Dataset + evaluator + registry + limits + supplied/generated skill
    │
    ├─ Development execution ── feedback ── bounded mutation proposer
    │                                             │
    └─ Candidate execution ◀───────────────────────┘
             │
             └─ Exact evaluation → paired validation gate
                                      │
                                      └─ Atomic champion update
                                               │
                                               └─ Freeze → final test → export
                                                                         │
                                                                         └─ Execute on new inputs

SQLite: immutable skills, trial attempts, usage, lineage, decisions, leases
Exports: skill.json, SKILL.md, report.json, self-contained inspector.html
```

| Module | Responsibility |
| --- | --- |
| `contracts` | Versioned JSON records, graph/split validation, canonical hashes, limits and policy |
| `runner` | Trusted async operator registry, copied task state, bounded steps/visits and execution traces |
| `evaluation` | Evaluator-owned expected outputs, exact scoring and complete case/repeat evidence |
| `optimization` | Supplied/retrieved/generated seeds, mutation policies, checkpoints and stop reasons |
| `selection` | Paired promotion plus comparable Pareto archives and constrained routing |
| `store` | SQLite transactions, immutable artifacts, durable attempts, usage and writer leases |
| `adapters` | Application-owned model callbacks and pinned context adapters |
| `registry` / `deployment` | Verified skill bundles, lookup and execution without evaluation labels |
| `reporting` / `cli` | Source-free exports, the local inspector and command-line entry points |

The [contracts](docs/CONTRACTS.md) define exact behavior; [schemas.json](docs/schemas.json) exports the implemented record formats.

## Minimal library example

This example runs offline on the authored fixture. `FeedbackProposer` is a domain policy that inspects development failures; it is not an LLM.

```python
import asyncio
from pathlib import Path

from workevo import Optimizer, Store, authored_dataset, builtin_registry, run_skill, seed_skill
from workevo.optimization import FeedbackProposer
from workevo.registry import export_skill


async def main():
    directory = Path(".workevo/library-example")
    with Store(directory / "studies.sqlite") as store:
        optimizer = Optimizer(store, authored_dataset(), builtin_registry(), FeedbackProposer())
        study = optimizer.create(seed_skill())
        result = await optimizer.run(study)
        if result.champion is None:
            raise RuntimeError(result.stop_reason)

        optimizer.freeze(study)
        final = await optimizer.final_test(study)
        bundle = export_skill(store, study, optimizer.evaluator, directory / "skill.json")
        deployed = await run_skill(
            bundle,
            {"identifier": " 0017 ", "display_name": " Ada "},
            optimizer.registry,
            store,
        )
        print(final["quality"])
        print(deployed.output)


asyncio.run(main())
```

Expected output: `1.0`, then `{'id': '0017', 'name': 'Ada'}`. This is fixture correctness, not a model-quality result. [examples/quickstart.py](examples/quickstart.py) adds a source-free report and the HTML inspector.

## CLI lifecycle and reuse

Run the complete authored example:

```bash
uv run workevo demo --directory .workevo/demo
```

The demo is scripted to include a later regression. Its retained champion is an earlier revision. To run a separate study with your own application configuration, expose an importable factory returning `Optimizer` and supply a compatible seed:

```bash
workevo run --database .workevo/app.sqlite \
  --factory myapp.workflow_config:create_optimizer --seed seed.json
```

`run` does not open the test partition. After search stops, `freeze` prevents further optimization; `test` evaluates the frozen champion. `export` writes the portable bundle and companion instructions. Repeated completed tests return the existing result without additional model calls. See [the full command list](docs/API.md).

For independent execution, create `input.json` with `{"identifier":" 0017 ","display_name":" Ada "}` and run:

```bash
workevo execute .workevo/demo/skill.json \
  --input input.json --database .workevo/deployment.sqlite
```

Execution does not load reference answers or the dataset. Import preserves provenance and does not automatically promote an artifact. Current implementation, operator and context identities must match the bundle.

## Integrating models and custom tasks

- **Target model:** map an existing async application function into `CallableModel`, then register it with `register_model_operator`. The returned operator version belongs in the workflow node.
- **Optimizer model:** use `ModelProposer`, or a custom proposer that maps a compact edit format into validated `Skill` records. `create(scaffold, generate_seed=True)` budgets initial generation and later mutations in the same study.
- **Task family:** supply a `Dataset` with disjoint development/validation/test cases and a compatible `Evaluator`. The core scorer uses exact JSON equality after the declared output validator.
- **Host operators:** register trusted async functions with strict parameter schemas. Workflows support sequences and boolean branches; per-node visit limits and global step/retry bounds constrain cycles.
- **Context:** use `MappingContext` or the optional `NavconrContext` callback adapter, with immutable revision identities and explicit byte bounds.

Model callbacks receive `(payload, max_output_tokens, timeout_seconds)` and return `CallResult` with parsed JSON and `ModelUsage`. Your application owns SDKs, wire formats, credentials, retries and pricing snapshots. Change identities when model settings or captured dependencies change. [existing_application.py](examples/existing_application.py) shows the boundary without making calls on import; [INTEGRATION.md](docs/INTEGRATION.md) covers the complete contract.

## Selection, budgets and recovery

Default promotion requires complete compatible development/validation evidence, valid output schemas, the configured correctness floor, and no per-case correctness regression. Strictly better quality wins; exact quality ties can win with fewer mean operator calls. Exact ties retain the incumbent. The store independently rechecks accepted promotions inside the champion transaction.

`Limits` covers candidates, trials, calls, retries, tokens, micro-USD, validation looks, absolute elapsed time, mutation size and artifact size. Reservations precede dispatch; unknown usage stays reserved, and known overruns are recorded. Hard token/spend limits require a host adapter that declares enforceable caps and supplies the required usage. The generic callback boundary cannot guarantee arbitrary vendor billing behavior.

A study pins implementation, dataset/evaluator, registry, proposer and context identities. Incompatible changes reject resumed comparisons. Source hashing is conservative: even a runtime-neutral source edit can make an older study incompatible. Historical reports keep their original hashes.

Interrupted local attempts require explicit recovery. `resume --recover` can reclaim a verified abandoned lease, preserving usage charges. An unresolved proposer is abandoned explicitly with `discard-proposal`; it is never silently replayed. Absolute deadlines include downtime. See [OPERATIONS.md](docs/OPERATIONS.md) for details.

Generated workflows cannot introduce executable source, imports or shell commands. Registered Python callbacks are trusted host code and must cooperate with cancellation; version 0.1.0 does not provide an OS sandbox for arbitrary generated programs.

## Benchmarks and checks

The [benchmark report](docs/BENCHMARKS.md) documents the dataset, controls, raw metrics, live-check scope and missing research evidence. No new paid call is required to reproduce the offline benchmark or render its figures.

```bash
make check
uv run python scripts/software_study.py --output .workevo/benchmark-review/software-study.json
uv run python scripts/live_benchmark.py --dry-run --output .workevo/benchmark-review/rehearsal.json
```

The ordinary suite has 62 tests. Hosted checks cover Python 3.11–3.13, lint/type checks, builds and the inspector. To check the actual local HTML in a browser:

```bash
uv sync --locked --group browser
uv run --group browser playwright install chromium
uv run workevo demo --directory .workevo/demo
uv run --group browser python scripts/check_inspector.py .workevo/demo/inspector.html
```

`--live` in `scripts/live_benchmark.py` makes paid model requests. The recorded three-call Haiku allowance was already exercised; the README refresh does not repeat it. Offline rehearsals explicitly label their simulated usage/costs.

## Build and project status

```bash
uv run python scripts/release.py
```

The release check builds a wheel/source archive, verifies license/asset inclusion and private-history exclusion, installs the wheel in a fresh Python 3.12 core-only environment, and executes the demo/import/deployment path. It does not publish anything.

The library and inspector are implemented under [MIT](LICENSE). The independently reviewed empirical study, compatible upstream optimizer comparisons, broader transfer/uncertainty evaluation and package-registry publication remain open. [STATUS.md](docs/STATUS.md) owns the evidence boundary; [TASKS.md](docs/TASKS.md) tracks acceptance. Core/runtime licensing and authored asset provenance are in [DEPENDENCIES.md](docs/DEPENDENCIES.md).
