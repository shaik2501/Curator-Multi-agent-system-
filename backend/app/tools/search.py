"""Web search tool: Tavily if TAVILY_API_KEY is set, else DuckDuckGo (ddgs)."""
from __future__ import annotations

from typing import List, TypedDict

from app.config import settings


class SearchResult(TypedDict):
    title: str
    url: str
    snippet: str


class SearchCapExceeded(Exception):
    """Raised when a run exceeds its per-run search cap."""


_run_search_counts: dict[str, int] = {}


def reset_run_search_count(run_id: str) -> None:
    _run_search_counts[run_id] = 0


def _check_and_increment(run_id: str) -> None:
    count = _run_search_counts.get(run_id, 0)
    if count >= settings.max_searches_per_run:
        raise SearchCapExceeded(
            f"Search cap of {settings.max_searches_per_run} reached for run {run_id}"
        )
    _run_search_counts[run_id] = count + 1


def search_web(query: str, run_id: str = "default", max_results: int = 5) -> List[SearchResult]:
    """Search the web for `query`. Raises SearchCapExceeded once the per-run cap is hit."""
    _check_and_increment(run_id)

    if settings.tavily_api_key:
        return _search_tavily(query, max_results)
    return _search_ddg(query, max_results)


def _search_tavily(query: str, max_results: int) -> List[SearchResult]:
    from tavily import TavilyClient

    client = TavilyClient(api_key=settings.tavily_api_key)
    resp = client.search(query=query, max_results=max_results)
    results: List[SearchResult] = []
    for item in resp.get("results", []):
        results.append(
            SearchResult(
                title=item.get("title", ""),
                url=item.get("url", ""),
                snippet=item.get("content", ""),
            )
        )
    return results


def _search_ddg(query: str, max_results: int) -> List[SearchResult]:
    from ddgs import DDGS

    results: List[SearchResult] = []
    with DDGS() as ddgs:
        for item in ddgs.text(query, max_results=max_results):
            results.append(
                SearchResult(
                    title=item.get("title", ""),
                    url=item.get("href", item.get("url", "")),
                    snippet=item.get("body", ""),
                )
            )
    return results
