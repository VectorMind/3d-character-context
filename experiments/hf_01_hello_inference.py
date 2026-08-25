# /// script
# requires-python = ">=3.11,<3.13"
# dependencies = ["requests>=2.32"]
# ///
"""Phase 1 / OP-011 - hello-world probe of Hugging Face REST inference access.

Validates, with the real HF_TOKEN from the workspace `.env`, that:

1. the token authenticates and what it is allowed to do (`/api/whoami-v2`);
2. the Inference Providers router is reachable and which models it serves;
3. a minimal chat completion round-trips (the "hello world" model call);
4. whether the legacy `api-inference.huggingface.co` route still answers;
5. whether any image-to-3d model is served by the REST inference API at all
   (the question that decides whether Spaces are required for TRELLIS).

Usage:

    uv run --script experiments/hf_01_hello_inference.py

Writes `.cache/results/<date>/<time>-hf-hello-inference/`.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import Report, load_dotenv, mask, require_env  # noqa: E402

ROUTER = "https://router.huggingface.co"
HUB = "https://huggingface.co"
LEGACY = "https://api-inference.huggingface.co"
TIMEOUT = 60

# Hello-world chat models, most likely available first.
CHAT_CANDIDATES = [
    "Qwen/Qwen2.5-7B-Instruct",
    "meta-llama/Llama-3.1-8B-Instruct",
    "mistralai/Mistral-7B-Instruct-v0.3",
    "HuggingFaceTB/SmolLM3-3B",
]

# Classic pipeline models for the legacy REST route.
LEGACY_CANDIDATES = [
    ("sentence-transformers/all-MiniLM-L6-v2", {"inputs": "hello world"}),
    ("distilbert-base-uncased-finetuned-sst-2-english", {"inputs": "hello world"}),
]


def timed(method: str, url: str, **kw):
    """Run one HTTP request, returning (response, seconds, exception)."""
    start = time.perf_counter()
    try:
        response = requests.request(method, url, timeout=TIMEOUT, **kw)
        return response, round(time.perf_counter() - start, 2), None
    except Exception as exc:  # a network-level failure is a finding, not a crash
        return None, round(time.perf_counter() - start, 2), exc


def main() -> int:
    load_dotenv()
    token = require_env("HF_TOKEN")
    auth = {"Authorization": f"Bearer {token}"}

    rep = Report("hf-hello-inference", "HF REST Inference - Hello World Access Probe")
    rep.data["token"] = mask(token)
    rep.p(
        "Free-access experiment (plan Phase 1, OP-011): can the Hugging Face "
        "REST inference API be reached with the workspace token, and does it "
        "serve anything for image-to-3d?"
    )
    rep.p(f"Token used: `{mask(token)}` (read from `.env`, never printed in full).")

    # --- 1. identity --------------------------------------------------
    rep.h2("1. Token identity - `GET /api/whoami-v2`")
    response, secs, exc = timed("GET", f"{HUB}/api/whoami-v2", headers=auth)
    if exc is not None:
        rep.probe("whoami", ok=False, latency_s=secs, error=repr(exc))
        rep.p(f"**FAILED** after {secs}s: `{exc!r}`")
        rep.write()
        return 1
    ok = response.status_code == 200
    rep.probe("whoami", ok=ok, status=response.status_code, latency_s=secs)
    if not ok:
        rep.p(f"**HTTP {response.status_code}** after {secs}s:")
        rep.code(response.text[:500])
        rep.write()
        return 1
    body = response.json()
    perms = (body.get("auth") or {}).get("accessToken") or {}
    orgs = ", ".join(o.get("name", "?") for o in body.get("orgs", []) or [])
    rep.table(
        ["Field", "Value"],
        [
            ["user", str(body.get("name"))],
            ["type", str(body.get("type"))],
            ["token name", str(perms.get("displayName"))],
            ["token role", str(perms.get("role"))],
            ["orgs", orgs or "-"],
            ["latency", f"{secs}s"],
        ],
    )
    fine = perms.get("fineGrained")
    if fine:
        rep.p("Fine-grained token scopes:")
        rep.code(json.dumps(fine, indent=2)[:2000], "json")

    # --- 2. router catalogue -----------------------------------------
    rep.h2("2. Inference Providers router - `GET /v1/models`")
    response, secs, exc = timed("GET", f"{ROUTER}/v1/models", headers=auth)
    if exc is not None:
        rep.probe("router_models", ok=False, latency_s=secs, error=repr(exc))
        rep.p(f"**FAILED** after {secs}s: `{exc!r}`")
    else:
        ok = response.status_code == 200
        rep.probe("router_models", ok=ok, status=response.status_code, latency_s=secs)
        if ok:
            payload = response.json()
            items = payload.get("data") if isinstance(payload, dict) else payload
            served = [str(m.get("id")) for m in (items or []) if isinstance(m, dict)]
            rep.p(
                f"HTTP 200 in {secs}s - **{len(served)} models** served by the "
                "router across all inference providers."
            )
            rep.p("First 10 ids as a sample:")
            rep.code("\n".join(served[:10]))
            rep.data["router_model_count"] = len(served)
        else:
            rep.p(f"**HTTP {response.status_code}** after {secs}s:")
            rep.code(response.text[:800])

    # --- 3. hello-world chat completion ------------------------------
    rep.h2("3. Hello-world model call - `POST /v1/chat/completions`")
    rows: list[list[str]] = []
    winner = None
    for model in CHAT_CANDIDATES:
        response, secs, exc = timed(
            "POST",
            f"{ROUTER}/v1/chat/completions",
            headers={**auth, "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": "Say hello world."}],
                "max_tokens": 24,
            },
        )
        if exc is not None:
            rep.probe("chat", model=model, ok=False, latency_s=secs, error=repr(exc))
            rows.append(
                [f"`{model}`", "-", f"{secs}s", f"transport error: {exc!r}"[:90]]
            )
            continue
        ok = response.status_code == 200
        if ok:
            data = response.json()
            reply = data["choices"][0]["message"]["content"].strip().replace("\n", " ")
            provider = data.get("provider") or response.headers.get(
                "x-inference-provider", "?"
            )
            note = f'reply: "{reply[:60]}" (provider `{provider}`)'
            winner = winner or (model, reply, provider, secs)
        else:
            note = response.text.strip().replace("\n", " ")[:120]
        rep.probe(
            "chat", model=model, ok=ok, status=response.status_code, latency_s=secs
        )
        rows.append([f"`{model}`", str(response.status_code), f"{secs}s", note])
        if ok:
            break
    rep.table(["Model", "HTTP", "Latency", "Result"], rows)
    if winner:
        rep.p(
            f"**Hello world succeeded** on `{winner[0]}` via provider "
            f"`{winner[2]}` in {winner[3]}s - REST inference access with this "
            "token is confirmed working."
        )
        rep.data["hello_world_model"] = winner[0]
    else:
        rep.p("**No chat model answered** - see the table for per-model status.")

    # --- 4. legacy route ---------------------------------------------
    rep.h2("4. Legacy route - `api-inference.huggingface.co/models/<id>`")
    rows = []
    for model, payload in LEGACY_CANDIDATES:
        response, secs, exc = timed(
            "POST", f"{LEGACY}/models/{model}", headers=auth, json=payload
        )
        if exc is not None:
            rep.probe("legacy", model=model, ok=False, latency_s=secs, error=repr(exc))
            rows.append(
                [f"`{model}`", "-", f"{secs}s", f"transport error: {exc!r}"[:90]]
            )
            continue
        ok = response.status_code == 200
        note = response.text.strip().replace("\n", " ")[:120]
        rep.probe(
            "legacy", model=model, ok=ok, status=response.status_code, latency_s=secs
        )
        rows.append([f"`{model}`", str(response.status_code), f"{secs}s", note])
    rep.table(["Model", "HTTP", "Latency", "Result"], rows)

    # --- 5. is image-to-3d served by REST inference at all? ----------
    rep.h2("5. Does REST inference serve `image-to-3d`?")
    response, secs, exc = timed(
        "GET",
        f"{HUB}/api/models",
        params={
            "pipeline_tag": "image-to-3d",
            "inference_provider": "all",
            "sort": "likes",
            "limit": 20,
        },
        headers=auth,
    )
    if exc is not None:
        rep.probe("image_to_3d_catalogue", ok=False, latency_s=secs, error=repr(exc))
        rep.p(f"**FAILED** after {secs}s: `{exc!r}`")
    else:
        ok = response.status_code == 200
        items = response.json() if ok else []
        rep.probe(
            "image_to_3d_catalogue",
            ok=ok,
            status=response.status_code,
            latency_s=secs,
            count=len(items),
        )
        rep.p(
            f"HTTP {response.status_code} in {secs}s - **{len(items)}** "
            "`image-to-3d` models are served by any inference provider."
        )
        if items:
            rep.table(
                ["Model", "Likes", "Downloads"],
                [
                    [f"`{m.get('id')}`", str(m.get("likes")), str(m.get("downloads"))]
                    for m in items
                ],
            )
        rep.data["image_to_3d_served"] = len(items)

        response2, secs2, _ = timed(
            "GET",
            f"{HUB}/api/models",
            params={"pipeline_tag": "image-to-3d", "sort": "likes", "limit": 10},
            headers=auth,
        )
        if response2 is not None and response2.status_code == 200:
            all_items = response2.json()
            rep.p(
                f"For contrast, the Hub itself hosts many `image-to-3d` models "
                f"(top {len(all_items)} by likes, {secs2}s) - they are simply "
                "not exposed through serverless inference:"
            )
            rep.table(
                ["Model", "Likes"],
                [[f"`{m.get('id')}`", str(m.get("likes"))] for m in all_items],
            )
            rep.data["image_to_3d_on_hub_sample"] = [m.get("id") for m in all_items]

    rep.write()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
