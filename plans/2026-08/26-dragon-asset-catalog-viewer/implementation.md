# Implementation — Dragon Asset Catalog And Web Viewer

Progress: `[####################] 100%`

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
  This prevented the default cube from leaking into the promoted
  `ninjago-riyu-generated-001` inspection, previews, and browser GLB while
  preserving the copied generated GLB byte-for-byte under `source/`.

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

## External Data Changes

All changes are under the selected private project at
`assets/collected/`. Original downloads now live under each package's
`source/`; derived reports, recipes, previews, GLBs, and README cards are
co-located in their specified directories.

On 2026-08-28 the append-only generated run `trellis2/ninjago-riyu-001` was
copied into the separate donor package `ninjago-riyu-generated-001`. The
generated run remains unchanged and authoritative; its GLB and the package
source copy share SHA-256
`ffeedea52006706e3e1eda4d9034386c90581896441b14220f9cfec3b9fac12c`.
