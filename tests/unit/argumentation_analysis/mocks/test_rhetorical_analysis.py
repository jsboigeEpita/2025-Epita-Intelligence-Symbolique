# -*- coding: utf-8 -*-
"""Tests pour le MockRhetoricalAnalyzer."""

import pytest
import logging
from argumentation_analysis.mocks.rhetorical_analysis import MockRhetoricalAnalyzer

@pytest.fixture
def analyzer() -> MockRhetoricalAnalyzer:
    """Fixture pour fournir une instance de MockRhetoricalAnalyzer sans config."""
    return MockRhetoricalAnalyzer()

@pytest.fixture
def analyzer_with_config() -> MockRhetoricalAnalyzer:
    """Fixture pour fournir une instance avec une config."""
    config = {"mode": "test", "sensitivity": "high"}
    return MockRhetoricalAnalyzer(config=config)

def test_initialization_default(analyzer: MockRhetoricalAnalyzer):
    """Teste l'initialisation sans configuration."""
    assert analyzer.get_config() == {}

def test_initialization_with_config(analyzer_with_config: MockRhetoricalAnalyzer):
    """Teste l'initialisation avec une configuration."""
    expected_config = {"mode": "test", "sensitivity": "high"}
    assert analyzer_with_config.get_config() == expected_config

def test_analyze_non_string_input(analyzer: MockRhetoricalAnalyzer, caplog):
    """Teste l'analyse avec une entrée non textuelle."""
    with caplog.at_level(logging.WARNING):
        result = analyzer.analyze(12345) # type: ignore
    assert "error" in result
    assert result["error"] == "Entrée non textuelle"
    assert result["tonalite"] == "Neutre (Erreur)"
    assert "MockRhetoricalAnalyzer.analyze a reçu une entrée non textuelle." in caplog.text

    caplog.clear()
    with caplog.at_level(logging.WARNING):
        result_none = analyzer.analyze(None) # type: ignore
    assert "error" in result_none
    assert "MockRhetoricalAnalyzer.analyze a reçu une entrée non textuelle." in caplog.text

def test_analyze_default_case(analyzer: MockRhetoricalAnalyzer):
    """Teste l'analyse d'un texte simple sans mots-clés spécifiques."""
    text = "Un texte simple et direct."
    result = analyzer.analyze(text)
    
    assert "figures_de_style" in result
    assert len(result["figures_de_style"]) == 1
    figure = result["figures_de_style"][0]
    assert figure["type"] == "Style Direct (Mock)"
    assert text[:50] in figure["extrait"]
    
    assert result["tonalite_globale"] == "Neutre"
    assert result["score_engagement_simule"] == 0.1
    assert result["longueur_texte"] == len(text)

def test_analyze_metaphor(analyzer: MockRhetoricalAnalyzer):
    """Teste la détection de 'exemple de métaphore'."""
    text = "Ceci est un exemple de métaphore pour illustrer."
    result = analyzer.analyze(text)
    
    assert len(result["figures_de_style"]) == 1
    figure = result["figures_de_style"][0]
    assert figure["type"] == "Métaphore (Mock)"
    assert "exemple de métaphore" in figure["extrait"]
    
    assert result["tonalite_globale"] == "Imagée"
    assert result["score_engagement_simule"] == 0.3

def test_analyze_rhetorical_question(analyzer: MockRhetoricalAnalyzer):
    """Teste la détection de 'question rhétorique'."""
    text = "N'est-ce pas une question rhétorique évidente ?"
    result = analyzer.analyze(text)
    
    assert len(result["figures_de_style"]) == 1
    figure = result["figures_de_style"][0]
    assert figure["type"] == "Question Rhétorique (Mock)"
    assert "question rhétorique" in figure["extrait"]
    
    assert result["tonalite_globale"] == "Interrogative / Persuasive"
    assert result["score_engagement_simule"] == 0.4

def test_analyze_ironic_tone(analyzer: MockRhetoricalAnalyzer):
    """Teste la détection de 'tonalité ironique'."""
    text = "Oh, quelle merveilleuse journée pluvieuse, c'est une tonalité ironique."
    result = analyzer.analyze(text)
    
    # La tonalité ironique est détectée, mais ne crée pas de figure de style par elle-même.
    assert len(result["figures_de_style"]) == 0

    assert result["tonalite_globale"] == "Ironique (Mock)"
    # score_engagement = 0.0 (base) - 0.2 (ironie) = -0.2, clamped to 0.0
    assert result["score_engagement_simule"] == 0.0

def test_analyze_combination_metaphor_and_question(analyzer: MockRhetoricalAnalyzer):
    """Teste la combinaison de métaphore et question rhétorique."""
    text = "Un exemple de métaphore, et aussi une question rhétorique ?"
    result = analyzer.analyze(text)
    
    assert len(result["figures_de_style"]) == 2
    types = {f["type"] for f in result["figures_de_style"]}
    assert "Métaphore (Mock)" in types
    assert "Question Rhétorique (Mock)" in types
    
    # La dernière tonalité détectée (question rhétorique) devrait dominer
    assert result["tonalite_globale"] == "Interrogative / Persuasive"
    # Métaphore: +0.3, Question: +0.4. Total = 0.7
    assert result["score_engagement_simule"] == 0.7

def test_analyze_combination_all_keywords(analyzer: MockRhetoricalAnalyzer):
    """Teste la combinaison de tous les mots-clés."""
    text = "Un exemple de métaphore, une question rhétorique, et une tonalité ironique."
    result = analyzer.analyze(text)
    
    assert len(result["figures_de_style"]) == 2 # Métaphore et Question
    types = {f["type"] for f in result["figures_de_style"]}
    assert "Métaphore (Mock)" in types
    assert "Question Rhétorique (Mock)" in types
    
    # La tonalité ironique est la dernière vérifiée et devrait s'appliquer
    assert result["tonalite_globale"] == "Ironique (Mock)"
    # Métaphore: +0.3, Question: +0.4, Ironie: -0.2. Total = 0.5
    assert result["score_engagement_simule"] == pytest.approx(0.5)

def test_score_engagement_clamping(analyzer: MockRhetoricalAnalyzer):
    """Teste que le score d'engagement est bien clampé entre 0 et 1."""
    # Cas où le score pourrait être > 1
    text_very_engaging = " ".join(["question rhétorique"] * 3) # 0.4 * 3 = 1.2
    result_high = analyzer.analyze(text_very_engaging)
    # Le mock actuel ne cumule pas les mêmes figures, il en ajoute une par mot-clé unique.
    # Si "question rhétorique" est présent, score = 0.4
    assert result_high["score_engagement_simule"] == 0.4 # Devrait être 0.4, pas 1.0

    # Pour tester le clamp à 1, il faudrait que la logique interne puisse dépasser 1.
    # Le mock actuel : métaphore (0.3) + question (0.4) = 0.7.
    # Si on avait une autre figure à 0.4, on aurait 1.1.
    # Modifions le mock pour ce test ou acceptons que le test actuel ne peut pas prouver le clamp supérieur.
    # Pour l'instant, on se base sur la logique interne du mock.

    # Cas où le score pourrait être < 0
    text_very_disengaging = "tonalité ironique " * 6 # 0.1 (default) - 0.2 (ironie) = -0.1
    result_low = analyzer.analyze(text_very_disengaging)
    assert result_low["score_engagement_simule"] == 0.0 # -0.1 clampé à 0.0

def test_analyze_empty_string(analyzer: MockRhetoricalAnalyzer):
    """Teste l'analyse d'une chaîne vide."""
    text = ""
    result = analyzer.analyze(text)
    assert len(result["figures_de_style"]) == 1
    assert result["figures_de_style"][0]["type"] == "Style Direct (Mock)"
    assert result["figures_de_style"][0]["extrait"] == ""
    assert result["tonalite_globale"] == "Neutre"
    assert result["score_engagement_simule"] == 0.1
    assert result["longueur_texte"] == 0