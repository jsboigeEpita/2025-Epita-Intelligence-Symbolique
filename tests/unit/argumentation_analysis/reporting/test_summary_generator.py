# -*- coding: utf-8 -*-
"""Tests pour le générateur de synthèses d'analyses rhétoriques."""

import pytest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock, call
from typing import List, Dict, Any

from argumentation_analysis.reporting.summary_generator import (
    run_summary_generation_pipeline,
    generate_rhetorical_analysis_for_extract, # Pourrait être testé plus en détail
    generate_markdown_summary_for_analysis,  # Pourrait être testé plus en détail
    generate_global_summary_report         # Pourrait être testé plus en détail
)

# --- Fixtures pour les données d'entrée du pipeline ---
@pytest.fixture
def sample_simulated_sources_data() -> List[Dict[str, Any]]:
    return [
        {
            "source_name": "TestSource1",
            "extracts": [
                {"extract_name": "Extract1.1", "type": "typeA"},
                {"extract_name": "Extract1.2", "type": "typeB"}
            ]
        }
    ]

@pytest.fixture
def sample_rhetorical_agents_data() -> List[Dict[str, Any]]:
    return [
        {"name": "AgentMock1", "strengths": ["S1"], "weaknesses": ["W1"]},
        {"name": "AgentMock2", "strengths": ["S2"], "weaknesses": ["W2"]}
    ]

@pytest.fixture
def sample_common_fallacies_data() -> List[Dict[str, Any]]:
    return [
        {"name": "FallacyMock1", "description": "Desc1", "severity": "High"}
    ]

@pytest.fixture
def temp_output_reports_dir(tmp_path: Path) -> Path:
    return tmp_path / "test_report_output"

# --- Tests pour run_summary_generation_pipeline ---

@patch("argumentation_analysis.reporting.summary_generator.generate_rhetorical_analysis_for_extract")
@patch("argumentation_analysis.reporting.summary_generator.generate_markdown_summary_for_analysis")
@patch("argumentation_analysis.reporting.summary_generator.generate_global_summary_report")
@patch("builtins.open") # Pour mocker l'écriture du fichier JSON global
@patch("json.dump")
def test_run_summary_generation_pipeline_successful_run(
    mock_json_dump: MagicMock,
    mock_open_global_json: MagicMock,
    mock_generate_global_summary: MagicMock,
    mock_generate_markdown: MagicMock,
    mock_generate_analysis: MagicMock,
    sample_simulated_sources_data: List[Dict[str, Any]],
    sample_rhetorical_agents_data: List[Dict[str, Any]],
    sample_common_fallacies_data: List[Dict[str, Any]],
    temp_output_reports_dir: Path
):
    """Teste une exécution réussie du pipeline de génération de résumés."""
    
    # Configurer les mocks pour qu'ils retournent des valeurs attendues
    mock_generate_analysis.return_value = {"analysis_data": "mocked_analysis"}
    mock_generate_markdown.return_value = temp_output_reports_dir / "summaries" / "mock_summary.md"
    mock_generate_global_summary.return_value = temp_output_reports_dir / "global_mock_report.md"

    run_summary_generation_pipeline(
        sample_simulated_sources_data,
        sample_rhetorical_agents_data,
        sample_common_fallacies_data,
        temp_output_reports_dir
    )

    # Vérifications
    # Nombre d'appels = nb_agents * nb_sources * nb_extracts_per_source
    # Ici: 2 agents * 1 source * 2 extraits = 4 appels à generate_rhetorical_analysis_for_extract
    # et 4 appels à generate_markdown_summary_for_analysis
    assert mock_generate_analysis.call_count == 2 * 2 
    assert mock_generate_markdown.call_count == 2 * 2

    # Vérifier les arguments du premier appel à generate_rhetorical_analysis_for_extract (par exemple)
    first_call_args_analysis = mock_generate_analysis.call_args_list[0][0]
    assert first_call_args_analysis[0] == sample_simulated_sources_data[0]["extracts"][0] # extract_def_item
    assert first_call_args_analysis[1] == sample_simulated_sources_data[0]["source_name"] # source_name_item
    assert first_call_args_analysis[2] == sample_rhetorical_agents_data[0] # agent_config_item
    assert first_call_args_analysis[3] == sample_common_fallacies_data # common_fallacies_data

    # Vérifier l'appel à generate_global_summary_report
    mock_generate_global_summary.assert_called_once()
    args_global_summary = mock_generate_global_summary.call_args[0]
    assert len(args_global_summary[0]) == 4 # all_generated_analyses
    assert args_global_summary[1] == temp_output_reports_dir
    assert args_global_summary[2] == sample_rhetorical_agents_data

    # Vérifier la sauvegarde JSON globale
    mock_open_global_json.assert_called_once() # Doit être appelé pour le JSON global
    # Le nom du fichier contient un timestamp, donc on vérifie le répertoire et le suffixe
    assert mock_open_global_json.call_args[0][0].parent == temp_output_reports_dir
    assert mock_open_global_json.call_args[0][0].name.startswith("all_rhetorical_analyses_simulated_")
    assert mock_open_global_json.call_args[0][0].name.endswith(".json")
    
    mock_json_dump.assert_called_once()
    assert len(mock_json_dump.call_args[0][0]) == 4 # all_generated_analyses

    # Vérifier que le sous-répertoire summaries a été créé (implicitement par generate_markdown_summary_for_analysis)
    summaries_dir = temp_output_reports_dir / "summaries"
    # Le mock de generate_markdown_summary_for_analysis devrait s'assurer de cela,
    # ou le test de cette fonction unitaire. Ici, on vérifie que le chemin passé est correct.
    first_call_args_markdown = mock_generate_markdown.call_args_list[0][0]
    assert first_call_args_markdown[1] == summaries_dir


@patch("argumentation_analysis.reporting.summary_generator.generate_rhetorical_analysis_for_extract", return_value={})
@patch("argumentation_analysis.reporting.summary_generator.generate_markdown_summary_for_analysis", return_value=Path("mock.md"))
@patch("argumentation_analysis.reporting.summary_generator.generate_global_summary_report", return_value=Path("global.md"))
@patch("builtins.open")
@patch("json.dump")
def test_run_summary_generation_pipeline_empty_inputs(
    mock_json_dump: MagicMock,
    mock_open: MagicMock,
    mock_g_global: MagicMock,
    mock_g_md: MagicMock,
    mock_g_analysis: MagicMock,
    temp_output_reports_dir: Path
):
    """Teste le pipeline avec des listes d'entrée vides."""
    
    # 1. Sources vides
    run_summary_generation_pipeline([], [{"name":"A1"}], [{"name":"F1"}], temp_output_reports_dir)
    mock_g_analysis.assert_not_called()
    mock_g_md.assert_not_called()
    # generate_global_summary est appelé même avec une liste vide d'analyses
    mock_g_global.assert_called_once_with([], temp_output_reports_dir, [{"name":"A1"}])
    # json.dump est appelé avec une liste vide
    args_dumped = mock_json_dump.call_args[0][0]
    assert args_dumped == []
    
    mock_g_analysis.reset_mock()
    mock_g_md.reset_mock()
    mock_g_global.reset_mock()
    mock_json_dump.reset_mock()

    # 2. Agents vides
    run_summary_generation_pipeline([{"source_name":"S1", "extracts":[]}], [], [{"name":"F1"}], temp_output_reports_dir)
    mock_g_analysis.assert_not_called()
    mock_g_md.assert_not_called()
    mock_g_global.assert_called_once_with([], temp_output_reports_dir, [])
    args_dumped = mock_json_dump.call_args[0][0]
    assert args_dumped == []

    mock_g_analysis.reset_mock()
    mock_g_md.reset_mock()
    mock_g_global.reset_mock()
    mock_json_dump.reset_mock()

    # 3. Fallacies vides (devrait quand même fonctionner, generate_fallacy_detection gère ça)
    run_summary_generation_pipeline(
        [{"source_name":"S1", "extracts":[{"extract_name":"E1"}]}], 
        [{"name":"A1"}], 
        [], # Fallacies vides
        temp_output_reports_dir
    )
    mock_g_analysis.assert_called_once() # Appelée une fois
    mock_g_md.assert_called_once()
    mock_g_global.assert_called_once()


# Des tests plus détaillés pour chaque fonction de génération (generate_rhetorical_analysis_for_extract, etc.)
# seraient dans des blocs de test séparés si on ne les mockait pas ici.
# Par exemple:
# def test_generate_rhetorical_analysis_for_extract_structure(...):
#     # ...
# def test_generate_markdown_summary_for_analysis_content(...):
#     # ...
# def test_generate_global_summary_report_content(...):
#     # ...