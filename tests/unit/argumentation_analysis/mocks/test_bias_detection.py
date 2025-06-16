# -*- coding: utf-8 -*-
"""Tests pour le MockBiasDetector."""

import pytest
import logging
from argumentation_analysis.mocks.bias_detection import MockBiasDetector

@pytest.fixture
def detector_default() -> MockBiasDetector:
    """Instance de MockBiasDetector avec config par défaut."""
    return MockBiasDetector()

@pytest.fixture
def detector_custom_config() -> MockBiasDetector:
    """Instance avec une configuration personnalisée."""
    config = {
        "min_context_length": 10,
        "bias_patterns": {
            "Test Biais (Mock)": [r"pattern test A", r"pattern test B"],
            "Autre Biais (Mock)": [r"exemple spécifique"]
        }
    }
    return MockBiasDetector(config=config)

def test_initialization_default(detector_default: MockBiasDetector):
    """Teste l'initialisation avec la configuration par défaut."""
    assert detector_default.get_config() == {}
    assert detector_default.min_context_length == 20
    assert "Biais de Confirmation (Mock)" in detector_default.bias_patterns
    assert r"il est évident que" in detector_default.bias_patterns["Biais de Confirmation (Mock)"]

def test_initialization_custom_config(detector_custom_config: MockBiasDetector):
    """Teste l'initialisation avec une configuration personnalisée."""
    expected_config = {
        "min_context_length": 10,
        "bias_patterns": {
            "Test Biais (Mock)": [r"pattern test A", r"pattern test B"],
            "Autre Biais (Mock)": [r"exemple spécifique"]
        }
    }
    assert detector_custom_config.get_config() == expected_config
    assert detector_custom_config.min_context_length == 10
    assert detector_custom_config.bias_patterns["Test Biais (Mock)"] == [r"pattern test A", r"pattern test B"]

def test_detect_biases_non_string_input(detector_default: MockBiasDetector, caplog):
    """Teste la détection avec une entrée non textuelle."""
    with caplog.at_level(logging.WARNING):
        result = detector_default.detect_biases(None) # type: ignore
    assert result == []
    assert "MockBiasDetector.detect_biases a reçu une entrée non textuelle." in caplog.text

def test_detect_biases_empty_string(detector_default: MockBiasDetector):
    """Teste avec une chaîne vide."""
    assert detector_default.detect_biases("") == []

def test_detect_biases_short_text_no_triggers(detector_default: MockBiasDetector):
    """Teste un texte court sans aucun déclencheur."""
    # min_context_length est 20 par défaut, le texte lui-même doit être assez long pour le contexte.
    assert detector_default.detect_biases("Texte court.") == [] 

# Tests pour chaque type de biais par défaut
def test_detect_bias_confirmation(detector_default: MockBiasDetector):
    text = "Il est évident que cette solution est la meilleure pour tout le monde."
    result = detector_default.detect_biases(text)
    assert len(result) >= 1
    found_bias = any(b["bias_type"] == "Biais de Confirmation (Mock)" and b["detected_pattern"] == r"il est évident que" for b in result)
    assert found_bias
    # Vérifier le contexte (le mock prend 30 chars avant/après)
    bias_entry = next(b for b in result if b["bias_type"] == "Biais de Confirmation (Mock)")
    assert bias_entry["context_snippet"].startswith("Il est évident que")
    assert bias_entry["context_snippet"].endswith("est la meilleu")

def test_detect_bias_generalisation(detector_default: MockBiasDetector):
    text = "Les politiciens disent toujours la vérité, c'est bien connu."
    result = detector_default.detect_biases(text)
    assert len(result) >= 1
    found_bias = any(b["bias_type"] == "Généralisation Hâtive (Mock)" and b["detected_pattern"] == r"toujours" for b in result)
    assert found_bias
    bias_entry = next(b for b in result if b["bias_type"] == "Généralisation Hâtive (Mock)")
    assert "disent toujours la vérité" in bias_entry["context_snippet"]
    assert bias_entry["severity_simulated"] == "Moyen"

def test_detect_bias_autorite(detector_default: MockBiasDetector):
    text = "Selon l'expert en la matière, cette approche est infaillible."
    result = detector_default.detect_biases(text)
    assert len(result) >= 1
    found_bias = any(b["bias_type"] == "Biais d'Autorité (Mock)" and b["detected_pattern"] == r"selon l'expert" for b in result)
    assert found_bias

def test_detect_bias_faux_dilemme(detector_default: MockBiasDetector):
    text = "C'est simple: soit A ou soit B, il n'y a pas d'autre choix possible."
    result = detector_default.detect_biases(text)
    assert len(result) >= 1
    found_bias = any(b["bias_type"] == "Faux Dilemme (Mock)" and b["detected_pattern"] == r"soit A ou soit B" for b in result)
    assert found_bias

def test_detect_biases_pattern_context_too_short(detector_custom_config: MockBiasDetector):
    """Teste un pattern trouvé mais le contexte autour est trop court."""
    # min_context_length = 10 pour detector_custom_config
    # Le pattern "pattern test A" est trouvé, mais le texte total est court.
    # Le contexte est text[max(0, match.start()-30):min(len(text), match.end()+30)]
    # Si text = "pattern test A", match.start=0, match.end=14. Contexte = text.
    # len(contexte) = 14 >= min_context_length 10. Donc ça devrait passer.
    text = "pattern test A" 
    result = detector_custom_config.detect_biases(text)
    assert len(result) == 1
    assert result[0]["bias_type"] == "Test Biais (Mock)"
    assert result[0]["detected_pattern"] == "pattern test A"

    # Si le texte est juste le pattern et min_context_length > len(pattern)
    short_detector = MockBiasDetector(config={"min_context_length": 30, "bias_patterns": {"Short (Mock)": ["shortpattern"]}})
    text_short_pattern = "shortpattern" # len 12
    result_short = short_detector.detect_biases(text_short_pattern) # min_context_length 30
    assert len(result_short) == 0 # Contexte (12) < min_context_length (30)

def test_detect_biases_exageration_fallback(detector_default: MockBiasDetector):
    """Teste le fallback sur 'Exagération Potentielle' si aucun autre biais et texte long."""
    text = "Ce film est absolument incroyable, une pure merveille. Rien d'autre à signaler de biaisé." 
    # Assurez-vous que ce texte est > 100 chars et ne contient pas les patterns de biais principaux.
    # Pour être sûr, on rend le texte plus long.
    text_long = text + " " + ("bla " * 30)
    assert len(text_long) > 100

    result = detector_default.detect_biases(text_long)
    assert len(result) == 1
    bias = result[0]
    assert bias["bias_type"] == "Exagération Potentielle (Mock)"
    assert bias["detected_pattern"] == "absolument incroyable"
    assert bias["severity_simulated"] == "Faible"

def test_detect_biases_no_exageration_if_other_bias_found(detector_default: MockBiasDetector):
    """Teste que l'exagération n'est pas détectée si un autre biais est présent."""
    text = "Il est évident que ce film est absolument incroyable. " + ("bla " * 30)
    result = detector_default.detect_biases(text)
    assert len(result) >= 1
    has_confirmation_bias = any(b["bias_type"] == "Biais de Confirmation (Mock)" for b in result)
    has_exageration_bias = any(b["bias_type"] == "Exagération Potentielle (Mock)" for b in result)
    assert has_confirmation_bias
    assert not has_exageration_bias # Le fallback ne devrait pas s'activer

def test_detect_biases_no_exageration_if_text_too_short(detector_default: MockBiasDetector):
    """Teste que l'exagération n'est pas détectée si le texte est trop court (<100)."""
    text = "Ce film est absolument incroyable." # len < 100
    result = detector_default.detect_biases(text)
    assert len(result) == 0

def test_detect_biases_multiple_patterns_same_type(detector_default: MockBiasDetector):
    """Teste la détection de plusieurs patterns pour un même type de biais."""
    # Biais de Confirmation (Mock) a "il est évident que" et "tout le monde sait que"
    text = "Il est évident que c'est vrai. D'ailleurs, tout le monde sait que c'est comme ça."
    result = detector_default.detect_biases(text)
    
    confirmation_biases = [b for b in result if b["bias_type"] == "Biais de Confirmation (Mock)"]
    assert len(confirmation_biases) == 2
    
    patterns_found = {b["detected_pattern"] for b in confirmation_biases}
    assert r"il est évident que" in patterns_found
    assert r"tout le monde sait que" in patterns_found

def test_detect_biases_structure_and_indices(detector_default: MockBiasDetector):
    """Vérifie la structure et les indices source."""
    text = "Selon l'expert, c'est la seule voie. Jamais une autre option n'a fonctionné."
    # Devrait trouver "Biais d'Autorité" et "Généralisation Hâtive"
    result = detector_default.detect_biases(text)
    assert len(result) >= 2 # Peut y en avoir plus si les patterns sont larges

    for bias in result:
        assert "bias_type" in bias
        assert "detected_pattern" in bias
        assert "context_snippet" in bias
        assert "severity_simulated" in bias
        assert "confidence" in bias
        assert "source_indices" in bias
        assert isinstance(bias["source_indices"], tuple)
        assert len(bias["source_indices"]) == 2
        
        start, end = bias["source_indices"]
        assert text[start:end].lower() == bias["detected_pattern"].lower() or \
               bias["detected_pattern"].lower() in text[start:end].lower() # Pour les regex plus complexes