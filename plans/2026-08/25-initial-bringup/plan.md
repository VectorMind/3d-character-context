# Plan: 3D Character Context Initial Bringup

Date: 2026-08-25
Status: Planning — first decision pass recorded 2026-08-25: OP-001…OP-010
accepted (several with amendments), which raised three new open points
OP-011…OP-013 now awaiting decision. No implementation yet.

The founding architecture document for this repository is
[`handoff.md`](./handoff.md) in this packet. This plan scopes the first
implementation packet out of it and carries the design decisions that must be
settled before code is written.

## Problem Summary

The repository is empty apart from the handoff document. We need the first
working slice of a generative-first dragon pipeline: a Python environment, the
core pydantic contracts, one hosted image-to-3D generator backend, and
trimesh-based mesh inspection — proving the hosted-generation boundary
end-to-end (handoff "First Milestone"):

```text
reference image → hosted generation → raw_dragon.glb → raw_dragon.measurements.json
```

Canonicalization, skeleton fitting, and the canonical template asset are
later packets (handoff milestones 2–5); this packet only prepares their
contracts and conventions.

## Resolution Summary

One-glance state of all open points (details in the Open Points section
below).

| OP | Topic | Resolution / Proposal | Confidence | Status |
| --- | --- | --- | --- | --- |
| OP-001 | Package and CLI naming | `character_context` package, `charctx` CLI | high | **accepted 2026-08-25** |
| OP-002 | Python version and tooling | uv + hatchling, ruff + pytest, `>=3.11,<3.13`, pin 3.12 — pin may tighten to 3.11 if OP-013 selects the `bpy` wheel | high (tooling) / medium (pin) | **accepted 2026-08-25** (pin revisit linked to OP-013) |
| OP-003 | First hosted generation backend | Hugging Face first; fal.ai, Hunyuan3D endpoints, and commercial APIs documented as alternatives only (README/spec), no code for them | medium | **accepted 2026-08-25 with amendment** |
| OP-004 | Backend abstraction depth | Relaxed: shared pydantic contracts + one concrete backend module; no protocol/registry machinery until a second backend actually lands; backend-specific behavior stays specific | medium | **accepted 2026-08-25 with amendment** |
| OP-005 | Geometry stack staging | Milestone 1: numpy + trimesh only; Open3D / PyTorch3D / PyMeshLab / libigl documented as staged alternatives, not installed | high | **accepted 2026-08-25** |
| OP-006 | Output layout and paid-result caching | Append-only: every paid generation gets its own new folder, never overwritten; generation artifacts live in the project folder (OP-009), repository `.cache/` keeps operational output | high | **accepted 2026-08-25 with amendment** |
| OP-007 | Provider credentials | Env vars / git-ignored `.env`; YAML config declares endpoints, never secrets | high | **accepted 2026-08-25** |
| OP-008 | Single-interface rule | Documented CLI for humans and agents, side-effect-free Python API, no agent skills | high | **accepted 2026-08-25** |
| OP-009 | Data/code split | Code repo holds only code and contracts; all input images, generated meshes, and canonical assets live in an external, uncommitted project folder — removing licensing constraints and enabling any base model; full automation, no hand-modelling dependence | high | **accepted 2026-08-25 with amendment** (contract details → OP-012) |
| OP-010 | Blender role | Blender is a first-class mandatory workspace tool, not optional: any library a pipeline stage needs is installed as part of the main flow, no redundant-optional variants | high | **accepted 2026-08-25 with amendment** (mechanism → OP-013) |
| OP-011 | Hugging Face access mechanism | `gradio_client` against an official public Space (TRELLIS or Hunyuan3D-2), HF token from `.env`; dedicated Inference Endpoint as the escalation path | medium | open (new) |
| OP-012 | Project-folder contract | Minimal for bringup: `charctx project init/use` + `--project`, conventional `inputs/ generated/ assets/` layout; manifest schema deferred until project-local code is needed | medium | open (new) |
| OP-013 | Blender install mechanism | Provisioned headless Blender binary in `.tools/` driven by subprocess (proposal) vs `bpy` pip wheel (pins Python to the wheel's version, currently 3.11) | medium | open (new) |

## Goal And Objectives

- A uv-managed `pyproject.toml` with a small base, mirroring the cad-context
  conventions (OP-002); no speculative optional groups — dependencies are
  added when a pipeline stage needs them (OP-010 doctrine).
- Core contracts as pydantic models: `GenerationRequest` and
  `RawCharacterResult` used now; `CanonicalizationResult` and
  `RiggedCharacterResult` defined for later packets (OP-004, relaxed).
- One working Hugging Face backend: reference image in, GLB downloaded into
  the project folder with its request metadata, append-only (OP-003, OP-006,
  OP-011).
- Minimal project-folder support so data never enters the code repo
  (OP-009, OP-012).
- trimesh-based mesh reporting producing `*.measurements.json` with the
  handoff metrics: vertex/face counts, bounding box, connected components,
  surface area, watertightness, sampled point count, file size, backend, and
  seed/request metadata.
- A CLI skeleton (`info`, `project`, `generate`, `report`, `paths`) with
  every shipped command documented in `README.md` (OP-008).
- First specs folded from the accepted decisions, including a documented
  alternatives section for backends (OP-003) and geometry libraries
  (OP-005) so strategy changes are cheap.

## Scope And Non-Goals

In scope: environment, contracts, one Hugging Face backend, minimal project
folder, artifact download and append-only persistence, mesh measurement,
CLI + Python API skeleton, tests around the artifact boundary, spec fold.

Non-goals (handoff "Critical Non-Goals" plus packet-level deferrals): the
canonical template asset, landmarks, any registration or fitting, rigging,
Blender usage (mechanism decided via OP-013, install lands with the first
stage that needs it), texture transfer, a web app, any second backend in
code (fal.ai, Hunyuan3D, Tripo/Meshy/Rodin remain documentation-only
alternatives), LoRA/model adaptation, self-hosting GPU models, the full
project manifest contract.

## Open Points

### OP-001 — Package and CLI naming

- Options considered: `character_context`/`charctx` (matches repo name and
  the multi-family end-state), `dragon_context`/`dragonctx` (handoff
  literal), short names like `char3d`.
- Resolution: **`character_context` package, `charctx` CLI.**
  `western_dragon` is the first character family, not the package name.
- Confidence: high. Status: **accepted 2026-08-25** as proposed.

### OP-002 — Python version and tooling

- Options considered: `>=3.11,<3.13` pin 3.12 vs cad-context's `<3.14`
  window vs 3.12-only.
- Resolution: **uv + hatchling, ruff + pytest dev group, line length 88,
  `>=3.11,<3.13`, `.python-version` pinned to 3.12** — identical tooling to
  cad-context.
- Linked revisit: if OP-013 selects the `bpy` pip wheel, the pin tightens to
  the wheel's Python (currently 3.11); the window already covers it.
- Confidence: high (tooling) / medium (pin, pending OP-013).
  Status: **accepted 2026-08-25**.

### OP-003 — First hosted generation backend

- Options considered: TRELLIS via fal.ai (original proposal), Hunyuan3D via
  fal.ai, Hugging Face Space, commercial APIs (Tripo/Meshy/Rodin).
- Resolution (maintainer amendment): **start with Hugging Face**, and list
  the others — fal.ai serverless endpoints, Hunyuan3D hosted variants, and
  the commercial APIs — as **documented alternatives in the README and the
  generator-backend spec, with no code for them**. The documentation entry
  for each alternative records what it offers and roughly how it would be
  integrated, so switching or adding later is cheap and deliberate.
- Rationale: keeps early experimentation free/cheap and inside the HF
  discovery ecosystem the handoff already assigns to model exploration;
  avoids committing spend and integration effort while the 3D-generation
  API landscape is immature.
- Confidence: medium (public-Space reliability is the known weakness — see
  OP-011 for the mechanism). Status: **accepted 2026-08-25 with amendment**.

### OP-004 — Backend abstraction depth

The maintainer relaxed the original protocol + registry proposal: the
3D-generation API landscape is not mature enough to justify heavy
abstraction; abstract only what is genuinely common.

What the real APIs look like (survey backing the resolution):

- **TRELLIS (HF Space)**: image(s) → GLB (plus Gaussian-splat preview),
  with numeric knobs (seed, per-stage guidance strengths and sampling
  steps). Cleanly image-to-3D.
- **Hunyuan3D-2 (HF Space / hosted)**: **two-stage** — shape generation
  (image → untextured mesh) then texture paint (mesh + image → textured
  mesh), each with its own options (background removal, steps, guidance,
  octree resolution, target face count).
- **Meshy / Tripo / Rodin (commercial REST)**: task-based — create task
  (image URL + options such as topology, target polycount, PBR, optional
  rigging), poll a job id, download from result URLs in several formats.
  Some bundle rigging/remeshing extras that go beyond generation.

Common denominator: `submit(image(s), options) → job → poll → mesh
artifact(s)`. That much is real but shallow; staging (Hunyuan's two steps),
rigging extras, and multiview handling are backend-specific.

- Resolution: **abstract only the shallow common denominator.** Keep the
  pydantic `GenerationRequest` (images, prompt, seed, free-form `options`
  dict) and `RawCharacterResult` (artifact path + metadata) as the only
  types crossing module boundaries; each backend is a plain module exposing
  `generate(request) -> RawCharacterResult`, free to implement staging or
  provider-specific behavior internally. **No `GeneratorBackend` protocol
  class, no `GeneratorSpec` registry** until a second backend actually
  lands in code — at which point the then-known shape of two real backends
  drives the abstraction. Provider-native responses still never leak past
  the backend module.
- Confidence: medium. Status: **accepted 2026-08-25 with amendment**.

### OP-005 — Geometry stack staging

- Options considered: minimal-now vs full handoff stack up front.
- Resolution: **minimal now** — base = pydantic, numpy, trimesh, HTTP/Space
  client. **All other candidates stay documented but uninstalled** so a
  strategy change is a doc-informed decision, not archaeology: Open3D
  (rigid registration/ICP, milestone 2), PyTorch + PyTorch3D (non-rigid
  fitting, milestone 3; Windows wheel hazard noted), PyMeshLab and libigl
  (repair/processing alternatives). The generator-backend/geometry spec
  carries this alternatives list; per OP-010 doctrine, when a stage needs
  one, it is installed as a mandatory part of the main flow, not as an
  optional extra.
- Confidence: high. Status: **accepted 2026-08-25**.

### OP-006 — Output layout and paid-result caching

- Options considered: fixed paths (overwrites), slugged folders with
  deliberate overwrite, timestamped always.
- Resolution (maintainer amendment): **cache every paid result, never
  overwrite.** Generation output is append-only: each run gets a fresh
  folder — `<project>/generated/<backend>/<name>-<NNN>/` (caller-chosen
  name plus an incrementing suffix, or the provider job id) — containing
  the mesh artifact(s), `request.json` (backend, images, seed, options,
  job id, timestamps), and later its `*.measurements.json`. Combined with
  OP-009, generated data lives in the project folder; the repository
  `.cache/` keeps only operational output (`results/`, `reports/`,
  `scratch/`, `downloads/`) exactly as in cad-context.
- Confidence: high. Status: **accepted 2026-08-25 with amendment**.

### OP-007 — Provider credentials

- Resolution: **env vars with git-ignored `.env` support** (e.g. `HF_TOKEN`);
  `config/providers.yaml` declares endpoints/Space ids/model ids only,
  never secrets. A missing key produces a clear error naming the variable;
  `info` reports which providers are credentialed without printing secrets.
- Confidence: high. Status: **accepted 2026-08-25** as proposed.

### OP-008 — Single-interface rule

- Resolution: **adopted** — the documented `charctx` CLI is the single
  interface for humans and agents, no agent skills, routing via
  README/AGENTS documentation; the side-effect-free Python API is the
  second surface and writes nothing.
- Confidence: high. Status: **accepted 2026-08-25** as proposed.

### OP-009 — Data/code split (supersedes "canonical template sourcing")

Original framing (how to source the canonical template) was superseded by a
structural decision.

- Resolution (maintainer amendment): **split the project data repo from
  this code repo, as cad-context does.** All input data (reference images),
  all generated 3D outputs, and the canonical template assets live in an
  external project folder that is never committed to git. Consequences:
  - no licensing constraint on base meshes or generated content — any
    suitable existing model, including closed/limited-license ones, can be
    used because nothing is redistributed;
  - the pipeline must be **fully automated** — the workflow does not assume
    a skilled 3D author/modeller; canonical-template production in
    milestone 2 must be scripted (automation over existing models plus
    Blender processing), not hand-sculpting;
  - the repository's earlier `assets/` convention is dropped; there is no
    committed asset directory.
- The concrete project-folder contract is split out as OP-012. The
  milestone-2 question of *which* base model/asset to canonicalize remains
  deferred to that packet, now free of licensing pressure.
- Confidence: high. Status: **accepted 2026-08-25 with amendment**.

### OP-010 — Blender role (supersedes "integration boundary")

Original proposal (keep Blender out, subprocess boundary later) was
partially reversed.

- Resolution (maintainer amendment): **Blender is an important tool in the
  workflow and therefore a first-class dependency of this workspace**, not
  an optional extra. The general doctrine: this repository no longer runs
  many optional tests with redundant libraries — when a solution pipeline
  needs more than one tool/library, all of them are installed as part of
  the main flow. Graceful-degrade complexity is reserved for genuinely
  external, unavoidable absences, not used to make core tools optional.
- What stays from the original analysis: milestone 1 (this packet's
  hosted-generation slice) has no Blender-using stage, so the Blender
  install itself lands with the first pipeline stage that calls it; the
  *mechanism* must be decided now and is split out as OP-013.
- Confidence: high (doctrine) / medium (mechanism, see OP-013).
  Status: **accepted 2026-08-25 with amendment**.

### OP-011 — Hugging Face access mechanism (new, from OP-003)

Choosing "Hugging Face" leaves the concrete integration open: HF's serverless
Inference API does not serve image-to-3D pipelines, so the realistic routes
are Spaces or dedicated endpoints.

- Options:
  - **`gradio_client` against an official public Space** (e.g.
    `microsoft/TRELLIS`, `tencent/Hunyuan3D-2`): zero hosting cost, exact
    parity with the demo the model authors maintain; weaknesses are queues,
    ZeroGPU quotas, cold starts, and Space UI/API changes breaking the
    client — acceptable for a bringup boundary, and the failure modes are
    visible and loggable.
  - **Duplicate the Space into our own HF account** (free or upgraded
    hardware): insulates from upstream UI churn and shares no public
    queue; still `gradio_client`, small config change.
  - **HF Inference Endpoint (dedicated)**: reliable and private but paid
    GPU-hours — the escalation path once the pipeline is worth stabilizing,
    not the first step.
- Sub-choice — which Space first: **TRELLIS** (handoff-preferred generator,
  single-stage image→GLB, simplest contract) vs **Hunyuan3D-2** (two-stage,
  textured output). Proposal: TRELLIS first; Hunyuan3D-2 documented as the
  second target.
- Proposal: `gradio_client` against the official TRELLIS Space, `HF_TOKEN`
  from `.env`, Space id in `config/providers.yaml`; duplicate-the-Space as
  the first mitigation if the public queue proves unusable; dedicated
  endpoint documented as the escalation path. Exact Space id and API
  surface verified and recorded at implementation time.
- Confidence: medium. Status: **open**.

### OP-012 — Project-folder contract (new, from OP-009)

How much of cad-context's external-project machinery does bringup need?

- Options:
  - **Minimal**: `charctx project init <path>` scaffolds a conventional
    layout (`inputs/`, `generated/`, `assets/`), `project use/clear/info`
    persists a pointer under `.cache/`, global `--project` overrides for
    one command. No manifest, no project-local Python code, no collision
    rules — those exist in cad-context because projects carry generator
    code, which our projects do not (yet).
  - **Full cad-context contract now** (manifest schema, trusted project
    code loading): maximum symmetry with the sibling repo, but speculative —
    nothing in milestones 1–5 requires project-local code.
  - **Just a `--project` path argument, no persistence**: least code, but
    every command invocation must repeat the path, which is hostile to the
    iterative loop.
- Proposal: minimal contract with the persisted pointer (first option).
  Layout inside a project:

  ```text
  <project>/
    inputs/                  # reference images
    generated/<backend>/<name>-<NNN>/   # append-only, per OP-006
    assets/                  # canonical template assets (milestone 2+)
  ```

  A manifest is introduced only when a later packet gives projects
  configuration or code of their own.
- Confidence: medium. Status: **open**.

### OP-013 — Blender install mechanism (new, from OP-010)

Blender is mandatory in the workflow (OP-010); the question is how it enters
the environment.

- Options:
  - **Provisioned headless binary**: declared in `config/artifacts.yaml`
    cad-context-style, fetched into `.tools/blender/` by a `charctx fetch`
    command, driven via `blender --background --python <script>`
    subprocess. No coupling to the workspace Python version (keeps
    OP-002's 3.12 pin), uses full official builds, and pipeline scripts run
    inside Blender's own bundled Python.
  - **`bpy` pip wheel**: `import bpy` directly in-process — nicer to
    program against and easier to test, but the wheel is built for exactly
    one Python version (currently 3.11), which would tighten the OP-002
    pin, and it trails/subsets full Blender builds.
  - **Both** (wheel for library-style use, binary for export/render jobs):
    two Blender surfaces to keep consistent — against the OP-010
    no-redundancy doctrine.
- Proposal: the provisioned headless binary. It is the mandatory-but-
  external pattern this workspace already plans for provisioned tools,
  keeps the Python pin free, and matches how Blender is exercised in batch
  (`--background`) anyway. Revisit only if subprocess round-trips prove to
  dominate milestone-2 iteration time.
- Confidence: medium. Status: **open**.

## Implementation Phases

0. **Decisions.** OP-001…OP-010 accepted 2026-08-25 (amendments recorded
   above). Remaining before code: maintainer decision on OP-011…OP-013.
1. **Environment.** `pyproject.toml` (base deps only, per OP-004/OP-005),
   `.python-version`, lockfile, `.gitignore`, `src/character_context/`
   package skeleton, `charctx` entry point with `info` and `paths`,
   repository `.cache/` operational layout.
2. **Contracts and project folder.** The four pydantic models (two used,
   two reserved), `config/providers.yaml`, `.env` credential loading per
   OP-007, and the minimal project commands per OP-012.
3. **Hugging Face backend.** The first backend module per OP-011: submit a
   reference image to the Space, await, download artifact(s) into the
   append-only `generated/` slot with `request.json`; `generate` CLI
   command. A recorded-response fixture keeps the default test suite
   offline and free.
4. **Mesh report.** trimesh loading, normalization and inspection producing
   `*.measurements.json` with all handoff metrics; `report` CLI command
   that also works on any local GLB/OBJ so it is testable without any
   provider call.
5. **Proof and spec fold.** pytest around every artifact boundary (offline
   via fixtures, plus one env-gated live smoke test), ruff clean, README
   command reference complete, and first specs folded: workspace layout +
   project folder, agent interface, generator-backend contract **including
   the documented backend alternatives** (fal.ai, Hunyuan3D, Tripo, Meshy,
   Rodin) **and staged geometry-library alternatives** (Open3D, PyTorch3D,
   PyMeshLab, libigl), mesh-report contract, and the Blender mechanism
   rule from OP-013.

## Dependencies And Risks

- Public HF Space reliability (queues, ZeroGPU quotas, API churn) is the
  main external risk of the OP-003 amendment; OP-011's duplicate-Space and
  dedicated-endpoint paths are the documented mitigations, and the
  relaxed OP-004 boundary keeps a later provider switch cheap.
- Free-tier generation quality/latency may pressure an early move to a paid
  alternative; because alternatives are documented but not coded, that
  move is a deliberate small packet, not a rewrite.
- The OP-013 outcome feeds back into OP-002's Python pin; deciding OP-013
  before Phase 1 avoids re-locking the environment.
- Windows wheel coverage for the deferred heavy stack (Open3D, PyTorch3D)
  remains the main future risk for milestones 2–3.
- Full automation of canonical-template production (OP-009) raises
  milestone 2's automation bar — previously hand-authoring was an option;
  now scripted derivation over existing models plus Blender processing is
  the required path.
- No dependency on any other packet; this packet unblocks all of them.

## Exit Criteria

- `uv sync` succeeds from a clean checkout on Windows.
- The core contracts exist with tests; provider-native responses do not
  appear outside the backend module.
- `charctx project init/use` produces and selects a project folder; no
  command writes input or generated data anywhere inside the code repo.
- One documented CLI run takes a reference image through Hugging Face
  generation to a downloaded mesh in a fresh append-only `generated/` slot
  with `request.json` (live, maintainer-run); repeating the run creates a
  new slot and overwrites nothing.
- `report` produces a `*.measurements.json` for that mesh — and for any
  local mesh fixture — containing every metric listed in the handoff's
  first milestone.
- Every shipped CLI command is documented in `README.md` with a usage line
  and example; the backend and geometry alternatives are documented per
  OP-003/OP-005.
- `uv run pytest` and `uv run ruff check .` are clean with the default
  (offline) suite.
- `test.md` records commands, fixtures, expected and actual results.
- The Phase 5 specs exist and `specifications/README.md` indexes them.
