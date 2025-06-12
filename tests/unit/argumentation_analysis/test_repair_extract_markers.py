
import os
import sys
import json
from pathlib import Path
import pytest
from unittest.mock import MagicMock, patch

# Ajouter le répertoire parent au chemin de recherche des modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importer les modèles et fonctions nécessaires pour les tests
from models.extract_definition import ExtractDefinitions, SourceDefinition, Extract
# Importer depuis le script principal
# Correction du chemin d'importation basé sur l'analyse du code source
from argumentation_analysis.utils.dev_tools.repair_utils import (
    repair_extract_markers,
    setup_agents
)
from argumentation_analysis.utils.extract_repair.marker_repair_logic import (
    ExtractRepairPlugin,
    generate_report
)

@pytest.fixture
def sample_extract_with_template():
    """Fixture pour un extrait avec template défectueux."""
    return Extract(
        extract_name="Test Extract With Template",
        start_marker="EBUT_EXTRAIT",
        end_marker="FIN_EXTRAIT",
        template_start="D{0}"
    )

@pytest.fixture
def sample_source_with_template(sample_extract_with_template):
    """Fixture pour une source avec un extrait utilisant un template."""
    return SourceDefinition(
        source_name="Test Source With Template",
        source_type="url",
        schema="https",
        host_parts=["example", "com"],
        path="/test",
        extracts=[sample_extract_with_template]
    )

@pytest.fixture
def sample_definitions_with_template(sample_source_with_template):
    """Fixture pour des définitions d'extraits avec template."""
    return ExtractDefinitions(sources=[sample_source_with_template])

@pytest.fixture
def sample_extract():
    """Fixture pour un extrait simple."""
    return Extract(
        extract_name="Test Extract",
        start_marker="DEBUT_EXTRAIT",
        end_marker="FIN_EXTRAIT"
    )

@pytest.fixture
def sample_source(sample_extract):
    """Fixture pour une source simple."""
    return SourceDefinition(
        source_name="Test Source",
        source_type="url",
        schema="https",
        host_parts=["example", "com"],
        path="/test",
        extracts=[sample_extract]
    )

@pytest.fixture
def sample_definitions(sample_source):
    """Fixture pour des définitions d'extraits simples."""
    return ExtractDefinitions(sources=[sample_source])


class TestExtractRepairPlugin:
    """Tests pour le plugin de réparation des extraits."""

    @pytest.fixture
    def extract_repair_plugin(self):
        """Fixture pour le plugin de réparation des extraits."""
        extract_service_mock = MagicMock()
        return ExtractRepairPlugin(extract_service_mock)

    def test_find_similar_markers(self, extract_repair_plugin):
        """Test de recherche de marqueurs similaires."""
        extract_repair_plugin.extract_service.find_similar_strings.return_value = [
            {"text": "DEBUT_EXTRAIT", "position": 15, "context": "Contexte avant DEBUT_EXTRAIT contexte après"}
        ]
        
        results = extract_repair_plugin.find_similar_markers(
            "Texte source complet", "DEBUT_EXTRAIT", max_results=2
        )
        
        assert len(results) == 1
        assert results[0]["marker"] == "DEBUT_EXTRAIT"
        assert results[0]["position"] == 15
        assert "Contexte avant" in results[0]["context"]

    def test_find_similar_markers_empty_inputs(self, extract_repair_plugin):
        """Test de recherche de marqueurs similaires avec des entrées vides."""
        assert len(extract_repair_plugin.find_similar_markers("", "DEBUT_EXTRAIT")) == 0
        assert len(extract_repair_plugin.find_similar_markers("Texte source", "")) == 0

    def test_update_extract_markers(self, extract_repair_plugin, sample_definitions):
        """Test de mise à jour des marqueurs d'un extrait."""
        source_idx, extract_idx = 0, 0
        new_start, new_end = "NOUVEAU_DEBUT", "NOUVELLE_FIN"
        
        result = extract_repair_plugin.update_extract_markers(
            sample_definitions, source_idx, extract_idx, new_start, new_end
        )
        
        assert result is True
        updated_extract = sample_definitions.sources[0].extracts[0]
        assert updated_extract.start_marker == new_start
        assert updated_extract.end_marker == new_end
        
        repair_results = extract_repair_plugin.get_repair_results()
        assert len(repair_results) == 1
        assert repair_results[0]["new_start_marker"] == new_start

    def test_update_extract_markers_with_template(self, extract_repair_plugin, sample_definitions):
        """Test de mise à jour des marqueurs d'un extrait avec template."""
        source_idx, extract_idx = 0, 0
        new_start, new_end, template_start = "NOUVEAU_DEBUT", "NOUVELLE_FIN", "T{0}"
        
        result = extract_repair_plugin.update_extract_markers(
            sample_definitions, source_idx, extract_idx, new_start, new_end, template_start
        )
        
        assert result is True
        updated_extract = sample_definitions.sources[0].extracts[0]
        assert updated_extract.template_start == template_start

    def test_update_extract_markers_invalid_indices(self, extract_repair_plugin, sample_definitions):
        """Test de mise à jour avec des indices invalides."""
        assert not extract_repair_plugin.update_extract_markers(sample_definitions, 99, 0, "a", "b")
        assert not extract_repair_plugin.update_extract_markers(sample_definitions, 0, 99, "a", "b")

class TestRepairScriptFunctions:
    """Tests pour les fonctions du script de réparation."""

    @patch('argumentation_analysis.agents.core.extract.repair_extract_markers.ExtractRepairPlugin')
    async def test_repair_extract_markers_with_template(self, mock_plugin_class, sample_definitions_with_template):
        """Test de réparation des extraits avec template."""
        mock_plugin = mock_plugin_class.return_value
        
        llm_service_mock, fetch_service_mock, extract_service_mock = MagicMock(), MagicMock(), MagicMock()
        
        _, results = await repair_extract_markers(
            sample_definitions_with_template, llm_service_mock, fetch_service_mock, extract_service_mock
        )
        
        mock_plugin.update_extract_markers.assert_called_once()
        args, _ = mock_plugin.update_extract_markers.call_args
        assert args[3] == "DEBUT_EXTRAIT" # new_start_marker
        
        assert len(results) > 0
        assert results[0]["status"] == "repaired"

    @patch('argumentation_analysis.agents.core.extract.repair_extract_markers.ExtractRepairPlugin')
    async def test_repair_extract_markers_without_template(self, mock_plugin_class, sample_definitions):
        """Test de réparation des extraits sans template (ne devrait rien faire)."""
        mock_plugin = mock_plugin_class.return_value
        llm_service_mock, fetch_service_mock, extract_service_mock = MagicMock(), MagicMock(), MagicMock()
        
        _, results = await repair_extract_markers(
            sample_definitions, llm_service_mock, fetch_service_mock, extract_service_mock
        )
        
        mock_plugin.update_extract_markers.assert_not_called()
        assert len(results) > 0
        assert results[0]["status"] == "valid"

    @patch('builtins.open')
    @patch('json.dump')
    def test_generate_report(self, mock_json_dump, mock_open):
        """Test de génération de rapport (vérifie l'écriture)."""
        results = [{"status": "repaired"}]
        generate_report(results, "test_report.html")
        mock_open.assert_called_with("test_report.html", "w", encoding="utf-8")
        # Le contenu HTML est complexe, on se contente de vérifier que l'écriture a lieu.
        assert mock_open.return_value.__enter__.return_value.write.call_count > 0


class TestSetupAgents:
    """Tests pour la configuration des agents."""

    @patch('semantic_kernel.Kernel')
    @patch('argumentation_analysis.agents.core.extract.repair_extract_markers.ExtractRepairAgent')
    @patch('argumentation_analysis.agents.core.extract.repair_extract_markers.ExtractValidationAgent')
    async def test_setup_agents(self, mock_validation_agent_class, mock_repair_agent_class, mock_kernel_class):
        """Test de configuration des agents."""
        llm_service_mock = MagicMock()
        llm_service_mock.service_id = "test-service-id"
        
        kernel_mock = mock_kernel_class.return_value
        
        kernel, repair_agent, validation_agent = await setup_agents(llm_service_mock)
        
        mock_kernel_class.assert_called_once()
        kernel_mock.add_service.assert_called_once_with(llm_service_mock)
        
        assert mock_repair_agent_class.call_count == 1
        assert mock_validation_agent_class.call_count == 1
        
        assert repair_agent is not None
        assert validation_agent is not None