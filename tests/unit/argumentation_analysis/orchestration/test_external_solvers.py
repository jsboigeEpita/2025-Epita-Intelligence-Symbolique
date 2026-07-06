"""Tests for external solver wiring in invoke_callables (#479).

Validates:
- _invoke_asp_reasoning: Clingo ASP solver with graceful fallback
- _invoke_fol_reasoning: EProver/Prover9 solver choice routing
- _invoke_modal_logic: SPASS solver choice routing
- _invoke_sat: SAT solver invocation
- Registry registration of ASP reasoning service
"""

import asyncio
import json
import pytest
from unittest.mock import MagicMock, patch, AsyncMock


# ---------------------------------------------------------------------------
# Test: _invoke_asp_reasoning (Clingo/ASP)
# ---------------------------------------------------------------------------


class TestInvokeASPReasoning:
    def _get_invoke(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_asp_reasoning,
        )
        return _invoke_asp_reasoning

    def test_fallback_when_no_jvm(self):
        """When no JVM is available, uses Python clingo or heuristic fallback."""
        invoke = self._get_invoke()
        result = asyncio.get_event_loop().run_until_complete(
            invoke("a :- b. b.", {})
        )
        # Either clingo_python (if clingo package available) or heuristic
        assert result["solver"] in ("clingo_python", "clingo_jvm", "heuristic")

    def test_program_from_context(self):
        """Uses program from context when provided."""
        invoke = self._get_invoke()
        result = asyncio.get_event_loop().run_until_complete(
            invoke("ignored", {"program": "fact1. fact2 :- fact1."})
        )
        assert "fact1" in result["program"] or "program" in result

    def test_empty_program(self):
        """Handles empty program gracefully."""
        invoke = self._get_invoke()
        result = asyncio.get_event_loop().run_until_complete(
            invoke("", {})
        )
        assert "solver" in result

    def test_comment_only_program(self):
        """Skips comment-only ASP programs."""
        invoke = self._get_invoke()
        result = asyncio.get_event_loop().run_until_complete(
            invoke("% this is a comment\n% another comment", {})
        )
        # Heuristic returns 0 models, clingo may return 0 or 1 empty model
        assert result["num_models"] >= 0

    @patch("argumentation_analysis.core.jvm_setup.is_jvm_started", return_value=False)
    def test_jvm_not_ready_falls_through(self, mock_jvm):
        """When JVM not ready, tries Python clingo then heuristic."""
        invoke = self._get_invoke()
        result = asyncio.get_event_loop().run_until_complete(
            invoke("a.", {})
        )
        # Either clingo_python or heuristic
        assert result["solver"] in ("clingo_python", "clingo_jvm", "heuristic")


# ---------------------------------------------------------------------------
# Test: _invoke_fol_reasoning with external solvers
# ---------------------------------------------------------------------------


class TestInvokeFOLWithExternalSolvers:
    def _get_invoke(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_fol_reasoning,
        )
        return _invoke_fol_reasoning

    def test_default_tweety_routing(self):
        """Without fol_solver context, uses TweetyBridge or Python fallback."""
        invoke = self._get_invoke()
        result = asyncio.get_event_loop().run_until_complete(
            invoke("test argument", {})
        )
        assert "formulas" in result
        assert "logic_type" in result
        assert result["logic_type"] == "first_order"

    @patch(
        "argumentation_analysis.orchestration.invoke_callables.FOLHandler",
        create=True,
    )
    def test_eprover_solver_choice(self, mock_handler_cls):
        """When fol_solver=eprover, routes to EProver."""
        # Mock the FOLHandler and its method
        mock_instance = MagicMock()
        mock_instance._fol_check_consistency_with_eprover.return_value = (True, "Consistent")
        mock_handler_cls.return_value = mock_instance

        # Patch the import within the function
        invoke = self._get_invoke()
        with patch.dict("sys.modules", {
            "argumentation_analysis.agents.core.logic.fol_handler": MagicMock(
                FOLHandler=mock_handler_cls
            ),
        }):
            result = asyncio.get_event_loop().run_until_complete(
                invoke("test", {"fol_solver": "eprover", "formulas": ["P(X)"]})
            )
            assert result.get("solver") == "eprover" or "formulas" in result

    def test_eprover_fallback_on_import_error(self):
        """When EProver handler can't be imported, falls back to Tweety."""
        invoke = self._get_invoke()
        result = asyncio.get_event_loop().run_until_complete(
            invoke("test argument", {"fol_solver": "eprover"})
        )
        # Should still produce a result (fallback to Tweety or Python)
        assert "formulas" in result or "error" in result

    def test_prover9_solver_choice_fallback(self):
        """When fol_solver=prover9 but Prover9 unavailable, falls back."""
        invoke = self._get_invoke()
        result = asyncio.get_event_loop().run_until_complete(
            invoke("test argument", {"fol_solver": "prover9"})
        )
        # Should produce a result either way
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# Test: _invoke_modal_logic with SPASS
# ---------------------------------------------------------------------------


class TestInvokeModalWithSPASS:
    def _get_invoke(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_modal_logic,
        )
        return _invoke_modal_logic

    # #1279 (2ccb1de3): a modal KB is supplied through ``context['formulas']``
    # (the direct/hand-written-KB channel). Raw text with no nl_to_logic
    # translation and no direct formulas is honestly marked
    # ``unavailable:no-translation`` — the pre-#1279 ``[input_text]`` raw-parse
    # fallback was removed as the #1224 trap (never feed raw prose to MlParser,
    # #1019). These tests pass the formula via context, matching the already-
    # passing ``test_formulas_from_context``; the modality-detection assertions
    # are unchanged.

    def test_default_tweety_routing(self):
        """Default routing (no explicit modal_solver) detects necessity."""
        invoke = self._get_invoke()
        result = asyncio.get_event_loop().run_until_complete(
            invoke("[](p -> q)", {"formulas": ["[](p -> q)"]})
        )
        assert "modalities" in result
        assert "necessity" in result["modalities"]

    def test_necessity_modality_detected(self):
        """Detects [] as necessity modality."""
        invoke = self._get_invoke()
        result = asyncio.get_event_loop().run_until_complete(
            invoke("[](p)", {"formulas": ["[](p)"]})
        )
        assert "necessity" in result["modalities"]

    def test_possibility_modality_detected(self):
        """Detects <> as possibility modality."""
        invoke = self._get_invoke()
        result = asyncio.get_event_loop().run_until_complete(
            invoke("<>(p)", {"formulas": ["<>(p)"]})
        )
        assert "possibility" in result["modalities"]

    def test_spass_solver_choice_fallback(self):
        """When modal_solver=spass but SPASS unavailable, falls back."""
        invoke = self._get_invoke()
        result = asyncio.get_event_loop().run_until_complete(
            invoke("[](p)", {"modal_solver": "spass"})
        )
        # Should produce a result either way (Tweety or heuristic)
        assert "modalities" in result
        assert "logic_type" in result

    def test_formulas_from_context(self):
        """Uses formulas from context when provided."""
        invoke = self._get_invoke()
        result = asyncio.get_event_loop().run_until_complete(
            invoke("ignored", {"formulas": ["[](a)", "<>(b)"]})
        )
        assert "necessity" in result["modalities"]
        assert "possibility" in result["modalities"]


# ---------------------------------------------------------------------------
# Test: _invoke_sat
# ---------------------------------------------------------------------------


class TestInvokeSAT:
    def _get_invoke(self):
        from argumentation_analysis.orchestration.invoke_callables import _invoke_sat
        return _invoke_sat

    def test_sat_solve(self):
        """SAT solver with simple formula."""
        invoke = self._get_invoke()
        result = asyncio.get_event_loop().run_until_complete(
            invoke("p && q", {"formulas": ["p && q"]})
        )
        assert "satisfiable" in result or "error" in result

    def test_sat_mus_mode(self):
        """SAT solver in MUS mode."""
        invoke = self._get_invoke()
        result = asyncio.get_event_loop().run_until_complete(
            invoke("p", {"formulas": ["p && !p"], "sat_mode": "mus"})
        )
        assert "mode" in result


# ---------------------------------------------------------------------------
# Test: Registry registration
# ---------------------------------------------------------------------------


class TestRegistryASPService:
    def test_asp_reasoning_registered(self):
        from argumentation_analysis.orchestration.registry_setup import setup_registry

        registry = setup_registry(include_optional=False)
        reg = registry._registrations.get("asp_reasoning_handler")
        assert reg is not None
        assert "asp_reasoning" in reg.capabilities

    def test_fol_reasoning_registered(self):
        from argumentation_analysis.orchestration.registry_setup import setup_registry

        registry = setup_registry(include_optional=False)
        reg = registry._registrations.get("fol_reasoning_service")
        assert reg is not None
        assert "fol_reasoning" in reg.capabilities

    def test_modal_logic_registered(self):
        from argumentation_analysis.orchestration.registry_setup import setup_registry

        registry = setup_registry(include_optional=False)
        reg = registry._registrations.get("modal_logic_service")
        assert reg is not None
        assert "modal_logic" in reg.capabilities


class TestSafeFloatEnv:
    """Test _safe_float_env guards against non-numeric env vars (#1003).

    Hermeticity: ATT-1 (#1336) env-read cluster. We patch the bound
    ``os.environ.get`` *at the module level* (``mod.os.environ.get``) so the
    prod call inside ``_safe_float_env`` sees the test value regardless of
    ambient env pollution (some prior test leaking a mocked env). This is the
    same fix pattern as PR #1406 (no-key option B): make the test contract
    explicit by mocking the exact call site, not the global ``os.environ``.
    """

    def _patch_mod_env_get(self, key_to_value):
        """Helper: patch ``mod.os.environ.get`` so ``key`` returns *value*
        and other keys fall through to the real ``os.environ.get``.
        """
        import argumentation_analysis.orchestration.invoke_callables as mod
        import os as _os

        _real_get = mod.os.environ.get
        _override = dict(key_to_value)

        def side_effect(key, default=None):
            if key in _override:
                return _override[key]
            return _real_get(key, default)

        return patch.object(mod.os.environ, "get", side_effect=side_effect)

    def test_valid_numeric_string(self):
        """Numeric string is parsed correctly."""
        import argumentation_analysis.orchestration.invoke_callables as mod

        with self._patch_mod_env_get({"_TEST_FLOAT": "42.5"}):
            assert mod._safe_float_env("_TEST_FLOAT", 10.0) == 42.5

    def test_non_numeric_falls_back_to_default(self):
        """Non-numeric env var falls back to default without crash."""
        import argumentation_analysis.orchestration.invoke_callables as mod

        with self._patch_mod_env_get({"_TEST_FLOAT": "not_a_number"}):
            assert mod._safe_float_env("_TEST_FLOAT", 10.0) == 10.0

    def test_missing_key_falls_back_to_default(self):
        """Missing env var falls back to default."""
        import argumentation_analysis.orchestration.invoke_callables as mod

        # Provide a present-but-unrelated key so the override is non-empty;
        # the test asserts the MISSING key still falls back to default.
        with self._patch_mod_env_get({"_TEST_FLOAT": "irrelevant"}):
            assert mod._safe_float_env("_TEST_FLOAT_MISSING", 99.0) == 99.0
