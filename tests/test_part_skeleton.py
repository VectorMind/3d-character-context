"""A skeleton read out of a labelled volume.

The claim under test is narrow and checkable: a joint is the boundary between
two labelled regions, so it can be *measured* rather than proposed. These tests
build volumes whose boundaries are known by construction and ask whether the
joint comes back where the boundary actually is -- and, just as importantly,
whether the machinery says so when it cannot.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest

from character_context import body_parts, part_skeleton, voxels
from character_context.asset_models import DerivedSkeletonDocument
from character_context.config import ConfigError
from character_context.project import Project
from test_part_volume import make_donor

PITCH = 0.1
# Chosen so voxel index 16 sits exactly on the world origin, which makes an
# expected boundary position readable rather than something to work out.
ORIGIN = (-1.6, -1.6, -1.6)


def stacked(*spans: tuple[str, int, int], resolution: int = 32):
    """A square bar along z cut into named parts at known z indices."""
    labels = np.zeros((resolution,) * 3, dtype=np.int16)
    lo, hi = resolution // 2 - 3, resolution // 2 + 3
    for name, start, stop in spans:
        labels[lo:hi, lo:hi, start:stop] = body_parts.part_index(name)
    grid = voxels.Grid(labels > 0, ORIGIN, PITCH, resolution)
    return grid, labels


def z_of(index: int) -> float:
    """The world z of a boundary sitting between voxel `index-1` and `index`."""
    return ORIGIN[2] + index * PITCH


def test_a_joint_lands_on_the_boundary_between_two_regions() -> None:
    """The packet's whole proposition, on a volume whose answer is known."""
    grid, labels = stacked(("pelvis", 8, 16), ("abdomen", 16, 24))

    document = part_skeleton.build(grid, labels, "bar", {"seeds": "synthetic"})

    abdomen = next(
        bone for bone in document.armatures[0].bones if bone.name == "abdomen"
    )
    assert abdomen.parent == "pelvis"
    # The two regions meet across the face between voxel 15 and voxel 16.
    assert abdomen.head[2] == pytest.approx(z_of(16), abs=PITCH / 2)
    # ... and the joint is centred on the bar, not pulled to a corner.
    assert abdomen.head[0] == pytest.approx(0.0, abs=PITCH)
    assert abdomen.head[1] == pytest.approx(0.0, abs=PITCH)


def test_a_bone_ends_where_its_child_begins_so_the_chain_is_connected() -> None:
    grid, labels = stacked(("pelvis", 6, 14), ("abdomen", 14, 22), ("chest", 22, 28))

    document = part_skeleton.build(grid, labels, "bar", {"seeds": "synthetic"})
    bones = {bone.name: bone for bone in document.armatures[0].bones}

    assert bones["pelvis"].tail == pytest.approx(bones["abdomen"].head)
    assert bones["abdomen"].tail == pytest.approx(bones["chest"].head)
    assert bones["abdomen"].connected is True
    # The last link in the chain has no child joint to end at, so it runs to
    # the far end of its own region instead.
    assert bones["chest"].tail[2] > bones["chest"].head[2]
    assert document.derivation["tail_rule"]["chest"] == "farthest voxel of the part"


def test_roll_is_never_invented() -> None:
    """An occupancy grid carries no twist, and the document says so."""
    grid, labels = stacked(("pelvis", 8, 16), ("abdomen", 16, 24))

    document = part_skeleton.build(grid, labels, "bar", {"seeds": "synthetic"})

    assert all(bone.roll == 0.0 for bone in document.armatures[0].bones)
    assert any(
        "Roll is not derived" in line
        for line in document.derivation["limitations"]
    )


def test_the_hierarchy_is_declared_and_adjacency_is_reported_beside_it() -> None:
    """Contact area alone reparents a part; the declared table does not.

    `hand.L` is placed against `chest` with no `forearm.L` between them. The
    derived spanning tree therefore hangs it off the chest, and the declared
    hierarchy reattaches it up its own chain. Both readings are in the
    document, which is the point of keeping the check.
    """
    resolution = 32
    labels = np.zeros((resolution,) * 3, dtype=np.int16)
    labels[13:19, 13:19, 8:16] = body_parts.part_index("pelvis")
    labels[13:19, 13:19, 16:24] = body_parts.part_index("abdomen")
    labels[13:19, 13:19, 24:28] = body_parts.part_index("chest")
    # A hand stuck straight onto the chest, with no arm anywhere.
    labels[19:23, 13:19, 24:28] = body_parts.part_index("hand.L")
    grid = voxels.Grid(labels > 0, ORIGIN, PITCH, resolution)

    document = part_skeleton.build(grid, labels, "bar", {"seeds": "synthetic"})
    bones = {bone.name: bone for bone in document.armatures[0].bones}

    assert bones["hand.L"].parent == "chest"
    assert document.derivation["attachment"]["hand.L"]["by"] == "reattached"
    assert document.derivation["reattached_parts"] == ["hand.L"]
    check = document.derivation["adjacency_check"]
    assert check["available"] is True
    # Contact area reaches the same conclusion here, and it is compared against
    # the hierarchy actually in force rather than against the raw table: an
    # absent forearm is not evidence that adjacency disagrees about anatomy.
    assert check["disagreements"] == []
    assert check["agrees_with_declared"] == check["parts"] == 4


def test_a_volume_with_no_root_part_refuses_and_names_what_it_has() -> None:
    grid, labels = stacked(("abdomen", 10, 18), ("chest", 18, 26))

    with pytest.raises(ConfigError) as error:
        part_skeleton.build(grid, labels, "bar", {"seeds": "synthetic"})

    message = str(error.value)
    assert "pelvis" in message
    # A refusal that does not say what it did find is a refusal you cannot act
    # on, so the present parts are named.
    assert "abdomen" in message and "chest" in message


def test_absent_parts_are_listed_rather_than_silently_missing() -> None:
    grid, labels = stacked(("pelvis", 10, 18), ("abdomen", 18, 26))

    document = part_skeleton.build(grid, labels, "bar", {"seeds": "synthetic"})

    absent = document.derivation["absent_parts"]
    assert "head" in absent and "wing_arm.L" in absent
    assert len(absent) == len(body_parts.PARTS) - 2
    assert document.summary["bones"] == 2
    assert document.summary["joints"] == 1


def test_the_document_validates_against_its_own_schema() -> None:
    grid, labels = stacked(("pelvis", 8, 16), ("abdomen", 16, 24))

    document = part_skeleton.build(grid, labels, "bar", {"seeds": "synthetic"})
    round_trip = DerivedSkeletonDocument.model_validate_json(
        json.dumps(document.model_dump(by_alias=True))
    )

    assert round_trip.schema_id == "charctx.derived-skeleton/v1"
    assert round_trip.armatures[0].roots == [body_parts.ROOT_PART]


# --------------------------------------------------------------------------
# The donor side
# --------------------------------------------------------------------------


def test_a_donor_chain_collapses_to_one_segment_per_part() -> None:
    """Three spine bones become one pelvis-to-chest reading of the same rig."""
    skeleton = {
        "armatures": [
            {
                "bones": [
                    {
                        "name": "DEF-Spine",
                        "parent": None,
                        "head": [0.0, 0.0, 0.0],
                        "tail": [0.0, 0.0, 1.0],
                        "length": 1.0,
                    },
                    {
                        "name": "DEF-Spine.001",
                        "parent": "DEF-Spine",
                        "head": [0.0, 0.0, 1.0],
                        "tail": [0.0, 0.0, 2.0],
                        "length": 1.0,
                    },
                    {
                        "name": "DEF-Spine.002",
                        "parent": "DEF-Spine.001",
                        "head": [0.0, 0.0, 2.0],
                        "tail": [0.0, 0.0, 3.0],
                        "length": 1.0,
                    },
                ]
            }
        ]
    }
    mapping = {
        "DEF-Spine": "pelvis",
        "DEF-Spine.001": "abdomen",
        "DEF-Spine.002": "abdomen",
    }

    reference = part_skeleton.donor_reference(skeleton, mapping)

    assert reference["abdomen"]["parent"] == "pelvis"
    assert reference["abdomen"]["head"] == [0.0, 0.0, 1.0]
    assert reference["abdomen"]["tail"] == [0.0, 0.0, 3.0]
    assert reference["abdomen"]["bones"] == 2
    # One attachment point, so the donor places this joint unambiguously.
    assert reference["abdomen"]["head_spread"] == 0.0


def test_a_part_the_donor_attaches_twice_reports_its_spread() -> None:
    """A part with two genuine roots has no single true joint, and says so."""
    skeleton = {
        "armatures": [
            {
                "bones": [
                    {
                        "name": "DEF-Spine",
                        "parent": None,
                        "head": [0.0, 0.0, 0.0],
                        "tail": [0.0, 0.0, 1.0],
                        "length": 1.0,
                    },
                    {
                        "name": "near",
                        "parent": "DEF-Spine",
                        "head": [0.0, 0.0, 1.0],
                        "tail": [0.0, 0.0, 2.0],
                        "length": 1.0,
                    },
                    {
                        "name": "far",
                        "parent": "DEF-Spine",
                        "head": [0.0, 0.0, 4.0],
                        "tail": [0.0, 0.0, 5.0],
                        "length": 0.1,
                    },
                ]
            }
        ]
    }
    mapping = {"DEF-Spine": "pelvis", "near": "abdomen", "far": "abdomen"}

    reference = part_skeleton.donor_reference(skeleton, mapping)

    # The longer subtree wins the joint, and the disagreement is measured.
    assert reference["abdomen"]["root_bones"] == 2
    assert reference["abdomen"]["head"] == [0.0, 0.0, 1.0]
    assert reference["abdomen"]["head_spread"] == pytest.approx(3.0)


def test_deriving_from_a_donor_writes_a_skeleton_beside_its_parts(
    project_root: Path,
) -> None:
    package = make_donor(project_root)

    result = part_skeleton.derive(
        Project(project_root), "european-dragon", seeds="reference", resolution=40
    )

    path = package / "parts" / "skeleton.json"
    assert path.is_file()
    assert result["file"] == str(path)
    document = json.loads(path.read_text(encoding="utf-8"))
    assert document["schema"] == "charctx.derived-skeleton/v1"
    assert document["taxonomy"] == body_parts.TAXONOMY
    assert {bone["name"] for bone in document["armatures"][0]["bones"]} == {
        "pelvis",
        "abdomen",
        "chest",
    }


def test_scoring_measures_joint_error_against_the_donors_own_rig(
    project_root: Path,
) -> None:
    make_donor(project_root)

    result = part_skeleton.score(
        Project(project_root), "european-dragon", seeds="reference", resolution=40
    )

    assert result["hierarchy_matches_donor"] == result["hierarchy_total"] == 3
    assert result["scored_joints"] == 2
    # The reference labelling is the donor's own bones, so a joint read back
    # out of it should land within a voxel or two of where they put it.
    assert result["joint_error"]["mean_voxels"] < 4
    assert result["joint_error"]["median_pct"] < 0.05
    assert result["missing_from_donor"] == []
    assert {row["part"] for row in result["per_bone"]} == {
        "pelvis",
        "abdomen",
        "chest",
    }


def test_a_run_cannot_be_labelled_from_a_rig_it_does_not_have(
    project_root: Path,
) -> None:
    with pytest.raises(ConfigError) as error:
        part_skeleton.derive(
            Project(project_root), "trellis2/run-001", seeds="reference"
        )

    assert "no authored rig" in str(error.value)


def test_an_unknown_seeding_is_refused_by_name() -> None:
    with pytest.raises(ConfigError) as error:
        part_skeleton._labelled(None, "european-dragon", "vibes", 32)

    assert "vibes" in str(error.value)
    assert "reference" in str(error.value)


def test_the_declared_hierarchy_is_total_and_acyclic() -> None:
    """Every part reaches the root, so no bone can be orphaned by the table."""
    for part in body_parts.PARTS:
        assert part.name in body_parts.PART_PARENT
        seen = {part.name}
        current = body_parts.PART_PARENT[part.name]
        while current is not None:
            assert current not in seen, f"{part.name} cycles through {current}"
            seen.add(current)
            current = body_parts.PART_PARENT[current]
        assert body_parts.ROOT_PART in seen or part.name == body_parts.ROOT_PART

    assert body_parts.PART_PARENT[body_parts.ROOT_PART] is None
    assert [
        name for name, parent in body_parts.PART_PARENT.items() if parent is None
    ] == [body_parts.ROOT_PART]


def test_geodesic_distance_goes_through_the_volume_not_across_the_air() -> None:
    """A U-shaped bar: the two tips are neighbours in space and far apart in it."""
    mask = np.zeros((24, 8, 24), dtype=bool)
    mask[4:20, 2:6, 4:8] = True   # one arm
    mask[4:20, 2:6, 16:20] = True  # the other arm
    mask[16:20, 2:6, 4:20] = True  # the bend joining them
    seed = np.zeros_like(mask)
    seed[4, 3, 5] = True

    distance = voxels.geodesic(mask, seed)
    far = voxels.farthest(mask, seed)

    # Straight-line neighbours across the gap ...
    assert math.dist((4, 3, 5), (4, 3, 17)) == pytest.approx(12.0)
    # ... but the walk has to go down one arm, round the bend and back up.
    assert distance[4, 3, 17] > 30
    assert far[0] < 8 and far[2] > 12
    assert distance[mask].min() == 0
    assert (distance[~mask] == -1).all()


def test_interfaces_find_only_touching_pairs() -> None:
    labels = np.zeros((12, 12, 12), dtype=np.int16)
    labels[2:10, 2:10, 2:6] = 1
    labels[2:10, 2:10, 6:10] = 2
    # A third region held one voxel clear of both.
    labels[2:10, 2:10, 11:12] = 3

    found = voxels.interfaces(labels)

    assert set(found) == {frozenset((1, 2))}
    assert len(found[frozenset((1, 2))]) == 64
