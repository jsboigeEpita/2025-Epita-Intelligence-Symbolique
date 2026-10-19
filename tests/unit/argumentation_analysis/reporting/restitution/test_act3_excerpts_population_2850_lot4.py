"""#2850 lot 4 — Act III's excerpt list names the population it was cut from.

Two census rows of ``act3_conclusion_plugin.py`` fed the writer prompt from
a capped selection and said nothing: ``cited_args[:_MAX_CLAIM_EXCERPTS]``
(:2234) and the dict-head fill ``args[:_MAX_CLAIM_EXCERPTS]`` (:2237).
Measured shape behind both: Act III cites 14 units on a real run and hands
the writer five — the #1622 idiom (the counters list, :2491-2507) already
established that a capped enumeration reaching a writer must say it is
capped, because the writer otherwise writes as if the list were complete.

Disposition per row:

* the citation cap keeps its budget (5, unchanged — the disclosure is what
  is owed, not a wider selection: anti-pendulum) and the prompt now carries
  ``claim_excerpts_total`` — the citable population (citations plus the
  dict's remaining units, distinct);
* the dict-head fill stops being a second cap: it draws from the FULL dict
  and takes only what the citations leave unused, so the population named
  in the prompt IS the population the one remaining cap applied to.

Measured equivalence: with citations first and the head only topping up
unused budget, the selected set and its ORDER are identical before and
after the rewrite (the old ``args[:5]`` slice could never be exhausted
before the budget was, since at most ``len(cited_args)`` of its five
entries were already cited).

Privacy: invented filler, opaque ids. Deterministic: no JVM, no LLM.
"""

from __future__ import annotations

from types import SimpleNamespace

from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    _MAX_CLAIM_EXCERPTS,
    build_act3_evidence,
    build_act3_prompt,
)


def _state(**fields) -> SimpleNamespace:
    base = dict(
        identified_arguments={},
        identified_fallacies={},
        argument_quality_scores={},
        counter_arguments=[],
        dung_frameworks={},
        fol_analysis_results=[],
        propositional_analysis_results=[],
        modal_analysis_results=[],
        narrative_synthesis="",
        governance_decisions=[],
        debate_transcripts=[],
    )
    base.update(fields)
    return SimpleNamespace(**base)


def _seven_units_two_cited() -> SimpleNamespace:
    """Seven units; the citations (winner + counter target) sit at arg_6 and
    arg_7 — outside the first five in insertion order, the measured shape."""
    return _state(
        identified_arguments={
            "arg_1": "Première unité d'ouverture, jamais citée.",
            "arg_2": "Deuxième unité d'ouverture sans citation.",
            "arg_3": "Troisième unité d'ouverture sans citation.",
            "arg_4": "Quatrième unité d'ouverture sans citation.",
            "arg_5": "Cinquième unité d'ouverture sans citation.",
            "arg_6": "Le lauréat du vote affirme une doctrine du contrôle local.",
            "arg_7": "Une unité contestée visée par un contre-argument.",
        },
        counter_arguments=[
            {
                "target_arg_id": "arg_7",
                "counter_content": "Le contre-argument synthétique.",
            }
        ],
        governance_decisions=[
            {
                "method": "vote_borda",
                "winner": "arg_6",
                "scores": {"arg_6": 12, "arg_7": 8},
            }
        ],
    )


def _three_units_all_reachable() -> SimpleNamespace:
    """Three units, one cited: the whole population fits under the cap."""
    return _state(
        identified_arguments={
            "arg_1": "Première unité, mesurée.",
            "arg_2": "Deuxième unité, lauréate du vote.",
            "arg_3": "Troisième unité, mesurée.",
        },
        governance_decisions=[
            {"method": "vote_borda", "winner": "arg_2", "scores": {"arg_2": 9}}
        ],
    )


class TestTheExcerptPopulationIsNamed:
    def test_evidence_carries_the_citable_population(self) -> None:
        evidence = build_act3_evidence(_seven_units_two_cited())
        assert len(evidence.claim_excerpts) == _MAX_CLAIM_EXCERPTS
        assert evidence.claim_excerpts_total == 7, (
            "the writer gets %d of the %d units the selection could have "
            "listed — the evidence must carry the denominator, exactly as "
            "counters_total does for the #1622 notice" % (_MAX_CLAIM_EXCERPTS, 7)
        )

    def test_prompt_says_the_list_is_truncated(self) -> None:
        prompt = build_act3_prompt(build_act3_evidence(_seven_units_two_cited()))
        assert "liste tronquée" in prompt, (
            "the only place the writer sees the excerpt list must say it is "
            "capped, or the conclusion writes as if it were exhaustive "
            "(#1622 idiom)"
        )
        assert f"{_MAX_CLAIM_EXCERPTS} revendications listées sur 7" in prompt
        assert "non énumérées ici" in prompt

    def test_no_notice_when_the_population_fits(self) -> None:
        evidence = build_act3_evidence(_three_units_all_reachable())
        prompt = build_act3_prompt(evidence)
        assert len(evidence.claim_excerpts) == 3
        assert evidence.claim_excerpts_total == 3
        assert (
            "liste tronquée" not in prompt
        ), "a run below the cap drops nothing — no false alarm"

    def test_selection_is_unchanged_by_the_population_rewrite(self) -> None:
        """The budget still wins: the citations come first, the dict head
        fills only what they leave unused — arg_1..arg_3 here."""
        evidence = build_act3_evidence(_seven_units_two_cited())
        ids = [unit_id for unit_id, _text in evidence.claim_excerpts]
        assert ids[:2] == ["arg_6", "arg_7"], ids
        assert ids[2:] == ["arg_1", "arg_2", "arg_3"], ids
        prompt = build_act3_prompt(evidence)
        assert "doctrine du contrôle local" in prompt  # the winner's own text
