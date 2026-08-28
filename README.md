# 3d-character-context

A generative-first 3D character workbench. The currently implemented hosted
generator (TRELLIS.2) invents novel character geometry from **one reference
image**; a
deterministic canonicalization layer then transforms that arbitrary mesh into
a **known canonical topology**, fits a **known skeleton**, and exports
predictable production assets (GLB/FBX).

V1 targets exactly one character family:

> Western quadruped dragon: four legs, two wings, one neck/head, one tail.

The guiding rule:

> **Use generative AI for invention. Use deterministic canonicalization for
> production.**

## Status

The hosted-generation and collected-asset catalog slices are implemented:
contracts, the external project folder, TRELLIS.2, mesh measurement, Blender
asset inspection/previews, the private Astro viewer, external-tool
provisioning, and the `charctx` CLI. The canonical layer - template topology,
landmarks, skeleton fitting, appearance transfer - is not built yet.

Hosted generation is currently **monoview**. `charctx generate` and the
`trellis2` backend condition each run on exactly one image. Genuine multi-image
conditioning is a parked future capability with the provider options and open
decisions tracked in
[`plans/2026-08/28-multiview-support/plan.md`](plans/2026-08/28-multiview-support/plan.md).
The plural `GenerationRequest.images` Python field is future-facing and does
not mean that TRELLIS.2 consumes multiple views.

The active packet is
[`plans/2026-08/25-initial-bringup/plan.md`](plans/2026-08/25-initial-bringup/plan.md),
with what actually landed in
[`implementation.md`](plans/2026-08/25-initial-bringup/implementation.md) and
proof in [`test.md`](plans/2026-08/25-initial-bringup/test.md). The founding
architecture document is
[`handoff.md`](plans/2026-08/25-initial-bringup/handoff.md).

## Architecture

```text
                3D CHARACTER CONTEXT
                        │
             ┌──────────┴──────────┐
             │                     │
       Generative Layer      Canonical Layer
             │                     │
     TRELLIS.2 (implemented)  western_dragon_v1
     Hunyuan / commercial          │
       (documented)            fixed topology
             │                 fixed skeleton
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

The generator backend is replaceable infrastructure; the canonical layer is
the durable product. Heavy 3D generation is not self-hosted: backends call
hosted inference over HTTPS and download mesh artifacts.

## Setup

```powershell
uv sync
```

Then create a git-ignored `.env` at the repository root:

```ini
HF_TOKEN=hf_...
CHARCTX_PROJECT=C:\path\to\your\characters-generation
```

`HF_TOKEN` needs the `inference.serverless.write` scope. `CHARCTX_PROJECT`
points at the external data folder - all images and meshes live there, never
in this repository. Scaffold one with `charctx project init <path>`.

## Command Reference

`charctx` is the single documented interface for humans and agents. Every
command accepts `--json` for machine-readable output and `--project PATH` to
override the selected project, before or after the subcommand.

### `charctx info`

Workspace state: version, selected project, which backends are credentialed,
which tools are provisioned. Never prints a credential.

```powershell
uv run charctx info
```

```text
charctx 0.1.0 (python 3.12.13)
repository : C:\dev\VectorMind\3d-character-context
project    : C:\Users\wassi\My Drive\Projects\3d-models\characters-generation

backends:
  trellis2 (default): microsoft/TRELLIS.2 - credentialed

tools:
  blender 5.2.1: installed
```

### `charctx paths`

Every location the workspace reads from or writes to - repository, config,
`.tools/`, each `.cache/` directory, and the selected project's data roots.

```powershell
uv run charctx paths
```

### `charctx backends`

Implemented backends and documented alternatives, kept visibly distinct. An
alternative has no code behind it and cannot be selected.

```powershell
uv run charctx backends
```

### `charctx project init [path]`

Scaffold the conventional project layout (`inputs/`, `generated/`,
`assets/`). Refuses any path inside this repository.

```powershell
uv run charctx project init "C:\Users\you\My Drive\Projects\3d-models\characters-generation"
```

### `charctx project info`

Report the active project folder, whether it is scaffolded, and how many
files each data root holds.

```powershell
uv run charctx project info
```

### `charctx assets inspect`

Read-only inventory of loose candidates and existing packages, including the
exact package id and move that `organize` would perform. It never writes.

```powershell
uv run charctx assets inspect
```

### `charctx assets organize`

Explicitly move every supported loose file in `assets/collected/` into its own
package. The command preflights the entire batch, stages each package, verifies
the source SHA-256 after the move, and refuses collisions or overwrites. It
takes no arguments and is a successful no-op when nothing is loose.

```powershell
uv run charctx assets organize
```

### `charctx assets list` and `show <id>`

Read normalized catalog cards or the complete character record for one asset.
Reference records also include every append-only generation linked by their
`generation_names` front-matter field. Both commands are read-only and form
the data boundary used by the web app.

```powershell
uv run charctx assets list
uv run charctx assets show european-dragon --json
```

### `charctx assets build [id]`

Use provisioned Blender to inspect and build one 3D donor package, or all 3D
donors when the id is omitted. Reference-image packages remain cataloged but
are skipped because they have no GLB build. A donor build writes
`inspection/report.json`, a reproducibility recipe, five standard WebP
previews, a browser GLB, and the generated README body while preserving the
manual-notes block. Rigged donors additionally receive a Blender-independent
`inspection/skeleton.json` with their exact source hierarchy and rest geometry,
plus sparse `inspection/skin-weights.json` bindings. Source files are not
modified and extraction does not normalize or redesign the rig.

```powershell
uv run charctx assets build european-dragon
uv run charctx assets build
```

### `charctx assets validate [id]`

Validate front matter, confined paths, original hashes, reports, previews, and
browser GLBs without rewriting them.

```powershell
uv run charctx assets validate
```

### `charctx web`

Start the private Astro catalog at `127.0.0.1:4321`. Missing web dependencies
are installed automatically; `--no-install` makes their absence an error.
The server exposes only declared previews and derived GLBs, never vendor
source files. There is deliberately no deploy or publishing command.

```powershell
uv run charctx web --open
uv run charctx web --port 4330 --no-install
```

### `charctx fetch <tool>`

Provision an external tool declared in `config/artifacts.yaml` into
`.tools/`, verifying its checksum before extraction and running its version
command afterwards. Nothing is fetched implicitly.

```powershell
uv run charctx fetch blender
```

```text
blender 5.2.1 provisioned
  executable: C:\dev\VectorMind\3d-character-context\.tools\blender\blender.exe
  verified  : Blender 5.2.1 LTS
```

Add `--force` to re-download and re-extract.

### `charctx generate <image> --name <slug>`

Send exactly one reference image through the current hosted backend and land
the result in a fresh, append-only run slot, then measure it. This command is
monoview; repeated images, a view-set directory, or a contact sheet are not a
supported substitute for a true multiview backend.

```powershell
uv run charctx generate "$env:CHARCTX_PROJECT\inputs\references\red-dragon.png" --name red-dragon --seed 42
```

```text
  connecting to microsoft/TRELLIS.2
  preprocessing reference image
  generating 3D asset (reserves GPU quota)
  extracting GLB
generated in 63.4s via microsoft/TRELLIS.2
  run  : ...\generated\trellis2\red-dragon-001
  mesh : red-dragon.glb
  report: red-dragon.measurements.json
  192190 vertices, 293665 faces, 3320 component(s), watertight=False
```

The slot holds the untouched downloaded mesh, its measurements, copied input
images, `request.json` (backend, Space, resolved options, seed, timestamps),
five neutral model-derived previews, and `viewer.json`. The viewer manifest is
easy to parse and records the model, inputs, measurements, previews, checksum,
and current pipeline-stage states using run-relative paths. Running the same
command again creates `red-dragon-002` and overwrites nothing.

Future multiview support will use a provider endpoint that jointly conditions
one mesh on two or more images. It will receive its own documented CLI shape;
no such command is implemented today. See the
[parked multiview plan](plans/2026-08/28-multiview-support/plan.md).

| Flag | Effect |
| --- | --- |
| `--backend <key>` | Use a specific configured backend (default: `trellis2`) |
| `--seed <int>` | Generation seed |
| `--option KEY=VALUE` | Override a backend option; repeatable |
| `--no-report` | Skip measuring the downloaded mesh |
| `--no-views` | Skip viewer manifest and model-derived preview creation |

**Cost:** TRELLIS.2 runs on shared ZeroGPU hardware. Each call reserves 120 s
of a small daily budget up front - roughly four generations per day on a free
account - shared across every ZeroGPU Space the account touches. When the
budget is spent, the command reports the provider's own message including
when it resets, and no empty run slot is left behind.

### `charctx generations build <backend>/<run-folder>`

Backfill or refresh `viewer.json` and the five neutral previews for an
existing generated run. The command checks the raw model SHA-256 before and
after Blender and never modifies it. `--character` declares the reference
record that owns the generation; when omitted, the request name is used.

```powershell
uv run charctx generations build trellis2/ninjago-riyu-001 --character ninjago-riyu
```

### `charctx report <mesh>`

Measure any local mesh - GLB, glTF, OBJ, PLY, STL - and write its
`*.measurements.json` sidecar. Works without any provider call.

```powershell
uv run charctx report path\to\mesh.glb
```

```text
C:\...\generated\trellis2\red-dragon-001\red-dragon.glb
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

| Flag | Effect |
| --- | --- |
| `--output PATH` | Write the sidecar somewhere else |
| `--backend`, `--name` | Record provenance in the sidecar |
| `--no-write` | Print metrics without writing a sidecar |

## Python API

The second surface is side-effect-free: it returns data and writes nothing.
Producing artifacts stays an explicit act through the CLI or through
functions named for the write they perform.

```python
from character_context import measure

m = measure("path/to/mesh.glb")
print(m.vertices, m.faces, m.connected_components, m.is_plausible)
```

## Experiments

[`experiments/`](experiments/README.md) holds standing provider-access probes
run with `uv run --script` - no environment needed. They answer "is this
provider reachable, and what does it actually offer today?" and write
timestamped reports into `.cache/results/`.

## Testing

```powershell
uv run pytest          # offline, free: no provider call
uv run ruff check .
```

The default suite never touches a provider. One live smoke test is marked
`live` and runs only with `CHARCTX_LIVE=1 uv run pytest -m live`; it costs GPU
quota and writes a real run into the project folder.

## Workflow

Development is spec-driven; see [`WORKFLOW.md`](WORKFLOW.md) for the full
rules and [`AGENTS.md`](AGENTS.md) for the operational summary agents read
first.

- [`specifications/`](specifications/README.md) — durable binding contracts.
- [`plans/`](plans/README.md) — dated planning packets;
  [`open.md`](plans/open.md) and [`closed.md`](plans/closed.md) index their
  status.
- [`config/`](config/) — endpoints, Space ids, and tool pins. Never secrets.
- External project folder (uncommitted) — all input images, generated meshes,
  and canonical assets.
- `.cache/`, `.tools/` — operational output and provisioned binaries;
  git-ignored.

The maintainer owns all git operations.
