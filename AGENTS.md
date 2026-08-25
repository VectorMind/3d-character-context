# Agent Guidance

Read this before doing anything in the repository. Binding contracts live in
`specifications/`; this is the operational summary. The workflow itself is
defined in `WORKFLOW.md`.

## Current State

The repository is in initial bringup. There is no Python package, CLI, or
canonical asset yet. The active planning packet is
`plans/2026-08/25-initial-bringup/`; its `plan.md` carries the open design
decisions (OP-001…), and its `handoff.md` is the founding architecture
document. Check `plans/open.md` for what is outstanding before starting work.

## Architecture In One Glance

```text
reference image(s)
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

## Two Surfaces (once the bringup lands)

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
| `.tools/` | provisioned external binaries (e.g. Blender) |

Data never lives in the code repo: reference images, generated meshes, and
canonical template assets belong to an external, uncommitted project folder
(`<project>/inputs/`, `<project>/generated/`, `<project>/assets/` — contract
under decision in OP-012). Never write data or generated files into `src/`,
`plans/`, `specifications/`, or the repository root. Never commit `.cache/`
or `.tools/`.

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
