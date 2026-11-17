"""Complete local optimization, export and deployment on authored data."""

import asyncio
from pathlib import Path

from workevo import (
    Optimizer,
    Store,
    authored_dataset,
    builtin_registry,
    run_skill,
    seed_skill,
)
from workevo.optimization import FeedbackProposer
from workevo.registry import export_skill
from workevo.reporting import write_report


async def main() -> None:
    directory = Path(".workevo/quickstart")
    with Store(directory / "studies.sqlite") as store:
        optimizer = Optimizer(store, authored_dataset(), builtin_registry(), FeedbackProposer())
        study = optimizer.create(seed_skill())
        result = await optimizer.run(study)
        assert result.champion
        optimizer.freeze(study)
        await optimizer.final_test(study)
        bundle = export_skill(store, study, optimizer.evaluator, directory / "skill.json")
        write_report(store, study, optimizer.evaluator, directory)
        output = await run_skill(
            bundle, {"identifier": " 0017 ", "display_name": " Ada "}, optimizer.registry, store
        )
        assert output.output == {"id": "0017", "name": "Ada"}
        print(output.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())
