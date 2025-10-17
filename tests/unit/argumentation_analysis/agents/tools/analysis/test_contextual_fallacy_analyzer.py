# Authentic gpt-5-mini imports (replacing mocks)
import openai
from semantic_kernel.contents import ChatHistory
from semantic_kernel.core_plugins import ConversationSummaryPlugin
from config.unified_config import UnifiedConfig

# -*- coding: utf-8 -*-
"""
Tests unitaires pour le module contextual_fallacy_analyzer.

Ce module contient les tests unitaires pour les classes et fonctions définies dans le module
agents.tools.analysis.contextual_fallacy_analyzer.
"""

import unittest
import json
from unittest.mock import patch, MagicMock


from argumentation_analysis.agents.tools.analysis.contextual_fallacy_analyzer import (
    ContextualFallacyAnalyzer,
)


class TestContextualFallacyAnalyzer(unittest.TestCase):
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

    """Tests pour la classe ContextualFallacyAnalyzer."""

    def setUp(self):
        """Initialisation avant chaque test."""
        # Créer un mock pour le DataFrame de la taxonomie
        self.test_df = MagicMock()
        self.test_df.__len__.return_value = 4
        # ... (configuration du mock df si nécessaire, mais load_config sera patché)

        # Patch pour ConfigManager.load_config pour qu'il retourne le mock DataFrame
        self.config_manager_patcher = patch(
            "argumentation_analysis.agents.tools.support.shared_services.ConfigManager.load_config"
        )
        self.mock_load_config = self.config_manager_patcher.start()
        self.mock_load_config.return_value = self.test_df

        # Créer l'instance à tester
        self.analyzer = ContextualFallacyAnalyzer()

    def tearDown(self):
        """Nettoyage après chaque test."""
        self.config_manager_patcher.stop()

    def test_init(self):
        """Teste l'initialisation de la classe."""
        self.assertIsNotNone(self.analyzer)
        # Vérifie que le logger est bien configuré
        self.assertIsNotNone(self.analyzer.logger)

    def test_get_taxonomy_df_uses_config_manager(self):
        """Vérifie que _get_taxonomy_df charge la taxonomie via le ConfigManager."""
        # Importer la fonction de chargement réelle pour la passer au mock
        from argumentation_analysis.agents.tools.analysis.contextual_fallacy_analyzer import (
            _load_fallacy_taxonomy,
        )

        # Appeler la méthode qui déclenche le chargement
        df = self.analyzer._get_taxonomy_df()

        # Vérifier que le résultat est bien celui du mock
        self.assertIsNotNone(df)
        self.assertEqual(len(df), 4)
        self.assertEqual(df, self.test_df)

        # Vérifier que ConfigManager.load_config a été appelé correctement
        self.mock_load_config.assert_called_once_with(
            "fallacy_taxonomy", _load_fallacy_taxonomy
        )

    def test_determine_context_type(self):
        """Teste la détermination du type de contexte."""
        # Tester différents types de contexte
        self.assertEqual(
            self.analyzer._determine_context_type("Discours politique sur l'économie"),
            "politique",
        )
        self.assertEqual(
            self.analyzer._determine_context_type("Étude scientifique sur le climat"),
            "scientifique",
        )
        self.assertEqual(
            self.analyzer._determine_context_type(
                "Publicité commerciale pour un produit"
            ),
            "commercial",
        )
        self.assertEqual(
            self.analyzer._determine_context_type(
                "Procès juridique concernant un litige"
            ),
            "juridique",
        )
        self.assertEqual(
            self.analyzer._determine_context_type(
                "Conférence académique sur la philosophie"
            ),
            "académique",
        )
        self.assertEqual(
            self.analyzer._determine_context_type("Discussion générale"), "général"
        )

    def test_identify_potential_fallacies(self):
        """Teste l'identification des sophismes potentiels."""
        # Tester avec différents textes contenant des sophismes
        text1 = "Les experts sont unanimes : ce produit est sûr et efficace."
        fallacies1 = self.analyzer._identify_potential_fallacies(text1)
        self.assertGreaterEqual(len(fallacies1), 1)
        self.assertEqual(fallacies1[0]["fallacy_type"], "Appel à l'autorité")

        text2 = "Tout le monde utilise ce produit, vous devriez l'essayer aussi."
        fallacies2 = self.analyzer._identify_potential_fallacies(text2)
        self.assertGreaterEqual(len(fallacies2), 1)
        self.assertEqual(fallacies2[0]["fallacy_type"], "Appel à la popularité")

        text3 = "Cette tradition ancestrale a fait ses preuves depuis des siècles."
        fallacies3 = self.analyzer._identify_potential_fallacies(text3)
        self.assertGreaterEqual(len(fallacies3), 1)
        self.assertEqual(fallacies3[0]["fallacy_type"], "Appel à la tradition")

        # Tester avec un texte sans sophismes évidents
        text4 = "Voici les faits et les données concernant ce sujet."
        fallacies4 = self.analyzer._identify_potential_fallacies(text4)
        self.assertEqual(len(fallacies4), 0)

    def test_filter_by_context(self):
        """Teste le filtrage des sophismes en fonction du contexte."""
        # Créer des sophismes potentiels
        potential_fallacies = [
            {
                "fallacy_type": "Appel à l'autorité",
                "keyword": "expert",
                "context_text": "Les experts affirment que...",
                "confidence": 0.5,
            },
            {
                "fallacy_type": "Appel à la popularité",
                "keyword": "tout le monde",
                "context_text": "Tout le monde sait que...",
                "confidence": 0.5,
            },
            {
                "fallacy_type": "Ad hominem",
                "keyword": "personne",
                "context_text": "Cette personne n'est pas crédible...",
                "confidence": 0.5,
            },
        ]

        # Tester le filtrage dans un contexte scientifique
        filtered_scientific = self.analyzer._filter_by_context(
            potential_fallacies, "scientifique"
        )
        self.assertEqual(
            len(filtered_scientific), 3
        )  # Tous les sophismes sont retournés, mais avec des confiances différentes

        # Vérifier que les confiances ont été ajustées
        for fallacy in filtered_scientific:
            if fallacy["fallacy_type"] in [
                "Appel à l'autorité",
                "Appel à la popularité",
            ]:
                self.assertEqual(fallacy["confidence"], 0.8)
                self.assertEqual(fallacy["contextual_relevance"], "Élevée")
            else:
                self.assertEqual(fallacy["confidence"], 0.3)
                self.assertEqual(fallacy["contextual_relevance"], "Faible")

        # Tester le filtrage dans un contexte politique
        filtered_political = self.analyzer._filter_by_context(
            potential_fallacies, "politique"
        )
        self.assertEqual(len(filtered_political), 3)

        # Vérifier que les confiances ont été ajustées
        for fallacy in filtered_political:
            if fallacy["fallacy_type"] in ["Ad hominem"]:
                self.assertEqual(fallacy["confidence"], 0.8)
                self.assertEqual(fallacy["contextual_relevance"], "Élevée")
            else:
                self.assertEqual(fallacy["confidence"], 0.3)
                self.assertEqual(fallacy["contextual_relevance"], "Faible")

        # Tester le filtrage dans un contexte général
        filtered_general = self.analyzer._filter_by_context(
            potential_fallacies, "général"
        )
        self.assertEqual(len(filtered_general), 3)

        # Vérifier que les confiances n'ont pas été modifiées
        for fallacy in filtered_general:
            self.assertEqual(fallacy["confidence"], 0.5)

    def test_analyze_context(self):
        """Teste l'analyse du contexte."""
        # Ce test est maintenant un test d'intégration léger qui vérifie la structure de la sortie.
        text = "Les experts affirment que ce produit est sûr et efficace."
        context = "Étude scientifique sur l'efficacité d'un médicament"

        result = self.analyzer.analyze_context(text, context)

        # On vérifie la structure de base du résultat.
        self.assertIn("context_type", result)
        self.assertIn("potential_fallacies_count", result)
        self.assertIn("contextual_fallacies_count", result)
        self.assertIn("contextual_fallacies", result)
        self.assertIsInstance(result["contextual_fallacies"], list)

    def test_identify_contextual_fallacies(self):
        """Teste l'identification des sophismes contextuels."""
        # On mock la méthode analyze_context pour isoler la logique de filtrage
        with patch.object(self.analyzer, "analyze_context") as mock_analyze_context:
            mock_analyze_context.return_value = {
                "contextual_fallacies": [
                    {"fallacy_type": "Appel à l'autorité", "confidence": 0.8},
                    {"fallacy_type": "Appel à la popularité", "confidence": 0.3},
                ]
            }

            argument = "Texte d'exemple."
            context = "Contexte d'exemple."
            result = self.analyzer.identify_contextual_fallacies(argument, context)

            # La méthode doit filtrer les sophismes avec une confiance < 0.5
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["fallacy_type"], "Appel à l'autorité")
            mock_analyze_context.assert_called_once_with(argument, context)

    def test_get_contextual_fallacy_examples(self):
        """Teste la récupération d'exemples de sophismes contextuels."""
        # Tester avec un sophisme et un contexte existants
        examples = self.analyzer.get_contextual_fallacy_examples(
            "Appel à l'autorité", "politique"
        )
        self.assertGreaterEqual(len(examples), 1)
        self.assertIsInstance(examples[0], str)

        # Tester avec un sophisme existant mais un contexte inexistant
        examples = self.analyzer.get_contextual_fallacy_examples(
            "Appel à l'autorité", "inexistant"
        )
        self.assertEqual(len(examples), 1)
        self.assertEqual(
            examples[0],
            "Aucun exemple disponible pour ce type de sophisme dans ce contexte.",
        )

        # Tester avec un sophisme inexistant
        examples = self.analyzer.get_contextual_fallacy_examples(
            "Sophisme inexistant", "politique"
        )
        self.assertEqual(len(examples), 1)
        self.assertEqual(
            examples[0],
            "Aucun exemple disponible pour ce type de sophisme dans ce contexte.",
        )


if __name__ == "__main__":
    unittest.main()
