"""The part taxonomy is total, and its bone mapping resolves by ancestry.

The taxonomy's usefulness rests on one claim: every bone of a rig lands in
exactly one part. That is only true if the mapping refuses to silently absorb
what it cannot place, so the refusal is tested as carefully as the success.
"""

from __future__ import annotations

import pytest

from character_context import body_parts
from character_context.config import ConfigError


def test_the_taxonomy_has_twenty_nine_body_parts_and_five_head_sub_parts() -> None:
    top = [part for part in body_parts.PARTS if not part.parent]
    sub = [part for part in body_parts.PARTS if part.parent]

    assert len(body_parts.PARTS) == 34
    assert len(top) == 29
    assert sum(1 for part in top if part.side == "center") == 9
    assert sum(1 for part in top if part.side == "left") == 10
    assert sum(1 for part in top if part.side == "right") == 10
    assert {part.name for part in sub} == {
        "nostril", "eye.L", "eye.R", "ear.L", "ear.R"
    }
    # Every sub-part refines the head; none of them is orphaned.
    assert {part.parent for part in sub} == {"head"}


def test_v1_part_indices_are_unchanged_by_the_v2_additions() -> None:
    """A v1 document's numbers still mean what they meant.

    Sub-parts were appended rather than interleaved precisely so that adding
    them could not silently relabel stored volumes.
    """
    assert body_parts.BY_NAME["head"].index == 1
    assert body_parts.BY_NAME["wing_hand.R"].index == 29
    assert min(part.index for part in body_parts.PARTS if part.parent) == 30


def test_a_sub_part_rolls_up_into_its_parent() -> None:
    assert body_parts.coarse("eye.L") == "head"
    assert body_parts.coarse("nostril") == "head"
    # A part that is nobody's child is its own coarse answer.
    assert body_parts.coarse("head") == "head"
    assert body_parts.coarse("tail_tip") == "tail_tip"


def test_part_indices_are_dense_stable_and_never_zero() -> None:
    """Zero is the unlabelled sentinel, so no part may claim it."""
    indices = sorted(part.index for part in body_parts.PARTS)
    assert indices == list(range(1, len(body_parts.PARTS) + 1))
    assert body_parts.BY_NAME["head"].index == 1


def test_every_paired_part_exists_on_both_sides_with_distinct_colours() -> None:
    paired = [(name, left, right) for name, left, right in body_parts.PAIRED]
    paired += [(name, left, right) for name, left, right, _ in body_parts.PAIRED_SUB]
    for name, _, _ in paired:
        left = body_parts.BY_NAME[f"{name}.L"]
        right = body_parts.BY_NAME[f"{name}.R"]
        assert left.side == "left"
        assert right.side == "right"
        # A mirror error should read as a brightness flip, not as a number.
        assert left.color != right.color


def test_mapping_walks_ancestry_rather_than_matching_names() -> None:
    """The same bone name on a hand and a foot must resolve differently.

    This is the case that rules out name matching outright: `european-dragon`
    carries `Finger_3` under both a forearm and a toe.
    """
    parents = {
        "root": None,
        "forearm": "root",
        "Finger_3": "forearm",
        "leg": "root",
        "toe": "leg",
        "Finger_3.001": "toe",
    }
    roots = {"root": "chest", "forearm": "hand.L", "leg": "foot.L"}

    mapping = body_parts.map_bones(parents, roots)

    assert mapping["Finger_3"] == "hand.L"
    assert mapping["Finger_3.001"] == "foot.L"
    assert mapping["root"] == "chest"


def test_a_deeper_rule_overrides_a_shallower_one() -> None:
    parents = {"a": None, "b": "a", "c": "b", "d": "c"}
    roots = {"a": "neck", "c": "head"}

    mapping = body_parts.map_bones(parents, roots)

    assert mapping["b"] == "neck"
    assert mapping["c"] == "head"
    assert mapping["d"] == "head"


def test_a_bone_matching_no_rule_is_an_error_not_a_default() -> None:
    parents = {"a": None, "orphan": None}
    roots = {"a": "chest"}

    with pytest.raises(ConfigError, match="reach the rig root without matching"):
        body_parts.map_bones(parents, roots)


def test_a_rule_naming_an_absent_bone_is_reported_not_rejected() -> None:
    """A rig that is a subset of the family the rules describe is legitimate.

    Only the other direction is fatal: a bone matching no rule would make the
    taxonomy's totality a fiction, so that one still raises.
    """
    parents = {"a": None}
    roots = {"a": "chest", "ghost": "head"}

    assert body_parts.map_bones(parents, roots) == {"a": "chest"}
    assert body_parts.unused_rules(parents, roots) == ["ghost"]


def test_an_unknown_part_name_is_rejected() -> None:
    with pytest.raises(ConfigError, match="is not a part of"):
        body_parts.part_index("wing_membrane")


def test_every_european_dragon_rule_targets_a_real_part() -> None:
    for part in body_parts.EUROPEAN_DRAGON_ROOTS.values():
        assert part in body_parts.BY_NAME


def test_the_donor_rig_maps_its_eye_bones_to_the_eye_sub_parts() -> None:
    """The rig has eye, iris and lid bones, so `eye.L/R` get a real reference.

    There is no equivalent bone for an ear or a nostril, which is why those
    sub-parts stay empty on the donor rather than being faked.
    """
    rules = body_parts.EUROPEAN_DRAGON_ROOTS
    assert rules["DEF-eye.L"] == "eye.L"
    assert rules["DEF-eye_iris.R"] == "eye.R"
    assert rules["DEF-lid3.T.L"] == "eye.L"
    assert not any(part.startswith("ear") for part in rules.values())


def test_an_unmapped_donor_is_named_rather_than_guessed() -> None:
    with pytest.raises(ConfigError, match="No bone-to-part mapping"):
        body_parts.roots_for("blender-dragon")
