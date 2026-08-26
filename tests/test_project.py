"""The project folder is where every byte of data lives, so its selection and
its append-only run slots are load-bearing rules, not conveniences."""

from __future__ import annotations

from pathlib import Path

import pytest

from character_context import project as project_mod
from character_context.config import PROJECT_ENV_VAR, ConfigError
from character_context.paths import REPO_ROOT


def test_explicit_path_wins_over_environment(
    project_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(PROJECT_ENV_VAR, str(REPO_ROOT / "elsewhere"))
    assert project_mod.select(project_root).root == project_root


def test_environment_selects_the_project(
    project_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(PROJECT_ENV_VAR, str(project_root))
    selected = project_mod.select()
    assert selected.root == project_root
    assert selected.scaffolded


def test_missing_selection_names_the_fix(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(PROJECT_ENV_VAR, "")
    monkeypatch.setattr(project_mod, "load_dotenv", lambda *a, **k: {})
    with pytest.raises(ConfigError) as excinfo:
        project_mod.select()
    assert PROJECT_ENV_VAR in str(excinfo.value)
    assert "--project" in str(excinfo.value)


def test_init_scaffolds_the_conventional_layout(tmp_path: Path) -> None:
    project, created = project_mod.init(tmp_path / "fresh")
    assert {p.name for p in created} == set(project_mod.PROJECT_DIRS)
    assert project.scaffolded

    # Scaffolding again is a no-op, never a reset.
    _, created_again = project_mod.init(tmp_path / "fresh")
    assert created_again == []


def test_init_refuses_to_write_inside_the_repository() -> None:
    with pytest.raises(ConfigError, match="inside the code repository"):
        project_mod.init(REPO_ROOT / "data")


def test_run_slots_increment_and_never_reuse(project_root: Path) -> None:
    project = project_mod.Project(project_root)
    first = project.run_slot("trellis2", "red-dragon")
    second = project.run_slot("trellis2", "red-dragon")
    third = project.run_slot("trellis2", "blue-dragon")

    assert first.name == "red-dragon-001"
    assert second.name == "red-dragon-002"
    assert third.name == "blue-dragon-001"
    assert first != second
    assert first.parent == project.generated / "trellis2"


def test_run_slot_skips_numbers_already_taken(project_root: Path) -> None:
    project = project_mod.Project(project_root)
    (project.generated / "trellis2").mkdir(parents=True)
    (project.generated / "trellis2" / "dragon-007").mkdir()
    assert project.run_slot("trellis2", "dragon").name == "dragon-008"


def test_describe_is_side_effect_free(tmp_path: Path) -> None:
    missing = project_mod.Project(tmp_path / "absent")
    described = missing.describe()
    assert described["exists"] is False
    assert not (tmp_path / "absent").exists()
