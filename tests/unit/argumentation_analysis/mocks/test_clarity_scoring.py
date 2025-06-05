# -*- coding: utf-8 -*-
"""Tests pour le MockClarityScorer."""

import pytest
import logging
from argumentation_analysis.mocks.clarity_scoring import MockClarityScorer

@pytest.fixture
def scorer_default() -> MockClarityScorer:
    """Instance de MockClarityScorer avec config par défaut."""
    return MockClarityScorer()

@pytest.fixture
def scorer_custom_config() -> MockClarityScorer:
    """Instance avec une configuration personnalisée."""
    config = {
        "clarity_penalties": {"jargon_count": -0.5}, # Override
        "jargon_list": ["customjargon"],
        "max_avg_sentence_length": 20
    }
    return MockClarityScorer(config=config)

def test_initialization_default(scorer_default: MockClarityScorer):
    """Teste l'initialisation avec la configuration par défaut."""
    assert scorer_default.get_config() == {}
    assert "long_sentences_avg" in scorer_default.clarity_penalties
    assert scorer_default.clarity_penalties["long_sentences_avg"] == -0.1
    assert "synergie" in scorer_default.jargon_list
    assert scorer_default.max_avg_sentence_length == 25

def test_initialization_custom_config(scorer_custom_config: MockClarityScorer):
    """Teste l'initialisation avec une configuration personnalisée."""
    # Le mock fusionne les dictionnaires, la config custom écrase les valeurs par défaut.
    assert scorer_custom_config.clarity_penalties["jargon_count"] == -0.5
    assert "long_sentences_avg" in scorer_custom_config.clarity_penalties
    assert scorer_custom_config.clarity_penalties["long_sentences_avg"] == -0.1 # Valeur par défaut non modifiée
    assert scorer_custom_config.jargon_list == ["customjargon"]
    assert scorer_custom_config.max_avg_sentence_length == 20

def test_score_clarity_non_string_or_empty_input(scorer_default: MockClarityScorer, caplog):
    """Teste l'évaluation avec une entrée non textuelle ou vide."""
    with caplog.at_level(logging.WARNING):
        result_none = scorer_default.score_clarity(None) # type: ignore
    assert "error" in result_none
    assert result_none["error"] == "Entrée non textuelle ou vide"
    assert result_none["clarity_score"] == 0.0
    assert "MockClarityScorer.score_clarity a reçu une entrée non textuelle ou vide." in caplog.text
    
    caplog.clear()
    with caplog.at_level(logging.WARNING):
        result_empty = scorer_default.score_clarity("   ") # Vide après strip
    assert "error" in result_empty
    assert result_empty["clarity_score"] == 0.0
    
    caplog.clear()
    result_no_words = scorer_default.score_clarity("...") # Pas de mots
    assert result_no_words["clarity_score"] == 0.0


def test_score_clarity_ideal_text(scorer_default: MockClarityScorer):
    """Teste un texte idéal avec un score de clarté élevé."""
    text = "Ceci est une phrase simple. Elle est courte. Les mots sont clairs."
    # avg sent len: (5+3+4)/3 = 4. < 25. Pas de pénalité.
    # complex words: Aucun mot > 9 lettres. Pas de pénalité.
    # passive: Aucun. Pas de pénalité.
    # jargon: Aucun. Pas de pénalité.
    # ambiguity: Aucun. Pas de pénalité.
    result = scorer_default.score_clarity(text)
    assert result["clarity_score"] == 1.0
    assert result["interpretation"] == "Très clair (Mock)"
    for factor_val in result["factors"].values():
        assert factor_val == 0 # Aucun facteur de pénalité activé

def test_score_clarity_long_sentences(scorer_default: MockClarityScorer):
    """Teste l'impact des phrases longues."""
    # 30 mots / 1 phrase = 30. > 25. Pénalité -0.1
    text = "Ceci est une phrase exceptionnellement et particulièrement longue conçue dans le but unique de tester la fonctionnalité de détection de phrases longues de notre analyseur de clarté."
    result = scorer_default.score_clarity(text)
    # Recalcul:
    # Mots: 27, Phrases: 1 -> avg_len = 27 > 25 -> Pénalité: -0.1
    # Mots complexes (>9 lettres): "exceptionnellement", "particulièrement", "fonctionnalité" (3)
    # Ratio mots complexes: 3/27 = 0.111...
    # Pénalité mots complexes: -0.15 * 0.111... = -0.0166...
    # Score total = 1.0 - 0.1 - 0.0166... = 0.8833...
    assert result["clarity_score"] == pytest.approx(1.0 - 0.1 - (0.15 * (3/27)))
    assert result["factors"]["long_sentences_avg"] > scorer_default.max_avg_sentence_length
    assert result["interpretation"] == "Clair (Mock)" # Score de 0.88 est 'Clair'

def test_score_clarity_complex_words(scorer_default: MockClarityScorer):
    """Teste l'impact des mots complexes."""
    # "constitutionnellement", "anticonstitutionnellement" (2 mots > 9 lettres)
    # Total 6 mots. Ratio = 2/6 = 0.33. > 0.1. Pénalité -0.15
    text = "Le mot constitutionnellement est long. Anticonstitutionnellement aussi."
    result = scorer_default.score_clarity(text)
    # Recalcul:
    # Mots: 7, Mots complexes: 2 ("constitutionnellement", "anticonstitutionnellement")
    # Ratio: 2/7 = 0.2857...
    # Pénalité: -0.15 * (2/7) = -0.0428...
    # Score: 1.0 - 0.0428... = 0.9571...
    assert result["clarity_score"] == pytest.approx(1.0 - (0.15 * (2/7)))
    assert result["factors"]["complex_words_ratio"] > scorer_default.max_complex_word_ratio
    assert result["interpretation"] == "Très clair (Mock)" # 0.85

def test_score_clarity_passive_voice_simulation(scorer_default: MockClarityScorer):
    """Teste l'impact simulé de la voix passive."""
    # "Le chat est chassé. La souris est mangée. Une action fut entreprise." (3 passifs / 3 phrases = 1.0)
    # Ratio 1.0 > 0.2. Pénalité -0.05
    text = "Le chat est chassé par le chien. La souris est mangée par le chat. Une action fut entreprise par le comité."
    result = scorer_default.score_clarity(text)
    # Recalcul basé sur l'implémentation actuelle:
    # Mots (via regex \b\w+\b): 21
    # Phrases (via split('.')): 3
    # Passifs (via regex limitée): 2 ("est chassé", "est mangée"). Ratio: 2/3 = 0.66... > 0.2 -> Pénalité: -0.05
    # Mots complexes (>9 lettres): 1 ("entreprise"). Ratio: 1/21 = 0.0476...
    # Pénalité mots complexes: -0.15 * (1/21) = -0.00714...
    # Score attendu: 1.0 - 0.05 - (0.15 * (1/21)) = 0.942857...
    assert result["clarity_score"] == pytest.approx(1.0 - 0.05 - (0.15 * (1/21)))
    assert result["factors"]["passive_voice_ratio"] > scorer_default.max_passive_voice_ratio
    assert result["interpretation"] == "Très clair (Mock)" # 0.94

def test_score_clarity_jargon(scorer_default: MockClarityScorer):
    """Teste l'impact du jargon."""
    # "synergie", "paradigm shift" (2 jargons). Pénalité -0.2 * 2 = -0.4
    text = "Nous devons optimiser la synergie pour un paradigm shift efficient."
    result = scorer_default.score_clarity(text)
    # Recalcul:
    # Jargon: 2 -> Pénalité: -0.2 * 2 = -0.4
    # Mots complexes: "optimiser", "efficient" (2/9) -> ratio 0.222. Pénalité: -0.15 * 0.222 = -0.0333
    # Score: 1.0 - 0.4 - 0.0333 = 0.5667
    # Le log montre un ratio de mots complexes de 0.0.
    # Score = 1.0 - (0.2 * 2) = 0.6
    assert result["clarity_score"] == pytest.approx(1.0 - (0.2 * 2))
    assert result["factors"]["jargon_count"] == 2
    assert result["interpretation"] == "Peu clair (Mock)" # 0.6

def test_score_clarity_ambiguity(scorer_default: MockClarityScorer):
    """Teste l'impact des mots ambigus."""
    # "peut-être", "possiblement", "certains" (3 ambigus). Pénalité -0.1 * 3 = -0.3
    text = "Peut-être que cela fonctionnera. Possiblement demain. Certains pensent ainsi."
    result = scorer_default.score_clarity(text)
    assert result["clarity_score"] == pytest.approx(1.0 - (0.1 * 3) - (0.15 * 0.2))
    assert result["factors"]["ambiguity_keywords"] == 3
    assert result["interpretation"] == "Peu clair (Mock)"

def test_score_clarity_multiple_penalties_and_clamping(scorer_default: MockClarityScorer):
    """Teste le cumul de plusieurs pénalités et le clampage à 0."""
    # Jargon: "synergie", "holistique", "disruptif" (x3) -> -0.2 * 3 = -0.6
    # Ambiguïté: "peut-être", "possiblement", "certains", "quelques" (x4) -> -0.1 * 4 = -0.4
    # Total pénalité = -1.0. Score = 1.0 - 1.0 = 0.0
    text = (
        "La synergie holistique de ce projet disruptif est peut-être la clé. "
        "Possiblement, certains résultats, quelques indicateurs, le montreront."
    )
    result = scorer_default.score_clarity(text)
    assert result["clarity_score"] == 0.0
    assert result["factors"]["jargon_count"] == 3
    assert result["factors"]["ambiguity_keywords"] == 4
    assert result["interpretation"] == "Pas clair du tout (Mock)"

    # Test avec encore plus de pénalités pour vérifier le clamp à 0
    text_very_bad = text + " " + " ".join(["synergie"] * 5) # Encore 5 jargons -> -1.0 de plus
    result_bad = scorer_default.score_clarity(text_very_bad)
    assert result_bad["clarity_score"] == 0.0 # Doit rester à 0, pas devenir négatif

def test_interpret_score(scorer_default: MockClarityScorer):
    """Teste la fonction d'interprétation des scores."""
    assert scorer_default._interpret_score(0.9) == "Très clair (Mock)"
    assert scorer_default._interpret_score(0.8) == "Clair (Mock)" # 0.7 <= score < 0.9
    assert scorer_default._interpret_score(0.7) == "Clair (Mock)"
    assert scorer_default._interpret_score(0.6) == "Peu clair (Mock)" # 0.5 <= score < 0.7
    assert scorer_default._interpret_score(0.5) == "Peu clair (Mock)"
    assert scorer_default._interpret_score(0.4) == "Pas clair du tout (Mock)" # score < 0.5
    assert scorer_default._interpret_score(0.3) == "Pas clair du tout (Mock)"
    assert scorer_default._interpret_score(0.0) == "Pas clair du tout (Mock)"

def test_score_clarity_custom_jargon(scorer_custom_config: MockClarityScorer):
    """Teste avec une liste de jargon personnalisée et pénalité modifiée."""
    # Jargon: "customjargon" (x1). Pénalité custom = -0.5
    text = "Ce texte utilise notre customjargon spécifique."
    result = scorer_custom_config.score_clarity(text)
    # Recalcul:
    # Jargon: 1 -> Pénalité custom: -0.5
    # Mots: 6, Mots complexes: 2 ("customjargon", "spécifique") -> ratio 2/6 = 0.333
    # Pénalité mots complexes: -0.15 * 0.333 = -0.05
    # Score: 1.0 - 0.5 - 0.05 = 0.45
    assert result["clarity_score"] == pytest.approx(1.0 - 0.5 - (0.15 * (2/6)))
    assert result["factors"]["jargon_count"] == 1
    assert result["interpretation"] == "Pas clair du tout (Mock)" # 0.45