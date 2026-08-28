# Agent Guidance

Read this before doing anything in the repository. Binding contracts live in
`specifications/`; this is the operational summary. The workflow itself is
defined in `WORKFLOW.md`.

## Current State

The hosted-generation slice is implemented and the canonical layer is not.
What exists: the `charctx` CLI (`info`, `paths`, `backends`, `project`,
`fetch`, `generate`, `report`), pydantic contracts, the external project
folder with append-only run slots, the `microsoft/TRELLIS.2` backend,
trimesh mesh measurement, and external-tool provisioning (Blender 5.2.1 in
`.tools/`). Hosted generation is monoview: `charctx generate` and `trellis2`
condition a run on exactly one image. Genuine multiview support is parked in
`plans/2026-08/28-multiview-support/`. What does not exist: a multiview
backend, canonical topology, landmarks, skeleton fitting, rigging, appearance
transfer.

Read `README.md` for the command reference and `specifications/README.md` for
the binding contracts. The active packet is
`plans/2026-08/25-initial-bringup/`: `plan.md` carries the design decisions
(OP-001…), `implementation.md` logs what actually landed, `test.md` holds the
proof, and `handoff.md` is the founding architecture document. Check
`plans/open.md` for what is outstanding before starting work.

Standing provider-access probes live in `experiments/`, run with
`uv run --script`. Use them to re-establish what a provider offers today
rather than trusting a document.

## Working Rules

- `uv run pytest` and `uv run ruff check .` before declaring work done. The
  default suite is offline and free; tests marked `live` run only with
  `CHARCTX_LIVE=1` and cost GPU quota.
- Hosted generation is metered: TRELLIS.2 reserves 120 s of a small daily
  ZeroGPU budget per call - roughly four generations per day on a free
  account - so do not spend a call on something a fixture or `charctx report`
  can prove.
- Add a command and its `README.md` entry together. A capability with no
  documented command is not delivered.

## Architecture In One Glance

```text
one reference image (current; multiview is future work)
        ↓ HTTPS
hosted generative 3D backend (TRELLIS / Hunyuan3D / commercial)
        ↓
raw arbitrary mesh (source surface, untrusted topology)
        ↓
deterministic canonicalization → known western-dragon topology
        ↓
canonical skeleton fit + skin weights
        ↓
verified GLB / FBX production asset
```

The generator backend is replaceable infrastructure; the canonical layer is
the product. Backend-native responses must never leak past the generator
boundary — the pipeline operates on normalized mesh artifacts and pydantic
contracts only.

## Two Surfaces

The CLI is the single documented interface for humans and agents. A
capability not reachable through a documented command is not delivered; add a
command and its README entry together. Alongside it, a side-effect-free
Python API returns data and in-memory objects without writing files; producing
artifacts stays an explicit act through the CLI or the export layer.
Throwaway scripts go in `.cache/scratch/`.

## Output Locations

Operational output stays under git-ignored `.cache/`:

| Path | Contents |
| --- | --- |
| `.cache/results/` | bounded command JSON/Markdown summaries |
| `.cache/reports/` | tracebacks and long subprocess/provider logs |
| `.cache/scratch/`, `.cache/downloads/` | experiments and downloads |
| `experiments/` (committed) | standing provider-access probes; each run reports into `.cache/results/<date>/<time>-<experiment>/` |
| `.tools/` | provisioned external binaries (e.g. Blender) |

Data never lives in the code repo: reference images, generated meshes,
collected donor/source assets, and canonical template assets belong to an
external, uncommitted project folder (`<project>/inputs/`,
`<project>/generated/`, `<project>/assets/`). This is the data co-workspace,
not merely a generation-output folder; when it has its own `AGENTS.md`,
`README.md`, or `INDEX.md`, read them before changing its data or layout. The
active project path comes from `CHARCTX_PROJECT` in this workspace's
git-ignored `.env` (a `--project` flag overrides it per command). Never write
data or generated files into `src/`, `plans/`, `specifications/`, or the
repository root. Never commit `.cache/` or `.tools/`.

Hosted generation costs money and is non-deterministic: every remote
generation is append-only — each run gets a fresh folder under the project's
`generated/` directory with its request metadata (backend, seed, options)
beside the downloaded artifact. No paid result is ever overwritten or
silently discarded.

## Secrets

Provider API keys come from environment variables (or a git-ignored `.env`),
never from committed files. Config files may declare endpoints and model ids
but never credentials.

## Proof Obligations

Mesh and rig proof means measurement, never appearance:

- re-load every GLB/OBJ artifact and check vertex/face counts, finite
  coordinates, bounds, watertightness, and connected components;
- canonical meshes must match template vertex/face counts and ordering
  exactly, with required regions present and no degenerate geometry;
- rigs must match the template bone hierarchy with valid approximately
  unit-sum skin weights and no unweighted vertices;
- deformation claims require deterministic test poses with recorded metrics;
- run the repository test suite and linter before declaring work done;
- record commands, expected/actual results, and gaps in the packet `test.md`.

## Git

The maintainer owns git operations. Do not run `git add`, `git commit`, `git
push`, or any other history-changing command. Leave finished work in the
working tree.

## Spec And Planning Workflow

Use `specifications/<slug>/spec.md` for durable requirements and
`plans/YYYY-MM/DD-<slug>/` for time-bounded work. Every packet has `plan.md`
and `test.md`. Create `implementation.md` only after implementation begins.
Create `survey.md` only when explicitly requested.

`plan.md` holds approved scope, milestones, dependencies, risks, exit
criteria, and stable open points (`OP-001`, etc.) with candidates, proposal,
confidence, and status. Do not silently collapse an unresolved choice.

`implementation.md` opens with a current filled/empty-block Progress line and
records changes, decisions, deviations, risks, and commands actually
performed. `test.md` records fixtures, commands, expected/actual results, and
remaining gaps. Update the packet whenever implementation changes its plan.

Fold every settled strategy, policy, or contract into the relevant durable
spec in the same pass.
