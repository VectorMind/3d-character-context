"""Spend the day's ZeroGPU budget deliberately, through the real CLI.

This is the script to run when you want live proof: it drives
`charctx generate` against `microsoft/TRELLIS.2`, lands results in the
selected project folder (never a temp directory), and verifies each run slot
afterwards.

It is quota-aware. When the Space refuses a call, it reads the provider's own
`Try again in H:MM:SS` and waits exactly that long rather than guessing or
hammering. A refused call costs nothing, so retrying is free.

Unlike the other probes here, this one runs in the **project environment**
rather than as a standalone PEP 723 script: it drives the installed `charctx`
CLI, so it needs the project installed anyway, and it has no dependencies of
its own to isolate.

Usage:

    uv run python experiments/hf_03_live_validation.py
    uv run python experiments/hf_03_live_validation.py --runs 3
    uv run python experiments/hf_03_live_validation.py --name blue-dragon --seed 7
    uv run python experiments/hf_03_live_validation.py --no-wait

Writes `.cache/results/<date>/<time>-live-validation/`; the meshes themselves
go to `<project>/generated/trellis2/<name>-<NNN>/`.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import REPO_ROOT, Report, load_dotenv, require_env  # noqa: E402

# The provider states its own reset time; never guess one.
RETRY_PATTERN = re.compile(r"Try again in (\d+):(\d{2}):(\d{2})")
RETRY_MARGIN_S = 45
MAX_WAIT_S = 6 * 3600


def run_cli(*args: str) -> tuple[int, str, str]:
    """Invoke the real `charctx` CLI, exactly as a user would."""
    completed = subprocess.run(
        ["uv", "run", "charctx", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return completed.returncode, completed.stdout or "", completed.stderr or ""


def quota_wait_seconds(message: str) -> int | None:
    """Seconds until the provider says the budget frees up, if it said so."""
    match = RETRY_PATTERN.search(message)
    if not match:
        return None
    hours, minutes, seconds = (int(g) for g in match.groups())
    return hours * 3600 + minutes * 60 + seconds + RETRY_MARGIN_S


def generate_once(
    name: str, seed: int, image: str, rep: Report, wait: bool
) -> dict | None:
    """One generation, waiting out a quota refusal if the provider names one."""
    total_waited = 0
    attempt = 0
    while True:
        attempt += 1
        started = time.perf_counter()
        code, out, err = run_cli(
            "generate", image, "--name", name, "--seed", str(seed), "--json"
        )
        elapsed = round(time.perf_counter() - started, 1)

        if code == 0:
            payload = json.loads(out)
            rep.probe(
                "generate",
                run=name,
                seed=seed,
                ok=True,
                attempt=attempt,
                waited_s=total_waited,
                duration_s=payload.get("duration_s"),
            )
            return payload

        combined = out + err
        delay = quota_wait_seconds(combined)
        if delay is None or not wait:
            rep.probe(
                "generate", run=name, seed=seed, ok=False, attempt=attempt,
                exit_code=code, error=combined.strip()[:300],
            )
            rep.p(f"**Run `{name}` failed** (exit {code}) after {elapsed}s:")
            rep.code(combined.strip()[:800])
            return None

        if total_waited + delay > MAX_WAIT_S:
            rep.probe(
                "generate", run=name, seed=seed, ok=False, attempt=attempt,
                gave_up_after_s=total_waited,
            )
            rep.p(
                f"**Gave up on `{name}`**: the provider asks for another "
                f"{delay // 60} min, past this run's {MAX_WAIT_S // 3600}h budget."
            )
            return None

        resumes = datetime.now() + timedelta(seconds=delay)
        rep.probe(
            "quota_wait", run=name, attempt=attempt, wait_s=delay,
            resumes_at=resumes.strftime("%H:%M:%S"),
        )
        rep.echo(
            f"[wait] quota refused {name}; sleeping {delay // 60}m{delay % 60:02d}s "
            f"until ~{resumes.strftime('%H:%M:%S')}"
        )
        time.sleep(delay)
        total_waited += delay


def verify_slot(payload: dict, rep: Report) -> dict:
    """Check the run slot really holds a self-contained, measured result."""
    run_dir = Path(payload["run_dir"])
    mesh = Path(payload["mesh"])
    measurements = payload.get("measurements") or {}

    files = sorted(p.name for p in run_dir.iterdir()) if run_dir.is_dir() else []
    checks = {
        "run_dir_in_project": "generated" in run_dir.parts,
        "run_dir_outside_repo": not str(run_dir).startswith(str(REPO_ROOT)),
        "mesh_exists": mesh.is_file(),
        "mesh_non_trivial": mesh.is_file() and mesh.stat().st_size > 100_000,
        "request_json": (run_dir / "request.json").is_file(),
        "measurements_sidecar": any(f.endswith(".measurements.json") for f in files),
        "reference_copied": any(f.startswith("reference.") for f in files),
        "no_temp_files": not any(f.endswith((".part", ".tmp")) for f in files),
        "measured_plausible": bool(measurements.get("vertices", 0) > 1000),
    }
    rep.probe("verify", run=run_dir.name, **checks)
    return {"run_dir": run_dir, "files": files, "checks": checks}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, default=2, help="how many generations")
    parser.add_argument("--name", default="red-dragon", help="run slug")
    parser.add_argument("--seed", type=int, default=42, help="seed for the first run")
    parser.add_argument("--image", help="reference image (default: project reference)")
    parser.add_argument(
        "--no-wait",
        action="store_true",
        help="fail immediately on a quota refusal instead of waiting it out",
    )
    args = parser.parse_args()

    load_dotenv()
    require_env("HF_TOKEN")
    project = require_env("CHARCTX_PROJECT")

    image = args.image or str(
        Path(project) / "inputs" / "references" / "trellis-example-dragon.png"
    )
    if not Path(image).is_file():
        raise SystemExit(f"Reference image not found: {image}")

    rep = Report("live-validation", "Live Validation - TRELLIS.2 Through The CLI")
    rep.p(
        "Live proof that `charctx generate` takes a reference image through "
        "`microsoft/TRELLIS.2` and lands a measured mesh in the selected "
        "project folder. Meshes go to the project, never to a temp directory; "
        "this folder holds only the report."
    )
    rep.table(
        ["Setting", "Value"],
        [
            ["project", f"`{project}`"],
            ["reference", f"`{Path(image).name}`"],
            ["runs requested", str(args.runs)],
            ["quota behavior", "fail fast" if args.no_wait else "wait out refusals"],
        ],
    )

    results: list[dict] = []
    for index in range(args.runs):
        seed = args.seed + index
        rep.h2(f"Run {index + 1} - `{args.name}` seed {seed}")
        payload = generate_once(args.name, seed, image, rep, wait=not args.no_wait)
        if payload is None:
            break

        verified = verify_slot(payload, rep)
        measurements = payload.get("measurements") or {}
        results.append(
            {
                "run_dir": str(verified["run_dir"]),
                "seed": seed,
                "duration_s": payload.get("duration_s"),
                "measurements": measurements,
                "checks": verified["checks"],
            }
        )

        rep.p(f"Generated in **{payload.get('duration_s')}s**.")
        rep.table(
            ["Field", "Value"],
            [
                ["run slot", f"`{verified['run_dir'].name}`"],
                ["files", ", ".join(f"`{f}`" for f in verified["files"])],
                ["vertices", f"{measurements.get('vertices', 0):,}"],
                ["faces", f"{measurements.get('faces', 0):,}"],
                [
                    "extents",
                    " x ".join(
                        f"{v:.4f}" for v in measurements.get("extents", [0, 0, 0])
                    ),
                ],
                ["surface area", f"{measurements.get('surface_area', 0):.4f}"],
                ["watertight", str(measurements.get("watertight"))],
                ["components", str(measurements.get("connected_components"))],
                ["degenerate faces", str(measurements.get("degenerate_faces"))],
                ["all finite", str(measurements.get("all_finite"))],
                ["textured", str(measurements.get("textured"))],
                ["file size", f"{measurements.get('file_size_bytes', 0):,} bytes"],
            ],
        )
        failed = [name for name, ok in verified["checks"].items() if not ok]
        rep.p(
            "All slot checks passed."
            if not failed
            else f"**Failed checks:** {', '.join(failed)}"
        )

    rep.h2("Outcome")
    rep.data["runs"] = results
    if not results:
        rep.p("**No generation completed.**")
        rep.write()
        return 1

    slots = [Path(r["run_dir"]).name for r in results]
    rep.p(f"Completed {len(results)} run(s): {', '.join(f'`{s}`' for s in slots)}.")
    if len(results) > 1:
        distinct = len(set(slots)) == len(slots)
        verdict = "each run took its own slot" if distinct else "**SLOT REUSED**"
        rep.p(f"Append-only: {verdict}.")
        first, second = results[0]["measurements"], results[1]["measurements"]
        rep.p(
            "Seed sensitivity: "
            f"{first.get('vertices', 0):,} vs {second.get('vertices', 0):,} vertices "
            f"({first.get('faces', 0):,} vs {second.get('faces', 0):,} faces)."
        )
    rep.write()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
