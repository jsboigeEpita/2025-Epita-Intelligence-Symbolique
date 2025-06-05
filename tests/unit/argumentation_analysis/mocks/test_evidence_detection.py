# -*- coding: utf-8 -*-
"""Tests pour le MockEvidenceDetector."""

import pytest
import logging
from argumentation_analysis.mocks.evidence_detection import MockEvidenceDetector

@pytest.fixture
def detector_default() -> MockEvidenceDetector:
    """Instance de MockEvidenceDetector avec config par défaut."""
    return MockEvidenceDetector()

@pytest.fixture
def detector_custom_config() -> MockEvidenceDetector:
    """Instance avec une configuration personnalisée."""
    config = {
        "min_evidence_length": 10,
        "evidence_keywords": ["preuve:", "source:"]
    }
    return MockEvidenceDetector(config=config)

def test_initialization_default(detector_default: MockEvidenceDetector):
    """Teste l'initialisation avec la configuration par défaut."""
    assert detector_default.get_config() == {}
    assert detector_default.min_evidence_length == 15
    assert "selon l'étude" in detector_default.evidence_keywords

def test_initialization_custom_config(detector_custom_config: MockEvidenceDetector):
    """Teste l'initialisation avec une configuration personnalisée."""
    expected_config = {
        "min_evidence_length": 10,
        "evidence_keywords": ["preuve:", "source:"]
    }
    assert detector_custom_config.get_config() == expected_config
    assert detector_custom_config.min_evidence_length == 10
    assert detector_custom_config.evidence_keywords == ["preuve:", "source:"]

def test_detect_evidence_non_string_input(detector_default: MockEvidenceDetector, caplog):
    """Teste la détection avec une entrée non textuelle."""
    with caplog.at_level(logging.WARNING):
        result = detector_default.detect_evidence(12345) # type: ignore
    assert result == []
    assert "MockEvidenceDetector.detect_evidence a reçu une entrée non textuelle." in caplog.text
    
    caplog.clear()
    with caplog.at_level(logging.WARNING):
        result_none = detector_default.detect_evidence(None) # type: ignore
    assert result_none == []
    assert "MockEvidenceDetector.detect_evidence a reçu une entrée non textuelle." in caplog.text

def test_detect_evidence_empty_string(detector_default: MockEvidenceDetector):
    """Teste avec une chaîne vide."""
    assert detector_default.detect_evidence("") == []

def test_detect_evidence_short_text_no_triggers(detector_default: MockEvidenceDetector):
    """Teste un texte court sans aucun déclencheur."""
    # min_evidence_length est 15 par défaut
    assert detector_default.detect_evidence("Texte court.") == [] 

def test_detect_evidence_by_keyword_success(detector_default: MockEvidenceDetector):
    """Teste la détection par mot-clé."""
    text = "En effet, selon l'étude les résultats sont concluants. Un autre point."
    result = detector_default.detect_evidence(text)
    assert len(result) == 1
    evidence = result[0]
    assert evidence["type"] == "Preuve par Mot-Clé (Mock)"
    assert evidence["evidence_text"] == "les résultats sont concluants." # S'arrête au point
    assert evidence["keyword_used"] == "selon l'étude"
    assert evidence["strength_simulated"] == 0.80
    keyword_start = text.find("selon l'étude")
    # Les indices de la source incluent le mot-clé et le texte de la preuve
    assert evidence["source_indices"] == (keyword_start, text.find(".", keyword_start) + 1)

def test_detect_evidence_by_keyword_no_period(detector_default: MockEvidenceDetector):
    """Teste mot-clé sans point final, prend une portion."""
    text = "De plus, les données montrent que l'impact est significatif et continue"
    result = detector_default.detect_evidence(text)
    assert len(result) == 1
    evidence = result[0]
    assert evidence["type"] == "Preuve par Mot-Clé (Mock)"
    assert evidence["evidence_text"] == "l'impact est significatif et continue" # Prend jusqu'à 150 chars ou fin
    assert evidence["keyword_used"] == "les données montrent que"

def test_detect_evidence_by_keyword_text_too_short_after_keyword(detector_default: MockEvidenceDetector, detector_custom_config: MockEvidenceDetector):
    """Teste mot-clé mais texte suivant trop court."""
    text = "Il a été prouvé que A." # "A." (len 2) < min_evidence_length 15
    result = detector_default.detect_evidence(text)
    assert result == [] # Ne devrait rien trouver car trop court, et pas de fallback global dans ce mock

    # Avec config custom (min_length 10)
    text_custom = "Preuve: B." # "B." (len 2) < min_evidence_length 10
    result_custom = detector_custom_config.detect_evidence(text_custom)
    assert result_custom == []

    text_custom_valid = "Source: C'est valide ici." # "C'est valide ici." (len 18) >= min_evidence_length 10
    result_custom_valid = detector_custom_config.detect_evidence(text_custom_valid)
    assert len(result_custom_valid) == 1
    assert result_custom_valid[0]["type"] == "Preuve par Mot-Clé (Mock)"
    assert result_custom_valid[0]["evidence_text"] == "C'est valide ici."
    assert result_custom_valid[0]["keyword_used"] == "Source:"

def test_detect_evidence_factual_digit_if_no_keywords(detector_default: MockEvidenceDetector):
    """Teste preuve factuelle (chiffre) si aucun mot-clé n'est trouvé."""
    text = "La population a augmenté de 1000 habitants. C'est un fait."
    # min_evidence_length = 15
    # "La population a augmenté de 1000 habitants." (OK, contient chiffre)
    # "C'est un fait." (OK, mais pas de chiffre/%)
    result = detector_default.detect_evidence(text)
    assert len(result) == 1 
    evidence = result[0]
    assert evidence["type"] == "Preuve Factuelle (Chiffre/%) (Mock)"
    assert evidence["evidence_text"] == "La population a augmenté de 1000 habitants"
    assert evidence["strength_simulated"] == 0.70

def test_detect_evidence_factual_percent_if_no_keywords(detector_default: MockEvidenceDetector):
    """Teste preuve factuelle (%) si aucun mot-clé n'est trouvé."""
    text = "Le taux de réussite est de 95%. C'est excellent."
    result = detector_default.detect_evidence(text)
    assert len(result) == 1
    evidence = result[0]
    assert evidence["type"] == "Preuve Factuelle (Chiffre/%) (Mock)"
    assert evidence["evidence_text"] == "Le taux de réussite est de 95%"

def test_detect_evidence_factual_filtered_by_length(detector_custom_config: MockEvidenceDetector):
    """Teste que les preuves factuelles sont filtrées par longueur."""
    # min_evidence_length = 10
    text = "Augmentation: 3%. Court. Plus long: 1234567890."
    # "Augmentation: 3%" (len 16) > 10
    # "Court" (len 5) < 10
    # "Plus long: 1234567890" (len 22) > 10
    result = detector_custom_config.detect_evidence(text)
    assert len(result) == 2
    texts = {ev["evidence_text"] for ev in result}
    assert "Augmentation: 3%" in texts
    assert "Plus long: 1234567890" in texts

def test_detect_evidence_by_citation_if_no_keywords_or_factual(detector_default: MockEvidenceDetector):
    """Teste preuve par citation si rien d'autre n'est trouvé."""
    text = 'Il a dit: "Ceci est une citation directe et pertinente." Et puis autre chose.'
    result = detector_default.detect_evidence(text)
    assert len(result) == 1
    evidence = result[0]
    assert evidence["type"] == "Preuve par Citation (Mock)"
    assert evidence["evidence_text"] == "Ceci est une citation directe et pertinente."
    assert evidence["strength_simulated"] == 0.75
    quote_start = text.find('"') + 1
    quote_end = text.find('"', quote_start)
    assert evidence["source_indices"] == (quote_start, quote_end)

def test_detect_evidence_citation_too_short(detector_custom_config: MockEvidenceDetector):
    """Teste qu'une citation trop courte n'est pas prise."""
    # min_evidence_length = 10
    text = 'Il a dit: "Courte".' # "Courte" (len 6) < 10
    result = detector_custom_config.detect_evidence(text)
    assert result == []

def test_detect_evidence_priority_order(detector_default: MockEvidenceDetector):
    """Teste l'ordre de priorité: Mot-clé > Factuel > Citation."""
    # 1. Mot-clé a priorité
    text_keyword_and_factual = "Selon l'étude, 50% des cas sont résolus. Il y a aussi 20 chiffres."
    result1 = detector_default.detect_evidence(text_keyword_and_factual)
    assert len(result1) == 1
    assert result1[0]["type"] == "Preuve par Mot-Clé (Mock)"
    assert result1[0]["evidence_text"] == "50% des cas sont résolus." # Texte après mot-clé

    # 2. Factuel a priorité sur Citation (si pas de mot-clé)
    text_factual_and_citation = 'Le rapport indique 75% de succès. Il a aussi affirmé: "C\'est vrai".'
    result2 = detector_default.detect_evidence(text_factual_and_citation)
    assert len(result2) == 1
    assert result2[0]["type"] == "Preuve Factuelle (Chiffre/%) (Mock)"
    assert result2[0]["evidence_text"] == "Le rapport indique 75% de succès"
    
    # 3. Citation en dernier recours
    text_only_citation = 'Quelqu\'un a dit: "Ceci est la seule preuve disponible ici et elle est assez longue pour être valide".'
    result3 = detector_default.detect_evidence(text_only_citation)
    assert len(result3) == 1
    assert result3[0]["type"] == "Preuve par Citation (Mock)"
    assert result3[0]["evidence_text"] == "Ceci est la seule preuve disponible ici et elle est assez longue pour être valide"

def test_detect_evidence_multiple_keywords(detector_default: MockEvidenceDetector):
    """Teste la détection de plusieurs mots-clés."""
    text = (
        "Selon l'étude, les faits sont têtus. "
        "Par exemple, les chiffres ne mentent pas."
    )
    result = detector_default.detect_evidence(text)
    assert len(result) == 2
    keywords_found = {ev["keyword_used"] for ev in result}
    assert "selon l'étude" in keywords_found
    assert "par exemple" in keywords_found
    
    evidence_texts = {ev["evidence_text"] for ev in result}
    assert "les faits sont têtus." in evidence_texts
    assert "les chiffres ne mentent pas." in evidence_texts