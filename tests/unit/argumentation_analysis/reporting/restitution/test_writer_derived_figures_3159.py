"""#3159 — the summary figures are written by the producer, not derived by the writer.

Three instances of one class, all measured on R1107 with 0 LLM calls: the
producer hands the writer correct figures and the writer **derives** a summary
that the record contradicts.

1. Act I — the coverage range. Phases at 6..15 (stakes 30 apart), the render
   said « from 8 to 10 ». The producer now writes « de 6 à 15 unités ».
2. Act III — the discourse-level virtue statement. #3137 shipped it as a RULE
   for the writer; the first post-#3143 render broke it (clarté at 4/8 said
   « generally clear », no base). The rule is gone, the producer writes the
   sentence with its base.
3. Act II — the quality ranking. « Le mieux tenu de tout le discours » was said
   of ``arg_14`` while ``arg_69`` ranked above it, on 8 scored units of 90. The
   ranking and its base now travel in the prompt, and the governance line says
   what the vote ranked.

Fixtures reproduce the doc_B and doc_A shapes (opaque ids, synthetic counts).
Deterministic — no JVM, no LLM, no network.
"""

from __future__ import annotations

from types import SimpleNamespace

from argumentation_analysis.reporting.restitution.act1_framing_plugin import (
    build_act1_evidence,
    build_act1_prompt,
)
from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
    build_act2_evidence,
    build_act2_prompt,
    quality_ranking_line,
)
from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    QualityStrength,
    build_act3_evidence,
    build_act3_prompt,
    discourse_virtue_sentence,
)

# --- Act I: the doc_B coverage map ------------------------------------------


def _doc_b_coverage() -> dict:
    return {
        "debate": {"k": 6, "N": 90},
        "governance": {"k": 6, "N": 90},
        "nl_to_logic": {"k": 6, "N": 90},
        "quality": {"k": 8, "N": 90},
        "atms": {"k": 8, "N": 90},
        "counter": {"k": 10, "N": 90},
        "fallacy": {"k": 10, "N": 90},
        "fol": {"k": 10, "N": 90},
        "pl": {"k": 10, "N": 90},
        "jtms": {"k": 10, "N": 90},
        "synthesis": {"k": 15, "N": 90},
        "stakes": {"k": 30, "N": 90},
    }


def _state(**fields) -> SimpleNamespace:
    base = dict(
        source_metadata={},
        stakes_and_stakeholders={
            "stakes": [],
            "stakeholders": [],
            "rhetorical_register": "",
            "discursive_arena": "",
        },
        identified_arguments={},
    )
    base.update(fields)
    return SimpleNamespace(**base)


class TestAct1CoverageRange:
    def test_the_prompt_carries_the_precomputed_range(self):
        prompt = build_act1_prompt(
            build_act1_evidence(_state(analysis_coverage=_doc_b_coverage()))
        )
        assert "de 6 à 15 unités" in prompt
        assert "Les enjeux, comptés à part : 30" in prompt

    def test_a_uniform_coverage_yields_a_single_figure(self):
        uniform = {p: {"k": 10, "N": 90} for p in ("debate", "quality", "pl")}
        prompt = build_act1_prompt(
            build_act1_evidence(_state(analysis_coverage=uniform))
        )
        assert "10 unités dans chaque module" in prompt
        assert "de 10 à 10" not in prompt

    def test_no_coverage_map_means_no_sentence(self):
        prompt = build_act1_prompt(build_act1_evidence(_state()))
        assert "Couverture :" not in prompt


# --- Act III: the discourse-level virtue statement ---------------------------

_CLARTE = "clarte"
_REDONDANCE = "redondance_faible"


def _doc_b_quality() -> dict:
    """8 evaluated units: redondance_faible at top on 7, clarté at top on 4."""
    quality = {}
    for i in range(8):
        scores = {_CLARTE: 1.0 if i < 4 else 0.5, _REDONDANCE: 1.0 if i < 7 else 0.5}
        quality[f"arg_{i}"] = {"scores": scores, "overall": 9.0}
    return quality


class TestAct3DiscourseVirtue:
    def test_the_sentence_names_the_virtue_that_passes_and_not_the_one_that_fails(
        self,
    ):
        evidence = build_act3_evidence(
            _state(
                argument_quality_scores=_doc_b_quality(),
                identified_arguments={f"arg_{i}": f"unité {i}" for i in range(8)},
            )
        )
        prompt = build_act3_prompt(evidence)
        start = prompt.index("VERDICT PRÉ-CALCULÉ")
        sentence = prompt[start : prompt.index("Aucune autre vertu", start)]
        assert _REDONDANCE in sentence
        assert "7/8 arguments évalués" in sentence
        assert (
            _CLARTE not in sentence
        ), "clarté at 4/8 must not be said of the discourse"

    def test_no_virtue_at_the_bar_says_so_plainly(self):
        sentence = discourse_virtue_sentence(
            [
                QualityStrength(
                    virtue=_CLARTE,
                    score=1.0,
                    args_at_top=4,
                    args_evaluated=8,
                    units_total=8,
                )
            ]
        )
        assert "aucune vertu n'atteint 3/4" in sentence
        assert "Le discours tient sur" not in sentence

    def test_the_bar_is_a_three_quarters_share(self):
        def _s(top: int) -> str:
            return discourse_virtue_sentence(
                [
                    QualityStrength(
                        virtue="x",
                        score=1.0,
                        args_at_top=top,
                        args_evaluated=8,
                        units_total=8,
                    )
                ]
            )

        assert "Le discours tient sur" not in _s(5)  # 5/8 < 3/4
        assert "Le discours tient sur" in _s(6)  # 6/8 == 3/4


# --- Act II: the measured quality ranking ------------------------------------


def _doc_a_quality() -> dict:
    quality = {
        "arg_69": {"overall": 5.0},
        "arg_14": {"overall": 4.5},
        "arg_28": {"overall": 4.5},
    }
    for i in range(5):
        quality[f"arg_{100 + i}"] = {"overall": 2.0}
    return quality


class TestAct2QualityRanking:
    def test_the_ranking_puts_the_top_unit_first_with_its_base(self):
        line = quality_ranking_line(_doc_a_quality(), 90)
        assert line.startswith("Classement qualité (base : 8 unités évaluées sur 90)")
        assert line.index("arg_69 (5.0)") < line.index("arg_14 (4.5)")

    def test_the_prompt_carries_the_ranking(self):
        state = _state(
            identified_arguments={f"arg_{i}": f"unité {i}" for i in range(90)},
            argument_quality_scores=_doc_a_quality(),
        )
        prompt = build_act2_prompt(build_act2_evidence(state))
        assert "Classement qualité (base : 8 unités évaluées sur 90)" in prompt
        assert "arg_69 (5.0)" in prompt

    def test_no_scored_unit_means_no_line(self):
        assert quality_ranking_line({}, 90) == ""
        assert quality_ranking_line({"arg_1": {}}, 90) == ""
