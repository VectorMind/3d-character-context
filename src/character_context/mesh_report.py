"""Mesh measurement.

Claims about geometry are backed by numbers, never by a screenshot. This
module loads any mesh artifact the pipeline touches - a hosted generator's
GLB, a local OBJ fixture, a canonical asset - and reports the same metrics for
all of them.

The Python API here is side-effect-free: `measure()` returns a model and
writes nothing. Writing `*.measurements.json` is an explicit act
(`write_measurements`, or the `charctx report` command).
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import numpy as np
import trimesh

from .contracts import MeshMeasurements

#: Surface samples taken to confirm the mesh can actually be sampled.
SAMPLE_POINTS = 2048


class MeshReportError(RuntimeError):
    """The artifact could not be loaded or holds no geometry."""


def _combined(path: Path) -> tuple[trimesh.Trimesh, int, bool]:
    """Load a mesh file into one concatenated mesh.

    Returns the combined mesh, how many geometries the source held, and
    whether any of them carried material/texture information.
    """
    try:
        loaded = trimesh.load(str(path), force="scene")
    except Exception as exc:  # provider files are untrusted input
        raise MeshReportError(f"Could not load {path}: {exc}") from exc

    if isinstance(loaded, trimesh.Trimesh):
        meshes = [loaded]
        geometries = 1
    else:
        meshes = [g for g in loaded.geometry.values() if isinstance(g, trimesh.Trimesh)]
        geometries = len(loaded.geometry)

    if not meshes:
        raise MeshReportError(f"No triangle geometry found in {path}")

    textured = any(
        getattr(getattr(mesh, "visual", None), "material", None) is not None
        for mesh in meshes
    )
    combined = meshes[0] if len(meshes) == 1 else trimesh.util.concatenate(meshes)
    return combined, geometries, textured


def _components(mesh: trimesh.Trimesh) -> int:
    """Connected-component count.

    trimesh needs a graph engine for this; both `networkx` and `scipy` are
    mandatory dependencies precisely so this metric is always available.
    """
    if len(mesh.faces) == 0:
        return 0
    return len(mesh.split(only_watertight=False))


def _degenerate_faces(mesh: trimesh.Trimesh) -> int:
    """Faces with zero area - a repair signal, and a fitting hazard."""
    if len(mesh.faces) == 0:
        return 0
    return int(np.count_nonzero(~mesh.nondegenerate_faces()))


def measure(
    path: str | Path,
    *,
    backend: str | None = None,
    seed: int | None = None,
    request_name: str | None = None,
) -> MeshMeasurements:
    """Measure a mesh artifact. Reads the file; writes nothing."""
    path = Path(path).resolve()
    if not path.is_file():
        raise MeshReportError(f"No such mesh file: {path}")

    mesh, geometries, textured = _combined(path)
    bounds = mesh.bounds
    watertight = bool(mesh.is_watertight)

    try:
        sampled = len(mesh.sample(SAMPLE_POINTS)) if len(mesh.faces) else 0
    except Exception:  # sampling failure is itself a finding, not a crash
        sampled = 0

    return MeshMeasurements(
        source=path,
        file_size_bytes=path.stat().st_size,
        file_format=path.suffix.lower().lstrip("."),
        geometries=geometries,
        vertices=int(len(mesh.vertices)),
        faces=int(len(mesh.faces)),
        bounds_min=tuple(float(v) for v in bounds[0]),
        bounds_max=tuple(float(v) for v in bounds[1]),
        extents=tuple(float(v) for v in mesh.extents),
        centroid=tuple(float(v) for v in mesh.centroid),
        surface_area=float(mesh.area),
        volume=float(mesh.volume) if watertight else None,
        watertight=watertight,
        connected_components=_components(mesh),
        degenerate_faces=_degenerate_faces(mesh),
        all_finite=bool(np.isfinite(mesh.vertices).all()),
        textured=textured,
        sampled_points=sampled,
        measured_at=datetime.now(),
        backend=backend,
        seed=seed,
        request_name=request_name,
    )


def measurements_path(mesh_path: str | Path) -> Path:
    """Conventional sidecar location: `<mesh stem>.measurements.json`."""
    mesh_path = Path(mesh_path)
    return mesh_path.with_suffix("").with_suffix(".measurements.json")


def write_measurements(
    measurements: MeshMeasurements, destination: Path | None = None
) -> Path:
    """Write a `*.measurements.json` sidecar beside the mesh, atomically."""
    target = (
        Path(destination) if destination else measurements_path(measurements.source)
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = measurements.model_dump_json(indent=2) + "\n"
    # The project folder may be cloud-synced: write then rename, so a sync
    # client never observes a half-written file.
    temp = target.with_name(target.name + ".tmp")
    temp.write_text(payload, encoding="utf-8")
    temp.replace(target)
    return target


def load_measurements(path: str | Path) -> MeshMeasurements:
    """Read a `*.measurements.json` sidecar back into the contract."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return MeshMeasurements.model_validate(data)
