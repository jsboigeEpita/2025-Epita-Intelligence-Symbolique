import pytest
from unittest.mock import MagicMock, patch, ANY, call, AsyncMock
from argumentation_analysis.orchestration.engine.main_orchestrator import MainOrchestrator
from argumentation_analysis.orchestration.engine.config import OrchestrationConfig
from argumentation_analysis.orchestration.engine.strategy import OrchestrationStrategy


@pytest.fixture
def mock_config():
    """Fixture pour une OrchestrationConfig mockée."""
    return MagicMock(spec=OrchestrationConfig)


@pytest.fixture
def mock_kernel():
    """Fixture pour un Kernel Semantic Kernel mocké."""
    return MagicMock(spec="semantic_kernel.Kernel")


@pytest.fixture
def orchestrator(mock_config, mock_kernel):
    """Fixture pour une instance de MainOrchestrator avec des mocks."""
    # On patch les imports des sous-orchestrateurs pour éviter les erreurs d'import
    # si les dépendances ne sont pas installées dans l'environnement de test.
    with patch('argumentation_analysis.orchestration.engine.main_orchestrator.CluedoExtendedOrchestrator', new=MagicMock()), \
         patch('argumentation_analysis.orchestration.engine.main_orchestrator.ConversationOrchestrator', new=MagicMock()), \
         patch('argumentation_analysis.orchestration.engine.main_orchestrator.RealLLMOrchestrator', new=MagicMock()), \
         patch('argumentation_analysis.orchestration.engine.main_orchestrator.LogiqueComplexeOrchestrator', new=MagicMock()), \
         patch('argumentation_analysis.orchestration.operational.direct_executor.DirectOperationalExecutor', new=MagicMock()):
        
        # On passe maintenant le mock_kernel requis par le constructeur.
        return MainOrchestrator(config=mock_config, kernel=mock_kernel)


@pytest.mark.asyncio
@patch('argumentation_analysis.orchestration.engine.main_orchestrator.select_strategy')
async def test_run_analysis_selects_and_executes_correct_strategy(mock_select_strategy, orchestrator):
    """
    Vérifie que run_analysis sélectionne une stratégie et exécute la méthode correspondante.
    Ce test est un exemple simple pour une seule stratégie.
    """
    # Configuration du mock
    test_strategy = OrchestrationStrategy.HIERARCHICAL_FULL
    mock_select_strategy.return_value = test_strategy
    
    # On mock la méthode d'exécution spécifique qui devrait être appelée
    with patch.object(orchestrator, '_execute_hierarchical_full', new_callable=AsyncMock) as mock_execute:
        mock_execute.return_value = {"status": "success", "strategy_used": test_strategy.value}
        
        # Appel de la méthode à tester
        text_input = "Ceci est un texte de test."
        result = await orchestrator.run_analysis(text_input)
        
        # Assertions
        mock_select_strategy.assert_called_once_with(orchestrator.config, text_input, None, None)
        mock_execute.assert_called_once_with(text_input)
        assert result["status"] == "success"
        assert result["strategy_used"] == test_strategy.value


# Liste de toutes les stratégies à tester, en associant la stratégie à sa méthode d'exécution.
# Cela rend le test facilement extensible si de nouvelles stratégies sont ajoutées.
strategy_to_method_map = [
    (OrchestrationStrategy.HIERARCHICAL_FULL, '_execute_hierarchical_full'),
    (OrchestrationStrategy.STRATEGIC_ONLY, '_execute_strategic_only'),
    (OrchestrationStrategy.TACTICAL_COORDINATION, '_execute_tactical_coordination'),
    (OrchestrationStrategy.OPERATIONAL_DIRECT, '_execute_operational_direct'),
    (OrchestrationStrategy.SPECIALIZED_DIRECT, '_execute_specialized_direct'),
    (OrchestrationStrategy.HYBRID, '_execute_hybrid'),
    (OrchestrationStrategy.SERVICE_MANAGER, '_execute_service_manager'),
    (OrchestrationStrategy.FALLBACK, '_execute_fallback'),
    (OrchestrationStrategy.COMPLEX_PIPELINE, '_execute_complex_pipeline'),
    (OrchestrationStrategy.MANUAL_SELECTION, '_execute_manual_selection'),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("strategy, method_name", strategy_to_method_map)
@patch('argumentation_analysis.orchestration.engine.main_orchestrator.select_strategy')
async def test_run_analysis_routes_to_all_strategies(mock_select_strategy, strategy, method_name, orchestrator):
    """
    Vérifie que run_analysis appelle la bonne méthode d'exécution pour chaque stratégie possible.
    Ce test paramétré garantit que le "routage" interne de run_analysis est correct.
    """
    # Configuration des mocks
    mock_select_strategy.return_value = strategy
    
    # On mock la méthode d'exécution qui devrait être appelée pour la stratégie en cours
    with patch.object(orchestrator, method_name, new_callable=AsyncMock) as mock_execute_method:
        mock_execute_method.return_value = {"status": "success", "strategy_used": strategy.value}
        
        text_input = f"Input for {strategy.name}"
        source_info = {"source": "test"}
        custom_config = {"mode": "fast"}
        
        # Appel de la méthode à tester
        result = await orchestrator.run_analysis(text_input, source_info, custom_config)
        
        # Assertions
        mock_select_strategy.assert_called_with(orchestrator.config, text_input, source_info, custom_config)
        mock_execute_method.assert_called_once_with(text_input)
        assert result["strategy_used"] == strategy.value


@pytest.mark.asyncio
@patch('argumentation_analysis.orchestration.engine.main_orchestrator.select_strategy')
async def test_run_analysis_handles_unknown_strategy(mock_select_strategy, orchestrator):
    """
    Vérifie le comportement de run_analysis lorsqu'une stratégie inconnue ou nulle est retournée.
    """
    # Configuration du mock pour retourner une valeur inattendue
    mock_select_strategy.return_value = None
    
    text_input = "Test avec une stratégie inconnue."
    result = await orchestrator.run_analysis(text_input)
    
    # Assertions
    assert result["status"] == "error"
    assert "Unknown or unsupported strategy" in result["message"]
    assert result["result"] is None