"""Tests for POST /api/runs/{id}/stop: it must genuinely interrupt an
in-flight run (not just fake a 200), and must reject stopping a run that
isn't in progress rather than silently succeeding."""
from __future__ import annotations

import asyncio
import time

import pytest
from fastapi.testclient import TestClient

from app import db
from app.db import LLMConfig

from tests._helpers import make_agent_configs, make_snapshot


def _make_config(config_id: str) -> LLMConfig:
    return db.create_llm_config(
        LLMConfig(
            id=config_id,
            label="Test Claude",
            provider_type="claude",
            api_key="sk-ant-fake",
            model="claude-sonnet-5",
            status="verified",
        )
    )


def test_stop_cancels_in_flight_run(monkeypatch):
    """Cancelling mid-flight (not a run that already finished) must actually
    cancel the asyncio.Task and mark the run 'stopped' — proving the stop
    endpoint interrupts real work rather than just flipping a flag."""
    import app.run_manager as run_manager

    # No real provider/LLM/graph work: check_config_available passes
    # instantly, and the "graph" blocks for a long time inside invoke() so
    # we have a wide window to cancel it mid-flight.
    monkeypatch.setattr(run_manager, "check_config_available", lambda provider_config_id: None)

    class SlowGraph:
        def invoke(self, state, config=None):
            time.sleep(10)
            return {"report": "should never be reached"}

    monkeypatch.setattr(run_manager, "build_graph", lambda callback=None: SlowGraph())

    config = _make_config("cfg-stop-inflight")
    agent_configs = make_agent_configs(config.id)
    run_id = "test-stop-inflight-run"
    db.create_run(run_id, "goal", make_snapshot(config))

    async def scenario():
        await run_manager.start_run(run_id, "goal", agent_configs)
        # Let the task actually get scheduled and enter graph.invoke().
        await asyncio.sleep(0.3)

        task = run_manager.get_task(run_id)
        assert task is not None, "run should be in-flight before we try to stop it"
        assert not task.done()

        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        return task

    task = asyncio.run(scenario())
    assert task.cancelled()

    run = db.get_run(run_id)
    assert run.status == "stopped"
    assert run.error is None


def test_stop_endpoint_cancels_via_http(monkeypatch):
    """End-to-end through the actual FastAPI route: POST .../stop on an
    in-flight run returns success and results in status=stopped shortly
    after."""
    import app.run_manager as run_manager
    from app.main import app

    monkeypatch.setattr(run_manager, "check_config_available", lambda provider_config_id: None)

    class SlowGraph:
        def invoke(self, state, config=None):
            time.sleep(10)
            return {"report": "should never be reached"}

    monkeypatch.setattr(run_manager, "build_graph", lambda callback=None: SlowGraph())

    config = _make_config("cfg-stop-http")
    agent_configs = make_agent_configs(config.id)
    run_id = "test-stop-http-run"
    db.create_run(run_id, "goal", make_snapshot(config))

    async def scenario():
        await run_manager.start_run(run_id, "goal", agent_configs)
        await asyncio.sleep(0.3)

        client = TestClient(app)
        resp = client.post(f"/api/runs/{run_id}/stop")
        assert resp.status_code == 200

        task = run_manager.get_task(run_id)
        if task is not None:
            try:
                await task
            except asyncio.CancelledError:
                pass

    asyncio.run(scenario())

    run = db.get_run(run_id)
    assert run.status == "stopped"


def test_stop_run_not_found_returns_404():
    from app.main import app

    client = TestClient(app)
    resp = client.post("/api/runs/does-not-exist/stop")
    assert resp.status_code == 404


def test_stop_already_finished_run_returns_non_200():
    """Stopping a run that has already completed must not silently succeed
    with a fake 200 — it should report that there's nothing to stop."""
    from app.main import app

    config = _make_config("cfg-stop-finished")
    run_id = "test-stop-finished-run"
    db.create_run(run_id, "goal", make_snapshot(config))
    db.update_run_status(run_id, "completed", report="already done")

    client = TestClient(app)
    resp = client.post(f"/api/runs/{run_id}/stop")
    assert resp.status_code == 409

    run = db.get_run(run_id)
    assert run.status == "completed"
