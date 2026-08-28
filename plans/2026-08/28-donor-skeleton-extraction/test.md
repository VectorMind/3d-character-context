# Test Proof — Donor Skeleton Extraction And Viewer

## Status

Implemented and proven, with one recorded gap: the interactive Chrome
click-smoke could not run in this session (no browser-control runtime was
available). Overlay alignment is proven numerically instead, which is the
measurement-based evidence `AGENTS.md` requires; the visual click-through of
the two toggles remains unverified.

## Fixtures

- `blender-dragon` — `source/blender_dragon.blend`
- `dragon` — `source/dragon.blend`
- `european-dragon` — `source/european-dragon.zip` → nested
  `Dragon_GameReady_Rig_&_Animations/…/SKM_Dragon_animations.fbx`
- generated target reference `trellis2/ninjago-riyu-001`

## Commands And Results

| Command / check | Expected | Actual |
| --- | --- | --- |
| `charctx assets build dragon` | Skeleton and skin-weight derivatives written | **Pass:** exit 0; `inspection/skeleton.json` + `inspection/skin-weights.json` produced; only pre-existing missing-texture warnings |
| `charctx assets build european-dragon` | Same, through the nested-archive/FBX path | **Pass:** exit 0; both derivatives produced |
| `charctx assets validate` | All packages schema/hash valid | **Pass:** `asset validation: pass`; all four assets `valid` |
| `charctx assets list` | Donors declare skeleton capability | **Pass:** all three donors report `skeleton extracted` |
| `charctx assets show <donor>` | Declared skeleton/weights paths | **Pass:** `skeleton: inspection/skeleton.json`, `weights: inspection/skin-weights.json` for all three |
| `charctx report <web/model.glb> --no-write` ×3 | Every rebuilt GLB reloads, finite, non-degenerate | **Pass:** 43,643/21,998 · 29,729/48,112 · 24,140/42,338 vertices/faces; `degenerate: 0`, `finite: True`, `plausible: True` |
| `uv run pytest` | Offline suite green | **Pass:** 83 passed, 1 live test skipped |
| `uv run ruff check .` | Lint clean | **Pass:** `All checks passed!` |
| `pnpm check` | Zero diagnostics | **Pass:** 10 files, 0 errors / 0 warnings / 0 hints |
| `pnpm build` | SSR + client build | **Pass:** Astro server and `ModelViewer` client chunk built |

### Source Bytes Unchanged

Rebuilding did not touch source bytes. Recorded recipe hash, on-disk hash, and
the 2026-08-26 baseline all agree:

- `blender_dragon.blend` — `13a4a92ed36c3922fa6cca8c2ed467209d53681d9d8b31752e5a17428cfe7ed3`
- `dragon.blend` — `6cb566aa82d9d7eb833aa7841019a49006aeae9a84ae385643268e959c7c92b3`
- `european-dragon.zip` — `8f464c74ea5a100ec8fdbd9d2456842f9880f80780af5182778be53bdab5d0d4`

### Web Boundary (`charctx web`, loopback :4321)

| Request | Expected | Actual |
| --- | --- | --- |
| `GET /assets/<donor>` ×3 | 200 detail page | **200** for all three |
| `GET /api/artifact/<donor>/inspection/skeleton.json` ×3 | 200 `application/json` | **200**, 58,123 / 292,232 / 251,932 bytes |
| `GET /api/artifact/<donor>/web/model.glb` ×3 | 200 GLB | **200**, 2,415,200 / 2,569,024 / 4,527,140 bytes |
| `GET /api/artifact/<donor>/inspection/skin-weights.json` | 404 — catalog metadata, not a browser artifact | **404** for all three |
| `GET /api/artifact/<donor>/source/<file>` | 404 — source boundary | **404** for all three |
| `GET /api/artifact/<donor>/../../../.env` | 404 — traversal rejected | **404** for all three |
| SSR island props | Declared skeleton URL reaches the viewer | **Pass:** `"skeletonUrl":[0,"/api/artifact/european-dragon/inspection/skeleton.json"]` beside `url`, `boundsMin`, `boundsMax` |

### Overlay Alignment (measured, not visual)

The viewer places the model and the overlay inside one `<group>` carrying a
single `fitTransform(boundsMin, boundsMax)` derived from the GLB measurement,
so alignment reduces to whether extracted viewer coordinates share the GLB's
space and scale. `.cache/scratch/overlay_alignment.py` replicates that
transform and tests every bone endpoint against the measured GLB box:

| Donor | Endpoints inside the measured GLB box | Fitted skeleton half-extent (mesh fits in 1.35) |
| --- | --- | --- |
| `european-dragon` | **336/336 (100.0%)** | `[0.75, 0.72, 1.35]` |
| `blender-dragon` | **75/76 (98.7%)** | `[0.31, 0.88, 1.37]` |
| `dragon` | **363/392 (92.6%)** | `[0.55, 0.21, 0.72]` |

The three misses are explained and are not coordinate errors:

- `blender-dragon`: one endpoint, the `head` bone tip, sits 0.07 units past the
  snout.
- `dragon`: 29 endpoints belong to the Rigify `root` control widget
  (`z = -8.10`, behind the body) and to `ORG-foot/toe` bones a few hundredths
  below the mesh's ground plane — control geometry that is deliberately outside
  the skin.

The `[x, z, -y]` conversion is therefore confirmed against independently
measured glTF geometry on all three donors.

### Build Reproducibility

Two consecutive `charctx assets build european-dragon` runs produced identical
measured counts (21,228 vertices / 21,262 polygons in Blender; 24,140 / 42,338
in the GLB), so the FBX path is deterministic today.

These differ from the 2026-08-26 record (21,236 / 21,268 and 24,164 / 42,350)
by exactly 8 vertices and 6 polygons — one cube. The cause is identified, not
outstanding: commit `2da4031` added the default-scene purge at the top of
`import_source`, so pre-`2da4031` FBX builds measured and exported Blender's
`--factory-startup` default Cube along with the donor. Today's numbers are the
corrected ones.

## Extracted Skeleton Facts

Measured from `inspection/skeleton.json` and `inspection/skin-weights.json` via
`.cache/scratch/skeleton_compare.py`. "Weight-bearing" counts bones that
actually receive a non-zero vertex influence, which is stronger evidence than
the `deform` flag — all three donors flag 100% of bones `use_deform`, so that
flag discriminates nothing here.

| Fact | `blender-dragon` | `dragon` | `european-dragon` |
| --- | --- | --- | --- |
| Armature | `metarig` | `rig.001` | `Root` |
| Bones | 38 | 196 | 168 |
| Roots / leaves / max depth | 2 / 10 / 8 | 2 / 45 / 15 | **1 / 65 / 17** |
| Name prefixes | 38 plain | 127 `DEF-`, 57 `ORG-`, 5 `MCH-`, 7 plain | **168 `DEF-`** |
| Weight-bearing bones | 29/38 (76%) | 114/196 (58%) | **164/168 (98%)** |
| Mesh bindings | 1 | 67 | 5 |
| Unweighted vertices | 0 | 4 | 0 |
| Max influences / vertex | 7 | 8 | 11 |
| Max weight-sum error | 0.109 | **4.838** | 0.185 |

Region coverage (bones / of which weight-bearing):

| Region | `blender-dragon` | `dragon` | `european-dragon` |
| --- | --- | --- | --- |
| Spine | 8 / 3 | 19 / 4 | 6 / 6 |
| Neck | 5 / 1 | 4 / 2 | 5 / 5 |
| Head, jaw, beak, teeth | 1 / 1 | 12 / 7 | 2 / 2 |
| Tail | **0 / 0** | 6 / 6 | 17 / 17 |
| Wing | **0 / 0** | 24 / 14 | 30 / 30 |
| Foreleg / shoulder | 0 / 0 | 4 / 2 | 14 / 14 |
| Hindleg / pelvis | 30 / 25 | 52 / 26 | 16 / 16 |
| Digits, palms | 0 / 0 | 46 / 38 | 54 / 54 |
| Eyes, lids | 0 / 0 | 4 / 2 | 22 / 18 |
| Feathers | 0 / 0 | 20 / 10 | 0 / 0 |

## Riyu Suitability Assessment

### Target body plan

Read from the generated `trellis2/ninjago-riyu-001` mesh previews and the
five-view reference package: a compact, grounded quadruped with four clawed
legs, two **membranous, unfeathered** wings rooted at the shoulders, a long
ridged tail, a short thick neck, and a large head. No independent arms/hands —
the forelimbs are paws.

This is a body-plan reading from geometry and reference images. Riyu has no
skeleton; nothing below is a claim about correspondence between donor bones and
Riyu anatomy.

### `european-dragon` — usable, and the only structurally complete donor

It is the sole donor whose hierarchy covers every region Riyu needs: 6 spine,
5 neck, 17 tail, 30 wing, and 4 limbs with digits, all weight-bearing. It is
also the only clean one — a single root, 168 pure `DEF-` bones with no control
or mechanism clutter, 98% weight-bearing, zero unweighted vertices, and
near-normalized weights (max sum error 0.185). Its overlay is the one that sits
100% inside its own mesh.

Adaptation burden, measured not guessed:

- **Rest pose is the blocking cost.** The rest pose is a rearing, vertically
  curled flight pose with draped wings and a coiled tail (see
  `previews/left.webp`), against Riyu's grounded four-point stance. The
  rest-pose delta, not the bone list, is the real work.
- **Over-articulated for the target**: 54 digit/palm bones and 22 eye/lid bones
  exceed anything Riyu's geometry can resolve.
- 11 influences per vertex exceeds the 4-influence limit of most runtime
  skinning paths and would need reduction on export.

### `dragon` — partially usable, not as a rig donor

It has wings, tail, and digits, but four measured facts rule it out as the
structural basis:

1. **Mixed control and deform rig.** 57 `ORG-` and 5 `MCH-` bones are Rigify
   scaffolding, yet all 196 bones are flagged `use_deform`; only 114 carry any
   weight. The flag cannot be trusted to separate them, so the deform set has
   to be recovered empirically.
2. **Wrong body plan.** 20 feather bones, a beak (`ORG-beak_001.B`,
   `DEF-beak.001.T`…), and tongue bones describe a feathered, beaked
   bird-dragon. Riyu has membranous wings and a muzzle. The hindleg group also
   carries two full `thigh/shin/foot/toe` pairs per side.
3. **Weights are not normalized.** Max weight-sum error 4.838 — some vertices
   carry roughly 5.8× total influence — plus 4 unweighted vertices.
4. **67 separate mesh bindings** against Riyu's single generated surface.

Useful only as a reference for wing-fold articulation, after stripping
`ORG-`/`MCH-` and renormalizing.

### `blender-dragon` — not usable as a rig donor

Its mesh has full wings and a long spiked tail; its armature rigs neither.

- **Zero wing bones.** The wing mesh is bound rigidly to `chest`, which carries
  the second-largest weight mass in the rig (2,430).
- **The tail chain is dead.** `hips.001…hips.005` follows the tail
  geometrically — head `[-0.04, 2.22, -1.23]` running back and down to tail
  `[0.10, 0.59, -5.26]`, against a mesh reaching `z = -5.87` — but every bone in
  the chain carries **weight mass 0**.
- `neck.001…neck.004` are likewise weightless; a single `neck` bone deforms the
  whole neck.
- Effective rig: head, one neck bone, chest, hips, and four legs. The 38-bone
  count overstates it; 9 bones are inert.

This is an unfinished Rigify metarig, not a skinned rig.

### Recommendation

Take `european-dragon`'s hierarchy as the structural reference when
`western_dragon_v1` is designed, and treat its rest pose as the primary
adaptation cost. Keep `blender-dragon` as a mesh/silhouette reference only.
Mine `dragon` for wing articulation ideas, nothing more.

Explicitly **not** claimed: that any donor can be retargeted to Riyu as-is,
that bone names prove anatomy, or that donor skeletons can be interpolated or
merged. No canonical correspondence exists yet, so no such operation is
defensible.

## Known Gaps

- The interactive browser smoke (clicking `Show skeleton` / `X-ray model` and
  confirming the drawn overlay) did not run: no browser-control runtime was
  available in this session. Route, prop, and geometric-alignment evidence is
  recorded above in its place.
- The overlay colors bones by the source `deform` flag, which all three donors
  set on every bone, so the deform/control distinction is invisible in the
  browser. The empirical weight-bearing set exists in the extracted data but is
  not surfaced. Deliberate: OP-004 binds the overlay to source facts, and
  changing it is skeleton-semantics work this packet excludes.
- Provider, creator, and license provenance remains unknown for all three
  donors; use stays confined to the private local workspace.
- Riyu itself remains unrigged. Nothing here fits, retargets, or skins it.
