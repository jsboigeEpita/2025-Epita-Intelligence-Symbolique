# -*- coding: utf-8 -*-
# tests/agents/core/logic/test_modal_logic_agent.py
"""
Tests unitaires pour la classe ModalLogicAgent.
"""

import unittest
import asyncio # Ajouté pour les tests async
from unittest.mock import MagicMock, patch, AsyncMock # AsyncMock ajouté

from semantic_kernel import Kernel
from semantic_kernel.functions.kernel_arguments import KernelArguments # Ajouté

from argumentation_analysis.agents.core.logic.modal_logic_agent import ModalLogicAgent, SYSTEM_PROMPT_ML
from argumentation_analysis.agents.core.logic.belief_set import ModalBeliefSet, BeliefSet
from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge


class TestModalLogicAgent(unittest.TestCase):
    """Tests pour la classe ModalLogicAgent."""

    def setUp(self):
        """Initialisation avant chaque test."""
        self.kernel = MagicMock(spec=Kernel)
        # Note: L'agent ModalLogicAgent utilise kernel.plugins[self.name]["FunctionName"].invoke(...)
        # Il faut donc s'assurer que kernel.plugins est un dictionnaire et que
        # kernel.plugins[agent_name] est aussi un dictionnaire contenant les mocks des fonctions.
        self.kernel.plugins = {}
        self.kernel.get_prompt_execution_settings_from_service_id = MagicMock(return_value={"temperature": 0.7})
        self.kernel.add_function = MagicMock()

        self.tweety_bridge_patcher = patch('argumentation_analysis.agents.core.logic.modal_logic_agent.TweetyBridge')
        self.mock_tweety_bridge_class = self.tweety_bridge_patcher.start()
        
        self.mock_tweety_bridge_instance = MagicMock(spec=TweetyBridge)
        self.mock_tweety_bridge_class.return_value = self.mock_tweety_bridge_instance
        self.mock_tweety_bridge_instance.is_jvm_ready.return_value = True
        self.mock_tweety_bridge_instance.validate_modal_belief_set.return_value = (True, "Ensemble de croyances modal valide")
        self.mock_tweety_bridge_instance.validate_modal_formula.return_value = (True, "Formule modale valide")
        self.mock_tweety_bridge_instance.execute_modal_query.return_value = "Tweety Result: Modal Query '[]p' is ACCEPTED (True)."

        self.agent = ModalLogicAgent(self.kernel) # Nom de l'agent est fixé dans la classe
        self.agent_name = self.agent.name # Récupérer le nom de l'agent pour les mocks de plugins

        # Mocker les fonctions sémantiques spécifiques au plugin de l'agent
        self.mock_text_to_modal_function = AsyncMock(return_value=MagicMock(result="[]p => <>q;"))
        self.mock_generate_queries_function = AsyncMock(return_value=MagicMock(result="p\n[]p\n<>q"))
        self.mock_interpret_function = AsyncMock(return_value=MagicMock(result="Interprétation des résultats modaux"))
        
        self.kernel.plugins[self.agent_name] = {
            "TextToModalBeliefSet": self.mock_text_to_modal_function,
            "GenerateModalQueries": self.mock_generate_queries_function,
            "InterpretModalResult": self.mock_interpret_function
        }

        self.llm_service_id = "test_modal_llm_service"
        self.agent.setup_agent_components(self.llm_service_id)

    def tearDown(self):
        """Nettoyage après chaque test."""
        self.tweety_bridge_patcher.stop()

    def test_initialization_and_setup(self):
        """Test de l'initialisation et de la configuration de l'agent."""
        self.assertEqual(self.agent.name, "ModalLogicAgent")
        self.assertEqual(self.agent.sk_kernel, self.kernel)
        self.assertEqual(self.agent.logic_type, "ML")
        self.assertEqual(self.agent.system_prompt, SYSTEM_PROMPT_ML)
        
        self.mock_tweety_bridge_class.assert_called_once_with(logic_type="ml")
        self.mock_tweety_bridge_instance.is_jvm_ready.assert_called_once()
        
        self.assertTrue(self.kernel.add_function.call_count >= 3)
        self.kernel.get_prompt_execution_settings_from_service_id.assert_called_with(self.llm_service_id)

    async def test_text_to_belief_set_success(self):
        """Test de la conversion de texte en ensemble de croyances modal avec succès."""
        # Le mock est déjà configuré dans setUp pour self.mock_text_to_modal_function
        
        belief_set, message = await self.agent.text_to_belief_set("Texte de test")
        
        self.mock_text_to_modal_function.assert_called_once_with(self.kernel, input="Texte de test")
        self.mock_tweety_bridge_instance.validate_modal_belief_set.assert_called_once_with("[]p => <>q;")
        
        self.assertIsInstance(belief_set, ModalBeliefSet)
        self.assertEqual(belief_set.content, "[]p => <>q;")
        self.assertEqual(message, "Conversion réussie")

    async def test_text_to_belief_set_empty_result(self):
        """Test de la conversion de texte en ensemble de croyances modal avec résultat vide."""
        self.mock_text_to_modal_function.return_value = MagicMock(result="")
        
        belief_set, message = await self.agent.text_to_belief_set("Texte de test")
        
        self.mock_text_to_modal_function.assert_called_once()
        self.mock_tweety_bridge_instance.validate_modal_belief_set.assert_not_called()
        
        self.assertIsNone(belief_set)
        self.assertEqual(message, "La conversion a produit un ensemble de croyances vide")

    async def test_text_to_belief_set_invalid_belief_set(self):
        """Test de la conversion de texte en ensemble de croyances modal avec ensemble invalide."""
        self.mock_text_to_modal_function.return_value = MagicMock(result="[]p => <>") # Syntaxe invalide
        self.mock_tweety_bridge_instance.validate_modal_belief_set.return_value = (False, "Erreur de syntaxe modale")
        
        belief_set, message = await self.agent.text_to_belief_set("Texte de test")
        
        self.mock_text_to_modal_function.assert_called_once()
        self.mock_tweety_bridge_instance.validate_modal_belief_set.assert_called_once_with("[]p => <>")
        
        self.assertIsNone(belief_set)
        self.assertEqual(message, "Ensemble de croyances invalide: Erreur de syntaxe modale")

    async def test_generate_queries(self):
        """Test de la génération de requêtes modales."""
        # Mock déjà configuré dans setUp pour self.mock_generate_queries_function
        self.mock_tweety_bridge_instance.validate_modal_formula.return_value = (True, "Formule modale valide")
        
        belief_set_obj = ModalBeliefSet("[]p;")
        queries = await self.agent.generate_queries("Texte de test", belief_set_obj)
        
        self.mock_generate_queries_function.assert_called_once_with(self.kernel, input="Texte de test", belief_set="[]p;")
        self.assertEqual(self.mock_tweety_bridge_instance.validate_modal_formula.call_count, 3)
        self.mock_tweety_bridge_instance.validate_modal_formula.assert_any_call("p")
        
        self.assertEqual(queries, ["p", "[]p", "<>q"])

    async def test_generate_queries_with_invalid_query(self):
        """Test de la génération de requêtes modales avec une requête invalide."""
        self.mock_generate_queries_function.return_value = MagicMock(result="p\n[]invalid\n<>q")

        def validate_side_effect(formula_str):
            if formula_str == "[]invalid":
                return (False, "Erreur de syntaxe modale")
            return (True, "Formule modale valide")
        self.mock_tweety_bridge_instance.validate_modal_formula.side_effect = validate_side_effect
        
        belief_set_obj = ModalBeliefSet("[]p;")
        queries = await self.agent.generate_queries("Texte de test", belief_set_obj)
        
        self.mock_generate_queries_function.assert_called_once()
        self.assertEqual(self.mock_tweety_bridge_instance.validate_modal_formula.call_count, 3)
        self.assertEqual(queries, ["p", "<>q"])

    def test_execute_query_accepted(self):
        """Test de l'exécution d'une requête modale acceptée."""
        belief_set_obj = ModalBeliefSet("[]p => <>q;")
        # mock_tweety_bridge_instance.execute_modal_query est déjà configuré dans setUp
        
        result, message = self.agent.execute_query(belief_set_obj, "[]p")
        
        self.mock_tweety_bridge_instance.execute_modal_query.assert_called_once_with(
            belief_set_content="[]p => <>q;",
            query_string="[]p"
        )
        self.assertTrue(result)
        self.assertEqual(message, "Tweety Result: Modal Query '[]p' is ACCEPTED (True).")

    def test_execute_query_rejected(self):
        """Test de l'exécution d'une requête modale rejetée."""
        belief_set_obj = ModalBeliefSet("[]p => <>q;")
        self.mock_tweety_bridge_instance.execute_modal_query.return_value = "Tweety Result: Modal Query '<>r' is REJECTED (False)."

        result, message = self.agent.execute_query(belief_set_obj, "<>r")
        
        self.mock_tweety_bridge_instance.execute_modal_query.assert_called_once_with(
            belief_set_content="[]p => <>q;",
            query_string="<>r"
        )
        self.assertFalse(result)
        self.assertEqual(message, "Tweety Result: Modal Query '<>r' is REJECTED (False).")

    def test_execute_query_error_tweety(self):
        """Test de l'exécution d'une requête modale avec erreur de Tweety."""
        belief_set_obj = ModalBeliefSet("[]p => <>q;")
        self.mock_tweety_bridge_instance.execute_modal_query.return_value = "FUNC_ERROR: Erreur de syntaxe Tweety Modale"

        result, message = self.agent.execute_query(belief_set_obj, "[]p")
        
        self.mock_tweety_bridge_instance.execute_modal_query.assert_called_once_with(
            belief_set_content="[]p => <>q;",
            query_string="[]p"
        )
        self.assertIsNone(result)
        self.assertEqual(message, "FUNC_ERROR: Erreur de syntaxe Tweety Modale")
    
    async def test_interpret_results(self):
        """Test de l'interprétation des résultats modaux."""
        # mock_interpret_function est déjà configuré dans setUp
        
        belief_set_obj = ModalBeliefSet("[]p => <>q;")
        queries_list = ["p", "[]p"]
        results_tuples = [
            (True, "Tweety Result: Modal Query 'p' is ACCEPTED (True)."),
            (False, "Tweety Result: Modal Query '[]p' is REJECTED (False).")
        ]
        
        interpretation = await self.agent.interpret_results("Texte de test", belief_set_obj, queries_list, results_tuples)
        
        self.mock_interpret_function.assert_called_once()
        args_call = self.mock_interpret_function.call_args[0]
        kwargs_call = self.mock_interpret_function.call_args[1]

        self.assertEqual(args_call[0], self.kernel)
        self.assertEqual(kwargs_call['input'], "Texte de test")
        self.assertEqual(kwargs_call['belief_set'], "[]p => <>q;")
        self.assertEqual(kwargs_call['queries'], "p\n[]p")
        expected_tweety_results = "Tweety Result: Modal Query 'p' is ACCEPTED (True).\nTweety Result: Modal Query '[]p' is REJECTED (False)."
        self.assertEqual(kwargs_call['tweety_result'], expected_tweety_results)
        
        self.assertEqual(interpretation, "Interprétation des résultats modaux")

    def test_validate_formula_valid(self):
        """Test de la validation d'une formule modale valide."""
        self.mock_tweety_bridge_instance.validate_modal_formula.return_value = (True, "Formule modale valide")
        is_valid = self.agent.validate_formula("[]p => <>q")
        self.assertTrue(is_valid)
        self.mock_tweety_bridge_instance.validate_modal_formula.assert_called_once_with("[]p => <>q")

    def test_validate_formula_invalid(self):
        """Test de la validation d'une formule modale invalide."""
        self.mock_tweety_bridge_instance.validate_modal_formula.return_value = (False, "Erreur de syntaxe modale")
        is_valid = self.agent.validate_formula("[]p => <>") # Syntaxe invalide
        self.assertFalse(is_valid)
        self.mock_tweety_bridge_instance.validate_modal_formula.assert_called_once_with("[]p => <>")

# Wrapper pour exécuter les tests async avec unittest
def async_test(f):
    def wrapper(*args, **kwargs):
        asyncio.run(f(*args, **kwargs))
    return wrapper

# Appliquer le décorateur aux méthodes de test async
TestModalLogicAgent.test_text_to_belief_set_success = async_test(TestModalLogicAgent.test_text_to_belief_set_success)
TestModalLogicAgent.test_text_to_belief_set_empty_result = async_test(TestModalLogicAgent.test_text_to_belief_set_empty_result)
TestModalLogicAgent.test_text_to_belief_set_invalid_belief_set = async_test(TestModalLogicAgent.test_text_to_belief_set_invalid_belief_set)
TestModalLogicAgent.test_generate_queries = async_test(TestModalLogicAgent.test_generate_queries)
TestModalLogicAgent.test_generate_queries_with_invalid_query = async_test(TestModalLogicAgent.test_generate_queries_with_invalid_query)
TestModalLogicAgent.test_interpret_results = async_test(TestModalLogicAgent.test_interpret_results)

if __name__ == "__main__":
    unittest.main()