from unittest.mock import patch, MagicMock

import openai
from semantic_kernel.contents import ChatHistory
from semantic_kernel.core_plugins import ConversationSummaryPlugin
from config.unified_config import UnifiedConfig

# -*- coding: utf-8 -*-
"""
Tests unitaires pour le module complex_fallacy_analyzer.

Ce module contient les tests unitaires pour les classes et fonctions définies dans le module
agents.tools.analysis.complex_fallacy_analyzer.
"""

import unittest
import json


from argumentation_analysis.agents.tools.analysis.complex_fallacy_analyzer import (
    ComplexFallacyAnalyzer,
)


class TestComplexFallacyAnalyzer(unittest.TestCase):
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

    """Tests pour la classe ComplexFallacyAnalyzer."""

    def setUp(self):
        """Initialisation avant chaque test."""
        # Patch pour les dépendances
        self.contextual_analyzer_patcher = patch(
            "argumentation_analysis.agents.tools.analysis.complex_fallacy_analyzer.ContextualFallacyAnalyzer"
        )
        self.mock_contextual_analyzer_class = self.contextual_analyzer_patcher.start()
        self.mock_contextual_analyzer = MagicMock()
        self.mock_contextual_analyzer_class.return_value = self.mock_contextual_analyzer

        self.severity_evaluator_patcher = patch(
            "argumentation_analysis.agents.tools.analysis.complex_fallacy_analyzer.FallacySeverityEvaluator"
        )
        self.mock_severity_evaluator_class = self.severity_evaluator_patcher.start()
        self.mock_severity_evaluator = MagicMock()
        self.mock_severity_evaluator_class.return_value = self.mock_severity_evaluator

        # Configurer le mock de l'évaluateur de sévérité
        self.mock_severity_evaluator._determine_severity_level.return_value = "Moyen"

        # Créer l'instance à tester
        self.analyzer = ComplexFallacyAnalyzer()

    def tearDown(self):
        """Nettoyage après chaque test."""
        self.contextual_analyzer_patcher.stop()
        self.severity_evaluator_patcher.stop()

    def test_init(self):
        """Teste l'initialisation de la classe."""
        self.assertIsNotNone(self.analyzer)
        self.assertEqual(
            self.analyzer.contextual_analyzer, self.mock_contextual_analyzer
        )
        self.assertEqual(self.analyzer.severity_evaluator, self.mock_severity_evaluator)
        self.assertIsNotNone(self.analyzer.fallacy_combinations)
        self.assertIsNotNone(self.analyzer.structural_fallacies)

    def test_load_fallacy_combinations(self):
        """Teste le chargement des combinaisons de sophismes."""
        # Réinitialiser l'analyseur pour appeler explicitement _load_fallacy_combinations
        self.analyzer = ComplexFallacyAnalyzer()

        # Vérifier que les combinaisons ont été chargées
        self.assertIn("Double appel", self.analyzer.fallacy_combinations)
        self.assertIn("Dilemme émotionnel", self.analyzer.fallacy_combinations)
        self.assertIn(
            "Attaque personnelle généralisée", self.analyzer.fallacy_combinations
        )

        # Vérifier que les sophismes structurels ont été chargés
        self.assertIn("Contradiction cachée", self.analyzer.structural_fallacies)
        self.assertIn("Cercle argumentatif", self.analyzer.structural_fallacies)

    def test_identify_combined_fallacies_with_matches(self):
        """Teste l'identification des combinaisons de sophismes avec des correspondances."""
        # Configurer le mock de l'analyseur contextuel
        self.mock_contextual_analyzer.identify_contextual_fallacies.return_value = [
            {
                "fallacy_type": "Appel à l'autorité",
                "keyword": "expert",
                "context_text": "Les experts affirment que...",
                "confidence": 0.8,
            },
            {
                "fallacy_type": "Appel à la popularité",
                "keyword": "tout le monde",
                "context_text": "Tout le monde sait que...",
                "confidence": 0.7,
            },
        ]

        # Appeler la méthode à tester
        argument = "Les experts affirment que ce produit est sûr. Tout le monde sait que c'est le meilleur."
        result = self.analyzer.identify_combined_fallacies(argument)

        # Vérifier les résultats
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["combination_name"], "Double appel")
        self.assertIn("Appel à l'autorité", result[0]["components"])
        self.assertIn("Appel à la popularité", result[0]["components"])
        self.assertEqual(len(result[0]["component_fallacies"]), 2)
        self.assertGreater(
            result[0]["severity"], 0.8
        )  # Devrait être 0.8 + 0.2 = 1.0 (plafonné)

        # Vérifier que l'analyseur contextuel a été appelé correctement
        self.mock_contextual_analyzer.identify_contextual_fallacies.assert_called_once_with(
            argument=argument, context="général"
        )

    def test_identify_combined_fallacies_without_matches(self):
        """Teste l'identification des combinaisons de sophismes sans correspondances."""
        # Configurer le mock de l'analyseur contextuel
        self.mock_contextual_analyzer.identify_contextual_fallacies.return_value = [
            {
                "fallacy_type": "Appel à l'autorité",
                "keyword": "expert",
                "context_text": "Les experts affirment que...",
                "confidence": 0.8,
            }
        ]

        # Appeler la méthode à tester
        argument = "Les experts affirment que ce produit est sûr."
        result = self.analyzer.identify_combined_fallacies(argument)

        # Vérifier les résultats
        self.assertEqual(len(result), 0)

        # Vérifier que l'analyseur contextuel a été appelé correctement
        self.mock_contextual_analyzer.identify_contextual_fallacies.assert_called_once_with(
            argument=argument, context="général"
        )

    def test_analyze_structural_fallacies(self):
        """Teste l'analyse des sophismes structurels."""
        # Configurer le mock de l'analyseur contextuel
        self.mock_contextual_analyzer.identify_contextual_fallacies.return_value = [
            {
                "fallacy_type": "Appel à l'autorité",
                "keyword": "expert",
                "context_text": "Les experts affirment que...",
                "confidence": 0.8,
            }
        ]

        # Patch pour les méthodes internes
        with patch.object(
            self.analyzer, "_detect_contradictions"
        ) as mock_detect_contradictions, patch.object(
            self.analyzer, "_detect_circular_arguments"
        ) as mock_detect_circular_arguments:
            # Configurer les mocks des méthodes internes
            mock_detect_contradictions.return_value = [
                {
                    "involved_arguments": [0, 1],
                    "details": {
                        "positive_statement": "Ce produit est sûr",
                        "negative_statement": "Ce produit n'est pas sûr",
                    },
                }
            ]
            mock_detect_circular_arguments.return_value = []

            # Appeler la méthode à tester
            arguments = [
                "Ce produit est sûr car les experts l'affirment.",
                "Ce produit n'est pas sûr car il n'a pas été testé.",
            ]
            result = self.analyzer.analyze_structural_fallacies(arguments)

            # Vérifier les résultats
            self.assertEqual(len(result), 1)
            self.assertEqual(
                result[0]["structural_fallacy_type"], "Contradiction cachée"
            )
            self.assertEqual(result[0]["involved_arguments"], [0, 1])
            self.assertEqual(result[0]["severity"], 0.8)
            self.assertEqual(result[0]["severity_level"], "Élevé")

            # Vérifier que les méthodes internes ont été appelées correctement
            mock_detect_contradictions.assert_called_once_with(arguments)
            mock_detect_circular_arguments.assert_called_once_with(arguments)

    def test_detect_contradictions(self):
        """Teste la détection des contradictions entre arguments."""
        # Appeler la méthode à tester
        arguments = [
            "Ce produit est sûr et efficace.",
            "Ce produit n'est pas sûr pour les enfants.",
        ]
        result = self.analyzer._detect_contradictions(arguments)

        # Vérifier les résultats
        self.assertGreaterEqual(len(result), 1)
        self.assertEqual(result[0]["involved_arguments"], [0, 1])
        self.assertIn("positive_statement", result[0]["details"])
        self.assertIn("negative_statement", result[0]["details"])

    def test_detect_circular_arguments(self):
        """Teste la détection des cercles argumentatifs."""
        # Appeler la méthode à tester
        arguments = [
            "Ce produit est efficace, donc il est recommandé.",
            "Ce produit est recommandé, donc il est populaire.",
            "Ce produit est populaire, donc il est efficace.",
        ]
        result = self.analyzer._detect_circular_arguments(arguments)

        # Vérifier les résultats
        self.assertGreaterEqual(len(result), 1)
        self.assertEqual(len(result[0]["involved_arguments"]), 3)
        self.assertTrue(result[0]["details"]["arg1_supports_arg2"])
        self.assertTrue(result[0]["details"]["arg2_supports_arg3"])
        self.assertTrue(result[0]["details"]["arg3_supports_arg1"])

    def test_identify_fallacy_patterns(self):
        """Teste l'identification des motifs de sophismes."""
        # Configurer le mock de l'analyseur contextuel
        self.mock_contextual_analyzer.identify_contextual_fallacies.return_value = [
            # Premier paragraphe
            {
                "fallacy_type": "Appel à l'autorité",
                "keyword": "expert",
                "context_text": "Les experts affirment que...",
                "confidence": 0.8,
            },
            # Deuxième paragraphe
            {
                "fallacy_type": "Appel à l'émotion",
                "keyword": "peur",
                "context_text": "Vous devriez avoir peur de...",
                "confidence": 0.7,
            },
            # Troisième paragraphe
            {
                "fallacy_type": "Appel à l'autorité",
                "keyword": "scientifique",
                "context_text": "Les scientifiques ont prouvé que...",
                "confidence": 0.8,
            },
            # Quatrième paragraphe
            {
                "fallacy_type": "Appel à l'émotion",
                "keyword": "inquiétude",
                "context_text": "Cela devrait vous inquiéter...",
                "confidence": 0.7,
            },
        ]

        # Patch pour les méthodes internes
        with patch.object(
            self.analyzer, "_detect_alternation_patterns"
        ) as mock_detect_alternation, patch.object(
            self.analyzer, "_detect_escalation_patterns"
        ) as mock_detect_escalation:
            # Configurer les mocks des méthodes internes
            mock_detect_alternation.return_value = [
                {
                    "fallacy_type1": "Appel à l'autorité",
                    "fallacy_type2": "Appel à l'émotion",
                    "alternation_count": 2,
                    "involved_paragraphs": [0, 1, 2, 3],
                }
            ]
            mock_detect_escalation.return_value = []

            # Appeler la méthode à tester
            text = """
            Les experts affirment que ce produit est sûr.
            
            Vous devriez avoir peur des conséquences si vous ne l'utilisez pas.
            
            Les scientifiques ont prouvé l'efficacité de ce produit.
            
            Cela devrait vous inquiéter si vous n'agissez pas maintenant.
            """
            result = self.analyzer.identify_fallacy_patterns(text)

            # Vérifier les résultats
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["pattern_type"], "Alternance")
            self.assertEqual(
                result[0]["fallacy_types"], ["Appel à l'autorité", "Appel à l'émotion"]
            )
            self.assertEqual(result[0]["severity"], 0.7)
            self.assertEqual(result[0]["severity_level"], "Élevé")

            # Vérifier que les méthodes internes ont été appelées correctement
            self.assertEqual(
                self.mock_contextual_analyzer.identify_contextual_fallacies.call_count,
                1,
            )
            mock_detect_alternation.assert_called_once()
            mock_detect_escalation.assert_called_once()

    def test_detect_alternation_patterns(self):
        """Teste la détection des motifs d'alternance."""
        # Créer des données de test
        paragraph_fallacies = [
            {
                "paragraph_index": 0,
                "fallacies": [
                    {"fallacy_type": "Appel à l'autorité", "confidence": 0.8}
                ],
            },
            {
                "paragraph_index": 1,
                "fallacies": [{"fallacy_type": "Appel à l'émotion", "confidence": 0.7}],
            },
            {
                "paragraph_index": 2,
                "fallacies": [
                    {"fallacy_type": "Appel à l'autorité", "confidence": 0.8}
                ],
            },
            {
                "paragraph_index": 3,
                "fallacies": [{"fallacy_type": "Appel à l'émotion", "confidence": 0.7}],
            },
        ]

        # Appeler la méthode à tester
        result = self.analyzer._detect_alternation_patterns(paragraph_fallacies)

        # Vérifier les résultats
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["fallacy_type1"], "Appel à l'autorité")
        self.assertEqual(result[0]["fallacy_type2"], "Appel à l'émotion")
        self.assertEqual(result[0]["alternation_count"], 3)
        self.assertEqual(len(result[0]["involved_paragraphs"]), 4)

    def test_detect_escalation_patterns(self):
        """Teste la détection des motifs d'escalade."""
        # Créer des données de test
        paragraph_fallacies = [
            {
                "paragraph_index": 0,
                "fallacies": [
                    {"fallacy_type": "Appel à la tradition", "confidence": 0.6}
                ],
            },
            {
                "paragraph_index": 1,
                "fallacies": [
                    {"fallacy_type": "Appel à l'autorité", "confidence": 0.7}
                ],
            },
            {
                "paragraph_index": 2,
                "fallacies": [{"fallacy_type": "Ad hominem", "confidence": 0.8}],
            },
        ]

        # Appeler la méthode à tester
        result = self.analyzer._detect_escalation_patterns(paragraph_fallacies)

        # Vérifier les résultats
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["start_fallacy_type"], "Appel à la tradition")
        self.assertEqual(result[0]["end_fallacy_type"], "Ad hominem")
        self.assertEqual(
            result[0]["fallacy_sequence"],
            ["Appel à la tradition", "Appel à l'autorité", "Ad hominem"],
        )
        self.assertEqual(result[0]["involved_paragraphs"], [0, 1, 2])


if __name__ == "__main__":
    unittest.main()
