"""Mesh proof is measurement. These tests check the measurements themselves
against meshes whose properties are known by construction."""

from __future__ import annotations

import math
from pathlib import Path

import pytest
import trimesh

from character_context import mesh_report
from character_context.mesh_report import MeshReportError


def test_measures_a_known_sphere(glb_file: Path) -> None:
    measured = mesh_report.measure(glb_file)

    assert measured.vertices > 0
    assert measured.faces > 0
    assert measured.watertight
    assert measured.connected_components == 1
    assert measured.degenerate_faces == 0
    assert measured.all_finite
    assert measured.sampled_points == mesh_report.SAMPLE_POINTS
    assert measured.is_plausible

    # A radius-0.5 sphere: area 4*pi*r^2 = pi, and an icosphere inscribes it,
    # so the measured area approaches pi from below.
    assert 0.85 * math.pi < measured.surface_area <= math.pi
    for extent in measured.extents:
        assert extent == pytest.approx(1.0, abs=0.05)
    assert measured.volume is not None


def test_counts_disconnected_components(two_part_glb: Path) -> None:
    measured = mesh_report.measure(two_part_glb)
    assert measured.geometries == 2
    assert measured.connected_components == 2
    # glTF export welds each box's duplicated corner vertices: 8 per box.
    assert measured.vertices == 16


def test_volume_is_omitted_when_not_watertight(tmp_path: Path) -> None:
    box = trimesh.creation.box(extents=(1, 1, 1))
    open_box = trimesh.Trimesh(vertices=box.vertices, faces=box.faces[:-2])
    path = tmp_path / "open.ply"
    open_box.export(path)

    measured = mesh_report.measure(path)
    assert measured.watertight is False
    assert measured.volume is None
    assert measured.file_format == "ply"


def test_records_request_metadata(glb_file: Path) -> None:
    measured = mesh_report.measure(
        glb_file, backend="trellis2", seed=42, request_name="red-dragon"
    )
    assert measured.backend == "trellis2"
    assert measured.seed == 42
    assert measured.request_name == "red-dragon"


def test_measure_writes_nothing(glb_file: Path) -> None:
    before = {p.name for p in glb_file.parent.iterdir()}
    mesh_report.measure(glb_file)
    assert {p.name for p in glb_file.parent.iterdir()} == before


def test_sidecar_roundtrip(glb_file: Path) -> None:
    measured = mesh_report.measure(glb_file, backend="trellis2")
    written = mesh_report.write_measurements(measured)

    assert written.name == "sphere.measurements.json"
    assert written.parent == glb_file.parent
    assert not written.with_name(written.name + ".tmp").exists()

    reloaded = mesh_report.load_measurements(written)
    assert reloaded.vertices == measured.vertices
    assert reloaded.backend == "trellis2"
    assert reloaded.bounds_min == measured.bounds_min


def test_missing_file_is_a_clear_error(tmp_path: Path) -> None:
    with pytest.raises(MeshReportError, match="No such mesh file"):
        mesh_report.measure(tmp_path / "absent.glb")


def test_unloadable_file_is_a_clear_error(tmp_path: Path) -> None:
    broken = tmp_path / "broken.glb"
    broken.write_bytes(b"not a glb at all")
    with pytest.raises(MeshReportError):
        mesh_report.measure(broken)
