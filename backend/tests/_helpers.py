"""Small shared helpers for building per-role agent_configs/snapshot test
fixtures — not a conftest, just plain importable functions."""
from __future__ import annotations

from app.db import LLMConfig
from app.state import AGENT_ROLES


def make_agent_configs(config_id: str) -> dict:
    """The same config id assigned to every one of the 7 agent roles —
    convenience for tests that don't care about per-role independence."""
    return {role: config_id for role in AGENT_ROLES}


def make_mixed_agent_configs(config_a_id: str, config_b_id: str, role_for_b: str = "web") -> dict:
    """config_a for every role except `role_for_b`, which gets config_b —
    used by tests that need to prove per-role independence actually works."""
    return {role: (config_b_id if role == role_for_b else config_a_id) for role in AGENT_ROLES}


def make_snapshot(config: LLMConfig) -> dict:
    """Snapshot dict (same config for every role) matching the shape stored
    on Run.agent_model_snapshot."""
    return {
        role: {
            "config_id": config.id,
            "provider_type": config.provider_type,
            "label": config.label,
        }
        for role in AGENT_ROLES
    }
