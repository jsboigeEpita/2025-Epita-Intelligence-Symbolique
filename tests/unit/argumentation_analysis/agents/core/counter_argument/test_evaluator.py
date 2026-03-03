# -*- coding: utf-8 -*-
"""
Tests for argumentation_analysis.agents.core.counter_argument.evaluator
Covers CounterArgumentEvaluator: init, evaluate, relevance, logical_strength,
persuasiveness, originality, clarity, recommendations, helper methods.
"""

import pytest

from argumentation_analysis.agents.core.counter_argument.evaluator import (
    CounterArgumentEvaluator,
)
from argumentation_analysis.agents.core.counter_argument.definitions import (
    Argument,
    CounterArgument,
    CounterArgumentType,
    ArgumentStrength,
    EvaluationResult,
)


@pytest.fixture
def evaluator():
    return CounterArgumentEvaluator()


def _make_argument(**overrides):
    defaults = dict(
        content="Tous les chats sont des animaux domestiques.",
        premises=["Tous les chats sont des animaux domestiques"],
        conclusion="Les chats sont domestiques",
        argument_type="deductive",
        confidence=0.8,
    )
    defaults.update(overrides)
    return Argument(**defaults)


def _make_counter(**overrides):
    defaults = dict(
        original_argument=_make_argument(),
        counter_type=CounterArgumentType.DIRECT_REFUTATION,
        counter_content="Cette conclusion est incorrecte car de nombreux chats vivent à l'état sauvage.",
        target_component="conclusion",
        strength=ArgumentStrength.MODERATE,
        confidence=0.7,
        supporting_evidence=[],
        rhetorical_strategy="",
    )
    defaults.update(overrides)
    return CounterArgument(**defaults)


# ============================================================
# Initialization
# ============================================================

class TestInit:
    def test_creates_instance(self, evaluator):
        assert isinstance(evaluator, CounterArgumentEvaluator)

    def test_has_criteria(self, evaluator):
        assert "relevance" in evaluator.evaluation_criteria
        assert "logical_strength" in evaluator.evaluation_criteria
        assert "persuasiveness" in evaluator.evaluation_criteria
        assert "originality" in evaluator.evaluation_criteria
        assert "clarity" in evaluator.evaluation_criteria

    def test_criteria_sum_to_one(self, evaluator):
        total = sum(evaluator.evaluation_criteria.values())
        assert abs(total - 1.0) < 0.01

    def test_has_persuasive_elements(self, evaluator):
        assert isinstance(evaluator.persuasive_elements, list)
        assert "preuve" in evaluator.persuasive_elements

    def test_has_logical_markers(self, evaluator):
        assert isinstance(evaluator.logical_markers, list)
        assert "car" in evaluator.logical_markers


# ============================================================
# evaluate (integration)
# ============================================================

class TestEvaluate:
    def test_returns_evaluation_result(self, evaluator):
        arg = _make_argument()
        counter = _make_counter()
        result = evaluator.evaluate(arg, counter)
        assert isinstance(result, EvaluationResult)

    def test_all_scores_in_range(self, evaluator):
        arg = _make_argument()
        counter = _make_counter()
        result = evaluator.evaluate(arg, counter)
        for field in ["relevance", "logical_strength", "persuasiveness", "originality", "clarity", "overall_score"]:
            score = getattr(result, field)
            assert 0.0 <= score <= 1.0, f"{field} = {score} out of range"

    def test_overall_is_weighted_sum(self, evaluator):
        arg = _make_argument()
        counter = _make_counter()
        result = evaluator.evaluate(arg, counter)
        expected = (
            result.relevance * 0.25
            + result.logical_strength * 0.25
            + result.persuasiveness * 0.20
            + result.originality * 0.15
            + result.clarity * 0.15
        )
        assert abs(result.overall_score - expected) < 0.01

    def test_has_recommendations(self, evaluator):
        arg = _make_argument()
        counter = _make_counter()
        result = evaluator.evaluate(arg, counter)
        assert isinstance(result.recommendations, list)


# ============================================================
# _evaluate_relevance
# ============================================================

class TestEvaluateRelevance:
    def test_high_overlap_gives_relevance(self, evaluator):
        arg = _make_argument(content="Les chats domestiques sont populaires")
        counter = _make_counter(
            counter_content="Les chats domestiques ne sont pas toujours populaires"
        )
        score = evaluator._evaluate_relevance(arg, counter)
        assert score > 0.0

    def test_no_overlap_low_relevance(self, evaluator):
        arg = _make_argument(content="Les oiseaux migrateurs")
        counter = _make_counter(
            counter_content="La philosophie analytique"
        )
        score = evaluator._evaluate_relevance(arg, counter)
        assert score < 0.5

    def test_argument_mention_bonus(self, evaluator):
        counter_with = _make_counter(
            counter_content="Cet argument est faux"
        )
        counter_without = _make_counter(
            counter_content="Cette affirmation est fausse"
        )
        arg = _make_argument()
        score_with = evaluator._evaluate_relevance(arg, counter_with)
        score_without = evaluator._evaluate_relevance(arg, counter_without)
        assert score_with >= score_without

    def test_premise_challenge_target_match(self, evaluator):
        arg = _make_argument(
            premises=["Les scientifiques affirment que la terre est ronde"]
        )
        counter = _make_counter(
            counter_type=CounterArgumentType.PREMISE_CHALLENGE,
            counter_content="Les scientifiques ne sont pas unanimes sur cette affirmation",
        )
        score = evaluator._evaluate_relevance(arg, counter)
        assert score > 0.0

    def test_max_is_one(self, evaluator):
        arg = _make_argument()
        counter = _make_counter()
        score = evaluator._evaluate_relevance(arg, counter)
        assert score <= 1.0


# ============================================================
# _evaluate_logical_strength
# ============================================================

class TestEvaluateLogicalStrength:
    def test_direct_refutation_base(self, evaluator):
        counter = _make_counter(counter_type=CounterArgumentType.DIRECT_REFUTATION)
        score = evaluator._evaluate_logical_strength(counter)
        assert score >= 0.7  # base for DIRECT_REFUTATION

    def test_logical_markers_boost(self, evaluator):
        counter_with = _make_counter(
            counter_content="Cela est faux car les données montrent le contraire"
        )
        counter_without = _make_counter(
            counter_content="Cela est faux"
        )
        score_with = evaluator._evaluate_logical_strength(counter_with)
        score_without = evaluator._evaluate_logical_strength(counter_without)
        assert score_with >= score_without

    def test_structure_bonus(self, evaluator):
        counter = _make_counter(
            counter_content="Il pleut car il y a des nuages, donc le sol sera mouillé"
        )
        score = evaluator._evaluate_logical_strength(counter)
        assert score > 0.7

    def test_strong_strength_bonus(self, evaluator):
        counter_strong = _make_counter(strength=ArgumentStrength.STRONG)
        counter_weak = _make_counter(strength=ArgumentStrength.WEAK)
        score_strong = evaluator._evaluate_logical_strength(counter_strong)
        score_weak = evaluator._evaluate_logical_strength(counter_weak)
        assert score_strong > score_weak

    def test_fallacy_penalty(self, evaluator):
        counter_clean = _make_counter(
            counter_content="Les données montrent le contraire"
        )
        counter_fallacy = _make_counter(
            counter_content="C'est un ad hominem de votre part"
        )
        score_clean = evaluator._evaluate_logical_strength(counter_clean)
        score_fallacy = evaluator._evaluate_logical_strength(counter_fallacy)
        assert score_clean >= score_fallacy

    def test_max_is_one(self, evaluator):
        counter = _make_counter(
            counter_type=CounterArgumentType.COUNTER_EXAMPLE,
            strength=ArgumentStrength.DECISIVE,
            counter_content="Car les preuves et exemples sont clairs, donc par conséquent c'est faux"
        )
        score = evaluator._evaluate_logical_strength(counter)
        assert score <= 1.0


# ============================================================
# _evaluate_persuasiveness
# ============================================================

class TestEvaluatePersuasiveness:
    def test_persuasive_elements_boost(self, evaluator):
        counter = _make_counter(
            counter_content="Les données et les études montrent des preuves contraires"
        )
        score = evaluator._evaluate_persuasiveness(counter)
        assert score > 0.2

    def test_good_length_bonus(self, evaluator):
        # 30-100 words
        words = " ".join(["mot"] * 50)
        counter = _make_counter(counter_content=words)
        score = evaluator._evaluate_persuasiveness(counter)
        assert score > 0.0

    def test_affirm_tone_boost(self, evaluator):
        counter = _make_counter(
            counter_content="Clairement cette conclusion est incorrecte"
        )
        score = evaluator._evaluate_persuasiveness(counter)
        # Should get some tone boost
        assert score > 0.0

    def test_max_is_one(self, evaluator):
        counter = _make_counter(
            counter_content="Les données clairement certainement prouvent avec des statistiques " * 5,
            rhetorical_strategy="statistical_evidence",
        )
        score = evaluator._evaluate_persuasiveness(counter)
        assert score <= 1.0


# ============================================================
# _evaluate_originality
# ============================================================

class TestEvaluateOriginality:
    def test_base_originality(self, evaluator):
        counter = _make_counter(counter_content="Une réfutation simple")
        score = evaluator._evaluate_originality(counter)
        assert 0.1 <= score <= 1.0

    def test_common_phrases_penalty(self, evaluator):
        counter_common = _make_counter(
            counter_content="Tout le monde sait que c'est faux, comme on dit souvent"
        )
        counter_original = _make_counter(
            counter_content="Cette perspective néglige des aspects fondamentaux"
        )
        score_common = evaluator._evaluate_originality(counter_common)
        score_original = evaluator._evaluate_originality(counter_original)
        assert score_original >= score_common

    def test_unexpected_phrases_boost(self, evaluator):
        counter = _make_counter(
            counter_content="Sous un angle différent, cette conclusion montre des failles"
        )
        score = evaluator._evaluate_originality(counter)
        assert score >= 0.5

    def test_strategy_combo_bonus(self, evaluator):
        counter = _make_counter(
            counter_type=CounterArgumentType.DIRECT_REFUTATION,
            rhetorical_strategy="socratic",
            counter_content="Une perspective nouvelle"
        )
        score = evaluator._evaluate_originality(counter)
        assert score > 0.5


# ============================================================
# _evaluate_clarity
# ============================================================

class TestEvaluateClarity:
    def test_short_sentences_good(self, evaluator):
        counter = _make_counter(
            counter_content="C'est faux. Les preuves sont claires."
        )
        score = evaluator._evaluate_clarity(counter)
        assert score > 0.0

    def test_connectors_boost(self, evaluator):
        counter = _make_counter(
            counter_content="C'est incorrect car les données contredisent cela"
        )
        score = evaluator._evaluate_clarity(counter)
        assert score > 0.0

    def test_structure_markers_boost(self, evaluator):
        counter = _make_counter(
            counter_content="Tout d'abord les preuves. Ensuite les conclusions. En conclusion c'est faux."
        )
        score = evaluator._evaluate_clarity(counter)
        assert score > 0.3

    def test_ambiguity_penalty(self, evaluator):
        counter_ambiguous = _make_counter(
            counter_content="Peut-être que possiblement il se pourrait que ce soit faux"
        )
        counter_clear = _make_counter(
            counter_content="Les données démontrent clairement que c'est faux"
        )
        score_ambiguous = evaluator._evaluate_clarity(counter_ambiguous)
        score_clear = evaluator._evaluate_clarity(counter_clear)
        assert score_clear >= score_ambiguous

    def test_min_is_point_one(self, evaluator):
        counter = _make_counter(counter_content="x")
        score = evaluator._evaluate_clarity(counter)
        assert score >= 0.1


# ============================================================
# _generate_recommendations
# ============================================================

class TestGenerateRecommendations:
    def test_low_relevance_recommendation(self, evaluator):
        recs = evaluator._generate_recommendations(
            _make_argument(), _make_counter(), 0.3, 0.8, 0.8, 0.8, 0.8,
        )
        assert any("relevance" in r.lower() for r in recs)

    def test_low_logic_recommendation(self, evaluator):
        recs = evaluator._generate_recommendations(
            _make_argument(), _make_counter(), 0.8, 0.3, 0.8, 0.8, 0.8,
        )
        assert any("logical" in r.lower() for r in recs)

    def test_all_good_recommendation(self, evaluator):
        recs = evaluator._generate_recommendations(
            _make_argument(), _make_counter(), 0.8, 0.8, 0.8, 0.8, 0.8,
        )
        assert any("good quality" in r.lower() for r in recs)

    def test_returns_list(self, evaluator):
        recs = evaluator._generate_recommendations(
            _make_argument(), _make_counter(), 0.5, 0.5, 0.5, 0.5, 0.5,
        )
        assert isinstance(recs, list)


# ============================================================
# Helper methods
# ============================================================

class TestHelperMethods:
    def test_extract_keywords_removes_stops(self, evaluator):
        kw = evaluator._extract_keywords("le chat est un animal domestique")
        assert "le" not in kw
        assert "est" not in kw
        assert "chat" in kw

    def test_extract_keywords_filters_short(self, evaluator):
        kw = evaluator._extract_keywords("le bon roi")
        assert "bon" not in kw  # len <= 3
        assert "roi" not in kw  # len <= 3

    def test_average_sentence_length(self, evaluator):
        avg = evaluator._average_sentence_length("A B C. D E.")
        assert avg == 2.5  # (3 + 2) / 2

    def test_average_sentence_length_empty(self, evaluator):
        assert evaluator._average_sentence_length("") == 0.0

    def test_has_structure_true(self, evaluator):
        assert evaluator._has_structure("Premièrement, cela est faux.") is True

    def test_has_structure_false(self, evaluator):
        assert evaluator._has_structure("Cela est faux.") is False

    def test_vocabulary_complexity_simple(self, evaluator):
        score = evaluator._vocabulary_complexity("un chat simple")
        assert score < 0.3

    def test_vocabulary_complexity_complex(self, evaluator):
        score = evaluator._vocabulary_complexity("paradigme ontologie épistémologie herméneutique")
        assert score > 0.3

    def test_vocabulary_complexity_empty(self, evaluator):
        assert evaluator._vocabulary_complexity("") == 0.0
