"""Workspace locations.

Every path the repository writes to is resolved here, so the data/code split
is enforced in one place rather than repeated at each call site.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

# src/character_context/paths.py -> repository root
REPO_ROOT = Path(__file__).resolve().parents[2]

CONFIG_DIR = REPO_ROOT / "config"
ARTIFACTS_CONFIG = CONFIG_DIR / "artifacts.yaml"
PROVIDERS_CONFIG = CONFIG_DIR / "providers.yaml"

ENV_FILE = REPO_ROOT / ".env"

#: Provisioned external binaries (Blender). Git-ignored.
TOOLS_DIR = REPO_ROOT / ".tools"

#: Operational output only. Git-ignored. Never data.
CACHE_DIR = REPO_ROOT / ".cache"
RESULTS_DIR = CACHE_DIR / "results"
REPORTS_DIR = CACHE_DIR / "reports"
SCRATCH_DIR = CACHE_DIR / "scratch"
DOWNLOADS_DIR = CACHE_DIR / "downloads"

CACHE_LAYOUT = {
    "results": RESULTS_DIR,
    "reports": REPORTS_DIR,
    "scratch": SCRATCH_DIR,
    "downloads": DOWNLOADS_DIR,
}


def ensure_cache_layout() -> None:
    """Create the operational cache directories if they do not exist."""
    for path in CACHE_LAYOUT.values():
        path.mkdir(parents=True, exist_ok=True)


def result_dir(slug: str, when: datetime | None = None) -> Path:
    """A fresh, timestamped folder under `.cache/results/`.

    Date and time are in the path, so runs accumulate instead of overwriting
    each other.
    """
    stamp = when or datetime.now()
    path = (
        RESULTS_DIR / stamp.strftime("%Y-%m-%d") / f"{stamp.strftime('%H%M%S')}-{slug}"
    )
    path.mkdir(parents=True, exist_ok=True)
    return path


def is_inside_repo(path: Path) -> bool:
    """True when `path` would write into the code repository."""
    try:
        path.resolve().relative_to(REPO_ROOT)
    except ValueError:
        return False
    return True
