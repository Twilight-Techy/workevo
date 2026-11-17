"""Build and verify local distributions. Never publishes anything."""

from __future__ import annotations

import email
import hashlib
import json
import platform
import subprocess
import tarfile
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def command(args, *, cwd=ROOT):
    result = subprocess.run(args, cwd=cwd, text=True, capture_output=True, timeout=180)
    if result.returncode:
        raise RuntimeError(f"Command failed: {args[0]}: {result.stderr[-2000:]}")
    return result.stdout


def main():
    command(["uv", "build"])
    wheel = ROOT / "dist/workevo-0.1.0-py3-none-any.whl"
    sdist = ROOT / "dist/workevo-0.1.0.tar.gz"
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        assert "workevo/inspector.html" in names
        assert "workevo/py.typed" in names
        metadata = email.message_from_bytes(
            archive.read(next(n for n in names if n.endswith("/METADATA")))
        )
        assert metadata["License-Expression"] == "MIT"
        license_text = archive.read(next(n for n in names if n.endswith("/LICENSE")))
        assert license_text == (ROOT / "LICENSE").read_bytes()
    with tarfile.open(sdist) as archive:
        names = archive.getnames()
        assert any(n.endswith("/README.md") for n in names)
        assert any(n.endswith("/LICENSE") for n in names)
        assert not any(
            "/context/" in n or "/.venv/" in n or "/.workevo/" in n or n.endswith(".sqlite")
            for n in names
        )
    with tempfile.TemporaryDirectory(prefix="workflow-wheel-smoke-") as directory:
        temp = Path(directory)
        command(["uv", "venv", "--python", "3.12", str(temp / "env")], cwd=temp)
        python = str(temp / "env/bin/python")
        command(["uv", "pip", "install", "--python", python, str(wheel)], cwd=temp)
        probe = command(
            [
                python,
                "-c",
                "import importlib.util,json;from workevo import __version__;print(json.dumps({'version':__version__,'optional_absent':all(importlib.util.find_spec(n) is None for n in ['navconr','openai','anthropic','pytest','playwright'])}))",
            ],
            cwd=temp,
        )
        assert json.loads(probe)["optional_absent"]
        cli = str(temp / "env/bin/workevo")
        result = json.loads(command([cli, "demo", "--directory", str(temp / "demo")], cwd=temp))
        bundle = json.loads((temp / "demo/skill.json").read_text())
        assert bundle["final_test"]["split"] == "test"
        command(
            [
                cli,
                "import",
                str(temp / "demo/skill.json"),
                "--database",
                str(temp / "registry.sqlite"),
            ],
            cwd=temp,
        )
        (temp / "input.json").write_text(
            json.dumps({"identifier": " 0017 ", "display_name": " Ada "})
        )
        deployed = json.loads(
            command(
                [
                    cli,
                    "execute",
                    str(temp / "demo/skill.json"),
                    "--input",
                    str(temp / "input.json"),
                    "--database",
                    str(temp / "deployment.sqlite"),
                ],
                cwd=temp,
            )
        )
        assert deployed["output"] == {"id": "0017", "name": "Ada"} and deployed["complete"]
        assert (temp / "demo/inspector.html").exists()
        receipt = {
            "schema_version": 1,
            "python_build_host": platform.python_version(),
            "wheel_core_python": "3.12",
            "version": json.loads(probe)["version"],
            "core_optional_dependencies_absent": True,
            "demo_champion": result["champion"],
            "deployment_output": deployed["output"],
            "wheel_includes_inspector_and_mit": True,
            "sdist_excludes_private_context": True,
            "artifacts": [
                {
                    "file": str(p.relative_to(ROOT)),
                    "bytes": p.stat().st_size,
                    "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                }
                for p in (wheel, sdist)
            ],
        }
    (ROOT / "reports/release-check.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
