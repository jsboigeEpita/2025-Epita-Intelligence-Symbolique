import openai
from semantic_kernel.contents import ChatHistory
from semantic_kernel.core_plugins import ConversationSummaryPlugin
from config.unified_config import UnifiedConfig

#!/usr/bin/env python3
"""
Tests d'intégration système pour orchestrations unifiées
======================================================

Tests bout-en-bout pour valider l'intégration complète du système
avec ConversationOrchestrator et UnifiedPipeline.
"""

import pytest
import asyncio
import sys
import time
import tempfile
from pathlib import Path
from datetime import datetime

from typing import Dict, Any, List

# Ajout du chemin pour les imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from argumentation_analysis.orchestration.conversation_orchestrator import (
        ConversationOrchestrator,
    )
    from argumentation_analysis.orchestration.unified_pipeline import (
        run_unified_analysis,
    )
    from argumentation_analysis.utils.tweety_error_analyzer import TweetyErrorAnalyzer
    from config.unified_config import UnifiedConfig as RealUnifiedConfig
    from argumentation_analysis.agents.core.logic.fol_logic_agent import FOLLogicAgent

    REAL_COMPONENTS_AVAILABLE = True
except ImportError as e:
    print(f"Avertissement: Composants réels non disponibles: {e}")
    REAL_COMPONENTS_AVAILABLE = False

    # Mocks pour tests d'intégration
    class ConversationOrchestrator:
        def __init__(self, mode="demo"):
            self.mode = mode
            self.agents = []
            self.state = {"status": "initialized"}

        def run_orchestration(self, text: str) -> str:
            return f"Integration test orchestration {self.mode}: {text[:50]}..."

        def get_agents(self) -> List:
            return self.agents

        def get_conversation_state(self) -> Dict:
            return {
                "mode": self.mode,
                "state": self.state,
                "messages_count": 0,
                "tools_count": 0,
                "processing_time": 0.0,
                "completed": True,
            }

    async def run_unified_analysis(text: str, **kwargs) -> Dict[str, Any]:
        """Mock fallback for run_unified_analysis."""
        return {
            "workflow_name": kwargs.get("workflow_name", "standard"),
            "summary": {"completed": 1, "failed": 0, "skipped": 0},
        }

    class TweetyErrorAnalyzer:
        def analyze_error(self, error_text: str) -> Any:
            return type(
                "TweetyErrorFeedback",
                (),
                {
                    "error_type": "INTEGRATION_ERROR",
                    "corrections": [
                        "Integration correction 1",
                        "Integration correction 2",
                    ],
                    "bnf_rules": ["Integration BNF rule"],
                    "confidence": 0.95,
                    "example_fix": "Fixed version for integration",
                },
            )()

    class UnifiedConfig:
        def __init__(self, **kwargs):
            self.logic_type = kwargs.get("logic_type", "FOL")
            self.mock_level = kwargs.get("mock_level", "PARTIAL")
            self.orchestration_type = kwargs.get("orchestration_type", "CONVERSATION")
            self.require_real_gpt = kwargs.get("require_real_gpt", False)
            self.require_real_tweety = kwargs.get("require_real_tweety", False)

        def to_dict(self):
            return {
                "logic_type": self.logic_type,
                "mock_level": self.mock_level,
                "orchestration_type": self.orchestration_type,
                "require_real_gpt": self.require_real_gpt,
                "require_real_tweety": self.require_real_tweety,
            }

    class FOLLogicAgent:
        def __init__(self, **kwargs):
            self.agent_name = "IntegrationFOLAgent"
            self.initialized = True


class TestUnifiedSystemIntegration:
    """Suite de tests pour l'intégration du système unifié."""

    def _create_authentic_gpt4o_mini_instance(self):
        """Crée une instance authentique de gpt-5-mini au lieu d'un mock."""
        config = RealUnifiedConfig()
        return config.get_kernel_with_gpt4o_mini()

    def _make_authentic_llm_call(self, prompt: str) -> str:
        """Fait un appel authentique à gpt-5-mini."""

        async def _async_call():
            try:
                kernel = self._create_authentic_gpt4o_mini_instance()
                result = await kernel.invoke("chat", input=prompt)
                return str(result)
            except Exception as e:
                # logger is not defined here, using print for visibility
                print(f"Appel LLM authentique échoué: {e}")
                return "Authentic LLM call failed"

        return asyncio.run(_async_call())

    def setup_method(self):
        """Configuration initiale pour chaque test."""
        self.test_texts = [
            "L'Ukraine a été créée par la Russie. Donc Poutine a raison.",
            "Si tous les hommes sont mortels et Socrate est un homme, alors Socrate est mortel.",
            "Le changement climatique est réel. Les politiques doivent agir maintenant.",
        ]

        self.unified_config = UnifiedConfig(
            logic_type="FOL",
            mock_level="NONE",
            orchestration_type="UNIFIED",
            require_real_gpt=True,
            require_real_tweety=True,
        )

    def test_complete_pipeline_integration(self):
        """Test d'intégration complète du pipeline unifié."""
        config = UnifiedConfig(logic_type="FOL", orchestration_type="CONVERSATION")
        conv_orchestrator = ConversationOrchestrator(mode="demo")
        conv_results = []
        for text in self.test_texts:
            result = conv_orchestrator.run_orchestration(text)
            conv_results.append(result)
            assert isinstance(result, str)
            assert len(result) > 0
        assert len(conv_results) == len(self.test_texts)
        for result in conv_results:
            assert "orchestration" in result.lower() or "demo" in result.lower()

    @pytest.mark.skip(reason="requires live LLM funded window — see #695")
    def test_conversation_to_pipeline_handoff(self):
        """Test de handoff conversation vers UnifiedPipeline."""

        async def _async_test():
            conv_orchestrator = ConversationOrchestrator(mode="demo")
            conv_result = conv_orchestrator.run_orchestration(self.test_texts[0])
            conv_state = conv_orchestrator.get_conversation_state()
            assert isinstance(conv_result, str)
            assert isinstance(conv_state, dict)

            pipeline_result = await run_unified_analysis(
                self.test_texts[0], workflow_name="standard"
            )
            assert isinstance(pipeline_result, dict)
            assert "summary" in pipeline_result

        asyncio.run(_async_test())

    def test_config_to_orchestration_mapping(self):
        """Test du mapping configuration vers orchestration."""
        configs = [
            UnifiedConfig(orchestration_type="CONVERSATION", logic_type="FOL"),
            UnifiedConfig(orchestration_type="REAL", logic_type="MODAL"),
            UnifiedConfig(orchestration_type="UNIFIED", logic_type="PL"),
        ]
        for config in configs:
            if config.orchestration_type in ["CONVERSATION", "UNIFIED"]:
                conv_orch = ConversationOrchestrator()
                assert conv_orch.config.logic_type == config.logic_type

    def test_agent_to_orchestrator_communication(self):
        """Test de communication agents vers orchestrateurs."""
        orchestrator = ConversationOrchestrator(mode="demo")
        result = orchestrator.run_orchestration(self.test_texts[0])
        if hasattr(orchestrator, "agents") and orchestrator.agents:
            assert len(orchestrator.agents) > 0
            for agent in orchestrator.agents:
                assert hasattr(agent, "agent_name") or hasattr(agent, "__class__")
        assert isinstance(result, str)

    @pytest.mark.skip(reason="requires live LLM funded window — see #695")
    def test_authentic_system_orchestration(self):
        """Test d'orchestration systeme authentique (sans mocks)."""

        async def _async_test():
            conv_orchestrator = ConversationOrchestrator(mode="enhanced")
            conv_result = conv_orchestrator.run_orchestration(self.test_texts[1])
            assert isinstance(conv_result, str)

            pipeline_result = await run_unified_analysis(
                self.test_texts[1], workflow_name="standard"
            )
            assert isinstance(pipeline_result, dict)
            assert "summary" in pipeline_result

        asyncio.run(_async_test())

    def test_end_to_end_performance(self):
        """Test de performance bout-en-bout."""
        start_time = time.time()
        orchestrator = ConversationOrchestrator(mode="micro")
        results = []
        for text in self.test_texts:
            result = orchestrator.run_orchestration(text)
            results.append(result)
        total_time = time.time() - start_time
        assert total_time < 10.0
        assert len(results) == len(self.test_texts)
        for result in results:
            assert isinstance(result, str)
            assert len(result) > 10


class TestUnifiedErrorHandlingIntegration:
    """Vérifie la robustesse du système face à des erreurs."""

    def setup_method(self):
        """Configuration initiale pour chaque test."""
        self.error_analyzer = TweetyErrorAnalyzer()

    def test_error_analysis_integration(self):
        """Test d'intégration analyse d'erreurs."""
        error_cases = [
            "Predicate 'unknown_pred' has not been declared",
            "Syntax error in modal formula",
            "Invalid logical operator in expression",
        ]
        for error_text in error_cases:
            feedback = self.error_analyzer.analyze_error(error_text)
            assert hasattr(feedback, "error_type")
            assert hasattr(feedback, "corrections")
            assert len(feedback.corrections) > 0
            assert feedback.confidence > 0.0

    @pytest.mark.skip(reason="requires live LLM funded window — see #695")
    def test_error_recovery_workflow(self):
        """Test du workflow de recuperation d'erreur."""

        async def _async_test():
            problematic_text = "Invalid logical formula: unknown_predicate(X)"
            try:
                result = await run_unified_analysis(
                    problematic_text, workflow_name="light"
                )
                assert isinstance(result, dict)
            except Exception as e:
                assert isinstance(e, (ValueError, RuntimeError, TypeError))

        asyncio.run(_async_test())

    def test_error_propagation_chain(self):
        """Test de propagation d'erreurs dans la chaîne."""
        error_config = UnifiedConfig(
            logic_type="FOL", orchestration_type="CONVERSATION"
        )
        orchestrator = ConversationOrchestrator()
        error_texts = ["", None, "🚫" * 1000]
        handled_errors = 0
        for text in error_texts:
            try:
                if text is not None:
                    result = orchestrator.run_orchestration(text)
                    if isinstance(result, str):
                        handled_errors += 1
            except Exception as e:
                assert isinstance(e, (ValueError, TypeError, AttributeError))
                handled_errors += 1
        assert handled_errors > 0


class TestUnifiedConfigurationIntegration:
    """Valide la gestion et la cohérence de la configuration unifiée."""

    def test_configuration_persistence(self):
        """Test de persistance de configuration."""
        complex_config = UnifiedConfig(
            logic_type="FOL",
            mock_level="NONE",
            orchestration_type="UNIFIED",
            require_real_gpt=False,
            require_real_tweety=True,
        )
        config_dict = complex_config.to_dict()
        assert isinstance(config_dict, dict)
        assert config_dict["logic_type"] == "fol"
        assert config_dict["mock_level"] == "none"

    def test_configuration_validation(self):
        """Test de validation de configuration."""
        valid_configs = [
            UnifiedConfig(logic_type="FOL", mock_level="NONE"),
            UnifiedConfig(
                logic_type="MODAL",
                mock_level="PARTIAL",
                require_real_gpt=False,
                require_real_tweety=False,
                require_full_taxonomy=False,
            ),
            UnifiedConfig(
                logic_type="PL",
                mock_level="FULL",
                require_real_gpt=False,
                require_real_tweety=False,
                require_full_taxonomy=False,
            ),
        ]
        for config in valid_configs:
            from config.unified_config import LogicType, MockLevel

            assert isinstance(config.logic_type, LogicType)
            assert isinstance(config.mock_level, MockLevel)

    def test_configuration_orchestrator_consistency(self):
        """Test de cohérence configuration-orchestrateur."""
        config = UnifiedConfig(
            logic_type="FOL",
            orchestration_type="CONVERSATION",
            mock_level="PARTIAL",
            require_real_gpt=False,
            require_real_tweety=False,
            require_full_taxonomy=False,
        )
        from config.unified_config import LogicType, MockLevel

        assert config.logic_type == LogicType.FOL
        assert config.mock_level == MockLevel.PARTIAL


class TestUnifiedPerformanceIntegration:
    """Évalue la performance et la scalabilité du système intégré."""

    def test_scalability_multiple_texts(self):
        """Test de scalabilité avec textes multiples."""
        test_texts = [
            f"Texte d'analyse {i}: Argumentation logique complexe avec {i} éléments."
            for i in range(1, 11)
        ]
        orchestrator = ConversationOrchestrator(mode="micro")
        start_time = time.time()
        results = []
        for text in test_texts:
            result = orchestrator.run_orchestration(text)
            results.append(result)
        total_time = time.time() - start_time
        assert total_time < 15.0
        assert len(results) == 10
        for result in results:
            assert isinstance(result, str)
            assert len(result) > 0

    @pytest.mark.skip(reason="requires live LLM funded window — see #695")
    def test_async_orchestration_performance(self):
        """Test de performance orchestration asynchrone via UnifiedPipeline."""

        async def _async_test():
            texts = [
                "Premier test async",
                "Deuxieme test async",
                "Troisieme test async",
            ]
            start_time = time.time()
            results = []
            for text in texts:
                result = await run_unified_analysis(
                    text, workflow_name="light", create_state=False
                )
                results.append(result)
            total_time = time.time() - start_time
            assert total_time < 5.0
            assert len(results) == 3
            for result in results:
                assert isinstance(result, dict)

        asyncio.run(_async_test())

    def test_memory_efficiency_integration(self):
        """Test d'efficacité mémoire en intégration."""
        import gc

        for i in range(10):
            config = UnifiedConfig(logic_type="FOL")
            orchestrator = ConversationOrchestrator()
            result = orchestrator.run_orchestration(f"Test mémoire {i}")
            assert isinstance(result, str)
            if i % 3 == 0:
                gc.collect()
        final_orchestrator = ConversationOrchestrator()
        final_result = final_orchestrator.run_orchestration("Test final")
        assert isinstance(final_result, str)


@pytest.mark.skipif(
    not REAL_COMPONENTS_AVAILABLE, reason="Composants réels non disponibles"
)
class TestAuthenticIntegrationSuite:
    """Exécute des tests d'intégration avec des composants réels (non mockés)."""

    def test_authentic_fol_integration(self):
        """Test d'intégration FOL authentique."""
        config = UnifiedConfig(
            logic_type="FOL", mock_level="NONE", require_real_tweety=True
        )
        orchestrator = ConversationOrchestrator()
        logical_text = "Si P alors Q. P est vrai. Donc Q est vrai."
        result = orchestrator.run_orchestration(logical_text)
        assert isinstance(result, str)
        assert len(result) > len(logical_text)

    def test_authentic_tweety_error_integration(self):
        """Test d'intégration erreur Tweety authentique."""
        analyzer = TweetyErrorAnalyzer()
        real_error = "Predicate 'believes' has not been declared in rule: believes(john, statement1)"
        feedback = analyzer.analyze_error(real_error)
        assert feedback.error_type != "MOCK_ERROR"
        assert len(feedback.corrections) > 0
        assert feedback.confidence > 0.5
        assert len(feedback.bnf_rules) > 0

    @pytest.mark.skip(reason="requires live LLM funded window — see #695")
    def test_authentic_pipeline_end_to_end(self):
        """Test pipeline authentique bout-en-bout via UnifiedPipeline."""

        async def _async_test():
            conv_orchestrator = ConversationOrchestrator()
            conv_result = conv_orchestrator.run_orchestration(
                "Tous les philosophes reflechissent. Socrate est un philosophe."
            )
            assert isinstance(conv_result, str)

            pipeline_result = await run_unified_analysis(
                "Tous les philosophes reflechissent. Socrate est un philosophe.",
                workflow_name="standard",
            )
            assert isinstance(pipeline_result, dict)
            assert "summary" in pipeline_result

        asyncio.run(_async_test())


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
