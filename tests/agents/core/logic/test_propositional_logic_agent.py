# -*- coding: utf-8 -*-
# tests/agents/core/logic/test_propositional_logic_agent.py
"""
Tests unitaires pour la classe PropositionalLogicAgent.
"""

import unittest
from unittest.mock import MagicMock, patch, PropertyMock

from semantic_kernel import Kernel
from semantic_kernel.functions import KernelFunction

from argumentation_analysis.agents.core.logic.propositional_logic_agent import PropositionalLogicAgent
from argumentation_analysis.agents.core.logic.belief_set import PropositionalBeliefSet
from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge


class TestPropositionalLogicAgent(unittest.TestCase):
    """Tests pour la classe PropositionalLogicAgent."""
    
    def setUp(self):
        """Initialisation avant chaque test."""
        # Mock du kernel
        self.kernel = MagicMock(spec=Kernel)
        self.kernel.plugins = {}
        
        # Mock des fonctions du kernel
        self.text_to_pl_function = MagicMock()
        self.text_to_pl_function.invoke.return_value = MagicMock(result="a => b")
        
        self.generate_queries_function = MagicMock()
        self.generate_queries_function.invoke.return_value = MagicMock(result="a\nb\na => b")
        
        self.interpret_function = MagicMock()
        self.interpret_function.invoke.return_value = MagicMock(result="Interprétation des résultats")
        
        self.execute_query_function = MagicMock()
        self.execute_query_function.invoke.return_value = MagicMock(result="Tweety Result: Query 'a => b' is ACCEPTED (True).")
        
        # Configuration du mock du plugin
        self.kernel.plugins = {
            "PLAnalyzer": {
                "semantic_TextToPLBeliefSet": self.text_to_pl_function,
                "semantic_GeneratePLQueries": self.generate_queries_function,
                "semantic_InterpretPLResult": self.interpret_function,
                "execute_pl_query": self.execute_query_function
            }
        }
        
        # Mock de TweetyBridge
        self.tweety_bridge_patcher = patch('argumentation_analysis.agents.core.logic.propositional_logic_agent.TweetyBridge')
        self.mock_tweety_bridge_class = self.tweety_bridge_patcher.start()
        self.mock_tweety_bridge = MagicMock(spec=TweetyBridge)
        self.mock_tweety_bridge_class.return_value = self.mock_tweety_bridge
        self.mock_tweety_bridge.is_jvm_ready.return_value = True
        self.mock_tweety_bridge.validate_belief_set.return_value = (True, "Ensemble de croyances valide")
        self.mock_tweety_bridge.validate_formula.return_value = (True, "Formule valide")
        
        # Création de l'agent
        self.agent = PropositionalLogicAgent(self.kernel)
    
    def tearDown(self):
        """Nettoyage après chaque test."""
        self.tweety_bridge_patcher.stop()
    
    def test_initialization(self):
        """Test de l'initialisation de l'agent."""
        self.assertEqual(self.agent.name, "PropositionalLogicAgent")
        self.assertEqual(self.agent.kernel, self.kernel)
        self.mock_tweety_bridge_class.assert_called_once()
    
    def test_setup_kernel(self):
        """Test de la configuration du kernel."""
        llm_service = MagicMock()
        llm_service.service_id = "test_service"
        
        # Mock pour get_prompt_execution_settings_from_service_id
        self.kernel.get_prompt_execution_settings_from_service_id.return_value = {"temperature": 0.7}
        
        self.agent.setup_kernel(llm_service)
        
        # Vérifier que la JVM est prête
        self.mock_tweety_bridge.is_jvm_ready.assert_called_once()
        
        # Vérifier que le plugin a été ajouté
        self.kernel.add_plugin.assert_called_once()
        
        # Vérifier que les fonctions sémantiques ont été ajoutées
        self.assertEqual(self.kernel.add_function.call_count, 3)
    
    def test_setup_kernel_jvm_not_ready(self):
        """Test de la configuration du kernel lorsque la JVM n'est pas prête."""
        self.mock_tweety_bridge.is_jvm_ready.return_value = False
        
        self.agent.setup_kernel(None)
        
        # Vérifier que la JVM est prête
        self.mock_tweety_bridge.is_jvm_ready.assert_called_once()
        
        # Vérifier que le plugin n'a pas été ajouté
        self.kernel.add_plugin.assert_not_called()
        
        # Vérifier que les fonctions sémantiques n'ont pas été ajoutées
        self.kernel.add_function.assert_not_called()
    
    def test_text_to_belief_set_success(self):
        """Test de la conversion de texte en ensemble de croyances avec succès."""
        belief_set, message = self.agent.text_to_belief_set("Texte de test")
        
        # Vérifier que la fonction sémantique a été appelée
        self.text_to_pl_function.invoke.assert_called_once_with("Texte de test")
        
        # Vérifier que l'ensemble de croyances a été validé
        self.mock_tweety_bridge.validate_belief_set.assert_called_once()
        
        # Vérifier le résultat
        self.assertIsInstance(belief_set, PropositionalBeliefSet)
        self.assertEqual(belief_set.content, "a => b")
        self.assertEqual(message, "Conversion réussie")
    
    def test_text_to_belief_set_empty_result(self):
        """Test de la conversion de texte en ensemble de croyances avec résultat vide."""
        self.text_to_pl_function.invoke.return_value = MagicMock(result="")
        
        belief_set, message = self.agent.text_to_belief_set("Texte de test")
        
        # Vérifier que la fonction sémantique a été appelée
        self.text_to_pl_function.invoke.assert_called_once_with("Texte de test")
        
        # Vérifier que l'ensemble de croyances n'a pas été validé
        self.mock_tweety_bridge.validate_belief_set.assert_not_called()
        
        # Vérifier le résultat
        self.assertIsNone(belief_set)
        self.assertEqual(message, "La conversion a produit un ensemble de croyances vide")
    
    def test_text_to_belief_set_invalid_belief_set(self):
        """Test de la conversion de texte en ensemble de croyances avec ensemble invalide."""
        self.mock_tweety_bridge.validate_belief_set.return_value = (False, "Erreur de syntaxe")
        
        belief_set, message = self.agent.text_to_belief_set("Texte de test")
        
        # Vérifier que la fonction sémantique a été appelée
        self.text_to_pl_function.invoke.assert_called_once_with("Texte de test")
        
        # Vérifier que l'ensemble de croyances a été validé
        self.mock_tweety_bridge.validate_belief_set.assert_called_once()
        
        # Vérifier le résultat
        self.assertIsNone(belief_set)
        self.assertEqual(message, "Ensemble de croyances invalide: Erreur de syntaxe")
    
    def test_generate_queries(self):
        """Test de la génération de requêtes."""
        belief_set = PropositionalBeliefSet("a => b")
        
        queries = self.agent.generate_queries("Texte de test", belief_set)
        
        # Vérifier que la fonction sémantique a été appelée
        self.generate_queries_function.invoke.assert_called_once_with(
            input="Texte de test",
            belief_set="a => b"
        )
        
        # Vérifier que les requêtes ont été validées
        self.assertEqual(self.mock_tweety_bridge.validate_formula.call_count, 3)
        
        # Vérifier le résultat
        self.assertEqual(queries, ["a", "b", "a => b"])
    
    def test_generate_queries_with_invalid_query(self):
        """Test de la génération de requêtes avec une requête invalide."""
        belief_set = PropositionalBeliefSet("a => b")
        
        # Configurer le mock pour rejeter la deuxième requête
        self.mock_tweety_bridge.validate_formula.side_effect = [
            (True, "Formule valide"),
            (False, "Erreur de syntaxe"),
            (True, "Formule valide")
        ]
        
        queries = self.agent.generate_queries("Texte de test", belief_set)
        
        # Vérifier que la fonction sémantique a été appelée
        self.generate_queries_function.invoke.assert_called_once_with(
            input="Texte de test",
            belief_set="a => b"
        )
        
        # Vérifier que les requêtes ont été validées
        self.assertEqual(self.mock_tweety_bridge.validate_formula.call_count, 3)
        
        # Vérifier le résultat (la deuxième requête doit être filtrée)
        self.assertEqual(queries, ["a", "a => b"])
    
    def test_execute_query_accepted(self):
        """Test de l'exécution d'une requête acceptée."""
        belief_set = PropositionalBeliefSet("a => b")
        
        result, message = self.agent.execute_query(belief_set, "a => b")
        
        # Vérifier que la fonction native a été appelée
        self.execute_query_function.invoke.assert_called_once_with(
            belief_set_content="a => b",
            query_string="a => b"
        )
        
        # Vérifier le résultat
        self.assertTrue(result)
        self.assertEqual(message, "Tweety Result: Query 'a => b' is ACCEPTED (True).")
    
    def test_execute_query_rejected(self):
        """Test de l'exécution d'une requête rejetée."""
        belief_set = PropositionalBeliefSet("a => b")
        self.execute_query_function.invoke.return_value = MagicMock(
            result="Tweety Result: Query 'a => b' is REJECTED (False)."
        )
        
        result, message = self.agent.execute_query(belief_set, "a => b")
        
        # Vérifier que la fonction native a été appelée
        self.execute_query_function.invoke.assert_called_once_with(
            belief_set_content="a => b",
            query_string="a => b"
        )
        
        # Vérifier le résultat
        self.assertFalse(result)
        self.assertEqual(message, "Tweety Result: Query 'a => b' is REJECTED (False).")
    
    def test_execute_query_error(self):
        """Test de l'exécution d'une requête avec erreur."""
        belief_set = PropositionalBeliefSet("a => b")
        self.execute_query_function.invoke.return_value = MagicMock(
            result="FUNC_ERROR: Erreur de syntaxe"
        )
        
        result, message = self.agent.execute_query(belief_set, "a => b")
        
        # Vérifier que la fonction native a été appelée
        self.execute_query_function.invoke.assert_called_once_with(
            belief_set_content="a => b",
            query_string="a => b"
        )
        
        # Vérifier le résultat
        self.assertIsNone(result)
        self.assertEqual(message, "FUNC_ERROR: Erreur de syntaxe")
    
    def test_interpret_results(self):
        """Test de l'interprétation des résultats."""
        belief_set = PropositionalBeliefSet("a => b")
        queries = ["a", "b", "a => b"]
        results = [
            "Tweety Result: Query 'a' is ACCEPTED (True).",
            "Tweety Result: Query 'b' is REJECTED (False).",
            "Tweety Result: Query 'a => b' is ACCEPTED (True)."
        ]
        
        interpretation = self.agent.interpret_results("Texte de test", belief_set, queries, results)
        
        # Vérifier que la fonction sémantique a été appelée
        self.interpret_function.invoke.assert_called_once_with(
            input="Texte de test",
            belief_set="a => b",
            queries="a\nb\na => b",
            tweety_result="Tweety Result: Query 'a' is ACCEPTED (True).\nTweety Result: Query 'b' is REJECTED (False).\nTweety Result: Query 'a => b' is ACCEPTED (True)."
        )
        
        # Vérifier le résultat
        self.assertEqual(interpretation, "Interprétation des résultats")
    
    def test_create_belief_set_from_data(self):
        """Test de la création d'un ensemble de croyances à partir de données."""
        belief_set_data = {
            "logic_type": "propositional",
            "content": "a => b"
        }
        
        belief_set = self.agent._create_belief_set_from_data(belief_set_data)
        
        # Vérifier le résultat
        self.assertIsInstance(belief_set, PropositionalBeliefSet)
        self.assertEqual(belief_set.content, "a => b")
        self.assertEqual(belief_set.logic_type, "propositional")


if __name__ == "__main__":
    unittest.main()