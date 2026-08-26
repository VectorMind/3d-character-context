# Specification: External Tools And Artifact Provisioning

## Purpose

Some pipeline stages need tools this repository does not build - Blender for
geometry and rigging work. This specification fixes how such a tool enters the
workspace.

## Doctrine

A tool a pipeline stage needs is a **mandatory** part of the main flow, not an
optional extra. This repository does not carry redundant alternative
libraries behind feature flags, and does not degrade gracefully when a core
tool is absent: it says the tool is missing and names the command that
provisions it. Graceful degradation is reserved for genuinely external,
unavoidable absences.

## Declaration

Every external tool is declared in `config/artifacts.yaml` with:

| Field | Meaning |
| --- | --- |
| `version` | Exact version. Never a range, never "latest" |
| `url` | Direct download URL from the vendor's official binary channel |
| `sha256` | Checksum published by the vendor for exactly that file |
| `size_bytes` | Expected size |
| `archive`, `archive_root` | Archive type and the single directory it unpacks to |
| `install_dir`, `executable` | Location under `.tools/` and the executable inside it |
| `version_args` | Command proving the provisioned tool runs |
| `platform` | Platform the entry is pinned for |

Bumping a version is a deliberate change to this file. No mechanism resolves
"the latest release" at runtime.

## Provisioning

`charctx fetch <name>` provisions a declared tool into the git-ignored
`.tools/`. Nothing is fetched implicitly; provisioning is always an explicit
act.

The mechanism:

1. downloads to `.cache/downloads/` through a temporary name, renamed on
   completion, and reuses an already-correct archive instead of re-downloading;
2. verifies the checksum **before** extraction, and discards the file on
   mismatch with a message showing both digests;
3. extracts to a staging directory and flattens the archive's versioned root,
   so the executable path stays stable across version bumps;
4. refuses a platform mismatch rather than installing a foreign binary;
5. runs the tool's declared version command, so "provisioned" means "runs".

A tool already present is left untouched unless re-provisioning is requested,
in which case the install directory is replaced rather than merged.

## Invocation

Provisioned tools are invoked as subprocesses from their resolved path, with
arguments built from committed configuration. Tool scripts run inside the
tool's own bundled runtime, so tool versions and the workspace Python version
stay independent.

## Acceptance Criteria

- A declared tool provisions from `config/artifacts.yaml` alone and reports
  its version.
- A checksum mismatch leaves no downloaded file behind.
- Re-fetching an already-provisioned tool changes nothing.
- The executable path does not contain a version number.
- `charctx info` reports which declared tools are provisioned.

## Non-Goals

- Building tools from source.
- A general package manager or dependency resolver.
- In-process library variants of a tool that is provisioned as a binary.
