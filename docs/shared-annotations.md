# Shared visual descriptions

The repository includes `data/annotations/sa-2026-10-03.json`: 7,815 reviewed
text descriptions under the repository's MIT license. It contains no game
geometry, textures, rendered images, embeddings, private database, or local paths.
Cloning/updating the repository downloads the pack; no private server is required.

| Kind | Descriptions | Source-bound | Reference-only |
| --- | ---: | ---: | ---: |
| Models | 2,716 | 2,291 | 425 |
| Texture occurrences | 5,099 | 3,895 | 1,204 |
| Total | 7,815 | 6,186 | 1,629 |

These are counts in the publisher's mixed SA/mod catalogue, not a promise that
all entries exist in a vanilla installation. Texture transfers reuse a real
review of identical pixels; they are not additional independent inspections.
This pack includes CP1 development enrichment and must not serve as unseen
CP1 evaluation data.

## October 2026 checkpoint

The October 3 pack incorporates 1,393 additional local descriptions from the
trial and the first three continuation waves: 683 models and 710 texture
occurrences. Exact-pixel transfers are included in occurrence counts, not counted
as independent image inspections. Sixty-four of these entries replace earlier
public descriptions of the same assets, so the public pack grows by 1,329 entries.
The September pack remains available unchanged.

This release also replaces 26 historical descriptions: 14 corrections independently
checked against source-bound images, plus 12 door-texture occurrences with identical
pixels, original prose and tags. Corrections cover object categories, drawer and
pane counts, lettering, decorative patterns, and open versus closed geometry.
Other historical audit proposals remain pending; this release does not certify
that all historical descriptions are correct. Reviews and the independent spot
checks were performed by AI agents, not human reviewers.

On the fixed local inventory of 47,222 entries, the reviewed working databases
progressed from 4,586 to 5,979 descriptions (9.71% to 12.66%). These local counts
are distinct from the public pack's mixed SA/mod inventory and do not prove that
every game asset was enumerated. Later continuation batches are excluded from
this release pending independent audit.

A clean import against that local inventory matched 5,969 entries: 2,124 models
and 3,845 texture occurrences. The other pack entries were reference-only (1,629),
had missing or different source bytes (165), or had no catalogue match (52).
Ten locally reviewed entries are not automatically reusable through this pack;
source bindings remain conservative, particularly for multi-view texture context.
No private databases, native game files, images or local paths are included.

## Use the pack

After installing GTA Scout and building your own catalogue as in the README:

```sh
asset-catalog-pack inspect --pack data/annotations/sa-2026-10-03.json
# Preview matches without changing the database:
asset-catalog-pack --db output/my-sa.sqlite import \
  --pack data/annotations/sa-2026-10-03.json \
  --game-root '/path/to/GTA San Andreas'
# Apply matching descriptions, preserving existing local reviews:
asset-catalog-pack --db output/my-sa.sqlite import \
  --pack data/annotations/sa-2026-10-03.json \
  --game-root '/path/to/GTA San Andreas' --apply
asset-catalog-semantic --db output/my-sa.sqlite build
asset-catalog-semantic --db output/my-sa.sqlite search \
  'a worn wooden chair' --kind model --hybrid
```

Semantic search requires the optional `.[semantic]` dependencies. Lexical search
works immediately after import. No Blender render or new vision call is needed
for source-matched descriptions. You should still inspect shortlisted assets for
your particular use and constraints.

Use `--archive PATH` for an extra IMG that was also included in your source
catalogue. Installation roots and IMG offsets can differ. The importer locates
entries locally, checks their length and SHA-256, and binds descriptions to local
metadata hashes. Model matching includes DFF and recorded texture dictionaries;
texture matching checks the dictionary bytes and named occurrence. Renamed
archives, different padding, dictionary repacks, unsupported source layouts and
ambiguous duplicate archives can reduce coverage even when appearances match.
There is no name-only fallback into verified semantic results.

**Reference-only entries remain publicly readable in the JSON pack.** Their
historical image reviews are real, but the surviving evidence cannot establish a
portable source-byte binding. They are not imported automatically. An agent can
use them as leads, then inspect local views and import its own review through
`asset-catalog-visual`. Their image hashes are provenance identifiers, not public
image downloads or independently reproducible visual evidence.

Imported annotations have method `shared-visual`, retain the pack version, entry
identifier, review-image hashes and limitations, and explicitly state that no
local visual review was performed. Search rechecks local source bytes and excludes
changed/missing sources; rebuild semantic vectors after importing updates.
Local visual reviews are never overwritten. Shared annotations can be refreshed
by importing a newer trusted pack. Moving a game installation requires reimport.
A pack digest detects corruption; it is not a publisher signature. Use packs from
a publisher you trust, just as you would any external description dataset.

## Publishing updates

The export command reads the source catalogue without modifying it, verifies
existing local image evidence, exports only an explicit public field list, and
rejects paths/URLs in prose. A private pixel audit can recover source bindings for
texture occurrences; model bindings come from render manifests linked to the
reviewed views. Missing source provenance produces a reference-only entry, not a
fabricated verified match.

```sh
asset-catalog-pack --db output/reviewed.sqlite export \
  --version sa-YYYY-MM-DD --audit output/private-texture-audit.json \
  --out data/annotations/sa-YYYY-MM-DD.json
```

Inspect the generated text, schema, counts and diff before publishing. Use a new
filename/version for updates. Never publish the source database or evidence
images. The sanctioned public text pack is distinct from private review packets.
