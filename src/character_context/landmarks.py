"""Propose anatomical landmarks on a generated mesh from geometry alone.

Nothing here calls a model or reads an image. It exploits three facts that hold
for a generated western dragon and that survive shell-soup topology, because
every step works on the vertex cloud and never on connectivity:

* the body is bilaterally symmetric about one plane;
* the body axis is the longest horizontal axis, and slicing along it gives a
  medial curve through tail, torso, neck and head;
* wings and feet are extremal -- the widest and the lowest parts of the mesh.

Joints buried inside the silhouette (elbow, knee, wing elbow, wing wrist, jaw
pivot) leave no reliable geometric signature and are deliberately not guessed.
They are reported in `not_attempted` so the gap stays visible.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .asset_models import Landmark, LandmarkDocument
from .config import ConfigError
from .project import Project

METHOD = "symmetry-medial-extremal/v1"
FOOT_BAND = 0.030
FOOT_CLUSTER_DISTANCE = 0.035
WING_MIN_SPAN_FRACTION = 0.32
END_BAND = 0.12
# How much narrower than its surroundings a slice must be before it counts
# as an occiput rather than as noise in the taper. Set from a measured sweep:
# on Riyu the true waist reads 0.151 and the best rival reads 0.039, so this
# sits about twice above the noise floor and twice below the signal.
OCCIPUT_DEPTH = 0.08
# How far forward of the occiput to start looking for the skull's crown. The
# tallest point in the head band sits on the boundary itself, where the neck's
# crest is still coming down.
CROWN_CLEARANCE = 0.25
NOT_ATTEMPTED = (
    "elbow.L",
    "elbow.R",
    "knee.L",
    "knee.R",
    "wing_elbow.L",
    "wing_elbow.R",
    "wing_wrist.L",
    "wing_wrist.R",
    "jaw_pivot",
    # Head surface features. A dragon's eyes, ears and nostrils are obvious to
    # a person looking at a rendered view and have no reliable signature in a
    # vertex cloud -- a socket is a dimple on some models and a bulge on
    # others. They are supplied through the manual overlay instead of guessed.
    "eye.L",
    "eye.R",
    "ear.L",
    "ear.R",
    "nostril",
)

# Landmarks a person or a vision model may supply through
# `skeleton/landmarks.manual.json`. Anything else in that file is rejected
# rather than silently accepted, so a typo cannot invent a landmark.
MANUAL_ALLOWED = frozenset(
    {
        "eye.L",
        "eye.R",
        "ear.L",
        "ear.R",
        "nostril",
        "head_base",
        "head_top",
        "neck_top",
        "snout",
        "skull",
        "neck_base",
        "jaw_pivot",
    }
)
MANUAL_FILE = "landmarks.manual.json"


def _vertices(model: Path):
    import numpy as np
    import trimesh

    loaded = trimesh.load(model, force="scene")
    parts = [
        geometry.vertices
        for geometry in loaded.dump()
        if getattr(geometry, "vertices", None) is not None and len(geometry.vertices)
    ]
    if not parts:
        raise ConfigError(f"Model has no vertices: {model}")
    return np.vstack(parts)


def _symmetry_axis(vertices) -> tuple[int, float, dict[str, float]]:
    """Pick the mirror axis by residual, not by assumption.

    Mirroring the cloud about each axis and measuring how well it lands back on
    itself separates the true plane from the others by a wide margin, so the
    choice is evidence rather than convention.
    """
    import numpy as np
    from scipy.spatial import cKDTree

    tree = cKDTree(vertices)
    sample = vertices[:: max(1, len(vertices) // 6000)]
    residuals = {}
    for axis in range(3):
        mirrored = sample.copy()
        mirrored[:, axis] = 2 * float(np.median(vertices[:, axis])) - mirrored[:, axis]
        distance, _ = tree.query(mirrored)
        residuals[("x", "y", "z")[axis]] = float(np.median(distance))
    best = min(range(3), key=lambda axis: residuals[("x", "y", "z")[axis]])
    return best, float(np.median(vertices[:, best])), residuals


def _medial_curve(vertices, axis: int, long_axis: int, up_axis: int, bins: int = 48):
    """Centroid of near-plane vertices per slice along the body axis."""
    import numpy as np

    near = vertices[
        np.abs(vertices[:, axis] - np.median(vertices[:, axis]))
        < 0.06 * np.ptp(vertices[:, axis])
    ]
    if len(near) < bins:
        near = vertices
    values = near[:, long_axis]
    edges = np.linspace(values.min(), values.max(), bins + 1)
    curve = []
    for index in range(bins):
        mask = (values >= edges[index]) & (values < edges[index + 1])
        if mask.sum() < 8:
            continue
        slab = near[mask]
        point = [0.0, 0.0, 0.0]
        point[long_axis] = float((edges[index] + edges[index + 1]) / 2)
        point[axis] = float(np.median(slab[:, axis]))
        point[up_axis] = float(np.median(slab[:, up_axis]))
        curve.append((point, int(mask.sum())))
    if not curve:
        raise ConfigError("Could not derive a medial curve from the mesh.")
    return curve


def _at(curve, long_axis: int, value: float) -> tuple[float, float, float]:
    """The medial curve at one position along the body axis, interpolated.

    Interpolated rather than snapped to the nearest sample. The curve is
    sampled in 48 bins over the whole body, which is coarser than the features
    that matter at the head: snapping put a measured occiput and the neck
    landmark behind it on the *same* sample, which would have seeded two
    competing parts on one voxel.
    """
    ordered = sorted(curve, key=lambda item: item[0][long_axis])
    positions = [item[0][long_axis] for item in ordered]
    if value <= positions[0]:
        return tuple(float(v) for v in ordered[0][0])
    if value >= positions[-1]:
        return tuple(float(v) for v in ordered[-1][0])
    for index in range(1, len(ordered)):
        if value <= positions[index]:
            low, high = ordered[index - 1][0], ordered[index][0]
            span = positions[index] - positions[index - 1]
            fraction = 0.0 if span <= 0 else (value - positions[index - 1]) / span
            return tuple(
                float(low[axis] + (high[axis] - low[axis]) * fraction)
                for axis in range(3)
            )
    return tuple(float(v) for v in ordered[-1][0])


def _foot_clusters(vertices, up_axis: int, axis: int, long_axis: int):
    import numpy as np
    from scipy.cluster.hierarchy import fcluster, linkage

    scale = float(np.ptp(vertices[:, long_axis]))
    floor = vertices[:, up_axis].min() + FOOT_BAND * scale
    low = vertices[vertices[:, up_axis] < floor]
    if len(low) < 40:
        return []
    sample = low[:: max(1, len(low) // 4000)]
    flat = sample[:, [axis, long_axis]]
    labels = fcluster(
        linkage(flat, "single"), FOOT_CLUSTER_DISTANCE * scale, criterion="distance"
    )
    clusters = []
    for label in sorted(set(labels)):
        members = sample[labels == label]
        if len(members) < 20:
            continue
        clusters.append(tuple(float(v) for v in members.mean(axis=0)))
    return clusters


def _section_profile(
    vertices, axis: int, up_axis: int, long_axis: int, plane: float,
    low: float, high: float, samples: int = 160, window: float = 1 / 40,
):
    """A cross-section size proxy along the body axis, near the midline.

    Half-width times height, at the 5th/95th percentile so a stray vertex
    cannot define a slice, and restricted to a band around the mirror plane so
    a spread wing never contributes to the body's own cross-section.

    Sampled with an **overlapping moving window** rather than disjoint bins.
    That is not a refinement, it is the difference between working and not: a
    dragon's occiput is about one bin wide, so with disjoint bins its depth
    depends on where the bin edges happen to fall, and shifting the profile's
    start by a hundredth of the body length was enough to smear a 39% waist
    down to 13% and lose it. Decoupling the window's width from the sampling
    step removes that phase sensitivity entirely.
    """
    import numpy as np

    span = float(np.ptp(vertices[:, axis]))
    near = vertices[np.abs(vertices[:, axis] - plane) < 0.06 * span]
    if len(near) < samples:
        return [], []
    reach = abs(high - low) * window
    if reach <= 0:
        return [], []
    values = near[:, long_axis]
    centres, areas = [], []
    for centre in np.linspace(low, high, samples):
        selected = near[np.abs(values - centre) <= reach]
        if len(selected) < 12:
            continue
        half = float(np.percentile(np.abs(selected[:, axis] - plane), 95))
        height = float(
            np.percentile(selected[:, up_axis], 95)
            - np.percentile(selected[:, up_axis], 5)
        )
        centres.append(float(centre))
        areas.append(half * height)
    return centres, areas


def _occiput(centres, areas) -> tuple[float, float, float] | None:
    """The neck-to-head constriction: the most prominent local minimum.

    Local, not global -- the profile also tapers all the way to the snout, so
    the smallest slice overall is the nose tip, and taking it would put the
    head's rear boundary at the front of the face.

    Depth comes from `scipy.signal.peak_prominences`, which measures a valley
    against the highest ground reachable before a *deeper* valley on either
    side. That is stricter than scanning the whole profile for a maximum, and
    it is what keeps a second waist further along from being measured against
    the first one's shoulder.

    The prominence is then divided by the shoulder it was measured from, so
    the test reads as "this waist is at least 8% narrower than the mesh on
    either side of it" and means the same thing whatever the model's scale.
    The runner-up's depth is returned too: how far the winner stands clear of
    the next candidate is what says whether the detection was comfortable, and
    a single number could not.
    """
    import numpy as np
    from scipy.signal import find_peaks, peak_prominences

    if len(areas) < 7:
        return None
    profile = np.asarray(areas, dtype=float)
    valleys, _ = find_peaks(-profile)
    if not len(valleys):
        return None
    prominences, _, _ = peak_prominences(-profile, valleys)

    # shoulder = the level the prominence was measured down from.
    shoulders = profile[valleys] + prominences
    usable = shoulders > 0
    if not usable.any():
        return None
    depths = np.zeros_like(prominences)
    depths[usable] = prominences[usable] / shoulders[usable]

    order = np.argsort(-depths)
    best = int(order[0])
    if depths[best] < OCCIPUT_DEPTH:
        return None
    runner_up = float(depths[order[1]]) if len(order) > 1 else 0.0
    return float(centres[valleys[best]]), float(depths[best]), runner_up


def _crown(vertices, axis: int, up_axis: int, long_axis: int, plane: float,
           low: float, high: float):
    """The highest point of the head, near the midline.

    The head is a bulb and its crown is the part a neck seed steals first, so
    it is worth a landmark of its own.
    """
    import numpy as np

    span = float(np.ptp(vertices[:, axis]))
    band = vertices[
        (vertices[:, long_axis] >= min(low, high))
        & (vertices[:, long_axis] <= max(low, high))
        & (np.abs(vertices[:, axis] - plane) < 0.10 * span)
    ]
    if len(band) < 12:
        return None
    return band[int(np.argmax(band[:, up_axis]))]


def propose(model: Path, target_id: str) -> LandmarkDocument:
    """Derive landmarks from one mesh without touching its bytes."""
    import numpy as np

    vertices = _vertices(model)
    axis, plane, residuals = _symmetry_axis(vertices)
    extents = [float(np.ptp(vertices[:, index])) for index in range(3)]
    up_axis = int(np.argmin(extents))
    if up_axis == axis:
        up_axis = next(index for index in range(3) if index != axis)
    long_axis = next(index for index in range(3) if index not in (axis, up_axis))

    curve = _medial_curve(vertices, axis, long_axis, up_axis)
    low = min(point[long_axis] for point, _ in curve)
    high = max(point[long_axis] for point, _ in curve)

    # Head or tail? A tail tapers to a point; a head is a bulb that ends
    # abruptly. Comparing the median half-width of the outermost slice at each
    # end separates them, and the band is kept narrow so a wing rooted just
    # behind the skull cannot be mistaken for the head itself.
    span = high - low

    def end_thickness(from_high: bool) -> float:
        edge = high if from_high else low
        band = vertices[np.abs(vertices[:, long_axis] - edge) < END_BAND * span]
        if not len(band):
            return float("inf")
        return float(np.median(np.abs(band[:, axis] - plane)))

    head_thickness, tail_thickness = end_thickness(True), end_thickness(False)
    head_at_high = head_thickness > tail_thickness
    head_value, tail_value = (high, low) if head_at_high else (low, high)
    forward = 1.0 if head_at_high else -1.0

    def along(fraction: float) -> float:
        return tail_value + (head_value - tail_value) * fraction

    clusters = _foot_clusters(vertices, up_axis, axis, long_axis)
    feet_by_side: dict[str, list[tuple[float, ...]]] = {"left": [], "right": []}
    for cluster in clusters:
        offset = cluster[axis] - plane
        # Facing `forward` with the short axis up, a right-handed frame puts the
        # character's right on the negative side of the mirror plane.
        side = "left" if offset * forward > 0 else "right"
        feet_by_side[side].append(cluster)
    for side in feet_by_side:
        feet_by_side[side].sort(
            key=lambda point: point[long_axis] * forward, reverse=True
        )

    wings = vertices[
        np.abs(vertices[:, axis] - plane)
        > WING_MIN_SPAN_FRACTION * float(np.ptp(vertices[:, axis]))
    ]

    marks: list[Landmark] = []

    def add(name: str, point, side: str, confidence: str, evidence: str) -> None:
        marks.append(
            Landmark(
                name=name,
                point=(float(point[0]), float(point[1]), float(point[2])),
                side=side,
                source="geometric",
                confidence=confidence,
                evidence=evidence,
            )
        )

    # Where the feet touch down is measured, so the girdles anchor to them
    # rather than to a fraction of the body axis. Guessing those positions
    # instead makes the centre chain contradict the paired landmarks derived
    # from the same feet.
    front = [feet[0] for feet in feet_by_side.values() if feet]
    hind = [feet[1] for feet in feet_by_side.values() if len(feet) > 1]
    girdles = len(front) >= 1 and len(hind) >= 1
    if girdles:
        chest_value = sum(foot[long_axis] for foot in front) / len(front)
        hip_value = sum(foot[long_axis] for foot in hind) / len(hind)
    else:
        chest_value, hip_value = along(0.80), along(0.52)

    def between(start: float, end: float, fraction: float) -> float:
        return start + (end - start) * fraction

    anchored = "ground-contact clusters" if girdles else "body-axis fraction"
    girdle_confidence = "high" if girdles else "medium"

    # Where does the head begin? Measure it rather than take a fraction of the
    # body axis: the neck narrows into the skull, and that waist is a local
    # minimum in the cross-section profile. With it in hand, `neck_base` and
    # `skull` stop being guesses at 0.30 and 0.78 of the way along and become
    # positions relative to a boundary the mesh actually has.
    section_centres, section_areas = _section_profile(
        vertices, axis, up_axis, long_axis, plane, chest_value, head_value
    )
    occiput = _occiput(section_centres, section_areas)
    head_base_value = occiput[0] if occiput else None

    if head_base_value is not None:
        neck_base_value = between(chest_value, head_base_value, 0.55)
        skull_value = between(head_base_value, head_value, 0.45)
        head_confidence = "high"
        head_evidence = (
            "narrowest cross-section between the neck and the snout"
        )
        skull_evidence = "midway between the measured occiput and the snout"
        neck_evidence = "behind the measured occiput"
        neck_confidence = "medium"
    else:
        neck_base_value = between(chest_value, head_value, 0.3)
        skull_value = between(chest_value, head_value, 0.78)
        head_confidence = "low"
        head_evidence = "no measurable occiput"
        skull_evidence = "behind the snout"
        neck_evidence = "ahead of the shoulder girdle"
        neck_confidence = "low"

    chain = (
        ("tail_tip", tail_value, "high", "medial curve at the tapering end"),
        ("tail_mid", between(tail_value, hip_value, 0.45), "medium",
         "midway from the tail tip to the hips"),
        ("tail_base", between(tail_value, hip_value, 0.82), "medium",
         "where the tail meets the hips"),
        ("hip_center", hip_value, girdle_confidence, f"hind {anchored}"),
        ("spine_mid", between(hip_value, chest_value, 0.5), "medium",
         "midway between the girdles"),
        ("chest", chest_value, girdle_confidence, f"front {anchored}"),
        ("neck_base", neck_base_value, neck_confidence, neck_evidence),
        ("skull", skull_value, "medium" if occiput else "low", skull_evidence),
        ("snout", head_value, "high", "medial curve at the blunt end"),
    )
    for name, value, confidence, evidence in chain:
        add(name, _at(curve, long_axis, value), "center", confidence, evidence)

    if head_base_value is not None:
        add(
            "head_base",
            _at(curve, long_axis, head_base_value),
            "center",
            head_confidence,
            head_evidence,
        )
        # Both the head and the neck carry the dorsal crest, and whichever one
        # is anchored on it takes the whole ridge from the other. Seeding only
        # the head's crown swung the error the other way: the head then ran
        # back along the crest into the shoulders. So both get a dorsal anchor,
        # and neither can claim the other's ridge.
        #
        # The head's own crown is measured clear of the occiput, because the
        # tallest point in the head band sits right on the boundary -- it is
        # the tail of the neck's crest, not the skull's crown.
        crown = _crown(
            vertices,
            axis,
            up_axis,
            long_axis,
            plane,
            between(head_base_value, head_value, CROWN_CLEARANCE),
            head_value,
        )
        if crown is not None:
            add(
                "head_top",
                crown,
                "center",
                "high",
                "highest near-midline vertex over the forward part of the skull",
            )
        ridge = _crown(
            vertices, axis, up_axis, long_axis, plane, chest_value, head_base_value
        )
        if ridge is not None:
            add(
                "neck_top",
                ridge,
                "center",
                "high",
                "highest near-midline vertex between the chest and the occiput",
            )

    if len(wings):
        for side in ("left", "right"):
            sign = 1.0 if (side == "left") == (forward > 0) else -1.0
            selected = wings[(wings[:, axis] - plane) * sign > 0]
            if not len(selected):
                continue
            tip = selected[np.argmax(np.abs(selected[:, axis] - plane))]
            add(
                f"wing_tip.{side[0].upper()}",
                tip,
                side,
                "high",
                "furthest vertex from the symmetry plane",
            )
            root_value = float(np.median(selected[:, long_axis]))
            root = list(_at(curve, long_axis, root_value))
            body = vertices[
                np.abs(vertices[:, long_axis] - root_value)
                < 0.02 * float(np.ptp(vertices[:, long_axis]))
            ]
            if len(body):
                span_axis = float(np.ptp(vertices[:, axis]))
                inner = body[np.abs(body[:, axis] - plane) < 0.18 * span_axis]
                if len(inner):
                    root[axis] = plane + sign * float(
                        np.percentile(np.abs(inner[:, axis] - plane), 90)
                    )
                    root[up_axis] = float(np.percentile(inner[:, up_axis], 85))
            add(
                f"wing_root.{side[0].upper()}",
                root,
                side,
                "medium",
                "body surface at the wing band's median position",
            )

    for side, feet in feet_by_side.items():
        initial = side[0].upper()
        for name, cluster in zip(("foot_front", "foot_hind"), feet, strict=False):
            add(
                f"{name}.{initial}",
                cluster,
                side,
                "high",
                "centroid of a ground-contact vertex cluster",
            )
        for joint, foot in zip(("shoulder", "hip"), feet, strict=False):
            point = list(_at(curve, long_axis, foot[long_axis]))
            point[axis] = plane + (foot[axis] - plane) * 0.55
            add(
                f"{joint}.{initial}",
                point,
                side,
                "low",
                "medial curve above the matching foot, drawn inboard",
            )

    return LandmarkDocument(
        target_id=target_id,
        method=METHOD,
        coordinate_system={
            "viewer_space": "right-handed, +Y up, model units",
            "symmetry_axis": ("x", "y", "z")[axis],
            "body_axis": ("x", "y", "z")[long_axis],
            "up_axis": ("x", "y", "z")[up_axis],
        },
        derivation={
            "vertices": int(len(vertices)),
            "symmetry_plane": plane,
            "mirror_residual_median": residuals,
            "head_towards": ("negative", "positive")[int(head_at_high)],
            "end_half_width": {
                "head": head_thickness,
                "tail": tail_thickness,
            },
            "head_position": head_value,
            "tail_position": tail_value,
            "ground_clusters": len(clusters),
            "occiput": (
                {
                    "position": occiput[0],
                    "depth": round(occiput[1], 4),
                    "runner_up_depth": round(occiput[2], 4),
                    "threshold": OCCIPUT_DEPTH,
                }
                if occiput
                else None
            ),
            "side_convention": (
                "Facing the head with the short axis up, a right-handed frame "
                "puts the character's right on the negative side of the mirror "
                "plane. Unverified against donor bone naming."
            ),
            "not_attempted": list(NOT_ATTEMPTED),
            "limitations": [
                "Every point is proposed from geometry; none is verified.",
                "Interior joints leave no reliable surface signature and are "
                "not guessed.",
                "Left/right labels follow a derived convention, not evidence.",
            ],
        },
        landmarks=marks,
        summary={
            "landmarks": len(marks),
            "center": sum(1 for mark in marks if mark.side == "center"),
            "left": sum(1 for mark in marks if mark.side == "left"),
            "right": sum(1 for mark in marks if mark.side == "right"),
            "not_attempted": len(NOT_ATTEMPTED),
            "high_confidence": sum(1 for mark in marks if mark.confidence == "high"),
        },
    )


def _merge_manual(document: LandmarkDocument, run: Path) -> list[str]:
    """Fold a hand- or model-supplied overlay into a proposal.

    The overlay is the answer to landmarks geometry cannot propose. A dragon's
    eyes, ears and nostrils are obvious in a rendered view and have no reliable
    signature in a vertex cloud, so they are asserted here rather than guessed
    there -- and a manual point always wins, because it is evidence and a
    proposal is not.

    Names outside `MANUAL_ALLOWED` are rejected rather than accepted: an
    overlay that can invent an arbitrary landmark is an overlay that turns a
    typo into geometry.
    """
    path = run / "skeleton" / MANUAL_FILE
    if not path.is_file():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ConfigError(f"Invalid JSON in {path}: {error}") from error
    entries = payload.get("landmarks")
    if not isinstance(entries, list):
        raise ConfigError(f"{MANUAL_FILE} has no 'landmarks' list.")

    existing = {mark.name: index for index, mark in enumerate(document.landmarks)}
    applied: list[str] = []
    for entry in entries:
        name = entry.get("name")
        if name not in MANUAL_ALLOWED:
            raise ConfigError(
                f"{MANUAL_FILE} names {name!r}, which is not a landmark this "
                f"overlay may set. Allowed: {', '.join(sorted(MANUAL_ALLOWED))}."
            )
        point = entry.get("point")
        if not (isinstance(point, list) and len(point) == 3):
            raise ConfigError(f"{MANUAL_FILE} entry {name!r} has no 3D point.")
        mark = Landmark(
            name=name,
            point=(float(point[0]), float(point[1]), float(point[2])),
            side=(
                "left" if name.endswith(".L")
                else "right" if name.endswith(".R")
                else "center"
            ),
            source="manual",
            confidence=entry.get("confidence", "high"),
            evidence=entry.get("evidence", "supplied through the manual overlay"),
        )
        if name in existing:
            document.landmarks[existing[name]] = mark
        else:
            document.landmarks.append(mark)
        applied.append(name)
    return applied


def build(
    project: Project, run_ref: str, character_id: str | None = None
) -> dict[str, Any]:
    """Write proposed landmarks beside one generation run."""
    from . import generations as generations_mod

    backend, run = generations_mod._resolve_run(project, run_ref)
    request = generations_mod._json(
        generations_mod._relative_file(run, "request.json")
    )
    character_id = character_id or generations_mod._request_name(request)
    model_relative = generations_mod._model_relative(run, request)
    model = generations_mod._relative_file(run, model_relative)
    before = generations_mod._sha256(model)

    document = propose(model, f"{backend}/{run.name}")
    manual = _merge_manual(document, run)
    if manual:
        document.derivation["manual_overlay"] = {
            "file": f"skeleton/{MANUAL_FILE}",
            "applied": manual,
        }
        document.summary["landmarks"] = len(document.landmarks)
        document.summary["manual"] = len(manual)
        for key, side in (("center", "center"), ("left", "left"), ("right", "right")):
            document.summary[key] = sum(
                1 for mark in document.landmarks if mark.side == side
            )
        document.summary["high_confidence"] = sum(
            1 for mark in document.landmarks if mark.confidence == "high"
        )

    if generations_mod._sha256(model) != before:
        raise ConfigError("Generated model changed while proposing landmarks.")

    stage = run / "skeleton"
    stage.mkdir(parents=True, exist_ok=True)
    path = stage / "landmarks.json"
    temp = path.with_suffix(".json.part")
    temp.write_text(
        document.model_dump_json(indent=2, by_alias=True) + "\n", encoding="utf-8"
    )
    temp.replace(path)
    manifest_path = generations_mod.write_manifest(run, character_id)
    return {
        "target": f"{backend}/{run.name}",
        "character_id": character_id,
        "method": METHOD,
        "landmarks": str(path),
        "manifest": str(manifest_path),
        "summary": document.summary,
        "axes": document.coordinate_system,
        "head_towards": document.derivation["head_towards"],
        "not_attempted": list(NOT_ATTEMPTED),
        "manual": manual,
        "names": [mark.name for mark in document.landmarks],
    }
