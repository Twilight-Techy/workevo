# Project memory

Last updated: 2026-11-18 (Africa/Lagos).

## User intent and authorization

Build a separate project that generates/loads reusable agent skills, executes and validates them, scores comparable outcomes, mutates workflows and retains the best validated artifact while model weights stay fixed. The user subsequently authorized implementing the full project end to end and explicitly selected open-source MIT licensing.

Project root: `/home/ubuntu/MyProjects/workevo`. It is a sibling of Navconr, not part of that repository. The latest user request explicitly authorizes renaming to workevo, creating/pushing a GitHub repository, and minimal-spend model tests/benchmarks. A fresh API key was supplied for this task and used only in process memory via hidden stdin. Package-registry publishing, hosting and a broader paid study remain separate.

## Implemented state

Local package/CLI version 0.1.0 includes strict versioned records, bounded workflow graphs, a trusted async operator registry, copied/reset task state, exact evaluation, paired promotion, bounded hill climbing, seed/mutation/target model callbacks, durable SQLite attempts/events/usage, single-writer leases and explicit recovery, portable skill export/import/lookup, independent deployment execution, Pareto utilities, pinned context and a self-contained interactive inspector.

The offline demo is a scripted regression fixture: seed correctness 37.5%, alias handling 62.5%, trimming 100%, redundant-step removal at equal correctness, then a rejected alias regression. The retained version is `3f63cb2c239f6a65d8f7908ac166868e574459d0af598b4f222ec4c5065a31f5`. A separate `FeedbackProposer` chooses domain edits from actual development failures; it is not a general model optimizer. Application callbacks have offline fixture coverage and the separately scoped three-call Haiku check described below.

Instructions, workflow, parameters, operator versions, context requirements and parent lineage participate in content identity. Study configuration pins dataset/evaluator, registered operator fingerprints, proposer identity, context identity, implementation source hash and resource limits. Changing any invalidates resumed comparisons. Model identity must include captured host settings not visible in source.

## Decisions and reasons

- ADR 001 chooses a small independent execution/evidence core with replaceable search/proposal interfaces after inspecting pinned SkillOpt, GEPA and AFlow interface/license files. No upstream code copied. Broad novelty is not established.
- Python 3.11–3.13, Pydantic 2, stdlib SQLite/asyncio and Hatchling. Core does not require a vendor SDK, Navconr, a graph database, frontend build or web service.
- Bounded content-addressed JSON lives in SQLite; exports are atomically written local files. A separate large-blob backend is deferred because supported artifacts are bounded. No automatic history deletion/GC.
- Registered operators are trusted application Python. Generated JSON cannot introduce imports, executable source or shell commands. This is not an OS sandbox; callbacks must cooperate with cancellation and SDK timeouts/retry accounting.
- First task family is authored record normalization with 24 cases, eight per split. Exact labels are evaluator-owned. The semantics repeat across disjoint values/template IDs; this is software coverage, not robust domain transfer.
- One champion per study/objective, retained trial history, optional comparable Pareto archive. A population is not automatically an ensemble.
- Seed generation from a task scaffold and subsequent mutations share one budget ledger. Existing learned revisions may start new studies while preserving ancestry. Deployment consumes the exported workflow without loading reference answers.
- Research gates are independent of software integration/release preparation, as explicitly changed in ADR 001. T015–T017 remain unchecked; no scientific requirement is replaced by a fixture.
- MIT selected by user, contributor attribution in LICENSE. Runtime dependencies and UI/fixture assets are inventoried in DEPENDENCIES.md. PyPI name lookup returned 404 on 2026-11-17; this is not namespace reservation.

## Verification and artifacts

- Ordinary checks: Ruff lint/format, mypy and pytest. The original 52-test implementation suite passed on Python 3.11.18, 3.12.3 and 3.13.18; one added process-crash check and updated reopened-cancellation check are included in the subsequent 53-test suite. Final receipts/check notes below distinguish actual runs.
- Offline software comparison: `reports/software-study-protocol.json` written before execution; `reports/software-study.json` contains 25 runs across five policies/controls and 1,416 trials. Development feedback and the manually authored reference attain 100%; random edits average 92.5% (62.5–100%); unchanged seed and instruction-only control attain 37.5%. These are fictional software fixtures. No live model, independently reviewed annotations, upstream optimizer run or capability claim.
- Browser verification: actual stored demo at `.workevo/release-demo/`, self-contained HTML inspector, five candidates and 24 champion case outcomes. Desktop 1440×1080 and phone 390×844 checks cover filtering, search, selection, trace disclosure and no page-wide overflow. Zero page errors. Screenshot/receipt: `reports/inspector.png`, `reports/inspector-mobile.png`, `reports/inspector.json`. Source-free report omits raw inputs/outputs/labels/context; hypotheses and metric/trace metadata remain visible.
- Optional Navconr example ran against real Navconr in a separate temporary environment: 39 exact source bytes returned for the fictional record contract. No Navconr source edits or model calls.
- Release check: `scripts/release.py` builds wheel/source archive, verifies MIT and inspector inclusion, rejects private context/runtime files in artifacts, installs wheel in a fresh Python 3.12 environment without Navconr/OpenAI/Anthropic/pytest/Playwright, runs the demo/import and executes exported skill on a fresh input yielding `{id: "0017", name: "Ada"}`. `reports/release-check.json` records exact hashes. It is excluded from sdist to avoid a self-referential receipt. Rebuild after documentation changes to keep artifacts current.
- CI definitions cover the Python matrix and browser checks. The public repository now runs them on pushes; see the publication log below and GitHub Actions for current status.

## Source history and integrity

`context/conversation.md` preserves the supplied block (including literal formatting) without reconstructed message metadata. Capture is 4,679 bytes; SHA-256 `69728690e684c8f95008c8f369a67f16c1922b5b8d8ea5f795d28898b300016f`. The local integrity receipt detects future changes, not authenticity against an independent export. Context/receipt remain ignored and excluded from distributions. The original conversation's novelty/performance claims are proposals, not results.

Initial setup completed T001–T002 and checked 14 local links. Current document/verification checks are recorded after implementation rather than treating those historical checks as current evidence. Navconr's working tree was clean before setup and remains outside this project's edits.

## Remaining acceptance and handoff

T005–T014 and T018–T020 cover the local software, integration and release preparation. T015–T017 remain open for independently reviewed tasks, a frozen live-model study protocol, compatible budget-matched SkillOpt/GEPA/AFlow comparisons and transfer/uncertainty analysis. Do not claim superiority or reuse the small fixture's 100% as model evidence.

Next research action is T015 once reviewed data/model choices and applicable paid-run authorization are available. The callable interfaces and CLI factories can connect the host's existing clients. Public source publication is now user-authorized and completed. Registry publication, hosting and paper submission remain separate actions. Use TASKS.md for exact acceptance rather than inflating completion from the local build.


Final boundary review: storage now revalidates skill artifacts, trial case/repeat identity and frozen-test membership. Accepted selection is checked again inside the champion transaction against the exact development/validation case-repeat manifest pinned in StudyConfig. Direct unscored promotion is rejected and rolled back. Empty evidence cannot be eligible. Two added storage-boundary tests bring the suite to 55 tests; final matrix/build receipts below apply after these changes.


## Final verification — 2026-11-17

After the persistence-boundary hardening, all 55 tests pass on Python 3.11.18, 3.12.3 and 3.13.18. Ruff lint/format, mypy, lock consistency and generated-schema checks pass. The software comparison was rerun against the exact final implementation hash: 25 runs, 1,416 trials, unchanged conclusions. Browser checks on the current release demo pass at desktop and phone sizes with zero page errors; the local inspector was queued for opening in the Codex panel.

All 36 local Markdown links resolve, context SHA-256 is unchanged, and six representative ignore paths were checked in a disposable repository. Navconr remains clean. The final release check rebuilds distributions after these documentation changes; its external receipt records artifact hashes without making the source archive self-referential. No code changes are made after the verified implementation revision.


## Rename, live check and source publication — 2026-11-17

The user chose **workevo**, explicitly requested a GitHub repository/push and authorized absolute-minimum API spending. The former local working name was Workflow Evolver (`workflow-evolver` / `workflow_evolver`). Folder, distribution, module, CLI, examples and documents are renamed consistently. Old local receipts are preserved under `.workevo/archive/before-rename/`; original context remains unchanged. Previous unshared artifacts are not promised compatible with the renamed module/implementation hash.

One opt-in Haiku live run used exactly three generation calls and three preflight token-count calls, no retries or redirects, low effort, thinking disabled and 256 output tokens per call. Measured 775 input + 92 output tokens; estimated cost $0.0001235 at the verified Haiku 5.5 rates. No cached tokens or unresolved usage. The key was received from the user, transferred through hidden stdin, never written to files, command-line arguments or reports, and the session copy was cleared. Do not automatically rerun the paid command.

`reports/live-haiku-protocol.json` was written before the run; `reports/live-haiku.json` records the actual results. One compact model-selected workflow mutation enabled aliases/trimming and removed the redundant step. Local exact validation/frozen test attain 100% on the small authored fixture (40 local trials total). Separate paired target executions on two additional held-out records scored baseline 1/2 and evolved 2/2. The latter is one batch per condition, not statistical evidence, a broad model benchmark, an upstream comparison or completion of T015–T017.

`scripts/live_benchmark.py` is opt-in (`--live`); ordinary checks import/test fake transports only. Seven additional offline tests exercise full rehearsal, generation/input/spend caps, unresolved failures, truncation accounting and redirect refusal. No paid requests belong in CI.

GitHub target is the authenticated user's account: `Twilight-Techy/workevo`, public under MIT. Source publication is authorized and the initial push is verified; the exclusion scan is clean and hosted CI is monitored before handoff. The name lookup for workevo is separate from the historical workflow-evolver check and does not reserve a registry name.


Renamed-source verification: 62 tests pass on Python 3.11.18, 3.12.3 and 3.13.18; Ruff, mypy and locked dependency checks pass. The 25-run/1,416-trial offline benchmark, generated schemas, desktop/mobile inspector checks and clean-wheel verification were refreshed under workevo. Current live/software protocols match the renamed implementation source hash. A pre-publication pattern scan found no credentials; context/receipt, environments, databases, runtime state, archives and build outputs are excluded. reports/verification.json records the combined evidence.


Publication completed: https://github.com/Twilight-Techy/workevo is public, default branch main. Initial commit 66973191606ec7738af82dc294469b0534e77e31 matched remote main after push. Git identity uses the account's public profile name and GitHub noreply address. Context/integrity receipt, environments, runtime/archive directories, databases and distribution files are absent from the tracked tree; staged credential scans pass. First hosted check: https://github.com/Twilight-Techy/workevo/actions/runs/44096913084. A following documentation commit records this handoff; check Actions for its current result. The three-call Haiku allowance is spent as recorded; do not rerun it automatically.


Hosted CI correction: first public run's browser job passed, but fresh Python jobs rejected runner.py's platform-sensitive `type: ignore` as unused. Replaced it with an explicit typing.cast around the JsonValue type expression; runtime behavior is unchanged and no warning/check is disabled. Fresh mypy and the ordinary suite are rerun, with a follow-up source push. This changes the conservative implementation source hash. The live protocol/receipt remain immutable evidence of the pre-cast revision (initial commit 6697319); do not rewrite their hash or incur more paid calls to refresh it. Offline comparisons and current demo/export are refreshed for the current implementation.


Hosted verification complete: https://github.com/Twilight-Techy/workevo/actions/runs/44147063716 passed for implementation commit 908052592345eef1abcb04962f2574fabe748021. All 62 tests, fresh mypy/Ruff checks and distribution builds pass on Python 3.11/3.12/3.13; hosted desktop/mobile inspector checks pass too. The working tree and remote main matched after the correction push. This final handoff update changes documentation/verification metadata only and skips redundant CI. No extra paid generations occurred; total remains 3 Haiku generations, 775 input/92 output tokens, estimated $0.0001235.


## Friendly/technical README split and benchmark presentation — 2026-11-18

The user requested both README audiences, a visually appealing friendly entry point, and benchmarks. Previously there was one mixed README plus detailed docs. README.md is now the friendly guide with original forest-green SVG branding, centered badges/navigation, concise benefits, offline quick start, real inspector screenshot and visible benchmark results. README.technical.md now owns architecture, library usage, model/custom-task integration, selection/budgets/recovery, CLI workflow and developer/build commands.

Added docs/BENCHMARKS.md with the actual five-policy correctness/search-expense table, methods, shared caps versus actual work, precise trial definition, reproducible commands and limits. Its separate live table preserves the existing three-call Haiku evidence (775 input/92 output, estimated $0.0001235; paired two-record check 1/2 vs 2/2). No new model calls or paid runs occurred. No old benchmark protocol/result was rewritten.

The original hero is code-authored SVG. scripts/render_benchmarks.py uses optional Matplotlib 3.11.2 to render recorded results, recomputes aggregates from the raw runs, rejects mismatches and writes source-SHA/plot-value provenance. Matplotlib is not added to the core runtime or lockfile. The source distribution now includes README.technical.md; release checks assert inclusion of both READMEs and the hero/benchmark SVGs.

Verification: all 85 local links/anchors in the documentation set resolve; both SVGs parse; plotted values and input-report SHA match the existing results. The full technical Python example runs in a separate temporary working directory and returns fixture quality 1.0 and the expected normalized record. Offline CLI demo and exported-skill execution pass. Reviewed GitHub-style local previews at desktop 1280px and phone 390px: all seven images/badges load, details expand, no page-wide overflow and no page errors; technical and benchmark pages also fit phone width. Ruff lint/format and lock checks pass. The clean-wheel/source release check passes, including source-history exclusion and new asset/doc inclusion. Runtime source implementation hash is unchanged; no new runtime tests or model calls were needed for this presentation change.


README publication verified: GitHub renders all seven README images/badges and exposes the technical/benchmark links. Hosted run https://github.com/Twilight-Techy/workevo/actions/runs/44223554622 passed on 0f1e8e2e74cb55e52c319e2635ac4fdcffef709d: Python 3.11–3.13 checks/builds and the browser inspector job all succeed. Original benchmark receipts remain unchanged. This final verification note is documentation-only and skips redundant CI.
