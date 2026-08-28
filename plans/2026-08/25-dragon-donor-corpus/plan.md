# Plan — Western-Dragon Donor Corpus Acquisition

Date: 2026-08-25  
Status: Open at Phase 0/7 — OP-001…OP-004 and OP-006…OP-010 await
maintainer review; OP-005 is accepted. Three manually collected candidates
were inventoried on 2026-08-26 and later organized, inspected, and made
locally browsable by the separate completed asset-catalog packet, but they
remain unprovenanced and are not accepted as donors.
Basis:
[`dragon_blender_rigging_handoff.md`](../25-rigging/dragon_blender_rigging_handoff.md),
especially sections 8–16 and milestone 2A

## Problem Summary

The rigging handoff calls for a small engineering reference corpus of rigged
western dragons. Before acquiring it, we need to understand how each candidate
marketplace actually manages assets: discovery and filters, stable identifiers,
accounts and libraries, entitlement, licenses, purchase/download flows,
available file formats, updates, and any supported automation surface.

“Automatic collection” cannot be assumed to mean one generic downloader.
Fab, Sketchfab, CGTrader, TurboSquid, and later candidates may expose different
official APIs, authentication models, commerce gates, browser-only flows, and
usage restrictions. The first executable work must therefore be a
source-by-source capability study. It will decide whether each source should
use an official API, an assisted signed-in Chrome flow, or a manual download
followed by automated intake.

The data must live in the designated cloud-synced project co-workspace selected
by `CHARCTX_PROJECT`, currently:

```text
C:\Users\wassi\My Drive\Projects\3d-models\characters-generation
```

That folder is authoritative for the data and its provenance. The repository
is authoritative for acquisition contracts, automation, and verification.

On 2026-08-26 the maintainer placed two BLEND files and one ZIP package directly
under `assets/collected/`. This is a useful early pilot, but it deliberately
does not resolve the open source-system questions: the files have no adjacent
source/license records and have not entered the proposed package lifecycle.
Their safe migration, inspection, preview generation, and catalog presentation
are scoped by the linked
[`Dragon Asset Catalog And Web Viewer`](../26-dragon-asset-catalog-viewer/plan.md)
packet.

## Resolution Summary

This table is the decision surface for the first maintainer review. An open
row is a proposal, not an accepted decision.

| OP | Topic | Proposal | Confidence | Status |
| --- | --- | --- | --- | --- |
| OP-001 | Corpus size and staging | Inspect up to 3 pilot assets, then target 10 accepted donors with a hard cap of 15; expand only for a named structural gap | medium | **open** |
| OP-002 | Initial source roster and order | Review Fab first, then Sketchfab, CGTrader, and TurboSquid; add other sources only if the first four leave a coverage gap | low | **open** |
| OP-003 | Per-source access method | Choose per source from official API/client credentials, assisted signed-in Chrome, or manual download; prefer the most official repeatable method that actually covers entitled asset delivery | high | **open** |
| OP-004 | Automation and purchase boundary | Automate discovery, metadata capture, integrity checks, and intake where permitted; keep checkout, payment, and acceptance of new terms as explicit maintainer actions | high | **open** |
| OP-005 | Data-workspace boundary | Use the selected cloud project as the durable data co-workspace; place third-party donors under `assets/`, never in this repository or `generated/` | high | **accepted 2026-08-25 (inherited from initial-bringup OP-009/OP-012)** |
| OP-006 | Collected-asset layout and corpus index | Keep self-contained provider/id asset packages under `assets/collected/`; maintain a separate reference-only corpus file under `assets/corpora/` instead of copying assets | medium | **open** |
| OP-007 | Provenance, licensing, and lifecycle record | Use a machine-readable record plus preserved source/license evidence; gate each item through candidate → approved → acquired → verified/hold/rejected → selected | medium | **open** |
| OP-008 | Donor acceptance rubric | Apply hard anatomy/rig/license gates, then score rig inspectability, source format, deformation evidence, and structural diversity | high | **open** |
| OP-009 | Duplicate and revision policy | Identify logical assets by provider + stable source id (URL hash only as fallback), hash every downloaded file, and never overwrite a prior acquisition | medium | **open** |
| OP-010 | Productized automation threshold | Use Chrome/manual work for the small pilot; implement a source adapter only when Phase 1 finds a supported interface and enough repeat use to justify maintenance; always automate local intake | high | **open** |

## Goal And Objectives

Create a small, lawful, reproducible donor corpus that is suitable for the
next milestone's Blender extraction and canonical-skeleton study.

Objectives:

- understand each initial marketplace's complete asset-management system
  before downloading;
- choose and document the least fragile permitted acquisition method per
  source;
- shortlist donors by rigging value rather than visual appeal alone;
- preserve original files, identity, provenance, licensing, and integrity;
- organize data so one asset can participate in multiple corpora without
  duplication;
- verify that an acquired file contains inspectable mesh, armature, weights,
  and advertised animations before calling it a donor;
- turn repeatable local intake and audit into a future documented `charctx`
  CLI surface, while avoiding speculative marketplace adapters.

## Scope And Non-Goals

In scope:

- read-only marketplace and official-documentation inspection;
- source capability/evidence matrix;
- corpus size, source, access, folder, metadata, licensing, and selection
  decisions;
- candidate discovery and scoring after the decision pass;
- a controlled pilot followed by a 10-donor target, capped at 15;
- permitted download assistance, checksum/provenance capture, structured
  intake, and minimal rig-presence verification;
- requirements for later acquisition/intake commands.

Non-goals:

- downloading, purchasing, or changing the data workspace during this
  planning pass;
- automatic checkout, payment, acceptance of marketplace terms, CAPTCHA or
  anti-bot bypass, private-API reverse engineering, or credential/session
  extraction;
- treating unclear licenses as permission;
- building a broad training dataset or claiming AI-training rights;
- redistributing marketplace assets;
- full donor skeleton/weight extraction, semantic bone mapping, canonical
  skeleton design, canonical mesh creation, or skin-weight synthesis;
- supporting wyverns, eastern dragons, bipeds, or arbitrary creatures;
- writing provider assets or long-lived metadata into the code repository.

## Source-System Discovery Contract

Phase 1 will record the following for each source, with evidence date and
official URLs. Unknowns remain explicitly unknown; the plan does not assume,
for example, that Fab has a suitable REST API or client-credentials flow.

| Area | Questions to answer |
| --- | --- |
| Catalog | Can search filter for western-dragon anatomy, rigged/animated status, price, license, and BLEND/FBX/GLB? |
| Identity | Is there a stable asset id, canonical URL, creator id, version, SKU, or listing revision? |
| Metadata | Which title, creator, description, format, animation, engine/DCC, and preview fields are exposed and exportable? |
| Rights | Where are license name/text/URL, AI or training restrictions, redistribution constraints, and asset-specific exceptions shown? |
| Account/library | How are free, purchased, claimed, and previously downloaded assets represented? Is an entitlement durable? |
| Delivery | Is download browser-only, launcher/client based, archive based, signed-URL based, or supported by an official API? Are original and alternate formats separate? |
| Automation | Is there a documented API, SDK, CLI, OAuth flow, API key, or client-credentials flow? What catalog, library, entitlement, and download operations does it actually cover? |
| Limits | What documented terms, quotas, rate limits, bot restrictions, token expiry, regional limits, or interactive gates apply? |
| Updates | Can an owned asset change? Are old versions retained? How are updates and duplicate cross-listings identified? |
| Fallback | If file delivery is manual, can discovery and subsequent local intake still be automated reliably? |

The source matrix is complete only when it distinguishes catalog APIs from
entitled-download APIs. The existence of a public catalog endpoint would not
by itself prove automatic file acquisition.

## Proposed Intake Shape (Pending OP-006/OP-007/OP-009)

The handoff sketched a top-level `donors/` folder. This plan instead proposes
keeping donors inside the already accepted three-root project contract:

```text
<project>/
  assets/
    _inbox/
      <acquisition-session>/
    collected/
      <source>/
        <source-id>--<slug>/
          record.yaml
          record.md
          license/
          source/
          previews/
          inspection/
    corpora/
      western-dragon-rigged-v1/
        corpus.yaml
```

Design intent:

- `_inbox/` is temporary quarantine, not a permanent dumping ground;
- `source/` preserves downloaded bytes and vendor archive structure;
- `license/` preserves supplied files and dated evidence, not just a guessed
  license label;
- `inspection/` contains derived reports/renders and never modifies source;
- `record.yaml` is machine-readable provenance/state; `record.md` is the
  concise human view and may later be generated from it;
- `corpus.yaml` references collected packages and records inclusion rationale;
  it is not a project manifest and does not duplicate asset bytes;
- when no stable source id exists, a canonical-URL hash is the proposed
  fallback pending OP-009;
- revisions or repeat acquisitions never overwrite previous original bytes.

Minimum proposed machine-readable fields:

```text
internal_asset_id
source, source_asset_id, canonical_url
title, creator, creator_url
discovered_at, acquired_at, acquisition_method
listed_formats, acquired_files, sha256, byte_size
listed_rigged, verified_armature, verified_weights
listed_animations, verified_animations
license_name, license_url, license_evidence
allowed_use, ai_training_status, redistribution_status
price_at_acquisition, transaction_reference_if_safe
lifecycle_state, hold_reason, selection_score, notes
```

Secrets, cookies, access tokens, raw client credentials, and payment details
must never enter these records.

## Open Points

### OP-001 — Corpus size and staging

How large should the first useful corpus be?

- **5–10 total:** follows the handoff closely and limits cost, but may miss
  wing, spine, rest-pose, or weight-layout diversity.
- **10–15 total:** still manually manageable and gives room for structural
  variation, but costs more and can encourage collection before validation.
- **20–30 total:** better coverage for statistics, but premature before we
  know whether marketplace rigs can be normalized.

Proposal: inspect/acquire no more than three pilot items first, then target 10
accepted donors with a hard cap of 15. Any expansion must name the missing
structural category it fills. Confidence: medium. Status: **open**.

### OP-002 — Initial source roster and order

Which marketplaces should Phase 1 study?

- **Fab:** explicitly raised by the maintainer and should be tested first;
  actual API/auth/download capabilities are unknown until inspected.
- **Sketchfab:** useful candidate catalog/viewer; rig/file/license and
  entitled-download surfaces must be verified rather than assumed.
- **CGTrader:** likely broad commercial coverage; filters, library, license,
  and delivery behavior need inspection.
- **TurboSquid:** likely broad commercial coverage; formats, rig claims,
  license, and delivery behavior need inspection.
- **Long-tail sources immediately:** may find better donors but would make the
  first comparison unbounded.

Proposal: Fab → Sketchfab → CGTrader → TurboSquid. Add another legal asset
library only after documenting a concrete anatomy, format, license, or price
gap. Confidence: low until Phase 1. Status: **open**.

### OP-003 — Per-source access method

What access mechanism should acquisition use?

- **Official API/SDK with documented credentials:** repeatable and easiest to
  validate, but only useful if it covers the user's entitled files rather
  than catalog search alone.
- **Maintainer's signed-in Chrome session:** can represent the real account
  and library flows and is suitable for early testing, but is interactive and
  sensitive to UI changes.
- **Manual user download + automated local intake:** robust for a corpus of
  10–15 and keeps commerce/account actions human, but file acquisition itself
  is not automatic.
- **Undocumented/private endpoints:** potentially automatable but fragile and
  unacceptable without explicit provider support and terms compatibility.

Proposal: decide per source after the capability matrix. Prefer a supported
official API when it covers the required operation; otherwise use assisted
Chrome or manual download, followed by the same automated local intake.
Exclude undocumented/private endpoints. Confidence: high. Status: **open**.

### OP-004 — Automation and purchase boundary

How far may an assisted workflow act?

- **Fully automatic including checkout:** highest apparent throughput, but
  risks unwanted purchases and accepting legal terms without review.
- **Automatic free/owned downloads, human purchase:** workable if a source
  clearly supports it and every entitlement is proven.
- **Human confirms every download:** safest but unnecessarily slow for
  already owned or clearly free items.

Proposal: automate discovery, metadata/licensing capture, owned/free download
where provider support and user intent are explicit, checksum, and intake.
The maintainer performs or explicitly approves checkout, payment, license
acceptance, and claiming a new entitlement. Confidence: high. Status:
**open**.

### OP-005 — Data-workspace boundary

This is inherited from initial-bringup OP-009/OP-012 and the cloud workspace's
`AGENTS.md`:

- the cloud project is the durable co-workspace for inputs, generated runs,
  and reusable/canonical assets;
- donor assets belong under `<project>/assets/`, not a new repository asset
  directory and not `<project>/generated/`;
- the cloud workspace is authoritative for data and provenance; the repo is
  authoritative for software and contracts.

Resolution: keep the accepted three-root contract and make the repository
workflow state explicitly that `assets/` includes collected donor/source
assets. Confidence: high. Status: **accepted 2026-08-25 (inherited)**.

### OP-006 — Collected-asset layout and corpus index

How should 10–15 donor packages be organized?

- **Flat `assets/collected/<asset-slug>/`:** matches the current cloud README
  exactly and is simple, but risks name collisions and weak provider grouping.
- **Provider/id packages under `assets/collected/` plus a corpus reference
  file:** collision-resistant, queryable, and keeps one physical asset usable
  by multiple corpora.
- **Top-level `<project>/donors/`:** matches the handoff sketch, but creates a
  fourth top-level data root and separates reusable assets from `assets/`.

Proposal: provider/id packages plus
`assets/corpora/western-dragon-rigged-v1/corpus.yaml`. Update the cloud
workspace README/INDEX only after this is accepted; do not create folders
during planning. Confidence: medium. Status: **open**.

### OP-007 — Provenance, licensing, and lifecycle record

What is the source of truth for each asset?

- **Markdown only:** pleasant to review but difficult to validate and catalog.
- **YAML/JSON only:** machine-safe but less convenient for licensing nuance.
- **Machine record + human view + raw evidence:** most complete, with modest
  duplication unless the human view is generated.

Proposal: validated `record.yaml`, concise `record.md`, and preserved license
files/pages/evidence. Use explicit lifecycle states: `candidate`, `approved`,
`acquired`, `verified`, `hold`, `rejected`, `selected`. Unknown license or
training terms never default to allowed. Confidence: medium. Status: **open**.

### OP-008 — Donor acceptance rubric

What qualifies as a useful donor?

- **Visual-quality first:** easy to shortlist but poorly aligned with the
  skeleton/weight study.
- **Hard technical gates only:** objective, but could produce a redundant
  corpus.
- **Hard gates plus a scored diversity rubric:** keeps every asset usable
  while deliberately covering different structures.

Proposal: hard-gate for four legs, two wings, one neck/head, one tail,
inspectable deform skeleton, skin weights, acceptable file format
(`BLEND` > `FBX` > `GLB/glTF`; no OBJ/STL-only donor), provenance, and usable
rights for local engineering reference. Then score rig inspectability,
neutral/rest pose, jaw and wing articulation, animation/deformation evidence,
format richness, and non-duplicative proportions/rig structure. Marketplace
claims remain unverified until the downloaded file is inspected. Confidence:
high. Status: **open**.

### OP-009 — Duplicate and revision policy

How should duplicate listings and updated files be handled?

- **Title/slug identity:** simple but unreliable across sellers and mirrors.
- **Provider + stable source id:** strong within a provider but does not by
  itself detect cross-market duplicates.
- **File hash only:** detects identical bytes but not repacks or revisions.
- **Combined source identity, hashes, and a manual related-asset link:** most
  reliable for a small corpus.

Proposal: provider + stable source id as logical identity, canonical-URL hash
only as fallback, SHA-256 for every file, and explicit `same_as`/`revision_of`
links. Never overwrite a previous original; use a new acquisition/revision
record. Confidence: medium. Status: **open**.

### OP-010 — Productized automation threshold

When should marketplace behavior become repository code?

- **Build adapters before browsing:** maximizes early automation but guesses
  at unstable or unavailable APIs.
- **Use browser automation as the permanent downloader:** fast to start but
  UI-fragile and awkward as the documented CLI contract.
- **Pilot first; productize supported repeated surfaces and always productize
  local intake:** keeps the durable code centered on stable contracts.

Proposal: use maintainer-provided Chrome control for the small discovery and
pilot loop. Do not promise Chrome UI automation as a production interface.
After Phase 1, implement an official source adapter only if a supported
interface covers a repeated need. Regardless of download method, later expose
local asset import/audit/catalog behavior through documented `charctx`
commands and the side-effect-free Python API. Confidence: high. Status:
**open**.

## Implementation Phases

### Phase 0 — Maintainer decision pass

- Review OP-001…OP-010 and accept, amend, or reject each proposal.
- Set the pilot spending ceiling and confirm whether only free/owned assets
  may be tested; no purchase is implied by this plan.
- Confirm which marketplace accounts can be inspected through Chrome.
- Gate: no pilot acquisition until the choices that affect rights, storage,
  and action authority are accepted.

### Phase 1 — Read-only source-system review with Chrome

- Use maintainer-provided Chrome access and existing signed-in state where
  needed.
- Inspect Fab first, then the accepted roster, using the discovery contract
  above.
- Consult only official provider documentation for API/auth claims.
- Record dated evidence for catalog, library, entitlement, license, delivery,
  API/auth, quota, and update behavior.
- Do not download, claim, purchase, accept terms, or modify a provider account
  during this phase.
- Produce a per-source recommendation: API, assisted Chrome, manual download,
  or unsuitable.

### Phase 2 — Approve the intake contract and selection rubric

- Resolve any OP amendments raised by Phase 1.
- Fold the accepted asset-package, provenance, and rights-gate rules into a
  durable specification before implementing them.
- Update the cloud workspace README/INDEX to match the accepted layout.
- Define the candidate/selection schema and a weighted donor rubric.
- Specify CLI behavior for importing an already downloaded asset without
  mutating the original bytes.

### Phase 3 — Controlled three-asset pilot

- Shortlist candidates across at least two source/access patterns where
  possible.
- Have the maintainer approve each candidate and any new entitlement or cost.
- Acquire at most three assets using the chosen per-source methods.
- Stage safely, compute hashes, capture source/license evidence, and promote
  self-contained packages into the cloud workspace.
- Run minimal Blender inspection: file opens, non-empty mesh exists, armature
  exists, vertices have bone influences, and advertised animations/actions
  are enumerated. Record facts, not appearance-only judgments.
- Review whether the proposed folders and records are tolerable in practice.

### Phase 4 — Automate the proven repeatable path

- Implement and document local intake, catalog, and audit behavior first.
- Implement source-specific API automation only for supported, proven
  interfaces selected after Phase 1/3.
- Keep browser/manual delivery as a documented input path where that is the
  correct source behavior.
- Use offline fixtures for default tests; keep live marketplace checks
  explicit, bounded, and non-purchasing.

### Phase 5 — Build the target corpus

- Discover and score a wider shortlist before downloading.
- Select for skeleton, wing, tail/neck, rest-pose, format, and animation
  diversity rather than accumulating near-duplicates.
- Grow from the verified pilot to 10 selected donors; stop at 10 unless a
  named coverage gap justifies another asset, never exceeding 15 in this
  packet.
- Keep rejected and hold records when they explain a decision, without
  retaining unauthorized asset bytes.

### Phase 6 — Audit and extraction handoff

- Reconcile the corpus file with collected packages and hashes.
- Confirm every selected donor has clear provenance/rights status and the
  minimum rig-presence report.
- Summarize source-specific acquisition methods and remaining manual steps.
- Open the separate donor-extraction/canonical-skeleton study packet; do not
  silently expand this acquisition packet into semantic bone normalization.

## Dependencies

- Maintainer decision pass and explicit authority for any download, claim, or
  purchase outside an already agreed free/owned scope.
- Maintainer-provided Chrome control and relevant logged-in sessions for the
  Phase 1 marketplace review.
- Official provider documentation and actual account/library behavior.
- The cloud project's `AGENTS.md`, `README.md`, `INDEX.md`, and asset-area
  guidance.
- Initial-bringup implementation for eventual `charctx` commands and managed
  Blender; Phase 1 documentation can proceed before that code exists.
- Blender 5.2.1 (or an explicitly revised pin) for pilot rig-presence checks.

## Risks And Mitigations

- **Catalog API mistaken for download API:** record capabilities operation by
  operation, including entitlement and file delivery.
- **Marketplace UI/API drift:** date every finding; prefer official supported
  interfaces and keep manual fallback explicit.
- **Terms or anti-automation restrictions:** do not bypass controls or use
  undocumented endpoints; mark the source manual or unsuitable.
- **Ambiguous asset license:** place the candidate on hold; do not infer rights
  from “free,” “purchased,” or “downloadable.”
- **Training-rights confusion:** this is an engineering reference corpus, not
  an ML dataset; record AI/training status separately and default unknown to
  not allowed.
- **Marketing says “rigged” but files disagree:** verify armature and weights
  after acquisition before selection.
- **Duplicate or mirrored listings:** combine provider ids, canonical URLs,
  hashes, creator identity, and manual relationship links.
- **Partial downloads/cloud-sync races:** use transient staging, verify archive
  completeness and hashes, then promote atomically; never edit vendor originals.
- **Credential or payment leakage:** keep secrets in environment/browser
  state and payment data out of records, logs, screenshots, and Git.
- **Over-collection:** three-asset pilot, 10-donor target, 15 cap, and a named
  diversity gap required for every item after 10.
- **Premature adapter maintenance:** productize only supported repeated
  surfaces; the local intake contract carries most of the durable value.

## Exit Criteria

- OP-001…OP-010 are accepted or explicitly amended, with the summary and
  detailed sections matching.
- The initial source roster has a dated evidence matrix covering every field
  in the discovery contract and a justified access method per source.
- Fab's actual official API/auth/catalog/library/download capabilities are
  recorded without conflating public catalog access with entitled delivery.
- The accepted folder, metadata, rights, identity, revision, and lifecycle
  contracts are folded into a durable repository specification and matching
  cloud-workspace guidance.
- At most three pilot packages prove end-to-end acquisition, provenance,
  hashing, cloud intake, and minimal Blender rig inspection.
- The final corpus contains 10 selected donors, or fewer only with a recorded
  availability/rights blocker; it never exceeds 15 in this packet.
- Every selected donor satisfies the hard anatomy/rig/format/provenance gates,
  has original bytes preserved, and has a reproducible inspection record.
- Every automated behavior is reachable through a documented CLI command;
  every manual/browser step is documented as such.
- No marketplace asset, credential, session material, or payment detail is in
  Git, `.cache/` is not treated as durable storage, and no prior acquisition
  was overwritten.
- Runtime commands, fixtures, expected/actual results, and remaining source
  gaps are recorded in `test.md` when implementation begins.

## First Working Session Readiness

When the maintainer is ready to provide Chrome control, the next action is
Phase 0 review followed by a **read-only Fab walkthrough**. That walkthrough
will answer the discovery-contract questions and locate official API/auth
documentation if exposed. It will not download or purchase a dragon. The
result will be a concrete recommendation for Fab before repeating the same
loop for the other accepted sources.
