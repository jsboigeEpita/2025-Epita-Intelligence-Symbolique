# -*- coding: utf-8 -*-
"""Tests pour les utilitaires de réparation d'extraits."""

import pytest
import asyncio
import logging # Ajout de l'import logging
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

from typing import Dict # Ajout pour le typage

from argumentation_analysis.utils.dev_tools.repair_utils import run_extract_repair_pipeline, setup_agents, repair_extract_markers
from argumentation_analysis.models.extract_definition import ExtractDefinitions, SourceDefinition, Extract # Pour typer les mocks
import semantic_kernel as sk # Pour setup_agents
# from semantic_kernel_compatibility import ChatCompletionAgent # Pour setup_agents (Commenté: non utilisé directement)
from argumentation_analysis.utils.extract_repair.marker_repair_logic import REPAIR_AGENT_INSTRUCTIONS, VALIDATION_AGENT_INSTRUCTIONS # Pour setup_agents


# --- Fixtures ---
@pytest.fixture
def mock_project_root(tmp_path: Path) -> Path:
    """Crée un répertoire racine de projet temporaire."""
    return tmp_path

@pytest.fixture
def mock_llm_service():
    """Mock pour LLMService."""
    return AsyncMock()

@pytest.fixture
def mock_definition_service():
    """Mock pour DefinitionService."""
    service = AsyncMock()
    # Simuler le retour de load_definitions
    sample_source = SourceDefinition(source_name="Test Source Hitler", source_type="text", schema="file", host_parts=[], path="", extracts=[])
    sample_defs = ExtractDefinitions(sources=[sample_source])
    service.load_definitions.return_value = (sample_defs, None)
    service.save_definitions.return_value = (True, None)
    service.export_definitions_to_json.return_value = (True, "Exported successfully")
    return service

@pytest.fixture
def mock_extract_service():
    """Mock pour ExtractService."""
    return AsyncMock()

@pytest.fixture
def mock_fetch_service():
    """Mock pour FetchService."""
    return AsyncMock()

@pytest.fixture
def mock_core_services(
    mock_definition_service: MagicMock,
    mock_extract_service: MagicMock,
    mock_fetch_service: MagicMock
) -> Dict[str, MagicMock]:
    """Mock pour le dictionnaire core_services."""
    return {
        "definition_service": mock_definition_service,
        "extract_service": mock_extract_service,
        "fetch_service": mock_fetch_service,
        "cache_service": AsyncMock(), # Non utilisé directement dans le pipeline testé
        "crypto_service": AsyncMock() # Non utilisé directement dans le pipeline testé
    }

# --- Tests pour run_extract_repair_pipeline ---

@pytest.mark.asyncio
@patch('argumentation_analysis.utils.dev_tools.repair_utils.generate_marker_repair_report')
@patch('argumentation_analysis.utils.dev_tools.repair_utils.repair_extract_markers', new_callable=AsyncMock)
@patch('argumentation_analysis.utils.dev_tools.repair_utils.FetchService')
@patch('argumentation_analysis.utils.dev_tools.repair_utils.ExtractService')
@patch('argumentation_analysis.utils.dev_tools.repair_utils.CacheService')
@patch('argumentation_analysis.utils.dev_tools.repair_utils.CryptoService')
@patch('argumentation_analysis.utils.dev_tools.repair_utils.DefinitionService')
@patch('argumentation_analysis.utils.dev_tools.repair_utils.create_llm_service')
async def test_run_extract_repair_pipeline_successful_run_no_save(
    mock_create_llm_service: MagicMock,
    MockDefinitionService: MagicMock,
    MockCryptoService: MagicMock,
    MockCacheService: MagicMock,
    MockExtractService: MagicMock,
    MockFetchService: MagicMock,
    mock_repair_extract_markers: AsyncMock,
    mock_generate_marker_repair_report: MagicMock,
    mock_project_root: Path,
    mock_llm_service: MagicMock,
    mock_definition_service: MagicMock
):
    """Teste une exécution réussie du pipeline sans sauvegarde."""
    mock_create_llm_service.return_value = mock_llm_service

    # Configurer les instances mockées retournées par les classes patchées
    mock_crypto_instance = AsyncMock()
    MockCryptoService.return_value = mock_crypto_instance

    mock_cache_instance = AsyncMock()
    MockCacheService.return_value = mock_cache_instance

    mock_extract_instance = AsyncMock()
    MockExtractService.return_value = mock_extract_instance

    mock_fetch_instance = AsyncMock()
    MockFetchService.return_value = mock_fetch_instance

    # Utiliser la configuration de la fixture mock_definition_service pour l'instance mockée
    MockDefinitionService.return_value = mock_definition_service
    sample_source = SourceDefinition(source_name="Test Source", source_type="text", schema="file", host_parts=[], path="", extracts=[])
    sample_defs = ExtractDefinitions(sources=[sample_source])
    mock_definition_service.load_definitions.return_value = (sample_defs, None)


    mock_repair_extract_markers.return_value = (sample_defs, [{"some_result": "data"}])

    output_report_path = str(mock_project_root / "repair_report.html")

    await run_extract_repair_pipeline(
        project_root_dir=mock_project_root,
        output_report_path_str=output_report_path,
        save_changes=False,
        hitler_only=False,
        custom_input_path_str=None,
        output_json_path_str=None
    )

    mock_create_llm_service.assert_called_once()
    
    MockDefinitionService.assert_called_once()
    MockCryptoService.assert_called_once()
    MockCacheService.assert_called_once()
    MockExtractService.assert_called_once()
    MockFetchService.assert_called_once()

    mock_definition_service.load_definitions.assert_called_once()
    mock_repair_extract_markers.assert_called_once()
    assert isinstance(mock_repair_extract_markers.call_args[0][0], ExtractDefinitions)
    assert mock_repair_extract_markers.call_args[0][1] == mock_llm_service
    assert mock_repair_extract_markers.call_args[0][2] == mock_fetch_instance
    assert mock_repair_extract_markers.call_args[0][3] == mock_extract_instance

    mock_generate_marker_repair_report.assert_called_once()
    assert mock_generate_marker_repair_report.call_args[0][0] == [{"some_result": "data"}]
    assert mock_generate_marker_repair_report.call_args[0][1] == output_report_path

    mock_definition_service.save_definitions.assert_not_called()
    mock_definition_service.export_definitions_to_json.assert_not_called()

@pytest.mark.asyncio
@patch('argumentation_analysis.utils.dev_tools.repair_utils.generate_marker_repair_report')
@patch('argumentation_analysis.utils.dev_tools.repair_utils.repair_extract_markers', new_callable=AsyncMock)
@patch('argumentation_analysis.utils.dev_tools.repair_utils.FetchService')
@patch('argumentation_analysis.utils.dev_tools.repair_utils.ExtractService')
@patch('argumentation_analysis.utils.dev_tools.repair_utils.CacheService')
@patch('argumentation_analysis.utils.dev_tools.repair_utils.CryptoService')
@patch('argumentation_analysis.utils.dev_tools.repair_utils.DefinitionService')
@patch('argumentation_analysis.utils.dev_tools.repair_utils.create_llm_service')
async def test_run_extract_repair_pipeline_with_save_and_json_export(
    mock_create_llm_service: MagicMock,
    MockDefinitionService: MagicMock,
    MockCryptoService: MagicMock,
    MockCacheService: MagicMock,
    MockExtractService: MagicMock,
    MockFetchService: MagicMock,
    mock_repair_extract_markers: AsyncMock,
    mock_generate_marker_repair_report: MagicMock,
    mock_project_root: Path,
    mock_llm_service: MagicMock,
    mock_definition_service: MagicMock
):
    """Teste le pipeline avec sauvegarde et export JSON."""
    mock_create_llm_service.return_value = mock_llm_service

    MockCryptoService.return_value = AsyncMock()
    MockCacheService.return_value = AsyncMock()
    MockExtractService.return_value = AsyncMock()
    MockFetchService.return_value = AsyncMock()
    MockDefinitionService.return_value = mock_definition_service

    updated_defs_mock = ExtractDefinitions(sources=[SourceDefinition(source_name="Updated", source_type="text", schema="file", host_parts=[], path="", extracts=[])])
    mock_definition_service.load_definitions.return_value = (updated_defs_mock, None)
    mock_repair_extract_markers.return_value = (updated_defs_mock, [{"status": "repaired"}])

    output_report_path = str(mock_project_root / "report.html")
    output_json_path = str(mock_project_root / "updated.json")

    await run_extract_repair_pipeline(
        project_root_dir=mock_project_root,
        output_report_path_str=output_report_path,
        save_changes=True,
        hitler_only=False,
        custom_input_path_str=None,
        output_json_path_str=output_json_path
    )

    mock_definition_service.save_definitions.assert_called_once_with(updated_defs_mock)
    mock_definition_service.export_definitions_to_json.assert_called_once_with(
        updated_defs_mock, Path(output_json_path)
    )
    mock_generate_marker_repair_report.assert_called_once()

@pytest.mark.asyncio
@patch('argumentation_analysis.utils.dev_tools.repair_utils.repair_extract_markers', new_callable=AsyncMock)
@patch('argumentation_analysis.utils.dev_tools.repair_utils.FetchService')
@patch('argumentation_analysis.utils.dev_tools.repair_utils.ExtractService')
@patch('argumentation_analysis.utils.dev_tools.repair_utils.CacheService')
@patch('argumentation_analysis.utils.dev_tools.repair_utils.CryptoService')
@patch('argumentation_analysis.utils.dev_tools.repair_utils.DefinitionService')
@patch('argumentation_analysis.utils.dev_tools.repair_utils.create_llm_service')
async def test_run_extract_repair_pipeline_hitler_only_filter(
    mock_create_llm_service: MagicMock,
    MockDefinitionService: MagicMock,
    MockCryptoService: MagicMock,
    MockCacheService: MagicMock,
    MockExtractService: MagicMock,
    MockFetchService: MagicMock,
    mock_repair_extract_markers: AsyncMock,
    mock_project_root: Path,
    mock_llm_service: MagicMock,
    mock_definition_service: MagicMock
):
    """Teste le filtrage --hitler-only."""
    mock_create_llm_service.return_value = mock_llm_service
    
    MockCryptoService.return_value = AsyncMock()
    MockCacheService.return_value = AsyncMock()
    MockExtractService.return_value = AsyncMock()
    MockFetchService.return_value = AsyncMock()
    MockDefinitionService.return_value = mock_definition_service

    sources_data = [
        SourceDefinition(source_name="Discours d'Hitler 1", source_type="text", schema="file", host_parts=[], path="", extracts=[]),
        SourceDefinition(source_name="Autre Discours", source_type="text", schema="file", host_parts=[], path="", extracts=[]),
        SourceDefinition(source_name="Texte Hitler sur la fin", source_type="text", schema="file", host_parts=[], path="", extracts=[])
    ]
    mock_definition_service.load_definitions.return_value = (ExtractDefinitions(sources=sources_data), None)
    
    mock_repair_extract_markers.return_value = (ExtractDefinitions(sources=[]), [])

    await run_extract_repair_pipeline(
        project_root_dir=mock_project_root,
        output_report_path_str=str(mock_project_root / "report.html"),
        save_changes=False,
        hitler_only=True,
        custom_input_path_str=None,
        output_json_path_str=None
    )

    mock_repair_extract_markers.assert_called_once()
    called_with_definitions = mock_repair_extract_markers.call_args[0][0]
    assert isinstance(called_with_definitions, ExtractDefinitions)
    assert len(called_with_definitions.sources) == 2
    assert called_with_definitions.sources[0].source_name == "Discours d'Hitler 1"
    assert called_with_definitions.sources[1].source_name == "Texte Hitler sur la fin"

@pytest.mark.asyncio
@patch('argumentation_analysis.utils.dev_tools.repair_utils.create_llm_service')
async def test_run_extract_repair_pipeline_llm_service_creation_fails(
    mock_create_llm_service: MagicMock,
    mock_project_root: Path,
    caplog
):
    """Teste l'échec de création du service LLM."""
    mock_create_llm_service.return_value = None 
    with caplog.at_level(logging.ERROR):
        await run_extract_repair_pipeline(
            project_root_dir=mock_project_root,
            output_report_path_str="report.html",
            save_changes=False, hitler_only=False, custom_input_path_str=None, output_json_path_str=None
        )
    assert "Impossible de créer le service LLM dans le pipeline." in caplog.text

@pytest.mark.asyncio
@patch('argumentation_analysis.utils.dev_tools.repair_utils.FetchService')
@patch('argumentation_analysis.utils.dev_tools.repair_utils.ExtractService')
@patch('argumentation_analysis.utils.dev_tools.repair_utils.CacheService')
@patch('argumentation_analysis.utils.dev_tools.repair_utils.CryptoService')
@patch('argumentation_analysis.utils.dev_tools.repair_utils.DefinitionService')
@patch('argumentation_analysis.utils.dev_tools.repair_utils.create_llm_service')
async def test_run_extract_repair_pipeline_load_definitions_fails(
    mock_create_llm_service: MagicMock,
    MockDefinitionService: MagicMock,
    MockCryptoService: MagicMock,
    MockCacheService: MagicMock,
    MockExtractService: MagicMock,
    MockFetchService: MagicMock,
    mock_project_root: Path,
    mock_llm_service: MagicMock,
    caplog
):
    """Teste l'échec du chargement des définitions."""
    mock_create_llm_service.return_value = mock_llm_service

    mock_def_instance = AsyncMock()
    mock_def_instance.load_definitions.return_value = (None, "Erreur de chargement test")
    MockDefinitionService.return_value = mock_def_instance
    
    MockCryptoService.return_value = AsyncMock()
    MockCacheService.return_value = AsyncMock()
    MockExtractService.return_value = AsyncMock()
    MockFetchService.return_value = AsyncMock()
    
    with caplog.at_level(logging.ERROR):
        await run_extract_repair_pipeline(
            project_root_dir=mock_project_root,
            output_report_path_str="report.html",
            save_changes=False, hitler_only=False, custom_input_path_str=None, output_json_path_str=None
        )
    assert "Aucune définition d'extrait chargée ou sources vides. Arrêt du pipeline." in caplog.text
    mock_def_instance.load_definitions.assert_called_once()

# --- Tests for setup_agents ---

@pytest.fixture
def mock_sk_kernel() -> MagicMock:
    kernel = MagicMock(spec=sk.Kernel)
    kernel.get_prompt_execution_settings_from_service_id.return_value = {}
    return kernel

@pytest.mark.asyncio
async def test_setup_agents_successful(mock_llm_service: MagicMock, mock_sk_kernel: MagicMock):
    """Teste la configuration réussie des agents."""
    mock_llm_service.service_id = "test_service_id"

    repair_agent, validation_agent = await setup_agents(mock_llm_service, mock_sk_kernel)
    
    assert repair_agent is None
    assert validation_agent is None

# --- Tests for repair_extract_markers ---

@pytest.fixture
def sample_extracts_for_repair() -> ExtractDefinitions:
    """Fournit des définitions d'extraits pour tester la réparation."""
    return ExtractDefinitions(sources=[
        SourceDefinition(source_name="SourceA", source_type="text", schema="file", host_parts=[], path="", extracts=[
            Extract(extract_name="E1_valid", start_marker="Valid start", end_marker="Valid end", template_start="V{0}alid start"),
            Extract(extract_name="E2_needs_repair", start_marker="rong start", end_marker="End E2", template_start="W{0}rong start"),
            Extract(extract_name="E3_no_template", start_marker="No template here", end_marker="End E3", template_start=None),
            Extract(extract_name="E4_template_no_fix", start_marker="CGood start", end_marker="End E4", template_start="C{0}Good start"),
        ])
    ])

@pytest.mark.asyncio
async def test_repair_extract_markers_repairs_and_reports(
    sample_extracts_for_repair: ExtractDefinitions,
    mock_llm_service: MagicMock,
    mock_fetch_service: MagicMock,
    mock_extract_service: MagicMock
):
    """Teste la logique de base de réparation et la structure des résultats."""
    
    updated_defs, results = await repair_extract_markers(
        sample_extracts_for_repair, 
        mock_llm_service, 
        mock_fetch_service, 
        mock_extract_service
    )

    assert updated_defs == sample_extracts_for_repair

    assert len(results) == 4

    res_e1 = next(r for r in results if r["extract_name"] == "E1_valid")
    assert res_e1["status"] == "valid"
    assert res_e1["new_start_marker"] == "Valid start"

    res_e2 = next(r for r in results if r["extract_name"] == "E2_needs_repair")
    assert res_e2["status"] == "repaired"
    assert res_e2["old_start_marker"] == "rong start"
    assert res_e2["new_start_marker"] == "Wrong start"
    assert updated_defs.sources[0].extracts[1].start_marker == "Wrong start"

    res_e3 = next(r for r in results if r["extract_name"] == "E3_no_template")
    assert res_e3["status"] == "valid"
    assert "Aucune correction basée sur template appliquée" in res_e3["message"]
    assert res_e3["new_start_marker"] == "No template here"

    res_e4 = next(r for r in results if r["extract_name"] == "E4_template_no_fix")
    assert res_e4["status"] == "valid"
    assert res_e4["new_start_marker"] == "CGood start"


@pytest.mark.asyncio
async def test_repair_extract_markers_empty_definitions(
    mock_llm_service: MagicMock,
    mock_fetch_service: MagicMock,
    mock_extract_service: MagicMock
):
    """Teste avec des définitions d'extraits vides."""
    empty_defs = ExtractDefinitions(sources=[])
    updated_defs, results = await repair_extract_markers(
        empty_defs, mock_llm_service, mock_fetch_service, mock_extract_service
    )
    assert updated_defs == empty_defs
    assert results == []

    source_with_no_extracts = ExtractDefinitions(sources=[SourceDefinition(source_name="S_empty", source_type="text", schema="file", host_parts=[], path="", extracts=[])])
    updated_defs_no_ext, results_no_ext = await repair_extract_markers(
        source_with_no_extracts, mock_llm_service, mock_fetch_service, mock_extract_service
    )
    assert updated_defs_no_ext == source_with_no_extracts
    assert results_no_ext == []
