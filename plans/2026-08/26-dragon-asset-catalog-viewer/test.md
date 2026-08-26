# Test — Dragon Asset Catalog And Web Viewer

Planning-only packet. This file records discovery and consistency evidence;
runtime proof will replace the gaps after OP-001…OP-006 are accepted and
implementation begins.

## Read-Only Discovery (2026-08-26)

- Read repository `AGENTS.md`, `WORKFLOW.md`, `README.md`, specifications
  index, open-plan index, and the donor-corpus plan.
- Read the selected cloud workspace's `AGENTS.md`, asset README, and collected
  asset README.
- Inventoried `assets/collected/`: three loose candidates totaling 101,744,228
  bytes plus the collection README; no per-asset directories exist.
- Listed both ZIP levels of `european-dragon.zip` without extraction.
- Computed candidate SHA-256 values and inspected both BLEND files with
  provisioned Blender 5.2.1 in background mode with auto-execution disabled.
- Read the local `cad-context` agent guidance, `cadctx web` launcher/CLI,
  web-app specification, Astro package/config, CLI bridge, artifact-confinement
  route, index, and Three.js GLB viewer.

## Planning Consistency Checks

- `plan.md` contains problem/resolution summaries, six detailed meaningful
  open points with candidates/proposal/confidence/status, goals, scope,
  package/front-matter proposals, phases, dependencies, risks, exit criteria,
  and an implementation gate.
- OP-001…OP-006 match between the one-glance table and detailed sections.
- The plan preserves the accepted external-project data boundary and does not
  place assets or previews in the repository.
- The plan preserves source bytes, uses Blender only through a documented CLI
  build, and keeps the web app dependent on `charctx --json` rather than a
  second metadata/geometry implementation.
- The packet is indexed in `plans/open.md` and has no `implementation.md`.

## Decision Pass 1 (2026-08-26)

- OP-001 accepted: curated README front matter and measured inspection JSON
  have split authority.
- OP-003 accepted with amendment: missing provenance is prominently labelled
  but does not block use in the private local viewer; the workspace has no
  publishing surface.
- OP-004…OP-006 accepted: durable Blender previews, cohesive CLI surface, and
  CLI-driven local Astro SSR viewer.
- OP-002 narrowed to one final proposal: read-only no-argument `assets
  inspect`, followed by explicit mutating no-argument `assets organize`; no
  `--move` flag.
- Settled rules were folded into `specifications/asset-packages/spec.md` and
  `specifications/web-app/spec.md`; the agent-interface spec and specification
  index were updated in the same pass.

## Execution Evidence

None for this packet. No collected asset was moved, renamed, extracted,
rendered, exported, or rewritten. Durable specifications were added for the
accepted design decisions, but no CLI implementation, dependency, or web
application code was added. The only Blender work was read-only discovery
recorded in the donor-corpus packet.

## Repository Baseline Checks (2026-08-26)

| Command | Expected | Actual |
| --- | --- | --- |
| `uv run pytest` | Existing offline suite passes without spending hosted-generation quota | **Pass:** 65 passed, 1 live test skipped in 2.94 s |
| `uv run ruff check .` | Repository lint is clean | **Pass:** `All checks passed!` |

The first sandboxed attempts could not open uv's existing user-level cache at
`C:\Users\wassi\AppData\Local\uv\cache`; the commands passed when rerun with
permission to access that cache. No dependency was added or changed.

## Known Gaps

- Only OP-002's exact no-argument `assets organize` behavior awaits final
  maintainer confirmation.
- Source/provider/creator/license facts are missing for all three candidates.
- The European-dragon FBX has not been imported into Blender.
- Node/pnpm availability in this repository has not been checked because web
  implementation is gated.
