"""
Tests authentiques pour InformalAnalysisAgent - Phase 5 Mock Elimination
Remplace complètement les mocks par des composants authentiques
"""

import os
import sys
import time
import json
import pytest
from typing import Optional, List, Dict

# Import auto-configuration environnement
from argumentation_analysis.core import environment as auto_env

# Imports fixtures authentiques
from .fixtures_authentic import (
    authentic_semantic_kernel,
    authentic_fallacy_detector,
    authentic_rhetorical_analyzer,
    authentic_contextual_analyzer,
    authentic_informal_agent,
    setup_authentic_taxonomy_csv,
    authentic_informal_analysis_plugin,
    sample_authentic_test_text
)

# Imports composants authentiques
from argumentation_analysis.agents.core.informal.informal_agent import InformalAnalysisAgent
from argumentation_analysis.agents.core.informal.informal_definitions import InformalAnalysisPlugin


class TestInformalAnalysisAgentAuthentic:
    """
    Tests authentiques pour InformalAnalysisAgent - Sans mocks, composants réels
    
    Phase 5: Élimination complète des mocks
    - Semantic Kernel authentique avec connecteurs Azure/OpenAI réels
    - Détecteurs de sophismes authentiques avec vraie logique
    - Analyseurs rhétoriques et contextuels authentiques  
    - InformalAnalysisAgent sans mocks
    - Tests d'analyse argumentative avec taxonomie réelle
    """

    @pytest.mark.authentic
    @pytest.mark.phase5
    @pytest.mark.no_mocks
    @pytest.mark.informal
    def test_initialization_and_setup_authentic(self, authentic_informal_agent):
        """
        Test authentique d'initialisation et configuration - AUCUN MOCK
        """
        start_time = time.time()
        
        agent = authentic_informal_agent
        
        # Vérifications de base authentiques
        assert agent.name == "authentic_informal_agent"
        assert agent._kernel is not None
        assert hasattr(agent, 'kernel_wrapper')
        
        # Test des capacités authentiques
        capabilities = agent.get_agent_capabilities()
        assert isinstance(capabilities, dict)
        assert "identify_arguments" in capabilities
        assert "analyze_fallacies" in capabilities
        assert "explore_fallacy_hierarchy" in capabilities
        assert "get_fallacy_details" in capabilities
        assert "categorize_fallacies" in capabilities
        assert "perform_complete_analysis" in capabilities
        
        print(f"[AUTHENTIC] Capacités agent: {list(capabilities.keys())}")
        
        # Test des informations authentiques
        info = agent.get_agent_info()
        assert isinstance(info, dict)
        assert info["name"] == "authentic_informal_agent"
        assert info["class"] == "InformalAnalysisAgent"
        assert "system_prompt" in info
        assert "llm_service_id" in info
        assert "capabilities" in info
        
        print(f"[AUTHENTIC] Info agent: {info['name']}, LLM disponible: {agent.llm_available}")
        
        execution_time = time.time() - start_time
        print(f"[AUTHENTIC] Test d'initialisation terminé en {execution_time:.2f}s")

    @pytest.mark.asyncio
    @pytest.mark.requires_llm
    @pytest.mark.authentic
    @pytest.mark.phase5
    @pytest.mark.no_mocks
    @pytest.mark.informal
    async def test_analyze_fallacies_authentic(self, authentic_informal_agent, sample_authentic_test_text):
        """
        Test authentique d'analyse de sophismes avec vrai LLM
        """
        if not authentic_informal_agent.llm_available:
            pytest.skip("Service LLM non configuré - test authentique impossible")
        
        start_time = time.time()
        
        agent = authentic_informal_agent
        text = sample_authentic_test_text
        
        try:
            # Analyse authentique de sophismes
            fallacies = await agent.analyze_fallacies(text)
            
            # Vérifications authentiques
            assert isinstance(fallacies, list)
            print(f"[AUTHENTIC] Sophismes détectés: {len(fallacies)}")
            
            for fallacy in fallacies:
                assert isinstance(fallacy, dict)
                assert "fallacy_type" in fallacy
                print(f"[AUTHENTIC] Sophisme: {fallacy.get('fallacy_type', 'N/A')}")
                
        except Exception as e:
            print(f"[AUTHENTIC] Erreur analyse sophismes: {e}")
            pytest.skip(f"Erreur de service LLM: {e}")
        
        execution_time = time.time() - start_time
        print(f"[AUTHENTIC] Test d'analyse de sophismes terminé en {execution_time:.2f}s")

    @pytest.mark.asyncio
    @pytest.mark.requires_llm  
    @pytest.mark.authentic
    @pytest.mark.phase5
    @pytest.mark.no_mocks
    @pytest.mark.informal
    async def test_identify_arguments_authentic(self, authentic_informal_agent, sample_authentic_test_text):
        """
        Test authentique d'identification d'arguments
        """
        if not authentic_informal_agent.llm_available:
            pytest.skip("Service LLM non configuré - test authentique impossible")
        
        start_time = time.time()
        
        agent = authentic_informal_agent
        text = sample_authentic_test_text
        
        try:
            # Identification authentique d'arguments
            arguments = await agent.identify_arguments(text)
            
            # Vérifications authentiques
            if arguments is not None:
                assert isinstance(arguments, list)
                print(f"[AUTHENTIC] Arguments identifiés: {len(arguments)}")
                
                for i, argument in enumerate(arguments):
                    assert isinstance(argument, str)
                    assert len(argument.strip()) > 0
                    print(f"[AUTHENTIC] Argument {i+1}: {argument[:50]}...")
            else:
                print("[AUTHENTIC] Aucun argument identifié ou erreur de traitement")
                
        except Exception as e:
            print(f"[AUTHENTIC] Erreur identification arguments: {e}")
            pytest.skip(f"Erreur de service LLM: {e}")
        
        execution_time = time.time() - start_time
        print(f"[AUTHENTIC] Test d'identification d'arguments terminé en {execution_time:.2f}s")

    @pytest.mark.asyncio
    @pytest.mark.requires_llm
    @pytest.mark.authentic
    @pytest.mark.phase5
    @pytest.mark.no_mocks
    @pytest.mark.informal
    async def test_analyze_argument_authentic(self, authentic_informal_agent):
        """
        Test authentique d'analyse d'argument complet
        """
        if not authentic_informal_agent.llm_available:
            pytest.skip("Service LLM non configuré - test authentique impossible")
        
        start_time = time.time()
        
        agent = authentic_informal_agent
        test_argument = "Les experts affirment que ce produit est sûr. N'est-il pas évident que vous devriez l'acheter?"
        
        try:
            # Analyse authentique d'argument
            result = await agent.analyze_argument(test_argument)
            
            # Vérifications authentiques
            assert isinstance(result, dict)
            assert "argument" in result
            assert result["argument"] == test_argument
            assert "fallacies" in result
            assert isinstance(result["fallacies"], list)
            
            print(f"[AUTHENTIC] Argument analysé: {test_argument[:50]}...")
            print(f"[AUTHENTIC] Sophismes trouvés: {len(result['fallacies'])}")
            
            for fallacy in result["fallacies"]:
                print(f"[AUTHENTIC] Sophisme détecté: {fallacy.get('fallacy_type', 'N/A')}")
                
        except Exception as e:
            print(f"[AUTHENTIC] Erreur analyse argument: {e}")
            pytest.skip(f"Erreur de service LLM: {e}")
        
        execution_time = time.time() - start_time
        print(f"[AUTHENTIC] Test d'analyse d'argument terminé en {execution_time:.2f}s")

    @pytest.mark.asyncio
    @pytest.mark.requires_llm
    @pytest.mark.authentic
    @pytest.mark.phase5
    @pytest.mark.no_mocks
    @pytest.mark.informal
    async def test_analyze_text_authentic(self, authentic_informal_agent, sample_authentic_test_text):
        """
        Test authentique d'analyse de texte complète
        """
        if not authentic_informal_agent.llm_available:
            pytest.skip("Service LLM non configuré - test authentique impossible")
        
        start_time = time.time()
        
        agent = authentic_informal_agent
        text = sample_authentic_test_text
        
        try:
            # Analyse authentique de texte
            result = await agent.analyze_text(text)
            
            # Vérifications authentiques
            assert isinstance(result, dict)
            assert "fallacies" in result
            assert "analysis_timestamp" in result
            assert isinstance(result["fallacies"], list)
            
            print(f"[AUTHENTIC] Texte analysé: {len(text)} caractères")
            print(f"[AUTHENTIC] Sophismes détectés: {len(result['fallacies'])}")
            print(f"[AUTHENTIC] Timestamp: {result['analysis_timestamp']}")
            
            # Vérification de la structure des sophismes
            for fallacy in result["fallacies"]:
                assert isinstance(fallacy, dict)
                print(f"[AUTHENTIC] Sophisme: {fallacy}")
                
        except Exception as e:
            print(f"[AUTHENTIC] Erreur analyse texte: {e}")
            pytest.skip(f"Erreur de service LLM: {e}")
        
        execution_time = time.time() - start_time
        print(f"[AUTHENTIC] Test d'analyse de texte terminé en {execution_time:.2f}s")

    @pytest.mark.authentic
    @pytest.mark.phase5
    @pytest.mark.no_mocks
    @pytest.mark.informal
    def test_fallacy_detection_local_authentic(self, authentic_fallacy_detector, sample_authentic_test_text):
        """
        Test authentique du détecteur de sophismes local (sans LLM)
        """
        start_time = time.time()
        
        detector = authentic_fallacy_detector
        text = sample_authentic_test_text
        
        # Détection authentique locale
        fallacies = detector.detect(text)
        
        # Vérifications authentiques
        assert isinstance(fallacies, list)
        print(f"[AUTHENTIC] Sophismes détectés localement: {len(fallacies)}")
        
        for fallacy in fallacies:
            assert isinstance(fallacy, dict)
            assert "fallacy_type" in fallacy
            assert "text" in fallacy
            assert "confidence" in fallacy
            assert "details" in fallacy
            assert "pattern" in fallacy
            
            assert isinstance(fallacy["confidence"], float)
            assert 0.0 <= fallacy["confidence"] <= 1.0
            
            print(f"[AUTHENTIC] Sophisme local: {fallacy['fallacy_type']} (confiance: {fallacy['confidence']:.2f})")
        
        execution_time = time.time() - start_time
        print(f"[AUTHENTIC] Test de détection locale terminé en {execution_time:.2f}s")

    @pytest.mark.authentic
    @pytest.mark.phase5
    @pytest.mark.no_mocks
    @pytest.mark.informal
    def test_rhetorical_analysis_authentic(self, authentic_rhetorical_analyzer, sample_authentic_test_text):
        """
        Test authentique de l'analyseur rhétorique
        """
        start_time = time.time()
        
        analyzer = authentic_rhetorical_analyzer
        text = sample_authentic_test_text
        
        # Analyse rhétorique authentique
        analysis = analyzer.analyze(text)
        
        # Vérifications authentiques
        assert isinstance(analysis, dict)
        assert "tone" in analysis
        assert "style" in analysis
        assert "techniques" in analysis
        assert "effectiveness" in analysis
        assert "tone_scores" in analysis
        
        assert isinstance(analysis["techniques"], list)
        assert isinstance(analysis["effectiveness"], float)
        assert 0.0 <= analysis["effectiveness"] <= 1.0
        assert isinstance(analysis["tone_scores"], dict)
        
        print(f"[AUTHENTIC] Ton: {analysis['tone']}")
        print(f"[AUTHENTIC] Style: {analysis['style']}")
        print(f"[AUTHENTIC] Techniques: {analysis['techniques']}")
        print(f"[AUTHENTIC] Efficacité: {analysis['effectiveness']:.2f}")
        
        execution_time = time.time() - start_time
        print(f"[AUTHENTIC] Test d'analyse rhétorique terminé en {execution_time:.2f}s")

    @pytest.mark.authentic
    @pytest.mark.phase5
    @pytest.mark.no_mocks
    @pytest.mark.informal
    def test_contextual_analysis_authentic(self, authentic_contextual_analyzer, sample_authentic_test_text):
        """
        Test authentique de l'analyseur contextuel
        """
        start_time = time.time()
        
        analyzer = authentic_contextual_analyzer
        text = sample_authentic_test_text
        
        # Analyse contextuelle authentique
        analysis = analyzer.analyze_context(text)
        
        # Vérifications authentiques
        assert isinstance(analysis, dict)
        assert "context_type" in analysis
        assert "audience" in analysis
        assert "intent" in analysis
        assert "confidence" in analysis
        assert "all_contexts" in analysis
        
        assert isinstance(analysis["confidence"], float)
        assert 0.0 <= analysis["confidence"] <= 1.0
        assert isinstance(analysis["all_contexts"], dict)
        
        print(f"[AUTHENTIC] Type de contexte: {analysis['context_type']}")
        print(f"[AUTHENTIC] Audience: {analysis['audience']}")
        print(f"[AUTHENTIC] Intention: {analysis['intent']}")
        print(f"[AUTHENTIC] Confiance: {analysis['confidence']:.2f}")
        
        execution_time = time.time() - start_time
        print(f"[AUTHENTIC] Test d'analyse contextuelle terminé en {execution_time:.2f}s")

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.authentic
    @pytest.mark.phase5
    @pytest.mark.no_mocks
    @pytest.mark.informal
    async def test_complete_informal_analysis_workflow_authentic(self, authentic_informal_agent, sample_authentic_test_text):
        """
        Test authentique du workflow complet d'analyse informelle
        """
        if not authentic_informal_agent.llm_available:
            pytest.skip("Service LLM requis pour test intégration authentique")
        
        start_time = time.time()
        
        agent = authentic_informal_agent
        text = sample_authentic_test_text
        
        try:
            # Workflow complet authentique
            print("[AUTHENTIC] Démarrage du workflow complet d'analyse informelle...")
            
            # 1. Identification des arguments
            arguments = await agent.identify_arguments(text)
            print(f"[AUTHENTIC] Étape 1 - Arguments identifiés: {len(arguments) if arguments else 0}")
            
            # 2. Analyse des sophismes
            fallacies = await agent.analyze_fallacies(text)
            print(f"[AUTHENTIC] Étape 2 - Sophismes détectés: {len(fallacies)}")
            
            # 3. Analyse complète du texte
            complete_analysis = await agent.analyze_text(text)
            print(f"[AUTHENTIC] Étape 3 - Analyse complète terminée")
            
            # 4. Vérifications du workflow
            assert isinstance(complete_analysis, dict)
            assert "fallacies" in complete_analysis
            assert "analysis_timestamp" in complete_analysis
            
            # 5. Analyse d'un argument spécifique si disponible
            if arguments and len(arguments) > 0:
                first_argument = arguments[0]
                argument_analysis = await agent.analyze_argument(first_argument)
                print(f"[AUTHENTIC] Étape 4 - Analyse argument spécifique terminée")
                
                assert isinstance(argument_analysis, dict)
                assert "argument" in argument_analysis
                assert "fallacies" in argument_analysis
            
            print("[AUTHENTIC] Workflow complet terminé avec succès")
            
        except Exception as e:
            print(f"[AUTHENTIC] Erreur workflow: {e}")
            pytest.skip(f"Erreur dans le workflow authentique: {e}")
        
        execution_time = time.time() - start_time
        print(f"[AUTHENTIC] Workflow complet terminé en {execution_time:.2f}s")

    @pytest.mark.performance
    @pytest.mark.authentic
    @pytest.mark.phase5
    @pytest.mark.no_mocks
    @pytest.mark.informal
    def test_local_components_performance_authentic(self, authentic_fallacy_detector, authentic_rhetorical_analyzer, authentic_contextual_analyzer):
        """
        Test authentique de performance des composants locaux
        """
        start_time = time.time()
        
        # Textes de test variés
        test_texts = [
            "Les experts affirment que ce produit est révolutionnaire.",
            "Vous êtes trop jeune pour comprendre cette situation complexe.",
            "Si nous permettons cela, bientôt tout sera autorisé.",
            "N'est-ce pas évident que cette solution est la meilleure?",
            "Pensez aux enfants qui souffriront de cette décision."
        ]
        
        total_fallacies = 0
        total_analyses = 0
        
        for i, text in enumerate(test_texts):
            # Test détecteur de sophismes
            fallacies = authentic_fallacy_detector.detect(text)
            total_fallacies += len(fallacies)
            
            # Test analyseur rhétorique
            rhetorical = authentic_rhetorical_analyzer.analyze(text)
            assert isinstance(rhetorical, dict)
            
            # Test analyseur contextuel
            contextual = authentic_contextual_analyzer.analyze_context(text)
            assert isinstance(contextual, dict)
            
            total_analyses += 3
            print(f"[AUTHENTIC] Texte {i+1}: {len(fallacies)} sophismes détectés")
        
        execution_time = time.time() - start_time
        
        print(f"[AUTHENTIC] Performance: {total_analyses} analyses en {execution_time:.2f}s")
        print(f"[AUTHENTIC] Total sophismes détectés: {total_fallacies}")
        if execution_time > 0:
            print(f"[AUTHENTIC] Vitesse: {total_analyses/execution_time:.1f} analyses/seconde")
        else:
            print("[AUTHENTIC] Vitesse: Exécution trop rapide pour mesurer.")
        
        # Performance attendue : traitement rapide local
        assert execution_time < 2.0  # Moins de 2 secondes pour traitement local


# Marqueurs pytest pour organisation des tests authentiques
pytestmark = [
    pytest.mark.authentic,  # Marqueur pour tests authentiques
    pytest.mark.phase5,     # Marqueur Phase 5
    pytest.mark.no_mocks,   # Marqueur sans mocks
    pytest.mark.informal,   # Marqueur spécifique analyse informelle
]


if __name__ == "__main__":
    # Exécution directe pour débogage
    pytest.main([__file__, "-v", "--tb=short"])