"""Labelled volumes: a reference from an authored rig, a proposal from geometry.

The scored comparison between the two is the point. A method that labels a
volume beautifully and has never been checked against an answer key is an
opinion, so these tests care most about whether the machinery that produces
the number is honest about what it could not place.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest
import trimesh

from character_context import assets, body_parts, part_volume
from character_context.asset_models import AssetFrontMatter
from character_context.config import ConfigError
from character_context.project import Project

IDENTITY = [
    [1.0, 0.0, 0.0, 0.0],
    [0.0, 1.0, 0.0, 0.0],
    [0.0, 0.0, 1.0, 0.0],
    [0.0, 0.0, 0.0, 1.0],
]

# A three-bone spine along z, which the european-dragon rules map to pelvis,
# abdomen and chest. Small on purpose: what is under test is the plumbing and
# the reporting, not a dragon.
SPINE = (
    ("DEF-Spine", None, (0.0, 0.0, -0.6), (0.0, 0.0, -0.2)),
    ("DEF-Spine.001", "DEF-Spine", (0.0, 0.0, -0.2), (0.0, 0.0, 0.2)),
    ("DEF-Spine.003", "DEF-Spine.001", (0.0, 0.0, 0.2), (0.0, 0.0, 0.6)),
)


def make_donor(project_root: Path, donor_id: str = "european-dragon") -> Path:
    package = project_root / "assets" / "collected" / donor_id
    for name in ("source", "inspection", "previews", "web"):
        (package / name).mkdir(parents=True, exist_ok=True)
    (package / "source" / "donor.blend").write_bytes(b"blend")
    assets._write_readme(
        package,
        AssetFrontMatter(
            id=donor_id,
            title="Donor dragon",
            kind="donor",
            primary_file="source/donor.blend",
        ),
    )

    # A capsule-ish body the bones sit inside.
    body = trimesh.creation.capsule(height=1.2, radius=0.25)
    spin = trimesh.transformations.rotation_matrix(math.pi / 2, [1, 0, 0])
    body.apply_transform(spin)
    body.apply_translation((0.0, 0.0, 0.0))
    trimesh.Scene({"body": body}).export(package / "web" / "model.glb")

    bones = [
        {
            "name": name,
            "parent": parent,
            "deform": True,
            "connected": parent is not None,
            "depth": index,
            "head": list(head),
            "tail": list(tail),
            "head_local": list(head),
            "tail_local": list(tail),
            "length": math.dist(head, tail),
            "roll": 0.0,
            "matrix_local": IDENTITY,
        }
        for index, (name, parent, head, tail) in enumerate(SPINE)
    ]
    skeleton = {
        "schema": "charctx.skeleton/v1",
        "asset_id": donor_id,
        "blender_version": "5.2.1-test",
        "source_model": "donor.blend",
        "coordinate_system": {"viewer_space": "right-handed, +Y up, -Z forward"},
        "armatures": [
            {
                "name": "rig",
                "pose_position": "POSE",
                "object_matrix": IDENTITY,
                "bones": bones,
                "roots": ["DEF-Spine"],
                "leaves": ["DEF-Spine.003"],
                "max_depth": 2,
                "bounds_min": [0.0, 0.0, -0.6],
                "bounds_max": [0.0, 0.0, 0.6],
                "total_length": 1.2,
                "deform_total_length": 1.2,
                "name_signals": {},
            }
        ],
        "summary": {"armatures": 1, "bones": 3, "deform_bones": 3},
    }
    (package / "inspection" / "skeleton.json").write_text(
        json.dumps(skeleton), encoding="utf-8"
    )
    (package / "inspection" / "skin-weights.json").write_text(
        json.dumps(
            {
                "schema": "charctx.skin-weights/v1",
                "asset_id": donor_id,
                "source_model": "donor.blend",
                "encoding": "csr-per-vertex",
                "bindings": [
                    {
                        "mesh": "Body",
                        "armature": "rig",
                        "vertices": 4,
                        "bone_names": [name for name, _, _, _ in SPINE],
                        "vertex_offsets": [0, 1, 2, 3, 4],
                        "bone_indices": [0, 1, 2, 0],
                        "weights": [1.0, 1.0, 1.0, 1.0],
                    }
                ],
                "summary": {"bindings": 1},
            }
        ),
        encoding="utf-8",
    )
    (package / "inspection" / "report.json").write_text(
        json.dumps(
            {
                "schema": "charctx.inspection/v1",
                "asset_id": donor_id,
                "blender_version": "5.2.1-test",
                "primary_model": "donor.blend",
                "source_files": [],
                "objects": {"total": 2, "types": {"MESH": 1, "ARMATURE": 1}},
                "meshes": [],
                "armatures": [{"name": "rig", "bones": 3}],
                "actions": [],
                "materials": [],
                "images": [],
                "bounds": {
                    "min": [-0.25, -0.25, -0.85],
                    "max": [0.25, 0.25, 0.85],
                    "extents": [0.5, 0.5, 1.7],
                },
                "warnings": [],
                "web_measurements": {
                    "vertices": 8,
                    "faces": 12,
                    "bounds_min": [-0.25, -0.25, -0.85],
                    "bounds_max": [0.25, 0.25, 0.85],
                },
                "skeleton": {
                    "path": "inspection/skeleton.json",
                    "bytes": 1,
                    "sha256": "x",
                    "schema": "charctx.skeleton/v1",
                    "summary": {"bones": 3},
                },
                "skin_weights": {
                    "path": "inspection/skin-weights.json",
                    "bytes": 1,
                    "sha256": "y",
                    "schema": "charctx.skin-weights/v1",
                    "summary": {"bindings": 1},
                },
            }
        ),
        encoding="utf-8",
    )
    return package


def test_a_reference_labels_the_whole_volume_and_names_what_is_absent(
    project_root: Path,
) -> None:
    package = make_donor(project_root)

    result = part_volume.reference(
        Project(project_root), "european-dragon", resolution=40
    )
    document = json.loads((package / "parts" / "parts.json").read_text())

    assert document["schema"] == part_volume.SCHEMA
    assert document["taxonomy"] == body_parts.TAXONOMY
    assert document["derivation"]["reference"] is True
    # Every solid voxel is claimed: the taxonomy is total over the volume.
    assert document["summary"]["labelled_fraction"] == pytest.approx(1.0)
    assert result["summary"]["parts_present"] == 3
    # The 26 parts this three-bone rig has no bones for are listed at zero,
    # not quietly dropped.
    assert set(result["empty_parts"]) == {
        part.name for part in body_parts.PARTS
    } - {"pelvis", "abdomen", "chest"}
    assert len(result["empty_parts"]) == len(body_parts.PARTS) - 3
    assert [entry["name"] for entry in document["parts"]] == [
        part.name for part in body_parts.PARTS
    ]


def test_a_reference_proves_its_map_covers_every_weight_bearing_bone(
    project_root: Path,
) -> None:
    make_donor(project_root)

    result = part_volume.reference(
        Project(project_root), "european-dragon", resolution=32
    )

    coverage = result["weight_coverage"]
    assert coverage["available"] is True
    assert coverage["total"] is True
    assert coverage["unmapped"] == []


def test_the_display_grid_is_pooled_rather_than_shipped_whole(
    project_root: Path,
) -> None:
    """The browser gets a decimated diagnostic, never the computation grid."""
    package = make_donor(project_root)

    part_volume.reference(Project(project_root), "european-dragon", resolution=40)
    document = json.loads((package / "parts" / "parts.json").read_text())

    assert document["grid"]["resolution"] == 40
    assert document["grid"]["display_resolution"] == 20
    assert len(document["voxels"]["index"]) == len(document["voxels"]["part"])
    assert len(document["voxels"]["index"]) < document["summary"]["solid_voxels"]


def test_landmark_seeding_cannot_reach_the_interior_chain_segments() -> None:
    """The structural gap this packet exists to expose.

    Nine parts have no landmark that stands for them, so a landmark-seeded
    segmentation cannot produce them at all -- they are absent by
    construction rather than misplaced. Every one of them is an interior
    chain segment or the jaw: exactly the joints the Riyu packet already
    declined to propose.
    """
    reachable = set(part_volume.LANDMARK_PARTS.values())
    every = {part.name for part in body_parts.PARTS}

    assert reachable <= every
    assert every - reachable == {
        "jaw",
        "upper_arm.L",
        "upper_arm.R",
        "forearm.L",
        "forearm.R",
        "shin.L",
        "shin.R",
        "wing_arm.L",
        "wing_arm.R",
    }


def test_the_head_carries_more_anchors_than_any_other_part() -> None:
    """A bulb on the end of a chain needs more than one seed to hold itself.

    With two, `head` lost its crown to `neck`, which was anchored higher up on
    the shared dorsal crest. The count is the fix, so it is the thing asserted.
    """
    anchors: dict[str, int] = {}
    for part in part_volume.LANDMARK_PARTS.values():
        anchors[part] = anchors.get(part, 0) + 1

    assert anchors["head"] == 4
    assert anchors["neck"] == 2
    assert max(anchors.values()) == anchors["head"]


def test_head_sub_parts_are_seedable_only_through_the_manual_overlay() -> None:
    """Geometry does not propose an eye, so the overlay is the only route in."""
    from character_context import landmarks as landmarks_mod

    for name in ("eye.L", "eye.R", "ear.L", "ear.R", "nostril"):
        assert part_volume.LANDMARK_PARTS[name] == name
        assert name in landmarks_mod.NOT_ATTEMPTED
        assert name in landmarks_mod.MANUAL_ALLOWED


def test_scoring_isolates_the_cost_of_sparsity(project_root: Path) -> None:
    make_donor(project_root)

    result = part_volume.score(
        Project(project_root), "european-dragon", mode="centroid", resolution=40
    )

    metrics = result["metrics"]
    assert result["proposal_seed_points"] < result["reference_seed_points"]
    # Per-part, never a single aggregate: one number would let a lost part
    # hide behind a large one that scored well.
    assert {row["part"] for row in metrics["per_part"]} == {
        "pelvis",
        "abdomen",
        "chest",
    }
    assert 0.0 <= metrics["mean_iou"] <= 1.0
    assert 0.0 <= metrics["voxel_accuracy"] <= 1.0
    assert len(result["unseedable_parts"]) == len(body_parts.PARTS) - 3


def test_an_unknown_scoring_mode_is_rejected(project_root: Path) -> None:
    make_donor(project_root)

    with pytest.raises(ConfigError, match="Unknown scoring mode"):
        part_volume.score(Project(project_root), "european-dragon", mode="vibes")


def test_segmentation_refuses_to_run_without_landmarks(
    project_root: Path, glb_file: Path
) -> None:
    import shutil

    run = project_root / "generated" / "trellis2" / "riyu-001"
    run.mkdir(parents=True)
    shutil.copy2(glb_file, run / "riyu.glb")
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

    with pytest.raises(ConfigError, match="needs proposed landmarks"):
        part_volume.segment(Project(project_root), "trellis2/riyu-001")
