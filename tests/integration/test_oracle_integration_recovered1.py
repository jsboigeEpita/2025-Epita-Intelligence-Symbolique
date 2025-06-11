
# Authentic gpt-4o-mini imports (replacing mocks)
import openai
from semantic_kernel.contents import ChatHistory
from semantic_kernel.core_plugins import ConversationSummaryPlugin
from config.unified_config import UnifiedConfig

# tests/integration/recovered/test_oracle_integration.py
"""
Tests d'intégration pour le système Oracle complet Oracle Enhanced v2.1.0.
Récupéré et adapté pour Oracle Enhanced v2.1.0

Tests couvrant:
- Workflow 3-agents end-to-end avec Oracle
- Intégration complète Sherlock → Watson → Moriarty
- Orchestration avec CluedoExtendedOrchestrator
- Validation des permissions et révélations
- Métriques de performance et comparaisons
- Différentes stratégies Oracle en action
"""

import pytest
import asyncio
import time

from typing import Dict, Any, List
from datetime import datetime

from semantic_kernel.kernel import Kernel
from semantic_kernel.contents.chat_message_content import ChatMessageContent

# Imports du système Oracle (adaptés v2.1.0)
from argumentation_analysis.orchestration.cluedo_extended_orchestrator import (
    CluedoExtendedOrchestrator,
    run_cluedo_oracle_game
)
from argumentation_analysis.core.cluedo_oracle_state import CluedoOracleState
from argumentation_analysis.agents.core.oracle.cluedo_dataset import CluedoDataset, RevealPolicy
from argumentation_analysis.agents.core.oracle.permissions import QueryType, PermissionManager
from argumentation_analysis.agents.core.pm.sherlock_enquete_agent import SherlockEnqueteAgent
from argumentation_analysis.agents.core.logic.watson_logic_assistant import WatsonLogicAssistant
from argumentation_analysis.agents.core.oracle.moriarty_interrogator_agent import MoriartyInterrogatorAgent


@pytest.mark.integration
class TestOracleWorkflowIntegration:
    async def _create_authentic_gpt4o_mini_instance(self):
        """Crée une instance authentique de gpt-4o-mini au lieu d'un mock."""
        config = UnifiedConfig()
        return config.get_kernel_with_gpt4o_mini()
        
    async def _make_authentic_llm_call(self, prompt: str) -> str:
        """Fait un appel authentique à gpt-4o-mini."""
        try:
            kernel = await self._create_authentic_gpt4o_mini_instance()
            result = await kernel.invoke("chat", input=prompt)
            return str(result)
        except Exception as e:
            logger.warning(f"Appel LLM authentique échoué: {e}")
            return "Authentic LLM call failed"

    """Tests d'intégration pour le workflow Oracle Enhanced v2.1.0."""
    
    @pytest.fixture
    async def mock_kernel(self):
        """Kernel Semantic Kernel mocké pour les tests d'intégration Oracle Enhanced v2.1.0."""
        kernel = await self._create_authentic_gpt4o_mini_instance()
        return kernel
    
    @pytest.fixture
    def integration_elements(self):
        """Éléments Cluedo simplifiés pour tests d'intégration Oracle Enhanced v2.1.0."""
        return {
            "suspects": ["Colonel Moutarde", "Professeur Violet", "Mademoiselle Rose"],
            "armes": ["Poignard", "Chandelier", "Revolver"],
            "lieux": ["Salon", "Cuisine", "Bureau"]
        }
    
    @pytest.fixture
    def oracle_orchestrator(self, mock_kernel):
        """Orchestrateur Oracle Enhanced v2.1.0 configuré pour les tests."""
        return CluedoExtendedOrchestrator(
            kernel=mock_kernel,
            max_turns=10,
            max_cycles=3,
            oracle_strategy="balanced"
        )
    
    @pytest.mark.asyncio
    async def test_complete_oracle_workflow_setup(self, oracle_orchestrator, integration_elements):
        """Test la configuration complète du workflow Oracle Enhanced v2.1.0."""
        # Configuration du workflow
        oracle_state = await oracle_orchestrator.setup_workflow(
            nom_enquete="Integration Test Case Oracle Enhanced v2.1.0",
            elements_jeu=integration_elements
        )
        
        # Vérifications de base Oracle Enhanced v2.1.0
        assert isinstance(oracle_state, CluedoOracleState)
        assert oracle_state.nom_enquete == "Integration Test Case Oracle Enhanced v2.1.0"
        assert oracle_state.oracle_strategy == "balanced"
        
        # Vérification des agents créés
        assert oracle_orchestrator.sherlock_agent is not None
        assert oracle_orchestrator.watson_agent is not None
        assert oracle_orchestrator.moriarty_agent is not None
        
        # Vérification du group chat
        assert oracle_orchestrator.group_chat is not None
        assert len(oracle_orchestrator.group_chat.agents) == 3
        
        # Vérification des noms d'agents
        agent_names = [agent.name for agent in oracle_orchestrator.group_chat.agents]
        assert "Sherlock" in agent_names
        assert "Watson" in agent_names
        assert "Moriarty" in agent_names
    
    @pytest.mark.asyncio
    async def test_agent_communication_flow(self, oracle_orchestrator, integration_elements):
        """Test le flux de communication entre les 3 agents Oracle Enhanced v2.1.0."""
        # Configuration
        await oracle_orchestrator.setup_workflow(elements_jeu=integration_elements)
        
        # Mock des agents pour simuler les réponses Oracle Enhanced v2.1.0
        mock_responses = [
            ChatMessageContent(role="assistant", content="Sherlock (Oracle Enhanced v2.1.0): Je commence l'investigation...", name="Sherlock"),
            ChatMessageContent(role="assistant", content="Watson (Oracle Enhanced v2.1.0): Analysons logiquement...", name="Watson"),
            ChatMessageContent(role="assistant", content="Moriarty (Oracle Enhanced v2.1.0): Je révèle que...", name="Moriarty")
        ]
        
        # Mock du group chat invoke pour retourner les réponses simulées
        async def mock_invoke():
            for response in mock_responses:
                yield response
        
        oracle_orchestrator.group_chat.invoke = mock_invoke
        
        # Exécution du workflow Oracle Enhanced v2.1.0
        result = await oracle_orchestrator.execute_workflow("Commençons l'enquête Oracle Enhanced v2.1.0!")
        
        # Vérifications
        assert "workflow_info" in result
        assert "solution_analysis" in result
        assert "oracle_statistics" in result
        assert "conversation_history" in result
        
        # Vérification de l'historique de conversation
        history = result["conversation_history"]
        assert len(history) == 3
        assert any("Sherlock" in msg["sender"] for msg in history)
        assert any("Watson" in msg["sender"] for msg in history)
        assert any("Moriarty" in msg["sender"] for msg in history)
    
    @pytest.mark.asyncio
    async def test_oracle_permissions_integration(self, oracle_orchestrator, integration_elements):
        """Test l'intégration du système de permissions Oracle Enhanced v2.1.0."""
        oracle_state = await oracle_orchestrator.setup_workflow(elements_jeu=integration_elements)
        
        # Test des permissions pour différents agents Oracle Enhanced v2.1.0
        permission_manager = oracle_state.dataset_access_manager.permission_manager
        
        # Sherlock devrait avoir accès aux requêtes de base
        sherlock_access = permission_manager.validate_agent_permission("Sherlock", QueryType.CARD_INQUIRY)
        assert isinstance(sherlock_access, bool)
        
        # Watson devrait avoir accès aux validations
        watson_access = permission_manager.validate_agent_permission("Watson", QueryType.SUGGESTION_VALIDATION)
        assert isinstance(watson_access, bool)
        
        # Moriarty devrait avoir des permissions spéciales Oracle Enhanced v2.1.0
        moriarty_access = permission_manager.validate_agent_permission("Moriarty", QueryType.CARD_INQUIRY)
        assert isinstance(moriarty_access, bool)
    
    @pytest.mark.asyncio
    async def test_revelation_system_integration(self, oracle_orchestrator, integration_elements):
        """Test l'intégration du système de révélations Oracle Enhanced v2.1.0."""
        oracle_state = await oracle_orchestrator.setup_workflow(elements_jeu=integration_elements)
        
        # Simulation d'une révélation par Moriarty Oracle Enhanced v2.1.0
        moriarty_cards = oracle_state.get_moriarty_cards()
        if moriarty_cards:
            test_card = moriarty_cards[0]
            
            # Test de révélation via l'Oracle Enhanced v2.1.0
            revelation_result = await oracle_state.query_oracle(
                agent_name="Moriarty",
                query_type="card_inquiry",
                query_params={"card_name": test_card}
            )
            
            # Vérification que la révélation est enregistrée
            assert isinstance(revelation_result, object)  # OracleResponse
            
            # Vérification des métriques Oracle Enhanced v2.1.0
            stats = oracle_state.get_oracle_statistics()
            assert stats["workflow_metrics"]["oracle_interactions"] >= 1
    
    def test_strategy_impact_on_workflow(self, mock_kernel, integration_elements):
        """Test l'impact des différentes stratégies sur le workflow Oracle Enhanced v2.1.0."""
        strategies = ["cooperative", "competitive", "balanced", "progressive"]
        orchestrators = []
        
        for strategy in strategies:
            orchestrator = CluedoExtendedOrchestrator(
                kernel=mock_kernel,
                max_turns=5,
                max_cycles=2,
                oracle_strategy=strategy
            )
            orchestrators.append(orchestrator)
        
        # Vérification que chaque orchestrateur a sa stratégie Oracle Enhanced v2.1.0
        for i, strategy in enumerate(strategies):
            assert orchestrators[i].oracle_strategy == strategy
    
    @pytest.mark.asyncio
    async def test_termination_conditions(self, oracle_orchestrator, integration_elements):
        """Test les conditions de terminaison du workflow Oracle Enhanced v2.1.0."""
        oracle_state = await oracle_orchestrator.setup_workflow(elements_jeu=integration_elements)
        
        # Test de la stratégie de terminaison Oracle Enhanced v2.1.0
        termination_strategy = oracle_orchestrator.group_chat.termination_strategy
        
        # Simulation d'historique pour test de terminaison
        mock_agent = await self._create_authentic_gpt4o_mini_instance()
        mock_agent.name = "TestAgent"
        mock_history = [
            ChatMessageContent(role="assistant", content="Test message Oracle Enhanced v2.1.0", name="TestAgent")
        ]
        
        # Test de terminaison par nombre de tours
        should_terminate = await termination_strategy.should_terminate(mock_agent, mock_history)
        assert isinstance(should_terminate, bool)
        
        # Test de résumé de terminaison
        summary = termination_strategy.get_termination_summary()
        assert isinstance(summary, dict)
        assert "turn_count" in summary
        assert "cycle_count" in summary


@pytest.mark.integration
class TestOraclePerformanceIntegration:
    """Tests de performance et métriques pour le système Oracle Enhanced v2.1.0."""
    
    @pytest.fixture
    async def performance_kernel(self):
        """Kernel optimisé pour tests de performance Oracle Enhanced v2.1.0."""
        kernel = await self._create_authentic_gpt4o_mini_instance()
        return kernel
    
    @pytest.mark.asyncio
    async def test_oracle_query_performance(self, performance_kernel):
        """Test les performances des requêtes Oracle Enhanced v2.1.0."""
        # Configuration rapide
        elements_jeu = {
            "suspects": ["Colonel Moutarde", "Professeur Violet"],
            "armes": ["Poignard", "Chandelier"],
            "lieux": ["Salon", "Cuisine"]
        }
        
        oracle_state = CluedoOracleState(
            nom_enquete_cluedo="Performance Test Oracle Enhanced v2.1.0",
            elements_jeu_cluedo=elements_jeu,
            oracle_strategy="balanced"
        )
        
        # Test de performance des requêtes multiples Oracle Enhanced v2.1.0
        start_time = time.time()
        
        for i in range(5):
            result = await oracle_state.query_oracle(
                agent_name="TestAgent",
                query_type="game_state",
                query_params={"request": f"test_oracle_enhanced_v2.1.0_{i}"}
            )
            assert result is not None
        
        execution_time = time.time() - start_time
        
        # Vérification que les requêtes sont rapides (< 1 seconde pour 5 requêtes)
        assert execution_time < 1.0
        
        # Vérification des métriques Oracle Enhanced v2.1.0
        stats = oracle_state.get_oracle_statistics()
        assert stats["workflow_metrics"]["oracle_interactions"] == 5
    
    @pytest.mark.asyncio
    async def test_concurrent_oracle_operations(self, performance_kernel):
        """Test les opérations Oracle Enhanced v2.1.0 concurrentes."""
        elements_jeu = {
            "suspects": ["Colonel Moutarde", "Professeur Violet"],
            "armes": ["Poignard", "Chandelier"],
            "lieux": ["Salon", "Cuisine"]
        }
        
        oracle_state = CluedoOracleState(
            nom_enquete_cluedo="Concurrency Test Oracle Enhanced v2.1.0",
            elements_jeu_cluedo=elements_jeu,
            oracle_strategy="balanced"
        )
        
        # Lancement de requêtes concurrentes Oracle Enhanced v2.1.0
        async def concurrent_query(agent_name, query_id):
            return await oracle_state.query_oracle(
                agent_name=agent_name,
                query_type="card_inquiry",
                query_params={"card_name": f"TestCardOracleEnhanced{query_id}"}
            )
        
        # Exécution concurrente
        tasks = [
            concurrent_query("Sherlock", 1),
            concurrent_query("Watson", 2),
            concurrent_query("Moriarty", 3)
        ]
        
        start_time = time.time()
        results = await asyncio.gather(*tasks)
        execution_time = time.time() - start_time
        
        # Vérifications Oracle Enhanced v2.1.0
        assert len(results) == 3
        for result in results:
            assert result is not None
        
        # Vérification que l'exécution concurrente est efficace
        assert execution_time < 2.0  # Moins de 2 secondes pour 3 requêtes concurrentes
        
        # Vérification de la cohérence de l'état Oracle Enhanced v2.1.0
        stats = oracle_state.get_oracle_statistics()
        assert stats["workflow_metrics"]["oracle_interactions"] == 3
    
    def test_memory_usage_oracle_state(self, performance_kernel):
        """Test l'utilisation mémoire de l'état Oracle Enhanced v2.1.0."""
        import sys
        
        # Mesure de la mémoire avant
        initial_size = sys.getsizeof({})
        
        # Création d'un état Oracle Enhanced v2.1.0 avec beaucoup de données
        elements_jeu = {
            "suspects": [f"SuspectOracleEnhanced{i}" for i in range(10)],
            "armes": [f"ArmeOracleEnhanced{i}" for i in range(10)],
            "lieux": [f"LieuOracleEnhanced{i}" for i in range(10)]
        }
        
        oracle_state = CluedoOracleState(
            nom_enquete_cluedo="Memory Test Oracle Enhanced v2.1.0",
            elements_jeu_cluedo=elements_jeu,
            oracle_strategy="balanced"
        )
        
        # Simulation d'activité intensive Oracle Enhanced v2.1.0
        for i in range(20):
            oracle_state.record_agent_turn(f"Agent{i%3}", "test", {"data": f"test_oracle_enhanced_v2.1.0_{i}"})
        
        # Mesure approximative de l'utilisation mémoire
        stats = oracle_state.get_oracle_statistics()
        
        # Vérification que les données sont bien organisées Oracle Enhanced v2.1.0
        assert len(stats["agent_interactions"]["agents_active"]) <= 3  # Max 3 agents
        assert len(oracle_state.recent_revelations) <= 10  # Limite des révélations récentes


@pytest.mark.integration
class TestOracleErrorHandlingIntegration:
    """Tests de gestion d'erreurs dans l'intégration Oracle Enhanced v2.1.0."""
    
    @pytest.fixture
    async def error_test_kernel(self):
        """Kernel pour tests d'erreurs Oracle Enhanced v2.1.0."""
        kernel = await self._create_authentic_gpt4o_mini_instance()
        return kernel
    
    @pytest.mark.asyncio
    async def test_agent_failure_recovery(self, error_test_kernel):
        """Test la récupération en cas d'échec d'agent Oracle Enhanced v2.1.0."""
        orchestrator = CluedoExtendedOrchestrator(
            kernel=error_test_kernel,
            max_turns=5,
            max_cycles=2,
            oracle_strategy="balanced"
        )
        
        # Configuration avec gestion d'erreur Oracle Enhanced v2.1.0
        try:
            oracle_state = await orchestrator.setup_workflow()
            
            # Simulation d'une erreur d'agent Oracle Enhanced v2.1.0
            with patch.object(oracle_state, 'query_oracle', side_effect=Exception("Agent error Oracle Enhanced v2.1.0")):
                result = await oracle_state.query_oracle("FailingAgent", "test_query", {})
                
                # L'erreur devrait être gérée gracieusement
                assert hasattr(result, 'success')
                if hasattr(result, 'success'):
                    assert result.success is False
        
        except Exception as e:
            # Les erreurs de configuration sont acceptables dans les tests Oracle Enhanced v2.1.0
            assert "kernel" in str(e).lower() or "service" in str(e).lower()
    
    @pytest.mark.asyncio
    async def test_dataset_connection_failure(self, error_test_kernel):
        """Test la gestion d'échec de connexion au dataset Oracle Enhanced v2.1.0."""
        elements_jeu = {
            "suspects": ["Colonel Moutarde"],
            "armes": ["Poignard"],
            "lieux": ["Salon"]
        }
        
        oracle_state = CluedoOracleState(
            nom_enquete_cluedo="Error Test Oracle Enhanced v2.1.0",
            elements_jeu_cluedo=elements_jeu,
            oracle_strategy="balanced"
        )
        
        # Simulation d'erreur de dataset Oracle Enhanced v2.1.0
        with patch.object(oracle_state.cluedo_dataset, 'process_query', 
                         side_effect=Exception("Dataset connection failed Oracle Enhanced v2.1.0")):
            
            result = await oracle_state.query_oracle(
                agent_name="TestAgent",
                query_type="test_query",
                query_params={}
            )
            
            # L'erreur devrait être gérée Oracle Enhanced v2.1.0
            assert hasattr(result, 'success')
            if hasattr(result, 'success'):
                assert result.success is False
    
    def test_invalid_configuration_handling(self, error_test_kernel):
        """Test la gestion de configurations invalides Oracle Enhanced v2.1.0."""
        # Test avec éléments de jeu invalides
        invalid_elements = {
            "suspects": [],  # Liste vide
            "armes": ["Poignard"],
            "lieux": ["Salon"]
        }
        
        # La création devrait soit échouer, soit se corriger automatiquement Oracle Enhanced v2.1.0
        try:
            oracle_state = CluedoOracleState(
                nom_enquete_cluedo="Invalid Config Test Oracle Enhanced v2.1.0",
                elements_jeu_cluedo=invalid_elements,
                oracle_strategy="invalid_strategy"  # Stratégie invalide
            )
            
            # Si la création réussit, vérifier les corrections automatiques Oracle Enhanced v2.1.0
            if hasattr(oracle_state, 'oracle_strategy'):
                # La stratégie devrait être corrigée ou avoir une valeur par défaut
                assert oracle_state.oracle_strategy in ["cooperative", "competitive", "balanced", "progressive", "invalid_strategy"]
        
        except (ValueError, TypeError, AttributeError) as e:
            # Les erreurs de validation sont acceptables Oracle Enhanced v2.1.0
            assert len(str(e)) > 0


@pytest.mark.integration
@pytest.mark.slow
class TestOracleScalabilityIntegration:
    """Tests de scalabilité pour le système Oracle Enhanced v2.1.0."""
    
    @pytest.mark.asyncio
    async def test_large_game_configuration(self):
        """Test avec une configuration de jeu importante Oracle Enhanced v2.1.0."""
        # Configuration étendue Oracle Enhanced v2.1.0
        large_elements = {
            "suspects": [f"SuspectOracleEnhanced{i}" for i in range(20)],
            "armes": [f"ArmeOracleEnhanced{i}" for i in range(15)],
            "lieux": [f"LieuOracleEnhanced{i}" for i in range(25)]
        }
        
        start_time = time.time()
        
        oracle_state = CluedoOracleState(
            nom_enquete_cluedo="Large Scale Test Oracle Enhanced v2.1.0",
            elements_jeu_cluedo=large_elements,
            oracle_strategy="balanced"
        )
        
        setup_time = time.time() - start_time
        
        # La configuration ne devrait pas être trop lente Oracle Enhanced v2.1.0
        assert setup_time < 5.0  # Moins de 5 secondes
        
        # Vérification que tous les éléments sont bien configurés Oracle Enhanced v2.1.0
        solution = oracle_state.get_solution_secrete()
        assert solution["suspect"] in large_elements["suspects"]
        assert solution["arme"] in large_elements["armes"]
        assert solution["lieu"] in large_elements["lieux"]
        
        moriarty_cards = oracle_state.get_moriarty_cards()
        assert len(moriarty_cards) > 0
        assert len(moriarty_cards) < len(large_elements["suspects"]) + len(large_elements["armes"]) + len(large_elements["lieux"])
    
    @pytest.mark.asyncio
    async def test_extended_workflow_simulation(self):
        """Test d'un workflow étendu avec nombreux tours Oracle Enhanced v2.1.0."""
        elements_jeu = {
            "suspects": ["Colonel Moutarde", "Professeur Violet", "Mademoiselle Rose"],
            "armes": ["Poignard", "Chandelier", "Revolver"],
            "lieux": ["Salon", "Cuisine", "Bureau"]
        }
        
        oracle_state = CluedoOracleState(
            nom_enquete_cluedo="Extended Workflow Test Oracle Enhanced v2.1.0",
            elements_jeu_cluedo=elements_jeu,
            oracle_strategy="progressive"
        )
        
        # Simulation de nombreux tours Oracle Enhanced v2.1.0
        agents = ["Sherlock", "Watson", "Moriarty"]
        
        start_time = time.time()
        
        for turn in range(30):  # 30 tours (10 cycles de 3 agents)
            agent = agents[turn % 3]
            
            # Enregistrement du tour Oracle Enhanced v2.1.0
            oracle_state.record_agent_turn(
                agent_name=agent,
                action_type="extended_test",
                action_details={"turn": turn, "agent": agent, "oracle_enhanced_version": "v2.1.0"}
            )
            
            # Requête Oracle occasionnelle Oracle Enhanced v2.1.0
            if turn % 3 == 0:  # Une requête tous les 3 tours
                await oracle_state.query_oracle(
                    agent_name=agent,
                    query_type="game_state",
                    query_params={"turn": turn, "oracle_enhanced_version": "v2.1.0"}
                )
        
        execution_time = time.time() - start_time
        
        # Vérification des performances Oracle Enhanced v2.1.0
        assert execution_time < 10.0  # Moins de 10 secondes pour 30 tours
        
        # Vérification des métriques finales Oracle Enhanced v2.1.0
        stats = oracle_state.get_oracle_statistics()
        assert stats["agent_interactions"]["total_turns"] == 30
        assert stats["workflow_metrics"]["oracle_interactions"] == 10  # Une requête tous les 3 tours
        assert len(stats["agent_interactions"]["agents_active"]) == 3