# Open Plans

Plan packets with work still outstanding. See each folder for details.

| Plan | Date | State | Implementation progress | Outstanding |
| --- | --- | --- | --- | --- |
| [Volumetric Body-Part Labeling](./2026-08/30-body-part-labeling/plan.md) | 2026-08-30 | Implementing | `▰▰▰▱▱ Phase 2/5` — the taxonomy, the voxel substrate, a donor reference volume and a scored ablation are landed and visible, and a **skeleton is now read out of a labelled volume**. Riyu's 6,209 shells voxelize to one solid component. Against the donor's own rig the derived joints land at **0.70% of the body diagonal, median** — the elbow at 0.33%, the knee at 0.72%, the jaw hinge at 1.12%, all of them joints the landmark route could not propose at all. The declared part hierarchy matches the donor 31/31; deriving it from region adjacency was measured at 27/31 and dropped. | Ten phase-2 open points (OP-201…OP-210) are proposed with confidences and are in the decision table above. Two matter most: the wing membrane is 13% out (OP-207), and the landmark route still yields no `pelvis`, so a rigless target gets no skeleton (OP-209). Then phases 3–5: volumetric weights, hosted neural segmentation (`tencent/Hunyuan3D-Part`, probed and live), and learned classification from the donor's 332 animation frames. |
| [Riyu Skeleton Fit And Rig Visualization](./2026-08/29-riyu-skeleton-fit/plan.md) | 2026-08-29 | **Review gate open** | `▰▰▰▱▱▱▱ Step 3/7` — the landmark-driven per-chain fit is landed: 74 of 168 bones anchored on Riyu's own landmarks across 8 chains, span fill 46% → 100%, and no anchored joint escapes the mesh. The remaining 94 bones are declared carried, not fitted. | **Look before continuing.** Two questions only the pictures can settle: whether the derived left/right convention matches the donor's bone naming, and whether the 85 carried joints outside the mesh need landmarks of their own before skinning. Then steps 4–7: semantic bone naming, rig-influence visualization on the donor, a distance heuristic scored against donor ground truth, and skinning Riyu. Deliberately independent of the 2026-08-25 handoff's canonical-mesh-first route; per-character, no reusability yet. |
| [Multiview Generator Support](./2026-08/28-multiview-support/plan.md) | 2026-08-28 | Parked future work | `□□□□□ Parked before Phase 1/5` — current monoview status is documented; no multiview backend or live proof exists. | OP-003/OP-004/OP-008 remain open: select and prove a genuine multiview backend, settle view-role and CLI contracts, run a controlled provider bakeoff, and reject unsupported cardinality explicitly. |
| [Western-Dragon Donor Corpus Acquisition](./2026-08/25-dragon-donor-corpus/plan.md) | 2026-08-25 | Planning + packaged manual candidates | `▱▱▱▱▱▱▱ Phase 0/7` — the three manual candidates were inventoried; the acquisition decision pass and structured intake are next. Their later packaging, inspection, and local catalog belong to the completed [asset catalog/viewer packet](./2026-08/26-dragon-asset-catalog-viewer/plan.md), so they do not advance this packet's acquisition phases. | OP-001…OP-004 and OP-006…OP-010, plus source-system research, await maintainer review; OP-005 is already accepted. The three candidates' provider/creator/license provenance remains unknown. Rigging basis: [dragon Blender rigging handoff](./2026-08/25-rigging/dragon_blender_rigging_handoff.md). |

## Decisions And Open Points

Everything across every packet that is **waiting on the maintainer**: open
points, design choices, questions, and anything else where a look or a
correction is what unblocks a better answer. A row leaves this table once it is
accepted, rejected or deferred; the packet's own resolution summary keeps the
history. An empty table means nothing is waiting.

None of these blocks work. Each names a proposal the packet has already
proceeded on, so what is being asked for is an overturn where a proposal is
wrong. Confidence is about evidence, not enthusiasm: `high` means it was
measured on real data, `medium` means it is a convention one donor agrees with,
`low` means it is reasoning that has not been tested.

| Id | Packet | Topic | Proposal | Confidence | Status |
| --- | --- | --- | --- | --- | --- |
| OP-201 | [body-part labeling](./2026-08/30-body-part-labeling/plan.md) | **Where is the elbow?** How a single joint is chosen out of an interface of thousands of voxel faces | Depth²-weighted centroid of the interface — a joint is a cross-section through a limb, a fold is a crease at the skin, and area alone cannot tell them apart | high | **Awaiting review** — measured: 0.66% median against 0.80% for a plain centroid; exponent swept |
| OP-202 | [body-part labeling](./2026-08/30-body-part-labeling/plan.md) | **Does the hierarchy come from geometry or from the taxonomy?** The packet's own framing table said "derived, not borrowed" | Declared by the taxonomy; adjacency derived every run and reported as a check | high | **Awaiting review** — measured: adjacency gets 27/31 and all four failures are *folds*; the declared table matches the donor 31/31 |
| OP-203 | [body-part labeling](./2026-08/30-body-part-labeling/plan.md) | Where a bone ends | The child joint farthest from the head, so a bone's tail is its child's head; the far end of its own region for a leaf | high | **Awaiting review** — measured: 0.71% median tail error against 1.33% |
| OP-204 | [body-part labeling](./2026-08/30-body-part-labeling/plan.md) | Where the root bone starts, since the root part has no parent to take a head from | Declared: `pelvis`, starting at its boundary with `tail_base`, with a farthest-point fallback when no tail is labelled | medium | **Awaiting review** — a rigging convention the donor happens to confirm exactly |
| OP-205 | [body-part labeling](./2026-08/30-body-part-labeling/plan.md) | Bone granularity: 31 derived bones against the donor's 168 | One bone per part now; a **declared** per-part subdivision later, so an interpolated joint stays visibly interpolated | medium | **Awaiting review** — a one-bone `tail_mid` cannot curl, so posing will hit this |
| OP-206 | [body-part labeling](./2026-08/30-body-part-labeling/plan.md) | Roll | Not derived; every bone reports 0 and the document says why | medium | **Awaiting review** — an occupancy grid carries no twist; skinning probably does not need it, posing will |
| OP-207 | [body-part labeling](./2026-08/30-body-part-labeling/plan.md) | The wing membrane — the one measured failure | Trim the interface by depth before taking its centroid; if that fails, giving the membrane its own part is the taxonomy change it would take | low | **Awaiting review** — `wing_hand` is **13% of the body diagonal** out against a 0.70% median; the proposed fix is untested |
| OP-208 | [body-part labeling](./2026-08/30-body-part-labeling/plan.md) | What number decides the deterministic route is not good enough, and phases 4–5 open | Median joint error ≤1% of the body diagonal under *donor-independent* seeding, with every taxonomy part present | medium | **Awaiting review** — reference seeding gives 0.70% and would pass; centroid seeding gives 1.42% and does not |
| OP-209 | [body-part labeling](./2026-08/30-body-part-labeling/plan.md) | What supplies the interior parts on a target with no rig | Chain-proportion priors first (measurable against the donor immediately), hosted segmentation second | low | **Awaiting review** — the landmark route yields no `pelvis` on the donor, so it produces **no skeleton at all** |
| OP-210 | [body-part labeling](./2026-08/30-body-part-labeling/plan.md) | **Does the derived skeleton replace the donor rig, or feed it?** The decision that closes the parenthesis opened inside the Riyu packet | Feed it: derived joints become anchors for the existing chain fit, and the donor keeps supplying only digits and within-chain proportion | medium | **Awaiting review** — the number that would settle it (how many of Riyu's 94 carried bones a derived joint anchors) is not measured |
| — | [Riyu skeleton fit](./2026-08/29-riyu-skeleton-fit/plan.md) | **Review gate: look at the pictures.** Whether the derived left/right convention matches the donor's bone naming, and whether the 85 carried joints outside the mesh need landmarks before skinning | Proceed to steps 4–7 once the two questions are answered by eye | — | **Awaiting review** — only the pictures can settle these |

## Dependencies

Every runtime dependency a packet has asked for, across all packets. A request
never blocks the work: the packet takes the path that needs no new dependency
and records the ceiling it hits, so the measurement is what makes the case.

| Id | Package | Packet | Case | Confidence | Status |
| --- | --- | --- | --- | --- | --- |
| DEP-001 | `scikit-image` | [body-part labeling](./2026-08/30-body-part-labeling/plan.md) | 3D `skeletonize` for part medial axes (phase 2's whole mechanism), `MCP_Geometric` for true Euclidean geodesics through a volume, compact `watershed`, `marching_cubes`. Probed on the real target: skeletonize 0.01 s, MCP 0.03 s, marching cubes 0.02 s. | high | **Approved 2026-08-30** |
| DEP-002 | `libigl` | [body-part labeling](./2026-08/30-body-part-labeling/plan.md) | Generalized winding number (inside/outside on shell soup) and bounded biharmonic weights for phase 3. | — | **Rejected — no Windows wheel for Python 3.12**; the sdist build fails on a missing MSVC toolchain. Revisit only with Build Tools installed, or if phase 3 needs BBW specifically. |
| DEP-003 | `scikit-learn` | [body-part labeling](./2026-08/30-body-part-labeling/plan.md) | A learned part classifier from the donor's 332 animation frames (phase 5). | medium | Deferred — phase 5 only; `scipy.cluster` covers current clustering. |
| DEP-004 | `rtree` / `embreex` / `manifold3d` | [body-part labeling](./2026-08/30-body-part-labeling/plan.md) | Faster trimesh proximity and ray queries; mesh repair and booleans. | low | Deferred — not a bottleneck (voxelizing Riyu takes ~3 s), and mesh repair is irrelevant while the substrate is voxels. |

`pillow` arrived transitively with `scikit-image` and is what a vision-model
view pipeline would need to render and back-project head landmarks.

Milestone 2A's donor-extraction half is delivered by the closed [donor
skeleton extraction packet](./2026-08/28-donor-skeleton-extraction/plan.md);
its canonical-skeleton study half is not.

Future packets already foreseen by the handoff (not yet opened): the canonical
skeleton study (rest of milestone 2A), canonical western-dragon template +
weights (milestone 2B), coarse alignment and non-rigid fitting (milestones
3–4), skeleton fit + skinning + deformation tests (milestone 5), and
appearance transfer (milestone 6).
