# Plan — Dragon Asset Catalog And Web Viewer

Date: 2026-08-26  
Status: Decision pass 1 complete — OP-001 and OP-003…OP-006 accepted;
OP-002 awaits final confirmation of the no-argument `assets organize`
contract; no asset migration, preview generation, or web implementation has
started

## Problem Summary

Three dragon candidates now sit as loose files in the external project's
`assets/collected/` root. They need consistent, self-contained folders with
human-readable README pages, YAML card metadata, measured technical facts,
preview images, and browser-ready 3D derivatives. The operation should become
reusable `charctx` behavior rather than a one-off file shuffle.

The same normalized asset contract should drive a local visual catalog. The
desired precedent is `C:\dev\VectorMind\cad-context`: an Astro SSR app started
only by the workspace CLI, asking the Python CLI for JSON and serving confined
artifacts without adding a second long-running Python service. This viewer is
read-only in V1 and must not become a parallel asset database or a second 3D
processing implementation.

Current read-only evidence:

| Candidate | Technical snapshot | Immediate issue |
| --- | --- | --- |
| `dragon.blend` | 67 mesh objects; 25,025 vertices; 196-bone armature; one 104-frame fly action | external textures are not packed/present; no provenance/license record |
| `blender_dragon.blend` | one 11,002-vertex mesh; 38-bone armature; no actions or materials | external texture is not packed/present; no provenance/license record |
| `european-dragon.zip` | nested rigged-animation FBX plus 14 PNG textures at 2K/4K | FBX not yet inspected; no provenance/license record |

## Resolution Summary

Only decisions that materially affect authority, safety, reproducibility, or
architecture are tracked. An open row is a proposal, not an accepted choice.

| OP | Topic | Proposal | Confidence | Status |
| --- | --- | --- | --- | --- |
| OP-001 | Metadata and README authority | Each package's `README.md` YAML front matter is authoritative for curated card/provenance fields; `inspection/report.json` is authoritative for measured facts; the CLI generates the README body from both while preserving a manual-notes region | high | **accepted 2026-08-26** |
| OP-002 | Safe package migration | `charctx assets inspect` is the no-write preview; `charctx assets organize` takes no required arguments and is itself the explicit mutation, organizing every eligible loose candidate under `assets/collected/` with full-batch preflight, staging, hash verification, and no overwrite/force mode | high | **open — final confirmation requested** |
| OP-003 | Missing provenance | Local viewing and processing remain allowed; use `provenance_status: incomplete`, explicit `unknown` fields, and a prominent catalog/page warning. This private workspace has no publishing path | high | **accepted 2026-08-26 with amendment** |
| OP-004 | Durable preview contract | Use headless Blender to produce a versioned inspection report, one browser GLB, and five deterministic WebP views inside each asset package; source files remain immutable and transient work stays in `.cache/` | high | **accepted 2026-08-26** |
| OP-005 | Reusable CLI surface | Add one `charctx assets` group for inspect/list/show/organize/build/validate and add `charctx web`; the Python domain API stays side-effect-free and all writes are explicit CLI actions | high | **accepted 2026-08-26** (organize semantics remain OP-002) |
| OP-006 | Web architecture and V1 scope | Build a local-only Astro SSR app in `webapp/`, started only by `charctx web`, sourcing catalog/detail JSON from `charctx assets`; V1 is a read-only catalog, gallery, facts table, file/texture/animation/skeleton summary, and interactive GLB viewer | high | **accepted 2026-08-26** |

## Goal And Objectives

Deliver one reproducible asset-management path from a loose downloaded model
to a browsable, evidence-backed dragon page.

Objectives:

- create identical package topology for BLEND, FBX/archive, and later GLB
  sources without changing original bytes;
- make YAML front matter concise enough to edit by hand and strict enough to
  validate with pydantic;
- extract technical facts with Blender rather than trusting marketplace labels;
- render consistent views and export a browser GLB through a documented CLI;
- generate attractive per-dragon README pages with an image gallery and
  characteristics/provenance tables;
- expose the same normalized facts to Astro through `charctx --json`;
- confine web access to declared selected-project asset paths;
- leave clear extension points for textures, skeleton visualization,
  animations, canonical comparisons, and deformation evidence.

## Scope And Non-Goals

In scope:

- asset-package schema and folder contract;
- safe inspect/organize migration of the three loose candidates;
- README YAML front matter and generated body;
- archive inventory and explicit primary-model selection;
- Blender scene inspection, GLB export, and deterministic preview renders;
- `charctx assets` read/write commands and side-effect-free Python models;
- Astro SSR catalog/detail pages and interactive GLB viewing;
- documentation, offline tests, web checks/build, and browser verification.

Non-goals:

- acquiring more marketplace assets or automating purchases;
- inventing missing source/license claims;
- modifying, repacking, cleaning, or repairing the source files;
- semantic bone-name normalization or selecting the canonical skeleton;
- editing weights, rigs, textures, or materials;
- publishing the catalog to the public internet or exposing it beyond the
  local host by default;
- editing asset metadata from the browser;
- serving BLEND/FBX directly to the browser;
- rendering generated dragons under `generated/` in V1; the first slice is
  reusable collected assets, with generated runs as a later catalog source.

## Proposed Asset Package

Pending the open points, each dragon becomes:

```text
<project>/assets/collected/<asset-id>/
  README.md                    # YAML card + generated human page
  source/                      # original bytes, names, archive structure
  license/                     # supplied license/evidence when available
  inspection/
    report.json                # measured Blender/source facts
    recipe.json                # tool/version/options/input hash
  previews/
    hero.webp
    front.webp
    left.webp
    rear.webp
    top.webp
  web/
    model.glb                  # browser derivative, not canonical production
```

`source/` is immutable. Re-running build may replace only deterministic
derived outputs after validating the current source hash; the report/recipe
records the exact Blender version and render/export settings.

### Proposed README Front Matter

```yaml
---
schema: charctx.asset/v1
id: european-dragon
title: European Dragon
kind: donor
status: collected
provenance_status: incomplete
family: western-dragon
tags: [quadruped, winged, rigged]
source:
  provider: unknown
  asset_id: unknown
  url: unknown
  creator: unknown
license:
  name: unknown
  url: unknown
  local_engineering_use: unknown
  redistribution: unknown
  ai_training: unknown
acquisition:
  method: manual
  date: unknown
primary_file: source/european-dragon.zip
cover: previews/hero.webp
web_model: web/model.glb
---
```

The generated README body contains:

- preview gallery;
- one-glance identity/status/source/license table;
- geometry, mesh-object, material, texture, armature, bone, action, and frame
  facts from `inspection/report.json`;
- original/derived file inventory with byte size and SHA-256;
- warnings such as missing external textures or unverified archive contents;
- a delimited manual-notes block preserved across regeneration.

## Open Points

### OP-001 — Metadata and README authority

Where should card metadata and measured facts live?

- **README front matter only:** matches the requested editing experience, but
  mixes curated claims with large generated inspection detail.
- **Separate `record.yaml` plus generated README:** clean machine contract but
  makes the README's front matter redundant or non-authoritative.
- **Split authority by concern:** README front matter owns curated identity,
  provenance, license, tags, and display paths; inspection JSON owns measured
  facts; the CLI combines both for catalog JSON and README body.

Resolution: split authority by concern. The CLI validates front matter with
pydantic, rejects unknown schema versions, and never overwrites the delimited
manual-notes region. Confidence: high. Status: **accepted 2026-08-26**.

### OP-002 — Safe package migration

How should the existing flat files be reorganized?

- **Move manually:** quick once, but not reproducible and provides no dry-run,
  collision, hash, or rollback evidence.
- **Copy through the CLI:** safest source preservation, but duplicates about
  102 MB and leaves the flat originals requiring later cleanup.
- **`assets organize` with no required arguments:** the mutating verb is the
  confirmation. It repeats a complete preflight, then organizes all eligible
  loose candidates. This is easy to remember and matches the maintainer's
  requested inspect/organize pair.
- **`assets adopt <source> ... --move`:** precise per item, but the flag is
  redundant once the command is already explicitly a mutation and it makes a
  three-item operation unnecessarily repetitive.
- **Fold organization into `assets build`:** fewer commands, but mixes source
  movement with Blender inspection/rendering and makes failures ambiguous.

Proposal: use this pair:

```text
charctx assets inspect              # no write; shows every proposed package/move
charctx assets organize             # no required args; performs those moves
```

`organize` considers only supported loose candidate files directly under the
selected project's `assets/collected/`; it ignores the collection README and
existing package directories. It derives ids from filename stems, validates
the entire batch and every resolved path before any write, refuses a collision
or invalid candidate, creates each package through staging, moves the original
under `source/` without changing its name or bytes, verifies SHA-256 after the
move, writes the initial README, and has no overwrite or force mode. Re-running
with no loose candidates is a successful no-op. Confidence: high. Status:
**open — final maintainer confirmation requested**.

Filename-derived package ids used by the proposed batch command:

- `dragon` for `dragon.blend`;
- `blender-dragon` for `blender_dragon.blend`;
- `european-dragon` for `european-dragon.zip`.

### OP-003 — Missing provenance

Must source and license be known before organization?

- **Wait for complete provenance:** produces cleaner first pages but blocks
  technical inspection and visual comparison.
- **Organize now with incomplete provenance:** preserves facts honestly and
  lets the local tooling work; the catalog makes the missing fields prominent.
- **Assume generic marketplace rights:** expedient but unacceptable because
  provider, asset license, and restrictions are asset-specific.

Resolution (maintainer amendment): this project and viewer are private local
workspace tools, with no publishing surface. Organize and use the models
locally even when provenance is missing. Record `provenance_status: incomplete`,
use explicit `unknown` values rather than omitting fields, and render a clear
warning on cards/pages. Do not infer or claim a license. Confidence: high.
Status: **accepted 2026-08-26 with amendment**.

Maintainer information requested for each candidate when available:

- source URL and marketplace/provider;
- listing title and creator;
- license name/URL or supplied license file;
- acquisition date and whether it was free, purchased, or self-created;
- any known redistribution, AI/training, or usage restrictions.

### OP-004 — Durable preview contract

Which outputs are durable, and how are they generated?

- **Render on every web request:** always fresh but slow, makes browsing depend
  on Blender, and mixes processing with serving.
- **Cache all previews only under repository `.cache/`:** keeps packages small
  but makes the cloud catalog incomplete for collaborators.
- **Durable derivatives beside the asset:** reproducible and cloud-visible;
  costs storage but only a few bounded files per donor.

Resolution: headless Blender produces `web/model.glb`, five 1024-pixel WebP
views (`hero`, `front`, `left`, `rear`, `top`), and inspection/recipe JSON in
the package. Use a neutral studio world, deterministic camera fitting and
lighting, explicit rest/current pose reporting, and no source save. Missing
textures are warnings and remain visibly missing rather than guessed.
Confidence: high. Status: **accepted 2026-08-26**.

### OP-005 — Reusable CLI surface

How much command surface should V1 expose?

- **One `assets build-all` command:** short but hides risky migration and makes
  inspection/render failures hard to isolate.
- **Many one-off scripts:** easy to prototype but violates the single
  documented interface.
- **One cohesive `assets` group:** separates read-only discovery from explicit
  writes while sharing the same contracts.

Resolution:

```text
charctx assets inspect              # loose/package inspection + proposed moves, no write
charctx assets list                 # normalized cards
charctx assets show <id>            # full normalized facts
charctx assets organize             # organize all eligible loose candidates
charctx assets build <id>           # inspect + GLB + renders + README body
charctx assets validate [<id>]      # schema, hashes, paths, derived outputs
charctx web                         # start the only supported web server
```

All commands support `--json` and `--project`; write commands report exact
files. The Python asset catalog/inspection API is read-only, while explicitly
named writer functions back CLI actions. Confidence: high. Status:
**accepted 2026-08-26**; the exact `organize` contract remains OP-002.

### OP-006 — Web architecture and V1 scope

What should be copied from `cad-context`, and what belongs in the first page?

- **Static Astro reading project files directly:** simple deployment, but
  duplicates YAML/report interpretation in TypeScript and cannot safely call
  the maintained CLI.
- **Separate Python API server + frontend:** conventional, but introduces a
  second service and parallel interface without a current need.
- **Astro SSR calling `charctx --json`:** proven locally in `cad-context` and
  preserves the CLI as the single backend contract.

Resolution: add repository `webapp/` using Astro 5, React 19,
`@react-three/fiber`, Drei, and Three.js, following the local `cad-context`
launcher/bridge/confinement pattern. `charctx web` installs dependencies when
needed, binds to `127.0.0.1` by default, snapshots one selected project, routes
logs to `.cache/reports/`, and starts no Python server.

V1 pages:

- collection index with cover image, title, status, formats, rig/animation
  badges, and warnings;
- asset detail with image gallery, interactive GLB orbit/fit/wireframe view,
  provenance/license and characteristics tables, file inventory, texture
  summary, armature/bone/action summary, and build warnings;
- placeholders driven by capability flags for future skeleton overlay,
  animation playback, texture channels, canonical comparison, and deformation
tests—not fake controls over absent data.

The app is private and local-only: it binds to loopback by default, carries no
deployment/publish command, and is not designed to expose the private Google
Drive workspace. Confidence: high. Status: **accepted 2026-08-26**.

## Implementation Phases

### Phase 0 — Final organization-command decision

- Accept or amend the exact no-argument `assets organize` semantics in OP-002.
- Package ids are deterministically derived from the existing filename stems;
  titles are humanized from those ids and remain editable in front matter.
- Source/license information may be supplied whenever available; incomplete
  provenance does not block local organization, processing, or viewing.
- No asset move occurs before this gate.

### Phase 1 — Durable contracts and command skeleton

- Complete the already-created asset-package and web-app specifications with
  OP-002's exact organization-command contract once accepted.
- Keep workspace-layout and agent-interface specs aligned with asset packages,
  `charctx assets`, and `charctx web`.
- Add pydantic models for curated front matter, inspection reports, file
  records, warnings, and normalized catalog cards.
- Add all commands with README usage in the same pass.

### Phase 2 — Read-only inspect, list, show, and validation

- Parse YAML front matter and measured reports only in Python.
- Discover loose candidates and complete packages under the selected project.
- Validate ids, paths, schema versions, hashes, status transitions, and
  confinement.
- Prove JSON/human output with temporary project fixtures.

### Phase 3 — Safe organization of the three candidates

- Run and record `assets inspect`; its output is the exact no-write preview of
  every source, derived id, destination, and collision check.
- Invoke `assets organize` as the explicit write operation; no `--move` flag or
  required item argument exists.
- Organize each file into its package, verify before/after SHA-256, and generate
  front matter with incomplete provenance clearly labelled.
- Update the cloud workspace README/INDEX only for the accepted folder
  contract; item details stay beside the item.

### Phase 4 — Blender inspection, web GLB, and standard views

- Implement a committed Blender script invoked through the provisioned 5.2.1
  binary with auto-execution disabled.
- Inspect scene/mesh/material/image/armature/bone/action facts without saving
  the source.
- Safely inventory archives and extract selected members only into transient
  staging; guard against archive path traversal.
- Export the browser GLB and render the five deterministic views.
- Record source hashes, Blender version, options, output hashes, warnings, and
  timing in inspection/recipe JSON.

### Phase 5 — README and catalog generation

- Generate the README gallery and tables from front matter + inspection JSON.
- Preserve manual notes exactly across rebuilds.
- Make `assets list/show/validate --json` the complete web-facing contract.
- Build all three pages; failures are per-asset and visible rather than hiding
  the rest of the collection.

### Phase 6 — Astro catalog and interactive viewer

- Scaffold `webapp/` from the architectural pattern, not by copying CAD
  concepts or geometry assumptions.
- Implement the CLI bridge, confined asset endpoints, catalog cards, detail
  page, preview gallery, and GLB viewer.
- Preserve source materials/textures in the GLB when available; do not replace
  missing textures with invented assets.
- Add loading, missing-derived-artifact, incomplete-provenance, and
  build-warning states.

### Phase 7 — Proof and handoff

- Run Python unit/integration tests and ruff.
- Run web type/check, unit tests, and production build.
- Start only through `charctx web`; verify index, each asset page, confined
  artifact serving, gallery images, and interactive GLB locally in the browser.
- Record screenshots and commands in `test.md`.
- Hand the verified catalog to the donor-extraction/canonical-skeleton packet.

## Dependencies

- Final maintainer decision on OP-002; all other plan decisions are accepted.
- Maintainer source/license details when available; missing details remain
  clearly labelled and do not block local work.
- Provisioned Blender 5.2.1.
- Node.js 22+ and pnpm/corepack for the Astro application, matching the proven
  local precedent unless implementation evidence requires a revision.
- The selected Google-Drive-synced project must be fully available locally
  during inspection/render/build.

## Risks And Mitigations

- **Original loss during reorganization:** separate read-only `inspect`, exact
  resolved paths, full-batch preflight, staged package creation, before/after
  hashes, no overwrite/force mode.
- **Cloud sync observes partial files:** write derived artifacts to temporary
  names and rename only after successful validation.
- **Missing or absolute texture paths:** report them; search only inside the
  package for exact/controlled matches; never mutate source or silently bind a
  guessed texture.
- **Untrusted BLEND auto-execution:** always use `--disable-autoexec` in
  headless processing.
- **Archive traversal or zip bombs:** validate member paths, counts, and
  expanded sizes before extracting selected members to `.cache/` staging.
- **Rigged marketing claims differ from files:** badges derive only from
  measured armature/weights/actions facts.
- **README/generated fact drift:** one CLI build owns generated sections;
  validation compares input/output hashes and recipe version.
- **Browser path escape or private-data exposure:** bind to loopback, serve only
  declared preview/web files through resolved-path confinement, and never
  expose vendor source archives through the web endpoint.
- **Astro becomes another asset backend:** TypeScript consumes only CLI JSON;
  it does not parse README YAML, inspect Blender files, or infer facts.
- **Large GLB/browser performance:** record GLB size and mesh complexity;
  warn or produce a clearly identified preview derivative without changing the
  source.

## Exit Criteria

- OP-001…OP-006 are accepted or amended in both summary and detail.
- Binding specs define package metadata, immutable sources, derived outputs,
  commands, confinement, and the web-app boundary.
- Each current candidate is in one self-contained folder with valid YAML front
  matter, original-byte hash, README gallery/tables, inspection/recipe JSON,
  five standard WebP views, and a loadable browser GLB—or has a recorded
  per-asset blocking error without corrupting the source.
- Unknown provenance/license fields remain explicit and visibly warn
  `provenance incomplete` without blocking local use.
- `charctx assets inspect/list/show/organize/build/validate` and `charctx web` are
  documented and support `--json`/`--project` consistently.
- The Astro catalog and detail pages obtain facts only from `charctx --json`,
  serve only declared derived files, and do not expose original vendor files.
- Interactive GLB orbit/fit/wireframe viewing works for every successfully
  built asset; missing materials/textures are accurately reported.
- `uv run pytest` and `uv run ruff check .` pass.
- Web check, tests, production build, and a CLI-started local browser smoke
  test pass and are recorded in `test.md`.

## Implementation Gate

Implementation should begin after the maintainer accepts or amends OP-002's
exact no-argument `charctx assets organize` behavior. OP-001 and OP-003…OP-006
are accepted. Until OP-002 is settled, the three source files remain untouched
in the cloud workspace.
