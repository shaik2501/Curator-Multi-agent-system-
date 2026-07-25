"""Live "list models this key can actually use" lookups for the Add-an-LLM
form. Stateless: never touches the database, never persists anything, and
never logs/echoes back a raw api_key value. A failed lookup (bad key,
network issue, endpoint unsupported) is normal expected output — it goes in
the `error` string, never raised as an HTTP error from this module.
"""
from __future__ import annotations

from typing import Optional

import httpx

from app.llm import DEFAULT_OLLAMA_BASE_URL

_TIMEOUT = 8.0
_CUSTOM_TIMEOUT = 5.0

_OPENAI_EXCLUDE_MARKERS = ("embedding", "whisper", "tts", "moderation", "dall-e")


class ModelListResult:
    __slots__ = ("models", "error")

    def __init__(self, models: list[str], error: Optional[str] = None):
        self.models = models
        self.error = error

    def to_dict(self) -> dict:
        return {"models": self.models, "error": self.error}


def _truncate(message: str, limit: int = 200) -> str:
    return message[:limit]


def list_claude_models(api_key: Optional[str]) -> ModelListResult:
    if not api_key:
        return ModelListResult([], "API key required")

    try:
        resp = httpx.get(
            "https://api.anthropic.com/v1/models",
            headers={"anthropic-version": "2023-06-01", "X-Api-Key": api_key},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        models = [item["id"] for item in data.get("data", []) if "id" in item]
        return ModelListResult(models, None)
    except Exception as exc:  # noqa: BLE001
        return ModelListResult([], _truncate(str(exc)))


def list_openai_models(api_key: Optional[str]) -> ModelListResult:
    if not api_key:
        return ModelListResult([], "API key required")

    try:
        resp = httpx.get(
            "https://api.openai.com/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        models = []
        for item in data.get("data", []):
            model_id = item.get("id")
            if not model_id:
                continue
            lowered = model_id.lower()
            if any(marker in lowered for marker in _OPENAI_EXCLUDE_MARKERS):
                continue
            models.append(model_id)
        return ModelListResult(models, None)
    except Exception as exc:  # noqa: BLE001
        return ModelListResult([], _truncate(str(exc)))


def list_gemini_models(api_key: Optional[str]) -> ModelListResult:
    if not api_key:
        return ModelListResult([], "API key required")

    try:
        resp = httpx.get(
            "https://generativelanguage.googleapis.com/v1beta/models",
            params={"key": api_key},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        models = []
        for item in data.get("models", []):
            name = item.get("name", "")
            supported = item.get("supportedGenerationMethods", [])
            if "generateContent" not in supported:
                continue
            bare_id = name[len("models/") :] if name.startswith("models/") else name
            if bare_id:
                models.append(bare_id)
        return ModelListResult(models, None)
    except Exception as exc:  # noqa: BLE001
        return ModelListResult([], _truncate(str(exc)))


def list_ollama_models(base_url: Optional[str]) -> ModelListResult:
    resolved_base_url = base_url or DEFAULT_OLLAMA_BASE_URL
    try:
        resp = httpx.get(f"{resolved_base_url}/api/tags", timeout=_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        models = [item["name"] for item in data.get("models", []) if "name" in item]
        return ModelListResult(models, None)
    except Exception:  # noqa: BLE001
        return ModelListResult([], f"Ollama is not reachable at {resolved_base_url}")


def list_custom_models(base_url: Optional[str], api_key: Optional[str]) -> ModelListResult:
    if not base_url:
        return ModelListResult([], "base_url required")

    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    fallback_error = (
        "This endpoint doesn't support model listing — enter the model name manually."
    )

    try:
        resp = httpx.get(
            f"{base_url.rstrip('/')}/models", headers=headers, timeout=_CUSTOM_TIMEOUT
        )
        resp.raise_for_status()
        data = resp.json()
        items = data.get("data")
        if not isinstance(items, list):
            return ModelListResult([], fallback_error)
        models = [item["id"] for item in items if isinstance(item, dict) and "id" in item]
        if not models:
            return ModelListResult([], fallback_error)
        return ModelListResult(models, None)
    except Exception:  # noqa: BLE001
        return ModelListResult([], fallback_error)


def list_models(provider_type: str, api_key: Optional[str], base_url: Optional[str]) -> ModelListResult:
    if provider_type == "claude":
        return list_claude_models(api_key)
    if provider_type == "openai":
        return list_openai_models(api_key)
    if provider_type == "gemini":
        return list_gemini_models(api_key)
    if provider_type == "ollama":
        return list_ollama_models(base_url)
    if provider_type == "custom":
        return list_custom_models(base_url, api_key)
    return ModelListResult([], f"Unknown provider_type: {provider_type!r}")
