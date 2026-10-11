"""Born-red witnesses for #3011 — conversational lane fallacy registration.

The parent-harness registration loop folded ``confidence`` into the fallback
justification prose and never passed ``confidence`` / ``problematic_quote`` to
``add_fallacy`` — the exact defect class #2972 repaired for the pipeline lane
(``_write_hierarchical_fallacy_to_state``), leaving the two lanes disagreeing
on which detections are filterable downstream (Act III weak-points slice, CSV
bundle). A registration failure was swallowed by a bare ``except Exception:
pass`` (#2978's CI exposed that class: a state rejecting a keyword vanished).

Fixtures are synthetic French (no corpus sentence, opaque ids only).
Real ``UnifiedAnalysisState`` throughout — the assertions read the canonical
``identified_fallacies`` surface DeepSynthesisAgent consumes, not a mock's
call log.
"""

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.orchestration.conversational_orchestrator import (
    _run_parent_harness_fallback,
)

# Short synthetic text (< 500 chars): the wide-net whole-text pass never
# fires, so only the per-argument invocation needs patching.
_SHORT_TEXT = "Texte synthétique pour le harnais parent, sans phrase de corpus."


def _harness(detection):
    """Patch the per-argument harness to return ``detection`` and pin the
    target-resolution ladder to None — the witness measures the registration
    contract, not #1633's resolution."""
    return patch(
        "argumentation_analysis.orchestration.invoke_callables."
        "_invoke_hierarchical_fallacy_per_argument",
        new_callable=AsyncMock,
        return_value={
            "fallacies": [detection],
            "exploration_method": "per_argument_parallel",
        },
    )


def _no_target():
    return patch(
        "argumentation_analysis.orchestration.state_writers."
        "resolve_fallacy_target_arg_id",
        return_value=None,
    )


def _single_entry(state: UnifiedAnalysisState):
    assert len(state.identified_fallacies) == 1
    return next(iter(state.identified_fallacies.values()))


class TestConfidenceAsField:
    async def test_measured_confidence_and_quote_reach_state_fields(self):
        """Born red on main: neither field is passed to add_fallacy."""
        state = UnifiedAnalysisState(initial_text="x")
        detection = {
            "fallacy_type": "appel_a_autorite",
            "justification": "Aucune source vérifiée n'étaye l'affirmation.",
            "confidence": 0.8,
            "problematic_quote": "Tous les experts s'accordent sur ce point.",
        }
        with _harness(detection), _no_target():
            result = await _run_parent_harness_fallback(_SHORT_TEXT, state)
        assert result is not None
        entry = _single_entry(state)
        assert entry["confidence"] == 0.8
        assert (
            entry["problematic_quote"] == "Tous les experts s'accordent sur ce point."
        )

    async def test_unmeasured_confidence_stays_absent_not_zero(self):
        """#1019 guard (green before AND after the fix, pins the tri-state):
        a detection without a measured confidence stores NO confidence key —
        unmeasured is not 0.0."""
        state = UnifiedAnalysisState(initial_text="x")
        detection = {
            "fallacy_type": "faux_dilemme",
            "justification": "Deux options présentées comme seules.",
        }
        with _harness(detection), _no_target():
            result = await _run_parent_harness_fallback(_SHORT_TEXT, state)
        assert result is not None
        entry = _single_entry(state)
        assert "confidence" not in entry

    async def test_non_numeric_confidence_is_not_stored(self):
        """Mirror-rule pin: the extraction is the pipeline writer's
        (``float(raw) if isinstance(raw, (int, float)) else None``) — a
        non-numeric confidence is not a measurement and stores nothing."""
        state = UnifiedAnalysisState(initial_text="x")
        detection = {
            "fallacy_type": "pente_glissante",
            "justification": "L'enchaînement causal n'est pas étayé.",
            "confidence": "élevée",
        }
        with _harness(detection), _no_target():
            result = await _run_parent_harness_fallback(_SHORT_TEXT, state)
        assert result is not None
        entry = _single_entry(state)
        assert "confidence" not in entry


class TestFallbackJustification:
    async def test_fallback_stops_carrying_confidence_as_prose(self):
        """Born red on main: a detection with a confidence and neither
        justification nor explanation produced
        ``Detected by parent harness (confidence: 0.8)`` — confidence is a
        field (#2972), not prose."""
        state = UnifiedAnalysisState(initial_text="x")
        detection = {
            "fallacy_type": "homme_de_paille",
            "confidence": 0.8,
        }
        with _harness(detection), _no_target():
            result = await _run_parent_harness_fallback(_SHORT_TEXT, state)
        assert result is not None
        entry = _single_entry(state)
        assert entry["justification"] == "Detected by parent harness"
        # and the confidence it used to leak as prose is now the field
        assert entry["confidence"] == 0.8


class TestRegistrationFailure:
    async def test_failure_counted_and_reported_not_swallowed(self):
        """Born red on main: ``except Exception: pass`` made a state rejecting
        the registration vanish — neither the summary nor the return dict
        carried it (#2978's failure class). Degrade, but count and name."""
        state = MagicMock(spec=["add_fallacy"])
        state.add_fallacy.side_effect = RuntimeError("state rejected the entry")
        detection = {
            "fallacy_type": "appel_a_autorite",
            "justification": "Aucune source vérifiée n'étaye l'affirmation.",
        }
        with _harness(detection), _no_target():
            result = await _run_parent_harness_fallback(_SHORT_TEXT, state)
        assert result is not None
        assert result["fallacies_registered"] == 0
        assert result["fallacies_failed"] == 1

    async def test_summary_line_reports_failures_next_to_registered(self, caplog):
        """The log summary line reports the failure count next to
        ``registered`` and ``skipped`` — an operator reading it sees the
        loss, not silence."""
        state = MagicMock(spec=["add_fallacy"])
        state.add_fallacy.side_effect = RuntimeError("state rejected the entry")
        detection = {
            "fallacy_type": "appel_a_autorite",
            "justification": "Aucune source vérifiée n'étaye l'affirmation.",
        }
        with _harness(detection), _no_target():
            # INFO captures both the summary line and the WARNING failure
            with caplog.at_level(logging.INFO):
                result = await _run_parent_harness_fallback(_SHORT_TEXT, state)
        assert result is not None
        assert result["fallacies_failed"] == 1
        summary = next(r for r in caplog.records if "fallacies found" in r.getMessage())
        assert "1 failed" in summary.getMessage()
        failure = next(
            r for r in caplog.records if "registration failed" in r.getMessage()
        )
        assert "appel_a_autorite" in failure.getMessage()
        assert "state rejected the entry" in failure.getMessage()


class TestNeighborhood:
    async def test_registered_detection_still_lands_on_real_state(self):
        """The fix must not disturb the count contract the Track KK / #648
        tests pin: registered detections still land, unusable types still
        skip."""
        state = UnifiedAnalysisState(initial_text="x")
        state.add_argument("Le premier argument synthétique.")
        detections = [
            {
                "fallacy_type": "appel_a_autorite",
                "justification": "Aucune source vérifiée n'étaye l'affirmation.",
                "confidence": 0.8,
                "problematic_quote": "Tous les experts s'accordent sur ce point.",
            },
            {"fallacy_type": "", "justification": "type inutilisable"},
        ]
        with patch(
            "argumentation_analysis.orchestration.invoke_callables."
            "_invoke_hierarchical_fallacy_per_argument",
            new_callable=AsyncMock,
            return_value={
                "fallacies": detections,
                "exploration_method": "per_argument_parallel",
            },
        ), _no_target():
            result = await _run_parent_harness_fallback(_SHORT_TEXT, state)
        assert result is not None
        assert result["fallacies_registered"] == 1
        assert result["fallacies_skipped_unusable"] == 1
        assert result["fallacies_failed"] == 0
        entry = _single_entry(state)
        assert entry["confidence"] == 0.8
