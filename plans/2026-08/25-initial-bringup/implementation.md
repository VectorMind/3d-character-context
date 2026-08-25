# Implementation — 3D Character Context Initial Bringup

## Progress

`▰▱▱▱▱▱▱ Phase 1/6` — free-access experiment: Hugging Face paths validated
end to end (REST inference + TRELLIS Spaces, one GLB proven); commercial free
tiers (Meshy, Tripo, Rodin) not yet probed, then Phase 2 (environment).

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
