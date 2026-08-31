"""Produce and score labelled body-part volumes.

Two kinds of labelled volume live here, and the spec requires them to stay
distinguishable:

* A **reference** labelling is derived from a donor's own authored rig. It is
  the closest thing to an answer key this workspace has.
* A **proposal** is derived from target geometry alone. It never becomes a
  reference by being good; its accuracy is whatever a scored run measured.

The point of keeping both is that the same proposal method can be run on the
donor, where an answer key exists, before it is pointed at a target where none
does. That is the difference between a number and an opinion.

**Why the reference is seeded from bones rather than from skin weights.** The
first design read the donor's authored weights, took each vertex's dominant
bone, and mapped it to a part -- 21,228 vertices labelled for free. That does
not survive contact with the browser model: glTF export splits vertices at UV
and normal seams, so the donor's `Dragon` mesh arrives as 21,050 vertices
against the weight document's 19,172, under a different name, with no
correspondence between them. Rather than invent a correspondence, the reference
is seeded by rasterising the donor's authored **bone segments**, which are
already in the browser model's coordinate space. It is a weaker claim than
per-vertex weights and is labelled as such.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import body_parts, voxels
from .config import ConfigError
from .project import Project

REFERENCE_METHOD = "authored-bone-seed/v1"
PROPOSAL_METHOD = "voxel-geodesic-watershed/v1"
SCHEMA = "charctx.part-volume/v1"

DEFAULT_RESOLUTION = 128
DISPLAY_POOL = 2

# Which part each proposed landmark stands for. Nine parts have no landmark at
# all -- `jaw`, and `upper_arm`, `forearm`, `shin`, `wing_arm` on both sides --
# and that gap is the measurement this packet exists to expose: a sparse
# landmark set structurally cannot produce a quarter of the taxonomy.
#
# `head` deliberately takes four anchors where every other part takes one or
# two. It is a bulb on the end of a chain, and a bulb loses its crown to
# whatever is seeded above it unless the crown is seeded too.
LANDMARK_PARTS: dict[str, str] = {
    "snout": "head",
    "skull": "head",
    "head_base": "head",
    "head_top": "head",
    # Head surface features. Geometry does not propose these; they arrive
    # through the manual overlay, from a person or a vision model reading a
    # rendered view.
    "eye.L": "eye.L",
    "eye.R": "eye.R",
    "ear.L": "ear.L",
    "ear.R": "ear.R",
    "nostril": "nostril",
    "neck_base": "neck",
    "neck_top": "neck",
    "chest": "chest",
    "spine_mid": "abdomen",
    "hip_center": "pelvis",
    "tail_base": "tail_base",
    "tail_mid": "tail_mid",
    "tail_tip": "tail_tip",
    **{
        f"{landmark}.{side}": f"{part}.{side}"
        for side in ("L", "R")
        for landmark, part in (
            ("shoulder", "shoulder"),
            ("foot_front", "hand"),
            ("hip", "thigh"),
            ("foot_hind", "foot"),
            ("wing_root", "wing_root"),
            ("wing_tip", "wing_hand"),
        )
    },
}


# --------------------------------------------------------------------------
# Seeding
# --------------------------------------------------------------------------


def _bone_seeds(
    skeleton: dict[str, Any], mapping: dict[str, str], pitch: float
) -> tuple[Any, Any]:
    """Sample points along every bone segment, carrying its part index."""
    import numpy as np

    points: list[Any] = []
    labels: list[int] = []
    step = max(pitch * 0.5, 1e-9)
    for armature in skeleton["armatures"]:
        for bone in armature["bones"]:
            part = mapping.get(bone["name"])
            if part is None:
                continue
            index = body_parts.part_index(part)
            head = np.asarray(bone["head"], dtype=float)
            tail = np.asarray(bone["tail"], dtype=float)
            length = float(np.linalg.norm(tail - head))
            count = max(int(length / step) + 1, 2)
            samples = head + np.linspace(0.0, 1.0, count)[:, None] * (tail - head)
            points.append(samples)
            labels.extend([index] * count)
    if not points:
        raise ConfigError("No donor bone mapped to a part; nothing to seed.")
    return np.vstack(points), np.asarray(labels, dtype=np.int16)


def _landmark_seeds(document: Any) -> tuple[Any, Any, list[str]]:
    """Landmark points that stand for a part, and the ones that do not."""
    import numpy as np

    points: list[list[float]] = []
    labels: list[int] = []
    ignored: list[str] = []
    for mark in document.landmarks:
        part = LANDMARK_PARTS.get(mark.name)
        if part is None:
            ignored.append(mark.name)
            continue
        points.append(list(mark.point))
        labels.append(body_parts.part_index(part))
    if not points:
        raise ConfigError("No proposed landmark maps to a part.")
    return (
        np.asarray(points, dtype=float),
        np.asarray(labels, dtype=np.int16),
        ignored,
    )


def _centroid_seeds(grid: voxels.Grid, labels: Any) -> tuple[Any, Any]:
    """One seed per part, at the part's own centre of mass.

    The clean ablation: it holds the part set and the geometry fixed and
    changes only how densely each part is seeded, so what it measures is the
    cost of sparsity by itself -- not the cost of sparsity confounded with a
    landmark proposer's mistakes.
    """
    import numpy as np
    from scipy import ndimage

    present = [
        part.index for part in body_parts.PARTS if (labels == part.index).any()
    ]
    if not present:
        raise ConfigError("The reference volume has no labelled part.")
    centres = ndimage.center_of_mass(labels > 0, labels, present)
    points = []
    kept = []
    for index, centre in zip(present, centres, strict=True):
        voxel = tuple(int(round(value)) for value in centre)
        # A crescent-shaped part's centroid can fall outside it; snap back to
        # the nearest voxel that actually carries the label.
        if labels[voxel] != index:
            candidates = np.argwhere(labels == index)
            distances = np.linalg.norm(candidates - np.asarray(voxel), axis=1)
            voxel = tuple(int(value) for value in candidates[distances.argmin()])
        points.append(grid.to_world(np.asarray([voxel]))[0])
        kept.append(index)
    return np.asarray(points, dtype=float), np.asarray(kept, dtype=np.int16)


# --------------------------------------------------------------------------
# Document assembly
# --------------------------------------------------------------------------


def _document(
    target_id: str,
    grid: voxels.Grid,
    labels: Any,
    method: str,
    reference: bool,
    derivation: dict[str, Any],
) -> dict[str, Any]:
    import numpy as np

    display, size = voxels.pool(labels, DISPLAY_POOL)
    occupied = np.flatnonzero(display)
    values = display.ravel()[occupied]

    counts = {
        part.name: int((labels == part.index).sum()) for part in body_parts.PARTS
    }
    solid = int(grid.solid.sum())
    labelled = int((labels > 0).sum())

    # A part with no voxels is listed at zero rather than omitted: a missing
    # part must be visible, not inferred from an absence.
    entries = [
        {
            "name": part.name,
            "index": part.index,
            "side": part.side,
            "color": part.color,
            "parent": part.parent,
            "voxels": counts[part.name],
        }
        for part in body_parts.PARTS
    ]
    split = {
        part.name: voxels.component_split(labels, part.index)
        for part in body_parts.PARTS
        if counts[part.name] > 0
    }

    return {
        "schema": SCHEMA,
        "target_id": target_id,
        "taxonomy": body_parts.TAXONOMY,
        "grid": {
            "resolution": grid.resolution,
            "pitch": grid.pitch,
            "origin": list(grid.origin),
            "display_resolution": size,
            "display_pitch": grid.pitch * DISPLAY_POOL,
        },
        "parts": entries,
        "voxels": {
            "encoding": "linear-index",
            "resolution": size,
            "index": [int(value) for value in occupied],
            "part": [int(value) for value in values],
        },
        "derivation": {
            "method": method,
            "reference": reference,
            **derivation,
            "empty_parts": [name for name, count in counts.items() if count == 0],
            # More than one component means the flood crossed a contact -- a
            # folded wing against a flank, a tail against a leg. Reported
            # rather than averaged away, because it is the real failure mode.
            "split_parts": {
                name: pieces for name, pieces in split.items() if pieces > 1
            },
        },
        "summary": {
            "coarse_voxels": {
                name: sum(
                    counts[part.name]
                    for part in body_parts.PARTS
                    if body_parts.coarse(part.name) == name
                )
                for name in sorted(
                    {body_parts.coarse(part.name) for part in body_parts.PARTS}
                )
                if any(
                    counts[part.name]
                    for part in body_parts.PARTS
                    if body_parts.coarse(part.name) == name
                )
            },
            "solid_voxels": solid,
            "labelled_voxels": labelled,
            "labelled_fraction": round(labelled / solid, 6) if solid else 0.0,
            "parts_present": sum(1 for count in counts.values() if count > 0),
            "parts_total": len(body_parts.PARTS),
            "display_voxels": int(len(occupied)),
        },
    }


def _write(path: Path, payload: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".part")
    temp.write_text(payload, encoding="utf-8")
    temp.replace(path)
    return path


def _scene(path: Path) -> Any:
    import trimesh

    return trimesh.load(path, force="scene")


def _donor(
    project: Project, donor_id: str
) -> tuple[dict[str, Any], dict[str, str], list[str], Path]:
    """The donor's skeleton, its part map, unused rules, and its package."""
    from .assets import _inspection, _package

    package, _ = _package(project, donor_id)
    inspection = _inspection(package)
    if inspection is None or inspection.skeleton is None:
        raise ConfigError(
            f"Donor {donor_id!r} has no extracted skeleton. "
            f"Run `charctx assets build {donor_id}` first."
        )
    skeleton = json.loads(
        (package / inspection.skeleton.path).read_text(encoding="utf-8")
    )
    parents = {
        bone["name"]: bone["parent"]
        for armature in skeleton["armatures"]
        for bone in armature["bones"]
    }
    roots = body_parts.roots_for(donor_id)
    mapping = body_parts.map_bones(parents, roots)
    return skeleton, mapping, body_parts.unused_rules(parents, roots), package


def _weight_coverage(package: Path, mapping: dict[str, str]) -> dict[str, Any]:
    """Check the part map against the rig's weight-bearing bones.

    Per-vertex weights cannot label the browser model, but they still say
    which bones actually deform anything -- so they are used to prove the map
    is total over the bones that matter, rather than merely over the bones
    that exist.
    """
    path = package / "inspection" / "skin-weights.json"
    if not path.is_file():
        return {"available": False}
    document = json.loads(path.read_text(encoding="utf-8"))
    named = {
        name
        for binding in document["bindings"]
        for name in binding.get("bone_names", [])
    }
    unmapped = sorted(named - set(mapping))
    return {
        "available": True,
        "weight_bearing_bones": len(named),
        "unmapped": unmapped,
        "total": not unmapped,
    }


# --------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------


def _label(
    scene: Any, points: Any, values: Any, resolution: int
) -> tuple[voxels.Grid, Any, dict[str, Any], int]:
    grid, report = voxels.voxelize(scene, resolution=resolution)
    seeds = voxels.seed_labels(grid, points, values)
    labels, rounds = voxels.watershed(grid, seeds)
    return grid, labels, report, rounds


def reference(
    project: Project, donor_id: str, resolution: int = DEFAULT_RESOLUTION
) -> dict[str, Any]:
    """Label a donor's volume from its own authored bone placement."""
    skeleton, mapping, unused, package = _donor(project, donor_id)
    model = package / "web" / "model.glb"
    if not model.is_file():
        raise ConfigError(f"Donor {donor_id!r} has no browser model at {model}.")

    scene = _scene(model)
    probe, _ = voxels.voxelize(scene, resolution=resolution)
    points, values = _bone_seeds(skeleton, mapping, probe.pitch)
    grid, labels, report, rounds = _label(scene, points, values, resolution)

    document = _document(
        target_id=donor_id,
        grid=grid,
        labels=labels,
        method=REFERENCE_METHOD,
        reference=True,
        derivation={
            "donor_id": donor_id,
            "bones_mapped": len(mapping),
            "unused_rules": unused,
            "seed_points": int(len(points)),
            "flood_rounds": rounds,
            "weight_coverage": _weight_coverage(package, mapping),
            "voxelization": report,
            "limitations": [
                "Seeded from authored bone segments, not from per-vertex "
                "weights: glTF export splits vertices at seams, so the "
                "browser model carries no correspondence to the weight "
                "document.",
                "A bone's influence region is approximated by its segment, "
                "so a part boundary sits midway between bones rather than "
                "where the authored weights actually cross over.",
                "One donor of unknown provenance; nothing here establishes "
                "what generalizes to another dragon.",
            ],
        },
    )
    path = _write(
        package / "parts" / "parts.json", json.dumps(document, indent=2) + "\n"
    )
    return {
        "target": donor_id,
        "method": REFERENCE_METHOD,
        "parts": str(path),
        "grid": document["grid"],
        "summary": document["summary"],
        "voxelization": report,
        "weight_coverage": document["derivation"]["weight_coverage"],
        "empty_parts": document["derivation"]["empty_parts"],
        "split_parts": document["derivation"]["split_parts"],
    }


def segment(
    project: Project,
    run_ref: str,
    character_id: str | None = None,
    resolution: int = DEFAULT_RESOLUTION,
) -> dict[str, Any]:
    """Classify a generation run's volume from its proposed landmarks."""
    from . import generations as generations_mod
    from .asset_models import LandmarkDocument

    backend, run = generations_mod._resolve_run(project, run_ref)
    request = generations_mod._json(generations_mod._relative_file(run, "request.json"))
    character_id = character_id or generations_mod._request_name(request)
    landmarks_path = run / "skeleton" / "landmarks.json"
    if not landmarks_path.is_file():
        raise ConfigError(
            "Part segmentation needs proposed landmarks. Run "
            "`charctx skeleton landmarks <backend>/<run>` first."
        )
    document = LandmarkDocument.model_validate_json(
        landmarks_path.read_text(encoding="utf-8")
    )
    points, values, ignored = _landmark_seeds(document)

    model = generations_mod._relative_file(
        run, generations_mod._model_relative(run, request)
    )
    grid, labels, report, rounds = _label(_scene(model), points, values, resolution)

    unreachable = [
        part.name
        for part in body_parts.PARTS
        if part.index in set(int(value) for value in values)
        and not (labels == part.index).any()
    ]
    result = _document(
        target_id=f"{backend}/{run.name}",
        grid=grid,
        labels=labels,
        method=PROPOSAL_METHOD,
        reference=False,
        derivation={
            "seeds": "landmarks",
            "landmark_method": document.method,
            "seed_points": int(len(points)),
            "seeded_parts": sorted(
                {body_parts.BY_INDEX[int(value)].name for value in values}
            ),
            # Ten parts have no landmark to seed them, so they cannot appear
            # at all. Naming them is the point, not a footnote.
            "unseedable_parts": sorted(
                part.name
                for part in body_parts.PARTS
                if part.index not in set(int(value) for value in values)
            ),
            "ignored_landmarks": ignored,
            "seeded_but_empty": unreachable,
            "flood_rounds": rounds,
            "voxelization": report,
            "limitations": [
                "Every part boundary is midway between two landmarks, so a "
                "boundary is only as good as the two points that bracket it.",
                "Parts with no landmark are absent, not misplaced.",
                "The flood can cross a thin contact between touching parts; "
                "`split_parts` reports where that happened.",
            ],
        },
    )
    path = _write(
        run / "parts" / "parts.json", json.dumps(result, indent=2) + "\n"
    )
    _write(
        run / "parts" / "manifest.json",
        json.dumps(
            {
                "schema": "charctx.part-stage/v1",
                "target_id": f"{backend}/{run.name}",
                "character_id": character_id,
                "taxonomy": body_parts.TAXONOMY,
                "method": PROPOSAL_METHOD,
                "parts": "parts/parts.json",
            },
            indent=2,
        )
        + "\n",
    )
    manifest_path = generations_mod.write_manifest(run, character_id)
    return {
        "target": f"{backend}/{run.name}",
        "character_id": character_id,
        "method": PROPOSAL_METHOD,
        "parts": str(path),
        "manifest": str(manifest_path),
        "grid": result["grid"],
        "summary": result["summary"],
        "voxelization": report,
        "unseedable_parts": result["derivation"]["unseedable_parts"],
        "empty_parts": result["derivation"]["empty_parts"],
        "split_parts": result["derivation"]["split_parts"],
    }


def _iou(proposal: Any, truth: Any) -> dict[str, Any]:
    """Per-part intersection over union, plus overall voxel agreement.

    Per-part on purpose. A single aggregate is dominated by the torso and the
    tail, which are large and easy, and would report a healthy number for a
    run that lost both wings entirely.
    """
    import numpy as np

    rows: list[dict[str, Any]] = []
    for part in body_parts.PARTS:
        expected = truth == part.index
        found = proposal == part.index
        union = int((expected | found).sum())
        if union == 0:
            continue
        intersection = int((expected & found).sum())
        rows.append(
            {
                "part": part.name,
                "iou": round(intersection / union, 4),
                "reference_voxels": int(expected.sum()),
                "proposal_voxels": int(found.sum()),
            }
        )
    considered = truth > 0
    agreement = (
        float((proposal[considered] == truth[considered]).mean())
        if considered.any()
        else 0.0
    )
    scored = [row["iou"] for row in rows]
    missed = [row["part"] for row in rows if row["proposal_voxels"] == 0]
    return {
        "parts_scored": len(rows),
        "voxel_accuracy": round(agreement, 4),
        "mean_iou": round(float(np.mean(scored)), 4) if scored else 0.0,
        "median_iou": round(float(np.median(scored)), 4) if scored else 0.0,
        "worst": sorted(rows, key=lambda row: row["iou"])[:6],
        "best": sorted(rows, key=lambda row: row["iou"], reverse=True)[:4],
        "missed_entirely": missed,
        "per_part": rows,
    }


def score(
    project: Project,
    donor_id: str,
    mode: str = "centroid",
    resolution: int = DEFAULT_RESOLUTION,
) -> dict[str, Any]:
    """Run a sparse-seed proposal on the donor and score it against its rig.

    Two modes, measuring two different things:

    * `centroid` seeds one point per part at that part's own centre of mass.
      Everything but seed density is held fixed, so what it isolates is the
      cost of sparsity alone.
    * `landmarks` runs the real geometric landmark proposer on the donor and
      seeds from its output. That is the whole donor-independent pipeline
      end to end -- but the donor's rest pose is rearing and curled, so a
      poor result here is as likely to indict the pose as the method.
    """
    if mode not in ("centroid", "landmarks"):
        raise ConfigError(f"Unknown scoring mode {mode!r}; use centroid or landmarks.")

    skeleton, mapping, _, package = _donor(project, donor_id)
    model = package / "web" / "model.glb"
    if not model.is_file():
        raise ConfigError(f"Donor {donor_id!r} has no browser model at {model}.")
    scene = _scene(model)

    grid, report = voxels.voxelize(scene, resolution=resolution)
    truth_points, truth_values = _bone_seeds(skeleton, mapping, grid.pitch)
    truth, truth_rounds = voxels.watershed(
        grid, voxels.seed_labels(grid, truth_points, truth_values)
    )

    if mode == "centroid":
        points, values = _centroid_seeds(grid, truth)
        detail: dict[str, Any] = {"seeds": "part centroids of the reference"}
    else:
        from . import landmarks as landmarks_mod

        document = landmarks_mod.propose(model, donor_id)
        points, values, ignored = _landmark_seeds(document)
        detail = {
            "seeds": "geometric landmark proposal",
            "landmark_method": document.method,
            "head_towards": document.derivation["head_towards"],
            "ignored_landmarks": ignored,
        }

    proposal, rounds = voxels.watershed(
        grid, voxels.seed_labels(grid, points, values)
    )
    metrics = _iou(proposal, truth)

    seeded = {int(value) for value in values}
    return {
        "target": donor_id,
        "mode": mode,
        "reference_method": REFERENCE_METHOD,
        "proposal_method": PROPOSAL_METHOD,
        "grid": {"resolution": grid.resolution, "pitch": grid.pitch},
        "solid_voxels": int(grid.solid.sum()),
        "reference_seed_points": int(len(truth_points)),
        "proposal_seed_points": int(len(points)),
        "reference_flood_rounds": truth_rounds,
        "proposal_flood_rounds": rounds,
        # Parts no seed can reach are absent by construction, not misplaced.
        # Counting them separately keeps the IoU honest.
        "unseedable_parts": sorted(
            part.name for part in body_parts.PARTS if part.index not in seeded
        ),
        "voxelization": report,
        "metrics": metrics,
        **detail,
    }
