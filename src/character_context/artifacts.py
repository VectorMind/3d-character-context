"""External-tool provisioning.

Tools the pipeline needs but does not build - Blender - are declared in
`config/artifacts.yaml` with an exact version and checksum, and fetched into
the git-ignored `.tools/` directory. Nothing is installed implicitly: a fetch
is always an explicit act, and a version bump is a one-line config change.
"""

from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
import time
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import httpx

from .config import ConfigError, artifact_config
from .paths import DOWNLOADS_DIR, TOOLS_DIR

CHUNK = 1 << 20  # 1 MiB


@dataclass(frozen=True)
class ProvisionedTool:
    """A tool present in `.tools/` and the executable that proves it."""

    name: str
    version: str
    install_dir: Path
    executable: Path

    @property
    def installed(self) -> bool:
        return self.executable.is_file()


def resolve(name: str) -> ProvisionedTool:
    """Where a declared tool lives, whether or not it has been fetched."""
    entry = artifact_config(name)
    install_dir = TOOLS_DIR / entry["install_dir"]
    return ProvisionedTool(
        name=name,
        version=str(entry["version"]),
        install_dir=install_dir,
        executable=install_dir / entry["executable"],
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(CHUNK), b""):
            digest.update(block)
    return digest.hexdigest()


def _download(url: str, target: Path, on_progress: Callable[[int, int], None] | None):
    """Stream a download to a temp file, then rename it into place."""
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_name(target.name + ".part")
    with httpx.stream("GET", url, follow_redirects=True, timeout=60) as response:
        response.raise_for_status()
        total = int(response.headers.get("content-length", 0))
        done = 0
        with temp.open("wb") as handle:
            for chunk in response.iter_bytes(CHUNK):
                handle.write(chunk)
                done += len(chunk)
                if on_progress:
                    on_progress(done, total)
    temp.replace(target)


def _move_into_place(source: Path, destination: Path, attempts: int = 5) -> None:
    """Rename a freshly extracted directory to its final name.

    On Windows an on-access virus scanner still holds handles on hundreds of
    just-written executables, and the rename fails with `PermissionError`
    until it lets go, so the rename is retried before falling back to a copy.
    """
    for attempt in range(attempts):
        try:
            source.replace(destination)
            return
        except PermissionError:
            if attempt + 1 == attempts:
                break
            time.sleep(2 * (attempt + 1))
    shutil.copytree(source, destination)


def fetch(
    name: str,
    *,
    force: bool = False,
    on_progress: Callable[[int, int], None] | None = None,
) -> ProvisionedTool:
    """Provision a declared tool into `.tools/`.

    Already-provisioned tools are returned untouched unless `force` is set.
    The download is checksum-verified against the pin before extraction.
    """
    entry = artifact_config(name)
    tool = resolve(name)

    platform = entry.get("platform")
    if platform and platform != sys.platform:
        raise ConfigError(
            f"Artifact {name!r} is pinned to platform {platform!r}, "
            f"but this is {sys.platform!r}. Add a platform-specific entry to "
            "config/artifacts.yaml before fetching here."
        )

    if tool.installed and not force:
        return tool

    archive = DOWNLOADS_DIR / Path(entry["url"]).name
    expected = str(entry["sha256"]).lower()

    if not (archive.is_file() and _sha256(archive) == expected):
        _download(entry["url"], archive, on_progress)
        actual = _sha256(archive)
        if actual != expected:
            archive.unlink(missing_ok=True)
            raise ConfigError(
                f"Checksum mismatch for {name} {entry['version']}:\n"
                f"  expected {expected}\n  actual   {actual}\n"
                "The pin in config/artifacts.yaml and the published file "
                "disagree; the download was discarded."
            )

    if entry.get("archive", "zip") != "zip":
        raise ConfigError(
            f"Unsupported archive type {entry.get('archive')!r} for {name!r}."
        )

    if tool.install_dir.exists():
        shutil.rmtree(tool.install_dir)
    tool.install_dir.parent.mkdir(parents=True, exist_ok=True)

    staging = tool.install_dir.with_name(tool.install_dir.name + ".unpack")
    if staging.exists():
        shutil.rmtree(staging)
    with zipfile.ZipFile(archive) as zf:
        zf.extractall(staging)

    # Portable builds unpack into a single versioned directory; flatten it so
    # the executable path stays stable across version bumps.
    root = entry.get("archive_root")
    source = staging / root if root else staging
    if not source.is_dir():
        raise ConfigError(
            f"Archive for {name!r} did not contain expected directory {root!r}."
        )
    _move_into_place(source, tool.install_dir)
    shutil.rmtree(staging, ignore_errors=True)

    if not tool.installed:
        raise ConfigError(
            f"Provisioned {name!r} but no executable at {tool.executable}."
        )
    return tool


def verify(name: str) -> tuple[ProvisionedTool, str]:
    """Run the tool's declared version command, proving it actually runs."""
    entry = artifact_config(name)
    tool = resolve(name)
    if not tool.installed:
        raise ConfigError(
            f"{name!r} is not provisioned. Run `charctx fetch {name}` first."
        )
    args = [str(tool.executable), *entry.get("version_args", ["--version"])]
    completed = subprocess.run(  # noqa: S603 - argv from committed config only
        args, capture_output=True, text=True, timeout=120
    )
    output = (completed.stdout or completed.stderr).strip()
    if completed.returncode != 0:
        raise ConfigError(
            f"{name!r} failed its version check "
            f"(exit {completed.returncode}):\n{output}"
        )
    return tool, output
