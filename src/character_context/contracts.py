"""Pipeline contracts.

These pydantic models are the only types that cross module boundaries.
Provider-native responses (Gradio payloads, REST job envelopes) stay inside
their backend module and are never returned to callers.

`GenerationRequest`, `RawCharacterResult`, and `MeshMeasurements` are in use.
`CanonicalizationResult` and `RiggedCharacterResult` describe the canonical
layer's outputs and exist so later stages inherit conventions rather than
invent them.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

MESH_SUFFIXES = {".glb", ".gltf", ".obj", ".ply", ".stl"}


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GenerationRequest(_Model):
    """What is asked of a hosted generator.

    Backend-specific knobs live in `options` rather than growing this model:
    every backend has a different set, and the common denominator across
    real image-to-3d APIs is only "image(s) plus options".
    """

    images: list[Path] = Field(min_length=1, description="Reference image paths")
    name: str = Field(
        description="Slug for the output folder, e.g. 'red-dragon'",
        pattern=r"^[a-z0-9]+(?:[-_][a-z0-9]+)*$",
    )
    backend: str = Field(description="Backend key from config/providers.yaml")
    seed: int = Field(default=0, ge=0)
    prompt: str | None = None
    options: dict[str, Any] = Field(default_factory=dict)

    @field_validator("images")
    @classmethod
    def _images_must_exist(cls, images: list[Path]) -> list[Path]:
        missing = [str(p) for p in images if not Path(p).is_file()]
        if missing:
            raise ValueError(f"Reference image(s) not found: {', '.join(missing)}")
        return [Path(p).resolve() for p in images]


class RawCharacterResult(_Model):
    """One completed hosted generation and where its artifacts landed.

    A raw result carries untrusted topology: arbitrary vertex counts and
    ordering, no semantic regions, no skeleton. Canonicalization is what turns
    it into a production asset.
    """

    request: GenerationRequest
    backend: str
    provider: str = Field(description="e.g. 'huggingface-space'")
    endpoint: str = Field(description="Provider-side identity, e.g. a Space id")
    mesh: Path = Field(description="Downloaded mesh artifact")
    extra_artifacts: list[Path] = Field(default_factory=list)
    run_dir: Path = Field(description="Append-only folder holding this run")
    job_id: str | None = None
    started_at: datetime
    completed_at: datetime
    duration_s: float = Field(ge=0)

    @field_validator("mesh")
    @classmethod
    def _mesh_must_be_a_mesh(cls, mesh: Path) -> Path:
        if mesh.suffix.lower() not in MESH_SUFFIXES:
            raise ValueError(
                f"Unexpected mesh suffix {mesh.suffix!r}; "
                f"expected one of {sorted(MESH_SUFFIXES)}"
            )
        return mesh


class MeshMeasurements(_Model):
    """Measured facts about a mesh artifact.

    Proof of mesh work is measurement, never appearance: this model is what a
    claim about geometry is backed by.
    """

    source: Path
    file_size_bytes: int = Field(ge=0)
    file_format: str

    geometries: int = Field(ge=0, description="Sub-meshes in the source scene")
    vertices: int = Field(ge=0)
    faces: int = Field(ge=0)

    bounds_min: tuple[float, float, float]
    bounds_max: tuple[float, float, float]
    extents: tuple[float, float, float]
    centroid: tuple[float, float, float]

    surface_area: float = Field(ge=0)
    volume: float | None = Field(
        default=None, description="Only meaningful when watertight"
    )
    watertight: bool
    connected_components: int = Field(ge=0)
    degenerate_faces: int = Field(ge=0)
    all_finite: bool
    textured: bool
    sampled_points: int = Field(
        ge=0, description="Surface samples taken to confirm the mesh is samplable"
    )

    measured_at: datetime
    backend: str | None = None
    seed: int | None = None
    request_name: str | None = None

    @property
    def is_plausible(self) -> bool:
        """Cheap sanity gate: real geometry, finite coordinates, non-zero size."""
        return (
            self.vertices > 0
            and self.faces > 0
            and self.all_finite
            and self.surface_area > 0
            and max(self.extents) > 0
        )


class CanonicalizationResult(_Model):
    """Reserved for milestone 2-3: a raw mesh fitted to the canonical topology.

    A canonical mesh matches the template's vertex and face counts and vertex
    ordering exactly, which is what makes every downstream stage deterministic.
    """

    source: RawCharacterResult | None = None
    template: str = Field(
        description="Canonical family/version, e.g. western_dragon_v1"
    )
    mesh: Path
    vertices: int = Field(ge=0)
    faces: int = Field(ge=0)
    matches_template_topology: bool
    landmarks: dict[str, tuple[float, float, float]] = Field(default_factory=dict)
    regions: dict[str, list[int]] = Field(default_factory=dict)
    fit_error_mean: float | None = None
    fit_error_max: float | None = None
    created_at: datetime


class RiggedCharacterResult(_Model):
    """Reserved for milestone 4: a canonical mesh with the canonical skeleton.

    A valid rig has every template bone, approximately unit-sum skin weights,
    and no unweighted vertices.
    """

    source: CanonicalizationResult | None = None
    skeleton: str = Field(description="Canonical skeleton id, e.g. western_dragon_v1")
    mesh: Path
    bones: list[str]
    missing_bones: list[str] = Field(default_factory=list)
    unweighted_vertices: int = Field(default=0, ge=0)
    max_weight_sum_error: float = Field(default=0.0, ge=0)
    created_at: datetime
