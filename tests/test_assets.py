"""Collected asset packages are safe, deterministic, and CLI-readable."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import trimesh

from character_context import assets
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
    assert inspection["web_measurements"]["vertices"] > 0
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
