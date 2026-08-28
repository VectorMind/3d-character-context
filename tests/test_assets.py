"""Collected asset packages are safe, deterministic, and CLI-readable."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import trimesh

from character_context import assets
from character_context.asset_models import AssetFrontMatter
from character_context.config import ConfigError
from character_context.project import Project


def collected(project_root: Path) -> Path:
    path = project_root / "assets" / "collected"
    path.mkdir()
    return path


def test_inspect_is_read_only_and_organize_is_explicit(project_root: Path) -> None:
    root = collected(project_root)
    source = root / "Blender_Dragon.blend"
    source.write_bytes(b"unchanged dragon bytes")
    expected = hashlib.sha256(source.read_bytes()).hexdigest()
    project = Project(project_root)

    preview = assets.inspect_collection(project)
    assert preview["loose"][0]["asset_id"] == "blender-dragon"
    assert source.is_file()
    assert not (root / "blender-dragon").exists()

    organized = assets.organize(project)
    package = root / "blender-dragon"
    moved = package / "source" / source.name
    assert organized[0]["sha256"] == expected
    assert not source.exists()
    assert hashlib.sha256(moved.read_bytes()).hexdigest() == expected
    assert (package / "README.md").is_file()
    assert assets.organize(project) == [], "a repeat with no loose files is a no-op"


def test_organize_preflights_all_collisions_before_moving(project_root: Path) -> None:
    root = collected(project_root)
    first = root / "first.blend"
    second = root / "second.blend"
    first.write_bytes(b"first")
    second.write_bytes(b"second")
    (root / "second").mkdir()

    with pytest.raises(ConfigError, match="destination exists"):
        assets.organize(Project(project_root))

    assert first.is_file()
    assert second.is_file()
    assert not (root / "first").exists()


def test_front_matter_is_curated_authority_and_starts_incomplete(
    project_root: Path,
) -> None:
    root = collected(project_root)
    (root / "dragon.blend").write_bytes(b"dragon")
    assets.organize(Project(project_root))

    metadata, body = assets.read_front_matter(root / "dragon" / "README.md")
    assert metadata.id == "dragon"
    assert metadata.status == "collected"
    assert metadata.provenance_status == "incomplete"
    assert metadata.source.url == "unknown"
    assert "private workspace page" in body


def test_build_writes_measured_derivatives_and_preserves_manual_notes(
    project_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = collected(project_root)
    (root / "dragon.blend").write_bytes(b"dragon source")
    project = Project(project_root)
    assets.organize(project)
    package = root / "dragon"
    readme = package / "README.md"
    text = readme.read_text(encoding="utf-8")
    readme.write_text(
        text.replace("Add local notes here.", "Keep this hand-written note."),
        encoding="utf-8",
    )

    def fake_blender(asset_id: str, model: Path, output: Path, log: Path) -> dict:
        mesh = trimesh.creation.icosphere(subdivisions=1)
        mesh.export(output / "model.glb")
        identity = [
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ]
        bones = [
            {
                "name": f"bone.{index:03d}",
                "parent": f"bone.{index - 1:03d}" if index else None,
                "deform": True,
                "connected": index > 0,
                "depth": index,
                "head": [0.0, float(index), 0.0],
                "tail": [0.0, float(index + 1), 0.0],
                "head_local": [0.0, float(index), 0.0],
                "tail_local": [0.0, float(index + 1), 0.0],
                "length": 1.0,
                "roll": 0.0,
                "matrix_local": identity,
            }
            for index in range(12)
        ]
        skeleton = {
            "schema": "charctx.skeleton/v1",
            "asset_id": asset_id,
            "blender_version": "5.2.1-test",
            "source_model": model.name,
            "coordinate_system": {"pose": "armature rest pose"},
            "armatures": [
                {
                    "name": "rig",
                    "pose_position": "POSE",
                    "object_matrix": identity,
                    "bones": bones,
                    "roots": ["bone.000"],
                    "leaves": ["bone.011"],
                    "max_depth": 11,
                    "bounds_min": [0.0, 0.0, 0.0],
                    "bounds_max": [0.0, 12.0, 0.0],
                    "total_length": 12.0,
                    "deform_total_length": 12.0,
                    "name_signals": {},
                }
            ],
            "summary": {
                "armatures": 1,
                "bones": 12,
                "deform_bones": 12,
                "roots": 1,
                "leaves": 1,
                "max_depth": 11,
            },
        }
        weights = {
            "schema": "charctx.skin-weights/v1",
            "asset_id": asset_id,
            "source_model": model.name,
            "encoding": "csr-per-vertex",
            "bindings": [
                {
                    "mesh": "dragon",
                    "armature": "rig",
                    "vertices": 42,
                    "bone_names": [bone["name"] for bone in bones],
                    "vertex_offsets": list(range(43)),
                    "bone_indices": [0] * 42,
                    "weights": [1.0] * 42,
                    "weighted_vertices": 42,
                    "unweighted_vertices": 0,
                    "influence_count": 42,
                    "max_influences": 1,
                    "max_weight_sum_error": 0.0,
                    "non_bone_assignments": 0,
                }
            ],
            "summary": {
                "bindings": 1,
                "vertices": 42,
                "weighted_vertices": 42,
                "unweighted_vertices": 0,
                "influences": 42,
                "max_influences": 1,
                "max_weight_sum_error": 0.0,
                "non_bone_assignments": 0,
            },
        }
        (output / "skeleton.json").write_text(json.dumps(skeleton), encoding="utf-8")
        (output / "skin-weights.json").write_text(
            json.dumps(weights), encoding="utf-8"
        )
        preview_dir = output / "previews"
        preview_dir.mkdir()
        for name in assets.PREVIEW_NAMES:
            (preview_dir / f"{name}.webp").write_bytes(b"RIFFfakewebp")
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text("fake blender")
        return {
            "blender_version": "5.2.1-test",
            "objects": {"total": 2, "types": {"MESH": 1, "ARMATURE": 1}},
            "meshes": [
                {
                    "name": "dragon",
                    "vertices": 42,
                    "polygons": 80,
                    "weighted_vertices": 42,
                }
            ],
            "armatures": [{"name": "rig", "bones": 12, "deform_bones": 12}],
            "actions": [{"name": "Fly", "frame_range": [1.0, 24.0]}],
            "materials": ["scales"],
            "images": [],
            "bounds": {"min": [-1, -1, -1], "max": [1, 1, 1], "extents": [2, 2, 2]},
            "warnings": [],
        }

    monkeypatch.setattr(assets, "_run_blender", fake_blender)
    result = assets.build_asset(project, "dragon")

    assert Path(result["web_model"]).is_file()
    assert all(Path(path).is_file() for path in result["previews"])
    assert "Keep this hand-written note." in readme.read_text(encoding="utf-8")
    inspection = json.loads((package / "inspection" / "report.json").read_text())
    assert inspection["armatures"][0]["bones"] == 12
    assert inspection["skeleton"]["path"] == "inspection/skeleton.json"
    assert inspection["skin_weights"]["summary"]["influences"] == 42
    assert (package / "inspection" / "skeleton.json").is_file()
    assert (package / "inspection" / "skin-weights.json").is_file()
    assert inspection["web_measurements"]["vertices"] > 0
    card = assets.list_assets(project)[0]
    assert card.skeleton == "inspection/skeleton.json"
    assert card.deform_bones == 12
    assert assets.validate(project) == [{"id": "dragon", "valid": True, "errors": []}]

    (package / "source" / "dragon.blend").write_bytes(b"changed source")
    with pytest.raises(ConfigError, match="Source changed"):
        assets.build_asset(project, "dragon")


def test_catalog_combines_curated_and_measured_facts(
    project_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = collected(project_root)
    (root / "dragon.blend").write_bytes(b"dragon")
    project = Project(project_root)
    assets.organize(project)
    card = assets.list_assets(project)[0]
    assert card.id == "dragon"
    assert card.provenance_status == "incomplete"
    assert card.web_model is None
    assert any("Provenance incomplete" in warning for warning in card.warnings)


def test_reference_image_package_validates_without_a_3d_build(
    project_root: Path,
) -> None:
    root = collected(project_root)
    package = root / "riyu"
    for name in ("source", "license", "inspection", "previews", "web"):
        (package / name).mkdir(parents=True, exist_ok=True)
    (package / "source" / "side.jpg").write_bytes(b"reference image")
    for name in assets.PREVIEW_NAMES:
        (package / "previews" / f"{name}.webp").write_bytes(b"RIFFpreview")
    assets._write_readme(
        package,
        AssetFrontMatter(
            id="riyu",
            title="Riyu Reference Turnaround",
            kind="reference",
            primary_file="source/side.jpg",
        ),
    )
    project = Project(project_root)

    card = assets.list_assets(project)[0]
    assert card.kind == "reference"
    assert card.web_model is None
    assert card.previews == [
        "previews/hero.webp",
        "previews/front.webp",
        "previews/left.webp",
        "previews/rear.webp",
        "previews/top.webp",
    ]
    assert assets.validate(project) == [{"id": "riyu", "valid": True, "errors": []}]
    with pytest.raises(ConfigError, match="reference-image package"):
        assets.build_asset(project, "riyu")
    with pytest.raises(ConfigError, match="No buildable 3D donor packages"):
        assets.build(project)
