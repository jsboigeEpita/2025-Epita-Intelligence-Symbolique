"""Track B #1278 — NL→FOL vivant-ou-fail-loud contract tests.

Pins the two acceptable outcomes (issue #1278 DoD, coordinator R479):

  1. ``decided``     — a real formula reaches the prover, which returns a
                       definite verdict (True/False).
  2. ``unavailable`` — no real formula could be translated from the source →
                       fail loud with a reason (``no-translation`` / ``parse-
                       fail``), NEVER 'trivially consistent sur vide' nor
                       fabricated ``Asserted(argN)`` templates (#1019).

Covers every ``_invoke_fol_reasoning`` return path, the ``_write_fol_to_state``
message passthrough, and the act2 honest 'FOL indisponible' surfacing.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

TWEETY_BRIDGE_PATH = (
    "argumentation_analysis.agents.core.logic.tweety_bridge.TweetyBridge"
)


def _run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


def _ctx_with_fol_formula(formula: str) -> dict:
    """Context carrying one upstream FOL formula (logic_type-agnostic injection
    via context['formulas'], unioned into the belief set)."""
    return {
        "phase_extract_output": {"arguments": [{"text": "some argument"}]},
        "formulas": [formula],
        "_state_object": None,
    }


# ---------------------------------------------------------------------------
# DoD #1 — decided: real formula + prover verdict
# ---------------------------------------------------------------------------


class TestFolDecidedOnRealFormulas:
    """A real FOL formula reaches the prover → fol_status='decided'."""

    def test_decided_consistent(self):
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_fol_reasoning,
        )

        context = _ctx_with_fol_formula("forall X: (Human(X) => Mortal(X))")
        mock_bridge = MagicMock()
        mock_bridge.check_consistency.return_value = (
            True,
            "FOL consistency check: consistent.",
        )
        with patch(TWEETY_BRIDGE_PATH, return_value=mock_bridge):
            result = _run(_invoke_fol_reasoning("text", context))

        assert result["fol_status"] == "decided"
        assert result["consistent"] is True
        assert any("Human" in f for f in result["formulas"])
        # No fabricated template predicate leaked in.
        assert not any(f.startswith("Asserted(arg") for f in result["formulas"])

    def test_decided_inconsistent(self):
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_fol_reasoning,
        )

        context = _ctx_with_fol_formula("forall X: (P(X) && !P(X))")
        mock_bridge = MagicMock()
        mock_bridge.check_consistency.return_value = (
            False,
            "FOL consistency check: inconsistent.",
        )
        with patch(TWEETY_BRIDGE_PATH, return_value=mock_bridge):
            result = _run(_invoke_fol_reasoning("text", context))

        assert result["fol_status"] == "decided"
        assert result["consistent"] is False


# ---------------------------------------------------------------------------
# DoD #2 — unavailable:no-translation
# ---------------------------------------------------------------------------


class TestFolUnavailableNoTranslation:
    """No formula translated → unavailable:no-translation (not 'trivially
    consistent sur vide', not fabricated templates)."""

    def test_no_formulas_marks_unavailable(self):
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_fol_reasoning,
        )

        context = {
            "phase_extract_output": {"arguments": [{"text": "an argument"}]},
            "_state_object": None,
        }
        # Force the no-translation path deterministically (no LLM, no on-the-fly
        # NL translator) regardless of API-key presence.
        with patch.dict(
            "sys.modules", {"argumentation_analysis.services.nl_to_logic": None}
        ):
            result = _run(_invoke_fol_reasoning("text", context))

        assert result["fol_status"] == "unavailable:no-translation"
        assert result["consistent"] is None
        assert result["formulas"] == []
        assert result["confidence"] == 0.0
        assert not any(f.startswith("Asserted(arg") for f in result.get("formulas", []))


# ---------------------------------------------------------------------------
# DoD #2 (variant) — unavailable:parse-fail
# ---------------------------------------------------------------------------


class TestFolUnavailableParseFail:
    """Formulas were produced but none parse into a verifiable belief set."""

    def test_all_formulas_rejected_by_solver(self):
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_fol_reasoning,
        )

        context = _ctx_with_fol_formula("garbage ((( not a formula")
        mock_bridge = MagicMock()
        # The combined check AND every per-formula isolation check reject.
        mock_bridge.check_consistency.side_effect = Exception("Tweety parse error")
        with patch(TWEETY_BRIDGE_PATH, return_value=mock_bridge):
            result = _run(_invoke_fol_reasoning("text", context))

        assert result["fol_status"] == "unavailable:parse-fail"
        assert result["consistent"] is None
        assert result["confidence"] == 0.0


# ---------------------------------------------------------------------------
# State writer — unavailable token surfaces on the entry
# ---------------------------------------------------------------------------


class TestStateWriterSurfacesUnavailable:
    """_write_fol_to_state carries the honest status as ``message`` (#1278)."""

    def test_unavailable_message_passed_to_state(self):
        from argumentation_analysis.orchestration.state_writers import (
            _write_fol_to_state,
        )

        state = MagicMock()
        output = {
            "formulas": [],
            "consistent": None,
            "fol_status": "unavailable:no-translation",
            "inferences": [],
            "confidence": 0.0,
        }
        _write_fol_to_state(output, state, {})

        assert state.add_fol_analysis_result.called
        call = state.add_fol_analysis_result.call_args
        # consistent preserved as None (not coerced to False, #1019).
        assert call[0][1] is None
        # message kwarg carries the unavailable token.
        assert call.kwargs.get("message") == "unavailable:no-translation"

    def test_decided_keeps_solver_message(self):
        from argumentation_analysis.orchestration.state_writers import (
            _write_fol_to_state,
        )

        state = MagicMock()
        output = {
            "formulas": ["forall X: (Human(X) => Mortal(X))"],
            "consistent": True,
            "fol_status": "decided",
            "message": "FOL consistency check: consistent.",
            "inferences": [],
            "confidence": 0.8,
        }
        _write_fol_to_state(output, state, {})

        call = state.add_fol_analysis_result.call_args
        assert call[0][1] is True
        assert call.kwargs.get("message") == "FOL consistency check: consistent."


# ---------------------------------------------------------------------------
# act2 — honest 'FOL indisponible' surfacing
# ---------------------------------------------------------------------------


def _findings_state(fol_results):
    return SimpleNamespace(
        propositional_analysis_results=[],
        fol_analysis_results=fol_results,
        dung_frameworks={},
    )


class TestAct2FolIndisponibleSurfacing:
    """When FOL is unavailable, the restitution surfaces it honestly instead of
    silence (DoD #2: 'marquer l'axe FOL unavailable: <raison>')."""

    def test_unavailable_fol_surfaces_indisponible(self):
        from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
            _collect_formal_findings,
        )

        state = _findings_state(
            [{"consistent": None, "message": "unavailable:no-translation"}]
        )
        findings = _collect_formal_findings(state)
        fol_findings = [f for f in findings if f.kind == "fol"]
        assert len(fol_findings) == 1
        assert "indisponible" in fol_findings[0].verdict.lower()

    def test_decided_fol_not_marked_indisponible(self):
        from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
            _collect_formal_findings,
        )

        state = _findings_state([{"consistent": True}])
        findings = _collect_formal_findings(state)
        fol_findings = [f for f in findings if f.kind == "fol"]
        assert len(fol_findings) == 1
        assert "indisponible" not in fol_findings[0].verdict.lower()
        # French restitution wording for a consistent FOL theory.
        assert "consistante" in fol_findings[0].verdict.lower()

    def test_no_fol_results_no_indisponible_finding(self):
        from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
            _collect_formal_findings,
        )

        state = _findings_state([])
        findings = _collect_formal_findings(state)
        assert not any(f.kind == "fol" for f in findings)
