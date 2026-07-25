"""Shared state definitions for the Curator LangGraph graph."""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, TypedDict

from pydantic import BaseModel, Field

# The 8 agent roles, each independently assigned to its own saved LLMConfig.
# "image" is the only role that requires a capability-checked (image_capable)
# config — see app.main._resolve_agent_model_snapshot.
AGENT_ROLES = (
    "supervisor",
    "web",
    "data",
    "coding",
    "writing",
    "critic",
    "synthesis",
    "image",
)


class Subtask(BaseModel):
    id: str
    description: str
    agent: str
    status: Literal["pending", "in_progress", "done"] = "pending"


class Note(BaseModel):
    agent: str
    content: str
    sources: List[str] = Field(default_factory=list)
    # Servable path (e.g. "/api/images/{run_id}/{filename}") for the image
    # worker's output. None for every other agent.
    image_url: Optional[str] = None


class Critique(BaseModel):
    round: int
    issues: List[str] = Field(default_factory=list)
    summary: str = ""


class ResearchState(TypedDict, total=False):
    run_id: str
    goal: str
    plan: List[Subtask]
    notes: List[Note]
    draft: str
    critiques: List[Critique]
    report: str
    next_agent: str
    task: str
    reason: str
    agent_configs: Dict[str, str]  # role -> LLMConfig id, keys = AGENT_ROLES
    supervisor_turns: int
    debate_rounds: int
    finished: bool
    error: Optional[str]


def new_state(
    run_id: str, goal: str, agent_configs: Optional[Dict[str, str]] = None
) -> "ResearchState":
    return {
        "run_id": run_id,
        "goal": goal,
        "plan": [],
        "notes": [],
        "draft": "",
        "critiques": [],
        "report": "",
        "next_agent": "",
        "task": "",
        "reason": "",
        "agent_configs": agent_configs or {},
        "supervisor_turns": 0,
        "debate_rounds": 0,
        "finished": False,
        "error": None,
    }
