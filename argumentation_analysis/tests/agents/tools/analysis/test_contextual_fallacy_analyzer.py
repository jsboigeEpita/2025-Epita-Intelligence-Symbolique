"""
Tests unitaires pour le module contextual_fallacy_analyzer.

Ce module contient les tests unitaires pour les classes et fonctions définies dans le module
agents.tools.analysis.contextual_fallacy_analyzer.
"""

import unittest
import json
from unittest.mock import MagicMock, patch, PropertyMock

from argumentation_analysis.agents.tools.analysis.contextual_fallacy_analyzer import ContextualFallacyAnalyzer


class TestContextualFallacyAnalyzer(unittest.TestCase):
    """Tests pour la classe ContextualFallacyAnalyzer."""

    def setUp(self):
        """Initialisation avant chaque test."""
        # Patch pour éviter le chargement réel de la taxonomie
        self.taxonomy_path_patcher = patch('argumentation_analysis.agents.tools.analysis.contextual_fallacy_analyzer.get_taxonomy_path')
        self.mock_get_taxonomy_path = self.taxonomy_path_patcher.start()
        self.mock_get_taxonomy_path.return_value = "mock_taxonomy_path.csv"
        
        self.validate_taxonomy_patcher = patch('argumentation_analysis.agents.tools.analysis.contextual_fallacy_analyzer.validate_taxonomy_file')
        self.mock_validate_taxonomy = self.validate_taxonomy_patcher.start()
        self.mock_validate_taxonomy.return_value = True
        
        # Patch pour pd.read_csv et DataFrame
        self.pandas_patcher = patch('argumentation_analysis.agents.tools.analysis.contextual_fallacy_analyzer.pd')
        self.mock_pandas = self.pandas_patcher.start()
        
        # Créer un mock pour le DataFrame
        self.test_df = MagicMock()
        self.test_df.__len__.return_value = 4
        self.test_df.index = [0, 1, 2, 3]
        self.test_df.columns = ['FK_Parent', 'depth', 'path', 'nom_vulgarisé', 'text_fr', 'description_fr', 'exemple_fr']
        
        # Configurer le comportement du DataFrame pour les accès aux données
        def mock_loc_getitem(key):
            if key == [0]:
                row = MagicMock()
                row.name = 0
                row.get.side_effect = lambda k, default=None: {
                    'path': '0', 'depth': 0, 'nom_vulgarisé': 'Racine',
                    'text_fr': 'Racine des sophismes', 'description_fr': 'Description racine'
                }.get(k, default)
                return [row]
            elif key == [1]:
                row = MagicMock()
                row.name = 1
                row.get.side_effect = lambda k, default=None: {
                    'path': '0.1', 'depth': 1, 'nom_vulgarisé': 'Appel à l\'autorité',
                    'text_fr': 'Description appel à l\'autorité', 'description_fr': 'Description détaillée 1'
                }.get(k, default)
                return [row]
            elif key == [2]:
                row = MagicMock()
                row.name = 2
                row.get.side_effect = lambda k, default=None: {
                    'path': '0.2', 'depth': 1, 'nom_vulgarisé': 'Appel à la popularité',
                    'text_fr': 'Description appel à la popularité', 'description_fr': 'Description détaillée 2'
                }.get(k, default)
                return [row]
            elif key == [3]:
                row = MagicMock()
                row.name = 3
                row.get.side_effect = lambda k, default=None: {
                    'path': '0.1.3', 'depth': 2, 'nom_vulgarisé': 'Appel à l\'émotion',
                    'text_fr': 'Description appel à l\'émotion', 'description_fr': 'Description détaillée 3'
                }.get(k, default)
                return [row]
            else:
                return MagicMock(__len__=lambda: 0)
        
        self.test_df.loc.__getitem__.side_effect = mock_loc_getitem
        
        self.mock_pandas.read_csv.return_value = self.test_df
        
        # Créer l'instance à tester
        self.analyzer = ContextualFallacyAnalyzer()

    def tearDown(self):
        """Nettoyage après chaque test."""
        self.taxonomy_path_patcher.stop()
        self.validate_taxonomy_patcher.stop()
        self.pandas_patcher.stop()

    def test_init(self):
        """Teste l'initialisation de la classe."""
        self.assertIsNotNone(self.analyzer)
        self.assertIsNotNone(self.analyzer.taxonomy_df)
        self.assertEqual(len(self.analyzer.taxonomy_df), 4)

    def test_load_taxonomy(self):
        """Teste le chargement de la taxonomie."""
        # Appeler la méthode à tester
        df = self.analyzer._load_taxonomy()
        
        # Vérifier les résultats
        self.assertIsNotNone(df)
        self.assertEqual(len(df), 4)
        self.mock_get_taxonomy_path.assert_called_once()
        self.mock_validate_taxonomy.assert_called_once()
        self.mock_pandas.read_csv.assert_called_once_with("mock_taxonomy_path.csv", encoding='utf-8')
        
        # Tester avec un chemin personnalisé
        df = self.analyzer._load_taxonomy("custom_path.csv")
        self.mock_pandas.read_csv.assert_called_with("custom_path.csv", encoding='utf-8')
        
        # Tester avec une erreur de validation
        self.mock_validate_taxonomy.return_value = False
        df = self.analyzer._load_taxonomy()
        self.assertIsNone(df)

    def test_determine_context_type(self):
        """Teste la détermination du type de contexte."""
        # Tester différents types de contexte
        self.assertEqual(self.analyzer._determine_context_type("Discours politique sur l'économie"), "politique")
        self.assertEqual(self.analyzer._determine_context_type("Étude scientifique sur le climat"), "scientifique")
        self.assertEqual(self.analyzer._determine_context_type("Publicité commerciale pour un produit"), "commercial")
        self.assertEqual(self.analyzer._determine_context_type("Procès juridique concernant un litige"), "juridique")
        self.assertEqual(self.analyzer._determine_context_type("Conférence académique sur la philosophie"), "académique")
        self.assertEqual(self.analyzer._determine_context_type("Discussion générale"), "général")

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
                "confidence": 0.5
            },
            {
                "fallacy_type": "Appel à la popularité",
                "keyword": "tout le monde",
                "context_text": "Tout le monde sait que...",
                "confidence": 0.5
            },
            {
                "fallacy_type": "Ad hominem",
                "keyword": "personne",
                "context_text": "Cette personne n'est pas crédible...",
                "confidence": 0.5
            }
        ]
        
        # Tester le filtrage dans un contexte scientifique
        filtered_scientific = self.analyzer._filter_by_context(potential_fallacies, "scientifique")
        self.assertEqual(len(filtered_scientific), 3)  # Tous les sophismes sont retournés, mais avec des confiances différentes
        
        # Vérifier que les confiances ont été ajustées
        for fallacy in filtered_scientific:
            if fallacy["fallacy_type"] in ["Appel à l'autorité", "Appel à la popularité"]:
                self.assertEqual(fallacy["confidence"], 0.8)
                self.assertEqual(fallacy["contextual_relevance"], "Élevée")
            else:
                self.assertEqual(fallacy["confidence"], 0.3)
                self.assertEqual(fallacy["contextual_relevance"], "Faible")
        
        # Tester le filtrage dans un contexte politique
        filtered_political = self.analyzer._filter_by_context(potential_fallacies, "politique")
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
        filtered_general = self.analyzer._filter_by_context(potential_fallacies, "général")
        self.assertEqual(len(filtered_general), 3)
        
        # Vérifier que les confiances n'ont pas été modifiées
        for fallacy in filtered_general:
            self.assertEqual(fallacy["confidence"], 0.5)

    def test_analyze_context(self):
        """Teste l'analyse du contexte."""
        # Patch pour les méthodes internes
        with patch.object(self.analyzer, '_determine_context_type') as mock_determine_context, \
             patch.object(self.analyzer, '_identify_potential_fallacies') as mock_identify_fallacies, \
             patch.object(self.analyzer, '_filter_by_context') as mock_filter_by_context:
            
            # Configurer les mocks
            mock_determine_context.return_value = "scientifique"
            mock_identify_fallacies.return_value = [
                {
                    "fallacy_type": "Appel à l'autorité",
                    "keyword": "expert",
                    "context_text": "Les experts affirment que...",
                    "confidence": 0.5
                }
            ]
            mock_filter_by_context.return_value = [
                {
                    "fallacy_type": "Appel à l'autorité",
                    "keyword": "expert",
                    "context_text": "Les experts affirment que...",
                    "confidence": 0.8,
                    "contextual_relevance": "Élevée"
                }
            ]
            
            # Appeler la méthode à tester
            text = "Les experts affirment que ce produit est sûr et efficace."
            context = "Étude scientifique sur l'efficacité d'un médicament"
            result = self.analyzer.analyze_context(text, context)
            
            # Vérifier les résultats
            self.assertEqual(result["context_type"], "scientifique")
            self.assertEqual(result["potential_fallacies_count"], 1)
            self.assertEqual(result["contextual_fallacies_count"], 1)
            self.assertEqual(len(result["contextual_fallacies"]), 1)
            self.assertEqual(result["contextual_fallacies"][0]["fallacy_type"], "Appel à l'autorité")
            self.assertEqual(result["contextual_fallacies"][0]["confidence"], 0.8)
            
            # Vérifier que les méthodes internes ont été appelées correctement
            mock_determine_context.assert_called_once_with(context)
            mock_identify_fallacies.assert_called_once_with(text)
            mock_filter_by_context.assert_called_once_with(mock_identify_fallacies.return_value, "scientifique")

    def test_identify_contextual_fallacies(self):
        """Teste l'identification des sophismes contextuels."""
        # Patch pour la méthode analyze_context
        with patch.object(self.analyzer, 'analyze_context') as mock_analyze_context:
            
            # Configurer le mock
            mock_analyze_context.return_value = {
                "context_type": "scientifique",
                "potential_fallacies_count": 2,
                "contextual_fallacies_count": 2,
                "contextual_fallacies": [
                    {
                        "fallacy_type": "Appel à l'autorité",
                        "keyword": "expert",
                        "context_text": "Les experts affirment que...",
                        "confidence": 0.8,
                        "contextual_relevance": "Élevée"
                    },
                    {
                        "fallacy_type": "Appel à la popularité",
                        "keyword": "tout le monde",
                        "context_text": "Tout le monde sait que...",
                        "confidence": 0.3,
                        "contextual_relevance": "Faible"
                    }
                ]
            }
            
            # Appeler la méthode à tester
            argument = "Les experts affirment que ce produit est sûr. Tout le monde sait que c'est le meilleur."
            context = "Étude scientifique"
            result = self.analyzer.identify_contextual_fallacies(argument, context)
            
            # Vérifier les résultats
            self.assertEqual(len(result), 1)  # Seul le sophisme avec confiance >= 0.5 est retourné
            self.assertEqual(result[0]["fallacy_type"], "Appel à l'autorité")
            self.assertEqual(result[0]["confidence"], 0.8)
            
            # Vérifier que la méthode analyze_context a été appelée correctement
            mock_analyze_context.assert_called_once_with(argument, context)

    def test_get_contextual_fallacy_examples(self):
        """Teste la récupération d'exemples de sophismes contextuels."""
        # Tester avec un sophisme et un contexte existants
        examples = self.analyzer.get_contextual_fallacy_examples("Appel à l'autorité", "politique")
        self.assertGreaterEqual(len(examples), 1)
        self.assertIsInstance(examples[0], str)
        
        # Tester avec un sophisme existant mais un contexte inexistant
        examples = self.analyzer.get_contextual_fallacy_examples("Appel à l'autorité", "inexistant")
        self.assertEqual(len(examples), 1)
        self.assertEqual(examples[0], "Aucun exemple disponible pour ce type de sophisme dans ce contexte.")
        
        # Tester avec un sophisme inexistant
        examples = self.analyzer.get_contextual_fallacy_examples("Sophisme inexistant", "politique")
        self.assertEqual(len(examples), 1)
        self.assertEqual(examples[0], "Aucun exemple disponible pour ce type de sophisme dans ce contexte.")


if __name__ == "__main__":
    unittest.main()