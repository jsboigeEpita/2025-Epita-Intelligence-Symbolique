"""#3335 — the Act III virtue verdict is rendered by the pipeline, never by the prose.

Since #3319 removed the « » around the pre-computed verdict, the writer stopped
copying that sentence and started PARAPHRASING it. Paid passes R1130a, R1131a
and R1132a all lost the measured base on the way:

    handed over : Le discours tient sur réfutation constructive (7/8 arguments
                  évalués, 89 unités) ; … Aucune autre vertu ne se dit du discours.
    printed     : Le discours a de vraies qualités : il réfute de façon
                  constructive, ne se répète guère et reste pertinent.

R1131a added « surtout » and « souvent » on top, which nothing measures. A
« reprends-le tel quel » instruction with no post-generation check is exactly
the #3134 shape: an instruction the writer can ignore is not a guarantee.

The repair is #3182's, applied to the verdict. The passing branch of
``discourse_virtue_sentence`` now returns the READER sentence; the prompt says
the pipeline renders it under the verdict heading and asks the writer to
restate none of it; and the assembly removes a woven restatement — the
paraphrase or the verbatim copy — before grafting the pipeline's passage after
the prose. What is removed is recorded in the state with counts, never the
sentence (#3249), under the #2046 fabrication-note keys.

The absent branch is untouched (the DoD's positive control): when no virtue
reaches the bar there is no reader sentence to print, and the writer keeps the
coding instruction.

Everything here is offline: an injectable async LLM stub, real
``UnifiedAnalysisState`` objects, no JVM, no network, no paid call.

Born-red note: every symbol imported at module level already exists on the
father, so the father COLLECTS and these redden on their assertions (the
verdict heading and sentence are spelled out as literals here rather than
imported — the rendering is the contract, not the constant's name; #1647).
"""

from __future__ import annotations

import asyncio

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    QualityStrength,
    build_act3_conclusion,
    build_act3_evidence,
    build_act3_prompt,
    discourse_virtue_sentence,
)

_SOURCE_CHARS = 12_000

#: The three virtues the paid pass crowned, above the bar (#3335). The prose
#: below speaks them in their VERBAL forms — « réfute », « se répète »,
#: « pertinent » — never in their display labels.
_VIRTUES = ("pertinence", "refutation_constructive", "redondance_faible")

#: The sentence the pipeline hands the reader for ``_state()``: the three
#: crowned virtues, each with its measured base. Spelled out, because this is
#: what the DoD asks to find byte-for-byte in the render.
_VERDICT = (
    "Le discours tient sur pertinence (7/8 arguments évalués — barre : 3/4 des arguments évalués, 2 unités) ; "
    "réfutation constructive (7/8 arguments évalués — barre : 3/4 des arguments évalués, 2 unités) ; "
    "faible redondance (7/8 arguments évalués — barre : 3/4 des arguments évalués, 2 unités). "
    "Aucune autre vertu ne se dit du discours."
)

#: The heading the grafted passage carries, so the reader knows whose figures
#: these are.
_VERDICT_HEADING = "Verdict sur les vertus (chiffres du pipeline)"

#: R1132a's shape, synthetic (model prose, no corpus sentence): the paraphrase
#: and the pipeline's own closing clause, in one beat.
_WOVEN_R1132 = (
    "### Ce que le discours dit vraiment\n\n"
    "Le locuteur défend une lecture ordonnée de ses engagements.\n\n"
    "### Ce qui tient et ce qui ne tient pas\n\n"
    "Le discours a de vraies qualités : il réfute de façon constructive, "
    "ne se répète guère et reste pertinent. Aucune autre vertu ne s'en dit.\n\n"
    "### Comment se faire son avis\n\n"
    "Le lecteur doit recevoir avec prudence ce qui n'est pas étayé.\n"
)

#: R1131a's shape: the two quantifiers nothing measures, then the clause.
_WOVEN_R1131 = (
    "### Ce qui tient\n\n"
    "Le discours tient surtout par sa pertinence et sa réfutation constructive : "
    "il répond souvent point par point. Aucune autre vertu ne se dit de lui.\n\n"
    "### Comment se faire son avis\n\n"
    "Le lecteur garde en tête ce qui reste à vérifier.\n"
)


def _stub_llm(text: str):
    async def _call(_prompt: str) -> str:
        return text

    return _call


def _state(top_holders: int = 7, evaluated: int = 8) -> UnifiedAnalysisState:
    """A state whose quality pass crowns `_VIRTUES` on `top_holders`/`evaluated`."""
    state = UnifiedAnalysisState("x" * _SOURCE_CHARS)
    state.add_argument("Le locuteur disqualifie l'adversaire.")
    state.add_argument("Une revendication défendue par un raisonnement causal.")
    quality = {}
    for i in range(1, evaluated + 1):
        top = 1.0 if i <= top_holders else 0.2
        quality[f"arg_{i}"] = {"scores": {virtue: top for virtue in _VIRTUES}}
    state.argument_quality_scores = quality
    return state


def _act3(woven: str, state: UnifiedAnalysisState):
    return asyncio.run(build_act3_conclusion(state, llm_callable=_stub_llm(woven)))


class TestThePipelineRendersTheVerdict:
    def test_the_rendered_act3_carries_the_verdict_byte_for_byte(self):
        """The DoD's preferred branch: the pre-computed sentence reaches the
        reader exactly, base included."""
        result = _act3(_WOVEN_R1132, _state())
        assert _VERDICT in result.narrative, result.narrative

    def test_the_paraphrase_and_its_closing_clause_are_removed(self):
        result = _act3(_WOVEN_R1132, _state())
        assert "de vraies qualités" not in result.narrative, result.narrative
        assert "Aucune autre vertu ne s'en dit" not in result.narrative
        # Everything else the writer said survives.
        assert "Le locuteur défend une lecture ordonnée" in result.narrative
        assert "Le lecteur doit recevoir avec prudence" in result.narrative

    def test_the_added_quantifiers_do_not_survive_the_removal(self):
        """R1131a: « surtout » and « souvent » are the writer's own addition —
        they leave with the sentence that carried them."""
        result = _act3(_WOVEN_R1131, _state())
        assert "surtout" not in result.narrative, result.narrative
        assert "souvent" not in result.narrative, result.narrative
        assert _VERDICT in result.narrative

    def test_the_statement_is_recorded_with_counts_never_the_sentence(self):
        """#3249 — a motive is a code literal: act, motive, count."""
        result = _act3(_WOVEN_R1132, _state())
        motif = result.degraded["act3_verdict_restatement"]
        assert "2" in motif
        assert "de vraies qualités" not in motif
        assert "réfute" not in motif

    def test_an_emptied_beat_does_not_keep_a_heading_over_nothing(self):
        """The beat whose whole prose WAS the verdict must not leave a heading
        the reader scrolls past to find nothing."""
        result = _act3(_WOVEN_R1132, _state())
        assert "### Ce qui tient et ce qui ne tient pas" not in result.narrative
        assert "### Comment se faire son avis" in result.narrative

    def test_the_grafted_passage_says_whose_figures_they_are(self):
        result = _act3(_WOVEN_R1132, _state())
        assert f"**{_VERDICT_HEADING}**" in result.narrative


class TestThePromptStopsAskingForACopy:
    def test_the_prompt_hands_the_verdict_as_the_pipeline_rendering(self):
        prompt = build_act3_prompt(build_act3_evidence(_state()))
        assert _VERDICT in prompt
        assert _VERDICT_HEADING in prompt
        assert "ne le reformule" in prompt

    def test_the_copy_instruction_is_gone(self):
        """#3319's instruction told the writer to copy a sentence nothing
        checked. The sentence is not copied at all now — the instruction has
        nothing left to say."""
        prompt = build_act3_prompt(build_act3_evidence(_state()))
        assert "reprends-le tel quel" not in prompt
        assert "sans guillemets" not in prompt
        assert "VERDICT PRÉ-CALCULÉ" not in prompt

    def test_the_sentence_handed_to_the_writer_is_the_reader_sentence(self):
        """The producer hands over what the reader will see — bare, no
        instruction prefix riding the sentence (#3159/#3319 substance)."""
        sentence = discourse_virtue_sentence(
            build_act3_evidence(_state()).quality_strengths
        )
        assert sentence == _VERDICT

    def test_the_single_virtue_case_keeps_its_base(self):
        sentence = discourse_virtue_sentence(
            [
                QualityStrength(
                    virtue="redondance_faible",
                    score=1.0,
                    args_at_top=6,
                    args_evaluated=7,
                    units_total=35,
                )
            ]
        )
        assert "«" not in sentence and "»" not in sentence, sentence
        assert sentence.startswith("Le discours tient sur faible redondance ")
        assert "(6/7 arguments évalués — barre : 3/4 des arguments évalués, 35 unités)" in sentence


class TestTheAbsentBranchIsUntouched:
    """The DoD's positive control: no virtue reaches the bar → no graft, no
    removal, and the writer keeps the coding instruction."""

    def test_nothing_is_grafted_when_no_virtue_reaches_the_bar(self):
        result = _act3(_WOVEN_R1132, _state(top_holders=2))
        assert _VERDICT_HEADING not in result.narrative
        assert "act3_verdict_restatement" not in result.degraded
        # The writer's own prose is left exactly as woven.
        assert "Le discours a de vraies qualités" in result.narrative

    def test_the_prompt_keeps_the_absence_instruction(self):
        prompt = build_act3_prompt(build_act3_evidence(_state(top_holders=2)))
        assert "aucune vertu n'atteint 3/4" in prompt
        assert _VERDICT_HEADING not in prompt


class TestTheDetectionIsBounded:
    """The detector is anchored on the pipeline's closing clause and walks back
    only over sentences that name a virtue above the bar. A sentence naming SOME
    of the crowned virtues but never closed by that clause is prose the writer
    owes the reader — removing it would be the repair eating the report.
    (#3348 tightened the other edge: naming EVERY passed virtue and no rejected
    one, discourse as subject, IS the verdict restated and is removed — the
    clause-less cases live in test_woven_verdict_without_closing_3348.py.)"""

    def test_a_virtue_sentence_without_the_clause_survives(self):
        woven = (
            "### Ce qui tient\n\n"
            "Le discours a de vraies qualités : il réfute de façon constructive "
            "et reste pertinent.\n\n"
            "### Comment se faire son avis\n\n"
            "Le lecteur préservera ce qui reste pertinent et bien structuré.\n"
        )
        result = _act3(woven, _state())
        assert "de vraies qualités" in result.narrative, result.narrative
        assert "Le lecteur préservera ce qui reste pertinent" in result.narrative
        assert _VERDICT in result.narrative

    def test_a_recommendation_naming_the_same_virtues_survives(self):
        woven = (
            "### Ce qui tient\n\n"
            "Le discours a de vraies qualités : il réfute de façon constructive, "
            "ne se répète guère et reste pertinent. Aucune autre vertu ne s'en dit.\n\n"
            "### Comment se faire son avis\n\n"
            "Le lecteur préservera ce qui reste pertinent et bien structuré.\n"
        )
        result = _act3(woven, _state())
        assert "Le lecteur préservera ce qui reste pertinent" in result.narrative
        assert "de vraies qualités" not in result.narrative
