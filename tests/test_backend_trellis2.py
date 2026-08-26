"""The TRELLIS.2 backend, exercised offline against the Space's recorded API
description. No network call, no GPU quota, no cost."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import trimesh

from character_context.backends import trellis2
from character_context.contracts import GenerationRequest
from character_context.project import Project


class FakeSpace:
    """Stands in for `gradio_client.Client` against `microsoft/TRELLIS.2`.

    It answers `view_api` from the recorded fixture and records every call, so
    tests can assert on exactly what the backend sends.
    """

    def __init__(self, api: dict, glb: Path, fail_with: Exception | None = None):
        self._api = api
        self._glb = glb
        self._fail_with = fail_with
        self.calls: list[tuple[str, dict]] = []

    def view_api(self, return_format: str = "dict", print_info: bool = False) -> dict:
        return {"named_endpoints": self._api}

    def predict(self, *, api_name: str, **kwargs):
        self.calls.append((api_name, kwargs))
        if self._fail_with is not None and api_name == "/image_to_3d":
            raise self._fail_with
        if api_name == "/preprocess_image":
            return str(kwargs["input"]["path"])
        if api_name == "/image_to_3d":
            return "preview.mp4"
        if api_name == "/extract_glb":
            return (str(self._glb), str(self._glb))
        return ()

    def called(self, api_name: str) -> dict:
        for name, kwargs in self.calls:
            if name == api_name:
                return kwargs
        raise AssertionError(f"{api_name} was never called; saw {self.order()}")

    def order(self) -> list[str]:
        return [name for name, _ in self.calls]


@pytest.fixture
def provider_glb(tmp_path: Path) -> Path:
    """A GLB standing in for what the Space hands back."""
    path = tmp_path / "provider" / "sample.glb"
    path.parent.mkdir(parents=True)
    trimesh.creation.icosphere(subdivisions=1, radius=0.5).export(path)
    return path


@pytest.fixture
def wired(
    monkeypatch: pytest.MonkeyPatch,
    trellis2_api: dict,
    provider_glb: Path,
    reference_image: Path,
    project_root: Path,
):
    """Backend wired to a fake Space, with a real request and project."""
    space = FakeSpace(trellis2_api, provider_glb)
    monkeypatch.setattr(trellis2, "_client", lambda *a, **k: space)
    monkeypatch.setattr(trellis2, "credential", lambda name, **k: "hf_test_token")

    request = GenerationRequest(
        images=[reference_image], name="red-dragon", backend="trellis2", seed=7
    )
    return space, request, Project(project_root)


def test_generation_lands_in_a_fresh_run_slot(wired) -> None:
    space, request, project = wired
    result = trellis2.generate(request, project)

    assert result.run_dir == project.generated / "trellis2" / "red-dragon-001"
    assert result.mesh.name == "red-dragon.glb"
    assert result.mesh.is_file()
    assert result.backend == "trellis2"
    assert result.endpoint == "microsoft/TRELLIS.2"
    assert result.provider == "huggingface-space"
    assert result.duration_s >= 0
    # No temp files survive the atomic writes.
    assert not [p for p in result.run_dir.iterdir() if p.suffix == ".part"]


def test_repeating_a_run_never_overwrites(wired) -> None:
    space, request, project = wired
    first = trellis2.generate(request, project)
    second = trellis2.generate(request, project)

    assert first.run_dir != second.run_dir
    assert second.run_dir.name == "red-dragon-002"
    assert first.mesh.is_file() and second.mesh.is_file()


def test_session_is_started_before_generating(wired) -> None:
    space, request, project = wired
    trellis2.generate(request, project)

    order = space.order()
    assert order.index("/start_session") < order.index("/image_to_3d")
    # /extract_glb reads what /image_to_3d left in the session.
    assert order.index("/image_to_3d") < order.index("/extract_glb")


def test_every_declared_parameter_is_sent(wired, trellis2_api: dict) -> None:
    """This Space rejects a partial parameter list with an opaque error."""
    space, request, project = wired
    trellis2.generate(request, project)

    declared = {
        p.get("parameter_name") or p.get("label")
        for p in trellis2_api["/image_to_3d"]["parameters"]
    }
    assert set(space.called("/image_to_3d")) == declared


def test_request_and_config_options_reach_the_call(wired) -> None:
    space, request, project = wired
    request = request.model_copy(update={"options": {"ss_sampling_steps": 4}})
    trellis2.generate(request, project)

    sent = space.called("/image_to_3d")
    assert sent["seed"] == 7  # from the request
    assert sent["resolution"] == "1024"  # from config/providers.yaml
    assert sent["ss_sampling_steps"] == 4  # request overrides config


def test_run_metadata_is_written_beside_the_mesh(wired) -> None:
    space, request, project = wired
    result = trellis2.generate(request, project)

    metadata = json.loads((result.run_dir / "request.json").read_text(encoding="utf-8"))
    assert metadata["backend"] == "trellis2"
    assert metadata["space"] == "microsoft/TRELLIS.2"
    assert metadata["request"]["seed"] == 7
    assert metadata["request"]["name"] == "red-dragon"
    assert metadata["resolved_options"]["resolution"] == "1024"
    assert "started_at" in metadata and "completed_at" in metadata
    assert "red-dragon.glb" in metadata["artifacts"]


def test_reference_image_travels_with_the_result(wired) -> None:
    space, request, project = wired
    result = trellis2.generate(request, project)

    copied = result.run_dir / "reference.png"
    assert copied.is_file()
    assert copied.read_bytes() == request.images[0].read_bytes()
    assert copied in result.extra_artifacts


def test_quota_exhaustion_is_a_named_error(
    monkeypatch: pytest.MonkeyPatch,
    trellis2_api: dict,
    provider_glb: Path,
    reference_image: Path,
    project_root: Path,
) -> None:
    message = (
        "You have exceeded your free ZeroGPU quota (120s requested vs. 12s left). "
        "Try again in 23:51:16."
    )
    space = FakeSpace(trellis2_api, provider_glb, fail_with=RuntimeError(message))
    monkeypatch.setattr(trellis2, "_client", lambda *a, **k: space)
    monkeypatch.setattr(trellis2, "credential", lambda name, **k: "hf_test_token")

    request = GenerationRequest(
        images=[reference_image], name="red-dragon", backend="trellis2"
    )
    with pytest.raises(trellis2.QuotaExhausted, match="Try again in"):
        trellis2.generate(request, Project(project_root))


def test_a_changed_space_api_is_reported_clearly(
    monkeypatch: pytest.MonkeyPatch,
    trellis2_api: dict,
    provider_glb: Path,
    reference_image: Path,
    project_root: Path,
) -> None:
    """Spaces change their API without notice; the failure must say so."""
    reduced = {k: v for k, v in trellis2_api.items() if k != "/extract_glb"}
    space = FakeSpace(reduced, provider_glb)
    monkeypatch.setattr(trellis2, "_client", lambda *a, **k: space)
    monkeypatch.setattr(trellis2, "credential", lambda name, **k: "hf_test_token")

    request = GenerationRequest(
        images=[reference_image], name="red-dragon", backend="trellis2"
    )
    with pytest.raises(trellis2.BackendError, match="/extract_glb"):
        trellis2.generate(request, Project(project_root))


def test_no_provider_native_payload_escapes(wired) -> None:
    """The Gradio payload must not leak past the backend boundary."""
    space, request, project = wired
    result = trellis2.generate(request, project)

    dumped = result.model_dump_json()
    assert "preview.mp4" not in dumped
    assert "named_endpoints" not in dumped
    assert str(space._glb) not in dumped


def test_describe_makes_no_network_call() -> None:
    described = trellis2.describe()
    assert described["space"] == "microsoft/TRELLIS.2"
    assert described["call_shape"] == "session-stateful"
    assert described["credential"] == "HF_TOKEN"
