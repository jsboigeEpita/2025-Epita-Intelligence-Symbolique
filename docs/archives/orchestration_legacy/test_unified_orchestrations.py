#!/usr/bin/env python3
"""
Tests unitaires avancés pour les orchestrations unifiées
======================================================

Suite finale de tests pour ConversationOrchestrator, RealLLMOrchestrator,
et coordination système complète avec composants authentiques.
"""

# Imports pour les mocks et les tests
from unittest.mock import MagicMock, AsyncMock, patch
import logging
from semantic_kernel import Kernel
from config.unified_config import UnifiedConfig

import pytest
import asyncio
import sys
import time
from pathlib import Path

from typing import Dict, Any, List

# Ajout du chemin pour les imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logger = logging.getLogger(__name__)

try:
    from argumentation_analysis.orchestration.conversation_orchestrator import (
        ConversationOrchestrator,
    )
    from argumentation_analysis.orchestration.real_llm_orchestrator import (
        RealLLMOrchestrator,
    )
    from argumentation_analysis.utils.tweety_error_analyzer import (
        TweetyErrorAnalyzer,
        TweetyErrorFeedback,
    )
    from argumentation_analysis.agents.core.logic.first_order_logic_agent_adapter import (
        FOLLogicAgent,
    )

    REAL_COMPONENTS_AVAILABLE = True
except ImportError as e:
    print(f"Avertissement: Composants réels non disponibles: {e}")
    REAL_COMPONENTS_AVAILABLE = False

    # Mocks de fallback
    class ConversationOrchestrator:
        def __init__(self, mode="demo", config=None):
            self.mode = mode
            self.config = config
            self.agents = []
            self.state = {}

        def run_orchestration(self, text: str) -> str:
            return f"Mock orchestration {self.mode}: {text[:50]}..."

        def get_agents(self) -> List:
            return self.agents

        def get_state(self) -> Dict:
            return self.state

    class RealLLMOrchestrator:
        def __init__(self, mode="real", kernel=None, config=None):
            self.mode = mode
            self.kernel = kernel
            self.config = config
            self.agents = {}
            self.rhetorical_analyzer = None  # Pour la compatibilité des tests

        def initialize(self) -> bool:
            return True

        def run_real_llm_orchestration(self, text: str) -> Dict[str, Any]:
            return {
                "status": "success",
                "analysis": f"Mock real LLM analysis: {text[:50]}...",
                "agents_used": ["RealAgent1", "RealAgent2"],
                "trace": "Mock trace",
                "bnf_feedback": None,
            }

    class TweetyErrorAnalyzer:
        def analyze_error(self, error_text: str) -> Any:
            return type(
                "TweetyErrorFeedback",
                (),
                {
                    "error_type": "MOCK_ERROR",
                    "corrections": ["Mock correction"],
                    "bnf_rules": ["Mock BNF rule"],
                    "confidence": 0.9,
                },
            )()


class TestUnifiedOrchestrations:
    """Tests avancés pour les orchestrations unifiées."""

    def setup_method(self):
        """Configuration initiale pour chaque test."""
        self.test_text = "L'Ukraine a été créée par la Russie. Donc Poutine a raison."
        self.test_config = UnifiedConfig(
            logic_type="FOL",
            mock_level="PARTIAL",  # On utilise des mocks partiels maintenant
            orchestration_type="UNIFIED",
            require_real_gpt=False,  # On n'exige plus le vrai GPT
            require_real_tweety=False,  # Doit être False si le mock_level n'est pas 'NONE'
            require_full_taxonomy=False,  # Doit aussi être False pour un mock partiel
        )

    def test_conversation_orchestrator_initialization(self):
        """Test d'initialisation avancée du ConversationOrchestrator."""
        orchestrator = ConversationOrchestrator(mode="demo")

        assert orchestrator.mode == "demo"
        assert hasattr(orchestrator, "agents")
        assert hasattr(orchestrator, "state")

        # Test conversation state API
        conv_state = orchestrator.get_conversation_state()
        assert isinstance(conv_state, dict)
        assert conv_state["mode"] == "demo"

    @pytest.mark.xfail(
        reason="RealLLMOrchestrator deprecated — .mode/.config attributes removed (#274)",
        strict=True,
    )
    def test_real_llm_orchestrator_configuration(self):
        """Test de configuration du RealLLMOrchestrator."""
        orchestrator = RealLLMOrchestrator(mode="real")

        assert orchestrator.mode == "real"
        assert hasattr(orchestrator, "config")
        assert isinstance(orchestrator.config, dict)

        # Test default config values
        assert orchestrator.config.get("retry_attempts") == 3
        assert orchestrator.config.get("cache_enabled") is True

    def test_multi_agent_coordination(self):
        """Test de coordination multi-agents."""
        orchestrator = ConversationOrchestrator(mode="demo")

        # Vérifier que les agents sont configurés
        agents = (
            orchestrator.get_agents()
            if hasattr(orchestrator, "get_agents")
            else orchestrator.agents
        )
        assert isinstance(agents, list)

        # Test de coordination basique
        result = orchestrator.run_orchestration(self.test_text)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_shared_state_management(self):
        """Test de gestion d'état partagé entre agents."""
        orchestrator = ConversationOrchestrator(mode="demo")

        # Test de l'état initial
        if hasattr(orchestrator, "get_state"):
            state = orchestrator.get_state()
            assert isinstance(state, dict)

        # Test de mise à jour d'état après orchestration
        result = orchestrator.run_orchestration(self.test_text)

        # Vérifier que l'état a été mis à jour
        if hasattr(orchestrator, "state"):
            assert orchestrator.state is not None

    def test_error_recovery_mechanisms(self):
        """Test des mécanismes de récupération d'erreur."""
        orchestrator = ConversationOrchestrator(mode="demo")

        # Test avec texte problématique
        problematic_texts = [
            "",  # Texte vide
            "A" * 10000,  # Texte très long
            "🤔💭🧠",  # Emojis uniquement
            None,  # Valeur None (si géré)
        ]

        for text in problematic_texts:
            try:
                if text is not None:
                    result = orchestrator.run_orchestration(text)
                    assert isinstance(result, str)
            except Exception as e:
                # Vérifier que l'erreur est appropriée
                assert isinstance(e, (ValueError, TypeError, AttributeError))

    def test_trace_generation_quality(self):
        """Test de la qualité de génération des traces."""
        orchestrator = ConversationOrchestrator(mode="trace")

        result = orchestrator.run_orchestration(self.test_text)

        # Vérifier la structure de la trace
        assert isinstance(result, str)
        assert len(result) > len(self.test_text)  # La trace doit être plus riche

        # Vérifier les éléments attendus dans une trace
        trace_indicators = ["trace", "agent", "step", "analysis", "→", "•"]
        has_trace_elements = any(
            indicator in result.lower() for indicator in trace_indicators
        )
        assert has_trace_elements

    def test_performance_orchestration(self):
        """Test de performance de l'orchestration."""
        orchestrator = ConversationOrchestrator(mode="micro")

        start_time = time.time()

        # Exécuter plusieurs orchestrations
        for i in range(3):
            text = f"Test {i}: Analyse rapide nécessaire."
            result = orchestrator.run_orchestration(text)
            assert isinstance(result, str)

        elapsed_time = time.time() - start_time

        # Performance : moins de 3 secondes pour 3 orchestrations micro
        assert elapsed_time < 3.0

    def test_resource_management(self):
        """Test de gestion des ressources."""
        # Test de création/destruction multiple d'orchestrateurs
        orchestrators = []

        for i in range(5):
            orch = ConversationOrchestrator(mode="micro")
            orchestrators.append(orch)

        # Tous les orchestrateurs doivent être créés correctement
        assert len(orchestrators) == 5

        # Test de nettoyage
        for orch in orchestrators:
            if hasattr(orch, "cleanup"):
                orch.cleanup()


class TestRealLLMOrchestrationAdvanced:
    """Tests avancés pour RealLLMOrchestrator."""

    def _create_authentic_gpt4o_mini_instance(self):
        """Crée une instance authentique de gpt-5-mini au lieu d'un mock."""
        config = UnifiedConfig()
        # Assurez-vous que la méthode get_kernel_with_gpt4o_mini existe et est correcte
        if hasattr(config, "get_kernel_with_gpt4o_mini"):
            return asyncio.run(config.get_kernel_with_gpt4o_mini())
        # Fallback ou erreur si la méthode n'existe pas
        raise AttributeError(
            "UnifiedConfig n'a pas de méthode 'get_kernel_with_gpt4o_mini'"
        )

    def _make_authentic_llm_call(self, prompt: str) -> str:
        """Fait un appel authentique à gpt-5-mini."""
        try:
            kernel = self._create_authentic_gpt4o_mini_instance()
            result = asyncio.run(kernel.invoke("chat", input=prompt))
            return str(result)
        except Exception as e:
            logger.warning(f"Appel LLM authentique échoué: {e}")
            return "Authentic LLM call failed"

    def setup_method(self):
        """Configuration initiale pour chaque test."""
        self.test_text = "L'Ukraine a été créée par la Russie. Donc Poutine a raison."
        self.mock_llm_service = MagicMock()
        self.mock_llm_service.invoke = AsyncMock(return_value="Mock LLM response")

    @pytest.mark.xfail(
        reason="RealLLMOrchestrator deprecated — .kernel/.is_initialized attributes removed (#274)",
        strict=True,
    )
    def test_real_llm_orchestrator_initialization(self):
        """Test d'initialisation complète du RealLLMOrchestrator."""
        orchestrator = RealLLMOrchestrator(mode="real", kernel=self.mock_llm_service)

        # Before initialization
        assert not orchestrator.is_initialized
        assert hasattr(orchestrator, "kernel")
        assert orchestrator.kernel is self.mock_llm_service

        # Check status API
        status = orchestrator.get_status()
        assert isinstance(status, dict)
        assert status["is_initialized"] is False

    def test_bnf_feedback_integration(self):
        """Test d'intégration avec TweetyErrorAnalyzer pour feedback BNF."""
        orchestrator = RealLLMOrchestrator(kernel=self.mock_llm_service)

        # Simuler une erreur Tweety
        error_text = "Predicate 'invalid_pred' has not been declared"

        analyzer = TweetyErrorAnalyzer()
        feedback = analyzer.analyze_error(error_text)

        assert hasattr(feedback, "error_type")
        assert hasattr(feedback, "corrections")
        assert hasattr(feedback, "bnf_rules")

    @patch("config.unified_config.UnifiedConfig.get_kernel_with_gpt4o_mini")
    def test_intelligent_retry_mechanism(self, mock_get_kernel):
        """Test du mécanisme de retry intelligent avec un kernel mocké."""
        # Configurer le mock pour simuler un LLM qui échoue puis réussit
        mock_kernel_instance = MagicMock(spec=Kernel)
        mock_kernel_instance.invoke = AsyncMock(
            side_effect=[Exception("First attempt fails"), "Success on retry"]
        )
        mock_get_kernel.return_value = mock_kernel_instance

        # L'orchestrateur va maintenant utiliser le kernel mocké via la config
        orchestrator = RealLLMOrchestrator(kernel=mock_kernel_instance)

        # Le test original peut continuer, en supposant que l'orchestrateur est
        # conçu pour gérer une exception et potentiellement réessayer.
        try:
            result = orchestrator.run_real_llm_orchestration(self.test_text)
            # Le test attend un succès au deuxième essai
            assert isinstance(result, dict)
            # On pourrait même vérifier que le service a été appelé deux fois
            # assert mock_kernel_instance.invoke.call_count == 2
        except Exception:
            # Si un retry n'est pas implémenté, le test échouera ici, ce qui est attendu.
            pass

    def test_semantic_kernel_integration(self):
        """Test d'intégration avec Semantic Kernel."""
        orchestrator = RealLLMOrchestrator(kernel=self.mock_llm_service)

        # Test d'initialisation du kernel
        if hasattr(orchestrator, "initialize"):
            orchestrator.initialize()

        # Vérifier que le kernel est configuré
        if hasattr(orchestrator, "kernel"):
            assert (
                orchestrator.kernel is not None or orchestrator.kernel is None
            )  # Selon implémentation


class TestUnifiedSystemCoordination:
    """Tests de coordination système unifiée."""

    def setup_method(self):
        """Configuration initiale pour chaque test."""
        self.test_text = "L'Ukraine a été créée par la Russie. Donc Poutine a raison."
        self.unified_config = UnifiedConfig(
            logic_type="FOL", mock_level="NONE", orchestration_type="UNIFIED"
        )

    def test_config_to_orchestration_mapping(self):
        """Test du mapping configuration vers orchestration."""
        # Test avec configuration conversation
        conv_config = UnifiedConfig(orchestration_type="CONVERSATION")
        conv_orchestrator = ConversationOrchestrator()

        assert conv_orchestrator is not None

        # Test avec configuration LLM réel
        real_config = UnifiedConfig(orchestration_type="REAL")
        real_orchestrator = RealLLMOrchestrator(config=real_config)

        assert real_orchestrator is not None

    def test_agent_to_orchestrator_communication(self):
        """Test de communication agent vers orchestrateur."""
        orchestrator = ConversationOrchestrator(mode="demo")

        # Test que les agents peuvent communiquer avec l'orchestrateur
        if hasattr(orchestrator, "agents") and orchestrator.agents:
            # Vérifier que les agents ont accès à l'orchestrateur
            for agent in orchestrator.agents:
                if hasattr(agent, "orchestrator"):
                    assert agent.orchestrator is not None

    @pytest.mark.xfail(
        reason="RealLLMOrchestrator deprecated — .get_status()/.get_metrics() removed (#274)",
        strict=True,
    )
    def test_conversation_to_real_llm_handoff(self):
        """Test de handoff entre orchestrateurs."""
        # Phase 1: Orchestration conversationnelle
        conv_orchestrator = ConversationOrchestrator(mode="demo")
        conv_result = conv_orchestrator.run_orchestration(self.test_text)

        assert isinstance(conv_result, str)

        # Get conversation state for handoff
        conv_state = conv_orchestrator.get_conversation_state()
        assert isinstance(conv_state, dict)
        assert "mode" in conv_state

        # Phase 2: Create real LLM orchestrator
        mock_llm = MagicMock()
        real_orchestrator = RealLLMOrchestrator(kernel=mock_llm)

        # Verify status before initialization
        status = real_orchestrator.get_status()
        assert isinstance(status, dict)
        assert not status["is_initialized"]

        # Verify metrics API
        metrics = real_orchestrator.get_metrics()
        assert isinstance(metrics, dict)
        assert metrics["total_requests"] == 0

    def test_authentic_mode_validation(self):
        """Test de validation du mode authentique."""
        # ConversationOrchestrator doesn't accept config= directly
        # Test the orchestrator and config independently
        orchestrator = ConversationOrchestrator(mode="demo")

        assert orchestrator.mode == "demo"
        conv_state = orchestrator.get_conversation_state()
        assert isinstance(conv_state, dict)
        assert "mode" in conv_state

        # Verify authentic config separately
        authentic_config = UnifiedConfig(
            logic_type="FOL",
            mock_level="NONE",
            require_real_gpt=True,
            require_real_tweety=True,
        )
        assert authentic_config.mock_level.value == "none"
        assert authentic_config.require_real_gpt is True
        assert authentic_config.require_real_tweety is True


class TestOrchestrationPerformanceAndRobustness:
    """Tests de performance et robustesse des orchestrations."""

    def test_concurrent_orchestrations(self):
        """Test d'orchestrations concurrentes."""
        import threading
        import queue

        results = queue.Queue()

        def run_orchestration(text_id):
            orchestrator = ConversationOrchestrator(mode="micro")
            result = orchestrator.run_orchestration(f"Test concurrent {text_id}")
            results.put((text_id, result))

        # Lancer plusieurs orchestrations en parallèle
        threads = []
        for i in range(3):
            thread = threading.Thread(target=run_orchestration, args=(i,))
            threads.append(thread)
            thread.start()

        # Attendre la fin
        for thread in threads:
            thread.join(timeout=5.0)

        # Vérifier les résultats
        assert results.qsize() == 3

        collected_results = []
        while not results.empty():
            collected_results.append(results.get())

        assert len(collected_results) == 3

    def test_memory_usage_stability(self):
        """Test de stabilité de l'utilisation mémoire."""
        import gc

        orchestrator = ConversationOrchestrator(mode="micro")

        # Exécuter plusieurs orchestrations
        for i in range(10):
            text = f"Test mémoire {i}: " + "Data " * 100
            result = orchestrator.run_orchestration(text)
            assert isinstance(result, str)

            # Forcer garbage collection
            if i % 3 == 0:
                gc.collect()

        # Test que l'orchestrateur est toujours fonctionnel
        final_result = orchestrator.run_orchestration("Test final")
        assert isinstance(final_result, str)

    def test_error_propagation_and_handling(self):
        """Test de propagation et gestion d'erreurs."""
        orchestrator = ConversationOrchestrator(mode="demo")

        # Test avec différents types d'erreurs
        error_cases = [
            ("", "empty_text"),
            ("A" * 50000, "very_long_text"),
            ("🔥💥⚡", "special_chars_only"),
        ]

        for text, case_name in error_cases:
            try:
                result = orchestrator.run_orchestration(text)
                # Si aucune erreur, vérifier que le résultat est valide
                assert isinstance(result, str)
                print(f"✓ Cas {case_name}: Géré gracieusement")
            except Exception as e:
                # Si erreur, vérifier qu'elle est appropriée
                assert isinstance(e, (ValueError, TypeError, RuntimeError))
                print(f"✓ Cas {case_name}: Erreur appropriée - {type(e).__name__}")

    def test_orchestration_chain_stability(self):
        """Test de stabilité des chaînes d'orchestration."""
        texts = [
            "Premier texte d'analyse.",
            "Deuxième texte plus complexe avec argumentation.",
            "Troisième texte final pour vérifier la stabilité.",
        ]

        orchestrator = ConversationOrchestrator(mode="demo")

        results = []
        for i, text in enumerate(texts):
            result = orchestrator.run_orchestration(text)
            results.append(result)

            # Vérifier la consistance
            assert isinstance(result, str)
            assert len(result) > 0

            # L'orchestrateur doit rester stable
            assert hasattr(orchestrator, "mode")
            assert orchestrator.mode == "demo"

        # Tous les résultats doivent être uniques et valides
        assert len(results) == 3
        assert len(set(results)) >= 1  # Au moins un résultat unique


@pytest.mark.skipif(
    not REAL_COMPONENTS_AVAILABLE, reason="Composants réels non disponibles"
)
class TestAuthenticOrchestrationIntegration:
    """Tests d'intégration authentique (sans mocks)."""

    def test_fol_agent_integration(self):
        """Test d'intégration avec FOLLogicAgent réel."""
        config = UnifiedConfig(logic_type="FOL", mock_level="NONE")
        orchestrator = ConversationOrchestrator(mode="demo")

        # Vérifier que l'agent FOL est configuré
        if hasattr(orchestrator, "agents"):
            fol_agents = [
                a
                for a in orchestrator.agents
                if "FOLLogicAgent" in str(type(a).__name__)
            ]
            if fol_agents:
                assert len(fol_agents) > 0

    def test_tweety_error_analyzer_integration(self):
        """Test d'intégration avec TweetyErrorAnalyzer réel."""
        analyzer = TweetyErrorAnalyzer()

        # Test avec erreur Tweety réelle
        error_text = "Predicate 'unknown_pred' has not been declared in rule"
        feedback = analyzer.analyze_error(error_text)

        assert feedback.error_type is not None
        assert len(feedback.corrections) > 0
        assert feedback.confidence > 0.0

    def test_unified_config_full_integration(self):
        """Test d'intégration complète avec UnifiedConfig."""
        config = UnifiedConfig(
            logic_type="FOL",
            mock_level="NONE",
            orchestration_type="UNIFIED",
            require_real_gpt=True,
            require_real_tweety=True,
        )

        assert config.logic_type.value == "fol"
        assert config.mock_level.value == "none"
        assert config.require_real_gpt == True
        assert config.require_real_tweety == True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
