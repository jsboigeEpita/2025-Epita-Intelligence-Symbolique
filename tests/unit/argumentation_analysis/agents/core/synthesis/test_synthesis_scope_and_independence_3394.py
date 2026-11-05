"""#3394 asks 4-5 (R1143) — the synthesis briefing's deferred holes, filled
on the main that #3406/#3409 landed on.

Ask 1 residual — ``_quality_line``: the writer received ``overall=1.28``
bare. The line now rides the score's own ceiling (``len(scores)``, #1942),
penalised or not; an entry with no ``scores`` map has an unmeasurable
ceiling and keeps the bare spelling.

Ask 3 residual — the briefing's fallacy lines carried ``type=<label>``
with no definition; the acts already print one, the briefing did not.

Ask 4 — « regularly »: the cycle-0 synthesis generalised ten fallacy lines
into a regularity claim over the whole document. The fallacy evidence now
travels with its read scope: how many units the detections sit on, over
how many the run identified.

Ask 5 — « plusieurs méthodes indépendantes convergent » counted a quality
score the same fallacy had penalised. A penalised unit's quality judgement
stays as CITED content and stops counting as an independent witness
(``compute_argument_convergence``, the #3145/#3133 machinery's next step).

Offline: no JVM, no network, no LLM.
"""

from __future__ import annotations

from types import SimpleNamespace

from argumentation_analysis.agents.core.synthesis.deep_synthesis_agent import (
    DeepSynthesisAgent,
)
from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.orchestration.state_writers import (
    _write_quality_to_state,
)
from argumentation_analysis.plugins.narrative_synthesis_plugin import (
    build_convergent_synthesis,
    compute_argument_convergence,
)

_ADDRESSEE = "la taxonomie s'adresse à qui commet le sophisme"


class TestTheQualityLineRidesItsScale:
    """Ask 1 residual — the writer receives the formatted string."""

    def test_an_unpenalised_sum_carries_its_ceiling(self):
        entry = {"scores": {f"v{i}": 0.5 for i in range(6)}, "overall": 1.28}
        assert DeepSynthesisAgent._quality_line(entry) == "overall=1,28 sur 6"

    def test_a_penalised_sum_carries_ceiling_and_penalty(self):
        entry = {
            "scores": {f"v{i}": 0.5 for i in range(6)},
            "overall": 4.250000000000001,
            "fallacy_penalty": {
                "applied": True,
                "fallacies": ["sophisme_a"],
                "penalty_factor": 0.15,
                "original_score": 5.0,
            },
        }
        line = DeepSynthesisAgent._quality_line(entry)
        assert line.startswith("overall=4,25 sur 6 après pénalité (5,00 avant)"), line
        assert "score penalise, non comparable aux scores sans penalite" in line

    def test_an_entry_without_scores_keeps_the_bare_spelling(self):
        # Control (the issue's byte-stability clause): no measurable
        # ceiling, no invented scale — and no penalty, no invented one.
        assert DeepSynthesisAgent._quality_line({"overall": 1.8}) == "overall=1.8"
        assert DeepSynthesisAgent._quality_line(4.5) == "overall=4.5"


class TestTheBriefingFallacyLines:
    """Ask 3 residual + ask 4 — the definition rides the first mention, the
    scope rides the section."""

    @staticmethod
    def _state(n_args: int, fallacies: dict) -> SimpleNamespace:
        return SimpleNamespace(
            identified_arguments={
                f"arg_{i}": f"Une revendication synthetique numero {i}."
                for i in range(1, n_args + 1)
            },
            identified_fallacies=fallacies,
            argument_quality_scores={},
            counter_arguments=[],
        )

    @staticmethod
    def _fallacy(fid: str, target: str, ftype: str = "appel_au_peuple") -> dict:
        return {
            "type": ftype,
            "family": "Erreur de raisonnement",
            "target_argument_id": target,
            "justification": "justification synthetique",
            "taxonomy_path": "6.3.3.1.3.2.2" if ftype == "comportementalisme" else "",
        }

    def test_the_first_fallacy_line_carries_the_definition(self):
        state = self._state(
            2, {"f_1": self._fallacy("f_1", "arg_1", "comportementalisme")}
        )
        brief = DeepSynthesisAgent.build_artifact_briefing(state)
        assert (
            f"— définition ({_ADDRESSEE}) : Vous adhérez" in brief
        ), "a label reaching the synthesis writer carries its definition (#3394)"

    def test_the_definition_is_said_once_per_label(self):
        state = self._state(
            2,
            {
                "f_1": self._fallacy("f_1", "arg_1", "comportementalisme"),
                "f_2": self._fallacy("f_2", "arg_2", "comportementalisme"),
            },
        )
        brief = DeepSynthesisAgent.build_artifact_briefing(state)
        assert brief.count("définition") == 1, brief.count("définition")

    def test_the_fallacy_section_states_its_read_scope(self):
        # Ask 4 — ten lines over four hundred units must not read as
        # « the text regularly … »: the counts travel with the evidence.
        state = self._state(
            5,
            {
                "f_1": self._fallacy("f_1", "arg_1"),
                "f_2": self._fallacy("f_2", "arg_3"),
            },
        )
        brief = DeepSynthesisAgent.build_artifact_briefing(state)
        assert (
            "PORTÉE DES DÉTECTIONS : les 2 détection(s) de ce run portent "
            "sur 2 unités distinctes, parmi 5 unités identifiées" in brief
        ), brief[:400]
        assert "se lit sur ces 2 unités" in brief

    def test_a_state_without_fallacies_states_no_scope(self):
        # Control: no detections, no scope line — the absence is not a
        # population.
        state = self._state(3, {})
        brief = DeepSynthesisAgent.build_artifact_briefing(state)
        assert "PORTÉE DES DÉTECTIONS" not in brief


def _penalised_entry(unpenalised_sum: float, n_fallacies: int) -> dict:
    """The evaluator output for a fallacy-targeted unit, post-#289 (the
    #3133 fixture convention)."""
    factor = min(0.3 * n_fallacies, 0.6)
    return {
        "scores_par_vertu": {f"v{k}": unpenalised_sum / 6 for k in range(6)},
        "note_finale": unpenalised_sum * (1 - factor),
        "fallacy_penalty": {
            "applied": True,
            "fallacies": ["appel_au_peuple"] * n_fallacies,
            "penalty_factor": factor,
            "original_score": unpenalised_sum,
        },
    }


def _state_with_penalised_unit():
    state = UnifiedAnalysisState("texte")
    state.identified_arguments = {
        "arg_1": "un argument vise par un sophisme",
        "arg_strong": "un argument solide",
    }
    state.identified_fallacies = {
        "f_1": {"target_argument_id": "arg_1", "type": "appel_au_peuple"},
    }
    _write_quality_to_state(
        {
            "per_argument_scores": {
                # Unpenalised sum 1.8/6 = 30% — genuinely weak, AND
                # penalised: the R1142 head counted it as an independent
                # second method.
                "arg_1": _penalised_entry(1.8, 1),
                "arg_strong": {
                    "scores_par_vertu": {f"v{k}": 1.0 for k in range(6)},
                    "note_finale": 6.0,
                },
            }
        },
        state,
        {},
    )
    return state


class TestAPenalisedScoreIsNeverAnIndependentMethod:
    """Ask 5 — the reader-visible figure for a penalised unit is the
    penalised one, so a convergence counting it claimed independence over
    a score the same fallacy had already moved."""

    def test_a_penalised_unit_keeps_the_judgement_but_not_the_witness(self):
        out = compute_argument_convergence(_state_with_penalised_unit())
        assert [m for m, _ in out["arg_1"]["independent_signals"]] == ["sophisme"]
        assert "qualite faible" in {m for m, _ in out["arg_1"]["cited_signals"]}
        assert out["arg_1"]["score"] == 1

    def test_no_convergent_verdict_over_a_penalised_score(self):
        synthesis = build_convergent_synthesis(_state_with_penalised_unit())
        assert "arg_1" not in synthesis["convergent_verdicts"]

    def test_an_unpenalised_weak_unit_still_counts(self):
        # Control: the genuinely weak UNPENALISED unit keeps its witness —
        # the demotion reads the record, not the value.
        state = UnifiedAnalysisState("texte")
        state.identified_arguments = {
            "arg_2": "un argument faible",
            "arg_strong": "un argument solide",
        }
        state.identified_fallacies = {
            "f_1": {"target_argument_id": "arg_2", "type": "appel_au_peuple"},
        }
        _write_quality_to_state(
            {
                "per_argument_scores": {
                    "arg_2": {
                        "scores_par_vertu": {f"v{k}": 0.3 for k in range(6)},
                        "note_finale": 1.8,
                    },
                    "arg_strong": {
                        "scores_par_vertu": {f"v{k}": 1.0 for k in range(6)},
                        "note_finale": 6.0,
                    },
                }
            },
            state,
            {},
        )
        out = compute_argument_convergence(state)
        assert [m for m, _ in out["arg_2"]["independent_signals"]] == [
            "sophisme",
            "qualite faible",
        ]
