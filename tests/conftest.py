"""Shared fixtures.

The default suite is offline and free: no test calls a provider, and no test
writes outside `tmp_path`. The one live test is marked `live` and skipped
unless `CHARCTX_LIVE=1`.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
import trimesh

FIXTURES = Path(__file__).parent / "fixtures"


def pytest_collection_modifyitems(config, items) -> None:
    """Keep the default suite offline and free.

    Tests marked `live` call a real provider and burn GPU quota, so they run
    only when the maintainer asks for it with `CHARCTX_LIVE=1`.
    """
    if os.environ.get("CHARCTX_LIVE") == "1":
        return
    skip_live = pytest.mark.skip(reason="live provider test; set CHARCTX_LIVE=1 to run")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip_live)


@pytest.fixture
def glb_file(tmp_path: Path) -> Path:
    """A small, watertight GLB built locally - no data committed to the repo."""
    mesh = trimesh.creation.icosphere(subdivisions=2, radius=0.5)
    path = tmp_path / "sphere.glb"
    mesh.export(path)
    return path


@pytest.fixture
def two_part_glb(tmp_path: Path) -> Path:
    """A GLB holding two disconnected meshes, for component counting."""
    left = trimesh.creation.box(extents=(1, 1, 1))
    right = trimesh.creation.box(extents=(1, 1, 1))
    right.apply_translation((5, 0, 0))
    scene = trimesh.Scene({"left": left, "right": right})
    path = tmp_path / "pair.glb"
    scene.export(path)
    return path


@pytest.fixture
def reference_image(tmp_path: Path) -> Path:
    """A minimal valid PNG standing in for a reference image."""
    png = bytes.fromhex(
        "89504e470d0a1a0a0000000d494844520000000100000001080600000"
        "01f15c4890000000a49444154789c6300010000050001"
        "0d0a2db40000000049454e44ae426082"
    )
    path = tmp_path / "reference.png"
    path.write_bytes(png)
    return path


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    """An external project folder scaffolded outside the repository."""
    root = tmp_path / "project"
    for directory in ("inputs", "generated", "assets"):
        (root / directory).mkdir(parents=True)
    return root


@pytest.fixture
def trellis2_api() -> dict:
    """The TRELLIS.2 Space API surface, recorded from the live Space."""
    data = json.loads((FIXTURES / "trellis2_view_api.json").read_text(encoding="utf-8"))
    return data["named_endpoints"]
