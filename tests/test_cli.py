"""The CLI is the single documented interface, so its contract - exit codes,
JSON shape, and error messages - is tested like any other contract."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from character_context.cli import main
from character_context.config import PROJECT_ENV_VAR


def run(capsys, *argv: str) -> tuple[int, str]:
    code = main(list(argv))
    return code, capsys.readouterr().out


def run_json(capsys, *argv: str) -> tuple[int, dict]:
    code, out = run(capsys, *argv)
    return code, json.loads(out)


def test_paths_lists_every_write_location(capsys) -> None:
    code, payload = run_json(capsys, "paths", "--json")
    assert code == 0
    assert set(payload["cache"]) == {"results", "reports", "scratch", "downloads"}
    assert payload["repository"].endswith("3d-character-context")


def test_info_reports_backends_without_revealing_secrets(
    capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HF_TOKEN", "hf_supersecrettokenvalue0000")
    code, payload = run_json(capsys, "info", "--json")
    assert code == 0

    trellis = next(b for b in payload["backends"] if b["backend"] == "trellis2")
    assert trellis["credentialed"] is True
    assert trellis["default"] is True
    assert "hf_supersecrettokenvalue0000" not in json.dumps(payload)


def test_backends_separates_implemented_from_documented(capsys) -> None:
    code, payload = run_json(capsys, "backends", "--json")
    assert code == 0
    assert [b["backend"] for b in payload["implemented"]] == ["trellis2"]
    names = {a["name"] for a in payload["alternatives"]}
    assert {"hunyuan3d", "commercial"} <= names


def test_report_measures_and_writes_a_sidecar(capsys, glb_file: Path) -> None:
    code, payload = run_json(capsys, "report", str(glb_file), "--json")
    assert code == 0
    assert payload["vertices"] > 0
    assert payload["watertight"] is True
    written = Path(payload["measurements_file"])
    assert written.is_file()
    assert json.loads(written.read_text(encoding="utf-8"))["faces"] == payload["faces"]


def test_report_can_measure_without_writing(capsys, glb_file: Path) -> None:
    code, payload = run_json(capsys, "report", str(glb_file), "--no-write", "--json")
    assert code == 0
    assert "measurements_file" not in payload
    assert not list(glb_file.parent.glob("*.measurements.json"))


def test_report_human_output_is_readable(capsys, glb_file: Path) -> None:
    code, out = run(capsys, "report", str(glb_file))
    assert code == 0
    for label in ("vertices", "faces", "watertight", "components", "plausible"):
        assert label in out


def test_report_on_a_missing_file_fails_clearly(capsys, tmp_path: Path) -> None:
    code = main(["report", str(tmp_path / "absent.glb")])
    assert code == 1
    assert "No such mesh file" in capsys.readouterr().err


def test_project_init_scaffolds_and_info_reports(
    capsys, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "workspace"
    code, payload = run_json(capsys, "project", "init", str(root), "--json")
    assert code == 0
    assert sorted(Path(p).name for p in payload["created"]) == [
        "assets",
        "generated",
        "inputs",
    ]

    monkeypatch.setenv(PROJECT_ENV_VAR, str(root))
    code, payload = run_json(capsys, "project", "info", "--json")
    assert code == 0
    assert payload["scaffolded"] is True


def test_project_init_refuses_the_repository(capsys) -> None:
    code = main(["project", "init", "."])
    assert code == 2  # configuration error, not a crash
    assert "inside the code repository" in capsys.readouterr().err


def test_unknown_backend_is_a_configuration_error(
    capsys, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(PROJECT_ENV_VAR, str(tmp_path))
    code = main(["generate", "image.png", "--name", "d", "--backend", "meshy"])
    assert code == 2
    assert "meshy" in capsys.readouterr().err


def test_generate_requires_a_project(
    capsys, monkeypatch: pytest.MonkeyPatch, reference_image: Path
) -> None:
    monkeypatch.setenv(PROJECT_ENV_VAR, "")
    monkeypatch.setattr("character_context.project.load_dotenv", lambda *a, **k: {})
    code = main(["generate", str(reference_image), "--name", "dragon"])
    assert code == 2
    assert PROJECT_ENV_VAR in capsys.readouterr().err


def test_option_flag_parses_typed_values(capsys) -> None:
    from character_context.cli import _parse_options

    parsed = _parse_options(["steps=12", "scale=1.5", "fast=true", "mode=stochastic"])
    assert parsed == {
        "steps": 12,
        "scale": 1.5,
        "fast": True,
        "mode": "stochastic",
    }


def test_option_flag_rejects_malformed_input() -> None:
    from character_context.cli import ConfigError, _parse_options

    with pytest.raises(ConfigError, match="key=value"):
        _parse_options(["steps"])
