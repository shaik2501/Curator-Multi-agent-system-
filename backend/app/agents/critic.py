"""Critic agent: attacks the draft, returns a structured critique list."""
from __future__ import annotations

import json
import re

from app.llm import ProviderUnavailable, get_llm, invoke_llm
from app.state import Critique, ResearchState

SYSTEM_PROMPT = """You are the Critic Agent on a research team.
Challenge the draft report: flag unsupported claims, missing perspectives,
weak/missing sources, and contradictions. Respond with ONLY a JSON object:
{"issues": ["issue 1", "issue 2", ...], "summary": "<one paragraph overview>"}
If the draft is solid, return an empty issues list."""


def _extract_json(text: str) -> dict:
    text = text.strip()
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1)
    else:
        brace_match = re.search(r"\{.*\}", text, re.DOTALL)
        if brace_match:
            text = brace_match.group(0)
    return json.loads(text)


def run(state: ResearchState, round_number: int) -> Critique:
    provider_config_id = state.get("agent_configs", {}).get("critic", "")
    draft = state.get("draft", "")

    try:
        llm = get_llm(provider_config_id=provider_config_id)
        response = invoke_llm(
            llm,
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Draft report:\n\n{draft}"},
            ]
        )
        content = response.content if hasattr(response, "content") else str(response)
        if isinstance(content, list):
            content = "".join(
                part.get("text", "") if isinstance(part, dict) else str(part) for part in content
            )
        parsed = _extract_json(content)
        return Critique(
            round=round_number,
            issues=parsed.get("issues", []),
            summary=parsed.get("summary", ""),
        )
    except ProviderUnavailable:
        raise
    except Exception as exc:  # noqa: BLE001
        return Critique(
            round=round_number,
            issues=[],
            summary=f"(Critic agent failed to produce structured critique: {exc})",
        )
