# Plan: Multiview Generator Support

Date: 2026-08-28  
Status: Parked future work — current generation remains monoview through
`microsoft/TRELLIS.2`; no multiview backend is selected or implemented.

## Problem Summary

The product direction calls for controlled views of one character to condition
one 3D generation, but the implemented `trellis2` backend and documented
`charctx generate <image>` command accept one conditioning image. The shared
`GenerationRequest.images` field is plural for future backend compatibility;
it does not make the current backend multiview-capable.

The initial provider experiment actually observed a multiview API on original
TRELLIS (`multiimages` plus `multiimage_algo`), but backend selection compared
the candidates primarily on access, latency, and measured mesh density. It did
not make two-or-more-view conditioning an exit criterion. This packet preserves
that gap and the candidate set without silently selecting a replacement.

## Resolution Summary

| OP | Topic | Proposal / accepted resolution | Confidence | Status |
| --- | --- | --- | --- | --- |
| OP-001 | Current capability label | Describe `trellis2` and `charctx generate` as **monoview** everywhere; plural request storage is not a capability claim | high | **accepted 2026-08-28** |
| OP-002 | Product direction | Add genuine multiview conditioning as a future backend capability while retaining TRELLIS.2 as a valid single-image baseline | high | **accepted 2026-08-28** |
| OP-003 | First multiview backend | Prove original TRELLIS multiview on the free community Space, then compare it with at least one maintained paid API before selecting a production backend | medium | proposed; parked |
| OP-004 | View semantics | Represent named roles where the provider uses them (`front`, `left`, `back`, `right`) and an ordered gallery where it does not; do not flatten both into undocumented list order | medium | open |
| OP-005 | EU licensing | Do not select Hunyuan3D-2mv for an EU-based workflow unless suitable rights are established; its published community license excludes the EU | high | **accepted constraint** |
| OP-006 | Selection evidence | Compare anatomical/view fidelity and failure rate, not vertex count alone; mesh measurement remains the artifact validity gate | high | **accepted 2026-08-28** |
| OP-007 | TRELLIS.2 community patch | Treat the unmerged multi-image PR as an experiment requiring owned hosting and validation, not as current official support | high | **accepted 2026-08-28** |
| OP-008 | CLI shape | Choose between repeated `--image`, named view flags, or a view-set manifest only after OP-003/OP-004 establish the first real backend contract | medium | open |

## Goal And Objectives

- Provide genuine conditioning from two or more views of the same character.
- Preserve the generator boundary: provider-native request and response shapes
  remain inside backend modules.
- Keep the implemented TRELLIS.2 path available for single-image comparisons.
- Make input cardinality and view-role requirements explicit in CLI help,
  request metadata, validation, and backend descriptions.
- Select a backend using controlled quality evidence on the western-dragon
  target rather than model age, nominal polygon count, or screenshots alone.

## Current Baseline

- `charctx generate <image>` accepts one positional image.
- `trellis2` submits only that image to the singular `/image_to_3d` parameter
  on `microsoft/TRELLIS.2`.
- The official TRELLIS.2 model card declares `Input: Single Image`, and the
  official pipeline exposes `run(image=...)` rather than a multi-image run.
- `GenerationRequest.images` is plural, but direct Python callers must pass
  exactly one image to `trellis2`; extra paths are not additional conditioning.
- No multiview generation result has been produced or evaluated in this
  repository.

## Candidate Options

Availability and API shapes are volatile. Re-run the standing/no-cost probes
before implementation and record the exact API description used by a backend.

### A. Original TRELLIS — community Hugging Face Space

- Endpoint: `trellis-community/TRELLIS` →
  `/generate_and_extract_glb`.
- Genuine multiview inputs: a `multiimages` gallery plus `multiimage_algo`
  (`stochastic` or `multidiffusion`). The 2026-08-25 experiment recorded both,
  and a no-generation API probe confirmed them again on 2026-08-28.
- Advantages: free proof path, already understood Gradio integration, arbitrary
  view gallery, MIT-licensed upstream model, smallest new HF backend.
- Risks: public-Space volatility and shared ZeroGPU quota; older model and the
  probed default export measured much lower mesh density than TRELLIS.2.
- Fit: leading candidate for the first no-cost multiview proof, not yet the
  production recommendation.

Sources: [official multi-image pipeline](https://github.com/microsoft/TRELLIS/blob/main/trellis/pipelines/trellis_image_to_3d.py),
[community Space](https://huggingface.co/spaces/trellis-community/TRELLIS).

### B. Original TRELLIS — fal.ai managed endpoint

- Endpoint: `fal-ai/trellis/multi` with `image_urls` and the same two
  multi-image algorithms.
- Advantages: explicit queue/result API, managed file upload, commercial-use
  offering, no dependence on a public Space session or ZeroGPU allowance.
- Risks: paid calls, provider credential and retention/privacy review, and the
  same underlying original-TRELLIS quality ceiling.
- Fit: lowest-friction managed alternative to candidate A and a strong
  reliability candidate if original TRELLIS quality is sufficient.

Source: [fal.ai TRELLIS multi API](https://fal.ai/models/fal-ai/trellis/multi/api).

### C. Official Microsoft TRELLIS Space / owned original-TRELLIS Space

- The official `microsoft/TRELLIS` code supports multi-image conditioning, but
  the public Space was still in `CONFIG_ERROR` on 2026-08-28.
- Duplicating original TRELLIS into an owned Space would preserve its API while
  controlling runtime and queue behavior.
- Advantages: known open implementation and controllable hosting.
- Risks: GPU hosting cost and operational ownership; duplicating a Space does
  not improve model quality.
- Fit: fallback deployment mechanism, not a distinct model-quality candidate.

### D. Hunyuan3D-2mv

- Purpose-built 1–4-view image-to-shape model. The public
  `tencent/Hunyuan3D-2mv` Space exposed `front`, `back`, `left`, and `right`
  image parameters in a no-generation probe on 2026-08-28.
- Advantages: explicit directional semantics and a dedicated multiview model;
  open implementation and a public ZeroGPU demo.
- Blocking risk: the published Tencent Hunyuan 3D 2.0 Community License defines
  its territory as excluding the European Union, United Kingdom, and South
  Korea. This workspace is operated from the EU. Do not use the model or its
  outputs unless suitable rights are established.
- Fit: technically relevant comparison, currently ineligible for selection.

Sources: [Hunyuan3D-2 repository](https://github.com/Tencent-Hunyuan/Hunyuan3D-2),
[license](https://github.com/Tencent-Hunyuan/Hunyuan3D-2/blob/main/LICENSE).

### E. Meshy Multi-Image to 3D

- Dedicated task API accepting one to four images; current models also support
  separate multi-view texture guidance.
- Advantages: maintained commercial API, managed generation/remesh/texture
  stages, flexible non-directional secondary views.
- Risks: paid and nondeterministic; account, rights, retention, output terms,
  costs, and quality on non-humanoid winged characters require live review.
- Fit: leading commercial bakeoff candidate.

Source: [Meshy Multi-Image to 3D API](https://docs.meshy.ai/en/api/multi-image-to-3d).

### F. Tripo multiview-to-model

- Dedicated endpoint accepting two to four views. The front is required and
  left/back/right have explicit roles.
- Advantages: maintained commercial API with clear camera-role semantics.
- Risks: paid; the standard directional slots do not directly consume top or
  three-quarter views; account and output terms and western-dragon quality need
  live review.
- Fit: leading commercial bakeoff candidate when canonical directional views
  are available.

Source: [Tripo multiview-to-model API](https://developers.tripo3d.ai/en/docs/generation-multiview-to-model/standard).

### G. Rodin / Hyper3D and other commercial generators

- The existing project documentation lists Rodin with task-based commercial
  generators, but no current, authoritative multiview request contract has
  been proven for this workspace.
- Advantages: possible high-quality production-oriented outputs and bundled
  processing.
- Risks: capability, limits, pricing, terms, and API access are unverified.
- Fit: discovery candidate only; it cannot enter a bakeoff as “multiview” until
  a standing probe proves a real multi-image endpoint.

### H. Unmerged TRELLIS.2 multi-image patch / owned fork

- An open upstream pull request adds sampler-injected `stochastic` and
  `multidiffusion` multi-image conditioning to TRELLIS.2.
- Advantages: potential combination of TRELLIS.2's higher-fidelity O-Voxel/PBR
  output with multiple input views.
- Risks: unmerged community code, no official weights/API guarantee for this
  use, owned GPU hosting, and no project evidence that the patch improves
  geometry or remains stable.
- Fit: research branch after a supported backend establishes a baseline.

Source: [TRELLIS.2 multi-image PR #104](https://github.com/microsoft/TRELLIS.2/pull/104).

### I. Non-solutions kept explicit

- A contact sheet or collage sent to TRELLIS.2 is still one image presented to
  a model trained for one object image; it is not genuine view fusion.
- Running TRELLIS.2 separately for each view produces several unrelated meshes,
  not one jointly conditioned mesh.
- Photogrammetry is a different reconstruction path requiring geometrically
  consistent photographs and camera overlap; the AI-synthesized turnaround
  images are not measurement evidence.

These may be useful experiments under another goal, but none may be labelled
multiview generator support.

## Scope

- Refresh provider API, runtime, quota, licensing, and input-limit facts.
- Define explicit input-cardinality and view-role contracts.
- Add one multiview backend and a documented CLI route.
- Preserve every source view and resolved provider request in the append-only
  run slot.
- Add offline contract tests and quota-gated live proof.
- Compare at least two materially different access/model options before
  selecting a production default.

## Non-Goals

- Removing or pretending to upgrade the existing TRELLIS.2 backend.
- Treating a collage as multiview conditioning.
- Spending hosted quota while this packet remains parked.
- Selecting a provider without reviewing current terms and data handling.
- Claiming canonical topology, rigging, deformation, or production readiness
  from a raw generator result.

## Implementation Phases

1. **Refresh and fixtures.** Re-probe candidate APIs without generation where
   possible; capture exact endpoint descriptions, runtime state, limits, and
   licensing evidence.
2. **Contract and CLI design.** Resolve OP-004/OP-008; define cardinality,
   named views, ordering, validation, metadata, and failure behavior without
   provider-native leakage.
3. **First backend.** Implement the selected proof backend with append-only
   artifact handling and complete README command documentation.
4. **Offline and live proof.** Add recorded API fixtures, unit tests, and a
   quota-gated run using a controlled western-dragon view set.
5. **Bakeoff and decision.** Compare a second provider, record anatomical and
   operational evidence, select or reject a production default, and fold the
   settled contract into the durable spec.

## Evaluation Matrix

Every live candidate uses the same permitted subset of one coherent view set
and records:

- input roles, count, dimensions, hashes, preprocessing, and provider limits;
- presence and approximate placement of four legs, two wings, head/neck, and
  one tail;
- front/side/rear/top silhouette agreement where the API accepts those roles;
- bilateral consistency, occluded-side invention, texture/PBR consistency,
  and obvious duplicated or missing anatomy;
- latency, queue failures, quota/cost, reproducibility metadata, output terms,
  and artifact retention behavior;
- reloaded mesh measurements required by the mesh-report specification.

Vertex/face count is an output fact, not a quality score.

## Dependencies And Risks

- Public Spaces and commercial APIs can change without notice.
- Multi-view references must depict the same design and pose; contradictory
  views can reduce rather than improve fidelity.
- The existing Riyu set has front, left, rear, top, and front-three-quarter
  views but no right view. Directional four-slot APIs and free-form galleries
  therefore consume different subsets.
- Provider terms and geographic restrictions can eliminate an otherwise good
  technical candidate.
- Live comparisons consume quota or money and must be explicitly activated.

## Exit Criteria

- Current monoview and future multiview capabilities are distinct in the CLI,
  README, backend descriptions, and request metadata.
- Passing an unsupported image count fails clearly; no backend silently ignores
  extra conditioning images.
- One documented CLI run submits at least two views to a provider endpoint that
  genuinely fuses them and lands one measured mesh in a fresh run slot.
- All submitted views and their roles/hashes are preserved with the request.
- At least one competing provider/access path is evaluated on the same view set
  before the production default is selected.
- `uv run pytest` and `uv run ruff check .` pass, with commands and live gaps
  recorded in `test.md`.
