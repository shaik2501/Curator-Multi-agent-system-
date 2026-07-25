"""Tests that a fatal provider error (missing/unknown LLM config, on any
one of the 7 per-role assignments) fails the run cleanly and quickly,
instead of looping through supervisor turns and completing with a garbage
report."""
from __future__ import annotations

import asyncio
import time

import pytest

from app import db
from app.db import LLMConfig
from app.llm import ProviderUnavailable, check_config_available

from tests._helpers import make_agent_configs, make_snapshot


def test_check_config_available_raises_for_unknown_id():
    with pytest.raises(ProviderUnavailable):
        check_config_available("does-not-exist")


def test_check_config_available_raises_when_key_missing():
    config = db.create_llm_config(
        LLMConfig(
            id="cfg-no-key",
            label="Claude no key",
            provider_type="claude",
            api_key=None,
            model="claude-sonnet-5",
            status="unverified",
        )
    )
    with pytest.raises(ProviderUnavailable):
        check_config_available(config.id)


def test_run_fails_fast_with_unknown_config_id_for_one_role():
    """Every role must resolve to a real config — a bad id on even a single
    role (here: 'web') must fail the whole run fast, naming that role."""
    from app.run_manager import _execute_run

    config = db.create_llm_config(
        LLMConfig(
            id="cfg-ok-for-others",
            label="Claude OK",
            provider_type="claude",
            api_key="sk-ant-fake",
            model="claude-sonnet-5",
            status="verified",
        )
    )
    agent_configs = make_agent_configs(config.id)
    agent_configs["web"] = "does-not-exist"

    run_id = "test-provider-fail-run"
    db.create_run(run_id, "smoke test run", make_snapshot(config))

    start = time.monotonic()
    asyncio.run(_execute_run(run_id, "smoke test run", agent_configs))
    elapsed = time.monotonic() - start

    run = db.get_run(run_id)
    assert run.status == "failed"
    assert run.error
    assert "web" in run.error
    assert "does-not-exist" in run.error

    events = db.get_events(run_id)
    error_events = [e for e in events if e.event_type == "error"]
    assert len(error_events) == 1
    assert "does-not-exist" in error_events[0].data

    # Fails fast: no 12-turn supervisor loop, no LLM calls attempted.
    assert elapsed < 5.0

    agent_started_events = [e for e in events if e.event_type == "agent_started"]
    assert len(agent_started_events) == 0


def test_run_fails_fast_with_config_missing_key():
    from app.run_manager import _execute_run

    config = db.create_llm_config(
        LLMConfig(
            id="cfg-missing-key-run",
            label="Claude missing key",
            provider_type="claude",
            api_key=None,
            model="claude-sonnet-5",
            status="unverified",
        )
    )
    agent_configs = make_agent_configs(config.id)

    run_id = "test-provider-fail-missing-key-run"
    db.create_run(run_id, "smoke test run", make_snapshot(config))

    asyncio.run(_execute_run(run_id, "smoke test run", agent_configs))

    run = db.get_run(run_id)
    assert run.status == "failed"
    assert run.error


def test_run_fails_cleanly_on_mid_run_billing_error(monkeypatch):
    """Regression test: a config with a present, syntactically-fine API key
    passes the upfront check_config_available fast-path, so the run actually
    enters the graph. If the *first real* llm.invoke() call (the
    supervisor's routing decision) fails with a billing/auth-style SDK
    error, that must propagate as ProviderUnavailable and fail the run
    cleanly — not get caught by the supervisor's malformed-JSON retry loop
    and eventually swallowed into 12 turns of garbage notes/drafts with the
    raw API error text embedded in a fake "completed" report."""
    from app.run_manager import _execute_run

    class ExplodingLLM:
        def invoke(self, messages):
            # Shaped like a real Anthropic 400 billing error, the exact
            # pattern from the regression: caught previously by agents'
            # broad `except Exception`, stuffed into note/draft text, and
            # looped on for all 12 supervisor turns instead of failing.
            raise RuntimeError(
                "Error code: 400 - {'type': 'error', 'error': {'type': "
                "'invalid_request_error', 'message': 'Your credit balance "
                "is too low to access the Anthropic API. Please go to "
                "Plans & Billing to upgrade or purchase credits.'}}"
            )

    monkeypatch.setattr("app.llm._build_client", lambda config: ExplodingLLM())

    config = db.create_llm_config(
        LLMConfig(
            id="cfg-billing-explode",
            label="Claude out of credit",
            provider_type="claude",
            api_key="sk-ant-real-looking-but-broke",
            model="claude-sonnet-5",
            status="verified",
        )
    )
    agent_configs = make_agent_configs(config.id)

    run_id = "test-mid-run-billing-failure"
    db.create_run(run_id, "goal", make_snapshot(config))

    start = time.monotonic()
    asyncio.run(_execute_run(run_id, "goal", agent_configs))
    elapsed = time.monotonic() - start

    run = db.get_run(run_id)
    assert run.status == "failed"
    assert run.error
    assert "credit balance" in run.error.lower()
    # The report must stay empty/None — no garbage draft text, no raw API
    # error embedded in a fake "completed" report.
    assert not run.report

    events = db.get_events(run_id)
    error_events = [e for e in events if e.event_type == "error"]
    assert len(error_events) == 1
    assert "credit balance" in error_events[0].data.lower()

    # Fails on the very first bad call — not after burning through all 12
    # supervisor turns retrying/looping on an unusable credential.
    assert elapsed < 5.0
    supervisor_turns_seen = [
        e for e in events if e.event_type == "agent_started" and '"agent": "supervisor"' in e.data
    ]
    assert len(supervisor_turns_seen) <= 1
