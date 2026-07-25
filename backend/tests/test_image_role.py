"""Tests for the 8th "image" agent role: image_capable defaults per
provider_type, the capability-gate 400 on POST /api/runs, the image agent's
real HTTP call (mocked success + failure), the image-serving endpoint, and a
full-graph smoke test that routes through "image" at least once."""
from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient

from app import db
from app.config import settings
from app.db import LLMConfig

from tests._helpers import make_agent_configs


# ---------------------------------------------------------------------------
# image_capable defaults per provider_type at creation
# ---------------------------------------------------------------------------


def test_claude_config_defaults_image_capable_false(monkeypatch):
    import app.llm_configs as llm_configs_module
    from types import SimpleNamespace

    monkeypatch.setattr(
        llm_configs_module, "_build_client", lambda config: SimpleNamespace(invoke=lambda m: SimpleNamespace(content="ok"))
    )
    from app.main import app

    client = TestClient(app)
    resp = client.post(
        "/api/llm-configs",
        json={"provider_type": "claude", "api_key": "sk-ant-fake", "model": "claude-sonnet-5"},
    )
    assert resp.status_code == 200
    assert resp.json()["image_capable"] is False


def test_openai_config_defaults_image_capable_true(monkeypatch):
    import app.llm_configs as llm_configs_module
    from types import SimpleNamespace

    monkeypatch.setattr(
        llm_configs_module, "_build_client", lambda config: SimpleNamespace(invoke=lambda m: SimpleNamespace(content="ok"))
    )
    from app.main import app

    client = TestClient(app)
    resp = client.post(
        "/api/llm-configs",
        json={"provider_type": "openai", "api_key": "sk-fake", "model": "gpt-4o"},
    )
    assert resp.status_code == 200
    assert resp.json()["image_capable"] is True


def test_gemini_config_defaults_image_capable_true(monkeypatch):
    import app.llm_configs as llm_configs_module
    from types import SimpleNamespace

    monkeypatch.setattr(
        llm_configs_module, "_build_client", lambda config: SimpleNamespace(invoke=lambda m: SimpleNamespace(content="ok"))
    )
    from app.main import app

    client = TestClient(app)
    resp = client.post(
        "/api/llm-configs",
        json={"provider_type": "gemini", "api_key": "fake-key", "model": "gemini-2.5-pro"},
    )
    assert resp.status_code == 200
    assert resp.json()["image_capable"] is True


def test_ollama_config_defaults_image_capable_false(monkeypatch):
    import app.llm_configs as llm_configs_module

    monkeypatch.setattr(llm_configs_module, "check_ollama_reachable_at", lambda base_url: True)
    from app.main import app

    client = TestClient(app)
    resp = client.post("/api/llm-configs", json={"provider_type": "ollama"})
    assert resp.status_code == 200
    assert resp.json()["image_capable"] is False


def test_custom_config_defaults_image_capable_false_without_opt_in(monkeypatch):
    import app.llm_configs as llm_configs_module

    monkeypatch.setattr(llm_configs_module, "_build_client", lambda config: (_ for _ in ()).throw(RuntimeError("boom")))
    from app.main import app

    client = TestClient(app)
    resp = client.post(
        "/api/llm-configs",
        json={"provider_type": "custom", "base_url": "http://localhost:1234/v1", "model": "some-model"},
    )
    assert resp.status_code == 200
    assert resp.json()["image_capable"] is False


def test_custom_config_can_opt_in_to_image_capable(monkeypatch):
    import app.llm_configs as llm_configs_module

    monkeypatch.setattr(llm_configs_module, "_build_client", lambda config: (_ for _ in ()).throw(RuntimeError("boom")))
    from app.main import app

    client = TestClient(app)
    resp = client.post(
        "/api/llm-configs",
        json={
            "provider_type": "custom",
            "base_url": "http://localhost:1234/v1",
            "model": "some-image-model",
            "image_capable": True,
        },
    )
    assert resp.status_code == 200
    assert resp.json()["image_capable"] is True


# ---------------------------------------------------------------------------
# POST /api/runs capability gate for the "image" role
# ---------------------------------------------------------------------------


def _claude_config(config_id: str = "cfg-claude-for-image-role") -> LLMConfig:
    return db.create_llm_config(
        LLMConfig(
            id=config_id,
            label="Test Claude",
            provider_type="claude",
            api_key="sk-ant-fake",
            model="claude-sonnet-5",
            image_capable=False,
            status="verified",
        )
    )


def _openai_image_config(config_id: str = "cfg-openai-image") -> LLMConfig:
    return db.create_llm_config(
        LLMConfig(
            id=config_id,
            label="Test OpenAI Image",
            provider_type="openai",
            api_key="sk-fake",
            model="gpt-image-1",
            image_capable=True,
            status="verified",
        )
    )


def test_create_run_all_claude_including_image_role_returns_400_naming_claude():
    from app.main import app

    config = _claude_config()
    agent_configs = make_agent_configs(config.id)  # all 8 roles, including "image", get Claude

    client = TestClient(app)
    resp = client.post("/api/runs", json={"goal": "goal", "agent_configs": agent_configs})
    assert resp.status_code == 400
    detail = resp.json()["detail"]
    assert "Claude" in detail
    assert "image generation" in detail.lower()


def test_create_run_with_image_capable_config_for_image_role_passes_gate(monkeypatch):
    from app.main import app
    import app.main as main_module

    async def fake_start_run(run_id, goal, agent_configs):
        return None

    monkeypatch.setattr(main_module, "start_run", fake_start_run)

    text_config = _claude_config()
    image_config = _openai_image_config()
    agent_configs = make_agent_configs(text_config.id)
    agent_configs["image"] = image_config.id

    client = TestClient(app)
    resp = client.post("/api/runs", json={"goal": "goal", "agent_configs": agent_configs})
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Image agent: mocked HTTP call, success + failure paths
# ---------------------------------------------------------------------------


def test_image_agent_openai_success_saves_file_and_sets_image_url(monkeypatch, tmp_path):
    import base64

    from app.agents import image as image_agent
    from app.state import new_state

    monkeypatch.setattr(settings, "images_path", str(tmp_path / "images"))

    fake_png_bytes = b"\x89PNG\r\n\x1a\nfake-image-bytes"
    fake_b64 = base64.b64encode(fake_png_bytes).decode()

    class FakeResponse:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {"data": [{"b64_json": fake_b64}]}

    def fake_post(url, headers=None, json=None, timeout=None):
        assert url == "https://api.openai.com/v1/images/generations"
        assert headers["Authorization"] == "Bearer sk-fake-openai-key"
        assert json["prompt"] == "a diagram of the system"
        return FakeResponse()

    monkeypatch.setattr("app.agents.image.httpx.post", fake_post)

    config = db.create_llm_config(
        LLMConfig(
            id="cfg-image-openai-success",
            label="OpenAI Image",
            provider_type="openai",
            api_key="sk-fake-openai-key",
            model="gpt-image-1",
            image_capable=True,
            status="verified",
        )
    )

    run_id = "test-image-agent-run"
    state = new_state(run_id, "goal", {"image": config.id})

    note = image_agent.run(state, "a diagram of the system")

    assert note.agent == "image"
    assert note.image_url == f"/api/images/{run_id}/{note.image_url.rsplit('/', 1)[-1]}"
    assert note.image_url.startswith(f"/api/images/{run_id}/")
    assert note.image_url.endswith(".png")

    saved_path = tmp_path / "images" / run_id / note.image_url.rsplit("/", 1)[-1]
    assert saved_path.is_file()
    assert saved_path.read_bytes() == fake_png_bytes


def test_image_agent_gemini_success(monkeypatch, tmp_path):
    import base64

    from app.agents import image as image_agent
    from app.state import new_state

    monkeypatch.setattr(settings, "images_path", str(tmp_path / "images"))

    fake_bytes = b"fake-gemini-image-bytes"
    fake_b64 = base64.b64encode(fake_bytes).decode()

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"output_image": {"data": fake_b64, "mime_type": "image/png"}}

    def fake_post(url, headers=None, json=None, timeout=None):
        assert url == "https://generativelanguage.googleapis.com/v1beta/interactions"
        assert headers["x-goog-api-key"] == "fake-gemini-key"
        assert json["model"] == "gemini-3.1-flash-image"
        assert json["input"] == [{"type": "text", "text": "a chart mockup"}]
        return FakeResponse()

    monkeypatch.setattr("app.agents.image.httpx.post", fake_post)

    config = db.create_llm_config(
        LLMConfig(
            id="cfg-image-gemini-success",
            label="Gemini Image",
            provider_type="gemini",
            api_key="fake-gemini-key",
            model="gemini-3.1-flash-image",
            image_capable=True,
            status="verified",
        )
    )

    run_id = "test-image-agent-gemini-run"
    state = new_state(run_id, "goal", {"image": config.id})

    note = image_agent.run(state, "a chart mockup")

    assert note.image_url is not None
    saved_path = tmp_path / "images" / run_id / note.image_url.rsplit("/", 1)[-1]
    assert saved_path.read_bytes() == fake_bytes


def test_image_agent_failure_does_not_crash_and_produces_clean_note(monkeypatch, tmp_path):
    from app.agents import image as image_agent
    from app.state import new_state

    monkeypatch.setattr(settings, "images_path", str(tmp_path / "images"))

    def fake_post(url, headers=None, json=None, timeout=None):
        raise RuntimeError("Error code: 429 - Rate limit exceeded")

    monkeypatch.setattr("app.agents.image.httpx.post", fake_post)

    config = db.create_llm_config(
        LLMConfig(
            id="cfg-image-openai-failure",
            label="OpenAI Image",
            provider_type="openai",
            api_key="sk-fake",
            model="gpt-image-1",
            image_capable=True,
            status="verified",
        )
    )

    run_id = "test-image-agent-failure-run"
    state = new_state(run_id, "goal", {"image": config.id})

    note = image_agent.run(state, "a diagram")

    assert note.agent == "image"
    assert note.image_url is None
    assert "429" in note.content or "Rate limit" in note.content


def test_image_agent_rejects_non_image_capable_config_defensively(tmp_path, monkeypatch):
    """Defense in depth: even if something bypassed the /api/runs gate, the
    agent itself must not silently proceed for a non-image-capable config."""
    from app.agents import image as image_agent
    from app.state import new_state

    monkeypatch.setattr(settings, "images_path", str(tmp_path / "images"))

    config = db.create_llm_config(
        LLMConfig(
            id="cfg-claude-somehow-assigned-to-image",
            label="Claude",
            provider_type="claude",
            api_key="sk-ant-fake",
            model="claude-sonnet-5",
            image_capable=False,
            status="verified",
        )
    )

    run_id = "test-image-agent-defense-run"
    state = new_state(run_id, "goal", {"image": config.id})

    note = image_agent.run(state, "a diagram")

    assert note.image_url is None
    assert "not image-capable" in note.content


# ---------------------------------------------------------------------------
# GET /api/images/{run_id}/{filename}
# ---------------------------------------------------------------------------


def test_get_image_serves_existing_file(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "images_path", str(tmp_path / "images"))

    run_dir = tmp_path / "images" / "run-abc"
    run_dir.mkdir(parents=True)
    (run_dir / "pic.png").write_bytes(b"\x89PNG\r\n\x1a\nsome-bytes")

    from app.main import app

    client = TestClient(app)
    resp = client.get("/api/images/run-abc/pic.png")
    assert resp.status_code == 200
    assert resp.content == b"\x89PNG\r\n\x1a\nsome-bytes"


def test_get_image_404_for_missing_file(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "images_path", str(tmp_path / "images"))

    from app.main import app

    client = TestClient(app)
    resp = client.get("/api/images/run-abc/does-not-exist.png")
    assert resp.status_code == 404


def test_get_image_404_for_path_traversal_attempt(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "images_path", str(tmp_path / "images"))
    (tmp_path / "images").mkdir(parents=True, exist_ok=True)
    secret = tmp_path / "secret.txt"
    secret.write_text("should not be servable")

    from app.main import app

    client = TestClient(app)
    resp = client.get("/api/images/..%2F/secret.txt")
    assert resp.status_code in (404, 400)


# ---------------------------------------------------------------------------
# Full graph smoke test: a run that routes through "image" at least once
# ---------------------------------------------------------------------------


def test_full_graph_smoke_routes_through_image_role(monkeypatch, tmp_path):
    from types import SimpleNamespace
    import base64

    monkeypatch.setattr(settings, "images_path", str(tmp_path / "images"))

    text_config = db.create_llm_config(
        LLMConfig(
            id="cfg-smoke-text",
            label="Smoke Text Claude",
            provider_type="claude",
            api_key="sk-ant-fake",
            model="claude-sonnet-5",
            image_capable=False,
            status="verified",
        )
    )
    image_config = db.create_llm_config(
        LLMConfig(
            id="cfg-smoke-image",
            label="Smoke OpenAI Image",
            provider_type="openai",
            api_key="sk-fake",
            model="gpt-image-1",
            image_capable=True,
            status="verified",
        )
    )
    agent_configs = make_agent_configs(text_config.id)
    agent_configs["image"] = image_config.id

    calls = {"supervisor": 0}

    class RecordingFakeLLM:
        def invoke(self, messages):
            system_content = messages[0]["content"] if messages else ""
            if "Critic Agent" in system_content:
                return SimpleNamespace(content='{"issues": [], "summary": "Looks solid."}')
            if "manage a research team" in system_content:
                calls["supervisor"] += 1
                if calls["supervisor"] == 1:
                    return SimpleNamespace(
                        content='{"next_agent": "image", "task": "diagram", "reason": "visual aid"}'
                    )
                return SimpleNamespace(content='{"action": "finish_research"}')
            return SimpleNamespace(content="Final polished report content.")

    monkeypatch.setattr("app.llm._build_client", lambda config: RecordingFakeLLM())

    fake_png_bytes = b"\x89PNG\r\n\x1a\nsmoke-test-bytes"
    fake_b64 = base64.b64encode(fake_png_bytes).decode()

    class FakeImageResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"data": [{"b64_json": fake_b64}]}

    monkeypatch.setattr(
        "app.agents.image.httpx.post", lambda *a, **k: FakeImageResponse()
    )

    run_id = "test-full-graph-image-smoke"
    db.create_run(
        run_id,
        "goal",
        {
            role: {"config_id": cfg_id, "provider_type": "claude", "label": "x"}
            for role, cfg_id in agent_configs.items()
        },
    )

    from app.run_manager import _execute_run

    asyncio.run(_execute_run(run_id, "smoke test goal needing a diagram", agent_configs))

    run = db.get_run(run_id)
    assert run.status == "completed"
    assert run.report

    notes = db.get_notes(run_id)
    image_notes = [n for n in notes if n.agent == "image"]
    assert len(image_notes) == 1

    import json as json_module

    events = db.get_events(run_id)
    note_added_events = [
        json_module.loads(e.data) for e in events if e.event_type == "note_added"
    ]
    image_events = [e for e in note_added_events if e["agent"] == "image"]
    assert len(image_events) == 1
    assert image_events[0]["image_url"] is not None
    assert image_events[0]["image_url"].startswith(f"/api/images/{run_id}/")
