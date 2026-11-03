# -*- coding: utf-8 -*-
"""#3358 — a measured virtue is localised only on a unit the measure scored.

Paid pass R1134a: Act III's « Comment se faire son avis » justified its
advice by the discourse's two measured virtues — « car c'est là que le
discours est clair et que sa réfutation est constructive » — localising
them onto two passages. One holds both at the top band; the other was
never among the evaluated units. The reader was told the measured virtues
live in a passage the measure never read.

The census before the gesture (this seat, 103 stored Act III states): 3
sentences localise a virtue, 2 distinct shapes, the class ≈ 1/103 — and
the recorded case is a MIXED bundle. A clause drop kills the true half
with the false one; the gesture is the #3343 bounded retry, with the
per-unit virtue table in the correction — the data the base prompt never
carried (it holds the strengths discourse-level only).

R1135 return, reworked: the acceptance used to demand a raw ``arg_N`` in
the prose — a shape production never writes (0 on the stored acts) and
the readability gate forbids (#2980). The acceptance now resolves the
designation the prose actually carries: a run of >= 4 consecutive tokens
of a unit's text (measured: 0 of the census sentences resolve — the rule
clears nothing it did not measure), the correction routes its table
through the #3296 relabel seam so the writer sees letters with a legend
and never an id (#3303), and the draft comparison counts the id/letter
leaks so a rewrite that prints jargon is never « better ».

Witnesses:

- the check: the recorded shape (locative, nothing resolvable) flags; a
  unit designated BY CONTENT that holds the virtues stands untouched
  (positive control, production shape — no id in the prose); content onto
  a below-band unit or a never-scored unit flags; a named ``arg_N`` is
  still read (the synthetic path); a 3-token overlap resolves nothing
  (the 4-token bound); a discourse-level claim is the verdict's ground,
  never food; a weakness statement is not an attribution; a rejected
  virtue's vocabulary never fires (bounded by the passed set);
- the wiring (born red on main, where no check reads the act): a flagged
  conclusion triggers exactly ONE more call whose prompt carries the
  flagged sentence, the per-unit table in the writer's LETTERS with its
  legend, and no raw id anywhere (#3296 seam) nor any « nomme-la » order
  (#3303); a clean rewrite wins; a rewrite that prints an id and a letter
  while fixing its motive is REJECTED — the comparison counts the leaks;
  a rewrite that is not better keeps the first draft; the retry never
  fires speculatively on the production-shape positive control;
- the retry key is archived in BOTH #2046 twins, so the motive never
  reaches the reader as machine voice.

Synthetic vocabularies only — no corpus text, opaque ids only.
"""

import asyncio
import re
from types import SimpleNamespace

from argumentation_analysis.reporting.restitution import (
    appendix,
    pipeline_adapter,
)
from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    VIRTUE_DISPLAY_FR,
    _VIRTUE_PROSE_RE,
    build_act3_conclusion,
)
from argumentation_analysis.reporting.restitution.virtue_attribution_check import (
    content_designated_units,
    flatten_unit_scores,
    held_virtues_table,
    unbacked_localisation_sentences,
    virtue_localisation_note,
    virtue_localisation_retry_motif,
)

#: 16 distinct unit texts — a 4-token run of one is nobody else's (the
#: number alone would not separate them: digits are not letter tokens).
_UNIT_WORDS = [
    "causale", "statistique", "anecdotique", "juridique", "historique",
    "technique", "morale", "pragmatique", "empirique", "conceptuelle",
    "rhétorique", "logique", "factuelle", "normative", "comparative",
    "circconstancielle",
]
_UNIT_TEXTS = {
    f"arg_{i}": f"La réponse engage une chaîne {word} de preuves."
    for i, word in enumerate(_UNIT_WORDS, start=1)
}

#: The recorded class-shape, synthetic: the « que faire » beat justifies
#: its advice by the discourse's measured virtues, localised onto passages
#: the sentence never designates by id or content.
_RECORDED_SHAPE = (
    "Pour vous faire un avis, tenez pour plus solides la réponse de la "
    "section centrale et le raisonnement de l'annexe technique, car c'est "
    "là que le discours est clair et que sa réfutation est constructive."
)

#: The positive control in the PRODUCTION shape — no id in the prose: the
#: localised unit is designated by its own text (a 4-token run), and it
#: holds both virtues at the top band.
_HOLDS_CONTENT_SHAPE = (
    "Pour vous faire un avis, tenez pour plus solides la réponse qui "
    "engage une chaîne causale de preuves, car c'est là que le discours "
    "est clair et que sa réfutation est constructive."
)

#: The synthetic id path, kept for robustness: prose never prints an id,
#: but if one slips through it is still read and judged.
_HOLDS_ID_SHAPE = (
    "Pour vous faire un avis, tenez pour plus solides la réponse arg_1, "
    "car c'est là que le discours est clair et que sa réfutation est "
    "constructive."
)

#: A rewrite that says the same advice without localising a virtue.
_CLEAN = (
    "Pour vous faire un avis, tenez pour plus solides la réponse de la "
    "section centrale et le raisonnement de l'annexe technique, car ils "
    "portent le fil du débat sans rupture."
)

#: A rewrite that obeys the OLD correction — it names the unit by its raw
#: id and carries the letter handle: its own motive drops, but the prose
#: now leaks an id (#2980) and a letter (#3317) the reader cannot resolve.
_JARGON_REWRITE = (
    "Pour vous faire un avis, tenez pour plus solides la réponse arg_1 "
    "(β), car c'est là que le discours est clair et que sa réfutation est "
    "constructive."
)

#: Both virtues passed the discourse bar (7 of 9 evaluated units at the
#: top band — the recorded geometry, 6/8): clarte and
#: refutation_constructive are the verdict's names, nothing else.
_PASSED = ["clarte", "refutation_constructive"]

#: 9 evaluated units of 16 identified: arg_1..arg_6 and arg_13 hold both
#: virtues at 1.0; arg_7 and arg_8 sit at the instrument's « partiel »
#: (0.5); arg_16 is identified but NEVER scored — the recorded gap.
_UNIT_SCORES = {
    **{
        f"arg_{i}": {"clarte": 1.0, "refutation_constructive": 1.0} for i in range(1, 7)
    },
    "arg_7": {"clarte": 0.5, "refutation_constructive": 0.5},
    "arg_8": {"clarte": 0.5, "refutation_constructive": 0.5},
    "arg_13": {"clarte": 1.0, "refutation_constructive": 1.0},
}


class TestTheCheck:
    def test_the_recorded_shape_localises_without_a_resolvable_unit(self):
        """The locative attributes the virtues onto passages designated by
        description — nothing the state can resolve, flagged."""
        flagged = unbacked_localisation_sentences(
            _RECORDED_SHAPE, _VIRTUE_PROSE_RE, _PASSED, _UNIT_SCORES,
            unit_texts=_UNIT_TEXTS,
        )
        assert flagged == [_RECORDED_SHAPE]

    def test_a_content_designated_holder_stands_untouched(self):
        """Positive control in the PRODUCTION shape (no id in the prose):
        designating the unit by its own text and attributing a virtue it
        holds at the top band is the GOOD behavior — and the acceptance
        path the retry's legend makes reachable."""
        flagged = unbacked_localisation_sentences(
            _HOLDS_CONTENT_SHAPE, _VIRTUE_PROSE_RE, _PASSED, _UNIT_SCORES,
            unit_texts=_UNIT_TEXTS,
        )
        assert flagged == []

    def test_content_onto_a_below_band_unit_flags(self):
        """The same content designation onto arg_7 (0.5) — the measure read
        the unit and it does not hold the virtue."""
        sentence = (
            "Tenez pour plus solides la réponse qui engage une chaîne "
            "morale de preuves, car c'est là que le discours est clair "
            "et que sa réfutation est constructive."
        )
        flagged = unbacked_localisation_sentences(
            sentence, _VIRTUE_PROSE_RE, _PASSED, _UNIT_SCORES,
            unit_texts=_UNIT_TEXTS,
        )
        assert flagged == [sentence]

    def test_content_onto_a_never_scored_unit_flags(self):
        """arg_16 is identified (its text exists) but never evaluated —
        the recorded gap, reached by content."""
        sentence = (
            "Tenez pour plus solides la réponse qui engage une chaîne "
            "circconstancielle de preuves, car c'est là que le discours "
            "est clair et que sa réfutation est constructive."
        )
        flagged = unbacked_localisation_sentences(
            sentence, _VIRTUE_PROSE_RE, _PASSED, _UNIT_SCORES,
            unit_texts=_UNIT_TEXTS,
        )
        assert flagged == [sentence]

    def test_a_three_token_overlap_resolves_nothing(self):
        """The 4-token bound: « la réponse causale » repeats three tokens
        of arg_1's text and still designates nothing — flagged, like the
        recorded shape."""
        sentence = (
            "Tenez pour plus solides la réponse causale du texte, car "
            "c'est là que le discours est clair et que sa réfutation est "
            "constructive."
        )
        assert content_designated_units(sentence, _UNIT_TEXTS) == []
        flagged = unbacked_localisation_sentences(
            sentence, _VIRTUE_PROSE_RE, _PASSED, _UNIT_SCORES,
            unit_texts=_UNIT_TEXTS,
        )
        assert flagged == [sentence]

    def test_a_named_unit_that_holds_the_virtues_stands_untouched(self):
        """The synthetic id path: a named id is still read and judged —
        robustness, production prose never carries one."""
        flagged = unbacked_localisation_sentences(
            _HOLDS_ID_SHAPE, _VIRTUE_PROSE_RE, _PASSED, _UNIT_SCORES,
            unit_texts=_UNIT_TEXTS,
        )
        assert flagged == []

    def test_a_named_unit_the_measure_never_read_is_flagged(self):
        sentence = "La réponse arg_16 est claire et sa réfutation constructive."
        flagged = unbacked_localisation_sentences(
            sentence, _VIRTUE_PROSE_RE, _PASSED, _UNIT_SCORES,
            unit_texts=_UNIT_TEXTS,
        )
        assert flagged == [sentence]

    def test_a_named_unit_below_the_top_band_is_flagged(self):
        sentence = "La réponse arg_7 est claire."
        flagged = unbacked_localisation_sentences(
            sentence, _VIRTUE_PROSE_RE, _PASSED, _UNIT_SCORES,
            unit_texts=_UNIT_TEXTS,
        )
        assert flagged == [sentence]

    def test_a_mixed_bundle_flags_even_when_one_holder_passes(self):
        """The recorded case: one passage holds the virtues, its neighbour
        never read them — the bundle is only as good as its weakest unit."""
        sentence = (
            "Tenez pour plus solides les réponses arg_1 et arg_16, car "
            "c'est là que le discours est clair et que sa réfutation est "
            "constructive."
        )
        flagged = unbacked_localisation_sentences(
            sentence, _VIRTUE_PROSE_RE, _PASSED, _UNIT_SCORES,
            unit_texts=_UNIT_TEXTS,
        )
        assert flagged == [sentence]

    def test_a_discourse_level_claim_is_the_verdicts_ground(self):
        """No unit id, no locative, no content designation: the pipeline's
        verdict passage owns the claim (#3159) — never food here."""
        sentence = "Le discours est clair et sa réfutation reste constructive."
        assert (
            unbacked_localisation_sentences(
                sentence, _VIRTUE_PROSE_RE, _PASSED, _UNIT_SCORES,
                unit_texts=_UNIT_TEXTS,
            )
            == []
        )

    def test_a_weakness_statement_is_not_an_attribution(self):
        """A negation or inverse marker before the virtue word says the
        unit LACKS the virtue — the weakness half of the vocabulary."""
        assert (
            unbacked_localisation_sentences(
                "La réponse arg_7 est le point le moins clair du texte.",
                _VIRTUE_PROSE_RE,
                _PASSED,
                _UNIT_SCORES,
                unit_texts=_UNIT_TEXTS,
            )
            == []
        )
        assert (
            unbacked_localisation_sentences(
                "La réponse arg_7 manque de clarté, et sa réfutation ne tient guère.",
                _VIRTUE_PROSE_RE,
                _PASSED,
                _UNIT_SCORES,
                unit_texts=_UNIT_TEXTS,
            )
            == []
        )

    def test_a_rejected_virtues_vocabulary_never_fires(self):
        """Bounded by the passed set (#3335's calibration): an act
        discussing « les sources » when no source virtue passed is never
        touched."""
        sentence = "C'est dans le passage cité que les sources abondent."
        assert (
            unbacked_localisation_sentences(
                sentence, _VIRTUE_PROSE_RE, ["clarte"], _UNIT_SCORES,
                unit_texts=_UNIT_TEXTS,
            )
            == []
        )

    def test_an_empty_passed_set_is_silent(self):
        assert (
            unbacked_localisation_sentences(
                _RECORDED_SHAPE, _VIRTUE_PROSE_RE, [], _UNIT_SCORES,
                unit_texts=_UNIT_TEXTS,
            )
            == []
        )

    def test_the_note_names_what_was_judged_never_a_sentence(self):
        """#3249 — the note is a code literal with counts, and its wording
        says what the check READ (no measured unit at the back of the
        localisation) — never a claim the passage lacks the virtue."""
        note = virtue_localisation_note(1)
        motif = virtue_localisation_retry_motif("Acte III", 1, 0)
        for piece in (note, motif):
            assert "section centrale" not in piece
            assert "constructive" not in piece
        assert "1 localisation" in note
        assert "sans unité mesurée à l'appui" in note
        assert "la réécriture" in motif

    def test_the_table_lists_holders_with_their_scores_and_states_its_cap(self):
        table = held_virtues_table(_PASSED, _UNIT_SCORES, display=VIRTUE_DISPLAY_FR)
        assert "- arg_13 : clarté 1.0, réfutation constructive 1.0" in table
        assert "arg_7" not in table, "a below-band unit is not a holder"
        assert "arg_16" not in table, "an unscored unit is not a holder"
        wide = held_virtues_table(
            ["clarte"],
            {f"arg_{i}": {"clarte": 1.0} for i in range(1, 16)},
            cap=12,
        )
        assert "12 unités listées sur 15" in wide, "the cap is stated, never silent"

    def test_flatten_reads_the_canonical_key_and_skips_the_rest(self):
        flat = flatten_unit_scores(
            {
                "arg_1": {"overall": 4.2, "scores": {"clarte": 1.0}},
                "arg_2": {"scores_par_vertu": {"clarte": 0.5}},
                "arg_3": {"overall": 9.9},
                "arg_4": "not a dict",
            }
        )
        assert flat == {
            "arg_1": {"clarte": 1.0},
            "arg_2": {"clarte": 0.5},
        }


# --- wiring, through the real builder ----------------------------------------


def _state(**fields: object) -> SimpleNamespace:
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


def _act3_state() -> SimpleNamespace:
    """16 identified units, 9 evaluated — the recorded geometry: both
    measured virtues pass the discourse bar (7/9), arg_16 is never
    scored. The unit texts are distinct so a 4-token run designates
    exactly one unit."""
    quality = {
        arg: {"overall": 1.0, "scores": dict(scores)}
        for arg, scores in _UNIT_SCORES.items()
    }
    return _state(
        identified_arguments=dict(_UNIT_TEXTS),
        identified_fallacies={
            "fl_1": {
                "target_argument_id": "arg_1",
                "family": "ad hominem",
                "type": "ad hominem circonstanciel",
                "taxonomy_path": "racine > sophismes de pertinence > ad hominem",
                "justification": "L'argument attaque la personne plutôt que la thèse.",
            },
        },
        argument_quality_scores=quality,
        counter_arguments=[
            {
                "target_arg_id": "arg_1",
                "strategy": "contre-exemple",
                "counter_content": "On peut attaquer la thèse sans attaquer la personne.",
            }
        ],
        dung_frameworks={
            "fw_1": {
                "name": "verification_grounded",
                "arguments": ["arg_1", "arg_2"],
                "attacks": [["arg_2", "arg_1"]],
                "extensions": {"all_members": ["arg_2"]},
                "semantics": "grounded",
            }
        },
        propositional_analysis_results=[
            {"satisfiable": True},
            {"satisfiable": False},
        ],
    )


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def _two_drafts(first: str, second: str, calls=None):
    """A stub writer that answers ``first`` then ``second``; records prompts."""
    seen = []

    async def llm_callable(prompt: str) -> str:
        seen.append(prompt)
        if calls is not None:
            calls.append(prompt)
        return first if len(seen) == 1 else second

    return llm_callable


#: One per-act letter (the seam's alphabet) followed by a virtue score —
#: the table row the writer must see, post-relabel.
_LETTER_ROW = re.compile(
    r"Tableau mesuré[^\n]*\n((?:- [αβγδεζηθικλμνξοπρστυφχψω]+ : [^\n]+\n?)+)"
)


class TestTheWiring:
    def test_a_flagged_conclusion_is_asked_once_through_the_relabel_seam(self):
        """Born red on main (no check reads the act): the retry must carry
        the flagged sentence AND the per-unit table — routed through the
        #3296 seam, so the writer sees letters with a legend, never a raw
        id (#3303: and never an order to print one)."""
        calls = []
        llm = _two_drafts(_RECORDED_SHAPE, _CLEAN, calls)
        result = _run(build_act3_conclusion(_act3_state(), llm_callable=llm))

        assert len(calls) == 2, "exactly ONE retry, never a loop"
        assert _RECORDED_SHAPE in calls[1]
        assert not re.search(r"\barg_\d+\b", calls[1]), (
            "no raw unit id anywhere in the writer's retry prompt (#3296)"
        )
        assert "nomme-la" not in calls[1], "never an order to print an id (#3303)"
        rows = _LETTER_ROW.search(calls[1])
        assert rows, "the virtue table rides the prompt"
        assert "clarté 1.0" in rows.group(1), (
            "the table speaks the reader's virtue names, on letter designations"
        )
        motif = result.degraded["act3_virtue_localisation_retry"]
        assert "la réécriture" in motif
        assert (
            "act3_virtue_localisation_unbacked" not in result.degraded
        ), "the retained draft is clean — no steady-state note"
        assert "act3_superlative_retry" not in result.degraded

    def test_the_production_shape_control_costs_no_call(self):
        """Positive control, production shape (content designation, no id):
        localising on a unit that holds the virtues is the good behavior —
        the retry never fires speculatively, and the sentence reaches the
        reader untouched."""
        calls = []
        llm = _two_drafts(_HOLDS_CONTENT_SHAPE, "jamais lu", calls)
        result = _run(build_act3_conclusion(_act3_state(), llm_callable=llm))

        assert len(calls) == 1
        assert _HOLDS_CONTENT_SHAPE in result.narrative
        assert "act3_virtue_localisation_retry" not in result.degraded
        assert "act3_virtue_localisation_unbacked" not in result.degraded

    def test_a_rewrite_that_prints_jargon_is_rejected(self):
        """The draft comparison counts the readability designation leaks
        (#2980 ids + #3317 letters): this rewrite fixes its own motive by
        naming the unit with its raw id and the letter handle — prose the
        reader cannot resolve — so it is NOT better and the first draft is
        kept."""
        calls = []
        llm = _two_drafts(_RECORDED_SHAPE, _JARGON_REWRITE, calls)
        result = _run(build_act3_conclusion(_act3_state(), llm_callable=llm))

        assert len(calls) == 2
        assert _RECORDED_SHAPE in result.narrative, "the first draft is kept"
        assert _JARGON_REWRITE not in result.narrative
        motif = result.degraded["act3_virtue_localisation_retry"]
        assert "le premier brouillon" in motif
        assert "act3_virtue_localisation_unbacked" in result.degraded

    def test_a_rewrite_that_is_not_better_keeps_the_first_draft(self):
        """Anti-regression guard on the gesture itself: the retry can never
        leave the reader with worse prose than the first draft, and the
        retained draft's unbacked localisation stays recorded."""
        calls = []
        llm = _two_drafts(_RECORDED_SHAPE, _RECORDED_SHAPE, calls)
        result = _run(build_act3_conclusion(_act3_state(), llm_callable=llm))

        assert len(calls) == 2
        assert _RECORDED_SHAPE in result.narrative
        motif = result.degraded["act3_virtue_localisation_retry"]
        assert "le premier brouillon" in motif
        assert "act3_virtue_localisation_unbacked" in result.degraded

    def test_a_retry_that_produces_nothing_keeps_the_first_draft(self):
        """Fail-loud on the retry too: the writer's silence is a recorded
        fact, not a reason to lose the first draft."""
        calls = []

        async def llm_callable(prompt: str) -> str:
            calls.append(prompt)
            if len(calls) == 2:
                raise RuntimeError("writer down")
            return _RECORDED_SHAPE

        result = _run(build_act3_conclusion(_act3_state(), llm_callable=llm_callable))

        assert len(calls) == 2
        assert _RECORDED_SHAPE in result.narrative
        motif = result.degraded["act3_virtue_localisation_retry"]
        assert "n'a rien produit" in motif
        assert "RuntimeError" in motif

    def test_the_retry_key_is_archived_in_both_twins(self):
        """The retry repairs the prose; it tells the reader nothing about
        the run. Both halves of the #2046 twin set must agree."""
        for holder in (appendix, pipeline_adapter):
            assert "act3_virtue_localisation_retry" in holder._FABRICATION_NOTE_KEYS
        assert (
            appendix._FABRICATION_NOTE_KEYS == pipeline_adapter._FABRICATION_NOTE_KEYS
        ), "the twins must stay byte-equal"
