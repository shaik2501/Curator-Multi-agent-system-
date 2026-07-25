"""Tests for GET /api/settings: it's now just the run-cap knobs — the
per-provider `providers` blob was superseded by /api/llm-configs."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import db
from app.config import settings


@pytest.fixture(autouse=True)
def _tmp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "db_path", str(tmp_path / "test_runs.db"))
    monkeypatch.setattr(settings, "chroma_path", str(tmp_path / "test_chroma"))
    import app.db as db_module

    db_module._engine = None
    db.init_db()
    yield
    db_module._engine = None


def test_settings_shape():
    from app.main import app

    client = TestClient(app)
    resp = client.get("/api/settings")
    assert resp.status_code == 200

    body = resp.json()
    assert set(body.keys()) == {
        "max_supervisor_turns",
        "max_debate_rounds",
        "max_searches_per_run",
    }
    assert body["max_supervisor_turns"] == settings.max_supervisor_turns
    assert body["max_debate_rounds"] == settings.max_debate_rounds
    assert body["max_searches_per_run"] == settings.max_searches_per_run
    # No provider info (and therefore no key material) belongs here anymore.
    assert "providers" not in body
