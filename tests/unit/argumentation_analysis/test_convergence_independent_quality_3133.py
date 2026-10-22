"""#3133 — the convergence counts independent signals only.

The #289 penalty multiplies an argument's ``note_finale`` by
``1 - min(0.3·n, 0.6)`` when *n* fallacies target it — a legitimate
cross-KB feature. But the quality writer dropped the ``fallacy_penalty``
record the evaluator attaches, so the state held a penalised ``overall``
next to unpenalised ``scores`` with nothing saying so; the convergence's
``"qualite faible"`` signal then read that penalised overall and counted
"low quality" as a method INDEPENDENT of the fallacy signal beside it.
The fallacy was counted twice — once directly, once through the score it
lowered — and the acts read "three independent methods converge" over two.

The repair keeps both judgements and separates the readers: the state
entry carries the penalty record (factor, fallacies, original score), the
convergence signal and its population gate read the UNPENALISED fraction,
and every other reader (acts' quality axes, deep synthesis, salience)
keeps reading the stored fallacy-adjusted ``overall`` — the penalty is
not removed, it just stops masquerading as a second witness.

Everything here is offline: real ``UnifiedAnalysisState`` objects through
the production writer, recorded evaluator outputs, no kernel, no network.
"""

from __future__ import annotations

import pytest

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.orchestration.state_writers import (
    _write_quality_to_state,
)
from argumentation_analysis.plugins.narrative_synthesis_plugin import (
    compute_argument_convergence,
)


def _virtues(total: float, n: int = 6) -> dict:
    """``n`` per-virtue [0, 1] scores summing to ``total``."""
    return {f"v{k}": total / n for k in range(n)}


def _penalised_entry(unpenalised_sum: float, n_fallacies: int) -> dict:
    """The evaluator output for a fallacy-targeted unit, post-#289."""
    factor = min(0.3 * n_fallacies, 0.6)
    return {
        "scores_par_vertu": _virtues(unpenalised_sum),
        "note_finale": unpenalised_sum * (1 - factor),
        "fallacy_penalty": {
            "applied": True,
            "fallacies": ["appel_au_peuple"] * n_fallacies,
            "penalty_factor": factor,
            "original_score": unpenalised_sum,
        },
    }


def _write_quality(state, entries: dict) -> None:
    """Run the production writer over an evaluator output."""
    _write_quality_to_state({"per_argument_scores": entries}, state, {})


def _signal_methods(state, arg_id: str) -> list:
    convergence = compute_argument_convergence(state)
    return [method for method, _detail in convergence[arg_id]["signals"]]


class TestTheStateRecordsThePenalty:
    def test_a_penalised_entry_keeps_the_penalty_record(self):
        # The writer used to store only the penalised ``overall`` — the
        # state then held an adjusted judgement with nothing saying so.
        state = UnifiedAnalysisState("texte")
        _write_quality(state, {"arg_1": _penalised_entry(3.6, 1)})
        entry = state.argument_quality_scores["arg_1"]
        penalty = entry["fallacy_penalty"]
        assert penalty["applied"] is True
        assert penalty["penalty_factor"] == pytest.approx(0.3)
        assert penalty["original_score"] == pytest.approx(3.6)
        assert len(penalty["fallacies"]) == 1

    def test_an_unpenalised_entry_gains_no_penalty_key(self):
        # No record, no key: the ~10 other readers of the entry see the
        # exact pre-#3133 shape when no penalty applies.
        state = UnifiedAnalysisState("texte")
        _write_quality(
            state,
            {"arg_1": {"scores_par_vertu": _virtues(6.0), "note_finale": 6.0}},
        )
        assert "fallacy_penalty" not in state.argument_quality_scores["arg_1"]


class TestConvergenceCountsIndependentSignals:
    @staticmethod
    def _state_with_penalised_unit():
        state = UnifiedAnalysisState("texte")
        state.identified_arguments = {
            "arg_1": "un argument vise par un sophisme",
            "arg_strong": "un argument solide",
        }
        state.identified_fallacies = {
            "f_1": {"target_argument_id": "arg_1", "type": "appel_au_peuple"},
        }
        _write_quality(
            state,
            {
                # Σ scores at 0.6 of the maximum, penalised to 0.42 — the
                # DoD instance: weak ONLY through the penalty.
                "arg_1": _penalised_entry(3.6, 1),
                # An unpenalised strong unit, so the population spans the
                # weak bar (the #1942 non-vacuity gate must not suppress
                # the signal the witness is about).
                "arg_strong": {
                    "scores_par_vertu": _virtues(6.0),
                    "note_finale": 6.0,
                },
            },
        )
        return state

    def test_a_unit_weak_only_through_the_penalty_gives_no_quality_signal(self):
        # On main the writer drops the record, the signal reads the
        # penalised 0.42 < 0.5, and "qualite faible" sits beside
        # "sophisme" as a second witness of the same fallacy.
        state = self._state_with_penalised_unit()
        assert _signal_methods(state, "arg_1") == ["sophisme"]

    def test_a_unit_weak_without_the_penalty_still_carries_qualite_faible(self):
        # Control: genuinely weak quality (0.3 of the maximum) keeps its
        # signal — the repair does not remove quality from convergence.
        state = UnifiedAnalysisState("texte")
        state.identified_arguments = {
            "arg_2": "un argument faible",
            "arg_strong": "un argument solide",
        }
        state.identified_fallacies = {
            "f_1": {"target_argument_id": "arg_2", "type": "appel_au_peuple"},
        }
        _write_quality(
            state,
            {
                "arg_2": _penalised_entry(1.8, 1),
                "arg_strong": {
                    "scores_par_vertu": _virtues(6.0),
                    "note_finale": 6.0,
                },
            },
        )
        assert _signal_methods(state, "arg_2") == ["sophisme", "qualite faible"]

    def test_the_signal_names_the_fraction_it_read(self):
        # The detail prints the fraction that fired the signal; with a
        # penalty on the entry that is the UNPENALISED one, stated as
        # such — a reader comparing with the stored ``overall`` must not
        # see two numbers with no explanation.
        arg_2_state = UnifiedAnalysisState("texte")
        arg_2_state.identified_arguments = {
            "arg_2": "un argument faible",
            "arg_strong": "un argument solide",
        }
        arg_2_state.identified_fallacies = {
            "f_1": {"target_argument_id": "arg_2", "type": "appel_au_peuple"},
        }
        _write_quality(
            arg_2_state,
            {
                "arg_2": _penalised_entry(1.8, 1),
                "arg_strong": {
                    "scores_par_vertu": _virtues(6.0),
                    "note_finale": 6.0,
                },
            },
        )
        details = [
            detail
            for method, detail in compute_argument_convergence(arg_2_state)["arg_2"][
                "signals"
            ]
            if method == "qualite faible"
        ]
        assert details and "30%" in details[0], details
        assert details and "penalite" in details[0].lower(), details


class TestThePopulationGateMeasuresTheSameQuantity:
    def test_a_gate_that_spans_only_unpenalised_lets_the_signal_fire(self):
        # #1942 gate consistency: the gate must measure the population the
        # signal reads. Here no PENALISED fraction clears 0.5 (max 0.42),
        # but the unpenalised population spans (0.6) — the genuinely weak
        # arg_b keeps its signal.
        state = UnifiedAnalysisState("texte")
        state.identified_arguments = {
            "arg_a": "un argument vise par un sophisme",
            "arg_b": "un argument faible sans sophisme",
        }
        state.identified_fallacies = {
            "f_1": {"target_argument_id": "arg_a", "type": "appel_au_peuple"},
        }
        _write_quality(
            state,
            {
                "arg_a": _penalised_entry(3.6, 1),
                "arg_b": {
                    "scores_par_vertu": _virtues(1.8),
                    "note_finale": 1.8,
                },
            },
        )
        assert "qualite faible" in _signal_methods(state, "arg_b")


class TestAddQualityScoreSanitisesTheRecord:
    def test_an_unapplied_or_absent_record_is_not_stored(self):
        state = UnifiedAnalysisState("texte")
        state.add_quality_score("arg_1", {"clarte": 0.5}, 0.5)
        assert "fallacy_penalty" not in state.argument_quality_scores["arg_1"]
        state.add_quality_score(
            "arg_2",
            {"clarte": 0.5},
            0.5,
            fallacy_penalty={"applied": False, "penalty_factor": 0.0},
        )
        assert "fallacy_penalty" not in state.argument_quality_scores["arg_2"]

    def test_an_applied_record_is_stored_next_to_overall(self):
        state = UnifiedAnalysisState("texte")
        record = {
            "applied": True,
            "fallacies": ["appeler_au_peuple"],
            "penalty_factor": 0.3,
            "original_score": 0.5,
        }
        state.add_quality_score("arg_1", {"clarte": 0.5}, 0.35, fallacy_penalty=record)
        entry = state.argument_quality_scores["arg_1"]
        assert entry["overall"] == pytest.approx(0.35)
        assert entry["fallacy_penalty"] == record
