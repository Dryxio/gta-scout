# Using GTA Scout with an AI agent

This is an early-alpha discovery tool. Read README.md, docs/catalog-schema.md and docs/blender-cli.md before operating it. Keep the agent's existing Blender CLI construction workflow; use this tool to find and inspect reusable assets.

## Start

1. Ask for or discover the user's local game/source path and Blender executable. Use a local ignored output directory outside the game. Do not assume the maintainer's Mac, VPS, CDN or catalogue exists.
2. Run the synthetic quick start and `--help` before relying on commands. `--db` comes before the subcommand.
3. Build a fresh source snapshot with `asset-catalog-sources`; inspect `source-report.json`, especially failures. Import it with `asset-catalog build`. A successful metadata import is not a visual review.
4. Search multiple formulations and related functional categories. Inspect coverage. Opaque names and incomplete annotations mean absence in the shortlist is not proof that a suitable asset does not exist.
5. Render small, varied batches with the Blender guide. Use local `--overrides`; there is no default hosted preview service. Review images yourself using your image-viewing capability. Never infer an object's full shape or material role from its filename or a hidden surface.
6. Import honest reviews, preserving evidence paths and hashes. Describe visible shape, material, condition, likely use, orientation uncertainty and missing views. Do not mark an AI review as human. Never fabricate a visual review to make a test or coverage counter pass. Ambiguous/failed assets remain unresolved.
7. Build semantic vectors from actual descriptions; search with `--hybrid` and inspect the proposed objects. Test explicit user constraints visually and check dimensions/collisions/orientation in the construction scene.
8. Record which candidates were used, rejected, or found manually outside the results. Keep new benchmark candidates independent of the descriptions used to train/tune the index.

## Reviews and revisions

`asset-catalog-visual prepare` emits `manifest.json` (private identities/evidence) and `packet.json` (review instructions, image IDs and exact response schema). `sheets --manifest MANIFEST --out DIR` creates contact sheets. Read the packet's schema rather than guessing response fields. Import responses with:

```sh
asset-catalog-visual --db output/my-sa.sqlite import --manifest PATH_TO_MANIFEST --responses PATH_TO_RESPONSES
asset-catalog-semantic --db output/my-sa.sqlite build
```

Do not move/delete evidence after importing: search rechecks image bytes. Moving a local database alone does not move its evidence or make paths portable. An updated source snapshot needs explicit reimport; a changed DFF with unchanged metadata requires rerender/review as well.

`asset-catalog-shortlist --help` provides query-specific constrained verification. General descriptions and query verdicts must remain separate. `scripts/plan-asset-catalog-batch.py` selects deterministic category-balanced exploration batches; `scripts/asset_catalog_campaign.py` splits review packets; `scripts/asset_catalog_run_chunks.py` resumes bounded render chunks with a journal. These tools prepare work, they do not autonomously call a vision service.

## Public contributions

Keep tests synthetic and game-free. Never commit output, local paths, credentials, native assets, or private annotation payloads. Benchmark reports should disclose sample construction, missed candidates, unsupported assets and costs, without redistributing game data. Do not claim CP completion from render counts alone.
