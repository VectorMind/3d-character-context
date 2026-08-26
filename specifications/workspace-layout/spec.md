# Specification: Workspace Layout And Data/Code Split

## Purpose

Fix where every byte the system reads or writes belongs, so that data,
operational output, and code never mix.

## The Split

The code repository holds code, contracts, configuration, and documentation.
It holds no character data.

All input data (reference images), all generated meshes, all collected donor
assets, and all canonical template assets live in an external **project
folder** that is never committed.

## Project Folder

A project folder carries three data roots:

```text
<project>/
  inputs/      # reference images and other run inputs
  generated/   # append-only generation runs
  assets/      # collected reusable assets and verified canonical assets
```

`charctx project init <path>` creates this layout. Scaffolding a project
inside the code repository is refused.

A project folder may be a cloud-synced collaboration workspace and may carry
its own `AGENTS.md`, `README.md`, or `INDEX.md`. Where present, those files
are authoritative for the data in that workspace, its provenance, and its
navigation; this repository remains authoritative for software behavior and
contracts.

### Selection

The active project comes from `CHARCTX_PROJECT`, read from the environment or
from the git-ignored `.env` at the repository root. A `--project PATH` flag
overrides it for one command. Precedence is `--project`, then
`CHARCTX_PROJECT`.

When no project is selected, a command fails with a message naming both the
variable and the flag. Commands never guess a location and never fall back to
a path inside the repository.

### Append-Only Generation

Hosted generation costs money or quota and is non-deterministic. Every run
gets a fresh slot:

```text
<project>/generated/<backend>/<name>-<NNN>/
    <name>.glb                     # the artifact
    <name>.measurements.json       # its measured facts
    reference.<ext>                # the input, copied so the run is self-contained
    request.json                   # backend, space, options, seed, timestamps
```

`<NNN>` increments; an existing slot is never reused, overwritten, or
cleared. Repeating an identical request produces a new slot. A run that
brings back no artifact leaves no slot behind.

Artifacts are written to a temporary name and renamed into place, so a
cloud-sync client never observes or uploads a partially written file.

## Repository Output

Operational output stays under the git-ignored `.cache/`:

| Path | Contents |
| --- | --- |
| `.cache/results/` | bounded command and experiment output, in `<YYYY-MM-DD>/<HHMMSS>-<slug>/` folders |
| `.cache/reports/` | tracebacks and long subprocess or provider logs |
| `.cache/scratch/` | throwaway experiments |
| `.cache/downloads/` | transient downloads, including tool archives |
| `.tools/` | provisioned external binaries |

`.cache/` is not a destination for anything valuable: material worth keeping
moves into the project folder through its intake flow, with its original
bytes unaltered and its provenance recorded beside it.

Nothing writes data or generated files into `src/`, `plans/`,
`specifications/`, `config/`, or the repository root.

## Secrets

Provider credentials come from environment variables or the git-ignored
`.env`. Committed configuration under `config/` declares endpoints, Space
ids, model ids, and version pins, and never a credential value. Configuration
may name the environment variable that carries a credential.

Any command that reports credential state reports whether a credential is
present, never its value.

## Acceptance Criteria

- `charctx paths` prints every location the workspace reads from or writes to.
- `charctx project init` refuses a path inside the repository.
- Two identical `charctx generate` runs produce two slots and overwrite
  nothing.
- No command writes outside `.cache/`, `.tools/`, and the selected project.
- Committed configuration contains no credential value.

## Non-Goals

- A project manifest or project-local Python code.
- Any committed asset directory in the code repository.
- Automatic cleanup, deduplication, or rotation of generated runs.
