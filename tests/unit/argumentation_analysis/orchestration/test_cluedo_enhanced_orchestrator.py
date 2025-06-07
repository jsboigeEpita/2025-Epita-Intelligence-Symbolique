"""
Tests unitaires pour l'orchestrateur Cluedo Enhanced.

Tests couvrant:
- Détection suggestions → révélations automatiques
- Gestion états Oracle Enhanced
- Workflow 3-agents optimisé
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, List
from datetime import datetime

from semantic_kernel.kernel import Kernel
from semantic_kernel.contents.chat_message_content import ChatMessageContent

from argumentation_analysis.orchestration.cluedo_extended_orchestrator import (
    CluedoExtendedOrchestrator,
    run_cluedo_oracle_game
)
from argumentation_analysis.core.cluedo_oracle_state import CluedoOracleState
from argumentation_analysis.agents.core.oracle.cluedo_dataset import RevealPolicy


@pytest.fixture
def mock_enhanced_kernel():
    """Kernel Semantic Kernel mocké pour Oracle Enhanced."""
    kernel = Mock(spec=Kernel)
    kernel.add_plugin = Mock()
    kernel.add_filter = Mock()
    
    # Mock des services GPT-4o-mini
    mock_service = Mock()
    mock_service.service_id = "openai-gpt4o-mini"
    mock_service.ai_model_id = "gpt-4o-mini"
    mock_service.get_chat_message_contents = AsyncMock()
    kernel.get_service = Mock(return_value=mock_service)
    
    return kernel


@pytest.fixture
def enhanced_elements():
    """Éléments Cluedo pour tests Enhanced."""
    return {
        "suspects": ["Colonel Moutarde", "Professeur Violet", "Mademoiselle Rose", "Madame Leblanc"],
        "armes": ["Poignard", "Chandelier", "Revolver", "Corde", "Tuyau"],
        "lieux": ["Salon", "Cuisine", "Bureau", "Bibliothèque", "Salle de bal"]
    }


@pytest.fixture
def enhanced_orchestrator(mock_enhanced_kernel):
    """Orchestrateur Enhanced configuré pour les tests."""
    return CluedoExtendedOrchestrator(
        kernel=mock_enhanced_kernel,
        max_turns=15,
        max_cycles=5,
        oracle_strategy="enhanced_auto_reveal"
    )


class TestCluedoEnhancedOrchestrator:
    """Tests de l'orchestrateur Cluedo Enhanced."""
    
    @pytest.mark.asyncio
    async def test_enhanced_orchestrator_initialization(self, enhanced_orchestrator, enhanced_elements):
        """Test l'initialisation de l'orchestrateur Enhanced."""
        # Configuration du workflow Enhanced
        oracle_state = await enhanced_orchestrator.setup_workflow(
            nom_enquete="Test Enhanced Orchestrator",
            elements_jeu=enhanced_elements
        )
        
        # Vérifications de base
        assert isinstance(oracle_state, CluedoOracleState)
        assert oracle_state.oracle_strategy == "enhanced_auto_reveal"
        assert enhanced_orchestrator.oracle_strategy == "enhanced_auto_reveal"
        
        # Vérification des agents créés
        assert enhanced_orchestrator.sherlock_agent is not None
        assert enhanced_orchestrator.watson_agent is not None
        assert enhanced_orchestrator.moriarty_agent is not None
        
        # Vérification du group chat Enhanced
        assert enhanced_orchestrator.group_chat is not None
        assert len(enhanced_orchestrator.group_chat.agents) == 3
        
        # Vérification de la configuration Enhanced
        assert hasattr(enhanced_orchestrator, '_enhanced_mode')
        assert enhanced_orchestrator._enhanced_mode is True
    
    @pytest.mark.asyncio
    async def test_suggestion_to_revelation_detection(self, enhanced_orchestrator, enhanced_elements):
        """Test la détection suggestions → révélations automatiques."""
        await enhanced_orchestrator.setup_workflow(elements_jeu=enhanced_elements)
        
        # Simulation de suggestions triviales qui devraient déclencher des révélations
        trivial_suggestions = [
            "Je ne sais pas vraiment qui c'est...",
            "Peut-être que c'est quelqu'un avec une arme...",
            "Il faut chercher des indices...",
            "Hmm, c'est difficile à dire..."
        ]
        
        revelations_triggered = []
        
        for suggestion in trivial_suggestions:
            # Analyse de la suggestion par l'orchestrateur Enhanced
            analysis = enhanced_orchestrator._analyze_suggestion_quality(suggestion)
            
            if analysis["is_trivial"]:
                revelation = enhanced_orchestrator._trigger_auto_revelation(
                    trigger_reason=analysis["reason"],
                    context="cluedo_investigation"
                )
                revelations_triggered.append(revelation)
        
        # Vérifier que des révélations ont été déclenchées
        assert len(revelations_triggered) >= 2
        
        # Vérifier la qualité des révélations
        for revelation in revelations_triggered:
            assert "content" in revelation
            assert len(revelation["content"]) > 30  # Révélation substantielle
            assert "auto_triggered" in revelation
            assert revelation["auto_triggered"] is True
    
    @pytest.mark.asyncio
    async def test_enhanced_workflow_execution(self, enhanced_orchestrator, enhanced_elements):
        """Test l'exécution du workflow Enhanced."""
        await enhanced_orchestrator.setup_workflow(elements_jeu=enhanced_elements)
        
        # Mock des réponses des agents avec pattern Enhanced
        mock_responses = [
            ChatMessageContent(
                role="assistant", 
                content="Sherlock: J'enquête sur le Colonel Moutarde...", 
                name="Sherlock"
            ),
            ChatMessageContent(
                role="assistant", 
                content="Watson: Analysons les preuves logiquement...", 
                name="Watson"
            ),
            ChatMessageContent(
                role="assistant", 
                content="Moriarty: Je révèle que j'ai la carte Poignard!", 
                name="Moriarty"
            )
        ]
        
        # Mock du group chat invoke Enhanced
        async def mock_enhanced_invoke():
            for response in mock_responses:
                yield response
        
        enhanced_orchestrator.group_chat.invoke = mock_enhanced_invoke
        
        # Exécution du workflow Enhanced
        result = await enhanced_orchestrator.execute_workflow("Commençons l'enquête Enhanced!")
        
        # Vérifications Enhanced
        assert "workflow_info" in result
        assert "solution_analysis" in result
        assert "oracle_statistics" in result
        assert "conversation_history" in result
        assert "enhanced_metrics" in result
        
        # Vérification des métriques Enhanced
        enhanced_metrics = result["enhanced_metrics"]
        assert "auto_revelations_count" in enhanced_metrics
        assert "suggestion_quality_scores" in enhanced_metrics
        assert "workflow_optimization_level" in enhanced_metrics
    
    def test_enhanced_state_management(self, enhanced_orchestrator, enhanced_elements):
        """Test la gestion des états Oracle Enhanced."""
        # Simulation de différents états Enhanced
        enhanced_states = [
            "investigation_active",
            "suggestion_analysis",
            "auto_revelation_triggered",
            "solution_approaching"
        ]
        
        state_transitions = {}
        
        for state in enhanced_states:
            # Simulation de transition d'état
            transition_result = enhanced_orchestrator._handle_enhanced_state_transition(
                current_state="idle",
                target_state=state,
                context={"elements_jeu": enhanced_elements}
            )
            
            state_transitions[state] = transition_result
        
        # Vérifier que tous les états Enhanced sont gérés
        for state, result in state_transitions.items():
            assert result["success"] is True
            assert result["new_state"] == state
            assert "enhanced_features_active" in result
    
    @pytest.mark.asyncio
    async def test_three_agent_optimization(self, enhanced_orchestrator, enhanced_elements):
        """Test l'optimisation du workflow 3-agents."""
        await enhanced_orchestrator.setup_workflow(elements_jeu=enhanced_elements)
        
        # Simulation d'un cycle complet optimisé
        agent_cycle = ["Sherlock", "Watson", "Moriarty"]
        cycle_results = []
        
        for turn, agent in enumerate(agent_cycle):
            # Simulation d'une action d'agent optimisée
            action_result = await enhanced_orchestrator._execute_optimized_agent_turn(
                agent_name=agent,
                turn_number=turn,
                context="enhanced_cluedo"
            )
            
            cycle_results.append({
                "agent": agent,
                "turn": turn,
                "result": action_result
            })
        
        # Vérifications de l'optimisation
        assert len(cycle_results) == 3
        
        # Vérifier que chaque agent a un rôle optimisé
        sherlock_result = cycle_results[0]["result"]
        watson_result = cycle_results[1]["result"]
        moriarty_result = cycle_results[2]["result"]
        
        assert sherlock_result["role"] == "investigator"
        assert watson_result["role"] == "analyzer"
        assert moriarty_result["role"] == "oracle_revealer"
        
        # Vérifier la cohérence du cycle
        assert sherlock_result["prepares_for"] == "watson_analysis"
        assert watson_result["prepares_for"] == "moriarty_revelation"
        assert moriarty_result["completes_cycle"] is True
    
    def test_enhanced_termination_strategy(self, enhanced_orchestrator):
        """Test la stratégie de terminaison Enhanced."""
        # Configuration de la stratégie Enhanced
        termination_strategy = enhanced_orchestrator._create_enhanced_termination_strategy()
        
        # Test des conditions de terminaison Enhanced
        test_scenarios = [
            {
                "scenario": "solution_found",
                "context": {"solution_confidence": 0.95, "revelations_count": 3},
                "expected_terminate": True
            },
            {
                "scenario": "max_revelations_reached",
                "context": {"solution_confidence": 0.7, "revelations_count": 10},
                "expected_terminate": True
            },
            {
                "scenario": "investigation_ongoing",
                "context": {"solution_confidence": 0.5, "revelations_count": 2},
                "expected_terminate": False
            }
        ]
        
        for scenario in test_scenarios:
            should_terminate = termination_strategy.evaluate_termination(
                scenario=scenario["scenario"],
                context=scenario["context"]
            )
            
            assert should_terminate == scenario["expected_terminate"]
    
    @pytest.mark.asyncio
    async def test_enhanced_error_recovery(self, enhanced_orchestrator, enhanced_elements):
        """Test la récupération d'erreur Enhanced."""
        await enhanced_orchestrator.setup_workflow(elements_jeu=enhanced_elements)
        
        # Simulation d'erreurs et récupération
        error_scenarios = [
            {"type": "agent_timeout", "agent": "Sherlock"},
            {"type": "invalid_response", "agent": "Watson"},
            {"type": "revelation_failure", "agent": "Moriarty"}
        ]
        
        recovery_results = []
        
        for error in error_scenarios:
            recovery_result = await enhanced_orchestrator._handle_enhanced_error_recovery(
                error_type=error["type"],
                failed_agent=error["agent"],
                context="enhanced_workflow"
            )
            
            recovery_results.append(recovery_result)
        
        # Vérifier que toutes les erreurs sont récupérées
        for result in recovery_results:
            assert result["recovery_successful"] is True
            assert result["fallback_action"] is not None
            assert result["enhanced_mode_maintained"] is True


class TestEnhancedWorkflowMetrics:
    """Tests des métriques de workflow Enhanced."""
    
    def test_enhanced_metrics_collection(self, enhanced_orchestrator, enhanced_elements):
        """Test la collecte de métriques Enhanced."""
        # Simulation d'activité Enhanced
        metrics_data = {
            "auto_revelations": 5,
            "suggestion_quality_avg": 0.7,
            "optimization_level": 0.85,
            "agent_efficiency": {
                "Sherlock": 0.9,
                "Watson": 0.8,
                "Moriarty": 0.95
            }
        }
        
        # Collecte des métriques
        enhanced_metrics = enhanced_orchestrator._collect_enhanced_metrics(metrics_data)
        
        # Vérifications
        assert "performance" in enhanced_metrics
        assert "efficiency" in enhanced_metrics
        assert "optimization" in enhanced_metrics
        
        assert enhanced_metrics["performance"]["auto_revelations"] == 5
        assert enhanced_metrics["efficiency"]["average_agent_efficiency"] > 0.8
        assert enhanced_metrics["optimization"]["level"] == 0.85
    
    def test_enhanced_quality_assessment(self, enhanced_orchestrator):
        """Test l'évaluation de qualité Enhanced."""
        # Test de suggestions de différentes qualités
        suggestions = [
            {"content": "Colonel Moutarde avec le Poignard dans le Salon", "expected_quality": "high"},
            {"content": "Je pense que c'est peut-être quelqu'un...", "expected_quality": "low"},
            {"content": "L'analyse des preuves suggère Professeur Violet", "expected_quality": "medium"},
            {"content": "Hmm, difficile à dire...", "expected_quality": "trivial"}
        ]
        
        for suggestion in suggestions:
            quality_score = enhanced_orchestrator._assess_suggestion_quality(suggestion["content"])
            
            if suggestion["expected_quality"] == "high":
                assert quality_score >= 0.8
            elif suggestion["expected_quality"] == "medium":
                assert 0.5 <= quality_score < 0.8
            elif suggestion["expected_quality"] == "low":
                assert 0.2 <= quality_score < 0.5
            else:  # trivial
                assert quality_score < 0.2


class TestEnhancedIntegrationReadiness:
    """Tests de préparation à l'intégration Enhanced."""
    
    def test_enhanced_gpt4o_mini_configuration(self, enhanced_orchestrator):
        """Test la configuration GPT-4o-mini Enhanced."""
        # Vérification de la configuration GPT-4o-mini
        gpt_config = enhanced_orchestrator._get_gpt4o_mini_configuration()
        
        assert gpt_config["model"] == "gpt-4o-mini"
        assert gpt_config["enhanced_prompts"] is True
        assert gpt_config["auto_revelation_enabled"] is True
        assert "rate_limiting" in gpt_config
        assert gpt_config["timeout"] <= 30  # Max 30 secondes
    
    def test_enhanced_prompts_generation(self, enhanced_orchestrator):
        """Test la génération de prompts Enhanced."""
        # Test des prompts Enhanced pour chaque agent
        agents = ["Sherlock", "Watson", "Moriarty"]
        
        for agent in agents:
            enhanced_prompt = enhanced_orchestrator._generate_enhanced_prompt(
                agent_name=agent,
                context="cluedo_enhanced",
                mode="auto_reveal"
            )
            
            assert isinstance(enhanced_prompt, str)
            assert len(enhanced_prompt) > 100  # Prompt substantiel
            assert agent.lower() in enhanced_prompt.lower()
            assert "enhanced" in enhanced_prompt.lower()
            
            # Prompts spécifiques par agent
            if agent == "Moriarty":
                assert "révélation automatique" in enhanced_prompt.lower() or "auto" in enhanced_prompt.lower()
            elif agent == "Sherlock":
                assert "enquête" in enhanced_prompt.lower() or "investigation" in enhanced_prompt.lower()
            elif agent == "Watson":
                assert "analyse" in enhanced_prompt.lower() or "logique" in enhanced_prompt.lower()
    
    @pytest.mark.asyncio
    async def test_enhanced_real_gpt_preparation(self, enhanced_orchestrator, enhanced_elements):
        """Test la préparation pour GPT-4o-mini réel."""
        # Configuration pour tests réels
        real_gpt_config = {
            "api_key_validation": True,
            "rate_limiting": True,
            "timeout_handling": True,
            "retry_logic": True
        }
        
        # Simulation de préparation
        preparation_result = await enhanced_orchestrator._prepare_for_real_gpt(
            config=real_gpt_config,
            elements_jeu=enhanced_elements
        )
        
        # Vérifications de préparation
        assert preparation_result["ready_for_real_gpt"] is True
        assert preparation_result["enhanced_features_configured"] is True
        assert preparation_result["agents_prepared"] == 3
        assert "estimated_tokens_per_turn" in preparation_result
        assert preparation_result["estimated_tokens_per_turn"] < 4000  # Limite GPT-4o-mini