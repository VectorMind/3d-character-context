# Implementation — Donor Skeleton Extraction And Viewer

## Progress

`▰▰▰▰▰▰ Phase 6/6` — extraction, viewer, package rebuilds, and the Riyu
suitability assessment are complete. One gap remains: the interactive browser
click-smoke, recorded in `test.md`.

## 2026-08-28 — Extraction Contract

- Opened the packet after the maintainer requested faithful extraction and
  browser inspection before any skeleton creation work.
- Settled separate `charctx.skeleton/v1` and `charctx.skin-weights/v1` JSON
  artifacts, dual coordinate spaces, declared web serving, and strict
  non-goals around normalization, interpolation, and canonical design.
- Folded the durable artifact, CLI, and viewer behavior into the binding specs
  and documented `charctx assets build` as the explicit production command.

## 2026-08-28 — Phases 2 And 3: Extraction And Viewer

Landed in commit `56867b4`:

- `blender/build_asset.py` gained `extract_skeleton` and `extract_skin_weights`,
  emitting armature-local rest data plus `[x, z, -y]` viewer coordinates and
  CSR-style sparse per-vertex influences.
- `asset_models.py` gained `SkeletonBone`/`SkeletonArmature`/`SkeletonDocument`
  and the skin-weight models with hierarchy validation; `assets.py` validates
  both derivatives, records hash/size/schema/summary in the inspection and
  recipe authorities, and rejects a measured armature with no extraction.
- `cli.py` publishes the declared paths and a `skeleton extracted` badge.
- The web boundary added `inspection/skeleton.json` to the artifact allowlist;
  `ModelViewer.tsx` gained `SkeletonOverlay`, a visibility toggle, and an x-ray
  model mode, all inside the existing shared `fitTransform` group.

## 2026-08-28 — Phases 4–6: Rebuild, Inspection, Assessment

- Rebuilt `dragon` and `european-dragon`, the two donors still carrying
  pre-extraction packages. `blender-dragon` was already current. All three
  packages now hold `inspection/skeleton.json` and `inspection/skin-weights.json`
  and pass `charctx assets validate`.
- Verified source bytes unchanged against the 2026-08-26 baseline hashes; the
  build's own source-hash guard is what permitted the rebuilds.
- Proved overlay alignment numerically rather than visually, replicating the
  viewer's `fitTransform` and testing every bone endpoint against the
  independently measured GLB box: 100% / 98.7% / 92.6% containment, with all
  misses accounted for as control geometry outside the skin.
- Recorded the evidence-backed donor-to-Riyu assessment in `test.md`:
  `european-dragon` is the only structurally complete and cleanly skinned donor;
  `dragon` is a mixed control/deform bird-dragon rig with un-normalized weights;
  `blender-dragon` is an unfinished metarig whose wing and tail chains carry no
  weight at all.

### Decisions And Findings

- **`deform` is not a usable discriminator on this corpus.** All three donors
  flag every bone `use_deform`, including 57 `ORG-` and 5 `MCH-` Rigify
  scaffolding bones in `dragon`. The analysis therefore derives the effective
  deform set empirically from the extracted sparse weights. The overlay still
  colors by the source flag, per OP-004 — surfacing the empirical set is
  skeleton-semantics work this packet excludes, and is logged as a gap.
- **The 2026-08-26 european-dragon count discrepancy is resolved, not open.**
  Today's build measures 8 vertices / 6 polygons fewer than that record —
  exactly one cube. Commit `2da4031` added the default-scene purge to
  `import_source`, so pre-`2da4031` FBX builds measured and exported Blender's
  `--factory-startup` default Cube. Two consecutive rebuilds today are
  identical; the FBX path is deterministic.
- **Skin weights stay off the web boundary** (404), as the web-app spec
  requires. They are catalog metadata, not a browser artifact.

### Deviations

- The interactive Chrome click-smoke used by earlier packets could not run:
  this session had no browser-control runtime. Substituted route-level,
  SSR-prop, and geometric-alignment evidence, and left the visual toggle
  check recorded as an open gap rather than claiming it passed.

### Commands Performed

```powershell
charctx assets build dragon
charctx assets build european-dragon     # run twice, for a determinism check
charctx assets validate
charctx assets list / show <donor>
charctx report <package>\web\model.glb --no-write   # all three donors
charctx web                              # loopback route and confinement checks
uv run pytest ; uv run ruff check .
pnpm check ; pnpm build                  # in webapp/
```

Analysis scripts are throwaway and live in `.cache/scratch/`:
`skeleton_compare.py` (region and weight-bearing comparison) and
`overlay_alignment.py` (viewer-transform containment proof).

No source code changed in this pass; the packet's remaining work was
production, measurement, and assessment.
