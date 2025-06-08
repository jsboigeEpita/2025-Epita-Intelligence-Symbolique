#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test d'intégration ConversationOrchestrator avec RealLLMOrchestrator
===================================================================

Valide que les deux composants refactorisés peuvent s'intégrer harmonieusement.
"""

import asyncio
import sys
from pathlib import Path
import logging

# Ajout du répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent))

from argumentation_analysis.orchestration.conversation_orchestrator import ConversationOrchestrator
from argumentation_analysis.orchestration.real_llm_orchestrator import RealLLMOrchestrator, LLMAnalysisRequest


def setup_logging():
    """Configure le logging pour les tests."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


async def test_components_initialization():
    """Test l'initialisation des deux composants."""
    print("🚀 Test d'initialisation des composants...")
    
    try:
        # Initialiser ConversationOrchestrator
        conv_orchestrator = ConversationOrchestrator()
        conv_init = await conv_orchestrator.initialize()
        print(f"  ✅ ConversationOrchestrator: {'✓' if conv_init else '✗'}")
        
        # Initialiser RealLLMOrchestrator
        llm_orchestrator = RealLLMOrchestrator()
        llm_init = await llm_orchestrator.initialize()
        print(f"  ✅ RealLLMOrchestrator: {'✓' if llm_init else '✗'}")
        
        return conv_init and llm_init, (conv_orchestrator, llm_orchestrator)
        
    except Exception as e:
        print(f"  ❌ Erreur d'initialisation: {e}")
        return False, (None, None)


async def test_basic_integration(conv_orchestrator, llm_orchestrator):
    """Test l'intégration basique entre les deux composants."""
    print("\n🔗 Test d'intégration basique...")
    
    try:
        # Texte de test
        test_text = "L'argumentation logique nécessite des prémisses valides et un raisonnement rigoureux."
        
        # Test 1: Analyse via ConversationOrchestrator
        session_id = await conv_orchestrator.create_session()
        conv_result = await conv_orchestrator.analyze_conversation(
            session_id=session_id,
            text=test_text,
            context={'test': 'integration'}
        )
        print(f"  ✅ ConversationOrchestrator: analyse réussie")
        
        # Test 2: Analyse via RealLLMOrchestrator
        llm_request = LLMAnalysisRequest(
            text=test_text,
            analysis_type="unified_analysis",
            context={'test': 'integration'}
        )
        llm_result = await llm_orchestrator.analyze_text(llm_request)
        print(f"  ✅ RealLLMOrchestrator: analyse réussie (confiance: {llm_result.confidence:.1%})")
        
        # Nettoyage
        await conv_orchestrator.close_session(session_id)
        
        return True
        
    except Exception as e:
        print(f"  ❌ Erreur d'intégration: {e}")
        return False


async def test_cross_communication(conv_orchestrator, llm_orchestrator):
    """Test la communication croisée entre les composants."""
    print("\n🌉 Test de communication croisée...")
    
    try:
        # Créer une session conversationnelle
        session_id = await conv_orchestrator.create_session()
        
        # Analyser plusieurs textes via les deux composants
        texts = [
            "La logique déductive part de prémisses générales vers des conclusions spécifiques.",
            "L'induction raisonne du particulier vers le général.",
            "L'abduction cherche la meilleure explication possible."
        ]
        
        for i, text in enumerate(texts, 1):
            # Analyse conversationnelle
            conv_result = await conv_orchestrator.analyze_conversation(
                session_id=session_id,
                text=text,
                context={'iteration': i, 'cross_test': True}
            )
            
            # Analyse LLM complémentaire
            llm_request = LLMAnalysisRequest(
                text=text,
                analysis_type="logical",
                context={'iteration': i, 'cross_test': True}
            )
            llm_result = await llm_orchestrator.analyze_text(llm_request)
            
            print(f"  ✅ Texte {i}: Conv ✓ + LLM ✓ (conf: {llm_result.confidence:.1%})")
        
        # Vérifier l'état du système
        conv_status = await conv_orchestrator.get_system_status()
        llm_metrics = llm_orchestrator.get_metrics()
        
        print(f"  📊 Sessions conv: {conv_status.get('active_sessions', 0)}")
        print(f"  📊 Analyses LLM: {llm_metrics.get('total_requests', 0)}")
        
        # Nettoyage
        await conv_orchestrator.close_session(session_id)
        
        return True
        
    except Exception as e:
        print(f"  ❌ Erreur de communication croisée: {e}")
        return False


async def test_performance_integration(conv_orchestrator, llm_orchestrator):
    """Test les performances d'intégration."""
    print("\n⚡ Test de performance d'intégration...")
    
    try:
        import time
        
        # Test de charge légère
        test_text = "Test de performance pour l'intégration des orchestrateurs."
        num_tests = 5
        
        # Mesurer le temps pour ConversationOrchestrator
        start_time = time.time()
        session_id = await conv_orchestrator.create_session()
        
        for i in range(num_tests):
            await conv_orchestrator.analyze_conversation(
                session_id=session_id,
                text=f"{test_text} Itération {i+1}",
                context={'perf_test': True, 'iteration': i+1}
            )
        
        conv_time = time.time() - start_time
        await conv_orchestrator.close_session(session_id)
        
        # Mesurer le temps pour RealLLMOrchestrator
        start_time = time.time()
        
        for i in range(num_tests):
            request = LLMAnalysisRequest(
                text=f"{test_text} Itération {i+1}",
                analysis_type="syntactic",
                context={'perf_test': True, 'iteration': i+1}
            )
            await llm_orchestrator.analyze_text(request)
        
        llm_time = time.time() - start_time
        
        print(f"  ⏱️  ConversationOrchestrator: {conv_time:.2f}s ({num_tests} analyses)")
        print(f"  ⏱️  RealLLMOrchestrator: {llm_time:.2f}s ({num_tests} analyses)")
        print(f"  📈 Ratio performance: {llm_time/conv_time:.2f}x")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Erreur de test de performance: {e}")
        return False


def main():
    """Fonction principale des tests d'intégration."""
    setup_logging()
    
    print("🧪 TESTS D'INTÉGRATION - ConversationOrchestrator + RealLLMOrchestrator")
    print("=" * 80)
    
    async def run_tests():
        success_count = 0
        total_tests = 4
        
        # Test 1: Initialisation
        init_success, components = await test_components_initialization()
        if init_success:
            success_count += 1
            conv_orchestrator, llm_orchestrator = components
        else:
            print("❌ Échec critique - arrêt des tests")
            return False
        
        # Test 2: Intégration basique
        if await test_basic_integration(conv_orchestrator, llm_orchestrator):
            success_count += 1
        
        # Test 3: Communication croisée
        if await test_cross_communication(conv_orchestrator, llm_orchestrator):
            success_count += 1
        
        # Test 4: Performance
        if await test_performance_integration(conv_orchestrator, llm_orchestrator):
            success_count += 1
        
        # Rapport final
        print(f"\n📊 RÉSULTATS FINAUX")
        print("=" * 80)
        print(f"✅ Tests réussis: {success_count}/{total_tests}")
        print(f"📈 Taux de succès: {success_count/total_tests*100:.1f}%")
        
        if success_count == total_tests:
            print("🎉 INTÉGRATION VALIDÉE - Tous les tests sont passés!")
            return True
        else:
            print("⚠️  INTÉGRATION PARTIELLE - Certains tests ont échoué")
            return False
    
    # Exécuter les tests
    success = asyncio.run(run_tests())
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
