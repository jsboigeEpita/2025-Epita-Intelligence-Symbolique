# -*- coding: utf-8 -*-
# tests/agents/core/logic/test_propositional_logic_agent.py
"""
Tests unitaires pour la classe PropositionalLogicAgent.
"""

import unittest
import asyncio 
from unittest.mock import MagicMock, patch, AsyncMock 

from semantic_kernel import Kernel
from semantic_kernel.functions.kernel_arguments import KernelArguments 

from argumentation_analysis.agents.core.logic.propositional_logic_agent import PropositionalLogicAgent
from argumentation_analysis.agents.core.logic.belief_set import PropositionalBeliefSet, BeliefSet
from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge
from argumentation_analysis.agents.core.pl.pl_definitions import PL_AGENT_INSTRUCTIONS


class TestPropositionalLogicAgent(unittest.TestCase):
    """Tests pour la classe PropositionalLogicAgent."""

    def setUp(self):
        """Initialisation avant chaque test."""
        self.kernel = MagicMock(spec=Kernel)
        self.kernel.invoke = AsyncMock() 
        self.kernel.get_prompt_execution_settings_from_service_id = MagicMock(return_value={"temperature": 0.7})
        self.kernel.add_function = MagicMock() 

        self.tweety_bridge_patcher = patch('argumentation_analysis.agents.core.logic.propositional_logic_agent.TweetyBridge')
        self.mock_tweety_bridge_class = self.tweety_bridge_patcher.start()
        
        self.mock_tweety_bridge_instance = MagicMock(spec=TweetyBridge)
        self.mock_tweety_bridge_class.return_value = self.mock_tweety_bridge_instance
        self.mock_tweety_bridge_instance.is_jvm_ready.return_value = True
        self.mock_tweety_bridge_instance.validate_belief_set.return_value = (True, "Ensemble de croyances valide")
        self.mock_tweety_bridge_instance.validate_formula.return_value = (True, "Formule valide")
        # Configurer le mock pour execute_pl_query car c'est la méthode spécifique de TweetyBridge pour PL
        # La méthode réelle retourne une chaîne, pas un tuple.
        self.mock_tweety_bridge_instance.execute_pl_query = MagicMock(return_value="Tweety Result: Query 'a => b' is ACCEPTED (True).")

        self.agent_name = "TestPLAgent"
        self.agent = PropositionalLogicAgent(self.kernel, agent_name=self.agent_name)
        
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
        
        self.mock_tweety_bridge_class.assert_called_once_with()
        # is_jvm_ready is called twice: once in the log info, once in the conditional check
        self.assertEqual(self.mock_tweety_bridge_instance.is_jvm_ready.call_count, 2)
        
        self.assertTrue(self.kernel.add_function.call_count >= 3)
        self.kernel.get_prompt_execution_settings_from_service_id.assert_called_with(self.llm_service_id)


    async def test_text_to_belief_set_success(self):
        """Test de la conversion de texte en ensemble de croyances avec succès."""
        mock_sk_result = MagicMock()
        mock_sk_result.__str__.return_value = "a => b" 
        self.kernel.invoke.return_value = mock_sk_result
        
        belief_set, message = await self.agent.text_to_belief_set("Texte de test")
        
        self.kernel.invoke.assert_called_once()
        args, kwargs = self.kernel.invoke.call_args
        self.assertEqual(kwargs['plugin_name'], self.agent_name)
        self.assertEqual(kwargs['function_name'], "TextToPLBeliefSet")
        self.assertIsInstance(kwargs['arguments'], KernelArguments)
        self.assertEqual(kwargs['arguments']['input'], "Texte de test")
        
        self.mock_tweety_bridge_instance.validate_belief_set.assert_called_once_with("a => b")
        
        self.assertIsInstance(belief_set, PropositionalBeliefSet)
        self.assertEqual(belief_set.content, "a => b")
        self.assertEqual(message, "Conversion réussie.")

    async def test_text_to_belief_set_empty_result(self):
        """Test de la conversion de texte en ensemble de croyances avec résultat vide."""
        mock_sk_result = MagicMock()
        mock_sk_result.__str__.return_value = "" 
        self.kernel.invoke.return_value = mock_sk_result
        
        belief_set, message = await self.agent.text_to_belief_set("Texte de test")
        
        self.kernel.invoke.assert_called_once()
        self.mock_tweety_bridge_instance.validate_belief_set.assert_not_called()
        
        self.assertIsNone(belief_set)
        self.assertEqual(message, "La conversion a produit un ensemble de croyances vide.")

    async def test_text_to_belief_set_invalid_belief_set(self):
        """Test de la conversion de texte en ensemble de croyances avec ensemble invalide."""
        mock_sk_result = MagicMock()
        mock_sk_result.__str__.return_value = "invalid_pl_syntax {"
        self.kernel.invoke.return_value = mock_sk_result
        self.mock_tweety_bridge_instance.validate_belief_set.return_value = (False, "Erreur de syntaxe")
        
        belief_set, message = await self.agent.text_to_belief_set("Texte de test")
        
        self.kernel.invoke.assert_called_once()
        self.mock_tweety_bridge_instance.validate_belief_set.assert_called_once_with("invalid_pl_syntax {")
        
        self.assertIsNone(belief_set)
        self.assertEqual(message, "Ensemble de croyances invalide: Erreur de syntaxe")

    async def test_generate_queries(self):
        """Test de la génération de requêtes."""
        mock_sk_result = MagicMock()
        mock_sk_result.__str__.return_value = "a\nb\na => b"
        self.kernel.invoke.return_value = mock_sk_result
        self.mock_tweety_bridge_instance.validate_formula.return_value = (True, "Formule valide")
        
        belief_set_obj = PropositionalBeliefSet("x => y")
        
        queries = await self.agent.generate_queries("Texte de test", belief_set_obj)
        
        self.kernel.invoke.assert_called_once()
        args, kwargs = self.kernel.invoke.call_args
        self.assertEqual(kwargs['plugin_name'], self.agent_name)
        self.assertEqual(kwargs['function_name'], "GeneratePLQueries")
        self.assertEqual(kwargs['arguments']['input'], "Texte de test")
        self.assertEqual(kwargs['arguments']['belief_set'], "x => y")

        self.assertEqual(self.mock_tweety_bridge_instance.validate_formula.call_count, 3)
        self.mock_tweety_bridge_instance.validate_formula.assert_any_call(formula_string="a")
        
        self.assertEqual(queries, ["a", "b", "a => b"])

    async def test_generate_queries_with_invalid_query(self):
        """Test de la génération de requêtes avec une requête invalide."""
        mock_sk_result = MagicMock()
        mock_sk_result.__str__.return_value = "a\ninvalid_query {\nc"
        self.kernel.invoke.return_value = mock_sk_result
        
        def validate_side_effect(formula_string): # Changed signature
            if formula_string == "invalid_query {":
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
        self.mock_tweety_bridge_instance.execute_pl_query.return_value = "Tweety Result: Query 'a => b' is ACCEPTED (True)." # Retourne une chaîne
        self.mock_tweety_bridge_instance.validate_formula.return_value = (True, "Formule valide")

        result, message = self.agent.execute_query(belief_set_obj, "a => b")
        
        self.mock_tweety_bridge_instance.validate_formula.assert_called_once_with(formula_string="a => b")
        self.mock_tweety_bridge_instance.execute_pl_query.assert_called_once_with(
            belief_set_content="a => b", # Corrected parameter name
            query_string="a => b"  # Corrected parameter name
        )
        
        self.assertTrue(result)
        self.assertEqual(message, "Tweety Result: Query 'a => b' is ACCEPTED (True).")

    def test_execute_query_rejected(self):
        """Test de l'exécution d'une requête rejetée."""
        belief_set_obj = PropositionalBeliefSet("a => b")
        self.mock_tweety_bridge_instance.execute_pl_query.return_value = "Tweety Result: Query 'c' is REJECTED (False)." # Retourne une chaîne
        self.mock_tweety_bridge_instance.validate_formula.return_value = (True, "Formule valide")

        result, message = self.agent.execute_query(belief_set_obj, "c")
        
        self.mock_tweety_bridge_instance.validate_formula.assert_called_once_with(formula_string="c")
        self.mock_tweety_bridge_instance.execute_pl_query.assert_called_once_with(
            belief_set_content="a => b", # Corrected parameter name
            query_string="c"  # Corrected parameter name
        )
        
        self.assertFalse(result)
        self.assertEqual(message, "Tweety Result: Query 'c' is REJECTED (False).")

    def test_execute_query_error_tweety(self):
        """Test de l'exécution d'une requête avec erreur de Tweety."""
        belief_set_obj = PropositionalBeliefSet("a => b")
        self.mock_tweety_bridge_instance.execute_pl_query.return_value = "FUNC_ERROR: Erreur de syntaxe Tweety" # Retourne une chaîne
        self.mock_tweety_bridge_instance.validate_formula.return_value = (True, "Formule valide")

        result, message = self.agent.execute_query(belief_set_obj, "a")
        
        self.mock_tweety_bridge_instance.validate_formula.assert_called_once_with(formula_string="a")
        self.mock_tweety_bridge_instance.execute_pl_query.assert_called_once_with(
            belief_set_content="a => b", # Corrected parameter name
            query_string="a"  # Corrected parameter name
        )
        
        self.assertIsNone(result)
        self.assertEqual(message, "FUNC_ERROR: Erreur de syntaxe Tweety")

    def test_execute_query_invalid_formula(self):
        """Test de l'exécution d'une requête avec une formule invalide."""
        belief_set_obj = PropositionalBeliefSet("a => b")
        self.mock_tweety_bridge_instance.validate_formula.return_value = (False, "Syntax Error in query")

        result, message = self.agent.execute_query(belief_set_obj, "invalid_query {")
        
        self.mock_tweety_bridge_instance.validate_formula.assert_called_once_with(formula_string="invalid_query {")
        self.mock_tweety_bridge_instance.execute_pl_query.assert_not_called()
        
        self.assertIsNone(result)
        self.assertEqual(message, "FUNC_ERROR: Requête invalide: invalid_query {")


    async def test_interpret_results(self):
        """Test de l'interprétation des résultats."""
        mock_sk_result = MagicMock()
        mock_sk_result.__str__.return_value = "Interprétation finale des résultats"
        self.kernel.invoke.return_value = mock_sk_result
        
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
        self.mock_tweety_bridge_instance.validate_formula.assert_called_once_with(formula_string="a => b")

    def test_validate_formula_invalid(self):
        """Test de la validation d'une formule invalide."""
        self.mock_tweety_bridge_instance.validate_formula.return_value = (False, "Erreur de syntaxe")
        is_valid = self.agent.validate_formula("a => (b")
        self.assertFalse(is_valid)
        self.mock_tweety_bridge_instance.validate_formula.assert_called_once_with(formula_string="a => (b")

def async_test(f):
    def wrapper(*args, **kwargs):
        asyncio.run(f(*args, **kwargs))
    return wrapper

TestPropositionalLogicAgent.test_text_to_belief_set_success = async_test(TestPropositionalLogicAgent.test_text_to_belief_set_success)
TestPropositionalLogicAgent.test_text_to_belief_set_empty_result = async_test(TestPropositionalLogicAgent.test_text_to_belief_set_empty_result)
TestPropositionalLogicAgent.test_text_to_belief_set_invalid_belief_set = async_test(TestPropositionalLogicAgent.test_text_to_belief_set_invalid_belief_set)
TestPropositionalLogicAgent.test_generate_queries = async_test(TestPropositionalLogicAgent.test_generate_queries)
TestPropositionalLogicAgent.test_generate_queries_with_invalid_query = async_test(TestPropositionalLogicAgent.test_generate_queries_with_invalid_query)
TestPropositionalLogicAgent.test_interpret_results = async_test(TestPropositionalLogicAgent.test_interpret_results)


if __name__ == "__main__":
    unittest.main()