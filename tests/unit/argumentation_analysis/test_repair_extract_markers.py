
import os
import sys
import json
from pathlib import Path
import pytest
from unittest.mock import MagicMock, patch

# Ajouter le répertoire parent au chemin de recherche des modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importer les modèles et fonctions nécessaires pour les tests
from argumentation_analysis.models.extract_definition import ExtractDefinitions, SourceDefinition, Extract
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
        start_marker="EBUT_EXTRAIT", # Simule un début de mot manquant
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
        # Correction: la méthode s'appelle find_similar_text, pas find_similar_strings
        # De plus, la méthode find_similar_text renvoie un tuple de (contexte, position, texte_trouvé)
        extract_repair_plugin.extract_service.find_similar_text.return_value = [
            ("Contexte avant DEBUT_EXTRAIT contexte après", 15, "DEBUT_EXTRAIT")
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

    @pytest.mark.asyncio
    async def test_repair_extract_markers_with_template(self, sample_definitions_with_template):
        """Test de réparation des extraits avec template."""
        llm_service_mock, fetch_service_mock, extract_service_mock = MagicMock(), MagicMock(), MagicMock()
        
        updated_defs, results = await repair_extract_markers(
            sample_definitions_with_template, llm_service_mock, fetch_service_mock, extract_service_mock
        )
        
        assert len(results) == 1
        result = results[0]
        assert result["status"] == "repaired"
        assert result["old_start_marker"] == "EBUT_EXTRAIT"
        assert result["new_start_marker"] == "DEBUT_EXTRAIT"
        
        # Vérifier aussi la modification directe de l'objet
        assert updated_defs.sources[0].extracts[0].start_marker == "DEBUT_EXTRAIT"

    @pytest.mark.asyncio
    async def test_repair_extract_markers_without_template(self, sample_definitions):
        """Test de réparation des extraits sans template (ne devrait rien faire)."""
        llm_service_mock, fetch_service_mock, extract_service_mock = MagicMock(), MagicMock(), MagicMock()
        
        updated_defs, results = await repair_extract_markers(
            sample_definitions, llm_service_mock, fetch_service_mock, extract_service_mock
        )
        
        assert len(results) == 1
        assert results[0]["status"] == "valid"
        assert updated_defs.sources[0].extracts[0].start_marker == "DEBUT_EXTRAIT"

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
    @patch('argumentation_analysis.utils.dev_tools.repair_utils.logger')
    @pytest.mark.asyncio
    async def test_setup_agents(self, mock_logger, mock_kernel_class):
        """
        Test de configuration des agents pour refléter l'état actuel (désactivé).
        """
        llm_service_mock = MagicMock()
        kernel_instance_mock = mock_kernel_class()

        repair_agent, validation_agent = await setup_agents(llm_service_mock, kernel_instance_mock)

        assert repair_agent is None
        assert validation_agent is None
        kernel_instance_mock.add_service.assert_not_called()
        mock_logger.warning.assert_called_once_with(
            "setup_agents: ChatCompletionAgent est temporairement désactivé. Retour de (None, None)."
        )