# ADR 001: independent execution/evidence core, replaceable search policy

Accepted 2026-11-17 for local implementation, after reading the pinned upstream license and interface files below. This is a narrow interface review, not a security audit or reproduction.

| Upstream | Commit | Reviewed files | License observed |
| --- | --- | --- | --- |
| [SkillOpt](https://github.com/microsoft/SkillOpt/tree/22c1ed85d20bf09476373c4a1b10965284873e3d) | `22c1ed85d20bf09476373c4a1b10965284873e3d` | `LICENSE`, `docs/guide/new-backend.md` | MIT |
| [GEPA](https://github.com/gepa-ai/gepa/tree/ce5b0d6e3d6af6c6dbec6de2c54536bbb961d309) | `ce5b0d6e3d6af6c6dbec6de2c54536bbb961d309` | `LICENSE`, `src/gepa/core/adapter.py` | MIT-style permission text |
| [AFlow](https://github.com/FoundationAgents/AFlow/tree/3f457218fc716093fe53f6df8a5d5e6379d66346) | `3f457218fc716093fe53f6df8a5d5e6379d66346` | `LICENSE`, `scripts/optimizer.py` | MIT |

GEPA exposes evaluation and reflective-dataset interfaces and is a plausible optional search-policy adapter. SkillOpt's documented backend registration fits its skill-training harness. AFlow's optimizer searches generated graph/code artifacts. None is adopted as the core dependency: the immediate requirement is an independent persisted evidence boundary, registered bounded operators, and replayable promotion decisions without vendor dependencies or generated-code execution.

Implement the small deterministic search policy locally. Keep proposer and operator interfaces application-owned so future upstream-policy adapters can reuse the same evaluation boundary. No upstream implementation is copied or vendored. These observations do not establish missing upstream features or a novel algorithm. Direct upstream comparisons remain separate research work.

Python 3.11+ is the support floor; test 3.11–3.13. Use Pydantic 2 for strict records, stdlib SQLite and asyncio, Hatchling for packaging, pytest/Ruff/mypy for checks. Keep UI as a read-only local report consuming exported records; no hosted service is required.

Research gates must not block independent software integration checks: T018/T019 may proceed after T012/T014 and a software evaluation report. T015–T017 still require separately reviewed empirical evidence before research completion. This changes scheduling, not scientific acceptance.
