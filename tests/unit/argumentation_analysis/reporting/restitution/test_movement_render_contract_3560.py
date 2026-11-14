"""#3560 — the render contract: carried or counted, never silently dropped.

The panel's tracer measured that every movement and every coverage-review
item reaches the Act II prompt, and between that prompt and the reader
stands the writer's discretion alone: no post-weave check verifies that
what the prompt carried was treated, and no count says how many were not.

This witness pins the contract, per the issue and the coordinator's
replay finding (14/11):

* a stubbed writer that treats ONE movement of three, and none of the
  review items, leaves a STATED DROP COUNT on the act — the counted form
  the first-reading note already uses — and the check reddens (the motif
  lands in ``degraded``; the verdict object is FAIL);
* a WRONG count reddens the same way, and the producer's line states the
  TRUE count;
* an EXACT count by the writer needs no pipeline line — the act is
  byte-identical (the drop is counted, which is the contract);
* the REVIEW ITEM channel states NO count while its measure is unproven:
  its 4-word run is language-bound (a quote in English on a French act
  never fires), so a count would be a false statement to the reader; the
  motif records the unmeasured channel. The predicate reads a bound item
  through its movement's beat, and the witness proves it TREATED when its
  unit's movement is treated — and untreated on another movement's beat,
  so the reading is not "any overlap";
* a prose that carries everything is returned byte-identical (positive
  control: the contract never fires speculatively);
* the prompt holds all three movement blocks and the item (the issue's
  positive control — the witness starts from data that is provably
  present) and teaches the counted form.

Born-red discipline: the module born in this PR
(``movement_render_contract``) is imported INSIDE its tests, so on ``main``
each witness fails on its own behaviour (no count line, no motif), not on a
collection error.

The document and its passages are made up: no corpus text, no source name.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from argumentation_analysis.agents.core.reading.coverage_review import LENS_BY_CLASS
from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
    build_act2_evidence,
    build_act2_narrative,
    build_act2_prompt,
)

# --- a synthetic document and its units ---------------------------------------

OPENING = "Speaker_A ouvre le débat sur une thèse simple."
FILLER = " ".join(
    f"Phrase de contexte numéro {index} pour installer le débat."
    for index in range(1, 31)
)
QUOTE = "Trois chiffres sur quatre appuient la mesure, sans jamais la qualifier."
CLOSING = "Le document se referme sur une question ouverte."
DOCUMENT = f"{OPENING} {FILLER} {QUOTE} {CLOSING}"
QUOTE_OFFSET = DOCUMENT.index(QUOTE)

UNITS = {
    # Three arguments, three fallacy families: three movements.
    "arg_1": "Un cas unique est monté en règle pour justifier la mesure.",
    "arg_2": "Le camp rival est disqualifié par sa personne plutôt que par ses idées.",
    "arg_3": "Deux voies seulement sont offertes à l'auditoire du débat.",
}
FALLACIES = {
    "f_1": {
        "target_argument_id": "arg_1",
        "family": "Erreur de raisonnement",
        "type": "Généralisation hâtive",
        "justification": "Un cas unique ne fonde pas une règle générale.",
    },
    "f_2": {
        "target_argument_id": "arg_2",
        "family": "Influence",
        "type": "Appel à la peur",
        "justification": "Le rival est rejeté par l'effroi plutôt que discuté.",
    },
    "f_3": {
        "target_argument_id": "arg_3",
        "family": "Tricherie",
        "type": "Faux dilemme",
        "justification": "Deux options seulement sont offertes là où il y en a d'autres.",
    },
}

#: One review item, named on a passage NO extracted unit carries — the
#: block's own material (the issue's review-item kind, the severe one at
#: cycle 10). No retained fallacy: its only anchor is its quote.
_REVIEW_ITEM = {
    "unit_id": "",
    "quote": QUOTE,
    "offset": QUOTE_OFFSET,
    "class": "statistical",
    "lens": LENS_BY_CLASS["statistical"],
    "reason": "le manquer coûterait au lecteur sa décision",
    "conclusion": "cet argument conclut par lui-même que la mesure tient",
    "rank": 1,
    "routed": {
        "lens": LENS_BY_CLASS["statistical"],
        "status": "lens_not_wired",
        "reason": "synthetic",
    },
}
_COVERAGE_REVIEW = {
    "status": "ok",
    "items": [dict(_REVIEW_ITEM)],
    "examined": 1,
    "examined_by_class": {},
    "document_chars": len(DOCUMENT),
    "dropped": {},
    "reason": "",
    "basis": "coverage_review",
}

#: Coordinator finding (14/11): a review item whose quote is ENGLISH on a
#: FRENCH act — the 4-word run is language-bound and can never witness the
#: treatment. Its unit is ``arg_2``, so the movement's beat carries it
#: whenever the prose treats that movement.
EN_QUOTE = "The timber of this argument is the analogy it keeps carrying."
_BOUND_EN_ITEM = {
    "unit_id": "arg_2",
    "quote": EN_QUOTE,
    "offset": 0,
    "class": "persuasion",
    "lens": LENS_BY_CLASS["persuasion"],
    "reason": "le passage porte l'essentiel du cadrage",
    "conclusion": "cet argument conclut que la comparaison suffit",
    "rank": 1,
    "routed": {
        "lens": LENS_BY_CLASS["persuasion"],
        "status": "lens_not_wired",
        "reason": "synthetic",
    },
}

#: Treats the SECOND movement (arg_2's) and nothing else; the bound item's
#: English quote shares no 4-word run with it, and its French conclusion is
#: not quoted either — only the movement binding can make it TREATED.
_BEAT_TWO = (
    "### Le mouvement de la peur\n\n"
    "Un appel à la peur disqualifie le rival par sa personne plutôt que par "
    "ses idées ; le procédé ferme la discussion."
)


def _state() -> SimpleNamespace:
    return SimpleNamespace(
        raw_text=DOCUMENT,
        identified_arguments=dict(UNITS),
        identified_fallacies={k: dict(v) for k, v in FALLACIES.items()},
        argument_quality_scores={},
        counter_arguments=[],
        analysis_coverage={
            "fallacy_per_argument": {"unit_ids": list(UNITS)},
        },
        coverage_review=dict(_COVERAGE_REVIEW, items=[dict(_REVIEW_ITEM)]),
    )


def _llm(text: str):
    async def _call(_prompt: str) -> str:
        return text

    return _call


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# --- the stubbed writers -------------------------------------------------------

#: Treats ONE movement of three (names its finding), none of the review
#: items, states no count: the exact shape the issue's witness asks for.
_TREAT_ONE = (
    "### Le mouvement de la généralisation\n\n"
    "Le discours ouvre sur une généralisation hâtive : un cas isolé devient "
    "la règle du récit. Le procédé raccourcit le raisonnement et la lecture "
    "reste provisoire ; le récit suit ce fil d'abord."
)

#: Same prose, with a WRONG movement count (1 measured drop is 2).
_TREAT_ONE_WRONG_COUNT = (
    _TREAT_ONE + "\n\n(1 mouvement non traité sur 3 ; 1 constat de couverture non "
    "repris sur 1.)"
)

#: Same prose, with the EXACT counts: the writer counted, the contract
#: holds, nothing is appended.
_TREAT_ONE_COUNTED = (
    _TREAT_ONE + "\n\n(2 mouvements non traités sur 3 ; 1 constat de couverture non "
    "repris sur 1.)"
)

#: Carries everything: all three movements by their finding names, and the
#: review item by its passage.
_TREAT_ALL = (
    "### Le mouvement de la généralisation\n\n"
    "Le discours ouvre sur une généralisation hâtive : un cas isolé devient "
    "la règle du récit.\n\n"
    "### Le mouvement de la peur\n\n"
    "Un appel à la peur disqualifie le rival par sa personne plutôt que par "
    "ses idées.\n\n"
    "### Le mouvement du dilemme\n\n"
    "Un faux dilemme n'offre que deux chemins à l'auditoire.\n\n"
    "### Le battement de clôture\n\n"
    "La revue de couverture relève enfin que trois chiffres sur quatre "
    "appuient la mesure, sans jamais la qualifier."
)

#: Anchor words that must NEVER appear in a motif — it carries counts only
#: (#3249): the motif is a closed producer vocabulary.
_ANCHOR_WORDS = (
    "généralisation",
    "hâtive",
    "peur",
    "dilemme",
    "chiffres sur quatre",
)


# --- the issue's positive control: the data is provably present ---------------


def test_the_prompt_holds_all_three_movements_the_item_and_the_count_rule():
    """The witness starts from data the prompt provably carries — on main
    too (the blocks pre-date this PR); the counted-form rule is the branch's
    own addition."""
    prompt = build_act2_prompt(build_act2_evidence(_state()))
    assert prompt.count("MOUVEMENT «") == 3
    for family in ("Erreur de raisonnement", "Influence", "Tricherie"):
        assert f"MOUVEMENT « {family} »" in prompt
    assert QUOTE in prompt, "the review item rides the block"
    # The branch's consigne: the counted form is taught, in the fixed
    # parseable shape the post-weave check reads back.
    assert "« N mouvements non traités sur M »" in prompt
    assert "« N constats de couverture non repris sur M »" in prompt


# --- ask 1: each movement treated or counted ----------------------------------


def test_a_writer_that_treats_one_movement_leaves_a_stated_drop_count():
    """Born red on main: the woven act carries no count there, and no check
    exists. On the branch the count line states 2 drops of 3 movements, in
    the counted form the first-reading note uses."""
    result = _run(build_act2_narrative(_state(), llm_callable=_llm(_TREAT_ONE)))

    assert result.status == "woven"
    assert "3 mouvements remis au rédacteur, 1 traité ici" in result.narrative
    assert "Compte du récit" in result.narrative


def test_the_check_reddens_when_the_count_is_missing():
    """The issue's redden condition: an item is missing AND the stated count
    is missing. The motif lands in ``degraded`` with counts only."""
    result = _run(build_act2_narrative(_state(), llm_callable=_llm(_TREAT_ONE)))

    assert "act2_render_contract" in result.degraded
    motif = result.degraded["act2_render_contract"]
    assert "2" in motif and "3" in motif, "2 movements absent of 3 handed"
    for anchor in _ANCHOR_WORDS:
        assert anchor not in motif, f"the motif quotes the act: {anchor!r}"


def test_the_check_reddens_when_the_count_is_wrong():
    """A stated count that disagrees with the measure reddens the same way,
    and the producer's line states the TRUE count beside the writer's."""
    result = _run(
        build_act2_narrative(_state(), llm_callable=_llm(_TREAT_ONE_WRONG_COUNT))
    )

    assert "act2_render_contract" in result.degraded
    assert "3 mouvements remis au rédacteur, 1 traité ici" in result.narrative


def test_an_exact_count_by_the_writer_needs_no_pipeline_line():
    """A counted drop is a measured choice, not a defect: the writer's exact
    movement count satisfies the contract and the act is byte-identical. The
    review-item channel is unmeasured (ask 2), so its note rides
    ``degraded`` — counts only, no movement defect, no pipeline count line."""
    result = _run(build_act2_narrative(_state(), llm_callable=_llm(_TREAT_ONE_COUNTED)))

    assert result.narrative == _TREAT_ONE_COUNTED
    assert "Compte du récit" not in result.narrative
    motif = result.degraded["act2_render_contract"]
    assert "mouvement absent" not in motif
    assert "mesure non éprouvée" in motif


# --- ask 2: the same contract for the review's items ---------------------------


def test_the_item_channel_states_no_count_until_its_measure_is_proven():
    """Coordinator finding (14/11), ask 2: a count the measure cannot witness
    is a false statement to the reader. The item channel is unmeasured, so the
    pipeline states NO item count (the movements' count still renders) and the
    motif records the unmeasured channel, counts only. The untreated item is
    still MEASURED as untreated — the tracer reads it, the reader is not told
    a number the measure cannot back."""
    from argumentation_analysis.reporting.restitution.movement_render_contract import (
        read_render_contract,
    )

    result = _run(build_act2_narrative(_state(), llm_callable=_llm(_TREAT_ONE)))

    assert "Compte du récit" in result.narrative, "the movements' count renders"
    assert "constat de couverture remis au rédacteur" not in result.narrative
    motif = result.degraded["act2_render_contract"]
    assert "1 constat de couverture remis au rédacteur" in motif
    assert "mesure non éprouvée" in motif, "the channel is recorded, not counted"
    reading = read_render_contract(_TREAT_ONE, build_act2_evidence(_state()), _state())
    assert reading.items_total == 1
    assert reading.items_treated == 0
    assert reading.items_measured is False


def test_a_bound_item_reads_treated_through_its_movements_beat():
    """Coordinator finding (14/11), ask 1: the quote is English, the act
    French — the 4-word run is language-bound and cannot witness the
    treatment. The item's unit (``arg_2``) is carried by a movement the prose
    treats, so that beat is the item's home (#3505): the item is TREATED.
    Red on the head before the predicate read the binding."""
    from argumentation_analysis.reporting.restitution.movement_render_contract import (
        read_render_contract,
    )

    state = _state()
    state.coverage_review = dict(_COVERAGE_REVIEW, items=[dict(_BOUND_EN_ITEM)])
    evidence = build_act2_evidence(state)

    reading = read_render_contract(_BEAT_TWO, evidence, state)
    assert reading.items_total == 1
    assert reading.items_treated == 1
    assert reading.items_untreated == 0

    # Not "any overlap": the SAME item on another movement's beat stays
    # untreated — the witness is the binding, not prose in general.
    control = read_render_contract(_TREAT_ONE, evidence, state)
    assert control.items_treated == 0


def test_a_beat_that_carries_the_items_quote_counts_as_treated():
    """The tracer's own measure: a 4-word run shared with the passage. The
    item channel is still unmeasured for COUNTING (ask 2), so the motif
    records that — but no movement drop and no count line are stated."""
    result = _run(build_act2_narrative(_state(), llm_callable=_llm(_TREAT_ALL)))

    assert "Compte du récit" not in result.narrative
    motif = result.degraded["act2_render_contract"]
    assert "mouvement absent" not in motif
    assert "mesure non éprouvée" in motif


# --- the positive control: the contract never fires speculatively --------------


def test_a_prose_that_carries_everything_is_returned_byte_identical():
    result = _run(build_act2_narrative(_state(), llm_callable=_llm(_TREAT_ALL)))

    assert result.status == "woven"
    assert result.narrative == _TREAT_ALL
    motif = result.degraded["act2_render_contract"]
    assert "mouvement absent" not in motif
    assert "mesure non éprouvée" in motif, "the channel is recorded, not counted"


# --- the verdict object, on the measure itself --------------------------------


def test_the_verdict_reddens_on_a_missing_count_and_passes_on_an_exact_one():
    """The deterministic check in isolation — the instrument the motif and
    the count line are computed from."""
    from argumentation_analysis.reporting.restitution.movement_render_contract import (
        check_render_contract,
        read_render_contract,
    )

    evidence = build_act2_evidence(_state())
    state = _state()

    missing = read_render_contract(_TREAT_ONE, evidence, state)
    assert missing.movements_total == 3
    assert missing.movements_treated == 1
    assert missing.movements_untreated == 2
    assert missing.items_total == 1
    assert missing.items_untreated == 1
    assert missing.stated_movement_drops is None
    assert check_render_contract(missing).band == "FAIL"

    wrong = read_render_contract(_TREAT_ONE_WRONG_COUNT, evidence, state)
    assert wrong.stated_movement_drops == 1
    assert check_render_contract(wrong).band == "FAIL"

    counted = read_render_contract(_TREAT_ONE_COUNTED, evidence, state)
    assert counted.stated_movement_drops == 2
    assert counted.stated_item_drops == 1
    assert check_render_contract(counted).band == "PASS"

    complete = read_render_contract(_TREAT_ALL, evidence, state)
    assert complete.movements_untreated == 0
    assert complete.items_untreated == 0
    assert check_render_contract(complete).band == "PASS"


def test_a_movement_named_by_its_theme_alone_counts_as_treated():
    """The movement's title is thematic (the consigne asks for it): naming
    the family is treating the beat, even without the finding's leaf name."""
    from argumentation_analysis.reporting.restitution.movement_render_contract import (
        read_render_contract,
    )

    prose = (
        "Le mouvement d'influence marque le second temps du texte, et le "
        "mouvement de tricherie le troisième ; la généralisation hâtive "
        "ouvre le récit, et trois chiffres sur quatre appuient la mesure "
        "pour clore."
    )
    reading = read_render_contract(prose, build_act2_evidence(_state()), _state())
    assert reading.movements_untreated == 0
    assert reading.items_untreated == 0
