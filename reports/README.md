# Recorded software evidence

`software-study-protocol.json` is written before execution. `software-study.json` contains the frozen protocol, code/dataset identities, every per-case trial, all selection events and resource charges, plus aggregate summaries. These are fictional authored software fixtures with exact labels, not independently reviewed scientific benchmarks.

The run contains five methods across five seed settings: 25 studies and 1,416 trials. Each study has the same upper candidate/resource limits; actual work is reported. Unchanged-seed and authored-reference controls intentionally perform less search.

| Policy/control | Mean final correctness | Meaning |
| --- | --- | --- |
| Unchanged seed | 37.5% | Initial schema-valid normalizer |
| Authored reference | 100% | Handwritten correct workflow; not one-shot model generation |
| Random edits | 92.5% (62.5–100%) | Random boolean flags and redundant-operation choice |
| Development feedback | 100% | Domain policy examines development errors to enable aliases/trimming and remove a redundant step |
| Instruction only | 37.5% | Negative control: deterministic operators do not consume instruction text |

The small fixture repeats similar semantics across disjoint values/template IDs. That is useful to catch pipeline errors, but does not establish real-world task diversity or out-of-distribution generalization. Repeats of deterministic controls are not independent scientific replications. No results from SkillOpt, GEPA or AFlow are fabricated or implied. Model judgment, cost savings on real providers and transfer to other domains are unmeasured.

`inspector.png`, its mobile companion and `inspector.json` come from the running self-contained inspector with an actual stored authored demo. Browser checks cover both widths, filtering, search, selection, per-case data, trace disclosure and console errors. There are no mocked browser responses or altered DOM data.

`release-check.json` describes exact distribution hashes and clean-wheel verification. It is excluded from the source distribution to avoid self-referential archive hashes. Distribution files are local under `dist/`.


## Minimum-cost live Haiku check

`live-haiku-protocol.json` precedes the explicitly authorized run. `live-haiku.json` records exactly three paid generations, three input-token preflights and zero retries: 775 input plus 92 output tokens, estimated **$0.0001235**. The API key is absent from all files.

The optimizer model chose compact flags for one candidate; workevo executed and selected it against development/validation before freezing and testing. Those 40 local exact trials use registered deterministic operators. A separate model-target smoke used two additional held-out records in one baseline batch and one evolved-instruction batch: 1/2 versus 2/2 correct. One tiny pair is not statistical, independently reviewed, or a comparison with other optimizers. The domain-specific compact edit format is an application adapter used to keep token cost minimal.

`haiku-rehearsal.json` is explicitly an offline fake-transport rehearsal; its token/cost values are simulated and are not billed. Run `uv run python scripts/live_benchmark.py --dry-run` without credentials. `--live` is a paid action, defaults to Haiku, uses hidden key entry or ANTHROPIC_API_KEY, and must not run automatically in CI. The completed authorized run should not be repeated merely to refresh reports.
