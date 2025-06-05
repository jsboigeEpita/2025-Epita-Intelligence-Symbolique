#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests unitaires pour le module agents.tools.analysis.enhanced.complex_fallacy_analyzer.
"""

import sys
import os
import json
import logging
import pytest

# Configurer le logging pour les tests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("TestEnhancedComplexFallacyAnalyzerPytest")

# Ajouter le répertoire racine au chemin Python pour pouvoir importer les modules
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# L'installation du package via `pip install -e .` devrait gérer l'accessibilité,
# mais cette modification assure le fonctionnement même sans installation en mode édition.
# Normalement géré par conftest.py et PYTHONPATH, mais ajout explicite pour robustesse.

# Importer les mocks pour numpy et pandas
# Le répertoire tests/mocks est ajouté à sys.path par conftest.py
from tests.mocks.legacy_numpy_array_mock import *
from tests.mocks.pandas_mock import *

# Import du module à tester
from argumentation_analysis.agents.tools.analysis.enhanced.complex_fallacy_analyzer import EnhancedComplexFallacyAnalyzer

# Données de test partagées (fixtures potentielles ou constantes de module)
ARGUMENTS_DATA = [
    {
        "id": "arg-1",
        "text": "Tous les experts sont d'accord que le réchauffement climatique est réel, donc c'est vrai.",
        "confidence": 0.9,
        "source": "texte-1",
        "position": {"start": 0, "end": 80}
    },
    {
        "id": "arg-2",
        "text": "Si nous acceptons le mariage homosexuel, bientôt les gens voudront épouser des animaux.",
        "confidence": 0.85,
        "source": "texte-1",
        "position": {"start": 81, "end": 160}
    },
    {
        "id": "arg-3",
        "text": "Mon opposant n'a pas de diplôme en économie, donc son plan économique est forcément mauvais.",
        "confidence": 0.8,
        "source": "texte-1",
        "position": {"start": 161, "end": 240}
    }
]

FALLACIES_DATA = [
    {
        "id": "fallacy-1",
        "type": "Appel à l'autorité",
        "argument_id": "arg-1",
        "confidence": 0.7,
        "description": "L'argument repose uniquement sur l'opinion d'experts sans présenter de preuves."
    },
    {
        "id": "fallacy-2",
        "type": "Pente glissante",
        "argument_id": "arg-2",
        "confidence": 0.8,
        "description": "L'argument suggère qu'une action mènera inévitablement à une chaîne d'événements indésirables sans justification."
    },
    {
        "id": "fallacy-3",
        "type": "Ad hominem",
        "argument_id": "arg-3",
        "confidence": 0.9,
        "description": "L'argument attaque la personne plutôt que ses idées."
    }
]

@pytest.fixture(scope="module")
def analyzer_instance():
    """Fixture pour initialiser EnhancedComplexFallacyAnalyzer une fois par module."""
    logger.info("Initialisation de EnhancedComplexFallacyAnalyzer pour le module de test.")
    analyzer = EnhancedComplexFallacyAnalyzer()
    return analyzer

def test_initialization(analyzer_instance):
    """Test l'initialisation de l'analyseur."""
    assert analyzer_instance is not None
    assert analyzer_instance.contextual_analyzer is not None
    assert analyzer_instance.severity_evaluator is not None
    assert analyzer_instance.argument_structure_patterns is not None
    assert analyzer_instance.advanced_fallacy_combinations is not None

def test_analyze_complex_fallacies(analyzer_instance):
    """Test la détection de sophismes composites."""
    arguments_text = [arg["text"] for arg in ARGUMENTS_DATA]
    result = analyzer_instance.detect_composite_fallacies(arguments_text, "général")
    assert isinstance(result, dict)
    assert "basic_combinations" in result
    assert "advanced_combinations" in result
    assert "fallacy_patterns" in result
    assert "composite_severity" in result
    assert isinstance(result["basic_combinations"], list)
    assert isinstance(result["advanced_combinations"], list)
    assert isinstance(result["fallacy_patterns"], list)

def test_detect_fallacy_combinations(analyzer_instance):
    """Test l'identification des combinaisons de sophismes."""
    fallacies_text = " ".join([fallacy["description"] for fallacy in FALLACIES_DATA])
    combinations = analyzer_instance.identify_combined_fallacies(fallacies_text)
    assert isinstance(combinations, list)

def test_analyze_argument_structure(analyzer_instance):
    """Test l'analyse de la structure des arguments."""
    arguments_text = [arg["text"] for arg in ARGUMENTS_DATA]
    result = analyzer_instance.analyze_argument_structure(arguments_text, "général")
    assert isinstance(result, dict)
    assert "identified_structures" in result
    assert "argument_relations" in result
    assert "coherence_evaluation" in result
    assert "vulnerability_analysis" in result

def test_detect_circular_reasoning(analyzer_instance):
    """Test la détection de raisonnements circulaires."""
    circular_arguments = [
        "La Bible est la parole de Dieu car elle le dit elle-même.",
        "La Bible dit qu'elle est la parole de Dieu, donc c'est vrai."
    ]
    result = analyzer_instance.analyze_inter_argument_coherence(circular_arguments, "religieux")
    assert isinstance(result, dict)
    assert "overall_coherence" in result
    assert result["overall_coherence"]["overall_score"] <= 0.6

def test_analyze_structure_vulnerabilities(analyzer_instance):
    """Test l'analyse des vulnérabilités structurelles."""
    arguments_text = [arg["text"] for arg in ARGUMENTS_DATA]
    result = analyzer_instance.analyze_argument_structure(arguments_text, "général")
    assert isinstance(result, dict)
    assert "vulnerability_analysis" in result

def test_evaluate_composite_severity(analyzer_instance):
    """Test l'évaluation de la sévérité composite."""
    arguments_text = [arg["text"] for arg in ARGUMENTS_DATA]
    result = analyzer_instance.detect_composite_fallacies(arguments_text, "général")
    assert isinstance(result, dict)
    assert "composite_severity" in result
    assert "adjusted_severity" in result["composite_severity"]
    assert result["composite_severity"]["adjusted_severity"] >= 0.0
    assert result["composite_severity"]["adjusted_severity"] <= 1.0

def test_analyze_fallacy_interactions(analyzer_instance):
    """Test l'analyse des interactions entre sophismes."""
    arguments_text = [arg["text"] for arg in ARGUMENTS_DATA]
    result = analyzer_instance.detect_composite_fallacies(arguments_text, "général")
    assert isinstance(result, dict)
    assert "basic_combinations" in result
    assert "advanced_combinations" in result

def test_analyze_inter_argument_coherence(analyzer_instance):
    """Test l'analyse de la cohérence inter-arguments."""
    arguments_text = [arg["text"] for arg in ARGUMENTS_DATA]
    result = analyzer_instance.analyze_inter_argument_coherence(arguments_text, "général")
    assert isinstance(result, dict)
    assert "thematic_coherence" in result
    assert "logical_coherence" in result
    assert "overall_coherence" in result

def test_identify_fallacy_patterns(analyzer_instance):
    """Test l'identification des motifs de sophismes."""
    arguments_text = " ".join([arg["text"] for arg in ARGUMENTS_DATA])
    patterns = analyzer_instance.identify_fallacy_patterns(arguments_text)
    assert isinstance(patterns, list)

# Pas besoin de if __name__ == "__main__": avec pytest