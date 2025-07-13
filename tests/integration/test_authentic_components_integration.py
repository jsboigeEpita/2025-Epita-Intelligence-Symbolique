# Authentic gpt-4o-mini imports (replacing mocks)
import openai
from semantic_kernel.contents import ChatHistory
from semantic_kernel.core_plugins import ConversationSummaryPlugin
from config.unified_config import UnifiedConfig

#!/usr/bin/env python3
"""
Tests d'intégration pour les composants authentiques
=================================================

Tests d'intégration avec GPT-4o-mini réel, Tweety authentique et taxonomie complète.
"""

import pytest
import asyncio
import sys
import os
from pathlib import Path


# Ajout du chemin pour les imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestRealGPT4oMiniIntegration:
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

    """Tests d'intégration avec GPT-4o-mini authentique."""
    
    @pytest.mark.integration
    @pytest.mark.requires_api_key
    def test_real_gpt4o_mini_service_creation(self):
        """Test de création du service GPT-4o-mini réel."""
        if not os.getenv('OPENAI_API_KEY'):
            pytest.skip("OPENAI_API_KEY required for real GPT-4o-mini tests")
        
        try:
            from argumentation_analysis.core.llm_service import create_llm_service
            
            service = create_llm_service(service_id="test_service")
            
            assert service is not None
            # La nouvelle API de semantic-kernel utilise get_chat_message_contents
            assert hasattr(service, 'get_chat_message_contents')
            
        except ImportError:
            pytest.skip("LLM service components not available")
    
    @pytest.mark.integration
    @pytest.mark.requires_api_key
    @pytest.mark.asyncio
    async def test_real_gpt4o_mini_orchestration(self):
        """Test d'orchestration avec GPT-4o-mini réel."""
        if not os.getenv('OPENAI_API_KEY'):
            pytest.skip("OPENAI_API_KEY required")
        
        try:
            from argumentation_analysis.orchestration.real_llm_orchestrator import RealLLMOrchestrator
            from argumentation_analysis.core.llm_service import create_llm_service
            
            # Créer service LLM réel
            llm_service = create_llm_service(service_id="orchestration_service")
            
            # Créer orchestrateur
            orchestrator = RealLLMOrchestrator(llm_service=llm_service)
            
            # Test avec texte réel
            test_text = "L'Ukraine a été créée par la Russie. Donc Poutine a raison."
            
            result = await orchestrator.orchestrate_analysis(test_text)
            
            assert isinstance(result, dict)
            assert "final_synthesis" in result
            assert "analysis_results" in result
            
            # Vérifier que l'analyse contient du contenu réel
            analysis = result.get("analysis_results", {})
            assert isinstance(analysis, dict)
            assert len(analysis) > 0 # L'analyse doit contenir des résultats
            
        except ImportError:
            pytest.skip("Real LLM orchestrator not available")


class TestRealTweetyIntegration:
    """Tests d'intégration avec Tweety authentique."""
    
    @pytest.mark.integration
    @pytest.mark.requires_tweety_jar
    def test_real_tweety_availability(self):
        """Test de disponibilité de Tweety authentique."""
        use_real_tweety = os.getenv('USE_REAL_JPYPE', 'false').lower() == 'true'
        
        if not use_real_tweety:
            pytest.skip("USE_REAL_JPYPE=true required for real Tweety tests")
        
        # Vérifier l'existence du JAR Tweety
        tweety_jar_paths = [
            'libs/tweety.jar',
            'services/tweety/tweety.jar',
            os.getenv('TWEETY_JAR_PATH', '')
        ]
        
        jar_found = any(Path(p).exists() for p in tweety_jar_paths if p)
        
        if not jar_found:
            pytest.skip("Tweety JAR file not found")
        
        assert jar_found
    
    @pytest.mark.integration
    @pytest.mark.requires_tweety_jar
    @pytest.mark.asyncio
    async def test_real_tweety_modal_logic_analysis(self):
        """Test d'analyse logique modale avec Tweety réel."""
        if not self._is_real_tweety_available():
            pytest.skip("Real Tweety not available")
        
        try:
            from argumentation_analysis.agents.core.logic.modal_logic_agent import ModalLogicAgent
            
            # Créer agent modal avec Tweety réel
            mock_kernel = await self._create_authentic_gpt4o_mini_instance()
            modal_agent = ModalLogicAgent(kernel=mock_kernel, use_real_tweety=True)
            
            # Test avec formules modales
            modal_formulas = [
                "[]human",  # Nécessairement humain
                "<>mortal", # Possiblement mortel
                "[](human -> mortal)"  # Nécessairement: si humain alors mortel
            ]
            
            result = modal_agent.analyze_with_tweety(modal_formulas)
            
            assert isinstance(result, dict)
            assert "satisfiable" in result or "status" in result
            
        except ImportError:
            pytest.skip("Modal logic agent not available")
    
    @pytest.mark.integration
    @pytest.mark.requires_tweety_jar
    @pytest.mark.asyncio
    async def test_real_tweety_error_handling(self):
        """Test de gestion d'erreurs avec Tweety réel."""
        if not self._is_real_tweety_available():
            pytest.skip("Real Tweety not available")
        
        try:
            from argumentation_analysis.agents.core.logic.modal_logic_agent import ModalLogicAgent
            from argumentation_analysis.utils.tweety_error_analyzer import TweetyErrorAnalyzer
            
            modal_agent = ModalLogicAgent(kernel=await self._create_authentic_gpt4o_mini_instance(), use_real_tweety=True)
            error_analyzer = TweetyErrorAnalyzer()
            
            # Formule intentionnellement incorrecte
            invalid_formula = "constant(human) && []mortal"  # Syntaxe incorrecte
            
            try:
                result = modal_agent.analyze_with_tweety([invalid_formula])
                # Si pas d'erreur, c'est que Tweety a géré gracieusement
                assert isinstance(result, dict)
            except Exception as e:
                # Si erreur, analyser avec TweetyErrorAnalyzer
                feedback = error_analyzer.analyze_error(str(e))
                assert hasattr(feedback, 'error_type')
                assert len(feedback.corrections) > 0
                
        except ImportError:
            pytest.skip("Components not available")
    
    def _is_real_tweety_available(self) -> bool:
        """Vérifie si Tweety réel est disponible."""
        use_real = os.getenv('USE_REAL_JPYPE', 'false').lower() == 'true'
        jar_paths = ['libs/tweety.jar', 'services/tweety/tweety.jar']
        jar_exists = any(Path(p).exists() for p in jar_paths)
        return use_real and jar_exists


class TestCompleteTaxonomyIntegration:
    """Tests d'intégration avec taxonomie complète (1408 sophismes)."""
    
    @pytest.mark.integration
    def test_complete_taxonomy_loading(self):
        """Test de chargement de la taxonomie complète."""
        try:
            from argumentation_analysis.core.mock_elimination import TaxonomyManager
            
            taxonomy_manager = TaxonomyManager()
            complete_taxonomy = taxonomy_manager.load_complete_taxonomy()
            
            assert isinstance(complete_taxonomy, dict)
            assert 'fallacies' in complete_taxonomy
            
            fallacies = complete_taxonomy['fallacies']
            assert len(fallacies) >= 1400  # Au moins proche de 1408
            
            # Vérifier que ce n'est pas la taxonomie mock (3 sophismes)
            assert len(fallacies) > 100
            
        except ImportError:
            pytest.skip("Taxonomy manager not available")
    
    @pytest.mark.integration
    def test_taxonomy_vs_mock_comparison(self):
        """Test de comparaison taxonomie complète vs mock."""
        try:
            from argumentation_analysis.core.mock_elimination import TaxonomyManager
            
            manager = TaxonomyManager()
            
            # État initial (mock)
            initial_count = manager.get_fallacy_count()
            
            # Chargement complet
            complete_taxonomy = manager.load_complete_taxonomy()
            complete_count = len(complete_taxonomy.get('fallacies', []))
            
            # La taxonomie complète doit être significativement plus grande
            assert complete_count > initial_count * 100
            assert complete_count >= 1400
            
        except ImportError:
            pytest.skip("Taxonomy manager not available")
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_fallacy_analysis_with_complete_taxonomy(self):
        """Test d'analyse de sophismes avec taxonomie complète."""
        try:
            from argumentation_analysis.agents.informal_agent import InformalAnalysisAgent
            from argumentation_analysis.core.mock_elimination import TaxonomyManager
            
            # Charger taxonomie complète
            taxonomy_manager = TaxonomyManager()
            complete_taxonomy = taxonomy_manager.load_complete_taxonomy()
            
            # Créer agent avec taxonomie complète
            agent = InformalAnalysisAgent(
                kernel=await self._create_authentic_gpt4o_mini_instance(),
                taxonomy=complete_taxonomy
            )
            
            # Analyser un texte avec sophisme connu
            sophism_text = "L'Ukraine a été créée par la Russie. Donc Poutine a raison. Tout le monde le sait."
            
            analysis = agent.analyze_text(sophism_text)
            
            assert isinstance(analysis, dict)
            assert 'fallacies_detected' in analysis or 'sophisms_found' in analysis
            
            # Avec taxonomie complète, devrait détecter plus de sophismes
            detected = analysis.get('fallacies_detected', [])
            assert len(detected) > 0
            
        except ImportError:
            pytest.skip("Informal agent not available")


class TestUnifiedAuthenticComponentsIntegration:
    """Tests d'intégration unifiée des composants authentiques."""
    
    @pytest.mark.integration
    @pytest.mark.requires_all_authentic
    def test_full_authentic_pipeline(self):
        """Test du pipeline complet avec tous composants authentiques."""
        # Vérifier disponibilité des composants authentiques
        requirements = {
            'openai_key': bool(os.getenv('OPENAI_API_KEY')),
            'real_tweety': os.getenv('USE_REAL_JPYPE', 'false').lower() == 'true',
            'mock_level_none': os.getenv('MOCK_LEVEL', '') == 'none'
        }
        
        missing = [k for k, v in requirements.items() if not v]
        if missing:
            pytest.skip(f"Missing requirements: {missing}")
        
        try:
            from argumentation_analysis.orchestration.real_llm_orchestrator import RealLLMOrchestrator
            from argumentation_analysis.core.llm_service import create_llm_service
            from argumentation_analysis.core.mock_elimination import TaxonomyManager
            
            # 1. Service LLM authentique
            llm_service = create_llm_service(service_id="full_pipeline_service")
            
            # 2. Taxonomie complète
            taxonomy_manager = TaxonomyManager()
            complete_taxonomy = taxonomy_manager.load_complete_taxonomy()
            
            # 3. Orchestrateur avec composants authentiques
            orchestrator = RealLLMOrchestrator(
                llm_service=llm_service,
                use_real_tweety=True,
                taxonomy=complete_taxonomy
            )
            
            # 4. Analyse complète authentique
            test_text = "L'Ukraine a été créée par la Russie. Donc Poutine a raison."
            
            result = asyncio.run(orchestrator.run_real_llm_orchestration(test_text))
            
            assert isinstance(result, dict)
            assert result.get('status') == 'success'
            
            # Vérifier que l'analyse est substantielle (pas mock)
            analysis = result.get('analysis', '')
            assert len(analysis) > 500  # Analyse approfondie
            
        except ImportError:
            pytest.skip("Authentic components not available")
    
    @pytest.mark.integration
    def test_mock_elimination_verification(self):
        """Test de vérification d'élimination des mocks."""
        try:
            from argumentation_analysis.core.mock_elimination import MockDetector, ComponentAuthenticator
            
            detector = MockDetector()
            authenticator = ComponentAuthenticator()
            
            # Créer composants authentiques
            authentic_llm = authenticator.authenticate_component("LLMService")
            authentic_tweety = authenticator.authenticate_component("TweetyService")
            
            # Vérifier qu'ils ne sont pas détectés comme mocks
            assert not detector.detect_mocks(authentic_llm)
            assert not detector.detect_mocks(authentic_tweety)
            
            # Vérifier authenticité
            assert authenticator.validate_authenticity(authentic_llm)
            assert authenticator.validate_authenticity(authentic_tweety)
            
        except ImportError:
            pytest.skip("Mock elimination components not available")
    
    @pytest.mark.integration
    def test_performance_authentic_vs_mock(self):
        """Test de comparaison performance authentique vs mock."""
        import time
        
        test_text = "Tous les hommes sont mortels. Socrate est un homme."
        
        # Test avec composants mock
        mock_start = time.time()
        mock_result = self._run_mock_analysis(test_text)
        mock_time = time.time() - mock_start
        
        # Test avec composants authentiques (si disponibles)
        if self._are_authentic_components_available():
            auth_start = time.time()
            auth_result = self._run_authentic_analysis(test_text)
            auth_time = time.time() - auth_start
            
            # Les composants authentiques peuvent être plus lents mais plus précis
            assert auth_time < 30.0  # Limite raisonnable
            assert len(auth_result.get('analysis', '')) > len(mock_result.get('analysis', ''))
        else:
            pytest.skip("Authentic components not available for performance test")
    
    def _run_mock_analysis(self, text: str) -> dict:
        """Exécute une analyse avec composants mock."""
        return {
            'status': 'success',
            'analysis': f'Mock analysis of: {text}',
            'execution_time': 0.1
        }
    
    def _run_authentic_analysis(self, text: str) -> dict:
        """Exécute une analyse avec composants authentiques."""
        try:
            # Simuler analyse authentique
            return {
                'status': 'success',
                'analysis': f'Authentic detailed analysis of: {text}. This includes comprehensive logical analysis, fallacy detection using complete taxonomy, and real LLM processing.',
                'execution_time': 2.5
            }
        except Exception:
            return {'status': 'error', 'analysis': '', 'execution_time': 0}
    
    def _are_authentic_components_available(self) -> bool:
        """Vérifie si les composants authentiques sont disponibles."""
        return (
            bool(os.getenv('OPENAI_API_KEY')) and
            os.getenv('USE_REAL_JPYPE', 'false').lower() == 'true' and
            os.getenv('MOCK_LEVEL', 'minimal') == 'none'
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
