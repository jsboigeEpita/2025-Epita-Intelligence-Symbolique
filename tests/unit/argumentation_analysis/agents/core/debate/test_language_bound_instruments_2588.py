"""#2588 — born-red witnesses: FR/DE text was scored with EN instruments.

The fact-check word lists, evidence/emotional indicators and Flesch
readability were English-only. On French or German text the fact-check
returned its neutral constant on every input (hedging and absolutes
matched nothing), and Flesch ran English syllable counting on French
words (a mid-range French sentence scored like a difficult one).

This file imports only surfaces that exist before #2588 so it can run
against ``main`` and show the defect.
"""

import pytest

from argumentation_analysis.agents.core.debate.debate_definitions import (
    ArgumentType,
    DebatePhase,
    EnhancedArgument,
)
from argumentation_analysis.agents.core.debate.debate_scoring import ArgumentAnalyzer
from argumentation_analysis.agents.core.quality import quality_evaluator

FR_HEDGED = (
    "Cette mesure pourrait peut-être améliorer la situation, sans doute "
    "progressivement, car les effets restent incertains et la décision est complexe."
)
FR_ABSOLUTE = (
    "Cette solution fonctionne toujours et ne échoue jamais : elle est "
    "absolument fiable pour tous les utilisateurs."
)
DE_HEDGED = (
    "Das könnte vielleicht helfen, möglicherweise schon recht bald, "
    "weil die Lage noch unklar ist."
)
DE_ABSOLUTE = (
    "Diese Lösung funktioniert immer und versagt niemals, "
    "denn der Erfolg ist mit Sicherheit absolut."
)
EN_HEDGED = "This measure might perhaps improve the situation for the country, and it is not certain."
EN_ABSOLUTE = "This solution always works and it never fails for all the users."

# Mid-range French sentence (vaccination sample of the performance
# benchmarks): measured 2026-09-26 on this repo — Flesch 42.9 under en
# rules, 64.0 under fr rules.
FR_MID = (
    "La vaccination est un outil essentiel de santé publique, car les études "
    "montrent qu'elle réduit la propagation des maladies et protège les plus "
    "fragiles, même si certains doutes persistent dans la population."
)
DE_MID = (
    "Der Klimawandel stellt eine der größten Herausforderungen unserer Zeit "
    "dar, und die Wissenschaft zeigt klar, dass der Mensch wesentlich dazu "
    "beiträgt."
)


def _make_arg(content: str) -> EnhancedArgument:
    return EnhancedArgument(
        agent_name="Alice",
        position="for",
        content=content,
        argument_type=ArgumentType.CLAIM,
        timestamp="2025-01-01T00:00:00",
        phase=DebatePhase.MAIN_ARGUMENTS,
    )


@pytest.fixture
def analyzer():
    return ArgumentAnalyzer()


class TestFactCheckLanguageBound:
    def test_french_hedged_vs_absolute_separate(self, analyzer):
        hedged = analyzer._basic_fact_check(FR_HEDGED)
        absolute = analyzer._basic_fact_check(FR_ABSOLUTE)
        assert hedged == 0.7
        assert absolute == 0.4

    def test_german_hedged_vs_absolute_separate(self, analyzer):
        assert analyzer._basic_fact_check(DE_HEDGED) == 0.7
        assert analyzer._basic_fact_check(DE_ABSOLUTE) == 0.4

    def test_english_control_unchanged(self, analyzer):
        assert analyzer._basic_fact_check(EN_HEDGED) == 0.7
        assert analyzer._basic_fact_check(EN_ABSOLUTE) == 0.4

    def test_undetectable_text_runs_the_lexicon_union(self, analyzer):
        # #2588 review: below 3 function words the detector cannot decide, and
        # mapping unknown->en would bring the defect back for short French.
        # The union of the three languages still measures: the lists are
        # disjoint, and "might" is hedging whichever list recognises it.
        short_fr_hedged = "Il faut peut-être baisser les impôts."
        assert analyzer._basic_fact_check(short_fr_hedged) == 0.7
        short_en_absolute = "Taxes must never rise for all firms."
        assert analyzer._basic_fact_check(short_en_absolute) == 0.4
        # No marker in any language: the neutral verdict is measured (zero
        # hedging, zero absolutes), not a constant masking blind lists.
        assert analyzer._basic_fact_check("zzqq xxvv kkww jjff.") == 0.6

    def test_explicit_language_overrides_detection(self, analyzer):
        # lang= is authoritative: a German-list pass on that French sentence
        # finds no marker of either category, so the neutral 0.6 applies.
        assert (
            analyzer._basic_fact_check(
                "Il faut peut-être baisser les impôts.", lang="de"
            )
            == 0.6
        )

    def test_word_boundary_none_is_not_nonetheless(self, analyzer):
        # Substring matching counted "none" inside "nonetheless", tying the
        # hedging hit and flattening the verdict to the neutral constant.
        assert (
            analyzer._basic_fact_check("The plan is nonetheless likely to succeed.")
            == 0.7
        )


class TestReadabilityLanguageBound:
    def test_french_text_uses_the_french_scale(self, analyzer):
        from textstat.textstat import textstatistics

        en_rules = max(
            0.0, min(1.0, textstatistics().flesch_reading_ease(FR_MID) / 100)
        )
        fr = analyzer._assess_readability(FR_MID)
        assert fr is not None
        assert fr > en_rules

    def test_german_text_uses_the_german_scale(self, analyzer):
        from textstat.textstat import textstatistics

        en_rules = max(
            0.0, min(1.0, textstatistics().flesch_reading_ease(DE_MID) / 100)
        )
        de = analyzer._assess_readability(DE_MID)
        assert de is not None
        # German Flesch (Amstad adaptation) runs lower than English Flesch on
        # the same text — measured: 67.3 (en rules) vs 55.3 (de rules).
        assert de < en_rules

    def test_unknown_language_readability_is_none(self, analyzer):
        assert analyzer._assess_readability("zzqq xxvv kkww jjff.") is None


class TestEvidenceAndEmotionLexicons:
    def test_french_evidence_indicators_count(self, analyzer):
        with_indicators = analyzer._assess_evidence_quality(
            "Selon les études montrent les données, 42% des cas évoluent."
        )
        without = analyzer._assess_evidence_quality(
            "Simple opinion sur une question locale et actuelle."
        )
        assert with_indicators > without

    def test_french_emotional_indicators_count(self, analyzer):
        with_indicators = analyzer._assess_emotional_appeal(
            "Cette catastrophe est terrible et gravissime pour la région."
        )
        without = analyzer._assess_emotional_appeal(
            "Cette évolution est régulière et documentée pour la région."
        )
        assert with_indicators > without


class TestClarteLanguageBound:
    def test_clarte_names_the_language_and_scale(self):
        score, comment = quality_evaluator.detect_clarte(FR_MID)
        # The comment says which language's Flesch scale produced the number.
        assert "fr" in comment
        # FR_MID measured 64.0 under fr rules: medium band of the fr scale.
        assert score == 0.5

    def test_clarte_unknown_language_falls_back_named(self):
        _, comment = quality_evaluator.detect_clarte("zzqq xxvv kkww jjff.")
        assert "heuristique" in comment


class TestPersuasivenessRenormalisation:
    def test_persuasiveness_stands_when_instruments_absent(self, analyzer):
        # Anti-pendule witness: an unknown-language argument keeps a computed
        # persuasiveness — readability (no formula to pick) drops out and its
        # weight renormalizes (#2344 machinery); fact-check measures via the
        # lexicon union (#2588 review) instead of returning a constant.
        metrics = analyzer.analyze_argument(_make_arg("zzqq xxvv kkww jjff."), [])
        assert metrics.readability_score is None
        assert metrics.fact_check_score == 0.6
        assert metrics.persuasiveness is not None
        assert 0.0 <= metrics.persuasiveness <= 1.0
