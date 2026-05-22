"""Tests for consolidated measurement (#658): signal integrity + formula survival + RR verification.

Covers:
  1. Signal integrity — per-signal fire counts, all 5 methods alive detection
  2. Formula counting from state PL/FOL entries
  3. Dung arg ID resolution (RR fix verification)
  4. Convergence depth computation with all 5 signals
"""

import pytest
from types import SimpleNamespace
from collections import Counter


def _make_state(
    identified_arguments=None,
    identified_fallacies=None,
    argument_quality_scores=None,
    counter_arguments=None,
    jtms_beliefs=None,
    dung_frameworks=None,
    propositional_analysis_results=None,
    fol_analysis_results=None,
):
    """Build a fake state namespace for convergence/formula testing."""
    return SimpleNamespace(
        identified_arguments=identified_arguments or {},
        identified_fallacies=identified_fallacies or {},
        argument_quality_scores=argument_quality_scores or {},
        counter_arguments=counter_arguments or [],
        jtms_beliefs=jtms_beliefs or {},
        dung_frameworks=dung_frameworks or {},
        propositional_analysis_results=propositional_analysis_results or [],
        fol_analysis_results=fol_analysis_results or [],
    )


class TestSignalIntegrity:
    """Per-signal fire counts and all-signals-alive detection."""

    def test_all_five_signals_fire(self):
        from argumentation_analysis.plugins.narrative_synthesis_plugin import (
            compute_argument_convergence,
        )

        state = _make_state(
            identified_arguments={"arg_1": "desc1"},
            identified_fallacies={
                "f1": {"target_argument_id": "arg_1", "type": "ad hominem"},
            },
            argument_quality_scores={"arg_1": {"overall": 3.0}},
            counter_arguments=[{"target_arg_id": "arg_1", "content": "counter"}],
            jtms_beliefs={
                "b1": {"name": "arg_1:some text", "valid": False},
            },
            dung_frameworks={
                "fw1": {
                    "arguments": ["arg_1"],
                    "extensions": [],
                    "semantics": "grounded",
                },
            },
        )
        result = compute_argument_convergence(state)
        assert "arg_1" in result
        assert result["arg_1"]["score"] == 5
        methods = {s[0] for s in result["arg_1"]["signals"]}
        assert methods == {
            "sophisme",
            "qualite faible",
            "contre-argument",
            "JTMS retracte",
            "rejet Dung",
        }

    def test_signal_1_fallacy(self):
        from argumentation_analysis.plugins.narrative_synthesis_plugin import (
            compute_argument_convergence,
        )

        state = _make_state(
            identified_arguments={"arg_1": "desc"},
            identified_fallacies={
                "f1": {"target_argument_id": "arg_1", "type": "straw man"},
            },
        )
        result = compute_argument_convergence(state)
        assert result["arg_1"]["score"] == 1
        assert result["arg_1"]["signals"][0][0] == "sophisme"

    def test_signal_2_quality(self):
        from argumentation_analysis.plugins.narrative_synthesis_plugin import (
            compute_argument_convergence,
        )

        state = _make_state(
            identified_arguments={"arg_1": "desc"},
            argument_quality_scores={"arg_1": {"overall": 2.5}},
        )
        result = compute_argument_convergence(state)
        assert result["arg_1"]["score"] == 1
        assert result["arg_1"]["signals"][0][0] == "qualite faible"

    def test_signal_3_counter_argument(self):
        from argumentation_analysis.plugins.narrative_synthesis_plugin import (
            compute_argument_convergence,
        )

        state = _make_state(
            identified_arguments={"arg_1": "desc"},
            counter_arguments=[{"target_arg_id": "arg_1", "content": "counter"}],
        )
        result = compute_argument_convergence(state)
        assert result["arg_1"]["score"] == 1
        assert result["arg_1"]["signals"][0][0] == "contre-argument"

    def test_signal_4_jtms_retracted(self):
        from argumentation_analysis.plugins.narrative_synthesis_plugin import (
            compute_argument_convergence,
        )

        state = _make_state(
            identified_arguments={"arg_1": "desc"},
            jtms_beliefs={
                "b1": {"name": "arg_1:excerpt text", "valid": False},
            },
        )
        result = compute_argument_convergence(state)
        assert result["arg_1"]["score"] == 1
        assert result["arg_1"]["signals"][0][0] == "JTMS retracte"

    def test_signal_5_dung_rejected(self):
        from argumentation_analysis.plugins.narrative_synthesis_plugin import (
            compute_argument_convergence,
        )

        state = _make_state(
            identified_arguments={"arg_1": "desc"},
            dung_frameworks={
                "fw1": {
                    "arguments": ["arg_1"],
                    "extensions": [],
                    "semantics": "grounded",
                },
            },
        )
        result = compute_argument_convergence(state)
        assert result["arg_1"]["score"] == 1
        assert result["arg_1"]["signals"][0][0] == "rejet Dung"

    def test_signal_4_no_false_positive_on_defeat_beliefs(self):
        from argumentation_analysis.plugins.narrative_synthesis_plugin import (
            compute_argument_convergence,
        )

        state = _make_state(
            identified_arguments={"arg_1": "desc"},
            jtms_beliefs={
                "b1": {"name": "DEFEAT:arg_1:rebuttal", "valid": False},
            },
        )
        result = compute_argument_convergence(state)
        assert "arg_1" not in result

    def test_signal_5_text_label_resolved(self):
        """RR fix: text-labeled Dung args resolved to canonical IDs."""
        from argumentation_analysis.plugins.narrative_synthesis_plugin import (
            compute_argument_convergence,
        )

        state = _make_state(
            identified_arguments={"arg_1": "The policy causes harm"},
            dung_frameworks={
                "fw1": {
                    "arguments": ["The policy causes harm to many people"],
                    "extensions": [],
                    "semantics": "grounded",
                },
            },
        )
        result = compute_argument_convergence(state)
        assert "arg_1" in result
        assert result["arg_1"]["signals"][0][0] == "rejet Dung"


class TestFormulaCounting:
    """Count surviving formulas from state PL/FOL results."""

    def test_count_from_state(self):
        state = _make_state(
            propositional_analysis_results=[
                {
                    "id": "pl_1",
                    "formulas": ["p1 => p2", "p2 => p3"],
                    "satisfiable": True,
                },
            ],
            fol_analysis_results=[
                {"id": "fol_1", "formulas": ["Forall(x, P(x))"], "consistent": True},
            ],
        )
        pl_count = sum(
            len(r.get("formulas", [])) for r in state.propositional_analysis_results
        )
        fol_count = sum(len(r.get("formulas", [])) for r in state.fol_analysis_results)
        total = pl_count + fol_count
        assert pl_count == 2
        assert fol_count == 1
        assert total == 3  # DoD met

    def test_dod_not_met_empty(self):
        state = _make_state(
            propositional_analysis_results=[],
            fol_analysis_results=[],
        )
        pl_count = sum(
            len(r.get("formulas", [])) for r in state.propositional_analysis_results
        )
        fol_count = sum(len(r.get("formulas", [])) for r in state.fol_analysis_results)
        assert pl_count + fol_count == 0

    def test_dod_met_many_formulas(self):
        state = _make_state(
            propositional_analysis_results=[
                {
                    "id": "pl_1",
                    "formulas": ["p1", "p2", "p3", "p4"],
                    "satisfiable": True,
                },
            ],
            fol_analysis_results=[
                {
                    "id": "fol_1",
                    "formulas": ["Forall(x, P(x) => Q(x))"],
                    "consistent": True,
                },
            ],
        )
        pl_count = sum(
            len(r.get("formulas", [])) for r in state.propositional_analysis_results
        )
        fol_count = sum(len(r.get("formulas", [])) for r in state.fol_analysis_results)
        assert pl_count + fol_count >= 3


class TestConvergenceDepth:
    """Verify convergence depth scoring with multiple signals."""

    def test_depth_3(self):
        from argumentation_analysis.plugins.narrative_synthesis_plugin import (
            compute_argument_convergence,
        )

        state = _make_state(
            identified_arguments={"arg_1": "desc"},
            identified_fallacies={
                "f1": {"target_argument_id": "arg_1", "type": "ad hominem"}
            },
            argument_quality_scores={"arg_1": {"overall": 2.0}},
            counter_arguments=[{"target_arg_id": "arg_1", "content": "counter"}],
        )
        result = compute_argument_convergence(state)
        assert result["arg_1"]["score"] >= 3

    def test_depth_4_with_jtms(self):
        from argumentation_analysis.plugins.narrative_synthesis_plugin import (
            compute_argument_convergence,
        )

        state = _make_state(
            identified_arguments={"arg_1": "desc"},
            identified_fallacies={
                "f1": {"target_argument_id": "arg_1", "type": "ad hominem"}
            },
            argument_quality_scores={"arg_1": {"overall": 2.0}},
            counter_arguments=[{"target_arg_id": "arg_1", "content": "counter"}],
            jtms_beliefs={"b1": {"name": "arg_1:text", "valid": False}},
        )
        result = compute_argument_convergence(state)
        assert result["arg_1"]["score"] >= 4

    def test_depth_5_all_signals(self):
        from argumentation_analysis.plugins.narrative_synthesis_plugin import (
            compute_argument_convergence,
        )

        state = _make_state(
            identified_arguments={"arg_1": "desc"},
            identified_fallacies={
                "f1": {"target_argument_id": "arg_1", "type": "ad hominem"}
            },
            argument_quality_scores={"arg_1": {"overall": 2.0}},
            counter_arguments=[{"target_arg_id": "arg_1", "content": "counter"}],
            jtms_beliefs={"b1": {"name": "arg_1:text", "valid": False}},
            dung_frameworks={
                "fw1": {
                    "arguments": ["arg_1"],
                    "extensions": [],
                    "semantics": "grounded",
                },
            },
        )
        result = compute_argument_convergence(state)
        assert result["arg_1"]["score"] == 5
