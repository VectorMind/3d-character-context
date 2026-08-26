"""`charctx` - the single documented interface for humans and agents.

Every capability the repository ships is reachable here and documented in
`README.md`; a capability with no command is not delivered. Each command
prints human-readable text by default and machine-readable JSON with
`--json`.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from . import __version__
from .config import (
    ConfigError,
    artifacts_config,
    backend_config,
    credential,
    load_dotenv,
    mask,
    providers_config,
)
from .paths import CACHE_LAYOUT, REPO_ROOT, TOOLS_DIR, ensure_cache_layout


def _emit(payload: dict[str, Any], lines: list[str], as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, indent=2, default=str))
    else:
        print("\n".join(lines))


def _parse_options(pairs: list[str] | None) -> dict[str, Any]:
    """Parse repeated `--option key=value` flags, coercing obvious scalars."""
    options: dict[str, Any] = {}
    for pair in pairs or []:
        if "=" not in pair:
            raise ConfigError(f"--option expects key=value, got {pair!r}")
        key, _, raw = pair.partition("=")
        value: Any = raw
        if raw.lower() in {"true", "false"}:
            value = raw.lower() == "true"
        else:
            try:
                value = int(raw)
            except ValueError:
                try:
                    value = float(raw)
                except ValueError:
                    pass
        options[key.strip()] = value
    return options


# --------------------------------------------------------------------------
# commands


def cmd_info(args: argparse.Namespace) -> int:
    """Report the workspace state: version, credentials, project, tools."""
    from . import artifacts as artifacts_mod
    from . import project as project_mod

    load_dotenv()
    config = providers_config()
    backends = config.get("backends") or {}

    provider_rows = []
    for name, entry in backends.items():
        variable = entry.get("credential", "")
        provider_rows.append(
            {
                "backend": name,
                "provider": entry.get("provider"),
                "endpoint": entry.get("space") or entry.get("url"),
                "credential": variable,
                "credentialed": bool(credential(variable, required=False)),
                "default": name == config.get("default_backend"),
            }
        )

    tool_rows = []
    for name in (artifacts_config().get("artifacts") or {}):
        tool = artifacts_mod.resolve(name)
        tool_rows.append(
            {
                "tool": name,
                "version": tool.version,
                "installed": tool.installed,
                "executable": str(tool.executable),
            }
        )

    try:
        selected = project_mod.select(args.project)
        project_info: dict[str, Any] = selected.describe()
    except ConfigError as exc:
        project_info = {"root": None, "error": str(exc)}

    payload = {
        "version": __version__,
        "python": sys.version.split()[0],
        "repository": str(REPO_ROOT),
        "project": project_info,
        "backends": provider_rows,
        "tools": tool_rows,
    }

    lines = [
        f"charctx {__version__} (python {sys.version.split()[0]})",
        f"repository : {REPO_ROOT}",
        f"project    : {project_info.get('root') or 'not selected'}"
        + (
            ""
            if not project_info.get("root") or project_info.get("scaffolded")
            else "  [not scaffolded]"
        ),
        "",
        "backends:",
    ]
    for row in provider_rows:
        flag = " (default)" if row["default"] else ""
        state = (
            "credentialed" if row["credentialed"] else f"missing {row['credential']}"
        )
        lines.append(f"  {row['backend']}{flag}: {row['endpoint']} - {state}")
    lines.append("")
    lines.append("tools:")
    for row in tool_rows:
        state = "installed" if row["installed"] else "not fetched"
        lines.append(f"  {row['tool']} {row['version']}: {state}")

    _emit(payload, lines, args.json)
    return 0


def cmd_paths(args: argparse.Namespace) -> int:
    """Show every location the workspace reads from or writes to."""
    from . import project as project_mod

    ensure_cache_layout()
    payload: dict[str, Any] = {
        "repository": str(REPO_ROOT),
        "cache": {name: str(path) for name, path in CACHE_LAYOUT.items()},
        "tools": str(TOOLS_DIR),
        "config": str(REPO_ROOT / "config"),
    }
    lines = [
        f"repository : {REPO_ROOT}",
        f"config     : {REPO_ROOT / 'config'}",
        f"tools      : {TOOLS_DIR}",
    ]
    for name, path in CACHE_LAYOUT.items():
        lines.append(f"cache/{name:<9}: {path}")

    try:
        selected = project_mod.select(args.project)
        payload["project"] = {
            "root": str(selected.root),
            "inputs": str(selected.inputs),
            "generated": str(selected.generated),
            "assets": str(selected.assets),
        }
        lines += [
            "",
            f"project    : {selected.root}",
            f"  inputs   : {selected.inputs}",
            f"  generated: {selected.generated}",
            f"  assets   : {selected.assets}",
        ]
    except ConfigError as exc:
        payload["project"] = {"root": None, "error": str(exc)}
        lines += ["", f"project    : not selected ({exc})"]

    _emit(payload, lines, args.json)
    return 0


def cmd_project_init(args: argparse.Namespace) -> int:
    """Scaffold the conventional layout in an external project folder."""
    from . import project as project_mod

    root = args.path or (project_mod.select(args.project).root)
    selected, created = project_mod.init(Path(root))
    payload = {
        "root": str(selected.root),
        "created": [str(p) for p in created],
        **selected.describe(),
    }
    lines = [f"project: {selected.root}"]
    lines += [f"  created {p.name}/" for p in created] or ["  already scaffolded"]
    lines.append(
        f"\nSelect it by adding CHARCTX_PROJECT={selected.root} to "
        f"{REPO_ROOT / '.env'}"
    )
    _emit(payload, lines, args.json)
    return 0


def cmd_project_info(args: argparse.Namespace) -> int:
    """Report the active project folder and what it holds."""
    from . import project as project_mod

    selected = project_mod.select(args.project)
    payload = selected.describe()
    lines = [
        f"project    : {selected.root}",
        f"exists     : {payload['exists']}",
        f"scaffolded : {payload['scaffolded']}",
    ]
    for name, count in (payload.get("files") or {}).items():
        lines.append(f"  {name:<10}: {count} file(s)")
    _emit(payload, lines, args.json)
    return 0


def cmd_fetch(args: argparse.Namespace) -> int:
    """Provision a declared external tool into `.tools/`."""
    from . import artifacts as artifacts_mod

    ensure_cache_layout()
    last = [-1]

    def progress(done: int, total: int) -> None:
        if args.json or not total:
            return
        percent = int(done * 100 / total)
        if percent != last[0]:
            last[0] = percent
            print(
                f"\r  downloading {args.name}: {percent:3d}% "
                f"({done / 1e6:.0f}/{total / 1e6:.0f} MB)",
                end="",
                flush=True,
            )

    tool = artifacts_mod.fetch(args.name, force=args.force, on_progress=progress)
    if not args.json:
        print()
    tool, output = artifacts_mod.verify(args.name)
    payload = {
        "tool": tool.name,
        "version": tool.version,
        "install_dir": str(tool.install_dir),
        "executable": str(tool.executable),
        "version_output": output,
    }
    lines = [
        f"{tool.name} {tool.version} provisioned",
        f"  executable: {tool.executable}",
        f"  verified  : {output.splitlines()[0] if output else '(no output)'}",
    ]
    _emit(payload, lines, args.json)
    return 0


def cmd_generate(args: argparse.Namespace) -> int:
    """Generate a mesh from a reference image through a hosted backend."""
    from . import backends, mesh_report
    from . import project as project_mod
    from .contracts import GenerationRequest

    selected = project_mod.select(args.project)
    if not selected.exists:
        raise ConfigError(
            f"Project folder {selected.root} does not exist. "
            "Run `charctx project init <path>` first."
        )

    backend_name, _ = backend_config(args.backend)
    request = GenerationRequest(
        images=[Path(args.image)],
        name=args.name,
        backend=backend_name,
        seed=args.seed,
        prompt=args.prompt,
        options=_parse_options(args.option),
    )

    module = backends.resolve(backend_name)

    def event(message: str) -> None:
        if not args.json:
            print(f"  {message}", flush=True)

    result = module.generate(request, selected, on_event=event)

    payload: dict[str, Any] = {
        "backend": result.backend,
        "endpoint": result.endpoint,
        "run_dir": str(result.run_dir),
        "mesh": str(result.mesh),
        "duration_s": result.duration_s,
    }
    lines = [
        f"generated in {result.duration_s}s via {result.endpoint}",
        f"  run  : {result.run_dir}",
        f"  mesh : {result.mesh.name}",
    ]

    if not args.no_report:
        measurements = mesh_report.measure(
            result.mesh,
            backend=result.backend,
            seed=request.seed,
            request_name=request.name,
        )
        written = mesh_report.write_measurements(measurements)
        payload["measurements"] = json.loads(measurements.model_dump_json())
        payload["measurements_file"] = str(written)
        lines += [
            f"  report: {written.name}",
            f"  {measurements.vertices} vertices, {measurements.faces} faces, "
            f"{measurements.connected_components} component(s), "
            f"watertight={measurements.watertight}",
        ]

    _emit(payload, lines, args.json)
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    """Measure any local mesh and write its `*.measurements.json`."""
    from . import mesh_report

    measurements = mesh_report.measure(
        args.mesh, backend=args.backend, request_name=args.name
    )
    payload = json.loads(measurements.model_dump_json())
    written: Path | None = None
    if not args.no_write:
        written = mesh_report.write_measurements(
            measurements, Path(args.output) if args.output else None
        )
        payload["measurements_file"] = str(written)

    lines = [
        f"{measurements.source}",
        f"  format     : {measurements.file_format} "
        f"({measurements.file_size_bytes:,} bytes, "
        f"{measurements.geometries} geometry/ies)",
        f"  vertices   : {measurements.vertices:,}",
        f"  faces      : {measurements.faces:,}",
        "  extents    : "
        + " x ".join(f"{v:.4f}" for v in measurements.extents),
        "  bounds     : "
        + " ".join(f"{v:.4f}" for v in measurements.bounds_min)
        + "  ->  "
        + " ".join(f"{v:.4f}" for v in measurements.bounds_max),
        f"  area       : {measurements.surface_area:.4f}",
        "  volume     : "
        + (
            f"{measurements.volume:.4f}"
            if measurements.volume is not None
            else "n/a (not watertight)"
        ),
        f"  watertight : {measurements.watertight}",
        f"  components : {measurements.connected_components}",
        f"  degenerate : {measurements.degenerate_faces} face(s)",
        f"  finite     : {measurements.all_finite}",
        f"  textured   : {measurements.textured}",
        f"  sampled    : {measurements.sampled_points} surface point(s)",
        f"  plausible  : {measurements.is_plausible}",
    ]
    if written:
        lines.append(f"  written    : {written}")

    _emit(payload, lines, args.json)
    return 0


def cmd_backends(args: argparse.Namespace) -> int:
    """List configured backends and documented alternatives."""
    config = providers_config()
    payload = {
        "default": config.get("default_backend"),
        "implemented": [],
        "alternatives": [],
    }
    lines = ["implemented backends:"]
    for name, entry in (config.get("backends") or {}).items():
        variable = entry.get("credential", "")
        row = {
            "backend": name,
            "provider": entry.get("provider"),
            "endpoint": entry.get("space"),
            "call_shape": entry.get("call_shape"),
            "credential": variable,
            "credential_state": mask(credential(variable, required=False)),
        }
        payload["implemented"].append(row)
        lines.append(
            f"  {name}: {row['endpoint']} ({row['call_shape']}), "
            f"{variable} {row['credential_state']}"
        )
    lines.append("")
    lines.append("documented alternatives (no code):")
    for name, entry in (config.get("alternatives") or {}).items():
        payload["alternatives"].append({"name": name, **entry})
        lines.append(f"  {name}: {entry.get('space') or entry.get('note', '')}")
    _emit(payload, lines, args.json)
    return 0


# --------------------------------------------------------------------------
# parser


# Global flags are accepted both before and after the subcommand, because
# `charctx report mesh.glb --json` is what a human or agent actually types.
# The shared copies suppress their defaults so a flag given before the
# subcommand is not overwritten by the subparser's default.
def _global_flags() -> argparse.ArgumentParser:
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument(
        "--project",
        metavar="PATH",
        default=argparse.SUPPRESS,
        help="override the project folder for this command "
        "(default: CHARCTX_PROJECT from .env)",
    )
    shared.add_argument(
        "--json",
        action="store_true",
        default=argparse.SUPPRESS,
        help="machine-readable output",
    )
    return shared


def build_parser() -> argparse.ArgumentParser:
    shared = _global_flags()
    parser = argparse.ArgumentParser(
        prog="charctx",
        description="Generative-first 3D character workbench.",
        parents=[shared],
    )
    parser.add_argument("--version", action="version", version=f"charctx {__version__}")
    parser.set_defaults(project=None, json=False)
    subparsers = parser.add_subparsers(dest="command", required=True)

    info = subparsers.add_parser(
        "info",
        help="workspace state: credentials, project, tools",
        parents=[shared],
    )
    info.set_defaults(func=cmd_info)

    paths = subparsers.add_parser(
        "paths", help="every location read from or written to", parents=[shared]
    )
    paths.set_defaults(func=cmd_paths)

    backends_cmd = subparsers.add_parser(
        "backends",
        help="configured backends and documented alternatives",
        parents=[shared],
    )
    backends_cmd.set_defaults(func=cmd_backends)

    project = subparsers.add_parser(
        "project", help="the external data project folder", parents=[shared]
    )
    project_sub = project.add_subparsers(dest="project_command", required=True)
    project_init = project_sub.add_parser(
        "init",
        help="scaffold inputs/ generated/ assets/",
        parents=[shared],
    )
    project_init.add_argument(
        "path", nargs="?", help="folder to scaffold (default: the selected project)"
    )
    project_init.set_defaults(func=cmd_project_init)
    project_info = project_sub.add_parser(
        "info", help="report the active project folder", parents=[shared]
    )
    project_info.set_defaults(func=cmd_project_info)

    fetch = subparsers.add_parser(
        "fetch", help="provision a declared external tool", parents=[shared]
    )
    fetch.add_argument("name", help="artifact name from config/artifacts.yaml")
    fetch.add_argument(
        "--force", action="store_true", help="re-download and re-extract"
    )
    fetch.set_defaults(func=cmd_fetch)

    generate = subparsers.add_parser(
        "generate",
        help="reference image -> hosted generation -> mesh",
        parents=[shared],
    )
    generate.add_argument("image", help="reference image path")
    generate.add_argument(
        "--name", required=True, help="slug for the run folder, e.g. red-dragon"
    )
    generate.add_argument("--backend", help="backend key (default: config default)")
    generate.add_argument("--seed", type=int, default=0)
    generate.add_argument(
        "--prompt", help="optional text prompt, if the backend uses one"
    )
    generate.add_argument(
        "--option",
        action="append",
        metavar="KEY=VALUE",
        help="backend option override; repeatable",
    )
    generate.add_argument(
        "--no-report",
        action="store_true",
        help="skip measuring the downloaded mesh",
    )
    generate.set_defaults(func=cmd_generate)

    report = subparsers.add_parser(
        "report", help="measure a local mesh", parents=[shared]
    )
    report.add_argument("mesh", help="path to a GLB/GLTF/OBJ/PLY/STL file")
    report.add_argument("--output", help="write the sidecar here instead")
    report.add_argument("--backend", help="record which backend produced it")
    report.add_argument("--name", help="record the request name")
    report.add_argument(
        "--no-write",
        action="store_true",
        help="print metrics without writing a sidecar",
    )
    report.set_defaults(func=cmd_report)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # one clear line, not a traceback, for CLI users
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
