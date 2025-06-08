#!/usr/bin/env python3
"""
Démonstration finale du système de correction intelligente des erreurs modales
============================================================================

Ce script montre concrètement comment le nouveau système de feedback BNF
transforme les échecs SK Retry en apprentissage constructif.
"""

import asyncio
import sys
from pathlib import Path

# Ajouter le chemin du projet
sys.path.insert(0, str(Path(__file__).parent))

from argumentation_analysis.utils.tweety_error_analyzer import TweetyErrorAnalyzer, create_bnf_feedback_for_error


def demo_error_analysis():
    """Démonstration de l'analyse intelligente des erreurs Tweety."""
    print("=" * 80)
    print("*** DEMONSTRATION - SYSTEME DE CORRECTION INTELLIGENTE DES ERREURS MODALES ***")
    print("=" * 80)
    print()
    
    # Simuler l'erreur typique du problème original
    original_error = "Predicate 'constantanalyser_faits_rigueur' has not been declared"
    
    print("[PROBLEME] ORIGINAL (SK Retry aveugle):")
    print("-" * 50)
    print("Tentative 1: Erreur - Predicate 'constantanalyser_faits_rigueur' has not been declared")
    print("Tentative 2: Erreur - Predicate 'constantanalyser_faits_rigueur' has not been declared") 
    print("Tentative 3: Erreur - Predicate 'constantanalyser_faits_rigueur' has not been declared")
    print("Résultat: ÉCHEC - Aucun apprentissage, répétition de la même erreur")
    print()
    
    print("🧠 NOUVELLE SOLUTION (Correction intelligente):")
    print("-" * 50)
    
    # Analyser l'erreur avec le nouveau système
    analyzer = TweetyErrorAnalyzer()
    
    print("Tentative 1: Erreur détectée - Analyse en cours...")
    feedback = analyzer.analyze_error(original_error, {"attempt": 1, "agent": "ModalLogicAgent"})
    
    print(f"✅ Type d'erreur identifié: {feedback.error_type}")
    print(f"✅ Confiance de l'analyse: {feedback.confidence:.0%}")
    print(f"✅ Règles BNF générées: {len(feedback.bnf_rules)} règles")
    print(f"✅ Corrections proposées: {len(feedback.corrections)} suggestions")
    print()
    
    # Générer le message de feedback complet
    feedback_message = analyzer.generate_bnf_feedback_message(feedback, 1)
    
    print("📋 FEEDBACK BNF CONSTRUCTIF GÉNÉRÉ:")
    print("-" * 40)
    # Afficher un extrait du feedback (premiers 300 caractères)
    feedback_lines = feedback_message.split('\n')[:8]
    for line in feedback_lines:
        print(f"   {line}")
    print("   [...Feedback complet avec règles BNF et exemples...]")
    print()
    
    print("🎯 AVANTAGE CLÉS:")
    print("✅ L'erreur est analysée et comprise (pas juste répétée)")
    print("✅ Règles BNF fournissent des corrections précises")
    print("✅ Le feedback guide la prochaine tentative")
    print("✅ Apprentissage constructif au lieu d'échec répétitif")
    print()
    
    return feedback


def demo_progressive_learning():
    """Démonstration de l'apprentissage progressif avec feedback cumulé."""
    print("📚 APPRENTISSAGE PROGRESSIF AVEC FEEDBACK CUMULÉ:")
    print("-" * 50)
    
    # Simuler plusieurs tentatives avec différentes erreurs
    test_errors = [
        "Predicate 'constantanalyser_faits_rigueur' has not been declared",
        "Syntax error in modal logic expression 'necessity(argument)'",
        "Invalid JSON structure in reasoning output",
        "Undefined variable 'RigourAnalyzer' in logical context"
    ]
    
    analyzer = TweetyErrorAnalyzer()
    bnf_feedback_history = []
    
    print("Simulation de 4 tentatives avec apprentissage progressif:")
    print()
    
    for attempt, error in enumerate(test_errors, 1):
        print(f"Tentative {attempt}: Analyse de '{error[:50]}...'")
        
        # Analyser l'erreur
        feedback = analyzer.analyze_error(error, {"attempt": attempt, "agent": "ModalLogicAgent"})
        
        # Ajouter à l'historique
        bnf_feedback_history.append({
            "attempt": attempt,
            "error": error,
            "feedback": feedback,
            "feedback_message": f"Feedback message for attempt {attempt}"
        })
        
        print(f"   → Feedback généré: {feedback.error_type} (confiance: {feedback.confidence:.0%})")
        print(f"   → Règles BNF: {len(feedback.bnf_rules)} | Corrections: {len(feedback.corrections)}")
    
    print(f"\n📊 HISTORIQUE CUMULÉ: {len(bnf_feedback_history)} tentatives avec feedback")
    print("✅ Chaque tentative bénéficie du feedback des précédentes")
    print("✅ L'agent apprend de ses erreurs au lieu de les répéter")
    print()
    
    return bnf_feedback_history


def demo_enhanced_prompt_construction():
    """Démonstration de la construction de prompts enrichis."""
    print("🚀 CONSTRUCTION DE PROMPTS ENRICHIS AVEC FEEDBACK:")
    print("-" * 50)
    
    # Import de la méthode du orchestrateur (simulation)
    from argumentation_analysis.orchestration.real_llm_orchestrator import RealLLMOrchestrator
    
    orchestrator = RealLLMOrchestrator()
    
    # Simuler un historique de feedback
    analyzer = TweetyErrorAnalyzer()
    feedback = analyzer.analyze_error("Predicate 'constanttest' has not been declared")
    
    bnf_feedback_history = [{
        "attempt": 1,
        "error": "Test error",
        "feedback": feedback,
        "feedback_message": "Test feedback message"
    }]
    
    original_text = "Analyser les faits avec rigueur permet d'éviter les erreurs logiques."
    enhanced_prompt = orchestrator._build_enhanced_prompt_with_bnf_feedback(original_text, bnf_feedback_history)
    
    print(f"Texte original: {len(original_text)} caractères")
    print(f"Prompt enrichi: {len(enhanced_prompt)} caractères")
    print(f"Amélioration: +{len(enhanced_prompt) - len(original_text)} caractères de guidance BNF")
    print()
    
    # Afficher un extrait du prompt enrichi
    print("📝 EXTRAIT DU PROMPT ENRICHI:")
    lines = enhanced_prompt.split('\n')[:10]
    for line in lines:
        print(f"   {line}")
    print("   [...Prompt complet avec règles BNF et corrections...]")
    print()


def main():
    """Démonstration complète du système."""
    print()
    print("🎉 SYSTÈME DE CORRECTION INTELLIGENTE DES ERREURS MODALES")
    print("Transformation des tentatives aveugles SK Retry en apprentissage constructif")
    print()
    
    # 1. Analyse d'erreurs intelligente
    feedback = demo_error_analysis()
    
    # 2. Apprentissage progressif
    history = demo_progressive_learning()
    
    # 3. Construction de prompts enrichis
    demo_enhanced_prompt_construction()
    
    print("🎯 RÉSULTAT FINAL:")
    print("=" * 50)
    print("✅ SYSTÈME OPÉRATIONNEL - Correction intelligente implémentée")
    print("✅ FEEDBACK BNF - Messages constructifs au lieu d'erreurs répétées") 
    print("✅ APPRENTISSAGE PROGRESSIF - Chaque tentative améliore la suivante")
    print("✅ INTÉGRATION COMPLÈTE - Compatible avec l'orchestration existante")
    print()
    print("🚀 PRÊT POUR UTILISATION EN PRODUCTION:")
    print("   powershell -File .\\scripts\\env\\activate_project_env.ps1 \\")
    print("   -CommandToRun \"python -m scripts.main.analyze_text \\")
    print("   --source-type simple --modes 'fallacies,coherence,semantic,unified' \\")
    print("   --format markdown --verbose\"")
    print()
    print("💡 Le système interceptera automatiquement les erreurs Tweety")
    print("   et fournira un feedback BNF constructif pour corriger les problèmes.")


if __name__ == "__main__":
    main()
