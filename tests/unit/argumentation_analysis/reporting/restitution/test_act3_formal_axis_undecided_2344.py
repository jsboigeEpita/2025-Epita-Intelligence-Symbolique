"""#2344: a formal axis that ran and broke is named, not read as one that never ran.

``_pl_verified``/``_fol_verified`` count decided verdicts only. Before this fix,
an axis whose every result came back undecided produced the same prompt, the
same conclusion and the same ``degraded`` as an axis with no result at all
(measured on ``main`` ``8ee0d1380``). The absence channel of #1605 now carries
it, with the producer's message as the reason.

The end-to-end cases drive the real writers into a real
``UnifiedAnalysisState``, so the entry shapes are the ones production writes.
The LLM is an async stub returning a conclusion that says nothing about the
formal axes. Synthetic atoms only (no corpus tokens).
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.orchestration.state_writers import (
    _write_fol_to_state,
    _write_propositional_to_state,
    _write_qbf_to_state,
    _write_sat_to_state,
)
from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    build_act3_conclusion,
    build_act3_evidence,
    build_act3_prompt,
)

_SILENT = (
    "### Ce que le discours dit vraiment\n\n"
    "Le locuteur défend sa position en disqualifiant son contradicteur.\n\n"
    "### Ce qui tient et ce qui ne tient pas\n\n"
    "La thèse repose sur un raisonnement causal étayé.\n\n"
    "### Comment se faire son avis\n\n"
    "Recevoir avec prudence l'attaque personnelle, retenir l'argument causal."
)

_PL_LABEL = "la logique propositionnelle"
_FOL_LABEL = "la logique du premier ordre"


def _stub_llm(text: str):
    async def _call(_prompt: str) -> str:
        return text

    return _call


def _state() -> UnifiedAnalysisState:
    state = UnifiedAnalysisState("formal-axis-undecided-2344 synthetic probe")
    state.add_argument("Le locuteur disqualifie l'adversaire.")
    state.add_argument("Une revendication défendue par un raisonnement causal.")
    return state


def _conclude(state, text: str = _SILENT):
    return asyncio.run(build_act3_conclusion(state, llm_callable=_stub_llm(text)))


def _lost(state) -> dict:
    return {d.capability: d for d in build_act3_evidence(state).absent_dimensions}


# --- what each writer leaves when the axis breaks -----------------------------


def _pl_broken(state) -> None:
    _write_propositional_to_state(
        {
            "formulas": ["p1 & p2", "!p1"],
            "satisfiable": None,
            "model": {},
            "message": "combined consistency unverified: parser rejected p2",
        },
        state,
        {},
    )


def _sat_backend_missing(state) -> None:
    _write_sat_to_state(
        {
            "mode": "solve",
            "satisfiable": None,
            "model": None,
            "error": "PySAT backend not installed",
        },
        state,
        {},
    )


def _fol_no_translation(state) -> None:
    _write_fol_to_state(
        {
            "formulas": [],
            "consistent": None,
            "message": "unavailable:no-translation — NL→FOL produced no formula",
            "fol_status": "unavailable:no-translation",
        },
        state,
        {},
    )


class TestNeverRunAndBrokenReadDifferently:
    """The discriminating control: before the fix all three pairs were equal."""

    @pytest.mark.parametrize(
        "break_axis, label",
        [
            (_pl_broken, _PL_LABEL),
            (_sat_backend_missing, _PL_LABEL),
            (_fol_no_translation, _FOL_LABEL),
        ],
        ids=["pl-parser", "sat-backend", "fol-translation"],
    )
    def test_broken_axis_changes_prompt_conclusion_and_degraded(
        self, break_axis, label
    ):
        never = _state()
        broken = _state()
        break_axis(broken)

        assert build_act3_prompt(build_act3_evidence(never)) != build_act3_prompt(
            build_act3_evidence(broken)
        )
        never_result, broken_result = _conclude(never), _conclude(broken)
        assert "act3_absent_dimensions" not in never_result.degraded
        assert label in broken_result.degraded["act3_absent_dimensions"]
        assert "Portée de cette analyse" not in never_result.narrative
        assert "Portée de cette analyse" in broken_result.narrative
        assert label in broken_result.narrative

    def test_the_scope_note_survives_the_claim_gate(self):
        # The note names the lost axis, and the #1605 claim gate removes a
        # sentence that names an axis without support unless it states the
        # absence. The note states it, so it must reach the reader intact.
        state = _state()
        _pl_broken(state)
        result = _conclude(state)
        assert "act3_claim_blocked" not in result.degraded
        assert f"n'a pas abouti sur ce texte : {_PL_LABEL}" in result.narrative


class TestTheCauseReachesThePrompt:
    def test_producer_message_is_the_reason(self):
        state = _state()
        _pl_broken(state)
        dim = _lost(state)["formal_pl"]
        assert dim.status == "undecided"
        assert dim.reason.startswith("1 résultat sans verdict décidé : ")
        assert "parser rejected p2" in dim.reason
        assert "parser rejected p2" in build_act3_prompt(build_act3_evidence(state))

    def test_sat_error_is_kept_as_the_entry_message(self):
        # The SAT writer used to drop the producer's ``error``: an undecided SAT
        # entry reached the state with no cause at all.
        state = _state()
        _sat_backend_missing(state)
        (entry,) = state.propositional_analysis_results
        assert entry["message"] == "PySAT backend not installed"
        assert "PySAT backend not installed" in _lost(state)["formal_pl"].reason

    def test_no_message_still_names_the_count(self):
        state = SimpleNamespace(
            identified_arguments={"arg_1": "x"},
            propositional_analysis_results=[
                {"formulas": ["p"], "satisfiable": None},
                {"formulas": ["q"], "satisfiable": None},
            ],
        )
        assert _lost(state)["formal_pl"].reason == "2 résultats sans verdict décidé."


class TestWhatIsNotALoss:
    def test_an_axis_that_did_not_run_is_not_lost(self):
        assert _lost(_state()) == {}

    def test_one_decided_result_keeps_the_axis(self):
        # The conclusion stands on its decided results; the appendix counts the
        # undecided ones.
        state = _state()
        _pl_broken(state)
        _write_propositional_to_state(
            {"formulas": ["p3"], "satisfiable": True, "model": {"p3": True}},
            state,
            {},
        )
        assert "formal_pl" not in _lost(state)
        assert "formal_pl" in build_act3_evidence(state).verdict.nontrivial_axes

    def test_undecided_guest_entry_does_not_make_the_host_axis_lost(self):
        # QBF writes into the PL container; its undecided verdict is not a
        # propositional result (#1605 guest rule), so no PL axis is lost.
        state = _state()
        _write_qbf_to_state({"formula": "exists x: x", "valid": None}, state, {})
        assert state.propositional_analysis_results
        assert "formal_pl" not in _lost(state)


class TestCompliantProseIsNotRepeated:
    def test_prose_naming_the_lost_axis_gets_no_second_note(self):
        state = _state()
        _pl_broken(state)
        compliant = _SILENT + (
            "\n\nLa vérification propositionnelle n'a pas abouti sur ce texte."
        )
        result = _conclude(state, compliant)
        assert "Portée de cette analyse" not in result.narrative
        assert "n'a pas abouti sur ce texte." in result.narrative
        assert "act3_absent_dimensions" in result.degraded
