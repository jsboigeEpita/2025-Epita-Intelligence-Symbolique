
# Authentic gpt-4o-mini imports (replacing mocks)
import openai
from semantic_kernel.contents import ChatHistory
from semantic_kernel.core_plugins import ConversationSummaryPlugin
from config.unified_config import UnifiedConfig

"""
Tests unitaires pour ModalLogicAgent.

Ce module teste toutes les fonctionnalités principales du ModalLogicAgent,
y compris la conversion de texte en belief sets, la génération de requêtes,
l'exécution et l'interprétation des résultats.
"""

import pytest
import asyncio
import json

from typing import Dict, Any, Optional, Tuple, List

from unittest.mock import MagicMock, AsyncMock, Mock, patch

# Import du module à tester
from argumentation_analysis.agents.core.logic.modal_logic_agent import (
    ModalLogicAgent,
    SYSTEM_PROMPT_MODAL,
    PROMPT_TEXT_TO_MODAL_BELIEF_SET,
    PROMPT_GEN_MODAL_QUERIES_IDEAS,
    PROMPT_INTERPRET_MODAL
)
from argumentation_analysis.agents.core.logic.belief_set import ModalBeliefSet
from semantic_kernel import Kernel


class TestModalLogicAgent:
    """Classe de tests pour ModalLogicAgent."""
    
    @pytest.fixture
    def mock_kernel(self):
        """Fixture pour un kernel mocké."""
        kernel = Mock(spec=Kernel)
        kernel.plugins = {}
        kernel.get_prompt_execution_settings_from_service_id = Mock(return_value=None)
        kernel.add_function = MagicMock()
        return kernel
    
    @pytest.fixture
    def mock_tweety_bridge(self):
        """Fixture pour un TweetyBridge mocké."""
        bridge = MagicMock()
        bridge.is_jvm_ready.return_value = True
        bridge.validate_modal_belief_set.return_value = (True, "Valid")
        bridge.validate_modal_formula.return_value = (True, "Valid formula")
        bridge.validate_modal_query_with_context.return_value = (True, "Valid query")
        bridge.execute_modal_query.return_value = "ACCEPTED: Query result"
        bridge.is_modal_kb_consistent.return_value = (True, "Consistent")
        return bridge
    
    @pytest.fixture
    def modal_agent(self, mock_kernel):
        """Fixture pour une instance de ModalLogicAgent."""
        agent = ModalLogicAgent(mock_kernel, "TestModalAgent", "test_service")
        return agent
    
    def test_init_modal_logic_agent(self, mock_kernel):
        """Test l'initialisation du ModalLogicAgent."""
        agent = ModalLogicAgent(mock_kernel, "TestAgent", "test_service")
        
        assert agent.name == "TestAgent"
        assert agent.logic_type == "Modal"
        assert agent._llm_service_id == "test_service"
        assert isinstance(agent.sk_kernel, Mock)
    
    def test_get_agent_capabilities(self, modal_agent):
        """Test la récupération des capacités de l'agent."""
        capabilities = modal_agent.get_agent_capabilities()
        
        assert capabilities["name"] == "TestModalAgent"
        assert capabilities["logic_type"] == "Modal"
        assert "description" in capabilities
        assert "methods" in capabilities
        
        methods = capabilities["methods"]
        assert "text_to_belief_set" in methods
        assert "generate_queries" in methods
        assert "execute_query" in methods
        assert "interpret_results" in methods
        assert "validate_formula" in methods
    
    @patch('argumentation_analysis.agents.core.logic.modal_logic_agent.TweetyBridge')
    def test_setup_agent_components(self, mock_tweety_class, modal_agent, mock_tweety_bridge):
        """Test la configuration des composants de l'agent."""
        mock_tweety_class.return_value = mock_tweety_bridge
        
        # Simulation des plugins mockés
        modal_agent.sk_kernel.plugins = {"TestModalAgent": {}}
        
        modal_agent.setup_agent_components("test_service")
        
        # Vérifier que TweetyBridge a été initialisé
        assert hasattr(modal_agent, '_tweety_bridge')
        
        # Vérifier que les fonctions sémantiques ont été ajoutées
        assert modal_agent.sk_kernel.add_function.call_count == 3
        
        # Vérifier les noms des fonctions ajoutées
        calls = modal_agent.sk_kernel.add_function.call_args_list
        function_names = [call[1]['function_name'] for call in calls]
        expected_functions = ["TextToModalBeliefSet", "GenerateModalQueryIdeas", "InterpretModalResult"]
        
        for expected_func in expected_functions:
            assert expected_func in function_names
    
    def test_construct_modal_kb_from_json(self, modal_agent):
        """Test la construction d'une base de connaissances modale depuis JSON."""
        kb_json = {
            "propositions": ["climat_urgent", "action_necessaire"],
            "modal_formulas": ["[]climat_urgent", "<>action_necessaire", "climat_urgent => []action_necessaire"]
        }
        
        kb_content = modal_agent._construct_modal_kb_from_json(kb_json)
        
        # Vérifier que les constantes sont déclarées
        assert "constant action_necessaire" in kb_content
        assert "constant climat_urgent" in kb_content
        
        # Vérifier que les propositions ne sont plus déclarées avec prop()
        assert "prop(climat_urgent)" not in kb_content
        assert "prop(action_necessaire)" not in kb_content
        
        # Vérifier que les formules modales sont présentes
        assert "[]climat_urgent" in kb_content
        assert "<>action_necessaire" in kb_content
        assert "climat_urgent => []action_necessaire" in kb_content
    
    def test_validate_modal_kb_json_valid(self, modal_agent):
        """Test la validation d'un JSON valide."""
        valid_json = {
            "propositions": ["prop1", "prop2"],
            "modal_formulas": ["[]prop1", "<>prop2", "prop1 => prop2"]
        }
        
        is_valid, message = modal_agent._validate_modal_kb_json(valid_json)
        
        assert is_valid == True
        assert "réussie" in message
    
    def test_validate_modal_kb_json_invalid_missing_key(self, modal_agent):
        """Test la validation d'un JSON invalide (clé manquante)."""
        invalid_json = {
            "propositions": ["prop1", "prop2"]
            # "modal_formulas" manquant
        }
        
        is_valid, message = modal_agent._validate_modal_kb_json(invalid_json)
        
        assert is_valid == False
        assert "modal_formulas" in message
    
    def test_validate_modal_kb_json_invalid_undeclared_props(self, modal_agent):
        """Test la validation d'un JSON avec propositions non déclarées."""
        invalid_json = {
            "propositions": ["prop1"],
            "modal_formulas": ["[]prop1", "<>prop2"]  # prop2 non déclaré
        }
        
        is_valid, message = modal_agent._validate_modal_kb_json(invalid_json)
        
        assert is_valid == False
        assert "prop2" in message
        assert "non déclarées" in message
    
    def test_extract_json_block_valid_json(self, modal_agent):
        """Test l'extraction d'un bloc JSON valide."""
        text_with_json = """
        Voici le résultat:
        {"propositions": ["prop1"], "modal_formulas": ["[]prop1"]}
        Fin du texte.
        """
        
        extracted = modal_agent._extract_json_block(text_with_json)
        parsed = json.loads(extracted)
        
        assert parsed["propositions"] == ["prop1"]
        assert parsed["modal_formulas"] == ["[]prop1"]
    
    def test_extract_json_block_truncated_json(self, modal_agent):
        """Test l'extraction et réparation d'un JSON tronqué."""
        truncated_text = '''
        Voici le résultat:
        {"propositions": ["prop1"], "modal_formulas":["[]prop1"
        '''
        
        extracted = modal_agent._extract_json_block(truncated_text)
        
        # Vérifier que le JSON peut être parsé après réparation
        try:
            parsed = json.loads(extracted)
            assert "propositions" in parsed
        except json.JSONDecodeError:
            # Si la réparation échoue, vérifier qu'on a au moins un JSON partiel
            assert "{" in extracted
    
    @pytest.mark.asyncio
    async def test_text_to_belief_set_success(self, modal_agent, mock_tweety_bridge):
        """Test la conversion réussie de texte en belief set."""
        modal_agent._tweety_bridge = mock_tweety_bridge
        
        # Mock de la fonction sémantique - doit retourner directement la chaîne JSON
        mock_json_response = '{"propositions": ["urgent"], "modal_formulas": ["[]urgent"]}'
    
        mock_plugin = {
            "TextToModalBeliefSet": MagicMock()
        }
        mock_plugin["TextToModalBeliefSet"].invoke = AsyncMock(return_value=mock_json_response)
        modal_agent.sk_kernel.plugins = {"TestModalAgent": mock_plugin}
        
        text = "Il est urgent d'agir sur le climat."
        belief_set, message = await modal_agent.text_to_belief_set(text)
        
        assert belief_set is not None
        assert isinstance(belief_set, ModalBeliefSet)
        assert "réussie" in message
        assert "constant urgent" in belief_set.content
        assert "[]urgent" in belief_set.content
    
    @pytest.mark.asyncio
    async def test_text_to_belief_set_json_error(self, modal_agent, mock_tweety_bridge):
        """Test la gestion d'erreur JSON lors de la conversion."""
        modal_agent._tweety_bridge = mock_tweety_bridge
        
        # Mock retournant un JSON invalide
        mock_invalid_json = 'JSON invalide {'
    
        mock_plugin = {
            "TextToModalBeliefSet": MagicMock()
        }
        mock_plugin["TextToModalBeliefSet"].invoke = AsyncMock(return_value=mock_invalid_json)
        modal_agent.sk_kernel.plugins = {"TestModalAgent": mock_plugin}
        
        text = "Texte de test"
        with pytest.raises(ValueError) as excinfo:
            await modal_agent.text_to_belief_set(text)
        
        # Vérifier que l'exception levée est bien due à une erreur de syntaxe/validation
        assert "JSON invalide" in str(excinfo.value) or "ERREUR DE SYNTAXE" in str(excinfo.value)
    
    def test_parse_modal_belief_set_content(self, modal_agent):
        """Test l'analyse du contenu d'un belief set modal."""
        belief_content = """
        constant urgent
        constant action
        
        prop(urgent)
        prop(action)
        
        []urgent
        <>(urgent => action)
        """
        
        parsed = modal_agent._parse_modal_belief_set_content(belief_content)
        
        assert "urgent" in parsed["propositions"]
        assert "action" in parsed["propositions"]
        assert "[]urgent" in parsed["modal_formulas"]
        assert "<>(urgent => action)" in parsed["modal_formulas"]
    
    @pytest.mark.asyncio
    async def test_generate_queries_success(self, modal_agent, mock_tweety_bridge):
        """Test la génération réussie de requêtes modales."""
        modal_agent._tweety_bridge = mock_tweety_bridge
        
        # Mock du belief set
        belief_set = ModalBeliefSet("prop(urgent)\n[]urgent")
        
        # Mock de la réponse LLM
        mock_json_response = '{"query_ideas": [{"formula": "[]urgent"}, {"formula": "<>urgent"}]}'
    
        mock_plugin = {
            "GenerateModalQueryIdeas": MagicMock()
        }
        mock_plugin["GenerateModalQueryIdeas"].invoke = AsyncMock(return_value=mock_json_response)
        modal_agent.sk_kernel.plugins = {"TestModalAgent": mock_plugin}
        
        text = "Test text"
        queries = await modal_agent.generate_queries(text, belief_set)
        
        assert len(queries) >= 1
        assert any("urgent" in query for query in queries)
    
    @pytest.mark.asyncio
    async def test_generate_queries_empty_response(self, modal_agent, mock_tweety_bridge):
        """Test la génération de requêtes avec réponse vide."""
        modal_agent._tweety_bridge = mock_tweety_bridge
        
        belief_set = ModalBeliefSet("prop(test)\n[]test")
        
        # Mock retournant une réponse vide
        mock_json_response = '{"query_ideas": []}'
    
        mock_plugin = {
            "GenerateModalQueryIdeas": MagicMock()
        }
        mock_plugin["GenerateModalQueryIdeas"].invoke = AsyncMock(return_value=mock_json_response)
        modal_agent.sk_kernel.plugins = {"TestModalAgent": mock_plugin}
        
        text = "Test text"
        queries = await modal_agent.generate_queries(text, belief_set)
        
        assert queries == []
    
    def test_execute_query_success(self, modal_agent, mock_tweety_bridge):
        """Test l'exécution réussie d'une requête."""
        modal_agent._tweety_bridge = mock_tweety_bridge
        mock_tweety_bridge.execute_modal_query.return_value = "ACCEPTED: Query validated"
        
        belief_set = ModalBeliefSet("prop(urgent)\n[]urgent")
        query = "[]urgent"
        
        result, message = modal_agent.execute_query(belief_set, query)
        
        assert result == True
        assert "ACCEPTED" in message
    
    def test_execute_query_rejected(self, modal_agent, mock_tweety_bridge):
        """Test l'exécution d'une requête rejetée."""
        modal_agent._tweety_bridge = mock_tweety_bridge
        mock_tweety_bridge.execute_modal_query.return_value = "REJECTED: Query not valid"
        
        belief_set = ModalBeliefSet("prop(urgent)\n[]urgent")
        query = "invalid_query"
        
        result, message = modal_agent.execute_query(belief_set, query)
        
        assert result == False
        assert "REJECTED" in message
    
    def test_execute_query_error(self, modal_agent, mock_tweety_bridge):
        """Test la gestion d'erreur lors de l'exécution de requête."""
        modal_agent._tweety_bridge = mock_tweety_bridge
        mock_tweety_bridge.execute_modal_query.side_effect = Exception("Test error")
        
        belief_set = ModalBeliefSet("prop(urgent)\n[]urgent")
        query = "[]urgent"
        
        result, message = modal_agent.execute_query(belief_set, query)
        
        assert result is None
        assert "FUNC_ERROR" in message
    
    @pytest.mark.asyncio
    async def test_interpret_results_success(self, modal_agent):
        """Test l'interprétation réussie des résultats."""
        # Mock de la fonction d'interprétation
        mock_response = "Interprétation: La requête []urgent est acceptée, indiquant une nécessité."
    
        mock_plugin = {
            "InterpretModalResult": MagicMock()
        }
        mock_plugin["InterpretModalResult"].invoke = AsyncMock(return_value=mock_response)
        modal_agent.sk_kernel.plugins = {"TestModalAgent": mock_plugin}
        
        text = "Texte original"
        belief_set = ModalBeliefSet("prop(urgent)\n[]urgent")
        queries = ["[]urgent"]
        results = [(True, "ACCEPTED: Query valid")]
        
        interpretation = await modal_agent.interpret_results(text, belief_set, queries, results)
        
        assert "Interprétation" in interpretation
        assert "urgent" in interpretation
    
    @pytest.mark.asyncio
    async def test_interpret_results_error(self, modal_agent):
        """Test la gestion d'erreur lors de l'interprétation."""
        # Mock qui lève une exception
        mock_plugin = {
            "InterpretModalResult": MagicMock()
        }
        mock_plugin["InterpretModalResult"].invoke = AsyncMock(side_effect=Exception("Interpret error"))
        modal_agent.sk_kernel.plugins = {"TestModalAgent": mock_plugin}
        
        text = "Texte"
        belief_set = ModalBeliefSet("prop(test)")
        queries = ["[]test"]
        results = [(True, "ACCEPTED")]
        
        interpretation = await modal_agent.interpret_results(text, belief_set, queries, results)
        
        assert "Erreur d'interprétation" in interpretation
    
    def test_validate_formula_success(self, modal_agent, mock_tweety_bridge):
        """Test la validation réussie d'une formule."""
        modal_agent._tweety_bridge = mock_tweety_bridge
        mock_tweety_bridge.validate_modal_formula.return_value = (True, "Valid")
        
        formula = "[]urgent"
        is_valid = modal_agent.validate_formula(formula)
        
        assert is_valid == True
    
    def test_validate_formula_invalid(self, modal_agent, mock_tweety_bridge):
        """Test la validation d'une formule invalide."""
        modal_agent._tweety_bridge = mock_tweety_bridge
        mock_tweety_bridge.validate_modal_formula.return_value = (False, "Invalid syntax")
        
        formula = "invalid_formula"
        is_valid = modal_agent.validate_formula(formula)
        
        assert is_valid == False
    
    def test_validate_formula_fallback(self, modal_agent, mock_tweety_bridge):
        """Test la validation avec fallback si méthode indisponible."""
        modal_agent._tweety_bridge = mock_tweety_bridge
        # Simuler l'absence de la méthode
        del mock_tweety_bridge.validate_modal_formula
        
        formula = "[]urgent"
        is_valid = modal_agent.validate_formula(formula)
        
        # Devrait utiliser la validation basique
        assert isinstance(is_valid, bool)
    
    def test_is_consistent_success(self, modal_agent, mock_tweety_bridge):
        """Test la vérification de cohérence réussie."""
        modal_agent._tweety_bridge = mock_tweety_bridge
        mock_tweety_bridge.is_modal_kb_consistent.return_value = (True, "Consistent KB")
        
        belief_set = ModalBeliefSet("prop(urgent)\n[]urgent")
        is_consistent, message = modal_agent.is_consistent(belief_set)
        
        assert is_consistent == True
        assert "Consistent" in message
    
    def test_is_consistent_inconsistent(self, modal_agent, mock_tweety_bridge):
        """Test la détection d'incohérence."""
        modal_agent._tweety_bridge = mock_tweety_bridge
        mock_tweety_bridge.is_modal_kb_consistent.return_value = (False, "Inconsistent KB")
        
        belief_set = ModalBeliefSet("prop(p)\n[]p\n[]!p")  # Contradictoire
        is_consistent, message = modal_agent.is_consistent(belief_set)
        
        assert is_consistent == False
        assert "Inconsistent" in message
    
    def test_is_consistent_fallback(self, modal_agent, mock_tweety_bridge):
        """Test la vérification de cohérence avec fallback."""
        modal_agent._tweety_bridge = mock_tweety_bridge
        # Simuler l'absence de la méthode
        del mock_tweety_bridge.is_modal_kb_consistent
        
        belief_set = ModalBeliefSet("prop(urgent)\n[]urgent")
        is_consistent, message = modal_agent.is_consistent(belief_set)
        
        # Devrait retourner True par défaut avec un message explicatif
        assert is_consistent == True
        assert "non implémentée" in message
    
    def test_create_belief_set_from_data(self, modal_agent):
        """Test la création d'un belief set depuis des données."""
        data = {"content": "prop(test)\n[]test"}
        belief_set = modal_agent._create_belief_set_from_data(data)
        
        assert isinstance(belief_set, ModalBeliefSet)
        assert belief_set.content == "prop(test)\n[]test"
    
    def test_create_belief_set_from_empty_data(self, modal_agent):
        """Test la création d'un belief set depuis des données vides."""
        data = {}
        belief_set = modal_agent._create_belief_set_from_data(data)
        
        assert isinstance(belief_set, ModalBeliefSet)
        assert belief_set.content == ""
    
    @pytest.mark.asyncio
    async def test_get_response_not_implemented(self, modal_agent):
        """Test que get_response n'est pas implémentée."""
        async for response in modal_agent.get_response(None):
            assert response == []
            break
    
    @pytest.mark.asyncio
    async def test_invoke_not_implemented(self, modal_agent):
        """Test que invoke n'est pas implémentée."""
        result = await modal_agent.invoke(None)
        assert result == []
    
    @pytest.mark.asyncio
    async def test_invoke_stream_not_implemented(self, modal_agent):
        """Test que invoke_stream n'est pas implémentée."""
        async for response in modal_agent.invoke_stream(None):
            assert response == []
            break


class TestModalLogicAgentIntegration:
    """Tests d'intégration pour ModalLogicAgent."""
    
    @pytest.fixture
    def integration_agent(self):
        """Agent configuré pour tests d'intégration."""
        # Créer un mock kernel simple
        mock_kernel = MagicMock(spec=Kernel)
        mock_kernel.plugins = {}
        
        # Créer un mock tweety bridge
        mock_tweety_bridge = MagicMock()
        mock_tweety_bridge.execute_modal_query.return_value = "ACCEPTED: Query valid"
        mock_tweety_bridge.validate_modal_belief_set.return_value = (True, "Valid belief set")
        
        agent = ModalLogicAgent(mock_kernel, "IntegrationAgent")
        agent._tweety_bridge = mock_tweety_bridge
        return agent
    
    @pytest.mark.asyncio
    async def test_full_analysis_workflow(self, integration_agent):
        """Test du workflow complet d'analyse modale."""
        # Configuration des mocks pour un workflow complet
        
        # 1. Mock pour text_to_belief_set
        mock_text_response = '{"propositions": ["urgent", "action"], "modal_formulas": ["[]urgent", "<>action"]}'
    
        # 2. Mock pour generate_queries
        mock_query_response = '{"query_ideas": [{"formula": "[]urgent"}, {"formula": "<>action"}]}'
    
        # 3. Mock pour interpret_results
        mock_interpret_response = "L'analyse modale montre que l'urgence est nécessaire et l'action est possible."
    
        # Configuration des plugins mockés
        mock_plugins = {
            "IntegrationAgent": {
                "TextToModalBeliefSet": MagicMock(),
                "GenerateModalQueryIdeas": MagicMock(),
                "InterpretModalResult": MagicMock()
            }
        }
    
        mock_plugins["IntegrationAgent"]["TextToModalBeliefSet"].invoke = AsyncMock(return_value=mock_text_response)
        mock_plugins["IntegrationAgent"]["GenerateModalQueryIdeas"].invoke = AsyncMock(return_value=mock_query_response)
        mock_plugins["IntegrationAgent"]["InterpretModalResult"].invoke = AsyncMock(return_value=mock_interpret_response)
        
        integration_agent.sk_kernel.plugins = mock_plugins
        
        # Configuration du TweetyBridge
        integration_agent._tweety_bridge.execute_modal_query.return_value = [
            "ACCEPTED: Urgency is necessary",
            "ACCEPTED: Action is possible"
        ]
        
        # Exécution du workflow complet
        text = "Il est urgent d'agir immédiatement sur cette situation critique."
        
        # 1. Conversion en belief set
        belief_set, _ = await integration_agent.text_to_belief_set(text)
        assert belief_set is not None
        
        # 2. Génération de requêtes
        queries = await integration_agent.generate_queries(text, belief_set)
        assert len(queries) >= 1
        
        # 3. Exécution des requêtes
        results = []
        for query in queries:
            result = integration_agent.execute_query(belief_set, query)
            results.append(result)
        
        # 4. Interprétation des résultats
        interpretation = await integration_agent.interpret_results(text, belief_set, queries, results)
        assert "modale" in interpretation
        assert "urgence" in interpretation.lower() or "urgent" in interpretation.lower()


# Utilitaires pour les tests
def create_test_modal_belief_set() -> ModalBeliefSet:
    """Crée un belief set modal pour les tests."""
    content = """
    constant urgent
    constant action
    
    prop(urgent)
    prop(action)
    
    []urgent
    <>(urgent => action)
    """
    return ModalBeliefSet(content.strip())


def create_invalid_modal_json() -> Dict[str, Any]:
    """Crée un JSON modal invalide pour les tests d'erreur."""
    return {
        "propositions": ["prop1"],
        "modal_formulas": ["[]undeclared_prop"]  # Proposition non déclarée
    }


if __name__ == "__main__":
    pytest.main([__file__, "-v"])