# -*- coding: utf-8 -*-
"""#3343 — the bounded writer retry on a whole-scope superlative.

#3297 built the instrument (the check records an unbacked whole-scope
superlative) and deliberately refused to rewrite the prose: a check that
rewrites is a check nobody can audit. The measured consequence, on the
coordinator's paid passes, is that the reader still receives the claim — 2 of
5 passes for Act II. #3159 had already given the writer the ranking and the
rule; the writer broke it anyway.

The gesture here is the third option between « record » and « delete the
sentence »: ask the WRITER once, with its own flagged sentences and the
measured ranking, to rewrite its own prose. Bounded by construction — one
call, never a loop — and the check still only records.

Witnesses (born red on main, where ``build_act2_retry_prompt`` does not
exist and the first draft is the only draft):

- a flagged first draft triggers exactly ONE more call, and that call carries
  the flagged sentence AND the measured base — the writer is told what it did
  and what it has to stand on;
- a clean rewrite is the retained act and the superlative motive disappears;
- a rewrite that is not better keeps the FIRST draft (tie or worse) — the
  retry can never make the reader's act worse than it was;
- a retry that produces nothing keeps the first draft and says so in the
  motive, never silently;
- a CLEAN first draft costs exactly one call and the act is byte-identical to
  the pre-#3343 path (positive control: the retry never fires speculatively);
- the motive carries act, counts and which draft was kept — never a sentence
  (#3249), and it is archived with the #2046 fabrication notes in BOTH twins,
  so it never reaches the reader as a repair note;
- Act III gets the same gesture: measured on this seat's stored states, its
  identical check fires on 16 of 48 act strings and its P1 licence suppresses
  none of them.

Synthetic vocabularies only — no corpus text, opaque ids only.
"""

import asyncio
from types import SimpleNamespace

from argumentation_analysis.reporting.restitution import (
    appendix,
    pipeline_adapter,
)
from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
    build_act2_narrative,
    build_act2_retry_prompt,
)
from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    build_act3_conclusion,
)

#: The R1125a shape — a whole-scope superlative with no ranking in the state.
_WHOLE_SCOPE = "Cet appui reste le plus fragile du dispositif."
_CLEAN = (
    "Premier mouvement : le raisonnement causal tient et porte le récit. "
    "Le second s'appuie sur une comparaison continue, sans faute relevée."
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


class TestActTwoRetry:
    """The bounded retry, end to end through the real builder."""

    def test_flagged_first_draft_is_asked_once_with_its_own_sentence(self):
        """Born red on main: the first draft is the only draft there, so a
        second call is the change itself. The correction must name the
        flagged sentence and the measured base — a retry that does not say
        what it saw is a dice roll."""
        calls = []
        first = "Premier mouvement : le raisonnement causal tient. " + _WHOLE_SCOPE
        llm = _two_drafts(first, _CLEAN, calls)
        _run(build_act2_narrative(_scored_state(), llm_callable=llm))

        assert len(calls) == 2, "exactly ONE retry, never a loop"
        assert _WHOLE_SCOPE in calls[1], (
            "the retry prompt must carry the sentence the check flagged"
        )
        assert "2 unités évaluées sur 2" in calls[1], (
            "the retry prompt must carry the measured base the sentence has "
            "to stand on"
        )

    def test_clean_rewrite_wins_and_the_motive_disappears(self):
        calls = []
        first = "Premier mouvement : le raisonnement causal tient. " + _WHOLE_SCOPE
        llm = _two_drafts(first, _CLEAN, calls)
        result = _run(build_act2_narrative(_scored_state(), llm_callable=llm))

        assert result.narrative.startswith("Premier mouvement : le raisonnement")
        assert _WHOLE_SCOPE not in result.narrative, (
            "the rewrite is the retained act — the reader no longer gets the "
            "unbacked claim"
        )
        assert "act2_whole_scope_superlative" not in result.degraded
        assert "act2_superlative_retry" in result.degraded
        motif = result.degraded["act2_superlative_retry"]
        assert "la réécriture" in motif
        assert "1" in motif and "0" in motif

    def test_a_rewrite_that_is_not_better_keeps_the_first_draft(self):
        """Anti-regression guard on the gesture itself: a retry can never
        leave the reader with worse prose than the first draft."""
        calls = []
        first = "Premier mouvement : le raisonnement causal tient. " + _WHOLE_SCOPE
        llm = _two_drafts(first, first, calls)
        result = _run(build_act2_narrative(_scored_state(), llm_callable=llm))

        assert result.narrative == first
        assert "act2_whole_scope_superlative" in result.degraded
        motif = result.degraded["act2_superlative_retry"]
        assert "le premier brouillon" in motif

    def test_clean_first_draft_costs_one_call_and_is_byte_identical(self):
        """Positive control: the retry fires on the CHECK, never
        speculatively. A clean act is exactly what it was before #3343."""
        calls = []
        llm = _two_drafts(_CLEAN, "jamais lu", calls)
        result = _run(build_act2_narrative(_scored_state(), llm_callable=llm))

        assert len(calls) == 1, "no retry unless the check fires"
        assert result.narrative == _CLEAN, (
            "a clean first draft is returned untouched — same bytes as the "
            "pre-#3343 path"
        )
        assert "act2_superlative_retry" not in result.degraded

    def test_a_retry_that_produces_nothing_keeps_the_first_draft(self):
        """Fail-loud on the retry too: the writer's silence is a recorded
        fact, not a reason to lose the first draft."""
        calls = []

        async def llm_callable(prompt: str) -> str:
            calls.append(prompt)
            if len(calls) == 2:
                raise RuntimeError("writer down")
            return "Premier mouvement : le raisonnement causal tient. " + _WHOLE_SCOPE

        result = _run(build_act2_narrative(_scored_state(), llm_callable=llm_callable))

        assert len(calls) == 2
        assert _WHOLE_SCOPE in result.narrative
        motif = result.degraded["act2_superlative_retry"]
        assert "n'a rien produit" in motif
        assert "RuntimeError" in motif, "the observed reason is recorded"

    def test_the_motive_never_quotes_the_act(self):
        """#3249 — ``restitution_acts_degraded`` is a closed producer
        vocabulary for the sanitizer; a motif quoting the act would carry
        corpus text into it."""
        calls = []
        first = "Premier mouvement : le raisonnement causal tient. " + _WHOLE_SCOPE
        llm = _two_drafts(first, first, calls)
        result = _run(build_act2_narrative(_scored_state(), llm_callable=llm))

        motif = result.degraded["act2_superlative_retry"]
        assert _WHOLE_SCOPE not in motif
        assert "fragile" not in motif

    def test_the_retry_key_is_archived_in_both_twins(self):
        """The retry repairs the prose; it tells the reader nothing about the
        run. Both halves of the #2046 twin set must agree, or the motif
        reaches the reader as machine voice."""
        assert "act2_superlative_retry" in appendix._FABRICATION_NOTE_KEYS
        assert "act2_superlative_retry" in pipeline_adapter._FABRICATION_NOTE_KEYS
        assert "act3_superlative_retry" in appendix._FABRICATION_NOTE_KEYS
        assert "act3_superlative_retry" in pipeline_adapter._FABRICATION_NOTE_KEYS
        assert (
            appendix._FABRICATION_NOTE_KEYS == pipeline_adapter._FABRICATION_NOTE_KEYS
        ), "the twins must stay byte-equal"


class TestRetryPrompt:
    def test_the_prompt_keeps_the_base_prompt(self):
        """The writer must not lose its data blocks on the second pass: the
        correction is appended to the SAME prompt, never a bare re-ask."""
        from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
            build_act2_evidence,
            build_act2_prompt,
        )

        evidence = build_act2_evidence(_scored_state())
        base = build_act2_prompt(evidence)
        retried = build_act2_retry_prompt(evidence, [_WHOLE_SCOPE])
        assert retried.startswith(base)
        assert "CORRECTION DEMANDÉE" in retried[len(base) :]


class TestActThreeRetry:
    """The same gesture on Act III, where the licence is the salience
    hierarchy (P1) — measured: 16 of 48 stored act strings fire the check and
    the P1 licence suppresses none of them."""

    @staticmethod
    def _state() -> SimpleNamespace:
        return _state(
            identified_arguments={
                "arg_1": "Le locuteur disqualifie l'adversaire par une attaque personnelle.",
                "arg_2": "Une revendication défendue par un raisonnement causal étayé.",
            },
            identified_fallacies={
                "fl_1": {
                    "target_argument_id": "arg_1",
                    "family": "ad hominem",
                    "type": "ad hominem circonstanciel",
                    "taxonomy_path": "racine > sophismes de pertinence > ad hominem",
                    "justification": "L'argument attaque la personne plutôt que la thèse.",
                },
            },
            argument_quality_scores={
                "arg_1": {"overall": 4.2, "scores": {"pertinence": 3.0, "clarte": 5.0}},
                "arg_2": {"overall": 7.8, "scores": {"pertinence": 8.0, "clarte": 7.5}},
            },
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

    _FLAGGED = "L'ensemble se referme sur un constat : ce point reste le plus faible du dispositif."
    _CLEAN = (
        "Le bilan est net : deux mouvements ont porté la discussion, et le "
        "premier concentre les objections."
    )

    def test_a_flagged_conclusion_is_asked_once(self):
        calls = []

        async def llm_callable(prompt: str) -> str:
            calls.append(prompt)
            return self._FLAGGED if len(calls) == 1 else self._CLEAN

        result = _run(build_act3_conclusion(self._state(), llm_callable=llm_callable))

        assert len(calls) == 2
        assert self._FLAGGED in calls[1]
        assert "act3_superlative_retry" in result.degraded
        assert "act3_whole_scope_superlative" not in result.degraded

    def test_a_clean_conclusion_costs_one_call(self):
        calls = []

        async def llm_callable(prompt: str) -> str:
            calls.append(prompt)
            return self._CLEAN

        result = _run(build_act3_conclusion(self._state(), llm_callable=llm_callable))

        assert len(calls) == 1
        assert "act3_superlative_retry" not in result.degraded
