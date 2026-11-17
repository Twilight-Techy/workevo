"""Offline-first command line. External callbacks are explicitly application-owned."""

from __future__ import annotations

import argparse
import asyncio
import importlib
import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from .contracts import Dataset, Limits, Node, Policy, Skill, StudyConfig, Workflow
from .deployment import run_skill
from .errors import EvolverError
from .evaluation import authored_dataset
from .optimization import Optimizer, demo_proposer, seed_skill
from .registry import atomic_write, export_skill, import_skill, lookup
from .reporting import write_report
from .runner import builtin_registry
from .store import Store


def load_factory(spec: str, store: Store) -> Optimizer:
    module, separator, name = spec.partition(":")
    if not separator:
        raise ValueError("factory must use module:function syntax")
    value = getattr(importlib.import_module(module), name)(store)
    if not isinstance(value, Optimizer):
        raise ValueError("factory must return an Optimizer")
    return value


def default_optimizer(store: Store) -> Optimizer:
    seed = seed_skill()
    return Optimizer(store, authored_dataset(), builtin_registry(), demo_proposer(seed))


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        prog="workevo", description="Optimize and inspect reusable bounded workflows"
    )
    root.add_argument("--version", action="version", version="workevo 0.1.0")
    sub = root.add_subparsers(dest="command", required=True)
    demo = sub.add_parser("demo", help="Run the complete offline authored example")
    demo.add_argument("--directory", type=Path, default=Path(".workevo/demo"))
    demo.add_argument("--candidates", type=int, default=6)
    schemas = sub.add_parser("schemas", help="Export versioned JSON schemas")
    schemas.add_argument("--output", type=Path)
    fixture = sub.add_parser("fixture", help="Export the authored fixture and seed")
    fixture.add_argument("directory", type=Path)
    for name in (
        "run",
        "resume",
        "freeze",
        "test",
        "report",
        "export",
        "inspect",
        "discard-proposal",
    ):
        p = sub.add_parser(name)
        p.add_argument("--database", type=Path, required=True)
        p.add_argument("--factory", help="Application-owned module:function returning Optimizer")
        if name == "run":
            p.add_argument("--seed", type=Path)
            p.add_argument("--generate-seed", action="store_true")
            p.add_argument("--limits", type=Path)
        else:
            p.add_argument("--study", required=True)
        if name in ("resume", "test"):
            p.add_argument(
                "--recover",
                action="store_true",
                help="Explicitly recover abandoned local attempts; retains charges",
            )
        if name in ("report", "inspect", "export"):
            p.add_argument("--output", type=Path, required=True)
    deploy = sub.add_parser("execute", help="Execute a bundle without evaluator data")
    deploy.add_argument("bundle", type=Path)
    deploy.add_argument("--input", type=Path, required=True)
    deploy.add_argument("--database", type=Path, required=True)
    deploy.add_argument("--factory")
    p = sub.add_parser("import")
    p.add_argument("bundle", type=Path)
    p.add_argument("--database", type=Path, required=True)
    p = sub.add_parser("lookup")
    p.add_argument("family")
    p.add_argument("--database", type=Path, required=True)
    p.add_argument("--context-hash", required=True)
    return root


async def dispatch(args: argparse.Namespace) -> Any:
    if args.command == "schemas":
        data = {
            model.__name__: model.model_json_schema()
            for model in (Skill, Node, Workflow, Dataset, Limits, Policy, StudyConfig)
        }
        if args.output:
            atomic_write(args.output, json.dumps(data, indent=2) + "\n")
            return {"schemas": str(args.output)}
        return data
    if args.command == "fixture":
        atomic_write(
            args.directory / "dataset.json", authored_dataset().model_dump_json(indent=2) + "\n"
        )
        atomic_write(args.directory / "seed.json", seed_skill().model_dump_json(indent=2) + "\n")
        return {"directory": str(args.directory)}
    if args.command == "demo":
        args.directory.mkdir(parents=True, exist_ok=True)
        with Store(args.directory / "studies.sqlite") as store:
            optimizer = default_optimizer(store)
            study = optimizer.create(seed_skill(), limits=Limits(candidates=args.candidates))
            result = await optimizer.run(study)
            if result.champion:
                optimizer.freeze(study)
                await optimizer.final_test(study)
                export_skill(store, study, optimizer.evaluator, args.directory / "skill.json")
            write_report(store, study, optimizer.evaluator, args.directory)
            return result.model_dump(mode="json") | {
                "inspector": str((args.directory / "inspector.html").resolve())
            }
    with Store(args.database) as store:
        if args.command == "execute":
            optimizer = (
                load_factory(args.factory, store) if args.factory else default_optimizer(store)
            )
            bundle = import_skill(
                store, args.bundle, optimizer.registry, context_hash=optimizer.context.identity
            )
            output = await run_skill(
                bundle,
                json.loads(args.input.read_text()),
                optimizer.registry,
                store,
                context=optimizer.context,
            )
            return output.model_dump(mode="json")
        if args.command == "import":
            bundle = import_skill(store, args.bundle, builtin_registry())
            return {"revision": bundle.revision, "promoted": False}
        if args.command == "lookup":
            return lookup(store, args.family, builtin_registry(), context_hash=args.context_hash)
        optimizer = load_factory(args.factory, store) if args.factory else default_optimizer(store)
        if args.command == "run":
            seed = Skill.model_validate_json(args.seed.read_bytes()) if args.seed else seed_skill()
            limits = (
                Limits.model_validate_json(args.limits.read_bytes()) if args.limits else Limits()
            )
            study = optimizer.create(seed, limits=limits, generate_seed=args.generate_seed)
            result = await optimizer.run(study)
            return result.model_dump(mode="json")
        if args.command == "discard-proposal":
            optimizer.discard_unresolved_proposal(args.study)
            return {"abandoned": True, "refund": False}
        if args.command == "resume":
            return (await optimizer.run(args.study, recover=args.recover)).model_dump(mode="json")
        if args.command == "freeze":
            return {"revision": optimizer.freeze(args.study).revision}
        if args.command == "test":
            return await optimizer.final_test(args.study, recover=args.recover)
        if args.command == "export":
            return {
                "revision": export_skill(
                    store, args.study, optimizer.evaluator, args.output
                ).revision
            }
        if args.command in ("report", "inspect"):
            write_report(store, args.study, optimizer.evaluator, args.output)
            return {"inspector": str((args.output / "inspector.html").resolve())}
    raise ValueError("unknown command")


def main() -> None:
    args = parser().parse_args()
    try:
        value = asyncio.run(dispatch(args))
        print(json.dumps(value, ensure_ascii=False, indent=2))
    except KeyboardInterrupt:
        raise SystemExit(130) from None
    except (EvolverError, ValidationError, ValueError, OSError) as error:
        # Never print callback exceptions or Pydantic input values; they may contain secrets.
        print(
            json.dumps(
                {
                    "error": type(error).__name__,
                    "message": str(error)
                    if isinstance(error, EvolverError)
                    else "Invalid input or unavailable local resource; see command help and project contracts.",
                }
            )
        )
        raise SystemExit(2) from None
