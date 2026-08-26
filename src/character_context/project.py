"""The external project folder: selection, scaffolding, and run slots.

No input image, generated mesh, or canonical asset is ever written inside the
code repository. Everything lives in a project folder chosen by the user and
recorded in the git-ignored `.env` as `CHARCTX_PROJECT`.

Selection precedence: an explicit `--project` for one command, then
`CHARCTX_PROJECT` from the environment or `.env`.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .config import PROJECT_ENV_VAR, ConfigError, load_dotenv
from .paths import ENV_FILE, is_inside_repo

#: The conventional layout every project folder carries.
PROJECT_DIRS = ("inputs", "generated", "assets")


@dataclass(frozen=True)
class Project:
    """A selected project folder and the locations inside it."""

    root: Path

    @property
    def inputs(self) -> Path:
        return self.root / "inputs"

    @property
    def generated(self) -> Path:
        return self.root / "generated"

    @property
    def assets(self) -> Path:
        return self.root / "assets"

    @property
    def exists(self) -> bool:
        return self.root.is_dir()

    @property
    def scaffolded(self) -> bool:
        return self.exists and all((self.root / d).is_dir() for d in PROJECT_DIRS)

    def run_slot(self, backend: str, name: str) -> Path:
        """Reserve a fresh append-only folder for one generation run.

        Slots are `generated/<backend>/<name>-<NNN>` with an incrementing
        suffix. An existing slot is never reused or overwritten: hosted
        generation costs money and quota, and is non-deterministic, so every
        result keeps its own folder.
        """
        parent = self.generated / backend
        parent.mkdir(parents=True, exist_ok=True)
        existing = sorted(parent.glob(f"{name}-[0-9][0-9][0-9]"))
        next_index = 1
        if existing:
            suffixes = [int(p.name.rsplit("-", 1)[-1]) for p in existing]
            next_index = max(suffixes) + 1
        while True:
            slot = parent / f"{name}-{next_index:03d}"
            try:
                slot.mkdir(parents=False, exist_ok=False)
                return slot
            except FileExistsError:  # a concurrent run took this number
                next_index += 1

    def describe(self) -> dict[str, object]:
        """Side-effect-free summary of the project's current state."""
        counts: dict[str, int] = {}
        if self.exists:
            for directory in PROJECT_DIRS:
                path = self.root / directory
                counts[directory] = (
                    sum(1 for _ in path.rglob("*") if _.is_file())
                    if path.is_dir()
                    else 0
                )
        return {
            "root": str(self.root),
            "exists": self.exists,
            "scaffolded": self.scaffolded,
            "files": counts,
        }


def select(explicit: str | Path | None = None) -> Project:
    """Resolve the active project folder.

    Raises `ConfigError` with the exact fix when no project is selected.
    """
    if explicit:
        return Project(Path(explicit).expanduser().resolve())

    load_dotenv()
    configured = os.environ.get(PROJECT_ENV_VAR, "").strip().strip('"')
    if not configured:
        raise ConfigError(
            f"No project folder selected. Add "
            f'`{PROJECT_ENV_VAR}=<path>` to {ENV_FILE}, or pass --project <path>.'
        )
    return Project(Path(configured).expanduser().resolve())


def init(root: Path) -> tuple[Project, list[Path]]:
    """Scaffold the conventional layout, returning the directories created.

    Refuses to scaffold inside the code repository: the data/code split is a
    structural rule, not a convention.
    """
    root = Path(root).expanduser().resolve()
    if is_inside_repo(root):
        raise ConfigError(
            f"Refusing to scaffold a project inside the code repository ({root}). "
            "The project folder is external and uncommitted by design."
        )
    created: list[Path] = []
    for directory in PROJECT_DIRS:
        path = root / directory
        if not path.is_dir():
            path.mkdir(parents=True)
            created.append(path)
    return Project(root), created
