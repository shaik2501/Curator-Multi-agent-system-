"""Tests for agent_configs validation on POST /api/runs (per-role LLM
config assignment) and the POST /api/providers/ollama/check endpoint."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app import db
from app.db import LLMConfig
from app.state import AGENT_ROLES

from tests._helpers import make_agent_configs


def _make_claude_config(config_id: str = "cfg-for-run-test") -> LLMConfig:
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


def test_create_run_missing_role_returns_400_naming_it():
    from app.main import app

    config = _make_claude_config()
    agent_configs = make_agent_configs(config.id)
    del agent_configs["critic"]  # drop one required role

    client = TestClient(app)
    resp = client.post("/api/runs", json={"goal": "test goal", "agent_configs": agent_configs})
    assert resp.status_code == 400
    assert "critic" in resp.json()["detail"]


def test_create_run_missing_multiple_roles_names_all():
    from app.main import app

    config = _make_claude_config()
    agent_configs = make_agent_configs(config.id)
    del agent_configs["critic"]
    del agent_configs["synthesis"]

    client = TestClient(app)
    resp = client.post("/api/runs", json={"goal": "test goal", "agent_configs": agent_configs})
    assert resp.status_code == 400
    detail = resp.json()["detail"]
    assert "critic" in detail
    assert "synthesis" in detail


def test_create_run_bad_config_id_for_one_role_returns_400_naming_it():
    from app.main import app

    config = _make_claude_config()
    agent_configs = make_agent_configs(config.id)
    agent_configs["writing"] = "does-not-exist"

    client = TestClient(app)
    resp = client.post("/api/runs", json={"goal": "test goal", "agent_configs": agent_configs})
    assert resp.status_code == 400
    assert "writing" in resp.json()["detail"]
    assert "does-not-exist" in resp.json()["detail"]


def test_create_run_accepts_valid_agent_configs_for_all_roles(monkeypatch):
    from app.main import app
    import app.main as main_module

    # Don't actually kick off graph work for this shape-only test — just
    # confirm a fully-valid agent_configs map passes the validation gate.
    # Claude isn't image-capable, so the image role needs its own config here
    # (see test_image_role_validation.py for the image-capability gate itself).
    async def fake_start_run(run_id, goal, agent_configs):
        return None

    monkeypatch.setattr(main_module, "start_run", fake_start_run)

    config = _make_claude_config()
    image_config = db.create_llm_config(
        LLMConfig(
            id="cfg-image-capable-for-run-test",
            label="Test OpenAI (image)",
            provider_type="openai",
            api_key="sk-fake",
            model="gpt-image-1",
            image_capable=True,
            status="verified",
        )
    )
    agent_configs = make_agent_configs(config.id)
    agent_configs["image"] = image_config.id

    client = TestClient(app)
    resp = client.post("/api/runs", json={"goal": "test goal", "agent_configs": agent_configs})
    assert resp.status_code == 200
    assert "run_id" in resp.json()


def test_create_run_agent_configs_covers_all_eight_roles():
    # Sanity check on the fixture itself: AGENT_ROLES must be exactly the 8
    # documented role names, since the endpoint's validation is keyed off it.
    assert set(AGENT_ROLES) == {
        "supervisor",
        "web",
        "data",
        "coding",
        "image",
        "writing",
        "critic",
        "synthesis",
    }


def test_ollama_check_endpoint_false_when_unreachable(monkeypatch):
    from app.main import app
    import app.main as main_module

    monkeypatch.setattr(main_module, "check_ollama_reachable", lambda: False)

    client = TestClient(app)
    resp = client.post("/api/providers/ollama/check")
    assert resp.status_code == 200
    assert resp.json() == {"reachable": False}


def test_ollama_check_endpoint_true_when_reachable(monkeypatch):
    from app.main import app
    import app.main as main_module

    monkeypatch.setattr(main_module, "check_ollama_reachable", lambda: True)

    client = TestClient(app)
    resp = client.post("/api/providers/ollama/check")
    assert resp.status_code == 200
    assert resp.json() == {"reachable": True}
