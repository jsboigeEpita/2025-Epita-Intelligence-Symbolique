"""Tests for Track AA (#686): model-aware determinism.

Covers:
  1. Reasoning model + deterministic mode → params suppressed
  2. Non-reasoning model + deterministic mode → temperature/seed present
  3. Force flag re-enables params for reasoning models
  4. Unset env vars → {} unchanged
  5. _resolve_model_id and _is_reasoning_model unit tests
"""

import os

import pytest


def _clear_det_env():
    """Remove all determinism-related env vars."""
    for key in (
        "LLM_DETERMINISTIC_MODE",
        "LLM_TEMPERATURE",
        "LLM_SEED",
        "LLM_FORCE_SAMPLING_PARAMS",
        "OPENAI_CHAT_MODEL_ID",
        "OPENROUTER_CHAT_MODEL_ID",
        "OPENROUTER_BASE_URL",
        "OPENROUTER_API_KEY",
    ):
        os.environ.pop(key, None)


class TestResolveModelId:
    """_resolve_model_id picks the right model from env."""

    def setup_method(self):
        self._saved = {}
        for key in (
            "OPENAI_CHAT_MODEL_ID",
            "OPENROUTER_CHAT_MODEL_ID",
            "OPENROUTER_BASE_URL",
            "OPENROUTER_API_KEY",
        ):
            self._saved[key] = os.environ.get(key)

    def teardown_method(self):
        for key, val in self._saved.items():
            if val is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = val

    def test_default_model(self):
        """OPENAI_CHAT_MODEL_ID explicitly set to known value."""
        _clear_det_env()
        os.environ["OPENAI_CHAT_MODEL_ID"] = "gpt-5-mini"
        try:
            from argumentation_analysis.orchestration.invoke_callables import (
                _resolve_model_id,
            )

            assert _resolve_model_id() == "gpt-5-mini"
        finally:
            os.environ.pop("OPENAI_CHAT_MODEL_ID", None)

    def test_openai_model_id(self):
        """OPENAI_CHAT_MODEL_ID overrides default."""
        _clear_det_env()
        os.environ["OPENAI_CHAT_MODEL_ID"] = "gpt-4o"
        try:
            from argumentation_analysis.orchestration.invoke_callables import (
                _resolve_model_id,
            )

            assert _resolve_model_id() == "gpt-4o"
        finally:
            os.environ.pop("OPENAI_CHAT_MODEL_ID", None)

    def test_openrouter_model_preferred(self):
        """When OpenRouter is configured, OPENROUTER_CHAT_MODEL_ID is used."""
        _clear_det_env()
        os.environ["OPENROUTER_BASE_URL"] = "https://openrouter.ai/api/v1"
        os.environ["OPENROUTER_API_KEY"] = "sk-or-test"
        os.environ["OPENROUTER_CHAT_MODEL_ID"] = "openai/gpt-4o"
        os.environ["OPENAI_CHAT_MODEL_ID"] = "gpt-5-mini"
        try:
            from argumentation_analysis.orchestration.invoke_callables import (
                _resolve_model_id,
            )

            assert _resolve_model_id() == "openai/gpt-4o"
        finally:
            _clear_det_env()


class TestIsReasoningModel:
    """_is_reasoning_model correctly classifies model ids."""

    @pytest.mark.parametrize(
        "model_id,expected",
        [
            ("gpt-5-mini", True),
            ("gpt-5", True),
            ("gpt-5-turbo", True),
            ("o1-preview", True),
            ("o1-mini", True),
            ("o3-mini", True),
            ("o3", True),
            ("openai/gpt-5-mini", True),
            ("openai/o1-preview", True),
            ("openai/o3-mini", True),
            ("gpt-4o", False),
            ("gpt-4o-mini", False),
            ("gpt-4-turbo", False),
            ("claude-3-opus", False),
            ("mistral-large", False),
            ("deepseek-chat", False),
        ],
    )
    def test_reasoning_classification(self, model_id, expected):
        from argumentation_analysis.orchestration.invoke_callables import (
            _is_reasoning_model,
        )

        assert _is_reasoning_model(model_id) is expected


class TestModelAwareDeterminism:
    """_get_determinism_params respects model type."""

    def setup_method(self):
        self._saved = {}
        for key in (
            "LLM_DETERMINISTIC_MODE",
            "LLM_TEMPERATURE",
            "LLM_SEED",
            "LLM_FORCE_SAMPLING_PARAMS",
            "OPENAI_CHAT_MODEL_ID",
            "OPENROUTER_CHAT_MODEL_ID",
            "OPENROUTER_BASE_URL",
            "OPENROUTER_API_KEY",
        ):
            self._saved[key] = os.environ.get(key)

    def teardown_method(self):
        for key, val in self._saved.items():
            if val is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = val

    def test_reasoning_model_suppresses_params(self):
        """gpt-5-mini + LLM_DETERMINISTIC_MODE=1 → params suppressed."""
        _clear_det_env()
        os.environ["OPENAI_CHAT_MODEL_ID"] = "gpt-5-mini"
        os.environ["LLM_DETERMINISTIC_MODE"] = "1"
        try:
            from argumentation_analysis.orchestration.invoke_callables import (
                _get_determinism_params,
            )

            assert _get_determinism_params() == {}
        finally:
            _clear_det_env()

    def test_reasoning_model_openrouter_slug_suppresses(self):
        """openai/gpt-5-mini + deterministic mode → suppressed."""
        _clear_det_env()
        os.environ["OPENROUTER_BASE_URL"] = "https://openrouter.ai/api/v1"
        os.environ["OPENROUTER_API_KEY"] = "sk-or-test"
        os.environ["OPENROUTER_CHAT_MODEL_ID"] = "openai/gpt-5-mini"
        os.environ["LLM_DETERMINISTIC_MODE"] = "1"
        try:
            from argumentation_analysis.orchestration.invoke_callables import (
                _get_determinism_params,
            )

            assert _get_determinism_params() == {}
        finally:
            _clear_det_env()

    def test_o1_suppresses(self):
        """o1-preview + deterministic mode → suppressed."""
        _clear_det_env()
        os.environ["OPENAI_CHAT_MODEL_ID"] = "o1-preview"
        os.environ["LLM_DETERMINISTIC_MODE"] = "1"
        try:
            from argumentation_analysis.orchestration.invoke_callables import (
                _get_determinism_params,
            )

            assert _get_determinism_params() == {}
        finally:
            _clear_det_env()

    def test_o3_suppresses(self):
        """o3-mini + deterministic mode → suppressed."""
        _clear_det_env()
        os.environ["OPENAI_CHAT_MODEL_ID"] = "o3-mini"
        os.environ["LLM_DETERMINISTIC_MODE"] = "1"
        try:
            from argumentation_analysis.orchestration.invoke_callables import (
                _get_determinism_params,
            )

            assert _get_determinism_params() == {}
        finally:
            _clear_det_env()

    def test_non_reasoning_model_allows_params(self):
        """gpt-4o + deterministic mode → temperature/seed present."""
        _clear_det_env()
        os.environ["OPENAI_CHAT_MODEL_ID"] = "gpt-4o"
        os.environ["LLM_DETERMINISTIC_MODE"] = "1"
        try:
            from argumentation_analysis.orchestration.invoke_callables import (
                _get_determinism_params,
            )

            result = _get_determinism_params()
            assert result["temperature"] == 0.0
            assert result["seed"] == 42
        finally:
            _clear_det_env()

    def test_force_flag_reenables_on_reasoning_model(self):
        """gpt-5-mini + deterministic + LLM_FORCE_SAMPLING_PARAMS=1 → params present."""
        _clear_det_env()
        os.environ["OPENAI_CHAT_MODEL_ID"] = "gpt-5-mini"
        os.environ["LLM_DETERMINISTIC_MODE"] = "1"
        os.environ["LLM_FORCE_SAMPLING_PARAMS"] = "1"
        try:
            from argumentation_analysis.orchestration.invoke_callables import (
                _get_determinism_params,
            )

            result = _get_determinism_params()
            assert result["temperature"] == 0.0
            assert result["seed"] == 42
        finally:
            _clear_det_env()

    def test_unset_env_returns_empty(self):
        """No determinism env vars → {} regardless of model."""
        _clear_det_env()
        os.environ["OPENAI_CHAT_MODEL_ID"] = "gpt-5-mini"
        try:
            from argumentation_analysis.orchestration.invoke_callables import (
                _get_determinism_params,
            )

            assert _get_determinism_params() == {}
        finally:
            _clear_det_env()

    def test_fine_grained_override_suppressed_on_reasoning(self):
        """LLM_TEMPERATURE=0.3 + gpt-5-mini → suppressed."""
        _clear_det_env()
        os.environ["OPENAI_CHAT_MODEL_ID"] = "gpt-5-mini"
        os.environ["LLM_TEMPERATURE"] = "0.3"
        try:
            from argumentation_analysis.orchestration.invoke_callables import (
                _get_determinism_params,
            )

            assert _get_determinism_params() == {}
        finally:
            _clear_det_env()

    def test_fine_grained_override_kept_on_non_reasoning(self):
        """LLM_TEMPERATURE=0.3 + gpt-4o → kept."""
        _clear_det_env()
        os.environ["OPENAI_CHAT_MODEL_ID"] = "gpt-4o"
        os.environ["LLM_TEMPERATURE"] = "0.3"
        try:
            from argumentation_analysis.orchestration.invoke_callables import (
                _get_determinism_params,
            )

            result = _get_determinism_params()
            assert result == {"temperature": 0.3}
        finally:
            _clear_det_env()


class TestXxTestsStillPass:
    """Verify existing XX tests still pass with the new model-aware behavior."""

    def test_xx_default_empty_still_works(self):
        """Original XX test: no env vars → {}."""
        _clear_det_env()
        from argumentation_analysis.orchestration.invoke_callables import (
            _get_determinism_params,
        )

        # Default model is gpt-5-mini (reasoning) but no det mode → {}
        assert _get_determinism_params() == {}
