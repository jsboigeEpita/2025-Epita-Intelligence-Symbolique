# -*- coding: utf-8 -*-
"""
Tests unitaires pour les utilitaires de reporting de project_core.
"""
import pytest
from pathlib import Path
import json
from unittest.mock import patch, mock_open, MagicMock

from project_core.utils.reporting_utils import (
    save_json_report,
    generate_json_report,
    save_text_report,
    generate_specific_rhetorical_markdown_report,
    generate_markdown_report_for_corpus,
    generate_overall_summary_markdown
)

# Fixtures pour les données de test
@pytest.fixture
def sample_dict_data() -> dict:
    return {"key1": "value1", "key2": 123, "key3": [1, 2, 3]}

@pytest.fixture
def sample_list_data() -> list:
    return [{"id": 1, "name": "item1"}, {"id": 2, "name": "item2"}]

@pytest.fixture
def sample_analysis_results() -> list:
    return [
        {
            "source_name": "Texte Alpha",
            "analysis": {
                "text": "Ceci est le texte alpha.",
                "fallacies": [
                    {"fallacy_type": "Ad Hominem", "description": "Attaque personnelle.", "severity": "Haute", "confidence": 0.9, "context_text": "alpha"},
                ],
                "categories": {"Attaques Personnelles": ["Ad Hominem"]}
            }
        },
        {
            "source_name": "Texte Beta",
            "error": "Erreur d'analyse majeure."
        },
        {
            "source_name": "Texte Gamma",
            "analysis": {
                "text": "Texte gamma sans sophisme.",
                "fallacies": [],
                "categories": {}
            }
        }
    ]

# Tests pour save_json_report
def test_save_json_report_dict_success(tmp_path, sample_dict_data):
    """Teste la sauvegarde réussie d'un dictionnaire JSON."""
    output_file = tmp_path / "report.json"
    assert save_json_report(sample_dict_data, output_file) is True
    assert output_file.exists()
    with open(output_file, 'r', encoding='utf-8') as f:
        loaded_data = json.load(f)
    assert loaded_data == sample_dict_data

def test_save_json_report_list_success(tmp_path, sample_list_data):
    """Teste la sauvegarde réussie d'une liste JSON."""
    output_file = tmp_path / "report_list.json"
    assert save_json_report(sample_list_data, output_file) is True
    assert output_file.exists()
    with open(output_file, 'r', encoding='utf-8') as f:
        loaded_data = json.load(f)
    assert loaded_data == sample_list_data

def test_save_json_report_os_error(tmp_path, sample_dict_data, mocker, caplog):
    """Teste la gestion d'une OSError lors de la sauvegarde JSON."""
    output_file = tmp_path / "report_os_error.json"
    mocker.patch("builtins.open", side_effect=OSError("Simulated OS Error"))
    assert save_json_report(sample_dict_data, output_file) is False
    assert "Erreur lors de la sauvegarde des données JSON" in caplog.text
    assert "Simulated OS Error" in caplog.text

# Tests pour generate_json_report
def test_generate_json_report_calls_save_json_report(tmp_path, sample_analysis_results, mocker):
    """Teste que generate_json_report appelle save_json_report."""
    output_file = tmp_path / "generated_report.json"
    mock_save_json = mocker.patch("project_core.utils.reporting_utils.save_json_report", return_value=True)
    
    generate_json_report(sample_analysis_results, output_file)
    
    mock_save_json.assert_called_once_with(sample_analysis_results, output_file)

def test_generate_json_report_logs_error_on_save_failure(tmp_path, sample_analysis_results, mocker, caplog):
    """Teste que generate_json_report logue une erreur si save_json_report échoue."""
    output_file = tmp_path / "gen_report_fail.json"
    mocker.patch("project_core.utils.reporting_utils.save_json_report", return_value=False)
    
    generate_json_report(sample_analysis_results, output_file)
    
    assert "Échec final de la génération du rapport JSON" in caplog.text

# Tests pour save_text_report
def test_save_text_report_success(tmp_path):
    """Teste la sauvegarde réussie d'un rapport textuel."""
    output_file = tmp_path / "text_report.md"
    report_content = "# Titre\n\nContenu du rapport."
    assert save_text_report(report_content, output_file) is True
    assert output_file.exists()
    assert output_file.read_text(encoding='utf-8') == report_content

def test_save_text_report_os_error(tmp_path, mocker, caplog):
    """Teste la gestion d'une OSError lors de la sauvegarde textuelle."""
    output_file = tmp_path / "text_report_os_error.txt"
    report_content = "Contenu."
    mocker.patch("builtins.open", side_effect=OSError("Simulated Text OS Error"))
    assert save_text_report(report_content, output_file) is False
    assert "Erreur lors de la sauvegarde du rapport textuel" in caplog.text
    assert "Simulated Text OS Error" in caplog.text

# Tests pour generate_specific_rhetorical_markdown_report
def test_generate_specific_rhetorical_markdown_report_success(tmp_path, sample_analysis_results, mocker):
    """Teste la génération réussie d'un rapport Markdown rhétorique."""
    output_file = tmp_path / "rhetorical_report.md"
    mock_save_text = mocker.patch("project_core.utils.reporting_utils.save_text_report", return_value=True)
    
    generate_specific_rhetorical_markdown_report(sample_analysis_results, output_file)
    
    mock_save_text.assert_called_once()
    # Vérifier le contenu du rapport passé à save_text_report
    args, _ = mock_save_text.call_args
    report_content_generated = args[0]
    
    assert "# Rapport d'Analyse Rhétorique Python" in report_content_generated
    assert "## Analyse de : Texte Alpha" in report_content_generated
    assert "Sophisme 1: Ad Hominem" in report_content_generated
    assert "Attaques Personnelles" in report_content_generated
    assert "## Analyse de : Texte Beta" in report_content_generated
    assert "**Erreur lors de l'analyse :** `Erreur d'analyse majeure.`" in report_content_generated
    assert "## Analyse de : Texte Gamma" in report_content_generated
    assert "Aucun sophisme détecté pour ce texte." in report_content_generated

def test_generate_specific_rhetorical_markdown_report_empty_analysis(tmp_path, mocker):
    """Teste la génération avec des résultats d'analyse vides ou sans analyse."""
    output_file = tmp_path / "empty_rhetoric.md"
    mock_save_text = mocker.patch("project_core.utils.reporting_utils.save_text_report", return_value=True)
    empty_results = [
        {"source_name": "Vide", "analysis": {}},
        {"source_name": "Sans Analyse", "analysis": None} # Simuler un cas où analysis pourrait être None
    ]
    generate_specific_rhetorical_markdown_report(empty_results, output_file)
    args, _ = mock_save_text.call_args
    report_content = args[0]
    assert "Aucune analyse disponible pour cette source (données d'analyse vides)." in report_content
    # Pour le cas "Sans Analyse", la logique actuelle de la fonction ne le gère pas explicitement
    # comme "Aucune analyse disponible" si analysis est None, mais plutôt comme un dict vide.
    # Si analysis est None, .get("text",...) etc. fonctionneront.
    # Le test actuel couvre le cas où analysis est un dict vide.

def test_generate_specific_rhetorical_markdown_report_save_fails(tmp_path, sample_analysis_results, mocker, caplog):
    """Teste le log d'erreur si la sauvegarde du rapport rhétorique échoue."""
    output_file = tmp_path / "rhetoric_save_fail.md"
    mocker.patch("project_core.utils.reporting_utils.save_text_report", return_value=False)
    generate_specific_rhetorical_markdown_report(sample_analysis_results, output_file)
    assert f"Échec de la sauvegarde du rapport Markdown rhétorique spécifique vers {output_file}" in caplog.text

# Tests pour generate_markdown_report_for_corpus
@pytest.fixture
def sample_corpus_data_full() -> dict:
    return {
        "best_agent": "Agent Avancé X",
        "base_agents": {
            "Agent Base A": {"fallacy_count": 5, "effectiveness": 0.75},
            "Agent Base B": {"fallacy_count": 3, "effectiveness": 0.60}
        },
        "advanced_agents": {
            "Agent Avancé X": {"fallacy_count": 10, "effectiveness": 0.92},
            "Agent Avancé Y": {"fallacy_count": 8, "effectiveness": 0.85}
        },
        "recommendations": ["Utiliser Agent X pour ce type de texte.", "Surveiller les faux positifs de B."]
    }

@pytest.fixture
def sample_corpus_data_minimal() -> dict:
    return {} # Données minimales, la fonction doit gérer cela gracieusement

def test_generate_markdown_report_for_corpus_full_data(sample_corpus_data_full):
    """Teste la génération de section de rapport pour un corpus avec toutes les données."""
    corpus_name = "Corpus Test Complet"
    report_lines = generate_markdown_report_for_corpus(corpus_name, sample_corpus_data_full)
    
    report_str = "\n".join(report_lines)
    assert f"### {corpus_name}" in report_str
    assert "**Agent le plus efficace**: Agent Avancé X" in report_str
    assert "#### Agents de base" in report_str
    assert "| Agent Base A | 5 | 0.75 |" in report_str
    assert "#### Agents avancés" in report_str
    assert "| Agent Avancé Y | 8 | 0.85 |" in report_str
    assert "#### Recommandations spécifiques" in report_str
    assert "- Utiliser Agent X pour ce type de texte." in report_str

def test_generate_markdown_report_for_corpus_minimal_data(sample_corpus_data_minimal):
    """Teste la génération avec des données de corpus minimales."""
    corpus_name = "Corpus Minimal"
    report_lines = generate_markdown_report_for_corpus(corpus_name, sample_corpus_data_minimal)
    report_str = "\n".join(report_lines)

    assert f"### {corpus_name}" in report_str
    assert "Agent le plus efficace" not in report_str # Ne devrait pas apparaître
    assert "Agents de base" not in report_str
    assert "Agents avancés" not in report_str
    assert "Recommandations spécifiques" not in report_str

def test_generate_markdown_report_for_corpus_type_error():
    """Teste que generate_markdown_report_for_corpus lève TypeError pour un mauvais nom de corpus."""
    with pytest.raises(TypeError, match="Le paramètre 'corpus_name' doit être une chaîne de caractères."):
        generate_markdown_report_for_corpus(123, {}) # type: ignore

# Tests pour generate_overall_summary_markdown
@pytest.fixture
def sample_all_average_scores() -> dict:
    return {
        "Corpus Alpha": {"confidence_score": 0.88, "contextual_richness": 0.70, "processing_time": 10.5},
        "Corpus Beta": {"confidence_score": 0.92, "contextual_richness": 0.85, "processing_time": 8.2},
        "Corpus Gamma": {"contextual_richness": 0.65, "custom_metric": 0.99} # Métrique manquante, métrique en plus
    }

def test_generate_overall_summary_markdown_success(sample_all_average_scores):
    """Teste la génération réussie du résumé global Markdown."""
    report_lines = generate_overall_summary_markdown(sample_all_average_scores)
    report_str = "\n".join(report_lines)

    assert "## Résumé Global des Scores Moyens par Corpus" in report_str
    # Vérifier l'en-tête du tableau (ordre des métriques est important)
    # Métriques attendues: confidence_score, contextual_richness, custom_metric, processing_time (ordre alpha)
    assert "| Corpus | Confidence Score | Contextual Richness | Custom Metric | Processing Time |" in report_str
    # Vérifier une ligne de données
    assert "| Corpus Alpha | 0.88 | 0.70 | 0.00 | 10.50 |" in report_str # custom_metric est 0.00 car manquante
    assert "| Corpus Beta | 0.92 | 0.85 | 0.00 | 8.20 |" in report_str
    assert "| Corpus Gamma | 0.00 | 0.65 | 0.99 | 0.00 |" in report_str # confidence et processing_time manquantes

def test_generate_overall_summary_markdown_empty_data():
    """Teste la génération du résumé avec des données de scores vides."""
    report_lines = generate_overall_summary_markdown({})
    report_str = "\n".join(report_lines)
    assert "Aucune donnée de score moyen disponible" in report_str

def test_generate_overall_summary_markdown_type_error():
    """Teste que generate_overall_summary_markdown lève TypeError pour de mauvaises données d'entrée."""
    with pytest.raises(TypeError, match="Le paramètre 'all_average_scores' doit être un dictionnaire."):
        generate_overall_summary_markdown([]) # type: ignore

# Test pour generate_performance_comparison_markdown_report (plus simple, car complexe à mocker entièrement)
def test_generate_performance_comparison_markdown_report_runs(tmp_path, mocker):
    """Teste que la fonction de comparaison de performance s'exécute et appelle save_text_report."""
    output_file = tmp_path / "perf_compare_report.md"
    mock_save_text = mocker.patch("project_core.utils.reporting_utils.save_text_report", return_value=True)
    
    base_metrics = {
        'fallacy_counts': {'base_contextual': 10},
        'confidence_scores': {'base_coherence': 0.7},
        'richness_scores': {'base_contextual': 0.6}
    }
    advanced_metrics = {
        'fallacy_counts': {'advanced_contextual': 15, 'advanced_complex': 20},
        'confidence_scores': {'advanced_rhetorical': 0.8, 'advanced_coherence': 0.75, 'advanced_severity': 0.9},
        'richness_scores': {'advanced_contextual': 0.7, 'advanced_rhetorical': 0.85}
    }
    
    generate_performance_comparison_markdown_report(base_metrics, advanced_metrics, output_file)
    
    mock_save_text.assert_called_once()
    args, _ = mock_save_text.call_args
    report_content = args[0]
    assert "# Rapport de comparaison des performances" in report_content
    assert "Agent contextuel de base | 10 |" in report_content # Vérifie une partie des données
    assert "Agent rhétorique avancé fournit l'analyse contextuelle la plus riche." in report_content # Vérifie une partie de l'analyse