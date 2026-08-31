# Plan — Riyu Skeleton Fit And Rig Visualization

Date: 2026-08-29
Status: Rough plan, stepwise — each step is proven by looking at it before the
next one starts

## Framing

This packet is deliberately independent of the
[2026-08-25 rigging handoff](../25-rigging/dragon_blender_rigging_handoff.md).
That document routes all rigging through a canonical mesh that does not exist
and has no source, which means designing `western_dragon_v1` before ever
watching a skeleton land on a generated mesh. This packet inverts that: fit
first, look at it, and let the evidence inform any canonical design later.

Being explicit about the trade so it is not discovered later: **this track is
per-character and produces no reusability yet.** Fitting Riyu does not make the
next dragon cheaper. What it produces instead is a landmark contract, a fitted
skeleton in the existing schema, rig-influence instrumentation, and a distance
heuristic with a measured error — the inputs any canonical design would need
anyway.

There are no open points. Scope questions are settled by building the smallest
version, looking at the result, and deciding from what we see.

## Assets In Play

- `ninjago-riyu-001` — the target. TRELLIS.2 output: 203,745 vertices, 289,479
  faces, **6,209 connected components**, not watertight, 1 degenerate face.
  Extents 1.0019 × 0.4442 × 0.9963 (x wingspan, y up, z length). Bilaterally
  symmetric and axis-aligned. No skeleton.
- `european-dragon` — the donor and the validation set. 168 bones, single root,
  164 weight-bearing, zero unweighted vertices, max weight-sum error 0.185,
  hand-authored weights. Rest pose is rearing and curled.
- `dragon`, `blender-dragon` — negative references only. Neither is a usable
  rig donor (see the [donor extraction
  assessment](../28-donor-skeleton-extraction/test.md)).

## Constraints The Target Mesh Imposes

Riyu's 6,209 components are load-bearing on method selection:

- **No algorithm may depend on source connectivity.** Geodesic distance,
  connected-component walks, and surface parameterization on the generated mesh
  are all out.
- Closest-point projection, ICP, cage/embedded deformation, ray casting, and
  depth rendering are all fine — none of them care that the target is shell
  soup.
- Blender's bone-heat weighting is not merely risky here, it is non-viable:
  heat diffuses across connected surface, and most of Riyu's shells are
  unreachable from any bone.

## Steps

Each step ends with something visible. Nothing proceeds on a step whose picture
has not been looked at.

### Step 1 — Crude rigid transfer, visible immediately

Scale and translate european-dragon's skeleton into Riyu's bounding box and
emit it as `charctx.skeleton/v1`.

It will be wrong. That is the point — the existing viewer overlay renders
`charctx.skeleton/v1` with **zero new code**, so this buys the first picture at
almost no cost, and the specific way it looks wrong (proportions, pose,
chain lengths) is what directs step 3.

*Proof:* the Riyu page shows a skeleton overlay. Bone count matches the donor.

### Step 2 — Landmarks

Define `charctx.landmarks/v1`: named 3D points in viewer space with side
(`L`/`R`/`center`), source (`geometric`/`assisted`/`manual`), and confidence.

Produce Riyu's landmarks by the layered strategy:

1. **Geometric proposal** — symmetry plane, medial axis from cross-sections
   along z, farthest-point extremity detection. Deterministic, no external
   calls. Expected to nail the spine/neck/tail chains and extremity positions.
2. **Semantic labelling** — geometry finds extremities but cannot tell a wing
   tip from a foot. Resolve naming from the five existing Blender renders,
   which come from cameras we control; render a depth/position pass alongside
   them so a 2D pixel back-projects to an exact 3D surface point, with no
   cross-view triangulation and no correspondence ambiguity.
3. **Manual correction** — final authority. Corrections are recorded, since the
   delta between proposal and correction is the learning signal for later
   automation.

`landmarks.json` is the contract. However the points are produced, the file is
the interface and nothing downstream knows the difference.

*Proof:* schema validates; every point lies inside the mesh bounds; bilateral
pairs mirror across x within tolerance.

### Step 3 — Landmark-driven per-chain fit

Place each chain — spine, neck, tail, both wings, four legs — from its own
landmarks, inheriting **hierarchy and proportion** from the donor while taking
every joint position from Riyu. Intermediate joints in subdivided chains
(spine, neck, tail) interpolate along fitted curves.

Because positions come from Riyu, the donor's rearing rest pose never enters
the math. This is why the pose problem does not block skeleton fitting, only
weight transfer later.

Output is again `charctx.skeleton/v1`, so it renders in the existing viewer.
**This is the step that delivers "the same skeleton on the new mesh."**

*Proof:* side-by-side with step 1 in the viewer; bone endpoints inside the mesh
bounds; left/right symmetry within tolerance.

### Step 4 — Semantic bone naming

Map donor names to semantics as part of the fitted output: european-dragon's
`DEF-Bone` → `DEF-Bone.002` → `DEF-Teeth_Bottom` chain is a real jaw, and
`DEF-neck.004` is the skull, not a neck segment. The fitted skeleton should
carry `jaw`, `head`, `wing_elbow.L` and so on rather than inherited noise.

*Proof:* every semantic bone required by a western dragon body plan is present;
the mapping is recorded as data.

### Step 5 — Rig influence visualization, on the donor first

Per-vertex coloring by **number of influencing bones**, plus per-bone influence
and weight-sum error.

Built against european-dragon before Riyu, because its weights are hand-authored
and correct — so the visualization is validated against known-good data instead
of being debugged against an unknown.

Transport: bake the diagnostic as **vertex colors into a derived GLB**. No new
browser parsing, no raw weight exposure, no conflict with the web-app spec's
rule that skin weights are catalog metadata rather than a browser artifact.
Riyu's raw weights at 203,745 vertices would be tens of megabytes; the baked
GLB stays small.

*Proof:* european-dragon's influence map renders in the viewer and visibly
matches its known weight structure — 11 influences maximum, dense at the wing
membrane, zero unweighted vertices.

### Step 6 — Distance heuristic, scored not guessed

Compute distance-based weights on the **donor** mesh and score them against its
authored weights, per vertex, as an error heat map.

european-dragon is a labelled validation set. The heuristic's error is knowable
before it ever touches Riyu, where there would be nothing to compare against.

*Proof:* a recorded per-vertex error distribution against authored weights, and
a visible heat map of where the heuristic fails.

### Step 7 — Skin Riyu and look at it

Apply the validated heuristic to the fitted skeleton, render the influence map
for Riyu, and iterate.

*Proof:* no unweighted vertices; weights normalize; influence map visually sane
at wings, shoulders, hips and jaw.

## Parenthesis Opened At The Review Gate

[Volumetric Body-Part Labeling](../30-body-part-labeling/plan.md), opened
2026-08-30, and it changes what steps 4-7 should be. Its phase 1 measured two
things this packet needs to absorb:

- **Riyu's 6,209 shells voxelize to a single solid component.** Every method
  this packet rejected for depending on surface connectivity -- geodesic
  distance, region growing, bone-heat weighting -- is available again in a
  volume. The "Constraints The Target Mesh Imposes" section above is correct
  about surfaces and does not apply to grids.
- **Nine of 29 standardized parts have no landmark that stands for them at
  all** -- `jaw`, and `upper_arm`, `forearm`, `shin`, `wing_arm` on both
  sides. They are absent by construction rather than misplaced, and they are
  the same joints step 2 declined to propose and step 3 had to carry on donor
  proportion. That is not an accuracy problem this packet can tune away.

The intent is for that packet to become a **prerequisite phase** of this one
rather than a sibling: a dense part labelling makes a skeleton derivable from
region medial axes and adjacency instead of fitted from a donor, which is the
reusability this packet explicitly gave up.

## Review Gate

Stop after **step 3** and look before committing to steps 5-7. The first real
fit is likely to change opinions about the rest.

## Validation Renders

Deterministic Blender renders of the fitted skeleton over the five standard
views, produced at each fitting step. Cheap, and bad joints are obvious at a
glance in a flip-through — this is where images earn their place, as review
rather than as an extraction mechanism.

## Risks

- Geometric landmark proposal may misidentify Riyu's wings, since spread
  membranes and the tail can present similar extremity signatures. Mitigated by
  the semantic labelling pass and by manual correction being authoritative.
- Riyu's shell soup means surface-normal and closest-point queries can land on
  interior shells. Any projection needs an outward-facing or ray-cast guard.
- Per-chain fitting can produce non-physical bone rolls; rolls are inherited
  from the donor and may need explicit recomputation from limb planes.
- The donor's proportions differ from Riyu's substantially (Riyu is compact and
  short-necked). Inheriting proportion rather than absolute length is what makes
  step 3 work, and that assumption is what step 1's picture tests.
- european-dragon's provenance is unknown. Everything here stays in the private
  local workspace; nothing derived from it is shippable.

## Exit Criteria

- Riyu carries a schema-valid fitted skeleton with semantic bone names, visible
  in the local viewer.
- `landmarks.json` exists, validates, and is symmetric within tolerance.
- Influence visualization works on the donor and on Riyu.
- The distance heuristic has a measured error against donor ground truth.
- Repository tests, Ruff, and Astro check/build pass; `test.md` records each
  step's picture and what it changed.
