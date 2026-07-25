"""Data agent: analyzes numbers/tables found in existing notes into comparisons/stats."""
from __future__ import annotations

from app.llm import ProviderUnavailable, get_llm, invoke_llm
from app.state import Note, ResearchState

SYSTEM_PROMPT = """You are the Data Agent on a research team.
Given prior research notes, extract any numbers/tables/facts you can compare,
and produce a short structured comparison, ranking, or simple statistics.
If no quantitative data is present, say so plainly and suggest what should be
gathered next. Respond in concise markdown."""


def run(state: ResearchState, task: str) -> Note:
    provider_config_id = state.get("agent_configs", {}).get("data", "")
    notes = state.get("notes", [])
    notes_text = "\n\n".join(f"[{n.agent}] {n.content}" for n in notes) or "(no notes yet)"

    try:
        llm = get_llm(provider_config_id=provider_config_id)
        response = invoke_llm(
            llm,
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Task: {task}\n\nExisting notes:\n{notes_text}",
                },
            ]
        )
        content = response.content if hasattr(response, "content") else str(response)
        if isinstance(content, list):
            content = "".join(
                part.get("text", "") if isinstance(part, dict) else str(part) for part in content
            )
    except ProviderUnavailable:
        raise
    except Exception as exc:  # noqa: BLE001
        content = f"(Data agent LLM call failed: {exc})"

    return Note(agent="data", content=content, sources=[])
