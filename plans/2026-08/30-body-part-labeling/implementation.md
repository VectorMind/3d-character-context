# Implementation — Volumetric Body-Part Labeling

## Progress

`▰▰▰▱▱ Phase 2/5` — a skeleton is now read out of a labelled volume, and the
question the packet was opened to answer has a number: the elbow lands **0.33%
of the body diagonal** from where the donor's own rig puts it, and the median
over all 30 joints is **0.70%**, about one voxel. The hierarchy claim did not
survive: adjacency alone recovers 27 of 31 edges, so the hierarchy is declared
by the taxonomy and adjacency is reported beside it as a check. Ten phase-2
open points are proposed with confidences and are waiting on the maintainer.
Next is phase 3, volumetric weights — but OP-207 (the wing membrane, the one
measured failure) and OP-209 (Riyu has no `pelvis`, so it still yields no
skeleton) are the two worth settling first.

## 2026-08-30 — Phase 1

### What landed

- `specifications/body-parts/spec.md` — `western-dragon-parts/v1` as a durable
  contract: 29 parts, the labelled-volume schema, the ancestry mapping rule,
  and the reference-versus-proposal distinction. Fills the "region definitions"
  gap the specifications index already named.
- `src/character_context/body_parts.py` — the taxonomy in executable form, plus
  `european-dragon`'s 31 part-root rules and the ancestry resolver.
- `src/character_context/voxels.py` — the substrate. Voxelization with
  boundary flood fill, seeded geodesic watershed, per-part component counting,
  and majority pooling for browser transport.
- `src/character_context/part_volume.py` — reference labelling, landmark-seeded
  proposal, and scoring with per-part IoU.
- `cli.py` — `charctx parts taxonomy | reference | segment | score`.
- Web — `parts` on both the generation manifest and the asset card, both route
  allowlists, and a `PartOverlay` drawing an `InstancedMesh` of coloured cubes
  behind a `Show body parts` toggle. Both the donor and the generation viewer
  carry it.
- `tests/test_body_parts.py` (10), `tests/test_voxels.py` (10),
  `tests/test_part_volume.py` (7) — 27 new tests.
- README gained the `charctx parts` section in the same pass.

### Decisions

- **The voxel grid is the substrate, and it works.** Riyu's **6,209
  disconnected shells voxelize to a single solid component.** That is the
  packet's central claim and it is now measured rather than argued. Everything
  the Riyu packet had to reject for depending on surface connectivity is
  available again.
- **The mapping resolves by ancestry.** `european-dragon` carries
  `DEF-Finger_3.L` on a hand and `DEF-Finger_3.L.001` on a foot; only the
  hierarchy separates them. 31 rules cover all 168 bones, and a bone reaching
  the root without matching any rule raises rather than defaulting.
- **A rule naming an absent bone reports rather than raises.** The first
  version refused a rig that lacked any ruled bone, which is wrong: a partial
  rig is legitimately a subset of the family the rules describe. Only the
  other direction stays fatal, because that is the one that would make the
  taxonomy's totality a fiction.
- **A part with zero voxels is listed at zero, not omitted.** A missing part
  has to be visible. This is why Riyu's output states 20/29 parts and names
  the nine absentees rather than reporting 20 parts and looking complete.
- **Absent-by-construction is separated from misplaced.** `unseedable_parts`
  counts parts no seed can reach; `seeded_but_empty` counts parts that had a
  seed and still lost. Collapsing the two would make a structural gap look
  like a segmentation failure.
- **Per-part IoU, never a single aggregate.** A single number is dominated by
  the torso and the tail and would report health for a run that lost both
  wings.
- **The overlay is unlit and its cubes are undersized.** The scene's key
  lights are tinted warm and cool, which would shift a part's colour toward a
  neighbour's — and colour identity is the overlay's entire message. Gaps
  between undersized cubes give back the depth cue that dropping shading costs.

### Two things the implementation discovered

**Per-vertex weights cannot label the browser model.** The design started from
the donor's authored skin weights — 21,228 vertices, zero unweighted, dominant
bone per vertex mapped to a part, dense labels for free. glTF export splits
vertices at UV and normal seams, so the donor's `Dragon` mesh arrives as
**21,050 vertices against the weight document's 19,172**, under mesh-data
names (`mesh.001`, `Sphere.003`) rather than object names, with no
correspondence available. Rather than invent one, the reference is seeded by
rasterising the donor's authored **bone segments**, which are already in the
browser model's coordinate space. The weights still earn their place: they
prove the part map is total over the 168 bones that actually deform something,
which is a stronger check than totality over the bones that merely exist.

**The fill leaked, and the fix is a density rule not a constant.** The first
voxelizer drew a fixed 400,000 surface samples. Random sampling leaves
pinholes by the coupon collector's problem, and **a single missing voxel lets
the exterior flood straight into the interior**, so `voxelize` silently
returned a hollow shell — caught only because a unit test asserted the centre
of a sphere was solid. Sample count is now derived from surface area and
pitch (`area / pitch² × 24`), and the report carries a `filled` boolean and an
`interior_voxels` count so a leak is visible rather than assumed away. The
donor now draws 331,015 samples and Riyu 941,196.

### What the numbers showed

| | donor | Riyu |
| --- | --- | --- |
| Input surface | 21,050 verts, 5 meshes | 203,745 verts, **6,209 shells** |
| Solid components after voxelization | 1 | **1** |
| Solid voxels at 128³ | 19,244 | 44,024 |
| Interior found | 2,754 | 12,881 |
| Labelled | 100% | 100% |
| Parts present | **29/29** | **20/29** |

The reference is healthy: all 29 parts present, left/right voxel counts within
3% of each other, no part split across disconnected components, and all 31
part rules used.

The scored ablation is where the argument lives:

| Seeding | Seed points | Voxel accuracy | Mean IoU |
| --- | --- | --- | --- |
| Reference (authored bones) | 1,922 | — | — |
| Part centroids, one per part | 29 | **81.5%** | **0.702** |
| Geometric landmark proposal | 19 | **28.8%** | **0.066** |

Worst parts under centroid seeding are `wing_arm` (0.47), `pelvis` (0.52),
`jaw` (0.52) and `chest` (0.55) — every one of them an *interior* chain
segment squeezed between two neighbours. Best are `hand` (0.96), `tail_mid`
(0.88) and `foot` (0.88) — extremities, which have only one neighbour to lose
ground to. So sparsity costs about 30% IoU, and it costs it precisely where
the Riyu packet already had no landmarks.

**The landmark number is not a segmentation result.** It measures the
*proposer* on an out-of-distribution pose. The donor's rest pose is rearing,
so its forelimbs are off the ground and the ground-contact clustering finds
**3 clusters instead of 4** — producing 19 landmarks instead of 21 and losing
`foot_hind.L` and `hip.L` entirely, *asymmetrically*. Eleven parts end up with
no seed at all. The honest reading is that the geometric landmark proposer
assumes a standing quadruped and silently degrades when that is false.

### The structural finding

Nine of the 29 parts — `jaw`, and `upper_arm`, `forearm`, `shin`, `wing_arm`
on both sides — **have no landmark that stands for them and cannot be produced
by landmark seeding at all.** They are absent by construction, not misplaced.
Every one is an interior chain segment or the jaw: exactly the joints the Riyu
packet's step 2 declined to propose and step 3 had to carry on donor
proportion.

That is the case for this packet in one line: the landmark route is not merely
imprecise about a third of the body plan, it is structurally silent about it.

### Checks

`uv run pytest` 139 passed / 1 live skipped (27 new) · `uv run ruff check .`
clean · `pnpm check` 0 diagnostics · Astro build pass · both part routes serve
(181,420 B for Riyu, 105,360 B for the donor) and the stage marker 404s.
Full numbers in `test.md`.

### Not done

The interactive browser click-through was not run — no browser-control runtime
is available in this session. Route, prop, containment, symmetry and IoU
evidence stand in its place.


## 2026-08-30 — Phase 1b: head sub-parts, and the loop that got there

Review found `neck` wearing the top of `head` like a cap. It was a real defect
and the fix took four measured passes, each of which moved the error somewhere
new before it went away.

### What the defect actually was

Not what it looked like. Forward of the `skull` landmark the volume was already
**100% head** — the neck was not eating the snout or the eyes. It was eating
the **crown**, and the cause was in `y`, not `z`: `neck_base` sat at y=+0.074
on the dorsal crest while `skull` sat at y=+0.039 below it, so every voxel on
top of the skull was geodesically nearer the neck's seed than the head's.

`head` held 918 voxels against `neck`'s 2,632.

### The loop

**Pass 1 — measure the boundary instead of guessing it.** `neck_base` and
`skull` were placed at fixed fractions (0.30 and 0.78) along the chest-to-snout
span. A dragon's neck narrows into its skull, and that waist is a local minimum
in the cross-section profile. Measured on Riyu: a 39% dip at z=+0.412, against
a 3.9% runner-up.

*It found nothing.* The waist is about one bin wide, so with disjoint bins its
depth depended on where the edges happened to fall — shifting the profile's
start by a hundredth of the body length smeared 39% down to 13% and lost it.
Replaced with an **overlapping moving window**, which decouples the window's
width from the sampling step and removes the phase sensitivity entirely. A
sweep over five window widths then picked `1/40`: not the deepest reading, the
one with the widest **margin** over the runner-up (3.9x, against 1.2x either
side of it). Every width agreed on the *location* to within 0.003, which is
what made the choice safe.

**Pass 2 — the two head landmarks landed on the same point.** `head_base` and
`neck_base` both snapped to the same medial-curve sample, because the curve is
sampled in 48 bins over the whole body and that is coarser than the features
that matter at the head. Two seeds on one voxel is two parts fighting over the
same ground. `_at` now interpolates between curve samples instead of snapping,
which improves every chain landmark, not just these.

**Pass 3 — the head took the crown, then kept going.** Seeding `head_top` at
the crest fixed the crown and swung the error the other way: the head ran back
down the dorsal ridge to z=+0.28, into the shoulders. The ridge profile says
why — it peaks at z=+0.355, y=+0.158, which is *behind* the occiput. The tall
crest belongs to the neck, and `head_top` had been sitting on its descending
flank.

**Pass 4 — anchor both, not one.** The neck gained `neck_top` at its own
dorsal maximum, and the head's crown is now measured a quarter of the way
forward of the occiput, clear of the neck's crest. The general rule, worth
carrying into every later part: **a part that is tall needs a dorsal anchor, or
its neighbour's dorsal anchor takes its top.**

### Result

| | before | after |
| --- | --- | --- |
| `head` | 918 | **2,045** |
| `neck` | 2,632 | 1,876 |
| Forward of `skull`, labelled head | 100% | 100% |
| Parts split across components | 0 | **0** |

The head owns its crown, the neck owns its crest, and every part is still a
single connected region. What looks like ragged interleaving along the
head/neck boundary in the viewer is the **display grid**, not the
segmentation: majority-pooling 2x2x2 blocks along any boundary alternates
winners. `split_parts` is empty at full resolution.

### Sub-parts

`western-dragon-parts/v2`: `nostril`, `eye.L/R`, `ear.L/R`, each declaring
`head` as its parent. Appended at indices 30-34 so every v1 index still means
what it meant.

- **The donor's rig has real eye bones** -- `DEF-eye`, `DEF-eye_iris` and eight
  lid bones per side, all parented to the skull. Mapping them gives `eye.L/R` a
  genuine reference region rather than a placeholder, and the donor reference
  now carries **31 of 34 parts**. There is no equivalent bone for an ear or a
  nostril, so those stay empty on the donor and say so.
- **A sub-part refines its parent, it does not remove the region.** The
  document reports both readings: `head` fine is 230 voxels on the donor and
  `coarse_voxels.head` is 411, the difference being the two eyes.
- **Geometry does not propose an eye.** A socket is a dimple on one model and a
  bulge on the next, and on a stylised character the eye is often painted
  rather than sculpted, so it has no geometry at all. Eyes, ears and nostrils
  are asserted through `skeleton/landmarks.manual.json` -- from a person or a
  vision model reading a rendered view. A manual point always overrides a
  proposal because it is evidence and a proposal is not, and the overlay may
  only set names on an allow-list, because an overlay that accepts any name
  turns a typo into geometry.

Riyu's eyes are **not supplied**: nothing in this session could see them, and
inventing them would be exactly the guess the packet refuses elsewhere. The
mechanism is in place and tested; the points are a VLM pass away.

### Also in this pass

- The donor reference flags `eye.L` as split into two components. The
  connectivity check earning its keep on its first real subject.

### Checks

`uv run pytest` 148 passed / 1 skipped (36 new since phase 1 began) ·
`uv run ruff check .` clean · `pnpm check` 0 diagnostics · Astro build passes.


## 2026-08-30 — Phase 1c: scipy.signal, and reproducibility

### `scipy.signal` after all

The block was transient. `scipy.signal`, `scipy.integrate` and the rest now
import cleanly on this workstation, so valley detection uses
`scipy.signal.peak_prominences` rather than the hand-rolled scan.

It is a better measurement, not merely a shorter one. The hand-rolled version
took a valley's shoulder as the maximum over the *whole* profile on each side;
scipy stops at the nearest **deeper** valley, which is the standard
topographic definition and the one that stays correct when a profile carries
two waists — the second would otherwise be measured against the first one's
shoulder. The scale-free ratio is kept on top of it: prominence divided by the
shoulder it was measured from, so the threshold still reads as "this waist is
at least 8% narrower than the mesh either side of it".

Verified behaviour-preserving on Riyu before the swap: both implementations
return the occiput at z=+0.4114 with depth 0.1505 and runner-up 0.0388, so
every number already recorded in `test.md` stands.

### Voxelization is now reproducible

Switching implementations surfaced something unrelated and worse: `head` came
back as 2,045 voxels on one run and 2,039 on the next. Surface sampling is
random and was unseeded, so **no recorded voxel count was reproducible** — a
small drift, but enough to make a measurement not a measurement.

`voxelize` now takes a `seed` (default 0), offset per geometry so two meshes
of equal area do not draw the identical pattern, and records it as
`sample_seed` in the report. Two consecutive runs now agree exactly:
`head` 2,049 · `neck` 1,877 · solid 44,006.


## 2026-08-31 — Phase 2: skeleton from the classification

The phase was drafted as three derivations — medial axes become bones, region
adjacency becomes the hierarchy, region boundaries become joints. One of the
three carried the phase, one turned out to be unnecessary, and one was
contradicted by its own measurement.

### The result, in one line

**The elbow is 0.33% of the body diagonal from where the donor's rig puts it.**
The knee is 0.72%, the wrist 0.37%, the jaw hinge 1.12%. These are the joints
the Riyu packet's step 2 declined to propose and step 3 carried on donor
proportion, and every one of them is now a measurement.

### What landed

- `src/character_context/part_skeleton.py` — interfaces between parts, the
  joint estimate, the bone hierarchy, the adjacency cross-check, and scoring
  against a source rig.
- `voxels.py` gained the substrate operations phase 2 needed and phase 3 will
  reuse: `geodesic` (hop distance *inside* a mask), `farthest`, and
  `interfaces` (every touching pair of parts, as voxel-face positions).
- `body_parts.py` gained `PART_PARENT`, the declared hierarchy, plus
  `ROOT_PART` / `ROOT_PROXIMAL` and the `part_children` / `hierarchy_chain`
  helpers. `charctx parts taxonomy` now prints it.
- `asset_models.py` gained `DerivedSkeletonDocument`
  (`charctx.derived-skeleton/v1`).
- `cli.py` — `charctx parts skeleton <target>` and
  `charctx parts skeleton-score <donor>`, both with `--seeds
  reference|centroid|landmarks`.
- Web — `part_skeleton` on the asset card and the generation manifest, both
  route allowlists, and a `Show part skeleton` toggle drawing the derived rig
  in its own colour with enlarged joint dots.
- `tests/test_part_skeleton.py` — 16 new tests, most of them on synthetic
  volumes whose boundaries are known by construction.

### The three derivations, and what happened to each

**Joints from region boundaries — this is the phase.** A joint is the centre of
the voxel faces separating two parts, weighted by each face's distance to the
surface. The weighting is worth its line of code: a real joint is a
*cross-section* through a limb and a fold is a *crease* at the skin, and by
area alone they are identical. Weighting by depth² moved the median joint error
from 0.80% to 0.66%. The exponent was swept — 1 gives back less, 3 gives back
nothing more.

**Bones from joint to joint — works, and medial axes were not needed.** A bone
runs from the joint with its parent to the joint with its farthest child, so a
bone's tail *is* its child's head and the chain is connected. The alternative,
running every bone to the far end of its own region, was measured at 1.33%
median tail error against 0.71%, and produces a rig of floating segments. The
drafted medial-axis route would have fitted a curve to a region in order to
find a segment the two joints already give directly, and would have added
spurious branches on blobby parts. `scikit-image` still earns DEP-001 through
`distance_transform_edt`.

**The hierarchy from adjacency — contradicted.** A maximum-contact spanning
tree over the region adjacency graph recovers **27 of the donor's 31 edges**.
The four it gets wrong are `jaw`→`neck`, `neck`→`wing_root.L`, and both
`wing_root`→`upper_arm`, and they share a cause: the donor's rest pose is
rearing with folded wings, so parts touch along large areas without
articulating. `jaw`–`neck` has 62 voxel faces of contact against the true
`head`–`neck` edge's 49.

Three edge scores were tried before giving up on the derivation: interface
depth (`jaw`–`neck` is *deeper* than `head`–`neck`, 1.75 against 1.52 voxels),
"endness" — how near the contact sits to the end of each region's geodesic
extent — and their products. None separated a joint from a fold. **Contact area
cannot tell articulation from adjacency, and neither could anything else
measurable here.**

So the hierarchy is declared by the taxonomy, which matches the donor's rig on
**31 of 31** parts, and adjacency is computed on every run and reported beside
it. The distinction that keeps this honest: declaring the *hierarchy* is not
borrowing the *skeleton*. Nothing about where a joint sits comes from a donor.

### What the numbers showed

Three seedings of the same volume, scored against the donor's authored rig at
128³ (pitch 0.166, body diagonal 26.25):

| Seeding | Bones | Hierarchy vs donor | Joint error, median | mean | max |
| --- | --- | --- | --- | --- | --- |
| Reference (the donor's own bones) | 31 | 31/31 | **0.70%** | 1.62% | 13.31% |
| Part centroids, one per part | 31 | 31/31 | **1.42%** | 2.31% | 14.21% |
| Geometric landmark proposal | — | — | **no skeleton at all** | | |

Reference seeding isolates the skeleton step: given a good labelling, how well
does a boundary locate a joint? Answer: **2.56 voxels mean, and the median is
nearer one.** Centroid seeding compounds it with a sparse labelling and roughly
doubles the error, which is the honest cost of not having the answer key.

Per joint, under reference seeding:

| Joint | Error | Joint | Error |
| --- | --- | --- | --- |
| `neck`←`chest` | 0.14% | `hand`←`forearm` (wrist) | 0.37% |
| `chest`←`abdomen` | 0.30% | `foot`←`shin` (ankle) | 0.62% |
| `forearm`←`upper_arm` (**elbow**) | 0.33% | `shin`←`thigh` (**knee**) | 0.72% |
| `tail_mid`←`tail_base` | 0.37% | `jaw`←`head` (**hinge**) | 1.12% |
| `upper_arm`←`shoulder` | 0.56% | `thigh`←`pelvis` (hip) | 1.41% |

### The one failure, and it is specific

`wing_hand` comes back **13.3%** out of place against a 0.70% median. The cause
is not general: `wing_arm` and `wing_hand` share a long membrane **seam** —
148 voxel faces of it — rather than a joint cross-section, so the interface
centroid sits mid-membrane instead of at the spar junction. Everything the
method assumes about an interface is false for a membrane.

The answer key is also weakest exactly there. The donor attaches `wing_hand`
with three separate spar bones whose heads are **3.99 apart**, so there is no
single true joint to be wrong about. That is now reported: `donor_head_spread`
travels with every scored row, and the summary carries a median over only the
27 joints the donor places at one point (**0.63%**). Fixing the score to hide
the ambiguity would have been the wrong move; reporting it is the right one.

### Decisions made during development

- **A derived skeleton gets its own schema.** `charctx.fitted-skeleton/v1`
  requires a `donor_id`, because a fitted skeleton *is* a donor hierarchy moved
  onto a target. This one has none, and putting a null there would blur the
  exact distinction the packet exists to draw. A donor may still *score* it,
  which is recorded in `derivation` rather than in the identity.
- **Roll is not derived.** An occupancy grid carries no twist. Every bone
  reports 0 and the document says why.
- **A part whose declared parent is missing climbs its own chain.** It is not
  dropped and not reparented to whatever it touches. On Riyu that fires eight
  times — hands hang off shoulders because no `forearm` was ever labelled —
  and `reattached_parts` names every one.
- **The adjacency check compares against the hierarchy in force, not the raw
  table.** An absent forearm is not evidence that contact area disagrees about
  anatomy, and counting it as such would make the check read worse the sparser
  the volume gets.
- **The score separates leaves from chained bones.** The donor's `head` chain
  stops behind the eyes while a derived `head` bone runs to the snout. That is
  a difference of convention, not an error, and pooling the two would hide
  both.

### Riyu, as a smoke check rather than a result

Pointed at `trellis2/ninjago-riyu-001` the command runs and produces 20 bones
over 20 parts — and it is not a skeleton anyone should use. Fourteen parts have
no bone, eight are reattached across a gap, and every interior joint the packet
exists to find is missing, because the landmark labelling cannot produce the
regions they lie between. **The same thing happens on the donor**, where the
real landmark proposer yields 17 of 34 parts and no `pelvis` at all, so no root
and no skeleton. That is OP-209, and it is the clearest statement yet of what
the packet still has to solve: the skeleton step is good; the labelling it
needs is not there yet on a rigless target.

### Ten open points, proposed rather than asked

Every question phase 2 raised is in `plan.md` with candidate options, a named
proposal the work has already proceeded on, and a confidence keyed to evidence
rather than enthusiasm — and each is mirrored in the new global decision table
in `plans/open.md`. `WORKFLOW.md` gained the rule that produced them: every
open point names a proposal and carries a confidence, not only the ones that
select a dependency.

### Checks

`uv run pytest` 164 passed / 1 live skipped (16 new) · `uv run ruff check .`
clean · `pnpm check` 0 diagnostics · Astro build passes. Full numbers in
`test.md`.
