# Independent relevance evaluation (CP1)

`asset-catalog-evaluate` freezes local visual judgments, captures real search on
an isolated SQLite backup, and scores the CP1 thresholds. It does not annotate
assets, call a vision reviewer, or turn synthetic test passes into a GTA result.

The [first real rerun](reports/cp1-2026-09-08.md) fails the recall target. Keep
that failure when comparing future runs; do not relabel the expected answers to
make a benchmark pass.

## Protocol

1. Choose at least 24 varied requests before tuning descriptions or ranking.
   Include opaque-name cases, explicit visible constraints and negatives. Define
   the source scope, query language, retrieval mode, inspection budget and costs
   to measure before searching. Freeze one primary mode; additional modes are
   diagnostic comparisons, not an opportunity to select a winning test after it runs.
2. Discover candidates outside the engine's shortlist, using independent visual
   exploration. Record at least 100 query/candidate judgments, including direct,
   related-but-partial, irrelevant and uncertain cases. A failed render is a
   separate technical failure, not a visual judgment or an irrelevant object.
3. Keep the ground truth away from annotators and the agent producing final
   answers. Freeze it with image SHA-256 evidence. Distinct texture occurrences
   may share a judgment only with an independently audited exact-RGBA mapping;
   preserve every occurrence key. This equivalence concerns appearance only.
4. Run against a consistent snapshot. Use the public search implementation and
   a single ordered top 30, never the union of 30 lexical and 30 semantic results
   advertised as recall@30. Corpus coverage is reported separately.
5. Have the answerer inspect candidate images against every constraint, within
   the predeclared inspection budget. Record accepted answers or an explicit
   abstention for every request. Accepted answers must belong to the fixed top
   30 and carry actual hashed views and per-constraint checks.
6. A separate blind auditor judges returned candidates without seeing the
   answerer's verdicts. Additional retrieved-only judgments can establish final
   precision; they must not inflate the independent recall denominator. Preserve
   disagreements and resolve them explicitly in a new version, retaining the old
   one. Do not claim that accepting your own known labels proves independent precision.
7. Report raw ranking, visual final answers, abstentions, unjudged answers,
   coverage, missed-candidate categories, latency, rendering/review time and
   model costs separately. A run tuned on these queries becomes a development
   regression; confirm improvements with a newly frozen independent holdout.

The evaluator checks input consistency, evidence bytes and metric arithmetic.
It cannot establish reviewer independence, correctness of visual judgments,
source-to-pixel mappings or sample diversity by itself. Its `passed` field is a
numerical gate on the supplied evidence, not automatic certification of CP1.

## Private suite format

All files below belong under an ignored `output/` directory. Do not commit game
identities, private descriptions, evidence images, local paths or SQLite files.
The synthetic test suite generates original PNG evidence and redistributable toy
judgments without game files.

A suite has `version: "cp1-evaluation-v1"` and these fields:

| Field | Contents |
| --- | --- |
| `protocol` | Nonempty `selection`, `independence`, `scope`, `reviewer`, `limitations`; `independent_of_retrieval: true` is a provenance declaration requiring external review. |
| `queries` | Records with distinct `id`, nonempty `query`, `game` (`sa`, `vc`, `gta3`), `kind` (`model`, `texture`) and `constraints: [{id, requirement}]`. |
| `judgments` | Records with `query_id`, `keys`, `status`, `reason`, `reviewer`, `views` and `constraint_checks`. |

Judgment `status` is `relevant`, `partial`, `irrelevant` or `uncertain`.
`views` is an array of `{path, sha256}` for actual images, with absolute local
paths. `constraint_checks` contains exactly one `{id, verdict, reason}` for
each query constraint; `verdict` is `pass`, `fail` or `unknown`. A direct
(`relevant`) ground-truth judgment requires all constraints to pass.

`keys` usually contains one asset key. Multiple keys are allowed only for
textures with `pixel_sha256` and `equivalence_provenance` documenting the
independent exact-pixel audit. Do not infer equivalence from names, a thumbnail,
or matching text. Overlapping judgment keys are rejected.

```sh
asset-catalog-evaluate freeze --suite output/eval/suite.json \
  --out output/eval/benchmark.json
asset-catalog-evaluate run --benchmark output/eval/benchmark.json \
  --db output/my-sa.sqlite --mode semantic --role heldout --out output/eval/run-01
asset-catalog-evaluate score --benchmark output/eval/benchmark.json \
  --run output/eval/run-01/run.json --out output/eval/raw-score.json
```

`run` uses existing vectors as-is and preserves the source database. Build
vectors explicitly beforehand with `asset-catalog-semantic` if necessary.
Semantic/hybrid runs need the optional semantic dependencies and pinned model;
lexical runs need only the core. The copy's hash, encoder identity, environment,
load time and per-query latency are saved. Absolute image references stay local;
this is not a portable evidence export (CP3).

Runs default to `--role diagnostic`, which cannot close CP1. Use `--role
development` once the cases have informed captions or ranking. Only an explicitly
declared `--role heldout` run can pass the checkpoint, after the independent
protocol has actually been followed. The declaration is stored in the hashed run;
it is not proof of independence, and old tuned runs must never be relabeled.

The default remains `--corpus annotations`. To diagnose the separately supported
metadata corpus, build it explicitly with `asset-catalog-semantic --db DATABASE
--corpus metadata build`, then use `run --corpus metadata` and a new output
directory. The run records the corpus in its system identity. Metadata retrieval
is a discovery channel; it does not establish visual relevance. Search coverage
now separates `freshVisuallyAnnotatedDocuments` (including usable exact-pixel
transfers) from `freshMetadataOnlyDocuments`. Neither number is a count of new
direct visual inspections.

`score` writes a report and exits **2** when any acceptance gate is incomplete
or fails. Omitting final decisions intentionally fails acceptance. Every output
file/run directory must be new, so reruns do not erase earlier failures.

## Final decisions and blind audit

The decisions document contains `run_sha256` (canonical JSON SHA-256 from
`asset_catalog_evaluate.digest(run)`), `reviewer`, `protocol`,
`independent_of_ground_truth: true` and `results`. Each result has `query_id`,
`decision` (`answered` or `abstained`), `reason` and `accepted`.
Each accepted record has `key`, `reason`, `views` and `constraint_checks` in the
same evidence/check format as the suite. Abstention uses an empty accepted list.

An optional separate audit document contains `run_sha256`, `reviewer`,
`independent_of_answers: true` and `judgments` in suite format, limited to
retrieved top-30 candidates. Conflicts with frozen judgments are rejected;
they require recorded adjudication instead of silently overwriting a failure.

```sh
asset-catalog-evaluate score --benchmark output/eval/benchmark.json \
  --run output/eval/run-01/run.json --decisions output/eval/answers.json \
  --audit output/eval/blind-audit.json --out output/eval/final-score.json
```

The scorer requires at least 85% independently direct accepted answers, at least
80% answered requests among original positive requests with known candidates,
at least 90% recall@30 over independently known direct candidates and zero
verified negative/constraint violations. Unannotated positives stay in recall's
denominator. Empty answers yield undefined precision, never 100%. Unjudged
accepted answers block acceptance; the reported precision is then only a lower
bound. Raw top-five precision stays null unless every returned position is
independently judged. Negative controls concern verified candidate/constraint
failures; no-positive-found is not a verified whole-game negative query.

Publish only manually reviewed aggregates and methodology. Detailed scores
contain private missed-candidate keys. Timing from `run` excludes rendering,
visual review and paid agent costs; measure those independently and report
unknown costs as unknown.
