"""Collected dragon packages: inspect, organize, build, and catalog."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import Any

import yaml

from . import artifacts, mesh_report
from .asset_models import AssetCard, AssetFileRecord, AssetFrontMatter, AssetInspection
from .config import ConfigError
from .paths import REPORTS_DIR, SCRATCH_DIR, ensure_cache_layout
from .project import Project

SUPPORTED_LOOSE = {".blend", ".zip", ".fbx", ".glb", ".gltf", ".obj"}
MODEL_PRIORITY = {".blend": 0, ".fbx": 1, ".glb": 2, ".gltf": 3, ".obj": 4}
PREVIEW_NAMES = ("hero", "front", "left", "rear", "top")
MANUAL_START = "<!-- charctx:manual:start -->"
MANUAL_END = "<!-- charctx:manual:end -->"
MAX_ARCHIVE_MEMBERS = 10_000
MAX_ARCHIVE_EXPANDED_BYTES = 4 * 1024**3


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    if not slug:
        raise ConfigError(f"Cannot derive an asset id from {value!r}.")
    return slug


def _title(asset_id: str) -> str:
    return " ".join(part.capitalize() for part in asset_id.split("-"))


def _collected(project: Project) -> Path:
    path = project.assets / "collected"
    if not path.is_dir():
        raise ConfigError(
            f"Collected asset folder does not exist: {path}. "
            "Create it in the selected data workspace first."
        )
    return path.resolve()


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def _loose_candidates(project: Project) -> list[Path]:
    root = _collected(project)
    return sorted(
        path
        for path in root.iterdir()
        if path.is_file() and path.suffix.lower() in SUPPORTED_LOOSE
    )


def read_front_matter(readme: Path) -> tuple[AssetFrontMatter, str]:
    if not readme.is_file():
        raise ConfigError(f"Missing asset README: {readme}")
    text = readme.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        raise ConfigError(f"Asset README has no YAML front matter: {readme}")
    end = next((i for i, line in enumerate(lines[1:], 1) if line.strip() == "---"), -1)
    if end < 0:
        raise ConfigError(f"Asset README front matter is not closed: {readme}")
    try:
        raw = yaml.safe_load("".join(lines[1:end])) or {}
        metadata = AssetFrontMatter.model_validate(raw)
    except Exception as exc:
        raise ConfigError(f"Invalid asset front matter in {readme}: {exc}") from exc
    return metadata, "".join(lines[end + 1 :])


def _manual_notes(body: str) -> str:
    start = body.find(MANUAL_START)
    end = body.find(MANUAL_END)
    if start < 0 or end < start:
        return "Add local notes here."
    return body[start + len(MANUAL_START) : end].strip("\r\n")


def _inspection(package: Path) -> AssetInspection | None:
    path = package / "inspection" / "report.json"
    if not path.is_file():
        return None
    try:
        return AssetInspection.model_validate_json(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ConfigError(f"Invalid inspection report {path}: {exc}") from exc


def _unknown_warning(metadata: AssetFrontMatter) -> str | None:
    if metadata.provenance_status == "incomplete":
        return "Provenance incomplete — private local workspace use only."
    return None


def _readme_text(
    metadata: AssetFrontMatter,
    inspection: AssetInspection | None,
    manual_notes: str,
) -> str:
    dumped = yaml.safe_dump(
        metadata.model_dump(mode="json", by_alias=True),
        sort_keys=False,
        allow_unicode=True,
        width=100,
    ).strip()
    gallery = "\n".join(
        f"![{metadata.title} — {name}](previews/{name}.webp)" for name in PREVIEW_NAMES
    )
    warnings = list(inspection.warnings if inspection else [])
    unknown = _unknown_warning(metadata)
    if unknown:
        warnings.insert(0, unknown)
    warning_text = "\n".join(f"- {item}" for item in warnings) or "- None recorded."

    if inspection:
        vertices = sum(int(mesh.get("vertices", 0)) for mesh in inspection.meshes)
        polygons = sum(int(mesh.get("polygons", 0)) for mesh in inspection.meshes)
        bones = sum(int(armature.get("bones", 0)) for armature in inspection.armatures)
        weighted = sum(
            int(mesh.get("weighted_vertices", 0)) for mesh in inspection.meshes
        )
        total_vertices = sum(int(mesh.get("vertices", 0)) for mesh in inspection.meshes)
        characteristics = [
            (
                "Source format",
                Path(inspection.primary_model).suffix.lower().lstrip(".").upper(),
            ),
            ("Mesh objects", len(inspection.meshes)),
            ("Vertices", f"{vertices:,}"),
            ("Polygons", f"{polygons:,}"),
            ("Armatures", len(inspection.armatures)),
            ("Bones", bones),
            ("Weighted vertices", f"{weighted:,} / {total_vertices:,}"),
            ("Materials", len(inspection.materials)),
            ("Images", len(inspection.images)),
            ("Actions", len(inspection.actions)),
            ("Blender", inspection.blender_version),
        ]
        characteristic_rows = "\n".join(
            f"| {key} | {value} |" for key, value in characteristics
        )
        file_rows = "\n".join(
            f"| `{record.path}` | {record.bytes:,} | `{record.sha256}` |"
            for record in inspection.source_files
        )
        actions = (
            "\n".join(
                f"- `{action.get('name', 'unnamed')}` — frames "
                f"{action.get('frame_range', ['?', '?'])[0]}–"
                f"{action.get('frame_range', ['?', '?'])[1]}"
                for action in inspection.actions
            )
            or "- None measured."
        )
    else:
        characteristic_rows = "| Build status | Not built yet |"
        file_rows = "| Source inventory | Run `charctx assets build` | — |"
        actions = "- Not inspected yet."

    source = metadata.source
    license_info = metadata.license
    return f"""---
{dumped}
---

# {metadata.title}

> **Local catalog status:** `{metadata.status}` · provenance
> `{metadata.provenance_status}`. This private workspace page is not a
> publication or a license-clearance claim.

## Views

{gallery}

## Card

| Field | Value |
| --- | --- |
| Asset id | `{metadata.id}` |
| Family | `{metadata.family}` |
| Source provider | {source.provider} |
| Source asset id | {source.asset_id} |
| Creator | {source.creator} |
| Source URL | {source.url} |
| License | {license_info.name} |
| License URL | {license_info.url} |
| Acquisition | {metadata.acquisition.method} · {metadata.acquisition.date} |

## Characteristics

| Characteristic | Measured value |
| --- | ---: |
{characteristic_rows}

## Animations

{actions}

## Source Files

| Path | Bytes | SHA-256 |
| --- | ---: | --- |
{file_rows}

## Warnings

{warning_text}

## Manual Notes

{MANUAL_START}
{manual_notes}
{MANUAL_END}
"""


def _write_readme(
    package: Path,
    metadata: AssetFrontMatter,
    inspection: AssetInspection | None = None,
) -> None:
    readme = package / "README.md"
    notes = "Add local notes here."
    if readme.is_file():
        _, body = read_front_matter(readme)
        notes = _manual_notes(body)
    text = _readme_text(metadata, inspection, notes)
    temp = readme.with_suffix(".md.tmp")
    temp.write_text(text, encoding="utf-8", newline="\n")
    temp.replace(readme)


def inspect_collection(project: Project) -> dict[str, Any]:
    root = _collected(project)
    loose = []
    for source in _loose_candidates(project):
        asset_id = _slug(source.stem)
        destination = root / asset_id
        loose.append(
            {
                "source": str(source),
                "bytes": source.stat().st_size,
                "sha256": _sha256(source),
                "asset_id": asset_id,
                "destination": str(destination),
                "collision": destination.exists(),
            }
        )
    packages = []
    for directory in sorted(path for path in root.iterdir() if path.is_dir()):
        readme = directory / "README.md"
        if readme.is_file():
            metadata, _ = read_front_matter(readme)
            packages.append(
                {
                    "id": metadata.id,
                    "title": metadata.title,
                    "kind": metadata.kind,
                    "path": str(directory),
                    "provenance_status": metadata.provenance_status,
                    "built": (directory / "inspection" / "report.json").is_file()
                    if metadata.kind == "donor"
                    else None,
                }
            )
    return {"root": str(root), "loose": loose, "packages": packages}


def organize(project: Project) -> list[dict[str, Any]]:
    """Organize every loose candidate; the command itself is the mutation."""
    root = _collected(project)
    candidates = _loose_candidates(project)
    planned: list[tuple[Path, str, Path]] = []
    seen: set[str] = set()
    for source in candidates:
        source = source.resolve()
        if source.parent != root or not _inside(source, root):
            raise ConfigError(f"Refusing loose asset outside {root}: {source}")
        asset_id = _slug(source.stem)
        destination = root / asset_id
        staging = root / f".charctx-organize-{asset_id}"
        if asset_id in seen:
            raise ConfigError(f"Two loose files resolve to asset id {asset_id!r}.")
        if destination.exists() or staging.exists():
            raise ConfigError(
                f"Cannot organize {source.name}: destination exists ({destination})."
            )
        seen.add(asset_id)
        planned.append((source, asset_id, destination))

    completed: list[dict[str, Any]] = []
    for source, asset_id, destination in planned:
        staging = root / f".charctx-organize-{asset_id}"
        staged_source = staging / "source" / source.name
        before = _sha256(source)
        moved = False
        try:
            for name in ("source", "license", "inspection", "previews", "web"):
                (staging / name).mkdir(parents=True, exist_ok=False)
            metadata = AssetFrontMatter(
                id=asset_id,
                title=_title(asset_id),
                primary_file=f"source/{source.name}",
                tags=["western-dragon", source.suffix.lower().lstrip(".")],
            )
            _write_readme(staging, metadata)
            os.replace(source, staged_source)
            moved = True
            after = _sha256(staged_source)
            if before != after:
                raise ConfigError(
                    f"Hash changed while organizing {source.name}: {before} -> {after}"
                )
            os.replace(staging, destination)
            completed.append(
                {
                    "id": asset_id,
                    "source": str(destination / "source" / source.name),
                    "package": str(destination),
                    "sha256": after,
                }
            )
        except Exception:
            if moved and staged_source.is_file() and not source.exists():
                os.replace(staged_source, source)
            if staging.exists():
                shutil.rmtree(staging)
            raise
    return completed


def _package(project: Project, asset_id: str) -> tuple[Path, AssetFrontMatter]:
    root = _collected(project)
    if _slug(asset_id) != asset_id:
        raise ConfigError(f"Invalid asset id {asset_id!r}; expected a lowercase slug.")
    package = (root / asset_id).resolve()
    if not _inside(package, root) or not package.is_dir():
        raise ConfigError(f"Unknown collected asset {asset_id!r} under {root}.")
    metadata, _ = read_front_matter(package / "README.md")
    if metadata.id != asset_id:
        raise ConfigError(
            f"Package directory {asset_id!r} disagrees with README id {metadata.id!r}."
        )
    return package, metadata


def _source_inventory(package: Path) -> list[AssetFileRecord]:
    source_root = package / "source"
    return [
        AssetFileRecord(
            path=path.relative_to(package).as_posix(),
            bytes=path.stat().st_size,
            sha256=_sha256(path),
        )
        for path in sorted(source_root.rglob("*"))
        if path.is_file()
    ]


def _safe_member_target(root: Path, member: str) -> Path:
    normalized = member.replace("\\", "/")
    if normalized.startswith("/") or re.match(r"^[A-Za-z]:", normalized):
        raise ConfigError(f"Archive member has an absolute path: {member!r}")
    target = (root / normalized).resolve()
    if not _inside(target, root):
        raise ConfigError(f"Archive member escapes extraction root: {member!r}")
    return target


def _extract_zip(path: Path, destination: Path, *, depth: int = 0) -> None:
    if depth > 3:
        raise ConfigError(f"Nested archive depth exceeds 3 at {path.name}.")
    with zipfile.ZipFile(path) as archive:
        members = archive.infolist()
        expanded = sum(member.file_size for member in members)
        if len(members) > MAX_ARCHIVE_MEMBERS or expanded > MAX_ARCHIVE_EXPANDED_BYTES:
            raise ConfigError(
                f"Archive {path.name} is too large to inspect safely "
                f"({len(members)} members, {expanded} expanded bytes)."
            )
        for member in members:
            target = _safe_member_target(destination, member.filename)
            if member.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as source, target.open("wb") as output:
                shutil.copyfileobj(source, output)
    nested = sorted(destination.rglob("*.zip"))
    for nested_zip in nested:
        nested_destination = nested_zip.with_suffix("")
        if nested_destination.exists():
            nested_destination = nested_zip.parent / f"{nested_zip.stem}-contents"
        nested_destination.mkdir(parents=True, exist_ok=False)
        _extract_zip(nested_zip, nested_destination, depth=depth + 1)


def _resolve_primary_model(primary: Path, staging: Path) -> tuple[Path, str]:
    if primary.suffix.lower() != ".zip":
        return primary, primary.name
    extract_root = staging / "extracted"
    extract_root.mkdir()
    _extract_zip(primary, extract_root)
    models = sorted(
        (
            path
            for path in extract_root.rglob("*")
            if path.suffix.lower() in MODEL_PRIORITY
        ),
        key=lambda path: (
            MODEL_PRIORITY[path.suffix.lower()],
            -path.stat().st_size,
            str(path),
        ),
    )
    if not models:
        raise ConfigError(f"No supported model found in archive {primary.name}.")
    selected = models[0]
    return selected, selected.relative_to(extract_root).as_posix()


def _atomic_copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp = destination.with_name(destination.name + ".tmp")
    shutil.copy2(source, temp)
    temp.replace(destination)


def _run_blender(
    asset_id: str,
    model: Path,
    output: Path,
    log: Path,
) -> dict[str, Any]:
    tool = artifacts.resolve("blender")
    if not tool.installed:
        raise ConfigError(
            "Blender is not provisioned. Run `charctx fetch blender` first."
        )
    script = Path(__file__).parent / "blender" / "build_asset.py"
    if not script.is_file():
        raise ConfigError(f"Missing Blender asset script: {script}")
    args = [str(tool.executable), "--background", "--disable-autoexec"]
    if model.suffix.lower() == ".blend":
        args.append(str(model))
    else:
        args.append("--factory-startup")
    args += [
        "--python",
        str(script),
        "--",
        "--asset-id",
        asset_id,
        "--output-dir",
        str(output),
    ]
    if model.suffix.lower() != ".blend":
        args += ["--source", str(model)]
    completed = subprocess.run(  # noqa: S603 - executable and script are pinned
        args,
        capture_output=True,
        text=True,
        timeout=600,
    )
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(
        "$ "
        + subprocess.list2cmdline(args)
        + "\n\n"
        + completed.stdout
        + "\n"
        + completed.stderr,
        encoding="utf-8",
    )
    if completed.returncode != 0:
        raise ConfigError(
            f"Blender build failed for {asset_id} (exit {completed.returncode}); "
            f"see {log}."
        )
    report = output / "report.json"
    if not report.is_file():
        raise ConfigError(f"Blender produced no report for {asset_id}; see {log}.")
    return json.loads(report.read_text(encoding="utf-8"))


def build_asset(project: Project, asset_id: str) -> dict[str, Any]:
    package, metadata = _package(project, asset_id)
    if metadata.kind != "donor":
        raise ConfigError(
            f"Asset {asset_id!r} is a reference-image package and has no 3D build."
        )
    primary = (package / metadata.primary_file).resolve()
    if not _inside(primary, package / "source") or not primary.is_file():
        raise ConfigError(
            f"Invalid or missing primary source for {asset_id}: {primary}"
        )
    previous = _inspection(package)
    if previous is not None:
        for record in previous.source_files:
            recorded = (package / record.path).resolve()
            if (
                not _inside(recorded, package / "source")
                or not recorded.is_file()
                or _sha256(recorded) != record.sha256
            ):
                raise ConfigError(
                    f"Source changed since the last inspection: {record.path}. "
                    "Refusing to replace derived outputs."
                )
    ensure_cache_layout()
    SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
    log = REPORTS_DIR / f"assets-{asset_id}.log"
    with tempfile.TemporaryDirectory(
        prefix=f"asset-{asset_id}-", dir=SCRATCH_DIR
    ) as temp:
        staging = Path(temp)
        blender_output = staging / "blender-output"
        blender_output.mkdir()
        model, model_label = _resolve_primary_model(primary, staging)
        raw = _run_blender(asset_id, model, blender_output, log)
        glb = blender_output / "model.glb"
        if not glb.is_file():
            raise ConfigError(f"Blender produced no GLB for {asset_id}; see {log}.")
        measurements = mesh_report.measure(glb, request_name=asset_id)
        raw.update(
            {
                "schema": "charctx.inspection/v1",
                "asset_id": asset_id,
                "primary_model": model_label,
                "source_files": [
                    record.model_dump(mode="json")
                    for record in _source_inventory(package)
                ],
                "web_measurements": json.loads(measurements.model_dump_json()),
            }
        )
        inspection = AssetInspection.model_validate(raw)
        report_path = staging / "report.final.json"
        report_path.write_text(
            inspection.model_dump_json(indent=2, by_alias=True), encoding="utf-8"
        )
        generated = [glb, report_path]
        for name in PREVIEW_NAMES:
            preview = blender_output / "previews" / f"{name}.webp"
            if not preview.is_file() or preview.stat().st_size == 0:
                raise ConfigError(f"Blender produced no {name} preview for {asset_id}.")
            generated.append(preview)
        recipe = {
            "schema": "charctx.recipe/v1",
            "asset_id": asset_id,
            "source_sha256": _sha256(primary),
            "source_primary": metadata.primary_file,
            "selected_model": model_label,
            "blender_version": inspection.blender_version,
            "views": list(PREVIEW_NAMES),
            "resolution": 1024,
            "outputs": {
                path.relative_to(staging).as_posix(): {
                    "bytes": path.stat().st_size,
                    "sha256": _sha256(path),
                }
                for path in generated
            },
        }
        recipe_path = staging / "recipe.json"
        recipe_path.write_text(json.dumps(recipe, indent=2), encoding="utf-8")

        _atomic_copy(glb, package / "web" / "model.glb")
        for name in PREVIEW_NAMES:
            _atomic_copy(
                blender_output / "previews" / f"{name}.webp",
                package / "previews" / f"{name}.webp",
            )
        _atomic_copy(report_path, package / "inspection" / "report.json")
        _atomic_copy(recipe_path, package / "inspection" / "recipe.json")
    _write_readme(package, metadata, inspection)
    return {
        "id": asset_id,
        "package": str(package),
        "report": str(package / "inspection" / "report.json"),
        "recipe": str(package / "inspection" / "recipe.json"),
        "web_model": str(package / "web" / "model.glb"),
        "previews": [
            str(package / "previews" / f"{name}.webp") for name in PREVIEW_NAMES
        ],
        "warnings": inspection.warnings,
        "log": str(log),
    }


def build(project: Project, asset_id: str | None = None) -> list[dict[str, Any]]:
    ids = (
        [asset_id]
        if asset_id
        else [item.id for item in list_assets(project) if item.kind == "donor"]
    )
    if not ids:
        raise ConfigError(
            f"No buildable 3D donor packages under {_collected(project)}."
        )
    return [build_asset(project, current) for current in ids]


def _generation_records(
    project: Project, metadata: AssetFrontMatter
) -> list[dict[str, Any]]:
    from . import generations

    return [
        record.model_dump(mode="json", by_alias=True)
        for record in generations.discover(
            project, metadata.generation_names, metadata.id
        )
    ]


def _card(
    package: Path,
    metadata: AssetFrontMatter,
    *,
    generation_count: int = 0,
) -> AssetCard:
    inspection = _inspection(package)
    warnings: list[str] = []
    if metadata.provenance_status == "incomplete":
        warnings.append("Provenance incomplete — private local workspace use only.")
    if inspection:
        warnings.extend(inspection.warnings)
    meshes = inspection.meshes if inspection else []
    armatures = inspection.armatures if inspection else []
    actions = inspection.actions if inspection else []
    source_formats = sorted(
        {
            path.suffix.lower().lstrip(".")
            for path in (package / "source").rglob("*")
            if path.is_file()
        }
    )
    cover = package / metadata.cover
    model = package / metadata.web_model
    previews = [
        f"previews/{name}.webp"
        for name in PREVIEW_NAMES
        if (package / "previews" / f"{name}.webp").is_file()
    ]
    return AssetCard(
        id=metadata.id,
        title=metadata.title,
        kind=metadata.kind,
        status=metadata.status,
        provenance_status=metadata.provenance_status,
        family=metadata.family,
        tags=metadata.tags,
        package_dir=str(package),
        primary_file=metadata.primary_file,
        source_formats=source_formats,
        rigged=bool(armatures),
        animated=bool(actions),
        bones=sum(int(item.get("bones", 0)) for item in armatures),
        actions=len(actions),
        vertices=sum(int(item.get("vertices", 0)) for item in meshes),
        polygons=sum(int(item.get("polygons", 0)) for item in meshes),
        cover=metadata.cover if cover.is_file() else None,
        web_model=metadata.web_model if model.is_file() else None,
        previews=previews,
        generations=generation_count,
        warnings=warnings,
    )


def list_assets(project: Project) -> list[AssetCard]:
    root = _collected(project)
    cards: list[AssetCard] = []
    for package in sorted(path for path in root.iterdir() if path.is_dir()):
        readme = package / "README.md"
        if not readme.is_file():
            continue
        metadata, _ = read_front_matter(readme)
        generation_count = len(_generation_records(project, metadata))
        cards.append(_card(package, metadata, generation_count=generation_count))
    return cards


def show_asset(project: Project, asset_id: str) -> dict[str, Any]:
    package, metadata = _package(project, asset_id)
    inspection = _inspection(package)
    generations = _generation_records(project, metadata)
    card = _card(package, metadata, generation_count=len(generations))
    return {
        "card": card.model_dump(mode="json"),
        "metadata": metadata.model_dump(mode="json", by_alias=True),
        "inspection": inspection.model_dump(mode="json", by_alias=True)
        if inspection
        else None,
        "generations": generations,
    }


def validate(project: Project, asset_id: str | None = None) -> list[dict[str, Any]]:
    if asset_id:
        package, metadata = _package(project, asset_id)
        count = len(_generation_records(project, metadata))
        cards: list[AssetCard | None] = [
            _card(package, metadata, generation_count=count)
        ]
    else:
        cards = list(list_assets(project))
    results: list[dict[str, Any]] = []
    for card in cards:
        assert card is not None
        package, metadata = _package(project, card.id)
        errors: list[str] = []
        primary = (package / metadata.primary_file).resolve()
        if not _inside(primary, package / "source") or not primary.is_file():
            errors.append("primary source is missing or escapes source/")
        inspection = _inspection(package)
        if metadata.kind == "reference":
            for name in PREVIEW_NAMES:
                relative = f"previews/{name}.webp"
                path = (package / relative).resolve()
                if not _inside(path, package / "previews") or not path.is_file():
                    errors.append(f"reference preview missing: {relative}")
        elif inspection:
            for record in inspection.source_files:
                path = (package / record.path).resolve()
                if not _inside(path, package / "source") or not path.is_file():
                    errors.append(f"recorded source missing: {record.path}")
                elif _sha256(path) != record.sha256:
                    errors.append(f"source hash mismatch: {record.path}")
            for relative in [metadata.cover, metadata.web_model]:
                path = (package / relative).resolve()
                if not _inside(path, package) or not path.is_file():
                    errors.append(f"derived output missing: {relative}")
        else:
            errors.append("asset has not been built")
        results.append({"id": card.id, "valid": not errors, "errors": errors})
    return results
