import pytest # type: ignore
from unittest.mock import MagicMock, patch, AsyncMock

from semantic_kernel import Kernel # type: ignore

from argumentation_analysis.agents.core.pm.sherlock_enquete_agent import SherlockEnqueteAgent, SHERLOCK_ENQUETE_AGENT_SYSTEM_PROMPT
from argumentation_analysis.agents.core.pm.pm_agent import ProjectManagerAgent
# from argumentation_analysis.agents.core.pm.pm_definitions import PM_INSTRUCTIONS # Plus utilisé directement ici

# Définir un nom d'agent de test pour éviter les conflits potentiels et pour la clarté
TEST_AGENT_NAME = "TestSherlockAgent"

@pytest.fixture
def mock_kernel() -> MagicMock:
    """Fixture pour créer un mock de Kernel."""
    return MagicMock(spec=Kernel)

def test_sherlock_enquete_agent_instanciation(mock_kernel: MagicMock, mocker: MagicMock) -> None:
    """
    Teste l'instanciation correcte de SherlockEnqueteAgent et vérifie l'appel au constructeur parent.
    """
    # Espionner le constructeur de la classe parente ProjectManagerAgent
    spy_super_init = mocker.spy(ProjectManagerAgent, "__init__")

    # Instancier SherlockEnqueteAgent
    agent = SherlockEnqueteAgent(kernel=mock_kernel, agent_name=TEST_AGENT_NAME)

    # Vérifier que l'agent est une instance de SherlockEnqueteAgent
    assert isinstance(agent, SherlockEnqueteAgent)
    assert agent.name == TEST_AGENT_NAME
    # Vérifier que le logger a été configuré avec le nom de l'agent
    assert agent.logger.name == f"agent.{agent.__class__.__name__}.{TEST_AGENT_NAME}"


    # Vérifier que le constructeur de ProjectManagerAgent a été appelé avec les bons arguments
    spy_super_init.assert_called_once_with(
        agent,  # l'instance self de SherlockEnqueteAgent
        mock_kernel,
        agent_name=TEST_AGENT_NAME,
        system_prompt=SHERLOCK_ENQUETE_AGENT_SYSTEM_PROMPT  # Vérifier le nouveau prompt par défaut
    )

def test_sherlock_enquete_agent_instanciation_with_custom_prompt(mock_kernel: MagicMock, mocker: MagicMock) -> None:
    """
    Teste l'instanciation de SherlockEnqueteAgent avec un prompt système personnalisé.
    """
    custom_prompt = "Instructions personnalisées pour Sherlock."
    spy_super_init = mocker.spy(ProjectManagerAgent, "__init__")

    agent = SherlockEnqueteAgent(kernel=mock_kernel, agent_name=TEST_AGENT_NAME, system_prompt=custom_prompt)

    assert isinstance(agent, SherlockEnqueteAgent)
    assert agent.name == TEST_AGENT_NAME
    assert agent.system_prompt == custom_prompt

    spy_super_init.assert_called_once_with(
        agent,
        mock_kernel,
        agent_name=TEST_AGENT_NAME,
        system_prompt=custom_prompt
    )

def test_sherlock_enquete_agent_default_name_and_prompt(mock_kernel: MagicMock, mocker: MagicMock) -> None:
    """
    Teste l'instanciation de SherlockEnqueteAgent avec le nom et le prompt par défaut.
    """
    spy_super_init = mocker.spy(ProjectManagerAgent, "__init__")

    agent = SherlockEnqueteAgent(kernel=mock_kernel)

    assert isinstance(agent, SherlockEnqueteAgent)
    assert agent.name == "SherlockEnqueteAgent" # Nom par défaut
    assert agent.system_prompt == SHERLOCK_ENQUETE_AGENT_SYSTEM_PROMPT # Vérifier le nouveau prompt par défaut

    spy_super_init.assert_called_once_with(
        agent,
        mock_kernel,
        agent_name="SherlockEnqueteAgent",
        system_prompt=SHERLOCK_ENQUETE_AGENT_SYSTEM_PROMPT
    )

@pytest.mark.asyncio
async def test_get_current_case_description(mock_kernel: MagicMock) -> None:
    """
    Teste la méthode get_current_case_description de SherlockEnqueteAgent.
    """
    agent = SherlockEnqueteAgent(kernel=mock_kernel, agent_name=TEST_AGENT_NAME)

    # Cas 1: invoke retourne un objet avec un attribut 'value'
    expected_description_value_attr = "Description de l'affaire (via value)"
    mock_invoke_result_value_attr = MagicMock()
    mock_invoke_result_value_attr.value = expected_description_value_attr
    mock_kernel.invoke = AsyncMock(return_value=mock_invoke_result_value_attr) # Simule une coroutine

    description = await agent.get_current_case_description()
    
    mock_kernel.invoke.assert_called_once_with(
        plugin_name="EnqueteStatePlugin",
        function_name="get_case_description"
    )
    assert description == expected_description_value_attr

    # Réinitialiser le mock pour le cas suivant
    mock_kernel.invoke.reset_mock()

    # Cas 2: invoke retourne directement la valeur
    expected_description_direct = "Description de l'affaire (direct)"
    mock_kernel.invoke = AsyncMock(return_value=expected_description_direct) # Simule une coroutine

    description_direct = await agent.get_current_case_description()

    mock_kernel.invoke.assert_called_once_with(
        plugin_name="EnqueteStatePlugin",
        function_name="get_case_description"
    )
    assert description_direct == expected_description_direct
    
    # Réinitialiser le mock pour le cas d'erreur
    mock_kernel.invoke.reset_mock()

    # Cas 3: Gestion d'erreur si invoke échoue
    mock_kernel.invoke = AsyncMock(side_effect=Exception("Test error")) # Simule une coroutine qui lève une exception
    
    # Patch logger pour vérifier les messages d'erreur
    with patch.object(agent.logger, 'error') as mock_logger_error:
        error_description = await agent.get_current_case_description()
        
        mock_kernel.invoke.assert_called_once_with(
            plugin_name="EnqueteStatePlugin",
            function_name="get_case_description"
        )
        assert error_description == "Erreur: Impossible de récupérer la description de l'affaire."
        mock_logger_error.assert_called_once()
        assert "Erreur lors de la récupération de la description de l'affaire: Test error" in mock_logger_error.call_args[0][0]
@pytest.mark.asyncio
async def test_add_new_hypothesis(mock_kernel: MagicMock) -> None:
    """
    Teste la méthode add_new_hypothesis de SherlockEnqueteAgent.
    """
    agent = SherlockEnqueteAgent(kernel=mock_kernel, agent_name=TEST_AGENT_NAME)
    hypothesis_text = "Le coupable est le Colonel Moutarde."
    confidence_score = 0.75
    expected_invoke_result = {"id": "hyp_123", "text": hypothesis_text, "confidence": confidence_score}

    # Cas 1: invoke retourne un objet avec un attribut 'value'
    mock_invoke_result_value_attr = MagicMock()
    mock_invoke_result_value_attr.value = expected_invoke_result
    mock_kernel.invoke = AsyncMock(return_value=mock_invoke_result_value_attr)

    result = await agent.add_new_hypothesis(hypothesis_text, confidence_score)

    mock_kernel.invoke.assert_called_once_with(
        plugin_name="EnqueteStatePlugin",
        function_name="add_hypothesis",
        text=hypothesis_text,
        confidence_score=confidence_score
    )
    assert result == expected_invoke_result

    # Réinitialiser le mock pour le cas suivant
    mock_kernel.invoke.reset_mock()

    # Cas 2: invoke retourne directement la valeur
    mock_kernel.invoke = AsyncMock(return_value=expected_invoke_result)

    result_direct = await agent.add_new_hypothesis(hypothesis_text, confidence_score)

    mock_kernel.invoke.assert_called_once_with(
        plugin_name="EnqueteStatePlugin",
        function_name="add_hypothesis",
        text=hypothesis_text,
        confidence_score=confidence_score
    )
    assert result_direct == expected_invoke_result
    
    # Réinitialiser le mock pour le cas d'erreur
    mock_kernel.invoke.reset_mock()

    # Cas 3: Gestion d'erreur si invoke échoue
    mock_kernel.invoke = AsyncMock(side_effect=Exception("Test error adding hypothesis"))
    
    with patch.object(agent.logger, 'error') as mock_logger_error:
        error_result = await agent.add_new_hypothesis(hypothesis_text, confidence_score)
        
        mock_kernel.invoke.assert_called_once_with(
            plugin_name="EnqueteStatePlugin",
            function_name="add_hypothesis",
            text=hypothesis_text,
            confidence_score=confidence_score
        )
        assert error_result is None
        mock_logger_error.assert_called_once()
        assert "Erreur lors de l'ajout de l'hypothèse: Test error adding hypothesis" in mock_logger_error.call_args[0][0]