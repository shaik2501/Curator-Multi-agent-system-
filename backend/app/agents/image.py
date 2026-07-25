"""Image generation agent: produces a generated image for the given task
via the assigned config's provider. Uses raw httpx REST calls, consistent
with how app/model_listing.py already talks to provider REST APIs — no new
SDK dependency for this.

Only configs with LLMConfig.image_capable=True can ever be assigned to the
"image" role — app.main._resolve_agent_model_snapshot enforces this at run
creation time (400 before the run even starts), so the "unsupported
provider" branches here are defense in depth, not the primary guard.

Provider notes (verified against live docs before implementing, per the
"don't trust stale training knowledge" warning for this fast-moving API
surface):
  - openai: POST /v1/images/generations, standard DALL-E-style response
    shape (data[].b64_json preferred, data[].url fallback).
  - gemini: the current (2026) "Interactions API" —
    POST https://generativelanguage.googleapis.com/v1beta/interactions,
    verified directly against ai.google.dev/gemini-api/docs/image-generation
    (the older generateContent-based image path is explicitly marked legacy
    on that page as of this writing). Response image bytes are base64 at
    output_image.data, with output_image.mime_type alongside.
  - custom: best-effort treated as an OpenAI-compatible
    {base_url}/images/generations endpoint, same shape as openai.
"""
from __future__ import annotations

import base64
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Tuple

import httpx

from app import db
from app.config import settings
from app.state import Note, ResearchState

if TYPE_CHECKING:
    from app.db import LLMConfig

_TIMEOUT = 60.0  # image generation is slower than a typical text completion


def _save_image_bytes(run_id: str, image_bytes: bytes) -> Tuple[Path, str]:
    """Save `image_bytes` under backend/data/images/{run_id}/{uuid4().hex}.png
    and return (absolute_path, servable_url)."""
    run_dir = settings.resolved_images_path() / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}.png"
    path = run_dir / filename
    path.write_bytes(image_bytes)
    return path, f"/api/images/{run_id}/{filename}"


def _extract_openai_style_image(data: dict) -> bytes:
    items = data.get("data", [])
    if not items:
        raise RuntimeError("Image generation returned no image data.")
    item = items[0]
    b64 = item.get("b64_json")
    if b64:
        return base64.b64decode(b64)
    url = item.get("url")
    if url:
        image_resp = httpx.get(url, timeout=_TIMEOUT)
        image_resp.raise_for_status()
        return image_resp.content
    raise RuntimeError("Image generation response had neither b64_json nor url.")


def _generate_openai(config: "LLMConfig", task: str) -> bytes:
    resp = httpx.post(
        "https://api.openai.com/v1/images/generations",
        headers={"Authorization": f"Bearer {config.api_key}"},
        json={"model": config.model, "prompt": task, "n": 1, "size": "1024x1024"},
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    return _extract_openai_style_image(resp.json())


def _generate_gemini(config: "LLMConfig", task: str) -> bytes:
    resp = httpx.post(
        "https://generativelanguage.googleapis.com/v1beta/interactions",
        headers={"x-goog-api-key": config.api_key, "Content-Type": "application/json"},
        json={
            "model": config.model,
            "input": [{"type": "text", "text": task}],
        },
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    output_image = data.get("output_image")
    if not output_image or not output_image.get("data"):
        raise RuntimeError("Gemini image generation response had no output_image.data.")
    return base64.b64decode(output_image["data"])


def _generate_custom(config: "LLMConfig", task: str) -> bytes:
    base_url = (config.base_url or "").rstrip("/")
    headers = {}
    if config.api_key:
        headers["Authorization"] = f"Bearer {config.api_key}"
    resp = httpx.post(
        f"{base_url}/images/generations",
        headers=headers,
        json={"model": config.model, "prompt": task, "n": 1, "size": "1024x1024"},
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    return _extract_openai_style_image(resp.json())


def run(state: ResearchState, task: str) -> Note:
    run_id = state.get("run_id", "default")
    provider_config_id = state.get("agent_configs", {}).get("image", "")

    config = db.get_llm_config(provider_config_id)
    if config is None:
        return Note(
            agent="image",
            content=f"(Image agent failed: LLM config {provider_config_id!r} was not found.)",
            sources=[],
        )

    # Defense in depth: app.main._resolve_agent_model_snapshot already
    # rejects a non-image-capable config for this role at run-creation time,
    # so this should be unreachable in the normal API flow.
    if not config.image_capable:
        return Note(
            agent="image",
            content=(
                f"(Image agent failed: '{config.label}' ({config.provider_type}) "
                "is not image-capable.)"
            ),
            sources=[],
        )

    try:
        if config.provider_type == "openai":
            image_bytes = _generate_openai(config, task)
        elif config.provider_type == "gemini":
            image_bytes = _generate_gemini(config, task)
        elif config.provider_type == "custom":
            image_bytes = _generate_custom(config, task)
        else:
            return Note(
                agent="image",
                content=(
                    f"(Image agent failed: provider_type {config.provider_type!r} "
                    "does not support image generation through this integration.)"
                ),
                sources=[],
            )
    except Exception as exc:  # noqa: BLE001 - a bad image call must not crash the run
        return Note(agent="image", content=f"(Image generation failed: {exc})", sources=[])

    _, image_url = _save_image_bytes(run_id, image_bytes)
    return Note(
        agent="image",
        content=f"Generated an image for: {task}",
        sources=[],
        image_url=image_url,
    )
