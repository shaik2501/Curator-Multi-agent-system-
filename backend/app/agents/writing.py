"""Writing agent: queries ChromaDB for relevant notes and drafts markdown with [n] citations."""
from __future__ import annotations

from app.llm import ProviderUnavailable, get_llm, invoke_llm
from app import memory
from app.state import ResearchState

SYSTEM_PROMPT = """You are the Writing Agent on a research team.
Draft (or revise) a markdown research report section using the provided
research notes. Use inline citations like [1], [2] that map to the numbered
sources list given to you. Be clear, well-organized, and factual — do not
invent claims that aren't supported by the notes."""


def _build_sources_map(hits: list[memory.QueryHit]) -> tuple[str, list[str]]:
    all_sources: list[str] = []
    for hit in hits:
        for src in hit["sources"]:
            if src not in all_sources:
                all_sources.append(src)

    numbered = "\n".join(f"[{i + 1}] {src}" for i, src in enumerate(all_sources))
    return numbered, all_sources


def run(state: ResearchState, task: str = "") -> str:
    provider_config_id = state.get("agent_configs", {}).get("writing", "")
    run_id = state.get("run_id", "default")
    goal = state.get("goal", "")

    query_text = task or goal
    hits = memory.query(run_id, query_text, k=8)
    if not hits:
        hits = memory.get_all_notes(run_id)

    notes_text = "\n\n".join(f"[{h['agent']}] {h['content']}" for h in hits) or "(no notes)"
    sources_numbered, _ = _build_sources_map(hits)

    critiques = state.get("critiques", [])
    critique_text = ""
    if critiques:
        latest = critiques[-1]
        critique_text = "\n\nAddress this critique from the previous round:\n" + "\n".join(
            f"- {issue}" for issue in latest.issues
        )

    prior_draft = state.get("draft", "")
    prior_draft_text = f"\n\nCurrent draft to revise:\n{prior_draft}" if prior_draft else ""

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
                        f"Relevant notes:\n{notes_text}\n\n"
                        f"Available sources:\n{sources_numbered}"
                        f"{critique_text}{prior_draft_text}"
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
        return f"(Writing agent LLM call failed: {exc})\n\n" + notes_text
