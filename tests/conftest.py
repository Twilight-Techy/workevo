import pytest

from workevo import (
    Optimizer,
    Store,
    authored_dataset,
    builtin_registry,
    demo_proposer,
    seed_skill,
)


@pytest.fixture
def system(tmp_path):
    with Store(tmp_path / "test.sqlite") as store:
        seed = seed_skill()
        optimizer = Optimizer(store, authored_dataset(), builtin_registry(), demo_proposer(seed))
        yield store, optimizer, seed
