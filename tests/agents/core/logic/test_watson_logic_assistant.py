# Authentic gpt-4o-mini imports (replacing mocks)
import openai
from semantic_kernel.contents import ChatHistory
from semantic_kernel.core_plugins import ConversationSummaryPlugin
from config.unified_config import UnifiedConfig

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from semantic_kernel import Kernel

from argumentation_analysis.agents.core.logic.watson_logic_assistant import WatsonLogicAssistant, WATSON_LOGIC_ASSISTANT_SYSTEM_PROMPT
from argumentation_analysis.agents.core.logic.propositional_logic_agent import PropositionalLogicAgent

# Définir un nom d'agent de test
TEST_AGENT_NAME = "TestWatsonAssistant"

@pytest.fixture
def mock_kernel() -> MagicMock:
    """Fixture pour créer un mock de Kernel."""
    return MagicMock(spec=Kernel)

@pytest.fixture
def mock_tweety_bridge() -> MagicMock:
    """Fixture pour créer un mock de TweetyBridge."""
    mock_bridge = MagicMock()
    # Simuler que la JVM est prête pour éviter les erreurs dans le constructeur de PropositionalLogicAgent
    mock_bridge.is_jvm_ready.return_value = True
    return mock_bridge

def test_watson_logic_assistant_instanciation(mock_kernel: MagicMock, mock_tweety_bridge: MagicMock, mocker: MagicMock) -> None:
    """
    Teste l'instanciation correcte de WatsonLogicAssistant et vérifie l'appel au constructeur parent.
    """
    # Espionner le constructeur de la classe parente PropositionalLogicAgent
    spy_super_init = mocker.spy(PropositionalLogicAgent, "__init__")
    
    # Patcher l'initialisation de TweetyBridge dans PropositionalLogicAgent pour utiliser notre mock
    # Cela est crucial car PropositionalLogicAgent.__init__ appelle self.setup_agent_components,
    # qui à son tour initialise self._tweety_bridge.
    with patch('argumentation_analysis.agents.core.logic.propositional_logic_agent.TweetyBridge', return_value=mock_tweety_bridge):
        # Instancier WatsonLogicAssistant
        agent = WatsonLogicAssistant(kernel=mock_kernel, agent_name=TEST_AGENT_NAME)

    # Vérifier que l'agent est une instance de WatsonLogicAssistant
    assert isinstance(agent, WatsonLogicAssistant)
    assert agent.name == TEST_AGENT_NAME
    # Vérifier que le logger a été configuré avec le nom de l'agent
    assert agent.logger.name == f"agent.WatsonLogicAssistant.{TEST_AGENT_NAME}"

    # Vérifier que le constructeur de PropositionalLogicAgent a été appelé avec les bons arguments
    # WatsonLogicAssistant passe son nom et son system_prompt au parent.
    spy_super_init.assert_called_once_with(
        agent,  # l'instance self de WatsonLogicAssistant
        mock_kernel,
        agent_name=TEST_AGENT_NAME, # Watson transmet son nom
        system_prompt=WATSON_LOGIC_ASSISTANT_SYSTEM_PROMPT # Watson transmet son prompt par défaut
    )
    
    # Vérifier que _tweety_bridge a été initialisé (via le patch)
    assert agent._tweety_bridge is mock_tweety_bridge
    # Vérifier que is_jvm_ready a été appelé lors de setup_agent_components
    mock_tweety_bridge.is_jvm_ready.assert_called()


def test_watson_logic_assistant_instanciation_with_custom_prompt(mock_kernel: MagicMock, mock_tweety_bridge: MagicMock, mocker: MagicMock) -> None:
    """
    Teste l'instanciation de WatsonLogicAssistant avec un prompt système personnalisé.
    """
    custom_prompt = "Instructions personnalisées pour Watson."
    spy_super_init = mocker.spy(PropositionalLogicAgent, "__init__")

    with patch('argumentation_analysis.agents.core.logic.propositional_logic_agent.TweetyBridge', return_value=mock_tweety_bridge):
        agent = WatsonLogicAssistant(kernel=mock_kernel, agent_name=TEST_AGENT_NAME, system_prompt=custom_prompt)

    assert isinstance(agent, WatsonLogicAssistant)
    assert agent.name == TEST_AGENT_NAME
    assert agent.system_prompt == custom_prompt # Vérifier que le prompt personnalisé est bien stocké

    spy_super_init.assert_called_once_with(
        agent,
        mock_kernel,
        agent_name=TEST_AGENT_NAME,
        system_prompt=custom_prompt # Watson transmet le prompt personnalisé
    )
    assert agent._tweety_bridge is mock_tweety_bridge
    mock_tweety_bridge.is_jvm_ready.assert_called()

def test_watson_logic_assistant_default_name_and_prompt(mock_kernel: MagicMock, mock_tweety_bridge: MagicMock, mocker: MagicMock) -> None:
    """
    Teste l'instanciation de WatsonLogicAssistant avec le nom et le prompt par défaut.
    """
    spy_super_init = mocker.spy(PropositionalLogicAgent, "__init__")

    with patch('argumentation_analysis.agents.core.logic.propositional_logic_agent.TweetyBridge', return_value=mock_tweety_bridge):
        agent = WatsonLogicAssistant(kernel=mock_kernel) # Utilise les valeurs par défaut

    assert isinstance(agent, WatsonLogicAssistant)
    assert agent.name == "WatsonLogicAssistant" # Nom par défaut
    assert agent.system_prompt == WATSON_LOGIC_ASSISTANT_SYSTEM_PROMPT # Vérifier le nouveau prompt par défaut

    spy_super_init.assert_called_once_with(
        agent,
        mock_kernel,
        agent_name="WatsonLogicAssistant", # Nom par défaut transmis
        system_prompt=WATSON_LOGIC_ASSISTANT_SYSTEM_PROMPT # Prompt par défaut de Watson transmis
    )
    assert agent._tweety_bridge is mock_tweety_bridge
    mock_tweety_bridge.is_jvm_ready.assert_called()


@pytest.mark.asyncio
async def test_get_agent_belief_set_content(mock_kernel: MagicMock, mock_tweety_bridge: MagicMock) -> None:
    """
    Teste la méthode get_agent_belief_set_content de WatsonLogicAssistant.
    """
    with patch('argumentation_analysis.agents.core.logic.propositional_logic_agent.TweetyBridge', return_value=mock_tweety_bridge):
        agent = WatsonLogicAssistant(kernel=mock_kernel, agent_name=TEST_AGENT_NAME)

    belief_set_id = "test_belief_set_001"
    
    # Cas 1: invoke retourne un objet avec un attribut 'value'
    expected_content_value_attr = "Contenu de l'ensemble de croyances (via value)"
    mock_invoke_result_value_attr = MagicMock()
    mock_invoke_result_value_attr.value = expected_content_value_attr
    mock_kernel.invoke = AsyncMock(return_value=mock_invoke_result_value_attr)

    content = await agent.get_agent_belief_set_content(belief_set_id)
    
    mock_kernel.invoke.assert_called_once_with(
        plugin_name="EnqueteStatePlugin",
        function_name="get_belief_set_content",
        belief_set_id=belief_set_id
    )
    assert content == expected_content_value_attr

    # Réinitialiser le mock pour le cas suivant
    mock_kernel.invoke.reset_mock()

    # Cas 2: invoke retourne directement la valeur
    expected_content_direct = "Contenu de l'ensemble de croyances (direct)"
    mock_kernel.invoke = AsyncMock(return_value=expected_content_direct)

    content_direct = await agent.get_agent_belief_set_content(belief_set_id)

    mock_kernel.invoke.assert_called_once_with(
        plugin_name="EnqueteStatePlugin",
        function_name="get_belief_set_content",
        belief_set_id=belief_set_id
    )
    assert content_direct == expected_content_direct
    
    # Réinitialiser le mock pour le cas None
    mock_kernel.invoke.reset_mock()

    # Cas 3: invoke retourne None (simulant un belief set non trouvé ou vide)
    mock_kernel.invoke = AsyncMock(return_value=None)
    
    content_none = await agent.get_agent_belief_set_content(belief_set_id)
    
    mock_kernel.invoke.assert_called_once_with(
        plugin_name="EnqueteStatePlugin",
        function_name="get_belief_set_content",
        belief_set_id=belief_set_id
    )
    assert content_none is None

    # Réinitialiser le mock pour le cas d'erreur
    mock_kernel.invoke.reset_mock()
    
    # Cas 4: Gestion d'erreur si invoke échoue
    mock_kernel.invoke = AsyncMock(side_effect=Exception("Test error on get_belief_set_content"))
    
    # Patch logger pour vérifier les messages d'erreur
    with patch.object(agent.logger, 'error') as mock_logger_error:
        error_content = await agent.get_agent_belief_set_content(belief_set_id)
        
        mock_kernel.invoke.assert_called_once_with(
            plugin_name="EnqueteStatePlugin",
            function_name="get_belief_set_content",
            belief_set_id=belief_set_id
        )
        assert error_content is None # La méthode retourne None en cas d'erreur
        mock_logger_error.assert_called_once()
        assert f"Erreur lors de la récupération du contenu de l'ensemble de croyances {belief_set_id}: Test error on get_belief_set_content" in mock_logger_error.call_args[0][0]

# @pytest.mark.asyncio
# async def test_add_new_deduction_result(mock_kernel: MagicMock, mock_tweety_bridge: MagicMock) -> None:
#     """
#     Teste la méthode add_new_deduction_result de WatsonLogicAssistant.
#     NOTE: Cette méthode n'existe pas directement sur l'agent. L'agent est censé
#     appeler une fonction sémantique via kernel.invoke. Ce test doit être réécrit
#     pour refléter cela.
#     """
#     with patch('argumentation_analysis.agents.core.logic.propositional_logic_agent.TweetyBridge', return_value=mock_tweety_bridge):
#         agent = WatsonLogicAssistant(kernel=mock_kernel, agent_name=TEST_AGENT_NAME)
#
#     query_id = "deduction_query_001"
#     formal_result = "Conclusion: X -> Y"
#     natural_language_interpretation = "Si X est vrai, alors Y est vrai."
#     belief_set_id = "bs_alpha"
#
#     expected_content_arg = {
#         "reponse_formelle": formal_result,
#         "interpretation_ln": natural_language_interpretation,
#         "belief_set_id_utilise": belief_set_id,
#         "status_deduction": "success"
#     }
#     expected_invoke_result = {"id": "res_456", "query_id": query_id, "content": expected_content_arg}
#
#     # Cas 1: invoke retourne un objet avec un attribut 'value'
#     mock_invoke_result_value_attr = MagicMock()
#     mock_invoke_result_value_attr.value = expected_invoke_result
#     mock_kernel.invoke = AsyncMock(return_value=mock_invoke_result_value_attr)
#
#     # result = await agent.add_new_deduction_.result(query_id, formal_result, natural_language_interpretation, belief_set_id)
#     # TODO: Réécrire ce test pour vérifier l'appel à kernel.invoke avec les bons paramètres
#     # pour EnqueteStatePlugin.add_result
#
#     # mock_kernel.invoke.assert_called_once_with(
#     #     plugin_name="EnqueteStatePlugin",
#     #     function_name="add_result", # ou le nom correct de la fonction du plugin
#     #     query_id=query_id,
#     #     agent_source="WatsonLogicAssistant", # ou self.name
#     #     content=expected_content_arg
#     # )
#     # assert result == expected_invoke_result
#
#     # Réinitialiser le mock pour le cas suivant
#     mock_kernel.invoke.reset_mock()
#
#     # Cas 2: invoke retourne directement la valeur
#     mock_kernel.invoke = AsyncMock(return_value=expected_invoke_result)
#
#     # result_direct = await agent.add_new_deduction_result(query_id, formal_result, natural_language_interpretation, belief_set_id)
#     # TODO: Réécrire ce test
#
#     # mock_kernel.invoke.assert_called_once_with(
#     #     plugin_name="EnqueteStatePlugin",
#     #     function_name="add_result",
#     #     query_id=query_id,
#     #     agent_source="WatsonLogicAssistant",
#     #     content=expected_content_arg
#     # )
#     # assert result_direct == expected_invoke_result
#
#     # Réinitialiser le mock pour le cas d'erreur
#     mock_kernel.invoke.reset_mock()
#
#     # Cas 3: Gestion d'erreur si invoke échoue
#     mock_kernel.invoke = AsyncMock(side_effect=Exception("Test error adding deduction result"))
#
#     # with patch.object(agent.logger, 'error') as mock_logger_error:
#         # error_result = await agent.add_new_deduction_result(query_id, formal_result, natural_language_interpretation, belief_set_id)
#         # TODO: Réécrire ce test
#
#         # mock_kernel.invoke.assert_called_once_with(
#         #     plugin_name="EnqueteStatePlugin",
#         #     function_name="add_result",
#         #     query_id=query_id,
#         #     agent_source="WatsonLogicAssistant",
#         #     content=expected_content_arg
#         # )
#         # assert error_result is None
#         # mock_logger_error.assert_called_once()
#         # assert f"Erreur lors de l'ajout du résultat de déduction pour la requête {query_id}: Test error adding deduction result" in mock_logger_error.call_args[0][0]