# Specifications

Use this directory for durable, spec-driven requirements.

Create one folder per specification:

```text
specifications/<slug>/spec.md
```

Specifications describe the problem, intended behavior, constraints,
interfaces, acceptance criteria, and non-goals. Keep implementation schedules
and running notes in `plans/` instead.

## Current Specifications

| Specification | Covers |
| --- | --- |
| [workspace-layout](workspace-layout/spec.md) | The data/code split, the external project folder and its selection, append-only generation slots, `.cache/` and `.tools/`, secret handling |
| [agent-interface](agent-interface/spec.md) | The single documented CLI, the side-effect-free Python API, exit codes, JSON output, failure reporting |
| [generator-backend](generator-backend/spec.md) | The backend boundary and its contracts, current TRELLIS.2 monoview cardinality, hosted-access facts and quota behavior, future multiview alternatives, staged geometry libraries |
| [mesh-report](mesh-report/spec.md) | What a measured mesh fact is, the sidecar contract, and the verification level each pipeline stage owes |
| [external-tools](external-tools/spec.md) | Declaring, pinning, checksum-verifying, and provisioning external binaries |
| [asset-packages](asset-packages/spec.md) | Collected-asset package layout, README front matter, measured inspection facts, immutable sources, previews, and incomplete provenance |
| [web-app](web-app/spec.md) | The private local Astro viewer, CLI boundary, confined derived-asset serving, and V1 catalog/detail scope |

## Not Yet Specified

Canonical asset conventions - coordinate system, scale, orientation, naming,
landmark and skeleton schemas, and region definitions - are required before
any canonicalization or non-rigid fitting work begins. The reserved
`CanonicalizationResult` and `RiggedCharacterResult` contracts carry the
conventions those stages inherit.
