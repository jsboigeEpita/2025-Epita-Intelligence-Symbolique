#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests pour les utilitaires d'agrégation de métriques de argumentation_analysis.utils.metrics_aggregation.
"""
import pytest
from pathlib import Path # Non utilisé directement mais bonne pratique
from typing import List, Dict, Any

# Ajuster le PYTHONPATH pour les tests
import sys
project_root_path = Path(__file__).resolve().parent.parent.parent.parent
if str(project_root_path) not in sys.path:
    sys.path.insert(0, str(project_root_path))

from argumentation_analysis.utils.metrics_aggregation import generate_performance_metrics_for_agents
# Les fonctions sous-jacentes (comme count_fallacies_in_results) sont testées dans leurs propres modules.
# Ici, on teste principalement l'agrégation correcte.

@pytest.fixture
def sample_base_results_for_metrics() -> List[Dict[str, Any]]:
    """Exemples de résultats de base pour generate_performance_metrics_for_agents."""
    return [
        {
            "source_name": "S1", "extract_name": "E1", "timestamp": "2023-01-01T10:00:00",
            "analyses": {
                "contextual_fallacies": {"argument_results": [{"detected_fallacies": [{"fallacy_type": "F1"}, {"fallacy_type": "F2"}]}], "contextual_factors": {"cf1":1, "cf2":2}, "analysis_timestamp": "2023-01-01T10:00:10"},
                "argument_coherence": {"overall_coherence": {"score": 0.8}, "recommendations": ["r1"], "coherence_evaluations": {"e1":{}}, "analysis_timestamp": "2023-01-01T10:00:05"},
                "semantic_analysis": {"analysis_timestamp": "2023-01-01T10:00:03"}
            }
        }
    ]

@pytest.fixture
def sample_advanced_results_for_metrics() -> List[Dict[str, Any]]:
    """Exemples de résultats avancés pour generate_performance_metrics_for_agents."""
    return [
        {
            "source_name": "S1", "extract_name": "E1", "timestamp": "2023-01-01T10:00:00",
            "analyses": {
                "contextual_fallacies": {"contextual_fallacies": [{"fallacy_type": "F_AdvCtx1", "confidence": 0.9}], "contextual_fallacies_count": 1, "context_analysis": {"context_type": "Debate", "context_subtypes": ["Pol"]}, "analysis_timestamp": "2023-01-01T10:00:20"},
                "complex_fallacies": {"individual_fallacies_count": 1, "basic_combinations": [{}], "composite_severity": {"severity_level": "Élevé"}, "analysis_timestamp": "2023-01-01T10:00:30"},
                "fallacy_severity": {"overall_severity": 0.7, "analysis_timestamp": "2023-01-01T10:00:25"},
                "rhetorical_results": {"overall_analysis": {"rhetorical_quality": 0.6, "main_strengths":["s1"]}, "coherence_analysis": {"overall_coherence": 0.5, "coherence_level":"Medium"}, "recommendations": {"coherence_recommendations": ["ar1", "ar2"]}, "analysis_timestamp": "2023-01-01T10:00:40"}
            }
        }
    ]

@pytest.mark.use_real_numpy
def test_generate_performance_metrics_for_agents_structure(
    sample_base_results_for_metrics: List[Dict[str, Any]],
    sample_advanced_results_for_metrics: List[Dict[str, Any]]
):
    """Teste la structure de base des métriques générées."""
    metrics = generate_performance_metrics_for_agents(
        sample_base_results_for_metrics,
        sample_advanced_results_for_metrics
    )
    
    expected_agents = ["base_contextual", "base_coherence", "base_semantic",
                       "advanced_contextual", "advanced_complex", "advanced_severity", "advanced_rhetorical"]
    for agent in expected_agents:
        assert agent in metrics
        assert isinstance(metrics[agent], dict)

    assert "fallacy_count" in metrics["base_contextual"]
    assert "confidence" in metrics["base_coherence"]
    assert "execution_time" in metrics["base_semantic"]
    assert "false_positive_rate" in metrics["advanced_contextual"] 
    assert "complexity" in metrics["advanced_complex"]

@pytest.mark.use_real_numpy
def test_generate_performance_metrics_for_agents_calculations(
    sample_base_results_for_metrics: List[Dict[str, Any]],
    sample_advanced_results_for_metrics: List[Dict[str, Any]]
):
    """Teste les valeurs calculées pour certaines métriques."""
    metrics = generate_performance_metrics_for_agents(
        sample_base_results_for_metrics,
        sample_advanced_results_for_metrics
    )

    # Base Contextual
    assert metrics["base_contextual"]["fallacy_count"] == 2.0
    assert metrics["base_contextual"]["execution_time"] == 10.0
    assert metrics["base_contextual"]["contextual_richness"] == 2.0
    assert pytest.approx(metrics["base_contextual"]["false_positive_rate"]) == 1.0 
    assert pytest.approx(metrics["base_contextual"]["false_negative_rate"]) == 1.0 

    # Base Coherence
    assert metrics["base_coherence"]["confidence"] == 0.8
    assert metrics["base_coherence"]["execution_time"] == 5.0
    assert metrics["base_coherence"]["relevance"] == 2.0 # 1 reco + 1 eval key

    # Base Semantic
    assert metrics["base_semantic"]["execution_time"] == 3.0

    # Advanced Contextual
    assert metrics["advanced_contextual"]["fallacy_count"] == 1.0
    assert metrics["advanced_contextual"]["execution_time"] == 20.0
    assert metrics["advanced_contextual"]["contextual_richness"] == 2.0
    assert pytest.approx(metrics["advanced_contextual"]["false_positive_rate"]) == 0.0

    # Advanced Complex
    assert metrics["advanced_complex"]["fallacy_count"] == 2.0
    assert metrics["advanced_complex"]["execution_time"] == 30.0
    assert pytest.approx(metrics["advanced_complex"]["false_positive_rate"]) == 0.05

    # Advanced Severity
    assert metrics["advanced_severity"]["confidence"] == 0.7
    assert metrics["advanced_severity"]["execution_time"] == 25.0

    # Advanced Rhetorical
    assert metrics["advanced_rhetorical"]["confidence"] == 0.6
    assert metrics["advanced_rhetorical"]["execution_time"] == 40.0
    assert metrics["advanced_rhetorical"]["contextual_richness"] == 1.0
    assert metrics["advanced_rhetorical"]["recommendation_relevance"] == 2.0
    assert "relevance" not in metrics["advanced_rhetorical"] or metrics["advanced_rhetorical"]["relevance"] == 0.0

@pytest.mark.use_real_numpy
def test_generate_performance_metrics_empty_inputs():
    """Teste avec des listes de résultats vides."""
    metrics = generate_performance_metrics_for_agents([], [])
    for agent_metrics in metrics.values():
        for metric_value in agent_metrics.values():
            assert metric_value == 0.0