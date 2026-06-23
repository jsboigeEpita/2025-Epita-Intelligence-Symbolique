"""FP-17 (#1236) — honest-absent surfacing for structured-arg capabilities.

ASPIC+/ABA/SETAF/weighted/bipolar have no text→structured translator wired
(translation-gap FP-4 #1201). On real corpora they run on auto-shaped synthetic
input, so an empty extension list means "never genuinely fed structured input",
NOT "evaluated, found nothing". These tests pin the contract that the state
writers + restitution appendix surface that distinction explicitly — never a
silent ``[]`` (#1019).

No JVM, no LLM. Synthetic atoms only (privacy HARD — no corpus tokens).
"""

from __future__ import annotations

from typing import Any, Dict

import pytest

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.orchestration.state_writers import (
    _record_structured_arg_status,
    _write_aba_to_state,
    _write_aspic_to_state,
    _write_bipolar_to_state,
    _write_setaf_to_state,
    _write_weighted_to_state,
)
from argumentation_analysis.reporting.restitution.appendix import (
    _provenance_counts,
    render_appendix,
)
from argumentation_analysis.reporting.restitution.state_adapter import (
    state_to_appendix_mapping,
)

# (capability, writer) pairs — the five formalisms in scope for #1236.
_WRITERS = [
    ("aspic_plus_reasoning", _write_aspic_to_state),
    ("aba_reasoning", _write_aba_to_state),
    ("setaf_reasoning", _write_setaf_to_state),
    ("weighted_argumentation", _write_weighted_to_state),
    ("bipolar_argumentation", _write_bipolar_to_state),
]

# A genuine-structured-input context per capability (a future translator would
# populate these keys). Presence of any flips the status to "evaluated".
_GENUINE_CTX: Dict[str, Dict[str, Any]] = {
    "aspic_plus_reasoning": {"strict_rules": [{"head": "h", "body": ["b"]}]},
    "aba_reasoning": {"contraries": {"a": "not_a"}},
    "setaf_reasoning": {"set_attacks": [{"attackers": ["a", "b"], "target": "c"}]},
    "weighted_argumentation": {"weighted_attacks": [("a", "b", 0.9)]},
    "bipolar_argumentation": {"supports": [["a", "b"]]},
}


def _new_state() -> UnifiedAnalysisState:
    return UnifiedAnalysisState("synthetic structured-arg probe")


class TestHonestAbsentEmitted:
    """Each structured-arg writer records absent_no_translator with no translator."""

    @pytest.mark.parametrize("capability,writer", _WRITERS)
    def test_empty_output_records_absent_no_translator(self, capability, writer):
        state = _new_state()
        # output={} → the writer early-returns, but the status MUST already be
        # recorded (no silent []): a capability that ran and produced nothing is
        # labelled, not dropped.
        writer({}, state, {})
        assert capability in state.structured_arg_status
        entry = state.structured_arg_status[capability]
        assert entry["status"] == "absent_no_translator"
        assert entry["degraded"] is True
        assert isinstance(entry["reason"], str) and entry["reason"]

    @pytest.mark.parametrize("capability,writer", _WRITERS)
    def test_no_genuine_input_is_absent_even_with_a_result(self, capability, writer):
        # Even when auto-shaped input yields a non-empty result, the absence of
        # genuine structured input means the verdict is NOT a genuine analysis.
        state = _new_state()
        output = {
            "reasoner_type": "simple",
            "framework_type": "necessity",
            "semantics": "grounded",
            "arguments": ["a", "b"],
            "assumptions": ["a"],
            "supports": [],
            "extensions": [["a"]],
            "statistics": {},
        }
        writer(output, state, {})
        assert state.structured_arg_status[capability]["status"] == (
            "absent_no_translator"
        )


class TestGenuineInputFlipsToEvaluated:
    """Genuine structured input via context flips the status to evaluated."""

    @pytest.mark.parametrize("capability,writer", _WRITERS)
    def test_genuine_context_marks_evaluated(self, capability, writer):
        state = _new_state()
        ctx = _GENUINE_CTX[capability]
        output = {
            "reasoner_type": "simple",
            "framework_type": "necessity",
            "semantics": "grounded",
            "arguments": ["a", "b"],
            "assumptions": ["a"],
            "supports": ctx.get("supports", []),
            "extensions": [["a"]],
            "statistics": {},
        }
        writer(output, state, ctx)
        entry = state.structured_arg_status[capability]
        assert entry["status"] == "evaluated"
        assert entry["degraded"] is False


class TestRecordHelperDirectly:
    def test_extension_count_is_zero_safe(self):
        state = _new_state()
        _record_structured_arg_status(state, "aspic_plus_reasoning", None, {})
        assert (
            state.structured_arg_status["aspic_plus_reasoning"]["extension_count"] == 0
        )

    def test_supports_counted_when_extensions_absent(self):
        state = _new_state()
        _record_structured_arg_status(
            state,
            "bipolar_argumentation",
            {"supports": [["a", "b"], ["b", "c"]]},
            {"supports": [["a", "b"]]},
        )
        entry = state.structured_arg_status["bipolar_argumentation"]
        assert entry["status"] == "evaluated"
        assert entry["extension_count"] == 2

    def test_no_op_on_state_without_recorder(self):
        # Defensive: a plain object lacking the recorder must not raise.
        _record_structured_arg_status(object(), "aspic_plus_reasoning", {}, {})


class TestSnapshotSurfacesStatus:
    def test_full_snapshot_includes_status(self):
        state = _new_state()
        _write_bipolar_to_state({}, state, {})
        snap = state.get_state_snapshot(summarize=False)
        assert "structured_arg_status" in snap
        assert snap["structured_arg_status"]["bipolar_argumentation"]["status"] == (
            "absent_no_translator"
        )

    def test_summarized_snapshot_keeps_full_status_not_a_count(self):
        state = _new_state()
        _write_aspic_to_state({}, state, {})
        snap = state.get_state_snapshot(summarize=True)
        # The full map is kept even in the summary — a bare count would re-hide
        # the absent_no_translator distinction this field exists to expose.
        assert isinstance(snap["structured_arg_status"], dict)
        assert snap["structured_arg_status"]["aspic_plus_reasoning"]["status"] == (
            "absent_no_translator"
        )


class TestAppendixSurfacesHonestAbsent:
    def test_appendix_shows_absent_no_silent_empty(self):
        state = _new_state()
        for _cap, writer in _WRITERS:
            writer({}, state, {})
        mapping = state_to_appendix_mapping(state)
        assert "structured_arg_status" in mapping

        counts = _provenance_counts(mapping)
        assert "arg_structuree" in counts
        line = counts["arg_structuree"]
        # No silent [] — the reader sees "absent (no translator)" per capability.
        assert "absent" in line
        for cap, _writer in _WRITERS:
            assert cap in line

        rendered = render_appendix(mapping)
        assert "arg_structuree" in rendered
        assert "absent" in rendered

    def test_appendix_indisponible_when_no_structured_arg_run(self):
        state = _new_state()
        counts = _provenance_counts(state_to_appendix_mapping(state))
        # Nothing ran → honest "indisponible", still not a silent empty list.
        assert counts["arg_structuree"] == "indisponible"
