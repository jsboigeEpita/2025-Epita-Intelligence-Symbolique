#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests pour les utilitaires d'extraction de métriques de argumentation_analysis.utils.metrics_extraction.
"""
import pytest
from pathlib import Path # Bien que non utilisé directement, souvent utile pour les fixtures
from typing import List, Dict, Any
from datetime import datetime # Pour les noms d'extraits générés

# Ajuster le PYTHONPATH pour les tests
import sys
# project_root_path = Path(__file__).resolve().parent.parent.parent.parent
# if str(project_root_path) not in sys.path:
#     sys.path.insert(0, str(project_root_path))
# Commenté car l'installation du package via `pip install -e .` devrait gérer l'accessibilité.

from argumentation_analysis.utils.metrics_extraction import (
    extract_execution_time_from_results,
    count_fallacies_in_results,
    extract_confidence_scores_from_results,
    analyze_contextual_richness_from_results,
    evaluate_coherence_relevance_from_results,
    _calculate_obj_complexity,
    analyze_result_complexity_from_results
)

# Fixtures et tests pour extract_execution_time_from_results

@pytest.fixture
def sample_results_for_time_extraction() -> List[Dict[str, Any]]:
    """Fournit des exemples de résultats pour tester l'extraction du temps."""
    return [
        {
            "extract_name": "Extract1",
            "timestamp": "2023-01-01T10:00:00",
            "analyses": {
                "analysis_A": {"analysis_timestamp": "2023-01-01T10:00:05"}, # 5s
                "analysis_B": {"analysis_timestamp": "2023-01-01T10:00:15"}  # 15s
            }
        },
        {
            "extract_name": "Extract2",
            "timestamp": "2023-01-01T11:00:00",
            "analyses": {
                "analysis_A": {"analysis_timestamp": "2023-01-01T11:00:10"}, # 10s
                "analysis_C": {"analysis_timestamp": "2023-01-01T11:00:30"}  # 30s
            }
        },
        { "extract_name": "Extract_NoMainTS", "analyses": {"analysis_A": {"analysis_timestamp": "2023-01-01T12:00:05"}} },
        { "extract_name": "Extract_NoAnalysisTS", "timestamp": "2023-01-01T13:00:00", "analyses": {"analysis_A": {}} },
        { "extract_name": "Extract_InvalidMainTS", "timestamp": "invalid-date-format", "analyses": {"analysis_A": {"analysis_timestamp": "2023-01-01T14:00:05"}} },
        { "extract_name": "Extract_InvalidAnalysisTS", "timestamp": "2023-01-01T15:00:00", "analyses": {"analysis_A": {"analysis_timestamp": "invalid-date"}} },
        { "extract_name": "Extract_NoAnalysesKey", "timestamp": "2023-01-01T16:00:00" },
        { "extract_name": "Extract_AnalysesNotDict", "timestamp": "2023-01-01T17:00:00", "analyses": "not_a_dict" },
        { "timestamp": "2023-01-01T18:00:00", "analyses": {"analysis_X": {"analysis_timestamp": "2023-01-01T18:00:05"}} }
    ]

@pytest.mark.use_real_numpy
def test_extract_execution_time_success(sample_results_for_time_extraction: List[Dict[str, Any]]):
    results_subset = sample_results_for_time_extraction[:2]
    execution_times = extract_execution_time_from_results(results_subset)
    assert "Extract1" in execution_times and execution_times["Extract1"]["analysis_A"] == 5.0 and execution_times["Extract1"]["analysis_B"] == 15.0
    assert "Extract2" in execution_times and execution_times["Extract2"]["analysis_A"] == 10.0 and execution_times["Extract2"]["analysis_C"] == 30.0

@pytest.mark.use_real_numpy
def test_extract_execution_time_empty_results():
    assert extract_execution_time_from_results([]) == {}

@pytest.mark.use_real_numpy
def test_extract_execution_time_missing_or_invalid_data(sample_results_for_time_extraction: List[Dict[str, Any]]):
    problematic_results = sample_results_for_time_extraction[2:]
    execution_times = extract_execution_time_from_results(problematic_results)
    assert "Extract_NoMainTS" not in execution_times
    assert "analysis_A" not in execution_times.get("Extract_NoAnalysisTS", {})
    assert "Extract_InvalidMainTS" not in execution_times
    assert "analysis_A" not in execution_times.get("Extract_InvalidAnalysisTS", {})
    assert "Extract_NoAnalysesKey" not in execution_times
    assert "Extract_AnalysesNotDict" not in execution_times
    found_generated_name = any(key.startswith("Inconnu_") and execution_times[key].get("analysis_X") == 5.0 for key in execution_times)
    assert found_generated_name

# Fixtures et tests pour count_fallacies_in_results

@pytest.fixture
def sample_results_for_fallacy_counting() -> List[Dict[str, Any]]:
    return [
        {"extract_name": "Extract_Fallacy1", "analyses": {"contextual_fallacies": {"argument_results": [{"detected_fallacies": [{"type": "Ad Hominem"}, {"type": "Straw Man"}]}, {"detected_fallacies": [{"type": "Hasty Generalization"}]}]}, "complex_fallacies": {"individual_fallacies_count": 1, "basic_combinations": [{}, {}], "advanced_combinations": [{}], "fallacy_patterns": [{}, {}, {}]}}},
        {"extract_name": "Extract_Fallacy_None", "analyses": {"contextual_fallacies": {"argument_results": [{"detected_fallacies": []}], "contextual_fallacies_count": 0}, "complex_fallacies": {"individual_fallacies_count": 0, "basic_combinations": [], "advanced_combinations": [], "fallacy_patterns": []}}},
        {"extract_name": "Extract_Fallacy_MissingKeys", "analyses": {"contextual_fallacies": {}, "complex_fallacies": {}}},
        {"extract_name": "Extract_NoAnalyses"},
        {"extract_name": "Extract_AnalysesNotDict", "analyses": "not_a_dict"},
        {"analyses": {"contextual_fallacies": { "argument_results": [{"detected_fallacies": [{"type": "Appeal to Emotion"}]}]}}},
        {"extract_name": "Extract_AdvContextual", "analyses": {"contextual_fallacies": {"argument_results": [{"detected_fallacies": [{"type": "Ad Hominem"}]}], "contextual_fallacies_count": 5}, "complex_fallacies": {"individual_fallacies_count": 0}}}
    ]

@pytest.mark.use_real_numpy
def test_count_fallacies_success(sample_results_for_fallacy_counting: List[Dict[str, Any]]):
    results_subset = [sample_results_for_fallacy_counting[0], sample_results_for_fallacy_counting[6]]
    fallacy_counts = count_fallacies_in_results(results_subset)
    assert fallacy_counts["Extract_Fallacy1"]["base_contextual"] == 3 and fallacy_counts["Extract_Fallacy1"]["advanced_complex"] == 7 and fallacy_counts["Extract_Fallacy1"]["advanced_contextual"] == 0
    assert fallacy_counts["Extract_AdvContextual"]["base_contextual"] == 1 and fallacy_counts["Extract_AdvContextual"]["advanced_complex"] == 0 and fallacy_counts["Extract_AdvContextual"]["advanced_contextual"] == 5

@pytest.mark.use_real_numpy
def test_count_fallacies_none_and_missing(sample_results_for_fallacy_counting: List[Dict[str, Any]]):
    results_subset = sample_results_for_fallacy_counting[1:5]
    fallacy_counts = count_fallacies_in_results(results_subset)
    assert fallacy_counts["Extract_Fallacy_None"]["base_contextual"] == 0 and fallacy_counts["Extract_Fallacy_None"]["advanced_complex"] == 0 and fallacy_counts["Extract_Fallacy_None"]["advanced_contextual"] == 0
    assert fallacy_counts["Extract_Fallacy_MissingKeys"]["base_contextual"] == 0 and fallacy_counts["Extract_Fallacy_MissingKeys"]["advanced_complex"] == 0 and fallacy_counts["Extract_Fallacy_MissingKeys"]["advanced_contextual"] == 0
    assert fallacy_counts["Extract_NoAnalyses"] == {"base_contextual": 0, "advanced_complex": 0, "advanced_contextual": 0}
    assert fallacy_counts["Extract_AnalysesNotDict"] == {"base_contextual": 0, "advanced_complex": 0, "advanced_contextual": 0}

@pytest.mark.use_real_numpy
def test_count_fallacies_empty_results():
    assert count_fallacies_in_results([]) == {}

@pytest.mark.use_real_numpy
def test_count_fallacies_extract_name_missing(sample_results_for_fallacy_counting: List[Dict[str, Any]]):
    results_subset = [sample_results_for_fallacy_counting[5]]
    fallacy_counts = count_fallacies_in_results(results_subset)
    generated_name_key = list(fallacy_counts.keys())[0]
    assert generated_name_key.startswith("Inconnu_") and fallacy_counts[generated_name_key]["base_contextual"] == 1

# Fixtures et tests pour extract_confidence_scores_from_results

@pytest.fixture
def sample_results_for_confidence_scores() -> List[Dict[str, Any]]:
    return [
        {"extract_name": "Extract_Conf1", "analyses": {"argument_coherence": {"overall_coherence": {"score": 0.85}}, "rhetorical_results": {"overall_analysis": {"rhetorical_quality": 0.75}, "coherence_analysis": {"overall_coherence": 0.90}}, "fallacy_severity": {"overall_severity": 0.60}}},
        {"extract_name": "Extract_Conf_Zeros", "analyses": {"argument_coherence": {"overall_coherence": {}}, "rhetorical_results": {"overall_analysis": {"rhetorical_quality": 0.0}}}},
        {"extract_name": "Extract_Conf_MissingStruct", "analyses": {"argument_coherence": "not_a_dict", "rhetorical_results": {"overall_analysis": "not_a_dict"}}},
        {"extract_name": "Extract_Conf_NoAnalyses"},
        {"analyses": {"argument_coherence": {"overall_coherence": {"score": 0.5}}}}
    ]

@pytest.mark.use_real_numpy
def test_extract_confidence_scores_success(sample_results_for_confidence_scores: List[Dict[str, Any]]):
    results_subset = [sample_results_for_confidence_scores[0]]
    confidence_scores = extract_confidence_scores_from_results(results_subset)
    scores1 = confidence_scores["Extract_Conf1"]
    assert scores1["base_coherence"] == 0.85 and scores1["advanced_rhetorical"] == 0.75 and scores1["advanced_coherence"] == 0.90 and scores1["advanced_severity"] == 0.60

@pytest.mark.use_real_numpy
def test_extract_confidence_scores_zeros_and_missing(sample_results_for_confidence_scores: List[Dict[str, Any]]):
    results_subset = sample_results_for_confidence_scores[1:4]
    confidence_scores = extract_confidence_scores_from_results(results_subset)
    assert confidence_scores["Extract_Conf_Zeros"]["base_coherence"] == 0.0 and confidence_scores["Extract_Conf_Zeros"]["advanced_rhetorical"] == 0.0
    assert confidence_scores["Extract_Conf_MissingStruct"]["base_coherence"] == 0.0
    assert confidence_scores["Extract_Conf_NoAnalyses"] == {}

@pytest.mark.use_real_numpy
def test_extract_confidence_scores_empty_results():
    assert extract_confidence_scores_from_results([]) == {}

@pytest.mark.use_real_numpy
def test_extract_confidence_scores_extract_name_missing(sample_results_for_confidence_scores: List[Dict[str, Any]]):
    results_subset = [sample_results_for_confidence_scores[4]]
    confidence_scores = extract_confidence_scores_from_results(results_subset)
    generated_name_key = list(confidence_scores.keys())[0]
    assert generated_name_key.startswith("Inconnu_") and confidence_scores[generated_name_key]["base_coherence"] == 0.5

# Fixtures et tests pour analyze_contextual_richness_from_results

@pytest.fixture
def sample_results_for_richness_analysis() -> List[Dict[str, Any]]:
    return [
        {"extract_name": "Extract_Rich1", "analyses": {"contextual_fallacies": {"contextual_factors": {"f1": "v1", "f2": "v2"}, "context_analysis": {"context_type": "Debate", "context_subtypes": ["Pol", "Pub"], "audience_characteristics": ["Exp", "Lay"], "formality_level": "Formal"}}, "rhetorical_results": {"overall_analysis": {"main_strengths": ["Clarity", "Evidence"], "main_weaknesses": ["Tone"], "context_relevance": True}}}},
        {"extract_name": "Extract_Rich_Empty", "analyses": {"contextual_fallacies": {"contextual_factors": {}, "context_analysis": {"context_subtypes": [], "audience_characteristics": []}}, "rhetorical_results": {"overall_analysis": {"main_strengths": [], "main_weaknesses": []}}}},
        {"extract_name": "Extract_Rich_MissingStruct", "analyses": {"contextual_fallacies": "not_a_dict", "rhetorical_results": {}}},
        {"extract_name": "Extract_Rich_NoAnalyses"},
        {"analyses": {"contextual_fallacies": {"contextual_factors": {"fx": "vx"}}}}
    ]

@pytest.mark.use_real_numpy
def test_analyze_contextual_richness_success(sample_results_for_richness_analysis: List[Dict[str, Any]]):
    results_subset = [sample_results_for_richness_analysis[0]]
    richness_scores = analyze_contextual_richness_from_results(results_subset)
    scores1 = richness_scores["Extract_Rich1"]
    assert scores1["base_contextual"] == 2.0 and scores1["advanced_contextual"] == 6.0 and scores1["advanced_rhetorical"] == 4.0

@pytest.mark.use_real_numpy
def test_analyze_contextual_richness_empty_and_missing(sample_results_for_richness_analysis: List[Dict[str, Any]]):
    results_subset = sample_results_for_richness_analysis[1:4]
    richness_scores = analyze_contextual_richness_from_results(results_subset)
    assert richness_scores["Extract_Rich_Empty"]["base_contextual"] == 0.0
    assert richness_scores["Extract_Rich_MissingStruct"]["base_contextual"] == 0.0
    assert richness_scores["Extract_Rich_NoAnalyses"] == {}

@pytest.mark.use_real_numpy
def test_analyze_contextual_richness_empty_results_list():
    assert analyze_contextual_richness_from_results([]) == {}

@pytest.mark.use_real_numpy
def test_analyze_contextual_richness_extract_name_missing(sample_results_for_richness_analysis: List[Dict[str, Any]]):
    results_subset = [sample_results_for_richness_analysis[4]]
    richness_scores = analyze_contextual_richness_from_results(results_subset)
    generated_name_key = list(richness_scores.keys())[0]
    assert generated_name_key.startswith("Inconnu_") and richness_scores[generated_name_key]["base_contextual"] == 1.0

# Fixtures et tests pour evaluate_coherence_relevance_from_results

@pytest.fixture
def sample_results_for_coherence_relevance() -> List[Dict[str, Any]]:
    return [
        {"extract_name": "Extract_CohRel1", "analyses": {"argument_coherence": {"recommendations": ["R1", "R2"], "coherence_evaluations": {"e1": {}, "e2": {}, "e3": {}}}, "rhetorical_results": {"coherence_analysis": {"overall_coherence": 0.8, "coherence_level": "High", "thematic_coherence": 0.9, "logical_coherence": 0.7}, "recommendations": {"coherence_recommendations": ["AR1", "AR2", "AR3"]}}}},
        {"extract_name": "Extract_CohRel_Empty", "analyses": {"argument_coherence": {"recommendations": [], "coherence_evaluations": {}}, "rhetorical_results": {"coherence_analysis": {}, "recommendations": {"coherence_recommendations": []}}}},
        {"extract_name": "Extract_CohRel_MissingStruct", "analyses": {"argument_coherence": "not_a_dict", "rhetorical_results": {"coherence_analysis": "not_a_dict", "recommendations": "not_a_dict"}}},
        {"extract_name": "Extract_CohRel_NoAnalyses"},
        {"analyses": {"argument_coherence": {"recommendations": ["R1"]}}}
    ]

@pytest.mark.use_real_numpy
def test_evaluate_coherence_relevance_success(sample_results_for_coherence_relevance: List[Dict[str, Any]]):
    results_subset = [sample_results_for_coherence_relevance[0]]
    relevance_scores = evaluate_coherence_relevance_from_results(results_subset)
    scores1 = relevance_scores["Extract_CohRel1"]
    assert scores1["base_coherence"] == 5.0 and scores1["advanced_coherence"] == 4.0 and scores1["advanced_recommendations"] == 3.0

@pytest.mark.use_real_numpy
def test_evaluate_coherence_relevance_empty_and_missing(sample_results_for_coherence_relevance: List[Dict[str, Any]]):
    results_subset = sample_results_for_coherence_relevance[1:4]
    relevance_scores = evaluate_coherence_relevance_from_results(results_subset)
    assert relevance_scores["Extract_CohRel_Empty"]["base_coherence"] == 0.0
    assert relevance_scores["Extract_CohRel_MissingStruct"]["base_coherence"] == 0.0
    assert relevance_scores["Extract_CohRel_NoAnalyses"] == {}

@pytest.mark.use_real_numpy
def test_evaluate_coherence_relevance_empty_results_list():
    assert evaluate_coherence_relevance_from_results([]) == {}

@pytest.mark.use_real_numpy
def test_evaluate_coherence_relevance_extract_name_missing(sample_results_for_coherence_relevance: List[Dict[str, Any]]):
    results_subset = [sample_results_for_coherence_relevance[4]]
    relevance_scores = evaluate_coherence_relevance_from_results(results_subset)
    generated_name_key = list(relevance_scores.keys())[0]
    assert generated_name_key.startswith("Inconnu_") and relevance_scores[generated_name_key]["base_coherence"] == 1.0

# Tests pour _calculate_obj_complexity et analyze_result_complexity_from_results

@pytest.mark.use_real_numpy
def test_calculate_obj_complexity():
    assert _calculate_obj_complexity("simple_string") == 0.0
    assert _calculate_obj_complexity([]) == 0.0
    assert _calculate_obj_complexity({}) == 0.0
    assert _calculate_obj_complexity(["a", "b"]) == 1.0
    assert _calculate_obj_complexity({"k1": "v1", "k2": "v2"}) == 1.0
    assert pytest.approx(_calculate_obj_complexity(["a", ["b", "c"]])) == 2.0
    assert pytest.approx(_calculate_obj_complexity({"k1": "v1", "k2": {"nk1": "nv1"}})) == 2.0
    complex_obj = {"a": [1, {"b": [2,3]}, 4], "c": 5}
    assert pytest.approx(_calculate_obj_complexity(complex_obj)) == 3.1666666666666665

@pytest.fixture
def sample_results_for_complexity() -> List[Dict[str, Any]]:
    return [
        {"extract_name": "Extract_Comp1", "analyses": {"simple_analysis": "just a string", "list_analysis": [1, 2, 3], "dict_analysis": {"k1": "v1", "k2": "v2"}}},
        {"extract_name": "Extract_Comp_Nested", "analyses": {"nested_list": ["a", ["b", ["c"]]], "nested_dict": {"k1": "v1", "k2": {"nk1": "nv1", "nk2": {"nnk1": "nnv1"}}}}},
        {"extract_name": "Extract_Comp_EmptyAnalyses", "analyses": {}},
        {"extract_name": "Extract_Comp_NoAnalysesKey"},
        {"extract_name": "Extract_Comp_AnalysesNotDict", "analyses": "not_a_dict_or_list"}
    ]

@pytest.mark.use_real_numpy
def test_analyze_result_complexity_success(sample_results_for_complexity: List[Dict[str, Any]]):
    results_subset = sample_results_for_complexity[:2]
    complexity_scores = analyze_result_complexity_from_results(results_subset)
    scores1 = complexity_scores["Extract_Comp1"]
    assert scores1["simple_analysis"] == 0.0 and pytest.approx(scores1["list_analysis"]) == 1.0 and pytest.approx(scores1["dict_analysis"]) == 1.0
    scores_nested = complexity_scores["Extract_Comp_Nested"]
    assert pytest.approx(scores_nested["nested_list"]) == 2.75 and pytest.approx(scores_nested["nested_dict"]) == 2.75

@pytest.mark.use_real_numpy
def test_analyze_result_complexity_empty_and_missing(sample_results_for_complexity: List[Dict[str, Any]]):
    results_subset = sample_results_for_complexity[2:]
    complexity_scores = analyze_result_complexity_from_results(results_subset)
    assert complexity_scores["Extract_Comp_EmptyAnalyses"] == {}
    assert complexity_scores["Extract_Comp_NoAnalysesKey"] == {}
    assert complexity_scores["Extract_Comp_AnalysesNotDict"] == {}

@pytest.mark.use_real_numpy
def test_analyze_result_complexity_empty_results_list():
    assert analyze_result_complexity_from_results([]) == {}