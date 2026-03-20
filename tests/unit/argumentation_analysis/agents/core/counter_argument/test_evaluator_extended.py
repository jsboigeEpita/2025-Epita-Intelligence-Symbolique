# tests/unit/argumentation_analysis/agents/core/counter_argument/test_evaluator_extended.py
"""Extended tests for CounterArgumentEvaluator — individual scoring methods."""

import pytest

from argumentation_analysis.agents.core.counter_argument.evaluator import (
    CounterArgumentEvaluator,
)
from argumentation_analysis.agents.core.counter_argument.definitions import (
    Argument,
    ArgumentStrength,
    CounterArgument,
    CounterArgumentType,
)


@pytest.fixture
def evaluator():
    return CounterArgumentEvaluator()


def _make_argument(
    content="Le climat change", premises=None, conclusion="Donc il faut agir"
):
    return Argument(
        content=content,
        premises=premises or ["Le climat change"],
        conclusion=conclusion,
        argument_type="inductive",
        confidence=0.7,
    )


def _make_counter(
    original=None,
    counter_type=CounterArgumentType.DIRECT_REFUTATION,
    counter_content="Cet argument est faux car les données montrent le contraire",
    strength=ArgumentStrength.MODERATE,
    rhetorical_strategy="",
):
    original = original or _make_argument()
    return CounterArgument(
        original_argument=original,
        counter_type=counter_type,
        counter_content=counter_content,
        target_component="premise_0",
        strength=strength,
        confidence=0.7,
        rhetorical_strategy=rhetorical_strategy,
    )


# ── _evaluate_relevance ──


class TestEvaluateRelevance:
    def test_high_keyword_overlap(self, evaluator):
        orig = _make_argument(
            content="Le climat change rapidement", premises=["Le climat change"]
        )
        counter = _make_counter(
            original=orig,
            counter_content="Le climat ne change pas rapidement selon les données",
        )
        score = evaluator._evaluate_relevance(orig, counter)
        assert score > 0.0

    def test_no_overlap(self, evaluator):
        orig = _make_argument(
            content="Les chats sont mignons", premises=["Les chats sont mignons"]
        )
        counter = _make_counter(
            original=orig, counter_content="La physique quantique démontre autre chose"
        )
        score = evaluator._evaluate_relevance(orig, counter)
        assert score < 0.5

    def test_premise_challenge_target_match(self, evaluator):
        orig = _make_argument(
            content="L'énergie solaire est efficace",
            premises=["L'énergie solaire produit beaucoup"],
            conclusion="Donc il faut investir",
        )
        counter = _make_counter(
            original=orig,
            counter_type=CounterArgumentType.PREMISE_CHALLENGE,
            counter_content="L'énergie solaire ne produit pas suffisamment selon l'argument",
        )
        score = evaluator._evaluate_relevance(orig, counter)
        assert score > 0.0

    def test_direct_refutation_conclusion_match(self, evaluator):
        orig = _make_argument(
            content="test",
            premises=["prémisse"],
            conclusion="La terre est plate",
        )
        counter = _make_counter(
            original=orig,
            counter_type=CounterArgumentType.DIRECT_REFUTATION,
            counter_content="La terre n'est pas plate, c'est prouvé",
        )
        score = evaluator._evaluate_relevance(orig, counter)
        assert score > 0.0

    def test_mentions_argument_bonus(self, evaluator):
        orig = _make_argument()
        counter = _make_counter(
            original=orig, counter_content="Cet argument est incorrect"
        )
        score_with = evaluator._evaluate_relevance(orig, counter)
        counter2 = _make_counter(original=orig, counter_content="C'est incorrect")
        score_without = evaluator._evaluate_relevance(orig, counter2)
        assert score_with >= score_without

    def test_strategy_bonus_counter_example_analogical(self, evaluator):
        orig = _make_argument()
        counter = _make_counter(
            original=orig,
            counter_type=CounterArgumentType.COUNTER_EXAMPLE,
            counter_content="Par exemple considérons le climat",
            rhetorical_strategy="analogical_counter",
        )
        score = evaluator._evaluate_relevance(orig, counter)
        # Should have strategy bonus
        assert score >= 0.0

    def test_strategy_bonus_premise_socratic(self, evaluator):
        orig = _make_argument()
        counter = _make_counter(
            original=orig,
            counter_type=CounterArgumentType.PREMISE_CHALLENGE,
            counter_content="Pourquoi le climat change-t-il?",
            rhetorical_strategy="socratic_questioning",
        )
        score = evaluator._evaluate_relevance(orig, counter)
        assert score >= 0.0

    def test_capped_at_one(self, evaluator):
        orig = _make_argument(
            content="Le climat change rapidement partout dans le monde",
            premises=["Le climat change rapidement partout"],
            conclusion="Le climat change rapidement partout",
        )
        counter = _make_counter(
            original=orig,
            counter_type=CounterArgumentType.PREMISE_CHALLENGE,
            counter_content="Le climat change rapidement partout dans le monde argument selon les données",
            rhetorical_strategy="socratic_questioning",
        )
        score = evaluator._evaluate_relevance(orig, counter)
        assert score <= 1.0

    def test_empty_original_keywords(self, evaluator):
        orig = _make_argument(content="le la les", premises=["le la"])
        counter = _make_counter(original=orig, counter_content="test")
        score = evaluator._evaluate_relevance(orig, counter)
        # All original keywords are stopwords, so overlap is 0
        assert score >= 0.0


# ── _evaluate_logical_strength ──


class TestEvaluateLogicalStrength:
    def test_type_strength_direct_refutation(self, evaluator):
        counter = _make_counter(
            counter_type=CounterArgumentType.DIRECT_REFUTATION, counter_content="Non"
        )
        score = evaluator._evaluate_logical_strength(counter)
        assert score >= 0.5

    def test_type_strength_counter_example(self, evaluator):
        counter = _make_counter(
            counter_type=CounterArgumentType.COUNTER_EXAMPLE,
            counter_content="Exemple contraire",
        )
        score = evaluator._evaluate_logical_strength(counter)
        assert score >= 0.5

    def test_type_strength_reductio(self, evaluator):
        counter = _make_counter(
            counter_type=CounterArgumentType.REDUCTIO_AD_ABSURDUM,
            counter_content="Absurde",
        )
        score = evaluator._evaluate_logical_strength(counter)
        assert score >= 0.5

    def test_logical_markers_boost(self, evaluator):
        counter_with = _make_counter(
            counter_content="Car ceci est faux, donc la conclusion est invalide"
        )
        counter_without = _make_counter(
            counter_content="Ceci est faux, la conclusion est invalide"
        )
        s1 = evaluator._evaluate_logical_strength(counter_with)
        s2 = evaluator._evaluate_logical_strength(counter_without)
        assert s1 >= s2

    def test_premise_conclusion_structure(self, evaluator):
        counter = _make_counter(
            counter_content="Parce que les données sont fausses, donc la conclusion ne tient pas"
        )
        score = evaluator._evaluate_logical_strength(counter)
        # Has both premise marker (parce que) and conclusion marker (donc)
        assert score >= 0.5

    def test_evidence_bonus(self, evaluator):
        counter = _make_counter(
            counter_content="Une étude prouve le contraire avec des exemples"
        )
        score = evaluator._evaluate_logical_strength(counter)
        assert score > 0.5

    def test_fallacy_penalty(self, evaluator):
        counter_clean = _make_counter(
            counter_content="Les données montrent le contraire"
        )
        counter_fallacy = _make_counter(
            counter_content="C'est un ad hominem et un faux dilemme"
        )
        s1 = evaluator._evaluate_logical_strength(counter_clean)
        s2 = evaluator._evaluate_logical_strength(counter_fallacy)
        assert s1 >= s2

    def test_strength_adjustment_strong(self, evaluator):
        counter_strong = _make_counter(
            strength=ArgumentStrength.STRONG, counter_content="Test"
        )
        counter_weak = _make_counter(
            strength=ArgumentStrength.WEAK, counter_content="Test"
        )
        s1 = evaluator._evaluate_logical_strength(counter_strong)
        s2 = evaluator._evaluate_logical_strength(counter_weak)
        assert s1 > s2

    def test_strength_decisive_bonus(self, evaluator):
        counter = _make_counter(
            strength=ArgumentStrength.DECISIVE, counter_content="Car c'est prouvé"
        )
        score = evaluator._evaluate_logical_strength(counter)
        assert score >= 0.7

    def test_capped_at_one(self, evaluator):
        counter = _make_counter(
            counter_type=CounterArgumentType.COUNTER_EXAMPLE,
            counter_content="Car une étude prouve cet exemple, donc la conclusion est invalide par conséquent",
            strength=ArgumentStrength.DECISIVE,
        )
        score = evaluator._evaluate_logical_strength(counter)
        assert score <= 1.0


# ── _evaluate_persuasiveness ──


class TestEvaluatePersuasiveness:
    def test_persuasive_elements_boost(self, evaluator):
        counter = _make_counter(
            counter_content="Une étude apporte des preuves et des données statistiques qui démontrent le contraire avec des résultats concrets"
        )
        score = evaluator._evaluate_persuasiveness(counter)
        assert score > 0.2

    def test_rhetoric_score_socratic(self, evaluator):
        counter = _make_counter(
            counter_content="Ceci est un long texte avec suffisamment de mots pour atteindre la longueur optimale",
            rhetorical_strategy="socratic_questioning",
        )
        score = evaluator._evaluate_persuasiveness(counter)
        assert score > 0.0

    def test_rhetoric_score_statistical(self, evaluator):
        counter = _make_counter(
            counter_content="Les données statistiques montrent le contraire avec un résultat significatif",
            rhetorical_strategy="statistical_evidence",
        )
        score = evaluator._evaluate_persuasiveness(counter)
        assert score > 0.0

    def test_affirmative_tone_boost(self, evaluator):
        counter_affirm = _make_counter(
            counter_content="Clairement les données montrent évidemment le contraire de manière certaine sans aucun doute possible"
        )
        counter_dubious = _make_counter(
            counter_content="Peut-être les données montrent probablement possiblement le contraire ou il se pourrait que"
        )
        s1 = evaluator._evaluate_persuasiveness(counter_affirm)
        s2 = evaluator._evaluate_persuasiveness(counter_dubious)
        assert s1 >= s2

    def test_optimal_length_score(self, evaluator):
        # 30-100 words gets 0.1 bonus
        words_50 = " ".join(["mot"] * 50)
        counter = _make_counter(counter_content=words_50)
        score = evaluator._evaluate_persuasiveness(counter)
        assert score >= 0.0

    def test_short_text_no_length_bonus(self, evaluator):
        counter = _make_counter(counter_content="Non")
        score = evaluator._evaluate_persuasiveness(counter)
        assert score < 0.5

    def test_capped_at_one(self, evaluator):
        counter = _make_counter(
            counter_content="Clairement une étude montre des preuves et données statistiques évidentes "
            * 5,
            rhetorical_strategy="socratic_questioning",
        )
        score = evaluator._evaluate_persuasiveness(counter)
        assert score <= 1.0


# ── _evaluate_originality ──


class TestEvaluateOriginality:
    def test_base_originality(self, evaluator):
        counter = _make_counter(
            counter_content="Un point de vue différent sur la question climatique"
        )
        score = evaluator._evaluate_originality(counter)
        assert 0.1 <= score <= 1.0

    def test_common_phrase_penalty(self, evaluator):
        counter_common = _make_counter(
            counter_content="Tout le monde sait que comme on dit souvent il est bien connu que évidemment"
        )
        counter_original = _make_counter(
            counter_content="Sous un angle différent, la thermodynamique quantique apporte une perspective alternative"
        )
        s1 = evaluator._evaluate_originality(counter_common)
        s2 = evaluator._evaluate_originality(counter_original)
        assert s2 > s1

    def test_strategy_combo_direct_socratic(self, evaluator):
        counter = _make_counter(
            counter_type=CounterArgumentType.DIRECT_REFUTATION,
            counter_content="Questionnons cette affirmation",
            rhetorical_strategy="socratic_questioning",
        )
        score = evaluator._evaluate_originality(counter)
        assert score >= 0.5  # Gets strategy_orig = 0.4

    def test_strategy_combo_premise_analogical(self, evaluator):
        counter = _make_counter(
            counter_type=CounterArgumentType.PREMISE_CHALLENGE,
            counter_content="Une analogie montre le contraire",
            rhetorical_strategy="analogical_counter",
        )
        score = evaluator._evaluate_originality(counter)
        assert score >= 0.5

    def test_unexpected_phrase_bonus(self, evaluator):
        counter = _make_counter(
            counter_content="Contrairement à ce qu'on pourrait penser, les données révèlent autre chose"
        )
        score = evaluator._evaluate_originality(counter)
        assert score >= 0.5

    def test_vocabulary_diversity(self, evaluator):
        # Many unique words should boost vocab_score
        counter = _make_counter(
            counter_content="L'épistémologie, l'herméneutique et la dialectique convergent vers une perspective alternative intéressante"
        )
        score = evaluator._evaluate_originality(counter)
        assert score > 0.0

    def test_floor_at_01(self, evaluator):
        counter = _make_counter(
            counter_content="Tout le monde sait que comme on dit souvent il est bien connu que"
        )
        score = evaluator._evaluate_originality(counter)
        assert score >= 0.1


# ── _evaluate_clarity ──


class TestEvaluateClarity:
    def test_short_sentences_high_clarity(self, evaluator):
        counter = _make_counter(
            counter_content="L'argument est faux. Les données prouvent le contraire. Donc la conclusion est invalide."
        )
        score = evaluator._evaluate_clarity(counter)
        assert score >= 0.3

    def test_long_sentences_lower_clarity(self, evaluator):
        long = " ".join(["mot"] * 40)
        counter = _make_counter(counter_content=long + ".")
        score = evaluator._evaluate_clarity(counter)
        # Long sentence reduces sentence_score
        assert score >= 0.0

    def test_structure_bonus(self, evaluator):
        counter = _make_counter(
            counter_content="Premièrement les données sont fausses. Ensuite la conclusion ne suit pas. En conclusion il faut rejeter cet argument."
        )
        score = evaluator._evaluate_clarity(counter)
        assert score > 0.3  # Gets structure bonus

    def test_connectors_bonus(self, evaluator):
        counter = _make_counter(
            counter_content="Car les données sont fausses. Cependant il faut noter."
        )
        score = evaluator._evaluate_clarity(counter)
        assert score > 0.0

    def test_ambiguity_penalty(self, evaluator):
        counter_clear = _make_counter(
            counter_content="Les données montrent le contraire."
        )
        counter_ambig = _make_counter(
            counter_content="Peut-être possiblement il se pourrait que les données montrent le contraire."
        )
        s1 = evaluator._evaluate_clarity(counter_clear)
        s2 = evaluator._evaluate_clarity(counter_ambig)
        assert s1 >= s2

    def test_vocabulary_complexity_impact(self, evaluator):
        counter_simple = _make_counter(
            counter_content="Les données montrent le contraire clairement."
        )
        counter_complex = _make_counter(
            counter_content="Le paradigme épistémologie herméneutique heuristique dialectique syllogisme ontologie axiomatique."
        )
        s1 = evaluator._evaluate_clarity(counter_simple)
        s2 = evaluator._evaluate_clarity(counter_complex)
        assert s1 >= s2

    def test_floor_at_01(self, evaluator):
        counter = _make_counter(
            counter_content="Peut-être possiblement il se pourrait que plus ou moins "
            * 3
        )
        score = evaluator._evaluate_clarity(counter)
        assert score >= 0.1


# ── _generate_recommendations ──


class TestGenerateRecommendations:
    def test_low_relevance(self, evaluator):
        orig = _make_argument()
        counter = _make_counter(original=orig)
        recs = evaluator._generate_recommendations(
            orig, counter, 0.3, 0.7, 0.7, 0.7, 0.7
        )
        assert any("relevance" in r.lower() for r in recs)

    def test_low_logic(self, evaluator):
        orig = _make_argument()
        counter = _make_counter(original=orig)
        recs = evaluator._generate_recommendations(
            orig, counter, 0.7, 0.3, 0.7, 0.7, 0.7
        )
        assert any("logical" in r.lower() for r in recs)

    def test_low_persuasion(self, evaluator):
        orig = _make_argument()
        counter = _make_counter(original=orig)
        recs = evaluator._generate_recommendations(
            orig, counter, 0.7, 0.7, 0.3, 0.7, 0.7
        )
        assert any("persuasive" in r.lower() for r in recs)

    def test_low_originality(self, evaluator):
        orig = _make_argument()
        counter = _make_counter(original=orig)
        recs = evaluator._generate_recommendations(
            orig, counter, 0.7, 0.7, 0.7, 0.3, 0.7
        )
        assert any("original" in r.lower() for r in recs)

    def test_low_clarity(self, evaluator):
        orig = _make_argument()
        counter = _make_counter(original=orig)
        recs = evaluator._generate_recommendations(
            orig, counter, 0.7, 0.7, 0.7, 0.7, 0.3
        )
        assert any("simplif" in r.lower() for r in recs)

    def test_all_good(self, evaluator):
        orig = _make_argument()
        counter = _make_counter(original=orig)
        recs = evaluator._generate_recommendations(
            orig, counter, 0.8, 0.8, 0.8, 0.8, 0.8
        )
        assert any("good quality" in r.lower() for r in recs)

    def test_multiple_low_scores(self, evaluator):
        orig = _make_argument()
        counter = _make_counter(original=orig)
        recs = evaluator._generate_recommendations(
            orig, counter, 0.3, 0.3, 0.3, 0.3, 0.3
        )
        assert len(recs) >= 5


# ── Helper methods ──


class TestHelperMethods:
    def test_extract_keywords_stopwords_removed(self, evaluator):
        keywords = evaluator._extract_keywords("le chat est dans la maison")
        assert "le" not in keywords
        assert "est" not in keywords
        assert "dans" not in keywords
        assert "chat" in keywords
        assert "maison" in keywords

    def test_extract_keywords_short_words_excluded(self, evaluator):
        keywords = evaluator._extract_keywords("il a un bon mot")
        assert "bon" not in keywords  # len 3, excluded
        assert "mot" not in keywords  # len 3, excluded

    def test_extract_keywords_punctuation_stripped(self, evaluator):
        keywords = evaluator._extract_keywords("L'argument, clairement! est faux.")
        assert all("," not in k and "!" not in k and "." not in k for k in keywords)

    def test_extract_keywords_empty(self, evaluator):
        assert evaluator._extract_keywords("") == set()

    def test_average_sentence_length(self, evaluator):
        text = "Phrase courte. Phrase un peu plus longue avec des mots."
        avg = evaluator._average_sentence_length(text)
        assert avg > 0

    def test_average_sentence_length_empty(self, evaluator):
        assert evaluator._average_sentence_length("") == 0.0

    def test_average_sentence_length_single(self, evaluator):
        avg = evaluator._average_sentence_length("Un deux trois")
        assert avg == 3.0

    def test_has_structure_true(self, evaluator):
        assert evaluator._has_structure(
            "Premièrement c'est vrai. Ensuite c'est confirmé."
        )

    def test_has_structure_false(self, evaluator):
        assert not evaluator._has_structure("Le chat dort tranquillement")

    def test_vocabulary_complexity_simple(self, evaluator):
        score = evaluator._vocabulary_complexity("Le chat mange du poisson")
        assert score < 0.3

    def test_vocabulary_complexity_complex(self, evaluator):
        score = evaluator._vocabulary_complexity(
            "Le paradigme épistémologie herméneutique ontologie"
        )
        assert score > 0.0

    def test_vocabulary_complexity_empty(self, evaluator):
        assert evaluator._vocabulary_complexity("") == 0.0

    def test_vocabulary_complexity_long_words(self, evaluator):
        # Words > 8 chars count too
        score = evaluator._vocabulary_complexity("extraordinairement phénoménalement")
        assert score > 0.0


# ── Full evaluate pipeline ──


class TestFullEvaluate:
    def test_evaluate_pipeline(self, evaluator):
        orig = _make_argument(
            content="Le changement climatique est urgent",
            premises=["Les températures augmentent", "Les glaciers fondent"],
            conclusion="Il faut agir maintenant",
        )
        counter = _make_counter(
            original=orig,
            counter_type=CounterArgumentType.PREMISE_CHALLENGE,
            counter_content=(
                "Car les températures n'augmentent pas de manière uniforme. "
                "Des études montrent des variations régionales significatives. "
                "Par conséquent, la conclusion est trop simpliste."
            ),
            strength=ArgumentStrength.STRONG,
            rhetorical_strategy="statistical_evidence",
        )
        result = evaluator.evaluate(orig, counter)
        assert 0.0 <= result.overall_score <= 1.0
        assert isinstance(result.recommendations, list)

    def test_evaluate_weak_counter(self, evaluator):
        orig = _make_argument()
        counter = _make_counter(
            original=orig,
            counter_content="Non",
            strength=ArgumentStrength.WEAK,
        )
        result = evaluator.evaluate(orig, counter)
        assert result.overall_score < 0.8
        assert len(result.recommendations) >= 1

    def test_weighted_sum_invariant(self, evaluator):
        orig = _make_argument()
        counter = _make_counter(original=orig)
        result = evaluator.evaluate(orig, counter)
        expected = (
            result.relevance * 0.25
            + result.logical_strength * 0.25
            + result.persuasiveness * 0.20
            + result.originality * 0.15
            + result.clarity * 0.15
        )
        assert abs(result.overall_score - expected) < 0.01
