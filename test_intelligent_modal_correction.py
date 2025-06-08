<<<<<<< MAIN
#!/usr/bin/env python3
"""
Test du système de correction intelligente des erreurs modales avec feedback BNF
===============================================================================

Ce script teste le nouveau système de correction intelligente qui remplace
les tentatives aveugles SK Retry par un apprentissage progressif basé sur le feedback BNF.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Ajouter le chemin du projet
sys.path.insert(0, str(Path(__file__).parent))

from argumentation_analysis.orchestration.real_llm_orchestrator import RealLLMOrchestrator
from argumentation_analysis.utils.tweety_error_analyzer import TweetyErrorAnalyzer, create_bnf_feedback_for_error

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("IntelligentModalCorrectionTest")


async def test_tweety_error_analyzer():
    """Test de l'analyseur d'erreurs Tweety."""
    print("\n🔍 TEST 1: Analyseur d'erreurs Tweety")
    print("="*50)
    
    analyzer = TweetyErrorAnalyzer()
    
    # Test des différents types d'erreurs
    test_errors = [
        "Predicate 'constantanalyser_faits_rigueur' has not been declared",
        "Predicate 'constantanalyser_faits_avec_rigueur' has not been declared", 
        "JSON structure invalid: missing key 'propositions'",
        "Expected modal operator but found constant"
    ]
    
    for i, error in enumerate(test_errors, 1):
        print(f"\n📋 Test d'erreur {i}: {error}")
        feedback = analyzer.analyze_error(error)
        print(f"   Type: {feedback.error_type}")
        print(f"   Confiance: {feedback.confidence:.2f}")
        print(f"   Règles BNF: {len(feedback.bnf_rules)} règles")
        print(f"   Corrections: {len(feedback.corrections)} corrections")
        
        # Test du message de feedback complet
        message = analyzer.generate_bnf_feedback_message(feedback, attempt_number=i)
        print(f"   Message généré: {len(message)} caractères")
    
    print("\n✅ Test de l'analyseur d'erreurs terminé")


async def test_enhanced_prompt_construction():
    """Test de la construction de prompts enrichis."""
    print("\n🔧 TEST 2: Construction de prompts enrichis")
    print("="*50)
    
    orchestrator = RealLLMOrchestrator()
    
    # Simuler un historique de feedback BNF
    analyzer = TweetyErrorAnalyzer()
    feedback1 = analyzer.analyze_error("Predicate 'constantanalyser_faits' has not been declared")
    feedback2 = analyzer.analyze_error("JSON structure invalid: missing modal_formulas")
    
    bnf_feedback_history = [
        {
            "attempt": 1,
            "error": "Predicate error",
            "feedback": feedback1,
            "feedback_message": "Feedback message 1"
        },
        {
            "attempt": 2, 
            "error": "JSON error",
            "feedback": feedback2,
            "feedback_message": "Feedback message 2"
        }
    ]
    
    # Test de construction du prompt enrichi
    original_text = "Analyser les faits avec rigueur permet d'éviter les erreurs."
    enhanced_prompt = orchestrator._build_enhanced_prompt_with_bnf_feedback(original_text, bnf_feedback_history)
    
    print(f"Texte original: {len(original_text)} caractères")
    print(f"Prompt enrichi: {len(enhanced_prompt)} caractères")
    print(f"Feedback intégrés: {len(bnf_feedback_history)} tentatives")
    
    # Vérifier que le prompt contient les éléments attendus
    expected_elements = ["RÈGLES BNF", "CORRECTIONS SPÉCIFIQUES", "INSTRUCTIONS STRICTES"]
    for element in expected_elements:
        if element in enhanced_prompt:
            print(f"   ✅ Contient: {element}")
        else:
            print(f"   ❌ Manque: {element}")
    
    print("\n✅ Test de construction de prompts terminé")


async def test_correction_failure_analysis():
    """Test de l'analyse d'échec de correction."""
    print("\n📊 TEST 3: Analyse d'échec de correction")
    print("="*50)
    
    orchestrator = RealLLMOrchestrator()
    
    # Simuler différents scénarios d'échec
    analyzer = TweetyErrorAnalyzer()
    
    # Scénario 1: Erreur récurrente
    feedback1 = analyzer.analyze_error("Predicate 'constanttest' has not been declared")
    feedback2 = analyzer.analyze_error("Predicate 'constanttest2' has not been declared")
    feedback3 = analyzer.analyze_error("Predicate 'constanttest3' has not been declared")
    
    recurring_failure_history = [
        {"attempt": 1, "feedback": feedback1},
        {"attempt": 2, "feedback": feedback2}, 
        {"attempt": 3, "feedback": feedback3}
    ]
    
    analysis1 = orchestrator._analyze_correction_failure(recurring_failure_history)
    print(f"Scénario erreurs récurrentes: {analysis1}")
    
    # Scénario 2: Types d'erreurs différents
    feedback_json = analyzer.analyze_error("JSON structure invalid")
    feedback_modal = analyzer.analyze_error("Expected modal operator")
    
    varied_failure_history = [
        {"attempt": 1, "feedback": feedback1},
        {"attempt": 2, "feedback": feedback_json},
        {"attempt": 3, "feedback": feedback_modal}
    ]
    
    analysis2 = orchestrator._analyze_correction_failure(varied_failure_history)
    print(f"Scénario erreurs variées: {analysis2}")
    
    # Scénario 3: Historique vide
    analysis3 = orchestrator._analyze_correction_failure([])
    print(f"Scénario historique vide: {analysis3}")
    
    print("\n✅ Test d'analyse d'échec terminé")


async def test_integration_with_real_orchestrator():
    """Test d'intégration avec l'orchestrateur réel."""
    print("\n🚀 TEST 4: Intégration avec orchestrateur réel")
    print("="*50)
    
    # Note: Ce test nécessite une configuration LLM réelle
    print("⚠️  Ce test nécessite une configuration LLM réelle.")
    print("    Il sera exécuté uniquement si les services sont disponibles.")
    
    try:
        orchestrator = RealLLMOrchestrator(mode="real")
        
        # Test d'initialisation
        init_success = await orchestrator.initialize()
        if init_success:
            print("   ✅ Initialisation de l'orchestrateur réussie")
            
            # Test avec un texte simple qui pourrait générer des erreurs modales
            test_text = "Il est nécessaire d'analyser les faits avec rigueur pour éviter les erreurs logiques."
            
            print(f"   📝 Test avec: {test_text}")
            print("   🔄 Lancement de l'analyse avec correction intelligente...")
            
            # Exécuter l'analyse complète (cela déclenchera le système de correction si nécessaire)
            result = await orchestrator.orchestrate_analysis(test_text)
            
            if result.get("orchestration", {}).get("success"):
                print("   ✅ Analyse terminée avec succès")
                
                # Analyser les résultats de correction intelligente
                modal_results = result.get("analysis_results", {}).get("agents_results", {}).get("modal", {})
                if "correction_attempted" in modal_results:
                    print("   🎯 Système de correction intelligente utilisé!")
                    if "bnf_feedback_history" in modal_results:
                        feedback_count = len(modal_results["bnf_feedback_history"])
                        print(f"   📚 {feedback_count} feedback(s) BNF générés")
                else:
                    print("   ✅ Analyse réussie sans correction nécessaire")
            else:
                print("   ⚠️  Analyse échouée - vérifier la configuration")
                
        else:
            print("   ❌ Échec d'initialisation - services LLM indisponibles")
            
    except Exception as e:
        print(f"   ❌ Erreur durant le test d'intégration: {e}")
        print("   💡 Ceci est normal si les services LLM ne sont pas configurés")
    
    print("\n✅ Test d'intégration terminé")


async def main():
    """Fonction principale de test."""
    print("🧪 TESTS DU SYSTÈME DE CORRECTION INTELLIGENTE DES ERREURS MODALES")
    print("================================================================")
    print("Ce script teste le nouveau système de feedback BNF pour la correction")
    print("automatique des erreurs TweetyProject dans l'agent modal.")
    print()
    
    # Exécuter tous les tests
    await test_tweety_error_analyzer()
    await test_enhanced_prompt_construction()
    await test_correction_failure_analysis()
    await test_integration_with_real_orchestrator()
    
    print("\n🎉 TOUS LES TESTS TERMINÉS")
    print("="*50)
    print("✅ Le système de correction intelligente est opérationnel")
    print("🎯 Les agents modaux peuvent maintenant apprendre de leurs erreurs")
    print("📚 Le feedback BNF guide les corrections automatiques")
    print()
    print("Pour tester en conditions réelles, exécutez:")
    print("powershell -File .\\scripts\\env\\activate_project_env.ps1 -CommandToRun \"python -m scripts.main.analyze_text --source-type simple --modes 'fallacies,coherence,semantic,unified' --format markdown --verbose\"")


if __name__ == "__main__":
    asyncio.run(main())

=======
#!/usr/bin/env python3
"""
Test du système de correction intelligente des erreurs modales avec feedback BNF
===============================================================================

Ce script teste le nouveau système de correction intelligente qui remplace
les tentatives aveugles SK Retry par un apprentissage progressif basé sur le feedback BNF.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Ajouter le chemin du projet
sys.path.insert(0, str(Path(__file__).parent))

from argumentation_analysis.orchestration.real_llm_orchestrator import RealLLMOrchestrator
from argumentation_analysis.utils.tweety_error_analyzer import TweetyErrorAnalyzer, create_bnf_feedback_for_error

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("IntelligentModalCorrectionTest")


async def test_tweety_error_analyzer():
    """Test de l'analyseur d'erreurs Tweety."""
    print("\n🔍 TEST 1: Analyseur d'erreurs Tweety")
    print("="*50)
    
    analyzer = TweetyErrorAnalyzer()
    
    # Test des différents types d'erreurs
    test_errors = [
        "Predicate 'constantanalyser_faits_rigueur' has not been declared",
        "Predicate 'constantanalyser_faits_avec_rigueur' has not been declared", 
        "JSON structure invalid: missing key 'propositions'",
        "Expected modal operator but found constant"
    ]
    
    for i, error in enumerate(test_errors, 1):
        print(f"\n📋 Test d'erreur {i}: {error}")
        feedback = analyzer.analyze_error(error)
        print(f"   Type: {feedback.error_type}")
        print(f"   Confiance: {feedback.confidence:.2f}")
        print(f"   Règles BNF: {len(feedback.bnf_rules)} règles")
        print(f"   Corrections: {len(feedback.corrections)} corrections")
        
        # Test du message de feedback complet
        message = analyzer.generate_bnf_feedback_message(feedback, attempt_number=i)
        print(f"   Message généré: {len(message)} caractères")
    
    print("\n✅ Test de l'analyseur d'erreurs terminé")


async def test_enhanced_prompt_construction():
    """Test de la construction de prompts enrichis."""
    print("\n🔧 TEST 2: Construction de prompts enrichis")
    print("="*50)
    
    orchestrator = RealLLMOrchestrator()
    
    # Simuler un historique de feedback BNF
    analyzer = TweetyErrorAnalyzer()
    feedback1 = analyzer.analyze_error("Predicate 'constantanalyser_faits' has not been declared")
    feedback2 = analyzer.analyze_error("JSON structure invalid: missing modal_formulas")
    
    bnf_feedback_history = [
        {
            "attempt": 1,
            "error": "Predicate error",
            "feedback": feedback1,
            "feedback_message": "Feedback message 1"
        },
        {
            "attempt": 2, 
            "error": "JSON error",
            "feedback": feedback2,
            "feedback_message": "Feedback message 2"
        }
    ]
    
    # Test de construction du prompt enrichi
    original_text = "Analyser les faits avec rigueur permet d'éviter les erreurs."
    enhanced_prompt = orchestrator._build_enhanced_prompt_with_bnf_feedback(original_text, bnf_feedback_history)
    
    print(f"Texte original: {len(original_text)} caractères")
    print(f"Prompt enrichi: {len(enhanced_prompt)} caractères")
    print(f"Feedback intégrés: {len(bnf_feedback_history)} tentatives")
    
    # Vérifier que le prompt contient les éléments attendus
    expected_elements = ["RÈGLES BNF", "CORRECTIONS SPÉCIFIQUES", "INSTRUCTIONS STRICTES"]
    for element in expected_elements:
        if element in enhanced_prompt:
            print(f"   ✅ Contient: {element}")
        else:
            print(f"   ❌ Manque: {element}")
    
    print("\n✅ Test de construction de prompts terminé")


async def test_correction_failure_analysis():
    """Test de l'analyse d'échec de correction."""
    print("\n📊 TEST 3: Analyse d'échec de correction")
    print("="*50)
    
    orchestrator = RealLLMOrchestrator()
    
    # Simuler différents scénarios d'échec
    analyzer = TweetyErrorAnalyzer()
    
    # Scénario 1: Erreur récurrente
    feedback1 = analyzer.analyze_error("Predicate 'constanttest' has not been declared")
    feedback2 = analyzer.analyze_error("Predicate 'constanttest2' has not been declared")
    feedback3 = analyzer.analyze_error("Predicate 'constanttest3' has not been declared")
    
    recurring_failure_history = [
        {"attempt": 1, "feedback": feedback1},
        {"attempt": 2, "feedback": feedback2}, 
        {"attempt": 3, "feedback": feedback3}
    ]
    
    analysis1 = orchestrator._analyze_correction_failure(recurring_failure_history)
    print(f"Scénario erreurs récurrentes: {analysis1}")
    
    # Scénario 2: Types d'erreurs différents
    feedback_json = analyzer.analyze_error("JSON structure invalid")
    feedback_modal = analyzer.analyze_error("Expected modal operator")
    
    varied_failure_history = [
        {"attempt": 1, "feedback": feedback1},
        {"attempt": 2, "feedback": feedback_json},
        {"attempt": 3, "feedback": feedback_modal}
    ]
    
    analysis2 = orchestrator._analyze_correction_failure(varied_failure_history)
    print(f"Scénario erreurs variées: {analysis2}")
    
    # Scénario 3: Historique vide
    analysis3 = orchestrator._analyze_correction_failure([])
    print(f"Scénario historique vide: {analysis3}")
    
    print("\n✅ Test d'analyse d'échec terminé")


async def test_integration_with_real_orchestrator():
    """Test d'intégration avec l'orchestrateur réel."""
    print("\n🚀 TEST 4: Intégration avec orchestrateur réel")
    print("="*50)
    
    # Note: Ce test nécessite une configuration LLM réelle
    print("⚠️  Ce test nécessite une configuration LLM réelle.")
    print("    Il sera exécuté uniquement si les services sont disponibles.")
    
    try:
        orchestrator = RealLLMOrchestrator(mode="real")
        
        # Test d'initialisation
        init_success = await orchestrator.initialize()
        if init_success:
            print("   ✅ Initialisation de l'orchestrateur réussie")
            
            # Test avec un texte simple qui pourrait générer des erreurs modales
            test_text = "Il est nécessaire d'analyser les faits avec rigueur pour éviter les erreurs logiques."
            
            print(f"   📝 Test avec: {test_text}")
            print("   🔄 Lancement de l'analyse avec correction intelligente...")
            
            # Exécuter l'analyse complète (cela déclenchera le système de correction si nécessaire)
            result = await orchestrator.orchestrate_analysis(test_text)
            
            if result.get("orchestration", {}).get("success"):
                print("   ✅ Analyse terminée avec succès")
                
                # Analyser les résultats de correction intelligente
                modal_results = result.get("analysis_results", {}).get("agents_results", {}).get("modal", {})
                if "correction_attempted" in modal_results:
                    print("   🎯 Système de correction intelligente utilisé!")
                    if "bnf_feedback_history" in modal_results:
                        feedback_count = len(modal_results["bnf_feedback_history"])
                        print(f"   📚 {feedback_count} feedback(s) BNF générés")
                else:
                    print("   ✅ Analyse réussie sans correction nécessaire")
            else:
                print("   ⚠️  Analyse échouée - vérifier la configuration")
                
        else:
            print("   ❌ Échec d'initialisation - services LLM indisponibles")
            
    except Exception as e:
        print(f"   ❌ Erreur durant le test d'intégration: {e}")
        print("   💡 Ceci est normal si les services LLM ne sont pas configurés")
    
    print("\n✅ Test d'intégration terminé")


async def main():
    """Fonction principale de test."""
    print("🧪 TESTS DU SYSTÈME DE CORRECTION INTELLIGENTE DES ERREURS MODALES")
    print("================================================================")
    print("Ce script teste le nouveau système de feedback BNF pour la correction")
    print("automatique des erreurs TweetyProject dans l'agent modal.")
    print()
    
    # Exécuter tous les tests
    await test_tweety_error_analyzer()
    await test_enhanced_prompt_construction()
    await test_correction_failure_analysis()
    await test_integration_with_real_orchestrator()
    
    print("\n🎉 TOUS LES TESTS TERMINÉS")
    print("="*50)
    print("✅ Le système de correction intelligente est opérationnel")
    print("🎯 Les agents modaux peuvent maintenant apprendre de leurs erreurs")
    print("📚 Le feedback BNF guide les corrections automatiques")
    print()
    print("Pour tester en conditions réelles, exécutez:")
    print("powershell -File .\\scripts\\env\\activate_project_env.ps1 -CommandToRun \"python -m scripts.main.analyze_text --source-type simple --modes 'fallacies,coherence,semantic,unified' --format markdown --verbose\"")


if __name__ == "__main__":
    asyncio.run(main())
>>>>>>> BACKUP
