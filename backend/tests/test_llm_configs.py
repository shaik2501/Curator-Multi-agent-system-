"""Tests for the dynamic LLM credentials system: POST/GET/verify/DELETE
/api/llm-configs, live verification (success + failure paths), key masking,
and a full-run smoke test proving get_llm(provider_config_id) resolves each
of the 7 agent roles to its OWN independently-assigned config."""
from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app import db
from app.db import LLMConfig

from tests._helpers import make_agent_configs, make_mixed_agent_configs, make_snapshot


class FakeLLM:
    def __init__(self, content: str = "ok", raise_exc: Exception | None = None):
        self._content = content
        self._raise_exc = raise_exc

    def invoke(self, messages):
        if self._raise_exc is not None:
            raise self._raise_exc
        return SimpleNamespace(content=self._content)


# ---------------------------------------------------------------------------
# Field validation per provider_type
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("provider_type", ["claude", "openai", "gemini"])
def test_create_llm_config_requires_api_key(provider_type):
    from app.main import app

    client = TestClient(app)
    resp = client.post(
        "/api/llm-configs",
        json={"provider_type": provider_type, "model": "some-model"},
    )
    assert resp.status_code == 400
    assert "api_key" in resp.json()["detail"]


@pytest.mark.parametrize("provider_type", ["claude", "openai", "gemini"])
def test_create_llm_config_requires_model(provider_type):
    from app.main import app

    client = TestClient(app)
    resp = client.post(
        "/api/llm-configs",
        json={"provider_type": provider_type, "api_key": "fake-key"},
    )
    assert resp.status_code == 400
    assert "model" in resp.json()["detail"]


def test_create_llm_config_custom_requires_base_url_and_model():
    from app.main import app

    client = TestClient(app)

    resp = client.post("/api/llm-configs", json={"provider_type": "custom", "model": "m"})
    assert resp.status_code == 400
    assert "base_url" in resp.json()["detail"]

    resp = client.post(
        "/api/llm-configs",
        json={"provider_type": "custom", "base_url": "http://localhost:1234/v1"},
    )
    assert resp.status_code == 400
    assert "model" in resp.json()["detail"]


def test_create_llm_config_ollama_needs_neither_key_nor_base_url(monkeypatch):
    """Ollama is zero-config: no api_key/base_url/model required, defaults apply."""
    import app.llm_configs as llm_configs_module

    monkeypatch.setattr(llm_configs_module, "check_ollama_reachable_at", lambda base_url: True)

    from app.main import app

    client = TestClient(app)
    resp = client.post("/api/llm-configs", json={"provider_type": "ollama"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["base_url"]  # default applied
    assert body["model"]  # default applied
    assert body["status"] == "verified"


def test_create_llm_config_rejects_unknown_provider_type():
    from app.main import app

    client = TestClient(app)
    resp = client.post("/api/llm-configs", json={"provider_type": "bogus", "model": "m"})
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Successful creation: masked preview, verification runs and sets status
# ---------------------------------------------------------------------------


def test_create_llm_config_success_masks_key_and_verifies(monkeypatch):
    import app.llm_configs as llm_configs_module

    monkeypatch.setattr(llm_configs_module, "_build_client", lambda config: FakeLLM("ok"))

    from app.main import app

    raw_key = "sk-ant-supersecretrealkeyvalue123456"
    client = TestClient(app)
    resp = client.post(
        "/api/llm-configs",
        json={
            "provider_type": "claude",
            "api_key": raw_key,
            "model": "claude-sonnet-5",
            "cheap_model": "claude-haiku-4-5",
        },
    )
    assert resp.status_code == 200
    body = resp.json()

    assert "api_key" not in body
    assert raw_key not in resp.text
    assert body["key_preview"] == f"{raw_key[:6]}...{raw_key[-4:]}"
    assert body["status"] == "verified"
    assert body["last_error"] is None
    assert body["last_checked_at"] is not None
    assert body["label"]  # auto-generated since none was given


def test_create_llm_config_auto_generates_label_when_blank(monkeypatch):
    import app.llm_configs as llm_configs_module

    monkeypatch.setattr(llm_configs_module, "_build_client", lambda config: FakeLLM("ok"))

    from app.main import app

    client = TestClient(app)
    resp = client.post(
        "/api/llm-configs",
        json={"provider_type": "openai", "api_key": "sk-fake", "model": "gpt-4o"},
    )
    assert resp.status_code == 200
    assert "OpenAI" in resp.json()["label"]


def test_create_llm_config_respects_given_label(monkeypatch):
    import app.llm_configs as llm_configs_module

    monkeypatch.setattr(llm_configs_module, "_build_client", lambda config: FakeLLM("ok"))

    from app.main import app

    client = TestClient(app)
    resp = client.post(
        "/api/llm-configs",
        json={
            "provider_type": "openai",
            "api_key": "sk-fake",
            "model": "gpt-4o",
            "label": "My Personal OpenAI Key",
        },
    )
    assert resp.json()["label"] == "My Personal OpenAI Key"


# ---------------------------------------------------------------------------
# Verification failure path
# ---------------------------------------------------------------------------


def test_create_llm_config_bad_key_verifies_as_failed_without_crashing(monkeypatch):
    import app.llm_configs as llm_configs_module

    auth_error = RuntimeError("Error code: 401 - Incorrect API key provided")
    monkeypatch.setattr(
        llm_configs_module, "_build_client", lambda config: FakeLLM(raise_exc=auth_error)
    )

    from app.main import app

    raw_key = "sk-totally-fake-and-invalid-openai-key"
    client = TestClient(app)
    resp = client.post(
        "/api/llm-configs",
        json={"provider_type": "openai", "api_key": raw_key, "model": "gpt-4o"},
    )
    assert resp.status_code == 200  # saving succeeds even though verification failed
    body = resp.json()

    assert body["status"] == "failed"
    assert body["last_error"]
    assert "invalid api key" in body["last_error"].lower()
    assert raw_key not in resp.text
    assert "api_key" not in body


def test_verify_endpoint_reruns_check_and_updates_status(monkeypatch):
    import app.llm_configs as llm_configs_module

    monkeypatch.setattr(llm_configs_module, "_build_client", lambda config: FakeLLM("ok"))

    config = db.create_llm_config(
        LLMConfig(
            id="cfg-verify-endpoint",
            label="Recheck me",
            provider_type="claude",
            api_key="sk-ant-fake",
            model="claude-sonnet-5",
            status="unverified",
        )
    )

    from app.main import app

    client = TestClient(app)
    resp = client.post(f"/api/llm-configs/{config.id}/verify")
    assert resp.status_code == 200
    assert resp.json()["status"] == "verified"


def test_verify_endpoint_404_for_unknown_id():
    from app.main import app

    client = TestClient(app)
    resp = client.post("/api/llm-configs/does-not-exist/verify")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET never leaks raw keys
# ---------------------------------------------------------------------------


def test_list_llm_configs_never_leaks_raw_keys():
    fake_key = "sk-ant-totally-secret-should-never-appear-anywhere"
    db.create_llm_config(
        LLMConfig(
            id="cfg-leak-check",
            label="Leak Check",
            provider_type="claude",
            api_key=fake_key,
            model="claude-sonnet-5",
            status="unverified",
        )
    )

    from app.main import app

    client = TestClient(app)
    resp = client.get("/api/llm-configs")
    assert resp.status_code == 200
    assert fake_key not in resp.text

    body = resp.json()
    assert len(body) == 1
    assert "api_key" not in body[0]
    assert body[0]["key_preview"] == f"{fake_key[:6]}...{fake_key[-4:]}"


# ---------------------------------------------------------------------------
# DELETE
# ---------------------------------------------------------------------------


def test_delete_llm_config_removes_it():
    config = db.create_llm_config(
        LLMConfig(
            id="cfg-to-delete",
            label="Delete Me",
            provider_type="claude",
            api_key="sk-ant-fake",
            model="claude-sonnet-5",
            status="unverified",
        )
    )

    from app.main import app

    client = TestClient(app)
    resp = client.delete(f"/api/llm-configs/{config.id}")
    assert resp.status_code == 200
    assert resp.json()["deleted"] is True

    resp = client.get("/api/llm-configs")
    ids = [c["id"] for c in resp.json()]
    assert config.id not in ids


def test_delete_llm_config_404_for_unknown_id():
    from app.main import app

    client = TestClient(app)
    resp = client.delete("/api/llm-configs/does-not-exist")
    assert resp.status_code == 404


def test_delete_referenced_config_does_not_break_run_history():
    """Deleting a config that a past run used is fine — the run row already
    snapshotted the full per-role agent_model_snapshot at creation time."""
    config = db.create_llm_config(
        LLMConfig(
            id="cfg-referenced-by-run",
            label="Used By A Run",
            provider_type="claude",
            api_key="sk-ant-fake",
            model="claude-sonnet-5",
            status="verified",
        )
    )
    run_id = "test-run-referencing-deleted-config"
    db.create_run(run_id, "goal", make_snapshot(config))
    db.update_run_status(run_id, "completed", report="a report")

    assert db.delete_llm_config(config.id) is True

    run = db.get_run(run_id)
    snapshot = db.run_agent_model_snapshot(run)
    assert snapshot["critic"]["provider_type"] == "claude"
    assert snapshot["critic"]["label"] == "Used By A Run"
    assert snapshot["writing"]["config_id"] == "cfg-referenced-by-run"
    assert run.status == "completed"


# ---------------------------------------------------------------------------
# Full run smoke test: each of the 7 agent roles resolves get_llm() to its
# OWN independently-assigned config — the test that actually proves
# per-role independence, not just that the plumbing runs.
# ---------------------------------------------------------------------------


def test_full_run_smoke_resolves_each_role_to_its_own_config(monkeypatch):
    config_a = db.create_llm_config(
        LLMConfig(
            id="cfg-role-a-everything-else",
            label="Config A (supervisor/data/coding/writing/critic/synthesis)",
            provider_type="claude",
            api_key="sk-ant-fake-a",
            model="claude-sonnet-5",
            status="verified",
        )
    )
    config_b = db.create_llm_config(
        LLMConfig(
            id="cfg-role-b-web-only",
            label="Config B (web only)",
            provider_type="gemini",
            api_key="fake-gemini-key-b",
            model="gemini-2.5-flash",
            status="verified",
        )
    )

    # config_a is assigned to every role except "web", which gets config_b —
    # a genuinely mixed assignment, not the same id everywhere.
    agent_configs = make_mixed_agent_configs(config_a.id, config_b.id, role_for_b="web")

    # Records (config_id, system_prompt) for every simulated LLM call, so we
    # can verify afterward which config actually backed which agent role.
    calls: list[tuple[str, str]] = []

    class RecordingFakeLLM:
        def __init__(self, config_id: str):
            self.config_id = config_id

        def invoke(self, messages):
            system_content = messages[0]["content"] if messages else ""
            calls.append((self.config_id, system_content))

            if "Web Research Agent" in system_content:
                return SimpleNamespace(content="- Found a relevant fact about the goal [source].")
            if "Critic Agent" in system_content:
                return SimpleNamespace(content='{"issues": [], "summary": "Draft looks solid."}')
            if "manage a research team" in system_content:
                # Supervisor: route to web once, then finish research.
                supervisor_calls_so_far = sum(
                    1 for _, sc in calls if "manage a research team" in sc
                )
                if supervisor_calls_so_far <= 1:
                    return SimpleNamespace(
                        content='{"next_agent": "web", "task": "search", "reason": "need facts"}'
                    )
                return SimpleNamespace(content='{"action": "finish_research"}')
            # Writing / Synthesis (and anything else): plain draft/report text.
            return SimpleNamespace(content="Final polished report content.")

    def fake_build_client(config):
        return RecordingFakeLLM(config.id)

    monkeypatch.setattr("app.llm._build_client", fake_build_client)

    run_id = "test-per-role-smoke-run"
    db.create_run(run_id, "goal", make_snapshot(config_a))  # snapshot content unused by the graph

    from app.run_manager import _execute_run

    asyncio.run(_execute_run(run_id, "smoke test goal", agent_configs))

    run = db.get_run(run_id)
    assert run.status == "completed"
    assert run.report
    assert run.error is None

    # The actual proof of per-role independence: every call whose system
    # prompt identifies it as the Web Research Agent used config_b's id,
    # and every other call (supervisor/critic/writing/synthesis) used
    # config_a's id. Both must have actually been exercised.
    web_calls = [c for c in calls if "Web Research Agent" in c[1]]
    non_web_calls = [c for c in calls if "Web Research Agent" not in c[1]]

    assert web_calls, "expected the web agent to have been invoked at least once"
    assert non_web_calls, "expected at least one non-web agent to have been invoked"

    assert all(config_id == config_b.id for config_id, _ in web_calls)
    assert all(config_id == config_a.id for config_id, _ in non_web_calls)
