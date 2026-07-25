"""Drives a Curator run in the background, wiring graph events to SSE + SQLite."""
from __future__ import annotations

import asyncio
import traceback
from typing import Dict

from app import db
from app.events import close_stream, publish
from app.graph import build_graph
from app.llm import ProviderUnavailable, check_config_available
from app.state import AGENT_ROLES, new_state

_run_tasks: dict[str, asyncio.Task] = {}


async def start_run(run_id: str, goal: str, agent_configs: Dict[str, str]) -> None:
    """Schedule a run as an asyncio background task."""
    task = asyncio.create_task(_execute_run(run_id, goal, agent_configs))
    _run_tasks[run_id] = task


def get_task(run_id: str) -> "asyncio.Task | None":
    """Return the in-flight asyncio.Task driving a run, or None if the run
    isn't currently in progress (already finished, or never started)."""
    return _run_tasks.get(run_id)


async def _fail_run(run_id: str, message: str, traceback_text: str = "") -> None:
    await publish(run_id, "error", {"message": message, "traceback": traceback_text})
    db.update_run_status(run_id, "failed", error=message)


def _check_all_agent_configs(agent_configs: Dict[str, str]) -> None:
    """Validate every role's assigned config up front, before touching the
    graph at all. Raises ProviderUnavailable naming the first bad role found
    — same fail-fast rationale as the single-config check this replaced,
    just extended to all 7 independently-assignable roles."""
    for role in AGENT_ROLES:
        config_id = agent_configs.get(role, "")
        try:
            check_config_available(config_id)
        except ProviderUnavailable as exc:
            raise ProviderUnavailable(f"[{role}] {exc}") from exc


async def _execute_run(run_id: str, goal: str, agent_configs: Dict[str, str]) -> None:
    loop = asyncio.get_event_loop()
    db.update_run_status(run_id, "running")

    # Fail fast, before touching the graph at all, if any role's assigned
    # LLM config obviously can't be used (missing/unknown config id, missing
    # key, unreachable Ollama). This is the cheap path: no supervisor turns,
    # no fallback-routing loop.
    try:
        await asyncio.to_thread(_check_all_agent_configs, agent_configs)
    except ProviderUnavailable as exc:
        await _fail_run(run_id, str(exc))
        await close_stream(run_id)
        _run_tasks.pop(run_id, None)
        return

    def sync_callback(event_type: str, data: dict) -> None:
        # Called from the (synchronous) graph execution thread; schedule the
        # coroutine on the main event loop thread-safely.
        asyncio.run_coroutine_threadsafe(publish(run_id, event_type, data), loop)

    try:
        graph = build_graph(callback=sync_callback)
        state = new_state(run_id, goal, agent_configs)

        from app.tools.search import reset_run_search_count

        reset_run_search_count(run_id)

        final_state = await asyncio.to_thread(graph.invoke, state, {"recursion_limit": 100})

        report = final_state.get("report", "")
        db.update_run_status(run_id, "completed", report=report)
    except asyncio.CancelledError:
        # CancelledError is a BaseException (not Exception) in Python 3.8+,
        # so it would otherwise skip straight past our except-Exception
        # handler below and propagate out of this coroutine, skipping the
        # "stopped" status update (though the `finally` block would still
        # run). Handle it explicitly: this is a user-initiated stop, not a
        # failure, so no error text and no `error` SSE event.
        #
        # Note: asyncio.to_thread cannot actually interrupt the underlying
        # synchronous graph.invoke() call running in the worker thread — the
        # thread keeps running to completion/its next checkpoint in the
        # background — but cancelling the awaiting task here immediately
        # reflects the stop in run status, which is what the API contract
        # (and the frontend) rely on.
        db.update_run_status(run_id, "stopped")
        raise
    except ProviderUnavailable as exc:
        # Belt-and-suspenders: a provider error surfaced mid-run (e.g. the
        # key was revoked between the upfront check and the first call, or
        # Ollama died mid-run) also fails the run cleanly instead of
        # continuing through the supervisor/debate/synthesis loop.
        await _fail_run(run_id, str(exc), traceback.format_exc())
    except Exception as exc:  # noqa: BLE001
        tb = traceback.format_exc()
        await _fail_run(run_id, str(exc), tb)
    finally:
        await close_stream(run_id)
        _run_tasks.pop(run_id, None)
