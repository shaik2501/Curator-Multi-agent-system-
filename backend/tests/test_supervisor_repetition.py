"""Tests that the supervisor's repetition signal (how many consecutive
turns routed to the same worker) is computed correctly and actually threaded
into the prompt sent to the model — this is a pure computation/prompt-
building test, not a live-LLM-behavior test."""
from __future__ import annotations

from app.agents.supervisor import (
    _build_user_prompt,
    _consecutive_repeat,
    _repetition_signal_line,
    _REPETITION_SIGNAL_THRESHOLD,
)
from app.state import Note, new_state


def _notes(*agents: str) -> list[Note]:
    return [Note(agent=a, content=f"note from {a}", sources=[]) for a in agents]


def test_consecutive_repeat_no_notes():
    assert _consecutive_repeat([]) == (None, 0)


def test_consecutive_repeat_single_note():
    assert _consecutive_repeat(_notes("web")) == ("web", 1)


def test_consecutive_repeat_counts_trailing_run_only():
    # data, web, web, web -> trailing run of "web" is 3, the earlier "data"
    # note doesn't extend it.
    notes = _notes("data", "web", "web", "web")
    assert _consecutive_repeat(notes) == ("web", 3)


def test_consecutive_repeat_resets_on_agent_change():
    notes = _notes("web", "web", "web", "data")
    assert _consecutive_repeat(notes) == ("data", 1)


def test_repetition_signal_line_empty_below_threshold():
    notes = _notes("web")  # count=1, below _REPETITION_SIGNAL_THRESHOLD (2)
    assert _repetition_signal_line(notes) == ""


def test_repetition_signal_line_present_at_threshold():
    notes = _notes("web", "web")  # count=2, meets threshold
    line = _repetition_signal_line(notes)
    assert line != ""
    assert "Web Research" in line
    assert "2 times" in line


def test_repetition_signal_line_scales_with_count():
    notes = _notes("web", "web", "web", "web")
    line = _repetition_signal_line(notes)
    assert "4 times" in line


def test_repetition_signal_line_uses_display_name_per_agent():
    notes = _notes("data", "data", "data")
    line = _repetition_signal_line(notes)
    assert "Data Analysis" in line
    assert "3 times" in line


def test_repetition_signal_threshold_is_at_least_two():
    # Sanity: a single turn should never itself be flagged as "repetition".
    assert _REPETITION_SIGNAL_THRESHOLD >= 2


def test_build_user_prompt_includes_repetition_signal_when_present():
    state = new_state("run1", "research goal")
    state["notes"] = _notes("web", "web", "web")

    prompt = _build_user_prompt(state)

    assert "research goal" in prompt
    assert "Repetition signal" in prompt
    assert "Web Research" in prompt
    assert "3 times" in prompt


def test_build_user_prompt_omits_repetition_signal_when_not_repeating():
    state = new_state("run1", "research goal")
    state["notes"] = _notes("web", "data")  # alternating, no repeat

    prompt = _build_user_prompt(state)

    assert "Repetition signal" not in prompt


def test_build_user_prompt_handles_no_notes_at_all():
    state = new_state("run1", "research goal")
    prompt = _build_user_prompt(state)
    assert "no notes gathered yet" in prompt
    assert "Repetition signal" not in prompt
