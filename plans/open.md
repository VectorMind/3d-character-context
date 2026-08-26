# Open Plans

Plan packets with work still outstanding. See each folder for details.

| Plan | Date | State | Outstanding |
| --- | --- | --- | --- |
| [3D Character Context Initial Bringup](./2026-08/25-initial-bringup/plan.md) | 2026-08-25 | Implemented, one proof outstanding | Phases 1-6 built: `charctx` CLI, pydantic contracts, `.env`-selected project folder with append-only run slots, the `microsoft/TRELLIS.2` backend, trimesh mesh reports, `charctx fetch blender` (provisioned and verified as Blender 5.2.1 LTS), five folded specs, 65 offline tests and ruff clean. **Outstanding:** a live `charctx generate` has not yet produced a mesh - the path is proven up to the GPU reservation and blocked by the free ZeroGPU daily quota; repeat the documented command after it resets. Commercial providers (Meshy, Tripo, Rodin) are out of scope by maintainer direction. Log: [implementation.md](./2026-08/25-initial-bringup/implementation.md); proof: [test.md](./2026-08/25-initial-bringup/test.md). |
| [Western-Dragon Donor Corpus Acquisition](./2026-08/25-dragon-donor-corpus/plan.md) | 2026-08-25 | Planning | OP-001…OP-010 await maintainer review. No marketplace research, downloads, purchases, or corpus changes have started. First executable phase is a read-only, evidence-recorded source-system review using maintainer-provided Chrome access; pilot acquisition remains gated on the decision pass. Rigging basis: [dragon Blender rigging handoff](./2026-08/25-rigging/dragon_blender_rigging_handoff.md). |

Future packets already foreseen by the handoff (not yet opened): donor
extraction + canonical skeleton study (milestone 2A after the acquisition
packet), canonical western-dragon template + weights (milestone 2B), coarse
alignment and non-rigid fitting (milestones 3–4), skeleton fit + skinning +
deformation tests (milestone 5), and appearance transfer (milestone 6).
