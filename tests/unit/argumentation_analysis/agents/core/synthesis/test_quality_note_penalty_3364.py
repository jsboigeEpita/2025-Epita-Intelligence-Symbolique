"""#3364 — the quality note's maximum ranks one measure, not two.

``argument_quality_scores[arg]["overall"]`` is the fallacy-ADJUSTED sum
(#289); a penalised entry also carries the #3133 record
(``fallacy_penalty`` with ``original_score``). When a population mixes
penalised and plain entries, the ``POPULATIONS`` note took its maximum over
both quantities at once: a unit penalised down to 1.8 competed with a unit
that genuinely scored 1.8, and the note crowned the wrong holder — the very
comparison the per-unit line forbids (#3357: « score penalise, non
comparable aux scores sans penalite »).

The repair reads the unpenalised measure for penalised entries (``overall``
for the rest), so every unit competes on one quantity, and the note's label
names that quantity (« mesure hors penalite »). A population with no applied
penalty keeps the line byte-identical (``max overall over all = …``), and the
two other ``_max_over_population`` call sites — ``counter_arguments``,
``convergent_verdicts`` — are untouched.

Deterministic — no JVM, no LLM, no network.
"""

from __future__ import annotations

from types import SimpleNamespace

from argumentation_analysis.agents.core.synthesis.deep_synthesis_agent import (
    DeepSynthesisAgent,
)


def _state(**fields) -> SimpleNamespace:
    base = dict(
        identified_arguments={},
        identified_fallacies={},
        counter_arguments=[],
        argument_quality_scores={},
        propositional_analysis_results=[],
        fol_analysis_results=[],
        modal_analysis_results=[],
        dung_frameworks={},
        jtms_retraction_chain=[],
        belief_revision_results=[],
    )
    base.update(fields)
    return SimpleNamespace(**base)


def _briefing(state, report=None) -> str:
    return DeepSynthesisAgent.build_artifact_briefing(state, report)


def _penalty(original: float, applied: bool = True) -> dict:
    return {
        "applied": applied,
        "original_score": original,
        "penalty_factor": 0.4,
        "fallacies": ["slippery_slope", "ad_populum"],
    }


#: 39 plain entries with distinct scores topping at 2.5 (arg_39); the
#: population is beyond the cap (15), so the note exists.
def _plain_quality(top: float = 2.5) -> dict:
    quality = {f"arg_{i}": {"overall": 1.0 + 0.01 * i} for i in range(1, 39)}
    quality["arg_39"] = {"overall": top}
    return quality


# ============================================================================
# The measured defect — a mixed population crowned the wrong unit
# ============================================================================


class TestAMixedPopulationRanksOneMeasure:
    def test_a_penalised_unit_tops_the_note_on_its_measure(self):
        """arg_40 was measured 4.5 and penalised to 1.8; arg_39 plainly
        holds 2.5. The parent crowned arg_39 (« max overall ») and the note
        hid arg_40's measure entirely."""
        quality = _plain_quality()
        quality["arg_40"] = {
            "overall": 1.8,
            "fallacy_penalty": _penalty(4.5),
        }
        briefing = _briefing(_state(argument_quality_scores=quality))

        assert "argument_quality_scores: 15 of 40 shown" in briefing
        assert "max mesure hors penalite over all = 4.5 (arg_40)" in briefing
        assert "max overall over all" not in briefing

    def test_a_tie_across_the_two_kinds_names_both_holders(self):
        """A plain 4.5 and a penalised unit measured 4.5 hold the same
        maximum once both rank on the measure — the tie line then names
        every holder (#3329), which the parent's mixed maximum could not
        even see."""
        quality = _plain_quality(top=4.5)
        quality["arg_40"] = {
            "overall": 1.8,
            "fallacy_penalty": _penalty(4.5),
        }
        briefing = _briefing(_state(argument_quality_scores=quality))

        assert (
            "max mesure hors penalite over all = 4.5, tied: arg_39, arg_40" in briefing
        )

    def test_an_all_penalised_population_ranks_on_the_measure(self):
        """Homogeneous penalised population: the measure to rank on is the
        recorded one, and the label says so — the parent ranked the
        penalised sums and crowned arg_1."""
        quality = {
            f"arg_{i}": {
                "overall": 2.0 - 0.001 * i,
                "fallacy_penalty": _penalty(4.0 + 0.01 * i),
            }
            for i in range(1, 40)
        }
        briefing = _briefing(_state(argument_quality_scores=quality))

        assert "max mesure hors penalite over all = 4.39 (arg_39)" in briefing


# ============================================================================
# Controls — what must NOT change
# ============================================================================


class TestTheControls:
    def test_a_pure_population_is_byte_identical(self):
        """Control (DoD): no applied penalty anywhere ⇒ the note keeps the
        pre-#3364 spelling, byte for byte."""
        briefing = _briefing(_state(argument_quality_scores=_plain_quality()))

        assert "max overall over all = 2.5 (arg_39)" in briefing
        assert "mesure hors penalite" not in briefing

    def test_an_unapplied_penalty_record_is_treated_as_plain(self):
        """A recorded-but-unapplied penalty (#3133) does not switch the
        measure: the entry's ``overall`` is its measure, recorded or not."""
        quality = _plain_quality()
        quality["arg_20"] = {
            "overall": 1.19,
            "fallacy_penalty": _penalty(9.9, applied=False),
        }
        briefing = _briefing(_state(argument_quality_scores=quality))

        assert "max overall over all = 2.5 (arg_39)" in briefing
        assert "9.9" not in briefing
        assert "mesure hors penalite" not in briefing

    def test_a_penalised_entry_without_original_score_stays_in_the_maximum(self):
        """Edge: applied penalty with no readable ``original_score`` — the
        unit falls back to its own ``overall`` rather than vanishing from
        the population (#3155 said the maximum is over ALL items): dropped,
        the maximum would fall back to arg_39's 2.5."""
        quality = _plain_quality()
        quality["arg_40"] = {
            "overall": 2.6,
            "fallacy_penalty": {"applied": True, "penalty_factor": 0.4},
        }
        briefing = _briefing(_state(argument_quality_scores=quality))

        assert "max mesure hors penalite over all = 2.6 (arg_40)" in briefing

    def test_the_counter_arguments_note_is_untouched(self):
        """Control: the sibling call site (``counter_arguments``) does not
        carry penalty records and its line keeps its spelling."""
        counters = [
            {
                "id": f"ca_{i}",
                "strategy": "direct_refutation",
                "score": 0.4,
                "counter_content": f"contre-argument {i}",
            }
            for i in range(1, 41)
        ]
        counters[21]["score"] = 0.59  # ca_22
        counters[37]["score"] = 0.59  # ca_38
        briefing = _briefing(_state(counter_arguments=counters))

        assert "max score over all = 0.59, tied: ca_22, ca_38" in briefing
        assert "mesure hors penalite" not in briefing
