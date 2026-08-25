# Plan: 3D Character Context Initial Bringup

Date: 2026-08-25
Status: Planning — open points under discussion, nothing accepted yet.

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
below). Nothing is accepted yet; each row names the current proposal.

| OP | Topic | Proposal | Confidence | Status |
| --- | --- | --- | --- | --- |
| OP-001 | Package and CLI naming | `character_context` package, `charctx` CLI; `western_dragon` is a character family, not the package name | medium | open |
| OP-002 | Python version and tooling | uv + hatchling, ruff + pytest, `>=3.11,<3.13`, pin 3.12 | high (tooling) / medium (version window) | open |
| OP-003 | First hosted generation backend | TRELLIS via fal.ai, image-to-3D; endpoint verified at implementation | medium | open |
| OP-004 | Backend abstraction and registry | `GeneratorBackend` protocol + `GeneratorSpec` registry + pydantic contracts; provider responses never leak | high | open |
| OP-005 | Geometry stack staging | Milestone 1: numpy + trimesh only; Open3D deferred to coarse-fit packet; torch/PyTorch3D deferred to non-rigid packet as optional extras | high | open |
| OP-006 | Output layout and paid-result caching | Typed `.cache/` layout; generated artifacts under `.cache/generated/<backend>/<slug>/` with request metadata persisted beside every download | medium | open |
| OP-007 | Provider credentials | Env vars / git-ignored `.env`; `config/providers.yaml` declares endpoints, never secrets | high | open |
| OP-008 | Single-interface rule | Adopt cad-context's rule: documented CLI for humans and agents, side-effect-free Python API, no agent skills | high | open |
| OP-009 | Canonical template sourcing (direction only) | Hand-author/adapt in Blender from a CC-licensed base mesh; full decision deferred to the milestone-2 packet | low | open |
| OP-010 | Blender integration boundary | Not a dependency of this packet; later packets use a headless Blender subprocess behind a backend class, never `bpy` in the core environment | medium | open |

## Goal And Objectives

- A uv-managed `pyproject.toml` with a small base plus optional-dependency
  groups, mirroring the cad-context conventions.
- Core contracts as pydantic models: `GenerationRequest`,
  `RawCharacterResult`, `CanonicalizationResult`, `RiggedCharacterResult`
  (the latter two defined but unused yet), plus the `GeneratorBackend`
  protocol and a `GeneratorSpec` registry.
- One working hosted TRELLIS backend: reference image in, GLB downloaded and
  persisted with its request metadata.
- trimesh-based mesh reporting producing `*.measurements.json` with the
  handoff metrics: vertex/face counts, bounding box, connected components,
  surface area, watertightness, sampled point count, file size, backend, and
  seed/request metadata.
- A CLI skeleton (`info`, `generators`, `generate`, `report`, `paths`) with
  every shipped command documented in `README.md`.
- First specs folded from the accepted decisions (workspace layout, agent
  interface, generator-backend contract, mesh-report contract).

## Scope And Non-Goals

In scope: environment, contracts, one hosted backend, artifact download and
persistence, mesh measurement, CLI + Python API skeleton, tests around the
artifact boundary, spec fold.

Non-goals (handoff "Critical Non-Goals" plus packet-level deferrals): the
canonical template asset, landmarks, any registration or fitting, rigging,
Blender integration, texture transfer, a web app, Hunyuan3D and commercial
backends (the protocol must merely make them obviously addable), LoRA/model
adaptation, self-hosting GPU models.

## Open Points

### OP-001 — Package and CLI naming

The handoff sketches `dragon-context/` with package `dragon_context`; the
repository is named `3d-character-context`, and the handoff's own product
hypothesis generalizes to multiple character-family canonicalizers with
`western_dragon` as the only V1 family.

- Options:
  - **`character_context` / `charctx`**: matches the repository name and the
    generalization hypothesis; dragons become the first family, not the
    brand; consistent with the sibling `cad_context`/`cadctx` pattern.
  - **`dragon_context` / `dragonctx`**: matches the handoff text literally;
    honest about V1 scope; would need a rename if a second family ever
    lands.
  - **`char3d` or similar short name**: shorter to type, but breaks the
    `*-context` family convention.
- Proposal: `character_context` package, `charctx` CLI. The handoff already
  treats the family registry (`canonicalizers = {"western_dragon": ...}`) as
  the end-state architecture; naming the package after one family bakes the
  V1 restriction into the wrong layer.
- Confidence: medium. Status: **open**.

### OP-002 — Python version and tooling

- Options:
  - **`>=3.11,<3.13`, pin 3.12**: safest overlap for the 3D stack — Open3D
    and PyTorch wheels are solid at 3.11/3.12, and PyTorch3D (needed only in
    the milestone-3 packet) constrains hardest; matches cad-context's floor.
  - **`>=3.11,<3.14`, pin 3.12** (cad-context's window): slightly wider, but
    3.13 wheel coverage for Open3D/PyTorch3D is the risk.
  - **`>=3.12` only**: newest baseline, no benefit to dropping 3.11.
- Tooling: uv for env/lock, hatchling build, ruff + pytest in the dev group,
  line length 88, `testpaths = ["tests"]` — identical to cad-context
  conventions. No serious alternative candidates given the sibling repo.
- Proposal: `>=3.11,<3.13`, pinned in `.python-version` to 3.12; widen later
  if the heavy geometry extras prove 3.13-clean.
- Confidence: high for tooling, medium for the version window (dominated by
  OP-005's deferred heavy dependencies). Status: **open**.

### OP-003 — First hosted generation backend

The handoff mandates image-to-3D (not text-to-3D) and prefers TRELLIS.2
hosted; hosting must be abstracted regardless.

- Options:
  - **TRELLIS via fal.ai**: handoff-preferred generator on a serverless
    provider with a plain HTTPS API, queueing, and retries; no GPU
    maintenance. Risk: which TRELLIS variant (original vs TRELLIS.2) is
    actually live on fal must be verified at implementation time.
  - **Hunyuan3D via fal.ai**: also genuine shape generation; the handoff
    ranks it as the second backend, not the first.
  - **Hugging Face Space via `gradio_client`**: good for discovery and free
    experimentation, but interactive Spaces are weak for a repeatable batch
    boundary (cold starts, queue opacity, breaking UI changes).
  - **Commercial API first (Tripo/Meshy/Rodin)**: most polished end-to-end,
    but bundles remeshing/rigging that would blur exactly the boundary this
    repository exists to own; handoff positions them as quality baselines.
- Proposal: TRELLIS on fal.ai as the first backend. The backend id encodes
  provider and model (e.g. `trellis-fal`); the concrete endpoint and model
  variant are recorded in `implementation.md` when verified. If TRELLIS.2 is
  not hosted anywhere usable at implementation time, fall back to hosted
  TRELLIS or Hunyuan3D on the same provider without changing the protocol.
- Confidence: medium (hosted availability is external and shifting).
  Status: **open**.

### OP-004 — Backend abstraction and registry

- Options:
  - **Protocol + registry (handoff sketch)**: `GeneratorBackend` protocol
    with `generate(request) -> RawCharacterResult`; `GeneratorSpec` entries
    (id, family, provider, mode, output formats) in a registry, mirroring
    the proven cad-context workbench pattern.
  - **Plain functions per provider**: less ceremony, but the swappability
    requirement is the core architectural principle of the handoff.
  - **Adopt a provider SDK's own abstractions**: leaks provider types —
    explicitly forbidden by the handoff.
- Proposal: the protocol + registry pattern, with the four pydantic
  contracts from the handoff as the only types crossing module boundaries.
  Provider SDKs (or raw HTTPS) are used strictly inside each backend module.
- Confidence: high. Status: **open**.

### OP-005 — Geometry stack staging

The handoff's full stack (numpy, trimesh, Open3D, torch, PyTorch3D) is only
fully needed at milestone 3; PyTorch3D on Windows has no official wheels and
is a known build hazard.

- Options:
  - **Minimal now, staged extras later**: base = pydantic, numpy, trimesh,
    HTTP client; add `[registration]` (Open3D) in the coarse-fit packet and
    `[fitting]` (torch, PyTorch3D) in the non-rigid packet, each behind its
    own optional-dependency group with graceful degradation.
  - **Full stack up front**: one sync installs everything, but pays the
    PyTorch3D-on-Windows cost before any code needs it and couples this
    packet's exit criteria to an unrelated build fight.
- Proposal: minimal now. Milestone 1 requires only trimesh for loading,
  normalization, sampling, and metrics. The optional-group layout is
  designed now (named groups reserved in `pyproject.toml`) so later packets
  add dependencies without restructuring.
- Confidence: high. Status: **open**.

### OP-006 — Output layout and paid-result caching

Hosted generation is paid and non-deterministic, which strains cad-context's
"fixed paths, no timestamps" rule: two runs of the same request produce
different, individually valuable artifacts.

- Options:
  - **Typed `.cache/` layout + slugged generation folders**: keep
    `.cache/results/`, `.cache/reports/`, `.cache/scratch/`,
    `.cache/downloads/` exactly as in cad-context; generated artifacts go to
    `.cache/generated/<backend>/<request-slug>/` containing the GLB, the
    `*.measurements.json`, and a `request.json` (backend, images, seed,
    options, provider job id, timestamps). The slug is caller-chosen
    (`--name`), defaulting to a short content-derived id, so a re-run with
    the same name overwrites deliberately and a new name preserves the paid
    result.
  - **Strictly fixed paths per backend**: matches cad-context literally but
    silently destroys paid non-deterministic results on every re-run.
  - **Timestamped folders always**: nothing is ever lost, but no stable path
    exists for iteration or downstream tooling.
- Proposal: the slugged layout. The stable-paths rule stays intact for
  everything deterministic (results, reports); generation artifacts get
  named, explicit slots because variants genuinely coexist — the same
  escape-hatch reasoning as cad-context's `--out-dir`.
- Confidence: medium. Status: **open**.

### OP-007 — Provider credentials

- Options:
  - **Env vars + git-ignored `.env`** (e.g. `FAL_KEY`): standard, works for
    agents and CI, keeps secrets out of history; `config/providers.yaml`
    declares endpoints/model ids only.
  - **Keys in a config file**: convenient, one leaked commit away from an
    incident.
  - **OS keyring**: safest locally but awkward for headless/agent use.
- Proposal: env vars with `.env` support; a missing key degrades to a clear
  actionable error naming the variable, and `info` reports which providers
  are credentialed without printing secrets.
- Confidence: high. Status: **open**.

### OP-008 — Single-interface rule

- Options: adopt cad-context's accepted OP-106/OP-108 doctrine (documented
  CLI as the single human/agent interface, no agent skills, side-effect-free
  Python API as the second surface) vs invent a different interface shape.
- Proposal: adopt it wholesale — it is proven in the sibling repository and
  `AGENTS.md` here is already written in its terms. Every capability ships
  as a documented CLI command; the Python API returns data and writes
  nothing.
- Confidence: high. Status: **open**.

### OP-009 — Canonical template sourcing (direction only)

The handoff ranks canonical asset quality as the top design-effort priority,
but the asset itself is the milestone-2 packet. What this packet should
settle is the sourcing direction, because it drives budget, licensing, and
whether Blender authoring skills are on the critical path.

- Options:
  - **Hand-author/adapt from a CC- or royalty-licensed western-dragon base
    mesh in Blender**: fastest path to clean edge flow, known regions, and a
    deliberate wing-membrane topology; licensing must permit redistribution
    of the derived canonical asset in-repo.
  - **Commission a modeler**: highest quality ceiling, external cost and
    turnaround.
  - **Generate with the hosted model, then manually retopologize**: dogfoods
    the generator but maximizes cleanup work on exactly the hardest part.
- Proposal: adapt a suitably licensed base mesh in Blender, hand-tuning
  topology to the handoff's requirements (stable vertex ordering, semantic
  regions, wing-membrane and jaw loops). Full decision — including the
  specific asset and license — belongs to the milestone-2 packet.
- Confidence: low. Status: **open** (direction only; decision deferred).

### OP-010 — Blender integration boundary

- Options:
  - **Headless Blender subprocess behind a backend class**, provisioned or
    detected like cad-context's external binaries: keeps `bpy`'s Python
    version pinning out of the core environment; Blender-specific logic
    stays behind a service boundary.
  - **`bpy` as a pip dependency**: importable directly, but hard-pins the
    interpreter version and bloats the environment for a tool milestone 1
    never touches.
  - **No Blender ever**: contradicts the handoff, which assigns Blender
    real downstream roles (shrinkwrap, armatures, baking, export).
- Proposal: no Blender dependency in this packet at all; record the
  subprocess-boundary rule now so milestone-2+ packets and the external-
  binaries spec inherit it.
- Confidence: medium. Status: **open**.

## Implementation Phases

0. **Decisions.** Maintainer reviews OP-001…OP-010; this plan is updated to
   the accepted state before code is written.
1. **Environment.** `pyproject.toml` (base + reserved optional groups per
   OP-005), `.python-version`, lockfile, `.gitignore`, package skeleton
   under `src/`, CLI entry point with `info` and `paths`, `.cache/` layout
   per OP-006.
2. **Contracts.** The four pydantic result/request models, the
   `GeneratorBackend` protocol, the `GeneratorSpec` registry,
   `config/providers.yaml`, credential handling per OP-007, and a `generators`
   CLI command listing the registry.
3. **Hosted backend.** The first TRELLIS backend per OP-003: submit a
   reference image, poll/await, download the GLB into its slugged folder
   with `request.json`; `generate` CLI command. A recorded-response fixture
   keeps tests offline.
4. **Mesh report.** trimesh loading, normalization and inspection producing
   `*.measurements.json` with all handoff metrics; `report` CLI command that
   also works on any local GLB/OBJ so it is testable without spending
   provider credit.
5. **Proof and spec fold.** pytest around every artifact boundary (offline
   via fixtures, plus one gated live smoke test), ruff clean, README command
   reference complete, and first specs folded: workspace layout, agent
   interface, generator-backend contract, mesh-report contract, and the
   canonical-conventions stub that OP-009/OP-010 feed.

## Dependencies And Risks

- Hosted TRELLIS availability and endpoint shape are external and may shift
  between planning and implementation (OP-003 fallback ordering).
- Provider costs: live tests must be explicitly gated (env-var opt-in) so
  the default suite never spends money.
- Windows wheel coverage for the deferred heavy stack (Open3D, PyTorch3D)
  is the main future risk; OP-005 keeps it out of this packet's critical
  path but OP-002's version window must anticipate it.
- The canonical asset (milestone 2) is the highest-effort, highest-risk item
  in the whole handoff; OP-009 only sets direction, and underestimating it
  later would stall milestones 2–4.
- No dependency on any other packet; this packet unblocks all of them.

## Exit Criteria

- `uv sync` succeeds from a clean checkout on Windows.
- The four core contracts and the backend protocol exist with tests.
- One documented CLI run takes a reference image through hosted generation
  to a downloaded GLB with persisted `request.json` (live, maintainer-run).
- `report` produces a `*.measurements.json` for that GLB — and for any local
  mesh fixture — containing every metric listed in the handoff's first
  milestone.
- Every shipped CLI command is documented in `README.md` with a usage line
  and example.
- `uv run pytest` and `uv run ruff check .` are clean with the default
  (offline) suite.
- `test.md` records commands, fixtures, expected and actual results.
- The Phase 5 specs exist and `specifications/README.md` indexes them.
