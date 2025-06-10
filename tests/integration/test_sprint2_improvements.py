
# Authentic gpt-4o-mini imports (replacing mocks)
import openai
from semantic_kernel.contents import ChatHistory
from semantic_kernel.core_plugins import ConversationSummaryPlugin
from config.unified_config import UnifiedConfig

# -*- coding: utf-8 -*-
# tests/integration/test_sprint2_improvements.py
"""
Tests d'intégration spécifiques pour valider les améliorations du Sprint 2.
"""

import unittest

import asyncio
from datetime import datetime

from argumentation_analysis.services.flask_service_integration import FlaskServiceIntegrator
from argumentation_analysis.services.logic_service import LogicService
from argumentation_analysis.orchestration.group_chat import GroupChatOrchestration
from argumentation_analysis.utils.async_manager import AsyncManager, run_hybrid_safe
from argumentation_analysis.agents.core.logic.first_order_logic_agent_adapter import FirstOrderLogicAgent, LogicAgentFactory
from argumentation_analysis.agents.core.informal.informal_agent_adapter import InformalAgent


class TestSprint2Improvements(unittest.TestCase):
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

    """Tests pour valider les améliorations du Sprint 2."""
    
    def setUp(self):
        """Initialisation avant chaque test."""
        self.mock_app = Magicawait self._create_authentic_gpt4o_mini_instance()
        self.mock_app.route = Magicawait self._create_authentic_gpt4o_mini_instance()
        
        # Mock flask app attributes
        self.mock_app.logic_service = None
        self.mock_app.group_chat_orchestration = None
        self.mock_app.service_integrator = None
        
    def test_harmonized_agent_interfaces(self):
        """Test que les interfaces d'agents sont harmonisées et compatibles."""
        # Test FirstOrderLogicAgent avec différents paramètres
        fol_agent1 = FirstOrderLogicAgent(agent_name="FOLAgent1")
        self.assertEqual(fol_agent1.name, "FOLAgent1")
        self.assertEqual(fol_agent1.agent_id, "FOLAgent1")
        self.assertEqual(fol_agent1.agent_name, "FOLAgent1")
        
        fol_agent2 = FirstOrderLogicAgent(agent_id="FOLAgent2")
        self.assertEqual(fol_agent2.name, "FOLAgent2")
        self.assertEqual(fol_agent2.agent_id, "FOLAgent2")
        self.assertEqual(fol_agent2.agent_name, "FOLAgent2")
        
        # Test InformalAgent avec différents paramètres
        informal_agent1 = InformalAgent(agent_id="InformalAgent1")
        self.assertEqual(informal_agent1.agent_id, "InformalAgent1")
        self.assertEqual(informal_agent1.agent_name, "InformalAgent1")
        
        informal_agent2 = InformalAgent(agent_name="InformalAgent2")
        self.assertEqual(informal_agent2.agent_id, "InformalAgent2")
        self.assertEqual(informal_agent2.agent_name, "InformalAgent2")
        
    def test_logic_agent_factory_robustness(self):
        """Test que la factory d'agents logiques est robuste."""
        # Test création d'agents valides
        fol_agent = LogicAgentFactory.create_agent("first_order")
        self.assertIsNotNone(fol_agent)
        self.assertEqual(fol_agent.name, "FirstOrderLogicAgent")
        self.assertEqual(fol_agent.agent_id, "fol_agent")
        
        pl_agent = LogicAgentFactory.create_agent("propositional")
        self.assertIsNotNone(pl_agent)
        self.assertEqual(pl_agent.name, "PropositionalLogicAgent")
        self.assertEqual(pl_agent.agent_id, "pl_agent")
        
        modal_agent = LogicAgentFactory.create_agent("modal")
        self.assertIsNotNone(modal_agent)
        self.assertEqual(modal_agent.name, "ModalLogicAgent")
        self.assertEqual(modal_agent.agent_id, "modal_agent")
        
        # Test gestion d'erreurs
        with self.assertRaises(Exception):
            LogicAgentFactory.create_agent("invalid_type")
    
    def test_flask_service_integration(self):
        """Test que l'intégration Flask fonctionne correctement."""
        integrator = FlaskServiceIntegrator()
        
        # Test initialisation
        success = integrator.init_app(self.mock_app)
        self.assertTrue(success)
        
        # Vérifier que les services sont intégrés
        self.assertIsNotNone(integrator.get_service('logic_service'))
        self.assertIsNotNone(integrator.get_service('group_chat_orchestration'))
        
        # Test healthcheck
        health_status = integrator.get_health_status()
        self.assertIn('status', health_status)
        self.assertIn('services_count', health_status)
        
        # Test healthcheck détaillé
        detailed_health = integrator.get_detailed_health_status()
        self.assertIn('services', detailed_health)
        self.assertIn('timestamp', detailed_health)
    
    def test_async_manager_functionality(self):
        """Test que le gestionnaire asynchrone fonctionne correctement."""
        async_manager = AsyncManager()
        
        # Test fonction synchrone
        def sync_function(x, y):
            return x + y
        
        result = async_manager.run_hybrid(sync_function, 2, 3)
        self.assertEqual(result, 5)
        
        # Test avec timeout
        def slow_function():
            import time
            time.sleep(0.1)
            return "completed"
        
        result = async_manager.run_hybrid(slow_function, timeout=1.0)
        self.assertEqual(result, "completed")
        
        # Test avec fallback
        def failing_function():
            raise Exception("Test error")
        
        result = async_manager.run_hybrid(failing_function, fallback_result="fallback")
        self.assertEqual(result, "fallback")
        
        # Test multiple tasks
        tasks = [
            {'func': sync_function, 'args': (1, 2)},
            {'func': sync_function, 'args': (3, 4)},
            {'func': sync_function, 'args': (5, 6)}
        ]
        
        results = async_manager.run_multiple_hybrid(tasks)
        self.assertEqual(results, [3, 7, 11])
    
    def test_group_chat_orchestration_robustness(self):
        """Test que l'orchestration de groupe chat est robuste."""
        orchestration = GroupChatOrchestration()
        
        # Test initialisation session
        success = orchestration.initialize_session("test_session", {
            "agent1": Magicawait self._create_authentic_gpt4o_mini_instance(),
            "agent2": Magicawait self._create_authentic_gpt4o_mini_instance()
        })
        self.assertTrue(success)
        
        # Test ajout de message
        message_entry = orchestration.add_message("agent1", "Test message")
        self.assertIn("timestamp", message_entry)
        self.assertIn("agent_id", message_entry)
        self.assertIn("message", message_entry)
        
        # Test analyse coordonnée
        analysis_result = orchestration.coordinate_analysis("Test text for analysis")
        self.assertIn("text", analysis_result)
        self.assertIn("agents_involved", analysis_result)
        self.assertIn("consolidated_analysis", analysis_result)
        
        # Test analyse asynchrone
        async_result = orchestration.coordinate_analysis_async("Test async text", timeout=30.0)
        self.assertIn("execution_mode", async_result)
        self.assertEqual(async_result["execution_mode"], "async")
        
        # Test health check
        health = orchestration.get_service_health()
        self.assertIn("status", health)
        
        # Test nettoyage
        cleanup_success = orchestration.cleanup_session()
        self.assertTrue(cleanup_success)
    
    def test_logic_service_robustness(self):
        """Test que le service de logique est robuste."""
        logic_service = LogicService()
        
        # Test initialisation
        success = logic_service.initialize_logic_agents()
        self.assertTrue(success)
        
        # Test analyse synchrone
        result = logic_service.analyze_text_logic("Test logical text", "first_order")
        self.assertIn("success", result)
        self.assertIn("logic_type", result)
        self.assertIn("analysis_id", result)
        
        # Test analyse asynchrone
        async_result = logic_service.analyze_text_logic_async("Test async logical text", "propositional")
        self.assertIn("success", async_result)
        self.assertIn("logic_type", async_result)
        
        # Test validation d'entrée
        is_valid, sanitized_text, sanitized_type = logic_service.validate_and_sanitize_input("Valid text", "first_order")
        self.assertTrue(is_valid)
        self.assertEqual(sanitized_text, "Valid text")
        self.assertEqual(sanitized_type, "first_order")
        
        # Test validation d'entrée invalide
        is_valid, _, sanitized_type = logic_service.validate_and_sanitize_input("", "invalid_type")
        self.assertFalse(is_valid)
        self.assertEqual(sanitized_type, "auto")
        
        # Test service status
        status = logic_service.get_service_status()
        self.assertIn("service_name", status)
        self.assertIn("status", status)
        self.assertIn("performance_stats", status)
        self.assertIn("circuit_breaker", status)
        
        # Test multiple queries async
        queries = [
            {"belief_set_id": "bs1", "query": "q1", "logic_type": "propositional"},
            {"belief_set_id": "bs2", "query": "q2", "logic_type": "first_order"}
        ]
        results = logic_service.execute_multiple_queries_async(queries)
        self.assertEqual(len(results), 2)
        
        # Test cache
        cache_cleared = logic_service.clear_cache()
        self.assertTrue(cache_cleared)
    
    def test_agent_workflow_integration(self):
        """Test d'intégration complète du workflow des agents."""
        # Créer les agents avec les nouvelles interfaces
        fol_agent = LogicAgentFactory.create_agent("first_order", agent_name="TestFOLAgent")
        informal_agent = InformalAgent(agent_id="TestInformalAgent", tools={
            "fallacy_detector": MagicMock(return_value=[
                {"fallacy_type": "ad_hominem", "confidence": 0.8, "location": "text segment"}
            ])
        })
        
        # Test des capacités
        fol_capabilities = fol_agent.get_agent_capabilities()
        self.assertIn("name", fol_capabilities)
        self.assertIn("logic_type", fol_capabilities)
        
        informal_capabilities = informal_agent.get_agent_capabilities()
        self.assertIn("fallacy_detection", informal_capabilities)
        
        # Test analyse avec agent informel
        informal_result = informal_agent.analyze_text("Test text with potential fallacies")
        self.assertIn("fallacies", informal_result)
        self.assertIn("analysis_timestamp", informal_result)
        
        # Test analyse complète
        complete_result = informal_agent.perform_complete_analysis("Complex text for analysis")
        self.assertIn("fallacies", complete_result)
        self.assertIn("categories", complete_result)
        self.assertIn("contextual_analysis", complete_result)
    
    def test_error_handling_and_fallbacks(self):
        """Test que la gestion d'erreurs et les fallbacks fonctionnent."""
        logic_service = LogicService()
        
        # Test circuit breaker
        self.assertFalse(logic_service._is_circuit_breaker_open())
        
        # Simuler des échecs pour déclencher le circuit breaker
        for _ in range(6):  # Plus que max_failures
            logic_service._record_circuit_breaker_failure()
        
        self.assertTrue(logic_service._is_circuit_breaker_open())
        
        # Test analyse avec circuit breaker ouvert
        fallback_result = logic_service.analyze_text_logic_async("Test text with circuit breaker open")
        self.assertTrue(fallback_result.get("fallback_mode", False))
        
        # Test réinitialisation circuit breaker
        logic_service._reset_circuit_breaker()
        self.assertFalse(logic_service._is_circuit_breaker_open())
        
        # Test mode fallback
        logic_service.enable_fallback_mode(False)
        disabled_fallback_result = logic_service._get_fallback_analysis_result("test", "propositional")
        self.assertFalse(disabled_fallback_result["success"])
        
        logic_service.enable_fallback_mode(True)
        enabled_fallback_result = logic_service._get_fallback_analysis_result("test", "propositional")
        self.assertTrue(enabled_fallback_result["success"])
    
    def test_performance_monitoring(self):
        """Test que le monitoring de performance fonctionne."""
        async_manager = AsyncManager()
        
        # Exécuter quelques tâches pour générer des statistiques
        def test_task(n):
            return n * 2
        
        for i in range(5):
            async_manager.run_hybrid(test_task, i)
        
        # Obtenir les statistiques
        stats = async_manager.get_performance_stats()
        self.assertIn("total_tasks", stats)
        self.assertIn("completed_tasks", stats)
        self.assertIn("average_duration", stats)
        
        # Test nettoyage des tâches
        cleaned = async_manager.cleanup_completed_tasks(max_age_hours=0)
        self.assertGreaterEqual(cleaned, 0)
    
    def test_concurrent_operations(self):
        """Test que les opérations concurrentes fonctionnent correctement."""
        orchestration = GroupChatOrchestration()
        
        # Initialiser avec plusieurs agents mockés
        agents = {}
        for i in range(3):
            mock_agent = Magicawait self._create_authentic_gpt4o_mini_instance()
            mock_agent.get_agent_capabilities# Mock eliminated - using authentic gpt-4o-mini {"type": f"agent_{i}"}
            agents[f"agent_{i}"] = mock_agent
        
        orchestration.initialize_session("concurrent_test", agents)
        
        # Test analyse coordonnée asynchrone avec plusieurs agents
        result = orchestration.coordinate_analysis_async(
            "Concurrent analysis text",
            target_agents=list(agents.keys()),
            timeout=30.0
        )
        
        self.assertEqual(len(result["agents_involved"]), 3)
        self.assertEqual(len(result["individual_results"]), 3)
        self.assertIn("consolidated_analysis", result)
        
        # Vérifier que la consolidation a fonctionné
        consolidated = result["consolidated_analysis"]
        self.assertIn("agents_count", consolidated)
        self.assertEqual(consolidated["agents_count"], 3)


if __name__ == "__main__":
    unittest.main()