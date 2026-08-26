"""The one live test: a real reference image through the real Space.

Skipped by default. It costs ZeroGPU quota (~120 s of a small daily budget)
and writes a real append-only run into the selected project folder, so the
maintainer opts in explicitly:

    CHARCTX_LIVE=1 uv run pytest -m live

`CHARCTX_LIVE_IMAGE` selects the reference image; otherwise the first image in
the project's `inputs/references/` is used.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from character_context import mesh_report
from character_context import project as project_mod
from character_context.backends import trellis2
from character_context.contracts import GenerationRequest

IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp")

pytestmark = pytest.mark.live


def _reference_image(project: project_mod.Project) -> Path:
    configured = os.environ.get("CHARCTX_LIVE_IMAGE")
    if configured:
        return Path(configured)
    candidates = sorted(
        p
        for p in (project.inputs / "references").glob("*")
        if p.suffix.lower() in IMAGE_SUFFIXES
    )
    if not candidates:
        pytest.skip(
            f"No reference image in {project.inputs / 'references'}; "
            "set CHARCTX_LIVE_IMAGE to choose one."
        )
    return candidates[0]


def test_live_generation_produces_a_measurable_mesh() -> None:
    project = project_mod.select()
    if not project.scaffolded:
        pytest.skip(f"Project {project.root} is not scaffolded")

    image = _reference_image(project)
    request = GenerationRequest(
        images=[image],
        name="live-smoke",
        backend="trellis2",
        seed=42,
    )

    try:
        result = trellis2.generate(request, project)
    except trellis2.QuotaExhausted as exc:
        pytest.skip(f"Free ZeroGPU quota exhausted: {exc}")

    assert result.mesh.is_file()
    assert result.run_dir.name.startswith("live-smoke-")
    assert (result.run_dir / "request.json").is_file()

    measured = mesh_report.measure(
        result.mesh,
        backend=result.backend,
        seed=request.seed,
        request_name=request.name,
    )
    assert measured.is_plausible
    assert measured.vertices > 1000, "a real generation should not be near-empty"
    assert measured.faces > 1000
    assert max(measured.extents) > 0.1
    mesh_report.write_measurements(measured)
