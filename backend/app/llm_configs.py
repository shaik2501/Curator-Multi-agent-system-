"""Live verification, masked serialization, and one-time .env seeding for
saved LLMConfig rows (app/db.py). This is the module the user-facing
"add a credential" flow runs through: paste a key -> verify live -> save.
"""
from __future__ import annotations

from typing import Optional

from app import db
from app.db import LLMConfig
from app.llm import (
    DEFAULT_OLLAMA_BASE_URL,
    DEFAULT_OLLAMA_MODEL,
    ProviderUnavailable,
    _build_client,
    check_ollama_reachable_at,
    classify_provider_error,
)

PRETTY_NAMES = {
    "claude": "Claude",
    "openai": "OpenAI",
    "gemini": "Gemini",
    "ollama": "Ollama (Local)",
    "custom": "Custom",
}


def mask_key(key: Optional[str]) -> Optional[str]:
    """first 6 + '...' + last 4 chars; never returns the raw value."""
    if not key:
        return None
    if len(key) <= 10:
        return "..." if len(key) <= 3 else f"{key[:2]}...{key[-1]}"
    return f"{key[:6]}...{key[-4:]}"


def default_label(provider_type: str) -> str:
    pretty = PRETTY_NAMES.get(provider_type, provider_type)
    return f"{pretty} — {db.utcnow().strftime('%b %d')}"


def to_public_dict(config: LLMConfig) -> dict:
    """Serialize a config for API responses. Never includes config.api_key."""
    return {
        "id": config.id,
        "label": config.label,
        "provider_type": config.provider_type,
        "key_preview": mask_key(config.api_key),
        "base_url": config.base_url,
        "model": config.model,
        "cheap_model": config.cheap_model,
        "image_capable": config.image_capable,
        "status": config.status,
        "last_checked_at": config.last_checked_at.isoformat()
        if config.last_checked_at
        else None,
        "last_error": config.last_error,
        "created_at": config.created_at.isoformat(),
    }


def verify_config(config: LLMConfig) -> LLMConfig:
    """Run a live check using the config's own credentials/base_url/model,
    persist status/last_error/last_checked_at, and return the updated row.

    - claude/openai/gemini/custom: build the real langchain client from this
      row's own fields and make one minimal real call.
    - ollama: no LLM call needed, just a reachability check against the
      row's base_url (default applied if unset).
    """
    status = "unverified"
    last_error: Optional[str] = None

    try:
        if config.provider_type == "ollama":
            base_url = config.base_url or DEFAULT_OLLAMA_BASE_URL
            if check_ollama_reachable_at(base_url):
                status = "verified"
            else:
                status = "failed"
                last_error = f"Ollama at {base_url} is not reachable."
        else:
            llm = _build_client(config)
            llm.invoke(
                [
                    {"role": "system", "content": "Reply with a single short word."},
                    {"role": "user", "content": "Say 'ok'."},
                ]
            )
            status = "verified"
    except ProviderUnavailable as exc:
        status = "failed"
        last_error = str(exc)[:200]
    except Exception as exc:  # noqa: BLE001 - classify and store, never crash
        status = "failed"
        last_error = classify_provider_error(exc)

    updated = db.update_llm_config_status(config.id, status=status, last_error=last_error)
    return updated if updated is not None else config


def seed_from_env_if_empty() -> None:
    """One-time seed: if the llm_configs table is empty, create rows from
    whatever's already configured in .env (app.config.settings) so a
    previously-working setup (e.g. a real ANTHROPIC_API_KEY) keeps working
    with zero action from the user. After this, .env provider vars are never
    read again at run time — /api/llm-configs is the single source of truth.
    """
    if db.count_llm_configs() > 0:
        return

    from app.config import settings

    candidates: list[LLMConfig] = []

    if settings.anthropic_api_key:
        candidates.append(
            LLMConfig(
                id=db.new_id(),
                label="Claude (from .env)",
                provider_type="claude",
                api_key=settings.anthropic_api_key,
                model=settings.claude_model,
                cheap_model=settings.claude_cheap_model,
                status="unverified",
            )
        )

    if settings.openai_api_key:
        candidates.append(
            LLMConfig(
                id=db.new_id(),
                label="OpenAI (from .env)",
                provider_type="openai",
                api_key=settings.openai_api_key,
                model=settings.openai_model,
                cheap_model=settings.openai_cheap_model,
                image_capable=True,
                status="unverified",
            )
        )

    if settings.gemini_api_key:
        candidates.append(
            LLMConfig(
                id=db.new_id(),
                label="Gemini (from .env)",
                provider_type="gemini",
                api_key=settings.gemini_api_key,
                model=settings.gemini_model,
                cheap_model=settings.gemini_cheap_model,
                image_capable=True,
                status="unverified",
            )
        )

    # Ollama is always seeded: zero-config by default (base_url/model always
    # have defaults, no key required).
    candidates.append(
        LLMConfig(
            id=db.new_id(),
            label="Ollama (Local)",
            provider_type="ollama",
            base_url=settings.ollama_base_url or DEFAULT_OLLAMA_BASE_URL,
            model=settings.ollama_model or DEFAULT_OLLAMA_MODEL,
            status="unverified",
        )
    )

    if settings.custom_base_url and settings.custom_model:
        candidates.append(
            LLMConfig(
                id=db.new_id(),
                label="Custom (from .env)",
                provider_type="custom",
                api_key=settings.custom_api_key,
                base_url=settings.custom_base_url,
                model=settings.custom_model,
                cheap_model=settings.custom_cheap_model,
                status="unverified",
            )
        )

    for candidate in candidates:
        created = db.create_llm_config(candidate)
        verify_config(created)
