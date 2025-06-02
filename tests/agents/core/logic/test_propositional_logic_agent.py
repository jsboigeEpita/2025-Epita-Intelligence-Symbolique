# -*- coding: utf-8 -*-
# tests/agents/core/logic/test_propositional_logic_agent.py
"""
Tests unitaires pour la classe PropositionalLogicAgent.
"""

import unittest
import asyncio # Ajouté pour les tests async
from unittest.mock import MagicMock, patch, AsyncMock # AsyncMock ajouté

from semantic_kernel import Kernel
from semantic_kernel.functions.kernel_arguments import KernelArguments # Ajouté

from argumentation_analysis.agents.core.logic.propositional_logic_agent import PropositionalLogicAgent
from argumentation_analysis.agents.core.logic.belief_set import PropositionalBeliefSet, BeliefSet
from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge
from argumentation_analysis.agents.core.pl.pl_definitions import PL_AGENT_INSTRUCTIONS


class TestPropositionalLogicAgent(unittest.TestCase):
    """Tests pour la classe PropositionalLogicAgent."""

    def setUp(self):
        """Initialisation avant chaque test."""
        self.kernel = MagicMock(spec=Kernel)
        # Mock pour kernel.invoke qui sera utilisé par les méthodes de l'agent
        self.kernel.invoke = AsyncMock()
        self.kernel.get_prompt_execution_settings_from_service_id = MagicMock(return_value={"temperature": 0.7})
        self.kernel.add_function = MagicMock() # Pour setup_agent_components

        # Patch de TweetyBridge avant l'initialisation de l'agent
        self.tweety_bridge_patcher = patch('argumentation_analysis.agents.core.logic.propositional_logic_agent.TweetyBridge')
        self.mock_tweety_bridge_class = self.tweety_bridge_patcher.start()
        
        self.mock_tweety_bridge_instance = MagicMock(spec=TweetyBridge)
        self.mock_tweety_bridge_class.return_value = self.mock_tweety_bridge_instance
        self.mock_tweety_bridge_instance.is_jvm_ready.return_value = True
        self.mock_tweety_bridge_instance.validate_belief_set.return_value = (True, "Ensemble de croyances valide")
        self.mock_tweety_bridge_instance.validate_formula.return_value = (True, "Formule valide")
        self.mock_tweety_bridge_instance.execute_query.return_value = (True, "Tweety Result: Query 'a => b' is ACCEPTED (True).")

        # Création de l'agent
        self.agent_name = "TestPLAgent"
        self.agent = PropositionalLogicAgent(self.kernel, agent_name=self.agent_name)
        
        # Appel explicite à setup_agent_components, car c'est maintenant une étape séparée
        # Pour les tests unitaires, llm_service_id peut être une chaîne factice.
        self.llm_service_id = "test_llm_service"
        self.agent.setup_agent_components(self.llm_service_id)

    def tearDown(self):
        """Nettoyage après chaque test."""
        self.tweety_bridge_patcher.stop()

    def test_initialization_and_setup(self):
        """Test de l'initialisation et de la configuration de l'agent."""
        self.assertEqual(self.agent.name, self.agent_name)
        self.assertEqual(self.agent.sk_kernel, self.kernel)
        self.assertEqual(self.agent.logic_type, "PL")
        self.assertEqual(self.agent.system_prompt, PL_AGENT_INSTRUCTIONS)
        
        # Vérifier que TweetyBridge a été initialisé dans setup_agent_components
        self.mock_tweety_bridge_class.assert_called_once_with(logic_type="pl")
        self.mock_tweety_bridge_instance.is_jvm_ready.assert_called_once()
        
        # Vérifier que les fonctions sémantiques ont été ajoutées
        # Le nombre exact dépend des prompts définis dans pl.prompts
        self.assertTrue(self.kernel.add_function.call_count >= 3)
        # Vérifier que get_prompt_execution_settings_from_service_id a été appelé
        self.kernel.get_prompt_execution_settings_from_service_id.assert_called_with(self.llm_service_id)


    async def test_text_to_belief_set_success(self):
        """Test de la conversion de texte en ensemble de croyances avec succès."""
        self.kernel.invoke.return_value = MagicMock(result="a => b") # Simule le retour de SK
        
        belief_set, message = await self.agent.text_to_belief_set("Texte de test")
        
        self.kernel.invoke.assert_called_once()
        args, kwargs = self.kernel.invoke.call_args
        self.assertEqual(kwargs['plugin_name'], self.agent_name)
        self.assertEqual(kwargs['function_name'], "TextToPLBeliefSet")
        self.assertIsInstance(kwargs['arguments'], KernelArguments)
        self.assertEqual(kwargs['arguments']['input'], "Texte de test")
        
        self.mock_tweety_bridge_instance.validate_belief_set.assert_called_once_with("a => b", logic_type="PL")
        
        self.assertIsInstance(belief_set, PropositionalBeliefSet)
        self.assertEqual(belief_set.content, "a => b")
        self.assertEqual(message, "Conversion réussie.")

    async def test_text_to_belief_set_empty_result(self):
        """Test de la conversion de texte en ensemble de croyances avec résultat vide."""
        self.kernel.invoke.return_value = MagicMock(result="")
        
        belief_set, message = await self.agent.text_to_belief_set("Texte de test")
        
        self.kernel.invoke.assert_called_once()
        self.mock_tweety_bridge_instance.validate_belief_set.assert_not_called()
        
        self.assertIsNone(belief_set)
        self.assertEqual(message, "La conversion a produit un ensemble de croyances vide.")

    async def test_text_to_belief_set_invalid_belief_set(self):
        """Test de la conversion de texte en ensemble de croyances avec ensemble invalide."""
        self.kernel.invoke.return_value = MagicMock(result="invalid_pl_syntax {")
        self.mock_tweety_bridge_instance.validate_belief_set.return_value = (False, "Erreur de syntaxe")
        
        belief_set, message = await self.agent.text_to_belief_set("Texte de test")
        
        self.kernel.invoke.assert_called_once()
        self.mock_tweety_bridge_instance.validate_belief_set.assert_called_once_with("invalid_pl_syntax {", logic_type="PL")
        
        self.assertIsNone(belief_set)
        self.assertEqual(message, "Ensemble de croyances invalide: Erreur de syntaxe")

    async def test_generate_queries(self):
        """Test de la génération de requêtes."""
        self.kernel.invoke.return_value = MagicMock(result="a\nb\na => b")
        # validate_formula sera appelé par generate_queries
        self.mock_tweety_bridge_instance.validate_formula.return_value = (True, "Formule valide")
        
        belief_set_obj = PropositionalBeliefSet("x => y")
        
        queries = await self.agent.generate_queries("Texte de test", belief_set_obj)
        
        self.kernel.invoke.assert_called_once()
        args, kwargs = self.kernel.invoke.call_args
        self.assertEqual(kwargs['plugin_name'], self.agent_name)
        self.assertEqual(kwargs['function_name'], "GeneratePLQueries")
        self.assertEqual(kwargs['arguments']['input'], "Texte de test")
        self.assertEqual(kwargs['arguments']['belief_set'], "x => y")

        # validate_formula est appelée pour chaque requête générée
        self.assertEqual(self.mock_tweety_bridge_instance.validate_formula.call_count, 3)
        self.mock_tweety_bridge_instance.validate_formula.assert_any_call(formula_str="a", logic_type="PL")
        
        self.assertEqual(queries, ["a", "b", "a => b"])

    async def test_generate_queries_with_invalid_query(self):
        """Test de la génération de requêtes avec une requête invalide."""
        self.kernel.invoke.return_value = MagicMock(result="a\ninvalid_query {\nc")
        
        # Configurer le mock pour rejeter la deuxième requête
        def validate_side_effect(formula_str, logic_type):
            if formula_str == "invalid_query {":
                return (False, "Erreur de syntaxe")
            return (True, "Formule valide")
        self.mock_tweety_bridge_instance.validate_formula.side_effect = validate_side_effect
        
        belief_set_obj = PropositionalBeliefSet("x => y")
        queries = await self.agent.generate_queries("Texte de test", belief_set_obj)
        
        self.kernel.invoke.assert_called_once()
        self.assertEqual(self.mock_tweety_bridge_instance.validate_formula.call_count, 3)
        self.assertEqual(queries, ["a", "c"])

    def test_execute_query_accepted(self):
        """Test de l'exécution d'une requête acceptée."""
        belief_set_obj = PropositionalBeliefSet("a => b")
        self.mock_tweety_bridge_instance.execute_query.return_value = (True, "Tweety Result: Query 'a => b' is ACCEPTED (True).")
        self.mock_tweety_bridge_instance.validate_formula.return_value = (True, "Formule valide") # Pour la validation interne

        result, message = self.agent.execute_query(belief_set_obj, "a => b")
        
        self.mock_tweety_bridge_instance.validate_formula.assert_called_once_with(formula_str="a => b", logic_type="PL")
        self.mock_tweety_bridge_instance.execute_query.assert_called_once_with(
            belief_set_str="a => b",
            query_str="a => b",
            logic_type="PL"
        )
        
        self.assertTrue(result)
        self.assertEqual(message, "Tweety Result: Query 'a => b' is ACCEPTED (True).")

    def test_execute_query_rejected(self):
        """Test de l'exécution d'une requête rejetée."""
        belief_set_obj = PropositionalBeliefSet("a => b")
        self.mock_tweety_bridge_instance.execute_query.return_value = (False, "Tweety Result: Query 'c' is REJECTED (False).")
        self.mock_tweety_bridge_instance.validate_formula.return_value = (True, "Formule valide")

        result, message = self.agent.execute_query(belief_set_obj, "c")
        
        self.mock_tweety_bridge_instance.validate_formula.assert_called_once_with(formula_str="c", logic_type="PL")
        self.mock_tweety_bridge_instance.execute_query.assert_called_once_with(
            belief_set_str="a => b",
            query_str="c",
            logic_type="PL"
        )
        
        self.assertFalse(result)
        self.assertEqual(message, "Tweety Result: Query 'c' is REJECTED (False).")

    def test_execute_query_error_tweety(self):
        """Test de l'exécution d'une requête avec erreur de Tweety."""
        belief_set_obj = PropositionalBeliefSet("a => b")
        self.mock_tweety_bridge_instance.execute_query.return_value = (None, "FUNC_ERROR: Erreur de syntaxe Tweety")
        self.mock_tweety_bridge_instance.validate_formula.return_value = (True, "Formule valide")

        result, message = self.agent.execute_query(belief_set_obj, "a")
        
        self.mock_tweety_bridge_instance.validate_formula.assert_called_once_with(formula_str="a", logic_type="PL")
        self.mock_tweety_bridge_instance.execute_query.assert_called_once_with(
            belief_set_str="a => b",
            query_str="a",
            logic_type="PL"
        )
        
        self.assertIsNone(result)
        self.assertEqual(message, "FUNC_ERROR: Erreur de syntaxe Tweety")

    def test_execute_query_invalid_formula(self):
        """Test de l'exécution d'une requête avec une formule invalide."""
        belief_set_obj = PropositionalBeliefSet("a => b")
        self.mock_tweety_bridge_instance.validate_formula.return_value = (False, "Syntax Error in query")

        result, message = self.agent.execute_query(belief_set_obj, "invalid_query {")
        
        self.mock_tweety_bridge_instance.validate_formula.assert_called_once_with(formula_str="invalid_query {", logic_type="PL")
        self.mock_tweety_bridge_instance.execute_query.assert_not_called() # Ne doit pas être appelé si la formule est invalide
        
        self.assertIsNone(result)
        self.assertEqual(message, "FUNC_ERROR: Requête invalide: invalid_query {")


    async def test_interpret_results(self):
        """Test de l'interprétation des résultats."""
        self.kernel.invoke.return_value = MagicMock(result="Interprétation finale des résultats")
        
        belief_set_obj = PropositionalBeliefSet("a => b")
        queries_list = ["a", "b", "a => b"]
        results_tuples = [
            (True, "Tweety Result: Query 'a' is ACCEPTED (True)."),
            (False, "Tweety Result: Query 'b' is REJECTED (False)."),
            (True, "Tweety Result: Query 'a => b' is ACCEPTED (True).")
        ]
        
        interpretation = await self.agent.interpret_results("Texte de test", belief_set_obj, queries_list, results_tuples)
        
        self.kernel.invoke.assert_called_once()
        args, kwargs = self.kernel.invoke.call_args
        self.assertEqual(kwargs['plugin_name'], self.agent_name)
        self.assertEqual(kwargs['function_name'], "InterpretPLResults")
        self.assertEqual(kwargs['arguments']['input'], "Texte de test")
        self.assertEqual(kwargs['arguments']['belief_set'], "a => b")
        self.assertEqual(kwargs['arguments']['queries'], "a\nb\na => b")
        expected_tweety_results = "Tweety Result: Query 'a' is ACCEPTED (True).\nTweety Result: Query 'b' is REJECTED (False).\nTweety Result: Query 'a => b' is ACCEPTED (True)."
        self.assertEqual(kwargs['arguments']['tweety_result'], expected_tweety_results)
        
        self.assertEqual(interpretation, "Interprétation finale des résultats")

    def test_validate_formula_valid(self):
        """Test de la validation d'une formule valide."""
        self.mock_tweety_bridge_instance.validate_formula.return_value = (True, "Formule valide")
        is_valid = self.agent.validate_formula("a => b")
        self.assertTrue(is_valid)
        self.mock_tweety_bridge_instance.validate_formula.assert_called_once_with(formula_str="a => b", logic_type="PL")

    def test_validate_formula_invalid(self):
        """Test de la validation d'une formule invalide."""
        self.mock_tweety_bridge_instance.validate_formula.return_value = (False, "Erreur de syntaxe")
        is_valid = self.agent.validate_formula("a => (b")
        self.assertFalse(is_valid)
        self.mock_tweety_bridge_instance.validate_formula.assert_called_once_with(formula_str="a => (b", logic_type="PL")

# Wrapper pour exécuter les tests async avec unittest
def async_test(f):
    def wrapper(*args, **kwargs):
        asyncio.run(f(*args, **kwargs))
    return wrapper

# Appliquer le décorateur aux méthodes de test async
TestPropositionalLogicAgent.test_text_to_belief_set_success = async_test(TestPropositionalLogicAgent.test_text_to_belief_set_success)
TestPropositionalLogicAgent.test_text_to_belief_set_empty_result = async_test(TestPropositionalLogicAgent.test_text_to_belief_set_empty_result)
TestPropositionalLogicAgent.test_text_to_belief_set_invalid_belief_set = async_test(TestPropositionalLogicAgent.test_text_to_belief_set_invalid_belief_set)
TestPropositionalLogicAgent.test_generate_queries = async_test(TestPropositionalLogicAgent.test_generate_queries)
TestPropositionalLogicAgent.test_generate_queries_with_invalid_query = async_test(TestPropositionalLogicAgent.test_generate_queries_with_invalid_query)
TestPropositionalLogicAgent.test_interpret_results = async_test(TestPropositionalLogicAgent.test_interpret_results)


if __name__ == "__main__":
    unittest.main()