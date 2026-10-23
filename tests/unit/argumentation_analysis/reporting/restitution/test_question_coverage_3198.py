# -*- coding: utf-8 -*-
"""#3198 — an absence in the analysis is never an absence in the text.

On the R1109 doc_A pass the conclusion wrote « le texte ne montre pas de
réponse à [terme] » while Act II weighed that very reply on two units. The
writer had read only the units the pipeline carried; the absence was in THEM.

The first attempt at this issue produced a per-term coverage block and
licensed « aucune unité de l'analyse ne porte sur ce terme ». On the real state
the coordinator measured it doing the opposite of its purpose: the cap cut the
question before its operative terms, generic words earned absence licences, and
the units the issue was about (stored in the source language, against a French
question) were reachable by no token. A lexical match cannot be exact across a
language boundary, and any producer weaker than exact mints false licences.

So the producer is dropped (R1109 re-review) and the two halves that survive
are the ones that do not depend on a match:

* **writer** — an absence is ALWAYS scoped to what the analysis carried
  (« les unités analysées ici n'en portent pas la trace »), never to the text;
  the obligation to answer the Act I question is untouched;
* **check** — a new ``reading_license`` flag reads the step itself, on the
  report's own wording: a sentence that puts the absence in the text.

* witness — the issue's sentence is flagged, in French and in English.
* controls — the evidence-scoped hedge, and a sentence denying a property of
  the text rather than an absence, earn no flag; the prompt carries no absence
  licence line any more.
* mutation — dropping the check reddens the two witnesses and nothing else.

Synthetic vocabulary only (phare, fournil — no corpus content, privacy HARD).
"""

from types import SimpleNamespace

from argumentation_analysis.agents.core.synthesis.reading_license import (
    check_reading_license,
)
from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    build_act3_evidence,
    build_act3_prompt,
)

_QUESTION = "Le phare décide-t-il de l'accostage, ou le fournil y suffit-il ?"


def _state(question: str = _QUESTION):
    return SimpleNamespace(
        propositional_analysis_results=None,
        fol_analysis_results=None,
        modal_analysis_results=None,
        identified_arguments={"arg_1": "Le phare octogonal commande l'entrée."},
        identified_fallacies={},
        counter_arguments=[],
        argument_quality_scores=None,
        interpretive_question=question,
    )


def _kinds(weave: str):
    return [f["kind"] for f in check_reading_license(weave, _state())["flags"]]


class TestTheCheckReadsTheStep:
    def test_the_issue_sentence_is_flagged(self):
        """Witness — born red: nothing read the step from « these units do not
        carry it » to « the text does not say it ». This is the sentence the
        R1109 doc_A render produced."""
        weave = (
            "Le texte ne montre pas de réponse à cette objection, alors que "
            "l'analyse en pèse une."
        )
        assert "text_absence_claim" in _kinds(weave)
        flag = next(
            f
            for f in check_reading_license(weave, _state())["flags"]
            if f["kind"] == "text_absence_claim"
        )
        assert "le texte ne montre pas" in flag["measured"]["span"].lower()

    def test_the_english_form_is_flagged_too(self):
        """The writer answers in the language of the prompt it is given; the
        step is the same one."""
        weave = "The text does not show any answer to this objection."
        assert "text_absence_claim" in _kinds(weave)

    def test_a_containment_form_is_flagged(self):
        """« aucune réponse n'apparaît dans le texte » says the same thing
        without the verb of appearance the first form needs."""
        weave = "Aucune réponse à cette objection n'apparaît dans le texte."
        assert "text_absence_claim" in _kinds(weave)


class TestTheControlsStayGreen:
    def test_the_evidence_scoped_hedge_is_not_flagged(self):
        """Control — the hedge the same report used correctly: the absence is
        put on what was analysed, which is exactly what the writer can know."""
        weave = (
            "Les revendications citées ici n'en portent pas la trace nette, "
            "et le verdict doit s'en tenir là."
        )
        assert "text_absence_claim" not in _kinds(weave)

    def test_denying_a_property_of_the_text_is_not_an_absence(self):
        """Control — « le texte n'établit pas de lien causal » denies a
        property the analysis could have established; it does not claim the
        text is silent about a thing."""
        weave = "Le texte n'établit pas de lien causal entre les deux faits."
        assert "text_absence_claim" not in _kinds(weave)

    def test_a_statement_about_another_subject_is_not_flagged(self):
        """Control — the subject is what makes the claim: an honest limit
        stated about the deliberation is not a claim about the text."""
        weave = "La délibération ne montre pas de réponse unanime à cette question."
        assert "text_absence_claim" not in _kinds(weave)


class TestTheProducerIsGone:
    def test_the_prompt_carries_no_absence_licence(self):
        """Witness (R1109 re-review) — the line that licensed an absence about
        the text is gone, and so is the per-term block that produced it."""
        prompt = build_act3_prompt(build_act3_evidence(_state()))
        assert "aucune unité de l'analyse ne porte sur ce terme" not in prompt
        assert "Ce que l'analyse rattache à chaque terme" not in prompt

    def test_the_question_obligation_survives(self):
        """Anti-pendulum — removing the licence must not remove the duty to
        answer the question Act I closed on."""
        prompt = build_act3_prompt(build_act3_evidence(_state()))
        assert "y répond EXPLICITEMENT" in prompt
        assert _QUESTION in prompt

    def test_the_writer_is_bound_to_scope_every_absence(self):
        """Witness — the consigne now states the scope rule in one sentence,
        on every absence, not only on the terms of the question."""
        prompt = build_act3_prompt(build_act3_evidence(_state()))
        assert "PORTÉE D'UNE ABSENCE" in prompt
        assert "une absence dans l'analyse n'est pas une absence" in prompt
        assert "jamais que le texte ne le montre" in prompt

    def test_a_state_with_no_question_still_renders_the_honest_absence(self):
        """Control — the pre-existing silence for a state where Act I posed
        nothing is untouched."""
        prompt = build_act3_prompt(build_act3_evidence(_state("")))
        assert "aucune question interprétative n'a été posée en Acte I" in prompt
