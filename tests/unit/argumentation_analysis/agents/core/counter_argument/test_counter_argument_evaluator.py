# tests/unit/argumentation_analysis/agents/core/counter_argument/test_counter_argument_evaluator.py
"""Tests for CounterArgumentEvaluator — 5-criteria weighted evaluation."""

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


@pytest.fixture
def original_argument():
    return Argument(
        content="Les vaccins sont dangereux car ils contiennent des produits chimiques.",
        premises=["Les vaccins contiennent des produits chimiques"],
        conclusion="Les vaccins sont dangereux",
        argument_type="inductive",
        confidence=0.7,
    )


@pytest.fixture
def counter_argument(original_argument):
    return CounterArgument(
        original_argument=original_argument,
        counter_type=CounterArgumentType.DIRECT_REFUTATION,
        counter_content="Les vaccins sont sûrs car de nombreuses études scientifiques ont prouvé leur efficacité. Par conséquent, l'argument initial est invalide.",
        target_component="conclusion",
        strength=ArgumentStrength.STRONG,
        confidence=0.9,
        supporting_evidence=["OMS", "études cliniques"],
        rhetorical_strategy="socratic_questioning",
    )


# ── Init ──

class TestEvaluatorInit:
    def test_criteria_weights(self, evaluator):
        assert evaluator.evaluation_criteria["relevance"] == 0.25
        assert evaluator.evaluation_criteria["logical_strength"] == 0.25
        assert evaluator.evaluation_criteria["persuasiveness"] == 0.20
        assert evaluator.evaluation_criteria["originality"] == 0.15
        assert evaluator.evaluation_criteria["clarity"] == 0.15

    def test_weights_sum_to_one(self, evaluator):
        total = sum(evaluator.evaluation_criteria.values())
        assert abs(total - 1.0) < 1e-9

    def test_has_persuasive_elements(self, evaluator):
        assert len(evaluator.persuasive_elements) > 0
        assert "preuve" in evaluator.persuasive_elements

    def test_has_logical_markers(self, evaluator):
        assert len(evaluator.logical_markers) > 0
        assert "donc" in evaluator.logical_markers


# ── evaluate (full pipeline) ──

class TestEvaluate:
    def test_returns_evaluation_result(self, evaluator, original_argument, counter_argument):
        result = evaluator.evaluate(original_argument, counter_argument)
        assert isinstance(result, EvaluationResult)

    def test_overall_score_range(self, evaluator, original_argument, counter_argument):
        result = evaluator.evaluate(original_argument, counter_argument)
        assert 0.0 <= result.overall_score <= 1.0

    def test_all_criteria_populated(self, evaluator, original_argument, counter_argument):
        result = evaluator.evaluate(original_argument, counter_argument)
        assert 0.0 <= result.relevance <= 1.0
        assert 0.0 <= result.logical_strength <= 1.0
        assert 0.0 <= result.persuasiveness <= 1.0
        assert 0.0 <= result.originality <= 1.0
        assert 0.0 <= result.clarity <= 1.0

    def test_recommendations_list(self, evaluator, original_argument, counter_argument):
        result = evaluator.evaluate(original_argument, counter_argument)
        assert isinstance(result.recommendations, list)

    def test_overall_is_weighted_sum(self, evaluator, original_argument, counter_argument):
        result = evaluator.evaluate(original_argument, counter_argument)
        expected = (
            result.relevance * 0.25
            + result.logical_strength * 0.25
            + result.persuasiveness * 0.20
            + result.originality * 0.15
            + result.clarity * 0.15
        )
        assert abs(result.overall_score - expected) < 1e-9


# ── _evaluate_relevance ──

class TestEvaluateRelevance:
    def test_high_keyword_overlap(self, evaluator, original_argument):
        ca = CounterArgument(
            original_argument=original_argument,
            counter_type=CounterArgumentType.DIRECT_REFUTATION,
            counter_content="Les vaccins ne sont pas dangereux car les produits chimiques sont contrôlés.",
            target_component="conclusion",
            strength=ArgumentStrength.MODERATE,
            confidence=0.7,
        )
        score = evaluator._evaluate_relevance(original_argument, ca)
        assert score > 0.0

    def test_no_overlap(self, evaluator, original_argument):
        ca = CounterArgument(
            original_argument=original_argument,
            counter_type=CounterArgumentType.COUNTER_EXAMPLE,
            counter_content="Le football est un sport populaire dans le monde entier.",
            target_component="premise",
            strength=ArgumentStrength.WEAK,
            confidence=0.3,
        )
        score = evaluator._evaluate_relevance(original_argument, ca)
        assert score < 0.5

    def test_premise_challenge_relevance(self, evaluator, original_argument):
        ca = CounterArgument(
            original_argument=original_argument,
            counter_type=CounterArgumentType.PREMISE_CHALLENGE,
            counter_content="Les produits chimiques dans les vaccins sont en quantités infimes et ne sont pas dangereux.",
            target_component="premise_0",
            strength=ArgumentStrength.STRONG,
            confidence=0.8,
            rhetorical_strategy="socratic_questioning",
        )
        score = evaluator._evaluate_relevance(original_argument, ca)
        assert score > 0.0

    def test_mentions_argument_bonus(self, evaluator, original_argument):
        ca1 = CounterArgument(
            original_argument=original_argument,
            counter_type=CounterArgumentType.DIRECT_REFUTATION,
            counter_content="Cet argument est faux.",
            target_component="conclusion",
            strength=ArgumentStrength.MODERATE,
            confidence=0.5,
        )
        ca2 = CounterArgument(
            original_argument=original_argument,
            counter_type=CounterArgumentType.DIRECT_REFUTATION,
            counter_content="C'est faux.",
            target_component="conclusion",
            strength=ArgumentStrength.MODERATE,
            confidence=0.5,
        )
        s1 = evaluator._evaluate_relevance(original_argument, ca1)
        s2 = evaluator._evaluate_relevance(original_argument, ca2)
        assert s1 >= s2  # "argument" mention gives 0.1 bonus

    def test_counter_example_analogical_bonus(self, evaluator, original_argument):
        ca = CounterArgument(
            original_argument=original_argument,
            counter_type=CounterArgumentType.COUNTER_EXAMPLE,
            counter_content="Un cas analogical montre le contraire des vaccins et produits chimiques.",
            target_component="premise",
            strength=ArgumentStrength.MODERATE,
            confidence=0.6,
            rhetorical_strategy="analogical_counter",
        )
        score = evaluator._evaluate_relevance(original_argument, ca)
        assert score <= 1.0

    def test_max_one(self, evaluator, original_argument):
        ca = CounterArgument(
            original_argument=original_argument,
            counter_type=CounterArgumentType.PREMISE_CHALLENGE,
            counter_content="Cet argument sur les vaccins dangereux et les produits chimiques est faux. Les vaccins contiennent des produits chimiques sûrs.",
            target_component="premise",
            strength=ArgumentStrength.DECISIVE,
            confidence=0.99,
            rhetorical_strategy="socratic_questioning",
        )
        score = evaluator._evaluate_relevance(original_argument, ca)
        assert score <= 1.0


# ── _evaluate_logical_strength ──

class TestEvaluateLogicalStrength:
    def test_direct_refutation_base(self, evaluator, original_argument):
        ca = CounterArgument(
            original_argument=original_argument,
            counter_type=CounterArgumentType.DIRECT_REFUTATION,
            counter_content="Simple text.",
            target_component="conclusion",
            strength=ArgumentStrength.MODERATE,
            confidence=0.5,
        )
        score = evaluator._evaluate_logical_strength(ca)
        assert score >= 0.7  # base for direct refutation

    def test_counter_example_base(self, evaluator, original_argument):
        ca = CounterArgument(
            original_argument=original_argument,
            counter_type=CounterArgumentType.COUNTER_EXAMPLE,
            counter_content="Simple text.",
            target_component="premise",
            strength=ArgumentStrength.MODERATE,
            confidence=0.5,
        )
        score = evaluator._evaluate_logical_strength(ca)
        assert score >= 0.8

    def test_logical_markers_bonus(self, evaluator, original_argument):
        ca = CounterArgument(
            original_argument=original_argument,
            counter_type=CounterArgumentType.DIRECT_REFUTATION,
            counter_content="C'est faux car les preuves montrent donc que...",
            target_component="conclusion",
            strength=ArgumentStrength.MODERATE,
            confidence=0.5,
        )
        score = evaluator._evaluate_logical_strength(ca)
        assert score > 0.7  # base + markers

    def test_evidence_bonus(self, evaluator, original_argument):
        ca = CounterArgument(
            original_argument=original_argument,
            counter_type=CounterArgumentType.DIRECT_REFUTATION,
            counter_content="La preuve montre que cette étude est fausse.",
            target_component="conclusion",
            strength=ArgumentStrength.MODERATE,
            confidence=0.5,
        )
        score = evaluator._evaluate_logical_strength(ca)
        assert score > 0.7

    def test_fallacy_penalty(self, evaluator, original_argument):
        ca_clean = CounterArgument(
            original_argument=original_argument,
            counter_type=CounterArgumentType.DIRECT_REFUTATION,
            counter_content="Simple clean text.",
            target_component="conclusion",
            strength=ArgumentStrength.MODERATE,
            confidence=0.5,
        )
        ca_fallacy = CounterArgument(
            original_argument=original_argument,
            counter_type=CounterArgumentType.DIRECT_REFUTATION,
            counter_content="C'est un ad hominem évident.",
            target_component="conclusion",
            strength=ArgumentStrength.MODERATE,
            confidence=0.5,
        )
        s_clean = evaluator._evaluate_logical_strength(ca_clean)
        s_fallacy = evaluator._evaluate_logical_strength(ca_fallacy)
        assert s_clean >= s_fallacy

    def test_strength_adjustment(self, evaluator, original_argument):
        ca_strong = CounterArgument(
            original_argument=original_argument,
            counter_type=CounterArgumentType.DIRECT_REFUTATION,
            counter_content="Simple text.",
            target_component="conclusion",
            strength=ArgumentStrength.DECISIVE,
            confidence=0.9,
        )
        ca_weak = CounterArgument(
            original_argument=original_argument,
            counter_type=CounterArgumentType.DIRECT_REFUTATION,
            counter_content="Simple text.",
            target_component="conclusion",
            strength=ArgumentStrength.WEAK,
            confidence=0.3,
        )
        s_strong = evaluator._evaluate_logical_strength(ca_strong)
        s_weak = evaluator._evaluate_logical_strength(ca_weak)
        assert s_strong > s_weak

    def test_max_one(self, evaluator, original_argument):
        ca = CounterArgument(
            original_argument=original_argument,
            counter_type=CounterArgumentType.COUNTER_EXAMPLE,
            counter_content="Car la preuve et l'exemple et l'étude donc montrent par conséquent...",
            target_component="conclusion",
            strength=ArgumentStrength.DECISIVE,
            confidence=0.99,
        )
        score = evaluator._evaluate_logical_strength(ca)
        assert score <= 1.0


# ── _evaluate_persuasiveness ──

class TestEvaluatePersuasiveness:
    def test_with_persuasive_elements(self, evaluator, original_argument):
        ca = CounterArgument(
            original_argument=original_argument,
            counter_type=CounterArgumentType.DIRECT_REFUTATION,
            counter_content="Une étude scientifique apporte la preuve que les données montrent le contraire. Les experts et la recherche confirment cette analyse basée sur les résultats.",
            target_component="conclusion",
            strength=ArgumentStrength.STRONG,
            confidence=0.8,
        )
        score = evaluator._evaluate_persuasiveness(ca)
        assert score > 0.3

    def test_no_persuasive_elements(self, evaluator, original_argument):
        ca = CounterArgument(
            original_argument=original_argument,
            counter_type=CounterArgumentType.DIRECT_REFUTATION,
            counter_content="Non.",
            target_component="conclusion",
            strength=ArgumentStrength.WEAK,
            confidence=0.3,
        )
        score = evaluator._evaluate_persuasiveness(ca)
        assert score >= 0.0

    def test_rhetoric_strategy_bonus(self, evaluator, original_argument):
        ca = CounterArgument(
            original_argument=original_argument,
            counter_type=CounterArgumentType.DIRECT_REFUTATION,
            counter_content="Cela montre le contraire.",
            target_component="conclusion",
            strength=ArgumentStrength.MODERATE,
            confidence=0.5,
            rhetorical_strategy="socratic_questioning",
        )
        score = evaluator._evaluate_persuasiveness(ca)
        assert score >= 0.0

    def test_optimal_length_bonus(self, evaluator, original_argument):
        # 30-100 words gives 0.1 bonus
        words = " ".join(["mot"] * 50)
        ca = CounterArgument(
            original_argument=original_argument,
            counter_type=CounterArgumentType.DIRECT_REFUTATION,
            counter_content=words,
            target_component="conclusion",
            strength=ArgumentStrength.MODERATE,
            confidence=0.5,
        )
        score = evaluator._evaluate_persuasiveness(ca)
        assert score >= 0.0

    def test_max_one(self, evaluator, original_argument):
        words = "preuve étude données expert recherche statistique évidence démontré prouvé consensus observation expérience analyse résultat exemple"
        ca = CounterArgument(
            original_argument=original_argument,
            counter_type=CounterArgumentType.DIRECT_REFUTATION,
            counter_content=f"Clairement certainement évidemment {words}. " * 5,
            target_component="conclusion",
            strength=ArgumentStrength.DECISIVE,
            confidence=0.99,
            rhetorical_strategy="statistical_evidence",
        )
        score = evaluator._evaluate_persuasiveness(ca)
        assert score <= 1.0


# ── _evaluate_originality ──

class TestEvaluateOriginality:
    def test_base_originality(self, evaluator, original_argument):
        ca = CounterArgument(
            original_argument=original_argument,
            counter_type=CounterArgumentType.DIRECT_REFUTATION,
            counter_content="Un texte original unique.",
            target_component="conclusion",
            strength=ArgumentStrength.MODERATE,
            confidence=0.5,
        )
        score = evaluator._evaluate_originality(ca)
        assert score >= 0.1

    def test_common_phrases_penalty(self, evaluator, original_argument):
        ca = CounterArgument(
            original_argument=original_argument,
            counter_type=CounterArgumentType.DIRECT_REFUTATION,
            counter_content="Tout le monde sait que évidemment bien entendu.",
            target_component="conclusion",
            strength=ArgumentStrength.MODERATE,
            confidence=0.5,
        )
        score = evaluator._evaluate_originality(ca)
        assert score < 0.9  # penalty applied

    def test_unexpected_angle_bonus(self, evaluator, original_argument):
        ca = CounterArgument(
            original_argument=original_argument,
            counter_type=CounterArgumentType.DIRECT_REFUTATION,
            counter_content="Contrairement à ce qu'on pourrait penser, les vaccins sont sûrs.",
            target_component="conclusion",
            strength=ArgumentStrength.MODERATE,
            confidence=0.5,
        )
        score = evaluator._evaluate_originality(ca)
        assert score > 0.5

    def test_strategy_originality_bonus(self, evaluator, original_argument):
        ca = CounterArgument(
            original_argument=original_argument,
            counter_type=CounterArgumentType.DIRECT_REFUTATION,
            counter_content="Texte simple et clair.",
            target_component="conclusion",
            strength=ArgumentStrength.MODERATE,
            confidence=0.5,
            rhetorical_strategy="socratic_questioning",
        )
        score = evaluator._evaluate_originality(ca)
        assert score >= 0.1

    def test_min_originality(self, evaluator, original_argument):
        ca = CounterArgument(
            original_argument=original_argument,
            counter_type=CounterArgumentType.DIRECT_REFUTATION,
            counter_content="a",
            target_component="conclusion",
            strength=ArgumentStrength.WEAK,
            confidence=0.1,
        )
        score = evaluator._evaluate_originality(ca)
        assert score >= 0.1

    def test_max_one(self, evaluator, original_argument):
        ca = CounterArgument(
            original_argument=original_argument,
            counter_type=CounterArgumentType.DIRECT_REFUTATION,
            counter_content="Contrairement à ce qu'on pourrait penser, sous un angle différent et avec une perspective alternative, voici un texte extrêmement original et unique avec vocabulaire varié.",
            target_component="conclusion",
            strength=ArgumentStrength.DECISIVE,
            confidence=0.99,
            rhetorical_strategy="socratic_questioning",
        )
        score = evaluator._evaluate_originality(ca)
        assert score <= 1.0


# ── _evaluate_clarity ──

class TestEvaluateClarity:
    def test_short_sentences_clear(self, evaluator, original_argument):
        ca = CounterArgument(
            original_argument=original_argument,
            counter_type=CounterArgumentType.DIRECT_REFUTATION,
            counter_content="C'est faux. Les faits montrent le contraire. Car la science le prouve.",
            target_component="conclusion",
            strength=ArgumentStrength.MODERATE,
            confidence=0.5,
        )
        score = evaluator._evaluate_clarity(ca)
        assert score > 0.3

    def test_ambiguity_penalty(self, evaluator, original_argument):
        ca = CounterArgument(
            original_argument=original_argument,
            counter_type=CounterArgumentType.DIRECT_REFUTATION,
            counter_content="Peut-être que possiblement il se pourrait que plus ou moins.",
            target_component="conclusion",
            strength=ArgumentStrength.WEAK,
            confidence=0.3,
        )
        score = evaluator._evaluate_clarity(ca)
        # Low due to ambiguity
        assert score >= 0.1

    def test_structured_text_bonus(self, evaluator, original_argument):
        ca = CounterArgument(
            original_argument=original_argument,
            counter_type=CounterArgumentType.DIRECT_REFUTATION,
            counter_content="Premièrement les faits. Ensuite les preuves. En conclusion c'est faux.",
            target_component="conclusion",
            strength=ArgumentStrength.MODERATE,
            confidence=0.5,
        )
        score = evaluator._evaluate_clarity(ca)
        assert score > 0.3

    def test_connector_bonus(self, evaluator, original_argument):
        ca = CounterArgument(
            original_argument=original_argument,
            counter_type=CounterArgumentType.DIRECT_REFUTATION,
            counter_content="Cependant les données montrent le contraire.",
            target_component="conclusion",
            strength=ArgumentStrength.MODERATE,
            confidence=0.5,
        )
        score = evaluator._evaluate_clarity(ca)
        assert score > 0.0

    def test_min_clarity(self, evaluator, original_argument):
        ca = CounterArgument(
            original_argument=original_argument,
            counter_type=CounterArgumentType.DIRECT_REFUTATION,
            counter_content="a",
            target_component="conclusion",
            strength=ArgumentStrength.WEAK,
            confidence=0.1,
        )
        score = evaluator._evaluate_clarity(ca)
        assert score >= 0.1

    def test_max_one(self, evaluator, original_argument):
        ca = CounterArgument(
            original_argument=original_argument,
            counter_type=CounterArgumentType.DIRECT_REFUTATION,
            counter_content="Premièrement c'est faux. Ensuite car les données. De plus en effet. Cependant toutefois néanmoins.",
            target_component="conclusion",
            strength=ArgumentStrength.MODERATE,
            confidence=0.5,
        )
        score = evaluator._evaluate_clarity(ca)
        assert score <= 1.0


# ── _generate_recommendations ──

class TestGenerateRecommendations:
    def test_low_relevance_recommendation(self, evaluator, original_argument, counter_argument):
        recs = evaluator._generate_recommendations(
            original_argument, counter_argument, 0.3, 0.8, 0.8, 0.8, 0.8
        )
        assert any("relevance" in r.lower() for r in recs)

    def test_low_logic_recommendation(self, evaluator, original_argument, counter_argument):
        recs = evaluator._generate_recommendations(
            original_argument, counter_argument, 0.8, 0.3, 0.8, 0.8, 0.8
        )
        assert any("logical" in r.lower() for r in recs)

    def test_low_persuasion_recommendation(self, evaluator, original_argument, counter_argument):
        recs = evaluator._generate_recommendations(
            original_argument, counter_argument, 0.8, 0.8, 0.3, 0.8, 0.8
        )
        assert any("persuasive" in r.lower() for r in recs)

    def test_low_originality_recommendation(self, evaluator, original_argument, counter_argument):
        recs = evaluator._generate_recommendations(
            original_argument, counter_argument, 0.8, 0.8, 0.8, 0.3, 0.8
        )
        assert any("original" in r.lower() for r in recs)

    def test_low_clarity_recommendation(self, evaluator, original_argument, counter_argument):
        recs = evaluator._generate_recommendations(
            original_argument, counter_argument, 0.8, 0.8, 0.8, 0.8, 0.3
        )
        assert any("simplif" in r.lower() for r in recs)

    def test_all_good_recommendation(self, evaluator, original_argument, counter_argument):
        recs = evaluator._generate_recommendations(
            original_argument, counter_argument, 0.8, 0.8, 0.8, 0.8, 0.8
        )
        assert any("good quality" in r.lower() for r in recs)

    def test_multiple_low_multiple_recs(self, evaluator, original_argument, counter_argument):
        recs = evaluator._generate_recommendations(
            original_argument, counter_argument, 0.3, 0.3, 0.3, 0.3, 0.3
        )
        assert len(recs) >= 5


# ── Helper methods ──

class TestHelperMethods:
    def test_extract_keywords(self, evaluator):
        kw = evaluator._extract_keywords("Les vaccins sont dangereux")
        assert isinstance(kw, set)
        assert "vaccins" in kw
        assert "dangereux" in kw
        assert "les" not in kw
        assert "sont" not in kw

    def test_extract_keywords_empty(self, evaluator):
        assert evaluator._extract_keywords("") == set()

    def test_average_sentence_length(self, evaluator):
        avg = evaluator._average_sentence_length("Hello world. Goodbye world.")
        assert avg == 2.0

    def test_average_sentence_length_empty(self, evaluator):
        assert evaluator._average_sentence_length("") == 0.0

    def test_has_structure_true(self, evaluator):
        assert evaluator._has_structure("Premièrement, nous voyons que...") is True

    def test_has_structure_false(self, evaluator):
        assert evaluator._has_structure("Simple text only.") is False

    def test_vocabulary_complexity_simple(self, evaluator):
        c = evaluator._vocabulary_complexity("Le chat est sur la table.")
        assert c < 0.3

    def test_vocabulary_complexity_complex(self, evaluator):
        c = evaluator._vocabulary_complexity("L'épistémologie et l'ontologie du paradigme herméneutique.")
        assert c > 0.0

    def test_vocabulary_complexity_empty(self, evaluator):
        assert evaluator._vocabulary_complexity("") == 0.0
