"""Shared pytest fixtures for the Curator backend test suite: every test
gets an isolated tmp SQLite DB + Chroma dir so tests never share state."""
from __future__ import annotations

import pytest

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
