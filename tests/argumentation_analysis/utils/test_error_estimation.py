#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests pour les utilitaires d'estimation des taux d'erreur de argumentation_analysis.utils.error_estimation.
"""
import pytest
from pathlib import Path # Non utilisé directement mais bonne pratique
from typing import List, Dict, Any
from datetime import datetime # Pour les noms d'extraits générés

# Ajuster le PYTHONPATH pour les tests
import sys
project_root_path = Path(__file__).resolve().parent.parent.parent.parent
if str(project_root_path) not in sys.path:
    sys.path.insert(0, str(project_root_path))

from argumentation_analysis.utils.error_estimation import estimate_false_positives_negatives_rates

@pytest.fixture
def sample_base_results_for_error_rates() -> List[Dict[str, Any]]:
    """Fournit des exemples de résultats de base pour estimer les taux d'erreur."""
    return [
        {"source_name": "SourceA", "extract_name": "Extract1", "analyses": {"contextual_fallacies": {"argument_results": [{"detected_fallacies": [{"fallacy_type": "AdHominem"}, {"fallacy_type": "StrawMan"}]}, {"detected_fallacies": [{"fallacy_type": "HastyGeneralization"}]}]}}},
        {"source_name": "SourceA", "extract_name": "Extract2", "analyses": {"contextual_fallacies": {"argument_results": [{"detected_fallacies": [{"fallacy_type": "AppealToAuthority"}]}]}}},
        {"source_name": "SourceB", "extract_name": "Extract_OnlyBase", "analyses": {"contextual_fallacies": {"argument_results": [{"detected_fallacies": [{"fallacy_type": "RedHerring"}]}]}}}
    ]

@pytest.fixture
def sample_advanced_results_for_error_rates() -> List[Dict[str, Any]]:
    """Fournit des exemples de résultats avancés pour estimer les taux d'erreur."""
    return [
        {"source_name": "SourceA", "extract_name": "Extract1", "analyses": {"contextual_fallacies": {"contextual_fallacies": [{"fallacy_type": "AdHominem", "confidence": 0.9}, {"fallacy_type": "HastyGeneralization", "confidence": 0.7}, {"fallacy_type": "AppealToEmotion", "confidence": 0.6}]}, "complex_fallacies": {"composite_severity": {"severity_level": "Modéré"}}}},
        {"source_name": "SourceA", "extract_name": "Extract2", "analyses": {"contextual_fallacies": {"contextual_fallacies": [{"fallacy_type": "AppealToAuthority", "confidence": 0.4}, {"fallacy_type": "SlipperySlope", "confidence": 0.8}]}, "complex_fallacies": {"composite_severity": {"severity_level": "Faible"}}}},
        {"source_name": "SourceC", "extract_name": "Extract_OnlyAdvanced", "analyses": {"contextual_fallacies": {"contextual_fallacies": [{"fallacy_type": "FalseDilemma", "confidence": 0.9}]}}}
    ]

def test_estimate_false_positives_negatives_rates_success(
    sample_base_results_for_error_rates: List[Dict[str, Any]],
    sample_advanced_results_for_error_rates: List[Dict[str, Any]]
):
    """Teste l'estimation réussie des taux de FP/FN."""
    error_rates = estimate_false_positives_negatives_rates(
        sample_base_results_for_error_rates,
        sample_advanced_results_for_error_rates
    )
    assert "base_contextual" in error_rates
    assert pytest.approx(error_rates["base_contextual"]["false_positive_rate"], 0.01) == (1/3 + 0)/2 
    assert pytest.approx(error_rates["base_contextual"]["false_negative_rate"], 0.01) == (1/3 + 1/2)/2

    assert "advanced_contextual" in error_rates
    assert pytest.approx(error_rates["advanced_contextual"]["false_positive_rate"], 0.01) == (0/1 + 1/2)/2 # Ajusté pour refléter la logique de la fonction
    assert error_rates["advanced_contextual"]["false_negative_rate"] == 0.0

    assert "advanced_complex" in error_rates
    assert pytest.approx(error_rates["advanced_complex"]["false_positive_rate"], 0.01) == (0.1 + 0.2) / 2
    assert error_rates["advanced_complex"]["false_negative_rate"] == 0.0

def test_estimate_false_positives_negatives_rates_no_common_extracts(
    sample_base_results_for_error_rates: List[Dict[str, Any]]
):
    no_common_advanced_results = [
        {"source_name": "SourceX", "extract_name": "NoMatch1", "analyses": {}},
        {"source_name": "SourceY", "extract_name": "NoMatch2", "analyses": {}}
    ]
    error_rates = estimate_false_positives_negatives_rates(
        sample_base_results_for_error_rates,
        no_common_advanced_results
    )
    expected_empty_rates = {"false_positive_rate": 0.0, "false_negative_rate": 0.0}
    assert error_rates["base_contextual"] == expected_empty_rates
    assert error_rates["advanced_contextual"] == expected_empty_rates
    assert error_rates["advanced_complex"] == expected_empty_rates

def test_estimate_false_positives_negatives_rates_empty_inputs(sample_base_results_for_error_rates, sample_advanced_results_for_error_rates):
    error_rates_empty_base = estimate_false_positives_negatives_rates([], sample_advanced_results_for_error_rates)
    error_rates_empty_advanced = estimate_false_positives_negatives_rates(sample_base_results_for_error_rates, [])
    error_rates_both_empty = estimate_false_positives_negatives_rates([], [])

    expected_empty_rates = {"false_positive_rate": 0.0, "false_negative_rate": 0.0}
    for rates_dict in [error_rates_empty_base, error_rates_empty_advanced, error_rates_both_empty]:
        assert rates_dict["base_contextual"] == expected_empty_rates
        assert rates_dict["advanced_contextual"] == expected_empty_rates
        assert rates_dict["advanced_complex"] == expected_empty_rates

def test_estimate_false_positives_negatives_rates_missing_fallacy_data():
    base_missing_fallacies = [
        {"source_name": "SourceA", "extract_name": "Extract1", "analyses": {}}
    ]
    advanced_missing_fallacies = [
        {"source_name": "SourceA", "extract_name": "Extract1", "analyses": {}}
    ]
    error_rates = estimate_false_positives_negatives_rates(base_missing_fallacies, advanced_missing_fallacies)
    
    expected_empty_rates = {"false_positive_rate": 0.0, "false_negative_rate": 0.0}
    assert error_rates["base_contextual"] == expected_empty_rates
    assert error_rates["advanced_contextual"] == expected_empty_rates
    assert error_rates["advanced_complex"] == expected_empty_rates