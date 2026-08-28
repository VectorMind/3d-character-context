# Implementation — Riyu Reference Turnaround

## Progress

`■■■■■ Done`
Five reference views, package report, catalog semantics, and runtime proof are complete.

## Data Workspace Changes

- Moved the five supplied files into
  `assets/collected/ninjago-riyu/source/` without changing their SHA-256
  values.
- Created five high-resolution PNG run inputs under
  `inputs/turnarounds/ninjago-riyu/`: front three-quarter, front, left, rear,
  and top.
- Created the standard five WebP catalog previews under the package's
  `previews/` directory.
- Replaced the initial top view with a targeted correction based on the
  maintainer-supplied dorsal-head crop. The final head uses broad stacked
  transverse armor plates.
- Removed the generated right view from the project deliverables after the
  maintainer confirmed that left and right profiles were redundant. The
  discarded variant remains recoverable under `.cache/scratch/` and in the
  built-in image generator's retained output folder.
- Added the package-level `README.md` with a valid YAML card, five-view
  gallery, recommended generator input, preprocessing notes, dimensions,
  hashes, source roles, provenance limits, and manual-notes block.

## Repository Changes

- Added `kind: reference` to collected-asset front matter and normalized
  cards.
- Made no-id donor builds skip image-reference packages and explicit reference
  builds fail with a clear bounded message.
- Added reference-package validation for the primary source and five standard
  previews without requiring a Blender inspection report or GLB.
- Updated CLI text and the private Astro catalog to present view/source facts
  instead of fake mesh, rig, action, or build states for reference packages.
- Folded the durable behavior into the asset-package and web-app
  specifications and documented donor-build behavior in the command README.
- Added an offline reference-package test.

## Deviations And Limits

- The first generation pass produced both left and right profiles. The final
  set deliberately retains only the standard left profile per maintainer
  feedback.
- The images are consistent visual references, not geometrically registered
  projections or measurement evidence.
- Provider, creator, URL, license, redistribution, and AI-related rights remain
  unknown and visibly incomplete.
- No TRELLIS or other hosted 3D generation was run.

## Commands Performed

- `uv run charctx assets show ninjago-riyu --json`
- `uv run charctx assets validate ninjago-riyu --json`
- `uv run pytest`
- `uv run ruff check .`
- `pnpm check`
- `pnpm build`
- `uv run charctx web --no-install --port 4331`
