# Public alpha checkpoints

These criteria preserve the original SA campaign's intent. Public contributors work from their own local sources; no private dataset is delivered. Numerical inventory counts from the original campaign are historical, not required universal totals.

- **CP1 — Independent missed-candidate evaluation.** Freeze at least 24 varied requests and 100 judgments, including negatives and explicit constraints. Select relevant candidates visually outside the search results. Report raw ranking, inspected final answers, abstentions and coverage separately. Target >=85% direct precision among accepted answers, >=80% answer rate on positive requests with known candidates, >=90% recall@30 over known direct candidates, and zero verified constraint violations. Finite evaluation cannot prove exhaustive recall.
- **CP2 — First useful enrichment.** Passed in an earlier local snapshot (1,730 usable direct visual descriptions, a diversity and quality audit). Exact-pixel transfers were excluded from the independent-review count. This is historical context, not an included dataset or a guarantee for fresh installs.
- **CP3 — Operational scale.** Deterministic inventory, resumable batches, transactional imports, corruption/missing-image/source-change checks, collision and failure recovery tests, measured latency/throughput/storage and portable evidence strategy. Existing tests cover selected cases; full-source acceptance remains open.
- **CP4 — Model coverage.** Every locally enumerated model needs fresh actual visual evidence or an individually justified unresolved verdict after reasonable source investigation. Rendered/inventoried does not mean described. Skinned/static renderer limitations are engineering work, not proof an object is unusable.
- **CP5 — Texture coverage.** Preserve every occurrence and exact pixel provenance; describe observable material/color/condition/pattern/alpha with uncertainty. Distinguish candidate TXD links from actual DFF material references and runtime binding. Review ambiguous atlases in model context. Never deduplicate by name alone.
- **CP6 — Later expansion.** VC/III source adapters and evidence-backed validation, new-asset maintenance and source watcher/import workflows. Outside the original SA campaign, not a prerequisite for the alpha.

The corresponding GitHub issues are the public task ledger. Packaging does not close any visual coverage checkpoint.

CP1 now has a [reproducible evaluator](evaluation.md) and a
[real failing baseline](reports/cp1-2026-09-08.md): semantic recall@30 is 5/22,
with 16 misses lacking fresh descriptions and one covered ranking miss. This
does not close CP1 or substitute for independent final-answer evaluation.
The [continuation](reports/cp1-2026-09-08-continuation.md) reaches 20/22 on the
development regression; it must not be relabeled as held-out acceptance.

Public tracking: [CP1 #1](https://github.com/Dryxio/gta-3d-ai/issues/1), [CP3 #2](https://github.com/Dryxio/gta-3d-ai/issues/2), [CP4 #3](https://github.com/Dryxio/gta-3d-ai/issues/3), [CP5 #4](https://github.com/Dryxio/gta-3d-ai/issues/4), [future CP6 #5](https://github.com/Dryxio/gta-3d-ai/issues/5).
