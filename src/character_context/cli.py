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
import webbrowser
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
from .paths import CACHE_LAYOUT, REPO_ROOT, REPORTS_DIR, TOOLS_DIR, ensure_cache_layout


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

    if not args.no_views:
        from . import generations as generations_mod

        try:
            viewer = generations_mod.build_view(
                selected,
                f"{result.backend}/{result.run_dir.name}",
                character_id=request.name,
            )
            payload["viewer"] = viewer
            lines += [
                f"  viewer: {Path(viewer['manifest']).name}",
                f"  views : {len(viewer['previews'])} model-derived preview(s)",
            ]
        except ConfigError as exc:
            payload["viewer_warning"] = str(exc)
            lines.append(f"  viewer warning: {exc}")

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


def cmd_assets_inspect(args: argparse.Namespace) -> int:
    """Read-only inventory of loose candidates and existing packages."""
    from . import assets as assets_mod
    from . import project as project_mod

    selected = project_mod.select(args.project)
    payload = assets_mod.inspect_collection(selected)
    lines = [f"collected assets: {payload['root']}", "", "loose candidates:"]
    for item in payload["loose"]:
        state = "COLLISION" if item["collision"] else "ready"
        lines.append(
            f"  {Path(item['source']).name} -> {item['asset_id']}/ "
            f"({item['bytes']:,} bytes, {state})"
        )
    if not payload["loose"]:
        lines.append("  none")
    lines += ["", "packages:"]
    for item in payload["packages"]:
        state = (
            "reference images"
            if item["kind"] == "reference"
            else "built"
            if item["built"]
            else "not built"
        )
        lines.append(
            f"  {item['id']}: {item['title']} ({item['provenance_status']}, {state})"
        )
    if not payload["packages"]:
        lines.append("  none")
    _emit(payload, lines, args.json)
    return 0


def cmd_assets_list(args: argparse.Namespace) -> int:
    """List normalized cards for collected asset packages."""
    from . import assets as assets_mod
    from . import project as project_mod

    selected = project_mod.select(args.project)
    cards = assets_mod.list_assets(selected)
    payload = {"assets": [card.model_dump(mode="json") for card in cards]}
    lines = [f"collected assets: {len(cards)}"]
    for card in cards:
        badges = ["reference images"] if card.kind == "reference" else [
            "rigged" if card.rigged else "unrigged"
        ]
        if card.kind == "donor" and card.skeleton:
            badges.append("skeleton extracted")
        if card.kind == "donor" and card.animated:
            badges.append("animated")
        badges.append(card.provenance_status)
        lines.append(f"  {card.id}: {card.title} ({', '.join(badges)})")
    _emit(payload, lines, args.json)
    return 0


def cmd_assets_show(args: argparse.Namespace) -> int:
    """Show normalized curated and measured facts for one package."""
    from . import assets as assets_mod
    from . import project as project_mod

    selected = project_mod.select(args.project)
    payload = assets_mod.show_asset(selected, args.asset_id)
    card = payload["card"]
    lines = [
        f"{card['id']}: {card['title']}",
        f"  package    : {card['package_dir']}",
        f"  kind       : {card['kind']}",
        f"  provenance : {card['provenance_status']}",
    ]
    if card["kind"] == "reference":
        lines.append(f"  previews   : {len(card['previews'])} image(s)")
    else:
        lines += [
            "  geometry   : "
            f"{card['vertices']:,} vertices, {card['polygons']:,} polygons",
            f"  rig        : {card['bones']} bones, {card['actions']} action(s)",
            f"  skeleton   : {card['skeleton'] or 'not extracted'}",
            f"  weights    : {card['skin_weights'] or 'not extracted'}",
            f"  web model  : {card['web_model'] or 'not built'}",
        ]
    for warning in card["warnings"]:
        lines.append(f"  warning    : {warning}")
    _emit(payload, lines, args.json)
    return 0


def cmd_assets_organize(args: argparse.Namespace) -> int:
    """Organize all eligible loose assets; this command is the mutation."""
    from . import assets as assets_mod
    from . import project as project_mod

    selected = project_mod.select(args.project)
    organized = assets_mod.organize(selected)
    payload = {"organized": organized, "count": len(organized)}
    lines = [f"organized {len(organized)} asset(s)"]
    lines += [f"  {item['id']}: {item['source']}" for item in organized]
    if not organized:
        lines.append("  no loose candidates; nothing changed")
    _emit(payload, lines, args.json)
    return 0


def cmd_assets_build(args: argparse.Namespace) -> int:
    """Inspect/render packages and write their deterministic derived assets."""
    from . import assets as assets_mod
    from . import project as project_mod

    selected = project_mod.select(args.project)
    built = assets_mod.build(selected, args.asset_id)
    payload = {"built": built, "count": len(built)}
    lines = [f"built {len(built)} asset(s)"]
    for item in built:
        lines.append(f"  {item['id']}: {item['web_model']}")
        for warning in item["warnings"]:
            lines.append(f"    warning: {warning}")
    _emit(payload, lines, args.json)
    return 0


def cmd_assets_validate(args: argparse.Namespace) -> int:
    """Validate package schemas, source hashes, paths, and derived outputs."""
    from . import assets as assets_mod
    from . import project as project_mod

    selected = project_mod.select(args.project)
    results = assets_mod.validate(selected, args.asset_id)
    valid = all(item["valid"] for item in results)
    payload = {"valid": valid, "assets": results}
    lines = [f"asset validation: {'pass' if valid else 'fail'}"]
    for item in results:
        lines.append(f"  {item['id']}: {'valid' if item['valid'] else 'invalid'}")
        lines += [f"    {error}" for error in item["errors"]]
    _emit(payload, lines, args.json)
    return 0 if valid else 1


def cmd_generations_build(args: argparse.Namespace) -> int:
    """Build model-derived views and a manifest for one generation run."""
    from . import generations as generations_mod
    from . import project as project_mod

    selected = project_mod.select(args.project)
    result = generations_mod.build_view(
        selected, args.run, character_id=args.character
    )
    lines = [
        f"generation view built: {result['run']}",
        f"  character: {result['character_id']}",
        f"  model    : {result['model']}",
        f"  manifest : {result['manifest']}",
        f"  previews : {len(result['previews'])}",
    ]
    _emit(result, lines, args.json)
    return 0


def cmd_skeleton_fit(args: argparse.Namespace) -> int:
    """Fit a donor skeleton onto one generation run's mesh."""
    from . import project as project_mod
    from . import skeleton_fit as skeleton_fit_mod

    selected = project_mod.select(args.project)
    result = skeleton_fit_mod.fit(
        selected, args.run, args.donor, method=args.method,
        character_id=args.character,
    )
    fill = result["target_fill_ratio"]
    containment = result["containment"]
    lines = [
        f"skeleton fitted: {result['target']}",
        f"  donor    : {result['donor']}",
        f"  method   : {result['method']}",
        f"  bones    : {result['bones']}",
        "  fill     : "
        + ", ".join(f"{axis} {value:.0%}" for axis, value in fill.items()),
        f"  outside  : {containment['outside_bounds']} of "
        f"{containment['joints']} joints beyond the mesh bounds"
        + (
            f" ({containment['anchored']['outside_bounds']} anchored, "
            f"{containment['carried']['outside_bounds']} carried)"
            if "anchored" in containment
            else ""
        ),
    ]
    if "chains" in result:
        symmetry = result["symmetry"]
        lines.extend(
            [
                f"  anchored : {result['anchored_bones']} bones on "
                f"{len(result['chains'])} chains; "
                f"{result['carried_bones']} carried in a parent frame",
                f"  symmetry : max {symmetry.get('max', 0.0):.6f} over "
                f"{symmetry.get('pairs', 0)} mirrored pairs",
            ]
        )
        for chain in result["chains"]:
            lines.append(
                f"    {chain['chain']:<12} {chain['bones']:>2} bones  "
                f"scale {chain['scale']:.4f}  "
                f"({' -> '.join(chain['landmarks'])})"
            )
        for entry in result["chains_skipped"]:
            lines.append(f"    {entry['chain']:<12} skipped: {entry['reason']}")
    else:
        lines.append(f"  scale    : {result['uniform_scale']:.6f} (uniform)")
    lines.append(f"  skeleton : {result['skeleton']}")
    _emit(result, lines, args.json)
    return 0


def cmd_skeleton_landmarks(args: argparse.Namespace) -> int:
    """Propose anatomical landmarks on one generation run's mesh."""
    from . import landmarks as landmarks_mod
    from . import project as project_mod

    selected = project_mod.select(args.project)
    result = landmarks_mod.build(selected, args.run, character_id=args.character)
    summary = result["summary"]
    axes = result["axes"]
    lines = [
        f"landmarks proposed: {result['target']}",
        f"  method    : {result['method']}",
        f"  axes      : symmetry {axes['symmetry_axis']}, body "
        f"{axes['body_axis']}, up {axes['up_axis']}",
        f"  head       : towards {result['head_towards']} "
        f"{axes['body_axis']}",
        f"  landmarks : {summary['landmarks']} "
        f"({summary['center']} center, {summary['left']} left, "
        f"{summary['right']} right; {summary['high_confidence']} high)",
        f"  skipped   : {len(result['not_attempted'])} interior joints "
        f"({', '.join(result['not_attempted'])})",
        f"  file      : {result['landmarks']}",
    ]
    _emit(result, lines, args.json)
    return 0


def cmd_parts_taxonomy(args: argparse.Namespace) -> int:
    """Print the standardized body-part taxonomy."""
    from . import body_parts as body_parts_mod

    result = body_parts_mod.describe()
    lines = [
        f"taxonomy: {result['taxonomy']}",
        f"  parts  : {result['parts']} "
        f"({len(result['axial'])} axial, {len(result['paired'])} paired)",
        f"  axial  : {', '.join(result['axial'])}",
        f"  paired : {', '.join(result['paired'])}",
        f"  sub    : {', '.join(result['sub_parts']) or 'none'}",
        f"  root   : {result['root']}, hierarchy declared over "
        f"{len(result['hierarchy'])} parts",
        f"  donors : {', '.join(result['donors_mapped']) or 'none mapped'}",
    ]
    _emit(result, lines, args.json)
    return 0


def _voxel_lines(result: dict) -> list[str]:
    voxelization = result["voxelization"]
    summary = result["summary"]
    lines = [
        f"  grid     : {result['grid']['resolution']}^3 at pitch "
        f"{result['grid']['pitch']:.5f}",
        f"  solid    : {summary['solid_voxels']} voxels "
        f"({voxelization['occupancy']:.1%} of the grid), "
        f"{voxelization['solid_components']} component(s)",
        f"  labelled : {summary['labelled_voxels']} "
        f"({summary['labelled_fraction']:.1%}) across "
        f"{summary['parts_present']}/{summary['parts_total']} parts",
    ]
    if result["empty_parts"]:
        lines.append(f"  empty    : {', '.join(result['empty_parts'])}")
    if result["split_parts"]:
        leaks = ", ".join(
            f"{name} x{pieces}" for name, pieces in result["split_parts"].items()
        )
        lines.append(f"  split    : {leaks}")
    return lines


def cmd_parts_reference(args: argparse.Namespace) -> int:
    """Label a donor's volume from its own authored rig."""
    from . import part_volume as part_volume_mod
    from . import project as project_mod

    selected = project_mod.select(args.project)
    result = part_volume_mod.reference(
        selected, args.donor, resolution=args.resolution
    )
    coverage = result["weight_coverage"]
    lines = [
        f"part reference: {result['target']}",
        f"  method   : {result['method']}",
        *_voxel_lines(result),
    ]
    if coverage.get("available"):
        state = (
            "all mapped"
            if coverage["total"]
            else "UNMAPPED: " + ", ".join(coverage["unmapped"][:5])
        )
        lines.append(
            f"  weights  : {coverage['weight_bearing_bones']} weight-bearing "
            f"bones, {state}"
        )
    lines.append(f"  file     : {result['parts']}")
    _emit(result, lines, args.json)
    return 0


def cmd_parts_segment(args: argparse.Namespace) -> int:
    """Classify one generation run's volume into body parts."""
    from . import part_volume as part_volume_mod
    from . import project as project_mod

    selected = project_mod.select(args.project)
    result = part_volume_mod.segment(
        selected, args.run, character_id=args.character, resolution=args.resolution
    )
    lines = [
        f"parts segmented: {result['target']}",
        f"  method   : {result['method']}",
        *_voxel_lines(result),
        f"  no seed  : {len(result['unseedable_parts'])} part(s) have no "
        f"landmark and cannot appear "
        f"({', '.join(result['unseedable_parts'])})",
        f"  file     : {result['parts']}",
    ]
    _emit(result, lines, args.json)
    return 0


def cmd_parts_score(args: argparse.Namespace) -> int:
    """Score a sparse-seed proposal against a donor's authored rig."""
    from . import part_volume as part_volume_mod
    from . import project as project_mod

    selected = project_mod.select(args.project)
    result = part_volume_mod.score(
        selected, args.donor, mode=args.mode, resolution=args.resolution
    )
    metrics = result["metrics"]
    lines = [
        f"part score: {result['target']} ({result['mode']} seeding)",
        f"  grid      : {result['grid']['resolution']}^3, "
        f"{result['solid_voxels']} solid voxels",
        f"  seeds     : {result['proposal_seed_points']} proposal vs "
        f"{result['reference_seed_points']} reference points",
        f"  accuracy  : {metrics['voxel_accuracy']:.1%} of labelled voxels agree",
        f"  IoU       : mean {metrics['mean_iou']:.3f}, "
        f"median {metrics['median_iou']:.3f} over "
        f"{metrics['parts_scored']} parts",
        "  worst     : "
        + ", ".join(f"{row['part']} {row['iou']:.2f}" for row in metrics["worst"]),
        "  best      : "
        + ", ".join(f"{row['part']} {row['iou']:.2f}" for row in metrics["best"]),
    ]
    if metrics["missed_entirely"]:
        lines.append(f"  missed    : {', '.join(metrics['missed_entirely'])}")
    if result["unseedable_parts"]:
        lines.append(
            f"  no seed   : {len(result['unseedable_parts'])} part(s) - "
            f"{', '.join(result['unseedable_parts'])}"
        )
    _emit(result, lines, args.json)
    return 0


def cmd_parts_skeleton(args: argparse.Namespace) -> int:
    """Derive a bone hierarchy from a target's labelled volume."""
    from . import part_skeleton as part_skeleton_mod
    from . import project as project_mod

    selected = project_mod.select(args.project)
    result = part_skeleton_mod.derive(
        selected, args.target, seeds=args.seeds, resolution=args.resolution
    )
    summary = result["summary"]
    check = result["adjacency_check"]
    lines = [
        f"skeleton derived: {result['target']} ({result['seeds']} seeding)",
        f"  method   : {result['method']}",
        f"  bones    : {summary['bones']} over "
        f"{summary['parts_present']}/{summary['parts_total']} parts, "
        f"depth {summary['max_depth']}, total length "
        f"{summary['total_length']:.3f}",
        f"  joints   : {summary['joints']} region boundaries",
    ]
    if check.get("available"):
        lines.append(
            f"  adjacency: {check['agrees_with_declared']}/{check['parts']} "
            f"derived edges agree with the declared hierarchy"
            + (
                ""
                if not check["disagreements"]
                else " ("
                + ", ".join(
                    f"{row['part']}->{row['derived']}"
                    for row in check["disagreements"]
                )
                + ")"
            )
        )
    if result["reattached_parts"]:
        lines.append(f"  reattached: {', '.join(result['reattached_parts'])}")
    if result["detached_parts"]:
        lines.append(f"  detached : {', '.join(result['detached_parts'])}")
    if result["degenerate_bones"]:
        lines.append(f"  degenerate: {', '.join(result['degenerate_bones'])}")
    if result["absent_parts"]:
        lines.append(f"  no bone  : {', '.join(result['absent_parts'])}")
    lines.append(f"  file     : {result['file']}")
    _emit(result, lines, args.json)
    return 0


def cmd_parts_skeleton_score(args: argparse.Namespace) -> int:
    """Score a derived skeleton against a donor's authored rig."""
    from . import part_skeleton as part_skeleton_mod
    from . import project as project_mod

    selected = project_mod.select(args.project)
    result = part_skeleton_mod.score(
        selected, args.donor, seeds=args.seeds, resolution=args.resolution
    )
    joint = result["joint_error"]
    check = result["adjacency_check"]
    lines = [
        f"skeleton score: {result['target']} ({result['seeds']} seeding)",
        f"  bones     : {result['bones']} bones, {result['scored_joints']} "
        f"joints scored against the donor rig",
        f"  hierarchy : {result['hierarchy_matches_donor']}/"
        f"{result['hierarchy_total']} declared parents match the donor; "
        f"adjacency alone agrees on {check.get('agrees_with_declared', 0)}",
        f"  joint err : median {joint['median_pct']:.2%} of the body "
        f"diagonal, mean {joint['mean_pct']:.2%} "
        f"({joint['mean_voxels']} voxels), max {joint['max_pct']:.2%}",
        f"  unambiguous: median {joint['unambiguous_median_pct']:.2%} over "
        f"{joint['unambiguous_joints']} joints the donor places at one point",
        f"  bone axis : median {result['axis_angle_deg']['median']}deg",
        "  worst     : "
        + ", ".join(
            f"{row['part']} {row['joint_error_pct']:.1%}"
            for row in result["worst_joints"]
        ),
        "  best      : "
        + ", ".join(
            f"{row['part']} {row['joint_error_pct']:.1%}"
            for row in result["best_joints"]
        ),
    ]
    if result["missing_from_donor"]:
        lines.append(f"  missing   : {', '.join(result['missing_from_donor'])}")
    _emit(result, lines, args.json)
    return 0


def cmd_web(args: argparse.Namespace) -> int:
    """Start the private local Astro asset catalog."""
    from . import project as project_mod
    from . import web as web_mod

    selected = project_mod.select(args.project)
    directory = web_mod.webapp_dir()
    log = REPORTS_DIR / "web.log"
    if not web_mod.dependencies_installed(directory):
        if args.no_install:
            raise ConfigError("web dependencies are missing; omit --no-install")
        web_mod.install(directory, log)
    server = web_mod.start(
        directory, project=selected.root, host=args.host, port=args.port
    )
    payload = {"url": server.url, "project": str(selected.root), "log": str(server.log)}
    _emit(
        payload,
        [
            f"dragon catalog: {server.url}",
            f"  project: {selected.root}",
            f"  log: {server.log}",
            "  Ctrl-C to stop",
        ],
        args.json,
    )
    if args.open:
        webbrowser.open(server.url)
    return server.wait()


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

    assets_cmd = subparsers.add_parser(
        "assets", help="collected asset packages and previews", parents=[shared]
    )
    assets_sub = assets_cmd.add_subparsers(dest="assets_command", required=True)
    assets_inspect = assets_sub.add_parser(
        "inspect",
        help="read-only loose/package inventory and proposed moves",
        parents=[shared],
    )
    assets_inspect.set_defaults(func=cmd_assets_inspect)
    assets_list = assets_sub.add_parser(
        "list", help="list normalized asset cards", parents=[shared]
    )
    assets_list.set_defaults(func=cmd_assets_list)
    assets_show = assets_sub.add_parser(
        "show", help="show one asset package", parents=[shared]
    )
    assets_show.add_argument("asset_id", help="collected asset id")
    assets_show.set_defaults(func=cmd_assets_show)
    assets_organize = assets_sub.add_parser(
        "organize",
        help="organize every eligible loose candidate (writes/moves)",
        parents=[shared],
    )
    assets_organize.set_defaults(func=cmd_assets_organize)
    assets_build = assets_sub.add_parser(
        "build",
        help="inspect/render one 3D donor or all 3D donors",
        parents=[shared],
    )
    assets_build.add_argument(
        "asset_id", nargs="?", help="asset id (default: build every 3D donor)"
    )
    assets_build.set_defaults(func=cmd_assets_build)
    assets_validate = assets_sub.add_parser(
        "validate",
        help="validate one asset or the whole collection",
        parents=[shared],
    )
    assets_validate.add_argument(
        "asset_id", nargs="?", help="asset id (default: validate every package)"
    )
    assets_validate.set_defaults(func=cmd_assets_validate)

    generations = subparsers.add_parser(
        "generations",
        help="append-only generation manifests and viewer views",
        parents=[shared],
    )
    generations_sub = generations.add_subparsers(
        dest="generations_command", required=True
    )
    generations_build = generations_sub.add_parser(
        "build",
        help="build viewer metadata and neutral views for one generation",
        parents=[shared],
    )
    generations_build.add_argument(
        "run", help="generation id as <backend>/<run-folder>"
    )
    generations_build.add_argument(
        "--character", help="owning character id (default: request name)"
    )
    generations_build.set_defaults(func=cmd_generations_build)

    skeleton = subparsers.add_parser(
        "skeleton",
        help="synthesize and inspect skeletons for generated meshes",
        parents=[shared],
    )
    skeleton_sub = skeleton.add_subparsers(dest="skeleton_command", required=True)
    skeleton_fit_parser = skeleton_sub.add_parser(
        "fit",
        help="fit a donor skeleton onto one generation run",
        parents=[shared],
    )
    skeleton_fit_parser.add_argument(
        "run", help="generation id as <backend>/<run-folder>"
    )
    skeleton_fit_parser.add_argument(
        "--donor", required=True, help="donor asset id supplying the hierarchy"
    )
    skeleton_fit_parser.add_argument(
        "--character", help="owning character id (default: request name)"
    )
    skeleton_fit_parser.add_argument(
        "--method",
        choices=("chain", "rigid"),
        default="chain",
        help="chain: anchor joints on the target's landmarks (default); "
        "rigid: move the donor rig as one body",
    )
    skeleton_fit_parser.set_defaults(func=cmd_skeleton_fit)

    skeleton_landmarks_parser = skeleton_sub.add_parser(
        "landmarks",
        help="propose anatomical landmarks on one generation run",
        parents=[shared],
    )
    skeleton_landmarks_parser.add_argument(
        "run", help="generation id as <backend>/<run-folder>"
    )
    skeleton_landmarks_parser.add_argument(
        "--character", help="owning character id (default: request name)"
    )
    skeleton_landmarks_parser.set_defaults(func=cmd_skeleton_landmarks)

    parts = subparsers.add_parser(
        "parts",
        help="classify a mesh volume into standardized body parts",
        parents=[shared],
    )
    parts_sub = parts.add_subparsers(dest="parts_command", required=True)

    parts_taxonomy = parts_sub.add_parser(
        "taxonomy", help="print the standardized part taxonomy", parents=[shared]
    )
    parts_taxonomy.set_defaults(func=cmd_parts_taxonomy)

    parts_reference = parts_sub.add_parser(
        "reference",
        help="label a donor's volume from its own authored rig",
        parents=[shared],
    )
    parts_reference.add_argument("donor", help="donor asset id")
    parts_reference.add_argument(
        "--resolution", type=int, default=128, help="voxel grid resolution"
    )
    parts_reference.set_defaults(func=cmd_parts_reference)

    parts_segment = parts_sub.add_parser(
        "segment",
        help="classify one generation run's volume from its landmarks",
        parents=[shared],
    )
    parts_segment.add_argument("run", help="generation id as <backend>/<run-folder>")
    parts_segment.add_argument(
        "--character", help="owning character id (default: request name)"
    )
    parts_segment.add_argument(
        "--resolution", type=int, default=128, help="voxel grid resolution"
    )
    parts_segment.set_defaults(func=cmd_parts_segment)

    parts_score = parts_sub.add_parser(
        "score",
        help="score sparse-seed segmentation against a donor's authored rig",
        parents=[shared],
    )
    parts_score.add_argument("donor", help="donor asset id")
    parts_score.add_argument(
        "--mode",
        choices=("centroid", "landmarks"),
        default="centroid",
        help="centroid: one seed per part, isolating the cost of sparsity; "
        "landmarks: the real geometric proposer, end to end",
    )
    parts_score.add_argument(
        "--resolution", type=int, default=128, help="voxel grid resolution"
    )
    parts_score.set_defaults(func=cmd_parts_score)

    parts_skeleton = parts_sub.add_parser(
        "skeleton",
        help="derive a bone hierarchy from a labelled volume",
        parents=[shared],
    )
    parts_skeleton.add_argument(
        "target", help="donor asset id, or generation id as <backend>/<run-folder>"
    )
    parts_skeleton.add_argument(
        "--seeds",
        choices=("reference", "centroid", "landmarks"),
        default="reference",
        help="how the volume is labelled first: reference uses a donor's own "
        "authored bones, centroid and landmarks are donor-independent",
    )
    parts_skeleton.add_argument(
        "--resolution", type=int, default=128, help="voxel grid resolution"
    )
    parts_skeleton.set_defaults(func=cmd_parts_skeleton)

    parts_skeleton_score = parts_sub.add_parser(
        "skeleton-score",
        help="score a derived skeleton against a donor's authored rig",
        parents=[shared],
    )
    parts_skeleton_score.add_argument("donor", help="donor asset id")
    parts_skeleton_score.add_argument(
        "--seeds",
        choices=("reference", "centroid", "landmarks"),
        default="reference",
        help="reference isolates the skeleton step; centroid and landmarks "
        "measure it compounded with a sparse labelling",
    )
    parts_skeleton_score.add_argument(
        "--resolution", type=int, default=128, help="voxel grid resolution"
    )
    parts_skeleton_score.set_defaults(func=cmd_parts_skeleton_score)

    web = subparsers.add_parser(
        "web", help="start the private local dragon catalog", parents=[shared]
    )
    web.add_argument("--host", default="127.0.0.1", help="listen host")
    web.add_argument("--port", type=int, default=4321, help="listen port")
    web.add_argument(
        "--no-install", action="store_true", help="fail if web dependencies are missing"
    )
    web.add_argument(
        "--open", action="store_true", help="open the catalog in the default browser"
    )
    web.set_defaults(func=cmd_web)

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
    generate.add_argument(
        "--no-views",
        action="store_true",
        help="skip model-derived viewer previews and viewer.json",
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
    raw = list(argv) if argv is not None else sys.argv[1:]
    args = parser.parse_args(raw)
    # Nested argparse parents can replace a root-level value with a child
    # default. Reapply the two deliberately position-independent global flags.
    if "--json" in raw:
        args.json = True
    for index, token in enumerate(raw):
        if token == "--project" and index + 1 < len(raw):
            args.project = raw[index + 1]
        elif token.startswith("--project="):
            args.project = token.partition("=")[2]
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
