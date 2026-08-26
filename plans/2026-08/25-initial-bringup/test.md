# Test — 3D Character Context Initial Bringup

Planning-only packet so far; per `WORKFLOW.md` this file records document
review and consistency checks instead of runtime proof. It will be replaced
by runtime proof (commands, fixtures, expected/actual results) once
implementation phases run.

## Document Consistency Checks (2026-08-25)

- `handoff.md` moved into this packet unchanged from the repository root; it
  remains the founding architecture reference for `plan.md`.
- `plan.md` follows the `WORKFLOW.md` plan shape: problem summary, resolution
  summary with the one-glance OP table, goal/objectives, scope/non-goals,
  detailed open points (each dependency/provider choice lists candidates,
  proposal, confidence, status), phases, dependencies/risks, exit criteria.
- Every OP row in the resolution summary table matches its detailed section
  (id, proposal, confidence, status) — checked by re-reading both.
- All open points have status **open**; none are recorded as accepted,
  consistent with no maintainer decision having been made yet.
- Packet scope matches the handoff's "First Milestone" and "Immediate
  Repository Bootstrap Tasks" 1–6 (+ conventions groundwork), with milestones
  2–5 explicitly out of scope.
- Repository scaffolding cross-references verified: `README.md`, `AGENTS.md`,
  `WORKFLOW.md`, `specifications/README.md`, `plans/README.md`,
  `plans/open.md`, and `plans/closed.md` exist and their relative links
  point at existing files.
- No `implementation.md` exists, consistent with no implementation having
  happened.

## Document Consistency Checks — Decision Pass 1 (2026-08-25)

- Maintainer decisions on OP-001…OP-010 folded into `plan.md`: table and
  detailed sections updated together; every accepted amendment (HF-first,
  relaxed abstraction, append-only caching, data/code split, Blender
  first-class) is recorded in both places with matching status.
- Three new open points raised from the answers — OP-011 (HF access
  mechanism/Space), OP-012 (project-folder contract), OP-013 (Blender
  install mechanism, linked back to OP-002's Python pin) — each with
  candidates, proposal, and confidence; all status open.
- Phases, goals, scope, risks, and exit criteria re-aligned with the
  amendments (no registry, HF backend, project folder, append-only slots,
  documented-only alternatives).
- Repository docs corrected where OP-009 invalidated them: `WORKFLOW.md`
  (Generated Artifacts → Data/Code Split), `AGENTS.md` (output table,
  project-folder rule, append-only rule), `README.md` (assets bullet, CLI
  name now accepted as `charctx`). `plans/open.md` row updated.

## Document Consistency Checks — Decision Pass 2 (2026-08-25)

- OP-011…OP-013 decisions folded: table and detailed sections match
  (status, amendments, confidence). OP-002's provisional Python pin is
  resolved to 3.12 by OP-013's binary choice, updated in both places.
- Phases renumbered 0–6 with the new Phase 1 free-access experiment;
  exit criteria extended (Phase 1 findings, `charctx fetch blender`,
  `.env`-based project selection); risks updated (experiment-first,
  Google-Drive path quoting/sync, atomic writes).
- OP-013 source claim verified live: `github.com/blender/blender` shows
  "There aren't any releases here" (mirror); `download.blender.org/release/`
  lists Blender4.1…5.2 with portable Windows zips at stable versioned
  paths (checked 4.5.11–4.5.13 assets).
- `AGENTS.md` project-folder paragraph updated to the `.env`
  (`CHARCTX_PROJECT`) mechanism; `plans/open.md` row updated.

## Document Consistency Checks — Decision Pass 3 (2026-08-25)

- Blender pin settled by the maintainer: 5.x line for new character-rigging
  features. Pinned to 5.2.1; asset verified live at
  `download.blender.org/release/Blender5.2/blender-5.2.1-windows-x64.zip`
  (listing checked: 5.0.0–5.2.1 Windows portable zips present).
- `plan.md` status line, OP-013 table row and detail section, Phase 0, and
  Risks (non-LTS churn note with the one-line LTS fallback) updated
  together; no open point remains anywhere in the plan.
- `plans/open.md` row updated to "planning complete, Phase 1 next".

## Runtime Proof — Phase 1, Hugging Face Free Access (2026-08-25)

First runtime proof in this packet. Scope: the Hugging Face half of the
Phase 1 free-access experiment (OP-011). Commercial free tiers were not
exercised — see Known Gaps.

### Environment

- Windows 11, `uv` 0.11.19, scripts run on uv-provisioned CPython 3.12.13.
- No repository environment exists yet: both scripts are self-contained
  PEP 723 scripts, so `uv run --script` builds their dependencies on the fly
  (`requests`; plus `gradio_client` 2.6.1, `trimesh`, `numpy`, `scipy`,
  `networkx` for the TRELLIS probe).
- Credential: `HF_TOKEN` from the git-ignored `.env` — a fine-grained user
  token (`laptop_dev_inf`) scoped `inference.serverless.write` +
  `inference.endpoints.infer.write`. Reports mask it (`hf_g…dZ (37 chars)`).

### Commands

```powershell
uv run --script experiments/hf_01_hello_inference.py
uv run --script experiments/hf_02_trellis_space.py --probe-only
uv run --script experiments/hf_02_trellis_space.py
uv run --script experiments/hf_02_trellis_space.py --measure .cache/results/2026-08-25/220907-trellis-hello-world
```

Results (each run writes its own timestamped folder, nothing overwritten):

| Time | Run | Outcome |
| --- | --- | --- |
| 22:02:15 | `hf-hello-inference` | pass |
| 22:04:40 | `trellis-hello-world` (`--probe-only`) | pass |
| 22:04:46 | `trellis-hello-world` | connect timeout + opaque `AppError`; drove the two script fixes below |
| 22:09:07 | `trellis-hello-world` | **pass — two GLBs downloaded and measured** |
| 22:12:52 | `trellis-remeasure` | pass (component counts resolved) |
| 22:14:03, 22:14:41 | `trellis-hello-world` | refused: free ZeroGPU quota exhausted |

### Expected vs Actual — REST inference hello world

| Check | Expected | Actual |
| --- | --- | --- |
| Token authenticates | HTTP 200 from `/api/whoami-v2` | 200 in 0.18 s, user `wassfila`, scopes listed |
| Router reachable | catalogue returned | 200 in 0.14 s, 133 models |
| Hello-world completion | a text reply | `meta-llama/Llama-3.1-8B-Instruct` → "Hello World!" in 1.1 s via `deepinfra` |
| Arbitrary Hub id works | assumed yes | **no** — `Qwen/Qwen2.5-7B-Instruct` → HTTP 400 "not supported by any provider you have enabled" |
| Legacy `api-inference` host | deprecated but answering | **DNS does not resolve** (`getaddrinfo failed`) — host retired |
| `image-to-3d` over REST | unknown, plan assumed unavailable | **0 models** served by any provider, vs many on the Hub — assumption confirmed with a number |

### Expected vs Actual — TRELLIS hello world

Input: `typical_creature_dragon.png` (563,963 bytes), fetched from the
`trellis-community/TRELLIS` Space repository at run time.

| Check | Expected | Actual |
| --- | --- | --- |
| `microsoft/TRELLIS` usable | plan's preferred Space | **`CONFIG_ERROR`, no hardware** — down |
| A TRELLIS Space answers | yes | two do: `trellis-community/TRELLIS`, `microsoft/TRELLIS.2` |
| Image in → GLB out | one GLB | **two GLBs**, one per running Space |
| Artifact re-loads | non-zero, finite geometry | both load; metrics below |

Measured artifacts (`*.measurements.json` beside each GLB):

| Metric | `trellis-community/TRELLIS` | `microsoft/TRELLIS.2` |
| --- | --- | --- |
| endpoint | `/generate_and_extract_glb` (1 call) | `/preprocess_image`→`/image_to_3d`→`/extract_glb` |
| generation time | 21.0 s | 65.0 s |
| file size | 1,745,380 B | 9,965,912 B |
| vertices / faces | 10,028 / 13,050 | 192,190 / 293,665 |
| extents (x, y, z) | 1.003, 0.728, 0.998 | 0.799, 0.595, 0.997 |
| surface area | 1.6015 | 2.0044 |
| watertight | False | False |
| connected components | 342 | 3,320 |
| all coordinates finite | True | True |
| textured | True | True |

Both meshes are normalized to roughly a unit cube, textured, and heavily
fragmented — untrusted topology, exactly what the canonicalization layer is
for. `volume` is reported but meaningless on a non-watertight mesh.

### Failures Reproduced And Fixed

| Failure | Cause | Fix in the script |
| --- | --- | --- |
| `ReadTimeout` connecting to `trellis-community/TRELLIS` | cold Space handshake | 300 s httpx timeout, 3 connect attempts |
| `AppError(...has not enabled verbose error reporting)` in 0.3 s on `/image_to_3d` | partial parameter list rejected upstream | `build_kwargs` sends every declared parameter, defaults taken from `view_api` |
| `ImportError: no graph engines available!` after a successful paid generation | `trimesh` needs a graph engine for connected components | `scipy` + `networkx` in the dependency block; the metric degrades to a recorded string instead of losing the run |
| `UnicodeEncodeError: 'charmap'` printing a result | Windows cp1252 console vs emoji in Space payloads | stdout/stderr reconfigured to UTF-8 in `_common.py` |

### Quota — Measured, Not Assumed

After four generations both Spaces refused further calls:

```text
You have exceeded your free ZeroGPU quota (120s requested vs. 156s left).
Try again in 23:51:16. Subscribe to Hugging Face PRO to get 25 min of
ZeroGPU quota a day.
```

Each call reserves 120 s of budget up front regardless of actual runtime, the
budget is shared across all ZeroGPU Spaces for the account, and it resets on a
24 h timer — roughly **four free generations per day**. `--probe-only` and
`--measure` exist so script iteration costs none of it.

## Runtime Proof — Phases 2-6, Bringup Implementation (2026-08-25)

### Environment

- Windows 11, `uv` 0.11.19. `uv sync` succeeds from this checkout and
  provisions CPython 3.12.13 per `.python-version`.
- Resolved versions of note: pydantic 2.13.4, trimesh 5.0.0, numpy 2.5.2,
  scipy 1.18.1, networkx 3.6.1, gradio-client (installed via `gradio-client`),
  pytest 9.1.1, ruff 0.16.4.
- Project selected through `.env`: `CHARCTX_PROJECT=C:\Users\wassi\My Drive\
  Projects\3d-models\characters-generation` (a cloud-synced path containing
  spaces).

### Commands And Results

| Command | Expected | Actual |
| --- | --- | --- |
| `uv sync` | clean environment | pass |
| `uv run pytest` | offline suite green | **65 passed, 1 skipped** (the skip is the `live` test) in 0.6 s |
| `uv run ruff check .` | clean | **All checks passed** |
| `uv run charctx info` | project, backend, tool state | pass — project selected, `trellis2` credentialed, `blender 5.2.1: installed` |
| `uv run charctx paths` | every write location | pass |
| `uv run charctx backends` | implemented vs documented | pass — `trellis2` implemented; 4 alternatives listed as documentation only |
| `uv run charctx project info` | active project contents | pass — `exists: True`, `scaffolded: True` |
| `uv run charctx fetch blender` | provision + verify | pass — **`Blender 5.2.1 LTS`** |
| `uv run charctx report <glb>` | metrics for a real mesh | pass — see below |
| `uv run charctx generate …` | mesh in a fresh slot | **blocked by quota** — see below |

### `charctx fetch blender`

Fetched the pinned artifact from `config/artifacts.yaml` alone:

```text
blender 5.2.1 provisioned
  executable: C:\dev\VectorMind\3d-character-context\.tools\blender\blender.exe
  verified  : Blender 5.2.1 LTS
```

- 404,851,964 bytes downloaded, SHA-256 verified against the vendor's
  published `blender-5.2.1.sha256` before extraction.
- The executable path carries no version number, so a pin bump does not move
  it.
- Failure reproduced and fixed on the way: `PermissionError: [WinError 5]`
  renaming the extracted directory while Windows still held handles on the
  freshly written executables. The rename now retries with backoff and falls
  back to a copy; the second run succeeded with the cached archive, no
  re-download.
- Recorded contradiction with the plan: 5.2.1 reports itself as **LTS**,
  where the plan assumed the 5.x line was non-LTS.

### `charctx report` On A Real TRELLIS.2 Artifact

Measured the GLB the Phase 1 experiment brought back from
`microsoft/TRELLIS.2`:

```text
  format     : glb (9,965,912 bytes, 1 geometry/ies)
  vertices   : 192,190
  faces      : 293,665
  extents    : 0.7991 x 0.5952 x 0.9970
  bounds     : -0.3995 -0.2978 -0.4975  ->  0.3996 0.2975 0.4996
  area       : 2.0044
  volume     : n/a (not watertight)
  watertight : False
  components : 3320
  degenerate : 1 face(s)
  finite     : True
  textured   : True
  sampled    : 2048 surface point(s)
  plausible  : True
```

Every metric the handoff's first milestone asks for is present. `volume` is
correctly withheld on a non-watertight surface rather than reported as a
number that means nothing.

### `charctx generate` Against The Live Space

```powershell
uv run charctx generate "…\inputs\references\trellis-example-dragon.png" --name red-dragon --seed 42
```

```text
  connecting to microsoft/TRELLIS.2
  preprocessing reference image
  generating 3D asset (reserves GPU quota)
error: QuotaExhausted: You have exceeded your free ZeroGPU quota (120s
requested vs. 156s left). Try again in 23:26:18. Subscribe to Hugging Face
PRO to get 25 min of ZeroGPU quota a day - …
```

What this **does** prove, against the real Space and not a mock: `.env`
loading, project selection over a cloud-synced path with spaces, run-slot
allocation, credential resolution, Space connection, `view_api` retrieval,
session start, image preprocessing (which round-tripped a real file), and the
full-parameter `/image_to_3d` submission. It fails exactly at the GPU
reservation, which the day's Phase 1 experiment had already spent.

What it does **not** prove: that a mesh comes back and lands in the slot.
That is the one outstanding exit criterion.

Two behaviors verified from the failure itself:

- the empty run slot was discarded —
  `generated/trellis2/` is empty, with no `red-dragon-001` left to be
  mistaken for a real run;
- the provider's message reaches the operator unedited, numbers and reset
  time included.

### Offline Test Coverage (65 tests)

| File | What it proves |
| --- | --- |
| `test_contracts.py` (9) | Missing images, bad slugs, empty image lists, and unknown top-level fields are all rejected; non-mesh artifacts are refused; the plausibility gate rejects empty and non-finite geometry |
| `test_config.py` (10) | The real environment beats `.env`; comments and blanks are ignored; a missing credential names its variable; `mask()` leaks no fragment of a value; committed YAML carries no secret; unknown backends and artifacts list the known ones; documented alternatives are not selectable; the Blender pin is exact |
| `test_project.py` (8) | Selection precedence; a missing selection names both the variable and the flag; scaffolding is idempotent and refused inside the repository; run slots increment, skip taken numbers, and never collide; `describe()` creates nothing |
| `test_mesh_report.py` (8) | A radius-0.5 icosphere measures its known area and extents; two disconnected boxes count as 2 components; a non-watertight mesh reports no volume; measuring writes nothing; the sidecar round-trips; unloadable files error clearly |
| `test_artifacts.py` (7) | The archive root is flattened; fetch is idempotent; `--force` replaces stale content; a checksum mismatch leaves no file behind; verifying an unprovisioned tool names the fetch command |
| `test_backend_trellis2.py` (11) | Against the Space's **recorded API description**: slots are fresh and never reused; session ordering; **every declared parameter is sent**; option precedence; `request.json` contents; the reference image travels with the result; quota refusal is its own error; a changed Space API is reported; no provider-native payload escapes |
| `test_cli.py` (12) | JSON and text output for every read command; no credential in output; sidecar writing and `--no-write`; exit code 2 for configuration errors and 1 for others; `--option` type coercion |
| `test_live_trellis2.py` (1) | Gated behind `CHARCTX_LIVE=1`; skipped in this run |

Fixtures: `tests/fixtures/trellis2_view_api.json` is the live Space's own API
description, recorded once with no GPU cost — so the offline suite checks the
real contract. All mesh fixtures are constructed at test time with trimesh,
so no binary data enters the repository.

### Data Workspace

One file was added to the co-workspace through its documented intake flow:
`inputs/references/trellis-example-dragon.png` (563,963 bytes, unmodified
original) with `trellis-example-dragon.provenance.md` beside it recording
source URL, origin, acquisition date, and rights. Nothing else in the data
workspace was modified; `generated/` remains empty.

## Known Gaps

- **One exit criterion is unmet: no live `charctx generate` has produced a
  mesh.** The path is proven up to the GPU reservation; the free ZeroGPU
  budget was spent by the Phase 1 experiment on the same day. Repeat the
  documented command after the quota resets.
- The `live` smoke test has never run green, for the same reason.
- Commercial free tiers (Meshy, Tripo, Rodin) are unprobed by maintainer
  direction, and the Hunyuan3D Spaces were never called; both remain
  documented alternatives asserted from documents rather than exercised.
- No quality judgement on any generated mesh - only measurement. Choosing
  between TRELLIS.2 and the faster, lower-density community Space on output
  quality needs a real dragon reference and more quota.
- Blender is provisioned and verified, but no pipeline stage invokes it, so
  the subprocess boundary is specified and untested.
- `charctx fetch` handles zip archives only, and the Blender pin is
  Windows-only; another platform is refused with a clear message rather than
  silently given a wrong binary.
- The canonical layer does not exist: `CanonicalizationResult` and
  `RiggedCharacterResult` are validated shapes with no behavior behind them.
- Provider behavior is a moving target and this proof is a snapshot: Space
  runtime stages, quota rules, and router catalogues were true on 2026-08-25
  and are re-provable by re-running `experiments/` and the suite.
