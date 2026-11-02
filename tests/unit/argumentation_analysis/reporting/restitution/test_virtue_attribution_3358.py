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

Witnesses:

- the check: the recorded shape (locative, no nameable unit) flags; a
  named unit that holds the virtues stands untouched (positive control —
  the ``arg_13`` shape of the issue); a named unit the measure never
  read, or scored below the top band, flags; a mixed bundle flags; a
  discourse-level claim is the verdict's ground, never food; a weakness
  statement (« le moins clair », « manque de clarté ») is not an
  attribution; a rejected virtue's vocabulary never fires (bounded by
  the passed set, #3335's calibration);
- the wiring (born red on main, where no check reads the act): a flagged
  conclusion triggers exactly ONE more call carrying the flagged sentence
  AND the per-unit table; a clean rewrite wins and the misattribution
  note disappears; a rewrite that is not better keeps the first draft;
  the ``arg_13`` shape costs ONE call and survives byte-identical (the
  retry never fires speculatively);
- the retry key is archived in BOTH #2046 twins, so the motive never
  reaches the reader as machine voice.

Synthetic vocabularies only — no corpus text, opaque ids only.
"""

import asyncio
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
    flatten_unit_scores,
    held_virtues_table,
    misattributed_virtue_sentences,
    virtue_attribution_note,
    virtue_attribution_retry_motif,
)

#: The recorded class-shape, synthetic: the « que faire » beat justifies
#: its advice by the discourse's measured virtues, localised onto passages
#: the sentence never names.
_RECORDED_SHAPE = (
    "Pour vous faire un avis, tenez pour plus solides la réponse de la "
    "section centrale et le raisonnement de l'annexe technique, car c'est "
    "là que le discours est clair et que sa réfutation est constructive."
)

#: The positive control — the issue's ``arg_13`` shape: same clause, but
#: the localised unit is NAMED and holds both virtues at the top band.
_HOLDS_SHAPE = (
    "Pour vous faire un avis, tenez pour plus solides la réponse arg_13, "
    "car c'est là que le discours est clair et que sa réfutation est "
    "constructive."
)

#: A rewrite that says the same advice without localising a virtue.
_CLEAN = (
    "Pour vous faire un avis, tenez pour plus solides la réponse de la "
    "section centrale et le raisonnement de l'annexe technique, car ils "
    "portent le fil du débat sans rupture."
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
    def test_the_recorded_shape_localises_without_a_nameable_unit(self):
        """The locative attributes the virtues onto passages designated by
        description — unverifiable by construction, flagged."""
        flagged = misattributed_virtue_sentences(
            _RECORDED_SHAPE, _VIRTUE_PROSE_RE, _PASSED, _UNIT_SCORES
        )
        assert flagged == [_RECORDED_SHAPE]

    def test_a_named_unit_that_holds_the_virtues_stands_untouched(self):
        """Positive control — the issue's ``arg_13`` shape: localising a
        virtue on a unit that holds it is the GOOD behavior."""
        flagged = misattributed_virtue_sentences(
            _HOLDS_SHAPE, _VIRTUE_PROSE_RE, _PASSED, _UNIT_SCORES
        )
        assert flagged == []

    def test_a_named_unit_the_measure_never_read_is_flagged(self):
        sentence = "La réponse arg_16 est claire et sa réfutation constructive."
        flagged = misattributed_virtue_sentences(
            sentence, _VIRTUE_PROSE_RE, _PASSED, _UNIT_SCORES
        )
        assert flagged == [sentence]

    def test_a_named_unit_below_the_top_band_is_flagged(self):
        sentence = "La réponse arg_7 est claire."
        flagged = misattributed_virtue_sentences(
            sentence, _VIRTUE_PROSE_RE, _PASSED, _UNIT_SCORES
        )
        assert flagged == [sentence]

    def test_a_mixed_bundle_flags_even_when_one_holder_passes(self):
        """The recorded case: one passage holds the virtues, its neighbour
        never read them — the bundle is only as good as its weakest unit."""
        sentence = (
            "Tenez pour plus solides les réponses arg_13 et arg_16, car "
            "c'est là que le discours est clair et que sa réfutation est "
            "constructive."
        )
        flagged = misattributed_virtue_sentences(
            sentence, _VIRTUE_PROSE_RE, _PASSED, _UNIT_SCORES
        )
        assert flagged == [sentence]

    def test_a_discourse_level_claim_is_the_verdicts_ground(self):
        """No unit id, no locative: the pipeline's verdict passage owns the
        claim (#3159) — never food here."""
        sentence = "Le discours est clair et sa réfutation reste constructive."
        assert (
            misattributed_virtue_sentences(
                sentence, _VIRTUE_PROSE_RE, _PASSED, _UNIT_SCORES
            )
            == []
        )

    def test_a_weakness_statement_is_not_an_attribution(self):
        """A negation or inverse marker before the virtue word says the
        unit LACKS the virtue — the weakness half of the vocabulary."""
        assert (
            misattributed_virtue_sentences(
                "La réponse arg_7 est le point le moins clair du texte.",
                _VIRTUE_PROSE_RE,
                _PASSED,
                _UNIT_SCORES,
            )
            == []
        )
        assert (
            misattributed_virtue_sentences(
                "La réponse arg_7 manque de clarté, et sa réfutation ne tient guère.",
                _VIRTUE_PROSE_RE,
                _PASSED,
                _UNIT_SCORES,
            )
            == []
        )

    def test_a_rejected_virtues_vocabulary_never_fires(self):
        """Bounded by the passed set (#3335's calibration): an act
        discussing « les sources » when no source virtue passed is never
        touched."""
        sentence = "C'est dans le passage cité que les sources abondent."
        assert (
            misattributed_virtue_sentences(
                sentence, _VIRTUE_PROSE_RE, ["clarte"], _UNIT_SCORES
            )
            == []
        )

    def test_an_empty_passed_set_is_silent(self):
        assert (
            misattributed_virtue_sentences(
                _RECORDED_SHAPE, _VIRTUE_PROSE_RE, [], _UNIT_SCORES
            )
            == []
        )

    def test_the_motifs_carry_counts_never_a_sentence(self):
        """#3249 — ``restitution_acts_degraded`` is a closed producer
        vocabulary; a motif quoting the act would carry corpus text."""
        note = virtue_attribution_note(1)
        motif = virtue_attribution_retry_motif("Acte III", 1, 0)
        for piece in (note, motif):
            assert "section centrale" not in piece
            assert "constructive" not in piece
        assert "1 attribution" in note
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
    scored."""
    identified = {
        f"arg_{i}": f"Un mouvement {i} défendu par un raisonnement causal étayé."
        for i in range(1, 17)
    }
    quality = {
        arg: {"overall": 1.0, "scores": dict(scores)}
        for arg, scores in _UNIT_SCORES.items()
    }
    return _state(
        identified_arguments=identified,
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


class TestTheWiring:
    def test_a_flagged_conclusion_is_asked_once_with_its_sentence_and_the_table(self):
        """Born red on main (no check reads the act): the retry must carry
        the flagged sentence AND the per-unit table — the data the base
        prompt never had."""
        calls = []
        llm = _two_drafts(_RECORDED_SHAPE, _CLEAN, calls)
        result = _run(build_act3_conclusion(_act3_state(), llm_callable=llm))

        assert len(calls) == 2, "exactly ONE retry, never a loop"
        assert _RECORDED_SHAPE in calls[1]
        assert "- arg_13 :" in calls[1], "the table names the holders"
        assert "clarté" in calls[1], "the table speaks the reader's virtue names"
        motif = result.degraded["act3_virtue_attribution_retry"]
        assert "la réécriture" in motif
        assert (
            "act3_virtue_misattribution" not in result.degraded
        ), "the retained draft is clean — no steady-state note"
        assert "act3_superlative_retry" not in result.degraded

    def test_the_arg13_shape_costs_one_call_and_survives(self):
        """Positive control: localising on a unit that holds the virtues is
        the good behavior — the retry never fires speculatively, and the
        sentence reaches the reader untouched."""
        calls = []
        llm = _two_drafts(_HOLDS_SHAPE, "jamais lu", calls)
        result = _run(build_act3_conclusion(_act3_state(), llm_callable=llm))

        assert len(calls) == 1
        assert _HOLDS_SHAPE in result.narrative
        assert "act3_virtue_attribution_retry" not in result.degraded
        assert "act3_virtue_misattribution" not in result.degraded

    def test_a_rewrite_that_is_not_better_keeps_the_first_draft(self):
        """Anti-regression guard on the gesture itself: the retry can never
        leave the reader with worse prose than the first draft, and the
        retained draft's misattribution stays recorded."""
        calls = []
        llm = _two_drafts(_RECORDED_SHAPE, _RECORDED_SHAPE, calls)
        result = _run(build_act3_conclusion(_act3_state(), llm_callable=llm))

        assert len(calls) == 2
        assert _RECORDED_SHAPE in result.narrative
        motif = result.degraded["act3_virtue_attribution_retry"]
        assert "le premier brouillon" in motif
        assert "act3_virtue_misattribution" in result.degraded

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
        motif = result.degraded["act3_virtue_attribution_retry"]
        assert "n'a rien produit" in motif
        assert "RuntimeError" in motif

    def test_the_retry_key_is_archived_in_both_twins(self):
        """The retry repairs the prose; it tells the reader nothing about
        the run. Both halves of the #2046 twin set must agree."""
        for holder in (appendix, pipeline_adapter):
            assert "act3_virtue_attribution_retry" in holder._FABRICATION_NOTE_KEYS
        assert (
            appendix._FABRICATION_NOTE_KEYS == pipeline_adapter._FABRICATION_NOTE_KEYS
        ), "the twins must stay byte-equal"
