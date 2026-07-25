"""Supervisor agent: the sole router in the graph.

Outputs JSON: {"next_agent": "...", "task": "...", "reason": "..."}
or {"action": "finish_research"}.

Parsing is robust to malformed LLM output: retried up to 3 times, and falls
back to routing to the writing agent if all retries fail.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple

from app.llm import ProviderUnavailable, get_llm, invoke_llm
from app.state import Note, ResearchState

VALID_AGENTS = {"web", "data", "coding", "image", "writing"}

_AGENT_DISPLAY_NAMES = {
    "web": "Web Research",
    "data": "Data Analysis",
    "coding": "Coding",
    "image": "Image Generation",
    "writing": "Writing",
}

# At/above this many consecutive turns on the same worker, surface a
# repetition signal in the prompt so the model can judge for itself whether
# it's still learning something new or just rephrasing the same search.
_REPETITION_SIGNAL_THRESHOLD = 2

SYSTEM_PROMPT = """You manage a research team with these workers: web, data, coding, image, writing.
- web: searches the internet and fetches pages for facts with sources.
- data: analyzes numbers/tables already gathered into comparisons and stats.
- coding: writes and runs small python snippets for computation/examples.
- image: generates an actual image (diagram, illustration, chart mockup, etc.)
  to include in the report. Only use this when a generated visual would
  genuinely help convey something in the goal — most research goals don't
  need one, so don't route here by default or "just in case."
- writing: drafts report sections from the shared research notes.

Given the research goal and a summary of notes gathered so far, decide the single
next best action. Respond with ONLY a JSON object, no prose, no markdown fences.

Either:
{"next_agent": "web" | "data" | "coding" | "image" | "writing", "task": "<specific instruction>", "reason": "<why>"}

or, once there is enough material for a full draft report:
{"action": "finish_research"}

Important judgment calls:
- Prefer distinct, substantive angles over rephrased repeats of a search you
  already ran. If the most recent notes from a worker already substantively
  cover the goal (or a sub-question of it), do not send that same worker
  back to fetch a near-duplicate of what it already found — either route to
  a different worker that would add something new, or move to
  finish_research.
- There is no fixed note-count threshold to hit before finishing — some
  goals need more digging, some need very little. Judge coverage, not
  quantity: once you have a handful of solid, distinct notes that
  meaningfully address the goal, bias toward finish_research rather than
  defaulting to "search again just in case."
- If you notice you are about to route to the same worker you've already
  used several times in a row for very similar tasks, that is a strong
  signal you have likely hit diminishing returns — treat it as a reason to
  reconsider, not a reason to keep going out of habit.
"""


def _extract_json(text: str) -> Dict[str, Any]:
    text = text.strip()
    # Strip markdown code fences if present.
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1)
    else:
        brace_match = re.search(r"\{.*\}", text, re.DOTALL)
        if brace_match:
            text = brace_match.group(0)
    return json.loads(text)


def _fallback_decision(reason: str) -> Dict[str, Any]:
    return {
        "next_agent": "writing",
        "task": "Draft the report using whatever notes are currently available.",
        "reason": reason,
    }


def _notes_summary(state: ResearchState) -> str:
    notes = state.get("notes", [])
    if not notes:
        return "(no notes gathered yet)"
    lines = [f"- [{n.agent}] {n.content[:200]}" for n in notes[-10:]]
    return "\n".join(lines)


def _consecutive_repeat(notes: List[Note]) -> Tuple[Optional[str], int]:
    """How many trailing notes in a row came from the same agent.

    Returns (agent_name, count) — e.g. if the last 4 notes were all from
    "web", returns ("web", 4). Returns (None, 0) if there are no notes yet.
    This is computed from the notes list itself (each worker turn appends
    exactly one note) rather than a separate counter, so it can't drift out
    of sync with what actually happened.
    """
    if not notes:
        return None, 0
    last_agent = notes[-1].agent
    count = 0
    for note in reversed(notes):
        if note.agent == last_agent:
            count += 1
        else:
            break
    return last_agent, count


def _repetition_signal_line(notes: List[Note]) -> str:
    """Build the "you've routed here N times in a row" prompt line, or an
    empty string if there's no meaningful repetition yet."""
    repeat_agent, repeat_count = _consecutive_repeat(notes)
    if not repeat_agent or repeat_count < _REPETITION_SIGNAL_THRESHOLD:
        return ""
    display_name = _AGENT_DISPLAY_NAMES.get(repeat_agent, repeat_agent)
    return (
        f"\nRepetition signal: you have routed to {display_name} {repeat_count} times "
        "in a row now. Consider whether you have enough to move on, rather than "
        "requesting another near-duplicate search."
    )


def _build_user_prompt(state: ResearchState) -> str:
    """Build the per-turn user prompt, including the repetition signal.
    Factored out from decide() so it's directly testable without mocking
    an LLM call."""
    goal = state.get("goal", "")
    notes_summary = _notes_summary(state)
    has_draft = bool(state.get("draft"))
    repetition_line = _repetition_signal_line(state.get("notes", []))

    return (
        f"Goal: {goal}\n\n"
        f"Notes so far:\n{notes_summary}\n\n"
        f"Draft exists: {has_draft}\n"
        f"{repetition_line}\n\n"
        "Decide the next action."
    )


def decide(state: ResearchState) -> Dict[str, Any]:
    """Ask the LLM for the next routing decision, with retry + fallback."""
    provider_config_id = state.get("agent_configs", {}).get("supervisor", "")
    user_prompt = _build_user_prompt(state)

    last_error: Exception | None = None
    for attempt in range(3):
        try:
            llm = get_llm(provider_config_id=provider_config_id)
            response = invoke_llm(
                llm,
                [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ]
            )
            content = response.content if hasattr(response, "content") else str(response)
            if isinstance(content, list):
                content = "".join(
                    part.get("text", "") if isinstance(part, dict) else str(part)
                    for part in content
                )
            decision = _extract_json(content)

            if decision.get("action") == "finish_research":
                return {"action": "finish_research"}

            next_agent = decision.get("next_agent")
            if next_agent not in VALID_AGENTS:
                raise ValueError(f"invalid next_agent: {next_agent!r}")

            return {
                "next_agent": next_agent,
                "task": decision.get("task", ""),
                "reason": decision.get("reason", ""),
            }
        except ProviderUnavailable:
            # Fatal: the provider itself can't be used (bad/missing key,
            # unreachable Ollama). Retrying model calls won't help — let
            # this propagate so the run fails cleanly instead of looping.
            raise
        except Exception as exc:  # noqa: BLE001 - broad on purpose, retried below
            last_error = exc
            continue

    return _fallback_decision(f"Fallback after {attempt + 1} failed parse attempts: {last_error}")
