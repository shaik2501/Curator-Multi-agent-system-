"""SQLModel tables and engine for run persistence."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, Session, SQLModel, create_engine, select, func

from app.config import settings


def new_id() -> str:
    return uuid.uuid4().hex[:12]

_engine = None


def utcnow() -> datetime:
    """Timezone-aware "now" in UTC. Use this everywhere instead of the
    deprecated/naive datetime.utcnow()."""
    return datetime.now(timezone.utc)


def as_utc(dt: datetime) -> datetime:
    """Return `dt` as a timezone-aware UTC datetime.

    SQLite has no native timezone type, so SQLAlchemy round-trips datetimes
    as naive values even though everything we write is already UTC. Attach
    the UTC tzinfo back on read so callers (and .isoformat()) always see the
    offset, e.g. "...+00:00" instead of an ambiguous naive string.
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def get_engine():
    global _engine
    if _engine is None:
        db_path = settings.resolved_db_path()
        _engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    return _engine


class Run(SQLModel, table=True):
    id: str = Field(primary_key=True)
    goal: str
    # Per-role LLMConfig assignment, JSON-encoded and snapshotted at run
    # creation time: {"supervisor": {"config_id", "provider_type", "label"},
    # "web": {...}, "data": {...}, "coding": {...}, "writing": {...},
    # "critic": {...}, "synthesis": {...}}. Snapshotted (not a live FK) so
    # run history still displays correctly even if a referenced LLMConfig is
    # later deleted. Use db.agent_model_snapshot_to_dict()/from_dict().
    agent_model_snapshot: str
    status: str = "pending"  # pending | running | completed | failed | stopped
    report: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class LLMConfig(SQLModel, table=True):
    __tablename__ = "llm_configs"

    id: str = Field(primary_key=True)
    label: str
    provider_type: str  # "claude" | "openai" | "gemini" | "ollama" | "custom"
    api_key: Optional[str] = None  # stored as-is; NEVER returned raw via any endpoint
    base_url: Optional[str] = None
    model: str
    cheap_model: Optional[str] = None  # falls back to `model` if unset
    # Whether this config can be assigned to the "image" agent role. Set
    # automatically from provider_type at creation (openai/gemini -> True,
    # claude/ollama -> False); for "custom" the caller must opt in explicitly
    # since we can't infer capability about an arbitrary endpoint.
    image_capable: bool = False
    status: str = "unverified"  # "verified" | "failed" | "unverified"
    last_checked_at: Optional[datetime] = None
    last_error: Optional[str] = None
    created_at: datetime = Field(default_factory=utcnow)


class Event(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    run_id: str = Field(index=True)
    seq: int
    event_type: str
    data: str  # JSON-encoded payload
    created_at: datetime = Field(default_factory=utcnow)


class NoteRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    run_id: str = Field(index=True)
    agent: str
    content: str
    sources: str  # JSON-encoded list[str]
    created_at: datetime = Field(default_factory=utcnow)


def init_db() -> None:
    SQLModel.metadata.create_all(get_engine())


def _normalize_run(run: Run) -> Run:
    run.created_at = as_utc(run.created_at)
    run.updated_at = as_utc(run.updated_at)
    return run


def _normalize_event(event: Event) -> Event:
    event.created_at = as_utc(event.created_at)
    return event


def _normalize_llm_config(config: LLMConfig) -> LLMConfig:
    config.created_at = as_utc(config.created_at)
    if config.last_checked_at is not None:
        config.last_checked_at = as_utc(config.last_checked_at)
    return config


def create_run(run_id: str, goal: str, agent_model_snapshot: dict) -> Run:
    """agent_model_snapshot: {role: {"config_id", "provider_type", "label"}, ...}
    for all 7 roles in app.state.AGENT_ROLES, already resolved/validated by
    the caller (see main.create_run)."""
    with Session(get_engine()) as session:
        run = Run(
            id=run_id,
            goal=goal,
            agent_model_snapshot=json.dumps(agent_model_snapshot),
            status="pending",
        )
        session.add(run)
        session.commit()
        session.refresh(run)
        return _normalize_run(run)


def update_run_status(
    run_id: str,
    status: str,
    report: Optional[str] = None,
    error: Optional[str] = None,
) -> None:
    with Session(get_engine()) as session:
        run = session.get(Run, run_id)
        if run is None:
            return
        run.status = status
        if report is not None:
            run.report = report
        if error is not None:
            run.error = error
        run.updated_at = utcnow()
        session.add(run)
        session.commit()


def run_agent_model_snapshot(run: Run) -> dict:
    """Decode a Run row's JSON-encoded agent_model_snapshot column."""
    try:
        return json.loads(run.agent_model_snapshot)
    except (TypeError, ValueError):
        return {}


def get_run(run_id: str) -> Optional[Run]:
    with Session(get_engine()) as session:
        run = session.get(Run, run_id)
        return _normalize_run(run) if run is not None else None


def list_runs() -> list[Run]:
    with Session(get_engine()) as session:
        return [_normalize_run(r) for r in session.exec(select(Run).order_by(Run.created_at.desc()))]


def next_event_seq(run_id: str) -> int:
    with Session(get_engine()) as session:
        last = session.exec(
            select(Event).where(Event.run_id == run_id).order_by(Event.seq.desc())
        ).first()
        return (last.seq + 1) if last else 0


def persist_event(run_id: str, event_type: str, data: dict) -> Event:
    with Session(get_engine()) as session:
        seq = next_event_seq(run_id)
        event = Event(run_id=run_id, seq=seq, event_type=event_type, data=json.dumps(data))
        session.add(event)
        session.commit()
        session.refresh(event)
        return _normalize_event(event)


def get_events(run_id: str, after_id: Optional[int] = None) -> list[Event]:
    """Return persisted events for a run, in order. If `after_id` is given,
    only events with a primary key greater than it are returned — used to
    honor an SSE Last-Event-ID on reconnect."""
    with Session(get_engine()) as session:
        query = select(Event).where(Event.run_id == run_id)
        if after_id is not None:
            query = query.where(Event.id > after_id)
        return [_normalize_event(e) for e in session.exec(query.order_by(Event.seq))]


def persist_note(run_id: str, agent: str, content: str, sources: list[str]) -> NoteRecord:
    with Session(get_engine()) as session:
        rec = NoteRecord(run_id=run_id, agent=agent, content=content, sources=json.dumps(sources))
        session.add(rec)
        session.commit()
        session.refresh(rec)
        return rec


def get_notes(run_id: str) -> list[NoteRecord]:
    with Session(get_engine()) as session:
        return list(session.exec(select(NoteRecord).where(NoteRecord.run_id == run_id)))


# ---------------------------------------------------------------------------
# LLMConfig CRUD
# ---------------------------------------------------------------------------


def create_llm_config(config: LLMConfig) -> LLMConfig:
    with Session(get_engine()) as session:
        session.add(config)
        session.commit()
        session.refresh(config)
        return _normalize_llm_config(config)


def get_llm_config(config_id: str) -> Optional[LLMConfig]:
    with Session(get_engine()) as session:
        config = session.get(LLMConfig, config_id)
        return _normalize_llm_config(config) if config is not None else None


def list_llm_configs() -> list[LLMConfig]:
    with Session(get_engine()) as session:
        return [_normalize_llm_config(c) for c in session.exec(select(LLMConfig).order_by(LLMConfig.created_at))]


def count_llm_configs() -> int:
    with Session(get_engine()) as session:
        return session.exec(select(func.count(LLMConfig.id))).one()


def update_llm_config_status(
    config_id: str, status: str, last_error: Optional[str] = None
) -> Optional[LLMConfig]:
    with Session(get_engine()) as session:
        config = session.get(LLMConfig, config_id)
        if config is None:
            return None
        config.status = status
        config.last_error = last_error
        config.last_checked_at = utcnow()
        session.add(config)
        session.commit()
        session.refresh(config)
        return _normalize_llm_config(config)


def delete_llm_config(config_id: str) -> bool:
    with Session(get_engine()) as session:
        config = session.get(LLMConfig, config_id)
        if config is None:
            return False
        session.delete(config)
        session.commit()
        return True
