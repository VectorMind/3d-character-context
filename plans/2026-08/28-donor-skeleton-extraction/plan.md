# Plan — Donor Skeleton Extraction And Viewer

Date: 2026-08-28  
Status: Complete — faithful donor preprocessing only; no canonical skeleton
design or per-character rigging

## Problem Summary

Three collected western-dragon donors contain armatures and skin weights, but
the current build records only counts and bone names. Their hierarchy, rest
geometry, transforms, and exact mesh bindings remain trapped inside BLEND/FBX
sources. The private viewer reports that a rig exists but cannot display it.

Before designing `western_dragon_v1`, the donor rigs need reproducible,
Blender-independent extraction and an as-is visual comparison surface. The
generated `ninjago-riyu-001` mesh is the target body-plan reference, but this
packet must not create, normalize, merge, retarget, or fit a skeleton.

## Resolution Summary

| OP | Topic | Resolution | Confidence | Status |
| --- | --- | --- | --- | --- |
| OP-001 | Extracted format | Write versioned JSON derivatives: `inspection/skeleton.json` for armatures and `inspection/skin-weights.json` for exact sparse bindings | high | **accepted 2026-08-28** |
| OP-002 | Coordinate spaces | Preserve Blender armature-local rest data and add world-to-glTF `[x, z, -y]` viewer coordinates without normalizing scale | high | **accepted 2026-08-28** |
| OP-003 | Viewer representation | Fetch the declared skeleton artifact through the confined asset route and render an independently toggleable rest-pose overlay with shared model fitting | high | **accepted 2026-08-28** |
| OP-004 | Semantic handling | Preserve source names and hierarchy exactly; lexical name counts are descriptive signals only, not semantic normalization | high | **accepted 2026-08-28** |
| OP-005 | Riyu assessment | Compare donor anatomy, articulation density, wing/tail/neck coverage, rest pose, and adaptation burden; do not claim interpolation or reuse without canonical correspondence | high | **accepted 2026-08-28** |

## Goal

Make every currently collected donor skeleton inspectable as validated data and
visible over its browser model, then produce an evidence-backed suitability
assessment against Riyu without performing skeleton creation work.

## Scope

- Extract every armature, source bone name, parent, deform/connect flags, rest
  head/tail, roll, local matrix, root/leaf/depth facts, and bounds.
- Extract exact sparse per-vertex bone influences for every armature-bound mesh.
- Record hashes, sizes, schemas, summaries, and reproducibility metadata in the
  existing inspection/recipe authorities.
- Expose declared skeleton capability through `charctx assets list/show`.
- Validate extraction artifacts and reject missing, changed, or malformed data.
- Add a skeleton overlay, visibility control, x-ray model mode, and existing
  orbit/pan/zoom interaction to the private viewer.
- Rebuild all three donor packages and compare them with `ninjago-riyu-001`.

## Non-Goals

- Selecting or creating the canonical western-dragon skeleton.
- Renaming bones into canonical semantics.
- Editing donor skeletons, weights, rest poses, meshes, or animations.
- Rigging or skinning Riyu.
- Retargeting animation or synthesizing controls.
- Treating name-based signals as anatomical proof.
- Combining donor skeletons or claiming that raw bone interpolation is valid.

## Phases

1. Specify extracted skeleton and skin-binding artifacts.
2. Implement Blender extraction and Python validation/catalog integration.
3. Add the declared skeleton artifact to the private web boundary and viewer.
4. Rebuild and validate all donor packages.
5. Inspect the overlays and assess donor-to-Riyu suitability.
6. Record proof and close the packet.

## Risks

- BLEND and imported FBX coordinate systems differ; dual-space output and shared
  viewer fitting must make the conversion explicit.
- Control and deform rigs may be mixed; extraction preserves `deform` flags and
  never assumes every bone is a production influence.
- A mesh may contain non-bone vertex groups; sparse bindings include only groups
  matching the bound armature and count excluded assignments.
- Bone names can suggest anatomy but do not prove it; the assessment must combine
  hierarchy facts with visual evidence.
- Unknown provenance limits all donor use to the private engineering workspace.

## Exit Criteria

- All three donors have schema-valid skeleton and skin-weight JSON derivatives.
- Original source hashes remain unchanged.
- CLI JSON declares skeleton paths and measured summaries.
- The local viewer displays each extracted rest skeleton aligned with its mesh
  and supports orbit, pan, zoom, skeleton visibility, and x-ray inspection.
- Repository tests, Ruff, Astro check/build, asset validation, and browser smoke
  checks pass.
- `test.md` records a bounded Riyu suitability assessment and remaining gaps.
