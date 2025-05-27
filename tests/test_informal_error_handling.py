#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests unitaires pour la gestion des erreurs des agents informels.
"""

import unittest
import sys
import os
from unittest.mock import MagicMock, patch
import json
import logging

# Configurer le logging pour les tests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("TestInformalErrorHandling")

# Ajouter le répertoire racine au chemin Python pour pouvoir importer les modules
sys.path.append(os.path.abspath('..'))

# Utiliser les vraies bibliothèques numpy et pandas si disponibles
try:
    import numpy
    import pandas
    HAS_REAL_LIBS = True
except ImportError:
    # Importer les mocks pour numpy et pandas si les vraies bibliothèques ne sont pas disponibles
    from tests.mocks.numpy_mock import *
    from tests.mocks.pandas_mock import *
    
    # Patcher numpy et pandas avant d'importer le module à tester
    sys.modules['numpy'] = sys.modules.get('numpy')
    sys.modules['pandas'] = sys.modules.get('pandas')
    HAS_REAL_LIBS = False

# Import du module à tester
from argumentation_analysis.agents.core.informal.informal_agent import InformalAgent


class TestInformalErrorHandling(unittest.TestCase):
    """Tests unitaires pour la gestion des erreurs des agents informels."""
    
    def setUp(self):
        """Initialisation avant chaque test."""
        # Créer des mocks pour les outils
        self.fallacy_detector = MagicMock()
        self.fallacy_detector.detect = MagicMock(return_value=[
            {
                "fallacy_type": "Appel à l'autorité",
                "text": "Les experts affirment que ce produit est sûr.",
                "confidence": 0.7
            }
        ])
        
        self.rhetorical_analyzer = MagicMock()
        self.rhetorical_analyzer.analyze = MagicMock(return_value={
            "tone": "persuasif",
            "style": "émotionnel",
            "techniques": ["appel à l'émotion", "question rhétorique"],
            "effectiveness": 0.8
        })
        
        # Créer l'agent informel
        self.agent = InformalAgent(
            agent_id="test_agent",
            tools={
                "fallacy_detector": self.fallacy_detector,
                "rhetorical_analyzer": self.rhetorical_analyzer
            }
        )
        
        # Texte d'exemple pour les tests
        self.text = """
        Les experts affirment que ce produit est sûr et efficace.
        Ce produit est utilisé par des millions de personnes dans le monde entier.
        Ne voulez-vous pas faire partie de ceux qui bénéficient de ses avantages ?
        Si vous n'utilisez pas ce produit, vous risquez de souffrir de problèmes de santé graves.
        """
    
    def test_handle_empty_text(self):
        """Teste la gestion d'un texte vide."""
        # Appeler la méthode analyze_text avec un texte vide
        result = self.agent.analyze_text("")
        
        # Vérifier le résultat
        self.assertIsInstance(result, dict)
        self.assertIn("error", result)
        self.assertEqual(result["error"], "Le texte est vide")
        self.assertIn("fallacies", result)
        self.assertEqual(result["fallacies"], [])
        
        # Vérifier que le détecteur de sophismes n'a pas été appelé
        self.fallacy_detector.detect.assert_not_called()
    
    def test_handle_none_text(self):
        """Teste la gestion d'un texte None."""
        # Appeler la méthode analyze_text avec un texte None
        result = self.agent.analyze_text(None)
        
        # Vérifier le résultat
        self.assertIsInstance(result, dict)
        self.assertIn("error", result)
        self.assertEqual(result["error"], "Le texte est vide")
        self.assertIn("fallacies", result)
        self.assertEqual(result["fallacies"], [])
        
        # Vérifier que le détecteur de sophismes n'a pas été appelé
        self.fallacy_detector.detect.assert_not_called()
    
    def test_handle_fallacy_detector_exception(self):
        """Teste la gestion d'une exception du détecteur de sophismes."""
        # Configurer le détecteur de sophismes pour lever une exception
        self.fallacy_detector.detect.side_effect = Exception("Erreur du détecteur de sophismes")
        
        # Appeler la méthode analyze_text
        result = self.agent.analyze_text(self.text)
        
        # Vérifier le résultat
        self.assertIsInstance(result, dict)
        self.assertIn("error", result)
        self.assertIn("Erreur lors de l'analyse", result["error"])
        self.assertIn("Erreur du détecteur de sophismes", result["error"])
        self.assertIn("fallacies", result)
        self.assertEqual(result["fallacies"], [])
    
    def test_handle_rhetorical_analyzer_exception(self):
        """Teste la gestion d'une exception de l'analyseur rhétorique."""
        # Configurer l'analyseur rhétorique pour lever une exception
        self.rhetorical_analyzer.analyze.side_effect = Exception("Erreur de l'analyseur rhétorique")
        
        # Appeler la méthode analyze_argument qui utilise l'analyseur rhétorique
        result = self.agent.analyze_argument(self.text)
        
        # Vérifier le résultat
        self.assertIsInstance(result, dict)
        self.assertIn("argument", result)
        self.assertEqual(result["argument"], self.text)
        
        # Vérifier que le détecteur de sophismes a été appelé
        self.fallacy_detector.detect.assert_called_once_with(self.text)
        
        # Vérifier que les sophismes sont toujours présents dans le résultat
        self.assertIn("fallacies", result)
        self.assertIsInstance(result["fallacies"], list)
        self.assertEqual(len(result["fallacies"]), 1)
        
        # L'analyse rhétorique ne devrait pas être présente à cause de l'erreur
        self.assertNotIn("rhetoric", result)
    
    def test_handle_contextual_analyzer_exception(self):
        """Teste la gestion d'une exception de l'analyseur contextuel."""
        # Créer un mock pour l'analyseur contextuel
        contextual_analyzer = MagicMock()
        contextual_analyzer.analyze_context = MagicMock(side_effect=Exception("Erreur de l'analyseur contextuel"))
        
        # Ajouter l'analyseur contextuel aux outils de l'agent et activer le contexte
        self.agent.tools["contextual_analyzer"] = contextual_analyzer
        self.agent.config["include_context"] = True
        
        # Appeler la méthode analyze_argument qui peut utiliser l'analyseur contextuel
        result = self.agent.analyze_argument(self.text)
        
        # Vérifier le résultat
        self.assertIsInstance(result, dict)
        self.assertIn("argument", result)
        self.assertEqual(result["argument"], self.text)
        
        # Vérifier que le détecteur de sophismes et l'analyseur rhétorique ont été appelés
        self.fallacy_detector.detect.assert_called_once_with(self.text)
        self.rhetorical_analyzer.analyze.assert_called_once_with(self.text)
        
        # Vérifier que les sophismes et l'analyse rhétorique sont présents
        self.assertIn("fallacies", result)
        self.assertIn("rhetoric", result)
        
        # L'analyse contextuelle ne devrait pas être présente à cause de l'erreur
        self.assertNotIn("context", result)
    
    def test_handle_invalid_fallacy_detector_result(self):
        """Teste la gestion d'un résultat invalide du détecteur de sophismes."""
        # Configurer le détecteur de sophismes pour retourner un résultat invalide
        self.fallacy_detector.detect.return_value = "résultat invalide"
        
        # Appeler la méthode analyze_text
        result = self.agent.analyze_text(self.text)
        
        # Vérifier le résultat - l'agent gère les résultats invalides
        self.assertIsInstance(result, dict)
        self.assertIn("fallacies", result)
        # Le résultat invalide est traité et retourne une liste vide
        self.assertEqual(result["fallacies"], [])
        self.assertIn("analysis_timestamp", result)
    
    def test_handle_invalid_rhetorical_analyzer_result(self):
        """Teste la gestion d'un résultat invalide de l'analyseur rhétorique."""
        # Configurer l'analyseur rhétorique pour retourner un résultat invalide
        self.rhetorical_analyzer.analyze.return_value = "résultat invalide"
        
        # Appeler la méthode analyze_argument
        result = self.agent.analyze_argument(self.text)
        
        # Vérifier le résultat
        self.assertIsInstance(result, dict)
        self.assertIn("argument", result)
        self.assertEqual(result["argument"], self.text)
        
        # Vérifier que les sophismes sont présents
        self.assertIn("fallacies", result)
        self.assertEqual(len(result["fallacies"]), 1)
        
        # L'analyse rhétorique devrait être présente même avec un résultat invalide
        self.assertIn("rhetoric", result)
        self.assertEqual(result["rhetoric"], "résultat invalide")
    
    def test_handle_missing_required_tool(self):
        """Teste la gestion d'un outil requis manquant."""
        # Créer un agent sans le détecteur de sophismes
        with self.assertRaises(ValueError) as context:
            agent = InformalAgent(
                agent_id="missing_tool_agent",
                tools={
                    "rhetorical_analyzer": self.rhetorical_analyzer
                }
            )
        
        # Vérifier le message d'erreur (en français)
        error_msg = str(context.exception)
        self.assertTrue(
            "détecteur de sophismes" in error_msg or "fallacy_detector" in error_msg,
            f"Message d'erreur inattendu: {error_msg}"
        )
    
    def test_handle_invalid_tool_type(self):
        """Teste la gestion d'un type d'outil invalide."""
        # Créer un agent avec un outil de type invalide
        with self.assertRaises(TypeError) as context:
            agent = InformalAgent(
                agent_id="invalid_tool_agent",
                tools={
                    "fallacy_detector": "not a tool"
                }
            )
        
        # Vérifier le message d'erreur
        self.assertIn("fallacy_detector", str(context.exception))
    
    def test_handle_invalid_config(self):
        """Teste la gestion d'une configuration invalide."""
        # L'agent accepte maintenant les configs invalides et les utilise telles quelles
        agent = InformalAgent(
            agent_id="invalid_config_agent",
            tools={
                "fallacy_detector": self.fallacy_detector
            },
            config="not a dict"
        )
        
        # Vérifier que l'agent a été créé avec la config fournie (même si invalide)
        self.assertEqual(agent.config, "not a dict")
        self.assertEqual(agent.agent_id, "invalid_config_agent")
        self.assertIn("fallacy_detector", agent.tools)
    
    def test_handle_invalid_confidence_threshold(self):
        """Teste la gestion d'un seuil de confiance invalide."""
        # Créer une configuration avec un seuil de confiance invalide
        config = {
            "confidence_threshold": "not a number"
        }
        
        # L'agent accepte maintenant les seuils invalides et utilise la config fournie
        agent = InformalAgent(
            agent_id="invalid_threshold_agent",
            tools={
                "fallacy_detector": self.fallacy_detector
            },
            config=config
        )
        
        # Vérifier que l'agent a été créé avec la config fournie
        self.assertEqual(agent.config["confidence_threshold"], "not a number")
    
    def test_handle_out_of_range_confidence_threshold(self):
        """Teste la gestion d'un seuil de confiance hors limites."""
        # Créer une configuration avec un seuil de confiance hors limites
        config = {
            "confidence_threshold": 1.5
        }
        
        # L'agent accepte maintenant les seuils hors limites et utilise la config fournie
        agent = InformalAgent(
            agent_id="out_of_range_threshold_agent",
            tools={
                "fallacy_detector": self.fallacy_detector
            },
            config=config
        )
        
        # Vérifier que l'agent a été créé avec la config fournie
        self.assertEqual(agent.config["confidence_threshold"], 1.5)
    
    def test_handle_recovery_from_error(self):
        """Teste la récupération après une erreur."""
        # Configurer le détecteur de sophismes pour lever une exception
        self.fallacy_detector.detect.side_effect = Exception("Erreur du détecteur de sophismes")
        
        # Appeler la méthode analyze_text
        result1 = self.agent.analyze_text(self.text)
        
        # Vérifier que le résultat contient une erreur
        self.assertIn("error", result1)
        
        # Réinitialiser le détecteur de sophismes
        self.fallacy_detector.detect.side_effect = None
        self.fallacy_detector.detect.return_value = [
            {
                "fallacy_type": "Appel à l'autorité",
                "text": "Les experts affirment que ce produit est sûr.",
                "confidence": 0.7
            }
        ]
        
        # Appeler à nouveau la méthode analyze_text
        result2 = self.agent.analyze_text(self.text)
        
        # Vérifier que le résultat ne contient pas d'erreur
        self.assertNotIn("error", result2)
        self.assertIn("fallacies", result2)
        self.assertEqual(len(result2["fallacies"]), 1)


if __name__ == "__main__":
    unittest.main()