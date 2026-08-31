# Test Proof — Volumetric Body-Part Labeling

## Status

Phase 1 complete and measured; phase 1b (head sub-parts) likewise. Phase 2
(skeleton from the classification) complete and measured on `european-dragon`,
recorded at the end of this file. Phases 3–5 pending.

Phase 1's numbers below are the readings **as they stood at the time**, kept
rather than overwritten: the head/neck defect phase 1b fixed is only legible
against them.

## Fixtures

- `european-dragon` — reference rig and validation set. 168 bones, all
  weight-bearing, 5 actions / 332 frames of pose data (unused in phase 1).
- `trellis2/ninjago-riyu-001` — the target. 203,745 vertices, **6,209
  connected components**, not watertight.
- Synthetic capsule + three-bone spine, built in `tests/` — no data committed.

## Access And Hardware, Established By Probe

| Fact | Value | Probed |
| --- | --- | --- |
| Local GPU | Intel Arc 140V (16 GB), **no CUDA** | `Get-CimInstance Win32_VideoController` |
| PartField requirement | PyTorch 2.4 + CUDA 12.4 | project README |
| `tencent/Hunyuan3D-Part` | `RUNNING`, `zero-a10g`, gradio | HF spaces API |
| Its API | `/segment(mesh_path, postprocess, postprocess_threshold, seed)` → `(mesh, face-id map)` | `gradio_client.view_api` |
| `nvidia/PartField`, `Pointcept/SAMPart3D`, `yhyang-myron/SAMPart3D` | HTTP 401 | HF spaces API |

Consequence: neural part segmentation is hosted or absent. Phase 1 needed no
new dependency at all — numpy 2.5, scipy 1.18, trimesh 5.0 were already
installed.

## Phase 1 Proof

### The taxonomy

```powershell
uv run charctx parts taxonomy
```

| Fact | Value |
| --- | --- |
| Taxonomy | `western-dragon-parts/v1` (v2 at phase 1b) |
| Parts | **29** — 9 axial, 10 paired |
| Donors mapped | `european-dragon` |
| Part rules | 31, covering all **168** bones |
| Rules the rig never presents | **0** |
| Bones reaching the root unmapped | **0** |
| Weight-bearing bones unmapped | **0** of 168 |

The last three are the totality claim, and all three are measured rather than
asserted.

### The substrate — the packet's central claim

```powershell
uv run charctx parts reference european-dragon
uv run charctx parts segment trellis2/ninjago-riyu-001
```

| Fact | donor | Riyu |
| --- | --- | --- |
| Input surface | 21,050 verts, 5 meshes | 203,745 verts, **6,209 shells** |
| Surface samples drawn | 331,015 | 941,196 |
| Shell voxels after closing | 16,490 | 31,143 |
| Interior voxels found | 2,754 | 12,881 |
| `filled` | **True** | **True** |
| **Solid components** | **1** | **1** |
| Occupancy of the 128³ grid | 0.9% | 2.1% |
| Labelled fraction | **100%** | **100%** |
| Parts present | **29/29** | 20/29 |
| Parts split across components | **0** | **0** |
| Display voxels shipped | 3,913 | 6,874 |
| Served artifact size | 105,360 B | 181,420 B |

**Riyu's 6,209 disconnected shells voxelize to one solid component.** That is
the finding the whole packet rests on, and it holds at the first attempt.

### Riyu's classified volume

| Part | Voxels | | Part | Voxels |
| --- | --- | --- | --- | --- |
| `tail_base` | 5,470 | | `wing_root.L` / `.R` | 2,170 / 2,147 |
| `tail_mid` | 3,842 | | `thigh.L` / `.R` | 2,601 / 2,560 |
| `abdomen` | 3,652 | | `foot.L` / `.R` | 1,789 / 1,745 |
| `shoulder.R` / `.L` | 3,034 / 2,668 | | `hand.L` / `.R` | 1,407 / 1,411 |
| `neck` | 2,632 | | `head` | 918 |
| `pelvis` | 2,320 | | `tail_tip` | 874 |
| `chest` | 1,782 | | `wing_hand.L` / `.R` | 485 / 517 |

Absent, all nine of them because no landmark stands for them: `jaw`,
`upper_arm.L/R`, `forearm.L/R`, `shin.L/R`, `wing_arm.L/R`.

Two things to read here rather than skip:

- **`wing_root` outweighs `wing_hand` 4.5 to 1** (2,170 against 485). The wing
  root seed sits on the body, so its region absorbs both the shoulder mass and
  the inner half of the membrane, while the tip seed only reaches the outer
  edge. A landmark at the wing elbow would fix it; there isn't one.
- **`shoulder` is 14% asymmetric** (3,034 right against 2,668 left) where every
  other pair agrees within 3%. Worth a look in the viewer.

### The scored ablation

```powershell
uv run charctx parts score european-dragon --mode centroid
uv run charctx parts score european-dragon --mode landmarks
```

| Seeding | Seed points | Voxel accuracy | Mean IoU | Median IoU |
| --- | --- | --- | --- | --- |
| Reference (authored bones) | 1,922 | — | — | — |
| **Part centroids, one per part** | 29 | **81.5%** | **0.702** | 0.697 |
| **Geometric landmark proposal** | 19 | **28.8%** | **0.066** | 0.000 |

Centroid seeding, worst and best:

| Worst | IoU | | Best | IoU |
| --- | --- | --- | --- | --- |
| `wing_arm.L` / `.R` | 0.47 / 0.47 | | `hand.L` / `.R` | 0.96 / 0.96 |
| `wing_root.R` | 0.52 | | `tail_mid` | 0.88 |
| `pelvis` | 0.52 | | `foot.R` | 0.88 |
| `jaw` | 0.52 | | | |
| `chest` | 0.55 | | | |

Every worst case is an *interior* chain segment with a neighbour on both sides;
every best case is an extremity with only one. **Sparsity costs roughly 30% IoU
and costs it exactly where the Riyu packet already had no landmarks.**

### Why the landmarks number is about the proposer, not the segmenter

Running the geometric proposer on the donor directly:

| Fact | Value |
| --- | --- |
| Ground-contact clusters found | **3** (expected 4) |
| Landmarks produced | **19** (Riyu: 21) |
| Missing | `foot_hind.L`, `hip.L` — **asymmetrically** |
| Parts left with no seed | 11 |
| Parts missed entirely | 12 |

The donor's rest pose is rearing, so its forelimbs are off the ground and the
ground-contact heuristic under-counts. The proposer assumes a standing
quadruped and degrades silently when that is false — which is a measured limit
of the *seed source*, not of the watershed.

### The structural gap

| Fact | Value |
| --- | --- |
| Parts in the taxonomy | 29 |
| Parts any landmark stands for | 20 |
| **Parts landmark seeding cannot produce at all** | **9** |

`jaw`, `upper_arm.L/R`, `forearm.L/R`, `shin.L/R`, `wing_arm.L/R`. Absent by
construction, not misplaced — which is why the output separates
`unseedable_parts` from `seeded_but_empty`.

### Two defects the implementation exposed, both fixed

1. **The voxel fill leaked and returned a hollow shell.** A fixed 400,000-sample
   surface splat leaves pinholes by the coupon collector's problem, and one
   missing voxel lets the exterior flood into the interior. Caught by a unit
   test asserting the centre of a sphere is solid — the real donor happened to
   have enough samples to hide it. Sample count is now derived from surface
   area and pitch (`area / pitch² × 24`), and the report carries `filled` and
   `interior_voxels` so a future leak is visible.
2. **The bone-to-part mapping refused legitimate partial rigs.** The first
   version raised when a rule named a bone the rig lacked. A rig that is a
   subset of the family the rules describe is legitimate, so unused rules are
   now reported and only the other direction — a bone matching no rule — stays
   fatal.

### Web proof

| Request | Expected | Actual |
| --- | --- | --- |
| `/api/generation/.../parts/parts.json` | 200 JSON | **200**, 181,420 B |
| `/api/artifact/european-dragon/parts/parts.json` | 200 JSON | **200**, 105,360 B |
| `/api/generation/.../parts/manifest.json` | 404 — stage marker is not a browser artifact | **404** |
| Riyu viewer island | carries `partUrl` | **Pass** |
| Donor viewer island | carries `partUrl` | **Pass** |
| Asset card | `parts: parts/parts.json` | **Pass** |

### Repository checks

`uv run pytest` **139 passed, 1 live skipped** (27 new: 10 taxonomy, 10 voxel,
7 volume) · `uv run ruff check .` clean · `pnpm check` 0 diagnostics · Astro
build passes.

## Known Gaps

- The reference is seeded from authored **bone segments**, not per-vertex
  weights: glTF export splits vertices at seams (21,050 against 19,172), so no
  correspondence exists. A part boundary therefore sits midway between bones
  rather than where the authored weights actually cross over.
- One donor, of unknown provenance. Nothing here establishes what generalizes
  to a second dragon.
- The 332 frames of donor animation are untouched. They are the synthetic
  corpus phase 5 would need.
- No neural method has been run. `tencent/Hunyuan3D-Part` is probed and live
  but unmetered work against it is deferred to phase 4, after a deterministic
  baseline exists — which it now does.
- The interactive browser click-through was not run; no browser-control
  runtime is available.

## Phase 1b Proof — Head Sub-Parts (2026-08-30)

### The defect, measured

Review found `neck` covering the top of `head`. The measurement located it
precisely, and not where it looked:

| Fact | Value |
| --- | --- |
| Volume forward of the `skull` landmark labelled head | **100%** |
| `head` voxels | 918 |
| `neck` voxels | 2,632 |
| `neck` reached up to | y = +0.1533 |
| `head` reached up to | y = +0.1048 |

So the neck was not taking the snout or the eyes; it was taking the **crown**,
and the cause was in `y`: `neck_base` at y=+0.074 sat on the dorsal crest,
above `skull` at y=+0.039.

### The occiput is measurable

Cross-section profile between the chest and the snout, near the midline:

| z | area proxy | |
| --- | --- | --- |
| +0.409 | 0.00565 | |
| **+0.412** | **0.00380** | **local minimum — 39% below both shoulders** |
| +0.416 | 0.00622 | |

Global minimum is the snout tip at 0.00091, which is why the test is for a
*local* minimum. Runner-up candidate depth: 0.039 against the winner's 0.151
under the shipped window.

### Two things the loop had to fix before it worked

| Pass | Symptom | Cause | Fix |
| --- | --- | --- | --- |
| 1 | Occiput not found at all | Waist is ~1 bin wide, so disjoint bins smeared it — a 0.01 shift in the profile's start took depth from 39% to 13% | Overlapping moving window |
| 2 | `head_base` and `neck_base` on the same voxel | Medial curve sampled in 48 bins over the whole body; both snapped to one sample | `_at` interpolates instead of snapping |
| 3 | `head` ran back to z=+0.28, into the shoulders | `head_top` sat on the descending flank of the *neck's* crest, which peaks at z=+0.355 behind the occiput | `neck_top` anchors the neck's own ridge; the head's crown is measured 25% forward of the occiput |

Window sweep, which set the shipped value:

| Window | Occiput z | Depth | Runner-up | Margin |
| --- | --- | --- | --- | --- |
| 1/25 | +0.4091 | 0.065 | 0.056 | 1.2× |
| **1/40** | **+0.4114** | **0.151** | **0.039** | **3.9×** |
| 1/60 | +0.4122 | 0.180 | 0.150 | 1.2× |
| 1/80 | +0.4122 | 0.393 | 0.182 | 2.2× |
| 1/120 | +0.4122 | 0.334 | 0.284 | 1.2× |

Chosen on **margin**, not depth: narrower windows recover the dip but multiply
the noise minima around it. Every width agrees the occiput is at z≈0.409–0.412,
so the location is stable even where the depth measure is not.

### Result on Riyu

| | before | after |
| --- | --- | --- |
| `head` | 918 | **2,045** |
| `neck` | 2,632 | 1,876 |
| Forward of `skull`, labelled head | 100% | 100% |
| Parts split across components | 0 | **0** |

`split_parts` is empty at full resolution: the ragged head/neck interleaving
visible in the viewer is the pooled **display** grid, where majority-voting
2×2×2 blocks along any boundary alternates winners. It is not in the
segmentation.

### Sub-parts

| Fact | Value |
| --- | --- |
| Taxonomy | `western-dragon-parts/v2`, **34 parts** |
| Sub-parts | `nostril`, `eye.L`, `eye.R`, `ear.L`, `ear.R`, all parented to `head` |
| v1 indices changed | **0** — sub-parts appended at 30–34 |
| Donor parts present | **31/34** (`eye.L` 76, `eye.R` 105 voxels) |
| Donor parts empty | `nostril`, `ear.L`, `ear.R` — the rig has no such bones |
| Donor `head` fine / coarse | 230 / **411** (the difference is the two eyes) |
| Donor connectivity flag | `eye.L` split into 2 components |
| Riyu sub-parts present | **0** — no overlay supplied |

Donor score after the change: **81.3% voxel accuracy, mean IoU 0.686 over 31
parts** (was 81.5% / 0.702 over 29). The small drop is the two eyes entering
the average at IoU 0.33 — tiny parts are harder, and the mean now includes them.

### Manual overlay

`skeleton/landmarks.manual.json`, merged at proposal time.

| Behaviour | Verified by |
| --- | --- |
| Adds a landmark geometry never proposes (`eye.L/R`) | `test_the_manual_overlay_overrides_a_proposal_and_adds_what_geometry_cannot` |
| Overrides a proposal, recorded as `source: manual` | same |
| Refuses a name outside the allow-list | `test_the_manual_overlay_refuses_a_landmark_it_may_not_set` |

**Riyu's eyes are not supplied.** Nothing in this session could see them, and
inventing coordinates would be the same guess the packet refuses everywhere
else. The mechanism is tested; the points need a vision-model pass or a person.

### Repository checks

`uv run pytest` **148 passed, 1 skipped** · `uv run ruff check .` clean ·
`pnpm check` 0 diagnostics · Astro build passes.

### New known gaps

- The occiput test has been exercised on exactly one generated dragon and one
  synthetic rod. `OCCIPUT_DEPTH = 0.08` is set from that single sweep.
- The donor's `eye.L` is split into two components; not investigated.


## Phase 1c Proof — scipy.signal And Reproducibility (2026-08-30)

### The import block was transient

| Module | Earlier | Now |
| --- | --- | --- |
| `scipy.ndimage`, `scipy.spatial`, `scipy.sparse.linalg` | OK | OK |
| `scipy.integrate` | **blocked** (`_quadpack` DLL, application-control policy) | **OK** |
| `scipy.signal` | **blocked** (imports `scipy.integrate`) | **OK** |

### The swap is behaviour-preserving, verified before making it

| Implementation | Occiput z | Depth | Runner-up |
| --- | --- | --- | --- |
| Hand-rolled numpy scan | +0.41142 | 0.1505 | 0.0388 |
| `scipy.signal.peak_prominences` | +0.41142 | 0.1505 | 0.0388 |

Identical, so every number recorded for phase 1b stands. scipy's is the
stricter measurement: it takes a valley's shoulder as the highest ground
before the nearest **deeper** valley, rather than the maximum over the whole
profile, which is what keeps a second waist from being measured against the
first one's shoulder.

### Voxelization was not reproducible, and now is

Surface sampling is random and was unseeded:

| Run | `head` | `neck` |
| --- | --- | --- |
| Before, run 1 | 2,045 | 1,876 |
| Before, run 2 | 2,039 | 1,876 |
| **After (seeded), run 1** | **2,049** | **1,877** |
| **After (seeded), run 2** | **2,049** | **1,877** |

A few voxels of drift, but enough that no recorded count was a measurement.
`voxelize(seed=0)` is now the default and the seed is recorded in the report.

### Repository checks

`uv run pytest` **148 passed, 1 skipped** · `uv run ruff check .` clean ·
`pnpm check` 0 diagnostics · Astro build passes.


## 2026-08-31 — Phase 2: skeleton from the classification

### Commands

```
uv run charctx parts skeleton european-dragon
uv run charctx parts skeleton-score european-dragon
uv run charctx parts skeleton-score european-dragon --seeds centroid
uv run charctx parts skeleton-score european-dragon --seeds landmarks
uv run charctx parts skeleton trellis2/ninjago-riyu-001 --seeds landmarks
uv run pytest ; uv run ruff check . ; pnpm check ; pnpm build
```

All at the default 128³ grid, pitch 0.16630, seed 0. `european-dragon`'s body
diagonal in viewer space is **26.245**, so 1% of it is 1.58 model units or
about 9.5 voxels; 0.1% is roughly one voxel.

### What the skeleton step alone is worth

`--seeds reference` labels the volume from the donor's own authored bone
segments and then reads a skeleton back out of it. It isolates the phase-2
question — *given a good labelling, how well does a region boundary locate a
joint?* — from the phase-1 question of how good the labelling is.

```
skeleton score: european-dragon (reference seeding)
  bones     : 31 bones, 30 joints scored against the donor rig
  hierarchy : 31/31 declared parents match the donor; adjacency alone agrees on 27
  joint err : median 0.70% of the body diagonal, mean 1.62% (2.562 voxels), max 13.31%
  unambiguous: median 0.63% over 27 joints the donor places at one point
  bone axis : median 5.42deg
  worst     : wing_hand.R 13.3%, wing_hand.L 12.8%, wing_arm.L 2.1%, wing_arm.R 2.1%, thigh.R 1.7%, thigh.L 1.4%
  best      : neck 0.1%, chest 0.3%, forearm.L 0.3%, forearm.R 0.3%, tail_mid 0.4%, hand.L 0.4%
```

Per joint (left side shown; right agrees to within 0.3 percentage points except
where noted):

| Bone | Joint error | in model units | Tail error | Axis angle |
| --- | --- | --- | --- | --- |
| `neck` | 0.14% | 0.0362 | 0.63% | 4.1° |
| `chest` | 0.30% | 0.0793 | 0.14% | 2.4° |
| `forearm.L` (**elbow**) | 0.33% | 0.0866 | 0.37% | 4.3° |
| `hand.L` (**wrist**) | 0.37% | 0.0976 | 0.56% | 4.9° |
| `tail_mid` | 0.37% | 0.0966 | 0.40% | 1.3° |
| `abdomen` | 0.38% | 0.0986 | 0.30% | 1.7° |
| `tail_tip` | 0.40% | 0.1042 | 0.95% | 2.7° |
| `upper_arm.L` (shoulder) | 0.56% | 0.1469 | 0.33% | 1.0° |
| `foot.L` (ankle) | 0.62% | 0.1640 | 0.63% | 2.0° |
| `head` (occiput) | 0.63% | 0.1650 | 2.02% | 20.0° |
| `pelvis` (root) | 0.68% | 0.1788 | 2.69% | 62.9° |
| `tail_base` | 0.68% | 0.1788 | 0.37% | 0.6° |
| `shin.L` (**knee**) | 0.75% | 0.1958 | 0.62% | 5.7° |
| `shoulder.L` | 0.76% | 0.1985 | 0.98% | 12.7° |
| `wing_root.L` | 0.90% | 0.2365 | 2.12% | 4.1° |
| `jaw` (**hinge**) | 1.12% | 0.2945 | 0.60% | 8.4° |
| `eye.L` | 1.27% | 0.3336 | 11.80% | 160.0° |
| `thigh.L` (hip) | 1.41% | 0.3710 | 0.75% | 15.6° |
| `wing_arm.L` (**wing elbow**) | 2.12% | 0.5556 | 12.76% | 28.8° |
| `wing_hand.L` | **12.76%** | 3.3493 | 1.52% | 17.8° |

**The nine joints the landmark route was structurally silent about** — both
elbows, both wrists, both knees, both wing elbows, and the jaw hinge — now
carry numbers: 0.33%, 0.37%, 0.72–0.75%, 2.08–2.12%, 1.12%.

Two rows are conventions rather than errors. `pelvis`'s 62.9° axis angle is a
0.454-long root bone whose direction is noise at this pitch, and `eye.L`'s
160° tail is a blob with no meaningful long axis. `head`'s 2.02% tail is the
donor's head chain stopping behind the eyes while a derived head bone runs to
the snout — which is why leaf tails are reported apart from chained ones
(chained median **0.63%** over 20 bones).

### The cost of not having the answer key

`--seeds centroid` holds the geometry and the part set fixed and changes only
the labelling, to one seed per part at its own centre of mass:

| Seeding | Bones | Hierarchy vs donor | Joint median | mean | mean voxels | max |
| --- | --- | --- | --- | --- | --- | --- |
| Reference (authored bones) | 31 | 31/31 | **0.70%** | 1.62% | 2.56 | 13.31% |
| Part centroids | 31 | 31/31 | **1.42%** | 2.31% | 3.64 | 14.21% |
| Geometric landmarks | — | — | — | — | — | — |

Sparse labelling roughly doubles the joint error. Worst under centroid seeding
are `wing_hand` (14.2%), `tail_base` (3.6%) and `wing_arm` (3.4%); best are
`foot` (0.5%), `chest` (0.6%) and `hand` (0.6%). Against OP-208's proposed gate
— median ≤1% under donor-independent seeding, every part present — **1.42%
does not pass.**

### Landmark seeding produces no skeleton at all

```
error: The labelled volume has no 'pelvis' voxels, so the hierarchy has no root
to hang from. 17 of 34 parts are present: abdomen, chest, foot.R, hand.L,
hand.R, head, neck, shoulder.L, shoulder.R, tail_base, tail_mid, tail_tip,
thigh.R, wing_hand.L, wing_hand.R, wing_root.L, wing_root.R.
```

This is the phase-1 finding arriving at its consequence. The geometric
proposer assumes a standing quadruped; the donor is rearing, so it yields 19
landmarks instead of 21 and loses the hip cluster, and 17 of 34 parts never get
a seed. Without `pelvis` there is no root and there is no skeleton. Recorded as
OP-209.

### The hierarchy, measured both ways

A maximum-contact spanning tree over the region adjacency graph, rooted at
`pelvis`, against the donor's own part hierarchy:

| | Result |
| --- | --- |
| Declared taxonomy hierarchy vs donor rig | **31 / 31** |
| Adjacency-derived tree vs the same | **27 / 31** |

The four failures and their cause:

| Derived | Should be | Contact voxels | Why |
| --- | --- | --- | --- |
| `jaw` → `neck` | `head` | 62 | The jaw's rear rests against the neck; the true `head`–`neck` edge has only 49 |
| `wing_root.L` → `upper_arm.L` | `chest` | 57 | Folded wing lying along the arm; `chest`–`wing_root.L` has 40 |
| `wing_root.R` → `upper_arm.R` | `chest` | 55 | Same, other side |
| `neck` → `wing_root.L` | `chest` | 39 | Cascades from the two above |

Three alternative edge scores were measured and none separated a joint from a
fold:

| Score | Why it failed |
| --- | --- |
| Interface mean depth | `jaw`–`neck` is **deeper** than `head`–`neck` (1.75 vs 1.52 voxels) |
| Depth-weighted contact (`Σ` depth) | Ranks the top 13 edges correctly, then `wing_root.L`–`wing_root.R` (137.8) beats four true edges |
| "Endness" — how near the contact sits to the end of each region's geodesic extent | Hub parts score ~0.5 by construction, penalising every true edge into `chest` and `pelvis`; a split `eye.L` produced an endness of 6.5 |

### The joint rule, measured

| Interface estimator | Median joint error | Mean | Elbow |
| --- | --- | --- | --- |
| Plain centroid (depth⁰) | 0.80% | 1.26% | 0.30% |
| Depth¹-weighted | 0.68% | 1.15% | 0.31% |
| **Depth²-weighted** | **0.66%** | **1.11%** | 0.33% |
| Depth³-weighted | 0.67% | 1.12% | 0.34% |

(Measured before the multi-root answer key was tightened, so these medians sit
slightly below the 0.70% headline; the ranking is what the choice rests on.)

### The bone-tail rule, measured

| Rule | Median tail error | Mean | Chain |
| --- | --- | --- | --- |
| **Farthest child joint, farthest voxel for a leaf** | **0.71%** | 1.76% | connected |
| Always the farthest voxel of the part | 1.33% | 1.89% | every bone floats |

Rule A's mean is dragged up by `wing_arm` alone (12.7%), for the membrane-seam
reason above; on every other bone it wins or ties.

### The answer key's own ambiguity

Two parts have more than one root bone in the donor rig, so "the true joint" is
not a single place:

| Part | Root bones | Spread between their heads |
| --- | --- | --- |
| `wing_hand.L/R` | 3 spars | **3.988** |
| `eye.L/R` | 11 (eye, iris, 8 lids) | 0.111 |

`donor_head_spread` travels with every scored row, and the summary reports a
median over only the 27 joints placed at one point (**0.63%**) beside the
median over all 30 (**0.70%**).

### Riyu, as a smoke check

```
skeleton derived: trellis2/ninjago-riyu-001 (landmarks seeding)
  bones    : 20 over 20/34 parts, depth 4, total length 3.041
  joints   : 19 region boundaries
  adjacency: 13/20 derived edges agree with the declared hierarchy
  reattached: foot.L, foot.R, hand.L, hand.R, wing_hand.L, wing_hand.R, wing_root.L, wing_root.R
  no bone  : ear.L, ear.R, eye.L, eye.R, forearm.L, forearm.R, jaw, nostril,
             shin.L, shin.R, upper_arm.L, upper_arm.R, wing_arm.L, wing_arm.R
```

It runs, and it is not a usable skeleton: eight parts are reattached across a
gap because their declared parents were never labelled, and every interior
joint is missing. Riyu has no scored number because it has no rig to score
against — which is the whole reason the donor is measured first.

### Repository checks

| Check | Result |
| --- | --- |
| `uv run pytest` | **164 passed, 1 skipped** (16 new in `tests/test_part_skeleton.py`) |
| `uv run ruff check .` | clean |
| `pnpm check` | 0 errors, 0 warnings, 0 hints (11 files) |
| `pnpm build` | passes |
| `parts/skeleton.json` served size (donor) | 29,856 B |

### Known gaps

- **One donor.** Every number here is against one rig of unknown provenance, in
  one rest pose, and that pose is rearing with folded wings — which is exactly
  the pose that produces the adjacency failures.
- **`wing_hand` is 13% out** and the fix proposed in OP-207 is untested.
- **No target has been scored**, only the donor. Riyu has no answer key.
- **Roll is not derived** and is not measured; the axis-angle column measures
  bone direction only.
- **The interactive click-through was not run** — no browser-control runtime in
  this session. Route allowlists, `pnpm check`, the Astro build and the served
  document size stand in its place.
