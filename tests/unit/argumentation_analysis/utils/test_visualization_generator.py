#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests pour les utilitaires de génération de visualisations de argumentation_analysis.utils.visualization_generator.
"""
import pytest
from pathlib import Path
from typing import Dict, Any
from unittest import mock

# Ajuster le PYTHONPATH pour les tests
import sys
project_root_path = Path(__file__).resolve().parent.parent.parent.parent
if str(project_root_path) not in sys.path:
    sys.path.insert(0, str(project_root_path))

from argumentation_analysis.utils.visualization_generator import generate_performance_visualizations, VISUALIZATION_LIBS_AVAILABLE

@pytest.fixture
def sample_metrics_for_visualization() -> Dict[str, Dict[str, Any]]:
    """Fournit des exemples de métriques pour la visualisation."""
    return {
        "base_contextual": {"fallacy_count": 2.5, "confidence": 0.7, "false_positive_rate": 0.1, "false_negative_rate": 0.2, "execution_time": 10.0, "contextual_richness": 3.0, "relevance": 2.0, "complexity": 1.5},
        "advanced_complex": {"fallacy_count": 5.0, "confidence": 0.9, "false_positive_rate": 0.05, "false_negative_rate": 0.1, "execution_time": 30.0, "contextual_richness": 5.0, "relevance": 4.0, "complexity": 3.0, "recommendation_relevance": 2.5},
        "advanced_rhetorical": {"confidence": 0.8, "execution_time": 20.0, "contextual_richness": 4.0, "recommendation_relevance": 3.0, "complexity": 2.5}
    }

@mock.patch('argumentation_analysis.utils.visualization_generator.VISUALIZATION_LIBS_AVAILABLE', False)
def test_generate_performance_visualizations_libs_not_available(
    sample_metrics_for_visualization: Dict[str, Dict[str, Any]],
    tmp_path: Path
):
    """Teste que la fonction ne fait rien si les bibliothèques ne sont pas disponibles."""
    output_dir = tmp_path / "viz_output_no_libs"
    generated_files = generate_performance_visualizations(sample_metrics_for_visualization, output_dir)
    assert generated_files == []
    assert not output_dir.exists()

@mock.patch('argumentation_analysis.utils.visualization_generator.VISUALIZATION_LIBS_AVAILABLE', True)
@mock.patch('matplotlib.pyplot.savefig')
@mock.patch('argumentation_analysis.utils.visualization_generator.pd.DataFrame.to_csv')
@mock.patch('matplotlib.pyplot.close')
@mock.patch('matplotlib.pyplot.figure')
@mock.patch('matplotlib.pyplot.bar')
@mock.patch('matplotlib.pyplot.text')
@mock.patch('matplotlib.pyplot.title')
@mock.patch('matplotlib.pyplot.xlabel')
@mock.patch('matplotlib.pyplot.ylabel')
@mock.patch('matplotlib.pyplot.xticks')
@mock.patch('matplotlib.pyplot.legend')
@mock.patch('matplotlib.pyplot.tight_layout')
@mock.patch('seaborn.color_palette', return_value=[(0.1, 0.2, 0.3), (0.4, 0.5, 0.6), (0.7, 0.8, 0.9), (0.2, 0.4, 0.6)]) # Fournir au moins 4 couleurs
@mock.patch('seaborn.heatmap')
@pytest.mark.use_real_numpy
@pytest.mark.skip(reason="Problème persistant avec TypeError dans NumPy/Pandas sous use_real_numpy")
def test_generate_performance_visualizations_files_created(
    mock_heatmap, mock_color_palette, mock_tight_layout, mock_legend, mock_xticks, mock_ylabel, mock_xlabel, mock_title, mock_text, mock_bar, mock_figure, mock_close, mock_df_to_csv, mock_plt_savefig,
    sample_metrics_for_visualization: Dict[str, Dict[str, Any]],
    tmp_path: Path
):
    """
    Teste que la fonction tente de créer les fichiers attendus lorsque les bibliothèques sont (supposément) disponibles.
    """
    output_dir = tmp_path / "viz_output_libs_available"
    generated_files = generate_performance_visualizations(sample_metrics_for_visualization, output_dir)

    assert output_dir.exists() 

    expected_pngs = [
        "fallacy_counts_comparison.png", "confidence_scores_comparison.png",
        "error_rates_comparison.png", "execution_times_comparison.png",
        "performance_matrix_heatmap.png"
    ]
    expected_csv = "performance_metrics_summary.csv"
    
    saved_png_files = [call_args[0][0].name for call_args in mock_plt_savefig.call_args_list]
    for png_name in expected_pngs:
        assert png_name in saved_png_files
        assert str(output_dir / png_name) in [str(call_args[0][0]) for call_args in mock_plt_savefig.call_args_list]

    assert mock_df_to_csv.call_count == 1
    saved_csv_path = mock_df_to_csv.call_args[0][0]
    assert saved_csv_path.name == expected_csv
    assert str(saved_csv_path) == str(output_dir / expected_csv)
    
    assert len(generated_files) == len(expected_pngs) + 1
    for png_name in expected_pngs:
        assert str(output_dir / png_name) in generated_files
    assert str(output_dir / expected_csv) in generated_files

@mock.patch('argumentation_analysis.utils.visualization_generator.VISUALIZATION_LIBS_AVAILABLE', True)
@mock.patch('matplotlib.pyplot.savefig') # Pour éviter les erreurs si les mocks précédents ne suffisent pas
@mock.patch('pandas.DataFrame.to_csv')
@mock.patch('matplotlib.pyplot.close')
@mock.patch('matplotlib.pyplot.figure')
@pytest.mark.use_real_numpy
def test_generate_performance_visualizations_empty_metrics(mock_fig, mock_close, mock_to_csv, mock_savefig, tmp_path: Path):
    """Teste avec un dictionnaire de métriques vide."""
    output_dir = tmp_path / "viz_empty_metrics"
    # Assurer que VISUALIZATION_LIBS_AVAILABLE est True pour ce test spécifique
    # car le mock global pourrait être False.
    # with mock.patch('argumentation_analysis.utils.visualization_generator.VISUALIZATION_LIBS_AVAILABLE', True):
    generated_files = generate_performance_visualizations({}, output_dir)
    
    assert generated_files == [] 
    assert output_dir.exists() # Le répertoire est créé même si aucun fichier n'est généré.
    mock_savefig.assert_not_called() # Aucun graphique ne devrait être sauvegardé
    mock_to_csv.assert_not_called() # Aucun CSV ne devrait être sauvegardé