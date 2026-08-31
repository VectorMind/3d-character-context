"""Synthesize a skeleton onto a generated mesh from a donor hierarchy.

Two methods live behind one command, and keeping both is the point rather than
an accident of refactoring:

* `rigid` is the crudest fit that can exist -- one uniform scale and one
  translation containing the donor skeleton in the target's measured box. It
  is expected to look wrong, and the *way* it looks wrong (which axis is
  starved, how far the donor pose is from the target's stance) is a
  measurement that no landmark-driven fit can produce for you.
* `chain` takes every anchored joint from the target's landmarks and keeps
  only the donor's hierarchy and its per-chain proportions. See `chain_fit`.

Both write the same `charctx.fitted-skeleton/v1` document, so the viewer draws
either one, and each method's own output is archived under `skeleton/fits/`
so the newer fit can be compared against the older one instead of merely
replacing it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import chain_fit
from .asset_models import (
    FittedArmature,
    FittedBone,
    FittedSkeletonDocument,
    LandmarkDocument,
    SkeletonDocument,
)
from .config import ConfigError
from .project import Project

AXES = ("x", "y", "z")
RIGID_METHOD = "uniform-contain-bounds/v1"
CHAIN_METHOD = chain_fit.METHOD
METHODS = {"rigid": RIGID_METHOD, "chain": CHAIN_METHOD}
DEFAULT_METHOD = "chain"

# The step-1 name is still the rigid method's identifier; keeping the old
# constant means the tests and documents written before step 3 stay true.
FIT_METHOD = RIGID_METHOD


def _slug(method: str) -> str:
    return method.split("/")[0]


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


def _rigid(
    donor: SkeletonDocument, scale: float, offset: list[float]
) -> list[FittedArmature]:
    """Move the whole donor rig as one body."""
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
    return armatures


def _landmarks(run: Path) -> LandmarkDocument:
    path = run / "skeleton" / "landmarks.json"
    if not path.is_file():
        raise ConfigError(
            "The chain method needs proposed landmarks. Run "
            "`charctx skeleton landmarks <backend>/<run>` first."
        )
    return LandmarkDocument.model_validate_json(path.read_text(encoding="utf-8"))


def _containment(
    armatures: list[FittedArmature],
    target_min: list[float],
    target_max: list[float],
    anchored: set[str] | None = None,
) -> dict[str, Any]:
    """How much of the fitted rig lands inside the mesh it is meant to drive.

    Split by anchored versus carried when the caller knows the difference: a
    joint a landmark placed and a joint that merely inherited its parent's
    frame are different claims, and lumping them into one number would hide
    which half of the method is escaping the mesh.
    """
    tolerance = 1e-6

    def outside(point: tuple[float, float, float]) -> bool:
        return any(
            point[axis] < target_min[axis] - tolerance
            or point[axis] > target_max[axis] + tolerance
            for axis in range(3)
        )

    groups: dict[str, list[bool]] = {"anchored": [], "carried": []}
    for armature in armatures:
        for bone in armature.bones:
            key = (
                "anchored"
                if anchored is None or bone.name in anchored
                else "carried"
            )
            groups[key].extend(outside(point) for point in (bone.head, bone.tail))

    total = groups["anchored"] + groups["carried"]
    report: dict[str, Any] = {
        "joints": len(total),
        "outside_bounds": sum(total),
        "outside_fraction": round(sum(total) / len(total), 6) if total else 0.0,
    }
    if anchored is not None:
        report["anchored"] = {
            "joints": len(groups["anchored"]),
            "outside_bounds": sum(groups["anchored"]),
        }
        report["carried"] = {
            "joints": len(groups["carried"]),
            "outside_bounds": sum(groups["carried"]),
        }
    return report


def fit(
    project: Project,
    run_ref: str,
    donor_id: str,
    method: str = DEFAULT_METHOD,
    character_id: str | None = None,
) -> dict[str, Any]:
    """Write a fitted donor skeleton beside one generation run."""
    from . import generations as generations_mod

    if method not in METHODS:
        raise ConfigError(
            f"Unknown fit method {method!r}; choose one of "
            f"{', '.join(sorted(METHODS))}."
        )

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

    shared: dict[str, Any] = {
        "donor_skeleton": donor_path.name,
        "donor_source_model": donor.source_model,
        "donor_bounds_min": donor_min,
        "donor_bounds_max": donor_max,
        "target_bounds_min": target_min,
        "target_bounds_max": target_max,
    }

    if method == "chain":
        landmarks = _landmarks(run)
        base = chain_fit.Similarity(
            chain_fit.IDENTITY, scale, (offset[0], offset[1], offset[2])
        )
        armatures, derivation, anchored = chain_fit.place(donor, landmarks, base)
        derivation.update(shared)
        # The rigid transform is still recorded: it is the fallback any bone
        # outside every chain would have used, and the number step 1 was for.
        derivation["fallback"] = {
            "method": RIGID_METHOD,
            "uniform_scale": scale,
            "translation": offset,
        }
        pose_note = "target landmarks; the donor rest pose is not carried"
    else:
        anchored = None
        armatures = _rigid(donor, scale, offset)
        derivation = {
            "method": RIGID_METHOD,
            "faithful": False,
            "uniform_scale": scale,
            "translation": offset,
            **shared,
            "limitations": [
                "Bone positions come from the donor, not from the target mesh.",
                "The donor rest pose is carried over unchanged.",
                "Bone rolls are inherited and are not recomputed for the target.",
            ],
        }
        pose_note = "donor rest pose, unchanged"

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
    derivation["target_fill_ratio"] = fill
    derivation["containment"] = _containment(
        armatures, target_min, target_max, anchored
    )
    all_bones = [bone for armature in armatures for bone in armature.bones]

    document = FittedSkeletonDocument(
        target_id=f"{backend}/{run.name}",
        donor_id=donor_id,
        coordinate_system={
            "viewer_space": donor.coordinate_system.get("viewer_space"),
            "scale": "target model units; donor uniformly rescaled",
            "pose": pose_note,
        },
        derivation=derivation,
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
    payload = document.model_dump_json(indent=2, by_alias=True) + "\n"

    # Every method keeps its own file, so a newer fit can be looked at beside
    # the one it replaced instead of quietly erasing it.
    fits = stage / "fits"
    fits.mkdir(exist_ok=True)
    _write(fits / f"{_slug(METHODS[method])}.json", payload)
    skeleton_path = _write(stage / "skeleton.json", payload)

    available = sorted(path.stem for path in fits.glob("*.json"))
    _write(
        stage / "manifest.json",
        json.dumps(
            {
                "schema": "charctx.skeleton-stage/v1",
                "target_id": f"{backend}/{run.name}",
                "character_id": character_id,
                "donor_id": donor_id,
                "method": METHODS[method],
                "skeleton": "skeleton/skeleton.json",
                "fits": [f"skeleton/fits/{name}.json" for name in available],
                "bones": len(all_bones),
            },
            indent=2,
        )
        + "\n",
    )

    manifest_path = generations_mod.write_manifest(run, character_id)
    result: dict[str, Any] = {
        "target": f"{backend}/{run.name}",
        "character_id": character_id,
        "donor": donor_id,
        "method": METHODS[method],
        "skeleton": str(skeleton_path),
        "manifest": str(manifest_path),
        "bones": len(all_bones),
        "uniform_scale": scale,
        "target_fill_ratio": fill,
        "containment": derivation["containment"],
    }
    if method == "chain":
        result.update(
            {
                "anchored_bones": derivation["anchored_bones"],
                "carried_bones": derivation["carried_bones"],
                "chains": derivation["chains"],
                "chains_skipped": derivation["chains_skipped"],
                "symmetry": derivation["symmetry"],
                "landmark_residual": derivation["landmark_residual"],
            }
        )
    return result


def _write(path: Path, payload: str) -> Path:
    temp = path.with_suffix(path.suffix + ".part")
    temp.write_text(payload, encoding="utf-8")
    temp.replace(path)
    return path
