# Closed Plans

Completed plan packets. Work is implemented and proven (or, for
planning-only packets, the decisions are settled). See each folder for
details.

| Plan | Date | Summary | Proof / Notes |
| --- | --- | --- | --- |
| [Dragon Asset Catalog And Web Viewer](./2026-08/26-dragon-asset-catalog-viewer/plan.md) | 2026-08-26 | OP-001…OP-006 settled and implemented: staged asset organization, YAML/JSON split authority, Blender inspection/previews/GLBs, generated package READMEs, normalized CLI, and private Astro/Three.js catalog. | Three packages validate; 76 offline tests and ruff pass; Astro check/build pass; loopback HTML/preview/GLB routes return 200 and source requests return 404; Chrome verifies the visible fitted model and wireframe interaction. See [test.md](./2026-08/26-dragon-asset-catalog-viewer/test.md). |
| [3D Character Context Initial Bringup](./2026-08/25-initial-bringup/plan.md) | 2026-08-25 | OP-001…OP-013 settled and all six phases implemented: `charctx` CLI, pydantic contracts, `.env`-selected external project folder with append-only run slots, the `microsoft/TRELLIS.2` backend, trimesh mesh reports, checksum-verified external-tool provisioning, and five folded specs. | Two live `charctx generate` runs landed measured meshes in `red-dragon-001`/`-002` (58.98 s / 63.16 s; 192,711 / 181,018 vertices), proving append-only and backend non-determinism; `charctx fetch blender` verified as Blender 5.2.1 LTS and driven headless; this packet's 67 offline tests pass inside a green 78-test suite with ruff clean. Follow-ups: the gated `live` pytest test awaits spare quota, and one empty pre-fix run slot awaits manual deletion. See [test.md](./2026-08/25-initial-bringup/test.md) and [implementation.md](./2026-08/25-initial-bringup/implementation.md). |
