import openai
from semantic_kernel.contents import ChatHistory
from semantic_kernel.core_plugins import ConversationSummaryPlugin
from config.unified_config import UnifiedConfig

# -*- coding: utf-8 -*-
"""
Tests unitaires pour le module extract_definitions.

Ce module contient les tests unitaires pour les classes définies dans le module
agents.core.extract.extract_definitions.
"""

import unittest
import json

from argumentation_analysis.agents.core.extract.extract_definitions import (
    ExtractResult,
    ExtractAgentPlugin,
    ExtractDefinition,
)


class TestExtractResult(unittest.TestCase):
    async def _create_authentic_gpt4o_mini_instance(self):
        """Crée une instance authentique de gpt-5-mini au lieu d'un mock."""
        config = UnifiedConfig()
        return config.get_kernel_with_gpt4o_mini()

    async def _make_authentic_llm_call(self, prompt: str) -> str:
        """Fait un appel authentique à gpt-5-mini."""
        try:
            kernel = await self._create_authentic_gpt4o_mini_instance()
            result = await kernel.invoke("chat", input=prompt)
            return str(result)
        except Exception as e:
            logger.warning(f"Appel LLM authentique échoué: {e}")
            return "Authentic LLM call failed"

    """Tests pour la classe ExtractResult."""

    def setUp(self):
        """Initialisation avant chaque test."""
        # Créer un résultat d'extraction valide
        self.valid_result = ExtractResult(
            source_name="Source de test",
            extract_name="Extrait de test",
            status="valid",
            message="Extraction réussie",
            start_marker="Début",
            end_marker="Fin",
            template_start="T{0}",
            explanation="Explication de l'extraction",
            extracted_text="Texte extrait de test",
        )

        # Créer un résultat d'extraction avec erreur
        self.error_result = ExtractResult(
            source_name="Source de test",
            extract_name="Extrait de test",
            status="error",
            message="Erreur lors de l'extraction",
            start_marker="Début",
            end_marker="Fin",
        )

        # Créer un résultat d'extraction rejeté
        self.rejected_result = ExtractResult(
            source_name="Source de test",
            extract_name="Extrait de test",
            status="rejected",
            message="Extraction rejetée",
            start_marker="Début",
            end_marker="Fin",
        )

    def test_init(self):
        """Test d'initialisation d'un résultat d'extraction."""
        # Vérifier les propriétés du résultat valide
        self.assertEqual(self.valid_result.source_name, "Source de test")
        self.assertEqual(self.valid_result.extract_name, "Extrait de test")
        self.assertEqual(self.valid_result.status, "valid")
        self.assertEqual(self.valid_result.message, "Extraction réussie")
        self.assertEqual(self.valid_result.start_marker, "Début")
        self.assertEqual(self.valid_result.end_marker, "Fin")
        self.assertEqual(self.valid_result.template_start, "T{0}")
        self.assertEqual(self.valid_result.explanation, "Explication de l'extraction")
        self.assertEqual(self.valid_result.extracted_text, "Texte extrait de test")

    def test_to_dict(self):
        """Test de conversion d'un résultat d'extraction en dictionnaire."""
        result_dict = self.valid_result.to_dict()

        # Vérifier les propriétés du dictionnaire
        self.assertEqual(result_dict["source_name"], "Source de test")
        self.assertEqual(result_dict["extract_name"], "Extrait de test")
        self.assertEqual(result_dict["status"], "valid")
        self.assertEqual(result_dict["message"], "Extraction réussie")
        self.assertEqual(result_dict["start_marker"], "Début")
        self.assertEqual(result_dict["end_marker"], "Fin")
        self.assertEqual(result_dict["template_start"], "T{0}")
        self.assertEqual(result_dict["explanation"], "Explication de l'extraction")
        self.assertEqual(result_dict["extracted_text"], "Texte extrait de test")

    def test_from_dict(self):
        """Test de création d'un résultat d'extraction à partir d'un dictionnaire."""
        result_dict = {
            "source_name": "Nouvelle source",
            "extract_name": "Nouvel extrait",
            "status": "valid",
            "message": "Nouvelle extraction",
            "start_marker": "Nouveau début",
            "end_marker": "Nouvelle fin",
            "template_start": "N{0}",
            "explanation": "Nouvelle explication",
            "extracted_text": "Nouveau texte extrait",
        }

        result = ExtractResult.from_dict(result_dict)

        # Vérifier les propriétés du résultat
        self.assertEqual(result.source_name, "Nouvelle source")
        self.assertEqual(result.extract_name, "Nouvel extrait")
        self.assertEqual(result.status, "valid")
        self.assertEqual(result.message, "Nouvelle extraction")
        self.assertEqual(result.start_marker, "Nouveau début")
        self.assertEqual(result.end_marker, "Nouvelle fin")
        self.assertEqual(result.template_start, "N{0}")
        self.assertEqual(result.explanation, "Nouvelle explication")
        self.assertEqual(result.extracted_text, "Nouveau texte extrait")

    def test_from_dict_with_missing_fields(self):
        """Test de création d'un résultat avec des champs manquants."""
        result_dict = {
            "source_name": "Source minimale",
            "extract_name": "Extrait minimal",
            "status": "valid",
            "message": "Extraction minimale",
        }

        result = ExtractResult.from_dict(result_dict)

        # Vérifier les propriétés du résultat
        self.assertEqual(result.source_name, "Source minimale")
        self.assertEqual(result.extract_name, "Extrait minimal")
        self.assertEqual(result.status, "valid")
        self.assertEqual(result.message, "Extraction minimale")
        self.assertEqual(result.start_marker, "")
        self.assertEqual(result.end_marker, "")
        self.assertEqual(result.template_start, "")
        self.assertEqual(result.explanation, "")
        self.assertEqual(result.extracted_text, "")


class TestExtractAgentPlugin(unittest.TestCase):
    """Tests pour la classe ExtractAgentPlugin."""

    def setUp(self):
        """Initialisation avant chaque test."""
        self.plugin = ExtractAgentPlugin()
        self.test_text = "Ceci est un texte de test pour l'extraction. " * 10

    def test_init(self):
        """Test d'initialisation du plugin d'extraction."""
        self.assertEqual(self.plugin.extract_results, [])

    def test_find_similar_markers_with_default_function(self):
        """Test de la méthode find_similar_markers avec la fonction par défaut."""
        marker = "texte de test"
        results = self.plugin.find_similar_markers(self.test_text, marker)

        # Vérifier que des résultats sont retournés
        self.assertTrue(len(results) > 0)

        # Vérifier la structure des résultats
        for result in results:
            self.assertIn("marker", result)
            self.assertIn("position", result)
            self.assertIn("context", result)

    async def test_find_similar_markers_with_custom_function(self):
        """Test de la méthode find_similar_markers avec une fonction personnalisée."""
        marker = "texte de test"

        # Créer une fonction mock
        mock_find_similar_text = AsyncMock()
        # Simuler le retour de la fonction find_similar_text
        # Elle devrait retourner une liste de tuples (contexte, position, texte_marqueur_trouvé)
        mock_find_similar_text.return_value = [
            ("contexte avant texte de test contexte après", 10, "texte de test")
        ]

        results = await self.plugin.find_similar_markers(  # find_similar_markers est probablement async
            self.test_text, marker, find_similar_text_func=mock_find_similar_text
        )

        # Vérifier que la fonction mock a été appelée
        mock_find_similar_text.assert_called_once_with(
            self.test_text, marker, context_size=50, max_results=5
        )

        # Vérifier les résultats
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["marker"], "texte de test")
        self.assertEqual(results[0]["position"], 10)
        self.assertEqual(
            results[0]["context"], "contexte avant texte de test contexte après"
        )

    def test_search_text_dichotomically(self):
        """Test de la méthode search_text_dichotomically."""
        search_term = "texte de test"
        results = self.plugin.search_text_dichotomically(self.test_text, search_term)

        # Vérifier que des résultats sont retournés
        self.assertTrue(len(results) > 0)

        # Vérifier la structure des résultats
        for result in results:
            self.assertIn("match", result)
            self.assertIn("position", result)
            self.assertIn("context", result)
            self.assertIn("block_start", result)
            self.assertIn("block_end", result)

    def test_extract_blocks(self):
        """Test de la méthode extract_blocks."""
        blocks = self.plugin.extract_blocks(self.test_text, block_size=100, overlap=20)

        # Vérifier que des blocs sont retournés
        self.assertTrue(len(blocks) > 0)

        # Vérifier la structure des blocs
        for block in blocks:
            self.assertIn("block", block)
            self.assertIn("start_pos", block)
            self.assertIn("end_pos", block)

        # Vérifier le chevauchement
        for i in range(1, len(blocks)):
            self.assertTrue(blocks[i]["start_pos"] < blocks[i - 1]["end_pos"])

    def test_get_extract_results(self):
        """Test de la méthode get_extract_results."""
        # Ajouter des résultats
        self.plugin.extract_results = [
            {"source_name": "Source 1", "extract_name": "Extrait 1"},
            {"source_name": "Source 2", "extract_name": "Extrait 2"},
        ]

        results = self.plugin.get_extract_results()

        # Vérifier les résultats
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["source_name"], "Source 1")
        self.assertEqual(results[0]["extract_name"], "Extrait 1")
        self.assertEqual(results[1]["source_name"], "Source 2")
        self.assertEqual(results[1]["extract_name"], "Extrait 2")


class TestExtractDefinition(unittest.TestCase):
    """Tests pour la classe ExtractDefinition."""

    def setUp(self):
        """Initialisation avant chaque test."""
        self.definition = ExtractDefinition(
            source_name="Source de test",
            extract_name="Extrait de test",
            start_marker="Début",
            end_marker="Fin",
            template_start="T{0}",
            description="Description de l'extrait",
        )

    def test_init(self):
        """Test d'initialisation d'une définition d'extraction."""
        self.assertEqual(self.definition.source_name, "Source de test")
        self.assertEqual(self.definition.extract_name, "Extrait de test")
        self.assertEqual(self.definition.start_marker, "Début")
        self.assertEqual(self.definition.end_marker, "Fin")
        self.assertEqual(self.definition.template_start, "T{0}")
        self.assertEqual(self.definition.description, "Description de l'extrait")

    def test_to_dict(self):
        """Test de conversion d'une définition d'extraction en dictionnaire."""
        definition_dict = self.definition.to_dict()

        # Vérifier les propriétés du dictionnaire
        self.assertEqual(definition_dict["source_name"], "Source de test")
        self.assertEqual(definition_dict["extract_name"], "Extrait de test")
        self.assertEqual(definition_dict["start_marker"], "Début")
        self.assertEqual(definition_dict["end_marker"], "Fin")
        self.assertEqual(definition_dict["template_start"], "T{0}")
        self.assertEqual(definition_dict["description"], "Description de l'extrait")

    def test_from_dict(self):
        """Test de création d'une définition d'extraction à partir d'un dictionnaire."""
        definition_dict = {
            "source_name": "Nouvelle source",
            "extract_name": "Nouvel extrait",
            "start_marker": "Nouveau début",
            "end_marker": "Nouvelle fin",
            "template_start": "N{0}",
            "description": "Nouvelle description",
        }

        definition = ExtractDefinition.from_dict(definition_dict)

        # Vérifier les propriétés de la définition
        self.assertEqual(definition.source_name, "Nouvelle source")
        self.assertEqual(definition.extract_name, "Nouvel extrait")
        self.assertEqual(definition.start_marker, "Nouveau début")
        self.assertEqual(definition.end_marker, "Nouvelle fin")
        self.assertEqual(definition.template_start, "N{0}")
        self.assertEqual(definition.description, "Nouvelle description")

    def test_from_dict_with_missing_fields(self):
        """Test de création d'une définition avec des champs manquants."""
        definition_dict = {
            "source_name": "Source minimale",
            "extract_name": "Extrait minimal",
            "start_marker": "Début minimal",
            "end_marker": "Fin minimale",
        }

        definition = ExtractDefinition.from_dict(definition_dict)

        # Vérifier les propriétés de la définition
        self.assertEqual(definition.source_name, "Source minimale")
        self.assertEqual(definition.extract_name, "Extrait minimal")
        self.assertEqual(definition.start_marker, "Début minimal")
        self.assertEqual(definition.end_marker, "Fin minimale")
        self.assertEqual(definition.template_start, "")
        self.assertEqual(definition.description, "")


if __name__ == "__main__":
    unittest.main()
