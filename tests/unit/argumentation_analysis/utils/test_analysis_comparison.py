# -*- coding: utf-8 -*-
"""Tests pour les utilitaires de comparaison d'analyses."""

import pytest
from datetime import datetime
from argumentation_analysis.utils.analysis_comparison import compare_rhetorical_analyses

@pytest.fixture
def sample_base_results_full():
    return {
        "analyses": {
            "fallacy_detection": {
                "fallacy_count": 2,
                "argument_results": [
                    {"detected_fallacies": [{"type": "ad_hominem"}]},
                    {"detected_fallacies": [{"type": "straw_man"}]}
                ]
            },
            "coherence_evaluation": {
                "overall_coherence": {"score": 0.6, "level": "Modérée"},
                "score": 0.6 # Ancien format possible
            },
            "analysis_depth": "Modérée"
        }
    }

@pytest.fixture
def sample_advanced_results_full():
    return {
        "analyses": {
            "contextual_fallacies": { # Nouveau nom possible
                "contextual_fallacies_count": 3,
                "argument_results": [
                    {"detected_fallacies": [{"type": "ad_hominem_adv"}]},
                    {"detected_fallacies": [{"type": "appeal_to_emotion"}]},
                    {"detected_fallacies": [{"type": "slippery_slope"}]}
                ]
            },
            "rhetorical_results": { # Nouveau nom possible
                "coherence_analysis": {"overall_coherence": {"score": 0.8, "level": "Élevée"}},
                "overall_analysis": {"rhetorical_quality": 0.85, "analysis_depth": "Élevée"}
            }
        }
    }

def test_compare_rhetorical_analyses_valid_inputs(sample_advanced_results_full, sample_base_results_full):
    """Teste la comparaison avec des entrées valides et complètes."""
    comparison = compare_rhetorical_analyses(sample_advanced_results_full, sample_base_results_full)
    
    assert "timestamp" in comparison
    
    fdc = comparison["fallacy_detection_comparison"]
    assert fdc["advanced_fallacy_count"] == 3
    assert fdc["base_fallacy_count"] == 2
    assert fdc["difference"] == 1
    
    cac = comparison["coherence_analysis_comparison"]
    assert cac["advanced_coherence_score"] == 0.8
    assert cac["base_coherence_score"] == 0.6
    assert round(cac["difference"], 2) == 0.2
    assert cac["advanced_coherence_level"] == "Élevée"
    assert cac["base_coherence_level"] == "Modérée"
    
    oc = comparison["overall_comparison"]
    assert oc["advanced_analysis_depth"] == "Élevée"
    assert oc["base_analysis_depth"] == "Modérée"
    assert oc["advanced_quality_score"] == 0.85
    assert len(oc["key_improvements_with_advanced"]) > 0

def test_compare_rhetorical_analyses_missing_keys_advanced(sample_base_results_full):
    """Teste la robustesse aux clés manquantes dans les résultats avancés."""
    advanced_results_missing = {
        "analyses": {
            # Pas de contextual_fallacies ou fallacy_detection
            "rhetorical_results": {
                # Pas de coherence_analysis
                "overall_analysis": {"rhetorical_quality": 0.7} # Pas de analysis_depth
            }
        }
    }
    comparison = compare_rhetorical_analyses(advanced_results_missing, sample_base_results_full)
    
    fdc = comparison["fallacy_detection_comparison"]
    assert fdc["advanced_fallacy_count"] == 0
    assert fdc["base_fallacy_count"] == 2
    assert fdc["difference"] == -2
    
    cac = comparison["coherence_analysis_comparison"]
    assert cac["advanced_coherence_score"] == 0.0
    assert cac["base_coherence_score"] == 0.6
    assert round(cac["difference"], 2) == -0.6
    assert cac["advanced_coherence_level"] == "N/A" # ou valeur par défaut de adv_coherence
    
    oc = comparison["overall_comparison"]
    assert oc["advanced_analysis_depth"] == "Élevée" # Valeur par défaut
    assert oc["advanced_quality_score"] == 0.7

def test_compare_rhetorical_analyses_missing_keys_base(sample_advanced_results_full):
    """Teste la robustesse aux clés manquantes dans les résultats de base."""
    base_results_missing = {
        "analyses": {
            # Pas de fallacy_detection
            # Pas de coherence_evaluation
            # Pas de analysis_depth
        }
    }
    comparison = compare_rhetorical_analyses(sample_advanced_results_full, base_results_missing)

    fdc = comparison["fallacy_detection_comparison"]
    assert fdc["advanced_fallacy_count"] == 3
    assert fdc["base_fallacy_count"] == 0
    assert fdc["difference"] == 3

    cac = comparison["coherence_analysis_comparison"]
    assert cac["advanced_coherence_score"] == 0.8
    assert cac["base_coherence_score"] == 0.0
    assert round(cac["difference"], 2) == 0.8
    assert cac["base_coherence_level"] == "N/A"

    oc = comparison["overall_comparison"]
    assert oc["base_analysis_depth"] == "Modérée" # Valeur par défaut

def test_compare_rhetorical_analyses_empty_inputs():
    """Teste avec des dictionnaires d'entrée vides."""
    comparison = compare_rhetorical_analyses({}, {})
    
    fdc = comparison["fallacy_detection_comparison"]
    assert fdc["advanced_fallacy_count"] == 0
    assert fdc["base_fallacy_count"] == 0
    
    cac = comparison["coherence_analysis_comparison"]
    assert cac["advanced_coherence_score"] == 0.0
    assert cac["base_coherence_score"] == 0.0
    assert cac["advanced_coherence_level"] == "N/A"
    assert cac["base_coherence_level"] == "N/A"

    oc = comparison["overall_comparison"]
    assert oc["advanced_analysis_depth"] == "Élevée" # Valeur par défaut
    assert oc["base_analysis_depth"] == "Modérée" # Valeur par défaut
    assert oc["advanced_quality_score"] == 0.0

def test_compare_rhetorical_analyses_invalid_inputs():
    """Teste avec des entrées qui ne sont pas des dictionnaires."""
    comparison_list_adv = compare_rhetorical_analyses([], {"test": 1})
    assert "error" in comparison_list_adv
    assert comparison_list_adv["error"] == "Entrées invalides pour la comparaison."

    comparison_list_base = compare_rhetorical_analyses({"test": 1}, [])
    assert "error" in comparison_list_base
    assert comparison_list_base["error"] == "Entrées invalides pour la comparaison."

    comparison_none = compare_rhetorical_analyses(None, None)
    assert "error" in comparison_none
    assert comparison_none["error"] == "Entrées invalides pour la comparaison."

def test_alternative_fallacy_structure_advanced(sample_base_results_full):
    """Teste une structure alternative pour les sophismes dans les résultats avancés."""
    advanced_alt_fallacy = {
        "analyses": {
            "fallacy_detection": { # Nom alternatif
                "argument_results": [
                    {"detected_fallacies": [{"type": "A"}, {"type": "B"}]}, # 2 ici
                    {"detected_fallacies": [{"type": "C"}]}  # 1 ici
                ]
                # Pas de contextual_fallacies_count direct
            },
             "rhetorical_results": {
                "coherence_analysis": {"overall_coherence": {"score": 0.7, "level": "Bonne"}},
            }
        }
    }
    comparison = compare_rhetorical_analyses(advanced_alt_fallacy, sample_base_results_full)
    fdc = comparison["fallacy_detection_comparison"]
    assert fdc["advanced_fallacy_count"] == 3 # 2 + 1
    assert fdc["base_fallacy_count"] == 2
    assert fdc["difference"] == 1

def test_alternative_fallacy_structure_base(sample_advanced_results_full):
    """Teste une structure alternative pour les sophismes dans les résultats de base."""
    base_alt_fallacy = {
        "analyses": {
            "fallacy_detection": { # Nom alternatif
                "fallacy_count": 4 # Compte direct
            },
            "coherence_evaluation": {
                "score": 0.5, "level": "Moyenne"
            }
        }
    }
    comparison = compare_rhetorical_analyses(sample_advanced_results_full, base_alt_fallacy)
    fdc = comparison["fallacy_detection_comparison"]
    assert fdc["advanced_fallacy_count"] == 3
    assert fdc["base_fallacy_count"] == 4 # Doit prendre le fallacy_count direct
    assert fdc["difference"] == -1

def test_alternative_coherence_structure(sample_advanced_results_full, sample_base_results_full):
    """Teste des structures alternatives pour la cohérence."""
    adv_alt_coherence = {
        "analyses": {
            "coherence_evaluation": {"score": 0.88, "level": "Très Bonne"} # Pas de rhetorical_results
        }
    }
    base_alt_coherence = {
        "analyses": {
            "coherence_evaluation": {"score": 0.55, "level": "Passable"} # Pas de argument_coherence
        }
    }
    # On ne passe que les données de cohérence pour simplifier, les autres seront à 0/Défaut
    comparison = compare_rhetorical_analyses(adv_alt_coherence, base_alt_coherence)
    cac = comparison["coherence_analysis_comparison"]
    assert cac["advanced_coherence_score"] == 0.88
    assert cac["base_coherence_score"] == 0.55
    assert round(cac["difference"], 2) == 0.33
    assert cac["advanced_coherence_level"] == "Très Bonne"
    assert cac["base_coherence_level"] == "Passable"