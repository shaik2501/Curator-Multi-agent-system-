"""Async per-run event bus used to bridge the graph execution to SSE clients."""
from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional

from app.db import persist_event

# Sentinel put on a run's queue to signal "no more events".
STREAM_DONE = object()

_queues: Dict[str, "asyncio.Queue"] = {}
_lock = asyncio.Lock()


def _get_or_create_queue(run_id: str) -> "asyncio.Queue":
    queue = _queues.get(run_id)
    if queue is None:
        queue = asyncio.Queue()
        _queues[run_id] = queue
    return queue


async def publish(run_id: str, event_type: str, data: Optional[dict] = None) -> None:
    """Persist an event to SQLite and push it onto the run's live queue."""
    data = data or {}
    event = persist_event(run_id, event_type, data)
    queue = _get_or_create_queue(run_id)
    await queue.put({"event": event_type, "data": data, "id": event.id})


async def close_stream(run_id: str) -> None:
    queue = _get_or_create_queue(run_id)
    await queue.put(STREAM_DONE)


async def subscribe(run_id: str):
    """Async generator yielding live events for a run (does not replay history)."""
    queue = _get_or_create_queue(run_id)
    while True:
        item = await queue.get()
        if item is STREAM_DONE:
            break
        yield item


def cleanup(run_id: str) -> None:
    _queues.pop(run_id, None)
