"""The landmark-driven chain fit takes joints from the target, not the donor.

The claim step 3 rests on is that a donor's rest pose cannot reach the fitted
skeleton: only its hierarchy and its per-chain proportions do. That claim is
falsifiable, so it is tested directly -- move the donor's coordinates anywhere
and every anchored joint must stay where it was.
"""

from __future__ import annotations

import json
import math
import shutil
from pathlib import Path

import pytest

from character_context import assets, chain_fit, generations, skeleton_fit
from character_context.asset_models import (
    AssetFrontMatter,
    LandmarkDocument,
    SkeletonDocument,
)
from character_context.config import ConfigError
from character_context.project import Project

IDENTITY_MATRIX = [
    [1.0, 0.0, 0.0, 0.0],
    [0.0, 1.0, 0.0, 0.0],
    [0.0, 0.0, 1.0, 0.0],
    [0.0, 0.0, 0.0, 1.0],
]


def bone(
    name: str,
    parent: str | None,
    head: tuple[float, float, float],
    tail: tuple[float, float, float],
    *,
    depth: int = 0,
    roll: float = 0.25,
) -> dict:
    length = math.dist(head, tail)
    return {
        "name": name,
        "parent": parent,
        "deform": True,
        "connected": parent is not None,
        "depth": depth,
        "head": list(head),
        "tail": list(tail),
        "head_local": list(head),
        "tail_local": list(tail),
        "length": length,
        "roll": roll,
        "matrix_local": IDENTITY_MATRIX,
    }


def skeleton(bones: list[dict], asset_id: str = "donor") -> SkeletonDocument:
    points = [point for item in bones for point in (item["head"], item["tail"])]
    roots = [item["name"] for item in bones if item["parent"] is None]
    names = {item["name"] for item in bones}
    return SkeletonDocument.model_validate(
        {
            "schema": "charctx.skeleton/v1",
            "asset_id": asset_id,
            "blender_version": "5.2.1-test",
            "source_model": "donor.blend",
            "coordinate_system": {"viewer_space": "right-handed, +Y up, -Z forward"},
            "armatures": [
                {
                    "name": "rig",
                    "pose_position": "POSE",
                    "object_matrix": IDENTITY_MATRIX,
                    "bones": bones,
                    "roots": roots,
                    "leaves": [
                        item["name"]
                        for item in bones
                        if item["name"]
                        not in {
                            other["parent"] for other in bones if other["parent"]
                        }
                    ],
                    "max_depth": max(item["depth"] for item in bones),
                    "bounds_min": [
                        min(point[axis] for point in points) for axis in range(3)
                    ],
                    "bounds_max": [
                        max(point[axis] for point in points) for axis in range(3)
                    ],
                    "total_length": sum(item["length"] for item in bones),
                    "deform_total_length": sum(item["length"] for item in bones),
                    "name_signals": {},
                }
            ],
            "summary": {
                "armatures": 1,
                "bones": len(bones),
                "deform_bones": len(bones),
                "roots": len(roots),
                "leaves": len(names - {item["parent"] for item in bones}),
                "max_depth": max(item["depth"] for item in bones),
            },
        }
    )


def landmarks(points: dict[str, tuple[float, float, float]]) -> LandmarkDocument:
    def side(name: str) -> str:
        if name.endswith(".L"):
            return "left"
        return "right" if name.endswith(".R") else "center"

    return LandmarkDocument.model_validate(
        {
            "schema": "charctx.landmarks/v1",
            "target_id": "trellis2/riyu-001",
            "method": "test/v1",
            "coordinate_system": {
                "symmetry_axis": "x",
                "body_axis": "z",
                "up_axis": "y",
            },
            "derivation": {"symmetry_plane": 0.0},
            "landmarks": [
                {
                    "name": name,
                    "point": list(point),
                    "side": side(name),
                    "source": "manual",
                    "confidence": "high",
                    "evidence": "fixture",
                }
                for name, point in points.items()
            ],
            "summary": {"landmarks": len(points)},
        }
    )


# --------------------------------------------------------------------------
# The geometry
# --------------------------------------------------------------------------


def test_a_chain_is_redistributed_along_the_target_by_donor_proportion() -> None:
    """Bone 2 is twice bone 1, so it takes twice the path on the target."""
    donor = skeleton(
        [
            bone("a", None, (0, 0, 0), (1, 0, 0), depth=0),
            bone("b", "a", (1, 0, 0), (3, 0, 0), depth=1),
            bone("c", "b", (3, 0, 0), (4, 0, 0), depth=2),
        ]
    )
    marks = landmarks({"start": (0, 0, 0), "end": (0, 0, 8)})
    spec = chain_fit.ChainSpec(
        name="axis", bones=("a", "b", "c"), landmarks=("start", "end"),
        from_parent=False,
    )

    armatures, derivation, anchored = chain_fit.place(
        donor, marks, chain_fit.Similarity(), (spec,)
    )
    placed = {item.name: item for item in armatures[0].bones}

    assert anchored == {"a", "b", "c"}
    # Donor lengths 1:2:1 over a target path of 8 -> 2, 4, 2.
    assert placed["a"].head == pytest.approx((0, 0, 0))
    assert placed["a"].tail == pytest.approx((0, 0, 2))
    assert placed["b"].tail == pytest.approx((0, 0, 6))
    assert placed["c"].tail == pytest.approx((0, 0, 8))
    assert derivation["chains"][0]["scale"] == pytest.approx(2.0)


def test_the_donor_rest_pose_cannot_reach_an_anchored_joint() -> None:
    """Move the donor anywhere; the anchored fit must not notice.

    This is the whole argument for step 3 over step 1, so it is asserted
    rather than described: only donor bone *lengths* may influence the result.
    """
    original = [
        bone("a", None, (0, 0, 0), (1, 0, 0), depth=0),
        bone("b", "a", (1, 0, 0), (3, 0, 0), depth=1),
    ]
    # Same lengths, wholly different placement and direction.
    moved = [
        bone("a", None, (10, -4, 7), (10, -3, 7), depth=0),
        bone("b", "a", (10, -3, 7), (10, -1, 7), depth=1),
    ]
    marks = landmarks({"start": (0, 0, 0), "end": (0, 0, 9)})
    spec = chain_fit.ChainSpec(
        name="axis", bones=("a", "b"), landmarks=("start", "end"), from_parent=False
    )

    def joints(bones: list[dict]) -> list[tuple[float, ...]]:
        armatures, _, _ = chain_fit.place(
            skeleton(bones), marks, chain_fit.Similarity(), (spec,)
        )
        return [
            point for item in armatures[0].bones for point in (item.head, item.tail)
        ]

    assert joints(original) == pytest.approx(joints(moved))


def test_a_chain_ends_exactly_on_its_terminal_landmarks() -> None:
    donor = skeleton(
        [
            bone("a", None, (0, 0, 0), (1, 0, 0), depth=0),
            bone("b", "a", (1, 0, 0), (2, 0, 0), depth=1),
        ]
    )
    marks = landmarks({"start": (0.1, 0.2, 0.3), "end": (-0.4, 0.5, 0.6)})
    spec = chain_fit.ChainSpec(
        name="axis", bones=("a", "b"), landmarks=("start", "end"), from_parent=False
    )

    armatures, derivation, _ = chain_fit.place(
        donor, marks, chain_fit.Similarity(), (spec,)
    )
    placed = {item.name: item for item in armatures[0].bones}

    assert placed["a"].head == pytest.approx((0.1, 0.2, 0.3))
    assert placed["b"].tail == pytest.approx((-0.4, 0.5, 0.6))
    assert derivation["landmark_residual"]["start"] == pytest.approx(0.0)
    assert derivation["landmark_residual"]["end"] == pytest.approx(0.0)


def test_a_bone_no_chain_claims_rides_in_its_parents_frame() -> None:
    """A carried bone keeps its donor offset, rotated and scaled by its parent."""
    donor = skeleton(
        [
            bone("a", None, (0, 0, 0), (2, 0, 0), depth=0),
            # A finger hanging off the chain's end, one unit further along.
            bone("finger", "a", (2, 0, 0), (3, 0, 0), depth=1),
        ]
    )
    marks = landmarks({"start": (0, 0, 0), "end": (0, 0, 4)})
    spec = chain_fit.ChainSpec(
        name="axis", bones=("a",), landmarks=("start", "end"), from_parent=False
    )

    armatures, derivation, anchored = chain_fit.place(
        donor, marks, chain_fit.Similarity(), (spec,)
    )
    placed = {item.name: item for item in armatures[0].bones}

    assert anchored == {"a"}
    assert derivation["carried_bones"] == 1
    # The parent was aimed +x -> +z and doubled, so the finger follows.
    assert placed["finger"].head == pytest.approx((0, 0, 4))
    assert placed["finger"].tail == pytest.approx((0, 0, 6))


def test_a_chain_with_missing_landmarks_is_skipped_with_its_reason() -> None:
    donor = skeleton([bone("a", None, (0, 0, 0), (1, 0, 0), depth=0)])
    marks = landmarks({"start": (0, 0, 0)})
    spec = chain_fit.ChainSpec(
        name="axis", bones=("a",), landmarks=("start", "end"), from_parent=False
    )

    armatures, derivation, anchored = chain_fit.place(
        donor, marks, chain_fit.Similarity(scale=3.0), (spec,)
    )

    assert anchored == set()
    assert derivation["chains"] == []
    assert derivation["chains_skipped"] == [
        {"chain": "axis", "reason": "landmarks absent: end"}
    ]
    # Nothing is dropped: the bone falls back to the rigid transform.
    assert armatures[0].bones[0].tail == pytest.approx((3, 0, 0))


def test_mirrored_landmarks_produce_a_mirrored_fit() -> None:
    donor = skeleton(
        [
            bone("root", None, (0, 0, 0), (0, 0, 1), depth=0),
            bone("limb.L", "root", (0, 0, 1), (1, 0, 1), depth=1),
            bone("limb.R", "root", (0, 0, 1), (-1, 0, 1), depth=1),
        ]
    )
    marks = landmarks(
        {
            "spine_a": (0, 0, 0),
            "spine_b": (0, 0, 2),
            "tip.L": (3, 0, 2),
            "tip.R": (-3, 0, 2),
        }
    )
    specs = (
        chain_fit.ChainSpec(
            name="spine", bones=("root",), landmarks=("spine_a", "spine_b"),
            from_parent=False,
        ),
        *(
            chain_fit.ChainSpec(
                name=f"limb.{side}",
                bones=(f"limb.{side}",),
                landmarks=(f"tip.{side}",),
            )
            for side in ("L", "R")
        ),
    )

    _, derivation, _ = chain_fit.place(donor, marks, chain_fit.Similarity(), specs)

    assert derivation["symmetry"]["pairs"] == 1
    assert derivation["symmetry"]["max"] == pytest.approx(0.0, abs=1e-9)


@pytest.mark.parametrize(
    "target",
    [(0, 0, 1), (0, 0, -1), (1, 0, 0), (0.6, 0.8, 0.0)],
)
def test_the_swing_rotation_stays_a_rotation(target: tuple[float, ...]) -> None:
    """Including the antiparallel case, which has no unique axis."""
    rotation = chain_fit._swing((0.0, 0.0, 1.0), target)  # type: ignore[arg-type]

    for row in range(3):
        assert sum(value * value for value in rotation[row]) == pytest.approx(1.0)
        for other in range(row + 1, 3):
            assert sum(
                rotation[row][axis] * rotation[other][axis] for axis in range(3)
            ) == pytest.approx(0.0, abs=1e-9)
    determinant = sum(
        rotation[0][index]
        * (
            rotation[1][(index + 1) % 3] * rotation[2][(index + 2) % 3]
            - rotation[1][(index + 2) % 3] * rotation[2][(index + 1) % 3]
        )
        for index in range(3)
    )
    assert determinant == pytest.approx(1.0)
    assert chain_fit._apply_matrix(rotation, (0.0, 0.0, 1.0)) == pytest.approx(target)


# --------------------------------------------------------------------------
# End to end, through the command
# --------------------------------------------------------------------------

SPINE_BONES = (
    "DEF-Spine",
    *(f"DEF-Spine.{index:03d}" for index in range(1, 6)),
    "DEF-neck",
    *(f"DEF-neck.{index:03d}" for index in range(1, 5)),
)


def make_donor(project_root: Path) -> Path:
    """A donor carrying the real spine chain plus three carried stubs."""
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
    bones = [
        bone(
            name,
            None if index == 0 else SPINE_BONES[index - 1],
            (0.0, 0.0, float(index)),
            (0.0, 0.0, float(index + 1)),
            depth=index,
        )
        for index, name in enumerate(SPINE_BONES)
    ]
    bones.append(
        bone("DEF-Teeth_Top", "DEF-neck.004", (0, 0, 11), (0, 0, 12), depth=11)
    )
    for side, sign in (("L", 1.0), ("R", -1.0)):
        bones.append(
            bone(f"DEF-Hip.{side}", "DEF-Spine", (0, 0, 0), (sign, 0, 0), depth=1)
        )
    (package / "inspection" / "skeleton.json").write_text(
        skeleton(bones).model_dump_json(by_alias=True), encoding="utf-8"
    )
    (package / "inspection" / "report.json").write_text(
        json.dumps(
            {
                "schema": "charctx.inspection/v1",
                "asset_id": "donor",
                "blender_version": "5.2.1-test",
                "primary_model": "donor.blend",
                "source_files": [],
                "objects": {"total": 2, "types": {"MESH": 1, "ARMATURE": 1}},
                "meshes": [],
                "armatures": [{"name": "rig", "bones": len(bones)}],
                "actions": [],
                "materials": [],
                "images": [],
                "bounds": {"min": [-1, 0, 0], "max": [1, 0, 12], "extents": [2, 0, 12]},
                "warnings": [],
                "web_measurements": {
                    "vertices": 8,
                    "faces": 12,
                    "bounds_min": [-1.0, 0.0, 0.0],
                    "bounds_max": [1.0, 0.0, 12.0],
                },
                "skeleton": {
                    "path": "inspection/skeleton.json",
                    "bytes": 1,
                    "sha256": "x",
                    "schema": "charctx.skeleton/v1",
                    "summary": {"bones": len(bones)},
                },
            }
        ),
        encoding="utf-8",
    )
    return package


def make_target(project_root: Path, glb_file: Path) -> Path:
    run = project_root / "generated" / "trellis2" / "riyu-001"
    run.mkdir(parents=True)
    shutil.copy2(glb_file, run / "riyu.glb")
    (run / "riyu.measurements.json").write_text(
        json.dumps(
            {
                "vertices": 162,
                "faces": 320,
                "bounds_min": [-1.0, -1.0, -1.0],
                "bounds_max": [1.0, 1.0, 1.0],
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


def write_landmarks(run: Path) -> None:
    (run / "skeleton").mkdir(parents=True, exist_ok=True)
    marks = landmarks(
        {
            "hip_center": (0.0, 0.0, -0.5),
            "spine_mid": (0.0, 0.0, -0.2),
            "chest": (0.0, 0.0, 0.1),
            "neck_base": (0.0, 0.1, 0.3),
            "skull": (0.0, 0.15, 0.45),
            "snout": (0.0, 0.15, 0.6),
        }
    )
    (run / "skeleton" / "landmarks.json").write_text(
        marks.model_dump_json(by_alias=True), encoding="utf-8"
    )


def test_the_command_anchors_the_spine_and_reports_what_it_could_not_fit(
    project_root: Path, glb_file: Path
) -> None:
    make_donor(project_root)
    run = make_target(project_root, glb_file)
    write_landmarks(run)

    result = skeleton_fit.fit(Project(project_root), "trellis2/riyu-001", "donor")
    document = json.loads((run / "skeleton" / "skeleton.json").read_text())

    assert result["method"] == chain_fit.METHOD
    assert document["derivation"]["method"] == chain_fit.METHOD
    assert result["anchored_bones"] == 11
    assert result["carried_bones"] == 3
    # Every chain the fixture donor has no bones for says so by name rather
    # than vanishing from the record.
    skipped = {entry["chain"] for entry in result["chains_skipped"]}
    assert skipped == {"tail", "wing.L", "wing.R", "foreleg.L", "foreleg.R",
                       "hindleg.L", "hindleg.R"}
    assert result["containment"]["anchored"]["outside_bounds"] == 0


def test_the_chain_fit_keeps_the_previous_method_for_comparison(
    project_root: Path, glb_file: Path
) -> None:
    make_donor(project_root)
    run = make_target(project_root, glb_file)
    write_landmarks(run)
    project = Project(project_root)

    skeleton_fit.fit(project, "trellis2/riyu-001", "donor", method="rigid")
    skeleton_fit.fit(project, "trellis2/riyu-001", "donor", method="chain")
    manifest = json.loads((run / generations.VIEWER_FILE).read_text())

    assert manifest["skeleton"] == "skeleton/skeleton.json"
    assert manifest["skeleton_alternate"] == "skeleton/fits/uniform-contain-bounds.json"
    assert (run / "skeleton" / "fits" / "landmark-chain.json").is_file()
    stage = json.loads((run / "skeleton" / "manifest.json").read_text())
    assert stage["method"] == chain_fit.METHOD
    assert stage["fits"] == [
        "skeleton/fits/landmark-chain.json",
        "skeleton/fits/uniform-contain-bounds.json",
    ]


def test_the_chain_method_refuses_to_run_without_landmarks(
    project_root: Path, glb_file: Path
) -> None:
    make_donor(project_root)
    make_target(project_root, glb_file)

    with pytest.raises(ConfigError, match="needs proposed landmarks"):
        skeleton_fit.fit(Project(project_root), "trellis2/riyu-001", "donor")


def test_an_unknown_method_is_rejected(project_root: Path, glb_file: Path) -> None:
    make_donor(project_root)
    make_target(project_root, glb_file)

    with pytest.raises(ConfigError, match="Unknown fit method"):
        skeleton_fit.fit(
            Project(project_root), "trellis2/riyu-001", "donor", method="magic"
        )
