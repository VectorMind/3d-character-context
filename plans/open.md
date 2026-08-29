# Open Plans

Plan packets with work still outstanding. See each folder for details.

| Plan | Date | State | Implementation progress | Outstanding |
| --- | --- | --- | --- | --- |
| [Riyu Skeleton Fit And Rig Visualization](./2026-08/29-riyu-skeleton-fit/plan.md) | 2026-08-29 | Implementing | `▰▰▱▱▱▱▱ Step 2/7` — the crude rigid transfer and 21 geometric landmarks are landed and visible on Riyu; interior joints are declared unattempted rather than guessed. Review gate at the end of step 3. | Fit european-dragon's hierarchy onto the generated Riyu mesh and see it, then landmarks, semantic naming, rig-influence visualization, and a distance heuristic scored against donor ground truth. Deliberately independent of the 2026-08-25 handoff's canonical-mesh-first route; per-character, no reusability yet. Review gate after step 3. |
| [Multiview Generator Support](./2026-08/28-multiview-support/plan.md) | 2026-08-28 | Parked future work | `□□□□□ Parked before Phase 1/5` — current monoview status is documented; no multiview backend or live proof exists. | OP-003/OP-004/OP-008 remain open: select and prove a genuine multiview backend, settle view-role and CLI contracts, run a controlled provider bakeoff, and reject unsupported cardinality explicitly. |
| [Western-Dragon Donor Corpus Acquisition](./2026-08/25-dragon-donor-corpus/plan.md) | 2026-08-25 | Planning + packaged manual candidates | `▱▱▱▱▱▱▱ Phase 0/7` — the three manual candidates were inventoried; the acquisition decision pass and structured intake are next. Their later packaging, inspection, and local catalog belong to the completed [asset catalog/viewer packet](./2026-08/26-dragon-asset-catalog-viewer/plan.md), so they do not advance this packet's acquisition phases. | OP-001…OP-004 and OP-006…OP-010, plus source-system research, await maintainer review; OP-005 is already accepted. The three candidates' provider/creator/license provenance remains unknown. Rigging basis: [dragon Blender rigging handoff](./2026-08/25-rigging/dragon_blender_rigging_handoff.md). |

Milestone 2A's donor-extraction half is delivered by the closed [donor
skeleton extraction packet](./2026-08/28-donor-skeleton-extraction/plan.md);
its canonical-skeleton study half is not.

Future packets already foreseen by the handoff (not yet opened): the canonical
skeleton study (rest of milestone 2A), canonical western-dragon template +
weights (milestone 2B), coarse alignment and non-rigid fitting (milestones
3–4), skeleton fit + skinning + deformation tests (milestone 5), and
appearance transfer (milestone 6).
