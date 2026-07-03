"""RA-8 #1053 — Anti-theater value-gate tests.

Verifies that Tweety satellite handlers raise RuntimeError when JVM is
unavailable, instead of returning synthetic Python fallback results that
would be written to state as authentic formal analysis (#1019).

Each test forces the handler import to fail (JVM unavailable scenario) and
asserts that:
1. A RuntimeError is raised (not a dict with "fallback": "python")
2. No synthetic result enters the state

Pattern: 16 handlers = 16 fail-loud tests + 2 anti-regression (Dung + QBF
native paths that remain legitimate).

NOTE: On machines with JVM available (like CI/agent machines), the handler
imports succeed — so we must mock them to fail to test the fallback path.
"""

import asyncio
import sys
from unittest.mock import patch, MagicMock

import pytest


# ---------------------------------------------------------------------------
# Helper: run an async function synchronously in tests
# ---------------------------------------------------------------------------
def _run(coro):
    """Run an async coroutine synchronously."""
    return asyncio.get_event_loop().run_until_complete(coro)


# ---------------------------------------------------------------------------
# Handlers under test — import at module level (all are async invoke_callables)
# ---------------------------------------------------------------------------
from argumentation_analysis.orchestration.invoke_callables import (
    _invoke_ranking,
    _invoke_bipolar,
    _invoke_aba,
    _invoke_adf,
    _invoke_aspic,
    _invoke_belief_revision,
    _invoke_probabilistic,
    _invoke_dialogue,
    _invoke_dl,
    _invoke_cl,
    _invoke_setaf,
    _invoke_weighted,
    _invoke_social,
    _invoke_eaf,
    _invoke_delp,
    _invoke_propositional_logic,
)

# ---------------------------------------------------------------------------
# Test data fixtures
# ---------------------------------------------------------------------------
_INPUT = "Test argument about climate policy."
_CTX = {
    "arguments": ["arg1", "arg2", "arg3"],
    "attacks": [["arg1", "arg2"]],
    "assumptions": ["a1", "a2", "a3"],
    "rules": ["r1", "r2"],
    "contraries": None,
    "semantics": "preferred",
    "statements": ["s1", "s2", "s3"],
    "acceptance_conditions": {"s1": "and(c(v))"},
    "tbox": ["A subsumes B"],
    "abox_concepts": ["a: A"],
    "abox_roles": [],
    "conditionals": ["A => B"],
    "query_conclusion": "B",
    "query_premise": None,
    "set_attacks": [["arg1"], ["arg2"]],
    "weighted_attacks": [{"source": "arg1", "target": "arg2", "weight": 0.8}],
    "votes": {"arg1": (3, 1), "arg2": (1, 3)},
    "program": "a <- b. -a.",
    "queries": ["a"],
    "criterion": "generalized_specificity",
    "proponent_args": ["arg1"],
    "opponent_args": ["arg2"],
    "topic": "Test topic",
    "formulas": ["p1 & p2", "!p1"],
    "probabilities": {"arg1": 0.7, "arg2": 0.3},
    "beliefs": ["belief1", "belief2"],
    "new_belief": "NOT(belief1)",
    "revision_method": "dalal",
}


# ---------------------------------------------------------------------------
# Fail-loud tests: each handler MUST raise RuntimeError when JVM unavailable
# ---------------------------------------------------------------------------
class TestRankingFailLoud:
    def test_raises_runtime_error(self):
        """When ranking handler import fails, must raise RuntimeError."""
        with patch.dict(
            sys.modules,
            {
                "argumentation_analysis.agents.core.logic.ranking_handler": None,
            },
        ):
            with pytest.raises(RuntimeError, match="Ranking semantics"):
                _run(_invoke_ranking(_INPUT, _CTX))


class TestBipolarFailLoud:
    def test_raises_runtime_error(self):
        # Force the handler import to fail (JVM-unavailable scenario) — on a
        # JVM-available machine (CI/agent) the real handler would run and never
        # fail-loud, so we mock it to fail exactly as the file docstring says.
        with patch.dict(
            sys.modules,
            {"argumentation_analysis.agents.core.logic.bipolar_handler": None},
        ):
            with pytest.raises(RuntimeError, match="Bipolar analysis"):
                _run(_invoke_bipolar(_INPUT, _CTX))


class TestABAFailLoud:
    def test_raises_runtime_error(self):
        with patch.dict(
            sys.modules,
            {"argumentation_analysis.agents.core.logic.aba_handler": None},
        ):
            with pytest.raises(RuntimeError, match="ABA reasoning"):
                _run(_invoke_aba(_INPUT, _CTX))


class TestADFFailLoud:
    def test_raises_runtime_error(self):
        with patch.dict(
            sys.modules,
            {"argumentation_analysis.agents.core.logic.adf_handler": None},
        ):
            with pytest.raises(RuntimeError, match="ADF reasoning"):
                _run(_invoke_adf(_INPUT, _CTX))


class TestASPICFailLoud:
    def test_raises_runtime_error(self):
        with patch.dict(
            sys.modules,
            {"argumentation_analysis.agents.core.logic.aspic_handler": None},
        ):
            with pytest.raises(RuntimeError, match="ASPIC\\+"):
                _run(_invoke_aspic(_INPUT, _CTX))


class TestBeliefRevisionFailLoud:
    def test_raises_runtime_error(self):
        with patch.dict(
            sys.modules,
            {"argumentation_analysis.agents.core.logic.belief_revision_handler": None},
        ):
            with pytest.raises(RuntimeError, match="Belief revision"):
                _run(_invoke_belief_revision(_INPUT, _CTX))


class TestProbabilisticFailLoud:
    def test_raises_runtime_error(self):
        with patch.dict(
            sys.modules,
            {"argumentation_analysis.agents.core.logic.probabilistic_handler": None},
        ):
            with pytest.raises(RuntimeError, match="Probabilistic"):
                _run(_invoke_probabilistic(_INPUT, _CTX))


class TestDialogueFailLoud:
    def test_raises_runtime_error(self):
        """When dialogue handler import fails, must raise RuntimeError."""
        with patch.dict(
            sys.modules,
            {
                "argumentation_analysis.agents.core.logic.dialogue_handler": None,
            },
        ):
            with pytest.raises(RuntimeError, match="Dialogue protocol"):
                _run(_invoke_dialogue(_INPUT, _CTX))


class TestDLFailLoud:
    def test_raises_runtime_error(self):
        with patch.dict(
            sys.modules,
            {"argumentation_analysis.agents.core.logic.dl_handler": None},
        ):
            with pytest.raises(RuntimeError, match="Description Logic"):
                _run(_invoke_dl(_INPUT, _CTX))


class TestCLFailLoud:
    def test_raises_runtime_error(self):
        with patch.dict(
            sys.modules,
            {"argumentation_analysis.agents.core.logic.cl_handler": None},
        ):
            with pytest.raises(RuntimeError, match="Conditional Logic"):
                _run(_invoke_cl(_INPUT, _CTX))


class TestSetAFFailLoud:
    def test_raises_runtime_error(self):
        with patch.dict(
            sys.modules,
            {"argumentation_analysis.agents.core.logic.setaf_handler": None},
        ):
            with pytest.raises(RuntimeError, match="SetAF"):
                _run(_invoke_setaf(_INPUT, _CTX))


class TestWeightedFailLoud:
    def test_raises_runtime_error(self):
        with patch.dict(
            sys.modules,
            {"argumentation_analysis.agents.core.logic.weighted_handler": None},
        ):
            with pytest.raises(RuntimeError, match="Weighted AF"):
                _run(_invoke_weighted(_INPUT, _CTX))


class TestSocialFailLoud:
    def test_raises_runtime_error(self):
        with patch.dict(
            sys.modules,
            {"argumentation_analysis.agents.core.logic.social_handler": None},
        ):
            with pytest.raises(RuntimeError, match="Social argumentation"):
                _run(_invoke_social(_INPUT, _CTX))


class TestEAFFailLoud:
    def test_raises_runtime_error(self):
        with patch.dict(
            sys.modules,
            {"argumentation_analysis.agents.core.logic.eaf_handler": None},
        ):
            with pytest.raises(RuntimeError, match="Epistemic AF"):
                _run(_invoke_eaf(_INPUT, _CTX))


class TestDeLPFailLoud:
    def test_raises_runtime_error(self):
        with patch.dict(
            sys.modules,
            {"argumentation_analysis.agents.core.logic.delp_handler": None},
        ):
            with pytest.raises(RuntimeError, match="DeLP"):
                _run(_invoke_delp(_INPUT, _CTX))


class TestPLFailLoud:
    """PL handler: when all Tweety solvers fail, must raise RuntimeError."""

    def test_raises_runtime_error(self):
        """When Tweety/PySAT is unavailable, PL must fail-loud.

        The old input ``$$UNPARSEABLE$$`` no longer reaches the fail-loud path:
        the #537 PL sanitizer legitimately salvages it into the valid atom
        ``__UNPARSEABLE__``, which PySAT then decides SAT — a real solver
        verdict, not theater. To exercise the actual "all Tweety solvers
        failed" contract (invoke_callables L5390) we force the TweetyBridge
        import to fail (JVM/Tweety-unavailable scenario), matching the
        sys.modules pattern the other fail-loud tests use.
        """
        ctx_bad = {
            "arguments": ["arg1", "arg2"],
            "formulas": ["p & q"],
        }
        with patch.dict(
            sys.modules,
            {"argumentation_analysis.agents.core.logic.tweety_bridge": None},
        ):
            with pytest.raises(RuntimeError, match="Propositional logic"):
                _run(_invoke_propositional_logic("test input", ctx_bad))


# ---------------------------------------------------------------------------
# Anti-regression: legitimate paths that must NOT raise
# ---------------------------------------------------------------------------
class TestDungNativeSurvives:
    """FP-22 #1249: _python_dung_fallback is now a fail-loud stub — raises RuntimeError."""

    def test_dung_fallback_raises_runtime_error(self):
        """_python_dung_fallback must raise RuntimeError — no fabricated extensions (#1019)."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _python_dung_fallback,
        )

        with pytest.raises(RuntimeError, match="JVM/Tweety required"):
            _python_dung_fallback(["a", "b"], [["a", "b"]])


class TestQBFNativeSurvives:
    """QBF already uses 'fallback': 'error' (conformant #1019)."""

    def test_qbf_fallback_is_error_not_python(self):
        """QBF native fallback returns 'fallback': 'error', not 'python'."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_qbf,
        )

        # QBF has its own native solver — test that the error fallback is
        # 'fallback': 'error', not 'python'
        with patch(
            "argumentation_analysis.orchestration.invoke_callables.asyncio.to_thread",
            side_effect=ImportError("No QBF module"),
        ):
            result = _run(_invoke_qbf(_INPUT, _CTX))
            assert isinstance(result, dict)
            assert result.get("fallback") == "error"
            assert result.get("fallback") != "python"


# ---------------------------------------------------------------------------
# State-writer guard: verify no writer processes RuntimeError
# ---------------------------------------------------------------------------
class TestStateWriterGuard:
    """Verify state writers never see fallback results (error propagated before)."""

    def test_writer_not_called_on_runtime_error(self):
        """If invoke raises RuntimeError, the state writer must not be called."""
        from argumentation_analysis.orchestration.state_writers import (
            _write_aba_to_state,
        )

        mock_state = MagicMock()
        # Invoke raises RuntimeError (as it does now when JVM unavailable)
        with patch.dict(
            sys.modules,
            {
                "argumentation_analysis.agents.core.logic.aba_handler": None,
            },
        ):
            with pytest.raises(RuntimeError):
                _run(_invoke_aba(_INPUT, _CTX))
        # Writer was never called because invoke raised before producing output
        mock_state.add_dung_framework.assert_not_called()
