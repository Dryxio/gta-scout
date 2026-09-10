# GTA Scout

**[Join the Discord community →](https://discord.gg/mgFRd2AzF8)**

**Create GTA-style 3D models and scenes with your AI.**

Describe what you want to make: a street-food stand, a new shop interior, a custom car, or an entire street market. Give your AI access to GTA Scout and Blender so it can build with the game's own visual style.

GTA Scout helps your AI find and inspect models and textures from your GTA files. Your agent then uses Blender to combine them, modify existing models, and create new geometry — turning your idea into an editable 3D creation you can preview and refine through conversation.

**Early alpha.** Works with an AI coding agent, Blender, and your own classic PC San Andreas files.

## Get started with your AI

**Give your AI this repo and tell it what you want to do.** It can check your setup, install the tools it needs, and walk you through anything that needs your help.

**Before you start:** this is a free tool for an AI coding agent. Your agent must be able to read and write files and run commands on your computer, including Blender. A chat that only gives you instructions cannot complete the workflow for you. Your AI provider may charge separately.

Copy this into your agent:

> Help me set up https://github.com/Dryxio/gta-scout. Read the README and agent guide, check what's already installed on my computer, and help me install what's missing, including the Blender tools for this task. Ask me where my GTA San Andreas files are if you need them. Then create a small street-food stand in the GTA San Andreas style. Find suitable game textures and props, model the stand in Blender, and save an editable .blend file with a rendered preview. Show me the result so we can refine it.

You'll need your own classic PC San Andreas files for game assets. Just trying the tool? Ask your agent to run the included demo first; it needs neither GTA nor Blender.

## What you can create

- **New props and buildings:** model a kiosk, a storefront, or a small building using textures that fit the game.
- **Custom vehicles:** turn an existing car into a police variant, a convertible, or a different build.
- **Interiors and scenes:** furnish a shop, extend a room, or assemble a street market from game assets and new geometry.

**Describe your idea → find the right assets with GTA Scout → build in Blender with your AI → preview and refine.**

The showcase below comes from this wider AI-assisted Blender workflow. GTA Scout supplies asset discovery and inspection; your agent supplies the modeling scripts and uses Blender to create the result. The specific showcase generators and game assets are not included in this repository.

**[Get started with your AI](#get-started-with-your-ai) · [Manual setup](#manual-setup) · [Agent guide](AGENTS.md) · [Blender CLI guide](docs/blender-cli.md)**

## Showcase

Click any image to inspect it at a larger size. Scene views below are captured in **Ariane**; vehicle and early project previews are rendered in **Blender**.

### Mariachi Plaza — a real place reimagined in Los Santos

A Los Angeles landmark interpreted in the San Andreas style and placed in the existing city. **Ariane viewport captures**, showing the plaza in its surrounding map and the day/night prelight.

| Plaza in the city — day | Kiosco — day |
| --- | --- |
| ![Plaza in the city — day](docs/images/showcase/02-mariachi--07-day-overview.jpg) | ![Kiosco — day](docs/images/showcase/02-mariachi--08-day-kiosco.jpg) |

| Plaza — night | Kiosco — night |
| --- | --- |
| ![Plaza — night](docs/images/showcase/02-mariachi--01-night-overview.jpg) | ![Kiosco — night](docs/images/showcase/02-mariachi--02-night-kiosco.jpg) |

| Lit pavilion interior | Street-level context |
| --- | --- |
| ![Lit pavilion interior](docs/images/showcase/02-mariachi--05-night-interior.jpg) | ![Street-level context](docs/images/showcase/02-mariachi--06-night-street.jpg) |

### Grove Street — night market

An existing neighborhood filled with custom stalls, reused props, signs and lighting. **Ariane viewport captures**; the populated Blender presentation is separate.

| Grove Street after dark | Market in daylight |
| --- | --- |
| ![Grove Street after dark](docs/images/showcase/01-grove-market--01-night-overview.jpg) | ![Market in daylight](docs/images/showcase/01-grove-market--08-day-overview.jpg) |

| Grill stall | Fresh produce |
| --- | --- |
| ![Grill stall](docs/images/showcase/01-grove-market--03-grill.jpg) | ![Fresh produce](docs/images/showcase/01-grove-market--04-fresh-produce.jpg) |

| Vinyl and tapes | Bakery stall |
| --- | --- |
| ![Vinyl and tapes](docs/images/showcase/01-grove-market--05-vinyl.jpg) | ![Bakery stall](docs/images/showcase/01-grove-market--06-bakery.jpg) |

### Vehicle conversions — LAST STOP and Sultan police

A bus turned into a food truck, a matching delivery scooter with modeled burger branding, and a Sultan adapted into an LSPD patrol car. **Blender renders**; the LAST STOP views include the later burger iterations.

| Bus converted into a food truck | Food truck — rear view |
| --- | --- |
| ![Bus converted into a food truck](docs/images/showcase/bus-food-truck--revisions--v3-burger--after-burger.jpg) | ![Food truck — rear view](docs/images/showcase/bus-food-truck--revisions--v3-burger--after-rear.jpg) |

| Matching delivery scooter | Sultan police |
| --- | --- |
| ![Matching Pizzaboy delivery scooter](docs/images/showcase/last-stop-pizzaboy--revisions--v2-burger--after-burger.jpg) | ![Sultan converted into an LSPD patrol car](docs/images/showcase/video-assistant--sultan--09.jpg) |

### Sultan cabriolet and Elegy racing

Different transformations of existing cars: an open cabin and a racing build with bodywork and livery changes. **Blender renders**.

| Sultan cabriolet | Open cabin detail |
| --- | --- |
| ![Sultan cabriolet](docs/images/showcase/sultan-cabriolet--after-hero.jpg) | ![Open cabin detail](docs/images/showcase/sultan-cabriolet--export-reread-interior.jpg) |

| Elegy racing | Elegy — rear and wing |
| --- | --- |
| ![Elegy racing](docs/images/showcase/elegy-racing--after-hero.jpg) | ![Elegy — rear and wing](docs/images/showcase/elegy-racing--after-rear.jpg) |

### Employment agency — opening an existing building

An accessible agency on the upper terrace of an existing Los Santos building, with reception and furnished offices. **Ariane viewport captures**.

| Upper-terrace entrance | Reception |
| --- | --- |
| ![Upper-terrace entrance](docs/images/showcase/03-employment--01-terrace.jpg) | ![Reception](docs/images/showcase/03-employment--03-reception.jpg) |

| Adviser desks | Office equipment |
| --- | --- |
| ![Adviser desks](docs/images/showcase/03-employment--04-advisers.jpg) | ![Office equipment](docs/images/showcase/03-employment--07-office-equipment.jpg) |

### CJ’s house — extending the original interior

A new staircase and additional floor connected to the original house. **Ariane viewport captures**, retaining the interior’s subdued lighting.

| New staircase | New upper hallway |
| --- | --- |
| ![New staircase](docs/images/showcase/04-cj-house--04-new-staircase.jpg) | ![New upper hallway](docs/images/showcase/04-cj-house--06-new-upper-hall.jpg) |

| Study | Bedroom |
| --- | --- |
| ![Study](docs/images/showcase/04-cj-house--07-study.jpg) | ![Bedroom](docs/images/showcase/04-cj-house--08-bedroom.jpg) |

<details>
<summary><strong>More police vehicles — 8 additional renders</strong></summary>

### More police conversions

A selection from the additional LSPD vehicle conversions. **Blender renders**.

| Buffalo | Bullet |
| --- | --- |
| ![Buffalo](docs/images/showcase/police-vehicle-batch--buffalo--front.jpg) | ![Bullet](docs/images/showcase/police-vehicle-batch--bullet--front.jpg) |

| Cheetah | Flash |
| --- | --- |
| ![Cheetah](docs/images/showcase/police-vehicle-batch--cheetah--front.jpg) | ![Flash](docs/images/showcase/police-vehicle-batch--flash--front.jpg) |

| Infernus | Jester |
| --- | --- |
| ![Infernus](docs/images/showcase/police-vehicle-batch--infernus--front.jpg) | ![Jester](docs/images/showcase/police-vehicle-batch--jester--front.jpg) |

| Turismo | Uranus |
| --- | --- |
| ![Turismo](docs/images/showcase/police-vehicle-batch--turismo--front.jpg) | ![Uranus](docs/images/showcase/police-vehicle-batch--uranus--front.jpg) |

</details>

### Earlier builds — kiosks, shops and interiors

**Blender renders** from the first workflow demos.

| Street kiosk | Open 24/7 convenience store |
| --- | --- |
| ![Papercuts street kiosk, rendered in Blender](docs/images/street-kiosk.png) | ![Open 24/7 convenience store, rendered in Blender](docs/images/247-store.png) |
| Coffee shop | LSSD interior |
| ![The Daily Grind café, rendered in Blender](docs/images/coffee-shop.png) | ![Sheriff reception, rendered in Blender](docs/images/lssd.png) |
Traffic-node authoring is available in the companion project [GTA Flow](https://github.com/Dryxio/gta-flow), with its own Blender and map screenshots.

The public project is named **GTA Scout**. For compatibility, the Python distribution remains `gta-asset-search` and existing `asset-catalog*` commands are unchanged.

## Manual setup

Prefer to install it yourself? Expand the instructions below.

<details>
<summary>Manual installation, configuration and examples</summary>

## Install and try it without GTA

Python **3.12 recommended**, Python 3.10+ supported by the core. SQLite must include FTS5. No server, SSH access, paid API key, or Blender installation is needed for this toy demo.

```sh
git clone https://github.com/Dryxio/gta-scout.git
cd gta-scout
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python examples/make_demo.py --out output/demo
asset-catalog --db output/demo/catalog.sqlite search 'red chair'
asset-catalog --db output/demo/catalog.sqlite stats
asset-catalog-visual --db output/demo/catalog.sqlite prepare \
  --keys output/demo/keys.json --overrides output/demo/overrides.json \
  --out output/demo/packets
```

On Windows, create the environment with `py -3.12 -m venv .venv` and activate it with `.venv\Scripts\Activate.ps1`. If your Python lacks `venv`/`ensurepip`, `uv venv --python 3.12 .venv` and `uv pip install --python .venv/bin/python -e .` are an alternative on macOS/Linux.

The demo generates two original toy images with opaque names and explicit synthetic descriptions. It tests plumbing, **not GTA search quality**. Use a new output directory when rerunning it.

### Optional semantic search

```sh
python -m pip install -e '.[semantic]'
asset-catalog-semantic --db output/demo/catalog.sqlite build
asset-catalog-semantic --db output/demo/catalog.sqlite search \
  'a place to sit down' --kind model --hybrid
```

This embeds **text**, including descriptions made after visual inspection, with `intfloat/multilingual-e5-small` at a pinned revision. The first use downloads model weights from Hugging Face; subsequent runs use the local cache. No image is automatically sent to a vision provider. Unannotated objects cannot acquire visual meaning simply by embedding their filenames. The default annotation corpus and the opt-in metadata corpus stay distinct; every semantic response reports coverage. Similarity scores are not probabilities.

## Use your own San Andreas files

The initial source adapter targets **classic PC San Andreas**, not Definitive Edition or console archives. Keep generated output outside your game installation:

```sh
asset-catalog-sources --game-root '/path/to/GTA San Andreas' \
  --out output/my-sa-source
asset-catalog --db output/my-sa.sqlite build --root output/my-sa-source --game sa
asset-catalog --db output/my-sa.sqlite search 'office desk' --kind model --limit 20
asset-catalog --db output/my-sa.sqlite jobs --limit 40
```

The adapter reads active IDE declarations in `data/gta.dat`, `data/default.ide`, optional `--ide FILE` extras, IMG v2 archives under `models/`, optional `--archive FILE` extras, and loose PC TXDs. It writes model and texture **metadata**, with a `source-report.json` listing failures. It does not export game binaries or pixels, modify the game, include inactive mod assets automatically, inventory all standalone clothing DFFs, or compute placements/dimensions. A dictionary may contain texture names whose pixels have not been visually inspected.

Already have a catalogue? Supply the [documented JSON layout](docs/catalog-schema.md) with `build --root`. Namespaces support `sa`, `vc`, and `gta3`; full VC/III source adapters and validation are future work.

**A fresh installation starts without our local annotations.** Render a bounded batch and have an agent/human review it before expecting useful visual semantic retrieval. See the [agent guide](AGENTS.md) and [Blender CLI workflow](docs/blender-cli.md).

</details>

## What works in this alpha

- Incremental SQLite/FTS5 import, bilingual lexical hints, game/kind/dimension filters, provenance and explicit partial matches.
- Local multilingual text embeddings, stale-vector exclusion and hybrid reciprocal-rank fusion.
- Local image overrides, immutable evidence packets, blind contact sheets, confidence/ambiguity tracking and evidence-hash checks.
- Query-specific shortlists with explicit constraints, separate from general-purpose annotations.
- Bounded campaign planning, resumable four-view Blender rendering, exact pixel transfer with parent provenance, and conservative render-signal diagnostics.
- Exact-byte scans and an optional cache deduplication planner; source game assets are never consolidated.

## Limits and roadmap

**Coverage is incomplete.** Existing unit tests do not prove that every relevant object is found. Missing models, transparent/ambiguous atlases, source variants, skinned geometry, and unreviewed appearances remain real gaps. Static rendering rejects skinned DFFs instead of inventing a successful preview. Metadata and source changes still need deliberate rebuild/review; this is not a filesystem watcher.

Our earlier local campaign indexed 50,017 entries (16,838 models including extra mod entries, and 33,179 texture occurrences). Its first enrichment checkpoint passed with 1,730 usable direct visual descriptions at that historical snapshot. **Those data and annotations are not distributed, those counts are not a standard vanilla-game inventory, and that checkpoint does not establish exhaustive recall.**

The public [issues](https://github.com/Dryxio/gta-scout/issues) track:

- Independent relevance / missed-candidate evaluation (CP1).
- End-to-end scale, interruption recovery, freshness, throughput and storage validation (CP3).
- Complete model review and honest unresolved-case accounting (CP4).
- Texture occurrence coverage, exact pixels, alpha and real model/atlas context (CP5).
- Later VC/III adapters and new-asset maintenance (CP6, outside the original SA campaign).

See [roadmap criteria](docs/roadmap.md), [validation](docs/validation.md), and [architecture / costs](docs/architecture.md).

The [CP1 evaluation CLI and independent-review protocol](docs/evaluation.md) now
capture reproducible local benchmarks. The [2026-09-08 real rerun](docs/reports/cp1-2026-09-08.md)
finds 5 of 22 independently known candidates in the semantic top 30; CP1 remains open.
The [continuation](docs/reports/cp1-2026-09-08-continuation.md) reaches 20/22 after
development enrichment; a new independent confirmation and final-answer audit remain required.

## Tests

```sh
python -m unittest discover -s tests -p 'test_asset_catalog*.py'
# Optional real pretrained model smoke, after installing .[semantic]:
ASSET_SEMANTIC_INTEGRATION=1 python -m unittest discover -s tests -p test_asset_catalog_semantic.py
# Optional Node extraction helpers:
npm ci --ignore-scripts
npm test
```

Default tests generate synthetic fixtures in temporary directories and need no game or network. The real embedding smoke downloads weights if uncached. CI runs the offline suite; it does not ship GTA data or promise gameplay validation.

## License and data

Original tool code: [MIT](LICENSE). [Third-party notices](THIRD_PARTY_NOTICES.md) cover separately installed dependencies, including GPL-licensed DragonFF. No DragonFF code, game binaries, texture packs, private catalog database, or reviewed GTA annotation dataset is bundled. Demo screenshots illustrate modding work and retain the rights of their underlying game content; they are not an asset redistribution license. Not affiliated with Rockstar Games or Take-Two Interactive.
