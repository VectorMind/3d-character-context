from __future__ import annotations

from pathlib import Path

from character_context import web


def test_dependencies_installed_requires_astro(tmp_path: Path) -> None:
    assert not web.dependencies_installed(tmp_path)
    (tmp_path / "node_modules" / "astro").mkdir(parents=True)
    assert web.dependencies_installed(tmp_path)


def test_ready_pattern_accepts_local_astro_url() -> None:
    match = web.READY_PATTERN.search("Local http://127.0.0.1:4327/")
    assert match is not None
    assert match.group(1) == "4327"


def test_webapp_directory_is_packaged_in_repository() -> None:
    assert (web.webapp_dir() / "package.json").is_file()
