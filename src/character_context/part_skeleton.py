"""Read a skeleton out of a labelled volume.

Phase 1 asked where each part of a dragon *is*. This module asks the question
that was the reason for asking that one: **where are its joints**.

The move is small enough to state in a sentence. A joint is not a point some
heuristic has to guess at; it is the **boundary between two labelled regions**,
and a boundary between two dense regions is a stable thing to measure where a
point estimate is not. The elbow is wherever `upper_arm` stops being
`upper_arm` and starts being `forearm`, and that surface exists in the volume
whether or not anything on the skin marks it. Nine joints the landmark route
declined to propose -- both elbows, both wrists, both knees, both wing elbows,
and the jaw hinge -- are ordinary interfaces here.

Three things come out of a labelled volume, and they are deliberately not
equally trusted:

* **Joints** are measured. Every one is the depth-weighted centre of the voxel
  faces separating two parts.
* **The hierarchy** is declared by the taxonomy, and adjacency is derived
  alongside it as a *check* rather than as the answer. Deriving it from contact
  area alone was tried and measured: 27 of the donor's 31 edges come back
  correct and four come back wrong, every one of them a place where the model
  is folded so that two parts touch without articulating. Contact area cannot
  tell a joint from a crease.
* **Roll** is not derived at all. A bone's twist about its own axis leaves no
  signature in an occupancy grid, and inventing one would be the kind of guess
  this packet exists to remove.
"""

from __future__ import annotations

from typing import Any

from . import body_parts, voxels
from .asset_models import DerivedSkeletonDocument, FittedArmature, FittedBone
from .config import ConfigError

METHOD = "part-boundary-skeleton/v1"
ARMATURE_NAME = "derived"

# A joint is the centre of mass of the interface between two parts, weighted by
# how deep in the body each interface voxel sits. Depth matters because the two
# kinds of interface look identical by area: a real joint is a *cross-section*
# through a limb, and a fold where two parts merely touch is a crease at the
# skin. Weighting by depth squared pulls the estimate toward the part of the
# interface that is actually inside the body. Measured on the donor it moves
# the median joint error from 0.80% of the body diagonal to 0.66%; the exponent
# is 2 because 1 gives back less and 3 gives back nothing more.
DEPTH_POWER = 2


# --------------------------------------------------------------------------
# Interfaces between parts
# --------------------------------------------------------------------------


def _contacts(grid: voxels.Grid, labels: Any) -> dict[frozenset[int], dict[str, Any]]:
    """Every touching pair of parts, with a world-space joint estimate."""
    import numpy as np
    from scipy import ndimage

    depth = ndimage.distance_transform_edt(labels > 0)
    found: dict[frozenset[int], dict[str, Any]] = {}
    for key, positions in voxels.interfaces(labels).items():
        # A face position is fractional on one axis; the depth of the pair is
        # read at the two voxels it lies between.
        floor = np.floor(positions).astype(int)
        ceiling = np.ceil(positions).astype(int)
        samples = np.minimum(
            depth[floor[:, 0], floor[:, 1], floor[:, 2]],
            depth[ceiling[:, 0], ceiling[:, 1], ceiling[:, 2]],
        )
        weights = np.power(np.maximum(samples, 1e-6), DEPTH_POWER)
        centre = (positions * weights[:, None]).sum(axis=0) / weights.sum()
        found[key] = {
            "point": tuple(
                float(value)
                for value in (centre + 0.5) * grid.pitch + np.asarray(grid.origin)
            ),
            "contacts": int(len(positions)),
            "mean_depth_voxels": round(float(samples.mean()), 4),
        }
    return found


def adjacency(
    labels: Any,
    contacts: dict[frozenset[int], dict[str, Any]],
    expected: dict[str, str | None] | None = None,
) -> dict[str, Any]:
    """Derive a hierarchy from contact area alone, and say where it disagrees.

    Kept and reported even though the declared hierarchy is what gets used.
    A maximum-contact spanning tree is the strongest thing adjacency by itself
    can say, so measuring it every run is what keeps "declared, not derived"
    an evidenced choice rather than a preference.

    `expected` is the hierarchy actually in force -- the declared table after
    any part with a missing parent has climbed to a present ancestor. Comparing
    against that rather than against the raw table matters on a partial
    labelling: a hand whose forearm was never labelled is *not* evidence that
    contact area disagrees about anatomy, and counting it as such would make
    this check read worse the sparser the volume gets.
    """
    import numpy as np

    present = {int(value) for value in np.unique(labels) if value > 0}
    root_index = body_parts.part_index(body_parts.ROOT_PART)
    if root_index not in present:
        return {"available": False, "reason": f"{body_parts.ROOT_PART} has no voxels"}

    def name(index: int) -> str:
        return body_parts.BY_INDEX[index].name

    tree: dict[int, int | None] = {root_index: None}
    while len(tree) < len(present):
        best: tuple[int, int, int] | None = None
        for pair, record in contacts.items():
            first, second = sorted(pair)
            for inside, outside in ((first, second), (second, first)):
                if inside in tree and outside in present and outside not in tree:
                    weight = record["contacts"]
                    if best is None or weight > best[0]:
                        best = (weight, outside, inside)
        if best is None:
            break
        tree[best[1]] = best[2]

    table = expected if expected is not None else body_parts.PART_PARENT
    agree = 0
    disagreements: list[dict[str, str | None]] = []
    for index, parent in tree.items():
        declared = table.get(name(index))
        derived = name(parent) if parent is not None else None
        if declared == derived:
            agree += 1
        else:
            disagreements.append(
                {"part": name(index), "derived": derived, "declared": declared}
            )
    return {
        "available": True,
        "method": "maximum-contact-spanning-tree",
        "parts": len(tree),
        "unreached_parts": sorted(name(index) for index in present - set(tree)),
        "agrees_with_declared": agree,
        "disagreements": sorted(disagreements, key=lambda row: str(row["part"])),
    }


# --------------------------------------------------------------------------
# Bones
# --------------------------------------------------------------------------


def _seed_at(grid: voxels.Grid, mask: Any, point: Any) -> Any:
    """A single-voxel seed mask at whichever voxel of `mask` is nearest."""
    import numpy as np

    seed = np.zeros(mask.shape, dtype=bool)
    candidates = np.argwhere(mask)
    if not len(candidates):
        return seed
    index = grid.to_index(np.asarray([point]))[0]
    distances = np.linalg.norm(candidates - index, axis=1)
    seed[tuple(candidates[int(distances.argmin())])] = True
    return seed


def _attachment(
    part: str, present: set[str], contacts: dict[frozenset[int], dict[str, Any]]
) -> tuple[str | None, str]:
    """The nearest declared ancestor this part actually touches.

    A part whose declared parent is missing or out of contact is **not**
    dropped and **not** silently reparented to whatever it happens to touch.
    It climbs its own declared chain until it finds an ancestor with a real
    interface, and how far it had to climb is recorded, because a hand that
    ends up hanging off a shoulder is a finding about the labelling.
    """
    index = body_parts.part_index(part)
    for step, ancestor in enumerate(body_parts.hierarchy_chain(part)):
        if ancestor not in present:
            continue
        key = frozenset((index, body_parts.part_index(ancestor)))
        if key in contacts:
            return ancestor, "declared" if step == 0 else "reattached"
    return None, "detached"


def build(
    grid: voxels.Grid,
    labels: Any,
    target_id: str,
    source: dict[str, Any],
) -> DerivedSkeletonDocument:
    """Turn a labelled volume into a bone hierarchy."""
    import numpy as np

    contacts = _contacts(grid, labels)
    present = {part.name for part in body_parts.PARTS if (labels == part.index).any()}
    if body_parts.ROOT_PART not in present:
        raise ConfigError(
            f"The labelled volume has no {body_parts.ROOT_PART!r} voxels, so the "
            f"hierarchy has no root to hang from. "
            f"{len(present)} of {len(body_parts.PARTS)} parts are present: "
            f"{', '.join(sorted(present)) or 'none'}."
        )

    attach: dict[str, str | None] = {}
    provenance: dict[str, str] = {}
    for part in sorted(present):
        if part == body_parts.ROOT_PART:
            attach[part], provenance[part] = None, "root"
            continue
        parent, how = _attachment(part, present, contacts)
        attach[part] = parent if parent is not None else body_parts.ROOT_PART
        provenance[part] = how

    def joint(part: str, other: str) -> Any:
        key = frozenset((body_parts.part_index(part), body_parts.part_index(other)))
        record = contacts.get(key)
        return None if record is None else np.asarray(record["point"], dtype=float)

    mask_of = {part: labels == body_parts.part_index(part) for part in present}

    # Heads first: every non-root bone starts at the interface with whatever
    # it ended up attached to.
    heads: dict[str, Any] = {}
    for part, parent in attach.items():
        if parent is None:
            continue
        point = joint(part, parent)
        if point is None:
            # Detached: no interface anywhere up the chain. Start the bone at
            # the part's own centroid so it still exists and still reports.
            point = grid.to_world(np.argwhere(mask_of[part])).mean(axis=0)
        heads[part] = point

    children: dict[str, list[str]] = {part: [] for part in present}
    for part, parent in attach.items():
        if parent is not None:
            children[parent].append(part)

    root = body_parts.ROOT_PART
    proximal = joint(root, body_parts.ROOT_PROXIMAL)
    if proximal is None:
        # No tail to start from. Take the point of the root part farthest from
        # everything hanging off it, which is the same idea by other means.
        mask = mask_of[root]
        anchor = (
            np.mean(
                [heads[child] for child in children[root] if child in heads], axis=0
            )
            if children[root]
            else grid.to_world(np.argwhere(mask)).mean(axis=0)
        )
        proximal = grid.to_world(
            np.asarray([voxels.farthest(mask, _seed_at(grid, mask, anchor))])
        )[0]
    heads[root] = proximal

    # Tails: a bone ends at the child joint farthest from its head, so the
    # chain stays connected. A part with no children ends at the point of
    # itself farthest from its head, measured *through* the part.
    tails: dict[str, Any] = {}
    tail_rule: dict[str, str] = {}
    degenerate: list[str] = []
    for part in sorted(present):
        head = heads[part]
        options = [
            (float(np.linalg.norm(heads[child] - head)), child)
            for child in children[part]
            if child in heads
        ]
        if options:
            _, chosen = max(options)
            tails[part] = heads[chosen]
            tail_rule[part] = f"joint with {chosen}"
        else:
            mask = mask_of[part]
            tails[part] = grid.to_world(
                np.asarray([voxels.farthest(mask, _seed_at(grid, mask, head))])
            )[0]
            tail_rule[part] = "farthest voxel of the part"
        if float(np.linalg.norm(tails[part] - head)) < grid.pitch * 0.5:
            degenerate.append(part)

    depth_of: dict[str, int] = {}

    def depth(part: str) -> int:
        if part not in depth_of:
            parent = attach[part]
            depth_of[part] = 0 if parent is None else depth(parent) + 1
        return depth_of[part]

    bones: list[FittedBone] = []
    for part in sorted(present, key=lambda name: (depth(name), name)):
        parent = attach[part]
        head = heads[part]
        tail = tails[part]
        connected = (
            parent is not None
            and float(np.linalg.norm(head - tails[parent])) < grid.pitch * 0.5
        )
        bones.append(
            FittedBone(
                name=part,
                parent=parent,
                deform=True,
                connected=bool(connected),
                depth=depth(part),
                head=tuple(float(value) for value in head),
                tail=tuple(float(value) for value in tail),
                length=float(np.linalg.norm(tail - head)),
                # Not derived. An occupancy grid carries no twist information.
                roll=0.0,
            )
        )

    by_name = {bone.name: bone for bone in bones}
    positions = np.asarray(
        [bone.head for bone in bones] + [bone.tail for bone in bones]
    )
    armature = FittedArmature(
        name=ARMATURE_NAME,
        bones=bones,
        roots=[bone.name for bone in bones if bone.parent is None],
        leaves=sorted(part for part in present if not children[part]),
        max_depth=max(bone.depth for bone in bones),
        bounds_min=tuple(float(value) for value in positions.min(axis=0)),
        bounds_max=tuple(float(value) for value in positions.max(axis=0)),
        total_length=float(sum(bone.length for bone in bones)),
    )

    solid = grid.to_world(np.argwhere(labels > 0))
    diagonal = float(np.linalg.norm(solid.max(axis=0) - solid.min(axis=0)))

    def contact_count(part: str) -> int:
        parent = attach[part]
        key = frozenset(
            (body_parts.part_index(part), body_parts.part_index(str(parent)))
        )
        record = contacts.get(key)
        return 0 if record is None else int(record["contacts"])

    return DerivedSkeletonDocument(
        target_id=target_id,
        taxonomy=body_parts.TAXONOMY,
        coordinate_system={
            "space": "viewer",
            "units": "model",
            "note": "Same space as the labelled volume this was read out of.",
        },
        derivation={
            "method": METHOD,
            "source": source,
            "grid": {
                "resolution": grid.resolution,
                "pitch": grid.pitch,
                "origin": list(grid.origin),
            },
            "hierarchy": "declared by the taxonomy",
            "joint_rule": (
                f"depth^{DEPTH_POWER}-weighted centre of the voxel faces "
                f"between two parts"
            ),
            "root": body_parts.ROOT_PART,
            "attachment": {
                part: {"parent": attach[part], "by": provenance[part]}
                for part in sorted(present)
            },
            "reattached_parts": sorted(
                part for part, how in provenance.items() if how == "reattached"
            ),
            "detached_parts": sorted(
                part for part, how in provenance.items() if how == "detached"
            ),
            "absent_parts": sorted(
                part.name for part in body_parts.PARTS if part.name not in present
            ),
            "degenerate_bones": sorted(degenerate),
            "tail_rule": tail_rule,
            "joints": [
                {
                    "part": part,
                    "parent": attach[part],
                    "point": list(by_name[part].head),
                    "contacts": contact_count(part),
                }
                for part in sorted(present)
                if attach[part] is not None
            ],
            "adjacency_check": adjacency(labels, contacts, attach),
            "limitations": [
                "Roll is not derived: an occupancy grid carries no twist "
                "signature, so every bone reports roll 0.",
                "A joint is only as sharp as the labelling that produced it; "
                "a boundary in the wrong place moves the joint with it.",
                "An interface that is a long seam rather than a cross-section "
                "-- a wing membrane against its spar -- puts the joint at the "
                "seam's centre, which is not where the spar meets its "
                "neighbour.",
                "One bone per part. A part the taxonomy does not subdivide "
                "gets one bone however many the source rig spent on it.",
            ],
        },
        armatures=[armature],
        summary={
            "bones": len(bones),
            "parts_present": len(present),
            "parts_total": len(body_parts.PARTS),
            "joints": sum(1 for bone in bones if bone.parent is not None),
            "max_depth": armature.max_depth,
            "total_length": round(armature.total_length, 6),
            "body_diagonal": round(diagonal, 6),
        },
    )


# --------------------------------------------------------------------------
# The donor's own skeleton, reduced to the same shape
# --------------------------------------------------------------------------


def donor_reference(
    skeleton: dict[str, Any], mapping: dict[str, str]
) -> dict[str, dict[str, Any]]:
    """Collapse an authored rig into one segment per part, for scoring.

    A part the donor spends six bones on becomes the segment from where that
    chain starts to where it ends, because that is the granularity a derived
    skeleton works at. Where a part has several root bones -- the wing's three
    distal spars, the eye's eleven lid bones -- the one carrying the longest
    subtree is taken and the disagreement between them is reported, since a
    part with two genuine attachment points has no single true joint and a
    score should say so rather than average them away.
    """
    import numpy as np

    bones = {
        bone["name"]: bone
        for armature in skeleton["armatures"]
        for bone in armature["bones"]
    }
    kin: dict[str, list[str]] = {name: [] for name in bones}
    for name, bone in bones.items():
        if bone["parent"] in kin:
            kin[bone["parent"]].append(name)

    lengths: dict[str, float] = {}

    def subtree_length(name: str) -> float:
        if name not in lengths:
            lengths[name] = float(bones[name]["length"]) + sum(
                subtree_length(child) for child in kin[name]
            )
        return lengths[name]

    grouped: dict[str, list[str]] = {}
    roots: dict[str, list[str]] = {}
    parent_part: dict[str, str | None] = {}
    for name, bone in bones.items():
        part = mapping[name]
        grouped.setdefault(part, []).append(name)
        above = bone["parent"]
        if above is None or mapping[above] != part:
            roots.setdefault(part, []).append(name)
            parent_part[part] = mapping[above] if above is not None else None

    result: dict[str, dict[str, Any]] = {}
    for part, names in roots.items():
        chosen = max(names, key=subtree_length)
        head = np.asarray(bones[chosen]["head"], dtype=float)
        candidates = np.asarray(
            [bones[name]["tail"] for name in grouped[part]], dtype=float
        )
        tail = candidates[int(np.linalg.norm(candidates - head, axis=1).argmax())]
        spread = (
            float(
                np.linalg.norm(
                    np.asarray([bones[name]["head"] for name in names]) - head, axis=1
                ).max()
            )
            if len(names) > 1
            else 0.0
        )
        result[part] = {
            "parent": parent_part[part],
            "head": [float(value) for value in head],
            "tail": [float(value) for value in tail],
            "bones": len(grouped[part]),
            "root_bone": chosen,
            "root_bones": len(names),
            # How far apart this part's several attachment points are. A large
            # spread means "the true joint" is not a single place.
            "head_spread": round(spread, 6),
        }
    return result


# --------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------

#: How a labelled volume is seeded before a skeleton is read out of it.
#: `reference` is the donor's own authored bones and is the only one that is
#: not a proposal; the other two are donor-independent and are what a target
#: with no rig actually gets.
SEED_MODES = ("reference", "centroid", "landmarks")


def _labelled(
    project: Any, target: str, seeds: str, resolution: int
) -> tuple[voxels.Grid, Any, dict[str, Any], Any]:
    """A labelled volume for a donor asset id or a `<backend>/<run>` id.

    Returns the grid, the labels, a description of how they were produced, and
    the package directory the result belongs beside (None for a run, whose
    directory travels in the description instead).
    """
    from . import part_volume

    if seeds not in SEED_MODES:
        raise ConfigError(f"Unknown seeding {seeds!r}; use {', '.join(SEED_MODES)}.")

    if "/" in target:
        if seeds != "landmarks":
            raise ConfigError(
                f"A generation run has no authored rig, so {seeds!r} seeding is "
                f"not available for {target!r}. Use --seeds landmarks."
            )
        return (*_labelled_run(project, target, resolution), None)

    skeleton, mapping, _, package = part_volume._donor(project, target)
    model = package / "web" / "model.glb"
    if not model.is_file():
        raise ConfigError(f"Donor {target!r} has no browser model at {model}.")
    scene = part_volume._scene(model)
    grid, report = voxels.voxelize(scene, resolution=resolution)

    truth_points, truth_values = part_volume._bone_seeds(skeleton, mapping, grid.pitch)
    truth, _ = voxels.watershed(
        grid, voxels.seed_labels(grid, truth_points, truth_values)
    )
    if seeds == "reference":
        return grid, truth, {"seeds": seeds, "voxelization": report}, package

    if seeds == "centroid":
        points, values = part_volume._centroid_seeds(grid, truth)
        detail: dict[str, Any] = {"seeds": seeds}
    else:
        from . import landmarks as landmarks_mod

        document = landmarks_mod.propose(model, target)
        points, values, ignored = part_volume._landmark_seeds(document)
        detail = {
            "seeds": seeds,
            "landmark_method": document.method,
            "ignored_landmarks": ignored,
        }
    labels, _ = voxels.watershed(grid, voxels.seed_labels(grid, points, values))
    detail["voxelization"] = report
    detail["seed_points"] = int(len(points))
    return grid, labels, detail, package


def _labelled_run(
    project: Any, run_ref: str, resolution: int
) -> tuple[voxels.Grid, Any, dict[str, Any]]:
    from . import generations as generations_mod
    from . import part_volume
    from .asset_models import LandmarkDocument

    backend, run = generations_mod._resolve_run(project, run_ref)
    request = generations_mod._json(generations_mod._relative_file(run, "request.json"))
    path = run / "skeleton" / "landmarks.json"
    if not path.is_file():
        raise ConfigError(
            "A derived skeleton needs a labelled volume, and a generation run "
            "is labelled from its proposed landmarks. Run "
            "`charctx skeleton landmarks <backend>/<run>` first."
        )
    document = LandmarkDocument.model_validate_json(path.read_text(encoding="utf-8"))
    points, values, ignored = part_volume._landmark_seeds(document)
    model = generations_mod._relative_file(
        run, generations_mod._model_relative(run, request)
    )
    grid, report = voxels.voxelize(part_volume._scene(model), resolution=resolution)
    labels, _ = voxels.watershed(grid, voxels.seed_labels(grid, points, values))
    return (
        grid,
        labels,
        {
            "seeds": "landmarks",
            "landmark_method": document.method,
            "ignored_landmarks": ignored,
            "seed_points": int(len(points)),
            "voxelization": report,
            "run": f"{backend}/{run.name}",
            "directory": str(run),
        },
    )


def derive(
    project: Any,
    target: str,
    seeds: str = "reference",
    resolution: int = 128,
) -> dict[str, Any]:
    """Derive a skeleton from a target's labelled volume and write it out."""
    import json
    from pathlib import Path

    from . import part_volume

    grid, labels, detail, package = _labelled(project, target, seeds, resolution)
    document = build(grid, labels, target, detail)
    directory = (
        package / "parts"
        if package is not None
        else Path(detail["directory"]) / "parts"
    )
    path = part_volume._write(
        directory / "skeleton.json",
        json.dumps(document.model_dump(by_alias=True), indent=2) + "\n",
    )
    derivation = document.derivation
    return {
        "target": target,
        "method": METHOD,
        "seeds": seeds,
        "file": str(path),
        "summary": document.summary,
        "reattached_parts": derivation["reattached_parts"],
        "detached_parts": derivation["detached_parts"],
        "absent_parts": derivation["absent_parts"],
        "degenerate_bones": derivation["degenerate_bones"],
        "adjacency_check": derivation["adjacency_check"],
    }


def score(
    project: Any,
    donor_id: str,
    seeds: str = "reference",
    resolution: int = 128,
) -> dict[str, Any]:
    """Score a derived skeleton against the donor's authored rig.

    Two errors are reported and they answer different questions:

    * **joint error** -- how far the derived joint is from where the donor put
      it. This is the number the packet exists for, and "where is the elbow" is
      one of its rows.
    * **tail error** -- how far the derived bone's far end is. Leaves are
      reported apart from chained bones on purpose: the donor's head chain
      stops behind the eyes while a derived head bone runs to the snout, which
      is a difference of convention rather than an error, and pooling the two
      would hide both.
    """
    import math

    import numpy as np

    from . import part_volume

    skeleton, mapping, _, _ = part_volume._donor(project, donor_id)
    truth = donor_reference(skeleton, mapping)
    grid, labels, detail, _ = _labelled(project, donor_id, seeds, resolution)
    document = build(grid, labels, donor_id, detail)

    bones = {bone.name: bone for bone in document.armatures[0].bones}
    diagonal = float(document.summary["body_diagonal"])

    rows: list[dict[str, Any]] = []
    for name, bone in sorted(bones.items()):
        expected = truth.get(name)
        if expected is None:
            continue
        head_error = float(
            np.linalg.norm(np.asarray(bone.head) - np.asarray(expected["head"]))
        )
        tail_error = float(
            np.linalg.norm(np.asarray(bone.tail) - np.asarray(expected["tail"]))
        )
        derived_axis = np.asarray(bone.tail) - np.asarray(bone.head)
        truth_axis = np.asarray(expected["tail"]) - np.asarray(expected["head"])
        scale = float(np.linalg.norm(derived_axis) * np.linalg.norm(truth_axis))
        angle = (
            math.degrees(
                math.acos(
                    max(-1.0, min(1.0, float(np.dot(derived_axis, truth_axis)) / scale))
                )
            )
            if scale > 1e-12
            else None
        )
        children = body_parts.part_children(name)
        rows.append(
            {
                "part": name,
                "parent": bone.parent,
                "parent_matches_donor": bone.parent == expected["parent"],
                "joint_error": round(head_error, 6),
                "joint_error_pct": round(head_error / diagonal, 6),
                "tail_error": round(tail_error, 6),
                "tail_error_pct": round(tail_error / diagonal, 6),
                "axis_angle_deg": None if angle is None else round(angle, 2),
                "leaf": all(child not in bones for child in children),
                # A part the donor attaches at several places has no single
                # true joint; the score says so rather than hiding it.
                "donor_head_spread": expected["head_spread"],
                "donor_bones": expected["bones"],
            }
        )

    scored = [row for row in rows if row["parent"] is not None]
    joints = np.asarray([row["joint_error_pct"] for row in scored])
    chained = [row for row in scored if not row["leaf"]]
    angles = [
        row["axis_angle_deg"] for row in rows if row["axis_angle_deg"] is not None
    ]
    unambiguous = [row for row in scored if row["donor_head_spread"] < grid.pitch]

    return {
        "target": donor_id,
        "seeds": seeds,
        "method": METHOD,
        "grid": {"resolution": grid.resolution, "pitch": grid.pitch},
        "body_diagonal": diagonal,
        "bones": len(bones),
        "scored_joints": len(scored),
        "hierarchy_matches_donor": sum(
            1 for row in rows if row["parent_matches_donor"]
        ),
        "hierarchy_total": len(rows),
        "adjacency_check": document.derivation["adjacency_check"],
        "joint_error": {
            "mean_pct": round(float(joints.mean()), 6) if len(joints) else None,
            "median_pct": round(float(np.median(joints)), 6) if len(joints) else None,
            "max_pct": round(float(joints.max()), 6) if len(joints) else None,
            "mean_voxels": round(
                float(np.mean([row["joint_error"] for row in scored]) / grid.pitch), 3
            )
            if scored
            else None,
            # The same statistic over only the joints the donor itself places
            # unambiguously, which is the fairer comparison.
            "unambiguous_median_pct": round(
                float(np.median([row["joint_error_pct"] for row in unambiguous])), 6
            )
            if unambiguous
            else None,
            "unambiguous_joints": len(unambiguous),
        },
        "tail_error": {
            "chained_median_pct": round(
                float(np.median([row["tail_error_pct"] for row in chained])), 6
            )
            if chained
            else None,
            "chained_bones": len(chained),
        },
        "axis_angle_deg": {
            "median": round(float(np.median(angles)), 2) if angles else None,
            "max": round(float(np.max(angles)), 2) if angles else None,
        },
        "worst_joints": sorted(scored, key=lambda row: -row["joint_error_pct"])[:6],
        "best_joints": sorted(scored, key=lambda row: row["joint_error_pct"])[:6],
        "missing_from_donor": sorted(set(truth) - set(bones)),
        "per_bone": rows,
    }
