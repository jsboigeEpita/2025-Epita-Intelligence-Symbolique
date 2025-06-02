# -*- coding: utf-8 -*-
"""Tests pour le MockCoherenceAnalyzer."""

import pytest
import logging
from argumentation_analysis.mocks.coherence_analysis import MockCoherenceAnalyzer

@pytest.fixture
def analyzer_default() -> MockCoherenceAnalyzer:
    """Instance de MockCoherenceAnalyzer avec config par défaut."""
    return MockCoherenceAnalyzer()

@pytest.fixture
def analyzer_custom_config() -> MockCoherenceAnalyzer:
    """Instance avec une configuration personnalisée."""
    config = {
        "coherence_factors": {"contradiction_penalty": -0.8}, # Override
        "transition_words": ["donc_custom", "ainsi_custom"],
        "contradiction_pairs": [("aime_custom", "déteste_custom")]
    }
    return MockCoherenceAnalyzer(config=config)

def test_initialization_default(analyzer_default: MockCoherenceAnalyzer):
    """Teste l'initialisation avec la configuration par défaut."""
    assert analyzer_default.get_config() == {}
    assert "transition_words_ratio" in analyzer_default.coherence_factors
    assert analyzer_default.coherence_factors["contradiction_penalty"] == -0.4
    assert "donc" in analyzer_default.transition_words
    assert ("j'aime", "je n'aime pas") in analyzer_default.contradiction_pairs

def test_initialization_custom_config(analyzer_custom_config: MockCoherenceAnalyzer):
    """Teste l'initialisation avec une configuration personnalisée."""
    # Le mock actuel écrase les coherence_factors, ne fusionne pas.
    assert analyzer_custom_config.coherence_factors["contradiction_penalty"] == -0.8
    assert "transition_words_ratio" not in analyzer_custom_config.coherence_factors
    assert analyzer_custom_config.transition_words == ["donc_custom", "ainsi_custom"]
    assert analyzer_custom_config.contradiction_pairs == [("aime_custom", "déteste_custom")]

def test_analyze_coherence_non_string_or_empty_input(analyzer_default: MockCoherenceAnalyzer, caplog):
    """Teste l'analyse avec une entrée non textuelle ou vide."""
    with caplog.at_level(logging.WARNING):
        result_none = analyzer_default.analyze_coherence(None) # type: ignore
    assert "error" in result_none
    assert result_none["error"] == "Entrée non textuelle ou vide"
    assert result_none["coherence_score"] == 0.0
    assert "MockCoherenceAnalyzer.analyze_coherence a reçu une entrée non textuelle ou vide." in caplog.text
    
    caplog.clear()
    result_empty_str = analyzer_default.analyze_coherence("   ")
    assert "error" in result_empty_str # Vide après strip
    assert result_empty_str["coherence_score"] == 0.0

    caplog.clear()
    result_no_words = analyzer_default.analyze_coherence("...") # Pas de mots
    assert result_no_words["coherence_score"] == 0.0


def test_analyze_coherence_ideal_text(analyzer_default: MockCoherenceAnalyzer):
    """Teste un texte idéalement cohérent."""
    # Beaucoup de mots de transition, répétition de mots-clés, pas de contradictions.
    # Score de base 0.5
    # Transition words: "donc", "ainsi", "de plus" (3) / ~20 mots. Ratio > 0.02. Score += 0.2
    # Repeated keywords: "cohérence" (x2), "texte" (x2). Count = 2. Score += 0.15
    # Pronoun referencing (texte > 50 mots): Score += 0.1
    # Total attendu = 0.5 + 0.2 + 0.15 + 0.1 = 0.95
    text = (
        "Ce texte est un exemple de cohérence. Donc, il suit une logique claire. "
        "De plus, les idées sont bien liées. Ainsi, la cohérence du texte est assurée. "
        "La structure du texte aide aussi."
    ) # 30 mots
    result = analyzer_default.analyze_coherence(text)
    assert result["coherence_score"] == pytest.approx(0.5 + 0.2 + 0.15 + 0.1) # 0.95
    assert result["factors"]["transition_words_ratio"] > 0
    assert result["factors"]["repeated_keywords_bonus"] > 0
    assert result["factors"]["consistent_pronoun_referencing"] == 1
    assert result["interpretation"] == "Très cohérent (Mock)"

def test_analyze_coherence_transition_words(analyzer_default: MockCoherenceAnalyzer):
    """Teste l'impact des mots de transition."""
    # Score de base 0.5. Pronoms +0.1 (car > 50 mots). Total 0.6
    # 5 mots de transition / ~30 mots. Ratio > 0.02. Score += 0.2. Total = 0.8
    text_good = "Le premier point est important. Donc, nous devons le considérer. De plus, il y a un autre aspect. Par conséquent, la conclusion est évidente. Finalement, c'est clair."
    result_good = analyzer_default.analyze_coherence(text_good)
    assert result_good["factors"]["transition_words_ratio"] > 0
    assert result_good["coherence_score"] > 0.5 + 0.1 # Plus que base + pronoms
    
    text_bad = "Point un. Point deux. Point trois. Point quatre. Point cinq. Point six. Point sept." # Peu de transitions
    result_bad = analyzer_default.analyze_coherence(text_bad)
    assert result_bad["factors"]["transition_words_ratio"] == 0
    # Score = 0.5 (base) + 0.1 (pronoms, car > 50 mots) = 0.6
    assert result_bad["coherence_score"] == pytest.approx(0.5 + 0.1)


def test_analyze_coherence_repeated_keywords(analyzer_default: MockCoherenceAnalyzer):
    """Teste l'impact de la répétition de mots-clés."""
    # Score de base 0.5. Pronoms +0.1. Total 0.6
    # "analyse" (x3), "pertinente" (x2). Count = 2. Score += 0.15. Total = 0.75
    text = "Cette analyse est une analyse très pertinente. L'analyse des données est pertinente."
    result = analyzer_default.analyze_coherence(text)
    assert result["factors"]["repeated_keywords_bonus"] >= 2
    assert result["coherence_score"] == pytest.approx(0.5 + 0.15 + 0.1)
    assert result["interpretation"] == "Très cohérent (Mock)"

def test_analyze_coherence_contradictions(analyzer_default: MockCoherenceAnalyzer):
    """Teste l'impact des contradictions."""
    # Score de base 0.5. Pronoms +0.1. Total 0.6
    # "j'aime" et "je n'aime pas". Contradiction x1. Score -= 0.4. Total = 0.2
    text = "J'aime le chocolat. Mais parfois, je n'aime pas le chocolat du tout."
    result = analyzer_default.analyze_coherence(text)
    assert result["factors"]["contradiction_penalty"] == 1
    assert result["coherence_score"] == pytest.approx(0.5 - 0.4 + 0.1) # 0.2
    assert result["interpretation"] == "Incohérent (Mock)"

def test_analyze_coherence_abrupt_topic_change(analyzer_default: MockCoherenceAnalyzer):
    """Teste l'impact d'un changement de sujet abrupt simulé."""
    # Score de base 0.5. Pronoms +0.1. Total 0.6
    # Changement abrupt. Score -= 0.2. Total = 0.4
    text = "Les pommes sont rouges et délicieuses. Les voitures vont vite."
    prev_summary = "Discussion sur les fruits et leurs couleurs."
    result = analyzer_default.analyze_coherence(text, prev_summary)
    assert result["factors"]["abrupt_topic_change_penalty"] == 1
    assert result["coherence_score"] == pytest.approx(0.5 - 0.2 + 0.1) # 0.4
    assert result["interpretation"] == "Peu cohérent (Mock)"

    text_coherent_topic = "Les pommes sont rouges. Les poires sont vertes."
    prev_summary_fruits = "Discussion sur les fruits."
    result_coherent = analyzer_default.analyze_coherence(text_coherent_topic, prev_summary_fruits)
    assert result_coherent["factors"]["abrupt_topic_change_penalty"] == 0


def test_analyze_coherence_multiple_factors_and_clamping(analyzer_default: MockCoherenceAnalyzer):
    """Teste le cumul de facteurs et le clampage."""
    # Base 0.5. Pronoms +0.1.
    # Transitions: "donc", "cependant" (x2) / ~20 mots. Ratio > 0.02. Score += 0.2
    # Répétition: "test" (x2). Score += 0.15
    # Contradiction: "j'aime", "je n'aime pas". Score -= 0.4
    # Total = 0.5 + 0.1 + 0.2 + 0.15 - 0.4 = 0.55
    text = "J'aime ce test. Donc, c'est un bon test. Cependant, je n'aime pas toujours ce test."
    result = analyzer_default.analyze_coherence(text)
    assert result["coherence_score"] == pytest.approx(0.55)
    assert result["interpretation"] == "Cohérent (Mock)"

    # Test clamp à 0
    # Base 0.5. Pronoms +0.1.
    # Contradictions x2 (si possible avec le mock simple) -> -0.8
    # "j'aime", "je n'aime pas" ET "c'est vrai", "c'est faux"
    # Total = 0.5 + 0.1 - 0.4 - 0.4 = -0.2 -> clampé à 0.0
    text_very_incoherent = "J'aime ça. C'est vrai. Mais je n'aime pas ça. Et c'est faux."
    result_bad = analyzer_default.analyze_coherence(text_very_incoherent)
    assert result_bad["factors"]["contradiction_penalty"] == 2
    assert result_bad["coherence_score"] == 0.0
    assert result_bad["interpretation"] == "Incohérent (Mock)"
    
    # Test clamp à 1
    # Base 0.5. Pronoms +0.1. Transitions +0.2. Répétition +0.15. (Total 0.95)
    # Si on avait un autre bonus de +0.1, ça dépasserait.
    # Le mock actuel ne permet pas facilement de dépasser 1 avec les bonus par défaut.
    text_very_coherent = (
        "Ce texte est un exemple de cohérence. Donc, il suit une logique claire. "
        "De plus, les idées sont bien liées. Ainsi, la cohérence du texte est assurée. "
        "La structure du texte aide aussi la cohérence. La cohérence est clé."
    ) # ~40 mots. Transitions: 4. Ratio 0.1. -> +0.2
      # Répétition: "cohérence" (x4), "texte" (x4). -> +0.15
      # Pronoms: +0.1
      # Total = 0.5 + 0.2 + 0.15 + 0.1 = 0.95.
    result_good = analyzer_default.analyze_coherence(text_very_coherent)
    assert result_good["coherence_score"] == pytest.approx(0.95)


def test_interpret_score(analyzer_default: MockCoherenceAnalyzer):
    """Teste la fonction d'interprétation des scores."""
    assert analyzer_default._interpret_score(0.80) == "Très cohérent (Mock)"
    assert analyzer_default._interpret_score(0.75) == "Très cohérent (Mock)"
    assert analyzer_default._interpret_score(0.60) == "Cohérent (Mock)"
    assert analyzer_default._interpret_score(0.50) == "Cohérent (Mock)"
    assert analyzer_default._interpret_score(0.30) == "Peu cohérent (Mock)"
    assert analyzer_default._interpret_score(0.25) == "Peu cohérent (Mock)"
    assert analyzer_default._interpret_score(0.10) == "Incohérent (Mock)"
    assert analyzer_default._interpret_score(0.0) == "Incohérent (Mock)"