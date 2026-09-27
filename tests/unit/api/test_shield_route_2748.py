"""The Shield REST route must not mix credentials across providers (#2748)."""

import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.shield_endpoints import shield_router


@pytest.mark.parametrize(
    "provider_error,preset,expected_blocked",
    [
        (False, "advanced", False),
        (True, "advanced", False),
        (True, "strict", True),
    ],
)
def test_shield_uses_one_route_per_request(
    monkeypatch, provider_error, preset, expected_blocked
):
    monkeypatch.setenv("SHIELD_ALLOW_ANONYMOUS", "1")
    monkeypatch.delenv("SHIELD_ENDPOINT_TOKEN", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-openai-key")
    monkeypatch.setenv("OPENAI_CHAT_MODEL_ID", "synthetic-openai-model")
    monkeypatch.setenv("OPENROUTER_API_KEY", "synthetic-router-key")
    monkeypatch.setenv("OPENROUTER_BASE_URL", "https://synthetic-router.invalid/v1")
    monkeypatch.setenv("OPENROUTER_CHAT_MODEL_ID", "synthetic-router-model")

    client_calls = []
    completion_calls = []

    class FakeCompletion:
        def create(self, **kwargs):
            completion_calls.append(kwargs)
            if provider_error:
                raise RuntimeError("synthetic provider failure")
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        finish_reason="stop",
                        message=SimpleNamespace(
                            content=json.dumps(
                                {"threat_score": 0, "categories": [], "explanation": ""}
                            )
                        ),
                    )
                ]
            )

    def fake_openai(**kwargs):
        client_calls.append(kwargs)
        return SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletion()))

    app = FastAPI()
    app.include_router(shield_router, prefix="/api")
    with patch("openai.OpenAI", side_effect=fake_openai):
        response = TestClient(app).post(
            "/api/shield/validate", json={"text": "Synthetic request", "preset": preset}
        )

    assert response.status_code == 200
    assert client_calls == [
        {
            "api_key": "synthetic-router-key",
            "base_url": "https://synthetic-router.invalid/v1",
        }
    ]
    assert len(completion_calls) == 1
    assert completion_calls[0]["model"] == "synthetic-router-model"
    data = response.json()
    assert data["blocked"] is expected_blocked
    layer = next(lr for lr in data["layer_results"] if lr["layer"] == "llm_validator")
    if provider_error:
        assert layer["error_type"] == "RuntimeError"
    else:
        assert layer["error_type"] is None


def test_shield_resolves_rotated_route_on_each_request(monkeypatch):
    monkeypatch.setenv("SHIELD_ALLOW_ANONYMOUS", "1")
    monkeypatch.delenv("SHIELD_ENDPOINT_TOKEN", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-openai-key")
    monkeypatch.setenv("OPENAI_CHAT_MODEL_ID", "synthetic-openai-model")
    monkeypatch.setenv("OPENROUTER_API_KEY", "synthetic-router-key")
    monkeypatch.setenv("OPENROUTER_BASE_URL", "https://synthetic-router.invalid/v1")
    monkeypatch.setenv("OPENROUTER_CHAT_MODEL_ID", "synthetic-router-model")

    routes = []
    models = []

    class FakeCompletion:
        def create(self, **kwargs):
            models.append(kwargs["model"])
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        finish_reason="stop",
                        message=SimpleNamespace(
                            content='{"threat_score": 0, "categories": []}'
                        ),
                    )
                ]
            )

    def fake_openai(**kwargs):
        routes.append(kwargs)
        return SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletion()))

    app = FastAPI()
    app.include_router(shield_router, prefix="/api")
    client = TestClient(app)
    with patch("openai.OpenAI", side_effect=fake_openai):
        first = client.post(
            "/api/shield/validate", json={"text": "Synthetic", "preset": "advanced"}
        )
        monkeypatch.delenv("OPENROUTER_API_KEY")
        second = client.post(
            "/api/shield/validate", json={"text": "Synthetic", "preset": "advanced"}
        )

    assert first.status_code == second.status_code == 200
    assert routes == [
        {
            "api_key": "synthetic-router-key",
            "base_url": "https://synthetic-router.invalid/v1",
        },
        {"api_key": "synthetic-openai-key", "base_url": "https://api.openai.com/v1"},
    ]
    assert models == ["synthetic-router-model", "synthetic-openai-model"]
