# Ordered tasks

Established 2026-11-17. `[x]` means the listed deliverables exist and their acceptance checks passed. Local software, integration and release-preparation deliverables are verified. Independent empirical milestones T015–T017 remain open. Dependencies and milestone gates both apply.

## M0 — Foundation and contracts

- [x] **T001 — Create the independent project foundation.** Dependencies: none. Create a sibling folder, introductory README, local working instructions, rules, plan, task ledger, and memory; preserve the supplied conversation separately from interpretation. Acceptance: documents exist, local links resolve, context is ignored, and Navconr is unchanged. Evidence: foundation verification recorded in memory.
- [x] **T002 — Establish the initial research position.** Dependencies: T001. Check primary sources for closest overlap and record hypotheses without novelty claims. Acceptance: related-work notes distinguish verified mechanisms from untested results and identify the closest skill/workflow optimizers. Evidence: SkillOpt, GEPA, AFlow, and Voyager primary pages checked on 2026-11-17.
- [x] **T003 — Decide reuse versus a new core.** Dependencies: T002. Inspect the relevant upstream contracts/licenses and compare adapters to a standalone engine. Acceptance: a short architecture decision explains build/reuse boundaries and whether the provisional module plan should change. Do not treat the initial web check as a code audit.
- [x] **T004 — Freeze prototype contracts and fixture protocol.** Dependencies: T003. Define exact versioned schemas, graph execution/data references, hash rules, split memberships, validators, limits, score normalization, repeat/promotion policy, retention, and async/cancellation behavior. Acceptance: valid/invalid record examples and a finite resettable task fixture specify all observable outcomes without runtime code; no labels enter runner inputs.

## M1 — Execution and evidence

- [x] **T005 — Scaffold an installable library and CLI.** Dependencies: T004. Select supported Python/dependency versions, package metadata, offline checks, and fixture layout. Acceptance: clean install, import, CLI help, and checks pass without model credentials or services.
- [x] **T006 — Implement immutable records and transactional storage.** Dependencies: T005. Persist revisions, lineage, trials, evaluation and selection records with schema checks/migrations. Acceptance: round trips, incompatible versions, interrupted writes, and conflicting champion updates have defined tested outcomes.
- [x] **T007 — Implement the resettable bounded operator runner.** Dependencies: T006. Execute validated sequence/branch graphs using a registry, step caps, shared usage accounting, deadlines, cancellation, and artifact capture. Acceptance: unknown operators, dangling references, cycles, policy escapes, cap overruns, and evaluator access cannot bypass enforcement; task state resets between trials.
- [x] **T008 — Implement the exact evaluator and offline fixture.** Dependencies: T007. Add evaluator-owned labels, input/output cases, split checks, raw metrics and hard gates. Acceptance: malformed/incorrect/partial outputs score as specified; invalid attempts cannot outrank valid candidates because of lower cost.

## M2 — Optimization vertical slice

- [x] **T009 — Implement champion selection and promotion.** Dependencies: T008. Pair candidate/incumbent evidence and apply the frozen gate atomically. Acceptance: regression, ties, missing data, incompatible configs and incomplete trials preserve the incumbent; known better fixtures promote.
- [x] **T010 — Implement bounded search and mutations.** Dependencies: T009. Add seed handling, deterministic bounded edits, development feedback, limited validation looks, patience and explicit stop outcomes. Acceptance: an offline run improves the intended fixture and retains an earlier champion when a later mutation performs worse; no-valid-skill and budget-exhaustion paths are explicit.
- [x] **T011 — Add CLI reporting and interruption/resume.** Dependencies: T010. Export lineage, raw metrics, all trial cost and a frozen champion. Acceptance: a clean local example runs without a model, interruption cannot double-count/promote incomplete work, and its report reproduces recorded selection decisions.

## M3 — Reusable skills and model proposals

- [x] **T012 — Implement portable skill export/import and lookup.** Dependencies: T011. Include instructions, workflow, operator dependencies, applicability, context requirements, evaluator/config references and failure cases. Acceptance: reimported artifacts reproduce fixture behavior; stale/incompatible skills fail clearly; unknown tasks can abstain.
- [x] **T013 — Add application-owned seed/mutation proposers.** Dependencies: T012. Use a neutral callback/protocol with versioned requests, bounded output, cancellation and usage capability declarations. Acceptance: fake integrations cover different host response shapes, rejected edits, missing usage and caps without a vendor SDK. Live checks remain a separate authorized step.
- [x] **T014 — Add optional bounded Pareto retention and routing.** Dependencies: T013. Preserve comparable nondominated candidates with tolerance/cap and deterministic selection policy. Acceptance: dominated/ineligible candidates are excluded; ties/noise and missing metrics are defined; selected deployment artifacts remain explicit.

## M4 — Empirical evaluation

- [ ] **T015 — Finalize the empirical study before optimization.** Dependencies: T014. Choose reviewed tasks, sample sizes/repeats, model configurations, untouched test splits, budgets, practical gain threshold, uncertainty method, baseline versions and license constraints. Acceptance: a frozen protocol and split hashes exist; research annotations and software fixtures are distinguished.
- [ ] **T016 — Run controlled comparisons and ablations.** Dependencies: T015 and applicable authorization for paid/live runs. Execute competent compatible baselines and raw per-case reporting. Acceptance: all attempted runs, errors, mutation/validation cost and deployment metrics are included; no test feedback reaches search.
- [ ] **T017 — Report supported findings and limitations.** Dependencies: T016. Analyze correctness, transfer, cost amortization, uncertainty and failures. Acceptance: claims match measured evidence, negative/inconclusive results remain visible, and frozen exports identify exact study configuration.

## M5 — Integrations and inspection

- [x] **T018 — Add an optional context adapter and Navconr example.** Dependencies: T012 and the offline software evaluation report; research findings depend on T017. Retrieve pinned evidence/context for workflow execution and skill lookup through public contracts. Acceptance: independent core still installs/runs without Navconr; context changes invalidate comparisons and cannot expose labels or grant permissions.
- [x] **T019 — Build a small lineage and tradeoff inspector.** Dependencies: T014 and the offline software evaluation report; research findings depend on T017. Display mutations, per-case outcomes, champion decisions, cumulative search cost and optional frontier. Acceptance: a developer can explain a promotion/rejection from recorded evidence without model calls or invented explanations.

## M6 — Release preparation

- [x] **T020 — Prepare a reproducible release and handoff.** Dependencies: T018, T019. Resolve name/license, review dependency/data terms, build installable artifacts and examples, validate docs and migrations, and record remaining limits. Acceptance: a clean environment reproduces the offline example and artifact contents exclude local history, credentials and private traces. Public publication/deployment/submission follows separate authorization.

## Execution notes

2026-11-17: T001–T002 completed as project setup. No runtime tasks were attempted. Next ready task: T003. The supplied conversation supports the concept; structured-data fixture, Python/SQLite, single champion default and optional frontier are provisional design choices made during setup.

2026-11-17 implementation: user authorized the full implementation and selected MIT. T003 is evidenced by ADR 001; T004 by CONTRACTS.md and the frozen authored fixture specification. Independent integration/inspector scheduling changed as recorded in ADR 001; empirical acceptance is unchanged.


2026-11-17 software completion evidence:

- T005–T008: installable package, typed/versioned records, immutable store, bounded runner and exact evaluator. Tests cover graph/split validation, schema compatibility, transactions, reset state, missing/unknown operators, branches, retry/step/resource caps and safe errors.
- T009–T011: real end-to-end search accepts three improvements and rejects the later regression. Tests cover ties, partial/missing/incompatible evidence, incumbent compare-and-swap, idempotent repeated operations, cancellation, reopened state and an actual child-process crash. CLI factory paths are exercised.
- T012–T014: skill JSON/SKILL.md export, verified import and applicability lookup; fresh-input execution without labels; application-owned model seed/mutation/target callbacks; usage reservation/failure/unknown/overrun tests; Pareto comparability, caps, missing metrics and deterministic routing.
- T015–T017: an authored software protocol/report exists (25 runs, 1,416 trials), but these boxes remain open. Reviewed empirical annotations, live models, compatible upstream runs and transfer/uncertainty findings are absent.
- T018: `examples/navconr_context.py` ran against real Navconr in a separate temporary dependency environment and returned 39 exact source bytes. Core wheel runs without Navconr or model SDKs.
- T019: desktop/phone browser tests exercise actual recorded data, filtering, search, selection, case outcomes, trace disclosure and overflow; zero page errors. `reports/inspector.json` and screenshots record the check.
- T020: MIT selected, runtime dependency/asset inventory reviewed, local name workevo selected, wheel/source artifacts built and checked in a fresh Python 3.12 core-only environment. PyPI JSON name lookup returned 404 on 2026-11-17; this does not reserve the name. Publication is not performed. `reports/release-check.json` records artifact hashes and label-free deployed output.

Final verification: 55 tests pass on Python 3.11/3.12/3.13; Ruff, mypy, lock and documentation checks pass. The storage boundary independently rejects unscored or mismatched evidence. reports/verification.json records the final local check summary.


## Naming, publication and minimum-cost live validation

- [x] **T021 — Rename to workevo and publish GitHub source.** User-authorized on 2026-11-17. Rename folder/distribution/module/CLI and docs, run offline checks/benchmarks/build verification, scan the staged source for credentials/private artifacts, create the public account repository, push main and verify matching remote commit.
- [x] **T022 — Run an absolute-minimum live model benchmark.** User-authorized on 2026-11-17. Evidence: reports/live-haiku-protocol.json and reports/live-haiku.json; three Haiku generations, no retries, 775 input/92 output tokens, estimated $0.0001235. One model-selected mutation plus separate baseline/evolved target checks. This does not close the broader research study gates.


GitHub publication verified: public MIT repository https://github.com/Twilight-Techy/workevo, main tracking origin/main, initial remote/local commit 66973191606ec7738af82dc294469b0534e77e31. Full 62-test suite and mypy pass locally on Python 3.11/3.12/3.13; 25-run/1,416-trial software benchmark refreshed. Hosted CI started at https://github.com/Twilight-Techy/workevo/actions/runs/44096913084. No further API generations after the three-call live receipt.
