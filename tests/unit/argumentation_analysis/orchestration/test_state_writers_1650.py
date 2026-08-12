"""#1650 — Three-state formal verdicts: an absent verdict never folds onto False.

Each writer test drives the real ``_write_*_to_state`` writer with an output
dict that LACKS the verdict key (or carries an explicit ``None``), and asserts
the state entry preserves it — ``None`` (undetermined) is never collapsed onto
``False`` ("the prover said nothing" != "the prover said no", #1019).

Anti-#1019 discipline (R761 #1643, R764 #1636): the writer is real, the handler
output is stubbed. A mocked writer would just agree with itself. The
substitution control is executed per site in the PR: reverting a writer to the
two-state form (``.get(key, False)`` / ``bool(...)``) makes the armed test go
red.

Privacy: synthetic atoms only (no corpus tokens).
"""

from __future__ import annotations

from typing import Any, Dict
from unittest.mock import AsyncMock, patch

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.orchestration.state_writers import (
    _write_cl_to_state,
    _write_modal_to_state,
    _write_nl_to_logic_to_state,
    _write_propositional_to_state,
    _write_qbf_to_state,
    _write_sat_to_state,
)


def _new_state() -> UnifiedAnalysisState:
    """A fresh state for a single writer probe."""
    return UnifiedAnalysisState("three-state-1650 synthetic probe")


# ─────────────────────────────────────────────────────────────────────────────
# PL — _write_propositional_to_state (state_writers.py, satisfiable)
# ─────────────────────────────────────────────────────────────────────────────


class TestPlSatisfiableThreeState1650:
    def test_absent_key_is_none_not_false(self) -> None:
        state = _new_state()
        _write_propositional_to_state(
            {"formulas": ["p & q"], "model": {"p": True}}, state, {}
        )
        assert state.propositional_analysis_results[0]["satisfiable"] is None

    def test_explicit_none_preserved(self) -> None:
        state = _new_state()
        _write_propositional_to_state(
            {"formulas": ["p"], "satisfiable": None, "model": {}}, state, {}
        )
        assert state.propositional_analysis_results[0]["satisfiable"] is None

    def test_decided_false_preserved(self) -> None:
        state = _new_state()
        _write_propositional_to_state(
            {"formulas": ["p & !p"], "satisfiable": False, "model": {}}, state, {}
        )
        assert state.propositional_analysis_results[0]["satisfiable"] is False

    def test_decided_true_preserved(self) -> None:
        state = _new_state()
        _write_propositional_to_state(
            {"formulas": ["p"], "satisfiable": True, "model": {"p": True}}, state, {}
        )
        assert state.propositional_analysis_results[0]["satisfiable"] is True


# ─────────────────────────────────────────────────────────────────────────────
# Modal — _write_modal_to_state (state_writers.py, valid)
# ─────────────────────────────────────────────────────────────────────────────


class TestModalValidThreeState1650:
    def test_absent_key_is_none_not_false(self) -> None:
        state = _new_state()
        _write_modal_to_state(
            {"formulas": ["K(agent, p)"], "modalities": ["epistemic"]}, state, {}
        )
        assert state.modal_analysis_results[0]["valid"] is None

    def test_explicit_none_preserved(self) -> None:
        # no-solver / no-translation → the producer emits valid=None
        state = _new_state()
        _write_modal_to_state(
            {"formulas": ["<>p"], "valid": None, "modalities": ["alethic"]}, state, {}
        )
        assert state.modal_analysis_results[0]["valid"] is None

    def test_decided_false_preserved(self) -> None:
        state = _new_state()
        _write_modal_to_state(
            {"formulas": ["[]p"], "valid": False, "modalities": ["necessity"]},
            state,
            {},
        )
        assert state.modal_analysis_results[0]["valid"] is False

    def test_decided_true_preserved(self) -> None:
        state = _new_state()
        _write_modal_to_state(
            {"formulas": ["<>p"], "valid": True, "modalities": ["possibility"]},
            state,
            {},
        )
        assert state.modal_analysis_results[0]["valid"] is True


# ─────────────────────────────────────────────────────────────────────────────
# NL→logic — _write_nl_to_logic_to_state (state_writers.py, is_valid)
# ─────────────────────────────────────────────────────────────────────────────


class TestNlToLogicIsValidThreeState1650:
    def test_absent_key_is_none_not_false(self) -> None:
        state = _new_state()
        _write_nl_to_logic_to_state(
            {"translations": [{"formula": "p -> q", "original_text": "s1"}]},
            state,
            {},
        )
        assert state.nl_to_logic_translations[0]["is_valid"] is None

    def test_decided_false_preserved(self) -> None:
        state = _new_state()
        _write_nl_to_logic_to_state(
            {
                "translations": [
                    {"formula": "p -> q", "original_text": "s1", "is_valid": False}
                ]
            },
            state,
            {},
        )
        assert state.nl_to_logic_translations[0]["is_valid"] is False

    def test_decided_true_preserved(self) -> None:
        state = _new_state()
        _write_nl_to_logic_to_state(
            {
                "translations": [
                    {"formula": "p -> q", "original_text": "s1", "is_valid": True}
                ]
            },
            state,
            {},
        )
        assert state.nl_to_logic_translations[0]["is_valid"] is True


# ─────────────────────────────────────────────────────────────────────────────
# Conditional Logic — _write_cl_to_state (state_writers.py, entailed)
# ─────────────────────────────────────────────────────────────────────────────


class TestClEntailedThreeState1650:
    def test_absent_key_is_none_not_false(self) -> None:
        state = _new_state()
        _write_cl_to_state({"message": "synthetic", "num_conditionals": 2}, state, {})
        entry = state.propositional_analysis_results[0]
        assert entry["satisfiable"] is None
        assert entry["formulas"][0].startswith("CL(")

    def test_decided_false_preserved(self) -> None:
        state = _new_state()
        _write_cl_to_state(
            {"entailed": False, "message": "m", "num_conditionals": 1}, state, {}
        )
        assert state.propositional_analysis_results[0]["satisfiable"] is False

    def test_decided_true_preserved(self) -> None:
        state = _new_state()
        _write_cl_to_state(
            {"entailed": True, "message": "m", "num_conditionals": 0}, state, {}
        )
        assert state.propositional_analysis_results[0]["satisfiable"] is True


# ─────────────────────────────────────────────────────────────────────────────
# SAT — _write_sat_to_state (state_writers.py, satisfiable)
# ─────────────────────────────────────────────────────────────────────────────


class TestSatSatisfiableThreeState1650:
    def test_absent_key_is_none_not_false(self) -> None:
        state = _new_state()
        _write_sat_to_state({"mode": "solve", "model": {}}, state, {})
        entry = state.propositional_analysis_results[0]
        assert entry["satisfiable"] is None
        assert entry["formulas"] == ["SAT: indéterminé"]

    def test_explicit_none_preserved(self) -> None:
        # PySAT unavailable → the producer emits satisfiable=None
        state = _new_state()
        _write_sat_to_state(
            {"mode": "solve", "satisfiable": None, "model": None}, state, {}
        )
        entry = state.propositional_analysis_results[0]
        assert entry["satisfiable"] is None
        assert entry["formulas"] == ["SAT: indéterminé"]

    def test_sat_true_preserved(self) -> None:
        state = _new_state()
        _write_sat_to_state(
            {"mode": "solve", "satisfiable": True, "model": {"p": True}}, state, {}
        )
        entry = state.propositional_analysis_results[0]
        assert entry["satisfiable"] is True
        assert entry["formulas"] == ["SAT: SAT"]

    def test_unsat_false_preserved(self) -> None:
        state = _new_state()
        _write_sat_to_state(
            {"mode": "solve", "satisfiable": False, "model": {}}, state, {}
        )
        entry = state.propositional_analysis_results[0]
        assert entry["satisfiable"] is False
        assert entry["formulas"] == ["SAT: UNSAT"]

    def test_mus_branch_keeps_explicit_false(self) -> None:
        # MUS found unsat subsets = a decided verdict; the explicit False stays
        state = _new_state()
        _write_sat_to_state({"mode": "mus", "mus_count": 2}, state, {})
        entry = state.propositional_analysis_results[0]
        assert entry["satisfiable"] is False
        assert entry["formulas"][0].startswith("SAT/MUS:")


# ─────────────────────────────────────────────────────────────────────────────
# QBF — _write_qbf_to_state (state_writers.py, valid → satisfiable)
# ─────────────────────────────────────────────────────────────────────────────


class TestQbfValidThreeState1650:
    def test_absent_key_is_none_not_false(self) -> None:
        state = _new_state()
        _write_qbf_to_state({"formula": "exists x. P(x)"}, state, {})
        assert state.propositional_analysis_results[0]["satisfiable"] is None

    def test_explicit_none_preserved(self) -> None:
        # QBF analysis failed → the producer emits valid=None
        state = _new_state()
        _write_qbf_to_state(
            {"formula": "P(x)", "valid": None, "fallback": "error"}, state, {}
        )
        assert state.propositional_analysis_results[0]["satisfiable"] is None

    def test_decided_false_preserved(self) -> None:
        state = _new_state()
        _write_qbf_to_state({"formula": "P(x)", "valid": False}, state, {})
        assert state.propositional_analysis_results[0]["satisfiable"] is False

    def test_decided_true_preserved(self) -> None:
        state = _new_state()
        _write_qbf_to_state({"formula": "P(x)", "valid": True}, state, {})
        assert state.propositional_analysis_results[0]["satisfiable"] is True


# ─────────────────────────────────────────────────────────────────────────────
# Producer regrep finds — invoke_callables.py
# ─────────────────────────────────────────────────────────────────────────────


class TestInvokeQbfErrorBranchThreeState1650:
    """A failed QBF analysis is undetermined (None), never 'invalid' (False).

    Regrep finding (#1650 DoD): the error fallback of ``_invoke_qbf`` wrote
    ``valid: False`` when both backends failed — folding "no solver ran" onto
    "the formula is invalid" for every downstream reader of ``valid``.
    """

    async def test_error_fallback_valid_is_none(self) -> None:
        from argumentation_analysis.orchestration import invoke_callables

        with (
            patch(
                "argumentation_analysis.agents.core.logic.qbf_handler.QBFHandler",
                side_effect=RuntimeError("forced JVM QBF failure"),
            ),
            patch(
                "argumentation_analysis.agents.core.logic.qbf_native.analyze_qbf",
                side_effect=RuntimeError("forced native QBF failure"),
            ),
        ):
            result = await invoke_callables._invoke_qbf(
                "P(x)", {"quantifiers": [], "formula": "P(x)"}
            )

        assert result["fallback"] == "error"
        assert result["valid"] is None


class TestRunFormalLogicFromStatePlThreeState1650:
    """The conversational PL post-processor preserves an absent verdict.

    Regrep finding (#1650 DoD): the direct ``add_propositional_analysis_result``
    call in ``_run_formal_logic_from_state`` folded
    ``bool(pl_out.get("satisfiable", False))`` — the same two-state motif as the
    sequential writer, on the conversational path.
    """

    async def test_absent_satisfiable_preserved_as_none(self) -> None:
        from argumentation_analysis.orchestration import invoke_callables

        state = _new_state()
        state.identified_arguments = {"a1": "synthetic argument text"}
        with (
            patch(
                "argumentation_analysis.orchestration.invoke_callables."
                "_invoke_propositional_logic",
                new=AsyncMock(return_value={"formulas": ["p"], "model": {"p": True}}),
            ),
            patch(
                "argumentation_analysis.orchestration.invoke_callables."
                "_invoke_fol_reasoning",
                new=AsyncMock(return_value={}),
            ),
        ):
            result = await invoke_callables._run_formal_logic_from_state(
                state, "synthetic"
            )

        assert result["pl_added"] == 1
        assert state.propositional_analysis_results[0]["satisfiable"] is None

    async def test_decided_false_preserved(self) -> None:
        from argumentation_analysis.orchestration import invoke_callables

        state = _new_state()
        state.identified_arguments = {"a1": "synthetic argument text"}
        with (
            patch(
                "argumentation_analysis.orchestration.invoke_callables."
                "_invoke_propositional_logic",
                new=AsyncMock(
                    return_value={"formulas": ["p"], "satisfiable": False, "model": {}}
                ),
            ),
            patch(
                "argumentation_analysis.orchestration.invoke_callables."
                "_invoke_fol_reasoning",
                new=AsyncMock(return_value={}),
            ),
        ):
            await invoke_callables._run_formal_logic_from_state(state, "synthetic")

        assert state.propositional_analysis_results[0]["satisfiable"] is False
