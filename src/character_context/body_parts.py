"""The standardized western-dragon part taxonomy and its bone mapping.

`specifications/body-parts/spec.md` is the binding contract; this module is its
executable form. Two things live here and nothing else:

* `TAXONOMY` -- 29 parts, nine axial and ten paired, with stable indices and
  display colours.
* `PART_ROOTS` -- the bone at which each part *begins*, for one donor rig.

The mapping resolves **by ancestry, never by name**. `european-dragon` carries
`DEF-Finger_3.L` on a hand and `DEF-Finger_3.L.001` on a foot; no amount of
string matching separates those, and only the hierarchy does. So about thirty
rules name part roots, every bone takes the part of its nearest matching
ancestor, and a bone that matches nothing is an error rather than a default --
a taxonomy that quietly absorbs unmapped bones cannot claim to be total.
"""

from __future__ import annotations

from dataclasses import dataclass

from .config import ConfigError

TAXONOMY = "western-dragon-parts/v2"

UNLABELLED = "unlabelled"

# Axial parts, head to tail. Order is the index order and is part of the
# contract: reordering these renames every stored label.
AXIAL: tuple[tuple[str, str], ...] = (
    ("head", "#e6402e"),
    ("jaw", "#f2792c"),
    ("neck", "#f2b134"),
    ("chest", "#c7d63f"),
    ("abdomen", "#6dbf4b"),
    ("pelvis", "#2fa86b"),
    ("tail_base", "#25a4a0"),
    ("tail_mid", "#2b8ec4"),
    ("tail_tip", "#4a63d8"),
)

# Paired parts. Each yields a `.L` and a `.R`, left lighter than right so a
# mirror error reads as a brightness flip rather than as a number to check.
PAIRED: tuple[tuple[str, str, str], ...] = (
    ("shoulder", "#b98cff", "#7a4fd1"),
    ("upper_arm", "#ff8ad0", "#cc4c96"),
    ("forearm", "#ff9d9d", "#cc5252"),
    ("hand", "#ffd2a1", "#d99441"),
    ("thigh", "#9de8c6", "#3fa87f"),
    ("shin", "#a8e0ff", "#4b9ccf"),
    ("foot", "#c8c8ff", "#6f6fcc"),
    ("wing_root", "#ffe98a", "#c9ab2e"),
    ("wing_arm", "#d0f07a", "#8fbb2e"),
    ("wing_hand", "#8ff0d8", "#2eb89b"),
)


# Sub-parts of the head, added in v2. They exist because `head` was losing its
# crown to `neck`: a part seeded by two points on a medial curve cannot hold a
# bulb against a neighbour seeded higher up. Features on the head's own surface
# are the natural anchors, and they are also the features a person -- or a
# vision model reading a rendered view -- can name reliably, which a mid-neck
# cross-section is not.
#
# Indices 1..29 are unchanged from v1 on purpose: a v1 document's numbers still
# mean what they meant, and only the new names occupy new slots.
AXIAL_SUB: tuple[tuple[str, str, str], ...] = (
    ("nostril", "#ffd9d2", "head"),
)

PAIRED_SUB: tuple[tuple[str, str, str, str], ...] = (
    ("eye", "#fff4fa", "#e3a8c6", "head"),
    ("ear", "#ded0ff", "#a58fdd", "head"),
)


# --------------------------------------------------------------------------
# The canonical part hierarchy
# --------------------------------------------------------------------------

# Which part each part hangs from. Declared, not derived, and that is a
# deliberate choice made after measuring the alternative: a maximum-contact
# spanning tree over the labelled volume's region adjacency recovers 27 of the
# donor's 31 edges and gets four wrong, every one of them a place where the
# model is *folded* so that two parts touch without articulating -- a wing root
# lying along an upper arm, a jaw resting against a neck. Contact area cannot
# tell a joint from a crease, and no scalar tried here did either.
#
# The hierarchy is a property of the body plan rather than of one mesh, so it
# belongs to the standardized taxonomy in the same way the part names do. What
# geometry contributes is the *joint positions*, which is the hard half and the
# half a donor could not supply. Adjacency is still derived on every run and
# reported as a cross-check: an edge of this table with no contact in the
# volume is a real defect worth seeing.
PART_PARENT: dict[str, str | None] = {
    "pelvis": None,
    "abdomen": "pelvis",
    "chest": "abdomen",
    "neck": "chest",
    "head": "neck",
    "jaw": "head",
    "tail_base": "pelvis",
    "tail_mid": "tail_base",
    "tail_tip": "tail_mid",
    "nostril": "head",
    **{
        name.replace("{s}", side): (
            parent.replace("{s}", side) if parent else None
        )
        for side in ("L", "R")
        for name, parent in (
            ("shoulder.{s}", "chest"),
            ("upper_arm.{s}", "shoulder.{s}"),
            ("forearm.{s}", "upper_arm.{s}"),
            ("hand.{s}", "forearm.{s}"),
            ("thigh.{s}", "pelvis"),
            ("shin.{s}", "thigh.{s}"),
            ("foot.{s}", "shin.{s}"),
            ("wing_root.{s}", "chest"),
            ("wing_arm.{s}", "wing_root.{s}"),
            ("wing_hand.{s}", "wing_arm.{s}"),
            ("eye.{s}", "head"),
            ("ear.{s}", "head"),
        )
    },
}

#: The part the hierarchy is rooted at, and the neighbour its bone starts from.
#: A root part has no parent to take a head position from, so one has to be
#: named. The hips are the conventional root of a quadruped rig and the donor
#: agrees -- its `DEF-Spine` head sits exactly on the pelvis/tail boundary.
ROOT_PART = "pelvis"
ROOT_PROXIMAL = "tail_base"


@dataclass(frozen=True)
class Part:
    name: str
    index: int
    color: str
    side: str
    parent: str | None = None


def _build() -> tuple[Part, ...]:
    parts: list[Part] = []
    index = 1
    for name, color in AXIAL:
        parts.append(Part(name, index, color, "center"))
        index += 1
    for name, left, right in PAIRED:
        parts.append(Part(f"{name}.L", index, left, "left"))
        parts.append(Part(f"{name}.R", index + 1, right, "right"))
        index += 2
    for name, color, parent in AXIAL_SUB:
        parts.append(Part(name, index, color, "center", parent))
        index += 1
    for name, left, right, parent in PAIRED_SUB:
        parts.append(Part(f"{name}.L", index, left, "left", parent))
        parts.append(Part(f"{name}.R", index + 1, right, "right", parent))
        index += 2
    return tuple(parts)


PARTS: tuple[Part, ...] = _build()
BY_NAME: dict[str, Part] = {part.name: part for part in PARTS}
BY_INDEX: dict[int, Part] = {part.index: part for part in PARTS}


def part_index(name: str) -> int:
    part = BY_NAME.get(name)
    if part is None:
        raise ConfigError(f"{name!r} is not a part of {TAXONOMY}.")
    return part.index


# --------------------------------------------------------------------------
# Bone-to-part roots, per donor rig
# --------------------------------------------------------------------------


def _sided(rules: dict[str, str]) -> dict[str, str]:
    """Expand one side's rules into both, by substituting the side token."""
    expanded: dict[str, str] = {}
    for bone, part in rules.items():
        for side in ("L", "R"):
            expanded[bone.replace("{s}", side)] = part.replace("{s}", side)
    return expanded


# `european-dragon`: 168 bones, single root at the hips. Every rule below is a
# bone at which a part begins; descendants inherit until another rule fires.
EUROPEAN_DRAGON_ROOTS: dict[str, str] = {
    # Axial. The rig's root sits at the pelvis and the spine runs forward.
    "DEF-Spine": "pelvis",
    "DEF-Spine.001": "abdomen",
    "DEF-Spine.003": "chest",
    "DEF-neck": "neck",
    "DEF-neck.004": "head",
    # The jaw hangs off the skull under two anonymous names; only the
    # hierarchy identifies it, which is the whole reason for ancestry rules.
    "DEF-Bone": "jaw",
    "DEF-tail": "tail_base",
    "DEF-tail.005": "tail_mid",
    "DEF-tail.011": "tail_tip",
    # The rig carries eye, iris and eyelid bones, all parented straight to the
    # skull. They give `eye.L/R` a genuine reference region rather than a
    # placeholder -- there is no equivalent for ears or nostrils, so those stay
    # empty on the donor and say so.
    **{
        f"DEF-{bone}.{side}": f"eye.{side}"
        for side in ("L", "R")
        for bone in (
            "eye_master",
            "eye",
            "eye_iris",
            *(f"lid{n}.{band}" for n in (1, 2, 3, 4) for band in ("B", "T")),
        )
    },
    **_sided(
        {
            "DEF-Hip.{s}": "pelvis",
            "DEF-collar.{s}": "shoulder.{s}",
            "DEF-upper_arm.{s}": "upper_arm.{s}",
            "DEF-forearm.{s}": "forearm.{s}",
            # The forelimb's digits hang off the last forearm segment.
            "DEF-forearm.{s}.002": "hand.{s}",
            "DEF-thigh.{s}": "thigh.{s}",
            "DEF-shin.{s}": "shin.{s}",
            # Toes and their digits are descendants of the foot.
            "DEF-foot.{s}": "foot.{s}",
            "DEF-Wing_Back_Support.{s}": "wing_root.{s}",
            "DEF-Wing_Fold_1.{s}": "wing_arm.{s}",
            # Three distal spars, two of them branching off the arm rather
            # than off each other, so each needs its own rule.
            "DEF-Wing_Fold_3.{s}": "wing_hand.{s}",
            "DEF-Wing_Fold_4.{s}": "wing_hand.{s}",
            "DEF-Wing_Fold_Mini.{s}": "wing_hand.{s}",
        }
    ),
}

DONOR_ROOTS: dict[str, dict[str, str]] = {
    "european-dragon": EUROPEAN_DRAGON_ROOTS,
}


def roots_for(donor_id: str) -> dict[str, str]:
    rules = DONOR_ROOTS.get(donor_id)
    if rules is None:
        raise ConfigError(
            f"No bone-to-part mapping is defined for donor {donor_id!r}. "
            f"Known donors: {', '.join(sorted(DONOR_ROOTS)) or 'none'}."
        )
    return rules


def map_bones(
    parents: dict[str, str | None], roots: dict[str, str]
) -> dict[str, str]:
    """Assign every bone the part of its nearest matching ancestor.

    Total by construction: a bone whose whole ancestry matches no rule raises,
    because a silent default would make the taxonomy's totality a fiction.
    """
    resolved: dict[str, str] = {}
    unmapped: list[str] = []
    for bone in parents:
        chain: list[str] = []
        current: str | None = bone
        part: str | None = None
        seen: set[str] = set()
        while current is not None and current not in seen:
            seen.add(current)
            if current in resolved:
                part = resolved[current]
                break
            if current in roots:
                part = roots[current]
                break
            chain.append(current)
            current = parents.get(current)
        if part is None:
            unmapped.append(bone)
            continue
        resolved[bone] = part
        for name in chain:
            resolved[name] = part

    if unmapped:
        raise ConfigError(
            f"{len(unmapped)} bone(s) reach the rig root without matching any "
            f"part rule: {', '.join(sorted(unmapped)[:8])}"
            + (" ..." if len(unmapped) > 8 else "")
        )
    return resolved


def part_children(name: str) -> list[str]:
    """The parts declared to hang off this one, in taxonomy index order."""
    return [
        part.name
        for part in PARTS
        if PART_PARENT.get(part.name) == name
    ]


def hierarchy_chain(name: str) -> list[str]:
    """A part and every declared ancestor above it, nearest first."""
    chain: list[str] = []
    current: str | None = PART_PARENT.get(name)
    while current is not None:
        chain.append(current)
        current = PART_PARENT.get(current)
    return chain


def coarse(name: str) -> str:
    """The part a sub-part rolls up into, or the part itself.

    Sub-parts refine a region; they do not remove it from its parent. A coarse
    view of a labelled volume is the one that answers "is this the head", and
    a fine view answers "is this the eye".
    """
    part = BY_NAME.get(name)
    return part.parent if part is not None and part.parent else name


def unused_rules(parents: dict[str, str | None], roots: dict[str, str]) -> list[str]:
    """Part roots the rig never presents.

    Reported rather than raised. A rule naming a bone a rig lacks is usually
    a typo, but it is legitimately empty for a rig that is a subset of the
    family the rules describe -- so the caller records it and a human reads
    it, instead of a partial rig being refused outright.
    """
    return sorted(set(roots) - set(parents))


def describe() -> dict[str, object]:
    """The taxonomy as data, for the documented command that prints it."""
    return {
        "taxonomy": TAXONOMY,
        "parts": len(PARTS),
        "axial": [
            part.name for part in PARTS if part.side == "center" and not part.parent
        ],
        "paired": [name for name, _, _ in PAIRED],
        "sub_parts": [part.name for part in PARTS if part.parent],
        "entries": [
            {
                "name": part.name,
                "index": part.index,
                "side": part.side,
                "color": part.color,
                "parent": part.parent,
                "attaches_to": PART_PARENT.get(part.name),
            }
            for part in PARTS
        ],
        "root": ROOT_PART,
        "hierarchy": {
            part.name: PART_PARENT.get(part.name) for part in PARTS
        },
        "donors_mapped": sorted(DONOR_ROOTS),
    }
