# Open Plans

Plan packets with work still outstanding. See each folder for details.

| Plan | Date | State | Outstanding |
| --- | --- | --- | --- |
| [3D Character Context Initial Bringup](./2026-08/25-initial-bringup/plan.md) | 2026-08-25 | Implemented, one proof outstanding | Phases 1-6 built: `charctx` CLI, pydantic contracts, `.env`-selected project folder with append-only run slots, the `microsoft/TRELLIS.2` backend, trimesh mesh reports, `charctx fetch blender` (provisioned and verified as Blender 5.2.1 LTS), five folded specs, 65 offline tests and ruff clean. **Outstanding:** a live `charctx generate` has not yet produced a mesh - the path is proven up to the GPU reservation and blocked by the free ZeroGPU daily quota; repeat the documented command after it resets. Commercial providers (Meshy, Tripo, Rodin) are out of scope by maintainer direction. Log: [implementation.md](./2026-08/25-initial-bringup/implementation.md); proof: [test.md](./2026-08/25-initial-bringup/test.md). |
| [Western-Dragon Donor Corpus Acquisition](./2026-08/25-dragon-donor-corpus/plan.md) | 2026-08-25 | Planning + manual candidates | OP-001…OP-010 await maintainer review. Three manually collected candidates (two BLEND, one nested-ZIP/FBX package) were read-only inventoried on 2026-08-26; none has adjacent provenance/license metadata or accepted package status. Source-system research remains outstanding. Their organization and presentation move through the [asset catalog/viewer packet](./2026-08/26-dragon-asset-catalog-viewer/plan.md). Rigging basis: [dragon Blender rigging handoff](./2026-08/25-rigging/dragon_blender_rigging_handoff.md). |
| [Dragon Asset Catalog And Web Viewer](./2026-08/26-dragon-asset-catalog-viewer/plan.md) | 2026-08-26 | Decision pass — one OP open | OP-001 and OP-003…OP-006 accepted 2026-08-26: split README/inspection authority, incomplete-provenance warnings without blocking private local viewing, durable Blender GLB/standard views, cohesive CLI, and local-only CLI-driven Astro SSR. **OP-002 remains:** confirm `charctx assets inspect` as the no-write preview and no-argument `charctx assets organize` as the explicit batch mutation, replacing `--move`. No asset has been moved or rendered and no web code exists yet. |

Future packets already foreseen by the handoff (not yet opened): donor
extraction + canonical skeleton study (milestone 2A after the acquisition
packet), canonical western-dragon template + weights (milestone 2B), coarse
alignment and non-rigid fitting (milestones 3–4), skeleton fit + skinning +
deformation tests (milestone 5), and appearance transfer (milestone 6).
