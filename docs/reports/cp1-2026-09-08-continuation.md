# CP1 continuation: coverage recovery and development regression

**The development recall target is reached; CP1 remains open pending a new
independent confirmation and final-answer audit.** The original benchmark now
informs development, so its improved result must not be called held out.

## Real measurements

All runs retain the original 24 requests, 100 judgments and 22 known direct
candidates. No ground-truth relevance labels or thresholds were changed.

| Stage | Corpus | Known direct recall@30 | Interpretation |
| --- | --- | ---: | --- |
| Original catalogue | Visual descriptions | 5/22 (22.73%) | Preserved initial failure |
| Broad recovery and 100 independently preselected texture reviews | Visual descriptions | 5/22 (22.73%) | More coverage did not cover these misses |
| Same broad enrichment | Metadata plus eligible descriptions | 4/22 (18.18%) | Diagnostic; metadata is not a substitute for visual meaning |
| Re-review of the historical candidate pool plus verified pixel transfers | Visual descriptions | **20/22 (90.91%)** | **Development regression, not independent acceptance** |

The previously covered shelter miss moved from rank 138 to rank 1 after its
actual appearance and recognizable function were described more clearly. A
fresh encoding matched the original stored vector (cosine approximately 1),
so the original miss was not attributed to corrupt vector bytes. No asset-key
boost, benchmark-specific ranking rule or change to the embedding weights was
introduced. Two independently known candidates remain outside the top 30.

Final visually accepted precision, positive-request answer rate and verified
final control violations are still unmeasured. Passing development recall does
not fill in those missing results.

## What was recovered and inspected

- Two earlier broadly selected model batches contained 192 completed reviews
  absent from the catalogue. Full manifest/image/asset checks allowed 175
  accepted descriptions and 17 ambiguity records to be imported. A scan of the
  other historical response files found no further unimported response records.
- The current operator actually inspected 100 textures from a batch selected
  before this evaluation. Captions describe visible appearance, with native alpha
  accounting and atlas/runtime limitations. These are not generated benchmark
  relevance labels.
- All 99 unique assets in the old independently explored candidate pool were
  then inspected as **development material**, including distractors and uncertain
  cases, rather than only the known positives. The result was 94 accepted
  descriptions and 5 ambiguous records. Blank, incomplete and insufficiently
  detailed views were not forced into accepted annotations.
- Pixel transfer planning found a missing historical source archive path. A
  local replacement was accepted only after all 194 referenced byte segments
  matched their original offsets, lengths and SHA-256 values. The original audit
  remained unchanged; the derived audit and mapping were saved separately.
- The source-verified transfer pass added 578 exact-pixel reuses and refreshed
  12 stale transfers after parent revisions. They count as **zero new visual
  inspections**, with occurrence provenance retained.

The local working catalogue now has 3,414 direct visual annotations and 3,072
exact-pixel transfers, for 6,486 eligible visual documents. The net increase from
the starting snapshot is 346 direct annotations and 578 transfers. Some accepted
reviews replaced existing descriptions, so review counts are not net additions.
Game files, captions, evidence images, database snapshots and occurrence keys
remain local and are not included in the repository.

## Public changes and checks

The evaluator can now explicitly capture the existing `annotations` or
`metadata` corpus. It records the choice in the run identity. Search coverage
distinguishes fresh documents with usable visual descriptions (including exact
pixel transfers) from metadata-only documents, preventing a full metadata index
from being mistaken for full visual coverage.

New runs default to a diagnostic role. The explicit `--role development`
classification cannot close CP1 even with perfect supplied metrics. Only an
explicitly declared held-out run can pass, and the actual independent protocol
still requires external review. Older run records without a role cannot silently
pass the new gate. The saved development run in this continuation predates that
role field; it is documented as development here and rejected by the gate.

Validation: **197 Python tests passed, including the real pinned encoder test;
2 Node tests passed.** New tests exercise separate corpus selection, honest
metadata/visual coverage and rejection of perfect-but-development evaluations.
Real captures ran all 24 requests after broad enrichment, in metadata mode and
after development re-review. The original failing outputs remain unchanged.

The metadata embedding build processed 50,017 documents in 305.43 seconds on
the same Apple M3 Pro/18 GiB/macOS 26.2 environment as the first report. The three
subsequent 24-query captures took 147.14, 150.32 and 142.00 seconds respectively,
excluding encoder initialization and image review. These are observations under
local workload, not a controlled performance comparison. Existing renders were
reused and verified. Agent review/token costs were not independently metered.

## Remaining acceptance work

Freeze new varied requests before inspecting search results, discover candidates
independently across the declared source scope, and keep those judgments hidden
from the final answerer. Measure the raw top 30 and an actual visually verified
answer/abstention for every request, with a separate blind audit of accepted
answers and negative/constraint controls. Retain failures instead of optimizing
the confirmation set and relabeling it held out.

The [evaluation protocol](../evaluation.md) and the [initial failed
baseline](cp1-2026-09-08.md) remain the reference. This continuation establishes
useful development progress, not completion of CP1, CP4 or CP5.
