"""#3328 — the writers no longer copy the pipeline's names for their inputs
onto the reader surface, and a gate class measures it.

The four tokens are the writer prompts' OWN words, which the writers turned
into prose: the Act I beat « La lecture game-theoretic » (the prompt named it
in English at l.952 and in the block header at l.970 — hence the near-100 %
rate), « rebuttal » handed over by the English grounding rules, and
« briefing » / « lot affiché » naming the dossier the writer receives.

The repair is at the producer, never a post-render substitution (#3259/#3264):
the beat and the block header are named in French, the grounding rule is
written in French with « contre-argument », the dossier the writer receives is
no longer called a briefing, and one reading rule says a writer never names
its own inputs — **without listing the forbidden words**, because naming a
token in a rule is what hands it over (#3307 measured that mechanism).

Measured on this seat before the change (187 stored states): game-theoretic
147 states / 147 occurrences, rebuttal 49 / 131, briefing 4 / 10, « lot
affiché » 0 (the coordinator seat carries 1/35). Bare « affiché » (35 states /
41 occurrences) and « inventaire » (64) are ordinary French and stay out of
the class — the negative fixtures below pin that.

Deterministic — no JVM, no LLM, no network.
"""

from __future__ import annotations

from types import SimpleNamespace

from argumentation_analysis.agents.core.synthesis.deep_synthesis_agent import (
    DeepSynthesisAgent,
)
from argumentation_analysis.reporting.restitution.act1_framing_plugin import (
    build_act1_evidence,
    build_act1_prompt,
    reset_taxonomy_cache,
)
from argumentation_analysis.reporting.restitution.reader_vocabulary_check import (
    check_reader_vocabulary,
)


def _state() -> SimpleNamespace:
    return SimpleNamespace(
        source_metadata={
            "genre": "discours politique",
            "speaker_role": "locuteur en autorité",
            "channel": "arène publique",
        },
        stakes_and_stakeholders={
            "rhetorical_register": "délibératif",
            "discursive_arena": "assemblée",
            "stakes": [],
            "stakeholders": [],
        },
        identified_arguments={},
    )


def _pipeline_reasons(body: str) -> list:
    verdict = check_reader_vocabulary(body)
    return [r for r in verdict.reasons if "#3328" in r]


class TestTheGateSeesThePipelineNames:
    """DoD box 3 — one class, letter-bounded, one fixture per token.

    Born red on main: the class does not exist, so every reason list is empty
    and the band is PASS."""

    def test_the_act1_heading_is_flagged(self):
        body = "### La lecture game-theoretic\n\nLes acteurs se partagent le terrain.\n"
        assert _pipeline_reasons(body)

    def test_the_english_fallacy_word_is_flagged(self):
        body = "La synthèse narrative concentre aussi les rebuttals de la partie.\n"
        assert _pipeline_reasons(body)

    def test_the_writers_input_name_is_flagged(self):
        body = "La synthèse dit ce que le briefing signale sur la question.\n"
        assert _pipeline_reasons(body)

    def test_the_capped_batch_phrase_is_flagged(self):
        body = "Le contre-argument le mieux noté du lot affiché reste isolé.\n"
        assert _pipeline_reasons(body)


class TestTheFrenchProseStaysOut:
    """Negative fixtures (DoD box 3) — the class must not police French."""

    def test_ordinary_french_is_not_flagged(self):
        body = (
            "Le contre-argument vise l'inventaire des thèses, et le tableau "
            "affiché reste lisible pour qui suit le débat.\n"
        )
        assert _pipeline_reasons(body) == []

    def test_bare_affiche_alone_is_not_flagged(self):
        """« affiché » is ordinary French; only the compound names an input."""
        body = "Le désaccord affiché entre les deux camps nourrit la lecture.\n"
        assert _pipeline_reasons(body) == []


class TestTheProducersStoppedHandingTheWordsOver:
    """DoD boxes 1 and 2 — the vocabulary is gone at the source."""

    def test_the_act1_prompt_names_its_fourth_beat_in_french(self):
        """Born red: on main the prompt reads « 4. La lecture game-theoretic »."""
        reset_taxonomy_cache()
        prompt = build_act1_prompt(build_act1_evidence(_state()))
        assert "game-theoretic" not in prompt.lower()
        assert "La lecture stratégique" in prompt

    def test_the_act1_block_header_is_french_too(self):
        """Born red: the header block carried the English name as well."""
        reset_taxonomy_cache()
        prompt = build_act1_prompt(build_act1_evidence(_state()))
        assert "[LECTURE STRATÉGIQUE" in prompt
        assert "[LECTURE GAME-THEORETIC" not in prompt

    def test_the_synthesis_briefing_hands_over_no_english_fallacy_word(self):
        """Born red: the grounding rule said « rebuttal » three times, and the
        report copied it (131 occurrences on 49 stored states)."""
        briefing = DeepSynthesisAgent.build_artifact_briefing(
            SimpleNamespace(
                identified_arguments={},
                identified_fallacies={},
                counter_arguments=[],
                argument_quality_scores={},
                propositional_analysis_results=[],
                fol_analysis_results=[],
                modal_analysis_results=[],
                dung_frameworks={},
                jtms_retraction_chain=[],
                belief_revision_results=[],
            )
        )
        assert "rebuttal" not in briefing.lower()
        assert "un contre-argument ne réfute" in briefing

    def test_the_synthesis_prompt_no_longer_calls_its_input_a_briefing(self):
        """Born red: « Tu reçois un BRIEFING D'ARTEFACTS » handed the writer
        the word it then used for its own source."""
        prompt = DeepSynthesisAgent.GROUNDED_SYNTHESIS_PROMPT
        assert "briefing" not in prompt.lower()
        assert "DOSSIER D'ARTEFACTS" in prompt

    def test_the_reading_rule_states_the_limit_without_listing_the_words(self):
        """The anti-pendulum check: forbidding a token by naming it is what
        hands it over (#3307's measured mechanism)."""
        rules = DeepSynthesisAgent.build_artifact_briefing(
            SimpleNamespace(
                identified_arguments={},
                identified_fallacies={},
                counter_arguments=[],
                argument_quality_scores={},
                propositional_analysis_results=[],
                fol_analysis_results=[],
                modal_analysis_results=[],
                dung_frameworks={},
                jtms_retraction_chain=[],
                belief_revision_results=[],
            )
        )
        assert "ne nomme jamais tes propres entrées de production" in rules
        rule_line = next(
            line
            for line in rules.splitlines()
            if "ne nomme jamais tes propres entrées" in line
        )
        assert "briefing" not in rule_line.lower()
