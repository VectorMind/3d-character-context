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

### Step 1 — Crude rigid transfer

_Pending._

### Step 2 — Landmarks

_Pending._

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
