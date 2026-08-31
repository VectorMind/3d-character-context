# Specification — Body-Part Taxonomy And Labelled Volumes

Status: Binding for part labelling, volumetric segmentation, and any skeleton
derived from either.

Covers the standardized western-dragon part taxonomy, the part hierarchy, the
contract for a labelled volume, the contract for a skeleton derived from one,
and the rule by which a source rig's bones map onto parts.
Implementation schedules live in
`plans/2026-08/30-body-part-labeling/`.

## Problem

A landmark is a point estimate over a mesh of hundreds of thousands of
vertices. Twenty of them describe a dragon thinly, so every joint between them
is an interpolation and every interior joint is unavailable. A *dense* label —
every part of the volume assigned to a named body part — replaces point
estimates with majority votes and turns "where is the elbow" into "where do two
regions meet", which is a stable question.

This specification fixes the region definitions that
`specifications/README.md` lists as required before canonicalization or
non-rigid fitting.

## The Taxonomy: `western-dragon-parts/v2`

Twenty-nine body parts plus five head sub-parts. Of the twenty-nine, nine are
unpaired and lie on the symmetry plane and ten are paired, carrying a `.L` /
`.R` suffix.

### Axial parts (9, unpaired)

| Part | Covers |
| --- | --- |
| `head` | Cranium, snout, eyes, upper teeth — everything rigid to the skull |
| `jaw` | Lower jaw and lower teeth — the one part of the head that articulates separately |
| `neck` | Skull base to the shoulder girdle |
| `chest` | Shoulder girdle and rib cage; both forelimbs and both wings attach here |
| `abdomen` | Between the girdles |
| `pelvis` | Hip girdle; both hindlimbs and the tail attach here |
| `tail_base` | Thick tail, from the pelvis |
| `tail_mid` | Tapering mid-tail |
| `tail_tip` | Thin distal tail |

### Appendicular parts (10, paired — 20 total)

| Part | Covers |
| --- | --- |
| `shoulder` | Clavicle/collar linking chest to forelimb |
| `upper_arm` | Humerus segment |
| `forearm` | Radius/ulna segment |
| `hand` | Palm, digits, claws of the forelimb |
| `thigh` | Femur segment |
| `shin` | Tibia segment |
| `foot` | Tarsus, toes, claws |
| `wing_root` | Scapula and wing base — the wing's attachment to the chest |
| `wing_arm` | The wing's proximal spar, to the wing elbow |
| `wing_hand` | The wing's distal spars and the membrane they carry |

### Head sub-parts (5)

| Part | Parent | Covers |
| --- | --- | --- |
| `nostril` | `head` | The nose opening |
| `eye.L` / `eye.R` | `head` | Eyeball, iris and lids |
| `ear.L` / `ear.R` | `head` | Ear or the ear-position horn |

Sub-parts exist because a part seeded by points on a medial curve cannot hold
a bulb against a neighbour seeded higher on a shared ridge: `head` was losing
its crown to `neck`. Features on the head's own surface are the natural
anchors, and they are also the features a person -- or a vision model reading
a rendered view -- can name reliably, which a mid-neck cross-section is not.

A sub-part **refines** its parent; it does not remove the region from it. A
labelled volume therefore reports both readings: the fine count for each part
on its own, and a `coarse_voxels` roll-up in which a sub-part's voxels are
added back to its parent. "Is this the head" and "is this the eye" are
different questions and both have to be answerable.

### The Part Hierarchy

The taxonomy declares which part each part hangs from, and that declaration is
part of the contract rather than something a run derives. `pelvis` is the root;
`abdomen` hangs off it, `chest` off `abdomen`, `neck` off `chest`, `head` off
`neck`, `jaw` and the head sub-parts off `head`; the tail chain runs
`tail_base` → `tail_mid` → `tail_tip` off `pelvis`; each forelimb runs
`shoulder` → `upper_arm` → `forearm` → `hand` off `chest`; each hindlimb runs
`thigh` → `shin` → `foot` off `pelvis`; each wing runs `wing_root` →
`wing_arm` → `wing_hand` off `chest`.

It is declared rather than derived because the hierarchy is a property of the
body plan, not of one mesh: `forearm.L` hangs off `upper_arm.L` for every
western dragon there will ever be, in the same way that a dragon has two wings.
Deriving it from region adjacency was measured and does not hold: contact area
cannot distinguish a joint from a *fold*, where two parts touch along a large
area without articulating.

Declaring the hierarchy is not the same as borrowing a skeleton. Nothing about
*where* a joint sits comes from a source rig; only the question of what hangs
off what is answered in advance.

Two rules make the declaration safe to depend on:

- It is **total and acyclic**: every part reaches the root, and only the root
  has no parent.
- A part whose declared parent is absent from a labelled volume **climbs its
  own declared chain** to the nearest present ancestor it actually touches, and
  the climb is recorded. It is never silently reparented to whatever it happens
  to be next to.

### Rules

- A part name is `<part>` for an axial part and `<part>.L` / `<part>.R` for a
  paired one. No other suffix is valid.
- A sub-part declares its `parent`; a top-level part declares `null`. Nesting
  is one level deep, because two levels would invite a hierarchy nobody can
  measure.
- The taxonomy is **total**: every solid voxel of a labelled volume carries
  exactly one part, or the explicit `unlabelled` sentinel (index 0).
- Part indices are stable within a taxonomy version. Adding a part requires a
  new version; renaming or re-indexing one always does. v2's sub-parts were
  **appended** at indices 30-34 rather than interleaved, so every v1 index
  still means what it meant and adding them could not silently relabel a
  stored volume.
- `wing_arm` and `wing_hand` deliberately do not name a "membrane" part. The
  membrane is carried by the spar that deforms it, because a membrane has no
  independent articulation and giving it a part would imply one.

## Bone-To-Part Mapping

A source rig names bones for the rigger's convenience, not for anatomy, and the
same name is reused in different places: `european-dragon` carries
`DEF-Finger_3.L` on a hand and `DEF-Finger_3.L.001` on a foot. **Name matching
cannot separate them; only the hierarchy can.**

The mapping is therefore defined by **part roots** and resolved by ancestry:

1. A small table names the bone at which each part *begins*.
2. Every bone takes the part of its nearest ancestor present in that table,
   itself included.
3. A bone whose ancestry reaches a root without matching any rule is an
   **error**, never a silent default. A taxonomy that quietly absorbs unmapped
   bones cannot be trusted to be total.

This keeps the table proportional to the taxonomy (about thirty rules) rather
than to the rig (168 bones), and it survives a donor that subdivides a chain
differently.

## Labelled-Volume Contract

Schema `charctx.part-volume/v1`. A labelled volume is derived geometry and is
never a faithful record of a source asset; `derivation` states how it was
produced, in the same discipline as `charctx.fitted-skeleton/v1`.

Required:

- `taxonomy` — the taxonomy version the labels belong to.
- `grid` — resolution, pitch, and origin, so a voxel index is convertible to a
  world position without re-deriving anything.
- `parts` — for each part present: name, stable index, display colour, `parent`
  (null for a top-level part), and voxel count. A part with zero voxels is
  listed with a zero count rather than omitted, so a missing part is visible
  instead of inferred.
- `voxels` — the display grid, as linear indices plus part indices.
- `derivation` — method, seed source, and every limitation that applies. It
  also separates **absent by construction** from **misplaced**:
  `unseedable_parts` are parts no seed can reach, `seeded_but_empty` are parts
  that had a seed and still lost, and `split_parts` names any part the flood
  left in more than one piece.
- `summary` — solid voxel count, occupancy ratio, labelled fraction, and
  `coarse_voxels`, the roll-up in which each sub-part's voxels are added back
  to its parent.

### Reference versus proposal

Two kinds of labelled volume exist and must stay distinguishable:

- **A reference** is derived from a source rig's own authored data. It is the
  closest thing to an answer key available, and the only thing another method
  may be scored against.
- **A proposal** is derived from target geometry alone. It carries whatever
  accuracy a scored run measured, and it never becomes a reference by being
  good.

`derivation.reference` is a required boolean.

The word is **reference**, not ground truth, and the difference is not
cosmetic. The intended source was per-vertex skin weights, which would have
been ground truth in the strict sense. That does not survive glTF export:
vertices split at UV and normal seams, so the browser model carries no
correspondence to the weight document. The reference is seeded from the rig's
authored **bone segments** instead — authored, but a step removed from the
weights, so a part boundary sits midway between bones rather than where the
authored weights actually cross over. Calling that ground truth would overstate
it.

A run that scores a proposal against a reference records per-part IoU, not a
single aggregate: an overall accuracy dominated by a large torso hides a wing
that was missed entirely.

## Derived-Skeleton Contract

Schema `charctx.derived-skeleton/v1`. A skeleton read out of a labelled volume,
with **no donor behind it**. It is a separate schema from
`charctx.fitted-skeleton/v1` because that one requires a `donor_id` — a fitted
skeleton *is* a donor hierarchy moved onto a target — and this one has none. A
source rig may still be used to *score* a derived skeleton, which is a
different relationship and is recorded in `derivation`, never in the identity.

Three things go into it and they are not equally trusted:

- **Joints are measured.** A joint is the boundary between two labelled
  regions: the centre of the voxel faces separating them, weighted by each
  face's distance to the surface. The weighting is not cosmetic — a real joint
  is a *cross-section* through a limb and a fold is a *crease* at the skin, and
  by area alone the two are indistinguishable.
- **The hierarchy is declared**, by the part hierarchy above. Region adjacency
  is derived on every run as a maximum-contact spanning tree and reported
  beside it; a disagreement is a finding about the mesh, not a hierarchy to
  adopt.
- **Roll is not derived.** An occupancy grid carries no twist signature, so
  every bone reports roll 0 and the document says so.

A bone runs from the joint with its parent to the joint with its farthest
child, so a bone's tail *is* its child's head and the chain is connected. A
part with no children runs to the far end of its own region, measured through
the region rather than across the air. The root part has no parent to start
from, so the taxonomy names where its bone begins.

Required in `derivation`:

- `method`, and the `source` describing how the volume was labelled;
- `attachment` — for every part, the parent it ended up on and whether that was
  `declared`, `reattached` (its declared parent was absent or out of contact)
  or `detached`;
- `adjacency_check` — the adjacency-derived tree and every place it disagrees
  with the hierarchy in force;
- `absent_parts`, `degenerate_bones`, and every limitation that applies.

A derived skeleton is scored against a source rig by **per-joint position
error**, in world units and as a fraction of the body diagonal — never by a
single aggregate. Where a source rig attaches a part at more than one place,
the score reports the spread between those attachment points: a part with two
genuine attachment points has no single true joint, and a score that averages
them is claiming a precision the answer key does not have.

## Transport

The full-resolution grid is a computation artifact and is **not** served to the
browser. A pooled display grid is, encoded as linear indices plus part indices —
a few hundred kilobytes, against tens of megabytes for the equivalent box mesh.

This follows the existing rule that skin weights are catalog metadata rather
than a browser artifact: the browser receives a diagnostic, never the raw
volumetric data.

## Acceptance Criteria

- Every one of a donor's bones maps to exactly one part, by ancestry, with no
  unmapped bone.
- Every solid voxel of a labelled volume carries exactly one part index.
- Paired parts are present on both sides, or their absence is reported.
- A proposal scored against ground truth reports per-part IoU and overall voxel
  accuracy.
- The part hierarchy is total and acyclic, and a derived skeleton reports for
  every part whether its parent was the declared one.
- A derived skeleton is scored by per-joint position error against a source
  rig, with the answer key's own ambiguity reported alongside it.
- The taxonomy and the mapping are data, inspectable through a documented
  command, and not buried in the code that consumes them.

## Landmarks That Geometry Will Not Propose

Eyes, ears and nostrils have no reliable signature in a vertex cloud -- a
socket is a dimple on one model and a bulge on the next, and on a stylised
character the eye is often painted rather than sculpted, so it has no
geometry at all. They are obvious to anyone looking at a rendered view.

So they are **asserted, not inferred**, through an overlay file beside the
proposal (`skeleton/landmarks.manual.json`), whose entries a person or a
vision model supplies. Two rules make the overlay safe to depend on:

- A manual point always wins over a proposal, because it is evidence and a
  proposal is not. It is recorded with `source: manual` so the two never blur.
- The overlay may only set names on a declared allow-list. An overlay that
  accepts any name is an overlay that turns a typo into geometry.

## Non-Goals

- Facial parts beyond the head sub-parts above. Individual teeth and lids ride
  with the skull; separating them serves animation, not rigging.
- Nesting more than one level deep.
- Individual digits. A `hand` is one part; naming five fingers multiplies the
  taxonomy by an amount no current method can measure.
- Non-dragon body plans. A quadruped-with-wings taxonomy is not a general
  articulated-object taxonomy and does not pretend to be.
