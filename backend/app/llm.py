"""LLM client factory, built from saved LLMConfig rows (app/db.py) rather
than global env-based Settings. Instantiation is lazy — no client is created
at import time."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.db import LLMConfig

KNOWN_PROVIDERS = {"claude", "openai", "gemini", "ollama", "custom"}

DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_OLLAMA_MODEL = "llama3.1:8b"


class ProviderUnavailable(Exception):
    """Raised for fatal provider errors: an unknown/missing config id,
    missing credentials on a saved config, missing custom-endpoint config,
    an unreachable Ollama server, or a mid-call SDK error indicating the
    credential itself can't be used right now (invalid key, exhausted
    quota/billing). These are NOT recoverable by retrying model calls —
    callers must let this propagate and fail the run, rather than
    swallowing it into agent output."""


# Substrings that indicate an LLM SDK call failed because the *credential*
# itself is unusable (bad key, no quota/credit, no permission) rather than a
# transient/parsing problem. Matched case-insensitively against str(exc) —
# deliberately provider-agnostic so it catches anthropic/openai/google SDK
# exceptions (APIStatusError, AuthenticationError, PermissionDeniedError,
# etc.) without importing each SDK's exception classes.
_FATAL_PROVIDER_ERROR_MARKERS = (
    "401",
    "403",
    "unauthorized",
    "invalid api key",
    "invalid_api_key",
    "incorrect api key",
    "authentication",
    "permission_denied",
    "api key not valid",
    "invalid x-api-key",
    "credit balance",
    "insufficient_quota",
    "exceeded your current quota",
    "quota exceeded",
    "billing",
)

_AUTH_ERROR_MARKERS = (
    "401",
    "403",
    "unauthorized",
    "invalid api key",
    "invalid_api_key",
    "incorrect api key",
    "authentication",
    "permission_denied",
    "api key not valid",
    "invalid x-api-key",
)


def is_fatal_provider_error(exc: Exception) -> bool:
    """True if `exc` (raised by a real llm.invoke(...) call) indicates the
    credential/provider itself can't be used right now — invalid key,
    exhausted quota, no billing credit, no permission — as opposed to a
    transient network blip or a parsing problem the caller should retry."""
    message = str(exc).lower()
    if any(marker in message for marker in _FATAL_PROVIDER_ERROR_MARKERS):
        return True
    status_code = getattr(exc, "status_code", None)
    if status_code in (401, 403):
        return True
    return False


def classify_provider_error(exc: Exception) -> str:
    """Turn a raw SDK exception into a short, clean human-readable message.
    Auth-shaped errors collapse to "Invalid API key"; everything else
    (billing/quota messages are often genuinely informative, e.g. "Your
    credit balance is too low...") keeps a truncated version of the real
    message. Shared by check-time verification (app/llm_configs.py) and
    run-time invoke_llm() so both report errors the same way."""
    message = str(exc)
    lowered = message.lower()
    if any(marker in lowered for marker in _AUTH_ERROR_MARKERS):
        return "Invalid API key"
    return message[:200]


def invoke_llm(llm, messages):
    """Call llm.invoke(messages), reraising provider-fatal errors (invalid
    key, exhausted quota/billing, no permission) as ProviderUnavailable
    instead of letting them look like an ordinary, retryable/degradable
    failure. Every agent should call this instead of llm.invoke(...)
    directly so a mid-run credential failure fails the whole run cleanly —
    same as the upfront missing-key check already does — rather than
    looping through supervisor turns producing garbage notes/drafts stuffed
    with the raw API error text.

    Non-fatal errors (network blips, malformed JSON the caller will retry,
    etc.) are re-raised unchanged so existing retry/fallback behavior for
    those is untouched.
    """
    try:
        return llm.invoke(messages)
    except ProviderUnavailable:
        raise
    except Exception as exc:  # noqa: BLE001 - classify, then decide fatal or not
        if is_fatal_provider_error(exc):
            raise ProviderUnavailable(classify_provider_error(exc)) from exc
        raise


def _build_client(config: "LLMConfig"):
    """Build a langchain chat client from a saved LLMConfig row's own
    fields (never from the global Settings/.env values).

    Note: the old main/cheap "tier" concept is gone — per-role config
    assignment (each of the 7 agents resolves its own saved LLMConfig via
    ResearchState.agent_configs) supersedes it. A config's `model` field is
    always what's used; `cheap_model` is retained on the row only as a
    legacy/optional field and is not read here.
    """
    provider_type = config.provider_type
    model = config.model

    if provider_type == "claude":
        from langchain_anthropic import ChatAnthropic

        if not config.api_key:
            raise ProviderUnavailable(
                f"No API key saved for LLM config {config.id!r} ({config.label})."
            )
        return ChatAnthropic(model=model, api_key=config.api_key, temperature=0.2)

    if provider_type == "openai":
        from langchain_openai import ChatOpenAI

        if not config.api_key:
            raise ProviderUnavailable(
                f"No API key saved for LLM config {config.id!r} ({config.label})."
            )
        return ChatOpenAI(model=model, api_key=config.api_key, temperature=0.2)

    if provider_type == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        if not config.api_key:
            raise ProviderUnavailable(
                f"No API key saved for LLM config {config.id!r} ({config.label})."
            )
        return ChatGoogleGenerativeAI(model=model, google_api_key=config.api_key, temperature=0.2)

    if provider_type == "ollama":
        from langchain_ollama import ChatOllama

        base_url = config.base_url or DEFAULT_OLLAMA_BASE_URL
        return ChatOllama(model=model, base_url=base_url, temperature=0.2)

    if provider_type == "custom":
        from langchain_openai import ChatOpenAI

        missing = []
        if not config.base_url:
            missing.append("base_url")
        if not config.model:
            missing.append("model")
        if missing:
            raise ProviderUnavailable(
                f"{' and '.join(missing)} not set for LLM config {config.id!r} ({config.label})."
            )
        return ChatOpenAI(
            model=model,
            api_key=config.api_key or "not-required",
            base_url=config.base_url,
            temperature=0.2,
        )

    raise ProviderUnavailable(f"Unknown provider_type: {provider_type!r}")


def check_config_available(provider_config_id: str) -> None:
    """Eagerly validate that a saved LLM config can actually be used, without
    making an LLM call (except for Ollama, which needs a real reachability
    check since it's zero-config by default). Raises ProviderUnavailable on
    failure — used as the cheap, fast pre-flight check before a run starts."""
    from app import db

    config = db.get_llm_config(provider_config_id)
    if config is None:
        raise ProviderUnavailable(f"LLM config {provider_config_id!r} was not found.")

    provider_type = config.provider_type

    if provider_type in ("claude", "openai", "gemini"):
        if not config.api_key:
            raise ProviderUnavailable(
                f"No API key saved for LLM config {config.id!r} ({config.label})."
            )
        return

    if provider_type == "custom":
        missing = []
        if not config.base_url:
            missing.append("base_url")
        if not config.model:
            missing.append("model")
        if missing:
            raise ProviderUnavailable(
                f"{' and '.join(missing)} not set for LLM config {config.id!r} ({config.label})."
            )
        return

    if provider_type == "ollama":
        base_url = config.base_url or DEFAULT_OLLAMA_BASE_URL
        if not check_ollama_reachable_at(base_url):
            raise ProviderUnavailable(f"Ollama at {base_url} is not reachable.")
        return

    raise ProviderUnavailable(f"Unknown provider_type: {provider_type!r}")


def check_ollama_reachable_at(base_url: str) -> bool:
    """Short-timeout, non-raising liveness check against an arbitrary Ollama
    base_url. Returns False on any failure (connection refused, timeout,
    non-2xx, etc.) instead of raising."""
    import httpx

    try:
        resp = httpx.get(f"{base_url}/api/tags", timeout=3.0)
        resp.raise_for_status()
        return True
    except Exception:  # noqa: BLE001
        return False


def check_ollama_reachable() -> bool:
    """Convenience wrapper: reachability check against the global default
    Ollama base_url (app.config.settings), used by the generic "Test
    Connection" endpoint that isn't tied to any particular saved config."""
    from app.config import settings

    return check_ollama_reachable_at(settings.ollama_base_url or DEFAULT_OLLAMA_BASE_URL)


def get_llm(provider_config_id: str):
    """Return a chat model instance for the given saved LLM config.

    provider_config_id: the id of a saved app.db.LLMConfig row.

    Raises ProviderUnavailable if the config id doesn't exist, or its
    credentials/config are missing.
    """
    from app import db

    config = db.get_llm_config(provider_config_id)
    if config is None:
        raise ProviderUnavailable(f"LLM config {provider_config_id!r} was not found.")

    return _build_client(config)
