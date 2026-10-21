"""#3106 — one FOL theory is one entry, however many solvers re-checked it.

Observed on the R1102 tunnel pass (doc_A): ``fol_analysis_results`` held three
entries where entry 1 (the FOL agent, EProver) and entry 2
(``_write_external_fol_solver_to_state``, the same EProver on the *same* formula
list) were one theory re-checked, not two analyses. The synthesis read the two
entries as two first-order analyses "returning inconsistency", i.e. as agreeing
checks, and the figure "N analyses" counted entries.

The repair is at the writer — the single site every reader consumes — never in
a reader: a re-check whose formula list an entry already holds attaches to that
entry (``external_checks``), naming its solver and whether it agrees; only a
different formula set appends a new theory.

Tri-state (#1019) is preserved in both directions: ``agrees`` is None when
either side did not decide, and the external verdict wins exactly where the
dispatch says it must — when it diverges from the entry's verdict, or when the
entry decided nothing — with ``consistent_source`` naming it and the displaced
verdict kept in ``superseded_verdict``. A degraded external answer (None) never
displaces a decision.

Real ``UnifiedAnalysisState`` objects, the production writers, opaque
predicates — no network, no LLM, zero spend.
"""

from __future__ import annotations

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.orchestration.state_writers import (
    _write_external_fol_solver_to_state,
    _write_fol_to_state,
)
from argumentation_analysis.reporting.restitution.appendix import _fol_axis_status

_FORMULAS = ["Pa", "!Pa", "Qb"]


def _agent_output(
    formulas=None, consistent=True, message="FOL consistency check (EProver)"
):
    """Exact emit shape of the FOL agent, as ``_write_fol_to_state`` reads it."""
    return {
        "formulas": list(formulas if formulas is not None else _FORMULAS),
        "consistent": consistent,
        "inferences": [],
        "confidence": 0.4,
        "message": message,
        "fol_status": "decided" if consistent is not None else "unavailable:no-solver",
    }


def _external_output(
    formulas=None, consistent=False, solver="eprover", message="check"
):
    """Exact emit shape of ``_invoke_external_fol_solver``."""
    return {
        "formulas": list(formulas if formulas is not None else _FORMULAS),
        "consistent": consistent,
        "solver": solver,
        "degraded": consistent is None,
        "message": message,
        "logic_type": "fol",
    }


class TestOneTheoryPerFormulaSet:
    def test_a_divergent_recheck_carries_the_external_verdict(self):
        """Same formula list ⇒ one entry; a divergence is not silently absorbed."""
        state = UnifiedAnalysisState("texte")
        _write_fol_to_state(_agent_output(consistent=True), state, {})
        _write_external_fol_solver_to_state(
            _external_output(consistent=False), state, {}
        )

        assert len(state.fol_analysis_results) == 1
        entry = state.fol_analysis_results[0]
        assert entry["consistent"] is False, "the prover's decision carries"
        assert entry["consistent_source"] == "external:eprover"
        assert entry["superseded_verdict"] == {
            "consistent": True,
            "source": "fol_agent",
        }, "the verdict it displaced must stay readable, not be erased"
        assert len(entry["external_checks"]) == 1
        check = entry["external_checks"][0]
        assert check["solver"] == "eprover"
        assert check["consistent"] is False
        assert check["agrees"] is False, "a divergent re-check must stay visible"
        assert "eprover" in check["message"]

    def test_the_render_counts_one_theory_not_two_entries(self):
        """The appendix counts THEORIES: one entry ⇒ one verified analysis."""
        state = UnifiedAnalysisState("texte")
        _write_fol_to_state(_agent_output(consistent=True), state, {})
        _write_external_fol_solver_to_state(
            _external_output(consistent=False), state, {}
        )

        status = _fol_axis_status(state.fol_analysis_results)
        assert status["verifiees"] == 1
        assert status["consistantes"] == 0
        assert status["inconsistantes"] == 1, (
            "the theory reads as the external solver found it; the divergence "
            "is not a second theory"
        )

    def test_a_degraded_entry_takes_the_external_verdict_with_its_source(self):
        """An agent that decided nothing must not hide a real external decision."""
        state = UnifiedAnalysisState("texte")
        _write_fol_to_state(_agent_output(consistent=None), state, {})
        _write_external_fol_solver_to_state(
            _external_output(consistent=False), state, {}
        )

        assert len(state.fol_analysis_results) == 1
        entry = state.fol_analysis_results[0]
        assert entry["consistent"] is False
        assert entry["consistent_source"] == "external:eprover"
        assert entry["external_checks"][0]["agrees"] is None

    def test_both_undecided_records_no_agreement(self):
        """Two undecided sides corroborate nothing — ``agrees`` stays None."""
        state = UnifiedAnalysisState("texte")
        _write_fol_to_state(_agent_output(consistent=None), state, {})
        _write_external_fol_solver_to_state(
            _external_output(consistent=None, solver="none"), state, {}
        )

        assert len(state.fol_analysis_results) == 1
        entry = state.fol_analysis_results[0]
        assert entry["consistent"] is None
        assert "consistent_source" not in entry
        assert entry["external_checks"][0]["agrees"] is None

    def test_a_different_formula_set_appends_a_second_theory(self):
        state = UnifiedAnalysisState("texte")
        _write_fol_to_state(_agent_output(consistent=True), state, {})
        _write_external_fol_solver_to_state(
            _external_output(formulas=["Rc", "Sc"], consistent=False), state, {}
        )

        assert len(state.fol_analysis_results) == 2
        assert state.fol_analysis_results[1]["consistent"] is False

    def test_a_same_solver_recheck_is_a_rerun_not_corroboration(self):
        """Two external checks on one theory: one entry, both checks kept."""
        state = UnifiedAnalysisState("texte")
        _write_fol_to_state(_agent_output(consistent=True), state, {})
        _write_external_fol_solver_to_state(
            _external_output(consistent=True), state, {}
        )
        _write_external_fol_solver_to_state(
            _external_output(consistent=True), state, {}
        )

        assert len(state.fol_analysis_results) == 1
        entry = state.fol_analysis_results[0]
        checks = entry["external_checks"]
        assert len(checks) == 2
        assert {c["solver"] for c in checks} == {"eprover"}
        assert entry["consistent"] is True
        assert "consistent_source" not in entry, "agreement displaces nothing"
        assert "superseded_verdict" not in entry

    def test_a_degraded_external_answer_displaces_nothing(self):
        """None is "did not decide" (#1019) — it must never overwrite a verdict."""
        state = UnifiedAnalysisState("texte")
        _write_fol_to_state(_agent_output(consistent=True), state, {})
        _write_external_fol_solver_to_state(
            _external_output(consistent=None, solver="none"), state, {}
        )

        entry = state.fol_analysis_results[0]
        assert entry["consistent"] is True
        assert "consistent_source" not in entry
        assert entry["external_checks"][0]["agrees"] is None

    def test_whitespace_differences_still_identify_one_theory(self):
        """The comparison is on formula content, not on string padding."""
        state = UnifiedAnalysisState("texte")
        _write_fol_to_state(_agent_output(consistent=True), state, {})
        _write_external_fol_solver_to_state(
            _external_output(formulas=[" Pa", "!Pa ", "Qb  "], consistent=False),
            state,
            {},
        )
        assert len(state.fol_analysis_results) == 1

    def test_empty_formula_lists_never_merge(self):
        """A degenerate (empty) set identifies no theory — never attach there."""
        state = UnifiedAnalysisState("texte")
        _write_external_fol_solver_to_state(_external_output(formulas=[]), state, {})
        _write_external_fol_solver_to_state(_external_output(formulas=[]), state, {})

        assert len(state.fol_analysis_results) == 2
