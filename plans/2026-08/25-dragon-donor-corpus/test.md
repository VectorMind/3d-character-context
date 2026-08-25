# Test — Western-Dragon Donor Corpus Acquisition

This is a planning-only packet. Per `WORKFLOW.md`, this file currently records
document review and consistency checks rather than marketplace or runtime
proof.

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

## Execution Evidence

None. No marketplace was browsed, no API was probed, no Chrome session was
controlled, no asset was downloaded or purchased, and no cloud-workspace data
or folder structure was changed in this planning pass.

## Known Gaps

- Fab, Sketchfab, CGTrader, and TurboSquid capabilities are intentionally
  unverified until Phase 1.
- All proposed folder/schema details except the inherited three-root data
  boundary await maintainer review.
- No runtime or asset fixture exists yet.
