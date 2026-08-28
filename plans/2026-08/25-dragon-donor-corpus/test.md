# Test — Western-Dragon Donor Corpus Acquisition

The packet remains in planning, but now includes read-only evidence about three
candidate files manually collected by the maintainer. A separate completed
packet later packaged and inspected them, but no candidate has yet been
accepted into this packet's proposed donor-acquisition lifecycle.

## Planning Consistency Checks (2026-08-25)

- Read the complete operational summaries in repository `AGENTS.md` and
  `WORKFLOW.md`, plus the active-plan index in `plans/open.md`.
- Considered
  `plans/2026-08/25-rigging/dragon_blender_rigging_handoff.md`, especially its
  donor-corpus purpose, 5–10 starting recommendation, selection gates, format
  preference, provenance requirements, extraction boundary, and milestone 2A.
- Read the cloud co-workspace `AGENTS.md`, `README.md`, `INDEX.md`,
  `assets/README.md`, `assets/collected/README.md`, and
  `assets/western_dragon_v1/README.md`.
- Confirmed the plan uses the accepted `inputs/`, `generated/`, `assets/`
  project roots and treats collected donors as reusable assets rather than
  generated runs.
- Confirmed `plan.md` contains the required problem summary, one-glance
  resolution table, goals, scope/non-goals, detailed open points with options,
  proposals/confidence/status, phases, dependencies, risks, and exit criteria.
- Confirmed OP-001…OP-010 table rows match the detailed sections; OP-005 is
  explicitly inherited/accepted and all other rows remain open for maintainer
  review.
- Confirmed the first executable phase is read-only source-system discovery
  and that download, purchase, account mutation, and corpus changes remain
  gated.
- Confirmed the plan separates catalog discovery, entitlement, and actual file
  delivery instead of assuming that a REST API solves all three.
- Updated repository workflow guidance so the external project is explicitly
  a data co-workspace for inputs, generated runs, collected donor/source
  assets, and canonical assets.
- Added the packet to `plans/open.md`; no `implementation.md` was created
  because implementation has not begun.

## Read-Only Candidate Inventory (2026-08-26)

Commands/checks:

- recursively enumerated files under the selected project's
  `assets/collected/` folder and grouped them by extension;
- listed both levels of `european-dragon.zip` using ZIP readers without
  extracting or changing it;
- computed SHA-256 for the three candidate files;
- opened the two BLEND files with provisioned Blender 5.2.1 using
  `--background --disable-autoexec` and an operational inspection script under
  `.cache/scratch/`; neither source file was saved or changed.

Actual results:

| Candidate | Bytes | SHA-256 | Read-only findings |
| --- | ---: | --- | --- |
| `blender_dragon.blend` | 2,638,248 | `13a4a92ed36c3922fa6cca8c2ed467209d53681d9d8b31752e5a17428cfe7ed3` | 1 mesh, 11,002 vertices, 10,998 polygons, 1 armature/38 deform bones, no actions or materials; one unpacked external texture reference |
| `dragon.blend` | 20,629,992 | `6cb566aa82d9d7eb833aa7841019a49006aeae9a84ae385643268e959c7c92b3` | 67 meshes, 25,025 vertices, 26,244 polygons, 1 armature/196 deform bones, 10 actions including one 104-frame fly action, 7 materials; unpacked external texture references |
| `european-dragon.zip` | 78,475,988 | `8f464c74ea5a100ec8fdbd9d2456842f9880f80780af5182778be53bdab5d0d4` | Outer archive contains a nested `Dragon_GameReady_Rig_&_Animations.zip` plus 4K textures; inner archive contains one 7,076,476-byte FBX and 14 PNG textures in 2K/4K variants; FBX not yet imported |

Expected: inventory and structural facts are obtained without changing the
cloud workspace. Actual: pass. The collection still contains the same three
candidate files and its README at the top level; no folders were created and
no files moved, extracted, rendered, or rewritten.

## Known Gaps

- Fab, Sketchfab, CGTrader, and TurboSquid capabilities are intentionally
  unverified until Phase 1.
- All proposed folder/schema details except the inherited three-root data
  boundary await maintainer review.
- Source URL, creator, license, and true acquisition date are unknown for all
  three candidates; they must remain `hold` unless supplied or deliberately
  resolved.
- The European-dragon FBX was later imported and measured by the completed
  asset-catalog packet; that is asset-inspection proof, not acquisition or
  provenance proof for this packet.
- Reusable asset-package, inspection, render, README-generation, and web-viewer
  commands now exist through the completed asset-catalog packet. Source-system
  acquisition research, intake decisions, and donor-corpus selection remain
  outstanding here.
