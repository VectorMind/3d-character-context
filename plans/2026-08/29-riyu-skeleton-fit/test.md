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

### Step 3 — Landmark-driven per-chain fit

_Pending._ Review gate: stop here and look.

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
