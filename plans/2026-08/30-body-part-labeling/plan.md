# Plan — Volumetric Body-Part Labeling

Date: 2026-08-30
Status: Phase 1 complete and measured (1a substrate, 1b head sub-parts,
1c determinism). Phase 2 built and measured on `european-dragon`; its ten open
points are proposed and awaiting maintainer review.
Parent: opened as a parenthesis inside
[Riyu Skeleton Fit And Rig Visualization](../29-riyu-skeleton-fit/plan.md), and
intended to become a **prerequisite phase** of it rather than a sibling.

## Framing

The Riyu packet fits a donor skeleton onto a target using 21 landmarks. It
works, and its own numbers say where it runs out: 74 of 168 bones are anchored
by evidence and 94 are carried on inheritance; the nine interior joints have no
surface signature and are still not measured; and the whole track is
per-character with no reusability.

The failure mode underneath all three is the same. **A landmark is a point
estimate over a 200,000-vertex object.** Twenty-one of them is a very thin
description of a dragon, so everything downstream is an interpolation between
lucky points.

This packet replaces that description with a dense one: **classify the target's
volume into standardized body parts first, then derive everything else from the
classification.** A part label is a majority vote over thousands of voxels
rather than a single point, so it degrades gracefully where a landmark simply
lands in the wrong place.

The prize is not a better fit. It is a different door:

| Question | With landmarks | With a labeled volume | What phase 2 measured |
| --- | --- | --- | --- |
| Where is the elbow? | A point nothing can propose | Where the `upper_arm` region meets `forearm` — a *boundary between regions*, which is stable | **0.33% of the body diagonal**, about two voxels, against the donor's own rig |
| Where does a bone go? | Interpolated between landmarks | The medial axis of one labeled region | Between two measured joints. Medial axes turned out to be unnecessary |
| What is the hierarchy? | Inherited from the donor | Region **adjacency** — derived, not borrowed | **Contradicted.** Adjacency alone gets 27 of 31 edges and the four failures are folds. Declared by the taxonomy instead — see OP-202 |
| Does it transfer to the next dragon? | No | Yes, if the taxonomy is standard | Not yet shown: one donor |

A labeled volume makes a skeleton **derivable from scratch** rather than
fitted. That is the reason this parenthesis is worth opening before continuing
with rigging.

### Prior art this is modelled on

The precedent is Shotton et al., *Real-Time Human Pose Recognition in Parts
from Single Depth Images* (Kinect, 2011): classify every pixel into one of ~31
body parts, then read joints out of the part clusters, rather than regressing
joints directly. The maintainer's 2012 doctoral work used the same shape —
Kinect voxels, mocap ground truth, random-forest part classification.

What has changed since is the classifier, not the architecture. The
architecture is still right, and it is what this packet adopts.

## Resolution Summary

Every decision and dependency this packet has taken, at a glance. Detail for
each is below.

| Id | Topic | Proposal | Confidence | Status |
| --- | --- | --- | --- | --- |
| DD-001 | Substrate | Voxel grid, not surface or point cloud | high | Accepted — measured: Riyu's 6,209 shells voxelize to 1 solid component |
| DD-002 | Boundaries vs names | Kept separate; a class-agnostic segmenter is still useful | high | Accepted |
| DD-003 | Answer key | Donor's authored rig, called a **reference** not ground truth | medium | Accepted, weakened in flight — per-vertex weights do not survive glTF export, so it is seeded from authored bone segments |
| DD-004 | Bone→part mapping | Resolve by ancestry; an unmapped bone is an error | high | Accepted — 31 rules cover all 168 bones, 0 unused |
| DD-005 | Neural segmentation | Hosted or absent | high | Accepted — established by probe: no CUDA on this machine |
| DD-006 | Seeds | Pluggable; report both landmark and centroid seeding | high | Accepted |
| DD-007 | Browser transport | Pooled display grid, never the computation grid | high | Accepted — 105–181 KB against tens of MB for a box mesh |
| DD-008 | Phase 1 ships nothing learned | Deterministic baseline first | high | Accepted |
| DD-009 | Head sub-parts | Taxonomy v2 adds `nostril`, `eye.L/R`, `ear.L/R` under `head`; appended at 30–34 so v1 indices keep their meaning | high | Accepted — `head` recovered 918 → 2,045 voxels |
| DD-010 | Features geometry will not propose | Eyes, ears, nostrils asserted through a manual overlay, never guessed | high | Accepted |
| DD-011 | Determinism | Surface sampling seeded; the seed is recorded | high | Accepted — an unseeded run drifted part counts by ~6 voxels |
| DD-012 | Derived-skeleton schema | `charctx.derived-skeleton/v1`, separate from the fitted one | high | Accepted — a fitted skeleton requires a `donor_id` and this one has no donor at all |
| OP-201 | Where is the elbow | Depth²-weighted centroid of the region interface | high | **Awaiting review** — measured 0.66% vs 0.80% median |
| OP-202 | Hierarchy: declared or derived | Declared by the taxonomy; adjacency reported as a check | high | **Awaiting review** — measured: adjacency alone gets 27/31 |
| OP-203 | Where a bone ends | The child joint farthest from the head; farthest voxel for a leaf | high | **Awaiting review** — measured 0.71% vs 1.33% median |
| OP-204 | The root bone's head | Declared: `pelvis`, starting at its boundary with `tail_base` | medium | **Awaiting review** — a convention, confirmed on one donor |
| OP-205 | Bone granularity | One bone per part now; declared per-part subdivision later | medium | **Awaiting review** — a one-bone `tail_mid` cannot curl |
| OP-206 | Roll | Not derived; every bone reports 0 and says so | medium | **Awaiting review** — revisit only if phase 3 skinning needs it |
| OP-207 | The wing membrane interface | Trim the interface by depth before taking its centroid | low | **Awaiting review** — the one measured failure, 13% error, fix untested |
| OP-208 | When deterministic is "not good enough" | Median joint error ≤1% under donor-independent seeding, every part present | medium | **Awaiting review** — currently 1.42%, so not met |
| OP-209 | What supplies the interior parts on a rigless target | Chain-proportion priors first, hosted segmentation second | low | **Awaiting review** — Riyu has no `pelvis`, so it produces no skeleton at all |
| OP-210 | Does the derived skeleton replace the donor rig | No: its joints become anchors for the existing chain fit | medium | **Awaiting review** — the decision that closes the Riyu parenthesis |
| DEP-001 | `scikit-image` | 3D skeletonize, MCP geodesics, compact watershed, marching cubes | high | **Approved 2026-08-30** |
| DEP-002 | `libigl` | Winding number, bounded biharmonic weights | — | **Rejected** — no Windows wheel for Python 3.12 |
| DEP-003 | `scikit-learn` | Learned classifier for phase 5 | medium | Deferred |
| DEP-004 | `rtree` / `embreex` / `manifold3d` | Faster queries, mesh repair | low | Deferred |

## The Central Move: The Substrate Is A Voxel Grid, Not A Surface

Riyu is 203,745 vertices in **6,209 disconnected shells**, not watertight. Every
surface-based method the Riyu packet considered had to be rejected for that
reason, including Blender's bone-heat weighting.

In an occupancy grid, those 6,209 shells are **one connected solid**. Shell soup
is a property of the surface representation and it does not survive
voxelization.

That single change unlocks, in one move, everything the Riyu packet listed as
blocked:

- geodesic distance *through the body* (a wing tip is far from the torso by way
  of the wing, not by way of the air);
- volumetric region growing and watershed;
- volumetric weight diffusion — bone heat's semantics without bone heat's
  topology requirement;
- inside/outside tests without a watertight surface.

Everything in this packet therefore happens in the grid. The mesh is an input
to voxelization and is never touched again.

## Two Label Sources, Deliberately Separated

The word "classification" hides two different problems, and merging them is
what makes this hard:

1. **Boundaries** — where one part stops and the next begins. Geometric, local,
   deterministic, and free.
2. **Names** — which region is a wing and which is a foreleg. Semantic, global,
   and the only part that actually needs a model.

They are kept apart throughout. Boundaries come from geometry; names come from
a seed's identity. A method that produces good boundaries and no names is still
useful, and a naming pass can be swapped without touching the geometry.

## Where The Answer Key Comes From

`european-dragon` is a labelled corpus that already exists and cost nothing:

- **21,228 vertices, every one weighted, zero unweighted, 57,473 influences.**
- **Five actions — Fly (80 frames), Idle Sit (60), Idle Stand (160), Run (16),
  Walk (16): 332 frames of pose data.** Posing the rig and re-voxelizing yields
  a labelled volume per frame. That is the Kinect pipeline exactly, with a
  rigged asset standing in for the mocap corpus. Untouched so far; it is the
  corpus phase 5 would need.

So the donor is both the label source and the validation set. Any method that
claims to label a volume can be scored against it before it is ever pointed at
a target that has no answer key.

**It is a reference, not ground truth, and the difference was forced.** The
plan intended to take each vertex's dominant bone as its label — dense truth
for free. That does not survive glTF export: vertices split at UV and normal
seams, so the browser model arrives as 21,050 vertices against the weight
document's 19,172, under different names, with no correspondence between them.
Rather than invent one, the reference is seeded by rasterising the rig's
authored **bone segments**. Still authored, but a step removed: a part
boundary sits midway between bones rather than where the weights actually
cross over. The weights still earn their keep by proving the part map is total
over the 168 bones that deform something. See DD-003.

## Hardware And Access, Established Not Assumed

Probed on 2026-08-30 rather than taken from a paper:

| Fact | Value | Consequence |
| --- | --- | --- |
| Local GPU | Intel Arc 140V (16 GB), no CUDA | PartField (PyTorch 2.4 + CUDA 12.4) and SAMPart3D cannot run locally. **Any neural route must be hosted.** |
| `tencent/Hunyuan3D-Part` | `RUNNING`, `zero-a10g`, Gradio | Live free hosted part segmentation, same access pattern as the TRELLIS.2 backend already in use |
| Its API | `/segment(mesh_path, postprocess, postprocess_threshold, seed) -> (mesh, face-id map)` | Returns **class-agnostic part IDs**, not names — which is exactly the boundaries/names split above |
| `nvidia/PartField`, `Pointcept/SAMPart3D` Spaces | HTTP 401 | Not freely reachable; local checkouts would need CUDA |

The deterministic route below needs **no new dependency at all**: numpy 2.5,
scipy 1.18, trimesh 5.0 and networkx 3.6 are already installed, and
`scipy.ndimage` covers voxelization, morphology, connected components and
distance transforms.

## Phases

Phase 1 is this session's scope and ends with a picture. Later phases are
sketched so the sequencing is visible, not committed.

### Phase 1 — A classified volume, deterministic, and a number saying how good it is

1. **The taxonomy.** `western-dragon-parts/v1`: 29 standardized parts, defined
   once as a durable contract in `specifications/body-parts/spec.md`.
2. **Voxelize.** Surface rasterization, morphological closing, then a flood
   fill from the grid boundary to separate inside from outside. No
   watertightness assumed anywhere.
3. **Ground truth.** Label the donor's vertices from its own skin weights via a
   bone-to-part table resolved *by ancestry*, not by name matching, then
   majority-pool into the grid.
4. **Segment.** Seeded geodesic watershed in the voxel graph: seeds are labelled
   voxels, every other solid voxel takes the label of its nearest seed measured
   *through the volume*.
5. **Score.** Run the identical segmentation on the donor from seeds that carry
   no reference labels, and score it against step 3. Per-part IoU and voxel
   accuracy.
6. **Look at it.** Colour-coded voxels in the existing web viewer.

*Exit:* Riyu carries a classified volume, the donor carries a measured accuracy
for the method that produced it, and both are visible.

### Phase 2 — Skeleton from the classification

Region boundaries become joints, and the nine interior joints the Riyu packet
declined to propose are ordinary interfaces here, which is the whole point.
Scored against the donor's real skeleton.

Two of the three things the phase was drafted to derive survived contact with
the measurement, and the third did not:

- **Joints, from region boundaries** — works, and is the phase's result. A
  joint is the depth-weighted centre of the voxel faces separating two parts.
- **Bones, from joint to joint** — works. A bone runs from the joint with its
  parent to the joint with its farthest child, so the chain is connected; a
  leaf runs to the far end of its own region.
- **The hierarchy, from region adjacency** — *does not work well enough to
  use.* Measured, it recovers 27 of the donor's 31 edges and gets four wrong,
  and every failure is a place where the model is folded so that two parts
  touch without articulating. The hierarchy is therefore declared by the
  taxonomy and adjacency is reported beside it as a check. See OP-202.

Medial axes are not used at all. They were the drafted mechanism and the
measurement made them unnecessary: a bone between two measured joints is
already the segment a medial axis would have been fitted to, and skeletonizing
a region adds a failure mode (spurious branches on a blobby part) for no
gain. `scikit-image` still earns DEP-001 through `distance_transform_edt`,
which is what makes an interface's depth readable.

### Phase 3 — Volumetric weights

Bone-heat semantics in the grid: rasterize bones as Dirichlet sources, solve a
sparse Laplace system, sample back at the vertices. Scored against the donor's
authored weights. This is Riyu steps 5–7 with the blocker removed.

### Phase 4 — Hosted neural segmentation, if phase 1 is not good enough

`tencent/Hunyuan3D-Part` for class-agnostic boundaries, named by matching its
regions against the phase-1 labelling. Metered, so it runs only when a
deterministic run has been scored first and found wanting.

### Phase 5 — Learned classification, if phase 4 is not good enough

The donor's 332 animation frames become a synthetic corpus, the way the Kinect
work used mocap. Deferred deliberately: the corpus is one dragon, so a
classifier trained on it may learn *european-dragon* rather than *dragon*.

## Open Points — Phase 2

Every one carries a proposal the work has already proceeded on, so nothing here
is blocking. What is being asked for is an overturn where a proposal is wrong,
not permission to continue. Confidence is about the evidence: `high` means it
was measured on real data, `medium` means it is a convention that one donor
agrees with, `low` means it is reasoning that has not been tested.

**OP-201 — Where is the elbow?** The framing table promised "where `upper_arm`
meets `forearm`". The interface between two labelled regions is thousands of
voxel faces, so a single point still has to be chosen out of it.

| Option | Argument |
| --- | --- |
| Plain centroid of the interface | Simplest. Median joint error **0.80%** of the body diagonal on the donor |
| **Depth²-weighted centroid** | Weight each interface voxel by its distance to the surface. A real joint is a *cross-section* through a limb and a fold is a crease at the skin, and they are indistinguishable by area alone. Median **0.66%** |
| Narrowest cross-section near the boundary | Anatomically appealing; a joint is often a waist. But a dragon's elbow is not narrower than its forearm, and phase 1b already spent four passes learning how fragile a waist measurement is |
| Junction of the two regions' medial axes | The drafted method. Needs two skeletonizations to produce a point the interface already gives directly |

*Proposal:* depth²-weighted centroid. *Confidence:* **high** — measured both
ways on the donor's 30 joints; the exponent was swept and 2 is where the
improvement stops. *What would move it:* a second donor where the two rank
differently.

**OP-202 — Does the hierarchy come from the geometry or from the taxonomy?**
This is the one the framing table was most confident about ("region
**adjacency** — derived, not borrowed"), and it is the one the measurement
contradicted.

| Option | Argument |
| --- | --- |
| Derive it: maximum-contact spanning tree | Genuinely donor-independent. Measured: **27 of 31** edges correct. The four failures are `jaw`→`neck`, `wing_root.L`→`upper_arm.L`, `wing_root.R`→`upper_arm.R` and `neck`→`wing_root.L` — every one a *fold*, where two parts touch along a large area without articulating |
| Derive it with a better edge score | Tried: interface depth, interface "endness" (how close the contact sits to the end of each region's extent), and their products. None separated a joint from a crease; `jaw`–`neck` has *more* contact and *more* depth than the true `head`–`neck` edge |
| **Declare it in the taxonomy; report adjacency as a check** | The hierarchy is a property of the western-dragon body plan, not of one mesh — `forearm.L` hangs off `upper_arm.L` for every dragon there will ever be. It belongs to a standardized taxonomy in the same way the part names do. The declared table matches the donor's rig on **31 of 31** parts |
| Borrow it from the donor rig | What the Riyu packet does, and what this packet exists to stop |

The distinction that matters: declaring the *hierarchy* is not borrowing the
*skeleton*. Nothing about where any joint sits comes from the donor, and the
hard half — the positions — is entirely measured. What is declared is the
same kind of statement as "a dragon has two wings".

*Proposal:* declare it. Adjacency is derived on every run and its disagreements
are recorded, so this stays an evidenced choice. *Confidence:* **high**.
*What would move it:* an edge score that separates joints from folds; a
disagreement would then be evidence rather than noise.

**OP-203 — Where does a bone end?**

| Option | Argument |
| --- | --- |
| **The child joint farthest from the head** | Keeps the chain connected: a bone's tail *is* its child's head, which is what a rig needs. Median tail error **0.71%**. For a part with no children, the far end of its own region |
| Always the far end of the part | Uniform, no special case, and disconnected: every bone floats. Median **1.33%** |
| The medial axis endpoint | Needs skeletonization for a point the interfaces already give |

*Proposal:* farthest child joint, falling back to the farthest voxel for a
leaf. *Confidence:* **high** — measured both ways.
*Known cost:* a leaf is scored generously. The donor's `head` chain stops
behind the eyes while a derived `head` bone runs to the snout, so leaf tails
are reported apart from chained ones rather than pooled.

**OP-204 — Where does the root bone start?** The root part has no parent to
take a head position from, so something has to be named.

| Option | Argument |
| --- | --- |
| **Declare it: `pelvis`, starting at its boundary with `tail_base`** | The hips are the conventional root of a quadruped rig, and the donor agrees exactly — `DEF-Spine`'s head sits on the pelvis/tail boundary. One line of declaration |
| The point of the root part farthest from all its children's joints | Derived, no declaration. Kept as the automatic fallback for a target with no tail |
| The root part's centroid | Simplest and wrong: it puts the root inside the hips rather than at their caudal end |

*Proposal:* declare it, with the farthest-point rule as the fallback when the
tail is absent. *Confidence:* **medium** — it is a convention rather than a
measurement, and one donor agreeing is not evidence that it generalizes.

**OP-205 — One bone per part?** The taxonomy has 34 parts, so a derived
skeleton has at most 34 bones against the donor's 168.

| Option | Argument |
| --- | --- |
| **One bone per part** | Every bone is bracketed by two measured joints, so every bone is evidence. Nothing is invented |
| Subdivide long parts by arc length | A one-bone `tail_mid` cannot curl and a one-bone `neck` cannot arch, so animation will want this. But a subdivision has no measurement behind it: the interior joints of a subdivided tail are interpolations, which is exactly what the packet replaced |
| Carry the donor's granularity | Reintroduces the donor dependency |

*Proposal:* one bone per part now; a **declared** per-part subdivision count
later, so an interpolated joint is visibly interpolated. *Confidence:*
**medium** — the ceiling is real and will be hit by phase 3 or by posing.

**OP-206 — Roll.** A bone's twist about its own axis has no signature in an
occupancy grid. Options are to leave it at zero and say so, to derive it from
the principal axis of the part's cross-section, or to inherit it from a donor.

*Proposal:* leave it at zero and record it as a limitation. *Confidence:*
**medium** — right until something needs it. Skinning is rotation-invariant
about the bone axis, so phase 3 probably will not; posing will.

**OP-207 — The wing membrane, which is the one measured failure.**
`wing_hand` comes back **13% of the body diagonal** out of place, against a
0.66% median. The cause is specific: `wing_arm` and `wing_hand` share a long
membrane *seam*, 148 voxel faces of it, rather than a joint cross-section, so
its centroid sits mid-membrane instead of at the spar junction.

| Option | Argument |
| --- | --- |
| Accept and report it | Honest, and it is reported. But it is a quarter of the wing |
| **Trim the interface by depth before taking the centroid** | Keep only the interface voxels deeper than some fraction of the local maximum, which is the spar. Cheap, no taxonomy change, untested |
| Give the membrane its own part | Makes the spar interface a cross-section again, and contradicts the v1 note that a membrane has no independent articulation and giving it a part would imply one |
| Intersect the interface with both regions' medial axes | The medial axes phase 2 did not need, brought back for one case |

*Proposal:* try the depth trim, and name the taxonomy change it would take if
that fails. *Confidence:* **low** — nothing here is measured yet.

**OP-208 — What number decides that the deterministic route is not good
enough?** Phases 4 and 5 are gated on this and the gate has never been stated.

*Proposal:* median joint error **≤1% of the body diagonal** under
*donor-independent* seeding, with every taxonomy part present. Two clauses,
both load-bearing: measuring under reference seeding flatters the method by
handing it the answer, and a median over the parts that happened to survive
would pass a run that lost both wings.

*Where it stands:* reference seeding gives **0.70%** and would pass; centroid
seeding gives **1.42%** and does not; landmark seeding produces no skeleton at
all. *Confidence:* **medium** — the threshold is a judgement, not a
measurement, and 1% is chosen because it is about six voxels at the working
resolution.

**OP-209 — What supplies the interior parts on a target with no rig?** This is
the gap phase 1 measured and phase 2 makes concrete: on the donor, the real
landmark proposer produces **17 of 34 parts and no `pelvis`**, so there is no
root and no skeleton at all.

| Option | Argument |
| --- | --- |
| Extend the manual/VLM overlay to interior joints | A person can point at an elbow. But the overlay exists for features geometry *cannot* propose, and an elbow is not one — it has no surface signature either, which is why it is the packet's subject |
| **Chain-proportion priors** | Between two measured joints, place the interior part boundaries at declared fractions of the chain. Donor-independent if the fractions are declared per family rather than copied; measurable against the donor immediately |
| Hosted neural segmentation (phase 4) | `tencent/Hunyuan3D-Part` is live and probed. Class-agnostic, so its regions still need naming — and naming them needs a labelling, which is the thing that is missing |
| Learned classification (phase 5) | The right long answer and the most expensive; one donor's 332 frames may teach *european-dragon* rather than *dragon* |

*Proposal:* chain-proportion priors first, because they can be measured against
the donor this week, then hosted segmentation. *Confidence:* **low** — the
priors are a guess until scored.

**OP-210 — Does the derived skeleton replace the donor rig, or feed it?** The
strategic question, and the one that closes the parenthesis opened inside the
Riyu packet.

| Option | Argument |
| --- | --- |
| The derived skeleton becomes the production rig | Fully donor-independent and reusable. But it has 31 bones and no roll, and the taxonomy deliberately names no fingers, toes, teeth or lids — a hand is one part on purpose |
| **Its joints become anchors for the existing chain fit** | The Riyu packet's step 3 anchored 74 of 168 bones on landmarks and carried 94 on donor proportion. Every derived joint is a new anchor, and they land exactly where the landmarks were silent. The donor keeps supplying only what it is genuinely authoritative about — digits and relative proportion inside a chain |
| Both, as separate artifacts | What exists today: `parts/skeleton.json` beside the fitted rig, drawn in the same viewer. Costs nothing to keep while the question is open |

*Proposal:* anchors, not a replacement. *Confidence:* **medium** — it is the
reading that makes phase 2 useful to the Riyu packet immediately, but the
number that would settle it (how many of the 94 carried bones a derived joint
actually anchors) has not been measured.

## Design Decisions

Set under maintainer clearance rather than left open, with the reasoning
recorded so any of them can be reversed on evidence.

**DD-001 — The voxel grid is the substrate.** Not the surface, not a point
cloud. It is what makes shell soup irrelevant, and every later phase
(geodesics, watershed, weight diffusion) needs the same grid.
*Reversible if:* memory at the resolution required for thin membranes proves
prohibitive.

**DD-002 — Boundaries and names stay separate.** A segmenter that returns
anonymous regions is still useful. Naming is a separate, much smaller problem.
*Consequence:* class-agnostic hosted models (Hunyuan3D-Part) are usable without
prompt engineering.

**DD-003 — The donor's authored rig is the answer key, and it is called a
reference rather than ground truth.** Free, dense, and already measured; the
alternative, hand annotation, is the thing this packet exists to avoid.
*Weakened in flight:* per-vertex weights cannot label the browser model
because glTF export splits vertices at seams, so the reference is seeded from
authored bone segments instead — a part boundary therefore sits midway between
bones rather than where the weights cross over. Calling that ground truth
would overstate it.
*Known limit:* one donor of unknown provenance. Nothing derived leaves the
private workspace, and a single donor cannot establish what generalizes.

**DD-004 — Bone-to-part mapping resolves by ancestry, not by name.** The donor
reuses `DEF-Finger_3.L` on both a hand and a foot; only the hierarchy
disambiguates them. So ~30 rules name part *roots*, and every bone takes the
part of its nearest matching ancestor. All 168 bones are covered by 31 rules,
and a bone matching no rule is an error rather than a silent default.

**DD-005 — No local neural network.** Established by probe, not preference: the
machine has no CUDA. Neural segmentation is hosted or absent.

**DD-006 — Seeds are pluggable and both sources are reported.**
`--seeds landmarks` uses the 21 geometric landmarks and is **donor-independent**
— the route toward a from-scratch skeleton. `--seeds skeleton` uses the fitted
skeleton's bones and is richer but inherits the donor. Comparing the two on the
donor measures exactly what the donor-independent route gives up, which is the
number that decides whether phase 2 is realistic.

**DD-007 — The volume is transported to the browser as a decimated grid, not a
mesh.** A pooled display grid of linear indices plus part indices is a few
hundred kilobytes; a box mesh of the same voxels is tens of megabytes. The
full-resolution grid stays on disk and is never served.

**DD-012 — A derived skeleton gets its own schema.**
`charctx.derived-skeleton/v1`, not `charctx.fitted-skeleton/v1`. The fitted
schema requires a `donor_id` because a fitted skeleton *is* a donor hierarchy
moved onto a target; this one has no donor at all, and forcing a null into that
field would blur exactly the distinction the packet is trying to establish. A
donor may still be used to *score* it, which is a different relationship and is
recorded in `derivation` rather than in the identity.

**DD-008 — Phase 1 ships nothing learned.** Every number in it is reproducible
from the same inputs with no model, no network call and no quota. A learned
method that cannot beat a deterministic baseline is not worth its complexity,
and there is no baseline until this one exists.

## Dependencies

**DEP-001 — `scikit-image`. Approved 2026-08-30.**

*Ceiling without it:* phase 2 has no medial axis, so a labelled region cannot
become a bone; and the head/neck boundary can only be held by adding landmarks
by hand, one ridge at a time.

*Alternatives:* writing 3D skeletonization out by hand (a thinning algorithm
with a correctness burden nobody here can discharge); staying with the
uniform-cost flood already implemented (works, but 6-connected unit steps
distort diagonal distances, and it has no compactness term to stop a region
running along a ridge).

*Probe, on this platform against real data:*

| Call | Measured |
| --- | --- |
| `morphology.skeletonize` (3D) | 0.01 s — a bent tube, 8,887 voxels → 61 spanning its full length |
| `graph.MCP_Geometric` | 0.03 s, reached 8,887/8,887 — true Euclidean geodesics, not 6-connected steps |
| `segmentation.watershed(compactness=…)` | 1.64 s on 64³ — the principled version of the fix that phase 1b made by hand |
| `measure.marching_cubes` | 0.02 s → 6,744 verts |

*Blast radius:* pulls `imageio`, `lazy-loader`, `pillow`, `tifffile`. Removing
it would cost phase 2's medial axes and phase 4's view rendering; nothing
already shipped depends on it.

**DEP-002 — `libigl`. Rejected 2026-08-30, on evidence.**

It resolves (`libigl==2.6.2`) and then does not install: there is no Windows
wheel for Python 3.12, so `uv` falls back to the source distribution and the
build dies on `CMAKE_C_COMPILER not set` with no `nmake` present. It would
have given generalized winding number and bounded biharmonic weights. Not
painful today — the flood-fill containment works and reports whether it
actually filled. Revisit only with MSVC Build Tools installed, or if phase 3
skinning specifically needs BBW.

This is the case the workflow's "probe, not a citation" rule exists for: the
dependency resolved cleanly in a dry run and would have been recommended on
that basis alone.

**DEP-003 / DEP-004 — deferred.** `scikit-learn` is phase 5 only, and
`scipy.cluster` covers the clustering in use. `rtree` / `embreex` /
`manifold3d` address a bottleneck this packet does not have (voxelizing Riyu
takes ~3 s) and mesh repair is irrelevant while the substrate is voxels.

## Risks

- **Thin wing membranes vanish at low grid resolution.** A membrane a few
  millimetres thick disappears at a coarse pitch, taking the wing's part
  boundary with it. Mitigated by reporting occupancy per part and flagging any
  part whose voxel count collapses; a membrane-aware anisotropic pitch is the
  fallback.
- **Geodesic watershed leaks across touching surfaces.** A wing folded against
  a flank, or a tail curled against a leg, connects two parts through a thin
  isthmus and the flood crosses it. Detectable — the leak shows as a part with
  a disconnected component — and reportable.
- **One donor.** DD-003's limit is real: everything measured here is measured
  against a single rig whose provenance is unknown.
- **The taxonomy is a commitment.** 29 parts chosen now will shape phases 2–5.
  It is a durable spec precisely so that changing it is a visible act.
- **Voxel fill assumes the surface closes at grid resolution.** Usually true and
  the reason voxelization helps at all, but a large genuine hole would let the
  fill leak inward. Reported as an occupancy ratio that a human can sanity-check.

## Exit Criteria (Phase 2)

- A labelled volume yields a bone hierarchy with a joint at every region
  boundary, written as `charctx.derived-skeleton/v1`.
- Every joint the donor's rig places is **measured**, not asserted: per-joint
  error in world units and as a fraction of the body diagonal, against the
  donor's own authored bones.
- The nine joints the landmark route was structurally silent about — both
  elbows, both wrists, both knees, both wing elbows, and the jaw hinge — each
  carry a number.
- The hierarchy question is settled by measurement rather than by preference:
  the adjacency-derived tree is computed on every run and its disagreements
  recorded.
- Every phase-2 open point names a proposal and a confidence, and appears in
  the global decision table in `plans/open.md`.
- The derived skeleton is visible in the local viewer beside the authored rig.
- Repository tests, Ruff, and Astro check/build pass; `test.md` records the
  commands and the numbers.

## Exit Criteria (Phase 1)

- `western-dragon-parts/v1` exists as a durable specification with 29 named
  parts and a total, ancestry-resolved mapping from all 168 donor bones.
- The donor carries a ground-truth labelled volume derived from its own weights.
- Riyu carries a classified volume produced without any donor label.
- The segmentation method has a **measured** per-part IoU and overall accuracy
  against the donor reference — not an assertion that it looks right.
- Both volumes are visible as coloured voxels in the local viewer.
- Repository tests, Ruff, and Astro check/build pass; `test.md` records the
  commands, the numbers, and the gaps.
