# -*- coding: utf-8 -*-
"""Tests pour les utilitaires de réparation d'extraits."""

import pytest
import asyncio
import logging # Ajout de l'import logging
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock # AsyncMock pour les fonctions async
from typing import Dict # Ajout pour le typage

from argumentation_analysis.utils.dev_tools.repair_utils import run_extract_repair_pipeline, setup_agents, repair_extract_markers
from argumentation_analysis.models.extract_definition import ExtractDefinitions, SourceDefinition, Extract # Pour typer les mocks
import semantic_kernel as sk # Pour setup_agents
from semantic_kernel.agents import ChatCompletionAgent # Pour setup_agents
from argumentation_analysis.utils.extract_repair.marker_repair_logic import REPAIR_AGENT_INSTRUCTIONS, VALIDATION_AGENT_INSTRUCTIONS # Pour setup_agents


# --- Fixtures ---
@pytest.fixture
def mock_project_root(tmp_path: Path) -> Path:
    """Crée un répertoire racine de projet temporaire."""
    return tmp_path

@pytest.fixture
def mock_llm_service():
    """Mock pour LLMService."""
    return MagicMock()

@pytest.fixture
def mock_definition_service():
    """Mock pour DefinitionService."""
    service = MagicMock()
    # Simuler le retour de load_definitions
    sample_source = SourceDefinition(source_name="Test Source Hitler", source_type="text", schema="file", host_parts=[], path="", extracts=[])
    sample_defs = ExtractDefinitions(sources=[sample_source])
    service.load_definitions.return_value = (sample_defs, None) # (definitions, error_message)
    service.save_definitions.return_value = (True, None) # (success, error_message)
    service.export_definitions_to_json.return_value = (True, "Exported successfully")
    return service

@pytest.fixture
def mock_extract_service():
    """Mock pour ExtractService."""
    return MagicMock()

@pytest.fixture
def mock_fetch_service():
    """Mock pour FetchService."""
    return MagicMock()

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
        "cache_service": MagicMock(), # Non utilisé directement dans le pipeline testé
        "crypto_service": MagicMock() # Non utilisé directement dans le pipeline testé
    }

# --- Tests pour run_extract_repair_pipeline ---

@patch("project_core.dev_utils.repair_utils.create_llm_service")
@patch("project_core.dev_utils.repair_utils.initialize_core_services")
@patch("project_core.dev_utils.repair_utils.repair_extract_markers", new_callable=AsyncMock) # Mock fonction async
@patch("project_core.dev_utils.repair_utils.generate_marker_repair_report")
@pytest.mark.asyncio # Nécessaire pour tester les fonctions async
async def test_run_extract_repair_pipeline_successful_run_no_save(
    mock_generate_report: MagicMock,
    mock_repair_markers: AsyncMock, # Doit être AsyncMock
    mock_init_core_services: MagicMock,
    mock_create_llm: MagicMock,
    mock_project_root: Path,
    mock_llm_service: MagicMock,
    mock_core_services: Dict[str, MagicMock],
    mock_definition_service: MagicMock # Pour vérifier les appels
):
    """Teste une exécution réussie du pipeline sans sauvegarde."""
    mock_create_llm.return_value = mock_llm_service
    mock_init_core_services.return_value = mock_core_services
    
    # Simuler le retour de repair_extract_markers
    # updated_definitions, results
    mock_repair_markers.return_value = (ExtractDefinitions(sources=[]), [{"some_result": "data"}])

    output_report_path = str(mock_project_root / "repair_report.html")

    await run_extract_repair_pipeline(
        project_root_dir=mock_project_root,
        output_report_path_str=output_report_path,
        save_changes=False,
        hitler_only=False,
        custom_input_path_str=None,
        output_json_path_str=None
    )

    mock_create_llm.assert_called_once()
    mock_init_core_services.assert_called_once_with(
        project_root_dir=mock_project_root,
        config_file_path=None
    )
    mock_definition_service.load_definitions.assert_called_once()
    mock_repair_markers.assert_called_once()
    # Vérifier les arguments de repair_extract_markers (le premier est extract_definitions)
    assert isinstance(mock_repair_markers.call_args[0][0], ExtractDefinitions)
    assert mock_repair_markers.call_args[0][1] == mock_llm_service # llm_service
    # Les autres services sont passés aussi

    mock_generate_report.assert_called_once()
    assert mock_generate_report.call_args[0][0] == [{"some_result": "data"}] # results
    assert mock_generate_report.call_args[0][1] == output_report_path # output_file_str

    mock_definition_service.save_definitions.assert_not_called()
    mock_definition_service.export_definitions_to_json.assert_not_called()


@patch("project_core.dev_utils.repair_utils.create_llm_service")
@patch("project_core.dev_utils.repair_utils.initialize_core_services")
@patch("project_core.dev_utils.repair_utils.repair_extract_markers", new_callable=AsyncMock)
@patch("argumentation_analysis.utils.extract_repair.marker_repair_logic.generate_report") # Correction de l'emplacement de generate_report
@pytest.mark.asyncio
async def test_run_extract_repair_pipeline_with_save_and_json_export(
    mock_generate_report: MagicMock,
    mock_repair_markers: AsyncMock,
    mock_init_core_services: MagicMock,
    mock_create_llm: MagicMock,
    mock_project_root: Path,
    mock_llm_service: MagicMock,
    mock_core_services: Dict[str, MagicMock],
    mock_definition_service: MagicMock
):
    """Teste le pipeline avec sauvegarde et export JSON."""
    mock_create_llm.return_value = mock_llm_service
    mock_init_core_services.return_value = mock_core_services
    
    updated_defs_mock = ExtractDefinitions(sources=[SourceDefinition(source_name="Updated", source_type="text", schema="file", host_parts=[], path="", extracts=[])])
    mock_repair_markers.return_value = (updated_defs_mock, [])

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


@patch("project_core.dev_utils.repair_utils.create_llm_service")
@patch("project_core.dev_utils.repair_utils.initialize_core_services")
@patch("project_core.dev_utils.repair_utils.repair_extract_markers", new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_run_extract_repair_pipeline_hitler_only_filter(
    mock_repair_markers: AsyncMock,
    mock_init_core_services: MagicMock,
    mock_create_llm: MagicMock,
    mock_project_root: Path,
    mock_llm_service: MagicMock,
    # mock_core_services: Dict[str, MagicMock], # Pas besoin de tout le dict ici
    mock_definition_service: MagicMock # On va modifier son retour
):
    """Teste le filtrage --hitler-only."""
    mock_create_llm.return_value = mock_llm_service
    
    # Configurer mock_definition_service pour retourner plusieurs sources
    sources_data = [
        SourceDefinition(source_name="Discours d'Hitler 1", source_type="text", schema="file", host_parts=[], path="", extracts=[]),
        SourceDefinition(source_name="Autre Discours", source_type="text", schema="file", host_parts=[], path="", extracts=[]),
        SourceDefinition(source_name="Texte Hitler sur la fin", source_type="text", schema="file", host_parts=[], path="", extracts=[])
    ]
    mock_definition_service.load_definitions.return_value = (ExtractDefinitions(sources=sources_data), None)
    
    # Configurer mock_init_core_services pour retourner le mock_definition_service modifié
    mock_core_services_custom = {
        "definition_service": mock_definition_service,
        "extract_service": MagicMock(), "fetch_service": MagicMock(),
        "cache_service": MagicMock(), "crypto_service": MagicMock()
    }
    mock_init_core_services.return_value = mock_core_services_custom
    
    mock_repair_markers.return_value = (ExtractDefinitions(sources=[]), []) # Peu importe le retour ici

    await run_extract_repair_pipeline(
        project_root_dir=mock_project_root,
        output_report_path_str=str(mock_project_root / "report.html"),
        save_changes=False,
        hitler_only=True, # Activer le filtre
        custom_input_path_str=None,
        output_json_path_str=None
    )

    mock_repair_markers.assert_called_once()
    # Vérifier que les définitions passées à repair_extract_markers sont filtrées
    called_with_definitions = mock_repair_markers.call_args[0][0]
    assert isinstance(called_with_definitions, ExtractDefinitions)
    assert len(called_with_definitions.sources) == 2 # Seules les sources "Hitler"
    assert called_with_definitions.sources[0].source_name == "Discours d'Hitler 1"
    assert called_with_definitions.sources[1].source_name == "Texte Hitler sur la fin"


@patch("project_core.dev_utils.repair_utils.create_llm_service", return_value=None) # Simule échec création LLM
@pytest.mark.asyncio
async def test_run_extract_repair_pipeline_llm_service_creation_fails(
    mock_create_llm: MagicMock, # Le patch est déjà appliqué
    mock_project_root: Path,
    caplog
):
    """Teste l'échec de création du service LLM."""
    with caplog.at_level(logging.ERROR):
        await run_extract_repair_pipeline(
            project_root_dir=mock_project_root,
            output_report_path_str="report.html",
            save_changes=False, hitler_only=False, custom_input_path_str=None, output_json_path_str=None
        )
    assert "Impossible de créer le service LLM dans le pipeline." in caplog.text


@patch("project_core.dev_utils.repair_utils.create_llm_service")
@patch("project_core.dev_utils.repair_utils.initialize_core_services")
@pytest.mark.asyncio
async def test_run_extract_repair_pipeline_load_definitions_fails(
    mock_init_core_services: MagicMock,
    mock_create_llm: MagicMock,
    mock_project_root: Path,
    mock_llm_service: MagicMock,
    mock_definition_service: MagicMock, # Pour contrôler son retour
    caplog
):
    """Teste l'échec du chargement des définitions."""
    mock_create_llm.return_value = mock_llm_service
    mock_definition_service.load_definitions.return_value = (None, "Erreur de chargement test") # Simule échec
    
    mock_core_services_custom = { "definition_service": mock_definition_service, 
                                  "extract_service": MagicMock(), "fetch_service": MagicMock(),
                                  "cache_service": MagicMock(), "crypto_service": MagicMock()}
    mock_init_core_services.return_value = mock_core_services_custom
    
    with caplog.at_level(logging.ERROR): # ou WARNING selon le log dans le pipeline
        await run_extract_repair_pipeline(
            project_root_dir=mock_project_root,
            output_report_path_str="report.html",
            save_changes=False, hitler_only=False, custom_input_path_str=None, output_json_path_str=None
        )
    assert "Aucune définition d'extrait chargée ou sources vides. Arrêt du pipeline." in caplog.text
# --- Tests for setup_agents ---

@pytest.fixture
def mock_sk_kernel() -> MagicMock:
    kernel = MagicMock(spec=sk.Kernel)
    kernel.get_prompt_execution_settings_from_service_id.return_value = {}
    return kernel

@pytest.mark.asyncio
async def test_setup_agents_successful(mock_llm_service: MagicMock, mock_sk_kernel: MagicMock):
    """Teste la configuration réussie des agents."""
    mock_llm_service.service_id = "test_service_id" # Nécessaire pour get_prompt_execution_settings

    with patch("project_core.dev_utils.repair_utils.ChatCompletionAgent", spec=ChatCompletionAgent) as MockAgent:
        repair_agent_instance = MagicMock()
        validation_agent_instance = MagicMock()
        MockAgent.side_effect = [repair_agent_instance, validation_agent_instance]

        repair_agent, validation_agent = await setup_agents(mock_llm_service, mock_sk_kernel)

        mock_sk_kernel.add_service.assert_called_once_with(mock_llm_service)
        mock_sk_kernel.get_prompt_execution_settings_from_service_id.assert_called_once_with("test_service_id")
        
        assert MockAgent.call_count == 2
        # Vérifier les appels à ChatCompletionAgent
        calls = MockAgent.call_args_list
        assert calls[0][1]["name"] == "RepairAgent"
        assert calls[0][1]["instructions"] == REPAIR_AGENT_INSTRUCTIONS
        assert calls[1][1]["name"] == "ValidationAgent"
        assert calls[1][1]["instructions"] == VALIDATION_AGENT_INSTRUCTIONS
        
        assert repair_agent == repair_agent_instance
        assert validation_agent == validation_agent_instance

@pytest.mark.asyncio
async def test_setup_agents_creation_fails(mock_llm_service: MagicMock, mock_sk_kernel: MagicMock, caplog):
    """Teste la gestion d'erreur si la création d'un agent échoue."""
    mock_llm_service.service_id = "test_service_id"
    
    with patch("project_core.dev_utils.repair_utils.ChatCompletionAgent", side_effect=Exception("Erreur création agent")):
        with pytest.raises(Exception, match="Erreur création agent"):
            await setup_agents(mock_llm_service, mock_sk_kernel)
        assert "Erreur lors de la création de l'agent de réparation" in caplog.text


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
    mock_llm_service: MagicMock, # Non utilisé directement par la logique actuelle de repair_extract_markers
    mock_fetch_service: MagicMock, # Non utilisé directement par la logique actuelle
    mock_extract_service: MagicMock # Passé à ExtractRepairPlugin, mais le plugin n'est pas testé en profondeur ici
):
    """Teste la logique de base de réparation et la structure des résultats."""
    
    # La logique actuelle de repair_extract_markers modifie extract_definitions en place.
    # On fait une copie pour vérifier les changements si nécessaire, bien que le test actuel se concentre sur les `results`.
    # import copy
    # original_defs = copy.deepcopy(sample_extracts_for_repair)

    updated_defs, results = await repair_extract_markers(
        sample_extracts_for_repair, 
        mock_llm_service, 
        mock_fetch_service, 
        mock_extract_service
    )

    assert updated_defs == sample_extracts_for_repair # Vérifie que l'objet est modifié en place

    assert len(results) == 4 # Un résultat par extrait

    # E1_valid
    res_e1 = next(r for r in results if r["extract_name"] == "E1_valid")
    assert res_e1["status"] == "valid"
    assert res_e1["new_start_marker"] == "Valid start"

    # E2_needs_repair
    res_e2 = next(r for r in results if r["extract_name"] == "E2_needs_repair")
    assert res_e2["status"] == "repaired"
    assert res_e2["old_start_marker"] == "rong start"
    assert res_e2["new_start_marker"] == "Wrong start" # "W" + "rong start"
    assert updated_defs.sources[0].extracts[1].start_marker == "Wrong start" # Vérifie la modification en place

    # E3_no_template
    res_e3 = next(r for r in results if r["extract_name"] == "E3_no_template")
    assert res_e3["status"] == "valid" # Ou un autre statut si on change la logique pour les sans-template
    assert "Aucune correction basée sur template appliquée" in res_e3["message"]
    assert res_e3["new_start_marker"] == "No template here"

    # E4_template_no_fix
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