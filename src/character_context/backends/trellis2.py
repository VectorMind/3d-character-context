"""Microsoft TRELLIS.2 image-to-3D, through its public Hugging Face Space.

Hugging Face's serverless inference API serves no `image-to-3d` model at all,
so a Gradio Space is the only free path to this model. The Space is
session-stateful: `/image_to_3d` generates into the session and `/extract_glb`
pulls the mesh out of it, so both calls must share one client.

Everything Gradio-shaped stays inside this module. Callers see a
`RawCharacterResult` and nothing else.
"""

from __future__ import annotations

import json
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from ..config import backend_config, credential
from ..contracts import GenerationRequest, RawCharacterResult
from ..project import Project

#: Shared ZeroGPU hardware queues; a cold Space can take minutes to answer.
HTTPX_TIMEOUT = 300
CONNECT_ATTEMPTS = 3
CONNECT_BACKOFF_S = 3


class BackendError(RuntimeError):
    """The provider refused or failed the request."""


class QuotaExhausted(BackendError):
    """The free GPU budget for the account is spent.

    Each call reserves a fixed slice of a small daily budget up front, so this
    is raised before any GPU work happens - no result is lost, and nothing was
    charged.
    """


def _client(space: str, token: str):
    """Connect to the Space, retrying the handshake on a cold-start timeout."""
    from gradio_client import Client

    last: Exception | None = None
    for attempt in range(CONNECT_ATTEMPTS):
        try:
            return Client(
                space,
                token=token,
                verbose=False,
                httpx_kwargs={"timeout": HTTPX_TIMEOUT},
            )
        except Exception as exc:
            last = exc
            if attempt + 1 < CONNECT_ATTEMPTS:
                time.sleep(CONNECT_BACKOFF_S)
    raise BackendError(f"Could not connect to Space {space!r}: {last!r}") from last


def _api_surface(client) -> dict[str, dict[str, Any]]:
    """The Space's declared endpoints, with each parameter's default."""
    info = client.view_api(return_format="dict", print_info=False)
    surface: dict[str, dict[str, Any]] = {}
    for name, endpoint in (info.get("named_endpoints") or {}).items():
        params: list[str] = []
        defaults: dict[str, Any] = {}
        for param in endpoint.get("parameters", []):
            key = param.get("parameter_name") or param.get("label")
            params.append(key)
            if param.get("parameter_has_default"):
                defaults[key] = param.get("parameter_default")
        surface[name] = {"params": params, "defaults": defaults}
    return surface


def _full_kwargs(endpoint: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    """Send every declared parameter, defaults included.

    This Space rejects a partial parameter list with an opaque upstream error,
    so defaults are read from its own API description and sent explicitly
    rather than hardcoded here - the Space stays free to change them.
    """
    kwargs: dict[str, Any] = {}
    for name in endpoint["params"]:
        if name in overrides:
            kwargs[name] = overrides[name]
        elif name in endpoint["defaults"]:
            kwargs[name] = endpoint["defaults"][name]
    return kwargs


def _call(client, api_name: str, **kwargs):
    """One Gradio call, with provider errors translated at the boundary."""
    try:
        return client.predict(api_name=api_name, **kwargs)
    except Exception as exc:
        message = str(exc)
        if "ZeroGPU quota" in message:
            raise QuotaExhausted(message) from exc
        raise BackendError(f"{api_name} failed: {message}") from exc


def _first_glb(result: Any) -> Path | None:
    """Find the GLB in whatever shape the endpoint returned."""
    found: list[str] = []

    def walk(value: Any) -> None:
        if isinstance(value, (list, tuple)):
            for item in value:
                walk(item)
        elif isinstance(value, dict):
            for item in value.values():
                walk(item)
        elif isinstance(value, str):
            found.append(value)

    walk(result)
    for value in found:
        if value.lower().endswith(".glb") and Path(value).is_file():
            return Path(value)
    return None


def _adopt(source: Path, slot: Path, name: str) -> Path:
    """Copy a provider file into the run slot atomically.

    The project folder may be cloud-synced: write to a temp name and rename,
    so a sync client never uploads a half-written mesh.
    """
    target = slot / name
    temp = target.with_name(target.name + ".part")
    shutil.copyfile(source, temp)
    temp.replace(target)
    return target


def _discard_if_empty(slot: Path) -> None:
    """Remove a run slot that never received an artifact."""
    try:
        if slot.is_dir() and not any(slot.iterdir()):
            slot.rmdir()
    except OSError:  # never let cleanup mask the real failure
        pass


def describe() -> dict[str, Any]:
    """Static description of this backend. Makes no network call."""
    name, config = backend_config("trellis2")
    return {
        "backend": name,
        "provider": config["provider"],
        "space": config["space"],
        "call_shape": config["call_shape"],
        "credential": config["credential"],
        "credentialed": credential(config["credential"], required=False) is not None,
    }


def generate(
    request: GenerationRequest,
    project: Project,
    *,
    on_event: Any = None,
) -> RawCharacterResult:
    """Run one generation and land its artifacts in a fresh run slot.

    The slot is created before the call and never reused, so a result can
    always be traced back to the request that paid for it.
    """
    backend, config = backend_config(request.backend)
    space = config["space"]
    token = credential(config["credential"])
    endpoints = config.get("endpoints", {})
    configured_options = dict(config.get("options") or {})

    def event(message: str) -> None:
        if on_event:
            on_event(message)

    event(f"connecting to {space}")
    client = _client(space, token)
    surface = _api_surface(client)

    missing = [
        api for api in endpoints.values() if api and api not in surface
    ]
    if missing:
        raise BackendError(
            f"Space {space!r} no longer exposes {', '.join(missing)}. "
            f"Its current endpoints are: {', '.join(sorted(surface))}. "
            "Update config/providers.yaml to the Space's current API."
        )

    from gradio_client import handle_file

    slot = project.run_slot(backend, request.name)
    started = datetime.now()
    start_perf = time.perf_counter()

    try:
        # Session first: /extract_glb reads what /image_to_3d left behind.
        if endpoints.get("session"):
            _call(client, endpoints["session"])

        image = handle_file(str(request.images[0]))
        if endpoints.get("preprocess"):
            event("preprocessing reference image")
            preprocessed = _call(
                client,
                endpoints["preprocess"],
                **_full_kwargs(surface[endpoints["preprocess"]], {"input": image}),
            )
            image = handle_file(
                preprocessed["path"] if isinstance(preprocessed, dict) else preprocessed
            )

        # Options precedence: config defaults, then per-request overrides.
        overrides: dict[str, Any] = {
            "image": image,
            "seed": request.seed,
            **configured_options,
            **request.options,
        }

        event("generating 3D asset (reserves GPU quota)")
        generate_kwargs = _full_kwargs(surface[endpoints["generate"]], overrides)
        _call(client, endpoints["generate"], **generate_kwargs)

        event("extracting GLB")
        extract_kwargs = _full_kwargs(surface[endpoints["extract"]], overrides)
        extracted = _call(client, endpoints["extract"], **extract_kwargs)
    except Exception:
        # Append-only protects results, not empty folders: a run that brought
        # nothing back leaves no slot behind to be mistaken for one that did.
        _discard_if_empty(slot)
        raise

    completed = datetime.now()
    duration = round(time.perf_counter() - start_perf, 2)

    glb = _first_glb(extracted)
    if glb is None:
        raise BackendError(
            f"{endpoints['extract']} returned no GLB file. Payload: {extracted!r}"
        )

    mesh = _adopt(glb, slot, f"{request.name}.glb")

    # Keep the run self-contained: the reference image travels with the result.
    extras: list[Path] = []
    for index, source in enumerate(request.images):
        suffix = source.suffix.lower()
        label = "reference" if len(request.images) == 1 else f"reference-{index + 1}"
        extras.append(_adopt(source, slot, f"{label}{suffix}"))

    metadata = {
        "backend": backend,
        "provider": config["provider"],
        "space": space,
        "call_shape": config.get("call_shape"),
        "request": json.loads(request.model_dump_json()),
        "resolved_options": {
            key: value
            for key, value in generate_kwargs.items()
            if not isinstance(value, (dict, list))
        },
        "extract_options": {
            key: value
            for key, value in extract_kwargs.items()
            if not isinstance(value, (dict, list))
        },
        "started_at": started.isoformat(timespec="seconds"),
        "completed_at": completed.isoformat(timespec="seconds"),
        "duration_s": duration,
        "artifacts": [mesh.name, *[p.name for p in extras]],
    }
    temp = slot / "request.json.part"
    temp.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    temp.replace(slot / "request.json")

    return RawCharacterResult(
        request=request,
        backend=backend,
        provider=config["provider"],
        endpoint=space,
        mesh=mesh,
        extra_artifacts=extras,
        run_dir=slot,
        job_id=None,
        started_at=started,
        completed_at=completed,
        duration_s=duration,
    )
