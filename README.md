# 3d-character-context

A generative-first 3D character workbench. A hosted generative 3D model
(TRELLIS, Hunyuan3D, or a commercial baseline) invents novel character
geometry from reference images; a deterministic canonicalization layer then
transforms that arbitrary mesh into a **known canonical topology**, fits a
**known skeleton**, and exports predictable production assets (GLB/FBX).

V1 targets exactly one character family:

> Western quadruped dragon: four legs, two wings, one neck/head, one tail.

The guiding rule:

> **Use generative AI for invention. Use deterministic canonicalization for
> production.**

## Status

The repository is in initial bringup — planning stage, no code yet. The
active packet is
[`plans/2026-08/25-initial-bringup/plan.md`](plans/2026-08/25-initial-bringup/plan.md),
which carries the open design decisions (naming, first hosted backend,
geometry stack staging, canonical asset sourcing, …). The founding
architecture document is
[`handoff.md`](plans/2026-08/25-initial-bringup/handoff.md) in the same
packet.

## Architecture

```text
                3D CHARACTER CONTEXT
                        │
             ┌──────────┴──────────┐
             │                     │
       Generative Layer      Canonical Layer
             │                     │
     TRELLIS / Hunyuan       western_dragon_v1
     Tripo / Meshy / Rodin        │
             │                fixed topology
             │                fixed skeleton
             │                     │
             └──────────┬──────────┘
                        ↓
                canonical fitting
                        ↓
                   rig fitting
                        ↓
                  verification
                        ↓
                    GLB / FBX
```

The generator backend is replaceable infrastructure behind a protocol and
registry; the canonical layer (topology, landmarks, skeleton, verification)
is the durable product. Heavy 3D generation is not self-hosted: backends call
hosted inference providers over HTTPS and download mesh artifacts.

## Planned Interface

Once the bringup packet lands, the repository follows the same interface rule
as its sibling `cad-context`: one documented CLI as the single interface for
humans and agents (name settled by OP-001 of the bringup plan), plus a
side-effect-free Python API. Every capability ships with its command and its
README entry together; this section becomes the command reference.

First milestone target:

```text
reference image
      ↓ hosted generation
raw_dragon.glb
      ↓ trimesh inspection
raw_dragon.measurements.json
```

## Workflow

Development is spec-driven; see [`WORKFLOW.md`](WORKFLOW.md) for the full
rules and [`AGENTS.md`](AGENTS.md) for the operational summary that agents
read first.

- [`specifications/`](specifications/README.md) — durable binding contracts.
- [`plans/`](plans/README.md) — dated planning packets;
  [`open.md`](plans/open.md) and [`closed.md`](plans/closed.md) index their
  status.
- `assets/` — hand-authored canonical template assets (source, committed).
- `.cache/` — all generated/downloaded artifacts (derived, git-ignored).

The maintainer owns all git operations.
