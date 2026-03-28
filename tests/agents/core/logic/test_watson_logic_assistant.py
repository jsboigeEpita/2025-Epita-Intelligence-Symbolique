import openai
from semantic_kernel.contents import ChatHistory
from semantic_kernel.core_plugins import ConversationSummaryPlugin
from config.unified_config import UnifiedConfig

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from semantic_kernel import Kernel
from semantic_kernel.functions import KernelArguments

from argumentation_analysis.agents.core.logic.watson_logic_assistant import (
    WatsonLogicAssistant,
    WATSON_LOGIC_ASSISTANT_SYSTEM_PROMPT,
)
from argumentation_analysis.agents.core.logic.propositional_logic_agent import (
    PropositionalLogicAgent,
)
from argumentation_analysis.agents.factory import AgentFactory
from argumentation_analysis.config.settings import AppSettings

# Définir un nom d'agent de test
TEST_AGENT_NAME = "TestWatsonAssistant"


# mock_kernel fixture removed - using mock_kernel_with_llm from conftest for Pydantic V2 compatibility


@pytest.fixture
def agent_factory(mock_kernel_with_llm) -> AgentFactory:
    """Fixture for creating an AgentFactory instance with Pydantic V2 compatible LLM.

    Uses mock_kernel_with_llm from conftest.py for Pydantic V2 compatibility.
    This fixes ValidationError when creating Watson agents that inherit ChatCompletionAgent.
    """
    # Créer une instance de configuration de base pour la factory
    mock_settings = AppSettings()
    # On peut surcharger des valeurs si nécessaire pour les tests
    mock_settings.service_manager.default_llm_service_id = "test_llm_service"
    return AgentFactory(
        kernel=mock_kernel_with_llm,
        llm_service_id=mock_settings.service_manager.default_llm_service_id,
    )


@pytest.fixture
def mock_tweety_bridge() -> MagicMock:
    """Fixture pour créer un mock de TweetyBridge."""
    mock_bridge = MagicMock()
    # Simuler que la JVM est prête pour éviter les erreurs dans le constructeur de PropositionalLogicAgent
    mock_bridge.is_jvm_ready.return_value = True
    return mock_bridge


@pytest.mark.llm_integration
def test_watson_logic_assistant_instanciation(
    agent_factory: AgentFactory, mock_tweety_bridge: MagicMock
) -> None:
    """
    Teste l'instanciation correcte de WatsonLogicAssistant via l'AgentFactory.
    """
    with patch(
        "argumentation_analysis.agents.core.logic.propositional_logic_agent.TweetyBridge",
        return_value=mock_tweety_bridge,
    ):
        # The factory's create_watson_agent has a potential issue passing an unexpected 'service_id'.
        # Assuming this is resolved or handled by mocks for the test to pass.
        agent = agent_factory.create_watson_agent(agent_name=TEST_AGENT_NAME)

    assert isinstance(agent, WatsonLogicAssistant)
    assert agent.name == TEST_AGENT_NAME
    # The logger name might change slightly depending on the base class __init_subclass__ if any
    assert agent.logger.name.endswith(f".{TEST_AGENT_NAME}")


@pytest.mark.llm_integration
def test_watson_logic_assistant_instanciation_with_custom_prompt(
    agent_factory: AgentFactory, mock_tweety_bridge: MagicMock
) -> None:
    """
    Teste l'instanciation de WatsonLogicAssistant avec un prompt système personnalisé en utilisant l'AgentFactory.
    """
    custom_prompt = "Instructions personnalisées pour Watson."
    with patch(
        "argumentation_analysis.agents.core.logic.propositional_logic_agent.TweetyBridge",
        return_value=mock_tweety_bridge,
    ):
        agent = agent_factory.create_watson_agent(
            agent_name=TEST_AGENT_NAME, system_prompt=custom_prompt
        )

    assert isinstance(agent, WatsonLogicAssistant)
    assert agent.name == TEST_AGENT_NAME
    assert agent.system_prompt == custom_prompt


@pytest.mark.llm_integration
def test_watson_logic_assistant_default_name_and_prompt(
    agent_factory: AgentFactory, mock_tweety_bridge: MagicMock
) -> None:
    """
    Teste l'instanciation de WatsonLogicAssistant avec le nom et le prompt par défaut via l'AgentFactory.
    """
    with patch(
        "argumentation_analysis.agents.core.logic.propositional_logic_agent.TweetyBridge",
        return_value=mock_tweety_bridge,
    ):
        agent = agent_factory.create_watson_agent()

    assert isinstance(agent, WatsonLogicAssistant)
    assert agent.name == "Watson"
    assert agent.system_prompt == WATSON_LOGIC_ASSISTANT_SYSTEM_PROMPT


@pytest.mark.asyncio
@pytest.mark.llm_integration
async def test_get_agent_belief_set_content(
    mock_kernel_with_llm: Kernel, mock_tweety_bridge: MagicMock
) -> None:
    """
    Teste la méthode get_agent_belief_set_content de WatsonLogicAssistant.
    Creates agent directly (not via factory) to avoid Pydantic V2 ValidationError
    during setup_agent_components() with mock tweety bridge.
    Uses object.__setattr__ to patch invoke on Pydantic V2 frozen Kernel.
    """
    # Pre-install mock invoke on kernel (Pydantic V2 frozen model)
    mock_invoke = AsyncMock()
    object.__setattr__(mock_kernel_with_llm, "invoke", mock_invoke)

    agent = WatsonLogicAssistant(
        kernel=mock_kernel_with_llm,
        agent_name=TEST_AGENT_NAME,
        tweety_bridge=mock_tweety_bridge,
    )

    belief_set_id = "test_belief_set_001"

    # Cas 1: invoke retourne un objet avec un attribut 'value'
    expected_content_value_attr = "Contenu de l'ensemble de croyances (via value)"
    mock_invoke_result_value_attr = MagicMock()
    mock_invoke_result_value_attr.value = expected_content_value_attr
    mock_invoke.return_value = mock_invoke_result_value_attr

    content = await agent.get_agent_belief_set_content(belief_set_id)
    mock_invoke.assert_called_once_with(
        plugin_name="EnqueteStatePlugin",
        function_name="get_belief_set_content",
        arguments=KernelArguments(belief_set_id=belief_set_id),
    )
    assert content == expected_content_value_attr

    # Cas 2: invoke retourne directement la valeur
    mock_invoke.reset_mock()
    expected_content_direct = "Contenu de l'ensemble de croyances (direct)"
    mock_invoke.return_value = expected_content_direct

    content_direct = await agent.get_agent_belief_set_content(belief_set_id)
    mock_invoke.assert_called_once_with(
        plugin_name="EnqueteStatePlugin",
        function_name="get_belief_set_content",
        arguments=KernelArguments(belief_set_id=belief_set_id),
    )
    assert content_direct == expected_content_direct

    # Cas 3: invoke retourne None (simulant un belief set non trouvé ou vide)
    mock_invoke.reset_mock()
    mock_invoke.return_value = None

    content_none = await agent.get_agent_belief_set_content(belief_set_id)
    mock_invoke.assert_called_once_with(
        plugin_name="EnqueteStatePlugin",
        function_name="get_belief_set_content",
        arguments=KernelArguments(belief_set_id=belief_set_id),
    )
    assert content_none is None

    # Cas 4: Gestion d'erreur si invoke échoue
    mock_invoke.reset_mock()
    mock_invoke.side_effect = Exception("Test error on get_belief_set_content")

    with patch.object(agent.logger, "error") as mock_logger_error:
        error_content = await agent.get_agent_belief_set_content(belief_set_id)

        mock_invoke.assert_called_once_with(
            plugin_name="EnqueteStatePlugin",
            function_name="get_belief_set_content",
            arguments=KernelArguments(belief_set_id=belief_set_id),
        )
        assert error_content is None
        mock_logger_error.assert_called_once()
        assert (
            f"Erreur lors de la récupération du contenu de l'ensemble de croyances {belief_set_id}: Test error on get_belief_set_content"
            in mock_logger_error.call_args[0][0]
        )


@pytest.mark.llm_integration
def test_watson_tools_validate_formula(mock_tweety_bridge: MagicMock) -> None:
    """Test WatsonTools.validate_formula calls TweetyBridge correctly."""
    from argumentation_analysis.agents.core.logic.watson_logic_assistant import (
        WatsonTools,
    )

    mock_tweety_bridge.validate_formula.return_value = (True, "Valid")
    tools = WatsonTools(tweety_bridge=mock_tweety_bridge, constants=["A", "B"])

    result = tools.validate_formula("A & B")
    assert result is True
    mock_tweety_bridge.validate_formula.assert_called_once()


@pytest.mark.llm_integration
def test_watson_tools_validate_formula_invalid(mock_tweety_bridge: MagicMock) -> None:
    """Test WatsonTools.validate_formula returns False for invalid formulas."""
    from argumentation_analysis.agents.core.logic.watson_logic_assistant import (
        WatsonTools,
    )

    mock_tweety_bridge.validate_formula.return_value = (False, "Syntax error")
    tools = WatsonTools(tweety_bridge=mock_tweety_bridge, constants=[])

    result = tools.validate_formula("A &&& B")
    assert result is False


@pytest.mark.llm_integration
def test_watson_tools_formal_step_by_step_analysis(
    mock_tweety_bridge: MagicMock,
) -> None:
    """Test WatsonTools.formal_step_by_step_analysis returns structured JSON."""
    from argumentation_analysis.agents.core.logic.watson_logic_assistant import (
        WatsonTools,
    )

    tools = WatsonTools(tweety_bridge=mock_tweety_bridge)
    result = tools.formal_step_by_step_analysis(
        problem_description="Si A alors B\nA et C\nNon D ou E"
    )
    assert "Voyons..." in result
    assert "formal_step_by_step_analysis" in result or "RIGOROUS_FORMAL" in result
