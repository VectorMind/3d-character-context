# Implementation — 3D Character Context Initial Bringup

## Progress

`▰▰▰▰▰▰ Done` — all six phases implemented and proven, including two
live `charctx generate` runs landing measured meshes in append-only project
slots; this packet's 67 offline tests pass inside a green 78-test suite, ruff
clean.
Non-blocking follow-ups: the `live` pytest test still needs a day with spare
quota, and one empty pre-fix run slot awaits manual deletion.

## 2026-08-25 — Phase 1, Hugging Face free access

Scope run this pass: the Hugging Face half of the Phase 1 free-access
experiment (OP-011) — REST inference hello world, then TRELLIS hello world.
The commercial free tiers named in Phase 1 were **not** probed and remain
open; no repository code (package, CLI, contracts) was written, so Phases 2–6
are untouched.

### Files Added

| Path | Purpose |
| --- | --- |
| `experiments/README.md` | How to run the probes, flags, output layout, quota warning |
| `experiments/_common.py` | Zero-dependency helpers: `.env` loading, token masking, timestamped results folder, Markdown/JSON report writer |
| `experiments/hf_01_hello_inference.py` | REST inference hello world (token identity → router → chat completion → legacy route → `image-to-3d` availability) |
| `experiments/hf_02_trellis_space.py` | TRELLIS hello world (Space runtime stages → reference image → Gradio API → GLB → trimesh measurement) |

Experiments live outside `src/` on purpose: they probe provider availability,
which is a moving target, and must stay re-runnable independently of the
package that does not exist yet. Each script is a self-contained PEP 723
script run with `uv run --script`, so Phase 1 needs no environment — which is
what the plan asked for, with the scripts kept as standing probes instead of
throwaway files in `.cache/scratch/` (maintainer request: this kind of test
deserves real code).

Every run writes `.cache/results/<YYYY-MM-DD>/<HHMMSS>-<experiment>/` holding
a Markdown report, the same run as JSON, and the artifacts it downloaded.
Timestamped paths make runs append-only, matching the OP-006 doctrine.

### Findings — REST Inference (`hf_01_hello_inference.py`)

- **Token works.** `HF_TOKEN` is a fine-grained user token (`laptop_dev_inf`,
  user `wassfila`) scoped to `inference.serverless.write` and
  `inference.endpoints.infer.write`. `whoami-v2` answers in 0.18 s.
- **Hello world round-trips.** `POST router.huggingface.co/v1/chat/completions`
  with `meta-llama/Llama-3.1-8B-Instruct` replied "Hello World!" in 1.1 s via
  provider `deepinfra`. The router serves 133 models.
- **Model ids are not free-form.** `Qwen/Qwen2.5-7B-Instruct` returned HTTP 400
  "not supported by any provider you have enabled" — the router serves an
  explicit catalogue, so a backend must resolve ids against `/v1/models`
  rather than assume a Hub id works.
- **The legacy route is gone.** `api-inference.huggingface.co` no longer
  resolves in DNS at all (`getaddrinfo failed`), not merely deprecated. Any
  code or documentation aimed at that host is dead.
- **REST inference serves zero `image-to-3d` models.** Querying the Hub with
  `pipeline_tag=image-to-3d&inference_provider=all` returns **0** results,
  while the Hub itself hosts many such models (`tencent/Hunyuan3D-2` 1803
  likes, `microsoft/TRELLIS.2-4B` 1138, `microsoft/TRELLIS-image-large` 672,
  `stabilityai/TripoSR` 649, …).

This decides OP-011's mechanism question empirically: **the REST/serverless
route cannot serve this pipeline at all.** Spaces are not one option among
several — they are the only free Hugging Face path to image-to-3d.

### Findings — TRELLIS Spaces (`hf_02_trellis_space.py`)

- **The Space the plan named is down.** `microsoft/TRELLIS` (4775 likes) is in
  stage `CONFIG_ERROR` with no hardware allocated — the exact upstream-churn
  risk the plan flagged, hit on the first day of contact. Two working
  alternatives were found and both produced meshes:

  | Space | Stage | API shape | Time | Vertices | Faces | GLB |
  | --- | --- | --- | --- | --- | --- | --- |
  | `trellis-community/TRELLIS` | RUNNING (zero-a10g) | one call `/generate_and_extract_glb` | 21.0 s | 10 028 | 13 050 | 1.7 MB |
  | `microsoft/TRELLIS.2` | RUNNING (zero-a10g) | `/preprocess_image` → `/image_to_3d` → `/extract_glb`, session-stateful | 65.0 s | 192 190 | 293 665 | 10.0 MB |
  | `microsoft/TRELLIS` | CONFIG_ERROR | — | — | — | — | — |

- **Both GLBs re-load and measure clean**: finite coordinates, textured, unit-ish
  bounds (extents ≈ 1.0 × 0.6–0.7 × 1.0, so the Space emits a normalized,
  roughly unit-cube asset), non-watertight with many connected components
  (342 and 3320) — i.e. exactly the "untrusted topology" the canonicalization
  layer exists to fix. Measurement, not appearance, per the proof obligations.
- **Partial parameter lists fail opaquely.** Calling `microsoft/TRELLIS.2`'s
  `/image_to_3d` with a subset of its parameters raises
  `AppError('The upstream Gradio app has raised an exception but has not
  enabled verbose error reporting')` in 0.3 s. Sending every declared
  parameter — defaults read from `view_api` — makes the same call succeed.
  The script now always fills the full signature (`build_kwargs`).
- **Cold-start handshakes time out.** The first connect to
  `trellis-community/TRELLIS` failed with `ReadTimeout`; the same connect
  succeeded seconds later. The script now uses a 300 s httpx timeout and
  retries the handshake three times.
- **The free ZeroGPU quota is the real constraint.** After four generations
  the Spaces refused further calls: *"You have exceeded your free ZeroGPU
  quota (120 s requested vs. 156 s left). Try again in 23:51:16. Subscribe to
  Hugging Face PRO to get 25 min of ZeroGPU quota a day."* Each TRELLIS call
  **reserves 120 s of budget up front** regardless of how long it actually
  runs, the budget is shared across all ZeroGPU Spaces for the account, and it
  resets on a 24 h timer. A free account therefore supports roughly **four
  generations per day**; HF PRO raises it to 25 min/day (~12 calls).

### Decisions Made During This Pass

- The candidate Space list is ordered simplest-API-first and every running
  candidate is exercised, so each run records a per-path finding rather than
  only the first success (`--first-success` restores stop-at-first).
- A `--measure` mode re-measures GLBs already on disk, and `--probe-only`
  reports Space stages without generating, so iterating on the scripts costs
  no GPU quota. Both were added after quota exhaustion made the cost visible.
- The hello-world input is the TRELLIS Space's own example asset
  `typical_creature_dragon.png` — a dragon, matching the target character
  family — fetched at run time, so no image is committed to the code repo.
- `trimesh` needs `networkx` (or scipy) for connected components; both are in
  the script's dependency block, and a missing graph engine degrades to a
  recorded "unavailable" string instead of losing an expensive run.
- Console output is forced to UTF-8: Space payloads contain emoji and the
  Windows cp1252 console raised `UnicodeEncodeError` mid-run.

### Deviations From The Plan

- Plan Phase 1 says throwaway scripts in `.cache/scratch/`. Per maintainer
  direction the probes are committed code in `experiments/` instead, with
  results in `.cache/results/<date>/<time>-<experiment>/`.
- Plan Phase 1 covers Meshy, Tripo, and Rodin free tiers as well. This pass
  was scoped to Hugging Face only; those remain unprobed and OP-011's backend
  selection is therefore **not yet final** (see below).

### Consequences For Later Phases

- OP-011's `gradio_client`-against-a-Space mechanism is **validated**, and its
  alternatives are no longer symmetrical: there is no serverless REST fallback
  for image-to-3d, so the escalation path from a free Space is
  duplicate-the-Space or a dedicated (paid) endpoint, nothing cheaper.
- The Phase 4 backend must treat Space identity as configuration, not a
  constant: the highest-profile TRELLIS Space is already broken, and the two
  working ones have **different API shapes** (single-call vs session-stateful
  three-call). `config/providers.yaml` should carry the Space id plus its
  call shape.
- Because a partial parameter list fails opaquely, the backend should send the
  full declared signature and read defaults from the Space's own API
  description rather than hardcoding them.
- The 120 s-per-call quota reservation makes append-only caching (OP-006) a
  hard requirement rather than a nicety: a discarded result costs a quarter of
  the day's free budget.
- Mesh reporting (Phase 5) is already exercised in miniature: the metrics
  emitted here (vertices, faces, bounds, extents, area, volume,
  watertightness, components, finiteness, file size) are the handoff's
  milestone-1 list and can seed the `*.measurements.json` contract.

### Open After This Pass

- Commercial free tiers (Meshy, Tripo, Rodin) unprobed — Phase 1 is not
  complete and the first backend is not finally selected.
- Which TRELLIS Space to adopt is not settled: `trellis-community/TRELLIS` is
  3× faster with a far simpler contract; `microsoft/TRELLIS.2` is the official
  successor with ~19× the vertex count. Quality comparison on a real dragon
  reference is a separate call, and needs quota.
- `tencent/Hunyuan3D-2.1` and `tencent/Hunyuan3D-2mini-Turbo` were seen
  RUNNING during discovery but were not called.

## 2026-08-25 — Phases 2-6, full bringup implementation

Maintainer direction for this pass: commit to the TRELLIS path with
`microsoft/TRELLIS.2` as the backend, leave the commercial providers out
entirely for now, and implement as much of the plan as possible even if some
proof has to wait.

### What Landed

| Area | Files |
| --- | --- |
| Environment | `pyproject.toml`, `.python-version` (3.12), `uv.lock` |
| Configuration | `config/providers.yaml`, `config/artifacts.yaml` |
| Package core | `src/character_context/{__init__,__main__,paths,config,contracts,project,mesh_report,artifacts,cli}.py` |
| Backend | `src/character_context/backends/{__init__,trellis2}.py` |
| Tests | `tests/{conftest,test_contracts,test_config,test_project,test_mesh_report,test_artifacts,test_backend_trellis2,test_cli,test_live_trellis2}.py`, `tests/fixtures/trellis2_view_api.json` |
| Specs | `specifications/{workspace-layout,agent-interface,generator-backend,mesh-report,external-tools}/spec.md` + index |
| Docs | `README.md` rewritten as the command reference; `AGENTS.md` current state |

### Phase 2 — Environment

`uv sync` produces a working environment on Windows with Python 3.12.13.
Base dependencies: pydantic, pyyaml, gradio-client, httpx, numpy, trimesh,
plus **networkx and scipy as mandatory** — trimesh cannot count connected
components without a graph engine, and that metric is part of the mesh-report
contract, so it is not left to chance (OP-010 doctrine applied concretely).
Dev group: pytest, ruff. Line length 88, ruff rules `E,F,W,I,UP,B`.

`charctx fetch blender` provisioned the pinned build from
`config/artifacts.yaml` alone and verified it: **`Blender 5.2.1 LTS`**. Two
facts worth recording:

- the 405 MB download is checksum-verified against the vendor's published
  `blender-5.2.1.sha256` before extraction, and a re-fetch reuses the cached
  archive instead of re-downloading;
- **5.2.1 identifies itself as LTS.** The plan treated the 5.x line as
  non-LTS and flagged faster churn as a risk; the running binary contradicts
  that, so the risk is smaller than recorded and the 4.5 fallback is less
  likely to be needed.

One real bug surfaced and was fixed: renaming the freshly extracted directory
failed with `PermissionError: [WinError 5]` because Windows still held
handles on hundreds of just-written executables. The rename now retries with
backoff and falls back to a copy.

### Phase 3 — Contracts And Project Folder

Four pydantic models in `contracts.py`, all `extra="forbid"`:
`GenerationRequest` and `RawCharacterResult` in use, `CanonicalizationResult`
and `RiggedCharacterResult` reserved for milestones 2-4, plus
`MeshMeasurements`. `GenerationRequest` validates that reference images exist
and that the run name is a filesystem-safe slug; `RawCharacterResult`
validates the artifact is a mesh. Backend knobs live in `options`, so adding
a backend never grows the model.

`project.py` implements selection (`--project`, then `CHARCTX_PROJECT` from
`.env`), scaffolding, and `run_slot()` — the append-only allocator. Slots
increment `<name>-<NNN>`, skip numbers already taken, and are created with
`exist_ok=False` so two concurrent runs cannot collide on one folder.
Scaffolding inside the repository is refused outright.

The real co-workspace is selected and exercised:
`C:\Users\wassi\My Drive\Projects\3d-models\characters-generation` — a path
with spaces on a cloud-synced drive. All artifact writes go to a temporary
name and are renamed into place so a sync client never uploads a half-written
file.

### Phase 4 — TRELLIS.2 Backend

`backends/trellis2.py` drives `microsoft/TRELLIS.2` through `gradio_client`.
Four decisions came straight out of the Phase 1 findings:

1. **Every declared parameter is sent**, with defaults read from the Space's
   own `view_api` rather than hardcoded. A partial list fails opaquely; a
   hardcoded default silently diverges when the Space changes.
2. **Session ordering is explicit** — `/start_session`, `/preprocess_image`,
   `/image_to_3d`, `/extract_glb` on one client, because the Space holds the
   generated asset in session state between the last two calls.
3. **Quota refusal is its own error type** (`QuotaExhausted`), carrying the
   provider's own message with its numbers and reset time unedited.
4. **A changed Space API is reported, not guessed at**: a configured endpoint
   that no longer exists produces an error naming it and listing what the
   Space exposes now.

Options precedence is config defaults, then per-request `--option` overrides.
Each run slot ends up self-contained: `<name>.glb`,
`<name>.measurements.json`, a copy of the reference image, and `request.json`
(backend, space, call shape, request, resolved options, timestamps,
artifacts). Provider-native payloads never leave the module — a test asserts
the Gradio temp paths and preview-video names do not appear in the result.

Added during the pass: a run that brings back nothing removes its empty slot.
Append-only protects results, not empty folders, and an empty slot would
otherwise be mistaken for a run that produced something.

### Phase 5 — Mesh Report

`mesh_report.measure()` loads any GLB/glTF/OBJ/PLY/STL, concatenates its
sub-meshes, and reports the handoff's milestone-1 metrics plus degenerate
faces, centroid, and sampled points. `volume` is emitted **only** when the
mesh is watertight — reporting a volume for an open surface would be a
meaningless number presented as a fact.

`measure()` writes nothing; `write_measurements()` writes the
`<stem>.measurements.json` sidecar atomically. `charctx report` works on any
local mesh, so mesh verification is fully testable with no provider call.

### Phase 6 — Proof, CLI, Specs

CLI commands: `info`, `paths`, `backends`, `project init|info`, `fetch`,
`generate`, `report`. Built on argparse — no CLI framework dependency, and
full control over the `--json` shape that agents consume. Global `--project`
and `--json` are accepted **before or after** the subcommand (shared parent
parser with suppressed defaults), because `charctx report mesh.glb --json` is
what people actually type. Exit codes: 0 success, 2 configuration/usage, 1
other; errors print one line, never a traceback.

65 offline tests pass and `ruff check .` is clean. The backend is tested
against `tests/fixtures/trellis2_view_api.json`, the Space's real API
description recorded live — so the offline suite checks the actual contract,
not an invented one. Mesh tests build their own geometry (icosphere, boxes),
so no binary fixture enters the repository.

Five specs folded, indexed in `specifications/README.md`: workspace-layout,
agent-interface, generator-backend (with the Phase 1 access facts, the
documented alternatives table, and the staged geometry libraries),
mesh-report, external-tools.

### Decisions Made During This Pass

- **argparse over a CLI framework.** The plan did not name one. argparse is
  stdlib, keeps the base dependency list at what the pipeline genuinely
  needs, and leaves the JSON contract fully under our control.
- **Credential masking reveals nothing.** `mask()` reports presence and
  length only (`set (37 chars)`), not a prefix. The agent-interface spec says
  a credential value never appears in output; a four-character prefix is
  still part of the value.
- **`networkx` and `scipy` are mandatory, not optional.** Discovered in Phase
  1 when a successful, quota-costing generation was lost to
  `ImportError: no graph engines available!` during measurement.
- **The reference image entered the data workspace through its intake flow.**
  `inputs/references/trellis-example-dragon.png` with a `.provenance.md`
  sidecar recording source URL, origin, acquisition date, bytes, and rights.
  The bytes are the unmodified original. It is a pipeline test input, not
  artwork for a production character.

### Deviations From The Plan

- Commercial free tiers (Meshy, Tripo, Rodin) were not probed — maintainer
  direction to leave them out. They stay documented alternatives in
  `config/providers.yaml` and the generator-backend spec.
- The plan's Phase 1 selected a backend "from the facts"; the maintainer
  selected `microsoft/TRELLIS.2` directly. `trellis-community/TRELLIS` is
  documented as the faster, lower-density alternative.
- `charctx backends` is a command the plan's skeleton did not list. It exists
  because the implemented/documented distinction has to be visible from the
  CLI, not only from a YAML file.

### Open After This Pass

- **A live `charctx generate` has not produced a mesh yet.** The full path was
  exercised against the real Space — connect, session, preprocess, and the
  full-parameter `/image_to_3d` call — and stopped exactly where expected:
  *"You have exceeded your free ZeroGPU quota (120s requested vs. 156s left).
  Try again in 23:26:18."* The day's budget was spent on the Phase 1
  experiment. The empty slot was correctly discarded. This resolves after the
  quota resets (~22:20 local on 2026-08-26) with:

  ```powershell
  uv run charctx generate "$env:CHARCTX_PROJECT\inputs\references\trellis-example-dragon.png" --name red-dragon --seed 42
  ```

- The live smoke test (`tests/test_live_trellis2.py`, marked `live`) is
  written and gated behind `CHARCTX_LIVE=1`; it has never run green.
- No canonical layer: template topology, landmarks, skeleton, and fitting are
  milestones 2-5 and unstarted. `CanonicalizationResult` and
  `RiggedCharacterResult` are shapes, not behavior.
- Blender is provisioned and verified but **no pipeline stage calls it yet**;
  the subprocess invocation pattern is specified, not exercised.
- `charctx fetch` supports zip archives only, and `config/artifacts.yaml`
  carries a Windows-only pin. A non-Windows platform is refused with a clear
  message rather than a wrong binary.

## 2026-08-26 — Live validation, and one real bug it exposed

Maintainer direction: spend the day's ZeroGPU budget on validation, and keep
generated results in the real project folder rather than temp directories.

### Live Proof — The Last Exit Criterion

`charctx generate` produced measured meshes through `microsoft/TRELLIS.2`
twice, into `<project>/generated/trellis2/red-dragon-001` and `-002`:

| | Run 1 (seed 42) | Run 2 (seed 43) |
| --- | --- | --- |
| duration | 58.98 s | 63.16 s |
| vertices / faces | 192,711 / 293,985 | 181,018 / 277,705 |
| components | 3,284 | 3,000 |
| file size | 9.99 MB | 9.47 MB |

Both slots are self-contained (`*.glb`, `*.measurements.json`,
`reference.png`, `request.json`) with no temp leftovers. Full numbers in
`test.md`.

The 6% spread between two seeds on one reference image is the concrete
justification for OP-006: a generation cannot be reproduced by re-running it,
so no result is ever discarded.

### New: `experiments/hf_03_live_validation.py`

A quota-aware runner for exactly this kind of session. It drives the real
`charctx` CLI as a subprocess (so it validates the shipped interface, not an
internal function), waits out a refusal using the provider's own
`Try again in H:MM:SS` rather than guessing, and verifies each resulting slot
against nine checks before reporting.

It runs in the project environment rather than as a standalone PEP 723
script: `uv run --script` failed here with `Failed to spawn: python - An
Application Control policy has blocked this file`, because a script with no
dependencies makes uv spawn a bare interpreter that Windows blocks. Since the
runner drives the installed CLI anyway, the project environment is the honest
home for it.

Two bugs surfaced on the free path before any quota was spent: that spawn
failure, and a `Report.probe()` keyword collision that would have crashed
*after* a successful generation and wasted it.

### Bug Fixed: Empty Run Slots On A Cloud-Synced Folder

The third (quota-refused) run left an empty `red-dragon-003/` behind, which
the previous pass's cleanup was meant to prevent.

Cause: Google Drive takes a handle on a newly created directory immediately,
so the cleanup `rmdir` fails with `PermissionError: [WinError 5]` — still
failing on four retries minutes later. Retrying, which fixed the analogous
Blender extraction rename, does not work here.

Fix: **allocate the run slot only after the provider returns a mesh.**
`generate()` now calls `project.run_slot()` after `_first_glb()` succeeds, so
a failed call cannot create a folder at all. The `_discard_if_empty` helper
was deleted as dead code. This is the better shape regardless of cloud sync —
not creating a thing beats cleaning it up — and it makes the workspace-layout
spec's "a run that brings back no artifact leaves no slot behind" true by
construction rather than by best effort.

Regression tests: `test_a_failed_call_creates_no_run_slot` and
`test_slot_numbering_ignores_failed_attempts` (a failed run between two
successes does not consume a slot number).

Suite after the fix: **78 passed, 1 skipped** repo-wide, ruff clean. That
count includes the parallel asset-catalog packet's tests; this packet
contributes 67 of them (13 backend, 16 CLI, 10 config, 8 contracts, 8 mesh
report, 8 project, 7 artifacts, plus the gated live test).

### Also Proven: The Blender Subprocess Boundary

Free to check, and it closed a gap the previous pass left open. Headless
Blender runs from the resolved `.tools/` path, exits 0, imports `bpy`
(5.2.1 LTS), and loads the factory-startup scene — on **Python 3.13.13**,
while `charctx` stays on the 3.12 pin. That independence is exactly what
choosing the provisioned binary over the `bpy` wheel bought (OP-013).

### Quota Facts, Refined

- Two generations plus the previous day's residual exhausted the day: the
  third attempt was refused with a **~24 h** wait.
- Practical free-tier rate: **2-4 generations per day**, not the 4 estimated
  from arithmetic alone.
- The rolling window is per-usage, not a midnight reset: yesterday's spend
  aged out 24 h after it was incurred, and the provider states the exact
  remaining wait.

### Open After This Pass

- The `live` pytest test remains unrun (no quota left); it exercises the same
  path the two CLI runs just proved.
- One empty `red-dragon-003/` directory predates the fix and is still on disk
  because Drive holds it. Harmless, deletable by hand.
- Everything else outstanding is milestone-2 work: the canonical layer, and
  any real geometry through the Blender boundary.
