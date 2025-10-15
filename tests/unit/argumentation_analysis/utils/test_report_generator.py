#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests pour les utilitaires de génération de rapports Markdown de argumentation_analysis.utils.report_generator.
"""
import pytest
from pathlib import Path
from typing import (
    List,
    Dict,
    Any,
)  # List n'est pas utilisé mais conservé pour cohérence
from datetime import datetime

# Ajuster le PYTHONPATH pour les tests
import sys

project_root_path = Path(__file__).resolve().parent.parent.parent.parent
if str(project_root_path) not in sys.path:
    sys.path.insert(0, str(project_root_path))
# Commenté car l'installation du package via `pip install -e .` devrait gérer l'accessibilité.

from argumentation_analysis.utils.report_generator import (
    generate_markdown_performance_report,
)


@pytest.fixture
def sample_metrics_for_markdown_report() -> Dict[str, Dict[str, Any]]:
    """Fournit des exemples de métriques pour le rapport Markdown."""
    return {
        "agent_A": {
            "fallacy_count": 3.0,
            "confidence": 0.8,
            "execution_time": 15.0,
            "false_positive_rate": 0.1,
            "false_negative_rate": 0.05,
            "contextual_richness": 4,
            "relevance": 3,
            "complexity": 2.0,
            "recommendation_relevance": 1.0,
        },
        "agent_B": {
            "fallacy_count": 1.5,
            "confidence": 0.6,
            "execution_time": 25.0,
            "false_positive_rate": 0.2,
            "false_negative_rate": 0.15,
            "contextual_richness": 2,
            "relevance": 1,
            "complexity": 1.0,
        },
    }


@pytest.fixture
def sample_results_summary() -> Dict[str, Any]:
    """Fournit un exemple de résumé de résultats."""
    return {"count": 10, "sources": ["Source1", "Source2"]}


def test_generate_markdown_performance_report_creation_and_content(
    sample_metrics_for_markdown_report: Dict[str, Dict[str, Any]],
    sample_results_summary: Dict[str, Any],
    tmp_path: Path,
):
    """Teste la création du fichier Markdown et vérifie une partie de son contenu."""
    output_file = tmp_path / "performance_report.md"

    generate_markdown_performance_report(
        sample_metrics_for_markdown_report,
        sample_results_summary,
        {"count": 5, "sources": ["Source3"]},
        output_file,
    )

    assert output_file.exists() and output_file.is_file()
    content = output_file.read_text(encoding="utf-8")

    assert (
        "# Rapport de Comparaison des Performances des Agents d'Analyse Rhétorique"
        in content
    )
    assert "## 2. Données Analysées" in content
    assert (
        f"- Nombre d'extraits pour l'analyse de base: {sample_results_summary['count']}"
        in content
    )
    assert "## 3. Métriques de Performance Agrégées par Agent/Type d'Analyse" in content
    assert (
        "| agent_A | 3.00 | 0.80 | 0.10 | 0.05 | 15.00 | 4.00 | 3.00 | 2.00 | 1.00 |"
        in content
    )
    assert (
        "| agent_B | 1.50 | 0.60 | 0.20 | 0.15 | 25.00 | 2.00 | 1.00 | 1.00 | 0.00 |"
        in content
    )
    assert "## 4. Analyse Détaillée et Recommandations (Exemples)" in content
    assert "- **Meilleure détection (nombre moyen) :** agent_A (3.00)" in content
    current_date_str = datetime.now().strftime("%Y-%m-%d")  # Comparer seulement la date
    assert (
        f"*Date de génération: {current_date_str}" in content
    )  # Vérifie au moins la date


def test_generate_markdown_performance_report_empty_metrics(
    sample_results_summary: Dict[str, Any], tmp_path: Path
):
    output_file = tmp_path / "empty_metrics_report.md"
    generate_markdown_performance_report(
        {}, sample_results_summary, sample_results_summary, output_file
    )
    assert output_file.exists()
    content = output_file.read_text(encoding="utf-8")
    assert "## 3. Métriques de Performance Agrégées par Agent/Type d'Analyse" in content
    assert content.count("| Agent/Type | Sophismes (moy.) |") == 1
    assert "| N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A |" in content
    assert "Aucune métrique disponible pour l'analyse détaillée." in content


def test_generate_markdown_performance_report_io_error(
    sample_metrics_for_markdown_report: Dict[str, Dict[str, Any]],
    sample_results_summary: Dict[str, Any],
    tmp_path: Path,
    caplog,
):
    output_file = tmp_path  # tmp_path est un répertoire, causera une IOError

    with caplog.at_level("ERROR"):
        generate_markdown_performance_report(
            sample_metrics_for_markdown_report,
            sample_results_summary,
            sample_results_summary,
            output_file,
        )

    assert f"Erreur lors de l'écriture du rapport Markdown {output_file}" in caplog.text
    assert output_file.is_dir()
