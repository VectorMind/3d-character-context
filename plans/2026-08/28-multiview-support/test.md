# Test — Multiview Generator Support

## Documentation Proof

| Check | Expected | Actual |
| --- | --- | --- |
| Packet structure | `plan.md`, `implementation.md`, and `test.md` exist | pass |
| Current capability | Implemented `trellis2` and `charctx generate` are labelled monoview | pass |
| Future status | Multiview is linked as parked future work, not presented as implemented | pass |
| Candidate coverage | Free HF, managed TRELLIS, Hunyuan3D-2mv, Meshy, Tripo, Rodin discovery, TRELLIS.2 patch, and non-solutions are explicit | pass |
| Decision integrity | Backend choice, view semantics, and CLI shape remain open | pass |

## Provider Surface Evidence

No-generation API-description probes were used; they spend no hosted GPU
quota and create no mesh artifact.

| Provider surface | Expected / actual result |
| --- | --- |
| `microsoft/TRELLIS.2` | singular `/image_to_3d(image, …)` — confirmed |
| `trellis-community/TRELLIS` | `/preprocess_images(images)` and `/generate_and_extract_glb(..., multiimages, ..., multiimage_algo, ...)` — confirmed |
| `tencent/Hunyuan3D-2mv` | `/shape_generation` and `/generation_all` accept front/back/left/right images — confirmed |
| `microsoft/TRELLIS` | unavailable with `CONFIG_ERROR` — confirmed |

The original 2026-08-25 report remains at
`.cache/results/2026-08-25/220907-trellis-hello-world/` and proves that the
community TRELLIS multi-image parameters were visible during initial backend
selection even though the generation call used an empty `multiimages` list.

## Runtime Proof

No multiview runtime behavior is claimed. When the packet is activated, record
offline tests and quota-bearing live comparisons here using the evaluation
matrix in `plan.md`.

## Repository Checks

| Command | Expected | Actual |
| --- | --- | --- |
| `uv run pytest` | Offline suite passes; live provider test remains gated | **83 passed, 1 skipped** in 1.64 s |
| `uv run ruff check .` | No lint errors | **All checks passed** |

## Known Gaps

- No multiview backend or documented multiview command exists.
- No provider has received two or more project images through `charctx`.
- No comparative anatomy or image-consistency evaluation has been performed.
- Commercial terms, costs, retention, and current quality remain unproven.
- Unsupported plural Python requests to `trellis2` are not yet rejected.
