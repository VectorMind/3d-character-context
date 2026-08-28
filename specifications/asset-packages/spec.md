# Specification: Collected Asset Packages

## Purpose

Make every reusable third-party or source asset self-contained, inspectable,
and locally browsable without modifying its original bytes or inventing
missing provenance.

## Location And Package Identity

Collected assets live only under the selected external project:

```text
<project>/assets/collected/<asset-id>/
```

`<asset-id>` is a lowercase filesystem-safe slug unique within the collection.
The package directory is the unit of catalog identity. Code, tests, and asset
bytes never cross between the repository and the project folder.

## Package Layout

```text
<asset-id>/
  README.md
  source/
  license/
  inspection/
    report.json
    recipe.json
  previews/
    hero.webp
    front.webp
    left.webp
    rear.webp
    top.webp
  web/
    model.glb
```

`license/` may be empty when no supplied evidence exists. Missing derived
output is represented as a build warning or incomplete build, never by a
fabricated placeholder that looks verified.

## Split Authority

`README.md` YAML front matter is authoritative for curated facts:

- schema version, asset id, display title, kind, family, and tags;
- collection state and provenance completeness;
- source provider/id/URL/creator when known;
- license name/URL and stated restrictions when known;
- acquisition method/date when known;
- declared primary source, cover image, and browser-model paths.
- generation request names owned by the character record.

`inspection/report.json` is authoritative for measured facts:

- original and derived file sizes and SHA-256 hashes;
- scene, object, mesh, vertex, polygon, material, and texture facts;
- armature, deform-bone, weight, action, and frame facts;
- missing external resources and other build warnings.

`inspection/recipe.json` records the exact source hash, tool/version, command
options, coordinate/pose decisions, output hashes, and timing that produced the
inspection and previews.

The generated README body combines the two authorities into an image gallery,
identity/provenance table, measured-characteristics table, file inventory, and
warnings. A delimited manual-notes region is preserved byte-for-byte across
regeneration.

TypeScript and browser code do not parse these files independently. The Python
domain layer validates and normalizes them, and the CLI publishes the resulting
JSON contract.

## Original And Derived Bytes

Everything under `source/` is immutable after package creation. Processing:

- disables embedded BLEND auto-execution;
- clears Blender's factory-startup objects before importing GLB, glTF, OBJ,
  or FBX sources, so default scene geometry cannot enter measured or derived
  output;
- never saves the source scene;
- extracts archive members only into transient `.cache/` staging after member
  path/count/expanded-size validation;
- never guesses or silently substitutes a missing texture;
- writes derived output through temporary names and atomically promotes it;
- may replace only deterministic files under `inspection/`, `previews/`, and
  `web/`, after confirming the recorded source hash still matches.

The browser GLB and images are preview derivatives, not canonical production
assets and not replacements for the vendor originals.

## Reference-Image Packages

A collected package may use `kind: reference` when its durable value is a
curated multi-view image set rather than a 3D source model. It keeps supplied
bytes under `source/`, declares one source image as `primary_file`, and
provides the same five named WebP previews used by the private catalog.
High-resolution run inputs remain under the project's `inputs/` root and are
linked from the package report rather than duplicated as authoritative
sources.

Reference packages are the durable character records. Their `generation_names`
front-matter list links request names without copying generated meshes into a
second collected package. `charctx assets show` discovers every matching run
under `generated/` and embeds its normalized manifest and measurements. The
package remains listed, shown, and validated through `charctx assets`, but is
not Blender-buildable and does not require its own inspection report or web
GLB. A no-id `assets build` skips it; an explicit build request fails with a
clear reference-package message.

One character therefore has one catalog identity and one detail page: source
references first, followed by a section for each append-only generation and
explicit future-stage states. Generated runs remain authoritative in
`generated/`; they are never promoted by duplicating their model bytes into a
second donor package.

## Organization Contract

`charctx assets inspect` is the read-only preview. `charctx assets organize`
is the explicit mutation and takes no required arguments: it handles every
supported loose candidate directly under `assets/collected/`.

Before any move, organization validates the full batch, derived ids, resolved
paths, and collisions. Each package is created through staging; the original
is moved under `source/` with the same filename, then its SHA-256 is verified.
There is no overwrite or force mode. A collection with no loose candidates is
a successful no-op.

## Provenance And Private Local Use

This workspace has no publishing or public-sharing path. Assets with missing
source or license facts remain available for local inspection, comparison,
rendering, and viewing.

Missing provenance is never silent:

- front matter sets `provenance_status: incomplete`;
- unknown fields contain the explicit value `unknown` rather than being
  omitted or guessed;
- normalized cards and detail pages show a prominent incomplete-provenance
  warning;
- no output claims that an unknown license permits redistribution, publishing,
  or AI training.

The local viewer's availability is not a license-cleared or publishable status.

## Standard Preview Set

Headless Blender produces one 1024-pixel WebP for each standard view:

```text
hero, front, left, rear, top
```

Camera fitting, neutral studio world, lighting, background, render engine,
rest/current-pose choice, export options, and Blender version are deterministic
and recorded in the recipe. Source material/texture data is preserved in the
browser GLB when actually available. Missing material data remains visible as
a warning.

## Acceptance Criteria

- Every package has valid front matter and a unique confined id.
- Curated claims and measured facts have exactly one authority each.
- Source hashes remain unchanged across inspection/render/build.
- A successful build writes report/recipe JSON, five standard images, a
  loadable GLB, and a regenerated README body.
- Incomplete provenance is visible but does not block private local viewing.
- No source archive, BLEND, or FBX is exposed by the web asset endpoint.

## Non-Goals

- Public catalog hosting, publishing, redistribution, or license clearance.
- Source-file repair, repacking, material invention, or rig editing.
- Canonical topology/skeleton selection or semantic bone normalization.
- Treating preview derivatives as production or canonical assets.
