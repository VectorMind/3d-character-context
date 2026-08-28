# Riyu Reference Turnaround

## Problem Summary

Five mixed-angle reference images of the same juvenile dragon need to become
a clean, high-resolution view set suitable for image-to-3D experiments and a
private catalog report. The supplied files currently sit loose inside a
collected package.

## Resolution Summary

| OP | Topic | Accepted resolution | Confidence | Status |
| --- | --- | --- | --- | --- |
| OP-001 | View set | Generate front, left, rear, top, and front three-quarter views in one neutral standing pose; one profile is sufficient. | high | accepted 2026-08-28 |
| OP-002 | Storage | Preserve supplied bytes under package `source/`; keep high-resolution PNGs under `inputs/turnarounds/ninjago-riyu/` and WebP catalog derivatives under package `previews/`. | high | accepted 2026-08-28 |
| OP-003 | Catalog semantics | Add an explicit image-reference package kind that validates five previews and is never sent through the Blender donor build. | high | accepted 2026-08-28 |

## Goal And Objectives

- Produce a coherent five-view, high-resolution image set without spending
  hosted 3D-generation quota.
- Preserve every supplied reference byte and record its hash and role.
- Add a valid `charctx.asset/v1` YAML card and image report for the private
  catalog.

## Scope

- Reference-guided raster generation and deterministic WebP resizing.
- Image-only collected package metadata and preprocessing provenance.
- Explicit CLI and private-viewer handling for reference-image packages.

## Non-Goals

- Running TRELLIS or creating a 3D mesh.
- Claiming geometric registration, canonical topology, rigging, or measured
  mesh facts.
- Guessing source URLs, creators, licenses, or redistribution rights.
- Changing the five standard Blender build outputs.

## Implementation Phases

1. Inspect source images and current package/catalog contracts.
2. Generate and visually inspect the six-view set.
3. Preserve sources, copy high-resolution inputs, and make WebP previews.
4. Add the YAML card and preprocessing record.
5. Run package, CLI, test, lint, and web checks.

## Dependencies And Risks

- Reference-guided image generation is non-deterministic and may introduce
  small cross-view design differences; the report must label the result as an
  AI-synthesized reference set rather than geometry ground truth.
- Provenance and license facts are missing; the package remains explicitly
  incomplete and private-workspace-only.
- The hosted 3D backend is metered and remains out of scope for this packet.

## Exit Criteria

- Five readable high-resolution PNGs and five catalog WebPs exist with recorded
  dimensions and hashes.
- Supplied source hashes are unchanged after packaging.
- The catalog card lists all five standard previews without exposing source
  files.
- `uv run pytest`, `uv run ruff check .`, and relevant web checks pass.
