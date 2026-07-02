"""Tests for the CONV-C deliberation trace (#1334, Epic #1331).

Covers the ``record_designation`` plumbing on ``UnifiedAnalysisState`` +
``StateManagerPlugin``: motivated PM designations are recorded in a
``deliberation_trace`` of ``DesignationRecord`` (the shared material of the
CONV-A/C metrics, the #708 anti-runaway audit, and CONV-D Act II).

Design doc: docs/architecture/CONV_C_PM_ECLAIRE.md (PR #1340).
"""

import json

import pytest

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.core.state_manager_plugin import StateManagerPlugin


# ---------------------------------------------------------------------------
# UnifiedAnalysisState.record_designation
# ---------------------------------------------------------------------------


def test_record_designation_appends_motivated_record():
    """A designation is recorded with its motivation + trigger + fingerprint."""
    state = UnifiedAnalysisState("Some text to analyse.")
    turn = state.record_designation(
        "FormalAgent",
        "InformalAgent a trouve une contradiction sur arg_3",
        "deepening",
    )
    assert turn == 1
    assert len(state.deliberation_trace) == 1
    record = state.deliberation_trace[0]
    assert record["designated_agent"] == "FormalAgent"
    assert "contradiction" in record["motivation"]
    assert record["trigger"] == "deepening"
    # fingerprint_before captured at the moment of the designation
    assert record["state_fingerprint_before"] is not None
    assert record["state_fingerprint_before"]["argument_count"] == 0
    # after/delta left for _run_phase backfill until the agent returns
    assert record["state_fingerprint_after"] is None
    assert record["delta_summary"] is None


def test_record_designation_auto_increments_turn():
    """Turn auto-derives (len(trace)+1) so the PM does not track it."""
    state = UnifiedAnalysisState("Some text to analyse.")
    t1 = state.record_designation("ExtractAgent", "etat vide", "initial")
    t2 = state.record_designation("InformalAgent", "extraire les sophismes", "deepening")
    t3 = state.record_designation("QualityAgent", "evaluer la qualite", "synergy")
    assert (t1, t2, t3) == (1, 2, 3)
    assert len(state.deliberation_trace) == 3


def test_record_designation_explicit_turn_respected():
    """An explicit turn index is honored (pipeline-global accounting)."""
    state = UnifiedAnalysisState("Some text to analyse.")
    turn = state.record_designation("ExtractAgent", "x", "initial", turn=7)
    assert turn == 7
    assert state.deliberation_trace[0]["turn"] == 7


def test_snapshot_exposes_deliberation_turn_count():
    """The summarized snapshot surfaces the trace length (lightweight)."""
    state = UnifiedAnalysisState("Some text to analyse.")
    snap = state.get_state_snapshot(summarize=True)
    assert snap["deliberation_turn_count"] == 0
    state.record_designation("ExtractAgent", "x", "initial")
    state.record_designation("InformalAgent", "y", "deepening")
    snap = state.get_state_snapshot(summarize=True)
    assert snap["deliberation_turn_count"] == 2


def test_designation_fingerprint_reflects_state_growth():
    """The fingerprint captures the state dimensions the PM reasons about."""
    state = UnifiedAnalysisState("Some text to analyse.")
    state.add_identified_arguments(["premisses: P conclusion: Q"])
    state.record_designation("FormalAgent", "argument extrait, formaliser", "deepening")
    fp = state.deliberation_trace[0]["state_fingerprint_before"]
    assert fp is not None
    assert fp["argument_count"] == 1


def test_full_snapshot_serializes_deliberation_trace():
    """The non-summarized snapshot carries the full trace (for CONV-D / audit)."""
    state = UnifiedAnalysisState("Some text to analyse.")
    state.record_designation("ExtractAgent", "raison initiale", "initial")
    # to_json serializes __dict__ -> deliberation_trace included
    payload = json.loads(state.to_json(indent=None))
    assert "deliberation_trace" in payload
    trace = payload["deliberation_trace"]
    assert len(trace) == 1
    assert trace[0]["designated_agent"] == "ExtractAgent"


# ---------------------------------------------------------------------------
# StateManagerPlugin.record_designation (kernel function companion)
# ---------------------------------------------------------------------------


def test_plugin_record_designation_delegates_to_state():
    """The kernel function delegates to state.record_designation."""
    state = UnifiedAnalysisState("Some text to analyse.")
    plugin = StateManagerPlugin(state)
    result = plugin.record_designation(
        "InformalAgent", "arguments extraits, detecter sophismes", "deepening"
    )
    assert result.startswith("OK.")
    assert len(state.deliberation_trace) == 1
    assert state.deliberation_trace[0]["designated_agent"] == "InformalAgent"


def test_plugin_record_designation_fails_loud_on_missing_method():
    """A state without record_designation (base RhetoricalAnalysisState) fails loud."""
    from argumentation_analysis.core.shared_state import RhetoricalAnalysisState

    base_state = RhetoricalAnalysisState("Some text to analyse.")
    plugin = StateManagerPlugin(base_state)  # type: ignore[arg-type]
    result = plugin.record_designation("ExtractAgent", "x", "initial")
    assert result.startswith("FUNC_ERROR")
    assert "record_designation" in result
