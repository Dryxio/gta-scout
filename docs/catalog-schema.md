# Local catalogue input

`asset-catalog --db DATABASE build --root CATALOG_ROOT --game sa` reads:

```
CATALOG_ROOT/
  models/data/models.json
  textures/data/textures.json
  models/data/model-sizes.json    # optional
  models/data/locations.json      # optional
```

Minimal models.json (synthetic):

```json
{"models":[{"id":1,"name":"item_x01","dff":"item_x01","txd":"fixture","source":"custom.ide","tags":[]}]}
```

Minimal textures.json (synthetic):

```json
{"textures":[{"name":"surface","txd":"fixture","source":"local/archive.img"}]}
```

Each model needs `id` and nonempty `name`. The extraction helper uses `dff` (falling back to `name`) and `txd`. Each texture needs `name`, `txd`; include `source` to prevent same-name occurrence collisions. Do not use a texture name as a pixel identity.

Model identity is `GAME:model:ID`. Texture identity is `GAME:texture:` followed by compact JSON `[source,txd,name]`. Use keys emitted by jobs/search, not hand-composed escaping. Conflicting duplicate identities fail transactionally; identical metadata repeats collapse. A build replaces that game's metadata snapshot, preserving other games and fresh matching annotations.

Optional sizes map string IDs to objects such as `{"1":{"width":1.2,"height":0.9,"depth":0.6}}`. Missing dimensions are excluded when dimension limits are requested. Optional locations use `{"locations":{"1":{"ipls":["fixture.ipl"],"locs":[{"x":0,"y":0,"z":0,"i":0}]}}}`. The placement `i` is the source IPL index, not an inferred interior ID.

Records and source roots enter the metadata hash. Raw DFF/TXD edits are not automatically detected by a metadata-only build. Render provenance separately includes source bytes and recipe hashes. Keep generated local metadata/evidence out of public Git.

## Local preview overrides

`asset-catalog-visual prepare --keys KEYS --overrides OVERRIDES --out DIR` expects:

```json
["sa:model:1"]
```

and an overrides mapping:

```json
{"sa:model:1":["/path/to/front.png","/path/to/side.png"]}
```

One to eight local images per selected key are supported. Every image is validated and hashed. For SA, the public GTA Stuff preview service (`https://gtastuff.namecdsl.xyz`) is used by default. Set `ASSET_PREVIEW_BASE_URL` to override it, or set it to an empty value to require local overrides. VC/III have no default preview service and require `ASSET_PREVIEW_BASE_URL` or local overrides. The service uses `thumbnails/ID.png` for SA models and sanitized `textures/TXD__NAME.png` for SA textures; VC/III use game-prefixed directories. Same-URL texture identity collisions require explicit local overrides. This preview URL scheme is not a pixel-resolution guarantee.

Annotation/review schema is emitted in each `packet.json`; use that exact version. No automatic external vision worker is included.

## Shared descriptions

`asset-catalog-pack` imports the versioned [public text pack](shared-annotations.md)
by checking local source bytes and rebinding to local asset hashes. Imported
`shared-visual` evidence tracks publisher review hashes and local source locators;
it does not require the publisher's private image paths or pretend a local review occurred.
