"""Tests that the supervisor-turn cap and debate-round cap are enforced."""
from __future__ import annotations

from unittest.mock import patch

from app.config import settings
from app.graph import _route_from_debate, _route_from_supervisor
from app.state import Critique, new_state


def test_supervisor_route_forces_debate_after_cap():
    state = new_state("run1", "goal")
    state["next_agent"] = "__force_synthesis__"
    assert _route_from_supervisor(state) == "debate"


def test_supervisor_route_normal_agent():
    state = new_state("run1", "goal")
    state["next_agent"] = "web"
    assert _route_from_supervisor(state) == "web"


def test_debate_route_stops_at_max_rounds():
    state = new_state("run1", "goal")
    state["debate_rounds"] = settings.max_debate_rounds
    state["critiques"] = [Critique(round=settings.max_debate_rounds, issues=["still bad"], summary="s")]
    assert _route_from_debate(state) == "synthesis"


def test_debate_route_continues_when_issues_and_under_cap():
    state = new_state("run1", "goal")
    state["debate_rounds"] = 1
    state["critiques"] = [Critique(round=1, issues=["missing sources"], summary="s")]
    assert settings.max_debate_rounds > 1  # sanity: cap allows another round
    assert _route_from_debate(state) == "debate"


def test_debate_route_stops_when_no_issues():
    state = new_state("run1", "goal")
    state["debate_rounds"] = 1
    state["critiques"] = [Critique(round=1, issues=[], summary="looks good")]
    assert _route_from_debate(state) == "synthesis"


def test_supervisor_node_caps_turns_at_max():
    from app.graph import _supervisor_node

    node = _supervisor_node(callback=None)
    state = new_state("run1", "goal")
    state["supervisor_turns"] = settings.max_supervisor_turns

    result = node(state)
    assert result["next_agent"] == "__force_synthesis__"
