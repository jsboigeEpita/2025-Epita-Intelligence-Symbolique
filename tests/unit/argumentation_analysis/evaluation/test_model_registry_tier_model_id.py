"""Numbered endpoints must send a model id, not a human display label (#2151).

`ModelRegistry.from_env()` used to pass `OPENAI_ENDPOINT_NAME_{i}` as BOTH
`display_name` and `model_id`. A label such as "Local Model - Medium (...)" is
not a model any endpoint serves, so every call returned HTTP 404 while the key
and URL were perfectly valid -- the silent mode of a config defect, invisible to
an audit that looks for 401s.
"""

import logging

import pytest

from argumentation_analysis.evaluation.model_registry import ModelRegistry


@pytest.fixture
def clean_openai_env(monkeypatch):
    """Prove independence from the ambient .env rather than assume it."""
    for i in range(2, 10):
        for prefix in (
            "OPENAI_API_KEY_",
            "OPENAI_BASE_URL_",
            "OPENAI_ENDPOINT_NAME_",
            "OPENAI_MODEL_ID_",
        ):
            monkeypatch.delenv(f"{prefix}{i}", raising=False)
    for var in ("OPENAI_API_KEY", "OPENROUTER_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    return monkeypatch


def test_no_numbered_tier_is_registered_when_env_is_clean(clean_openai_env):
    """Negative control: without this, the assertions below prove nothing."""
    registry = ModelRegistry.from_env()
    assert "endpoint-4" not in registry.list_models()


def test_model_id_comes_from_its_own_variable_not_the_label(clean_openai_env):
    clean_openai_env.setenv("OPENAI_API_KEY_4", "irrelevant-for-this-test")
    clean_openai_env.setenv("OPENAI_BASE_URL_4", "https://example.invalid/v1")
    clean_openai_env.setenv("OPENAI_ENDPOINT_NAME_4", "Local Model - Medium (some-v1)")
    clean_openai_env.setenv("OPENAI_MODEL_ID_4", "some-model-v2")

    config = ModelRegistry.from_env().get("endpoint-4")

    # The API receives the model id...
    assert config.model_id == "some-model-v2"
    # ...and the human keeps the label. Collapsing the two is the defect.
    assert config.display_name == "Local Model - Medium (some-v1)"
    assert config.model_id != config.display_name


def test_fallback_to_the_label_warns_and_names_the_variable_to_set(
    clean_openai_env, caplog
):
    clean_openai_env.setenv("OPENAI_API_KEY_4", "irrelevant-for-this-test")
    clean_openai_env.setenv("OPENAI_BASE_URL_4", "https://example.invalid/v1")
    clean_openai_env.setenv("OPENAI_ENDPOINT_NAME_4", "Local Model - Medium (some-v1)")

    with caplog.at_level(logging.WARNING, logger="evaluation.model_registry"):
        config = ModelRegistry.from_env().get("endpoint-4")

    # Behaviour is preserved (non-breaking) ...
    assert config.model_id == "Local Model - Medium (some-v1)"
    # ... but it is no longer silent, and the message names the fix.
    assert "OPENAI_MODEL_ID_4" in caplog.text
    assert "404" in caplog.text
