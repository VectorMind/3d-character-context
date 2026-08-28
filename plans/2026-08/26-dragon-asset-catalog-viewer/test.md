# Test — Dragon Asset Catalog And Web Viewer

Runtime proof for the accepted OP-001…OP-006 implementation.

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
- At planning time the packet was indexed in `plans/open.md`; after delivery it
  moved to `plans/closed.md` and gained `implementation.md`.

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

| Command/check | Actual |
| --- | --- |
| `charctx assets inspect --json` before organization | Three ready candidates, zero collisions; exact ids and target packages reported without writes |
| `charctx assets organize --json` | Three packages created; original files moved under `source/`; post-move hashes equal discovery hashes |
| `charctx assets build blender-dragon` | Report, recipe, GLB, README, and five WebPs produced; missing external texture reported |
| `charctx assets build dragon` | 25,025 vertices, 26,244 polygons, 196 bones, one real action; five visible views and GLB produced |
| `charctx assets build european-dragon` | Guarded nested archive extraction and FBX import; 21,236 vertices, 21,268 polygons, 168 bones, five actions; five views and GLB produced |
| Direct image inspection | Hero WebPs for all three visually checked; neutral material and scale-adjusted studio lights produce readable geometry |
| `charctx assets validate --json` | All three package schemas, source hashes, declared paths, reports, preview sets, and GLBs valid |
| `charctx report <web/model.glb> --no-write` for all three | Every exported GLB reloads with finite geometry: 43,643/21,998, 29,729/48,112, and 24,164/42,350 vertices/faces respectively |

Original source hashes retained:

- `blender_dragon.blend`: `13a4a92ed36c3922fa6cca8c2ed467209d53681d9d8b31752e5a17428cfe7ed3`
- `dragon.blend`: `6cb566aa82d9d7eb833aa7841019a49006aeae9a84ae385643268e959c7c92b3`
- `european-dragon.zip`: `8f464c74ea5a100ec8fdbd9d2456842f9880f80780af5182778be53bdab5d0d4`

## Web Proof

| Check | Actual |
| --- | --- |
| `pnpm check` | Pass: zero errors, warnings, or hints |
| `pnpm build` | Pass: Astro SSR server and React/Three client built |
| `charctx web --no-install --port 4321` | Server ready on loopback and sourced the selected cloud project |
| `GET /` | 200, collection HTML with three cards |
| `GET /assets/dragon` | 200, measured detail HTML and hydrated viewer |
| declared preview request | 200 `image/webp` |
| declared GLB request | 200 `model/gltf-binary` |
| `GET /api/artifact/dragon/source/dragon.blend` | 404; source boundary enforced |
| Chrome collection smoke | Three visual cards, exact measured counts, and explicit incomplete-provenance labels rendered with no final console errors |
| Chrome detail smoke | GLB decoded to `1 mesh loaded`; the neutral rest geometry was visible and fitted; wireframe click changed the control to `Solid` and visibly drew topology |

The mandated in-app browser control runtime returned `Browser is not
available: iab`. The documented Chrome-control fallback was used instead and
completed the interactive screenshot/click smoke test.

## Repository Baseline Checks (2026-08-26)

| Command | Expected | Actual |
| --- | --- | --- |
| `uv run pytest` | Existing offline suite passes without spending hosted-generation quota | **Pass:** 65 passed, 1 live test skipped in 2.94 s |
| `uv run ruff check .` | Repository lint is clean | **Pass:** `All checks passed!` |

Final post-implementation rerun: **76 passed, 1 live test skipped** in 0.81 s;
ruff reported `All checks passed!`.

The first sandboxed attempts could not open uv's existing user-level cache at
`C:\Users\wassi\AppData\Local\uv\cache`; the commands passed when rerun with
permission to access that cache. No dependency was added or changed.

## Known Gaps

- Source/provider/creator/license facts are missing for all three candidates.
- Existing source texture links are missing or absolute and were not guessed;
  previews therefore use a neutral inspection material.

## Generated Riyu Promotion Proof (2026-08-28)

| Check | Actual |
| --- | --- |
| Copy + `charctx assets inspect` | Proposed `ninjago-riyu-generated-001` with no collision; source copy matched the append-only run hash |
| `charctx assets organize --json` | Created a separate donor package and retained SHA-256 `ffeedea52006706e3e1eda4d9034386c90581896441b14220f9cfec3b9fac12c` |
| `charctx assets build ninjago-riyu-generated-001 --json` | Produced inspection/recipe JSON, five previews, and `web/model.glb` from one imported mesh; no factory-startup cube remained |
| `charctx assets validate ninjago-riyu-generated-001 --json` | Pass with no errors |
| CLI catalog inspection | 203,745 source vertices, 289,479 polygons, one mesh object, no rig or animation |
| Live local viewer | `/assets/ninjago-riyu-generated-001` returned 200 and reached `1 mesh loaded` with visible inspection geometry and no console errors |

The optional source-material viewer mode renders this TRELLIS derivative
transparent/invisible; the default neutral inspection material remains visible.
This is recorded as a separate material-compatibility gap and did not alter the
copied source or block geometry inspection.
