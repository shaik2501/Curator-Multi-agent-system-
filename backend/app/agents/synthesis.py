"""Synthesis agent: merges draft + critiques + notes into the final report with a Sources section."""
from __future__ import annotations

from app.llm import ProviderUnavailable, get_llm, invoke_llm
from app import memory
from app.state import ResearchState

SYSTEM_PROMPT = """You are the Synthesis/Reviewer Agent on a research team.
Merge the draft report and the critic's feedback into a final, polished
markdown research report. Keep inline citations like [1], [2]. End with a
"## Sources" section listing every numbered source URL used."""


def run(state: ResearchState) -> str:
    provider_config_id = state.get("agent_configs", {}).get("synthesis", "")
    run_id = state.get("run_id", "default")
    goal = state.get("goal", "")
    draft = state.get("draft", "")
    critiques = state.get("critiques", [])

    critique_text = "\n\n".join(
        f"Round {c.round} critique: {c.summary}\n"
        + "\n".join(f"- {issue}" for issue in c.issues)
        for c in critiques
    ) or "(no critique rounds occurred)"

    all_hits = memory.get_all_notes(run_id)
    all_sources: list[str] = []
    for hit in all_hits:
        for src in hit["sources"]:
            if src not in all_sources:
                all_sources.append(src)
    sources_numbered = "\n".join(f"[{i + 1}] {s}" for i, s in enumerate(all_sources))

    try:
        llm = get_llm(provider_config_id=provider_config_id)
        response = invoke_llm(
            llm,
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Research goal: {goal}\n\n"
                        f"Draft:\n{draft}\n\n"
                        f"Critique history:\n{critique_text}\n\n"
                        f"Numbered sources (use exactly these numbers/urls in the Sources section):\n"
                        f"{sources_numbered}"
                    ),
                },
            ]
        )
        content = response.content if hasattr(response, "content") else str(response)
        if isinstance(content, list):
            content = "".join(
                part.get("text", "") if isinstance(part, dict) else str(part) for part in content
            )
        return content
    except ProviderUnavailable:
        raise
    except Exception as exc:  # noqa: BLE001
        sources_section = "\n\n## Sources\n" + sources_numbered if sources_numbered else ""
        return f"(Synthesis LLM call failed: {exc})\n\n{draft}{sources_section}"
