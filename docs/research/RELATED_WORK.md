# Initial related-work check

Checked 2026-11-17 using primary paper pages and the SkillOpt repository. This is an initial overlap assessment, not an exhaustive literature review, code audit, or independent reproduction. No upstream package was installed or benchmarked.

| Work | Verified mechanism and overlap | What remains to assess |
| --- | --- | --- |
| [SkillOpt](https://arxiv.org/abs/2605.23904), May 2026; [official code](https://github.com/microsoft/SkillOpt) | Treats a natural-language skill as trainable external state for a frozen agent. A separate optimizer proposes bounded edits; validation gates determine acceptance. Direct overlap with the user's central loop and best-skill export. | Exact edit space, multi-objective/replay features, evaluation fairness, and whether extending it is preferable to a separate engine. |
| [GEPA](https://arxiv.org/abs/2507.19457), July 2025, revised February 2026 | Uses execution trajectories and natural-language reflection to propose/test prompt updates and combine complementary candidates from a Pareto frontier. Overlaps reflective mutations, retained alternatives, and feedback-guided search. | Distinguish its per-task frontier semantics from this project's proposed quality/cost/latency frontier; evaluate structured workflow adapters. |
| [AFlow](https://arxiv.org/abs/2410.10762), October 2024, revised April 2025 | Searches code-represented agentic workflows using Monte Carlo tree search, code modifications, execution feedback, and accumulated search experience. Direct overlap with optimizing workflow structure. | Equivalent operator space, execution isolation, total search budgets, and suitability as a reference search policy. |
| [Voyager](https://arxiv.org/abs/2305.16291), May 2023, revised October 2023 | Uses an automatic curriculum, a growing executable skill library, and iterative feedback-driven code improvement in Minecraft. Overlaps skill accumulation and retrieval for later tasks. | Whether its embodied setting offers a useful transfer/reuse experiment for this project's intended developer tasks. |

The papers' performance claims are author-reported and are not reproduced here. This project has no measurements yet. Avoid describing the broad proposal as unexplored or the first of its kind.

## Interpretation for this project

The central idea is coherent as discrete optimization over external agent state with fixed model weights. Calling a workflow the model's weights is an analogy. It does not establish equivalence to gradient descent, reinforcement learning, or biological evolution. A mutation/selection loop may be implemented as hill climbing, evolutionary search, or other black-box search; the initial policy is deliberately simple.

A retained population is not automatically an ensemble: routing chooses an alternative, whereas an ensemble executes/combines several outputs. A Pareto archive also differs from storing candidates that happen to solve different cases.

Potential investigation areas are structured workflow mutation with portable exports, evidence-backed applicability limits, and context-aware retrieval through an optional Navconr adapter. These are project directions, not established novel contributions. Existing systems may already cover them; complete a deeper feature/code review before making a claim or committing to a new optimizer implementation.

## Next research action

In T003, compare building adapters around existing optimizers with writing the proposed small core. Record a reasoned decision covering artifact semantics, graph edits, execution controls, provider independence, license compatibility, and reproduction effort. In T015, pin exact upstream versions and comparable evaluation settings before running baselines.
