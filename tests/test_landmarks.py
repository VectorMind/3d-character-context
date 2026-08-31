"""Landmarks are proposed from geometry alone, with their limits declared."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from character_context import generations, landmarks
from character_context.asset_models import LandmarkDocument
from character_context.config import ConfigError
from character_context.project import Project


@pytest.fixture
def creature_glb(tmp_path: Path) -> Path:
    """A stand-in quadruped: symmetric in x, long in z, four legs, two wings.

    Deliberately crude — the proposal must key off symmetry, elongation and
    extremes, not off anything dragon-specific.
    """
    import numpy as np
    import trimesh

    def block(extents, translation):
        # Subdivided: the proposal clusters ground-contact vertices, so a
        # corners-only box would starve it of the density a real mesh has.
        mesh = trimesh.creation.box(extents=extents)
        for _ in range(3):
            mesh = mesh.subdivide()
        mesh.apply_translation(translation)
        return mesh

    parts = [block((0.30, 0.30, 1.40), (0, 0, 0))]
    # Head end at +z, so a correct run reports `head_towards: positive`. The
    # tail is a long taper at -z; the head is a short blunt block.
    parts.append(block((0.26, 0.26, 0.30), (0, 0.05, 0.85)))
    for index in range(14):
        fraction = index / 14
        width = 0.26 * (1 - fraction) + 0.02
        parts.append(block((width, width, 0.10), (0, 0, -0.75 - index * 0.10)))
    for x in (-0.18, 0.18):
        for z in (0.45, -0.45):
            parts.append(block((0.12, 0.60, 0.12), (x, -0.42, z)))
    for x in (-0.9, 0.9):
        parts.append(block((1.4, 0.04, 0.40), (x, 0.10, 0.40)))
    scene = trimesh.Scene({f"part{index}": part for index, part in enumerate(parts)})
    path = tmp_path / "creature.glb"
    scene.export(path)
    assert np.isfinite(scene.bounds).all()
    return path


def make_run(project_root: Path, model: Path) -> Path:
    run = project_root / "generated" / "trellis2" / "creature-001"
    run.mkdir(parents=True)
    import shutil

    shutil.copy2(model, run / "creature.glb")
    (run / "request.json").write_text(
        json.dumps(
            {
                "backend": "trellis2",
                "request": {"name": "creature", "seed": 1},
                "artifacts": ["creature.glb"],
            }
        ),
        encoding="utf-8",
    )
    return run


def test_proposal_finds_the_symmetry_plane_and_body_axis(creature_glb: Path) -> None:
    document = landmarks.propose(creature_glb, "trellis2/creature-001")

    assert document.schema_id == "charctx.landmarks/v1"
    assert document.coordinate_system["symmetry_axis"] == "x"
    assert document.coordinate_system["body_axis"] == "z"
    assert document.coordinate_system["up_axis"] == "y"
    # The mirror axis must win on evidence, not by a wide-enough margin to be
    # a coincidence.
    residual = document.derivation["mirror_residual_median"]
    assert residual["x"] < residual["y"]
    assert residual["x"] < residual["z"]


def test_proposal_orients_the_head_by_taper(creature_glb: Path) -> None:
    document = landmarks.propose(creature_glb, "trellis2/creature-001")
    points = {mark.name: mark.point for mark in document.landmarks}

    assert document.derivation["head_towards"] == "positive"
    # The blunt end is the head; the long taper is the tail.
    assert points["snout"][2] > points["chest"][2] > points["hip_center"][2]
    assert points["hip_center"][2] > points["tail_base"][2] > points["tail_tip"][2]


def test_paired_landmarks_are_mirrored_and_sided(creature_glb: Path) -> None:
    document = landmarks.propose(creature_glb, "trellis2/creature-001")
    points = {mark.name: mark.point for mark in document.landmarks}
    sides = {mark.name: mark.side for mark in document.landmarks}

    for base in ("wing_tip", "foot_front", "foot_hind"):
        left, right = points[f"{base}.L"], points[f"{base}.R"]
        assert sides[f"{base}.L"] == "left"
        assert sides[f"{base}.R"] == "right"
        # Opposite sides of the plane, and mirror images along it.
        assert left[0] * right[0] < 0
        assert left[0] == pytest.approx(-right[0], abs=0.05)
        assert left[2] == pytest.approx(right[2], abs=0.05)


def test_girdles_anchor_to_the_feet_rather_than_to_a_guess(
    creature_glb: Path,
) -> None:
    """The centre chain must agree with the paired landmarks it shares evidence with."""
    document = landmarks.propose(creature_glb, "trellis2/creature-001")
    points = {mark.name: mark.point for mark in document.landmarks}
    confidence = {mark.name: mark.confidence for mark in document.landmarks}

    assert points["chest"][2] == pytest.approx(points["shoulder.L"][2], abs=1e-6)
    assert points["hip_center"][2] == pytest.approx(points["hip.L"][2], abs=1e-6)
    assert confidence["chest"] == "high"
    assert confidence["hip_center"] == "high"


def test_interior_joints_are_declared_unattempted_not_guessed(
    creature_glb: Path,
) -> None:
    document = landmarks.propose(creature_glb, "trellis2/creature-001")
    names = {mark.name for mark in document.landmarks}

    for skipped in landmarks.NOT_ATTEMPTED:
        assert skipped not in names
    assert set(document.derivation["not_attempted"]) == set(landmarks.NOT_ATTEMPTED)
    assert document.derivation["limitations"]
    assert all(mark.source == "geometric" for mark in document.landmarks)


def test_document_rejects_a_side_that_disagrees_with_its_name() -> None:
    payload = {
        "schema": "charctx.landmarks/v1",
        "target_id": "t",
        "method": "m",
        "coordinate_system": {},
        "derivation": {},
        "landmarks": [
            {
                "name": "wing_tip.L",
                "point": [0.0, 0.0, 0.0],
                "side": "right",
                "source": "geometric",
                "confidence": "high",
                "evidence": "e",
            }
        ],
        "summary": {},
    }
    with pytest.raises(ValueError, match="disagrees with side"):
        LandmarkDocument.model_validate(payload)


def test_build_declares_landmarks_and_preserves_the_model(
    project_root: Path, creature_glb: Path
) -> None:
    run = make_run(project_root, creature_glb)
    before = (run / "creature.glb").read_bytes()

    result = landmarks.build(Project(project_root), "trellis2/creature-001")
    manifest = json.loads((run / generations.VIEWER_FILE).read_text(encoding="utf-8"))

    assert Path(result["landmarks"]).is_file()
    assert manifest["landmarks"] == "skeleton/landmarks.json"
    assert (run / "creature.glb").read_bytes() == before


def test_build_rejects_an_unsafe_run(project_root: Path, creature_glb: Path) -> None:
    make_run(project_root, creature_glb)
    with pytest.raises(ConfigError, match="safe slugs"):
        landmarks.build(Project(project_root), "../creature-001")


def test_the_occiput_is_the_deepest_local_minimum_not_the_smallest_slice() -> None:
    """A taper's narrowest point is the nose, which is not the occiput.

    The profile below falls away steadily toward the snout and carries one
    genuine waist partway along. Taking the global minimum would put the
    head's rear boundary at the tip of the face; the local minimum is the
    only answer that means anything.
    """
    centres = [i / 20 for i in range(20)]
    areas = [1.0, .98, .95, .92, .88, .60, .86, .84, .80, .74,
             .68, .60, .52, .44, .36, .28, .20, .13, .07, .02]

    found = landmarks._occiput(centres, areas)

    assert found is not None
    position, depth, runner_up = found
    assert position == pytest.approx(0.25)
    # Clear of the runner-up by a wide margin, which is what makes it usable.
    assert depth > runner_up * 3


def test_a_gentle_taper_has_no_occiput_and_says_so() -> None:
    centres = [i / 12 for i in range(12)]
    areas = [1.0 - i * 0.08 for i in range(12)]

    assert landmarks._occiput(centres, areas) is None


def test_the_section_profile_survives_a_shift_in_where_it_starts() -> None:
    """Disjoint bins lost the waist when the edges moved; a window must not.

    This is the regression that mattered: with fixed bins, starting the
    profile a hundredth of the body length earlier smeared a 39% waist down
    to 13% and the occiput vanished.
    """
    import numpy as np

    # A rod with a waist at z = 0.60.
    rng = np.random.default_rng(0)
    z = rng.uniform(0.0, 1.0, 60_000)
    radius = np.where(np.abs(z - 0.60) < 0.03, 0.05, 0.12)
    angle = rng.uniform(0, 2 * np.pi, len(z))
    vertices = np.stack(
        [radius * np.cos(angle), radius * np.sin(angle), z], axis=1
    )

    found = []
    for low in (0.0, 0.01, 0.02, 0.03):
        centres, areas = landmarks._section_profile(
            vertices, 0, 1, 2, 0.0, low, 1.0
        )
        result = landmarks._occiput(centres, areas)
        assert result is not None, f"waist lost when starting at {low}"
        found.append(result[0])

    assert max(found) - min(found) < 0.03
    assert all(0.55 < value < 0.65 for value in found)


def test_the_manual_overlay_overrides_a_proposal_and_adds_what_geometry_cannot(
    project_root: Path, creature_glb: Path
) -> None:
    run = make_run(project_root, creature_glb)
    (run / "skeleton").mkdir(parents=True, exist_ok=True)
    (run / "skeleton" / landmarks.MANUAL_FILE).write_text(
        json.dumps(
            {
                "schema": "charctx.landmarks-manual/v1",
                "landmarks": [
                    {"name": "eye.L", "point": [0.1, 0.2, 0.9]},
                    {"name": "eye.R", "point": [-0.1, 0.2, 0.9]},
                    {"name": "snout", "point": [0.0, 0.05, 1.0],
                     "evidence": "clicked in the front view"},
                ],
            }
        ),
        encoding="utf-8",
    )

    result = landmarks.build(Project(project_root), "trellis2/creature-001")
    document = json.loads(
        (run / "skeleton" / "landmarks.json").read_text(encoding="utf-8")
    )
    marks = {mark["name"]: mark for mark in document["landmarks"]}

    assert set(result["manual"]) == {"eye.L", "eye.R", "snout"}
    # Added: geometry never proposes an eye.
    assert marks["eye.L"]["point"] == [0.1, 0.2, 0.9]
    assert marks["eye.L"]["side"] == "left"
    assert marks["eye.R"]["side"] == "right"
    # Overridden: a manual point is evidence and a proposal is not.
    assert marks["snout"]["point"] == [0.0, 0.05, 1.0]
    assert marks["snout"]["source"] == "manual"
    assert document["derivation"]["manual_overlay"]["applied"]
    assert document["summary"]["landmarks"] == len(document["landmarks"])


def test_the_manual_overlay_refuses_a_landmark_it_may_not_set(
    project_root: Path, creature_glb: Path
) -> None:
    """An overlay that accepts any name turns a typo into geometry."""
    run = make_run(project_root, creature_glb)
    (run / "skeleton").mkdir(parents=True, exist_ok=True)
    (run / "skeleton" / landmarks.MANUAL_FILE).write_text(
        json.dumps({"landmarks": [{"name": "elbow.L", "point": [0, 0, 0]}]}),
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="not a landmark this overlay may set"):
        landmarks.build(Project(project_root), "trellis2/creature-001")
