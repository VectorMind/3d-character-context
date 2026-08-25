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

## Known Gaps

- Commercial free tiers (Meshy, Tripo, Rodin) are still unprobed, so Phase 1
  is not complete and the first backend is not finally selected.
- `tencent/Hunyuan3D-2.1` and `tencent/Hunyuan3D-2mini-Turbo` were observed
  `RUNNING` during Space discovery but were never called; the two-stage
  Hunyuan contract remains asserted from documents.
- No quality judgement was made on either TRELLIS output — only measurement.
  Choosing between the fast, low-poly community Space and the official
  high-density `TRELLIS.2` needs a real dragon reference and more quota.
- Still no repository environment, package, CLI, or test suite: `uv sync`,
  `pytest`, `ruff`, and `charctx fetch blender` remain unproven (Phases 2–6).
- Provider behavior is a moving target and this proof is a snapshot: Space
  runtime stages, quota rules, and router catalogues were true on 2026-08-25
  and are re-provable by re-running the scripts in `experiments/`.
