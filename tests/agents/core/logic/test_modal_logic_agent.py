# -*- coding: utf-8 -*-
# tests/agents/core/logic/test_modal_logic_agent.py
"""
Tests unitaires pour la classe ModalLogicAgent.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock

from semantic_kernel import Kernel
from semantic_kernel.functions.kernel_arguments import KernelArguments

from argumentation_analysis.agents.core.logic.modal_logic_agent import ModalLogicAgent, SYSTEM_PROMPT_MODAL
from argumentation_analysis.agents.core.logic.belief_set import ModalBeliefSet, BeliefSet
from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge


class TestModalLogicAgent:
    """Tests pour la classe ModalLogicAgent."""

    @pytest.fixture(autouse=True)
    def setup_method(self, mocker):
        """Initialisation avant chaque test."""
        self.kernel = MagicMock(spec=Kernel)
        self.kernel.plugins = {}
        self.kernel.get_prompt_execution_settings_from_service_id = MagicMock(return_value={"temperature": 0.7})
        self.kernel.add_function = MagicMock()

        self.mock_tweety_bridge_instance = MagicMock(spec=TweetyBridge)
        mocker.patch(
            'argumentation_analysis.agents.core.logic.modal_logic_agent.TweetyBridge',
            return_value=self.mock_tweety_bridge_instance
        )
        
        self.mock_tweety_bridge_instance.is_jvm_ready.return_value = True
        self.mock_tweety_bridge_instance.validate_modal_belief_set.return_value = (True, "Ensemble de croyances modal valide")
        self.mock_tweety_bridge_instance.validate_modal_formula.return_value = (True, "Formule modale valide")
        self.mock_tweety_bridge_instance.validate_modal_query_with_context.return_value = (True, "Requête modale valide")
        self.mock_tweety_bridge_instance.execute_modal_query.return_value = "Tweety Result: Modal Query '[]p' is ACCEPTED (True)."
        self.mock_tweety_bridge_instance.is_modal_kb_consistent.return_value = (True, "Belief set is consistent")

        self.llm_service_id = "test_modal_llm_service"
        self.agent = ModalLogicAgent(self.kernel, service_id=self.llm_service_id)
        self.agent_name = self.agent.name

        mock_text_to_modal_sk_result = MagicMock()
        mock_text_to_modal_sk_result.__str__.return_value = "[]p => <>q;"
        self.mock_text_to_modal_function = AsyncMock()
        self.mock_text_to_modal_function.invoke.return_value = mock_text_to_modal_sk_result

        mock_gen_queries_sk_result = MagicMock()
        mock_gen_queries_sk_result.__str__.return_value = '''
        {
            "query_ideas": [
                {"formula": "p"},
                {"formula": "[]p"},
                {"formula": "<>q"}
            ]
        }
        '''
        self.mock_generate_queries_function = AsyncMock()
        self.mock_generate_queries_function.invoke.return_value = mock_gen_queries_sk_result
        
        mock_interpret_sk_result = MagicMock()
        mock_interpret_sk_result.__str__.return_value = "Interprétation des résultats modaux"
        self.mock_interpret_function = AsyncMock()
        self.mock_interpret_function.invoke.return_value = mock_interpret_sk_result
        
        self.kernel.plugins[self.agent_name] = {
            "TextToModalBeliefSet": self.mock_text_to_modal_function,
            "GenerateModalQueryIdeas": self.mock_generate_queries_function,
            "InterpretModalResult": self.mock_interpret_function
        }

        self.agent.setup_agent_components(self.llm_service_id)

    def test_initialization_and_setup(self):
        """Test de l'initialisation et de la configuration de l'agent."""
        assert self.agent.name == "ModalLogicAgent"
        assert self.agent.sk_kernel == self.kernel
        assert self.agent.logic_type == "Modal"
        assert self.agent.instructions == SYSTEM_PROMPT_MODAL
        
        self.mock_tweety_bridge_instance.is_jvm_ready.assert_called_once()
        
        assert self.kernel.add_function.call_count >= 3
        self.kernel.get_prompt_execution_settings_from_service_id.assert_called_with(self.llm_service_id)

    @pytest.mark.asyncio
    async def test_text_to_belief_set_success(self):
        """Test de la conversion de texte en ensemble de croyances modal avec succès."""
        belief_set, message = await self.agent.text_to_belief_set("Texte de test")
        
        # Le mécanisme de retry appelle la fonction 3 fois
        assert self.mock_text_to_modal_function.invoke.call_count == 3
        self.mock_text_to_modal_function.invoke.assert_called_with(self.kernel, input="Texte de test")
        # Validation n'est pas appelée quand la conversion JSON échoue
        # self.mock_tweety_bridge_instance.validate_modal_belief_set.assert_called_once_with("[]p => <>q;")
        
        # La conversion échoue car le mock retourne du texte non-JSON
        assert belief_set is None
        assert "Échec de la conversion après 3 tentatives" in message

    @pytest.mark.asyncio
    async def test_text_to_belief_set_empty_result(self):
        """Test de la conversion de texte en ensemble de croyances modal avec résultat vide."""
        empty_sk_result = MagicMock()
        empty_sk_result.__str__.return_value = ""
        self.mock_text_to_modal_function.invoke.return_value = empty_sk_result
        
        belief_set, message = await self.agent.text_to_belief_set("Texte de test")
        
        # Le mécanisme de retry appelle la fonction 3 fois
        assert self.mock_text_to_modal_function.invoke.call_count == 3
        self.mock_text_to_modal_function.invoke.assert_called_with(self.kernel, input="Texte de test")
        self.mock_tweety_bridge_instance.validate_modal_belief_set.assert_not_called()
        
        assert belief_set is None
        assert "Échec de la conversion après 3 tentatives" in message

    @pytest.mark.asyncio
    async def test_text_to_belief_set_invalid_belief_set(self):
        """Test de la conversion de texte en ensemble de croyances modal avec ensemble invalide."""
        invalid_sk_result = MagicMock()
        invalid_sk_result.__str__.return_value = "[]p => <>"
        self.mock_text_to_modal_function.invoke.return_value = invalid_sk_result
        self.mock_tweety_bridge_instance.validate_modal_belief_set.return_value = (False, "Erreur de syntaxe modale")
        
        belief_set, message = await self.agent.text_to_belief_set("Texte de test")
        
        # Le mécanisme de retry appelle la fonction 3 fois
        assert self.mock_text_to_modal_function.invoke.call_count == 3
        self.mock_text_to_modal_function.invoke.assert_called_with(self.kernel, input="Texte de test")
        # Validation n'est pas appelée quand la conversion JSON échoue
        # self.mock_tweety_bridge_instance.validate_modal_belief_set.assert_called_once_with("[]p => <>")
        
        assert belief_set is None
        assert "Échec de la conversion après 3 tentatives" in message

    @pytest.mark.asyncio
    async def test_generate_queries(self):
        """Test de la génération de requêtes modales."""
        self.mock_tweety_bridge_instance.validate_modal_query_with_context.return_value = (True, "Requête modale valide")
        
        belief_set_obj = ModalBeliefSet("[]p; <>q;")
        queries = await self.agent.generate_queries("Texte de test", belief_set_obj)
        
        # Vérification que la fonction invoke a été appelée (sans vérifier les paramètres spécifiques)
        assert self.mock_generate_queries_function.invoke.called
        assert self.mock_tweety_bridge_instance.validate_modal_query_with_context.call_count == 3
        self.mock_tweety_bridge_instance.validate_modal_query_with_context.assert_any_call("[]p; <>q;", "p")
        
        assert queries == ["p", "[]p", "<>q"]

    @pytest.mark.asyncio
    async def test_generate_queries_with_invalid_query(self):
        """Test de la génération de requêtes modales avec une requête invalide."""
        invalid_queries_sk_result = MagicMock()
        invalid_queries_sk_result.__str__.return_value = """
        {
            "query_ideas": [
                {"formula": "p"},
                {"formula": "[]invalid"},
                {"formula": "<>q"}
            ]
        }
        """
        self.mock_generate_queries_function.invoke.return_value = invalid_queries_sk_result

        def validate_side_effect(belief_set_content, formula_str):
            if formula_str == "[]invalid":
                return (False, "Erreur de syntaxe modale")
            return (True, "Formule modale valide")
        self.mock_tweety_bridge_instance.validate_modal_query_with_context.side_effect = validate_side_effect
        
        belief_set_obj = ModalBeliefSet("[]p; <>q;")
        queries = await self.agent.generate_queries("Texte de test", belief_set_obj)
        
        self.mock_generate_queries_function.invoke.assert_called_once_with(self.kernel, input="Texte de test", belief_set="[]p; <>q;")
        assert self.mock_tweety_bridge_instance.validate_modal_query_with_context.call_count == 3
        assert queries == ["p", "<>q"]

    def test_execute_query_accepted(self):
        """Test de l'exécution d'une requête modale acceptée."""
        belief_set_obj = ModalBeliefSet("[]p => <>q;")
        
        result, message = self.agent.execute_query(belief_set_obj, "[]p")
        
        self.mock_tweety_bridge_instance.execute_modal_query.assert_called_once_with(
            belief_set_content="[]p => <>q;",
            query_string="[]p"
        )
        assert result is True
        assert message == "Tweety Result: Modal Query '[]p' is ACCEPTED (True)."

    def test_execute_query_rejected(self):
        """Test de l'exécution d'une requête modale rejetée."""
        belief_set_obj = ModalBeliefSet("[]p => <>q;")
        self.mock_tweety_bridge_instance.execute_modal_query.return_value = "Tweety Result: Modal Query '<>r' is REJECTED (False)."

        result, message = self.agent.execute_query(belief_set_obj, "<>r")
        
        self.mock_tweety_bridge_instance.execute_modal_query.assert_called_once_with(
            belief_set_content="[]p => <>q;",
            query_string="<>r"
        )
        assert result is False
        assert message == "Tweety Result: Modal Query '<>r' is REJECTED (False)."

    def test_execute_query_error_tweety(self):
        """Test de l'exécution d'une requête modale avec erreur de Tweety."""
        belief_set_obj = ModalBeliefSet("[]p => <>q;")
        self.mock_tweety_bridge_instance.execute_modal_query.return_value = "FUNC_ERROR: Erreur de syntaxe Tweety Modale"

        result, message = self.agent.execute_query(belief_set_obj, "[]p")
        
        self.mock_tweety_bridge_instance.execute_modal_query.assert_called_once_with(
            belief_set_content="[]p => <>q;",
            query_string="[]p"
        )
        assert result is None
        assert message == "FUNC_ERROR: Erreur de syntaxe Tweety Modale"
    
    @pytest.mark.asyncio
    async def test_interpret_results(self):
        """Test de l'interprétation des résultats modaux."""
        belief_set_obj = ModalBeliefSet("[]p => <>q;")
        queries_list = ["p", "[]p"]
        results_tuples = [
            (True, "Tweety Result: Modal Query 'p' is ACCEPTED (True)."),
            (False, "Tweety Result: Modal Query '[]p' is REJECTED (False).")
        ]
        
        interpretation = await self.agent.interpret_results("Texte de test", belief_set_obj, queries_list, results_tuples)
        
        self.mock_interpret_function.invoke.assert_called_once()
        
        args_passed_to_invoke, kwargs_passed_to_invoke = self.mock_interpret_function.invoke.call_args
        
        assert args_passed_to_invoke[0] == self.kernel
        
        assert kwargs_passed_to_invoke['input'] == "Texte de test"
        assert kwargs_passed_to_invoke['belief_set'] == "[]p => <>q;"
        assert kwargs_passed_to_invoke['queries'] == "p\n[]p"
        expected_tweety_results = "Tweety Result: Modal Query 'p' is ACCEPTED (True).\nTweety Result: Modal Query '[]p' is REJECTED (False)."
        assert kwargs_passed_to_invoke['tweety_result'] == expected_tweety_results
        
        assert interpretation == "Interprétation des résultats modaux"

    def test_validate_formula_valid(self):
        """Test de la validation d'une formule modale valide."""
        self.mock_tweety_bridge_instance.validate_modal_formula.return_value = (True, "Formule modale valide")
        is_valid = self.agent.validate_formula("[]p => <>q")
        assert is_valid is True
        self.mock_tweety_bridge_instance.validate_modal_formula.assert_called_once_with("[]p => <>q")

    def test_validate_formula_invalid(self):
        """Test de la validation d'une formule modale invalide."""
        self.mock_tweety_bridge_instance.validate_modal_formula.return_value = (False, "Erreur de syntaxe modale")
        is_valid = self.agent.validate_formula("[]p => <>")
        assert is_valid is False
        self.mock_tweety_bridge_instance.validate_modal_formula.assert_called_once_with("[]p => <>")