# Implementation plan

Established 2026-11-17. The version 0.1.0 local software is implemented and checked; [TASKS.md](TASKS.md) owns completion, and [STATUS.md](STATUS.md) distinguishes software evidence from open research gates.

## Outcome and first use case

Build a provider-neutral library that proposes a skill/workflow, executes it under explicit limits, validates outputs, scores comparable trials, proposes bounded mutations, and retains a validated champion. Later it can retain multiple nondominated alternatives and retrieve a suitable skill for a new task.

The first vertical slice uses fictional structured-data normalization tasks: convert a small record into a required schema while preserving identifiers and handling missing values. Registered operators perform parsing, normalization, validation, and a bounded fallback. Task inputs and expected outputs are separate; only the evaluator sees expected outputs. Exact validators expose execution and selection bugs without dependence on a model judge. This is a provisional engineering fixture, not the final research domain.

The prototype will accept a seed workflow and a deterministic proposer. The next stage adds an application-owned model callback that can propose a seed and mutations from development outcomes. Fixed model weights apply to the executor and proposer; their identities and configurations are recorded separately.

Coding tasks, unrestricted program synthesis, distributed search, learned routing, autonomous external actions, hosted multi-tenancy, and a graph database are outside the first prototype. Navconr is optional and comes after the independent loop works.

## Architecture

```text
Task family + immutable dataset/split manifest + evaluator + limits
  → seed generator / retrieved skill / supplied seed
  → candidate validator
  → bounded runner with registered operators and resettable state
  → output artifacts + safe action trace + usage + stop reason
  → evaluator (correctness gates + raw metrics)
  → selector (paired validation gate against incumbent)
  → immutable skill registry + atomic champion pointer

Development results → bounded mutation proposer → new candidate revision
All attempts → append-only trial history and reproducible report
Frozen champion → final test → export with evidence and limitations
```

| Boundary | Contract |
| --- | --- |
| Proposer | Receives development feedback and permitted edit scope; returns a candidate and short hypothesis |
| Candidate validator | Checks schema, graph connectivity, operator registry, limits, and permissions before execution |
| Runner | Receives task inputs and candidate; returns actual artifacts/events without access to labels |
| Evaluator | Owns labels and rubric; produces gates, raw metrics, and structured failure reasons |
| Selector | Applies frozen comparison/promotion rules; never edits evidence or evaluator configuration |
| Registry | Stores immutable revisions, lineage, applicability, evidence, and atomic selection pointers |
| Context adapter | Supplies pinned source references and bounded context; no required Navconr dependency |
| Model adapter | Application-owned callable/protocol; preserves cancellation and usage capabilities |

Python is the working language. Use SQLite for metadata, transactions, and lineage; bounded content-addressed JSON artifacts in SQLite, with explicit local export files. Validate typed records at boundaries. Dependency versions, Python support, schema encoding, and sync/async convenience APIs are resolved in T004/T005 before runtime work. Do not copy Navconr's implementation or install its dependencies merely to scaffold this project.

Implemented package modules: `contracts`, `store`, `runner`, `evaluation`, `selection`, `optimization`, `registry`, `adapters`, and `cli`. The inspector consumes exported records; core logic does not depend on UI state. Deployment and reporting are separate modules.

## Records and execution semantics

| Record | Required fields/concepts |
| --- | --- |
| TaskSpec | ID/family, input schema, output schema, permitted operators, environment/reset contract |
| DatasetManifest | Content hashes, disjoint split IDs, family grouping, version, provenance |
| SkillRevision | Content hash, parent IDs, instructions, applicability, context requirements, workflow, operator versions |
| Workflow | Versioned bounded graph, entry point, typed data references, explicit terminal states |
| Mutation | Parent hash, changed paths, edit budget, proposer identity, hypothesis, development evidence IDs |
| Trial | Candidate/task/config hashes, repeat/seed, attempt ID, start/end, outcome, artifacts, usage, failure |
| Evaluation | Trial ID, evaluator hash, hard gates, raw metrics/units, completeness, normalized score if defined |
| SelectionDecision | Candidate/incumbent, paired evidence, policy hash, accept/reject/inconclusive, rationale |
| Budget | Trial/candidate/call/token/retry caps, deadline, monetary cap and accounting capabilities |
| SkillExport | Frozen revision, dependencies, applicability, validation evidence, final-test report, limitations |

The following historical sketch explains the original concept. The implemented field names and valid records are defined by [CONTRACTS.md](CONTRACTS.md) and [schemas.json](schemas.json); this sketch is not an importable skill:

```json
{
  "schema_version": 1,
  "skill_id": "normalize-record",
  "revision": "<content-hash>",
  "parent_revisions": [],
  "instructions": "Normalize permitted fields and validate the result.",
  "applicability": {"task_family": "record-normalization-v1"},
  "context_requirements": [],
  "workflow": {
    "entry": "parse",
    "nodes": [
      {"id": "parse", "operator": "parse_record", "next": "validate"},
      {"id": "validate", "operator": "validate_record", "next": "done"}
    ],
    "terminals": ["done"],
    "max_steps": 4
  }
}
```

An unknown operator, dangling edge, hidden executable source, invalid input reference, or missing termination bound is invalid. The first graph supports sequence and a registered conditional branch; loops/retries require explicit counters, and total step bounds apply regardless of graph shape. Operators cannot mutate evaluator state.

Candidate lifecycle: `proposed → validated → development_evaluated → validation_evaluated → accepted/rejected/inconclusive`. Invalid and failed attempts retain terminal records. A study-level frozen export receives a final test report; final-test scores do not feed further edits in that study. An accepted validation champion is not automatically a tested deployment release.

Publication uses one transaction to confirm complete compatible evidence and update the incumbent pointer. Check expected incumbent revision to prevent competing selectors overwriting newer decisions. Crashes before commit leave the prior champion intact. Resume may retry a local resettable trial as a new attempt, but never assume a pending external call was free or had no side effects.

## Optimization policy

Start with sequential bounded hill climbing: evaluate the seed, propose one small change, evaluate it on development cases, validate promising candidates against the incumbent, and promote only through the frozen gate. Never replace the incumbent simply because the final iteration scored highest on one case.

Search stops at a candidate/trial/call/token/spend cap, deadline, cancellation, or a predefined patience limit. Return the last valid incumbent plus stop reason and incomplete-work details. If no candidate is eligible, return `no_valid_skill` rather than a fabricated winner.

The first objective is maximize correctness subject to hard resource constraints, then break ties with declared deterministic execution cost. Later objectives can combine normalized quality, latency, and cost. The percentages in the conversation are illustrative; they are not adopted defaults. Quality gates cannot be traded for lower cost.

Pareto mode compares only eligible candidates under the same dataset, model, runner, and evaluator configuration. Minimize cost/latency and maximize quality; retain nondominated candidates with a declared tolerance and archive cap. A deterministic policy chooses the deployed candidate. An archive is not an ensemble unless multiple workflows are actually run and combined.

## Milestones and exits

| Milestone | Tasks | Exit gate |
| --- | --- | --- |
| M0: foundation and contracts | T001–T004 | Scope/history documented; exact schemas and frozen offline protocol reviewed |
| M1: execution and evidence | T005–T008 | Installable library; bounded/resettable runner; immutable complete trial records |
| M2: optimization vertical slice | T009–T011 | Offline search retains the right champion and survives rejection/interruption |
| M3: reusable skills and model proposals | T012–T014 | Export/import and application-owned proposer work; optional frontier is inspectable |
| M4: empirical evaluation | T015–T017 | Fixed protocol, competent budget-matched baselines, held-out results with limits |
| M5: integrations and inspection | T018–T019 | Optional context integration and lineage/score inspector use public contracts |
| M6: release preparation | T020 | Reproducible installable artifacts, licensing/identity decisions, honest documentation |

M1 begins after T004. Default runtime checks are offline. M3's integration uses a fake application callback first; any live smoke remains separate and requires authorization. Negative evaluation results do not prevent honest reporting or a useful library release, but they prevent unsupported effectiveness claims.


## Implemented scheduling and release boundary

ADR 001 allows the local context adapter, inspector and distribution checks after software verification without waiting for external empirical review. M4 remains a separate research acceptance lane. This does not close T015–T017 or justify a performance claim. Local artifacts are version 0.1.0 under MIT; publication is a separate action.

The library now supports application-owned seed generation from a task scaffold inside the same budget ledger, new studies seeded from learned revisions, and label-free execution of portable bundles. Current SQLite artifacts are bounded JSON; an external large-blob backend is deferred because it is not needed for the supported artifact sizes.
