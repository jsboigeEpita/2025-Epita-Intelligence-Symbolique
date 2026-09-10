"""#1635: the external-solver verdict must reach the state it claims to write.

Both external-solver writers had two write branches and neither ever fired on a
real run: the dict-state branch wrote ``state["external_fol_solver"]`` /
``state["external_modal_solver"]`` — keys no reader polls — and the
``UnifiedAnalysisState`` branch was gated on ``isinstance(state.fol_analysis_results,
dict)``, always False because the canonical attribute is a ``List``. The solver
ran, decided, and the verdict evaporated.

These tests build a REAL ``UnifiedAnalysisState`` (never a hand-made dict, never
a ``MagicMock``) and call the writers with the exact output shape
``_invoke_external_fol_solver`` / ``_invoke_external_modal_solver`` emit
(``invoke_callables.py``): ``{formulas, consistent|valid, solver, degraded,
message, logic_type}``. The verdict must land in the canonical
``fol_analysis_results`` / ``modal_analysis_results`` lists — the only form every
reader (appendix axis status, Acte II) consumes — with the solver provenance
carried by ``message`` (#1278/#1279) and the tri-state preserved (#1019).

They fail if the write becomes unreachable again: on a real state an unwritten
verdict leaves the list empty.
"""

from __future__ import annotations

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.orchestration.state_writers import (
    _write_external_fol_solver_to_state,
    _write_external_modal_solver_to_state,
)
from argumentation_analysis.reporting.restitution.appendix import (
    _fol_axis_status,
    _modal_axis_status,
)


def _fol_handler_output(consistent, solver="tweety", message="FOL check done"):
    """Exact emit shape of ``_invoke_external_fol_solver`` (tri-state consistent)."""
    return {
        "formulas": ["forall x (P(x) -> Q(x))"],
        "consistent": consistent,
        "solver": solver,
        "degraded": consistent is None,
        "message": message,
        "logic_type": "fol",
    }


def _modal_handler_output(valid, solver="spass", message="Modal check done"):
    """Exact emit shape of ``_invoke_external_modal_solver`` (tri-state valid)."""
    return {
        "formulas": ["[]p", "<>q"],
        "valid": valid,
        "modalities": ["box", "diamond"],
        "solver": solver,
        "degraded": valid is None,
        "message": message,
        "logic_type": "modal",
    }


class TestExternalFolSolverVerdictReachesState:
    def test_decided_verdict_lands_in_fol_list_with_provenance(self):
        state = UnifiedAnalysisState("texte")
        _write_external_fol_solver_to_state(
            _fol_handler_output(consistent=True, solver="eprover"), state, {}
        )
        assert len(state.fol_analysis_results) == 1
        entry = state.fol_analysis_results[0]
        assert entry["consistent"] is True
        assert "eprover" in (
            entry.get("message") or ""
        ), "provenance must name the external solver (#1278)"

    def test_degraded_verdict_lands_as_none_never_dropped(self):
        # consistent=None (parse-fail / no-solver) must still append an honest
        # degraded entry — silence reads as "axis never ran" (#1019).
        state = UnifiedAnalysisState("texte")
        _write_external_fol_solver_to_state(
            _fol_handler_output(consistent=None, solver="none"), state, {}
        )
        assert len(state.fol_analysis_results) == 1
        assert state.fol_analysis_results[0]["consistent"] is None

    def test_repeated_writes_append_not_overwrite(self):
        # The dead dict branch overwrote scalar keys; the canonical list form
        # accumulates one entry per solver decision.
        state = UnifiedAnalysisState("texte")
        _write_external_fol_solver_to_state(_fol_handler_output(True), state, {})
        _write_external_fol_solver_to_state(_fol_handler_output(False), state, {})
        assert len(state.fol_analysis_results) == 2

    def test_appendix_reads_the_written_verdict(self):
        # End-to-end on a real state: writer → canonical list → appendix reader.
        state = UnifiedAnalysisState("texte")
        _write_external_fol_solver_to_state(
            _fol_handler_output(consistent=False), state, {}
        )
        status = _fol_axis_status(state.fol_analysis_results)
        assert status["verdict"] == "décidé"
        assert status["inconsistantes"] == 1


class TestExternalModalSolverVerdictReachesState:
    def test_decided_verdict_lands_in_modal_list_with_provenance(self):
        state = UnifiedAnalysisState("texte")
        _write_external_modal_solver_to_state(
            _modal_handler_output(valid=True, solver="spass"), state, {}
        )
        assert len(state.modal_analysis_results) == 1
        entry = state.modal_analysis_results[0]
        assert entry["valid"] is True
        assert "spass" in (
            entry.get("message") or ""
        ), "provenance must name the external solver (#1279)"

    def test_degraded_verdict_lands_as_none_never_dropped(self):
        state = UnifiedAnalysisState("texte")
        _write_external_modal_solver_to_state(
            _modal_handler_output(valid=None, solver="none"), state, {}
        )
        assert len(state.modal_analysis_results) == 1
        assert state.modal_analysis_results[0]["valid"] is None

    def test_repeated_writes_append_not_overwrite(self):
        state = UnifiedAnalysisState("texte")
        _write_external_modal_solver_to_state(_modal_handler_output(True), state, {})
        _write_external_modal_solver_to_state(_modal_handler_output(False), state, {})
        assert len(state.modal_analysis_results) == 2

    def test_appendix_reads_the_written_verdict(self):
        state = UnifiedAnalysisState("texte")
        _write_external_modal_solver_to_state(
            _modal_handler_output(valid=False), state, {}
        )
        status = _modal_axis_status(state.modal_analysis_results)
        assert status["verdict"] == "décidé"
        assert status["inconsistantes"] == 1
