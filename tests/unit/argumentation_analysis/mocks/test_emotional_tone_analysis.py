# -*- coding: utf-8 -*-
"""Tests pour le MockEmotionalToneAnalyzer."""

import pytest
import logging
from argumentation_analysis.mocks.emotional_tone_analysis import MockEmotionalToneAnalyzer

@pytest.fixture
def analyzer_default() -> MockEmotionalToneAnalyzer:
    """Instance de MockEmotionalToneAnalyzer avec config par défaut."""
    return MockEmotionalToneAnalyzer()

@pytest.fixture
def analyzer_custom_config() -> MockEmotionalToneAnalyzer:
    """Instance avec une configuration personnalisée."""
    config = {
        "emotion_keywords": {
            "Bonheur (Custom)": ["super", "génial"],
            "Tristesse (Custom)": ["nul", "dommage"]
        },
        "intensity_threshold": 0.7
    }
    return MockEmotionalToneAnalyzer(config=config)

def test_initialization_default(analyzer_default: MockEmotionalToneAnalyzer):
    """Teste l'initialisation avec la configuration par défaut."""
    assert analyzer_default.get_config() == {}
    assert analyzer_default.intensity_threshold == 0.6
    assert "Joie (Mock)" in analyzer_default.emotion_keywords
    assert "heureux" in analyzer_default.emotion_keywords["Joie (Mock)"]

def test_initialization_custom_config(analyzer_custom_config: MockEmotionalToneAnalyzer):
    """Teste l'initialisation avec une configuration personnalisée."""
    expected_config_keywords = {
            "Bonheur (Custom)": ["super", "génial"],
            "Tristesse (Custom)": ["nul", "dommage"]
    }
    assert analyzer_custom_config.intensity_threshold == 0.7
    assert analyzer_custom_config.emotion_keywords == expected_config_keywords

def test_analyze_tone_non_string_input(analyzer_default: MockEmotionalToneAnalyzer, caplog):
    """Teste l'analyse avec une entrée non textuelle."""
    with caplog.at_level(logging.WARNING):
        result = analyzer_default.analyze_tone([1,2,3]) # type: ignore
    assert "error" in result
    assert result["error"] == "Entrée non textuelle"
    assert result["dominant_emotion"] == "Inconnue"
    assert "MockEmotionalToneAnalyzer.analyze_tone a reçu une entrée non textuelle." in caplog.text

def test_analyze_tone_empty_string(analyzer_default: MockEmotionalToneAnalyzer):
    """Teste avec une chaîne vide."""
    result = analyzer_default.analyze_tone("")
    assert result["dominant_emotion"] == "Neutre (Mock)"
    for score in result["emotions_scores"].values():
        assert score == 0.0
    assert result["details"] == []

def test_analyze_tone_no_keywords(analyzer_default: MockEmotionalToneAnalyzer):
    """Teste un texte sans mots-clés émotionnels."""
    text = "Ceci est un texte purement factuel et descriptif."
    result = analyzer_default.analyze_tone(text)
    assert result["dominant_emotion"] == "Neutre (Mock)"
    for score in result["emotions_scores"].values():
        assert score == 0.0

def test_analyze_tone_single_emotion_joy(analyzer_default: MockEmotionalToneAnalyzer):
    """Teste la détection de la joie."""
    text = "Je suis tellement heureux et content aujourd'hui, c'est une journée joyeuse !"
    # "heureux": 0.3+0.1=0.4
    # "content": 0.3+0.1=0.4 (cumulatif sur le count, puis min(1.0, 0.3*count+0.1))
    # "joyeux": 0.3+0.1=0.4
    # count = 3. score = min(1.0, 0.3*3 + 0.1) = min(1.0, 1.0) = 1.0
    result = analyzer_default.analyze_tone(text)
    assert result["emotions_scores"]["Joie (Mock)"] == 1.0 
    assert result["dominant_emotion"] == "Joie (Mock)" # 1.0 >= threshold 0.6
    
    details = result["details"]
    assert len(details) == 3
    keywords_found = {d["keyword"] for d in details if d["emotion"] == "Joie (Mock)"}
    assert "heureux" in keywords_found
    assert "content" in keywords_found
    assert "joyeux" in keywords_found

def test_analyze_tone_single_emotion_sadness_strong_keyword(analyzer_default: MockEmotionalToneAnalyzer):
    """Teste la détection de la tristesse avec un mot-clé fort."""
    text = "Il se sentait complètement déprimé et abattu."
    # "déprimé": 0.3*1+0.1 = 0.4. Mot fort -> +0.2. Total = 0.6
    # "abattu": 0.3*1+0.1 = 0.4. (le score est par émotion, pas par mot-clé individuel avant cumul)
    # count = 2. score_base = min(1.0, 0.3*2+0.1) = 0.7. Mot fort "déprimé" présent -> +0.2. Total = 0.9
    result = analyzer_default.analyze_tone(text)
    assert result["emotions_scores"]["Tristesse (Mock)"] == 0.9
    assert result["dominant_emotion"] == "Tristesse (Mock)" # 0.9 >= 0.6

def test_analyze_tone_mixed_emotions_dominant_below_threshold(analyzer_default: MockEmotionalToneAnalyzer):
    """Teste émotions mixtes où la plus forte est sous le seuil d'intensité."""
    text = "Je suis un peu content mais aussi un peu triste."
    # "content" (Joie): 0.3*1+0.1 = 0.4
    # "triste" (Tristesse): 0.3*1+0.1 = 0.4
    # Max score = 0.4, qui est < intensity_threshold (0.6)
    result = analyzer_default.analyze_tone(text)
    assert result["emotions_scores"]["Joie (Mock)"] > 0.0
    assert result["emotions_scores"]["Tristesse (Mock)"] > 0.0
    # Le dominant est le premier trouvé avec le max_score si égalité, ou le dernier si mis à jour.
    # Ici, les deux sont à 0.4. L'ordre dans emotion_keywords peut jouer.
    # Joie vient avant Tristesse.
    assert "Mixte (dominant: Joie, score: 0.40)" in result["dominant_emotion"] or \
           "Mixte (dominant: Tristesse, score: 0.40)" in result["dominant_emotion"]


def test_analyze_tone_mixed_emotions_one_dominant_above_threshold(analyzer_default: MockEmotionalToneAnalyzer):
    """Teste émotions mixtes avec une clairement dominante."""
    text = "Je suis très très heureux, ravi même ! Un peu triste aussi, mais surtout joyeux."
    # Joie: "heureux" (x2), "ravi", "joyeux". count = 4.
    # score_base = min(1.0, 0.3*4+0.1) = 1.0. "ravi" est fort -> +0.2. Total = 1.0 (capé)
    # Tristesse: "triste". count = 1. score = 0.3*1+0.1 = 0.4.
    result = analyzer_default.analyze_tone(text)
    assert result["emotions_scores"]["Joie (Mock)"] == 1.0
    assert result["emotions_scores"]["Tristesse (Mock)"] == 0.4
    assert result["dominant_emotion"] == "Joie (Mock)" # 1.0 >= 0.6

def test_analyze_tone_custom_config_keywords(analyzer_custom_config: MockEmotionalToneAnalyzer):
    """Teste avec les mots-clés de la configuration personnalisée."""
    text = "C'est super génial ! Mais quel dommage."
    # Bonheur: "super", "génial". count = 2. score = min(1.0, 0.3*2+0.1) = 0.7
    # Tristesse: "dommage". count = 1. score = 0.3*1+0.1 = 0.4
    result = analyzer_custom_config.analyze_tone(text)
    assert result["emotions_scores"]["Bonheur (Custom)"] == 0.7
    assert result["emotions_scores"]["Tristesse (Custom)"] == 0.4
    # intensity_threshold est 0.7 pour custom_config
    assert result["dominant_emotion"] == "Bonheur (Custom)" # 0.7 >= 0.7

def test_analyze_tone_details_indices(analyzer_default: MockEmotionalToneAnalyzer):
    """Vérifie les indices dans les détails."""
    text = "J'ai peur et je suis triste." # peur (0,5), triste (20,26)
    # Peur: "peur". count=1. score=0.4
    # Tristesse: "triste". count=1. score=0.4
    result = analyzer_default.analyze_tone(text)
    details = result["details"]
    assert len(details) == 2
    
    found_peur = False
    found_triste = False
    for detail in details:
        if detail["emotion"] == "Peur (Mock)" and detail["keyword"] == "peur":
            assert detail["indices"] == (text.lower().find("peur"), text.lower().find("peur") + len("peur"))
            found_peur = True
        if detail["emotion"] == "Tristesse (Mock)" and detail["keyword"] == "triste":
            assert detail["indices"] == (text.lower().find("triste"), text.lower().find("triste") + len("triste"))
            found_triste = True
    assert found_peur
    assert found_triste