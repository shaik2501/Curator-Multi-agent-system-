"""LangGraph StateGraph wiring for Curator.

START -> supervisor
supervisor -> (conditional edge on next_agent) -> web | data | coding | image | writing
each worker -> supervisor
supervisor -> debate (writer <-> critic, max N rounds) -> synthesis
synthesis -> END

Supervisor is the only router; workers never call each other directly.
Hard caps (MAX_SUPERVISOR_TURNS, MAX_DEBATE_ROUNDS) force synthesis when hit.
"""
from __future__ import annotations

import asyncio
import uuid
from typing import Any, Callable, Optional

from langgraph.graph import END, StateGraph

from app import memory
from app.agents import coding as coding_agent
from app.agents import critic as critic_agent
from app.agents import data as data_agent
from app.agents import image as image_agent
from app.agents import supervisor as supervisor_agent
from app.agents import synthesis as synthesis_agent
from app.agents import web as web_agent
from app.agents import writing as writing_agent
from app.config import settings
from app.state import Critique, Note, ResearchState

EventCallback = Optional[Callable[[str, dict], None]]

_WORKER_RUNNERS = {
    "web": web_agent.run,
    "data": data_agent.run,
    "coding": coding_agent.run,
    "image": image_agent.run,
    "writing": None,  # writing agent produces a draft string, handled specially
}


def _emit(callback: EventCallback, event_type: str, data: dict) -> None:
    if callback is not None:
        callback(event_type, data)


def _supervisor_node(callback: EventCallback):
    def node(state: ResearchState) -> ResearchState:
        turns = state.get("supervisor_turns", 0)
        _emit(callback, "agent_started", {"agent": "supervisor", "turn": turns + 1})

        if turns >= settings.max_supervisor_turns:
            state["next_agent"] = "__force_synthesis__"
            _emit(
                callback,
                "agent_message",
                {
                    "agent": "supervisor",
                    "message": f"Max supervisor turns ({settings.max_supervisor_turns}) reached; forcing synthesis.",
                },
            )
            return state

        decision = supervisor_agent.decide(state)
        state["supervisor_turns"] = turns + 1

        if decision.get("action") == "finish_research":
            state["next_agent"] = "__debate_or_synthesis__"
            _emit(
                callback,
                "agent_message",
                {"agent": "supervisor", "message": "Research complete; moving to debate/synthesis."},
            )
            return state

        state["next_agent"] = decision["next_agent"]
        state["task"] = decision.get("task", "")
        state["reason"] = decision.get("reason", "")
        _emit(
            callback,
            "agent_message",
            {
                "agent": "supervisor",
                "message": f"Routing to {decision['next_agent']}: {decision.get('task', '')}",
                "reason": decision.get("reason", ""),
            },
        )
        return state

    return node


def _make_worker_node(agent_name: str, callback: EventCallback):
    def node(state: ResearchState) -> ResearchState:
        task = state.get("task", "")
        _emit(callback, "agent_started", {"agent": agent_name, "task": task})

        if agent_name == "writing":
            draft = writing_agent.run(state, task)
            state["draft"] = draft
            note = Note(agent="writing", content=f"Draft produced ({len(draft)} chars).", sources=[])
        else:
            runner = _WORKER_RUNNERS[agent_name]
            note = runner(state, task)

        notes = state.get("notes", [])
        notes.append(note)
        state["notes"] = notes

        memory.add_note(state.get("run_id", "default"), note)
        from app.db import persist_note

        persist_note(state.get("run_id", "default"), note.agent, note.content, note.sources)

        _emit(
            callback,
            "note_added",
            {
                "agent": note.agent,
                "content": note.content[:500],
                "sources": note.sources,
                "image_url": note.image_url,
            },
        )
        _emit(callback, "agent_message", {"agent": agent_name, "message": "Task complete; returning to supervisor."})
        return state

    return node


def _route_from_supervisor(state: ResearchState) -> str:
    next_agent = state.get("next_agent", "")
    if next_agent == "__force_synthesis__":
        return "debate"
    if next_agent == "__debate_or_synthesis__":
        return "debate"
    if next_agent in ("web", "data", "coding", "writing", "image"):
        return next_agent
    return "debate"


def _debate_node(callback: EventCallback):
    def node(state: ResearchState) -> ResearchState:
        rounds = state.get("debate_rounds", 0)

        if not state.get("draft"):
            state["draft"] = writing_agent.run(state, state.get("goal", ""))
            _emit(callback, "debate_turn", {"role": "writer", "round": rounds, "message": "Initial draft written."})

        if rounds >= settings.max_debate_rounds:
            _emit(
                callback,
                "agent_message",
                {"agent": "critic", "message": f"Max debate rounds ({settings.max_debate_rounds}) reached."},
            )
            return state

        round_number = rounds + 1
        _emit(callback, "agent_started", {"agent": "critic", "round": round_number})
        critique = critic_agent.run(state, round_number)
        critiques = state.get("critiques", [])
        critiques.append(critique)
        state["critiques"] = critiques
        state["debate_rounds"] = round_number
        _emit(
            callback,
            "debate_turn",
            {"role": "critic", "round": round_number, "issues": critique.issues, "summary": critique.summary},
        )

        if critique.issues:
            _emit(callback, "agent_started", {"agent": "writing", "round": round_number, "revision": True})
            state["draft"] = writing_agent.run(state, state.get("goal", ""))
            _emit(
                callback,
                "debate_turn",
                {"role": "writer", "round": round_number, "message": "Draft revised based on critique."},
            )

        return state

    return node


def _route_from_debate(state: ResearchState) -> str:
    rounds = state.get("debate_rounds", 0)
    critiques = state.get("critiques", [])
    last_issues = critiques[-1].issues if critiques else []

    if rounds >= settings.max_debate_rounds:
        return "synthesis"
    if not last_issues:
        return "synthesis"
    return "debate"


def _synthesis_node(callback: EventCallback):
    def node(state: ResearchState) -> ResearchState:
        _emit(callback, "agent_started", {"agent": "synthesis"})
        report = synthesis_agent.run(state)
        state["report"] = report
        state["finished"] = True
        _emit(callback, "report_ready", {"report": report})
        return state

    return node


def build_graph(callback: EventCallback = None):
    """Build (and compile) the Curator LangGraph StateGraph.

    `callback(event_type: str, data: dict)` is invoked synchronously as the
    graph executes; run_manager wraps this to publish SSE events. No LLM
    client is instantiated here — this function is safe to call without any
    API keys present.
    """
    graph = StateGraph(ResearchState)

    graph.add_node("supervisor", _supervisor_node(callback))
    graph.add_node("web", _make_worker_node("web", callback))
    graph.add_node("data", _make_worker_node("data", callback))
    graph.add_node("coding", _make_worker_node("coding", callback))
    graph.add_node("image", _make_worker_node("image", callback))
    graph.add_node("writing", _make_worker_node("writing", callback))
    graph.add_node("debate", _debate_node(callback))
    graph.add_node("synthesis", _synthesis_node(callback))

    graph.set_entry_point("supervisor")

    graph.add_conditional_edges(
        "supervisor",
        _route_from_supervisor,
        {
            "web": "web",
            "data": "data",
            "coding": "coding",
            "image": "image",
            "writing": "writing",
            "debate": "debate",
        },
    )
    graph.add_edge("web", "supervisor")
    graph.add_edge("data", "supervisor")
    graph.add_edge("coding", "supervisor")
    graph.add_edge("image", "supervisor")
    graph.add_edge("writing", "supervisor")

    graph.add_conditional_edges("debate", _route_from_debate, {"debate": "debate", "synthesis": "synthesis"})
    graph.add_edge("synthesis", END)

    return graph.compile()


def new_run_id() -> str:
    return uuid.uuid4().hex[:12]
