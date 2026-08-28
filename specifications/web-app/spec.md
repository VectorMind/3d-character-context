# Specification: Private Dragon Asset Web App

## Role

The web app is a private local catalog and 3D preview surface for the selected
project. It owns no asset metadata interpretation, Blender inspection, render
logic, source conversion, or filesystem discovery.

The app has no deployment/publish command. It binds to `127.0.0.1` by default
and is not a mechanism for exposing the private cloud workspace.

## Architecture

The application lives under repository `webapp/` and uses Astro SSR with
React, Three.js, `@react-three/fiber`, and Drei. The only supported start
surface is:

```text
charctx web
```

The command resolves/install-checks web dependencies, snapshots one active
project for the server lifetime, starts Astro, routes server output to
`.cache/reports/`, and reports the loopback URL. Switching projects requires a
restart. There is no second long-running Python service.

Astro server handlers invoke `charctx --json` for catalog and asset facts.
They do not parse README front matter or inspection JSON, open Blender files,
or infer asset capabilities. Client code never spawns a process or reads the
filesystem.

## V1 Surface

The collection index shows:

- cover, title, asset id and collection state;
- source formats;
- measured rig and animation badges;
- incomplete provenance and build warnings.

Reference-image cards replace donor mesh/bone/action counts with their
available reference-view and linked-generation counts. Their detail page is a
unified character record: it shows reference views, then one section per
append-only generation with its input images, interactive raw GLB, measured
facts, request metadata, checksum, regenerated model views, and pipeline-stage
states.

The asset detail page shows:

- the standard preview gallery;
- an interactive GLB orbit/fit/wireframe view;
- curated identity, provenance, and license facts;
- measured geometry/material/texture facts;
- file inventory and hashes;
- armature, bone, skin-weight, action, and frame summaries;
- missing-resource and build warnings.

Future skeleton overlays, animation playback, texture-channel inspection,
canonical comparisons, and deformation evidence appear only when a CLI
capability flag and real artifact support them. The UI does not show fake
controls over absent data.

## Artifact Confinement

Web handlers serve only paths declared by normalized CLI output under a known
package's `previews/` or `web/` directory. For every request they:

- identify the asset through the CLI catalog;
- resolve both the declared root and requested file;
- enforce lexical and real-path containment;
- require a regular file and a supported preview MIME type;
- use `no-store` or a content-hash cache key when derived files change.

The server never exposes `source/`, `license/`, original vendor archives,
BLEND/FBX files, `.cache/`, or arbitrary project paths.

Generation handlers likewise resolve a character through `assets show`, then
serve only that record's declared raw model, preserved inputs, or regenerated
previews from the exact declared backend/run. Request metadata, measurement
sidecars, undeclared files, and traversal attempts are not HTTP artifacts.

## CLI Boundary

The web app obtains all normalized state through the documented `charctx
assets` commands. A CLI failure is displayed as a bounded error and does not
cause the app to scan the project directly as a fallback.

The V1 app is read-only. It does not edit front matter, reorganize files,
invoke asset builds, mutate Blender scenes, or change the selected project.

## Acceptance Criteria

- The server starts only through `charctx web` and listens on loopback by
  default.
- Catalog cards and details match `charctx assets ... --json` facts.
- Every successfully built asset loads its images and GLB interactively.
- Every linked generation appears on its reference character page without a
  duplicate catalog card.
- Incomplete provenance and missing-texture warnings are plainly visible.
- Path traversal, symlink escape, and source-file requests are rejected.
- Astro check, tests, production build, and a CLI-started local browser smoke
  test pass.

## Non-Goals

- Public deployment, publishing, sharing, authentication, or remote access.
- A browser metadata editor or asset-processing UI.
- Direct BLEND/FBX loading.
- A second Python HTTP API or duplicated TypeScript asset model.
