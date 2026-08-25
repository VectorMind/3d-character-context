# Open Plans

Plan packets with work still outstanding. See each folder for details.

| Plan | Date | State | Outstanding |
| --- | --- | --- | --- |
| [3D Character Context Initial Bringup](./2026-08/25-initial-bringup/plan.md) | 2026-08-25 | Planning complete | All open points OP-001…OP-013 accepted 2026-08-25 (HF-first with a Phase 1 free-access experiment, relaxed abstraction, append-only paid results, data/code split with `.env`-selected co-workspace, Blender 5.2.1 via `charctx fetch` from download.blender.org). Phase 1 in progress: Hugging Face free access validated 2026-08-25 — REST inference serves no `image-to-3d` (Spaces are the only free HF path), `microsoft/TRELLIS` is down, and both `trellis-community/TRELLIS` and `microsoft/TRELLIS.2` returned measured GLBs on ~4 free generations/day of ZeroGPU quota. Outstanding: probe the commercial free tiers (Meshy, Tripo, Rodin), then select the backend and start Phase 2. Probes: [experiments/](../experiments/README.md); log: [implementation.md](./2026-08/25-initial-bringup/implementation.md). Founding architecture: [handoff.md](./2026-08/25-initial-bringup/handoff.md). |
| [Western-Dragon Donor Corpus Acquisition](./2026-08/25-dragon-donor-corpus/plan.md) | 2026-08-25 | Planning | OP-001…OP-010 await maintainer review. No marketplace research, downloads, purchases, or corpus changes have started. First executable phase is a read-only, evidence-recorded source-system review using maintainer-provided Chrome access; pilot acquisition remains gated on the decision pass. Rigging basis: [dragon Blender rigging handoff](./2026-08/25-rigging/dragon_blender_rigging_handoff.md). |

Future packets already foreseen by the handoff (not yet opened): donor
extraction + canonical skeleton study (milestone 2A after the acquisition
packet), canonical western-dragon template + weights (milestone 2B), coarse
alignment and non-rigid fitting (milestones 3–4), skeleton fit + skinning +
deformation tests (milestone 5), and appearance transfer (milestone 6).
