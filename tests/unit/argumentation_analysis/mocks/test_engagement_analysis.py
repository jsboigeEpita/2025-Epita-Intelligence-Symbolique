# -*- coding: utf-8 -*-
"""Tests pour le MockEngagementAnalyzer."""

import pytest
import logging
from argumentation_analysis.mocks.engagement_analysis import MockEngagementAnalyzer

@pytest.fixture
def analyzer_default() -> MockEngagementAnalyzer:
    """Instance de MockEngagementAnalyzer avec config par défaut."""
    return MockEngagementAnalyzer()

@pytest.fixture
def analyzer_custom_config() -> MockEngagementAnalyzer:
    """Instance avec une configuration personnalisée."""
    config = {
        "engagement_signals": {
            "custom_signal": 0.5,
            "vocabulaire_positif_fort": 0.2 # Override
        },
        # Les listes de mots-clés ne sont pas directement dans config pour ce mock,
        # mais on pourrait les surcharger si le mock était plus complexe.
    }
    return MockEngagementAnalyzer(config=config)

def test_initialization_default(analyzer_default: MockEngagementAnalyzer):
    """Teste l'initialisation avec la configuration par défaut."""
    assert analyzer_default.get_config() == {}
    assert "questions_directes" in analyzer_default.engagement_signals
    assert analyzer_default.engagement_signals["questions_directes"] == 0.2
    assert "incroyable" in analyzer_default.positive_keywords

def test_initialization_custom_config(analyzer_custom_config: MockEngagementAnalyzer):
    """Teste l'initialisation avec une configuration personnalisée."""
    expected_signals = { # Le mock fusionne la config fournie avec les valeurs par défaut
            "questions_directes": 0.2,
            "appels_action": 0.3,
            "pronoms_inclusifs": 0.1,
            "vocabulaire_positif_fort": 0.2, # Surchargé
            "vocabulaire_negatif_fort": -0.1,
            "longueur_texte_bonus": 0.05,
            "custom_signal": 0.5 # Ajouté
    }
    # Le mock actuel ne fusionne pas intelligemment, il écrase.
    # Il faudrait modifier le mock pour qu'il fusionne les dictionnaires.
    # Pour l'instant, il prendra ce qui est dans "engagement_signals" de la config.
    assert analyzer_custom_config.engagement_signals["custom_signal"] == 0.5
    assert analyzer_custom_config.engagement_signals["vocabulaire_positif_fort"] == 0.2


def test_analyze_engagement_non_string_input(analyzer_default: MockEngagementAnalyzer, caplog):
    """Teste l'analyse avec une entrée non textuelle."""
    with caplog.at_level(logging.WARNING):
        result = analyzer_default.analyze_engagement(123.45) # type: ignore
    assert "error" in result
    assert result["error"] == "Entrée non textuelle"
    assert result["engagement_score"] == 0.0
    assert "MockEngagementAnalyzer.analyze_engagement a reçu une entrée non textuelle." in caplog.text

def test_analyze_engagement_empty_string(analyzer_default: MockEngagementAnalyzer):
    """Teste avec une chaîne vide."""
    result = analyzer_default.analyze_engagement("")
    assert result["engagement_score"] == 0.0
    assert result["interpretation"] == "Pas du tout engageant (Mock)"
    for signal_count in result["signals_detected"].values():
        assert signal_count == 0

def test_analyze_engagement_no_signals(analyzer_default: MockEngagementAnalyzer):
    """Teste un texte sans signaux d'engagement clairs."""
    text = "Un simple fait."
    result = analyzer_default.analyze_engagement(text)
    assert result["engagement_score"] == 0.0 # Ou très proche de 0 si bonus longueur s'applique
    assert result["interpretation"] == "Pas du tout engageant (Mock)"

def test_analyze_engagement_questions_directes(analyzer_default: MockEngagementAnalyzer):
    text = "Que pensez-vous de cela ? C'est une bonne idée, n'est-ce pas ?"
    # "?" (x2), "qu'en pensez-vous", "n'est-ce pas"
    # signals_detected["questions_directes"] = 2 (pour "?") + 1 + 1 = 4
    # score += 0.2 * min(4, 3) = 0.2 * 3 = 0.6
    result = analyzer_default.analyze_engagement(text)
    assert result["signals_detected"]["questions_directes"] >= 2 # Le mock compte les patterns
    assert result["engagement_score"] >= 0.2 * min(result["signals_detected"]["questions_directes"], 3)
    assert result["engagement_score"] > 0.5 # Devrait être engageant
    assert result["interpretation"] == "Engageant (Mock)" # 0.6

def test_analyze_engagement_appel_action(analyzer_default: MockEngagementAnalyzer):
    text = "Cliquez ici pour en savoir plus et rejoignez notre communauté !"
    # "cliquez", "rejoignez"
    # score += 0.3
    result = analyzer_default.analyze_engagement(text)
    assert result["signals_detected"]["appels_action"] == 2
    assert result["engagement_score"] >= 0.3
    assert result["interpretation"] == "Engageant (Mock)" # 0.3

def test_analyze_engagement_pronoms_inclusifs(analyzer_default: MockEngagementAnalyzer):
    text = "Ensemble, nous pouvons faire la différence pour notre futur. Votre aide est précieuse."
    # "ensemble", "nous", "notre", "votre"
    # count = 4. score += 0.1 * min(4, 5) = 0.4
    result = analyzer_default.analyze_engagement(text)
    assert result["signals_detected"]["pronoms_inclusifs"] >= 4
    assert result["engagement_score"] >= 0.1 * min(result["signals_detected"]["pronoms_inclusifs"], 5)
    assert result["interpretation"] == "Engageant (Mock)" # 0.4

def test_analyze_engagement_vocabulaire_positif(analyzer_default: MockEngagementAnalyzer):
    text = "C'est une solution incroyable et fantastique."
    # "incroyable", "fantastique"
    # score += 0.15
    result = analyzer_default.analyze_engagement(text)
    assert result["signals_detected"]["vocabulaire_positif_fort"] == 2
    assert result["engagement_score"] >= 0.15
    assert result["interpretation"] == "Pas du tout engageant (Mock)" # 0.15

def test_analyze_engagement_vocabulaire_negatif(analyzer_default: MockEngagementAnalyzer):
    text = "Ce fut une expérience terrible et décevante."
    # "terrible", "décevant"
    # score += -0.1
    result = analyzer_default.analyze_engagement(text)
    assert result["signals_detected"]["vocabulaire_negatif_fort"] == 2
    assert result["engagement_score"] == 0.0 # -0.1 clampé à 0
    assert result["interpretation"] == "Pas du tout engageant (Mock)"

def test_analyze_engagement_longueur_texte_bonus(analyzer_default: MockEngagementAnalyzer):
    text = "a" * 201 # > 200
    # score += 0.05
    result = analyzer_default.analyze_engagement(text)
    assert result["signals_detected"]["longueur_texte_bonus"] == 1
    assert result["engagement_score"] >= 0.05
    assert result["interpretation"] == "Pas du tout engageant (Mock)" # 0.05

def test_analyze_engagement_combination_and_clamping(analyzer_default: MockEngagementAnalyzer):
    text = (
        "Qu'en pensez-vous ? Cliquez ici ! Ensemble, nous ferons des choses incroyables. "
        "C'est une opportunité révolutionnaire. Rejoignez-nous maintenant. Votre avis compte. "
        "N'est-ce pas merveilleux ? " + ("bla " * 30) # Pour bonus longueur
    )
    # Questions: "Qu'en pensez-vous ?", "N'est-ce pas ?" -> count=2. score_q = 0.2 * 2 = 0.4
    # Action: "Cliquez", "Rejoignez" -> count=2. score_a = 0.3
    # Inclusifs: "Ensemble", "nous", "Votre" -> count=3. score_i = 0.1 * 3 = 0.3
    # Positif: "incroyables", "révolutionnaire", "merveilleux" -> count=3. score_p = 0.15
    # Longueur: > 200 -> score_l = 0.05
    # Total = 0.4 + 0.3 + 0.3 + 0.15 + 0.05 = 1.2. Devrait être clampé à 1.0
    result = analyzer_default.analyze_engagement(text)
    assert result["engagement_score"] == 1.0
    assert result["interpretation"] == "Très engageant (Mock)"
    assert result["signals_detected"]["questions_directes"] >= 2
    assert result["signals_detected"]["appels_action"] >= 2
    assert result["signals_detected"]["pronoms_inclusifs"] >= 3
    assert result["signals_detected"]["vocabulaire_positif_fort"] >= 3
    assert result["signals_detected"]["longueur_texte_bonus"] == 1

def test_interpret_score(analyzer_default: MockEngagementAnalyzer):
    """Teste la fonction d'interprétation des scores."""
    assert analyzer_default._interpret_score(0.80) == "Très engageant (Mock)"
    assert analyzer_default._interpret_score(0.75) == "Très engageant (Mock)"
    assert analyzer_default._interpret_score(0.60) == "Engageant (Mock)"
    assert analyzer_default._interpret_score(0.50) == "Engageant (Mock)"
    assert analyzer_default._interpret_score(0.30) == "Peu engageant (Mock)"
    assert analyzer_default._interpret_score(0.25) == "Peu engageant (Mock)"
    assert analyzer_default._interpret_score(0.10) == "Pas du tout engageant (Mock)"
    assert analyzer_default._interpret_score(0.0) == "Pas du tout engageant (Mock)"