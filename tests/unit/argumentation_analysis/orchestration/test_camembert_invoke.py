"""Tests for _invoke_camembert_fallacy function (#297 update).

Verifies the self-hosted LLM fallacy detection invoke function that replaced
the dead CamemBERT adapter (PR #299).

Hermeticity (ATT-1 #1336 camembert cluster): the prod reads
``SELF_HOSTED_LLM_ENDPOINT``/``SELF_HOSTED_LLM_MODEL`` via
``os.environ.get`` directly. Patching ``os.environ`` globally with
``patch.dict`` was fragile in the full suite (a prior test leaks a mocked
env, and the prod call sees the empty defaults). Same fix as PR #1406
(no-key option B): patch the *bound* ``os.environ.get`` at the
``invoke_callables`` module level so the override reaches the prod call
site hermetically. Plus, ``_invoke_camembert_fallacy`` lives in
``unified_pipeline`` but imports ``os`` itself — the patch is applied to
``invoke_callables.os`` because the function-level ``os`` import resolves
to the same ``os`` module object (CPython caches it in ``sys.modules``).
"""

import json
import pytest
from unittest.mock import MagicMock, patch, AsyncMock, create_autospec

from semantic_kernel import Kernel


def _patch_invokecallables_env_get(overrides):
    """Patch ``invoke_callables.os.environ.get`` so the listed keys return
    the test-supplied *overrides* values; other keys fall through to the
    real ``os.environ.get``. This is hermetic against leaked mocks because
    it targets the *exact* prod call site, not the global ``os.environ``.
    """
    from argumentation_analysis.orchestration import invoke_callables as mod

    _real_get = mod.os.environ.get
    _override = dict(overrides)

    def side_effect(key, default=None):
        if key in _override:
            return _override[key]
        return _real_get(key, default)

    return patch.object(mod.os.environ, "get", side_effect=side_effect)


# #1591 hermeticity: for the not-configured tests, overrides must be EXPLICIT
# empties — an empty dict lets the ambient .env values through
# (SELF_HOSTED_LLM_ENDPOINT/MODEL set on dev machines), which opens the
# configured gate: the test then hits the real endpoint (measured: 2
# requests each) AND asserts a verdict ("not configured") the run can no
# longer produce (the 3 tests were red on any machine with the endpoint
# configured). Empty overrides close the gate in every environment.
_NOT_CONFIGURED = {"SELF_HOSTED_LLM_ENDPOINT": "", "SELF_HOSTED_LLM_MODEL": ""}


class TestInvokeCamemBERTFallacy:
    """Tests for _invoke_camembert_fallacy (now self-hosted LLM)."""

    async def test_invoke_camembert_no_endpoint(self):
        """Returns early with explanation when SELF_HOSTED_LLM_ENDPOINT not set."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_camembert_fallacy,
        )

        # No SELF_HOSTED_LLM_ENDPOINT / MODEL override => prod sees empty
        # strings and takes the not-configured branch (the "real_get"
        # fallback may return ambient values, which are equally "" if
        # unconfigured).
        with _patch_invokecallables_env_get(_NOT_CONFIGURED):
            result = await _invoke_camembert_fallacy("test text", {})

        assert result["total_fallacies"] == 0
        assert result["tiers_used"] == ["none"]
        assert "not configured" in result["explanation"]

    async def test_invoke_camembert_success(self):
        """_invoke_camembert_fallacy returns detected_fallacies from self-hosted LLM."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_camembert_fallacy,
        )

        mock_plugin = MagicMock()
        mock_plugin.run_guided_analysis = AsyncMock(
            return_value=json.dumps(
                {
                    "fallacies": [
                        {
                            "fallacy_type": "Ad Hominem",
                            "confidence": 0.92,
                            "explanation": "Attack on person",
                            "taxonomy_pk": "1.1",
                        }
                    ],
                    "exploration_method": "self_hosted",
                }
            )
        )

        env = {
            "SELF_HOSTED_LLM_ENDPOINT": "http://localhost:5000/v1",
            "SELF_HOSTED_LLM_MODEL": "test-model",
        }

        # #2486: the function imports FallacyWorkflowPlugin from its module;
        # the sys.modules entry below is the mock it runs against.
        with _patch_invokecallables_env_get(env), patch("openai.AsyncOpenAI"), patch(
            "semantic_kernel.kernel.Kernel", autospec=True
        ), patch("semantic_kernel.connectors.ai.open_ai.OpenAIChatCompletion"):
            with patch.dict(
                "sys.modules",
                {
                    "openai": MagicMock(AsyncOpenAI=MagicMock()),
                    "semantic_kernel.kernel": MagicMock(Kernel=create_autospec(Kernel)),
                    "semantic_kernel.connectors.ai.open_ai": MagicMock(
                        OpenAIChatCompletion=MagicMock()
                    ),
                    "argumentation_analysis.plugins.fallacy_workflow_plugin": MagicMock(
                        FallacyWorkflowPlugin=MagicMock(return_value=mock_plugin)
                    ),
                },
            ):
                result = await _invoke_camembert_fallacy(
                    "Tu es stupide donc ton argument est faux.", {}
                )

        assert "detected_fallacies" in result
        assert result["total_fallacies"] == 1
        assert "Ad Hominem" in result["detected_fallacies"]
        assert result["tiers_used"] == ["self_hosted_llm"]

    async def test_invoke_camembert_empty_text(self):
        """_invoke_camembert_fallacy handles empty input (no endpoint configured)."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_camembert_fallacy,
        )

        # Without endpoint, returns early regardless of text
        with _patch_invokecallables_env_get(_NOT_CONFIGURED):
            result = await _invoke_camembert_fallacy("", {})

        assert result["total_fallacies"] == 0
        assert isinstance(result["detected_fallacies"], dict)

    async def test_invoke_camembert_import_failure(self):
        """_invoke_camembert_fallacy gracefully handles missing dependencies."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_camembert_fallacy,
        )

        env = {
            "SELF_HOSTED_LLM_ENDPOINT": "http://localhost:5000/v1",
            "SELF_HOSTED_LLM_MODEL": "test-model",
        }

        with _patch_invokecallables_env_get(env), patch.dict(
            "sys.modules", {"openai": None}
        ):
            result = await _invoke_camembert_fallacy("test text", {})

        # Should return graceful fallback, not crash
        assert isinstance(result, dict)
        assert result["detected_fallacies"] == {}
        assert result["total_fallacies"] == 0

    async def test_invoke_camembert_uses_to_thread(self):
        """_invoke_camembert_fallacy no longer uses to_thread (uses async SK)."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_camembert_fallacy,
        )

        # Without endpoint configured, the function returns early
        # without calling any async operations
        with _patch_invokecallables_env_get(_NOT_CONFIGURED):
            result = await _invoke_camembert_fallacy("test", {})

        assert result["tiers_used"] == ["none"]

    async def test_invoke_camembert_runtime_failure_is_degraded(self):
        """Anti-théâtre #1019 (#1275): a runtime failure (e.g. the configured
        SELF_HOSTED_LLM_MODEL 404s on the endpoint) must surface as degraded,
        NOT silently read as "ran and found 0 fallacies".

        Endpoint+model are configured (so the not-configured gate passes), but
        the plugin call raises — simulating the 404 observed in capstone #1269.
        """
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_camembert_fallacy,
        )

        # Plugin call raises (model 404 / endpoint error surfaces here)
        mock_plugin = MagicMock()
        mock_plugin.run_guided_analysis = AsyncMock(
            side_effect=RuntimeError("404 - model does not exist on endpoint")
        )

        env = {
            "SELF_HOSTED_LLM_ENDPOINT": "http://localhost:5000/v1",
            "SELF_HOSTED_LLM_MODEL": "qwen3.5-35b-a3b",
        }

        # #2486: as above, the sys.modules entry is the plugin the function
        # imports.
        with _patch_invokecallables_env_get(env), patch("openai.AsyncOpenAI"), patch(
            "semantic_kernel.kernel.Kernel", autospec=True
        ), patch("semantic_kernel.connectors.ai.open_ai.OpenAIChatCompletion"):
            with patch.dict(
                "sys.modules",
                {
                    "openai": MagicMock(AsyncOpenAI=MagicMock()),
                    "semantic_kernel.kernel": MagicMock(Kernel=create_autospec(Kernel)),
                    "semantic_kernel.connectors.ai.open_ai": MagicMock(
                        OpenAIChatCompletion=MagicMock()
                    ),
                    "argumentation_analysis.plugins.fallacy_workflow_plugin": MagicMock(
                        FallacyWorkflowPlugin=MagicMock(return_value=mock_plugin)
                    ),
                },
            ):
                result = await _invoke_camembert_fallacy(
                    "Argument ad hominem classique.", {}
                )

        # Honest zero: the run did NOT succeed, it degraded.
        assert result["total_fallacies"] == 0
        assert result["tiers_used"] == ["none"]
        assert result["detected_fallacies"] == {}
        # Anti-théâtre signal: downstream MUST be able to tell this apart from
        # a successful run that genuinely found 0 fallacies.
        assert result["status"] == "unavailable"
        assert result["degraded"] is True
        reason = result["degradation_reason"]
        assert isinstance(reason, str) and reason
        # Reason must attribute the failure to the configured model/endpoint
        # (not a generic "failed") so the operator can fix the config.
        assert "qwen3.5-35b-a3b" in reason
        assert "localhost:5000" in reason

    async def test_plugin_detection_reaches_the_state(self):
        """#2130 born-red witness (a): one fake-plugin detection ⇒ one
        ``neural_fallacy_scores`` entry in the state, through the REAL
        invoker and the REAL writer.

        The R1070 measure: the invoker emits ``detected_fallacies`` (a dict)
        while the writer read ``detections`` (a list no producer emits) — so
        even with a valid key and a responding service, nothing reached the
        state. On main ``314c04555`` this chain writes 0 entries.
        """
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_camembert_fallacy,
            _write_camembert_to_state,
        )
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState

        mock_plugin = MagicMock()
        mock_plugin.run_guided_analysis = AsyncMock(
            return_value=json.dumps(
                {
                    "fallacies": [
                        {
                            "fallacy_type": "Ad Hominem",
                            "confidence": 0.92,
                            "explanation": "Attack on person",
                            "taxonomy_pk": "1.1",
                        }
                    ],
                    "exploration_method": "self_hosted",
                }
            )
        )

        env = {
            "SELF_HOSTED_LLM_ENDPOINT": "http://localhost:5000/v1",
            "SELF_HOSTED_LLM_MODEL": "test-model",
        }

        with _patch_invokecallables_env_get(env), patch("openai.AsyncOpenAI"), patch(
            "semantic_kernel.kernel.Kernel", autospec=True
        ), patch("semantic_kernel.connectors.ai.open_ai.OpenAIChatCompletion"):
            with patch.dict(
                "sys.modules",
                {
                    "openai": MagicMock(AsyncOpenAI=MagicMock()),
                    "semantic_kernel.kernel": MagicMock(Kernel=create_autospec(Kernel)),
                    "semantic_kernel.connectors.ai.open_ai": MagicMock(
                        OpenAIChatCompletion=MagicMock()
                    ),
                    "argumentation_analysis.plugins.fallacy_workflow_plugin": MagicMock(
                        FallacyWorkflowPlugin=MagicMock(return_value=mock_plugin)
                    ),
                },
            ):
                result = await _invoke_camembert_fallacy("Argument ad hominem.", {})

        state = UnifiedAnalysisState("test text")
        _write_camembert_to_state(result, state, {})

        assert len(state.neural_fallacy_scores) == 1, (
            "the producer's detection must reach the state — a writer reading "
            "a key the producer never emits writes nothing (#2130)"
        )
        entry = state.neural_fallacy_scores[0]
        assert entry["label"] == "Ad Hominem"
        assert entry["confidence"] == 0.92
        assert entry["detector"] == "self_hosted_llm"

    async def test_plugin_error_is_the_degradation_reason(self):
        """#2130 born-red witness (b): a plugin that RETURNS an error (no
        exception — one-shot failed with 401, the shape measured on the
        R1070 paid run) makes the phase output name THAT error as the
        degradation reason, not the taxonomy bypass marker that also rode
        along.

        On main, the invoker drops ``error`` entirely and publishes only
        ``wide-net funnel bypassed (empty_taxonomy_navigator, …)`` — the run
        log says 401, the state says taxonomy.
        """
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_camembert_fallacy,
        )

        # The real-run double marker (R1070): taxonomy absent (bypass) AND
        # the one-shot itself failed with the 401.
        mock_plugin = MagicMock()
        mock_plugin.run_guided_analysis = AsyncMock(
            return_value=json.dumps(
                {
                    "error": "Error code: 401 - {'error': 'Unauthorized'}",
                    "fallacies": [],
                    "fallback_reason": "empty_taxonomy_navigator",
                    "taxonomy_state": "none",
                }
            )
        )

        env = {
            "SELF_HOSTED_LLM_ENDPOINT": "http://localhost:5000/v1",
            "SELF_HOSTED_LLM_MODEL": "test-model",
        }

        with _patch_invokecallables_env_get(env), patch("openai.AsyncOpenAI"), patch(
            "semantic_kernel.kernel.Kernel", autospec=True
        ), patch("semantic_kernel.connectors.ai.open_ai.OpenAIChatCompletion"):
            with patch.dict(
                "sys.modules",
                {
                    "openai": MagicMock(AsyncOpenAI=MagicMock()),
                    "semantic_kernel.kernel": MagicMock(Kernel=create_autospec(Kernel)),
                    "semantic_kernel.connectors.ai.open_ai": MagicMock(
                        OpenAIChatCompletion=MagicMock()
                    ),
                    "argumentation_analysis.plugins.fallacy_workflow_plugin": MagicMock(
                        FallacyWorkflowPlugin=MagicMock(return_value=mock_plugin)
                    ),
                },
            ):
                result = await _invoke_camembert_fallacy("Argument ad hominem.", {})

        assert result["degraded"] is True
        reason = result["degradation_reason"]
        # The reason names the error the plugin carried — the 401 the run
        # log shows — not the taxonomy marker that also rode along.
        assert (
            "401" in reason
        ), f"the plugin's error must be the degradation reason, got {reason!r}"
        assert "Unauthorized" in reason
        # The carried error is part of the phase output, not swallowed.
        assert "401" in result.get("error", "")


class TestCamemBERTRegistryRegistration:
    """Tests for neural_fallacy_detection registration in setup_registry."""

    def test_registry_includes_camembert_fallacy_detector(self):
        """setup_registry registers camembert_fallacy_detector when available."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            setup_registry,
        )

        registry = setup_registry(include_optional=True)
        providers = registry.find_for_capability("neural_fallacy_detection")
        names = [p.name for p in providers]
        # camembert_fallacy_detector may not be registered if import fails
        # but the registry should still be valid
        assert registry is not None
        assert isinstance(names, list)

    def test_registry_camembert_provides_neural_fallacy_detection(self):
        """camembert_fallacy_detector provides neural_fallacy_detection capability."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            setup_registry,
        )

        registry = setup_registry(include_optional=True)
        providers = registry.find_for_capability("neural_fallacy_detection")
        names = [p.name for p in providers]
        # #1593: ``isinstance(names, list)`` passed with the lookup stubbed
        # to return NO providers. The capability must have at least one
        # (measured: self_hosted_fallacy_detector; camembert joins when its
        # deps import).
        assert names, "neural_fallacy_detection must have at least one provider"

    def test_registry_camembert_optional_registration(self):
        """camembert_fallacy_detector is optional (graceful skip if unavailable)."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            setup_registry,
        )

        # Without patching, CamemBERT may or may not be available
        # The test verifies that setup_registry doesn't crash either way
        try:
            registry = setup_registry(include_optional=True)
            assert registry is not None
        except ImportError:
            # If FrenchFallacyAdapter is not available, it should be skipped
            pytest.skip("FrenchFallacyAdapter not available")
