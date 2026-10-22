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


def _quality(overall: float, n: int = 9) -> dict:
    """#1942 honest entry shape: per-virtue [0, 1] notes summing to ``overall``
    — readers normalize by ``len(scores)``."""
    return {"overall": overall, "scores": {f"v{i}": overall / n for i in range(n)}}


# 0.6 of the applicable maximum — a silent second argument that spans the
# weak bar, so the #1942 non-vacuity gate lets "qualite faible" mean
# something on these fixtures.
_SPAN = _quality(5.4)


_DUNG_ATTACKER = "arg_0"  # synthetic survivor, outside identified_arguments


def _dung_frame_rejecting(node: str, semantics: str = "grounded") -> dict:
    """A native frame in which ``node`` is genuinely OUT (#3153).

    Under grounded semantics an argument outside the extension is **out**
    (attacked by an accepted one) or **undecided** (a stand-off) — never
    automatically rejected. These fixtures used to list one node with an
    empty extension and NO attack graph, a frame no grounded solve can
    produce (a lone unattacked node is always accepted); the explicit
    attacker keeps the reading honest.
    """
    return {
        "name": f"verification_{semantics}",
        "arguments": [_DUNG_ATTACKER, node],
        "attacks": [[_DUNG_ATTACKER, node]],
        "extensions": {"all_members": [_DUNG_ATTACKER]},
        "semantics": semantics,
    }


def _make_state(
    identified_arguments=None,
    identified_fallacies=None,
    argument_quality_scores=None,
    counter_arguments=None,
    jtms_beliefs=None,
    dung_frameworks=None,
    propositional_analysis_results=None,
    fol_analysis_results=None,
    counter_sample=None,
):
    """Build a fake state namespace for convergence/formula testing.

    ``counter_sample`` — #3145: the counter phase's recorded sample. The
    counter signal counts as an independent method only when the sample shows
    the axis discriminates (some sampled unit got no counter); omitted, the
    counter is cited but never counted.
    """
    coverage = {}
    if counter_sample is not None:
        coverage["counter"] = {
            "k": len(counter_sample),
            "N": len(counter_sample),
            "bands_covered": 3,
            "bands_total": 3,
            "unit_ids": list(counter_sample),
        }
    return SimpleNamespace(
        identified_arguments=identified_arguments or {},
        identified_fallacies=identified_fallacies or {},
        argument_quality_scores=argument_quality_scores or {},
        counter_arguments=counter_arguments or [],
        jtms_beliefs=jtms_beliefs or {},
        dung_frameworks=dung_frameworks or {},
        propositional_analysis_results=propositional_analysis_results or [],
        fol_analysis_results=fol_analysis_results or [],
        analysis_coverage=coverage,
    )


class TestSignalIntegrity:
    """Per-signal fire counts and all-signals-alive detection."""

    def test_all_five_signals_fire(self):
        from argumentation_analysis.plugins.narrative_synthesis_plugin import (
            compute_argument_convergence,
        )

        # #3145: all five signals still FIRE (present in ``signals``), but
        # only the independent classes count — the counter needs a recorded
        # sample that discriminates (arg_2, sampled, got no counter), and the
        # JTMS retraction is derived from the fallacy, cited not counted.
        state = _make_state(
            identified_arguments={"arg_1": "desc1", "arg_2": "solid"},
            identified_fallacies={
                "f1": {"target_argument_id": "arg_1", "type": "ad hominem"},
            },
            argument_quality_scores={"arg_1": _quality(3.0), "arg_2": _SPAN},
            counter_arguments=[{"target_arg_id": "arg_1", "content": "counter"}],
            jtms_beliefs={
                "b1": {"name": "arg_1:some text", "valid": False},
            },
            dung_frameworks={"fw1": _dung_frame_rejecting("arg_1")},
            counter_sample=["arg_1", "arg_2"],
        )
        result = compute_argument_convergence(state)
        assert "arg_1" in result
        assert result["arg_1"]["score"] == 4
        methods = {s[0] for s in result["arg_1"]["signals"]}
        assert methods == {
            "sophisme",
            "qualite faible",
            "contre-argument",
            "JTMS retracte",
            "rejet Dung",
        }
        independent = {s[0] for s in result["arg_1"]["independent_signals"]}
        assert independent == {
            "sophisme",
            "qualite faible",
            "contre-argument",
            "rejet Dung",
        }
        cited = {s[0] for s in result["arg_1"]["cited_signals"]}
        assert cited == {"JTMS retracte"}

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
            identified_arguments={"arg_1": "desc", "arg_2": "solid"},
            argument_quality_scores={"arg_1": _quality(2.5), "arg_2": _SPAN},
        )
        result = compute_argument_convergence(state)
        assert result["arg_1"]["score"] == 1
        assert result["arg_1"]["signals"][0][0] == "qualite faible"

    def test_signal_3_counter_argument(self):
        from argumentation_analysis.plugins.narrative_synthesis_plugin import (
            compute_argument_convergence,
        )

        # #3145: the counter fires as an independent method when the recorded
        # sample shows the axis discriminates (arg_2, sampled, got no
        # counter); without that sample it is cited, not counted.
        state = _make_state(
            identified_arguments={"arg_1": "desc", "arg_2": "solid"},
            counter_arguments=[{"target_arg_id": "arg_1", "content": "counter"}],
            counter_sample=["arg_1", "arg_2"],
        )
        result = compute_argument_convergence(state)
        assert result["arg_1"]["score"] == 1
        assert result["arg_1"]["signals"][0][0] == "contre-argument"

    def test_signal_3_counter_cited_when_sample_absent(self):
        from argumentation_analysis.plugins.narrative_synthesis_plugin import (
            compute_argument_convergence,
        )

        state = _make_state(
            identified_arguments={"arg_1": "desc"},
            counter_arguments=[{"target_arg_id": "arg_1", "content": "counter"}],
        )
        result = compute_argument_convergence(state)
        # No recorded sample → the axis is unmeasured, the counter is content.
        assert result["arg_1"]["score"] == 0
        assert result["arg_1"]["signals"][0][0] == "contre-argument"
        assert result["arg_1"]["cited_signals"][0][0] == "contre-argument"

    def test_signal_4_jtms_retracted(self):
        from argumentation_analysis.plugins.narrative_synthesis_plugin import (
            compute_argument_convergence,
        )

        # #3145: the retraction still fires (visible content), but DERIVED
        # signals never count — the entry exists with score 0, the signal in
        # ``cited_signals``.
        state = _make_state(
            identified_arguments={"arg_1": "desc"},
            jtms_beliefs={
                "b1": {"name": "arg_1:excerpt text", "valid": False},
            },
        )
        result = compute_argument_convergence(state)
        assert result["arg_1"]["score"] == 0
        assert result["arg_1"]["signals"][0][0] == "JTMS retracte"
        assert result["arg_1"]["cited_signals"][0][0] == "JTMS retracte"

    def test_signal_5_dung_rejected(self):
        from argumentation_analysis.plugins.narrative_synthesis_plugin import (
            compute_argument_convergence,
        )

        state = _make_state(
            identified_arguments={"arg_1": "desc"},
            dung_frameworks={"fw1": _dung_frame_rejecting("arg_1")},
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
                "fw1": _dung_frame_rejecting("The policy causes harm to many people")
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

        # #3145: depth 3 needs three INDEPENDENT classes — the counter counts
        # because the recorded sample discriminates (arg_2 got no counter).
        state = _make_state(
            identified_arguments={"arg_1": "desc", "arg_2": "solid"},
            identified_fallacies={
                "f1": {"target_argument_id": "arg_1", "type": "ad hominem"}
            },
            argument_quality_scores={"arg_1": _quality(2.0), "arg_2": _SPAN},
            counter_arguments=[{"target_arg_id": "arg_1", "content": "counter"}],
            counter_sample=["arg_1", "arg_2"],
        )
        result = compute_argument_convergence(state)
        assert result["arg_1"]["score"] >= 3

    def test_depth_4_needs_four_independent_not_jtms(self):
        from argumentation_analysis.plugins.narrative_synthesis_plugin import (
            compute_argument_convergence,
        )

        # #3145: depth 4 is reachable — by four INDEPENDENT classes (Dung
        # joins sophisme/qualite/contre-argument), never by adding the JTMS
        # echo of the fallacy on top of three: it stays cited content.
        state = _make_state(
            identified_arguments={"arg_1": "desc", "arg_2": "solid"},
            identified_fallacies={
                "f1": {"target_argument_id": "arg_1", "type": "ad hominem"}
            },
            argument_quality_scores={"arg_1": _quality(2.0), "arg_2": _SPAN},
            counter_arguments=[{"target_arg_id": "arg_1", "content": "counter"}],
            counter_sample=["arg_1", "arg_2"],
            # #3153: an explicit attack graph — a frame with no recorded
            # graph is non-concluable (no Dung signal), and this test needs
            # Dung as the 4th INDEPENDENT class.
            dung_frameworks={"fw1": _dung_frame_rejecting("arg_1")},
        )
        result = compute_argument_convergence(state)
        assert result["arg_1"]["score"] == 4

        # Adding the derived JTMS echo on top changes nothing in the count.
        state.jtms_beliefs = {"b1": {"name": "arg_1:text", "valid": False}}
        result = compute_argument_convergence(state)
        assert result["arg_1"]["score"] == 4
        cited = {s[0] for s in result["arg_1"]["cited_signals"]}
        assert cited == {"JTMS retracte"}

    def test_depth_5_all_signals(self):
        from argumentation_analysis.plugins.narrative_synthesis_plugin import (
            compute_argument_convergence,
        )

        # #3145: five signals firing on one argument count 4 independent
        # methods — the JTMS retraction is the fallacy's echo, cited.
        state = _make_state(
            identified_arguments={"arg_1": "desc", "arg_2": "solid"},
            identified_fallacies={
                "f1": {"target_argument_id": "arg_1", "type": "ad hominem"}
            },
            argument_quality_scores={"arg_1": _quality(2.0), "arg_2": _SPAN},
            counter_arguments=[{"target_arg_id": "arg_1", "content": "counter"}],
            counter_sample=["arg_1", "arg_2"],
            jtms_beliefs={"b1": {"name": "arg_1:text", "valid": False}},
            dung_frameworks={"fw1": _dung_frame_rejecting("arg_1")},
        )
        result = compute_argument_convergence(state)
        assert result["arg_1"]["score"] == 4
        assert len(result["arg_1"]["signals"]) == 5
