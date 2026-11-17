import json
import os
import subprocess
import sys

from workevo import Limits


def call(*args, cwd, env=None):
    result = subprocess.run(
        [sys.executable, "-m", "workevo", *map(str, args)],
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)


def test_cli_fixture_schemas_and_application_factory(tmp_path):
    call("fixture", tmp_path / "fixtures", cwd=tmp_path)
    schema = call("schemas", cwd=tmp_path)
    assert schema["Skill"]["properties"]["schema_version"]["const"] == 1
    assert json.loads((tmp_path / "fixtures/dataset.json").read_text())["test"]
    factory = tmp_path / "application.py"
    factory.write_text(
        "from workevo import Optimizer, authored_dataset, builtin_registry, SequenceProposer\ndef create(store):\n    return Optimizer(store,authored_dataset(),builtin_registry(),SequenceProposer(()))\n"
    )
    environment = dict(os.environ, PYTHONPATH=str(tmp_path))
    limits = tmp_path / "limits.json"
    limits.write_text(Limits(candidates=1).model_dump_json())
    database = tmp_path / "study.sqlite"
    result = call(
        "run",
        "--database",
        database,
        "--factory",
        "application:create",
        "--seed",
        tmp_path / "fixtures/seed.json",
        "--limits",
        limits,
        cwd=tmp_path,
        env=environment,
    )
    assert result["candidates"] == 1 and result["champion"]
    common = [
        "--database",
        database,
        "--factory",
        "application:create",
        "--study",
        result["study_id"],
    ]
    call("freeze", *common, cwd=tmp_path, env=environment)
    final = call("test", *common, cwd=tmp_path, env=environment)
    assert final["quality"] == 0.375
    call("export", *common, "--output", tmp_path / "bundle.json", cwd=tmp_path, env=environment)
    assert (tmp_path / "SKILL.md").exists()


def test_cli_validation_errors_do_not_echo_private_inputs(tmp_path):
    seed = tmp_path / "bad.json"
    seed.write_text('{"secret":"SHOULD_NOT_APPEAR"}')
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "workevo",
            "run",
            "--database",
            str(tmp_path / "db.sqlite"),
            "--seed",
            str(seed),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "SHOULD_NOT_APPEAR" not in result.stdout + result.stderr
