"""FastAPI application: Curator API + SSE streaming."""
from __future__ import annotations

import asyncio
import json
from typing import Dict, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from app import db, memory
from app.config import settings
from app.db import LLMConfig
from app.events import subscribe
from app.graph import new_run_id
from app.llm import DEFAULT_OLLAMA_BASE_URL, DEFAULT_OLLAMA_MODEL, KNOWN_PROVIDERS, check_ollama_reachable
from app.llm_configs import PRETTY_NAMES, default_label, seed_from_env_if_empty, to_public_dict, verify_config
from app.model_listing import list_models
from app.run_manager import get_task, start_run
from app.state import AGENT_ROLES

# provider_types that can generate images without the user having to opt in
# explicitly (unlike "custom", where we can't infer anything about an
# arbitrary endpoint).
_AUTO_IMAGE_CAPABLE_PROVIDERS = {"openai": True, "gemini": True, "claude": False, "ollama": False}

@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    # One-time seed from .env so a previously-working setup (e.g. a real
    # ANTHROPIC_API_KEY) keeps working with zero user action. After this,
    # .env provider vars are never read again at run time.
    seed_from_env_if_empty()
    yield

app = FastAPI(title="Curator Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# LLM configs — dynamic, user-managed credentials
# ---------------------------------------------------------------------------


class LLMConfigRequest(BaseModel):
    label: Optional[str] = None
    provider_type: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None
    cheap_model: Optional[str] = None
    # Only meaningful for provider_type="custom" — for every other type,
    # image capability is inferred automatically and this is ignored.
    image_capable: Optional[bool] = None


@app.post("/api/llm-configs")
async def create_llm_config(payload: LLMConfigRequest) -> dict:
    provider_type = payload.provider_type
    if provider_type not in KNOWN_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown provider_type {provider_type!r}; must be one of {sorted(KNOWN_PROVIDERS)}",
        )

    api_key = payload.api_key
    base_url = payload.base_url
    model = payload.model
    cheap_model = payload.cheap_model

    if provider_type in ("claude", "openai", "gemini"):
        if not api_key:
            raise HTTPException(
                status_code=400, detail=f"api_key is required for provider_type={provider_type!r}"
            )
        if not model:
            raise HTTPException(
                status_code=400, detail=f"model is required for provider_type={provider_type!r}"
            )
    elif provider_type == "custom":
        if not base_url:
            raise HTTPException(status_code=400, detail="base_url is required for provider_type='custom'")
        if not model:
            raise HTTPException(status_code=400, detail="model is required for provider_type='custom'")
    elif provider_type == "ollama":
        base_url = base_url or DEFAULT_OLLAMA_BASE_URL
        model = model or DEFAULT_OLLAMA_MODEL

    label = payload.label.strip() if payload.label and payload.label.strip() else default_label(provider_type)

    if provider_type == "custom":
        image_capable = bool(payload.image_capable)  # opt-in only, default False
    else:
        image_capable = _AUTO_IMAGE_CAPABLE_PROVIDERS.get(provider_type, False)

    config = LLMConfig(
        id=db.new_id(),
        label=label,
        provider_type=provider_type,
        api_key=api_key,
        base_url=base_url,
        model=model,
        cheap_model=cheap_model,
        image_capable=image_capable,
        status="unverified",
    )
    created = db.create_llm_config(config)
    verified = await asyncio.to_thread(verify_config, created)
    return to_public_dict(verified)


@app.get("/api/llm-configs")
def list_llm_configs() -> list[dict]:
    return [to_public_dict(c) for c in db.list_llm_configs()]


class ListModelsRequest(BaseModel):
    provider_type: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None


@app.post("/api/llm-configs/list-models")
async def list_llm_config_models(payload: ListModelsRequest) -> dict:
    """Stateless: fetches the real list of models the given (not-yet-saved)
    credentials can use, straight from the provider. Never touches the DB,
    never persists or logs the api_key, and always returns 200 — a failed
    fetch is normal expected output in the `error` field, not a server
    error."""
    if payload.provider_type not in KNOWN_PROVIDERS:
        return {"models": [], "error": f"Unknown provider_type {payload.provider_type!r}"}

    result = await asyncio.to_thread(
        list_models, payload.provider_type, payload.api_key, payload.base_url
    )
    return result.to_dict()


@app.post("/api/llm-configs/{config_id}/verify")
async def verify_llm_config(config_id: str) -> dict:
    config = db.get_llm_config(config_id)
    if config is None:
        raise HTTPException(status_code=404, detail="llm config not found")
    verified = await asyncio.to_thread(verify_config, config)
    return to_public_dict(verified)


@app.delete("/api/llm-configs/{config_id}")
def delete_llm_config(config_id: str) -> dict:
    deleted = db.delete_llm_config(config_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="llm config not found")
    return {"id": config_id, "deleted": True}


# ---------------------------------------------------------------------------
# Runs
# ---------------------------------------------------------------------------


class StartRunRequest(BaseModel):
    goal: str
    agent_configs: Dict[str, str]


class StartRunResponse(BaseModel):
    run_id: str


def _resolve_agent_model_snapshot(agent_configs: Dict[str, str]) -> dict:
    """Validate that `agent_configs` has exactly the 7 required role keys,
    each referencing a real LLMConfig, and build the snapshot dict to store
    on the Run row. Raises HTTPException(400) naming the specific missing
    or bad role on failure."""
    missing_roles = [role for role in AGENT_ROLES if not agent_configs.get(role)]
    if missing_roles:
        raise HTTPException(
            status_code=400,
            detail=f"agent_configs is missing required role(s): {missing_roles}",
        )

    snapshot: dict = {}
    for role in AGENT_ROLES:
        config_id = agent_configs[role]
        config = db.get_llm_config(config_id)
        if config is None:
            raise HTTPException(
                status_code=400,
                detail=f"agent_configs.{role} references unknown LLM config {config_id!r}",
            )

        if role == "image" and not config.image_capable:
            pretty = PRETTY_NAMES.get(config.provider_type, config.provider_type)
            raise HTTPException(
                status_code=400,
                detail=(
                    f"{pretty} does not support image generation — choose an "
                    "OpenAI or Gemini config for the image role."
                ),
            )

        snapshot[role] = {
            "config_id": config.id,
            "provider_type": config.provider_type,
            "label": config.label,
        }
    return snapshot


@app.post("/api/runs", response_model=StartRunResponse)
async def create_run(payload: StartRunRequest) -> StartRunResponse:
    if not payload.goal or not payload.goal.strip():
        raise HTTPException(status_code=400, detail="goal must not be empty")

    snapshot = _resolve_agent_model_snapshot(payload.agent_configs)

    run_id = new_run_id()
    db.create_run(run_id, payload.goal, snapshot)
    resolved_agent_configs = {role: snapshot[role]["config_id"] for role in AGENT_ROLES}
    await start_run(run_id, payload.goal, resolved_agent_configs)
    return StartRunResponse(run_id=run_id)


@app.get("/api/runs")
def list_runs() -> list[dict]:
    runs = db.list_runs()
    return [
        {
            "id": r.id,
            "goal": r.goal,
            "agent_model_snapshot": db.run_agent_model_snapshot(r),
            "status": r.status,
            "created_at": r.created_at.isoformat(),
            "updated_at": r.updated_at.isoformat(),
        }
        for r in runs
    ]


@app.get("/api/runs/{run_id}")
def get_run(run_id: str) -> dict:
    run = db.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    return {
        "id": run.id,
        "goal": run.goal,
        "agent_model_snapshot": db.run_agent_model_snapshot(run),
        "status": run.status,
        "report": run.report,
        "error": run.error,
        "created_at": run.created_at.isoformat(),
        "updated_at": run.updated_at.isoformat(),
    }


@app.post("/api/runs/{run_id}/stop")
async def stop_run(run_id: str) -> dict:
    run = db.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")

    task = get_task(run_id)
    if task is None or task.done():
        raise HTTPException(status_code=409, detail="run is not in progress")

    task.cancel()
    return {"id": run_id, "status": "stopping"}


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------


@app.get("/api/settings")
async def get_settings() -> dict:
    return {
        "max_supervisor_turns": settings.max_supervisor_turns,
        "max_debate_rounds": settings.max_debate_rounds,
        "max_searches_per_run": settings.max_searches_per_run,
    }


@app.post("/api/providers/ollama/check")
async def check_ollama() -> dict:
    """Fresh, uncached live reachability check against the default Ollama
    base_url — for a frontend "Test Connection" button not tied to a
    specific saved config. Reuses check_ollama_reachable's short timeout."""
    reachable = await asyncio.to_thread(check_ollama_reachable)
    return {"reachable": reachable}


@app.get("/api/images/{run_id}/{filename}")
def get_image(run_id: str, filename: str) -> FileResponse:
    """Serve an image the "image" agent generated for a run.
    backend/data/images/{run_id}/{filename} -> 404 if it doesn't exist (or
    if run_id/filename try to path-traverse out of the images directory)."""
    images_root = settings.resolved_images_path().resolve()
    candidate = (images_root / run_id / filename).resolve()

    if images_root not in candidate.parents or not candidate.is_file():
        raise HTTPException(status_code=404, detail="image not found")

    return FileResponse(candidate, media_type="image/png")


@app.get("/api/runs/{run_id}/knowledge")
def get_knowledge(run_id: str) -> list[dict]:
    run = db.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    hits = memory.get_all_notes(run_id)
    return [{"agent": h["agent"], "content": h["content"], "sources": h["sources"]} for h in hits]


@app.get("/api/runs/{run_id}/events")
async def stream_events(run_id: str, request: Request):
    run = db.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")

    # Each SSE message carries a stable `id:` (the persisted event's primary
    # key) so the client can dedupe on reconnect. If the client sends back
    # Last-Event-ID, skip persisted events it has already seen instead of
    # replaying the whole history again.
    last_event_id_header = request.headers.get("last-event-id")
    after_id: int | None = None
    if last_event_id_header is not None and last_event_id_header.isdigit():
        after_id = int(last_event_id_header)

    async def event_generator():
        for event in db.get_events(run_id, after_id=after_id):
            yield {"event": event.event_type, "data": event.data, "id": str(event.id)}

        if run.status in ("completed", "failed"):
            return

        async for item in subscribe(run_id):
            yield {
                "event": item["event"],
                "data": json.dumps(item["data"]),
                "id": str(item.get("id", "")),
            }

    return EventSourceResponse(event_generator())
