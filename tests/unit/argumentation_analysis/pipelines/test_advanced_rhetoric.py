import pytest

# Authentic gpt-5-mini imports (replacing mocks)
# import openai
# from semantic_kernel.contents import ChatHistory
# from semantic_kernel.core_plugins import ConversationSummaryPlugin
# from config.unified_config import UnifiedConfig

import logging

# -*- coding: utf-8 -*-
"""Tests pour le pipeline d'analyse rhétorique avancée."""

import pytest
import json
from pathlib import Path
from unittest.mock import MagicMock, call

from typing import List, Dict, Any

from argumentation_analysis.pipelines.advanced_rhetoric import (
    run_advanced_rhetoric_pipeline,
)
from argumentation_analysis.core.interfaces.fallacy_detector import (
    AbstractFallacyDetector,
)


from unittest.mock import patch

MODULE_PATH = "argumentation_analysis.pipelines.advanced_rhetoric"


@pytest.fixture
def mock_tqdm(mocker):
    """Mocks the tqdm progress bar."""
    return mocker.patch(f"{MODULE_PATH}.tqdm")


@pytest.fixture
def mock_json_dump(mocker):
    """Mocks json.dump."""
    return mocker.patch(f"{MODULE_PATH}.json.dump")


@pytest.fixture
def mock_open(mocker):
    """Mocks the built-in open function."""
    return mocker.patch(f"{MODULE_PATH}.open")


@pytest.fixture
def mock_analysis_plugin(mocker) -> MagicMock:
    """Mocks the AnalysisToolsPlugin class and its instance created within the pipeline."""
    mock_plugin_instance = MagicMock()
    # On mock la classe pour que son instanciation retourne notre mock d'instance contrôlable
    mock_plugin_class = mocker.patch(f"{MODULE_PATH}.AnalysisToolsPlugin")
    mock_plugin_class.return_value = mock_plugin_instance
    return mock_plugin_instance


@pytest.fixture
def mock_analyze_single_extract(mocker):
    """Mocks the analyze_extract_advanced function."""
    return mocker.patch(f"{MODULE_PATH}.analyze_extract_advanced")


@pytest.fixture
def sample_extract_definitions() -> List[Dict[str, Any]]:
    """Fournit des définitions d'extraits pour les tests."""
    return [
        {
            "source_name": "Source1",
            "extracts": [
                {"extract_name": "Ext1.1", "extract_text": "Texte de l'extrait 1.1"},
                {"extract_name": "Ext1.2", "extract_text": "Texte de l'extrait 1.2"},
            ],
        },
        {
            "source_name": "Source2",
            "extracts": [
                {"extract_name": "Ext2.1", "extract_text": "Texte de l'extrait 2.1"}
            ],
        },
    ]


@pytest.fixture
def sample_base_results() -> List[Dict[str, Any]]:
    """Fournit des résultats d'analyse de base pour les tests."""
    return [
        {
            "source_name": "Source1",
            "extract_name": "Ext1.1",
            "analyses": {"coherence": 0.8},
        },
        {
            "source_name": "Source1",
            "extract_name": "Ext1.2",
            "analyses": {"coherence": 0.7},
        },
        {
            "source_name": "Source2",
            "extract_name": "Ext2.1",
            "analyses": {"coherence": 0.9},
        },
    ]


@pytest.fixture
def temp_output_file(tmp_path: Path) -> Path:
    """Crée un chemin de fichier de sortie temporaire."""
    return tmp_path / "advanced_results.json"


@pytest.fixture
def mock_fallacy_detector() -> MagicMock:
    """Fournit un mock du AbstractFallacyDetector."""
    return MagicMock(spec=AbstractFallacyDetector)


def test_run_advanced_rhetoric_pipeline_success(
    mock_tqdm: MagicMock,
    mock_json_dump: MagicMock,
    mock_open: MagicMock,
    mock_analysis_plugin: MagicMock,
    mock_analyze_single_extract: MagicMock,
    sample_extract_definitions: List[Dict[str, Any]],
    sample_base_results: List[Dict[str, Any]],
    temp_output_file: Path,
    mock_fallacy_detector: MagicMock,
):
    """Teste une exécution réussie du pipeline."""
    mock_progress_bar_instance = MagicMock()
    mock_tqdm.return_value = mock_progress_bar_instance

    def analyze_single_side_effect(extract_def, source_name, base_res, plugin):
        return {
            "analyzed": True,
            "extract_name": extract_def["extract_name"],
            "source_name": source_name,
        }

    mock_analyze_single_extract.side_effect = analyze_single_side_effect

    run_advanced_rhetoric_pipeline(
        sample_extract_definitions,
        sample_base_results,
        temp_output_file,
        mock_fallacy_detector,
    )

    assert mock_analyze_single_extract.call_count == 3

    # Vérifier que analyze_extract_advanced a été appelé avec le plugin mocké
    calls = [
        call(
            sample_extract_definitions[0]["extracts"][0],
            "Source1",
            sample_base_results[0],
            mock_analysis_plugin,
        ),
        call(
            sample_extract_definitions[0]["extracts"][1],
            "Source1",
            sample_base_results[1],
            mock_analysis_plugin,
        ),
        call(
            sample_extract_definitions[1]["extracts"][0],
            "Source2",
            sample_base_results[2],
            mock_analysis_plugin,
        ),
    ]
    mock_analyze_single_extract.assert_has_calls(calls, any_order=True)

    mock_tqdm.assert_called_once_with(
        total=3, desc="Pipeline d'analyse avancée", unit="extrait"
    )
    assert mock_progress_bar_instance.update.call_count == 3
    mock_progress_bar_instance.close.assert_called_once()

    mock_open.assert_called_once_with(temp_output_file, "w", encoding="utf-8")
    assert mock_json_dump.call_args[0][0] == [
        {"analyzed": True, "extract_name": "Ext1.1", "source_name": "Source1"},
        {"analyzed": True, "extract_name": "Ext1.2", "source_name": "Source1"},
        {"analyzed": True, "extract_name": "Ext2.1", "source_name": "Source2"},
    ]


def test_run_advanced_rhetoric_pipeline_no_base_results(
    mock_analyze_single_extract: MagicMock,
    sample_extract_definitions: List[Dict[str, Any]],
    temp_output_file: Path,
    mock_analysis_plugin: MagicMock,
    mock_tqdm: MagicMock,
    mock_open: MagicMock,
    mock_json_dump: MagicMock,
    mock_fallacy_detector: MagicMock,
):
    """Teste le pipeline sans résultats de base."""
    mock_analyze_single_extract.return_value = {"analyzed": True}

    run_advanced_rhetoric_pipeline(
        sample_extract_definitions, [], temp_output_file, mock_fallacy_detector
    )

    # Vérifier que analyze_extract_advanced est appelé avec base_result=None et le plugin
    for extract_def_list in sample_extract_definitions:
        for extract_def in extract_def_list["extracts"]:
            # Trouver l'appel correspondant
            found_call = next(
                c
                for c in mock_analyze_single_extract.call_args_list
                if c.args[0] == extract_def
            )
            assert found_call.args[2] is None  # base_result est None
            assert (
                len(found_call.args) > 3 and found_call.args[3] == mock_analysis_plugin
            )


def test_run_advanced_rhetoric_pipeline_extract_analysis_error(
    mock_tqdm: MagicMock,
    mock_json_dump: MagicMock,
    mock_open: MagicMock,
    mock_analysis_plugin: MagicMock,  # Utilise le mock du plugin
    mock_analyze_single_extract: MagicMock,
    sample_extract_definitions: List[Dict[str, Any]],
    temp_output_file: Path,
    caplog,
    mock_fallacy_detector: MagicMock,
):
    """Teste la gestion d'erreur si l'analyse d'un extrait échoue."""
    # mock_create_mocks.return_value = {} # Remplacé par mock_advanced_tools

    # Configurer le mock pour lever une exception
    mock_analyze_single_extract.side_effect = Exception("Erreur d'analyse d'extrait!")

    with caplog.at_level(logging.ERROR):
        run_advanced_rhetoric_pipeline(
            sample_extract_definitions, [], temp_output_file, mock_fallacy_detector
        )

    assert mock_analyze_single_extract.call_count == 3  # Tentative pour chaque extrait
    assert (
        "Erreur dans le pipeline pour l'extrait 'Ext1.1': Erreur d'analyse d'extrait!"
        in caplog.text
    )

    # Vérifier que les résultats contiennent une entrée d'erreur pour chaque extrait
    results_dumped = mock_json_dump.call_args[0][0]
    assert len(results_dumped) == 3
    for res in results_dumped:
        assert "error" in res
        assert res["error"] == "Erreur de pipeline: Erreur d'analyse d'extrait!"


def test_run_advanced_rhetoric_pipeline_save_error(
    mock_tqdm: MagicMock,
    mock_json_dump: MagicMock,
    mock_open: MagicMock,
    mock_analysis_plugin: MagicMock,  # Utilise le mock du plugin
    sample_extract_definitions: List[Dict[str, Any]],
    temp_output_file: Path,
    caplog,
    mock_fallacy_detector: MagicMock,
):
    """Teste la gestion d'erreur si la sauvegarde des résultats échoue."""
    # Configurer le mock 'open' pour qu'il lève une IOError
    mock_open.side_effect = IOError("Erreur de sauvegarde!")

    # On a besoin de mocker analyze_extract_advanced pour qu'il ne lève pas d'erreur pendant la boucle
    with patch(
        "argumentation_analysis.pipelines.advanced_rhetoric.analyze_extract_advanced",
        return_value={"ok": True},
    ):
        with caplog.at_level(logging.ERROR):
            run_advanced_rhetoric_pipeline(
                sample_extract_definitions, [], temp_output_file, mock_fallacy_detector
            )

    # Vérifications
    mock_open.assert_called_once_with(temp_output_file, "w", encoding="utf-8")
    mock_json_dump.assert_not_called()  # Correct, car open échoue avant
    assert (
        "❌ Erreur lors de la sauvegarde des résultats du pipeline: Erreur de sauvegarde!"
        in caplog.text
    )


def test_run_advanced_rhetoric_pipeline_empty_extract_definitions(
    temp_output_file: Path, mock_fallacy_detector: MagicMock
):
    """Teste le pipeline avec une liste vide de définitions d'extraits."""
    # Utilise les vrais mocks pour les outils car on ne mocke pas l'analyse ici
    run_advanced_rhetoric_pipeline([], [], temp_output_file, mock_fallacy_detector)

    # Vérifier que le fichier de sortie est créé mais vide (ou contient une liste vide)
    assert temp_output_file.exists()
    with open(temp_output_file, "r") as f:
        content = json.load(f)
    assert content == []


# Test pour use_real_tools (nécessiterait de mocker les imports des outils réels)
# Ce test est plus complexe car il dépend de la disponibilité des outils réels.
# Pour l'instant, on se concentre sur le flux avec les mocks.
