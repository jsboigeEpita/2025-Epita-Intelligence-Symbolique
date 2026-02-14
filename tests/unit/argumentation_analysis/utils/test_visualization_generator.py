#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests pour les utilitaires de génération de visualisations de argumentation_analysis.utils.visualization_generator.
"""

import pytest
from pathlib import Path
from typing import Dict, Any
from unittest.mock import MagicMock

# Ajuster le PYTHONPATH pour les tests
import sys

project_root_path = Path(__file__).resolve().parent.parent.parent.parent
if str(project_root_path) not in sys.path:
    sys.path.insert(0, str(project_root_path))
# Commenté car l'installation du package via `pip install -e .` devrait gérer l'accessibilité.

from argumentation_analysis.utils.visualization_generator import (
    generate_performance_visualizations,
    VISUALIZATION_LIBS_AVAILABLE,
)


@pytest.fixture
def sample_metrics_for_visualization() -> Dict[str, Dict[str, Any]]:
    """Fournit des exemples de métriques pour la visualisation."""
    return {
        "base_contextual": {
            "fallacy_count": 2.5,
            "confidence": 0.7,
            "false_positive_rate": 0.1,
            "false_negative_rate": 0.2,
            "execution_time": 10.0,
            "contextual_richness": 3.0,
            "relevance": 2.0,
            "complexity": 1.5,
        },
        "advanced_complex": {
            "fallacy_count": 5.0,
            "confidence": 0.9,
            "false_positive_rate": 0.05,
            "false_negative_rate": 0.1,
            "execution_time": 30.0,
            "contextual_richness": 5.0,
            "relevance": 4.0,
            "complexity": 3.0,
            "recommendation_relevance": 2.5,
        },
        "advanced_rhetorical": {
            "confidence": 0.8,
            "execution_time": 20.0,
            "contextual_richness": 4.0,
            "recommendation_relevance": 3.0,
            "complexity": 2.5,
        },
    }


def test_generate_performance_visualizations_libs_not_available(
    mocker, sample_metrics_for_visualization: Dict[str, Dict[str, Any]], tmp_path: Path
):
    """Teste que la fonction ne fait rien si les bibliothèques ne sont pas disponibles."""
    mocker.patch(
        "argumentation_analysis.utils.visualization_generator.VISUALIZATION_LIBS_AVAILABLE",
        False,
    )
    output_dir = tmp_path / "viz_output_no_libs"
    generated_files = generate_performance_visualizations(
        sample_metrics_for_visualization, output_dir
    )
    assert generated_files == []
    assert not output_dir.exists()


def test_generate_performance_visualizations_files_created(
    mocker, sample_metrics_for_visualization: Dict[str, Dict[str, Any]], tmp_path: Path
):
    """
    Teste que la fonction tente de créer les fichiers attendus lorsque les bibliothèques sont (supposément) disponibles.
    """
    mocker.patch(
        "argumentation_analysis.utils.visualization_generator.VISUALIZATION_LIBS_AVAILABLE",
        True,
    )

    # Mocker les fonctions de haut niveau de matplotlib et pandas
    mock_plt = mocker.patch("argumentation_analysis.utils.visualization_generator.plt")
    mock_sns = mocker.patch("argumentation_analysis.utils.visualization_generator.sns")
    mocker.patch("argumentation_analysis.utils.visualization_generator.pd")

    # Configurer le mock pour subplots() pour retourner un tuple de mocks
    mock_fig, mock_ax = mocker.MagicMock(), mocker.MagicMock()
    mock_plt.subplots.return_value = (mock_fig, mock_ax)

    output_dir = tmp_path / "viz_output_libs_available"
    generated_files = generate_performance_visualizations(
        sample_metrics_for_visualization, output_dir
    )

    assert output_dir.exists()

    # Vérifier que les fonctions de plotting ont été appelées
    assert mock_plt.subplots.call_count > 0
    assert mock_fig.savefig.call_count > 0

    # Vérifier qu'au moins un graphique a été généré
    assert len(generated_files) > 0


def test_generate_performance_visualizations_empty_metrics(mocker, tmp_path: Path):
    """Teste avec un dictionnaire de métriques vide."""
    mocker.patch(
        "argumentation_analysis.utils.visualization_generator.VISUALIZATION_LIBS_AVAILABLE",
        True,
    )
    mock_savefig = mocker.patch("matplotlib.pyplot.savefig")
    mock_to_csv = mocker.patch("pandas.DataFrame.to_csv")
    mocker.patch("matplotlib.pyplot.close")
    mocker.patch("matplotlib.pyplot.figure")

    output_dir = tmp_path / "viz_empty_metrics"
    generated_files = generate_performance_visualizations({}, output_dir)

    assert generated_files == []
    assert (
        output_dir.exists()
    )  # Le répertoire est créé même si aucun fichier n'est généré.
    mock_savefig.assert_not_called()  # Aucun graphique ne devrait être sauvegardé
    mock_to_csv.assert_not_called()  # Aucun CSV ne devrait être sauvegardé
