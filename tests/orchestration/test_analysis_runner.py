# Fichier : tests/orchestration/test_analysis_runner.py
# Ce fichier de test est temporairement désactivé.
# Il ciblait `analysis_runner.py`, qui a été remplacé par `analysis_runner_v2.py`.
# Les tests doivent être réécrits pour correspondre à la nouvelle architecture de l'orchestrateur.

import pytest

@pytest.mark.skip(
    reason="Test obsolète suite au refactoring de analysis_runner.py vers analysis_runner_v2.py"
)
def test_placeholder():
    pass

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
    mock_agent_group_chat = MagicMock()
    
    # --- Act (Action) ---
    
    # Importer et exécuter le module à tester
    from argumentation_analysis.orchestration.analysis_runner import AnalysisRunner
    
    # Créer l'instance avec les mocks
    runner = AnalysisRunner(mock_settings_instance)
    
    # Exécuter le test
    result = await runner.run_full_analysis("Test text for integration")
    
    # --- Assert (Vérification) ---
    
    # Vérifier que le kernel a été créé avec les bons paramètres
    mock_kernel_builder.create_kernel.assert_called_once()
    kernel_args = mock_kernel_builder.create_kernel.call_args[0]
    assert kernel_args.service_manager == mock_settings_instance
    assert kernel_args.llm_service_id == "mock_service"
    
    # Vérifier que les agents ont été créés via la factory
    mock_agent_factory.create_informal_fallacy_agent.assert_called_once()
    mock_agent_factory.create_project_manager_agent.assert_called_once()
    
    # Vérifier que le chat de groupe a été créé
    assert hasattr(result, 'agent_group_chat')
    
    # Vérifier que les agents ont été ajoutés au chat
    mock_agent_group_chat.add_agent.assert_called()
    
    # Vérifier que le chat a été démarré
    mock_agent_group_chat.start.assert_called_once()
    
    # Vérifier que les agents ont été exécutés
    assert mock_fallacy_agent.analyze.called
    assert mock_manager_agent.analyze.called
    
    # Vérifier la structure du résultat
    assert result["status"] == "success"
    assert "conversation_state" in result
    assert "report" in result
    assert "text_analyzed" in result
    assert result["text_analyzed"] == "Test text for integration"
    assert result["mode"] == "demo"
