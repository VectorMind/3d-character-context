# Specification: Generator Backend Contract

## Purpose

The hosted generative 3D model is replaceable infrastructure. This
specification fixes the boundary that makes it replaceable, and records what
the alternatives offer so a switch is a decision rather than an
investigation.

## The Boundary

A backend is a module exposing one function:

```python
generate(request: GenerationRequest, project: Project, *, on_event=None)
    -> RawCharacterResult
```

Only `GenerationRequest` and `RawCharacterResult` cross the boundary.
Provider-native material - Gradio payloads, REST job envelopes, temporary
provider file paths, provider error types - stays inside the backend module.
A provider failure is re-raised as a backend error; a quota refusal is raised
as a distinct error type carrying the provider's own message.

`GenerationRequest` carries reference images, a run name, a seed, an optional
prompt, and a free-form `options` mapping. Backend-specific knobs belong in
`options`; they never become new top-level fields, because every backend has
a different set.

### No Premature Abstraction

There is no backend protocol class and no registry. Real image-to-3d APIs
differ in staging - one call, a session-stateful sequence, or submit-and-poll
- in their options, and in what they return. The shared contract is the two
models, not a machinery layer. An abstraction over backends is justified only
by two backends that actually exist in code.

Configured backends and documented alternatives are kept visibly distinct: a
backend key with no implementation behind it fails with a message saying so,
never with a silent fallback.

## Configuration

`config/providers.yaml` declares, per backend: provider kind, endpoint or
Space id, the name of the environment variable holding its credential, the
call shape, its endpoint names, default options, and known quota behavior. It
declares no credential value.

A backend sends every parameter an endpoint declares, taking defaults from
the provider's own API description rather than hardcoding them. Partial
parameter lists are not sent: providers reject them, sometimes opaquely, and
hardcoded defaults silently diverge from the provider's.

A provider that no longer exposes a configured endpoint produces an error
naming the missing endpoint and the endpoints that now exist.

## Hosted Access Facts

Hugging Face's serverless inference API serves **no** `image-to-3d` model. A
Gradio Space is therefore the only free Hugging Face path to these models,
and the escalation path from a public Space is duplicating the Space into an
owned account or a dedicated (paid) inference endpoint - there is no cheaper
serverless fallback.

Public Spaces are volatile: a Space's runtime stage, API shape, and
availability change without notice, and the most popular Space for a model is
not necessarily the running one. Space identity and call shape are therefore
configuration, never constants in code.

Spaces on shared ZeroGPU hardware reserve a fixed slice of a small daily
budget **per call, up front**, regardless of how long the call runs. The
budget is shared across every ZeroGPU Space an account touches and resets on a
rolling 24-hour timer. This is why generation output is append-only: a
discarded result costs a substantial fraction of a day's capacity.

## Implemented Backend

`trellis2` - Microsoft TRELLIS.2 through the `microsoft/TRELLIS.2` Space.
Session-stateful: a session is started, the reference image is preprocessed,
`/image_to_3d` generates into the session, and `/extract_glb` pulls the mesh
out of it. All four calls share one client. Credential: `HF_TOKEN`.

## Documented Alternatives

No code exists for these. Each entry records what it offers and how it would
be integrated.

| Alternative | Shape | What it offers | Integration |
| --- | --- | --- | --- |
| `trellis-community/TRELLIS` Space | Single call `/generate_and_extract_glb` | Original TRELLIS; roughly a third of the time and a far simpler contract, at roughly a twentieth of the vertex density | New backend module, single-call shape; same credential |
| `tencent/Hunyuan3D-2.1` Space | Two stages | Shape generation then texture paint, each with its own options (background removal, steps, guidance, octree resolution, target face count) | New backend module modelling both stages internally; same credential |
| fal.ai serverless endpoints | REST, submit + poll | Hosted TRELLIS/Hunyuan variants without Space queues; paid | New backend module plus a provider credential |
| Meshy, Tripo, Rodin | REST, task-based | Create task with image and options (topology, target polycount, PBR, sometimes rigging), poll a job id, download from result URLs in several formats | New backend module per provider, each with its own credential and job polling |
| Duplicated Space in an owned account | Same as the Space it copies | Insulation from upstream churn, a private queue, optionally better hardware | Configuration change only |
| Dedicated inference endpoint | REST | Reliable and private, paid GPU-hours | New provider kind plus a credential |

## Staged Geometry Libraries

The mesh stack is `numpy` and `trimesh`, with `networkx` and `scipy` as
mandatory graph engines. The following are documented and uninstalled; each
is installed as a mandatory part of the main flow when a stage needs it, never
as an optional extra with a degraded fallback:

| Library | Role when its stage arrives |
| --- | --- |
| Open3D | Rigid registration and ICP for coarse alignment |
| PyTorch + PyTorch3D | Non-rigid fitting to canonical topology (Windows wheel availability is the known hazard) |
| PyMeshLab | Mesh repair and processing |
| libigl | Geometry-processing alternative for fitting and parameterization |

## Acceptance Criteria

- A backend module returns `RawCharacterResult` and nothing provider-shaped.
- Every declared endpoint parameter is sent on every call.
- A quota refusal is distinguishable from every other failure and preserves
  the provider's message.
- Backend behavior is testable offline against a recorded API description,
  with no network call and no quota spent.
- Selecting a documented alternative as if it were implemented fails with a
  message that lists the implemented backends.

## Non-Goals

- Self-hosting generative models on local or rented GPUs.
- A backend protocol, registry, or plugin system.
- Normalizing quality, style, or topology differences between backends: that
  is the canonical layer's work, not the boundary's.
