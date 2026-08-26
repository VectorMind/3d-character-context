"""Start the private local Astro asset catalog."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from .paths import REPO_ROOT, REPORTS_DIR

READY_PATTERN = re.compile(r"https?://(?:localhost|127\.0\.0\.1):(\d+)")


class WebAppError(RuntimeError):
    """The local viewer could not be started."""


@dataclass
class DevServer:
    process: subprocess.Popen[bytes]
    url: str
    log: Path

    def wait(self) -> int:
        try:
            return self.process.wait()
        except KeyboardInterrupt:
            self.stop()
            return 0

    def stop(self) -> None:
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()


def webapp_dir() -> Path:
    directory = REPO_ROOT / "webapp"
    if not (directory / "package.json").is_file():
        raise WebAppError(f"no web app at {directory}")
    return directory


def package_manager() -> tuple[str, ...]:
    pnpm = shutil.which("pnpm")
    if pnpm:
        return (pnpm,)
    corepack = shutil.which("corepack")
    if corepack:
        return (corepack, "pnpm")
    raise WebAppError("pnpm/corepack not found; install Node.js 22+")


def dependencies_installed(directory: Path) -> bool:
    return (directory / "node_modules" / "astro").exists()


def install(directory: Path, log: Path) -> None:
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as handle:
        handle.write("$ pnpm install\n")
        completed = subprocess.run(
            [*package_manager(), "install"],
            cwd=directory,
            stdout=handle,
            stderr=subprocess.STDOUT,
            check=False,
        )
    if completed.returncode:
        raise WebAppError(f"pnpm install failed; see {log}")


def start(
    directory: Path,
    *,
    project: Path,
    host: str = "127.0.0.1",
    port: int = 4321,
    timeout: float = 120.0,
) -> DevServer:
    log = REPORTS_DIR / "web.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    handle = log.open("w", encoding="utf-8")
    handle.write(f"$ pnpm dev --host {host} --port {port}\n")
    handle.flush()
    environment = os.environ.copy()
    environment["CHARCTX_PROJECT"] = str(project)
    process = subprocess.Popen(  # noqa: S603
        [*package_manager(), "dev", "--host", host, "--port", str(port)],
        cwd=directory,
        stdout=handle,
        stderr=subprocess.STDOUT,
        env=environment,
    )
    handle.close()
    try:
        url = _wait_until_ready(process, log, host, timeout)
    except Exception:
        process.terminate()
        raise
    return DevServer(process, url, log)


def _wait_until_ready(
    process: subprocess.Popen[bytes], log: Path, host: str, timeout: float
) -> str:
    deadline = time.monotonic() + timeout
    bound_port: int | None = None
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise WebAppError(
                f"dev server exited with code {process.returncode}; see {log}"
            )
        text = log.read_text(encoding="utf-8", errors="replace")
        match = READY_PATTERN.search(text)
        if match:
            bound_port = int(match.group(1))
        if bound_port is not None:
            url = f"http://{host}:{bound_port}/"
            try:
                with urllib.request.urlopen(url, timeout=2) as response:  # noqa: S310
                    if response.status < 500:
                        return url
            except (urllib.error.URLError, OSError):
                pass
        time.sleep(0.25)
    raise WebAppError(f"dev server did not answer within {timeout:.0f}s; see {log}")
