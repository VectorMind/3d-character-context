"""Synthesize a skeleton onto a generated mesh from a donor hierarchy.

Step 1 is deliberately the crudest fit that can exist: one uniform scale and
one translation, chosen so the donor skeleton is contained in the target's
measured bounding box. It is expected to look wrong. The point is that the
*way* it looks wrong -- which axis is starved, how far the pose is from the
target's stance -- is measurable and visible, and directs the landmark-driven
fit that replaces it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .asset_models import (
    FittedArmature,
    FittedBone,
    FittedSkeletonDocument,
    SkeletonDocument,
)
from .config import ConfigError
from .project import Project

AXES = ("x", "y", "z")
FIT_METHOD = "uniform-contain-bounds/v1"


def _donor_skeleton(project: Project, donor_id: str) -> tuple[SkeletonDocument, Path]:
    from .assets import _inspection, _package

    package, _ = _package(project, donor_id)
    inspection = _inspection(package)
    if inspection is None or inspection.skeleton is None:
        raise ConfigError(
            f"Donor {donor_id!r} has no extracted skeleton. "
            f"Run `charctx assets build {donor_id}` first."
        )
    path = package / inspection.skeleton.path
    if not path.is_file():
        raise ConfigError(f"Declared donor skeleton is missing: {path}")
    return (
        SkeletonDocument.model_validate_json(path.read_text(encoding="utf-8")),
        path,
    )


def _target_bounds(
    run: Path, measurements: str | None
) -> tuple[list[float], list[float]]:
    if not measurements:
        raise ConfigError(
            "The generation has no measurement sidecar; run `charctx report` on "
            "its model first."
        )
    data = json.loads((run / measurements).read_text(encoding="utf-8"))
    minimum = data.get("bounds_min")
    maximum = data.get("bounds_max")
    if not (isinstance(minimum, list) and isinstance(maximum, list)):
        raise ConfigError(f"Measurement sidecar has no usable bounds: {measurements}")
    if len(minimum) != 3 or len(maximum) != 3:
        raise ConfigError(f"Measurement bounds are not 3D: {measurements}")
    return [float(v) for v in minimum], [float(v) for v in maximum]


def _skeleton_bounds(
    document: SkeletonDocument,
) -> tuple[list[float], list[float]]:
    points = [
        point
        for armature in document.armatures
        for bone in armature.bones
        for point in (bone.head, bone.tail)
    ]
    if not points:
        raise ConfigError("Donor skeleton contains no bones.")
    return (
        [min(point[axis] for point in points) for axis in range(3)],
        [max(point[axis] for point in points) for axis in range(3)],
    )


def _transform(
    donor_min: list[float],
    donor_max: list[float],
    target_min: list[float],
    target_max: list[float],
) -> tuple[float, list[float]]:
    """Uniform scale that contains the donor in the target box, then center it.

    Uniform on purpose: a per-axis scale would shear every bone away from its
    donor proportions, which is exactly the thing this step is measuring.
    """
    donor_size = [donor_max[i] - donor_min[i] for i in range(3)]
    target_size = [target_max[i] - target_min[i] for i in range(3)]
    ratios = [
        target_size[i] / donor_size[i] for i in range(3) if donor_size[i] > 1e-9
    ]
    if not ratios:
        raise ConfigError("Donor skeleton is degenerate in every axis.")
    scale = min(ratios)
    donor_center = [(donor_min[i] + donor_max[i]) / 2 for i in range(3)]
    target_center = [(target_min[i] + target_max[i]) / 2 for i in range(3)]
    offset = [target_center[i] - donor_center[i] * scale for i in range(3)]
    return scale, offset


def _apply(
    point: tuple[float, float, float], scale: float, offset: list[float]
) -> tuple[float, float, float]:
    return (
        point[0] * scale + offset[0],
        point[1] * scale + offset[1],
        point[2] * scale + offset[2],
    )


def fit(
    project: Project,
    run_ref: str,
    donor_id: str,
    character_id: str | None = None,
) -> dict[str, Any]:
    """Write a rigidly fitted donor skeleton beside one generation run."""
    from . import generations as generations_mod

    backend, run = generations_mod._resolve_run(project, run_ref)
    request = generations_mod._json(
        generations_mod._relative_file(run, "request.json")
    )
    character_id = character_id or generations_mod._request_name(request)
    manifest = generations_mod.derive_manifest(run, character_id)

    donor, donor_path = _donor_skeleton(project, donor_id)
    target_min, target_max = _target_bounds(run, manifest.measurements)
    donor_min, donor_max = _skeleton_bounds(donor)
    scale, offset = _transform(donor_min, donor_max, target_min, target_max)

    armatures: list[FittedArmature] = []
    for source in donor.armatures:
        bones: list[FittedBone] = []
        points: list[tuple[float, float, float]] = []
        for bone in source.bones:
            head = _apply(bone.head, scale, offset)
            tail = _apply(bone.tail, scale, offset)
            points.extend((head, tail))
            bones.append(
                FittedBone(
                    name=bone.name,
                    parent=bone.parent,
                    deform=bone.deform,
                    connected=bone.connected,
                    depth=bone.depth,
                    head=head,
                    tail=tail,
                    length=bone.length * scale,
                    roll=bone.roll,
                )
            )
        armatures.append(
            FittedArmature(
                name=source.name,
                bones=bones,
                roots=source.roots,
                leaves=source.leaves,
                max_depth=source.max_depth,
                bounds_min=tuple(
                    min(point[axis] for point in points) for axis in range(3)
                ),
                bounds_max=tuple(
                    max(point[axis] for point in points) for axis in range(3)
                ),
                total_length=source.total_length * scale,
            )
        )

    fitted_min = [
        min(armature.bounds_min[axis] for armature in armatures) for axis in range(3)
    ]
    fitted_max = [
        max(armature.bounds_max[axis] for armature in armatures) for axis in range(3)
    ]
    target_size = [target_max[i] - target_min[i] for i in range(3)]
    fill = {
        AXES[i]: round((fitted_max[i] - fitted_min[i]) / target_size[i], 4)
        if target_size[i] > 1e-9
        else 0.0
        for i in range(3)
    }
    all_bones = [bone for armature in armatures for bone in armature.bones]

    document = FittedSkeletonDocument(
        target_id=f"{backend}/{run.name}",
        donor_id=donor_id,
        coordinate_system={
            "viewer_space": donor.coordinate_system.get("viewer_space"),
            "scale": "target model units; donor uniformly rescaled",
            "pose": "donor rest pose, unchanged",
        },
        derivation={
            "method": FIT_METHOD,
            "faithful": False,
            "donor_skeleton": donor_path.name,
            "donor_source_model": donor.source_model,
            "uniform_scale": scale,
            "translation": offset,
            "donor_bounds_min": donor_min,
            "donor_bounds_max": donor_max,
            "target_bounds_min": target_min,
            "target_bounds_max": target_max,
            "target_fill_ratio": fill,
            "limitations": [
                "Bone positions come from the donor, not from the target mesh.",
                "The donor rest pose is carried over unchanged.",
                "Bone rolls are inherited and are not recomputed for the target.",
            ],
        },
        armatures=armatures,
        summary={
            "armatures": len(armatures),
            "bones": len(all_bones),
            "deform_bones": sum(bone.deform for bone in all_bones),
            "roots": sum(len(armature.roots) for armature in armatures),
            "leaves": sum(len(armature.leaves) for armature in armatures),
            "max_depth": max(armature.max_depth for armature in armatures),
            "bounds_min": fitted_min,
            "bounds_max": fitted_max,
        },
    )

    stage = run / "skeleton"
    stage.mkdir(parents=True, exist_ok=True)
    skeleton_path = stage / "skeleton.json"
    temp = skeleton_path.with_suffix(".json.part")
    temp.write_text(
        document.model_dump_json(indent=2, by_alias=True) + "\n", encoding="utf-8"
    )
    temp.replace(skeleton_path)

    marker = stage / "manifest.json"
    marker_temp = marker.with_suffix(".json.part")
    marker_temp.write_text(
        json.dumps(
            {
                "schema": "charctx.skeleton-stage/v1",
                "target_id": f"{backend}/{run.name}",
                "character_id": character_id,
                "donor_id": donor_id,
                "method": FIT_METHOD,
                "skeleton": "skeleton/skeleton.json",
                "bones": len(all_bones),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    marker_temp.replace(marker)

    manifest_path = generations_mod.write_manifest(run, character_id)
    return {
        "target": f"{backend}/{run.name}",
        "character_id": character_id,
        "donor": donor_id,
        "method": FIT_METHOD,
        "skeleton": str(skeleton_path),
        "manifest": str(manifest_path),
        "bones": len(all_bones),
        "uniform_scale": scale,
        "target_fill_ratio": fill,
    }
