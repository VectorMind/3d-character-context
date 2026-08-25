# Dragon 3D Generation Repository Handoff

## Purpose

Create a new repository for a **generative-first 3D dragon pipeline**.

The system should:

1. Generate a novel dragon mesh from reference images or multiview inputs using a hosted cutting-edge 3D generative model.
2. Treat the generated mesh as arbitrary/untrusted topology.
3. Transform that result into a **known canonical dragon topology**.
4. Fit a **known dragon skeleton** to the canonicalized mesh.
5. Export a predictable production asset such as GLB/FBX.
6. Keep the generative backend swappable so new 3D models/providers can be adopted without rewriting the canonicalization pipeline.

The initial target is **one body plan only**:

> Western quadruped dragon: four legs, two wings, one neck/head, one tail.

Do not attempt to support wyverns, eastern serpentine dragons, hydras, drakes, or other substantially different skeleton/topology families in the first version.

---

# Core Design Principle

The most important architectural decision is to separate:

```text
GENERATIVE 3D
    ↓
arbitrary mesh

from

CANONICALIZATION
    ↓
known topology
    ↓
known skeleton
```

The generative model should be considered replaceable infrastructure.

The valuable long-term layer is:

```text
ANY SUPPORTED GENERATED WESTERN DRAGON
                    ↓
         anatomical interpretation
                    ↓
       canonical dragon topology
                    ↓
        canonical dragon skeleton
                    ↓
      predictable production asset
```

This is analogous to a CAD generator registry, except the generator output is initially non-deterministic and must be normalized before downstream use.

---

# Recommended End-to-End Workflow

```text
concept / character reference
             ↓
     controlled image views
             ↓
 front / 3⁄4 / side / back
             ↓
 hosted generative 3D model
             ↓
       raw generated mesh
             ↓
      mesh preprocessing
             ↓
 anatomy / landmarks estimation
             ↓
 coarse canonical cage fitting
             ↓
 non-rigid template deformation
             ↓
   canonical dragon topology
             ↓
     canonical skeleton fit
             ↓
        skin weight transfer
             ↓
 deformation / rig validation
             ↓
          GLB / FBX
```

The first prototype should prefer **image-to-3D or multiview-to-3D** over direct text-to-3D.

Text prompts can be used upstream to create coherent concept views, but the 3D generation stage should receive explicit visual conditioning whenever possible.

---

# Generative 3D Backends

## Preferred first backend: TRELLIS.2

Use TRELLIS.2 as the first experimental generator.

Why:

- modern image-to-3D architecture;
- genuinely synthesizes new geometry rather than selecting a pre-existing parametric dragon;
- uses a structured learned 3D representation rather than directly predicting arbitrary triangle lists;
- returns exportable mesh assets;
- available through hosted inference providers, so local GPU hosting is not required;
- can later be specialized with LoRA-style adaptation where hosting providers support it.

Conceptual pipeline:

```text
reference image(s)
      ↓
vision conditioning
      ↓
generative transformer
      ↓
structured latent 3D representation
      ↓
O-Voxel / geometry representation
      ↓
mesh
      ↓
materials / PBR export
```

TRELLIS.2 should be treated as a **replaceable generator backend**, not a hard dependency of the repository architecture.

---

## Secondary backend: Hunyuan3D

Support Hunyuan3D after the first TRELLIS integration.

Relevant variants discussed:

- Hunyuan3D 2.1
- newer Hunyuan3D hosted endpoints where available

Typical architecture:

```text
reference image
      ↓
shape generator
      ↓
untextured mesh
      ↓
paint / PBR model
      ↓
textured mesh
```

This is also genuine shape generation rather than a fixed-base character morph system.

---

## Commercial comparison backends

Later compare against:

- Tripo
- Meshy
- Rodin / Hyper3D

These services are useful not merely because of model inference, but because they increasingly bundle:

- image preprocessing;
- background removal;
- multiview conditioning;
- geometry generation;
- remeshing / topology cleanup;
- part segmentation;
- UV creation;
- PBR texturing;
- low-poly conversion;
- rigging;
- animation;
- file conversion;
- hosted GPU infrastructure;
- queueing and retries.

For this project, commercial APIs are useful as **quality baselines** and potentially as production backends, but they should not define the canonical internal representation.

---

# Hosting Strategy

Do not self-host the heavy 3D generator in the first implementation.

Preferred architecture:

```text
local Python repository
        ↓ HTTPS
hosted 3D inference provider
        ↓
GLB / mesh result
        ↓
local canonicalization pipeline
```

Candidate hosting approaches:

## Serverless model providers

Example:

- fal.ai

Advantages:

- GPU infrastructure is managed externally;
- simple HTTP/API integration;
- easy experimentation with large current models;
- better suited than manually maintaining CUDA/model serving for early work;
- can expose new models faster than building local infrastructure.

## Hugging Face

Use Hugging Face primarily for:

- model discovery;
- inspecting open weights;
- testing official Spaces;
- experimenting with cutting-edge models;
- potentially calling Spaces programmatically for prototypes.

For a stable batch production system, a dedicated inference provider may be preferable to relying on an interactive Space.

The repository must therefore abstract generator hosting.

Example interface:

```python
class GeneratorBackend(Protocol):
    def generate(self, request: GenerationRequest) -> RawCharacterResult:
        ...
```

Possible implementations:

```text
TrellisFalBackend
HunyuanFalBackend
HuggingFaceSpaceBackend
TripoBackend
MeshyBackend
RodinBackend
```

---

# Important Model Terminology

Do not describe the target systems simply as "3D VAE LLMs".

A more accurate description is:

> 3D generative models using learned latent representations, often combining sparse/structured 3D VAEs with diffusion, flow-matching, or transformer-based generators.

The VAE or equivalent component serves as a compact geometry representation or codec.

The generative model predicts samples in that latent/structured space.

The output is then decoded into geometry.

Typical family:

```text
image / multiview
      ↓
vision encoder
      ↓
latent generator
      ↓
3D latent / sparse geometry representation
      ↓
geometry decoder
      ↓
mesh
```

Successful systems tend to avoid generating raw arbitrary triangle arrays directly.

Common intermediate representations across modern 3D generation research include:

- SDFs;
- occupancy fields;
- sparse voxels;
- structured voxels;
- triplanes;
- point-based latent sets;
- sparse latent grids;
- implicit fields.

---

# Why Generative Output Must Be Canonicalized

Raw 3D generation is excellent for novelty but poor for stable downstream character workflows.

Two independently generated dragons may have:

```text
different vertex counts
different edge flow
different topology
different wing segmentation
different tail segmentation
different mouth topology
different connected components
```

Therefore this is unsuitable as-is for:

- consistent rigging;
- shared animations;
- semantic morphing;
- interpolation between characters;
- reusable deformation logic;
- predictable game/animation pipelines.

The generative mesh is therefore a **source surface**, not the final production topology.

---

# Canonical Dragon Representation

Create one hand-authored canonical western-dragon asset.

Recommended asset:

```text
assets/
  western_dragon_v1/
    canonical_dragon.blend
    canonical_dragon.glb
    skeleton.json
    landmarks.json
    regions.json
```

The canonical mesh should have:

- known vertex count;
- stable vertex ordering;
- stable edge loops;
- named semantic regions;
- known UV layout;
- known skeleton;
- known vertex groups / skin weights;
- clean wing membrane topology;
- clean jaw / mouth topology;
- sufficient loops around shoulders, hips, wing joints, neck, jaw, and tail.

Semantic regions should include at minimum:

```text
head
jaw
neck
chest
pelvis
tail
front_leg.L
front_leg.R
back_leg.L
back_leg.R
wing.L
wing.R
wing_membrane.L
wing_membrane.R
```

---

# Landmark System

Canonicalization should initially rely on explicit anatomical landmarks rather than trying to solve fully semantic 3D understanding from scratch.

Potential landmarks:

```text
nose_tip
jaw_tip
head_center
neck_base
chest_center
pelvis_center

shoulder.L
shoulder.R
elbow_front.L
elbow_front.R
wrist_front.L
wrist_front.R
front_foot.L
front_foot.R

hip.L
hip.R
knee.L
knee.R
ankle.L
ankle.R
back_foot.L
back_foot.R

wing_root.L
wing_root.R
wing_elbow.L
wing_elbow.R
wing_wrist.L
wing_wrist.R
wing_tip.L
wing_tip.R

tail_base
tail_mid
tail_tip
```

Start with manually authored or semi-manually extracted landmarks during prototyping if required.

Automated landmark inference can be improved later.

---

# Canonicalization Strategy

Do **not** think of the problem as conventional independent retopology.

The intended operation is:

> deform one known dragon topology so that it matches the generated dragon surface.

Suggested stages:

## Stage 1 — preprocessing

Use Python mesh tools to:

- load the generated GLB/OBJ;
- remove invalid geometry;
- inspect connected components;
- normalize scale;
- normalize coordinate system;
- detect gross orientation;
- repair obvious mesh problems;
- optionally decimate extremely dense meshes;
- sample a clean surface point cloud.

Candidate libraries:

- `trimesh`
- Open3D
- PyMeshLab

---

## Stage 2 — coarse alignment

Fit the canonical dragon to the raw mesh using:

- global scale;
- translation;
- rotation;
- major anatomical landmarks;
- coarse skeleton pose;
- body segment lengths.

Possible techniques:

- landmark least-squares fitting;
- rigid registration;
- ICP for selected regions;
- skeleton-driven deformation;
- cage deformation.

Open3D can help with rigid registration and ICP.

---

## Stage 3 — non-rigid template fitting

Deform the canonical topology toward the generated surface while preserving desirable topology.

Possible loss:

```text
L =
  w_surface     * surface_distance
+ w_landmarks   * landmark_distance
+ w_laplacian   * mesh_smoothness
+ w_edges       * edge_regularization
+ w_normals     * normal_consistency
+ w_symmetry    * bilateral_symmetry
+ w_anatomy     * anatomical_constraints
```

Useful tools:

- PyTorch
- PyTorch3D
- libigl / Python bindings
- custom differentiable optimization

Possible geometry metric:

- Chamfer distance between sampled points;
- point-to-surface distance;
- signed distance where available.

Do not optimize only Chamfer distance. Pure surface fitting can produce anatomically invalid deformations.

---

## Stage 4 — detail projection

After the canonical mesh matches the major form:

- shrinkwrap/project the canonical surface to the source;
- transfer or bake high-frequency detail;
- transfer color/material information;
- generate normal/displacement maps where appropriate.

Blender can be useful here even if it is not the generator.

---

# Skeleton Strategy

Use one known skeleton for western dragons.

The rig should be designed before automating canonicalization.

Suggested hierarchy:

```text
root
└── pelvis
    ├── spine.*
    │   ├── chest
    │   │   ├── neck.*
    │   │   │   ├── head
    │   │   │   └── jaw
    │   │   ├── wing.L.*
    │   │   ├── wing.R.*
    │   │   ├── front_leg.L.*
    │   │   └── front_leg.R.*
    │   └── ...
    ├── back_leg.L.*
    ├── back_leg.R.*
    └── tail.*
```

Wing skeleton should contain explicit:

```text
wing_root
wing_upper
wing_elbow
wing_forearm
wing_wrist
wing_finger_1...
wing_finger_n...
```

because wing membrane deformation is one of the main failure points of generic creature rigs.

---

# Rigging Philosophy

Once the source has been transformed into the canonical topology:

```text
canonical topology
        +
canonical skeleton
        +
canonical skin weights
```

should already exist as a coherent template.

Ideally, rigging new characters becomes primarily:

- adjust bone locations to the fitted anatomy;
- preserve the known hierarchy;
- transfer/recompute skin weights only where needed;
- run deformation validation.

This is much more stable than auto-rigging an arbitrary generated mesh from scratch.

---

# Blender Role

Blender should not be considered the generative AI.

Use Blender as an optional downstream geometry/rigging engine.

Possible roles:

- shrinkwrap;
- shape keys;
- armatures;
- vertex groups;
- skinning;
- weight transfer;
- modifiers;
- Geometry Nodes;
- UV tools;
- texture baking;
- GLTF/FBX export;
- deterministic validation renders.

Python integration options:

```text
bpy via Blender Python runtime
or
headless Blender subprocess
```

The GUI is not required for batch processing.

The repository should keep Blender-specific logic behind a backend/service boundary.

Example:

```python
class BlenderCanonicalizationBackend:
    def shrinkwrap(...):
        ...

    def bind_armature(...):
        ...

    def bake_normal_map(...):
        ...

    def export_glb(...):
        ...
```

---

# Pure-Python Geometry Stack

Recommended initial dependencies:

```text
pydantic
numpy
trimesh
open3d
torch
pytorch3d
```

Optional:

```text
pymeshlab
libigl bindings
scipy
```

Possible Blender integration later:

```text
bpy
```

or a configured external Blender executable.

Do not make Blender mandatory for the earliest raw-mesh inspection and registration experiments.

---

# Suggested Repository Structure

```text
dragon-context/
├── README.md
├── pyproject.toml
├── config/
│   └── generators.yaml
├── assets/
│   └── western_dragon_v1/
│       ├── canonical_dragon.glb
│       ├── canonical_dragon.blend
│       ├── skeleton.json
│       ├── landmarks.json
│       └── regions.json
├── src/
│   └── dragon_context/
│       ├── api.py
│       ├── cli.py
│       ├── params.py
│       ├── types.py
│       ├── registry.py
│       │
│       ├── generators/
│       │   ├── base.py
│       │   ├── trellis.py
│       │   ├── hunyuan.py
│       │   ├── tripo.py
│       │   ├── meshy.py
│       │   └── rodin.py
│       │
│       ├── geometry/
│       │   ├── load.py
│       │   ├── repair.py
│       │   ├── normalize.py
│       │   ├── sampling.py
│       │   └── metrics.py
│       │
│       ├── canonicalization/
│       │   ├── landmarks.py
│       │   ├── registration.py
│       │   ├── coarse_fit.py
│       │   ├── nonrigid_fit.py
│       │   ├── losses.py
│       │   └── detail_transfer.py
│       │
│       ├── rigging/
│       │   ├── skeleton.py
│       │   ├── fit.py
│       │   ├── weights.py
│       │   └── validation.py
│       │
│       ├── blender/
│       │   ├── backend.py
│       │   ├── shrinkwrap.py
│       │   ├── rig.py
│       │   └── export.py
│       │
│       ├── exchange/
│       │   ├── glb.py
│       │   └── fbx.py
│       │
│       └── verify/
│           ├── geometry.py
│           ├── topology.py
│           ├── rig.py
│           └── export.py
└── tests/
```

---

# Core Data Types

Suggested high-level contracts:

```python
class GenerationRequest(BaseModel):
    backend: str
    images: list[str]
    prompt: str | None = None
    seed: int | None = None
    options: dict = {}


class RawCharacterResult(BaseModel):
    backend: str
    artifact_path: str
    metadata: dict


class CanonicalizationResult(BaseModel):
    source_path: str
    canonical_mesh_path: str
    fit_metrics: dict
    warnings: list[str]


class RiggedCharacterResult(BaseModel):
    canonical_mesh_path: str
    skeleton_id: str
    export_paths: dict[str, str]
    validation: dict
```

Backend-native responses should not leak throughout the rest of the application.

---

# Generator Registry

Use a registry similar to the CAD workbench pattern.

Example:

```python
GeneratorSpec(
    id="trellis2-hosted",
    family="generative-3d",
    provider="fal",
    mode="image-to-3d",
    output_formats=("glb",),
)

GeneratorSpec(
    id="hunyuan3d-hosted",
    family="generative-3d",
    provider="fal",
    mode="image-to-3d",
    output_formats=("glb",),
)
```

The rest of the pipeline should operate on normalized mesh artifacts, not provider SDK objects.

---

# Verification

Do not use appearance alone as proof.

## Raw generator checks

```text
✓ artifact downloads successfully
✓ GLB/OBJ can be re-read
✓ non-zero vertex/face count
✓ finite coordinates
✓ bounds are reasonable
✓ connected components reported
```

## Canonical topology checks

```text
✓ expected canonical vertex count
✓ expected canonical face count
✓ canonical vertex ordering preserved
✓ required regions present
✓ no NaN vertices
✓ no degenerate faces
✓ UV layer present
```

## Anatomy checks

```text
✓ head is connected to neck
✓ four legs detected/fitted
✓ two wings detected/fitted
✓ one tail detected/fitted
✓ left/right symmetry within tolerance where expected
```

## Rig checks

```text
✓ all required bones exist
✓ hierarchy matches template
✓ skin weights are valid
✓ no unweighted vertices
✓ weight sums approximately equal 1
✓ expected wing/tail/neck chains exist
```

## Deformation tests

Automate test poses:

```text
jaw open
neck bend
tail curl
front leg lift
back leg crouch
wing half-open
wing fully spread
```

Generate deterministic renders or mesh metrics for these poses.

---

# First Milestone

Do **not** begin by solving the entire pipeline.

The first milestone should be:

```text
reference image
      ↓
TRELLIS.2 hosted generation
      ↓
download GLB
      ↓
load with trimesh
      ↓
normalize and inspect
      ↓
produce JSON mesh report
```

Required output:

```text
raw_dragon.glb
raw_dragon.measurements.json
```

Metrics:

- vertex count;
- face count;
- bounding box;
- connected-component count;
- surface area;
- watertightness;
- sampled point count;
- file size;
- generator backend;
- seed/request metadata.

This proves the hosted generation boundary independently of canonicalization.

---

# Second Milestone

Create or supply:

```text
western_dragon_v1 canonical template
```

Then implement:

```text
raw dragon
    ↓
manual or predefined anatomical landmarks
    ↓
rigid/coarse alignment
    ↓
canonical template roughly matches source
```

Do not yet require perfect surface detail.

Exit criterion:

> canonical mesh with identical topology to the template, broadly aligned to a generated dragon.

---

# Third Milestone

Implement differentiable/non-rigid fitting.

Goal:

```text
canonical mesh
      ↓ optimize
raw generated surface
```

while preserving:

- smoothness;
- topology;
- symmetry;
- proportions;
- anatomical constraints.

Compare several losses and record metrics.

---

# Fourth Milestone

Fit the known dragon skeleton and transfer the known skinning setup.

Run deterministic deformation tests.

Only after this milestone should the asset be considered animation-ready.

---

# Fifth Milestone

Transfer surface appearance:

- base color;
- PBR materials;
- normal/displacement details;
- generated texture information.

This should occur **after** canonical geometry is stable.

---

# Future Direction: Dragon-Specific Generative Adaptation

Once enough successful source dragons exist, investigate adapting the generative model toward the canonicalizer's preferred anatomy.

Potential strategy:

```text
TRELLIS.2
    +
dragon LoRA / fine-tuning
    ↓
more consistently western-quadruped dragon anatomy
    ↓
easier canonicalization
```

This adaptation is intended to improve:

- body-plan consistency;
- wing placement;
- number of limbs;
- tail attachment;
- silhouette;
- style.

It should **not** be relied upon to produce canonical topology.

Canonicalization remains a separate deterministic stage.

---

# Critical Non-Goals for V1

Do not attempt in the first repository iteration:

- training a 3D foundation model from scratch;
- self-hosting large GPU models;
- supporting every dragon archetype;
- fully automatic semantic landmark detection;
- arbitrary creature auto-rigging;
- facial animation;
- production-quality texture transfer;
- automatic clothing/armor systems;
- perfect retopology of arbitrary creatures.

Focus exclusively on proving:

```text
hosted generative dragon
        ↓
known western-dragon topology
        ↓
known western-dragon skeleton
```

---

# Main Technical Risk

The hardest problem is **not generative 3D inference**.

Hosted providers make that comparatively easy.

The hardest problem is robustly mapping:

```text
arbitrary generated dragon geometry
```

onto:

```text
one canonical semantic dragon representation
```

without collapsing anatomy or producing bad deformations.

Therefore repository design effort should prioritize:

1. canonical asset quality;
2. landmark definitions;
3. coarse anatomical registration;
4. non-rigid fitting;
5. rig validation.

The generator backend should remain deliberately replaceable.

---

# Recommended Starting Stack

```text
Python 3.11+
Pydantic
NumPy
trimesh
Open3D
PyTorch
PyTorch3D
HTTP client / provider SDK
```

Optional:

```text
PyMeshLab
libigl
Blender / bpy
```

Preferred first hosted backend:

```text
TRELLIS.2 via hosted inference
```

Secondary comparison:

```text
Hunyuan3D
```

Commercial quality baselines:

```text
Tripo
Meshy
Rodin
```

---

# Product/Research Hypothesis

The project is based on this hypothesis:

> Cutting-edge generative 3D models are already good enough to serve as a source of novel fantasy-character geometry, while canonical topology and skeleton fitting remain the missing deterministic layer required for repeatable character production.

If this proves true, the repository should evolve into a general architecture where:

```text
generator backend
+
character-family canonicalizer
+
known topology
+
known rig
```

are independent modules.

Later:

```python
canonicalizers = {
    "western_dragon": WesternDragonCanonicalizer(),
    "wyvern": WyvernCanonicalizer(),
    "eastern_dragon": EasternDragonCanonicalizer(),
}
```

but only `western_dragon` should exist in V1.

---

# Immediate Repository Bootstrap Tasks

1. Initialize Python package and dependency management.
2. Define `GenerationRequest`, `RawCharacterResult`, `CanonicalizationResult`, and `RiggedCharacterResult`.
3. Define a generator backend protocol.
4. Implement one hosted TRELLIS.2 backend.
5. Download and validate one generated GLB.
6. Add trimesh-based mesh reporting.
7. Establish canonical western-dragon asset conventions.
8. Define landmark and skeleton JSON schemas.
9. Implement coarse registration.
10. Add tests around every artifact boundary.
11. Keep provider-specific code isolated.
12. Document all canonical coordinate, scale, orientation, and naming conventions before implementing non-rigid fitting.

---

# Final Architectural Summary

```text
                DRAGON CONTEXT
                      │
           ┌──────────┴──────────┐
           │                     │
     Generative Layer      Canonical Layer
           │                     │
   TRELLIS / Hunyuan       western_dragon_v1
   Tripo / Meshy / Rodin          │
           │                 fixed topology
           │                 fixed skeleton
           │                     │
           └──────────┬──────────┘
                      ↓
              canonical fitting
                      ↓
                 rig fitting
                      ↓
                verification
                      ↓
                  GLB / FBX
```

The guiding rule:

> **Use generative AI for invention. Use deterministic canonicalization for production.**
