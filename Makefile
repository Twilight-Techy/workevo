.PHONY: setup check demo study build
setup:
	uv sync --locked
check:
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy src
	uv run pytest
demo:
	uv run workevo demo --directory .workevo/demo
study:
	uv run python scripts/software_study.py --output reports/software-study.json
build:
	uv build
