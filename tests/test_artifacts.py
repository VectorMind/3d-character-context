"""External tools are pinned and checksum-verified. These tests exercise the
fetch mechanism against a locally built archive - no download."""

from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

import pytest

from character_context import artifacts
from character_context.config import ConfigError


@pytest.fixture
def fake_tool(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    """A declared artifact whose archive is built locally, not downloaded."""
    payload = tmp_path / "build" / "faketool-1.2.3-windows-x64"
    payload.mkdir(parents=True)
    (payload / "faketool.exe").write_text("#!/bin/sh\necho faketool 1.2.3\n")
    (payload / "readme.txt").write_text("bundled file")

    archive = tmp_path / "faketool-1.2.3-windows-x64.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        for item in payload.rglob("*"):
            zf.write(item, item.relative_to(payload.parent))

    entry = {
        "version": "1.2.3",
        "url": f"https://example.invalid/{archive.name}",
        "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "archive": "zip",
        "archive_root": payload.name,
        "install_dir": "faketool",
        "executable": "faketool.exe",
        "version_args": ["--version"],
    }

    monkeypatch.setattr(artifacts, "TOOLS_DIR", tmp_path / "tools")
    monkeypatch.setattr(artifacts, "DOWNLOADS_DIR", tmp_path / "downloads")
    monkeypatch.setattr(
        artifacts, "artifact_config", lambda name: entry if name == "faketool" else {}
    )

    def fake_download(url, target, on_progress):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(archive.read_bytes())
        if on_progress:
            on_progress(target.stat().st_size, target.stat().st_size)

    monkeypatch.setattr(artifacts, "_download", fake_download)
    return {"entry": entry, "archive": archive, "tmp_path": tmp_path}


def test_fetch_flattens_the_archive_root(fake_tool: dict) -> None:
    tool = artifacts.fetch("faketool")

    assert tool.installed
    assert tool.executable.name == "faketool.exe"
    # The versioned directory inside the zip must not survive: the executable
    # path has to stay stable across version bumps.
    assert tool.executable.parent.name == "faketool"
    assert (tool.install_dir / "readme.txt").is_file()
    assert not tool.install_dir.with_name("faketool.unpack").exists()


def test_fetch_is_idempotent(fake_tool: dict) -> None:
    first = artifacts.fetch("faketool")
    marker = first.install_dir / "marker.txt"
    marker.write_text("still here")

    second = artifacts.fetch("faketool")
    assert second.install_dir == first.install_dir
    assert marker.is_file(), "an already-provisioned tool must not be re-extracted"


def test_force_reprovisions(fake_tool: dict) -> None:
    first = artifacts.fetch("faketool")
    stale = first.install_dir / "stale.txt"
    stale.write_text("left over from an old version")

    artifacts.fetch("faketool", force=True)
    assert not stale.exists()


def test_checksum_mismatch_discards_the_download(
    fake_tool: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    entry = dict(fake_tool["entry"])
    entry["sha256"] = "0" * 64
    monkeypatch.setattr(artifacts, "artifact_config", lambda name: entry)

    with pytest.raises(ConfigError, match="Checksum mismatch"):
        artifacts.fetch("faketool")

    downloaded = fake_tool["tmp_path"] / "downloads" / fake_tool["archive"].name
    assert not downloaded.exists(), "a mismatched download must not be kept"


def test_verify_refuses_when_not_provisioned(fake_tool: dict) -> None:
    with pytest.raises(ConfigError, match="charctx fetch faketool"):
        artifacts.verify("faketool")


def test_resolve_reports_declared_location_before_fetching(fake_tool: dict) -> None:
    tool = artifacts.resolve("faketool")
    assert tool.version == "1.2.3"
    assert not tool.installed


def test_blender_is_declared_for_this_platform() -> None:
    tool = artifacts.resolve("blender")
    assert tool.version == "5.2.1"
    assert tool.executable.name == "blender.exe"
    assert ".tools" in str(tool.install_dir)
