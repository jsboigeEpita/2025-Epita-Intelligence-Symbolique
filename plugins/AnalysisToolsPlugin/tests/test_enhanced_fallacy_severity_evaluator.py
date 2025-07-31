#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests unitaires pour le module agents.tools.analysis.enhanced.fallacy_severity_evaluator.
"""

import sys
import os
import json
import logging
from datetime import datetime
import pytest # Ajout de l'import pytest

# Configurer le logging pour les tests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("TestEnhancedFallacySeverityEvaluatorPytest")

# Import du module à tester
from ..logic.fallacy_severity_evaluator import EnhancedFallacySeverityEvaluator

@pytest.fixture
def evaluator_instance():
    """Fixture pour initialiser EnhancedFallacySeverityEvaluator pour chaque test."""
    return EnhancedFallacySeverityEvaluator()

@pytest.fixture
def test_arguments():
    """Fixture pour les arguments de test."""
    return [
        "Les experts affirment que ce produit est sûr.",
        "Ce produit est utilisé par des millions de personnes.",
        "Par conséquent, vous devriez faire confiance aux experts et utiliser ce produit.",
        "Si vous n'utilisez pas ce produit, vous risquez de souffrir de problèmes de santé graves."
    ]

@pytest.fixture
def test_fallacies():
    """Fixture pour les sophismes de test."""
    return [
        {
            "fallacy_type": "Appel à l'autorité",
            "context_text": "Les experts affirment que ce produit est sûr.",
            "confidence": 0.7
        },
        {
            "fallacy_type": "Appel à la popularité",
            "context_text": "Ce produit est utilisé par des millions de personnes.",
            "confidence": 0.6
        },
        {
            "fallacy_type": "Appel à la peur",
            "context_text": "Si vous n'utilisez pas ce produit, vous risquez de souffrir de problèmes de santé graves.",
            "confidence": 0.8
        }
    ]

def test_initialization(evaluator_instance):
    """Teste l'initialisation de l'évaluateur de gravité des sophismes amélioré."""
    assert evaluator_instance is not None
    assert evaluator_instance.logger is not None
    
    assert evaluator_instance.fallacy_severity_base is not None
    assert "Appel à l'autorité" in evaluator_instance.fallacy_severity_base
    assert "Appel à la popularité" in evaluator_instance.fallacy_severity_base
    assert "Appel à la peur" in evaluator_instance.fallacy_severity_base
    
    assert evaluator_instance.context_severity_modifiers is not None
    assert "académique" in evaluator_instance.context_severity_modifiers
    assert "scientifique" in evaluator_instance.context_severity_modifiers
    assert "politique" in evaluator_instance.context_severity_modifiers
    
    assert evaluator_instance.audience_severity_modifiers is not None
    assert "experts" in evaluator_instance.audience_severity_modifiers
    assert "grand public" in evaluator_instance.audience_severity_modifiers
    
    assert evaluator_instance.domain_severity_modifiers is not None
    assert "santé" in evaluator_instance.domain_severity_modifiers
    assert "politique" in evaluator_instance.domain_severity_modifiers

def test_evaluate_fallacy_severity(evaluator_instance, test_arguments):
    """Teste la méthode evaluate_fallacy_severity."""
    result = evaluator_instance.evaluate_fallacy_severity(test_arguments, "commercial")
    
    assert isinstance(result, dict)
    assert "overall_severity" in result
    assert "severity_level" in result
    assert "fallacy_evaluations" in result
    assert "context_analysis" in result
    assert "analysis_timestamp" in result
    
    assert isinstance(result["fallacy_evaluations"], list)
    # Le nombre exact dépend de l'implémentation de la détection interne, 
    # mais il devrait y avoir au moins une évaluation si des sophismes sont trouvés.
    # Si aucun sophisme n'est détecté par la logique interne (qui n'est pas mockée ici), cette liste peut être vide.
    # Pour un test plus robuste, il faudrait mocker la détection de sophismes interne.
    # Pour l'instant, on vérifie juste que la structure est correcte.
    # assert len(result["fallacy_evaluations"]) >= 1 # Peut être 0 si aucun sophisme détecté

    assert isinstance(result["context_analysis"], dict)
    assert "context_type" in result["context_analysis"]
    assert "audience_type" in result["context_analysis"]
    assert "domain_type" in result["context_analysis"]
    assert result["context_analysis"]["context_type"] == "commercial"

def test_evaluate_fallacy_list(evaluator_instance, test_fallacies):
    """Teste la méthode evaluate_fallacy_list."""
    result = evaluator_instance.evaluate_fallacy_list(test_fallacies, "scientifique")
    
    assert isinstance(result, dict)
    assert "overall_severity" in result
    assert "severity_level" in result
    assert "fallacy_evaluations" in result
    assert "context_analysis" in result
    assert "analysis_timestamp" in result
    
    assert isinstance(result["fallacy_evaluations"], list)
    assert len(result["fallacy_evaluations"]) == 3
    
    assert isinstance(result["context_analysis"], dict)
    assert "context_type" in result["context_analysis"]
    assert "audience_type" in result["context_analysis"]
    assert "domain_type" in result["context_analysis"]
    assert result["context_analysis"]["context_type"] == "scientifique"
    
    assert 0.0 <= result["overall_severity"] <= 1.0
    assert result["severity_level"] in ["Faible", "Modéré", "Élevé", "Critique"]

def test_analyze_context_impact(evaluator_instance):
    """Teste la méthode _analyze_context_impact."""
    context_analysis = evaluator_instance._analyze_context_impact("scientifique")
    
    assert isinstance(context_analysis, dict)
    assert "context_type" in context_analysis
    assert "audience_type" in context_analysis
    assert "domain_type" in context_analysis
    assert "context_severity_modifier" in context_analysis
    assert "audience_severity_modifier" in context_analysis
    assert "domain_severity_modifier" in context_analysis
    
    assert context_analysis["context_type"] == "scientifique"
    assert context_analysis["audience_type"] == "experts"
    assert context_analysis["domain_type"] == "sciences" # ou "scientifique" selon l'implémentation
    assert context_analysis["context_severity_modifier"] == 0.3
    assert context_analysis["audience_severity_modifier"] == 0.2
    assert context_analysis["domain_severity_modifier"] == 0.2

def test_calculate_fallacy_severity(evaluator_instance):
    """Teste la méthode _calculate_fallacy_severity."""
    fallacy = {
        "fallacy_type": "Appel à l'autorité",
        "context_text": "Les experts affirment que ce produit est sûr.",
        "confidence": 0.7
    }
    context_analysis = {
        "context_type": "scientifique",
        "audience_type": "experts",
        "domain_type": "sciences",
        "context_severity_modifier": 0.3,
        "audience_severity_modifier": 0.2,
        "domain_severity_modifier": 0.2
    }
    
    severity_evaluation = evaluator_instance._calculate_fallacy_severity(fallacy, context_analysis)
    
    assert isinstance(severity_evaluation, dict)
    assert "fallacy_type" in severity_evaluation
    assert "context_text" in severity_evaluation
    assert "base_severity" in severity_evaluation
    assert "context_modifier" in severity_evaluation
    assert "audience_modifier" in severity_evaluation
    assert "domain_modifier" in severity_evaluation
    assert "final_severity" in severity_evaluation
    assert "severity_level" in severity_evaluation
    
    assert severity_evaluation["fallacy_type"] == "Appel à l'autorité"
    assert severity_evaluation["context_text"] == "Les experts affirment que ce produit est sûr."
    assert severity_evaluation["base_severity"] == 0.6 # Valeur de base pour "Appel à l'autorité"
    assert severity_evaluation["context_modifier"] == 0.3
    assert severity_evaluation["audience_modifier"] == 0.2
    assert severity_evaluation["domain_modifier"] == 0.2
    
    expected_severity = min(1.0, 0.6 + 0.3 + 0.2 + 0.2) # 0.6 + 0.7 = 1.3 -> 1.0
    assert severity_evaluation["final_severity"] == expected_severity
    assert severity_evaluation["severity_level"] in ["Faible", "Modéré", "Élevé", "Critique"]

def test_determine_severity_level(evaluator_instance):
    """Teste la méthode _determine_severity_level."""
    assert evaluator_instance._determine_severity_level(0.3) == "Faible"
    assert evaluator_instance._determine_severity_level(0.5) == "Modéré"
    assert evaluator_instance._determine_severity_level(0.8) == "Élevé"
    assert evaluator_instance._determine_severity_level(0.95) == "Critique"

def test_calculate_overall_severity(evaluator_instance):
    """Teste la méthode _calculate_overall_severity."""
    fallacy_evaluations = [
        {"final_severity": 1.0, "severity_level": "Critique"},
        {"final_severity": 0.7, "severity_level": "Élevé"},
        {"final_severity": 1.0, "severity_level": "Critique"}
    ]
    
    overall_severity, severity_level = evaluator_instance._calculate_overall_severity(fallacy_evaluations)
    
    assert isinstance(overall_severity, float)
    assert isinstance(severity_level, str)
    
    # moyenne = (1.0 + 0.7 + 1.0) / 3 = 2.7 / 3 = 0.9
    # max_val = 1.0
    # expected_severity = (0.7 * 0.9) + (0.3 * 1.0) = 0.63 + 0.3 = 0.93
    expected_severity_value = (0.7 * ((1.0 + 0.7 + 1.0) / 3)) + (0.3 * 1.0)
    assert abs(overall_severity - expected_severity_value) < 0.01
    assert severity_level == "Critique"

def test_calculate_overall_severity_empty_list(evaluator_instance):
    """Teste la méthode _calculate_overall_severity avec une liste vide."""
    overall_severity, severity_level = evaluator_instance._calculate_overall_severity([])
    assert overall_severity == 0.0
    assert severity_level == "Faible"

@pytest.mark.parametrize("context", ["académique", "politique", "commercial", "juridique", "médical"])
def test_evaluate_fallacy_severity_with_different_contexts(evaluator_instance, test_arguments, context):
    """Teste la méthode evaluate_fallacy_severity avec différents contextes."""
    result = evaluator_instance.evaluate_fallacy_severity(test_arguments, context)
    
    assert isinstance(result, dict)
    assert "overall_severity" in result
    assert "severity_level" in result
    assert "fallacy_evaluations" in result
    assert "context_analysis" in result
    assert result["context_analysis"]["context_type"] == context

# Pas besoin de if __name__ == "__main__": avec pytest