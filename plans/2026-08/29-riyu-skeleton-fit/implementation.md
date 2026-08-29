# Implementation — Riyu Skeleton Fit And Rig Visualization

## Progress

`▰▰▱▱▱▱▱ Step 2/7` — the crude rigid transfer and the geometric landmark
proposal are both landed and visible on Riyu's page. Step 3 (landmark-driven
per-chain fit) is next, and the review gate sits at its end.

## 2026-08-29 — Step 1: Crude Rigid Transfer

Riyu now carries a fitted 168-bone skeleton, served through the confined
generation route and drawn by the existing overlay.

### What landed

- `src/character_context/skeleton_fit.py` — one uniform scale plus one
  translation that contain the donor skeleton in the target's measured box.
- `asset_models.py` — `FittedBone`, `FittedArmature`, `FittedSkeletonDocument`,
  and a `skeleton` field on `GenerationManifest`.
- `generations.py` — the manifest declares `skeleton/skeleton.json` when
  present and validates its confinement; the existing `skeleton` stage marker
  flips the pipeline strip to complete.
- `cli.py` — `charctx skeleton fit <backend>/<run> --donor <id>`, a new
  `skeleton` command group that later steps will grow into.
- Web — the generation artifact route allowlists the declared skeleton and
  serves `application/json`; the generation viewer receives `skeletonUrl`.
- `tests/test_skeleton_fit.py` — six tests.
- README gained the command section in the same pass.

### Decisions

- **A separate schema, deviating from the plan text.** The plan said emit
  `charctx.skeleton/v1` so the viewer renders it free. Implementing it exposed
  a conflict: the asset-packages spec defines that schema as the authority for
  a donor's *unmodified* source rig, and a synthesized fit is the opposite of
  that. Emitting `charctx.fitted-skeleton/v1` instead keeps faithful and
  derived data distinguishable, and cost only a widened union type in the
  viewer — the overlay never validated the schema string at runtime.
- **`FittedBone` is narrower than `SkeletonBone`.** `head_local`, `tail_local`
  and `matrix_local` are Blender armature-local data with no meaning once the
  bone has left its armature, so a fitted document does not carry them rather
  than carrying transformed nonsense.
- **Uniform scale, not per-axis.** A per-axis scale would shear every bone away
  from its donor proportions, which is the exact quantity this step is trying
  to measure. Non-uniform fitting would also have hidden the pose mismatch that
  the fill ratio exposed.
- **The stage marker is not a browser artifact.** `skeleton/manifest.json`
  stays off the route allowlist; only the skeleton document is served.
- The viewer status line now reads "fitted" rather than "extracted" for a
  fitted document.

### What the picture showed

Fill ratio `x 46% · y 100% · z 83%`. Height binds the uniform scale on its own,
because the donor's rearing rest pose makes it tall relative to its width, so
the wings land at under half of Riyu's span. That is a measurement of the
**pose** mismatch rather than of anatomy, and it is the concrete argument for
step 3 taking every joint position from Riyu instead of transforming the donor
rigidly. Step 2's landmark set must pin wing root, elbow, wrist and tip
explicitly.

### Checks

`uv run pytest` 89 passed / 1 live skipped · `uv run ruff check .` clean ·
`pnpm check` 0 diagnostics · Astro build pass · loopback route and confinement
checks pass. Full numbers in `test.md`.

### Not done

The interactive browser click-through was not run — no browser-control runtime
is available in this session. Route, prop, pipeline-state and containment
evidence stand in its place.


## 2026-08-29 — Step 2: Landmarks

Riyu now carries 21 proposed landmarks, drawn as side-coloured spheres behind
their own toggle.

### What landed

- `src/character_context/landmarks.py` — `symmetry-medial-extremal/v1`. Picks
  the mirror axis by measuring residuals rather than assuming one, derives a
  medial curve along the body axis, orients head-vs-tail by end thickness, and
  reads wings and feet off the extremes. No model call, no image.
- `asset_models.py` — `Landmark`, `LandmarkDocument`, and a `landmarks` field
  on `GenerationManifest`. The document validator rejects a landmark whose
  declared side disagrees with its name suffix.
- `cli.py` — `charctx skeleton landmarks <backend>/<run>`.
- Web — route allowlist, bridge type, page prop, and a `LandmarkOverlay` with a
  `Show landmarks` toggle; x-ray is now offered whenever either overlay exists.
- `tests/test_landmarks.py` — eight tests over a subdivided synthetic quadruped.
- README gained the command section in the same pass.

### Decisions

- **Nothing depends on connectivity.** Every step runs on the vertex cloud, so
  Riyu's 6,209 shells are handled exactly like a clean mesh. This was a
  constraint recorded in the plan and it held without special-casing.
- **Interior joints are not guessed.** `elbow`, `knee`, `wing_elbow`,
  `wing_wrist` and `jaw_pivot` have no reliable surface signature. Emitting a
  plausible-looking guess would have been worse than the gap, so they are
  absent and listed in `not_attempted`.
- **Colour by side in the viewer.** Amber centre, cyan left, magenta right —
  chosen so a left/right inversion shows up as obviously wrong colours rather
  than as a number someone has to check.
- **The left/right convention is derived and flagged.** Facing the head with
  the short axis up, a right-handed frame puts the character's right on the
  negative side of the mirror plane. Recorded in `derivation.side_convention`
  and explicitly marked unverified against donor bone naming.

### Two defects the first output exposed

Both were found by looking at the numbers, which is the point of the loop:

- **The centre chain contradicted its own evidence.** Girdles placed at
  arbitrary fractions put `hip_center` at z=+0.008 while `hip.L/R`, derived
  from measured feet, sat at z=+0.153 — 15% of body length apart. `chest` and
  `hip_center` now anchor to the foot clusters and agree exactly.
- **The head/tail test counted empty space as thin.** Walking inward from each
  end, an empty slice satisfied the thinness test, so on sparse geometry the
  walk never stopped and the orientation inverted. Replaced with a median
  half-width comparison in a narrow band at each end — narrow so a wing rooted
  behind the skull is not mistaken for the head.

### What the picture showed

Head direction resolved to +z on an end half-width of 0.0479 against 0.0211,
independently confirmed by the top-view render. The mirror axis won by 22×.
Exactly four ground clusters were found without being told to expect four.

The gap is now the interesting part: the chain, girdles, wing roots and feet
are all in hand, but every joint *between* them is missing. Step 3 must
interpolate the leg and wing chains along the donor's proportions between known
landmarks — which is precisely the job the donor hierarchy exists to do.

### Checks

`uv run pytest` 98 passed / 1 live skipped · `uv run ruff check .` clean ·
`pnpm check` 0 diagnostics · Astro build pass · route and confinement checks
pass. Numbers in `test.md`.
