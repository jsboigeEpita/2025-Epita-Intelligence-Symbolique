# Fichier : tests/orchestration/test_analysis_runner.py

import pytest
from unittest.mock import patch, MagicMock
import io
import sys
from contextlib import redirect_stdout

# Importer la fonction main du script à tester
from argumentation_analysis.orchestration.analysis_runner_v2 import run_analysis_v2 as analysis_runner_main
from semantic_kernel.contents import AuthorRole

@pytest.mark.asyncio
@patch('argumentation_analysis.orchestration.analysis_runner.AppSettings')
@patch('argumentation_analysis.orchestration.analysis_runner.KernelBuilder')
@patch('argumentation_analysis.orchestration.analysis_runner.AgentFactory')
@patch('argumentation_analysis.orchestration.analysis_runner.AgentGroupChat')
async def test_analysis_runner_full_integration_flow(
    mock_agent_group_chat, mock_agent_factory, mock_kernel_builder, mock_app_settings,
    capsys
):
    """
    Teste le flux d'intégration complet du analysis_runner.
    Ce test simule la configuration du kernel, la création des agents,
    et l'invocation du chat de groupe pour s'assurer que tous les composants
    sont appelés correctement et que la sortie est gérée comme prévu.
    """
    # --- Arrangement (Arrange) ---
    
    # Simuler AppSettings pour retourner des settings contrôlés
    mock_settings_instance = mock_app_settings.return_value
    mock_settings_instance.service_manager.default_llm_service_id = "mock_service"
    
    # Simuler KernelBuilder pour retourner un kernel mocké
    mock_kernel = MagicMock()
    mock_kernel_builder.create_kernel.return_value = mock_kernel
    
    # Simuler AgentFactory pour retourner des agents mockés
    mock_fallacy_agent = MagicMock()
    mock_fallacy_agent.name = "Fallacy_Analyst"
    mock_manager_agent = MagicMock()
    mock_manager_agent.name = "Project_Manager"
    
    mock_factory_instance = mock_agent_factory.return_value
    mock_factory_instance.create_informal_fallacy_agent.return_value = mock_fallacy_agent
    mock_factory_instance.create_project_manager_agent.return_value = mock_manager_agent
    
    # Simuler AgentGroupChat pour retourner un historique de chat prédéfini
    mock_chat_instance = mock_agent_group_chat.return_value
    # Créer un générateur asynchrone pour simuler le comportement de invoke
    async def mock_invoke_generator():
        msg1 = MagicMock()
        msg1.role = AuthorRole.USER
        msg1.name = "User"
        msg1.content = "Initial text"
        yield msg1
        
        msg2 = MagicMock()
        msg2.role = AuthorRole.ASSISTANT
        msg2.name = "Project_Manager"
        msg2.content = "Analysis complete"
        yield msg2

    mock_chat_instance.invoke.return_value = mock_invoke_generator()

    # --- Action (Act) ---
    # Le script `main` est exécuté. `capsys` va capturer toute sortie vers stdout/stderr.
    await analysis_runner_main()

    # --- Affirmation (Assert) ---

    # Vérifier que les méthodes clés ont été appelées
    mock_app_settings.assert_called_once()
    mock_kernel_builder.create_kernel.assert_called_once_with(mock_settings_instance)
    
    mock_agent_factory.assert_called_once_with(mock_kernel, "mock_service")
    mock_factory_instance.create_informal_fallacy_agent.assert_called_once()
    mock_factory_instance.create_project_manager_agent.assert_called_once()
    
    mock_agent_group_chat.assert_called_once()
    mock_chat_instance.invoke.assert_called_once()
    
    # Récupérer la sortie capturée par la fixture `capsys`
    captured = capsys.readouterr()
    output = captured.out

    # Vérifier que la sortie finale contient les informations attendues de l'historique
    # Le premier message vient du `chat_history` créé dans le script principal
    assert "[USER] - User:" in output
    assert "Le sénateur prétend que sa loi va créer des emplois" in output

    # Les messages suivants viennent de notre mock de `invoke`
    # Note: les noms d'agents sont mockés, donc on vérifie le contenu
    assert "Initial text" in output
    assert "Project_Manager" in output
    assert "Analysis complete" in output
    