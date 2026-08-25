"""Shared helpers for the free-access experiments (Phase 1, OP-011).

Zero external dependencies on purpose: every experiment script is a
self-contained PEP 723 script run with ``uv run --script``, and this module is
imported from the script directory, so it must work with the standard library
alone.
"""

from __future__ import annotations

import json
import os
import platform
import sys
import time
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Provider payloads carry emoji and non-latin text; the Windows console
# defaults to cp1252 and would crash on printing them.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")


def load_dotenv(path: Path | None = None) -> dict[str, str]:
    """Load ``KEY=VALUE`` pairs from the workspace ``.env`` into os.environ.

    Existing environment variables win, so a shell export can override the
    file. Values are never printed by this module.
    """
    env_path = path or (REPO_ROOT / ".env")
    loaded: dict[str, str] = {}
    if not env_path.is_file():
        return loaded
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        loaded[key] = value
        os.environ.setdefault(key, value)
    return loaded


def require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(
            f"Missing {name}. Put it in {REPO_ROOT / '.env'} as {name}=... "
            "or export it in the shell."
        )
    return value


def mask(secret: str) -> str:
    """Render a credential safe to write into a report."""
    if not secret:
        return "<empty>"
    if len(secret) <= 10:
        return f"<{len(secret)} chars>"
    return f"{secret[:4]}…{secret[-2:]} ({len(secret)} chars)"


def results_dir(slug: str, when: datetime | None = None) -> Path:
    """``.cache/results/<YYYY-MM-DD>/<HHMMSS>-<slug>/`` — date and time in path."""
    stamp = when or datetime.now()
    path = (
        REPO_ROOT
        / ".cache"
        / "results"
        / stamp.strftime("%Y-%m-%d")
        / f"{stamp.strftime('%H%M%S')}-{slug}"
    )
    path.mkdir(parents=True, exist_ok=True)
    return path


class Report:
    """Accumulates Markdown sections and a JSON summary for one experiment run."""

    def __init__(self, slug: str, title: str) -> None:
        self.slug = slug
        self.title = title
        self.started = datetime.now()
        self.started_perf = time.perf_counter()
        self.dir = results_dir(slug, self.started)
        self.lines: list[str] = []
        self.data: dict[str, object] = {
            "experiment": slug,
            "started": self.started.isoformat(timespec="seconds"),
        }
        self.probes: list[dict[str, object]] = []

    # --- markdown ------------------------------------------------------
    def h2(self, text: str) -> None:
        self.lines.append(f"\n## {text}\n")

    def h3(self, text: str) -> None:
        self.lines.append(f"\n### {text}\n")

    def p(self, text: str) -> None:
        self.lines.append(text + "\n")

    def bullet(self, text: str) -> None:
        self.lines.append(f"- {text}")

    def code(self, text: str, lang: str = "text") -> None:
        self.lines.append(f"\n```{lang}\n{text.rstrip()}\n```\n")

    def table(self, headers: list[str], rows: list[list[str]]) -> None:
        self.lines.append("| " + " | ".join(headers) + " |")
        self.lines.append("| " + " | ".join("---" for _ in headers) + " |")
        for row in rows:
            self.lines.append("| " + " | ".join(row) + " |")
        self.lines.append("")

    # --- probes --------------------------------------------------------
    def probe(self, name: str, **fields: object) -> None:
        """Record one access attempt (endpoint, status, latency, error…)."""
        entry = {"name": name, **fields}
        self.probes.append(entry)
        print(f"[probe] {json.dumps(entry, default=str)}", flush=True)

    def echo(self, text: str) -> None:
        print(text, flush=True)

    # --- output --------------------------------------------------------
    def write(self) -> Path:
        elapsed = time.perf_counter() - self.started_perf
        self.data["probes"] = self.probes
        self.data["elapsed_s"] = round(elapsed, 2)
        self.data["python"] = sys.version.split()[0]
        self.data["platform"] = platform.platform()

        header = [
            f"# {self.title}",
            "",
            f"- Run: `{self.started.strftime('%Y-%m-%d %H:%M:%S')}` local",
            f"- Script: `{Path(sys.argv[0]).name}`",
            f"- Python: {sys.version.split()[0]} on {platform.system()} "
            f"{platform.release()}",
            f"- Elapsed: {elapsed:.1f}s",
            f"- Results folder: `{self.dir.relative_to(REPO_ROOT)}`",
            "",
        ]
        md = self.dir / f"{self.slug}.md"
        md.write_text("\n".join(header + self.lines) + "\n", encoding="utf-8")
        (self.dir / f"{self.slug}.json").write_text(
            json.dumps(self.data, indent=2, default=str) + "\n", encoding="utf-8"
        )
        print(f"\nReport: {md}", flush=True)
        return md
