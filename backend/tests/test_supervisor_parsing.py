"""Tests for supervisor routing JSON parsing, including malformed-input fallback."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from app.agents import supervisor
from app.state import new_state


class FakeLLM:
    def __init__(self, responses):
        self._responses = list(responses)

    def invoke(self, messages):
        content = self._responses.pop(0)
        return SimpleNamespace(content=content)


def test_valid_json_routes_to_agent():
    state = new_state("run1", "test goal")
    fake = FakeLLM(['{"next_agent": "web", "task": "search stuff", "reason": "need facts"}'])
    with patch("app.agents.supervisor.get_llm", return_value=fake):
        decision = supervisor.decide(state)
    assert decision["next_agent"] == "web"
    assert decision["task"] == "search stuff"


def test_finish_research_action():
    state = new_state("run1", "test goal")
    fake = FakeLLM(['{"action": "finish_research"}'])
    with patch("app.agents.supervisor.get_llm", return_value=fake):
        decision = supervisor.decide(state)
    assert decision["action"] == "finish_research"


def test_json_wrapped_in_markdown_fence():
    state = new_state("run1", "test goal")
    fake = FakeLLM(['```json\n{"next_agent": "data", "task": "analyze", "reason": "r"}\n```'])
    with patch("app.agents.supervisor.get_llm", return_value=fake):
        decision = supervisor.decide(state)
    assert decision["next_agent"] == "data"


def test_malformed_json_falls_back_to_writing_after_retries():
    state = new_state("run1", "test goal")
    fake = FakeLLM(["not json at all", "still not json", "nope"])
    with patch("app.agents.supervisor.get_llm", return_value=fake):
        decision = supervisor.decide(state)
    assert decision["next_agent"] == "writing"


def test_invalid_agent_name_falls_back():
    state = new_state("run1", "test goal")
    fake = FakeLLM(
        [
            '{"next_agent": "bogus_agent", "task": "x", "reason": "y"}',
            '{"next_agent": "bogus_agent", "task": "x", "reason": "y"}',
            '{"next_agent": "bogus_agent", "task": "x", "reason": "y"}',
        ]
    )
    with patch("app.agents.supervisor.get_llm", return_value=fake):
        decision = supervisor.decide(state)
    assert decision["next_agent"] == "writing"
