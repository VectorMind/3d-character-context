# Test Proof — Riyu Skeleton Fit And Rig Visualization

## Status

Not started. Proof is recorded per step as each one lands.

## Fixtures

- `trellis2/ninjago-riyu-001` — fit target
- `european-dragon` — donor hierarchy and weight ground truth
- `dragon`, `blender-dragon` — negative references only

## Baseline (2026-08-29, before any step)

| Fact | Value | Source |
| --- | --- | --- |
| Riyu vertices / faces | 203,745 / 289,479 | `charctx report ninjago-riyu.glb --no-write` |
| Riyu connected components | 6,209 | same |
| Riyu watertight | False (1 degenerate face) | same |
| Riyu extents | 1.0019 × 0.4442 × 0.9963 | same |
| Riyu skeleton | none | `charctx assets show ninjago-riyu` |
| Donor bones / weight-bearing | 168 / 164 | `inspection/skeleton.json`, `skin-weights.json` |
| Donor max weight-sum error | 0.185 | `inspection/skin-weights.json` |
| Donor unweighted vertices | 0 | same |

## Per-Step Proof

Each step records: the command run, the expected picture, what was actually
seen, and what it changed about the next step.

### Step 1 — Crude rigid transfer (2026-08-29)

**Command**

```powershell
uv run charctx skeleton fit trellis2/ninjago-riyu-001 --donor european-dragon
```

**Expected picture:** a 168-bone skeleton visible on Riyu's page, obviously
wrong, with a measurable account of *how* wrong.

**Actual**

| Fact | Value |
| --- | --- |
| Schema | `charctx.fitted-skeleton/v1` (`faithful: false`) |
| Method | `uniform-contain-bounds/v1` |
| Bones / armatures / roots / leaves / depth | 168 / 1 / 1 / 65 / 17 |
| Uniform scale | 0.040686 |
| Translation | `[0, -0.2276, 0.2733]` |
| Donor skeleton bounds | `[-5.694, 0.128, -16.924] .. [5.694, 11.047, 3.377]` |
| Riyu measured bounds | `[-0.5010, -0.2224, -0.5004] .. [0.5009, 0.2219, 0.4959]` |
| Endpoint containment | **336/336 (100%)** — guaranteed by a contain fit |
| Artifact size | 94,600 bytes |

**Target fill ratio — the measurement this step exists to produce**

| Axis | Fill | Reading |
| --- | --- | --- |
| y (height) | **100%** | Height is the binding axis and sets the scale alone |
| z (length) | 83% | Tolerable |
| x (wingspan) | **46%** | The donor's wings reach barely half of Riyu's span |

The donor's rearing, vertically-curled rest pose makes it tall relative to its
width. Under a uniform scale that height consumes the whole budget, so the
wings fall 54% short. **The number is a measurement of the pose mismatch, not
of a wingspan difference** — and it is the concrete case for step 3 taking
every joint position from Riyu rather than transforming the donor as a rigid
body.

**Web proof**

| Request | Expected | Actual |
| --- | --- | --- |
| `GET /assets/ninjago-riyu` | 200 | **200** |
| `GET /api/generation/ninjago-riyu/trellis2/ninjago-riyu-001/skeleton/skeleton.json` | 200 JSON | **200**, 94,600 B, `application/json` |
| `.../skeleton/manifest.json` | 404 — stage marker is not a browser artifact | **404** |
| `.../request.json` | 404 — undeclared | **404** |
| Viewer island props | carries the fitted skeleton URL | **Pass** |
| Pipeline strip | `Skeleton` flips to complete | **`complete`** |

**Repository checks:** 89 tests pass with one live skip (6 new); ruff clean;
`pnpm check` 0 diagnostics; Astro build passes.

**What it changes for the next step:** confirmed that a rigid transfer cannot
work and quantified why. Step 2's landmark set must therefore pin wing root,
elbow, wrist and tip explicitly, since wingspan is where the rigid fit fails
hardest.

### Step 2 — Landmarks (2026-08-29)

**Command**

```powershell
uv run charctx skeleton landmarks trellis2/ninjago-riyu-001
```

**Expected picture:** landmark spheres on Riyu, coloured by side, with the
points geometry cannot find left visibly absent rather than guessed.

**Axes and orientation, derived not assumed**

| Fact | Value | Evidence |
| --- | --- | --- |
| Symmetry axis | **x** | Mirror residual `x 0.0014` vs `y 0.0308`, `z 0.0439` — the true plane wins by 22× |
| Symmetry plane | x = −0.0004 | Median of the cloud |
| Body axis / up axis | z / y | Longest and shortest extents |
| Head direction | **+z** | End half-width: head 0.0479 vs tail 0.0211 |
| Ground clusters | **4** | Exactly four feet, found without being told to expect four |

The head/tail call was independently confirmed against the top-view render:
head at the far +z end, wings immediately behind the skull, long tapering tail
at −z.

**Landmarks proposed: 21** (9 centre, 6 left, 6 right; 10 high-confidence)

| Landmark | Point | Confidence |
| --- | --- | --- |
| `snout` | `[-0.001, 0.046, 0.486]` | high |
| `skull` | `[-0.006, 0.039, 0.465]` | low |
| `neck_base` | `[0.002, 0.074, 0.403]` | low |
| `chest` | `[0.002, -0.002, 0.361]` | high |
| `spine_mid` | `[0.000, 0.002, 0.257]` | medium |
| `hip_center` | `[-0.001, -0.015, 0.153]` | high |
| `tail_base` | `[-0.004, -0.072, 0.029]` | medium |
| `tail_mid` | `[0.001, -0.137, -0.200]` | medium |
| `tail_tip` | `[0.000, -0.157, -0.490]` | high |
| `wing_tip.L/R` | `[±0.501, -0.030, 0.352]` | high |
| `wing_root.L/R` | `[±0.128, 0.101, 0.340]` | medium |
| `foot_front.L/R` | `[±0.091, -0.210, 0.364]` | high |
| `foot_hind.L/R` | `[±0.107, -0.210, 0.149]` | high |
| `shoulder.L/R` | `[±0.050, -0.002, 0.361]` | low |
| `hip.L/R` | `[±0.059, -0.015, 0.153]` | low |

Paired landmarks mirror to within 0.001 in x and agree in z. The centre chain
is monotonic along the body axis.

**Not attempted, and recorded as such:** `elbow.L/R`, `knee.L/R`,
`wing_elbow.L/R`, `wing_wrist.L/R`, `jaw_pivot`. These are interior joints with
no reliable surface signature. They are absent from the document rather than
guessed, and listed in `derivation.not_attempted`.

**Web proof**

| Request | Expected | Actual |
| --- | --- | --- |
| `.../skeleton/landmarks.json` | 200 JSON | **200**, 8,014 B, `application/json` |
| `.../skeleton/landmarks.json.part` | 404 — undeclared temp file | **404** |
| Viewer island props | carries `landmarkUrl` | **Pass** |

**Repository checks:** 98 tests pass with one live skip (8 new + 1 shared);
ruff clean; `pnpm check` 0 diagnostics; Astro build passes.

**Two defects the output exposed, both fixed**

1. **The centre chain contradicted its own evidence.** With girdle positions
   set by arbitrary fractions of the body axis, `hip_center` landed at z=+0.008
   while `hip.L/R` — derived from the measured hind feet — sat at z=+0.153, a
   disagreement of 15% of body length. The chain now anchors `chest` and
   `hip_center` to the foot clusters, so the two agree exactly and both earn
   high confidence.
2. **The head/tail test counted empty space as thin.** The first heuristic
   walked inward from each end measuring how far the cross-section stayed thin,
   but an empty slice satisfied "thin", so on sparse geometry the run never
   terminated and the orientation came out backwards. Replaced with a direct
   comparison of median half-width in a narrow band at each end — narrow on
   purpose, so a wing rooted just behind the skull cannot be read as the head.

**What it changes for the next step:** the chain, girdles, wing roots and feet
are all in hand, but every leg and wing joint between them is missing. Step 3
cannot place `wing_elbow`/`wing_wrist` or the leg chains from landmarks alone,
so it will have to interpolate them along the donor's proportions between the
landmarks that do exist — which is exactly where the donor hierarchy earns its
place.

### Step 3 — Landmark-driven per-chain fit (2026-08-30)

**Commands**

```powershell
uv run charctx skeleton fit trellis2/ninjago-riyu-001 --donor european-dragon --method rigid
uv run charctx skeleton fit trellis2/ninjago-riyu-001 --donor european-dragon
```

The first re-archives step 1's fit under `skeleton/fits/` so the viewer can
draw it behind the new one; the second is the chain fit and becomes the
declared skeleton.

**Expected picture:** the same 168-bone hierarchy, now with its joints on
Riyu's anatomy — wings reaching the wing tips, legs ending at the feet, the
neck running to the snout — and a measurement of what the method refused to
place.

**Actual**

| Fact | Value |
| --- | --- |
| Schema / method | `charctx.fitted-skeleton/v1`, `landmark-chain/v1` (`faithful: false`) |
| Bones | 168 — **74 anchored on 8 chains, 94 carried in a parent frame** |
| Landmarks consumed | 20 of the 21 proposed |
| Fitted bounds | `[-0.5010, -0.2723, -0.4900] .. [0.5009, 0.1564, 0.5271]` |
| Artifact size | 99,196 bytes |

**Fill ratio, against step 1**

| Axis | Step 1 (rigid) | Step 3 (chain) | Reading |
| --- | --- | --- | --- |
| x (span) | 46% | **100%** | The wings now reach the wing tips instead of stopping halfway |
| y (height) | 100% | 97% | No longer the binding axis; the rig no longer stands taller than the dragon |
| z (length) | 83% | 102% | Slight overshoot, entirely from carried head bones (see below) |

**Per-chain scale — each chain gets its own, which is the point**

| Chain | Bones | Donor length | Target length | Scale |
| --- | --- | --- | --- | --- |
| spine | 11 | 7.590 | 0.3898 | 0.0514 |
| tail | 17 | 15.839 | 0.6657 | 0.0420 |
| wing.L / wing.R | 10 / 10 | 21.390 | 0.5459 / 0.5467 | 0.0255 / 0.0256 |
| foreleg.L / .R | 6 / 6 | 5.094 | 0.2728 / 0.2736 | 0.0536 / 0.0537 |
| hindleg.L / .R | 7 / 7 | 4.359 | 0.2287 / 0.2282 | 0.0525 / 0.0523 |

The wing's scale is half the body's because the donor's wing is **folded** in
rest pose, so its arc length is roughly twice the straight root-to-tip span it
is fitted onto. The fitted wing is correct — it spans exactly wing root to
wing tip — but the scale spread is a direct readout of which donor chains are
curled, and it is the reason a folded donor cannot be used for absolute
lengths.

**Containment — the number that separates evidence from inheritance**

| Group | Joints | Outside the mesh bounds |
| --- | --- | --- |
| Anchored (landmark-placed) | 148 | **0** |
| Carried (parent-frame ride) | 188 | **85** |
| Total | 336 | 85 (25.3%) |

Every escaping joint is carried, none is anchored. The offenders are
`DEF-Finger_*` (30), `DEF-palm.*` (6), the eye and lid bones (22),
`DEF-Teeth_Top`/`DEF-Bone`/`DEF-Teeth_Bottom` (3) and their siblings: fingers
and toes push below the ground plane (y −0.272 against −0.222) and the head
detail pushes past the snout (z +0.527 against +0.496). This is the carry
doing exactly what it says on the tin — it inherits the parent chain's scale,
and the parent chain's scale is not the right scale for a hand.

**Symmetry** — 68 mirrored bone pairs, max error **0.004938**, mean 0.001408,
worst at `DEF-eye_iris.L`. That is 0.5% of body length at the worst carried
bone, and the anchored chains are tighter still: the L/R chain scales agree to
within 0.2%.

**Landmark residual** — distance from each landmark to the nearest anchored
joint:

| Landmark | Residual | |
| --- | --- | --- |
| `tail_tip`, `hip_center`, `snout`, `wing_tip.L/R`, `foot_front.L/R`, `foot_hind.L/R` | **0.000000** | chain endpoints, hit exactly |
| `neck_base` | 0.004435 | |
| `spine_mid` | 0.005836 | |
| `hip.L` / `hip.R` | 0.005942 / 0.006338 | |
| `chest` | 0.008849 | |
| `shoulder.L` / `.R` | 0.010913 / 0.011637 | |
| `tail_base` | 0.014566 | |
| `wing_root.R` / `.L` | 0.016715 / 0.020105 | |
| `tail_mid` | 0.017333 | |
| `skull` | **0.022554** | worst — and a `low`-confidence landmark |

Interior residuals are expected to be non-zero: bones are distributed by donor
proportion, so a chain passes *through* an interior landmark's neighbourhood
without a joint necessarily landing on it. The worst miss is 2.3% of body
length, at `skull` — one of the two landmarks step 2 already flagged `low`.

**Web proof**

| Request | Expected | Actual |
| --- | --- | --- |
| `.../skeleton/skeleton.json` | 200, the chain fit | **200**, 99,196 B, `application/json` |
| `.../skeleton/fits/uniform-contain-bounds.json` | 200 — the declared alternate | **200**, 94,711 B, `application/json` |
| `.../skeleton/fits/landmark-chain.json` | 404 — not separately declared; identical bytes to `skeleton.json` | **404** |
| `.../skeleton/manifest.json` | 404 — stage marker is not a browser artifact | **404** |
| Viewer island props | carries `skeletonUrl`, `comparisonUrl`, `landmarkUrl` | **Pass** |
| `viewer.json` | `skeleton_alternate` names the rigid fit | **Pass** |

**Repository checks:** 112 tests pass with one live skip (14 new); ruff clean;
`pnpm check` 0 diagnostics; Astro build passes.

**What it changes for the next step:** the review gate is here. Two things
the pictures should settle, because measurement cannot: whether the derived
left/right convention matches the donor's own bone naming, and whether the
carried subtrees escaping the mesh matter enough to earn landmarks of their
own before skinning. Step 5 onward should not start until both are answered —
weight transfer inherits every joint placed here.

_Review gate: stop here and look._

### Step 4 — Semantic bone naming

_Pending._

### Step 5 — Influence visualization on the donor

_Pending._

### Step 6 — Distance heuristic scored against donor ground truth

_Pending._

### Step 7 — Skin Riyu

_Pending._

## Known Gaps

- This track is per-character; it produces no cross-character reusability.
- Donor provenance is unknown; nothing derived from `european-dragon` is
  shippable outside the private workspace.
