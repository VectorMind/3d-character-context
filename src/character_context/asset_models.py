"""Validated contracts for collected asset packages."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


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
