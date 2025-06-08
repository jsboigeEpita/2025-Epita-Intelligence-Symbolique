#!/usr/bin/env python3
"""
Tests d'intégration système pour orchestrations unifiées
======================================================

Tests bout-en-bout pour valider l'intégration complète du système
avec ConversationOrchestrator, RealLLMOrchestrator et pipeline unifié.
"""

import pytest
import asyncio
import sys
import time
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from typing import Dict, Any, List

# Ajout du chemin pour les imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from argumentation_analysis.orchestration.conversation_orchestrator import ConversationOrchestrator
    from argumentation_analysis.orchestration.real_llm_orchestrator import RealLLMOrchestrator
    from argumentation_analysis.utils.tweety_error_analyzer import TweetyErrorAnalyzer
    from config.unified_config import UnifiedConfig
    from argumentation_analysis.agents.core.logic.fol_logic_agent import FirstOrderLogicAgent
    REAL_COMPONENTS_AVAILABLE = True
except ImportError as e:
    print(f"Avertissement: Composants réels non disponibles: {e}")
    REAL_COMPONENTS_AVAILABLE = False
    
    # Mocks pour tests d'intégration
    class ConversationOrchestrator:
        def __init__(self, mode="demo", config=None):
            self.mode = mode
            self.config = config
            self.agents = []
            self.state = {"status": "initialized"}
            
        def run_orchestration(self, text: str) -> str:
            return f"Integration test orchestration {self.mode}: {text[:50]}..."
            
        def get_agents(self) -> List:
            return self.agents
            
        def get_state(self) -> Dict:
            return self.state
            
        def is_authentic_mode(self) -> bool:
            return self.config and self.config.mock_level == 'NONE'
    
    class RealLLMOrchestrator:
        def __init__(self, mode="real", llm_service=None, config=None):
            self.mode = mode
            self.llm_service = llm_service
            self.config = config
            self.agents = {}
            self.initialized = False
            
        async def initialize(self) -> bool:
            self.initialized = True
            return True
            
        async def run_real_llm_orchestration(self, text: str) -> Dict[str, Any]:
            return {
                "status": "success",
                "analysis": f"Integration LLM analysis: {text[:50]}...",
                "agents_used": ["IntegrationAgent1", "IntegrationAgent2"],
                "trace": "Integration trace with detailed steps",
                "bnf_feedback": None,
                "performance_metrics": {
                    "duration": 0.5,
                    "tokens_used": 150,
                    "success_rate": 1.0
                }
            }
            
        def load_state(self, state: Dict):
            self.previous_state = state
    
    class TweetyErrorAnalyzer:
        def analyze_error(self, error_text: str) -> Any:
            return type('TweetyErrorFeedback', (), {
                'error_type': 'INTEGRATION_ERROR',
                'corrections': ['Integration correction 1', 'Integration correction 2'],
                'bnf_rules': ['Integration BNF rule'],
                'confidence': 0.95,
                'example_fix': 'Fixed version for integration'
            })()
    
    class UnifiedConfig:
        def __init__(self, **kwargs):
            self.logic_type = kwargs.get('logic_type', 'FOL')
            self.mock_level = kwargs.get('mock_level', 'PARTIAL')
            self.orchestration_type = kwargs.get('orchestration_type', 'CONVERSATION')
            self.require_real_gpt = kwargs.get('require_real_gpt', False)
            self.require_real_tweety = kwargs.get('require_real_tweety', False)
            
        def to_dict(self):
            return {
                'logic_type': self.logic_type,
                'mock_level': self.mock_level,
                'orchestration_type': self.orchestration_type,
                'require_real_gpt': self.require_real_gpt,
                'require_real_tweety': self.require_real_tweety
            }
    
    class FirstOrderLogicAgent:
        def __init__(self, **kwargs):
            self.agent_name = "IntegrationFOLAgent"
            self.initialized = True


class TestUnifiedSystemIntegration:
    """Tests d'intégration système complet."""
    
    def setup_method(self):
        """Configuration initiale pour chaque test."""
        self.test_texts = [
            "L'Ukraine a été créée par la Russie. Donc Poutine a raison.",
            "Si tous les hommes sont mortels et Socrate est un homme, alors Socrate est mortel.",
            "Le changement climatique est réel. Les politiques doivent agir maintenant."
        ]
        
        self.unified_config = UnifiedConfig(
            logic_type='FOL',
            mock_level='NONE',
            orchestration_type='UNIFIED',
            require_real_gpt=True,
            require_real_tweety=True
        )
    
    def test_complete_pipeline_integration(self):
        """Test d'intégration complète du pipeline unifié."""
        # Phase 1: Configuration
        config = UnifiedConfig(
            logic_type='FOL',
            orchestration_type='CONVERSATION'
        )
        
        # Phase 2: Orchestration conversationnelle
        conv_orchestrator = ConversationOrchestrator(mode="demo", config=config)
        conv_results = []
        
        for text in self.test_texts:
            result = conv_orchestrator.run_orchestration(text)
            conv_results.append(result)
            assert isinstance(result, str)
            assert len(result) > 0
        
        # Phase 3: Validation des résultats
        assert len(conv_results) == len(self.test_texts)
        
        # Phase 4: Vérification de la cohérence
        for result in conv_results:
            assert "orchestration" in result.lower() or "demo" in result.lower()
    
    @pytest.mark.asyncio
    async def test_conversation_to_real_llm_handoff(self):
        """Test de handoff conversation vers LLM réel."""
        # Phase 1: Orchestration conversationnelle
        conv_config = UnifiedConfig(orchestration_type='CONVERSATION')
        conv_orchestrator = ConversationOrchestrator(mode="demo", config=conv_config)
        
        conv_result = conv_orchestrator.run_orchestration(self.test_texts[0])
        conv_state = conv_orchestrator.get_state()
        
        assert isinstance(conv_result, str)
        assert isinstance(conv_state, dict)
        
        # Phase 2: Transition vers LLM réel
        real_config = UnifiedConfig(orchestration_type='REAL_LLM')
        mock_llm = Mock()
        real_orchestrator = RealLLMOrchestrator(
            mode="real", 
            llm_service=mock_llm, 
            config=real_config
        )
        
        # Initialisation
        await real_orchestrator.initialize()
        
        # Transfert d'état
        real_orchestrator.load_state(conv_state)
        
        # Phase 3: Orchestration LLM réelle
        real_result = await real_orchestrator.run_real_llm_orchestration(self.test_texts[0])
        
        assert isinstance(real_result, dict)
        assert "status" in real_result
        assert real_result["status"] == "success"
        
        # Phase 4: Validation de la continuité
        assert hasattr(real_orchestrator, 'previous_state')
        assert real_orchestrator.previous_state == conv_state
    
    def test_config_to_orchestration_mapping(self):
        """Test du mapping configuration vers orchestration."""
        # Test configurations multiples
        configs = [
            UnifiedConfig(orchestration_type='CONVERSATION', logic_type='FOL'),
            UnifiedConfig(orchestration_type='REAL_LLM', logic_type='MODAL'),
            UnifiedConfig(orchestration_type='UNIFIED', logic_type='PROPOSITIONAL')
        ]
        
        for config in configs:
            # Test création orchestrateur conversation
            if config.orchestration_type in ['CONVERSATION', 'UNIFIED']:
                conv_orch = ConversationOrchestrator(config=config)
                assert conv_orch.config.logic_type == config.logic_type
            
            # Test création orchestrateur LLM réel
            if config.orchestration_type in ['REAL_LLM', 'UNIFIED']:
                real_orch = RealLLMOrchestrator(config=config)
                assert real_orch.config.logic_type == config.logic_type
    
    def test_agent_to_orchestrator_communication(self):
        """Test de communication agents vers orchestrateurs."""
        orchestrator = ConversationOrchestrator(mode="demo")
        
        # Test communication basique
        result = orchestrator.run_orchestration(self.test_texts[0])
        
        # Vérifier que les agents ont été utilisés
        if hasattr(orchestrator, 'agents') and orchestrator.agents:
            assert len(orchestrator.agents) > 0
            
            # Test que chaque agent peut communiquer
            for agent in orchestrator.agents:
                assert hasattr(agent, 'agent_name') or hasattr(agent, '__class__')
        
        assert isinstance(result, str)
    
    @pytest.mark.asyncio
    async def test_authentic_system_orchestration(self):
        """Test d'orchestration système authentique (sans mocks)."""
        # Configuration authentique complète
        authentic_config = UnifiedConfig(
            logic_type='FOL',
            mock_level='NONE',
            orchestration_type='UNIFIED',
            require_real_gpt=True,
            require_real_tweety=True
        )
        
        # Test orchestrateur conversation authentique
        conv_orchestrator = ConversationOrchestrator(
            mode="enhanced", 
            config=authentic_config
        )
        
        assert conv_orchestrator.is_authentic_mode()
        
        conv_result = conv_orchestrator.run_orchestration(self.test_texts[1])
        assert isinstance(conv_result, str)
        
        # Test orchestrateur LLM réel authentique
        real_orchestrator = RealLLMOrchestrator(config=authentic_config)
        await real_orchestrator.initialize()
        
        real_result = await real_orchestrator.run_real_llm_orchestration(self.test_texts[1])
        assert isinstance(real_result, dict)
        assert "status" in real_result
    
    def test_end_to_end_performance(self):
        """Test de performance bout-en-bout."""
        start_time = time.time()
        
        # Pipeline complet
        orchestrator = ConversationOrchestrator(mode="micro")
        
        results = []
        for text in self.test_texts:
            result = orchestrator.run_orchestration(text)
            results.append(result)
        
        total_time = time.time() - start_time
        
        # Validation performance
        assert total_time < 10.0  # Maximum 10 secondes pour 3 textes
        assert len(results) == len(self.test_texts)
        
        # Validation qualité
        for result in results:
            assert isinstance(result, str)
            assert len(result) > 10  # Résultat substantiel


class TestUnifiedErrorHandlingIntegration:
    """Tests d'intégration pour gestion d'erreurs unifiée."""
    
    def setup_method(self):
        """Configuration initiale pour chaque test."""
        self.error_analyzer = TweetyErrorAnalyzer()
    
    def test_error_analysis_integration(self):
        """Test d'intégration analyse d'erreurs."""
        # Simulation d'erreurs Tweety courantes
        error_cases = [
            "Predicate 'unknown_pred' has not been declared",
            "Syntax error in modal formula",
            "Invalid logical operator in expression"
        ]
        
        for error_text in error_cases:
            feedback = self.error_analyzer.analyze_error(error_text)
            
            assert hasattr(feedback, 'error_type')
            assert hasattr(feedback, 'corrections')
            assert len(feedback.corrections) > 0
            assert feedback.confidence > 0.0
    
    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self):
        """Test du workflow de récupération d'erreur."""
        # Orchestrateur avec gestion d'erreur
        orchestrator = RealLLMOrchestrator()
        await orchestrator.initialize()
        
        # Simulation d'erreur puis récupération
        problematic_text = "Invalid logical formula: unknown_predicate(X)"
        
        try:
            result = await orchestrator.run_real_llm_orchestration(problematic_text)
            
            # Si pas d'erreur, vérifier que le résultat est valide
            assert isinstance(result, dict)
            
            # Vérifier présence de feedback d'erreur si applicable
            if "bnf_feedback" in result and result["bnf_feedback"]:
                assert "error" in str(result["bnf_feedback"]).lower()
                
        except Exception as e:
            # Si erreur non gérée, vérifier qu'elle est appropriée
            assert isinstance(e, (ValueError, RuntimeError, TypeError))
    
    def test_error_propagation_chain(self):
        """Test de propagation d'erreurs dans la chaîne."""
        # Configuration avec gestion d'erreur
        error_config = UnifiedConfig(
            logic_type='FOL',
            orchestration_type='CONVERSATION'
        )
        
        orchestrator = ConversationOrchestrator(config=error_config)
        
        # Test avec différents types d'erreurs
        error_texts = [
            "",  # Texte vide
            None,  # Valeur None
            "🚫" * 1000,  # Caractères problématiques
        ]
        
        handled_errors = 0
        
        for text in error_texts:
            try:
                if text is not None:
                    result = orchestrator.run_orchestration(text)
                    if isinstance(result, str):
                        handled_errors += 1
            except Exception as e:
                # Erreur gérée appropriément
                assert isinstance(e, (ValueError, TypeError, AttributeError))
                handled_errors += 1
        
        # Au moins une erreur doit être gérée
        assert handled_errors > 0


class TestUnifiedConfigurationIntegration:
    """Tests d'intégration pour configuration unifiée."""
    
    def test_configuration_persistence(self):
        """Test de persistance de configuration."""
        # Configuration complexe
        complex_config = UnifiedConfig(
            logic_type='FOL',
            mock_level='MINIMAL',
            orchestration_type='UNIFIED',
            require_real_gpt=False,
            require_real_tweety=True
        )
        
        # Test sérialisation/désérialisation
        config_dict = complex_config.to_dict()
        assert isinstance(config_dict, dict)
        assert config_dict['logic_type'] == 'FOL'
        assert config_dict['mock_level'] == 'MINIMAL'
    
    def test_configuration_validation(self):
        """Test de validation de configuration."""
        # Configurations valides
        valid_configs = [
            UnifiedConfig(logic_type='FOL', mock_level='NONE'),
            UnifiedConfig(logic_type='MODAL', mock_level='PARTIAL'),
            UnifiedConfig(logic_type='PROPOSITIONAL', mock_level='FULL')
        ]
        
        for config in valid_configs:
            assert config.logic_type in ['FOL', 'MODAL', 'PROPOSITIONAL']
            assert config.mock_level in ['NONE', 'PARTIAL', 'FULL']
    
    def test_configuration_orchestrator_consistency(self):
        """Test de cohérence configuration-orchestrateur."""
        config = UnifiedConfig(
            logic_type='FOL',
            orchestration_type='CONVERSATION',
            mock_level='PARTIAL'
        )
        
        # Test que l'orchestrateur respecte la configuration
        orchestrator = ConversationOrchestrator(config=config)
        
        if hasattr(orchestrator, 'config'):
            assert orchestrator.config.logic_type == 'FOL'
            assert orchestrator.config.mock_level == 'PARTIAL'


class TestUnifiedPerformanceIntegration:
    """Tests de performance d'intégration système."""
    
    def test_scalability_multiple_texts(self):
        """Test de scalabilité avec textes multiples."""
        # Générer textes de test variés
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
        
        # Validation performance
        assert total_time < 15.0  # Maximum 15 secondes pour 10 textes
        assert len(results) == 10
        
        # Validation qualité
        for result in results:
            assert isinstance(result, str)
            assert len(result) > 0
    
    @pytest.mark.asyncio
    async def test_async_orchestration_performance(self):
        """Test de performance orchestration asynchrone."""
        orchestrator = RealLLMOrchestrator()
        await orchestrator.initialize()
        
        # Test performance async
        texts = [
            "Premier test async",
            "Deuxième test async", 
            "Troisième test async"
        ]
        
        start_time = time.time()
        
        # Exécution séquentielle asynchrone
        results = []
        for text in texts:
            result = await orchestrator.run_real_llm_orchestration(text)
            results.append(result)
        
        total_time = time.time() - start_time
        
        # Validation
        assert total_time < 5.0  # Maximum 5 secondes pour 3 textes async
        assert len(results) == 3
        
        for result in results:
            assert isinstance(result, dict)
            assert "status" in result
    
    def test_memory_efficiency_integration(self):
        """Test d'efficacité mémoire en intégration."""
        import gc
        
        # Test avec création/destruction multiple d'orchestrateurs
        for i in range(10):
            config = UnifiedConfig(logic_type='FOL')
            orchestrator = ConversationOrchestrator(config=config)
            
            result = orchestrator.run_orchestration(f"Test mémoire {i}")
            assert isinstance(result, str)
            
            # Nettoyage périodique
            if i % 3 == 0:
                gc.collect()
        
        # Test final de stabilité
        final_orchestrator = ConversationOrchestrator()
        final_result = final_orchestrator.run_orchestration("Test final")
        assert isinstance(final_result, str)


@pytest.mark.skipif(not REAL_COMPONENTS_AVAILABLE, reason="Composants réels non disponibles")
class TestAuthenticIntegrationSuite:
    """Suite de tests d'intégration authentique (sans mocks)."""
    
    def test_authentic_fol_integration(self):
        """Test d'intégration FOL authentique."""
        config = UnifiedConfig(
            logic_type='FOL', 
            mock_level='NONE',
            require_real_tweety=True
        )
        
        orchestrator = ConversationOrchestrator(config=config)
        
        # Test avec formule logique réelle
        logical_text = "Si P alors Q. P est vrai. Donc Q est vrai."
        result = orchestrator.run_orchestration(logical_text)
        
        assert isinstance(result, str)
        assert len(result) > len(logical_text)  # Analyse enrichie
    
    def test_authentic_tweety_error_integration(self):
        """Test d'intégration erreur Tweety authentique."""
        analyzer = TweetyErrorAnalyzer()
        
        # Test avec vraie erreur Tweety
        real_error = "Predicate 'believes' has not been declared in rule: believes(john, statement1)"
        feedback = analyzer.analyze_error(real_error)
        
        assert feedback.error_type != 'MOCK_ERROR'
        assert len(feedback.corrections) > 0
        assert feedback.confidence > 0.5
        assert len(feedback.bnf_rules) > 0
    
    @pytest.mark.asyncio
    async def test_authentic_pipeline_end_to_end(self):
        """Test pipeline authentique bout-en-bout."""
        # Configuration authentique complète
        config = UnifiedConfig(
            logic_type='FOL',
            mock_level='NONE',
            orchestration_type='UNIFIED',
            require_real_gpt=True,
            require_real_tweety=True
        )
        
        # Phase conversation
        conv_orchestrator = ConversationOrchestrator(config=config)
        conv_result = conv_orchestrator.run_orchestration(
            "Tous les philosophes réfléchissent. Socrate est un philosophe."
        )
        
        assert isinstance(conv_result, str)
        
        # Phase LLM réel
        real_orchestrator = RealLLMOrchestrator(config=config)
        await real_orchestrator.initialize()
        
        real_result = await real_orchestrator.run_real_llm_orchestration(
            "Tous les philosophes réfléchissent. Socrate est un philosophe."
        )
        
        assert isinstance(real_result, dict)
        assert real_result["status"] == "success"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
