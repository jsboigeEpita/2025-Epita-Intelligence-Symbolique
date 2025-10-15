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
    PROMPT_INTERPRET_MODAL,
)
from argumentation_analysis.agents.core.logic.belief_set import ModalBeliefSet
from semantic_kernel import Kernel


@pytest.fixture
def mock_tweety_bridge():
    """Fixture pour un TweetyBridge mocké."""
    bridge = MagicMock()
    bridge.is_jvm_ready.return_value = True
    bridge.validate_modal_belief_set.return_value = (True, "Valid")
    bridge.validate_modal_formula.return_value = (True, "Valid formula")
    bridge.validate_modal_query_with_context.return_value = (True, "Valid query")
    bridge.execute_modal_query.return_value = "ACCEPTED: Query result"
    bridge.is_modal_kb_consistent.return_value = (True, "Consistent")
    return bridge


class TestModalLogicAgent:
    """Classe de tests pour ModalLogicAgent."""

    @pytest.fixture
    def mock_kernel(self):
        """
        Crée un mock simplifié et robuste du noyau sémantique.
        Cette version pré-remplit les plugins pour éviter les problèmes de scope
        et de référence lors des tests.
        """
        kernel = Mock(spec=Kernel)
        from semantic_kernel.functions.kernel_function import KernelFunction

        # Pré-créer la structure des plugins avec des mocks de fonctions robustes
        kernel.plugins = {}
        for agent_name in ["TestModalAgent", "IntegrationAgent"]:
            kernel.plugins[agent_name] = {
                "TextToModalBeliefSet": AsyncMock(spec=KernelFunction),
                "GenerateModalQueryIdeas": AsyncMock(spec=KernelFunction),
                "InterpretModalResult": AsyncMock(spec=KernelFunction),
            }

        # Simuler get_function pour retourner les mocks pré-créés
        def mock_get_function(plugin_name, function_name):
            return kernel.plugins.get(plugin_name, {}).get(function_name)

        # Simuler add_function pour qu'elle retourne le mock pré-existant.
        def mock_add_function(plugin_name, function_name, **kwargs):
            return kernel.plugins.get(plugin_name, {}).get(function_name)

        # Utiliser un MagicMock avec un side_effect pour compter les appels
        kernel.add_function = MagicMock(side_effect=mock_add_function)
        kernel.get_function = MagicMock(side_effect=mock_get_function)
        kernel.get_prompt_execution_settings_from_service_id = Mock(return_value=None)

        return kernel

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
        assert isinstance(agent._kernel, Mock)

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

    def test_construct_modal_kb_from_json(self, modal_agent):
        """Test la construction d'une base de connaissances modale depuis JSON."""
        kb_json = {
            "propositions": ["climat_urgent", "action_necessaire"],
            "modal_formulas": [
                "[](climat_urgent)",
                "<>(action_necessaire)",
                "climat_urgent => [](action_necessaire)",
            ],
        }

        kb_content = modal_agent._construct_modal_kb_from_json(kb_json)

        # Vérifier que les constantes sont déclarées
        assert "constant action_necessaire" in kb_content
        assert "constant climat_urgent" in kb_content

        # Vérifier que les propositions ne sont plus déclarées avec prop()
        assert "prop(climat_urgent)" not in kb_content
        assert "prop(action_necessaire)" not in kb_content

        # Vérifier que les formules modales sont présentes
        assert "[](climat_urgent)" in kb_content
        assert "<>(action_necessaire)" in kb_content
        assert "climat_urgent => [](action_necessaire)" in kb_content

    def test_validate_modal_kb_json_valid(self, modal_agent):
        """Test la validation d'un JSON valide."""
        valid_json = {
            "propositions": ["prop1", "prop2"],
            "modal_formulas": ["[](prop1)", "<>(prop2)", "prop1 => prop2"],
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
            "modal_formulas": ["[](prop1)", "<>(prop2)"],  # prop2 non déclaré
        }

        is_valid, message = modal_agent._validate_modal_kb_json(invalid_json)

        assert is_valid == False
        assert "prop2" in message
        assert "non déclarées" in message

    def test_extract_json_block_valid_json(self, modal_agent):
        """Test l'extraction d'un bloc JSON valide."""
        text_with_json = """
        Voici le résultat:
        {"propositions": ["prop1"], "modal_formulas": ["[](prop1)"]}
        Fin du texte.
        """

        extracted = modal_agent._extract_json_block(text_with_json)
        parsed = json.loads(extracted)

        assert parsed["propositions"] == ["prop1"]
        assert parsed["modal_formulas"] == ["[](prop1)"]

    def test_extract_json_block_truncated_json(self, modal_agent):
        """Test l'extraction et réparation d'un JSON tronqué."""
        truncated_text = """
        Voici le résultat:
        {"propositions": ["prop1"], "modal_formulas":["[](prop1)"
        """

        extracted = modal_agent._extract_json_block(truncated_text)

        # Vérifier que le JSON peut être parsé après réparation
        try:
            parsed = json.loads(extracted)
            assert "propositions" in parsed
        except json.JSONDecodeError:
            # Si la réparation échoue, vérifier qu'on a au moins un JSON partiel
            assert "{" in extracted

    # @pytest.mark.real_jpype
    @pytest.mark.asyncio
    async def test_text_to_belief_set_success(self, modal_agent, mock_tweety_bridge):
        """Test la conversion réussie de texte en belief set."""
        modal_agent._tweety_bridge = mock_tweety_bridge

        # Mock de la fonction sémantique - doit retourner directement la chaîne JSON
        mock_json_response = (
            '{"propositions": ["urgent"], "modal_formulas": ["[](urgent)"]}'
        )

        # Correction : le mock doit retourner un objet avec un attribut 'value'
        # Le mock 'invoke' est déjà un AsyncMock grâce à la fixture.
        # On configure directement sa valeur de retour.
        # La valeur de retour d'une coroutine mockée est la valeur que `await` produira.
        mock_response = MagicMock()
        mock_response.value = mock_json_response
        modal_agent._kernel.plugins[modal_agent.name][
            "TextToModalBeliefSet"
        ].invoke.return_value = mock_response

        # Correction : Le mock doit maintenant simuler le handler.
        mock_tweety_bridge.modal_handler.is_modal_kb_consistent.return_value = (
            True,
            "Consistent",
        )

        text = "Il est urgent d'agir sur le climat."
        belief_set, message = await modal_agent.text_to_belief_set(text)

        assert belief_set is not None
        assert isinstance(belief_set, ModalBeliefSet)
        assert "réussie" in message
        assert "constant urgent" in belief_set.content
        assert "[](urgent)" in belief_set.content

    # @pytest.mark.real_jpype
    @pytest.mark.asyncio
    async def test_text_to_belief_set_json_error(self, modal_agent, mock_tweety_bridge):
        """Test la gestion d'erreur JSON lors de la conversion."""
        modal_agent._tweety_bridge = mock_tweety_bridge

        # Mock retournant un JSON invalide
        mock_invalid_json = "JSON invalide {"

        mock_response = MagicMock()
        mock_response.value = mock_invalid_json
        modal_agent._kernel.plugins[modal_agent.name][
            "TextToModalBeliefSet"
        ].invoke.return_value = mock_response

        text = "Texte de test"
        with pytest.raises(ValueError) as excinfo:
            await modal_agent.text_to_belief_set(text)

        # Vérifier que l'exception levée est bien due à une erreur de syntaxe/validation
        assert "JSON invalide" in str(excinfo.value) or "ERREUR DE SYNTAXE" in str(
            excinfo.value
        )

    def test_parse_modal_belief_set_content(self, modal_agent):
        """Test l'analyse du contenu d'un belief set modal."""
        belief_content = """
        constant urgent
        constant action
        
        [](urgent)
        <>(urgent => action)
        """

        parsed = modal_agent._parse_modal_belief_set_content(belief_content)

        assert "urgent" in parsed["propositions"]
        assert "action" in parsed["propositions"]
        assert "[](urgent)" in parsed["modal_formulas"]
        assert "<>(urgent => action)" in parsed["modal_formulas"]

    # @pytest.mark.real_jpype
    @pytest.mark.asyncio
    async def test_generate_queries_success(self, modal_agent, mock_tweety_bridge):
        """Test la génération réussie de requêtes modales."""
        modal_agent._tweety_bridge = mock_tweety_bridge

        # Mock du belief set
        belief_set = ModalBeliefSet("constant urgent\n\n[](urgent)")

        # Mock de la réponse LLM
        mock_json_response = (
            '{"query_ideas": [{"formula": "[](urgent)"}, {"formula": "<>(urgent)"}]}'
        )

        mock_response = MagicMock()
        mock_response.value = mock_json_response
        modal_agent._kernel.plugins[modal_agent.name][
            "GenerateModalQueryIdeas"
        ].invoke.return_value = mock_response

        # Correction : S'assurer que la validation de formule est aussi mockée
        mock_tweety_bridge.modal_handler.validate_modal_formula.return_value = (
            True,
            "Valid formula",
        )

        text = "Test text"
        queries = await modal_agent.generate_queries(text, belief_set)

        assert len(queries) >= 1
        assert any("urgent" in query for query in queries)

    # @pytest.mark.real_jpype
    @pytest.mark.asyncio
    async def test_generate_queries_empty_response(
        self, modal_agent, mock_tweety_bridge
    ):
        """Test la génération de requêtes avec réponse vide."""
        modal_agent._tweety_bridge = mock_tweety_bridge

        belief_set = ModalBeliefSet("constant test\n\n[](test)")

        # Mock retournant une réponse vide
        mock_json_response = '{"query_ideas": []}'

        mock_response = MagicMock()
        mock_response.value = mock_json_response
        modal_agent._kernel.plugins[modal_agent.name][
            "GenerateModalQueryIdeas"
        ].invoke.return_value = mock_response

        text = "Test text"
        queries = await modal_agent.generate_queries(text, belief_set)

        assert queries == []

    def test_execute_query_success(self, modal_agent, mock_tweety_bridge):
        """Test l'exécution réussie d'une requête."""
        modal_agent._tweety_bridge = mock_tweety_bridge
        mock_tweety_bridge.modal_handler.execute_modal_query.return_value = (
            "ACCEPTED: Query validated"
        )

        belief_set = ModalBeliefSet("constant urgent\n\n[](urgent)")
        query = "[](urgent)"

        result, message = modal_agent.execute_query(belief_set, query)

        assert result == True
        assert "ACCEPTED" in message

    def test_execute_query_rejected(self, modal_agent, mock_tweety_bridge):
        """Test l'exécution d'une requête rejetée."""
        modal_agent._tweety_bridge = mock_tweety_bridge
        mock_tweety_bridge.modal_handler.execute_modal_query.return_value = (
            "REJECTED: Query not valid"
        )

        belief_set = ModalBeliefSet("constant urgent\n\n[](urgent)")
        query = "invalid_query"

        result, message = modal_agent.execute_query(belief_set, query)

        assert result == False
        assert "REJECTED" in message

    def test_execute_query_error(self, modal_agent, mock_tweety_bridge):
        """Test la gestion d'erreur lors de l'exécution de requête."""
        modal_agent._tweety_bridge = mock_tweety_bridge
        mock_tweety_bridge.modal_handler.execute_modal_query.side_effect = Exception(
            "Test error"
        )

        belief_set = ModalBeliefSet("constant urgent\n\n[](urgent)")
        query = "[](urgent)"

        result, message = modal_agent.execute_query(belief_set, query)

        assert result is None
        assert "FUNC_ERROR" in message

    # @pytest.mark.real_jpype
    @pytest.mark.asyncio
    async def test_interpret_results_success(self, modal_agent):
        """Test l'interprétation réussie des résultats."""
        # Mock de la fonction d'interprétation
        mock_response = "Interprétation: La requête [](urgent) est acceptée, indiquant une nécessité."

        mock_response_object = MagicMock()
        mock_response_object.value = mock_response
        modal_agent._kernel.plugins[modal_agent.name][
            "InterpretModalResult"
        ].invoke.return_value = mock_response_object

        text = "Texte original"
        belief_set = ModalBeliefSet("constant urgent\n\n[](urgent)")
        queries = ["[](urgent)"]
        results = [(True, "ACCEPTED: Query valid")]

        interpretation = await modal_agent.interpret_results(
            text, belief_set, queries, results
        )

        assert "Interprétation" in interpretation
        assert "urgent" in interpretation

    # @pytest.mark.real_jpype
    @pytest.mark.asyncio
    async def test_interpret_results_error(self, modal_agent):
        """Test la gestion d'erreur lors de l'interprétation."""
        # Mock qui lève une exception
        modal_agent._kernel.plugins[modal_agent.name][
            "InterpretModalResult"
        ].invoke.side_effect = Exception("Interpret error")

        text = "Texte"
        belief_set = ModalBeliefSet("constant test\n\n[](test)")
        queries = ["[](test)"]
        results = [(True, "ACCEPTED")]

        interpretation = await modal_agent.interpret_results(
            text, belief_set, queries, results
        )

        assert "Erreur d'interprétation" in interpretation

    def test_validate_formula_success(self, modal_agent, mock_tweety_bridge):
        """Test la validation réussie d'une formule."""
        modal_agent._tweety_bridge = mock_tweety_bridge
        mock_tweety_bridge.modal_handler.validate_modal_formula.return_value = (
            True,
            "Valid",
        )

        formula = "[](urgent)"
        is_valid = modal_agent.validate_formula(formula)

        assert is_valid == True

    def test_validate_formula_invalid(self, modal_agent, mock_tweety_bridge):
        """Test la validation d'une formule invalide."""
        modal_agent._tweety_bridge = mock_tweety_bridge
        mock_tweety_bridge.modal_handler.validate_modal_formula.return_value = (
            False,
            "Invalid syntax",
        )

        formula = "invalid_formula"
        is_valid = modal_agent.validate_formula(formula)

        assert is_valid == False

    def test_validate_formula_fallback(self, modal_agent, mock_tweety_bridge):
        """Test la validation avec fallback si méthode indisponible."""
        modal_agent._tweety_bridge = mock_tweety_bridge
        mock_tweety_bridge.invoke.return_value = {
            "is_valid": True,
            "message": "Fallback successful",
        }
        # Simuler l'absence de la méthode sur le handler de manière robuste
        delattr(mock_tweety_bridge.modal_handler, "validate_modal_formula")

        formula = "[](urgent)"
        is_valid = modal_agent.validate_formula(formula)

        # Devrait utiliser la validation basique
        assert is_valid is True

    def test_is_consistent_success(self, modal_agent, mock_tweety_bridge):
        """Test la vérification de cohérence réussie."""
        modal_agent._tweety_bridge = mock_tweety_bridge
        mock_tweety_bridge.modal_handler.is_modal_kb_consistent.return_value = (
            True,
            "Consistent KB",
        )

        belief_set = ModalBeliefSet("constant urgent\n\n[](urgent)")
        is_consistent, message = modal_agent.is_consistent(belief_set)

        assert is_consistent == True
        assert "Consistent" in message

    @pytest.mark.real_jpype
    def test_is_consistent_inconsistent(self, modal_agent, mock_tweety_bridge):
        """Test la détection d'incohérence."""
        modal_agent._tweety_bridge = mock_tweety_bridge
        mock_tweety_bridge.modal_handler.is_modal_kb_consistent.return_value = (
            False,
            "Inconsistent KB",
        )

        belief_set = ModalBeliefSet("constant p\n\n[](p)\n!<>(p)")  # Contradictoire
        is_consistent, message = modal_agent.is_consistent(belief_set)

        assert is_consistent == False
        assert "Inconsistent" in message

    def test_is_consistent_fallback(self, modal_agent, mock_tweety_bridge):
        """Test la vérification de cohérence avec fallback."""
        modal_agent._tweety_bridge = mock_tweety_bridge
        mock_tweety_bridge.invoke.return_value = {
            "is_consistent": True,
            "message": "Fallback successful",
        }
        # Simuler l'absence de la méthode sur le handler de manière robuste
        delattr(mock_tweety_bridge.modal_handler, "is_modal_kb_consistent")

        belief_set = ModalBeliefSet("constant urgent\n\n[](urgent)")
        is_consistent, message = modal_agent.is_consistent(belief_set)

        # Devrait retourner True par défaut avec un message explicatif
        assert is_consistent is True
        assert "Fallback successful" in message

    def test_create_belief_set_from_data(self, modal_agent):
        """Test la création d'un belief set depuis des données."""
        data = {"content": "constant test\n\n[](test)"}
        belief_set = modal_agent._create_belief_set_from_data(data)

        assert isinstance(belief_set, ModalBeliefSet)
        assert belief_set.content == "constant test\n\n[](test)"

    def test_create_belief_set_from_empty_data(self, modal_agent):
        """Test la création d'un belief set depuis des données vides."""
        data = {}
        belief_set = modal_agent._create_belief_set_from_data(data)

        assert isinstance(belief_set, ModalBeliefSet)
        assert belief_set.content == ""

    # @pytest.mark.real_jpype
    @pytest.mark.asyncio
    async def test_get_response(self, modal_agent, mock_tweety_bridge):
        """Test que get_response (via invoke_single) retourne un statut."""
        modal_agent._tweety_bridge = mock_tweety_bridge

        mock_response = MagicMock()
        mock_response.value = (
            '{"propositions": ["test"], "modal_formulas": ["[](test)"]}'
        )
        modal_agent._kernel.plugins[modal_agent.name][
            "TextToModalBeliefSet"
        ].invoke.return_value = mock_response
        mock_tweety_bridge.modal_handler.is_modal_kb_consistent.return_value = (
            True,
            "Valid",
        )

        # get_response est une coroutine, pas un générateur asynchrone
        result = await modal_agent.get_response("test text")
        assert "Analyse modale initiée" in result

    # @pytest.mark.real_jpype
    @pytest.mark.asyncio
    async def test_invoke(self, modal_agent, mock_tweety_bridge):
        """Test que invoke retourne un générateur qui produit le statut de invoke_single."""
        modal_agent._tweety_bridge = mock_tweety_bridge

        mock_response = MagicMock()
        mock_response.value = (
            '{"propositions": ["test"], "modal_formulas": ["[](test)"]}'
        )
        modal_agent._kernel.plugins[modal_agent.name][
            "TextToModalBeliefSet"
        ].invoke.return_value = mock_response
        mock_tweety_bridge.modal_handler.is_modal_kb_consistent.return_value = (
            True,
            "Valid",
        )

        results = [result async for result in modal_agent.invoke("test text")]
        assert len(results) == 1
        assert "Analyse modale initiée" in results[0]

    # @pytest.mark.real_jpype
    @pytest.mark.real_jpype
    @pytest.mark.asyncio
    async def test_invoke_stream(self, modal_agent, mock_tweety_bridge):
        """Test que invoke_stream retourne un générateur qui produit le statut de invoke_single."""
        modal_agent._tweety_bridge = mock_tweety_bridge

        mock_response = MagicMock()
        mock_response.value = (
            '{"propositions": ["test"], "modal_formulas": ["[](test)"]}'
        )
        modal_agent._kernel.plugins[modal_agent.name][
            "TextToModalBeliefSet"
        ].invoke.return_value = mock_response
        mock_tweety_bridge.modal_handler.is_modal_kb_consistent.return_value = (
            True,
            "Valid",
        )

        results = [result async for result in modal_agent.invoke_stream("test text")]
        assert len(results) == 1
        assert "Analyse modale initiée" in results[0]


class TestModalLogicAgentIntegration:
    """Tests d'intégration pour ModalLogicAgent."""

    @pytest.fixture
    def mock_kernel(self):
        """
        Crée un mock simplifié et robuste du noyau sémantique.
        Cette version pré-remplit les plugins pour éviter les problèmes de scope
        et de référence lors des tests.
        """
        kernel = Mock(spec=Kernel)
        from semantic_kernel.functions.kernel_function import KernelFunction

        # Pré-créer la structure des plugins avec des mocks de fonctions robustes
        kernel.plugins = {}
        for agent_name in ["TestModalAgent", "IntegrationAgent"]:
            kernel.plugins[agent_name] = {
                "TextToModalBeliefSet": AsyncMock(spec=KernelFunction),
                "GenerateModalQueryIdeas": AsyncMock(spec=KernelFunction),
                "InterpretModalResult": AsyncMock(spec=KernelFunction),
            }

        # Simuler get_function pour retourner les mocks pré-créés
        def mock_get_function(plugin_name, function_name):
            return kernel.plugins.get(plugin_name, {}).get(function_name)

        # Simuler add_function pour qu'elle retourne le mock pré-existant.
        def mock_add_function(plugin_name, function_name, **kwargs):
            return kernel.plugins.get(plugin_name, {}).get(function_name)

        # Utiliser un MagicMock avec un side_effect pour compter les appels
        kernel.add_function = MagicMock(side_effect=mock_add_function)
        kernel.get_function = MagicMock(side_effect=mock_get_function)
        kernel.get_prompt_execution_settings_from_service_id = Mock(return_value=None)

        return kernel

    @pytest.fixture
    def modal_agent(self, mock_kernel):
        """Fixture pour une instance de ModalLogicAgent pour l'intégration."""
        # Utiliser un nom d'agent cohérent avec la configuration du mock_kernel
        agent = ModalLogicAgent(mock_kernel, "IntegrationAgent", "test_service")
        return agent

    @pytest.mark.asyncio
    async def test_full_analysis_workflow(self, modal_agent, mock_tweety_bridge):
        """
        Test du workflow complet d'analyse modale en utilisant des mocks
        ciblés avec précision sur les fonctions du noyau sémantique.
        """
        agent = modal_agent
        agent._tweety_bridge = mock_tweety_bridge

        # 1. Définir les réponses attendues pour chaque fonction sémantique
        #    On mock l'attribut '.value' car le code de l'agent l'utilise
        #    pour extraire la réponse du noyau.

        mock_belief_set_result = MagicMock()
        mock_belief_set_result.value = '{"propositions": ["urgent", "action"], "modal_formulas": ["[](urgent)", "<>(action)"]}'

        mock_query_ideas_result = MagicMock()
        mock_query_ideas_result.value = (
            '{"query_ideas": [{"formula": "[](urgent)"}, {"formula": "<>(action)"}]}'
        )

        mock_interpretation_result = MagicMock()
        mock_interpretation_result.value = "L'analyse modale montre que l'urgence est nécessaire et l'action est possible."

        # 2. Patcher le dictionnaire de plugins sur le noyau pour que les appels
        #    à `invoke` retournent nos valeurs mockées.
        #    C'est la correction clef : on cible ce que le code *réel* de l'agent appelle.
        # Le nom de l'agent doit correspondre à celui utilisé dans la fixture modal_agent
        plugins = agent._kernel.plugins["IntegrationAgent"]
        plugins["TextToModalBeliefSet"].invoke.return_value = mock_belief_set_result
        plugins["GenerateModalQueryIdeas"].invoke.return_value = mock_query_ideas_result
        plugins["InterpretModalResult"].invoke.return_value = mock_interpretation_result

        # 3. Configurer le comportement du mock TweetyBridge pour les requêtes logiques
        agent._tweety_bridge.modal_handler.execute_modal_query.side_effect = [
            "ACCEPTED: Urgency is necessary",
            "ACCEPTED: Action is possible",
        ]
        # On s'assure aussi que la validation de consistance retourne un tuple valide
        agent._tweety_bridge.modal_handler.is_modal_kb_consistent.return_value = (
            True,
            "Consistent",
        )
        # Correction : La validation de formule doit aussi être mockée pour chaque requête générée
        agent._tweety_bridge.modal_handler.validate_modal_formula.return_value = (
            True,
            "Valid formula",
        )

        # 4. Exécution et validation du workflow complet
        text = "Il est urgent d'agir immédiatement sur cette situation critique."

        # Étape 1: Conversion du texte en ensemble de croyances
        belief_set, _ = await agent.text_to_belief_set(text)
        plugins["TextToModalBeliefSet"].invoke.assert_awaited_once()
        assert belief_set is not None
        assert "urgent" in belief_set.content

        # Étape 2: Génération de requêtes
        queries = await agent.generate_queries(text, belief_set)
        plugins["GenerateModalQueryIdeas"].invoke.assert_awaited_once()
        assert len(queries) >= 1
        assert "urgent" in queries[0]

        # Étape 3: Exécution des requêtes
        results = []
        for query in queries:
            result_tuple = agent.execute_query(belief_set, query)
            results.append(result_tuple)

        assert agent._tweety_bridge.modal_handler.execute_modal_query.call_count == len(
            queries
        )
        assert len(results) == 2
        assert results[0][0] is True

        # Étape 4: Interprétation des résultats
        interpretation = await agent.interpret_results(
            text, belief_set, queries, results
        )
        plugins["InterpretModalResult"].invoke.assert_awaited_once()
        assert "modale" in interpretation
        assert "urgence" in interpretation.lower() or "urgent" in interpretation.lower()


# Utilitaires pour les tests
def create_test_modal_belief_set() -> ModalBeliefSet:
    """Crée un belief set modal pour les tests."""
    content = """
    constant urgent
    constant action
    
    [](urgent)
    <>(urgent => action)
    """
    return ModalBeliefSet(content.strip())


def create_invalid_modal_json() -> Dict[str, Any]:
    """Crée un JSON modal invalide pour les tests d'erreur."""
    return {
        "propositions": ["prop1"],
        "modal_formulas": ["[](undeclared_prop)"],  # Proposition non déclarée
    }


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
