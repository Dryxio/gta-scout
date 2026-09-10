# Alpha validation

The [CP1 continuation](reports/cp1-2026-09-08-continuation.md) passes **197 Python
tests with the real encoder and 2 Node tests**. Real development recall reaches
20/22 after actual image review and source-verified transfers. This is a tuned
development result, not a new independent acceptance result.

CP1 evaluation work validated on 2026-09-08: **194 Python tests passed**, including
the opt-in real pinned encoder test, plus **2 Node tests passed**. The 27 new
evaluator tests use original synthetic images. A non-editable package installation
exposes `asset-catalog-evaluate`; a separate real 24-query capture reproduces the
baseline top 30 exactly. The [real relevance report](reports/cp1-2026-09-08.md)
fails CP1's recall threshold and leaves final visual precision unmeasured.

Initial extraction validated on 2026-09-07:

- Python 3.12, clean isolated environment: **167 tests, 166 passed, 1 optional pretrained-model test skipped**. Synthetic fixtures cover catalogue import/rollback, stale images/vectors, same-name texture collisions, query constraints, review races/revisions, pixel transfers, campaign resume and source adapter bounds.
- Opt-in semantic file: **13 tests passed**, including actual pinned multilingual-e5-small inference. This is a small synthetic inference smoke, not an independent GTA recall benchmark.
- Node.js helper tests: **2 passed** (malformed TXD rejection). Real extraction separately checked below; two unit tests are not exhaustive decoder validation.
- Local read-only classic PC SA adapter: **14,344 models and 32,878 texture occurrences**, no reported read failures on that installation. Includes active/default IDE scope; not equal to the historical catalogue with mod/standalone extras. No source files or resulting metadata are committed.
- One real local static DFF chair extracted with textures and rendered in four views under **Blender 5.2.1 LTS**, with a separately obtained public DragonFF checkout. Outputs stayed local and ignored. One model does not validate every source format or skinned asset.
- Synthetic quick start, visual local override packet and actual semantic build/search executed. The default preview service is unconfigured; no private CDN is needed.

The repository CI runs game-free tests on Python 3.10 and 3.12, plus Node helper tests. Gameplay behavior, full-catalogue visual coverage, hardware-wide timing/storage and final independent relevance targets remain unvalidated. See the public checkpoint issues.

Publication checks: a separate clean clone installed as a non-editable package passed the same 167-test suite and the toy search/local-image packet demo. The initial [GitHub Actions run](https://github.com/Dryxio/gta-scout/actions/runs/34073391506) passed on Python 3.10 and 3.12. The staged-file audit allowed only source/docs/tests and four curated PNG renders; no native asset, database, private source path or credential pattern was present.
