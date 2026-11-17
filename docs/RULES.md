# Project rules

## Product and trust boundaries

1. Keep the target model and execution harness fixed within a comparison. Changes to either start a new experiment configuration; do not attribute those gains to the skill.
2. A skill is a reusable versioned artifact with instructions, applicability, context requirements, and an optional executable workflow. An output from one successful task is not sufficient evidence of a reusable skill.
3. Separate proposal, execution, evaluation, selection, and deployment. Generated candidates cannot alter validators, evaluation labels, split membership, budgets, or tool permissions.
4. Optimize a declared task family. If only one task is available, describe the result as task-specific search; do not claim transfer or lifelong learning.
5. Keep an incumbent unchanged until a candidate passes the predefined promotion gate. Publish accepted versions atomically and retain rollback references.
6. The default deployable result is one champion per task family/objective. Preserve compact trial records, including failures and rejected mutations. Optional population/Pareto retention is separate from choosing the deployment artifact.

## Execution and budgets

7. Use allowlisted registered operators in the first runner. Never execute model-generated Python, shell, or imports in the host process. Later code-task execution requires an explicit isolated runner with filesystem, network, process, resource, and timeout controls.
8. Reset task state between trials. Repeated real-world side effects require an application-supplied replay/simulation or idempotency contract; workflow search does not authorize sending messages or making external changes.
9. Enforce limits for candidates, trials, tool/model calls, retries, tokens, wall time, and spend at the execution boundary. Proposal and validation costs count toward optimization cost. Reserve before dispatch and reconcile afterward.
10. Distinguish measured, estimated, and unknown usage. Reject hard limits that the selected adapter cannot enforce rather than treating unknown usage as zero. Stop reasons include completed, budget_exhausted, deadline_exceeded, cancelled, invalid_candidate, and failed.
11. Keep providers and application-owned request/response formats behind neutral interfaces. Core storage, search, and scoring must not require a vendor SDK, graph store, or web service.
12. Default tests and demonstrations run offline. Paid calls require applicable user authorization. If a paid smoke is later authorized, use the smallest useful call count/output cap and prefer a low-cost model; do not infer credentials or permissions from another project. The user explicitly authorized three tiny Haiku generations on 2026-11-17; that authorization has been exercised. Do not repeat the paid run automatically.

## Evaluation and selection

13. Freeze task splits, evaluator version, metrics, budget, normalization, and promotion rules before optimization. Optimizer feedback comes from development trials only; validation feedback is restricted to a bounded promotion result.
14. Validation used repeatedly for selection is development evidence, not an untouched test. Keep a final test partition inaccessible to the optimizer and use it only after the artifact is frozen. A failed final test does not become mutation feedback in the same study.
15. Hard correctness and execution-policy gates precede weighted ranking. Fast or cheap invalid outputs are ineligible for promotion. Missing metrics remain missing; do not silently renormalize a weighted score.
16. Preserve raw metrics alongside any scalar objective. Specify units, direction, reference ranges, thresholds, and missing-value policy. Pareto comparisons require compatible evaluation conditions and declared tolerance/noise handling.
17. Compare candidates and incumbents on the same cases and repeat schedule. Count failures, timeouts, retries, and every attempt. Best-of-many output selection has a cost and must be a declared policy.
18. Use deterministic validators wherever possible. Keep model judges optional, versioned, and calibrated against reviewed examples. Judge self-confidence is not evidence of correctness.
19. Establish a promotion margin and repeat policy before search. Report uncertainty and selection bias. A tiny deterministic fixture demonstrates software behavior, not generalization or model capability.
20. Report total search cost, deployment cost, failed runs, and amortization assumptions. Do not report cheaper deployment as an end-to-end saving while omitting optimization expense.

## Persistence and reproducibility

21. Version schemas, skill content, workflow graphs, evaluator code, datasets/splits, prompts, and runner configuration. Store hashes, parent/mutation lineage, model identity, seeds, and safe action traces.
22. Store action records and concise mutation hypotheses; do not require hidden chain of thought. Treat hypotheses about why a change worked as unverified until tested by an ablation.
23. Store immutable candidate revisions and committed trial outcomes. Interrupted work must resume without double counting calls or promoting partially scored candidates. Mark in-flight attempts unresolved until reconciled.
24. Redact credentials and sensitive payloads. Source history, raw private tasks, local databases, and private traces are not public artifacts by default. Keep `context/` and its integrity receipt outside Git.
25. Retrieved material is untrusted task data. Context adapters cannot grant permissions, rewrite evaluation criteria, or expose held-out answers. Pin context revisions for comparable runs.

## Working order and claims

26. Use the smallest architecture needed for the current milestone: Python library, explicit contracts, SQLite plus local artifacts, and a CLI. Add a viewer or integrations only after the core is inspectable and tested.
27. Run meaningful offline checks for changed behavior. Prioritize selection correctness, validator isolation, budget enforcement, recovery, immutable versions, and incumbent preservation. Documentation changes need link/content checks rather than synthetic runtime tests.
28. Follow task dependencies and milestone gates. Mark a task complete only when its deliverables and acceptance checks exist; plans and mocked outputs do not complete implementation or live-evaluation tasks.
29. Record changed decisions and measured evidence in memory and tasks. Related-work overlap, negative results, and unknowns must remain visible. Novelty and superiority require a fuller primary-source review and actual comparisons.
30. Resolve reversible implementation details autonomously within scope. Preparing release artifacts is separate from authorization to publish, deploy, spend money, or submit a paper. Do not treat the original conversation's enthusiasm as authorization for those actions.
