# /// script
# requires-python = ">=3.11,<3.13"
# dependencies = [
#   "gradio_client>=1.7",
#   "requests>=2.32",
#   "trimesh>=4.4",
#   "numpy>=1.26",
#   "scipy>=1.13",
#   "networkx>=3.3",
# ]
# ///
"""Phase 1 / OP-011 - TRELLIS hello world: one image in, one GLB out.

The REST inference API serves no `image-to-3d` model (proven by
`hf_01_hello_inference.py`), so the free path to TRELLIS is a Gradio Space
driven with `gradio_client` and the workspace `HF_TOKEN`. This script:

1. reports the runtime stage of every candidate TRELLIS Space (which of them
   are actually up right now);
2. downloads a hello-world reference image (a Space example asset);
3. connects to the first usable Space and records its real API surface;
4. runs the simplest image-to-3d call it exposes and downloads the GLB;
5. proves the artifact by re-loading it with trimesh and measuring it.

Every candidate Space that is up is exercised, so the report carries a
per-path finding rather than only the first success.

Usage:

    uv run --script experiments/hf_02_trellis_space.py
    uv run --script experiments/hf_02_trellis_space.py --space microsoft/TRELLIS.2
    uv run --script experiments/hf_02_trellis_space.py --image path/to/ref.png
    uv run --script experiments/hf_02_trellis_space.py --first-success
    uv run --script experiments/hf_02_trellis_space.py --probe-only

Writes `.cache/results/<date>/<time>-trellis-hello-world/`.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import Report, load_dotenv, mask, require_env  # noqa: E402

HUB = "https://huggingface.co"
TIMEOUT = 60
# Spaces on shared ZeroGPU hardware queue: give the HTTP client room, and
# retry the handshake, which times out on a cold Space.
SPACE_HTTPX = {"timeout": 300}
CONNECT_ATTEMPTS = 3

# Candidate TRELLIS Spaces, simplest usable API first. The official
# `microsoft/TRELLIS` Space is included so its state is recorded even when it
# is down.
CANDIDATE_SPACES = [
    "trellis-community/TRELLIS",
    "microsoft/TRELLIS.2",
    "microsoft/TRELLIS",
]

# Hello-world input: an example asset shipped by the TRELLIS Space itself,
# and a dragon - the character family this repository targets.
HELLO_IMAGE = (
    "trellis-community/TRELLIS",
    "assets/example_image/typical_creature_dragon.png",
)

# Generation knobs kept deliberately low: this is an access probe, not a
# quality run. Fewer sampling steps means less ZeroGPU quota burnt.
FAST_OPTIONS = {
    "seed": 42,
    "ss_sampling_steps": 12,
    "slat_sampling_steps": 12,
    "mesh_simplify": 0.95,
    "texture_size": 1024,
}


def space_runtime(space_id: str, headers: dict) -> dict:
    """Runtime facts for one Space: stage, hardware, host."""
    try:
        response = requests.get(
            f"{HUB}/api/spaces/{space_id}", headers=headers, timeout=TIMEOUT
        )
    except Exception as exc:
        return {"id": space_id, "error": repr(exc)}
    if response.status_code != 200:
        return {"id": space_id, "status": response.status_code}
    data = response.json()
    runtime = data.get("runtime") or {}
    return {
        "id": space_id,
        "status": 200,
        "stage": runtime.get("stage"),
        "hardware": (runtime.get("hardware") or {}).get("current"),
        "sdk": data.get("sdk"),
        "likes": data.get("likes"),
        "host": data.get("host"),
    }


def download_example_image(dest: Path, headers: dict) -> tuple[Path, str]:
    """Fetch the hello-world reference image from the Space repository."""
    space_id, rel = HELLO_IMAGE
    url = f"{HUB}/spaces/{space_id}/resolve/main/{rel}"
    response = requests.get(url, headers=headers, timeout=TIMEOUT)
    response.raise_for_status()
    path = dest / Path(rel).name
    path.write_bytes(response.content)
    return path, url


def summarize_api(client) -> dict:
    """Named endpoints of a Space with their parameter names and defaults."""
    info = client.view_api(return_format="dict", print_info=False)
    endpoints = {}
    for name, endpoint in (info.get("named_endpoints") or {}).items():
        params = [
            p.get("parameter_name") or p.get("label")
            for p in endpoint.get("parameters", [])
        ]
        defaults = {
            (p.get("parameter_name") or p.get("label")): p.get("parameter_default")
            for p in endpoint.get("parameters", [])
            if p.get("parameter_has_default")
        }
        endpoints[name] = {
            "params": params,
            "defaults": defaults,
            "returns": [r.get("label") for r in endpoint.get("returns", [])],
        }
    return endpoints


def build_kwargs(endpoint: dict, overrides: dict) -> dict:
    """Fill every declared parameter, defaults included.

    `microsoft/TRELLIS.2` raises an opaque upstream `AppError` when its
    `/image_to_3d` endpoint is called with only a subset of its parameters,
    so partial calls are never made: declared defaults are sent explicitly.
    """
    kwargs: dict = {}
    for name in endpoint["params"]:
        if name in overrides:
            kwargs[name] = overrides[name]
        elif name in endpoint["defaults"]:
            kwargs[name] = endpoint["defaults"][name]
    return kwargs


def connect(space_id: str, token: str):
    """Connect to a Space, retrying the handshake on a cold-start timeout."""
    from gradio_client import Client

    last: Exception | None = None
    for attempt in range(CONNECT_ATTEMPTS):
        try:
            return Client(
                space_id, token=token, verbose=False, httpx_kwargs=SPACE_HTTPX
            ), attempt
        except Exception as exc:
            last = exc
            time.sleep(3)
    raise last  # type: ignore[misc]


def pick_glb(result) -> Path | None:
    """Find the GLB path in whatever shape the endpoint returned."""
    candidates: list = []

    def walk(value):
        if isinstance(value, (list, tuple)):
            for item in value:
                walk(item)
        elif isinstance(value, dict):
            for item in value.values():
                walk(item)
        elif isinstance(value, str):
            candidates.append(value)

    walk(result)
    for value in candidates:
        if value.lower().endswith(".glb") and Path(value).is_file():
            return Path(value)
    return None


def generate(client, endpoints: dict, image_path: Path, rep: Report):
    """Run the simplest image-to-3d call the Space exposes."""
    from gradio_client import handle_file

    if "/start_session" in endpoints:
        try:
            client.predict(api_name="/start_session")
            rep.probe("start_session", ok=True)
        except Exception as exc:
            rep.probe("start_session", ok=False, error=repr(exc))

    handle = handle_file(str(image_path))

    def loggable(kwargs: dict) -> str:
        return json.dumps(
            {
                key: ("<file>" if isinstance(value, (dict, list)) else value)
                for key, value in kwargs.items()
            }
        )

    # Shape A - community Space: one call, image in, GLB out.
    if "/generate_and_extract_glb" in endpoints:
        endpoint = endpoints["/generate_and_extract_glb"]
        kwargs = build_kwargs(endpoint, {"image": handle, **FAST_OPTIONS})
        rep.p(f"Call: `/generate_and_extract_glb` with `{loggable(kwargs)}`")
        start = time.perf_counter()
        result = client.predict(api_name="/generate_and_extract_glb", **kwargs)
        elapsed = round(time.perf_counter() - start, 1)
        return result, elapsed, "/generate_and_extract_glb"

    # Shape B - official TRELLIS.2: preprocess, image_to_3d (session state),
    # then extract_glb.
    if "/image_to_3d" in endpoints and "/extract_glb" in endpoints:
        if "/preprocess_image" in endpoints:
            key = endpoints["/preprocess_image"]["params"][0] or "input"
            preprocessed = client.predict(**{key: handle}, api_name="/preprocess_image")
            rep.probe("preprocess_image", ok=True)
            handle = handle_file(
                preprocessed["path"] if isinstance(preprocessed, dict) else preprocessed
            )
        kwargs = build_kwargs(
            endpoints["/image_to_3d"], {"image": handle, **FAST_OPTIONS}
        )
        rep.p(
            "Call: `/image_to_3d` then `/extract_glb` (session-stateful Space) "
            f"with `{loggable(kwargs)}`"
        )
        start = time.perf_counter()
        client.predict(api_name="/image_to_3d", **kwargs)
        extract = build_kwargs(endpoints["/extract_glb"], {"texture_size": 1024})
        result = client.predict(api_name="/extract_glb", **extract)
        elapsed = round(time.perf_counter() - start, 1)
        return result, elapsed, "/image_to_3d+/extract_glb"

    raise RuntimeError(
        f"No known image-to-3d endpoint on this Space; saw: {sorted(endpoints)}"
    )


def _components(mesh) -> int | str:
    """Connected-component count; needs a graph engine (scipy) in trimesh."""
    try:
        return int(len(mesh.split(only_watertight=False)))
    except Exception as exc:  # missing graph engine must not lose the run
        return f"unavailable: {exc}"


def measure(glb_path: Path) -> dict:
    """Re-load the artifact and measure it - proof by measurement, not looks."""
    import numpy as np
    import trimesh

    scene = trimesh.load(str(glb_path), force="scene")
    meshes = [g for g in scene.geometry.values() if hasattr(g, "faces")]
    combined = trimesh.util.concatenate(meshes) if meshes else None
    if combined is None:
        return {"error": "no mesh geometry in file"}
    bounds = combined.bounds
    return {
        "file": glb_path.name,
        "file_size_bytes": glb_path.stat().st_size,
        "geometries": len(scene.geometry),
        "vertices": int(len(combined.vertices)),
        "faces": int(len(combined.faces)),
        "bounds_min": [round(float(v), 4) for v in bounds[0]],
        "bounds_max": [round(float(v), 4) for v in bounds[1]],
        "extents": [round(float(v), 4) for v in combined.extents],
        "surface_area": round(float(combined.area), 4),
        "volume": round(float(combined.volume), 4),
        "watertight": bool(combined.is_watertight),
        "connected_components": _components(combined),
        "all_finite": bool(np.isfinite(combined.vertices).all()),
        "has_texture": any(
            getattr(getattr(g, "visual", None), "material", None) is not None
            for g in meshes
        ),
    }


def measure_only(targets: list[Path]) -> int:
    """Re-measure GLB files already on disk - no Space call, no quota."""
    files: list[Path] = []
    for target in targets:
        if target.is_dir():
            files.extend(sorted(target.glob("*.glb")))
        elif target.is_file():
            files.append(target)
    if not files:
        print("No GLB files found in the given targets.")
        return 1

    rep = Report("trellis-remeasure", "TRELLIS Artifacts - Re-measurement")
    rep.p("Offline re-measurement of GLB artifacts already downloaded.")
    for path in files:
        rep.h2(f"`{path.name}`")
        metrics = measure(path)
        metrics["source_path"] = str(path)
        rep.data.setdefault("measurements", {})[path.name] = metrics
        rep.probe("measure", file=path.name, vertices=metrics.get("vertices"))
        rep.table(["Metric", "Value"], [[k, str(v)] for k, v in metrics.items()])
        (path.parent / f"{path.stem}.measurements.json").write_text(
            json.dumps(metrics, indent=2) + "\n", encoding="utf-8"
        )
    rep.write()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--space", help="Space id to use (default: first usable)")
    parser.add_argument(
        "--image", type=Path, help="reference image (default: Space example dragon)"
    )
    parser.add_argument("--probe-only", action="store_true", help="skip generation")
    parser.add_argument(
        "--measure",
        type=Path,
        nargs="+",
        help="re-measure existing GLB files (or folders of them) and exit; "
        "costs no GPU quota",
    )
    parser.add_argument(
        "--first-success",
        action="store_true",
        help="stop after the first Space that returns a GLB (default: try all)",
    )
    args = parser.parse_args()

    if args.measure:
        return measure_only(args.measure)

    load_dotenv()
    token = require_env("HF_TOKEN")
    headers = {"Authorization": f"Bearer {token}"}

    rep = Report(
        "trellis-hello-world", "TRELLIS Hello World - Space Access And GLB Proof"
    )
    rep.data["token"] = mask(token)
    rep.p(
        "Free-access experiment (plan Phase 1, OP-011): drive TRELLIS through "
        "its public Gradio Space with the workspace token and bring back one "
        "measurable GLB."
    )

    # --- 1. which Spaces are up --------------------------------------
    rep.h2("1. Candidate TRELLIS Spaces - runtime stage")
    spaces = [space_runtime(sid, headers) for sid in CANDIDATE_SPACES]
    rep.data["spaces"] = spaces
    for entry in spaces:
        rep.probe("space_runtime", **entry)
    rep.table(
        ["Space", "Stage", "Hardware", "Likes", "Host"],
        [
            [
                f"`{s['id']}`",
                str(s.get("stage") or s.get("error") or s.get("status")),
                str(s.get("hardware")),
                str(s.get("likes")),
                f"`{s.get('host')}`" if s.get("host") else "-",
            ]
            for s in spaces
        ],
    )
    running = [s["id"] for s in spaces if s.get("stage") == "RUNNING"]
    rep.p(f"Running now: {', '.join(f'`{s}`' for s in running) or 'none'}.")

    order = (
        [args.space] if args.space else [s for s in CANDIDATE_SPACES if s in running]
    )
    if not order:
        rep.p("**No candidate Space is running** - nothing to call.")
        rep.write()
        return 1

    # --- 2. hello-world input image ----------------------------------
    rep.h2("2. Hello-world reference image")
    if args.image:
        image_path = args.image.resolve()
        source = f"local file `{image_path}`"
    else:
        image_path, url = download_example_image(rep.dir, headers)
        source = f"Space example asset `{url}`"
    rep.p(
        f"Input: {source} -> `{image_path.name}` "
        f"({image_path.stat().st_size:,} bytes), copied into the results folder."
    )
    rep.data["input_image"] = str(image_path)

    if args.probe_only:
        rep.p("`--probe-only` given: stopping before any generation call.")
        rep.write()
        return 0

    # --- 3/4/5. connect, inspect, generate, measure --------------------
    succeeded: list[str] = []
    step = 3
    for space_id in order:
        slug = space_id.replace("/", "-")
        rep.h2(f"{step}. `{space_id}` - API surface")
        step += 1
        try:
            connect_start = time.perf_counter()
            client, retries = connect(space_id, token)
            connect_s = round(time.perf_counter() - connect_start, 2)
            endpoints = summarize_api(client)
            rep.probe(
                "connect", space=space_id, ok=True, latency_s=connect_s,
                retries=retries, endpoints=len(endpoints),
            )
            rep.p(
                f"Connected in {connect_s}s"
                + (f" after {retries} retried handshake(s)" if retries else "")
                + ". Named endpoints:"
            )
            rep.table(
                ["Endpoint", "Parameters", "Returns"],
                [
                    [
                        f"`{name}`",
                        ", ".join(f"`{p}`" for p in ep["params"]) or "-",
                        ", ".join(str(r) for r in ep["returns"]) or "-",
                    ]
                    for name, ep in endpoints.items()
                ],
            )
            rep.data.setdefault("api", {})[space_id] = endpoints
        except Exception as exc:
            rep.probe("connect", space=space_id, ok=False, error=repr(exc))
            rep.p(f"**Connection failed:** `{exc!r}`")
            continue

        rep.h3("Generation")
        try:
            result, secs, endpoint = generate(client, endpoints, image_path, rep)
            rep.probe(
                "generate", space=space_id, ok=True, latency_s=secs, endpoint=endpoint
            )
            rep.p(f"`{endpoint}` returned in **{secs}s**.")
            rep.code(str(result)[:1500])
        except Exception as exc:
            quota = "ZeroGPU quota" in str(exc)
            rep.probe(
                "generate", space=space_id, ok=False, quota_exhausted=quota,
                error=repr(exc),
            )
            if quota:
                rep.data["quota_exhausted"] = True
                rep.p(
                    "**Free ZeroGPU quota exhausted** - the Space refused the "
                    "call before any GPU work started. The daily free budget "
                    "is shared across every ZeroGPU Space for this account, "
                    "and each TRELLIS call reserves a fixed slice of it:"
                )
                rep.code(str(exc))
            else:
                rep.p(f"**Generation failed:** `{exc!r}`")
                rep.code(traceback.format_exc()[-1200:])
            continue

        glb = pick_glb(result)
        if glb is None:
            rep.p("**No GLB found** in the returned payload.")
            continue

        saved = rep.dir / f"trellis-{slug}.glb"
        saved.write_bytes(glb.read_bytes())
        rep.p(f"GLB saved as `{saved.name}` in the results folder.")

        rep.h3("Artifact proof - trimesh measurement")
        metrics = measure(saved)
        metrics["space"] = space_id
        metrics["endpoint"] = endpoint
        metrics["generation_s"] = secs
        rep.data.setdefault("measurements", {})[space_id] = metrics
        (rep.dir / f"trellis-{slug}.measurements.json").write_text(
            json.dumps(metrics, indent=2) + "\n", encoding="utf-8"
        )
        rep.table(["Metric", "Value"], [[k, str(v)] for k, v in metrics.items()])
        rep.p(
            f"**TRELLIS hello world succeeded** on `{space_id}` in {secs}s; "
            "the GLB re-loads and measures non-degenerate geometry."
        )
        succeeded.append(space_id)
        if args.first_success:
            break

    rep.h2(f"{step}. Outcome")
    rep.data["succeeded_spaces"] = succeeded
    if succeeded:
        rep.p(
            "Free image-to-3d access is proven through "
            + ", ".join(f"`{s}`" for s in succeeded)
            + "."
        )
        rep.write()
        return 0
    rep.p("**No candidate Space produced a GLB.**")
    rep.write()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
