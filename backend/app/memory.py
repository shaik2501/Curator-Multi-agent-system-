"""ChromaDB-backed shared memory for agent notes."""
from __future__ import annotations

import re
import uuid
from typing import List, TypedDict

from app.config import settings
from app.state import Note

_client = None


def _get_client():
    global _client
    if _client is None:
        import chromadb

        _client = chromadb.PersistentClient(path=str(settings.resolved_chroma_path()))
    return _client


def _collection_name(run_id: str) -> str:
    sanitized = re.sub(r"[^a-zA-Z0-9_-]", "_", run_id)
    return f"run_{sanitized}"


def _get_collection(run_id: str):
    client = _get_client()
    return client.get_or_create_collection(name=_collection_name(run_id))


def add_note(run_id: str, note: Note) -> None:
    """Embed a note into the run's ChromaDB collection."""
    collection = _get_collection(run_id)
    collection.add(
        ids=[str(uuid.uuid4())],
        documents=[note.content],
        metadatas=[{"agent": note.agent, "sources": ",".join(note.sources)}],
    )


class QueryHit(TypedDict):
    content: str
    agent: str
    sources: List[str]


def query(run_id: str, text: str, k: int = 5) -> List[QueryHit]:
    """Query the run's ChromaDB collection for the top-k most relevant notes."""
    collection = _get_collection(run_id)
    if collection.count() == 0:
        return []
    n_results = min(k, collection.count())
    result = collection.query(query_texts=[text], n_results=n_results)

    hits: List[QueryHit] = []
    documents = result.get("documents", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]
    for doc, meta in zip(documents, metadatas):
        sources_raw = (meta or {}).get("sources", "")
        sources = [s for s in sources_raw.split(",") if s]
        hits.append(QueryHit(content=doc, agent=(meta or {}).get("agent", ""), sources=sources))
    return hits


def get_all_notes(run_id: str) -> List[QueryHit]:
    """Return every note stored for a run (used by the /knowledge endpoint)."""
    collection = _get_collection(run_id)
    if collection.count() == 0:
        return []
    result = collection.get()
    hits: List[QueryHit] = []
    for doc, meta in zip(result.get("documents", []), result.get("metadatas", [])):
        sources_raw = (meta or {}).get("sources", "")
        sources = [s for s in sources_raw.split(",") if s]
        hits.append(QueryHit(content=doc, agent=(meta or {}).get("agent", ""), sources=sources))
    return hits
