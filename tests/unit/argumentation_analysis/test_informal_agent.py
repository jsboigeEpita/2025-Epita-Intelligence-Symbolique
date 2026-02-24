import openai
from semantic_kernel.contents import ChatHistory
from semantic_kernel.core_plugins import ConversationSummaryPlugin
from config.unified_config import UnifiedConfig

# -*- coding: utf-8 -*-
"""
Tests unitaires pour l'agent d'analyse informelle.
"""

import unittest
from unittest.mock import patch, MagicMock
import json
import os
import tempfile
import pandas as pd
import numpy as np

from pathlib import Path
import semantic_kernel as sk
from argumentation_analysis.agents.core.informal.informal_definitions import (
    InformalAnalysisPlugin,
    setup_informal_kernel,
)
import pytest
import logging

# Configuration du logging pour les tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest.fixture(scope="function")
def informal_plugin_with_test_df(mocker):
    """
        Fixture Pytest qui fournit une instance de InformalAnalysisPlugin avec une taxonomie de test.
        - Crée un DataFrame de test en mémoire.
        - Patche `load_csv_file` pour qu'il retourne ce DataFrame au lieu de lire un fichier.
        - Initialise le plugin, qui appelle en interne la logique de préparation des données
    (_internal_load_and_prepare_dataframe), assurant ainsi que le DataFrame est
    correctement indexé et que les types de données sont normalisés.
    """
    test_df = pd.DataFrame(
        {
            "PK": [1, 2, 3, 4, 5, 6],
            "FK_Parent": [pd.NA, 1, 1, 2, pd.NA, 5],
            "parent_pk": [pd.NA, 1, 1, 2, pd.NA, 5],
            "path": ["1", "1.2", "1.3", "1.2.4", "5", "5.6"],
            "depth": [0, 1, 1, 2, 0, 1],
            "Name": [
                "Cat A",
                "Sophisme A1",
                "Sophisme A2",
                "Sophisme A1.1",
                "Cat B",
                "Sophisme B1",
            ],
            "nom_vulgarise": [
                "Catégorie A",
                "Sophisme A Un",
                "Sophisme A Deux",
                "Sophisme A Un Point Un",
                "Catégorie B",
                "Sophisme B Un",
            ],
            "Famille": [
                "Famille Alpha",
                "Famille Alpha",
                "Famille Alpha",
                "Famille Alpha",
                "Famille Beta",
                "Famille Beta",
            ],
            "text_fr": [
                "Description A",
                "Desc A1",
                "Desc A2",
                "Desc A1.1",
                "Description B",
                "Desc B1",
            ],
            "desc_fr": [
                "Définition longue A",
                "Déf A1",
                "Déf A2",
                "Déf A1.1",
                "Définition longue B",
                "Déf B1",
            ],
            "example_fr": [
                "Exemple A",
                "Ex A1",
                "Ex A2",
                "Ex A1.1",
                "Exemple B",
                "Ex B1",
            ],
        }
    )

    # Patcher la fonction de chargement pour qu'elle retourne notre DataFrame de test
    mocker.patch(
        "argumentation_analysis.agents.core.informal.informal_definitions.load_csv_file",
        return_value=test_df.copy(),
    )

    # Initialiser le plugin. Le chemin fourni ici est un placeholder car le chargement est patché.
    mock_kernel = MagicMock(spec=sk.Kernel)
    plugin = InformalAnalysisPlugin(
        kernel=mock_kernel, taxonomy_file_path="dummy/path/to/taxonomy.csv"
    )

    # Forcer le chargement et la préparation du DataFrame dans le cache du plugin pour les tests.
    # C'est l'étape cruciale qui manquait.
    plugin._get_taxonomy_dataframe()

    return plugin


@pytest.mark.use_real_numpy
class TestInformalAnalysisPlugin:
    """
    Suite de tests refactorisée pour InformalAnalysisPlugin.
    Ces tests utilisent une fixture qui prépare correctement une instance du plugin
    avec une taxonomie de test, en s'assurant que l'index et les types de données
    sont correctement configurés.
    """

    def test_get_taxonomy_dataframe(self, informal_plugin_with_test_df):
        """
        Vérifie que la méthode _get_taxonomy_dataframe retourne un DataFrame
        correctement préparé (indexé sur PK).
        """
        df = informal_plugin_with_test_df._get_taxonomy_dataframe()

        assert df is not None
        assert isinstance(df, pd.DataFrame)
        assert df.index.name == "PK"
        assert pd.api.types.is_integer_dtype(df.index.dtype)

    def test_explore_fallacy_hierarchy(self, informal_plugin_with_test_df):
        """
        Teste l'exploration réussie de la hiérarchie d'un nœud.
        """
        pk_to_test = "1"
        result_json = informal_plugin_with_test_df.explore_fallacy_hierarchy(pk_to_test)
        result = json.loads(result_json)

        assert result.get("error") is None
        assert result["current_node"]["pk"] == 1
        assert len(result["children"]) == 2
        assert result["children"][0]["nom_vulgarise"] == "Sophisme A Un"

    def test_get_fallacy_details(self, informal_plugin_with_test_df):
        """
        Teste la récupération des détails complets d'un sophisme via la fonction publique.
        """
        pk_to_test = "2"
        result_json = informal_plugin_with_test_df.get_fallacy_details(pk_to_test)
        details = json.loads(result_json)

        assert details.get("error") is None
        assert details["pk"] == 2
        assert details["Name"] == "Sophisme A1"
        assert details["parent"]["nom_vulgarise"] == "Catégorie A"
        assert len(details["children"]) == 1
        assert details["children"][0]["pk"] == 4

    def test_find_fallacy_definition(self, informal_plugin_with_test_df):
        """
        Teste la recherche de la définition d'un sophisme par son nom.
        """
        result_json = informal_plugin_with_test_df.find_fallacy_definition(
            "Sophisme A Un"
        )
        result = json.loads(result_json)

        assert result.get("error") is None
        assert result["pk"] == 2
        assert "Sophisme A Un" in result["fallacy_name"]
        assert result["definition"] == "Déf A1"


@pytest.mark.use_real_numpy
class TestSetupInformalKernel:
    """Tests pour la fonction setup_informal_kernel."""

    @pytest.fixture
    def configured_kernel_and_service(self):
        """Fixture pour initialiser un kernel et un service LLM authentique."""
        config = UnifiedConfig()
        kernel_with_service = config.get_kernel_with_gpt4o_mini()
        llm_service = kernel_with_service.get_service()
        kernel = sk.Kernel()
        return kernel, llm_service

    @patch("semantic_kernel.Kernel.add_function")
    @patch("semantic_kernel.Kernel.add_plugin")
    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY"), reason="OPENAI_API_KEY non disponible"
    )
    async def test_setup_informal_kernel(
        self, mock_add_plugin, mock_add_function, configured_kernel_and_service
    ):
        """Teste la configuration du kernel pour l'agent informel."""
        kernel, llm_service = configured_kernel_and_service

        # Appeler la fonction à tester
        setup_informal_kernel(kernel, llm_service)

        # Vérifier que le plugin natif a été ajouté une fois
        mock_add_plugin.assert_called_once()
        # Vérifier le type de l'instance du plugin
        plugin_instance = mock_add_plugin.call_args[0][0]
        assert isinstance(plugin_instance, InformalAnalysisPlugin)

        # Vérifier que les fonctions sémantiques ont été ajoutées
        assert mock_add_function.call_count >= 3

        # On peut optionnellement vérifier les noms des fonctions ajoutées
        added_functions = [
            call.kwargs["function_name"] for call in mock_add_function.call_args_list
        ]
        assert "semantic_IdentifyArguments" in added_functions
        assert "semantic_AnalyzeFallacies" in added_functions
        assert "semantic_JustifyFallacyAttribution" in added_functions


if __name__ == "__main__":
    # Garde la compatibilité pour une exécution directe du script, mais les tests sont maintenant orientés pytest.
    # Pour exécuter, utiliser `pytest` à la racine du projet.
    pass
