"""Place a donor bone hierarchy on a target mesh using its landmarks.

Step 1 moved the donor skeleton rigidly, which measured how far the donor's
rest pose is from the target's stance but put no joint where the target's
anatomy actually is. This module inverts that: every anchored joint position
comes from the *target*, and the donor contributes only the two things it is
genuinely authoritative about -- the bone hierarchy, and the relative
proportions of the bones inside one chain.

The method is deliberately small enough to state in full:

* A **chain** is an ordered run of donor bones (spine, tail, one wing spar,
  one leg) paired with an ordered polyline of target landmarks. The chain's
  bones are redistributed along that polyline by arc length, so each bone
  keeps its share of the chain while the path and the total length are the
  target's. The donor's rearing rest pose cannot leak in, because none of its
  coordinates are used -- only its bone lengths.
* Every bone that is **not** in a chain -- fingers, toes, palms, teeth, eyes
  and lids, the second wing spar -- has no landmark and is not guessed at. It
  rides along in its parent's local frame under the similarity transform
  (swing rotation, uniform scale, translation) that the parent bone received.
  That is a recorded carry, not an anatomical claim.

Nothing here reads mesh connectivity, so the target's disjoint shells are
irrelevant: the landmarks already absorbed every geometric question.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from .asset_models import (
    FittedArmature,
    FittedBone,
    LandmarkDocument,
    SkeletonArmature,
    SkeletonBone,
    SkeletonDocument,
)

METHOD = "landmark-chain/v1"

Vec = tuple[float, float, float]
Matrix = tuple[Vec, Vec, Vec]

IDENTITY: Matrix = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
EPSILON = 1e-12


# --------------------------------------------------------------------------
# Small-vector arithmetic
#
# 168 bones of 3-vectors do not need numpy, and staying in pure Python keeps
# the geometry readable next to the anatomy it describes.
# --------------------------------------------------------------------------


def _sub(a: Vec, b: Vec) -> Vec:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _add(a: Vec, b: Vec) -> Vec:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _mul(a: Vec, k: float) -> Vec:
    return (a[0] * k, a[1] * k, a[2] * k)


def _dot(a: Vec, b: Vec) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a: Vec, b: Vec) -> Vec:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _norm(a: Vec) -> float:
    return math.sqrt(_dot(a, a))


def _unit(a: Vec) -> Vec:
    length = _norm(a)
    return (0.0, 0.0, 0.0) if length < EPSILON else _mul(a, 1.0 / length)


def _apply_matrix(m: Matrix, v: Vec) -> Vec:
    return (_dot(m[0], v), _dot(m[1], v), _dot(m[2], v))


def _matmul(a: Matrix, b: Matrix) -> Matrix:
    return tuple(  # type: ignore[return-value]
        tuple(sum(a[row][k] * b[k][column] for k in range(3)) for column in range(3))
        for row in range(3)
    )


def _swing(source: Vec, target: Vec) -> Matrix:
    """The shortest rotation carrying one unit direction onto another.

    Shortest on purpose: it introduces no twist of its own, so whatever roll a
    bone carries stays the donor's inherited roll rather than an artefact of
    how the bone was re-aimed.
    """
    axis = _cross(source, target)
    cosine = _dot(source, target)
    if cosine < -1.0 + 1e-9:
        # Antiparallel: a half turn about any perpendicular axis.
        fallback = _cross(source, (1.0, 0.0, 0.0))
        if _norm(fallback) < 1e-9:
            fallback = _cross(source, (0.0, 1.0, 0.0))
        u = _unit(fallback)
        return tuple(  # type: ignore[return-value]
            tuple(
                2.0 * u[row] * u[column] - (1.0 if row == column else 0.0)
                for column in range(3)
            )
            for row in range(3)
        )
    skew: Matrix = (
        (0.0, -axis[2], axis[1]),
        (axis[2], 0.0, -axis[0]),
        (-axis[1], axis[0], 0.0),
    )
    squared = _matmul(skew, skew)
    factor = 1.0 / (1.0 + cosine)
    return tuple(  # type: ignore[return-value]
        tuple(
            (1.0 if row == column else 0.0)
            + skew[row][column]
            + squared[row][column] * factor
            for column in range(3)
        )
        for row in range(3)
    )


@dataclass(frozen=True)
class Similarity:
    """Rotation, uniform scale and translation from donor space to target."""

    rotation: Matrix = IDENTITY
    scale: float = 1.0
    translation: Vec = (0.0, 0.0, 0.0)

    def apply(self, point: Vec) -> Vec:
        return _add(
            _apply_matrix(self.rotation, _mul(point, self.scale)), self.translation
        )


def _similarity(donor_head: Vec, donor_tail: Vec, head: Vec, tail: Vec) -> Similarity:
    """The transform taking one donor bone onto its fitted placement."""
    donor_vector = _sub(donor_tail, donor_head)
    vector = _sub(tail, head)
    donor_length, length = _norm(donor_vector), _norm(vector)
    if donor_length < EPSILON or length < EPSILON:
        return Similarity(IDENTITY, 1.0, _sub(head, donor_head))
    rotation = _swing(
        _mul(donor_vector, 1.0 / donor_length), _mul(vector, 1.0 / length)
    )
    scale = length / donor_length
    return Similarity(
        rotation, scale, _sub(head, _apply_matrix(rotation, _mul(donor_head, scale)))
    )


# --------------------------------------------------------------------------
# Chain specifications
#
# Donor-specific by design: this packet fits one character from one donor and
# claims no reusability. Keeping the map as data rather than as heuristics is
# what makes the claim inspectable, and what lets a spec be swapped whole when
# a second donor arrives.
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class ChainSpec:
    name: str
    bones: tuple[str, ...]
    landmarks: tuple[str, ...]
    from_parent: bool = True
    note: str = ""


def _spine() -> ChainSpec:
    return ChainSpec(
        name="spine",
        bones=(
            "DEF-Spine",
            *(f"DEF-Spine.{index:03d}" for index in range(1, 6)),
            "DEF-neck",
            *(f"DEF-neck.{index:03d}" for index in range(1, 5)),
        ),
        landmarks=("hip_center", "spine_mid", "chest", "neck_base", "skull", "snout"),
        from_parent=False,
        note=(
            "the donor root sits at the hips, so this chain is anchored "
            "entirely by landmarks and every other chain hangs off it"
        ),
    )


def _tail() -> ChainSpec:
    return ChainSpec(
        name="tail",
        bones=("DEF-tail", *(f"DEF-tail.{index:03d}" for index in range(1, 17))),
        landmarks=("tail_base", "tail_mid", "tail_tip"),
    )


def _wing(side: str) -> ChainSpec:
    return ChainSpec(
        name=f"wing.{side}",
        bones=(
            f"DEF-Wing_Back_Support.{side}",
            f"DEF-Shoulder_Blade.{side}",
            f"DEF-Wing_Base.{side}",
            f"DEF-Wing_Fold_1.{side}",
            f"DEF-Wing_Fold_2.{side}",
            f"DEF-Wing_Fold_2.02.{side}",
            f"DEF-Wing_Fold_2.03.{side}",
            f"DEF-Wing_Fold_4.{side}",
            f"DEF-Wing_Fold_4.02.{side}",
            f"DEF-Wing_Fold_4.03.{side}",
        ),
        landmarks=(f"wing_root.{side}", f"wing_tip.{side}"),
        note=(
            "Fold_4 is the spar that reaches the donor's wing tip; the Fold_3 "
            "and mini-fold spars have no landmark and ride along"
        ),
    )


def _foreleg(side: str) -> ChainSpec:
    return ChainSpec(
        name=f"foreleg.{side}",
        bones=(
            f"DEF-collar.{side}",
            f"DEF-upper_arm.{side}",
            f"DEF-upper_arm.{side}.001",
            f"DEF-forearm.{side}",
            f"DEF-forearm.{side}.001",
            f"DEF-forearm.{side}.002",
        ),
        landmarks=(f"shoulder.{side}", f"foot_front.{side}"),
    )


def _hindleg(side: str) -> ChainSpec:
    return ChainSpec(
        name=f"hindleg.{side}",
        bones=(
            f"DEF-thigh.{side}",
            f"DEF-thigh.{side}.001",
            f"DEF-shin.{side}",
            f"DEF-shin.{side}.001",
            f"DEF-foot.{side}",
            f"DEF-foot.{side}.001",
            f"DEF-toe.{side}",
        ),
        landmarks=(f"hip.{side}", f"foot_hind.{side}"),
    )


# Order matters: a chain that starts from its parent needs that parent placed
# first, and every branch here hangs off the spine.
EUROPEAN_DRAGON_CHAINS: tuple[ChainSpec, ...] = (
    _spine(),
    _tail(),
    *(_wing(side) for side in ("L", "R")),
    *(_foreleg(side) for side in ("L", "R")),
    *(_hindleg(side) for side in ("L", "R")),
)


# --------------------------------------------------------------------------
# Polyline resampling
# --------------------------------------------------------------------------


def _cumulative(points: list[Vec]) -> list[float]:
    totals = [0.0]
    for index in range(1, len(points)):
        totals.append(totals[-1] + _norm(_sub(points[index], points[index - 1])))
    return totals


def _sample(points: list[Vec], totals: list[float], distance: float) -> Vec:
    """The point at one arc length along a polyline, clamped at both ends."""
    if distance <= 0.0:
        return points[0]
    if distance >= totals[-1]:
        return points[-1]
    for index in range(1, len(totals)):
        if distance <= totals[index]:
            span = totals[index] - totals[index - 1]
            if span < EPSILON:
                return points[index]
            fraction = (distance - totals[index - 1]) / span
            step = _sub(points[index], points[index - 1])
            return _add(points[index - 1], _mul(step, fraction))
    return points[-1]


# --------------------------------------------------------------------------
# Fitting
# --------------------------------------------------------------------------


@dataclass
class ChainFit:
    """Everything one fitted armature produced, including what it refused."""

    armature: FittedArmature
    anchored: list[str] = field(default_factory=list)
    chains: list[dict[str, Any]] = field(default_factory=list)
    skipped: list[dict[str, Any]] = field(default_factory=list)


def _chain_polyline(
    spec: ChainSpec,
    marks: dict[str, Vec],
    bones: dict[str, SkeletonBone],
    transforms: dict[str, Similarity],
) -> tuple[list[Vec] | None, str]:
    """The target path for one chain, or the reason it cannot be built."""
    missing = [name for name in spec.landmarks if name not in marks]
    if missing:
        return None, f"landmarks absent: {', '.join(missing)}"
    points: list[Vec] = []
    if spec.from_parent:
        parent = bones[spec.bones[0]].parent
        if parent is None or parent not in transforms:
            return None, f"parent {parent!r} was not placed by an earlier chain"
        # The attachment rides on the already-fitted parent, so the chain grows
        # out of target-derived geometry rather than out of an attachment
        # landmark that was never proposed.
        points.append(transforms[parent].apply(bones[spec.bones[0]].head))
    points.extend(marks[name] for name in spec.landmarks)
    if _cumulative(points)[-1] < EPSILON:
        return None, "target path has zero length"
    return points, ""


def _fit_armature(
    armature: SkeletonArmature,
    marks: dict[str, Vec],
    specs: tuple[ChainSpec, ...],
    base: Similarity,
) -> ChainFit:
    bones = {bone.name: bone for bone in armature.bones}
    placed: dict[str, tuple[Vec, Vec]] = {}
    transforms: dict[str, Similarity] = {}
    chains: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for spec in specs:
        absent = [name for name in spec.bones if name not in bones]
        if absent:
            skipped.append(
                {"chain": spec.name, "reason": f"donor lacks {', '.join(absent)}"}
            )
            continue
        polyline, reason = _chain_polyline(spec, marks, bones, transforms)
        if polyline is None:
            skipped.append({"chain": spec.name, "reason": reason})
            continue

        chain = [bones[name] for name in spec.bones]
        lengths = [_norm(_sub(bone.tail, bone.head)) for bone in chain]
        donor_total = sum(lengths)
        if donor_total < EPSILON:
            skipped.append({"chain": spec.name, "reason": "donor chain has no length"})
            continue

        totals = _cumulative(polyline)
        target_total = totals[-1]
        walked = 0.0
        joints: list[Vec] = [polyline[0]]
        for length in lengths:
            walked += length
            reach = walked / donor_total * target_total
            joints.append(_sample(polyline, totals, reach))

        for index, bone in enumerate(chain):
            head, tail = joints[index], joints[index + 1]
            placed[bone.name] = (head, tail)
            transforms[bone.name] = _similarity(bone.head, bone.tail, head, tail)

        chains.append(
            {
                "chain": spec.name,
                "bones": len(chain),
                "landmarks": list(spec.landmarks),
                "from_parent": spec.from_parent,
                "donor_length": round(donor_total, 6),
                "target_length": round(target_total, 6),
                "scale": round(target_total / donor_total, 6),
                **({"note": spec.note} if spec.note else {}),
            }
        )

    anchored = list(placed)

    # Everything the chains did not claim rides along in its parent's frame.
    # A root no chain claimed falls back to the rigid transform, so the method
    # degrades to step 1 rather than to nothing.
    for bone in armature.bones:
        if bone.name in placed:
            continue
        inherited = (
            transforms.get(bone.parent, base) if bone.parent is not None else base
        )
        transforms[bone.name] = inherited
        placed[bone.name] = (inherited.apply(bone.head), inherited.apply(bone.tail))

    fitted: list[FittedBone] = []
    points: list[Vec] = []
    for bone in armature.bones:
        head, tail = placed[bone.name]
        points.extend((head, tail))
        fitted.append(
            FittedBone(
                name=bone.name,
                parent=bone.parent,
                deform=bone.deform,
                connected=bone.connected,
                depth=bone.depth,
                head=head,
                tail=tail,
                length=_norm(_sub(tail, head)),
                roll=bone.roll,
            )
        )

    return ChainFit(
        armature=FittedArmature(
            name=armature.name,
            bones=fitted,
            roots=armature.roots,
            leaves=armature.leaves,
            max_depth=armature.max_depth,
            bounds_min=tuple(  # type: ignore[arg-type]
                min(point[axis] for point in points) for axis in range(3)
            ),
            bounds_max=tuple(  # type: ignore[arg-type]
                max(point[axis] for point in points) for axis in range(3)
            ),
            total_length=sum(bone.length for bone in fitted),
        ),
        anchored=anchored,
        chains=chains,
        skipped=skipped,
    )


# --------------------------------------------------------------------------
# Measurement
# --------------------------------------------------------------------------


def _mirror_name(name: str) -> str | None:
    """`DEF-Finger_3.001.L.001` -> `DEF-Finger_3.001.R.001`, or None."""
    parts = name.split(".")
    if "L" not in parts:
        return None
    return ".".join("R" if part == "L" else part for part in parts)


def symmetry_error(
    armatures: list[FittedArmature], axis: int, plane: float
) -> dict[str, Any]:
    """How far each left bone sits from its mirrored right counterpart."""
    lookup = {bone.name: bone for armature in armatures for bone in armature.bones}
    worst_name, worst = "", 0.0
    errors: list[float] = []
    for name, bone in lookup.items():
        partner = _mirror_name(name)
        if partner is None or partner not in lookup:
            continue
        other = lookup[partner]
        for left, right in ((bone.head, other.head), (bone.tail, other.tail)):
            mirrored = list(left)
            mirrored[axis] = 2.0 * plane - mirrored[axis]
            error = _norm(
                _sub((mirrored[0], mirrored[1], mirrored[2]), right)
            )
            errors.append(error)
            if error > worst:
                worst_name, worst = name, error
    if not errors:
        return {"pairs": 0}
    return {
        "pairs": len(errors) // 2,
        "max": round(worst, 6),
        "max_bone": worst_name,
        "mean": round(sum(errors) / len(errors), 6),
    }


def landmark_residual(
    armatures: list[FittedArmature], anchored: set[str], marks: dict[str, Vec]
) -> dict[str, float]:
    """Distance from each landmark to the nearest anchored joint.

    A chain endpoint should be ~0. An interior landmark will not be: bones are
    distributed by donor proportion, so the fitted chain passes *through* an
    interior landmark's neighbourhood without a joint necessarily landing on
    it. The size of that miss is the number worth reading.
    """
    joints = [
        point
        for armature in armatures
        for bone in armature.bones
        if bone.name in anchored
        for point in (bone.head, bone.tail)
    ]
    if not joints:
        return {}
    return {
        name: round(min(_norm(_sub(point, joint)) for joint in joints), 6)
        for name, point in marks.items()
    }


def place(
    donor: SkeletonDocument,
    landmarks: LandmarkDocument,
    base: Similarity,
    specs: tuple[ChainSpec, ...] = EUROPEAN_DRAGON_CHAINS,
) -> tuple[list[FittedArmature], dict[str, Any], set[str]]:
    """Fit every donor armature onto one target's landmarks.

    Returns the fitted armatures, the derivation record, and the set of bones
    that a chain actually anchored -- the caller needs that last one to keep
    anchored evidence separate from carried inheritance in its own metrics.
    """
    marks: dict[str, Vec] = {
        mark.name: (mark.point[0], mark.point[1], mark.point[2])
        for mark in landmarks.landmarks
    }
    results = [
        _fit_armature(armature, marks, specs, base) for armature in donor.armatures
    ]
    armatures = [result.armature for result in results]
    anchored = {name for result in results for name in result.anchored}
    total = sum(len(armature.bones) for armature in armatures)

    axis_name = str(landmarks.coordinate_system.get("symmetry_axis", "x"))
    axis = {"x": 0, "y": 1, "z": 2}.get(axis_name, 0)
    plane = float(landmarks.derivation.get("symmetry_plane", 0.0))

    derivation: dict[str, Any] = {
        "method": METHOD,
        "faithful": False,
        "landmark_method": landmarks.method,
        "landmarks_used": sorted(
            {
                name
                for result in results
                for chain in result.chains
                for name in chain["landmarks"]
            }
        ),
        "chains": [chain for result in results for chain in result.chains],
        "chains_skipped": [entry for result in results for entry in result.skipped],
        "anchored_bones": len(anchored),
        "carried_bones": total - len(anchored),
        "symmetry": symmetry_error(armatures, axis, plane),
        "landmark_residual": landmark_residual(armatures, anchored, marks),
        "limitations": [
            "Anchored joints come from the target; every other bone is "
            "carried in its parent's frame and asserts no target anatomy.",
            "Bone rolls are inherited from the donor and are not recomputed "
            "from limb planes.",
            "A chain is straight between its landmarks, so a fitted limb has "
            "no curvature that a landmark did not put there.",
            "The interior joints step 2 declined to propose are still not "
            "measured; their positions follow donor proportion alone.",
        ],
    }
    return armatures, derivation, anchored
