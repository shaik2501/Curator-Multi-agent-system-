"""Environment/config loading for Curator backend."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")


def _env_int(name: str, default: int) -> int:
    val = os.getenv(name)
    if val is None or val == "":
        return default
    try:
        return int(val)
    except ValueError:
        return default


@dataclass
class Settings:
    anthropic_api_key: str | None = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY"))
    tavily_api_key: str | None = field(default_factory=lambda: os.getenv("TAVILY_API_KEY"))
    default_provider: str = field(default_factory=lambda: os.getenv("DEFAULT_PROVIDER", "claude"))
    claude_model: str = field(default_factory=lambda: os.getenv("CLAUDE_MODEL", "claude-sonnet-5"))
    claude_cheap_model: str = field(
        default_factory=lambda: os.getenv("CLAUDE_CHEAP_MODEL", "claude-haiku-4-5")
    )
    ollama_model: str = field(default_factory=lambda: os.getenv("OLLAMA_MODEL", "llama3.1:8b"))
    ollama_base_url: str = field(
        default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    )
    openai_api_key: str | None = field(default_factory=lambda: os.getenv("OPENAI_API_KEY"))
    openai_model: str = field(default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-4o"))
    openai_cheap_model: str = field(
        default_factory=lambda: os.getenv("OPENAI_CHEAP_MODEL", "gpt-4o-mini")
    )
    gemini_api_key: str | None = field(default_factory=lambda: os.getenv("GEMINI_API_KEY"))
    gemini_model: str = field(
        default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-2.5-pro")
    )
    gemini_cheap_model: str = field(
        default_factory=lambda: os.getenv("GEMINI_CHEAP_MODEL", "gemini-2.5-flash")
    )
    custom_base_url: str | None = field(default_factory=lambda: os.getenv("CUSTOM_BASE_URL"))
    custom_api_key: str | None = field(default_factory=lambda: os.getenv("CUSTOM_API_KEY"))
    custom_model: str | None = field(default_factory=lambda: os.getenv("CUSTOM_MODEL"))
    custom_cheap_model: str | None = field(
        default_factory=lambda: os.getenv("CUSTOM_CHEAP_MODEL")
    )
    db_path: str = field(default_factory=lambda: os.getenv("DB_PATH", "./data/runs.db"))
    chroma_path: str = field(default_factory=lambda: os.getenv("CHROMA_PATH", "./data/chroma"))
    images_path: str = field(default_factory=lambda: os.getenv("IMAGES_PATH", "./data/images"))
    max_supervisor_turns: int = field(default_factory=lambda: _env_int("MAX_SUPERVISOR_TURNS", 12))
    max_debate_rounds: int = field(default_factory=lambda: _env_int("MAX_DEBATE_ROUNDS", 2))
    max_searches_per_run: int = field(default_factory=lambda: _env_int("MAX_SEARCHES_PER_RUN", 15))

    def resolved_db_path(self) -> Path:
        p = Path(self.db_path)
        if not p.is_absolute():
            p = BACKEND_DIR / p
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def resolved_chroma_path(self) -> Path:
        p = Path(self.chroma_path)
        if not p.is_absolute():
            p = BACKEND_DIR / p
        p.mkdir(parents=True, exist_ok=True)
        return p

    def resolved_images_path(self) -> Path:
        p = Path(self.images_path)
        if not p.is_absolute():
            p = BACKEND_DIR / p
        p.mkdir(parents=True, exist_ok=True)
        return p


settings = Settings()
