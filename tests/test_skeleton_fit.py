"""A donor skeleton is rigidly fitted onto a generated mesh, then declared."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from character_context import assets, generations, skeleton_fit
from character_context.asset_models import AssetFrontMatter
from character_context.config import ConfigError
from character_context.project import Project


def make_donor(project_root: Path) -> Path:
    """A donor package whose skeleton's bones span a 2 x 3 x 2 box."""
    package = project_root / "assets" / "collected" / "donor"
    for name in ("source", "inspection", "previews", "web"):
        (package / name).mkdir(parents=True, exist_ok=True)
    (package / "source" / "donor.blend").write_bytes(b"blend")
    assets._write_readme(
        package,
        AssetFrontMatter(
            id="donor",
            title="Donor dragon",
            kind="donor",
            primary_file="source/donor.blend",
        ),
    )
    identity = [
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]
    bones = [
        {
            "name": f"bone.{index:03d}",
            "parent": None if index == 0 else f"bone.{index - 1:03d}",
            "deform": True,
            "connected": index > 0,
            "depth": index,
            "head": [-1.0 if index == 0 else 1.0, float(index), -1.0],
            "tail": [1.0, float(index + 1), 1.0],
            "head_local": [0.0, float(index), 0.0],
            "tail_local": [0.0, float(index + 1), 0.0],
            "length": 1.0,
            "roll": 0.25,
            "matrix_local": identity,
        }
        for index in range(3)
    ]
    skeleton = {
        "schema": "charctx.skeleton/v1",
        "asset_id": "donor",
        "blender_version": "5.2.1-test",
        "source_model": "donor.blend",
        "coordinate_system": {"viewer_space": "right-handed, +Y up, -Z forward"},
        "armatures": [
            {
                "name": "rig",
                "pose_position": "POSE",
                "object_matrix": identity,
                "bones": bones,
                "roots": ["bone.000"],
                "leaves": ["bone.002"],
                "max_depth": 2,
                "bounds_min": [-1.0, 0.0, -1.0],
                "bounds_max": [1.0, 4.0, 1.0],
                "total_length": 3.0,
                "deform_total_length": 3.0,
                "name_signals": {},
            }
        ],
        "summary": {
            "armatures": 1,
            "bones": 3,
            "deform_bones": 3,
            "roots": 1,
            "leaves": 1,
            "max_depth": 2,
        },
    }
    (package / "inspection" / "skeleton.json").write_text(
        json.dumps(skeleton), encoding="utf-8"
    )
    report = {
        "schema": "charctx.inspection/v1",
        "asset_id": "donor",
        "blender_version": "5.2.1-test",
        "primary_model": "donor.blend",
        "source_files": [],
        "objects": {"total": 2, "types": {"MESH": 1, "ARMATURE": 1}},
        "meshes": [],
        "armatures": [{"name": "rig", "bones": 3, "deform_bones": 3}],
        "actions": [],
        "materials": [],
        "images": [],
        "bounds": {"min": [-1, 0, -1], "max": [1, 4, 1], "extents": [2, 4, 2]},
        "warnings": [],
        "web_measurements": {
            "vertices": 8,
            "faces": 12,
            "bounds_min": [-1.0, 0.0, -1.0],
            "bounds_max": [1.0, 4.0, 1.0],
        },
        "skeleton": {
            "path": "inspection/skeleton.json",
            "bytes": 1,
            "sha256": "x",
            "schema": "charctx.skeleton/v1",
            "summary": {"bones": 3},
        },
    }
    (package / "inspection" / "report.json").write_text(
        json.dumps(report), encoding="utf-8"
    )
    return package


def make_target(project_root: Path, glb_file: Path) -> Path:
    """A generation run whose measured mesh spans a 20 x 3 x 20 box."""
    run = project_root / "generated" / "trellis2" / "riyu-001"
    run.mkdir(parents=True)
    shutil.copy2(glb_file, run / "riyu.glb")
    (run / "riyu.measurements.json").write_text(
        json.dumps(
            {
                "vertices": 162,
                "faces": 320,
                "bounds_min": [-10.0, -1.5, -10.0],
                "bounds_max": [10.0, 1.5, 10.0],
            }
        ),
        encoding="utf-8",
    )
    (run / "request.json").write_text(
        json.dumps(
            {
                "backend": "trellis2",
                "request": {"name": "riyu", "seed": 7},
                "artifacts": ["riyu.glb"],
            }
        ),
        encoding="utf-8",
    )
    return run


def test_fit_scales_uniformly_to_contain_the_target_and_records_its_limits(
    project_root: Path, glb_file: Path
) -> None:
    make_donor(project_root)
    run = make_target(project_root, glb_file)

    result = skeleton_fit.fit(Project(project_root), "trellis2/riyu-001", "donor")
    document = json.loads((run / "skeleton" / "skeleton.json").read_text())

    # The donor's bones span 3 units in y against the target's 3, which is
    # the tightest axis, so height alone sets the uniform scale.
    assert result["uniform_scale"] == pytest.approx(1.0)
    assert document["schema"] == "charctx.fitted-skeleton/v1"
    assert document["derivation"]["faithful"] is False
    assert document["derivation"]["method"] == skeleton_fit.FIT_METHOD
    assert document["derivation"]["limitations"]

    # Uniform scale means the donor cannot fill the target's much wider box,
    # and that shortfall is the measurement this step exists to produce.
    fill = document["derivation"]["target_fill_ratio"]
    assert fill["y"] == pytest.approx(1.0)
    assert fill["x"] == pytest.approx(0.1)
    assert fill["z"] == pytest.approx(0.1)


def test_fitted_skeleton_lands_inside_the_target_bounds(
    project_root: Path, glb_file: Path
) -> None:
    make_donor(project_root)
    run = make_target(project_root, glb_file)

    skeleton_fit.fit(Project(project_root), "trellis2/riyu-001", "donor")
    document = json.loads((run / "skeleton" / "skeleton.json").read_text())

    for armature in document["armatures"]:
        for bone in armature["bones"]:
            for point in (bone["head"], bone["tail"]):
                assert -10.0 <= point[0] <= 10.0
                assert -1.5 <= point[1] <= 1.5
                assert -10.0 <= point[2] <= 10.0


def test_fit_preserves_hierarchy_and_scales_lengths(
    project_root: Path, glb_file: Path
) -> None:
    make_donor(project_root)
    run = make_target(project_root, glb_file)

    skeleton_fit.fit(Project(project_root), "trellis2/riyu-001", "donor")
    document = json.loads((run / "skeleton" / "skeleton.json").read_text())
    bones = document["armatures"][0]["bones"]

    assert [bone["name"] for bone in bones] == ["bone.000", "bone.001", "bone.002"]
    assert [bone["parent"] for bone in bones] == [None, "bone.000", "bone.001"]
    assert document["summary"]["bones"] == 3
    # Rolls are inherited untouched; recomputing them is not this step's job.
    assert all(bone["roll"] == 0.25 for bone in bones)
    # Scale is 1.0 here, so lengths survive unchanged.
    assert all(bone["length"] == pytest.approx(1.0) for bone in bones)


def test_manifest_declares_the_skeleton_and_completes_the_stage(
    project_root: Path, glb_file: Path
) -> None:
    make_donor(project_root)
    run = make_target(project_root, glb_file)

    skeleton_fit.fit(Project(project_root), "trellis2/riyu-001", "donor")
    manifest = json.loads(
        (run / generations.VIEWER_FILE).read_text(encoding="utf-8")
    )

    assert manifest["skeleton"] == "skeleton/skeleton.json"
    assert manifest["stages"]["skeleton"] == "complete"


def test_fit_requires_a_donor_with_an_extracted_skeleton(
    project_root: Path, glb_file: Path
) -> None:
    package = make_donor(project_root)
    (package / "inspection" / "report.json").unlink()
    make_target(project_root, glb_file)

    with pytest.raises(ConfigError, match="no extracted skeleton"):
        skeleton_fit.fit(Project(project_root), "trellis2/riyu-001", "donor")


def test_fit_requires_measured_target_bounds(
    project_root: Path, glb_file: Path
) -> None:
    make_donor(project_root)
    run = make_target(project_root, glb_file)
    (run / "riyu.measurements.json").unlink()

    with pytest.raises(ConfigError, match="no measurement sidecar"):
        skeleton_fit.fit(Project(project_root), "trellis2/riyu-001", "donor")
