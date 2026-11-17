# Evaluation protocol: initial design

Status: the authored software protocol is frozen and executed in reports/software-study-protocol.json and reports/software-study.json. This document remains the design for the independent empirical study; T015 must freeze its reviewed data and model configuration before research optimization.

## Questions

1. Does execution-guided mutation improve correctness on unseen tasks compared with the seed and one-shot generation under a fixed total optimization budget?
2. Does structured workflow mutation add value beyond instruction-only mutation?
3. What optimization expense buys a deployment-time quality/cost tradeoff, and how many future uses are needed to amortize it?
4. When does retaining several alternatives help a deterministic context/budget selector, relative to one champion?

These are hypotheses. The offline fixture can validate the software loop but cannot answer model capability questions.

## Data and isolation

Use versioned input/label manifests with `development`, `validation`, and `test` partitions. Split by task template/source family, then assert disjoint membership and inspect near duplicates. Freeze memberships and hashes before search. The optimizer receives development errors and artifacts; it receives only bounded aggregate promotion feedback from validation. It never receives test inputs or labels during search.

Repeated validation selection can overfit. Bound the number of validation looks and record them. Final testing runs once per frozen study configuration; a new search after viewing test results requires a new study and new untouched test data. No selector may route using a case's reference answer or test outcome.

Initial engineering coverage should include Unicode identifiers, leading zeros, optional/missing fields, malformed input, conflicting field aliases, and distractor fields. Keep expected outputs evaluator-owned. The software fixture has 24 cases, eight per partition, as fixed in T004; research sample sizes/repeats are chosen in T015 from pilot variance and compute limits, before opening test results.

## Gates and raw metrics

An evaluation records output-schema validity, exact/field correctness, execution-policy compliance, and completeness. Invalid schema, unauthorized actions, evaluator access, or exceeded hard resource limits makes a candidate ineligible. Ordinary task errors lower measured quality; promotion must satisfy a predeclared correctness floor and paired regression policy. Candidate-level eligibility and per-case success are different concepts.

Keep raw quality rate, failure/timeout rate, tool/model calls, retries, measured tokens, estimated monetary spend with price snapshot, and wall-clock latency. Record missing usage explicitly. Measure proposal/search/validation/final-test cost separately from deployment cost, including rejected and crashed attempts.

The deterministic vertical slice uses correctness rate first, then declared operator-call cost. Require strictly improved quality or equal quality with reduced deterministic cost, with no prohibited per-case regression on the validation fixture. Exact ties retain the incumbent. This gate proves selection semantics; it is not a statistical research threshold.

For stochastic model runs, predeclare minimum practical gain, repeat schedule, paired uncertainty calculation, validation-look limit, and regression tolerance in T015. Use paired cases across methods and seeds where supported; state hosted-provider reproducibility limits. If evidence is insufficient, return `inconclusive` and retain the incumbent.

For optional scalar scores, freeze weights summing to one and fixed normalization ranges before search. For a higher-is-better metric use a clipped declared range; invert for lower-is-better metrics. Report clipping and raw values so improvements beyond the range are visible. Required missing metrics invalidate the score; never rescale remaining weights silently. Hard gates apply independently of the scalar score.

## Comparisons

| Baseline/ablation | Purpose |
| --- | --- |
| Unchanged seed | Measures whether search adds value |
| One-shot generated skill | Separates optimization from merely supplying instructions |
| Bounded random mutation | Tests whether feedback-guided proposals outperform the same search budget |
| Greedy instruction-only mutation | Tests structural edits beyond prompt changes |
| SkillOpt and GEPA | Closest skill/prompt optimizer candidates where task and harness contracts can be matched |
| AFlow | Workflow-search comparison where an equivalent operator space and execution budget can be provided |
| No retained mutation memory | Tests whether accumulated lessons improve future proposals |
| Single champion versus bounded frontier | Tests reuse/selection tradeoffs and added search expense |

A citation is not a baseline implementation. T015 must document upstream versions, adaptation, supported tasks, licensing, and any unmatched capabilities before claiming direct comparison. Keep target models, tools, tasks, evaluators, output caps, and total optimization expense comparable. If budgets cannot be matched, report separate settings and avoid superiority claims.

## Report and promotion evidence

Publish raw per-case results, aggregate metrics and uncertainty, failure taxonomy, candidate/selection counts, all budget consumption, environment/model identities, dataset/evaluator/skill hashes, mutation lineage, and final frozen-artifact hash. Separate synthetic fixture results, live-smoke results, and research evidence.

Mutation explanations are hypotheses. Test an edit in isolation or remove it in an ablation before asserting causality. Transfer requires evaluation on a new task family/environment, not replaying known cases. Retest or mark stale when models, tools, data distribution, or context revisions change.

Where per-use monetary saving is positive, report break-even uses as `total optimization expense / per-use saving`, with assumptions and uncertainty. If quality differs or saving is nonpositive, do not present that quotient as a like-for-like saving.


## Recorded local software check

The actual offline run uses unchanged seed, manually authored reference, random flag/structure edits, development-feedback edits and an instruction-only negative control. Five seed settings give 25 runs and 1,416 trials. The authored reference is not a generated one-shot baseline. The instruction-only control cannot affect deterministic operators. Template identifiers and input values are disjoint, but underlying normalization semantics repeat, so these splits do not establish robust domain transfer. See reports/README.md for exact findings and limits.

Real-model one-shot generation, upstream optimizer comparisons, independently reviewed tasks, noisy-selection uncertainty analysis and transfer experiments remain unrun. The existing software report is not a substitute for those gates.
