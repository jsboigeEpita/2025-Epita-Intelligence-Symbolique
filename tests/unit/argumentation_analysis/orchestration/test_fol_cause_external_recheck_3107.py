"""#3107 x #3106 — the stated cause is the one of the verdict that carries.

A re-check by the external solver rides the entry it re-ran (#3106): when it
diverges, its verdict carries and the displaced verdict — with its source —
is kept in ``superseded_verdict``. The cause introduced for #3107 was
written by the FOL agent's writer, so it travels with THAT verdict: promoting
the external verdict must move the cause into the superseded record, and the
carrying entry must state none. A prover that decided "inconsistent" without
a cause classification states no cause; inheriting the displaced one would
make the render attribute to the carrier a cause it never gave.

Witnessed here (real state, production writers and readers, opaque
predicates, zero spend):

* a displacing re-check moves the cause into ``superseded_verdict`` and the
  entry stops stating it;
* the renders (appendix ``causes``, Acte III weak points) follow the carrier:
  no cause is printed for a verdict that no longer speaks;
* an agreeing re-check leaves the cause untouched;
* an undecided entry promoted by the prover states no invented cause;
* ``formula_sources`` survives (it is a property of the theory, not of a
  verdict).
"""

from __future__ import annotations

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.orchestration.fol_cause import classify_inconsistency
from argumentation_analysis.orchestration.state_writers import (
    _write_external_fol_solver_to_state,
    _write_fol_to_state,
)
from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    _fol_stated_causes,
)
from argumentation_analysis.reporting.restitution.appendix import _fol_axis_status

FORMULAS = ["P(a)", "!P(a)"]


def _inconsistent_entry():
    """Real state + the production writer: one theory, two voices, a cause."""
    state = UnifiedAnalysisState("texte")
    a = state.add_argument("P(a)", producer="llm_extract")
    b = state.add_argument("not P(a)", producer="llm_extract")
    state.argument_provenance[a]["speaker"] = "Speaker_A"
    state.argument_provenance[b]["speaker"] = "Speaker_B"
    cause = classify_inconsistency(
        FORMULAS,
        [[a], [b]],
        {a: "Speaker_A", b: "Speaker_B"},
    )
    _write_fol_to_state(
        {
            "formulas": list(FORMULAS),
            "consistent": False,
            "inferences": [],
            "confidence": 0.4,
            "message": "FOL consistency check (EProver)",
            "fol_status": "decided",
            "consistency_cause": cause,
            "formula_sources": [[a], [b]],
        },
        state,
        {},
    )
    entry = state.fol_analysis_results[0]
    assert entry["consistency_cause"]["cause"] == "between_voices"
    return state, entry


def _recheck(state, consistent, solver="eprover"):
    _write_external_fol_solver_to_state(
        {
            "formulas": list(FORMULAS),
            "consistent": consistent,
            "solver": solver,
            "message": "external solver result",
        },
        state,
        {},
    )
    return state.fol_analysis_results[0]


class TestCauseFollowsTheCarryingVerdict:
    def test_a_displacing_recheck_moves_the_cause_into_the_superseded_record(self):
        state, entry = _inconsistent_entry()
        cause = entry["consistency_cause"]

        entry = _recheck(state, consistent=True)

        assert entry["consistent"] is True
        assert entry["consistent_source"] == "external:eprover"
        assert "consistency_cause" not in entry, (
            "the carrying external verdict never classified a cause; the "
            "displaced one must not survive as if it were its own"
        )
        superseded = entry["superseded_verdict"]
        assert superseded["consistent"] is False
        assert superseded["source"] == "fol_agent"
        assert superseded["cause"] == cause
        assert entry["external_checks"][-1]["agrees"] is False
        # A theory property, not a verdict property: still true after promotion.
        assert entry["formula_sources"] == [["arg_1"], ["arg_2"]]

    def test_the_renders_state_no_cause_for_the_verdict_that_no_longer_speaks(self):
        state, _entry = _inconsistent_entry()
        # Before: the carrier is the agent's verdict, so the cause renders.
        assert _fol_axis_status(state.fol_analysis_results).get("causes")
        assert _fol_stated_causes(state)

        _recheck(state, consistent=True)

        status = _fol_axis_status(state.fol_analysis_results)
        assert status.get("causes", []) == []
        assert _fol_stated_causes(state) == []

    def test_an_agreeing_recheck_keeps_the_cause(self):
        state, before = _inconsistent_entry()
        cause = before["consistency_cause"]

        entry = _recheck(state, consistent=False)

        assert entry["consistent"] is False
        assert entry["consistency_cause"] == cause
        assert "superseded_verdict" not in entry
        assert entry["external_checks"][-1]["agrees"] is True
        assert _fol_stated_causes(state)

    def test_an_undecided_entry_promoted_by_the_prover_states_no_invented_cause(self):
        state = UnifiedAnalysisState("texte")
        state.add_fol_analysis_result(
            list(FORMULAS), None, [], 0.0, message="degraded: no prover answer"
        )

        entry = _recheck(state, consistent=False)

        assert entry["consistent"] is False
        assert entry["consistent_source"] == "external:eprover"
        assert (
            "consistency_cause" not in entry
        ), "no producer classified this inconsistency; silence is honest"
        assert "superseded_verdict" not in entry  # nothing was displaced
        assert _fol_stated_causes(state) == []
