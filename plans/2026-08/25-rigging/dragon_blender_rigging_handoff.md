# Handoff: Blender-First DIY Dragon Rigging and Canonicalization Vision

Date: 2026-08-25  
Repository: `VectorMind/3d-character-context`  
Status: Design handoff for the next repo agent  
Scope: Blender role, rigging terminology, canonical skeleton strategy, donor-asset collection, and how these fit into the existing generative-first pipeline

---

## 1. Why This Handoff Exists

The repository already has the correct top-level architecture:

```text
GENERATIVE 3D
    ↓
arbitrary generated dragon mesh
    ↓
CANONICALIZATION
    ↓
known topology
    ↓
known skeleton
    ↓
production asset
```

The new clarification is that **we should not think of rigging as “AI must invent a dragon skeleton for every generated dragon.”**

Instead, the preferred DIY architecture is:

```text
existing rigged dragon examples
        ↓
study / extract / normalize
        ↓
define ONE canonical western-dragon skeleton
        +
define ONE canonical western-dragon mesh
        +
define ONE canonical skin-weight layout
        ↓
for every generated dragon:
    fit canonical mesh
        ↓
    fit known skeleton
        ↓
    reuse/adapt known weights
        ↓
    validate deformation
```

This is substantially more tractable than generic creature auto-rigging.

The repository should therefore treat:

- **skeleton design** as a mostly one-time canonical-asset problem;
- **skeleton fitting** as the repeated per-character problem;
- **rig-control generation** as Blender automation;
- **arbitrary creature auto-rigging** as out of scope for V1.

---

# 2. Terminology

Use these terms consistently in code, specs, README, and agent discussions.

## Skeleton

A hierarchy of joints/bones describing how the character deforms.

Example conceptual hierarchy:

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
    ├── back_leg.L.*
    ├── back_leg.R.*
    └── tail.*
```

For this project, the important skeleton is primarily the **deform skeleton**.

---

## Armature

Blender's object that contains the skeleton.

The repository may store the canonical skeleton in a Blender-independent format such as JSON, while Blender creates the armature deterministically.

---

## Skin Weights

For each mesh vertex, weights define which bones influence it and by how much.

Conceptually:

```text
vertex_1042:
    wing_upper.L: 0.60
    wing_forearm.L: 0.40
```

A mesh plus skeleton is not enough for useful animation; the skin weights are essential.

---

## Skinning

Binding the mesh to the skeleton using skin weights.

---

## Rig

Use the term **rig** for the larger animation system:

```text
deform skeleton
+
skin weights
+
optional animation controls
+
IK/FK systems
+
constraints
+
drivers
+
controller shapes
```

The V1 production requirement is primarily:

```text
canonical mesh
+
deform skeleton
+
valid skin weights
```

Animator-facing controls can be generated later.

---

## Rigging

The overall process of:

1. creating or selecting the skeleton;
2. fitting it to the anatomy;
3. binding/skinning the mesh;
4. generating or adapting weights;
5. optionally generating animation controls;
6. validating deformation.

---

# 3. Core Architectural Decision

## Do not generate a fresh skeleton for every dragon

The system should **not** solve:

```text
arbitrary dragon
    ↓
invent arbitrary new skeleton
```

Instead solve:

```text
arbitrary generated western dragon
    ↓
fit known canonical western-dragon representation
    ↓
fit known canonical skeleton
```

This matches the repository's existing design principle: the valuable deterministic layer is the canonical representation, not the generator backend.

---

# 4. Blender's Role

Blender is now a **first-class deterministic workspace tool** for the canonicalization and rigging pipeline.

It is not the generative AI model.

Blender should be treated as the programmable geometry, armature, skinning, baking, validation, and export engine.

Preferred execution model remains:

```text
Python workspace
    ↓ subprocess
provisioned Blender binary
    ↓ --background --python script.py
deterministic Blender operation
```

Use the full Blender binary rather than making the repo depend on a `bpy` wheel unless later evidence strongly favors the wheel.

---

# 5. What Blender Can Automate

Blender Python can reliably automate:

- importing FBX / GLB / BLEND assets;
- creating armatures;
- creating and deleting bones;
- setting bone head/tail positions;
- setting hierarchy and parenting;
- assigning bone rolls/orientation;
- posing armatures;
- creating vertex groups;
- assigning skin weights;
- automatic parenting / weight generation;
- copying and remapping weights;
- shrinkwrap and surface projection;
- mesh modifiers;
- UV operations;
- texture baking;
- normal/displacement baking;
- GLB / FBX export;
- deterministic pose tests;
- deterministic validation renders.

Blender therefore removes a large amount of low-level manual 3D-tool work.

---

# 6. What Blender Does NOT Solve Automatically

Blender does not provide the key semantic decisions by itself.

It will not reliably infer:

```text
this point is shoulder.L
this point is hip.R
this is wing_root.L
this is the elbow
this is the jaw pivot
```

Therefore the difficult repeated problem is still:

> semantic anatomical interpretation of an arbitrary generated western dragon.

That layer feeds Blender with concrete joint / landmark positions.

---

# 7. Rigify: Useful, But Not the Canonical Skeleton Itself

Blender Rigify should be treated as a **control-rig generator**, not as our semantic representation.

Potential use:

```text
our canonical deform skeleton / metarig
        ↓
fit bone positions to dragon
        ↓
Rigify generates animator-friendly controls
```

Rigify already has useful quadruped and modular limb/spine/tail concepts, but there is no assumption that an existing stock metarig exactly matches a western quadruped dragon with two wings.

Potential strategy:

1. build a custom dragon metarig once;
2. reuse that metarig for every canonical dragon;
3. fit the deform bones programmatically;
4. optionally invoke Rigify to generate controls.

The repository must remain valid even if Rigify is not used for the first production export.

---

# 8. The New Important Input: A Donor Corpus of Rigged Dragons

We should explicitly collect a small library of existing rigged western dragons.

This is not primarily a generative training dataset.

It is an **engineering reference corpus** used to design and validate:

- canonical skeleton hierarchy;
- typical joint positions;
- bone orientations;
- wing-bone structure;
- neck/tail subdivision;
- jaw articulation;
- skin-weight patterns;
- useful rest poses;
- deformation tests.

Start small.

Recommended first target:

```text
5–10 high-quality rigged western dragons
```

Only expand toward 20–30 if the first collection shows meaningful structural diversity.

---

# 9. Donor Selection Criteria

Prefer assets that satisfy:

```text
✓ four legs
✓ two wings
✓ one neck/head
✓ one tail
✓ clearly rigged
✓ deform skeleton available
✓ skin weights available
✓ neutral/rest pose inspectable
```

Strongly prefer assets that also contain:

```text
✓ jaw articulation
✓ wing folding
✓ walk / run
✓ takeoff
✓ flight
✓ landing
✓ neck movement
✓ tail motion
```

Animations are useful because they reveal whether the donor skeleton actually deforms well.

---

# 10. Preferred Source Formats

## Acquisition order

Prefer:

```text
1. BLEND
2. FBX
3. GLB / glTF
```

Avoid relying on OBJ/STL for donor rigs.

### BLEND

Best donor source when available because it may preserve:

- mesh;
- armature;
- weights;
- materials;
- animation actions;
- constraints;
- custom properties;
- control rig;
- drivers.

### FBX

Excellent rig interchange format.

Usually preserves:

- mesh;
- skeleton;
- skinning;
- animations;
- materials to a useful degree.

### GLB / glTF

Excellent normalized interchange format.

Useful for:

- mesh;
- PBR;
- skin;
- skeleton;
- animation.

However it generally does not preserve authoring-tool-specific control-rig logic.

### OBJ / STL

Do not use for skeleton donors.

They do not carry the rigging information we care about.

---

# 11. Candidate Asset Sources

Useful sources to investigate and document include:

- Fab;
- CGTrader;
- TurboSquid;
- Sketchfab;
- other legal asset libraries with downloadable rigged creatures.

Do not assume that downloading an asset grants unrestricted ML/training/republication rights.

For every donor record:

```text
source
source URL
license
purchase/download date
allowed usage
AI/training restriction if stated
redistribution restriction
original file formats
```

The repository's code remains clean; donor assets live in the external project folder and are not committed.

---

# 12. Proposed External Project Layout for Donors

Extend the project-folder concept with a donor/reference area when this packet lands.

Conceptual layout:

```text
<project>/
    inputs/
        references/

    generated/
        <backend>/
            <run>/

    assets/
        western_dragon_v1/
            canonical_dragon.blend
            canonical_dragon.glb
            skeleton.json
            landmarks.json
            regions.json
            weights.npz

    donors/
        dragon_001/
            source/
                original.blend
                original.fbx
            extracted/
                mesh.glb
                skeleton.json
                weights.npz
                animations.json
                metadata.json

        dragon_002/
            ...
```

Do not add this blindly to milestone 1. It belongs with the canonical-asset / Blender packet.

---

# 13. Donor Extraction Pipeline

Create a deterministic headless-Blender extraction command.

Conceptually:

```text
BLEND / FBX / GLB donor
        ↓
headless Blender
        ↓
identify deform mesh
identify armature
        ↓
extract:
    mesh
    bone hierarchy
    bone transforms
    rest pose
    skin weights
    animation names
    material metadata
        ↓
normalize coordinates
        ↓
write normalized donor package
```

Suggested CLI concept:

```text
charctx donor import <source-file> --name dragon_001
charctx donor report dragon_001
```

Do not implement these names until they fit the repository's command conventions.

---

# 14. Normalized Skeleton Representation

The canonical and donor skeletons should have a Blender-independent representation.

Suggested conceptual schema:

```json
{
  "skeleton_id": "western_dragon_v1",
  "bones": [
    {
      "name": "wing_root.L",
      "parent": "chest",
      "head": [0.0, 0.0, 0.0],
      "tail": [0.0, 0.0, 0.0],
      "rest_matrix": [],
      "deform": true
    }
  ]
}
```

Exact schema should be designed during implementation.

Important fields:

- semantic canonical name;
- original donor name;
- parent;
- head;
- tail;
- rest transform;
- deform/control classification;
- left/right semantic side;
- optional region/limb metadata.

---

# 15. Bone-Name Normalization

Different donor assets will use incompatible naming.

Examples:

```text
Wing_L
LeftWing01
l_wing_1
wing.root.L
Bone.073
```

Map these into repository semantics such as:

```text
wing_root.L
wing_upper.L
wing_elbow.L
wing_forearm.L
wing_wrist.L
wing_finger_1.L
```

For a first donor corpus, manual semantic mapping is acceptable.

The mapping itself becomes valuable reference data.

Do not over-engineer automatic name matching before a few real donor rigs are inspected.

---

# 16. What We Learn From Donors

For each donor, derive normalized anatomical ratios.

Examples:

```text
pelvis position / body length
shoulder position / torso length
hip position / torso length
neck length / body length
tail base / pelvis
wing root / chest
wing elbow / wing length
wing wrist / wing length
jaw pivot / skull dimensions
front knee/elbow ratios
rear knee/ankle ratios
```

Also compare:

```text
number of spine bones
number of neck bones
number of tail bones
number of wing fingers
toe/finger bones
jaw structure
wing membrane support
```

The goal is not to average everything mathematically.

The goal is to make an informed canonical design.

---

# 17. Canonical Skeleton Design

After inspecting donors, define one deliberate skeleton:

```text
western_dragon_v1
```

It should be:

- semantically named;
- deterministic;
- stable across every generated dragon;
- sufficiently articulated for walk/run/fly/land;
- not needlessly dense;
- explicit about wing structure;
- explicit about jaw;
- explicit about tail and neck chains.

The canonical skeleton should be stored as data and regenerated by Blender code.

The `.blend` file is useful, but the source of truth should not exist only inside an opaque Blender file.

---

# 18. Canonical Skin Weights

Do the same for skinning.

The canonical template should contain a known weight layout.

For a new generated dragon:

```text
generated source surface
        ↓
canonical mesh is deformed to source
        ↓
canonical vertex identity remains unchanged
        ↓
canonical skin weights remain attached to those vertices
```

This is one of the strongest reasons to canonicalize topology first.

If vertex identity is preserved, we do not need to auto-skin every arbitrary generated mesh from scratch.

Weights may need local correction after extreme proportion changes, but the starting point is deterministic.

---

# 19. New Per-Character Rigging Problem

Once canonicalization succeeds, rigging a new dragon becomes:

```text
known canonical topology
        +
known semantic landmarks
        ↓
fit canonical bone positions
        ↓
preserve canonical hierarchy
        ↓
reuse/adapt canonical weights
        ↓
validate
```

This is much simpler than:

```text
arbitrary generated topology
        ↓
invent skeleton
        ↓
invent weights
```

---

# 20. The Main Hard Problem Remains Semantic Correspondence

The difficult part is not Blender armature creation.

The difficult part is:

```text
arbitrary generated dragon
        ↓
identify:
    head
    jaw
    neck
    shoulders
    hips
    elbows
    knees
    feet
    wing roots
    wing elbows
    wing wrists
    wing tips
    tail base/mid/tip
```

This should be treated as a major independent workstream.

Potential inputs later:

- geometric heuristics;
- bilateral symmetry;
- canonical body-plan constraints;
- source reference images;
- multiview renders;
- segmentation from commercial APIs;
- temporary generic rigs from external services;
- learned landmark models;
- donor-corpus priors.

Do not hide this under the generic word "rigging."

---

# 21. Relationship to TRELLIS / Tripo / Rodin / Hi3D

Generator APIs remain replaceable.

Their job is primarily:

```text
reference image(s)
        ↓
raw 3D source surface
```

Commercial providers may additionally offer:

- remeshing;
- segmentation;
- generic retopology;
- generic rigging;
- animations.

These outputs can be useful as **temporary semantic hints**.

For example:

```text
raw dragon
    ↓
commercial segmentation / generic creature rig
    ↓
extract likely joints / body regions
    ↓
discard provider topology and provider rig
    ↓
fit our canonical dragon
```

This is acceptable because our source of truth remains the canonical topology and skeleton.

---

# 22. Suggested Revised Milestone Separation

## Milestone 1 — hosted generation boundary

Keep the existing plan:

```text
reference image
    ↓
HF/TRELLIS generation
    ↓
raw GLB
    ↓
trimesh report
```

Do not pull Blender donor work into milestone 1.

---

## Milestone 2A — donor corpus and canonical skeleton study

Before non-rigid fitting:

```text
collect 5–10 donor dragons
    ↓
headless Blender extraction
    ↓
skeleton/weight reports
    ↓
semantic bone-name normalization
    ↓
canonical skeleton design
```

Outputs:

```text
donors/<id>/extracted/...
assets/western_dragon_v1/skeleton.json
```

---

## Milestone 2B — canonical mesh + canonical weights

Create/supply one canonical western-dragon mesh with:

- fixed topology;
- UVs;
- regions;
- semantic landmarks;
- canonical skeleton;
- canonical skin weights.

This is the reusable production template.

---

## Milestone 3 — semantic correspondence + coarse fit

Input:

```text
raw generated dragon
```

Output:

```text
canonical dragon broadly fitted
```

Use:

- landmarks;
- symmetry;
- segment proportions;
- coarse skeleton pose;
- rigid/ICP/cage techniques;
- Blender where helpful.

---

## Milestone 4 — non-rigid fixed-topology fitting

Optimize canonical topology toward source while preserving:

- topology;
- vertex ordering;
- anatomy;
- symmetry;
- smoothness;
- reasonable edge lengths.

---

## Milestone 5 — skeleton fitting + deformation validation

Fit canonical bones from the fitted canonical geometry.

Reuse/adapt weights.

Automate test poses such as:

```text
jaw open
neck bend
tail curl
front leg lift
back leg crouch
wing half-open
wing fully spread
```

Failures here are production failures.

---

## Milestone 6 — appearance transfer

Only after geometry/rig stability:

- PBR transfer;
- texture rebake;
- normal/displacement detail;
- possibly use a model-assisted mesh-texturing pipeline.

---

# 23. Blender Code Organization

When Blender lands, keep Blender-specific code behind a clear service boundary.

Possible structure:

```text
src/character_context/
    blender/
        runner.py
        importers.py
        armature.py
        weights.py
        donors.py
        shrinkwrap.py
        bake.py
        export.py
        validation.py

    rigging/
        skeleton.py
        fit.py
        weights.py
        validation.py

    canonicalization/
        landmarks.py
        registration.py
        coarse_fit.py
        nonrigid_fit.py
```

Important boundary:

```text
rigging/skeleton.py
```

should define domain semantics independent of Blender.

```text
blender/armature.py
```

should implement those semantics in Blender.

---

# 24. Suggested Data Contracts

Potential future models:

```python
class BoneSpec(BaseModel):
    name: str
    parent: str | None
    head: tuple[float, float, float]
    tail: tuple[float, float, float]
    deform: bool = True


class SkeletonSpec(BaseModel):
    skeleton_id: str
    bones: list[BoneSpec]


class DonorCharacter(BaseModel):
    donor_id: str
    source_path: str
    mesh_path: str
    skeleton_path: str
    weights_path: str
    metadata_path: str


class SkeletonFitResult(BaseModel):
    skeleton_id: str
    fitted_skeleton_path: str
    metrics: dict
    warnings: list[str]
```

These are conceptual only; design them when implementation starts.

---

# 25. Validation Requirements

Do not consider a dragon rigged merely because bones exist.

Validate:

## Skeleton

```text
✓ required semantic bones exist
✓ parent hierarchy matches canonical skeleton
✓ bone lengths are finite and non-zero
✓ left/right limbs map correctly
✓ wing chains exist
✓ tail chain exists
✓ neck/head/jaw chain exists
```

## Skin weights

```text
✓ no unexpected unweighted vertices
✓ sums approximately normalize to 1
✓ weights reference valid deform bones
✓ wing membrane has intentional support
```

## Deformation

Automated test poses must check for:

- severe self-intersections;
- wing membrane collapse;
- shoulder collapse;
- hip collapse;
- jaw tearing;
- tail discontinuities;
- broken normals;
- disconnected geometry.

---

# 26. Explicit Non-Goals

Do NOT spend V1 effort on:

- generic arbitrary-creature skeleton generation;
- generating a novel bone hierarchy for every dragon;
- learning animator control rigs from scratch;
- supporting every dragon body plan;
- hydras;
- wyverns;
- serpentine eastern dragons;
- facial expression rigs;
- procedural muscle simulation;
- cloth/armor rigging;
- large-scale training on donor assets.

The target remains:

```text
western quadruped dragon
four legs
two wings
one neck/head
one tail
```

---

# 27. Practical Recommendation to the Next Agent

The next repo agent should preserve the current milestone-1 plan, then prepare a later packet around:

> **Blender donor extraction + canonical skeleton definition**

Before implementing any sophisticated rig fitting, the agent should:

1. inspect the current plan and handoff;
2. keep Blender as a first-class workspace tool;
3. define donor-asset metadata and licensing records;
4. prototype one deterministic Blender extraction script;
5. run it on 2–3 representative rigged dragon assets;
6. compare skeleton hierarchies and weights;
7. only then propose the exact `western_dragon_v1` skeleton schema;
8. do not prematurely build a generic rig abstraction;
9. do not make provider auto-rigging the canonical solution;
10. treat provider segmentation/rigging only as optional hints.

---

# 28. Key Mental Model

The project should be understood as:

```text
         GENERATION
TRELLIS / Tripo / Rodin / Hi3D
             ↓
       arbitrary dragon
             ↓
   semantic interpretation
             ↓
  canonical dragon topology
             ↓
   canonical skeleton fit
             ↓
 canonical skin weights
             ↓
   Blender validation
             ↓
        GLB / FBX
```

The reusable value is:

```text
canonical mesh
+
canonical semantic skeleton
+
canonical weights
+
deterministic fitting
+
deformation validation
```

Not the generator, and not arbitrary automatic creature rigging.

---

# 29. Final Design Thesis

The DIY path is realistic because Blender already solves the mechanical parts of rig construction, skinning, deformation tooling, baking, and export.

The repository's engineering effort should therefore concentrate on the parts Blender does not know:

1. what a valid western-dragon anatomy is;
2. where semantic landmarks are on each generated dragon;
3. how the canonical topology should deform toward the source;
4. where the known canonical bones should move;
5. how to detect failed deformation.

Existing rigged dragons should be treated as **few-shot engineering references** that help us design the canonical representation and derive robust anatomical priors.

That gives the pipeline a practical bridge between open generative 3D and deterministic production character assets.
