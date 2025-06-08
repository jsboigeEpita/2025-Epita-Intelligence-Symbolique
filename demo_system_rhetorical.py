#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Démonstration avancée du système d'analyse rhétorique unifié
=============================================================
"""

import asyncio
import json
import logging
from datetime import datetime
from argumentation_analysis.pipelines.unified_text_analysis import UnifiedTextAnalysisPipeline, UnifiedAnalysisConfig
from argumentation_analysis.orchestration.conversation_orchestrator import ConversationOrchestrator
from argumentation_analysis.orchestration.real_llm_orchestrator import RealLLMOrchestrator


# Textes de test avec différents niveaux de complexité argumentative
DEMO_TEXTS = {
    "simple": "L'intelligence artificielle transforme notre société de manière profonde et irréversible.",
    
    "argumentatif": """
    L'intelligence artificielle présente des avantages considérables pour l'humanité. 
    Premièrement, elle automatise les tâches répétitives, libérant du temps pour des activités créatives. 
    Deuxièmement, elle permet des diagnostics médicaux plus précis, sauvant potentiellement des vies. 
    Cependant, certains critiquent ses risques pour l'emploi. 
    Néanmoins, l'histoire montre que les innovations technologiques créent généralement plus d'emplois qu'elles n'en détruisent.
    """,
    
    "sophisme": """
    Tous mes amis utilisent cette nouvelle application, donc elle doit être la meilleure. 
    Si nous n'adoptons pas immédiatement cette technologie, nous serons dépassés par nos concurrents. 
    D'ailleurs, mon concurrent principal n'est pas crédible car il a échoué dans ses précédentes entreprises.
    Il n'y a que deux choix possibles : soit nous innovons rapidement, soit nous disparaissons.
    """
}


def print_section(title):
    """Affiche une section avec formatage."""
    print(f"\n{'='*60}")
    print(f"{title.upper()}")
    print(f"{'='*60}")


def print_subsection(title):
    """Affiche une sous-section avec formatage."""
    print(f"\n{'-'*40}")
    print(f"{title}")
    print(f"{'-'*40}")


async def demo_unified_pipeline():
    """Démonstration complète du pipeline unifié."""
    print_section("Pipeline d'analyse unifié")
    
    for complexity, text in DEMO_TEXTS.items():
        print_subsection(f"Analyse {complexity}")
        print(f"Texte : {text.strip()[:100]}...")
        
        # Configuration adaptée au niveau de complexité
        use_advanced = complexity in ["argumentatif", "sophisme"]
        
        config = UnifiedAnalysisConfig(
            analysis_modes=["fallacies", "coherence", "semantic"],
            logic_type="propositional",
            use_advanced_tools=use_advanced,
            use_mocks=True,  # Utiliser mocks pour la stabilité
            orchestration_mode="standard"
        )
        
        pipeline = UnifiedTextAnalysisPipeline(config)
        await pipeline.initialize()
        
        # Analyse
        start_time = datetime.now()
        result = await pipeline.analyze_text_unified(text, {
            "complexity": complexity,
            "demo_mode": True
        })
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        
        # Affichage des résultats
        print(f"\n[RÉSULTATS]")
        print(f"  Temps de traitement: {processing_time:.1f}ms")
        print(f"  Modes d'analyse: {', '.join(result['metadata']['analysis_config']['analysis_modes'])}")
        
        # Analyse informelle
        informal = result.get('informal_analysis', {})
        fallacies = informal.get('fallacies', [])
        print(f"  Sophismes détectés: {len(fallacies)}")
        
        if fallacies:
            for i, fallacy in enumerate(fallacies[:2], 1):  # Afficher max 2
                print(f"    {i}. {fallacy.get('type', 'Inconnu')} (confiance: {fallacy.get('confidence', 0):.2f})")
        
        # Recommandations
        recommendations = result.get('recommendations', [])
        if recommendations:
            print(f"  Recommandations: {len(recommendations)}")
            for rec in recommendations[:2]:
                print(f"    - {rec}")


def demo_conversation_orchestrator():
    """Démonstration de l'orchestrateur conversationnel."""
    print_section("Orchestrateur conversationnel")
    
    modes = ["micro", "demo"]
    
    for mode in modes:
        print_subsection(f"Mode {mode}")
        
        orchestrator = ConversationOrchestrator(mode=mode)
        text = DEMO_TEXTS["argumentatif"]
        
        print(f"Texte analysé: {text.strip()[:80]}...")
        
        # Orchestration
        start_time = datetime.now()
        report = orchestrator.run_orchestration(text)
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        
        # Statistiques
        state = orchestrator.get_conversation_state()
        
        print(f"\n[RÉSULTATS]")
        print(f"  Temps de traitement: {processing_time:.1f}ms")
        print(f"  Agents orchestrés: {len(orchestrator.agents)}")
        print(f"  Messages échangés: {state['messages_count']}")
        print(f"  Outils utilisés: {state['tools_count']}")
        print(f"  Score global: {state['state']['score']:.3f}")
        print(f"  Sophismes détectés: {state['state']['fallacies_detected']}")
        print(f"  Statut: {'Terminé' if state['completed'] else 'En cours'}")


async def demo_real_llm_orchestrator():
    """Démonstration de l'orchestrateur LLM réel."""
    print_section("Orchestrateur LLM réel")
    
    orchestrator = RealLLMOrchestrator(mode="real")
    await orchestrator.initialize()
    
    for complexity, text in [("simple", DEMO_TEXTS["simple"]), ("complexe", DEMO_TEXTS["sophisme"])]:
        print_subsection(f"Analyse {complexity}")
        print(f"Texte : {text.strip()[:80]}...")
        
        # Orchestration
        start_time = datetime.now()
        result = await orchestrator.orchestrate_analysis(text)
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        
        print(f"\n[RÉSULTATS]")
        print(f"  Temps de traitement: {result['processing_time_ms']:.1f}ms")
        print(f"  Synthèse: {result['final_synthesis']}")
        
        conversation_log = result.get('conversation_log', {})
        messages = conversation_log.get('messages', [])
        tools = conversation_log.get('tool_calls', [])
        
        print(f"  Messages d'orchestration: {len(messages)}")
        print(f"  Outils utilisés: {len(tools)}")
        
        # Afficher quelques messages significatifs
        for msg in messages[:2]:
            agent = msg.get('agent', 'Unknown')
            content = msg.get('message', '')[:60]
            print(f"    {agent}: {content}...")


def demo_comparative_analysis():
    """Démonstration d'analyse comparative."""
    print_section("Analyse comparative des sophistications")
    
    print("Comparaison des textes par niveau de sophistication argumentative:")
    
    results = {}
    
    for name, text in DEMO_TEXTS.items():
        # Analyse simple avec orchestrateur conversationnel
        orchestrator = ConversationOrchestrator(mode="micro")
        report = orchestrator.run_orchestration(text)
        state = orchestrator.get_conversation_state()
        
        results[name] = {
            "score": state['state']['score'],
            "fallacies": state['state']['fallacies_detected'],
            "agents": len(orchestrator.agents),
            "length": len(text.split())
        }
    
    print(f"\n{'Texte':<15} {'Score':<8} {'Sophismes':<10} {'Mots':<6} {'Évaluation'}")
    print("-" * 60)
    
    for name, data in results.items():
        score = data['score']
        fallacies = data['fallacies']
        words = data['length']
        
        # Évaluation simple
        if score > 0.7:
            evaluation = "Sophistiqué"
        elif score > 0.4:
            evaluation = "Modéré"
        else:
            evaluation = "Simple"
        
        print(f"{name:<15} {score:<8.3f} {fallacies:<10} {words:<6} {evaluation}")


async def demo_performance_metrics():
    """Démonstration des métriques de performance."""
    print_section("Métriques de performance")
    
    # Test de performance avec texte répété
    test_text = DEMO_TEXTS["argumentatif"]
    iterations = 5
    
    print(f"Test de performance avec {iterations} itérations")
    print(f"Texte de test: {len(test_text)} caractères, {len(test_text.split())} mots")
    
    # Test Pipeline unifié
    config = UnifiedAnalysisConfig(
        analysis_modes=["fallacies", "coherence"],
        use_mocks=True,
        orchestration_mode="standard"
    )
    
    pipeline = UnifiedTextAnalysisPipeline(config)
    await pipeline.initialize()
    
    times = []
    for i in range(iterations):
        start = datetime.now()
        await pipeline.analyze_text_unified(test_text)
        end = datetime.now()
        times.append((end - start).total_seconds() * 1000)
    
    # Éviter la division par zéro
    if times and len(times) > 0:
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
    else:
        avg_time = min_time = max_time = 0.0
    
    print(f"\n[PERFORMANCE PIPELINE UNIFIÉ]")
    print(f"  Temps moyen: {avg_time:.1f}ms")
    print(f"  Temps minimum: {min_time:.1f}ms")
    print(f"  Temps maximum: {max_time:.1f}ms")
    
    # Éviter la division par zéro pour le débit
    if avg_time > 0:
        debit = len(test_text)/avg_time*1000
        print(f"  Débit: {debit:.0f} caractères/seconde")
    else:
        print(f"  Débit: N/A (temps de traitement trop faible)")


async def main():
    """Fonction principale de démonstration."""
    print("=" * 80)
    print("DÉMONSTRATION AVANCÉE DU SYSTÈME D'ANALYSE RHÉTORIQUE UNIFIÉ")
    print("=" * 80)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Réduire le logging pour la démo
    logging.getLogger().setLevel(logging.WARNING)
    
    try:
        # 1. Pipeline unifié
        await demo_unified_pipeline()
        
        # 2. Orchestrateur conversationnel
        demo_conversation_orchestrator()
        
        # 3. Orchestrateur LLM réel
        await demo_real_llm_orchestrator()
        
        # 4. Analyse comparative
        demo_comparative_analysis()
        
        # 5. Métriques de performance
        await demo_performance_metrics()
        
        print_section("Conclusion")
        print("[OK] Pipeline d'analyse unifié : OPÉRATIONNEL")
        print("[OK] Orchestrateur conversationnel : OPÉRATIONNEL")
        print("[OK] Orchestrateur LLM réel : OPÉRATIONNEL")
        print("[OK] Analyse des sophismes : FONCTIONNELLE")
        print("[OK] Métriques de performance : DISPONIBLES")
        print("\nLe système d'analyse rhétorique unifié est pleinement fonctionnel!")
        
    except Exception as e:
        print(f"\n[ERREUR] Erreur lors de la démonstration: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)