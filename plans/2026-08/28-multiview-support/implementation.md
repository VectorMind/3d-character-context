# Implementation — Multiview Generator Support

## Progress

`□□□□□ Parked before Phase 1/5`
Current monoview status is documented; provider implementation and live proof come next when activated.

## Documentation Baseline — 2026-08-28

- Opened a separate future-work packet rather than expanding the completed
  initial-bringup packet.
- Recorded the complete candidate set and kept backend selection, view
  semantics, and CLI shape as explicit open points.
- Updated the generator-backend specification, operational guidance, root
  README, specification index, experiment README, and provider descriptions to
  label the implemented TRELLIS.2 path as monoview.
- Preserved `GenerationRequest.images` as a future-facing shared shape while
  documenting that it does not promise multi-image support from `trellis2`.
- Recorded contact sheets and per-view independent generations as non-solutions
  rather than compatibility workarounds.

## Discovery Evidence Carried Into The Packet

- The 2026-08-25 standing probe recorded original TRELLIS parameters
  `multiimages`, `multiimage_algo`, and `/preprocess_images` but exercised only
  one image.
- No-generation `gradio_client.view_api()` probes on 2026-08-28 confirmed:
  - `microsoft/TRELLIS.2` still has one singular `image` input;
  - `trellis-community/TRELLIS` exposes a multi-image gallery and two fusion
    algorithms;
  - `tencent/Hunyuan3D-2mv` exposes front/back/left/right inputs;
  - `microsoft/TRELLIS` remains in `CONFIG_ERROR`.
- No provider generation was run and no GPU quota or commercial credit was
  spent for this documentation pass.

## Deferred Implementation

- No backend, CLI, request-validation, config-schema, or test-fixture behavior
  changed in this pass.
- In particular, direct Python callers can still construct a plural
  `GenerationRequest` for `trellis2`; the future implementation must reject
  unsupported cardinality rather than silently use only the first image.

## Commands Performed

- `gradio_client.Client(...).view_api()` against the four recorded Hugging
  Face Spaces; API-description only, no generation.
- `uv run pytest` → 83 passed, 1 live test skipped.
- `uv run ruff check .` → all checks passed.
