"""The contracts are the only types crossing module boundaries, so their
validation is what keeps bad data out of the pipeline."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from character_context.contracts import (
    GenerationRequest,
    MeshMeasurements,
    RawCharacterResult,
)


def test_request_resolves_existing_images(reference_image: Path) -> None:
    request = GenerationRequest(
        images=[reference_image], name="red-dragon", backend="trellis2", seed=7
    )
    assert request.images[0].is_absolute()
    assert request.seed == 7
    assert request.options == {}


def test_request_rejects_missing_image(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="not found"):
        GenerationRequest(
            images=[tmp_path / "nope.png"], name="dragon", backend="trellis2"
        )


def test_request_rejects_unusable_name(reference_image: Path) -> None:
    for bad in ("Red Dragon", "dragon/", "", "UPPER"):
        with pytest.raises(ValidationError):
            GenerationRequest(images=[reference_image], name=bad, backend="trellis2")


def test_request_needs_at_least_one_image() -> None:
    with pytest.raises(ValidationError):
        GenerationRequest(images=[], name="dragon", backend="trellis2")


def test_request_rejects_unknown_fields(reference_image: Path) -> None:
    # Backend knobs belong in `options`, not as new top-level fields.
    with pytest.raises(ValidationError):
        GenerationRequest(
            images=[reference_image],
            name="dragon",
            backend="trellis2",
            texture_size=1024,
        )


def _result(mesh: Path, request: GenerationRequest) -> RawCharacterResult:
    now = datetime.now()
    return RawCharacterResult(
        request=request,
        backend="trellis2",
        provider="huggingface-space",
        endpoint="microsoft/TRELLIS.2",
        mesh=mesh,
        run_dir=mesh.parent,
        started_at=now,
        completed_at=now,
        duration_s=1.5,
    )


def test_raw_result_accepts_a_mesh(glb_file: Path, reference_image: Path) -> None:
    request = GenerationRequest(
        images=[reference_image], name="dragon", backend="trellis2"
    )
    result = _result(glb_file, request)
    assert result.mesh.suffix == ".glb"
    assert result.extra_artifacts == []


def test_raw_result_rejects_a_non_mesh(tmp_path: Path, reference_image: Path) -> None:
    request = GenerationRequest(
        images=[reference_image], name="dragon", backend="trellis2"
    )
    with pytest.raises(ValidationError, match="Unexpected mesh suffix"):
        _result(tmp_path / "result.txt", request)


def test_measurements_plausibility_gate(tmp_path: Path) -> None:
    base = {
        "source": tmp_path / "m.glb",
        "file_size_bytes": 10,
        "file_format": "glb",
        "geometries": 1,
        "bounds_min": (0.0, 0.0, 0.0),
        "bounds_max": (1.0, 1.0, 1.0),
        "extents": (1.0, 1.0, 1.0),
        "centroid": (0.5, 0.5, 0.5),
        "watertight": True,
        "connected_components": 1,
        "degenerate_faces": 0,
        "textured": False,
        "sampled_points": 128,
        "measured_at": datetime.now(),
    }
    good = MeshMeasurements(
        **base, vertices=10, faces=8, surface_area=6.0, all_finite=True
    )
    assert good.is_plausible

    empty = MeshMeasurements(
        **base, vertices=0, faces=0, surface_area=0.0, all_finite=True
    )
    assert not empty.is_plausible

    broken = MeshMeasurements(
        **base, vertices=10, faces=8, surface_area=6.0, all_finite=False
    )
    assert not broken.is_plausible
