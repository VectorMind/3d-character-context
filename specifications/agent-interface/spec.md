# Specification: Agent And Human Interface

## Purpose

Give humans and agents exactly one way to operate the system, and keep the
programmatic surface free of hidden side effects.

## Two Surfaces

### 1. The `charctx` CLI

The documented CLI is the single interface. A capability that is not
reachable through a documented command is not delivered: a command and its
`README.md` entry ship together.

There are no agent-specific skills, wrappers, or alternative entry points.
Agents are routed to the CLI by `AGENTS.md` and `README.md`.

Every command:

- prints human-readable text by default and a JSON object with `--json`;
- accepts `--project` and `--json` either before or after the subcommand;
- returns `0` on success, `2` for a configuration or usage error, `1` for any
  other failure;
- prints one clear error line to stderr, not a traceback, naming the fix
  where a fix exists (the missing variable, the command to run).

### 2. The Python API

`import character_context` exposes the contracts and read-only operations.
This surface is **side-effect-free**: it returns data and in-memory objects
and writes no files.

Producing an artifact is always an explicit act - a CLI command, or a
function named for the write it performs (`write_measurements`, `fetch`,
`init`). Measuring, describing, selecting, and resolving never write.

## Command Surface

| Command | Contract |
| --- | --- |
| `charctx info` | Workspace state: version, selected project, backends and whether each is credentialed, provisioned tools. Reveals no credential value. |
| `charctx paths` | Every location read from or written to. |
| `charctx backends` | Implemented backends and documented alternatives, kept visibly distinct. |
| `charctx project init [path]` | Scaffold the conventional project layout. |
| `charctx project info` | Report the active project and what it holds. |
| `charctx fetch <tool>` | Provision a declared external tool and verify it runs. |
| `charctx generate <image> --name <slug>` | Reference image through a hosted backend into a fresh append-only run slot; measures the result unless `--no-report`. |
| `charctx report <mesh>` | Measure any local mesh artifact and write its sidecar unless `--no-write`. |
| `charctx assets inspect` | Read-only inspection of loose collected candidates and existing asset packages, including proposed organization paths. |
| `charctx assets list` | Normalized asset cards from validated README front matter plus measured inspection facts. |
| `charctx assets show <id>` | Full normalized curated and measured facts for one collected asset. |
| `charctx assets build <id>` | Explicitly write measured inspection output, standard preview renders, browser GLB, and the generated README body for one package. |
| `charctx assets validate [<id>]` | Validate package schemas, confined paths, hashes, and required derived outputs without rewriting them. |
| `charctx web` | Start the private loopback-only Astro catalog/viewer; it calls this CLI for all asset facts. |

Commands that cost money or quota make that visible before spending it, and
report what was spent afterwards.

## Failure Reporting

An error message states what failed and what to do about it. Provider
refusals are surfaced with the provider's own wording preserved, so a quota
message, its numbers, and its reset time reach the operator unedited.

## Acceptance Criteria

- Every shipped command appears in `README.md` with a usage line and example.
- `--json` output parses and carries the same facts as the text output.
- No function reachable from `import character_context` writes a file unless
  its name says it does.
- No credential value appears in any command's output.

## Non-Goals

- Agent skills or MCP servers.
- Interactive prompts: every command is non-interactive and scriptable.
- A second CLI, an independently started API/application server, or a public
  deployment/publishing surface.
