"""Web research agent: search + fetch, returns facts with source URLs."""
from __future__ import annotations

from app.llm import ProviderUnavailable, get_llm, invoke_llm
from app.state import Note, ResearchState
from app.tools.fetch import fetch_page
from app.tools.search import SearchCapExceeded, search_web

SYSTEM_PROMPT = """You are the Web Research Agent on a research team.
You are given search results and fetched page text. Extract concrete facts
relevant to the task. Respond with a concise set of factual bullet points.
Do not include URLs in the bullet text itself; sources are tracked separately."""


def run(state: ResearchState, task: str) -> Note:
    run_id = state.get("run_id", "default")
    provider_config_id = state.get("agent_configs", {}).get("web", "")

    try:
        results = search_web(task, run_id=run_id, max_results=5)
    except SearchCapExceeded as exc:
        return Note(agent="web", content=f"Search cap reached: {exc}", sources=[])

    if not results:
        return Note(agent="web", content=f"No search results found for: {task}", sources=[])

    sources: list[str] = []
    fetched_snippets: list[str] = []
    for result in results[:3]:
        url = result.get("url", "")
        if url:
            sources.append(url)
        page_text = fetch_page(url) if url else result.get("snippet", "")
        fetched_snippets.append(
            f"Source: {result.get('title', '')} ({url})\n{page_text[:2000]}"
        )

    combined = "\n\n---\n\n".join(fetched_snippets)

    try:
        llm = get_llm(provider_config_id=provider_config_id)
        response = invoke_llm(
            llm,
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Task: {task}\n\nGathered material:\n{combined}",
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
        content = f"(LLM summarization failed: {exc}) Raw material:\n{combined[:1500]}"

    return Note(agent="web", content=content, sources=sources)
