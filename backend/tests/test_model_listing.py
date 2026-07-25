"""Tests for POST /api/llm-configs/list-models and app/model_listing.py:
live "what models can this key actually use" lookups. Stateless — no DB
writes, never a non-200 from the endpoint itself, never raises on a bad
key/network failure, and never echoes a raw api_key value anywhere."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx
import pytest
from fastapi.testclient import TestClient

from app import db
from app.config import settings
from app import model_listing


@pytest.fixture(autouse=True)
def _tmp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "db_path", str(tmp_path / "test_runs.db"))
    monkeypatch.setattr(settings, "chroma_path", str(tmp_path / "test_chroma"))
    import app.db as db_module

    db_module._engine = None
    db.init_db()
    yield
    db_module._engine = None


def _fake_response(json_body: dict, status_code: int = 200) -> SimpleNamespace:
    resp = SimpleNamespace()
    resp.status_code = status_code
    resp._json = json_body

    def raise_for_status():
        if status_code >= 400:
            raise httpx.HTTPStatusError("bad status", request=None, response=resp)

    resp.raise_for_status = raise_for_status
    resp.json = lambda: resp._json
    return resp


# ---------------------------------------------------------------------------
# claude
# ---------------------------------------------------------------------------


def test_list_claude_models_success(monkeypatch):
    mock_get = MagicMock(
        return_value=_fake_response(
            {"data": [{"id": "claude-sonnet-5"}, {"id": "claude-haiku-4-5"}]}
        )
    )
    monkeypatch.setattr(httpx, "get", mock_get)

    result = model_listing.list_claude_models("sk-ant-fake-key")
    assert result.error is None
    assert result.models == ["claude-sonnet-5", "claude-haiku-4-5"]
    assert mock_get.called
    # Never echo the key back in any header value we can inspect from here —
    # sanity check the call was made with the real key in the header (server
    # side, never returned), not present anywhere in the result.
    assert "sk-ant-fake-key" not in result.to_dict().values()


def test_list_claude_models_missing_key_makes_no_http_call(monkeypatch):
    mock_get = MagicMock(side_effect=AssertionError("should never be called"))
    monkeypatch.setattr(httpx, "get", mock_get)

    result = model_listing.list_claude_models(None)
    assert result.models == []
    assert result.error == "API key required"
    mock_get.assert_not_called()


def test_list_claude_models_auth_failure_does_not_raise(monkeypatch):
    def _boom(*args, **kwargs):
        raise httpx.HTTPStatusError(
            "401 Unauthorized",
            request=MagicMock(),
            response=_fake_response({"error": "invalid x-api-key"}, status_code=401),
        )

    monkeypatch.setattr(httpx, "get", _boom)

    result = model_listing.list_claude_models("sk-ant-bad-key")
    assert result.models == []
    assert result.error
    assert "sk-ant-bad-key" not in result.error


# ---------------------------------------------------------------------------
# openai
# ---------------------------------------------------------------------------


def test_list_openai_models_success_filters_non_chat_models(monkeypatch):
    mock_get = MagicMock(
        return_value=_fake_response(
            {
                "data": [
                    {"id": "gpt-4o"},
                    {"id": "gpt-4o-mini"},
                    {"id": "text-embedding-3-small"},
                    {"id": "whisper-1"},
                    {"id": "tts-1"},
                    {"id": "dall-e-3"},
                    {"id": "text-moderation-latest"},
                ]
            }
        )
    )
    monkeypatch.setattr(httpx, "get", mock_get)

    result = model_listing.list_openai_models("sk-fake")
    assert result.error is None
    assert set(result.models) == {"gpt-4o", "gpt-4o-mini"}


def test_list_openai_models_missing_key_makes_no_http_call(monkeypatch):
    mock_get = MagicMock(side_effect=AssertionError("should never be called"))
    monkeypatch.setattr(httpx, "get", mock_get)

    result = model_listing.list_openai_models(None)
    assert result.models == []
    assert result.error == "API key required"
    mock_get.assert_not_called()


def test_list_openai_models_auth_failure_does_not_raise(monkeypatch):
    def _boom(*args, **kwargs):
        raise httpx.HTTPStatusError("401", request=MagicMock(), response=MagicMock())

    monkeypatch.setattr(httpx, "get", _boom)

    result = model_listing.list_openai_models("sk-bad")
    assert result.models == []
    assert result.error
    assert "sk-bad" not in result.error


# ---------------------------------------------------------------------------
# gemini
# ---------------------------------------------------------------------------


def test_list_gemini_models_success_filters_and_strips_prefix(monkeypatch):
    mock_get = MagicMock(
        return_value=_fake_response(
            {
                "models": [
                    {
                        "name": "models/gemini-2.5-pro",
                        "supportedGenerationMethods": ["generateContent"],
                    },
                    {
                        "name": "models/gemini-2.5-flash",
                        "supportedGenerationMethods": ["generateContent"],
                    },
                    {
                        "name": "models/embedding-001",
                        "supportedGenerationMethods": ["embedContent"],
                    },
                ]
            }
        )
    )
    monkeypatch.setattr(httpx, "get", mock_get)

    result = model_listing.list_gemini_models("fake-gemini-key")
    assert result.error is None
    assert set(result.models) == {"gemini-2.5-pro", "gemini-2.5-flash"}
    assert all("models/" not in m for m in result.models)


def test_list_gemini_models_missing_key_makes_no_http_call(monkeypatch):
    mock_get = MagicMock(side_effect=AssertionError("should never be called"))
    monkeypatch.setattr(httpx, "get", mock_get)

    result = model_listing.list_gemini_models(None)
    assert result.models == []
    assert result.error == "API key required"
    mock_get.assert_not_called()


def test_list_gemini_models_auth_failure_does_not_raise(monkeypatch):
    def _boom(*args, **kwargs):
        raise httpx.HTTPStatusError("400", request=MagicMock(), response=MagicMock())

    monkeypatch.setattr(httpx, "get", _boom)

    result = model_listing.list_gemini_models("bad-key")
    assert result.models == []
    assert result.error
    assert "bad-key" not in result.error


# ---------------------------------------------------------------------------
# ollama
# ---------------------------------------------------------------------------


def test_list_ollama_models_reachable_with_models(monkeypatch):
    mock_get = MagicMock(
        return_value=_fake_response({"models": [{"name": "llama3.1:8b"}, {"name": "qwen2.5:7b"}]})
    )
    monkeypatch.setattr(httpx, "get", mock_get)

    result = model_listing.list_ollama_models("http://localhost:11434")
    assert result.error is None
    assert result.models == ["llama3.1:8b", "qwen2.5:7b"]


def test_list_ollama_models_not_reachable(monkeypatch):
    def _boom(*args, **kwargs):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(httpx, "get", _boom)

    result = model_listing.list_ollama_models("http://localhost:11434")
    assert result.models == []
    assert "not reachable" in result.error
    assert "http://localhost:11434" in result.error


# ---------------------------------------------------------------------------
# custom
# ---------------------------------------------------------------------------


def test_list_custom_models_success(monkeypatch):
    mock_get = MagicMock(
        return_value=_fake_response({"data": [{"id": "llama-3-70b"}, {"id": "mixtral-8x7b"}]})
    )
    monkeypatch.setattr(httpx, "get", mock_get)

    result = model_listing.list_custom_models("http://localhost:1234/v1", "some-key")
    assert result.error is None
    assert result.models == ["llama-3-70b", "mixtral-8x7b"]


def test_list_custom_models_unsupported_endpoint_fails_gracefully(monkeypatch):
    def _boom(*args, **kwargs):
        raise httpx.ConnectTimeout("timed out")

    monkeypatch.setattr(httpx, "get", _boom)

    result = model_listing.list_custom_models("http://localhost:9999/v1", None)
    assert result.models == []
    assert "manually" in result.error


def test_list_custom_models_unexpected_shape_fails_gracefully(monkeypatch):
    mock_get = MagicMock(return_value=_fake_response({"unexpected": "shape"}))
    monkeypatch.setattr(httpx, "get", mock_get)

    result = model_listing.list_custom_models("http://localhost:1234/v1", None)
    assert result.models == []
    assert "manually" in result.error


def test_list_custom_models_missing_base_url():
    result = model_listing.list_custom_models(None, "some-key")
    assert result.models == []
    assert result.error


# ---------------------------------------------------------------------------
# Endpoint-level
# ---------------------------------------------------------------------------


def test_list_models_endpoint_always_200(monkeypatch):
    from app.main import app

    monkeypatch.setattr(
        "app.main.list_models",
        lambda provider_type, api_key, base_url: model_listing.ModelListResult(
            [], "some error"
        ),
    )

    client = TestClient(app)
    resp = client.post(
        "/api/llm-configs/list-models", json={"provider_type": "claude", "api_key": "bad"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["models"] == []
    assert body["error"] == "some error"


def test_list_models_endpoint_does_not_touch_db(monkeypatch):
    from app.main import app

    monkeypatch.setattr(
        "app.main.list_models",
        lambda provider_type, api_key, base_url: model_listing.ModelListResult(
            ["claude-sonnet-5"], None
        ),
    )

    client = TestClient(app)
    resp = client.post(
        "/api/llm-configs/list-models",
        json={"provider_type": "claude", "api_key": "sk-ant-fake"},
    )
    assert resp.status_code == 200
    assert resp.json()["models"] == ["claude-sonnet-5"]

    # Stateless: nothing was saved to llm_configs.
    assert db.list_llm_configs() == []


def test_list_models_endpoint_unknown_provider_type():
    from app.main import app

    client = TestClient(app)
    resp = client.post("/api/llm-configs/list-models", json={"provider_type": "bogus"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["models"] == []
    assert body["error"]


def test_list_models_endpoint_never_echoes_raw_key(monkeypatch):
    from app.main import app

    monkeypatch.setattr(
        "app.main.list_models",
        lambda provider_type, api_key, base_url: model_listing.ModelListResult([], "API key required"),
    )

    client = TestClient(app)
    fake_key = "sk-ant-should-never-appear-in-response"
    resp = client.post(
        "/api/llm-configs/list-models", json={"provider_type": "claude", "api_key": fake_key}
    )
    assert fake_key not in resp.text
