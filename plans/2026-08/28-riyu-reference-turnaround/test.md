# Test — Riyu Reference Turnaround

## Source Preservation

The five supplied images were moved into the package's immutable `source/`
directory. SHA-256 values after the move matched their pre-move values:

| Source | SHA-256 |
| --- | --- |
| `And_I_know_just_the_thing%21.webp` | `c13c1484efe6ab7587c0b2b079973af7278ac4ff247e42e91dbafbe80c8c1a34` |
| `front.jpg` | `58f3cdfd9ef989c3cdd7e0b82f958110c9c24deffb790ef7abcc2a8121af62a2` |
| `side.jpg` | `1f28aa6d239456c46bb48a910c192a278d873cfbe6bfcd1d65a276f3aed9dc53` |
| `ThePowerWithin_29.JPG.webp` | `1ab7a5f71c851d53a965c8c7ace093b85171ca81de80d3d8cbabd2b7e8cd93ae` |
| `We_Are_All_Dragons_29.JPG.webp` | `744eb2b345784162c7000969309ffd9abe9ea1acbdfd57a79497ad3fbc706183` |

## Image Proof

- Direct visual inspection covered all five inputs and every generated view.
- The final set contains front three-quarter, front, left, rear, and top views
  in one neutral standing pose with a white background and separated wing
  silhouettes.
- The top view was regenerated with the maintainer's crop as the authoritative
  head-detail reference. The final output shows stacked transverse head plates
  rather than the initial leaf-shaped crown.
- High-resolution outputs are 1402 × 1122 except the 1254 × 1254 top view.
- Catalog WebPs are 1024 pixels on the longest edge and use the standard
  `hero`, `front`, `left`, `rear`, and `top` names.
- No hosted 3D-generation command was run.

## CLI And Package Validation

| Check | Actual |
| --- | --- |
| `uv run charctx assets show ninjago-riyu --json` | Card parses as `kind: reference`; five previews, cover, JPG/WebP source formats, no mesh/rig facts, and no web model |
| `uv run charctx assets validate ninjago-riyu --json` | **Pass:** `valid: true`, no errors |

## Repository And Web Proof

| Command/check | Actual |
| --- | --- |
| `uv run pytest` | **Pass:** 79 passed, 1 live test skipped in 1.35 s |
| `uv run ruff check .` | **Pass:** `All checks passed!` |
| `pnpm check` | **Pass:** 0 errors, warnings, or hints |
| `pnpm build` | **Pass:** Astro server and client built; existing large-chunk advisory only |
| `GET /assets/ninjago-riyu` | 200; title and image-reference message present |
| five declared preview routes | 200 `image/webp`; byte sizes match the saved previews |
| `GET /api/artifact/ninjago-riyu/source/side.jpg` | 404; source confinement preserved |

## Known Gaps

- Reference-source provenance and licensing facts are unknown.
- The image set is AI-synthesized and not geometrically registered.
- No 3D generator result, mesh inspection, rig, or deformation proof exists in
  this packet.
