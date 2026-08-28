# Implementation — Dragon Asset Catalog And Web Viewer

## Progress

`■■■■■■ Done`
Asset organization, inspection, previews, validation, CLI, and private catalog
are implemented and proven.

## Landed

- Added pydantic contracts for README front matter, measured inspection facts,
  files, and normalized catalog cards.
- Added `charctx assets inspect/list/show/organize/build/validate` with the
  accepted read/write split, full-batch collision preflight, staged package
  creation, source hash verification, guarded recursive ZIP extraction, and
  package validation.
- Organized the three loose downloads into `blender-dragon`, `dragon`, and
  `european-dragon` packages without changing their original hashes.
- Added a Blender 5.2 headless build that disables auto-execution, measures
  geometry/rig/action/material data, exports GLB, and renders five neutral
  inspection views. Render energy scales with asset bounds so arbitrary source
  units remain visible.
- Added generated README cards with YAML front matter, galleries, measured
  tables, inventories, warnings, and preserved manual-notes regions.
- Added the Astro SSR/React/Three.js Dragon Atlas and `charctx web` launcher.
  The viewer supports orbit, measured fit, neutral/source material switching
  when source materials are complete, and wireframe display; animation clips
  are summarized but playback remains a future capability.
- Restricted the artifact route to the CLI-declared preview/GLB allowlist with
  real-path confinement; source asset requests return 404.
- Cleared Blender's factory-startup objects before importing non-BLEND donors.
  This prevents the default cube from leaking into imported inspection meshes
  and model-derived previews.
- Extended reference packages into unified character records. Their declared
  generation request names now resolve append-only run manifests, measured
  facts, inputs, raw GLBs, regenerated views, and stage states through
  `assets show`; generated models are no longer copied into duplicate donor
  packages.
- Added `charctx generations build` and automatic post-generation view builds.
  Each run gets a parseable `viewer.json` plus five neutral previews, while a
  before/after SHA-256 check protects the provider model.
- Extended the private web detail page with per-generation sections and a
  confined generated-artifact route. Reference inputs, raw interactive model,
  measurements, request data, regenerated views, and explicit future stages
  now share one character URL.

## Deviations And Findings

- The two BLEND packages reference absent external textures. The FBX package
  includes texture images in its archive but retains absolute author-machine
  links. V1 does not guess bindings, so all are reported prominently.
- Preview renders use a neutral override material for reliable geometry review;
  GLB export occurs first and retains source materials and available textures.
- Blender 5.2 exposes different color-look enum spellings depending on the
  source file's saved color configuration. The builder selects the first
  supported deterministic contrast look.
- The in-app browser runtime was unavailable, so the documented Chrome-control
  fallback was used. It exposed and drove fixes for incorrect detail-table
  keys and invisible rigged meshes with incomplete materials, then verified the
  final catalog, visible GLB inspection mesh, and wireframe interaction.
- The plan originally deferred generated-run rendering from V1. On 2026-08-28
  the maintainer explicitly expanded the existing viewer scope. The durable
  package, workspace, web, and CLI specifications were updated in the same
  pass; no unresolved architectural choice required a new plan packet.

## External Data Changes

All changes are under the selected private project at
`assets/collected/`. Original downloads now live under each package's
`source/`; derived reports, recipes, previews, GLBs, and README cards are
co-located in their specified directories.

On 2026-08-28 the temporary duplicate donor package
`ninjago-riyu-generated-001` was retired after its useful viewer derivatives
were regenerated beside the authoritative append-only run. The reference
record `ninjago-riyu` now links that run natively. The original GLB remained
unchanged at SHA-256
`ffeedea52006706e3e1eda4d9034386c90581896441b14220f9cfec3b9fac12c`.
