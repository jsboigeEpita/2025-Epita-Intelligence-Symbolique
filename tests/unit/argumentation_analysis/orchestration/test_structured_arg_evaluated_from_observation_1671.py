"""#1671 — ``evaluated`` must be computed from an observation, not from an input.

The ``has_genuine_input`` branch of ``_record_structured_arg_status`` used to
write *"framework evaluated on real structured artifacts"* while observing only
that an INPUT key was present in the context. Nothing in it looked at what the
handler returned.

That is not a latent defect. Measured on the real state artefacts, four of the
five axes reach that branch with ``extensions == [[]]`` — the handler did not
raise, it *succeeded on an empty theory* — and were filed
``evaluated / degraded=False``. Such an axis is invisible in both directions: the
absence ledger skips it (not degraded) and the presence channel finds nothing to
project.

The condition these tests establish and that no pre-existing fixture posed: a
genuine input present **and** an output carrying nothing. That pair is why the
branch was never armed.

No JVM, no LLM. Synthetic atoms only (privacy HARD — no corpus tokens).
"""

from __future__ import annotations

from typing import Any, Dict

import pytest

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.orchestration.state_writers import (
    _record_structured_arg_status,
)
from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    _collect_absent_dimensions,
)

# One genuine-structured-input context per capability, keyed exactly as
# ``_STRUCTURED_ARG_INPUT_KEYS`` expects. Every one of these makes
# ``has_genuine_input`` true, which is the branch under test.
_GENUINE_CTX: Dict[str, Dict[str, Any]] = {
    "aspic_plus_reasoning": {"defeasible_rules": [{"head": "h", "body": ["b"]}]},
    "aba_reasoning": {"contraries": {"a": "not_a"}},
    "setaf_reasoning": {"set_attacks": [{"attackers": ["a", "b"], "target": "c"}]},
    "weighted_argumentation": {"weighted_attacks": [("a", "b", 0.9)]},
    "bipolar_argumentation": {"supports": [["a", "b"]]},
}

_CAPABILITIES = sorted(_GENUINE_CTX)


def _new_state() -> UnifiedAnalysisState:
    return UnifiedAnalysisState("synthetic structured-arg probe")


class TestEmptyResultIsNotAnEvaluation:
    """The pair no fixture posed: genuine input present, output carrying nothing."""

    @pytest.mark.parametrize("capability", _CAPABILITIES)
    def test_single_empty_extension_is_not_evaluated(self, capability):
        # The exact shape measured on real artefacts: one result set, empty.
        state = _new_state()
        _record_structured_arg_status(
            state, capability, {"extensions": [[]]}, _GENUINE_CTX[capability]
        )
        entry = state.structured_arg_status[capability]
        assert entry["status"] == "evaluated_empty"
        assert entry["degraded"] is True

    @pytest.mark.parametrize("capability", _CAPABILITIES)
    def test_no_result_set_at_all_is_not_evaluated(self, capability):
        state = _new_state()
        _record_structured_arg_status(
            state, capability, {"extensions": []}, _GENUINE_CTX[capability]
        )
        assert state.structured_arg_status[capability]["status"] == "evaluated_empty"

    @pytest.mark.parametrize("capability", _CAPABILITIES)
    def test_handler_reporting_degraded_is_not_evaluated(self, capability):
        # The second route to the same false label: the honest-degraded migration
        # turns handler ``raise`` into a degraded return. Input is still genuine.
        state = _new_state()
        _record_structured_arg_status(
            state,
            capability,
            {"degraded": True, "extensions": [["a", "b"]]},
            _GENUINE_CTX[capability],
        )
        entry = state.structured_arg_status[capability]
        assert entry["status"] == "evaluated_empty"
        assert entry["degraded"] is True

    @pytest.mark.parametrize("capability", _CAPABILITIES)
    def test_reason_asserts_only_what_was_observed(self, capability):
        state = _new_state()
        _record_structured_arg_status(
            state, capability, {"extensions": [[]]}, _GENUINE_CTX[capability]
        )
        reason = state.structured_arg_status[capability]["reason"]
        # The pre-#1671 sentence claimed an evaluation nothing had observed.
        assert "evaluated on real structured artifacts" not in reason
        assert "no non-empty result set" in reason


class TestSubstantiveResultStaysEvaluated:
    """Anti-pendulum: repairing the false positive must not paint everything red."""

    @pytest.mark.parametrize("capability", _CAPABILITIES)
    def test_non_empty_extension_is_evaluated(self, capability):
        state = _new_state()
        _record_structured_arg_status(
            state,
            capability,
            {"extensions": [["a", "b"], ["c"]]},
            _GENUINE_CTX[capability],
        )
        entry = state.structured_arg_status[capability]
        assert entry["status"] == "evaluated"
        assert entry["degraded"] is False

    def test_supports_carry_the_result_when_extensions_absent(self):
        # Bipolar reports under "supports", not "extensions" — the only axis that
        # comes back substantive on every real artefact measured.
        state = _new_state()
        _record_structured_arg_status(
            state,
            "bipolar_argumentation",
            {"supports": [["a", "b"], ["b", "c"]]},
            _GENUINE_CTX["bipolar_argumentation"],
        )
        entry = state.structured_arg_status["bipolar_argumentation"]
        assert entry["status"] == "evaluated"
        assert entry["degraded"] is False

    @pytest.mark.parametrize("capability", _CAPABILITIES)
    def test_absent_input_path_is_untouched(self, capability):
        # #1608 owns the other branch; #1671 must not reach into it.
        state = _new_state()
        _record_structured_arg_status(state, capability, {"extensions": [[]]}, {})
        assert state.structured_arg_status[capability]["status"] != "evaluated_empty"


class TestExtensionCountKeepsItsMeaning:
    """``extension_count`` describes; it does not decide."""

    def test_one_empty_extension_still_counts_as_one(self):
        state = _new_state()
        _record_structured_arg_status(
            state,
            "aspic_plus_reasoning",
            {"extensions": [[]]},
            _GENUINE_CTX["aspic_plus_reasoning"],
        )
        entry = state.structured_arg_status["aspic_plus_reasoning"]
        # len([[]]) == 1 is the right answer to "how many result sets came back".
        assert entry["extension_count"] == 1
        # ...and it is precisely why the count cannot carry the verdict.
        assert entry["status"] == "evaluated_empty"

    @pytest.mark.parametrize(
        "output,expected",
        [
            ({"extensions": [[]]}, 0),
            ({"extensions": []}, 0),
            ({"extensions": [["a"], []]}, 1),
            ({"extensions": [["a"], ["b", "c"]]}, 2),
            ({"supports": [["a", "b"]]}, 1),
            ({"supports": []}, 0),
            ({}, 0),
            (None, 0),
            ({"extensions": "not-a-list"}, 0),
        ],
    )
    def test_substantive_member_count(self, output, expected):
        # Imported here, not at module scope: a module-level import of a helper
        # that #1671 introduces would turn every test in this file into a
        # collection error on the pre-fix code, and a collection error proves
        # nothing about the assertions. The rest of the file must be able to run
        # — and fail on its assertions — against the code it accuses.
        from argumentation_analysis.orchestration.state_writers import (
            _structured_arg_substantive_members,
        )

        assert _structured_arg_substantive_members(output) == expected


class TestTheAxisBecomesVisibleDownstream:
    """The consequence, not the label: pin the relation to the absence ledger."""

    def test_vacuous_axis_reaches_the_absence_collector(self):
        state = _new_state()
        _record_structured_arg_status(
            state,
            "aspic_plus_reasoning",
            {"extensions": [[]]},
            _GENUINE_CTX["aspic_plus_reasoning"],
        )
        absent = _collect_absent_dimensions(state)
        assert [d.capability for d in absent] == ["aspic_plus_reasoning"]
        assert absent[0].status == "evaluated_empty"

    def test_substantive_axis_stays_out_of_the_absence_collector(self):
        state = _new_state()
        _record_structured_arg_status(
            state,
            "aspic_plus_reasoning",
            {"extensions": [["a"], ["b"]]},
            _GENUINE_CTX["aspic_plus_reasoning"],
        )
        assert _collect_absent_dimensions(state) == []

    def test_vacuous_axis_is_not_counted_among_capabilities_used(self):
        from argumentation_analysis.orchestration.unified_pipeline import (
            _collect_degraded_capabilities,
        )

        state = _new_state()
        _record_structured_arg_status(
            state,
            "aspic_plus_reasoning",
            {"extensions": [[]]},
            _GENUINE_CTX["aspic_plus_reasoning"],
        )
        degraded, used = _collect_degraded_capabilities(
            {}, state, ["aspic_plus_reasoning", "informal_analysis"]
        )
        assert "aspic_plus_reasoning" in degraded
        assert "aspic_plus_reasoning" not in used
        assert "informal_analysis" in used
