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
        result = asyncio.get_event_loop().run_until_complete(invoke("a :- b. b.", {}))
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
        result = asyncio.get_event_loop().run_until_complete(invoke("", {}))
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
        result = asyncio.get_event_loop().run_until_complete(invoke("a.", {}))
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
        # #1583: family-(a) — short input leaks a real NL→logic LLM call; the
        # verdict (formulas/logic_type) is solver routing, not model-gated.
        with patch("openai.AsyncOpenAI", side_effect=RuntimeError("no-network-1583")):
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
        mock_instance._fol_check_consistency_with_eprover.return_value = (
            True,
            "Consistent",
        )
        mock_handler_cls.return_value = mock_instance

        # Patch the import within the function
        invoke = self._get_invoke()
        with patch.dict(
            "sys.modules",
            {
                "argumentation_analysis.agents.core.logic.fol_handler": MagicMock(
                    FOLHandler=mock_handler_cls
                ),
            },
        ):
            result = asyncio.get_event_loop().run_until_complete(
                invoke("test", {"fol_solver": "eprover", "formulas": ["P(X)"]})
            )
            assert result.get("solver") == "eprover" or "formulas" in result

    def test_eprover_fallback_on_import_error(self):
        """When EProver handler can't be imported, falls back to Tweety."""
        invoke = self._get_invoke()
        # #1583: family-(a) — verdict (fallback result) is local; patch ctor.
        with patch("openai.AsyncOpenAI", side_effect=RuntimeError("no-network-1583")):
            result = asyncio.get_event_loop().run_until_complete(
                invoke("test argument", {"fol_solver": "eprover"})
            )
        # Should still produce a result (fallback to Tweety or Python)
        assert "formulas" in result or "error" in result

    def test_prover9_solver_choice_fallback(self):
        """When fol_solver=prover9 but Prover9 unavailable, falls back."""
        invoke = self._get_invoke()
        # #1583: family-(a) — verdict (fallback result) is local; patch ctor.
        with patch("openai.AsyncOpenAI", side_effect=RuntimeError("no-network-1583")):
            result = asyncio.get_event_loop().run_until_complete(
                invoke("test argument", {"fol_solver": "prover9"})
            )
        # #1588: the previous sole assertion was ``isinstance(result, dict)``,
        # which no state of the code could falsify — every return path of
        # ``_invoke_fol_reasoning`` returns a dict. Assert instead the property
        # the name promises: the prover9 choice is routed away (fallback) and
        # still terminates on a rendered FOL outcome rather than an arbitrary
        # mapping. All four return paths carry ``fol_status``/``logic_type``,
        # so this holds whichever backend the runner ends up using.
        assert result["logic_type"] == "first_order"
        assert result["fol_status"], "no FOL status rendered — routing did not complete"
        assert "prover9" not in str(result.get("message", "")).lower(), (
            "Prover9 reported as the engine that ran — the test is named for the "
            "fallback; if Prover9 is now wired, rename it and assert the verdict."
        )


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


# ---------------------------------------------------------------------------
# #1634: a Tweety parse failure must not be serialized as a decided verdict
# ---------------------------------------------------------------------------


class TestParseFailureIsNotAVerdict:
    """A refused belief set decided nothing, and must say so.

    Measured on a real JVM before the fix, driving the production callable with
    an unparsable FOL belief set: ``consistent=False`` — the *same* value a
    genuinely inconsistent theory produces — while the accompanying message
    read ``"Degraded: FOL consistency check error (Erreur de parsing Tweety
    …)"``. The message was honest; the field a reader actually consumes was
    not, and it always erred toward the negative.

    Each test below asserts the CONTRAST (undecided vs decided), not just the
    sentinel: asserting ``is None`` alone would survive a change that made
    every outcome None.
    """

    @staticmethod
    def _run(coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    def _fol_with_handler_reply(self, reply, solver="eprover", eprover=True):
        """Drive the real external-FOL callable over one bridge reply."""
        import argumentation_analysis.orchestration.invoke_callables as mod
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_external_fol_solver,
        )

        bridge = MagicMock()
        bridge.check_consistency.return_value = reply
        fake_mod = MagicMock()
        fake_mod.TweetyBridge.return_value = bridge
        with patch.dict(
            "sys.modules",
            {"argumentation_analysis.agents.core.logic.tweety_bridge": fake_mod},
        ), patch.object(
            mod.shutil, "which", side_effect=lambda b: "/x" if eprover else None
        ):
            return self._run(
                _invoke_external_fol_solver(
                    "probe",
                    {
                        "fol_solver": solver,
                        "phase_fol_output": {"formulas": ["P(a)"]},
                    },
                )
            )

    @pytest.mark.parametrize("eprover", [True, False], ids=["eprover", "tweety"])
    def test_fol_parse_failure_is_undecided_on_both_branches(self, eprover):
        """Both FOL return paths flattened the handler's ``None`` (#1634).

        The EProver branch and the TweetyBridge fallback carried the same
        ``bool(is_consistent)``; the fallback is the one real corpora take,
        since ``eprover`` is usually not on PATH.
        """
        degraded = self._fol_with_handler_reply(
            (None, "Degraded: FOL consistency check error (parse)"), eprover=eprover
        )
        decided = self._fol_with_handler_reply(
            (False, "FOL consistency check (EProver): inconsistent"), eprover=eprover
        )
        assert decided["consistent"] is False, "a real inconsistency still decides"
        assert degraded["consistent"] is None, "a parse failure decided nothing"
        assert degraded["consistent"] is not decided["consistent"], (
            "a parse failure is indistinguishable from a decided inconsistency "
            "again — that conflation is #1634"
        )

    def test_fol_degraded_flag_tracks_the_verdict_rather_than_the_solver(self):
        """``degraded`` was hardcoded False on every branch — an inert field.

        It never meant "we fell back to Tweety" (#1019 settled that Tweety is a
        genuine reasoner); it now means "no verdict was reached", which is the
        one thing it can usefully tell the state writer.
        """
        degraded = self._fol_with_handler_reply((None, "Degraded: parse"))
        decided = self._fol_with_handler_reply((True, "consistent"))
        assert degraded["degraded"] is True
        assert decided["degraded"] is False

    def test_modal_parse_failure_is_undecided(self):
        """The modal external phase inherited the wrapper's flattening (#1634)."""
        import argumentation_analysis.orchestration.invoke_callables as mod
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_external_modal_solver,
        )

        def run(verdict):
            bridge = MagicMock()
            bridge.execute_modal_query.return_value = (verdict, "msg")
            fake_mod = MagicMock()
            fake_mod.TweetyBridge.return_value = bridge
            with patch.dict(
                "sys.modules",
                {"argumentation_analysis.agents.core.logic.tweety_bridge": fake_mod},
            ), patch.object(mod.shutil, "which", return_value=None):
                return self._run(
                    _invoke_external_modal_solver(
                        "probe",
                        {
                            "phase_modal_output": {
                                "formulas": ["[](p)"],
                                "modalities": ["necessity"],
                            }
                        },
                    )
                )

        assert run(False)["valid"] is False, "a decided negative stays decided"
        assert run(None)["valid"] is None, "a refused belief set decided nothing"

    def test_prover9_reports_what_the_binary_actually_said(self):
        """#1634 + a polarity inversion found at the same line.

        The Prover9 input is a bare SOS list with **no goal**, so a proof is the
        derivation of the empty clause: ``THEOREM PROVED`` ⇒ the KB is
        INCONSISTENT, ``SEARCH FAILED`` ⇒ consistent. The old expression stored
        ``consistent = proved``, exactly backwards — measured against the
        bundled binary, ``P(a). -P(a).`` yielded THEOREM PROVED and was stored
        ``consistent=True``.

        And with neither marker present, nothing was decided at all.
        """
        import argumentation_analysis.orchestration.invoke_callables as mod
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_external_fol_solver,
        )

        def run(prover9_stdout):
            fake_runner = MagicMock()
            fake_runner.run_prover9.return_value = prover9_stdout
            with patch.dict(
                "sys.modules",
                {"argumentation_analysis.core.prover9_runner": fake_runner},
            ), patch.object(mod.shutil, "which", return_value=None), patch(
                "pathlib.Path.is_file", return_value=True
            ):
                return self._run(
                    _invoke_external_fol_solver(
                        "probe",
                        {
                            "fol_solver": "prover9",
                            "phase_fol_output": {"formulas": ["P(a)"]},
                        },
                    )
                )

        refuted = run("... THEOREM PROVED ...")
        exhausted = run("... SEARCH FAILED ...")
        silent = run("... nothing conclusive here ...")

        assert refuted["solver"] == "prover9", "the prover9 branch was not taken"
        assert refuted["consistent"] is False, (
            "Prover9 derived the empty clause from the SOS list — that is an "
            "INCONSISTENT KB, not a consistent one"
        )
        assert exhausted["consistent"] is True
        assert silent["consistent"] is None
        assert silent["degraded"] is True
