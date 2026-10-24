# -*- coding: utf-8 -*-
"""#3237 — one cause rule for both acts, and the check that guarantees it.

The R1110c render (coordinator's seat, doc_A, code ``4101cdc26``) showed Act
II describing a formal contradiction whose recorded cause is
``between_sources`` (« locuteurs non documentés par ce run ») as
« le point où les deux voix se heurtent » — precisely the cause the record
says it cannot establish. Act III's prompt carried the #3107 cause rule; Act
II's did not.

Witnesses here:
- the rebuilt Act II prompt carries ``FORMAL_CAUSE_NAMING_RULE`` (born red on
  main, where the rule reaches Act III only);
- both acts carry the SAME constant — the imported text, not a copy that can
  drift;
- the post-render check flags the R1110c shape (same-sentence and anaphoric
  tie), stays silent on a ``between_voices`` state (the run then documents
  the two voices), on a cause-less state, and on a rhetorical voice clash
  with no formal noun in its window (the legitimate two-voice caution);
- the producer-side strip (#1605 removal shape) removes the sentence before
  the act is persisted, and the integration witness shows the woven act
  itself comes out clean.

Synthetic vocabularies only — no corpus text, opaque ids only.
"""

from types import SimpleNamespace

from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
    build_act2_evidence,
    build_act2_narrative,
    build_act2_prompt,
)
from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    build_act3_evidence,
    build_act3_prompt,
)
from argumentation_analysis.reporting.restitution.formal_cause_check import (
    check_formal_cause_attribution,
    stated_formal_causes,
    strip_voice_clash_cause_sentences,
)

# A distinctive fragment of the rule — the sentence that was missing from
# Act II's prompt on main (the misstated cause is charged to a speaker).
_RULE_FRAGMENT = "n'attribue jamais cette inconsistance au raisonnement d'un locuteur"

# The R1110c shape, in the witness's own words: the generic part of the
# rendered sentence only (« le point où les deux voix se heurtent »), tied to
# a formal constat.
_SAME_SENTENCE_BODY = (
    "Le cadre formel relève deux contradictions entre ces passages : c'est le "
    "point où les deux voix se heurtent, et le jugement du lecteur en dépend."
)
_ANAPHORIC_BODY = (
    "Le solveur établit une contradiction entre ces passages. C'est le point "
    "où les deux voix se heurtent."
)
_RHETORICAL_BODY = (
    "Sur la conduite du débat, les deux voix se heurtent dès l'ouverture, et "
    "le lecteur le voit dès la première page."
)


def _state(**fields: object) -> SimpleNamespace:
    """Lightweight state stub with the acts' relevant fields."""
    base = dict(
        identified_arguments={
            "arg_1": "Un argument défendu par un raisonnement causal.",
        },
        identified_fallacies={},
        argument_quality_scores={},
        counter_arguments=[],
        dung_frameworks={},
        fol_analysis_results=[],
        propositional_analysis_results=[],
        modal_analysis_results=[],
        governance_decisions=[],
        debate_transcripts=[],
    )
    base.update(fields)
    return SimpleNamespace(**base)


def _refuted_fol_state(cause: str = "between_sources") -> SimpleNamespace:
    """A run whose one refuted FOL theory recorded the given cause."""
    return _state(
        fol_analysis_results=[
            {
                "consistent": False,
                "message": None,
                "consistency_cause": {"cause": cause},
            }
        ]
    )


class TestOneRuleOneFather:
    """Both acts' prompts carry the cause rule, from the same constant."""

    def test_act2_prompt_carries_the_cause_rule(self):
        """DoD 1 — rebuilt Act II prompt carries the rule (absent on main)."""
        prompt = build_act2_prompt(build_act2_evidence(_refuted_fol_state()))
        assert _RULE_FRAGMENT in prompt, (
            "Act II's prompt must carry FORMAL_CAUSE_NAMING_RULE: Act II "
            "receives the recorded causes on its evidence lines, and without "
            "the rule that binds the prose to them it misstates the cause "
            "(R1110c — the defect this issue repairs)"
        )

    def test_act3_prompt_still_carries_the_cause_rule(self):
        """The inline #3107 block became the constant — Act III keeps it."""
        prompt = build_act3_prompt(build_act3_evidence(_refuted_fol_state()))
        assert _RULE_FRAGMENT in prompt, (
            "Act III's prompt carried the rule since #3107; moving it to the "
            "shared constant must not lose it"
        )

    def test_both_acts_carry_the_imported_constant_not_a_copy(self):
        """One father — the imported text, so no second wording can drift."""
        # Imported lazily so the behavior witnesses above stay runnable
        # against a tree where the constant does not exist yet (born red).
        from argumentation_analysis.orchestration.fol_cause import (
            FORMAL_CAUSE_NAMING_RULE,
        )

        for build_prompt, build_evidence in (
            (build_act2_prompt, build_act2_evidence),
            (build_act3_prompt, build_act3_evidence),
        ):
            prompt = build_prompt(build_evidence(_refuted_fol_state()))
            assert FORMAL_CAUSE_NAMING_RULE in prompt


class TestStatedFormalCauses:
    """The gate's reader: stated causes over refuted PL/FOL records."""

    def test_reads_fol_cause_on_refuted_record(self):
        causes = stated_formal_causes(_refuted_fol_state())
        assert causes == ["between_sources"]

    def test_reads_pl_cause_through_the_satisfiable_key(self):
        """PL's canonical writer key is ``satisfiable``, not ``consistent``."""
        st = _state(
            propositional_analysis_results=[
                {
                    "satisfiable": False,
                    "consistency_cause": {"cause": "between_sources"},
                }
            ]
        )
        assert stated_formal_causes(st) == ["between_sources"]

    def test_unsettled_verdict_states_no_cause(self):
        """#1019 — None is not False: an unsettled record states nothing.

        The six stored local renders carry exactly this shape (PL/FOL records
        with no settled verdict), and the check measured 0 flags on them.
        """
        st = _state(
            fol_analysis_results=[{"consistent": None, "message": None}],
            propositional_analysis_results=[{"satisfiable": None}],
        )
        assert stated_formal_causes(st) == []
        assert check_formal_cause_attribution(_SAME_SENTENCE_BODY, st).band == "PASS"

    def test_verified_record_states_no_cause(self):
        st = _state(fol_analysis_results=[{"consistent": True, "message": None}])
        assert stated_formal_causes(st) == []


class TestFormalCauseAttributionCheck:
    """Post-render defense in depth — the R1110c shape and its controls."""

    def test_flags_the_same_sentence_tie(self):
        verdict = check_formal_cause_attribution(
            _SAME_SENTENCE_BODY, _refuted_fol_state()
        )
        assert verdict.band == "FAIL"
        assert any("deux voix" in r for r in verdict.reasons)

    def test_flags_the_anaphoric_tie(self):
        """« C'est le point où … » refers back — the noun lives one sentence up."""
        verdict = check_formal_cause_attribution(_ANAPHORIC_BODY, _refuted_fol_state())
        assert verdict.band == "FAIL"

    def test_silent_on_a_between_voices_state(self):
        """Anti-pendulum — when the run documents two voices, the clash
        sentence is the honest one and the check says nothing."""
        verdict = check_formal_cause_attribution(
            _SAME_SENTENCE_BODY, _refuted_fol_state("between_voices")
        )
        assert verdict.band == "PASS"

    def test_silent_without_stated_cause(self):
        st = _state(fol_analysis_results=[{"consistent": False, "message": None}])
        verdict = check_formal_cause_attribution(_SAME_SENTENCE_BODY, st)
        assert verdict.band == "PASS"

    def test_silent_on_rhetorical_voice_clash(self):
        """The two-voice caution without a formal constat in its window is
        legitimate prose present in every act — it never flags."""
        verdict = check_formal_cause_attribution(_RHETORICAL_BODY, _refuted_fol_state())
        assert verdict.band == "PASS"

    def test_silent_without_state(self):
        verdict = check_formal_cause_attribution(_SAME_SENTENCE_BODY, None)
        assert verdict.band == "PASS"


class TestProducerSideStrip:
    """#1605 removal shape — the sentence goes before the act is persisted."""

    def test_strip_removes_the_defect_sentence_only(self):
        narrative = (
            "Premier mouvement du récit, sans rapport avec la cause. "
            + _ANAPHORIC_BODY
            + " Dernier mouvement, lui aussi gardé."
        )
        out, removed = strip_voice_clash_cause_sentences(
            narrative, _refuted_fol_state()
        )
        assert len(removed) == 1
        assert "deux voix se heurtent" in removed[0]
        assert "deux voix" not in out
        assert "Premier mouvement" in out and "Dernier mouvement" in out

    def test_strip_keeps_the_sentence_when_between_voices(self):
        narrative = _ANAPHORIC_BODY
        out, removed = strip_voice_clash_cause_sentences(
            narrative, _refuted_fol_state("between_voices")
        )
        assert removed == []
        assert out == narrative


class TestWovenActComesOutClean:
    """Integration — the woven Act II itself carries no misstated cause."""

    def test_woven_act2_strips_the_voice_clash_cause(self):
        """The stub LLM weaves the R1110c shape; the persisted act must not
        carry it, while the honest movements survive (red on main, where no
        strip exists)."""
        woven = (
            "Premier mouvement : l'argument causal tient, appuyé par le "
            "raisonnement du locuteur. "
            + _ANAPHORIC_BODY
            + " Le jugement du lecteur reste entier."
        )

        async def llm_callable(prompt: str) -> str:  # pragma: no cover - stub
            return woven

        result = (
            __import__("asyncio")
            .get_event_loop()
            .run_until_complete(
                build_act2_narrative(_refuted_fol_state(), llm_callable=llm_callable)
            )
        )
        assert "deux voix se heurtent" not in result.narrative
        assert "Premier mouvement" in result.narrative
