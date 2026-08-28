"""Validated contracts for collected asset packages."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AssetSource(BaseModel):
    provider: str = "unknown"
    asset_id: str = "unknown"
    url: str = "unknown"
    creator: str = "unknown"


class AssetLicense(BaseModel):
    name: str = "unknown"
    url: str = "unknown"
    local_engineering_use: str = "private-workspace-only"
    redistribution: str = "unknown"
    ai_training: str = "unknown"


class AssetAcquisition(BaseModel):
    method: str = "manual"
    date: str = "unknown"


class AssetFrontMatter(BaseModel):
    """Human-curated card and provenance data from README front matter."""

    model_config = ConfigDict(populate_by_name=True)

    schema_id: Literal["charctx.asset/v1"] = Field(
        default="charctx.asset/v1", alias="schema"
    )
    id: str
    title: str
    kind: Literal["donor", "reference"] = "donor"
    status: Literal["collected", "selected", "canonical"] = "collected"
    provenance_status: Literal["complete", "incomplete"] = "incomplete"
    family: Literal["western-dragon"] = "western-dragon"
    tags: list[str] = Field(default_factory=lambda: ["western-dragon"])
    source: AssetSource = Field(default_factory=AssetSource)
    license: AssetLicense = Field(default_factory=AssetLicense)
    acquisition: AssetAcquisition = Field(default_factory=AssetAcquisition)
    primary_file: str
    cover: str = "previews/hero.webp"
    web_model: str = "web/model.glb"
    generation_names: list[str] = Field(default_factory=list)


class AssetFileRecord(BaseModel):
    path: str
    bytes: int
    sha256: str


class DerivedArtifactRecord(BaseModel):
    """Declared, hash-bound derivative inside one asset package."""

    path: str
    bytes: int = Field(ge=0)
    sha256: str
    schema_id: str = Field(alias="schema")
    summary: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(populate_by_name=True)


class SkeletonBone(BaseModel):
    """One unmodified source bone measured in rest pose."""

    name: str
    parent: str | None = None
    deform: bool
    connected: bool
    depth: int = Field(ge=0)
    head: tuple[float, float, float]
    tail: tuple[float, float, float]
    head_local: tuple[float, float, float]
    tail_local: tuple[float, float, float]
    length: float = Field(ge=0)
    roll: float
    matrix_local: list[list[float]]


class SkeletonArmature(BaseModel):
    name: str
    pose_position: str
    object_matrix: list[list[float]]
    bones: list[SkeletonBone]
    roots: list[str]
    leaves: list[str]
    max_depth: int = Field(ge=0)
    bounds_min: tuple[float, float, float]
    bounds_max: tuple[float, float, float]
    total_length: float = Field(ge=0)
    deform_total_length: float = Field(ge=0)
    name_signals: dict[str, int] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_hierarchy(self) -> SkeletonArmature:
        names = [bone.name for bone in self.bones]
        if len(names) != len(set(names)):
            raise ValueError(f"armature {self.name!r} has duplicate bone names")
        known = set(names)
        for bone in self.bones:
            if bone.parent is not None and bone.parent not in known:
                raise ValueError(
                    f"bone {bone.name!r} has unknown parent {bone.parent!r}"
                )
            seen = {bone.name}
            parent = bone.parent
            while parent is not None:
                if parent in seen:
                    raise ValueError(f"bone hierarchy cycles through {parent!r}")
                seen.add(parent)
                parent = next(item.parent for item in self.bones if item.name == parent)
        measured_roots = [bone.name for bone in self.bones if bone.parent is None]
        if self.roots != measured_roots:
            raise ValueError("declared roots disagree with the bone hierarchy")
        return self


class SkeletonDocument(BaseModel):
    """Blender-independent, faithful donor skeleton extraction."""

    schema_id: Literal["charctx.skeleton/v1"] = Field(
        default="charctx.skeleton/v1", alias="schema"
    )
    asset_id: str
    blender_version: str
    source_model: str
    coordinate_system: dict[str, Any]
    armatures: list[SkeletonArmature]
    summary: dict[str, Any]

    model_config = ConfigDict(populate_by_name=True)


class SkinWeightBinding(BaseModel):
    mesh: str
    armature: str
    vertices: int = Field(ge=0)
    bone_names: list[str]
    vertex_offsets: list[int]
    bone_indices: list[int]
    weights: list[float]
    weighted_vertices: int = Field(ge=0)
    unweighted_vertices: int = Field(ge=0)
    influence_count: int = Field(ge=0)
    max_influences: int = Field(ge=0)
    max_weight_sum_error: float = Field(ge=0)
    non_bone_assignments: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_sparse_encoding(self) -> SkinWeightBinding:
        if len(self.vertex_offsets) != self.vertices + 1:
            raise ValueError("vertex_offsets must contain vertices + 1 entries")
        if not self.vertex_offsets or self.vertex_offsets[0] != 0:
            raise ValueError("vertex_offsets must begin at zero")
        if any(
            current > following
            for current, following in zip(
                self.vertex_offsets, self.vertex_offsets[1:], strict=False
            )
        ):
            raise ValueError("vertex_offsets must be non-decreasing")
        if len(self.bone_indices) != len(self.weights):
            raise ValueError("bone_indices and weights must have equal length")
        if self.vertex_offsets[-1] != len(self.weights):
            raise ValueError("last vertex offset must equal the influence count")
        if self.influence_count != len(self.weights):
            raise ValueError("declared influence_count disagrees with weights")
        if any(
            index < 0 or index >= len(self.bone_names)
            for index in self.bone_indices
        ):
            raise ValueError("bone index escapes bone_names")
        if self.weighted_vertices + self.unweighted_vertices != self.vertices:
            raise ValueError("weighted and unweighted counts disagree with vertices")
        return self


class SkinWeightsDocument(BaseModel):
    """Exact sparse source skin bindings; no weight synthesis or normalization."""

    schema_id: Literal["charctx.skin-weights/v1"] = Field(
        default="charctx.skin-weights/v1", alias="schema"
    )
    asset_id: str
    source_model: str
    encoding: Literal["csr-per-vertex"] = "csr-per-vertex"
    bindings: list[SkinWeightBinding]
    summary: dict[str, Any]

    model_config = ConfigDict(populate_by_name=True)


class AssetInspection(BaseModel):
    """Measured facts written by the asset build pipeline."""

    schema_id: Literal["charctx.inspection/v1"] = Field(
        default="charctx.inspection/v1", alias="schema"
    )
    asset_id: str
    blender_version: str
    primary_model: str
    source_files: list[AssetFileRecord]
    objects: dict[str, Any]
    meshes: list[dict[str, Any]]
    armatures: list[dict[str, Any]]
    actions: list[dict[str, Any]]
    materials: list[str]
    images: list[dict[str, Any]]
    bounds: dict[str, Any]
    web_measurements: dict[str, Any]
    skeleton: DerivedArtifactRecord | None = None
    skin_weights: DerivedArtifactRecord | None = None
    warnings: list[str] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)


class AssetCard(BaseModel):
    id: str
    title: str
    kind: str
    status: str
    provenance_status: str
    family: str
    tags: list[str]
    package_dir: str
    primary_file: str
    source_formats: list[str]
    rigged: bool
    animated: bool
    bones: int
    actions: int
    vertices: int
    polygons: int
    cover: str | None
    web_model: str | None
    skeleton: str | None = None
    skin_weights: str | None = None
    deform_bones: int = 0
    previews: list[str]
    generations: int = 0
    warnings: list[str]


class GenerationManifest(BaseModel):
    """Self-contained, relative-path index for one append-only generation."""

    schema_id: Literal["charctx.generation-view/v1"] = Field(
        default="charctx.generation-view/v1", alias="schema"
    )
    character_id: str
    backend: str
    run: str
    request_name: str
    seed: int = 0
    started_at: str | None = None
    completed_at: str | None = None
    duration_s: float | None = None
    model: str
    model_sha256: str
    measurements: str | None = None
    request_file: str = "request.json"
    inputs: list[str] = Field(default_factory=list)
    previews: list[str] = Field(default_factory=list)
    stages: dict[str, str] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)


class GenerationRecord(GenerationManifest):
    """Manifest plus normalized run location and measured facts for clients."""

    run_dir: str
    metrics: dict[str, Any] | None = None
