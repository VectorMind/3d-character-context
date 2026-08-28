"""Normalized discovery and viewer preparation for append-only generations."""

from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path
from typing import Any

from .asset_models import GenerationManifest, GenerationRecord
from .config import ConfigError
from .paths import REPORTS_DIR, SCRATCH_DIR, ensure_cache_layout
from .project import Project

VIEWER_FILE = "viewer.json"
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
RUN_PART = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
PIPELINE_STAGES = (
    "references",
    "generation",
    "canonicalization",
    "skeleton",
    "rigging",
    "poses",
)
VIEW_NAMES = ("hero", "front", "left", "rear", "top")


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def _sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ConfigError(f"Invalid JSON file {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ConfigError(f"Expected a JSON object in {path}.")
    return value


def _relative_file(run: Path, relative: str) -> Path:
    path = (run / relative).resolve()
    if not _inside(path, run) or not path.is_file():
        raise ConfigError(
            f"Generation artifact is missing or escapes its run: {relative}"
        )
    return path


def _request_name(request: dict[str, Any]) -> str:
    nested = request.get("request") or {}
    name = nested.get("name")
    if not isinstance(name, str) or not name:
        raise ConfigError("Generation request.json has no request.name.")
    return name


def _model_relative(run: Path, request: dict[str, Any]) -> str:
    declared = request.get("artifacts") or []
    for value in declared:
        if isinstance(value, str) and Path(value).suffix.lower() in {".glb", ".gltf"}:
            _relative_file(run, value)
            return Path(value).as_posix()
    models = sorted([*run.glob("*.glb"), *run.glob("*.gltf")])
    if not models:
        raise ConfigError(f"Generation run has no GLB/glTF model: {run}")
    return models[0].relative_to(run).as_posix()


def _input_files(run: Path, request: dict[str, Any]) -> list[str]:
    candidates: set[Path] = set()
    for value in request.get("artifacts") or []:
        if isinstance(value, str) and Path(value).suffix.lower() in IMAGE_SUFFIXES:
            candidates.add(_relative_file(run, value))
    candidates.update(
        path.resolve()
        for path in run.glob("reference*")
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    )
    supporting = run / "supporting-views"
    if supporting.is_dir():
        candidates.update(
            path.resolve()
            for path in supporting.iterdir()
            if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
        )
    return sorted(path.relative_to(run).as_posix() for path in candidates)


def _stage_states(run: Path, inputs: list[str]) -> dict[str, str]:
    markers = {
        "canonicalization": run / "canonical" / "manifest.json",
        "skeleton": run / "skeleton" / "manifest.json",
        "rigging": run / "rig" / "manifest.json",
        "poses": run / "poses" / "manifest.json",
    }
    states = {
        "references": "complete" if inputs else "missing",
        "generation": "complete",
    }
    states.update(
        {
            name: "complete" if marker.is_file() else "not-started"
            for name, marker in markers.items()
        }
    )
    return {name: states[name] for name in PIPELINE_STAGES}


def derive_manifest(run: Path, character_id: str) -> GenerationManifest:
    """Derive a stable relative-path manifest from existing run contracts."""
    run = run.resolve()
    request_file = _relative_file(run, "request.json")
    request = _json(request_file)
    backend = request.get("backend")
    if not isinstance(backend, str) or not backend:
        backend = run.parent.name
    model_relative = _model_relative(run, request)
    model = _relative_file(run, model_relative)
    measurements_path = run / f"{model.stem}.measurements.json"
    measurements = (
        measurements_path.relative_to(run).as_posix()
        if measurements_path.is_file()
        else None
    )
    inputs = _input_files(run, request)
    previews = [
        f"previews/{name}.webp"
        for name in VIEW_NAMES
        if (run / "previews" / f"{name}.webp").is_file()
    ]
    warnings: list[str] = []
    if measurements is None:
        warnings.append("No mesh measurement sidecar is present.")
    if not previews:
        warnings.append("No model-derived preview views are present.")
    nested = request.get("request") or {}
    return GenerationManifest(
        character_id=character_id,
        backend=backend,
        run=run.name,
        request_name=_request_name(request),
        seed=int(nested.get("seed") or 0),
        started_at=request.get("started_at"),
        completed_at=request.get("completed_at"),
        duration_s=request.get("duration_s"),
        model=model_relative,
        model_sha256=_sha256(model),
        measurements=measurements,
        inputs=inputs,
        previews=previews,
        stages=_stage_states(run, inputs),
        warnings=warnings,
    )


def write_manifest(run: Path, character_id: str) -> Path:
    """Write one generation viewer manifest atomically."""
    manifest = derive_manifest(run, character_id)
    target = run / VIEWER_FILE
    temp = target.with_suffix(".json.part")
    temp.write_text(
        manifest.model_dump_json(indent=2, by_alias=True) + "\n", encoding="utf-8"
    )
    temp.replace(target)
    return target


def _record(run: Path, character_id: str) -> GenerationRecord:
    manifest_path = run / VIEWER_FILE
    if manifest_path.is_file():
        manifest = GenerationManifest.model_validate_json(
            manifest_path.read_text(encoding="utf-8")
        )
    else:
        manifest = derive_manifest(run, character_id)
    if manifest.character_id != character_id:
        raise ConfigError(
            f"Generation {run.name} belongs to {manifest.character_id!r}, "
            f"not {character_id!r}."
        )
    _relative_file(run, manifest.model)
    for relative in [*manifest.inputs, *manifest.previews]:
        _relative_file(run, relative)
    metrics = None
    if manifest.measurements:
        metrics = _json(_relative_file(run, manifest.measurements))
    return GenerationRecord(
        **manifest.model_dump(mode="python", by_alias=False),
        run_dir=str(run),
        metrics=metrics,
    )


def discover(
    project: Project, request_names: list[str], character_id: str
) -> list[GenerationRecord]:
    """Return every generation whose request name is linked by the character."""
    if not request_names or not project.generated.is_dir():
        return []
    wanted = set(request_names)
    records: list[GenerationRecord] = []
    backends = sorted(
        path for path in project.generated.iterdir() if path.is_dir()
    )
    for backend in backends:
        for run in sorted(path for path in backend.iterdir() if path.is_dir()):
            request_path = run / "request.json"
            if not request_path.is_file():
                continue
            request = _json(request_path)
            if _request_name(request) not in wanted:
                continue
            records.append(_record(run, character_id))
    return records


def _resolve_run(project: Project, run_ref: str) -> tuple[str, Path]:
    normalized = run_ref.replace("\\", "/").strip("/")
    parts = normalized.split("/")
    if len(parts) != 2 or any(not RUN_PART.fullmatch(part) for part in parts):
        raise ConfigError("Run must be '<backend>/<run-folder>', using safe slugs.")
    backend, run_name = parts
    run = (project.generated / backend / run_name).resolve()
    if not _inside(run, project.generated) or not run.is_dir():
        raise ConfigError(
            f"Unknown generation run {run_ref!r} under {project.generated}."
        )
    return backend, run


def build_view(
    project: Project, run_ref: str, character_id: str | None = None
) -> dict[str, Any]:
    """Render neutral views and write viewer.json without changing the raw model."""
    from .assets import PREVIEW_NAMES, _atomic_copy, _run_blender

    ensure_cache_layout()
    SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
    backend, run = _resolve_run(project, run_ref)
    request = _json(_relative_file(run, "request.json"))
    character_id = character_id or _request_name(request)
    model_relative = _model_relative(run, request)
    model = _relative_file(run, model_relative)
    before = _sha256(model)
    log = REPORTS_DIR / f"generation-view-{backend}-{run.name}.log"
    with tempfile.TemporaryDirectory(
        prefix=f"generation-view-{run.name}-", dir=SCRATCH_DIR
    ) as temp:
        output = Path(temp) / "blender-output"
        output.mkdir()
        _run_blender(f"{backend}-{run.name}", model, output, log)
        for name in PREVIEW_NAMES:
            preview = output / "previews" / f"{name}.webp"
            if not preview.is_file() or preview.stat().st_size == 0:
                raise ConfigError(f"Blender produced no {name} preview for {run_ref}.")
            _atomic_copy(preview, run / "previews" / f"{name}.webp")
    after = _sha256(model)
    if before != after:
        raise ConfigError(
            f"Generation model changed while building views: {before} -> {after}"
        )
    manifest_path = write_manifest(run, character_id)
    manifest = GenerationManifest.model_validate_json(
        manifest_path.read_text(encoding="utf-8")
    )
    return {
        "character_id": character_id,
        "run": f"{backend}/{run.name}",
        "run_dir": str(run),
        "model": str(model),
        "model_sha256": after,
        "manifest": str(manifest_path),
        "previews": [str(run / path) for path in manifest.previews],
        "log": str(log),
    }
