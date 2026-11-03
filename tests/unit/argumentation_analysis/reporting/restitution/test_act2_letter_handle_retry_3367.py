# -*- coding: utf-8 -*-
"""#3367 — the writer's own letter handles join the #3343 bounded retry.

The #3296 relabel seam gives the WRITER per-act Greek letters with a legend;
#3317 made the gate count what the writer prints of them: a letter in the
reader's prose is a designation nobody can resolve — the legend lives in the
prompt only. The measured consequence (coordinator's paid pass R1135a) is
letters printed into the act — including doubled handles past the alphabet
(``ψψψ``, ``λλ``) — and until #3367 nothing read that count on the writer's
side: the gate filed its verdict after the fact, and the prose stayed.

The gesture is the #3343 family's third member: the letter count joins the
SINGLE bounded retry's trigger, the correction quotes the writer's own
letter-carrying sentences and restates the designation rule (designate the
unit by what it says — like the rest of the prose, the legend carries the
text — or say it at discourse level). The gate stays after, unchanged. No
deterministic strip (#3317's own calibration: a check that rewrites is a
check nobody can audit), no second retry (the bound stays ONE per act), no
``arg_N`` back (#3296), and the per-act table is untouched (#3305).

Witnesses (born red on main, where the trigger reads only superlatives and
``greek_label_sentences`` does not exist):

- a draft printing a standalone letter is asked ONCE more, and that call
  quotes the letter-carrying sentence and restates the designation rule —
  never an order to print an id or a letter;
- a clean rewrite is the retained act and the letter motive says so; a
  rewrite that is not better on the SUMMED count keeps the first draft —
  the retry can never leave the reader with worse prose;
- a retry that produces nothing keeps the first draft and says why, never
  silently;
- a CLEAN first draft costs exactly one call (the retry never fires
  speculatively), and a letter inside a « … » quotation is DATA — it never
  triggers (the citation channel, same exemption as the gate's own count);
- superlative and letters together fire ONE retry — the letter motive joins
  the same call, it does not open a second one — and both motives are filed;
- the motive is counts only, never a quote (#3249), and it is archived with
  the #2046 fabrication notes in BOTH twins, never rendered to the reader.

Synthetic vocabularies only — no corpus text, opaque ids only.
"""

import asyncio
import re
from types import SimpleNamespace

from argumentation_analysis.reporting.restitution import (
    appendix,
    pipeline_adapter,
)
from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
    build_act2_narrative,
    build_act2_retry_prompt,
)
from argumentation_analysis.reporting.restitution.readability_gate import (
    greek_label_sentences,
)


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


def _scored_state() -> SimpleNamespace:
    """Two units, both quality-scored → the #3159 ranking line exists."""
    return _state(
        identified_arguments={
            "arg_1": "Un mouvement défendu par un raisonnement causal étayé.",
            "arg_2": "Une revendication appuyée sur une comparaison continue.",
        },
        argument_quality_scores={
            "arg_1": {"overall": 4.2, "scores": {"pertinence": 3.0, "clarte": 5.0}},
            "arg_2": {"overall": 7.8, "scores": {"pertinence": 8.0, "clarte": 7.5}},
        },
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


#: A draft that prints one standalone letter handle — no superlative anywhere,
#: so on the pure-letter path only the #3317 count fires.
_LETTER_DRAFT = (
    "Premier mouvement : la comparaison continue porte le récit (β), et le "
    "second mouvement suit."
)
_CLEAN = (
    "Premier mouvement : la comparaison continue porte le récit, et le second "
    "mouvement suit."
)
#: The R1135a recorded shape: doubled handles past the 24-letter alphabet.
_DOUBLED_DRAFT = (
    "Le bilan tient en deux temps : la plainte sourde (ψψψ) et le repli " "mesuré (λλ)."
)
_WHOLE_SCOPE = "Cet appui reste le plus fragile du dispositif."
_RULE = "désigne l'unité par ce qu'elle dit"


class TestLetterSentences:
    """The instrument — standalone letter tokens, quoted spans exempt."""

    def test_a_standalone_letter_flags_its_sentence(self):
        hits = greek_label_sentences(_LETTER_DRAFT)
        assert len(hits) == 1
        assert "(β)" in hits[0]

    def test_doubled_handles_flag_like_single_ones(self):
        """The recorded R1135a shape: ``ψψψ`` is one letter run, not three."""
        assert len(greek_label_sentences(_DOUBLED_DRAFT)) == 1

    def test_a_quoted_letter_is_data_and_never_flags(self):
        quoted = "Premier mouvement : la citation porte « α » comme donnée."
        assert greek_label_sentences(quoted) == []

    def test_a_french_word_never_flags(self):
        """« bêta » is a word (letters touching word characters), not a
        token — the gate's own boundary, unchanged here."""
        prose = "La réponse est bêta et la comparaison suit."
        assert greek_label_sentences(prose) == []


class TestActTwoLetterRetry:
    """The bounded letter retry, end to end through the real builder."""

    def test_a_letter_draft_is_asked_once_with_its_own_sentence(self):
        """Born red on main: the trigger there reads only superlatives, so a
        letter-only draft costs ONE call. The correction must quote the
        flagged sentence and restate the designation rule — a retry that
        does not say what it saw is a dice roll."""
        calls = []
        llm = _two_drafts(_LETTER_DRAFT, _CLEAN, calls)
        _run(build_act2_narrative(_scored_state(), llm_callable=llm))

        assert len(calls) == 2, "exactly ONE retry, never a loop"
        assert "(β)" in calls[1], "the retry prompt quotes the flagged sentence"
        assert _RULE in calls[1], "the designation rule is restated, not assumed"

    def test_the_retry_never_orders_an_id_or_letter_print(self):
        """#3303/#3296: the correction says designate by what the unit SAYS,
        it never tells the writer to print an id or the letter."""
        calls = []
        llm = _two_drafts(_LETTER_DRAFT, _CLEAN, calls)
        _run(build_act2_narrative(_scored_state(), llm_callable=llm))

        assert not re.search(
            r"\barg_\d+\b", calls[1]
        ), "no raw id may reach the writer — the seam owns the keys"
        correction = calls[1][calls[1].index("CORRECTION DEMANDÉE") :]
        assert "N'imprime jamais la lettre seule" in correction
        assert "nomme" not in correction, (
            "the letter correction never orders a designation by name — "
            "the #3303 trap, restated for letters"
        )

    def test_clean_rewrite_wins_and_the_letter_motive_names_it(self):
        calls = []
        llm = _two_drafts(_LETTER_DRAFT, _CLEAN, calls)
        result = _run(build_act2_narrative(_scored_state(), llm_callable=llm))

        assert result.narrative == _CLEAN
        assert "β" not in result.narrative, (
            "the rewrite is the retained act — the reader never gets a "
            "handle they cannot resolve"
        )
        assert "act2_designation_letter_retry" in result.degraded
        motif = result.degraded["act2_designation_letter_retry"]
        assert "la réécriture" in motif
        assert "1" in motif and "0" in motif
        assert (
            "act2_superlative_retry" not in result.degraded
        ), "no superlative fired — its motive must not appear"

    def test_a_rewrite_that_is_not_better_keeps_the_first_draft(self):
        """Anti-regression guard on the gesture itself: a retry can never
        leave the reader with worse prose than the first draft."""
        calls = []
        llm = _two_drafts(_LETTER_DRAFT, _LETTER_DRAFT, calls)
        result = _run(build_act2_narrative(_scored_state(), llm_callable=llm))

        assert result.narrative == _LETTER_DRAFT
        motif = result.degraded["act2_designation_letter_retry"]
        assert "le premier brouillon" in motif

    def test_clean_first_draft_costs_one_call_and_no_motif(self):
        """Positive control: the retry fires on the CHECK, never
        speculatively."""
        calls = []
        llm = _two_drafts(_CLEAN, "jamais lu", calls)
        result = _run(build_act2_narrative(_scored_state(), llm_callable=llm))

        assert len(calls) == 1, "no retry unless the check fires"
        assert result.narrative == _CLEAN
        assert "act2_designation_letter_retry" not in result.degraded

    def test_a_retry_that_produces_nothing_keeps_the_first_draft(self):
        """Fail-loud on the retry too: the writer's silence is a recorded
        fact, not a reason to lose the first draft."""
        calls = []

        async def llm_callable(prompt: str) -> str:
            calls.append(prompt)
            if len(calls) == 2:
                raise RuntimeError("writer down")
            return _LETTER_DRAFT

        result = _run(build_act2_narrative(_scored_state(), llm_callable=llm_callable))

        assert len(calls) == 2
        assert result.narrative == _LETTER_DRAFT
        motif = result.degraded["act2_designation_letter_retry"]
        assert "n'a rien produit" in motif
        assert "RuntimeError" in motif, "the observed reason is recorded"

    def test_a_letter_inside_quotes_never_triggers_the_retry(self):
        """The citation channel: a letter inside « … » is quoted data, the
        same exemption the gate's own count follows (#3311/#3317)."""
        calls = []
        quoted = "Premier mouvement : la citation porte « α » comme donnée."
        llm = _two_drafts(quoted, "jamais lu", calls)
        result = _run(build_act2_narrative(_scored_state(), llm_callable=llm))

        assert len(calls) == 1
        assert "act2_designation_letter_retry" not in result.degraded

    def test_superlative_and_letters_fire_one_retry_and_file_both_motifs(self):
        """The letter motive JOINS the #3343 single retry — one call, never
        two — and each family's motive is filed under its own key."""
        calls = []
        mixed = _LETTER_DRAFT + " " + _WHOLE_SCOPE
        clean = (
            "Premier mouvement : la comparaison continue porte le récit, sans "
            "faute relevée sur l'ensemble évalué."
        )
        llm = _two_drafts(mixed, clean, calls)
        result = _run(build_act2_narrative(_scored_state(), llm_callable=llm))

        assert len(calls) == 2, "ONE retry for both motives, never a second call"
        assert "act2_superlative_retry" in result.degraded
        assert "act2_designation_letter_retry" in result.degraded
        assert "β" not in result.narrative
        assert _WHOLE_SCOPE not in result.narrative

    def test_the_motive_never_quotes_the_act(self):
        """#3249 — ``restitution_acts_degraded`` is a closed producer
        vocabulary for the sanitizer; a motif quoting the act would carry
        corpus text into it."""
        calls = []
        llm = _two_drafts(_LETTER_DRAFT, _LETTER_DRAFT, calls)
        result = _run(build_act2_narrative(_scored_state(), llm_callable=llm))

        motif = result.degraded["act2_designation_letter_retry"]
        assert _LETTER_DRAFT not in motif
        assert "β" not in motif

    def test_the_doubled_recorded_shape_fires_the_retry(self):
        """The R1135a recorded shape — doubled handles past the alphabet —
        is one flag and one retry, not a new class of defect."""
        calls = []
        llm = _two_drafts(_DOUBLED_DRAFT, _CLEAN, calls)
        result = _run(build_act2_narrative(_scored_state(), llm_callable=llm))

        assert len(calls) == 2
        assert "act2_designation_letter_retry" in result.degraded
        motif = result.degraded["act2_designation_letter_retry"]
        assert "1" in motif, "one flagged sentence, not one per letter run"

    def test_the_key_is_archived_in_both_twins(self):
        """The retry repairs the prose; it tells the reader nothing about the
        run. Both halves of the #2046 twin set must agree, or the motif
        reaches the reader as machine voice."""
        assert "act2_designation_letter_retry" in appendix._FABRICATION_NOTE_KEYS
        assert (
            "act2_designation_letter_retry" in pipeline_adapter._FABRICATION_NOTE_KEYS
        )
        assert (
            appendix._FABRICATION_NOTE_KEYS == pipeline_adapter._FABRICATION_NOTE_KEYS
        ), "the twins must stay byte-equal"


class TestRetryPrompt:
    def test_the_letter_block_keeps_the_base_prompt(self):
        """The writer must not lose its data blocks on the second pass: the
        correction is appended to the SAME prompt, never a bare re-ask."""
        from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
            build_act2_evidence,
            build_act2_prompt,
        )

        evidence = build_act2_evidence(_scored_state())
        base = build_act2_prompt(evidence)
        retried = build_act2_retry_prompt(evidence, [], letter_flagged=[_LETTER_DRAFT])
        assert retried.startswith(base)
        assert "CORRECTION DEMANDÉE" in retried[len(base) :]
        assert "(β)" in retried[len(base) :]

    def test_letters_alone_carry_the_plain_header(self):
        """When no superlative fired, the letter correction is THE
        correction — the header says so, no orphan superlative block."""
        from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
            build_act2_evidence,
        )

        evidence = build_act2_evidence(_scored_state())
        prompt = build_act2_retry_prompt(evidence, [], letter_flagged=[_LETTER_DRAFT])
        assert "AUTRE CORRECTION" not in prompt
        correction = prompt[prompt.index("CORRECTION DEMANDÉE") :]
        assert (
            "superlatif" not in correction
        ), "no superlative fired — its correction block must not appear"

    def test_both_motives_carry_their_own_blocks(self):
        from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
            build_act2_evidence,
        )

        evidence = build_act2_evidence(_scored_state())
        prompt = build_act2_retry_prompt(
            evidence, [_WHOLE_SCOPE], letter_flagged=[_LETTER_DRAFT]
        )
        assert "CORRECTION DEMANDÉE — ta rédaction ci-dessus contient" in prompt
        assert "AUTRE CORRECTION DEMANDÉE" in prompt
        assert _WHOLE_SCOPE in prompt and "(β)" in prompt

    def test_superlative_only_is_unchanged_by_this_pr(self):
        """Anti-regression on #3343: with no letters to correct, the retry
        prompt is the superlative correction and nothing else."""
        from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
            build_act2_evidence,
            build_act2_prompt,
        )

        evidence = build_act2_evidence(_scored_state())
        base = build_act2_prompt(evidence)
        retried = build_act2_retry_prompt(evidence, [_WHOLE_SCOPE])
        tail = retried[len(base) :]
        assert _WHOLE_SCOPE in tail
        assert "lettre de désignation" not in tail
