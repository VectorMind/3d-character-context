"""Generated runs link into character records without becoming duplicate assets."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from character_context import assets, generations
from character_context.asset_models import AssetFrontMatter
from character_context.config import ConfigError
from character_context.project import Project


def make_run(project_root: Path, glb_file: Path) -> Path:
    run = project_root / "generated" / "trellis2" / "dragon-001"
    run.mkdir(parents=True)
    shutil.copy2(glb_file, run / "dragon.glb")
    (run / "reference.png").write_bytes(b"reference")
    supporting = run / "supporting-views"
    supporting.mkdir()
    (supporting / "left.webp").write_bytes(b"left")
    (run / "dragon.measurements.json").write_text(
        json.dumps({"vertices": 162, "faces": 320, "watertight": True}),
        encoding="utf-8",
    )
    (run / "request.json").write_text(
        json.dumps(
            {
                "backend": "trellis2",
                "started_at": "2026-08-28T10:00:00Z",
                "completed_at": "2026-08-28T10:00:47Z",
                "duration_s": 47.0,
                "request": {"name": "dragon", "seed": 42},
                "artifacts": ["dragon.glb", "reference.png"],
            }
        ),
        encoding="utf-8",
    )
    return run


def make_character(project_root: Path) -> Path:
    package = project_root / "assets" / "collected" / "dragon"
    for name in ("source", "license", "inspection", "previews", "web"):
        (package / name).mkdir(parents=True, exist_ok=True)
    (package / "source" / "front.png").write_bytes(b"front")
    assets._write_readme(
        package,
        AssetFrontMatter(
            id="dragon",
            title="Dragon character record",
            kind="reference",
            primary_file="source/front.png",
            generation_names=["dragon"],
        ),
    )
    return package


def test_manifest_indexes_run_with_relative_paths_and_preserves_model(
    project_root: Path, glb_file: Path
) -> None:
    run = make_run(project_root, glb_file)
    before = hashlib.sha256((run / "dragon.glb").read_bytes()).hexdigest()

    manifest_path = generations.write_manifest(run, "dragon")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["schema"] == "charctx.generation-view/v1"
    assert manifest["model"] == "dragon.glb"
    assert manifest["model_sha256"] == before
    assert manifest["inputs"] == ["reference.png", "supporting-views/left.webp"]
    assert manifest["stages"] == {
        "references": "complete",
        "generation": "complete",
        "canonicalization": "not-started",
        "skeleton": "not-started",
        "rigging": "not-started",
        "poses": "not-started",
    }
    assert hashlib.sha256((run / "dragon.glb").read_bytes()).hexdigest() == before


def test_reference_asset_embeds_every_linked_generation(
    project_root: Path, glb_file: Path
) -> None:
    make_character(project_root)
    run = make_run(project_root, glb_file)
    generations.write_manifest(run, "dragon")

    shown = assets.show_asset(Project(project_root), "dragon")

    assert shown["card"]["generations"] == 1
    assert len(shown["generations"]) == 1
    generation = shown["generations"][0]
    assert generation["run"] == "dragon-001"
    assert generation["model"] == "dragon.glb"
    assert generation["metrics"]["vertices"] == 162
    assert [card.id for card in assets.list_assets(Project(project_root))] == [
        "dragon"
    ]


def test_manifest_character_mismatch_and_unsafe_run_are_rejected(
    project_root: Path, glb_file: Path
) -> None:
    run = make_run(project_root, glb_file)
    generations.write_manifest(run, "another-character")
    project = Project(project_root)

    with pytest.raises(ConfigError, match="belongs to"):
        generations.discover(project, ["dragon"], "dragon")
    with pytest.raises(ConfigError, match="safe slugs"):
        generations.build_view(project, "../dragon-001", "dragon")
