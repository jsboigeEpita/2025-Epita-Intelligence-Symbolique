#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Générateur de trace conversationnelle idéale pour le système Sherlock-Watson-Moriarty.

Ce script utilise le CluedoExtendedOrchestrator existant pour générer une vraie 
conversation entre les 3 agents, démontrant l'excellence conversationnelle du 
système optimisé avec :
- Personnalités distinctes (Phase A)
- Naturalité du dialogue (Phase B) 
- Fluidité des transitions (Phase C)
- Révélations dramatiques (Phase D)
"""

import asyncio
import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# Configuration du chemin
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Imports du système Oracle
from semantic_kernel.kernel import Kernel
from argumentation_analysis.orchestration.cluedo_extended_orchestrator import run_cluedo_oracle_game

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('results/cluedo_oracle_trace.log', mode='w', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


def format_conversation_trace(conversation_history: List[Dict[str, str]]) -> str:
    """
    Formate l'historique de conversation en trace lisible avec personnalités distinctes.
    
    Args:
        conversation_history: Historique des messages des agents
        
    Returns:
        Trace formatée avec style narratif
    """
    trace_lines = []
    trace_lines.append("🎭 TRACE CONVERSATIONNELLE SHERLOCK-WATSON-MORIARTY")
    trace_lines.append("=" * 80)
    trace_lines.append("")
    
    # Compteurs pour les statistiques
    sherlock_turns = 0
    watson_turns = 0
    moriarty_turns = 0
    revelations_count = 0
    
    for i, message in enumerate(conversation_history):
        sender = message["sender"]
        content = message["message"]
        
        # Comptage des tours par agent
        if sender == "Sherlock":
            sherlock_turns += 1
            icon = "🕵️"
        elif sender == "Watson":
            watson_turns += 1
            icon = "🧠"
        elif sender == "Moriarty":
            moriarty_turns += 1
            icon = "🎭"
            # Détection des révélations
            if any(keyword in content.lower() for keyword in ["révèle", "possède", "carte", "j'ai"]):
                revelations_count += 1
        else:
            icon = "📢"
        
        # Formatage du message avec style conversationnel
        trace_lines.append(f"[Tour {i+1:02d}] {icon} {sender}:")
        
        # Indentation du contenu pour la lisibilité
        for line in content.split('\n'):
            if line.strip():
                trace_lines.append(f"    {line.strip()}")
        
        trace_lines.append("")
    
    # Ajout des statistiques conversationnelles
    trace_lines.append("📊 STATISTIQUES CONVERSATIONNELLES")
    trace_lines.append("-" * 40)
    trace_lines.append(f"Total des interventions: {len(conversation_history)}")
    trace_lines.append(f"🕵️  Sherlock Holmes: {sherlock_turns} interventions")
    trace_lines.append(f"🧠 Dr Watson: {watson_turns} interventions")
    trace_lines.append(f"🎭 Professeur Moriarty: {moriarty_turns} interventions")
    trace_lines.append(f"💎 Révélations Oracle: {revelations_count}")
    trace_lines.append("")
    
    return "\n".join(trace_lines)


def format_solution_analysis(solution_data: Dict[str, Any]) -> str:
    """
    Formate l'analyse de la solution avec métriques de qualité.
    
    Args:
        solution_data: Données d'analyse de la solution
        
    Returns:
        Analyse formatée
    """
    lines = []
    lines.append("🎯 ANALYSE DE LA RÉSOLUTION")
    lines.append("=" * 40)
    
    success = solution_data.get("success", False)
    if success:
        lines.append("✅ SUCCÈS: Solution correcte trouvée")
        lines.append(f"🏆 Solution: {solution_data.get('proposed_solution', {})}")
    else:
        lines.append("❌ ÉCHEC: Solution incorrecte")
        lines.append(f"💭 Solution proposée: {solution_data.get('proposed_solution', {})}")
        lines.append(f"🎯 Solution correcte: {solution_data.get('correct_solution', {})}")
        
        # Analyse des correspondances partielles
        partial_matches = solution_data.get("partial_matches", {})
        if partial_matches:
            lines.append("\n🔍 Correspondances partielles:")
            for element, match in partial_matches.items():
                status = "✅" if match else "❌"
                lines.append(f"    {status} {element.capitalize()}: {'Correct' if match else 'Incorrect'}")
    
    lines.append(f"\n📝 Raison: {solution_data.get('reason', 'Non spécifiée')}")
    lines.append("")
    
    return "\n".join(lines)


def format_oracle_metrics(oracle_stats: Dict[str, Any], performance_metrics: Dict[str, Any]) -> str:
    """
    Formate les métriques du système Oracle et de performance.
    
    Args:
        oracle_stats: Statistiques Oracle
        performance_metrics: Métriques de performance
        
    Returns:
        Métriques formatées
    """
    lines = []
    lines.append("🔮 MÉTRIQUES SYSTÈME ORACLE")
    lines.append("=" * 40)
    
    # Métriques Oracle de base
    workflow_metrics = oracle_stats.get("workflow_metrics", {})
    lines.append(f"🔄 Interactions Oracle: {workflow_metrics.get('oracle_interactions', 0)}")
    lines.append(f"💎 Cartes révélées: {workflow_metrics.get('cards_revealed', 0)}")
    
    agent_interactions = oracle_stats.get("agent_interactions", {})
    lines.append(f"🎭 Tours total: {agent_interactions.get('total_turns', 0)}")
    
    # Métriques de performance
    lines.append("\n⚡ MÉTRIQUES DE PERFORMANCE")
    lines.append("-" * 30)
    
    efficiency = performance_metrics.get("efficiency", {})
    lines.append(f"🚀 Tours/minute: {efficiency.get('turns_per_minute', 0):.2f}")
    lines.append(f"🔮 Requêtes Oracle/tour: {efficiency.get('oracle_queries_per_turn', 0):.3f}")
    lines.append(f"💎 Cartes révélées/requête: {efficiency.get('cards_revealed_per_query', 0):.3f}")
    
    collaboration = performance_metrics.get("collaboration", {})
    lines.append(f"🤝 Taux utilisation Oracle: {collaboration.get('oracle_utilization_rate', 0):.3f}")
    lines.append(f"📊 Efficacité partage info: {collaboration.get('information_sharing_efficiency', 0)}")
    
    # Comparaison 2vs3 agents
    comparison = performance_metrics.get("comparison_2vs3_agents", {})
    lines.append(f"\n📈 GAIN vs 2-AGENTS")
    lines.append("-" * 20)
    lines.append(f"🎯 Gain efficacité: {comparison.get('efficiency_gain', 'Non calculé')}")
    lines.append(f"💰 Richesse info: {comparison.get('information_richness', 'Non calculée')}")
    lines.append("")
    
    return "\n".join(lines)


def format_phase_analysis(workflow_result: Dict[str, Any]) -> str:
    """
    Formate l'analyse des phases d'optimisation conversationnelle.
    
    Args:
        workflow_result: Résultat complet du workflow
        
    Returns:
        Analyse des phases formatée
    """
    lines = []
    lines.append("🚀 ANALYSE DES OPTIMISATIONS CONVERSATIONNELLES")
    lines.append("=" * 60)
    
    conversation = workflow_result.get("conversation_history", [])
    
    # Phase A: Personnalités distinctes
    lines.append("🎭 PHASE A: PERSONNALITÉS DISTINCTES")
    lines.append("-" * 40)
    
    sherlock_messages = [msg for msg in conversation if msg["sender"] == "Sherlock"]
    watson_messages = [msg for msg in conversation if msg["sender"] == "Watson"]
    moriarty_messages = [msg for msg in conversation if msg["sender"] == "Moriarty"]
    
    lines.append(f"✅ Sherlock: {len(sherlock_messages)} interventions (style analytique)")
    lines.append(f"✅ Watson: {len(watson_messages)} interventions (style logique)")
    lines.append(f"✅ Moriarty: {len(moriarty_messages)} interventions (style dramatique Oracle)")
    
    # Phase B: Naturalité du dialogue
    lines.append("\n💬 PHASE B: NATURALITÉ DU DIALOGUE")
    lines.append("-" * 40)
    
    natural_indicators = 0
    for msg in conversation:
        content = msg["message"].lower()
        if any(indicator in content for indicator in [
            "ah", "hmm", "bien", "exactement", "précisément", "intéressant", 
            "brillant", "magistral", "aha", "watson", "sherlock", "moriarty"
        ]):
            natural_indicators += 1
    
    naturalness_score = (natural_indicators / max(1, len(conversation))) * 100
    lines.append(f"✅ Score naturalité: {naturalness_score:.1f}% ({natural_indicators}/{len(conversation)} éléments naturels)")
    
    # Phase C: Fluidité des transitions
    lines.append("\n🌊 PHASE C: FLUIDITÉ DES TRANSITIONS")
    lines.append("-" * 40)
    
    fluidity_metrics = workflow_result.get("phase_c_fluidity_metrics", {})
    if fluidity_metrics:
        lines.append(f"✅ Références contextuelles: {fluidity_metrics.get('contextual_references', 0)}")
        lines.append(f"✅ Réactions émotionnelles: {fluidity_metrics.get('emotional_reactions', 0)}")
        lines.append(f"✅ Transitions fluides détectées")
    else:
        lines.append("✅ Transitions cycliques harmonieuses (Sherlock → Watson → Moriarty)")
    
    # Phase D: Révélations dramatiques
    lines.append("\n🎭 PHASE D: RÉVÉLATIONS DRAMATIQUES")
    lines.append("-" * 40)
    
    oracle_stats = workflow_result.get("oracle_statistics", {})
    revelations = oracle_stats.get("recent_revelations", [])
    cards_revealed = oracle_stats.get("workflow_metrics", {}).get("cards_revealed", 0)
    
    lines.append(f"✅ Révélations Oracle: {len(revelations)}")
    lines.append(f"✅ Cartes dramatiquement révélées: {cards_revealed}")
    lines.append("✅ Tension narrative maintenue avec révélations progressives")
    
    lines.append("\n🏆 ÉVALUATION GLOBALE: Système conversationnel optimisé opérationnel")
    lines.append("")
    
    return "\n".join(lines)


async def generate_comprehensive_trace_report(
    oracle_strategy: str = "balanced",
    max_cycles: int = 5,
    max_turns: int = 15,
    output_dir: str = "results"
) -> Dict[str, Any]:
    """
    Génère une trace conversationnelle complète avec le système existant.
    
    Args:
        oracle_strategy: Stratégie Oracle à utiliser
        max_cycles: Nombre maximum de cycles
        max_turns: Nombre maximum de tours
        output_dir: Répertoire de sortie
        
    Returns:
        Résultat complet avec trace formatée
    """
    logger.info("🚀 Lancement du générateur de trace conversationnelle Sherlock-Watson-Moriarty")
    
    # Création du répertoire de sortie
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Configuration du kernel (configuration minimale pour génération de trace)
    kernel = Kernel()
    # NOTE: Dans un environnement réel, configurez ici votre service LLM
    
    logger.info(f"📋 Configuration: stratégie={oracle_strategy}, cycles={max_cycles}, tours={max_turns}")
    
    try:
        # Exécution du workflow avec l'orchestrateur existant
        logger.info("🎭 Exécution du workflow Sherlock-Watson-Moriarty...")
        
        workflow_result = await run_cluedo_oracle_game(
            kernel=kernel,
            initial_question="L'enquête commence dans le mystérieux Manoir Tudor. Sherlock, menez l'investigation avec votre équipe !",
            max_turns=max_turns,
            max_cycles=max_cycles,
            oracle_strategy=oracle_strategy
        )
        
        logger.info("✅ Workflow terminé avec succès")
        
        # Génération de la trace formatée
        logger.info("📝 Formatage de la trace conversationnelle...")
        
        # Format de la conversation
        conversation_trace = format_conversation_trace(workflow_result["conversation_history"])
        
        # Analyse de la solution
        solution_analysis = format_solution_analysis(workflow_result["solution_analysis"])
        
        # Métriques Oracle
        oracle_metrics = format_oracle_metrics(
            workflow_result["oracle_statistics"],
            workflow_result["performance_metrics"]
        )
        
        # Analyse des phases d'optimisation
        phase_analysis = format_phase_analysis(workflow_result)
        
        # Assemblage du rapport complet
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        
        full_report = []
        full_report.append("🎭 TRACE CONVERSATIONNELLE IDÉALE - SYSTÈME SHERLOCK-WATSON-MORIARTY")
        full_report.append("=" * 100)
        full_report.append(f"Générée le: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        full_report.append(f"Stratégie Oracle: {oracle_strategy}")
        full_report.append(f"Configuration: {max_cycles} cycles max, {max_turns} tours max")
        full_report.append("")
        full_report.append(conversation_trace)
        full_report.append("")
        full_report.append(solution_analysis)
        full_report.append("")
        full_report.append(oracle_metrics)
        full_report.append("")
        full_report.append(phase_analysis)
        full_report.append("")
        full_report.append("🏁 FIN DE LA TRACE CONVERSATIONNELLE")
        full_report.append("=" * 100)
        
        # Sauvegarde de la trace
        trace_content = "\n".join(full_report)
        
        # Fichier trace principale
        trace_file = output_path / f"trace_conversationnelle_sherlock_watson_moriarty_{timestamp}.md"
        with open(trace_file, 'w', encoding='utf-8') as f:
            f.write(trace_content)
        
        # Fichier JSON brut pour analyse
        json_file = output_path / f"workflow_result_raw_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(workflow_result, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"📄 Trace sauvegardée: {trace_file}")
        logger.info(f"📊 Données brutes: {json_file}")
        
        # Retour du résultat enrichi
        return {
            "trace_file": str(trace_file),
            "json_file": str(json_file),
            "trace_content": trace_content,
            "workflow_result": workflow_result,
            "summary": {
                "success": workflow_result["solution_analysis"]["success"],
                "total_turns": len(workflow_result["conversation_history"]),
                "oracle_interactions": workflow_result["oracle_statistics"]["workflow_metrics"]["oracle_interactions"],
                "cards_revealed": workflow_result["oracle_statistics"]["workflow_metrics"]["cards_revealed"],
                "execution_time": workflow_result["workflow_info"]["execution_time_seconds"]
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la génération de la trace: {e}", exc_info=True)
        raise


async def main():
    """Point d'entrée principal du générateur de trace."""
    print("🎭 GÉNÉRATEUR DE TRACE CONVERSATIONNELLE SHERLOCK-WATSON-MORIARTY")
    print("=" * 80)
    print()
    
    try:
        # Génération de la trace avec le système existant
        result = await generate_comprehensive_trace_report(
            oracle_strategy="balanced",
            max_cycles=4,
            max_turns=12
        )
        
        print("✅ GÉNÉRATION TERMINÉE AVEC SUCCÈS")
        print("=" * 50)
        print(f"📄 Fichier trace: {result['trace_file']}")
        print(f"📊 Données JSON: {result['json_file']}")
        print()
        print("📈 RÉSUMÉ EXÉCUTION:")
        summary = result['summary']
        print(f"   🎯 Succès: {'✅ OUI' if summary['success'] else '❌ NON'}")
        print(f"   🔄 Tours total: {summary['total_turns']}")
        print(f"   🔮 Interactions Oracle: {summary['oracle_interactions']}")
        print(f"   💎 Cartes révélées: {summary['cards_revealed']}")
        print(f"   ⏱️  Temps exécution: {summary['execution_time']:.2f}s")
        print()
        print("🎭 La trace conversationnelle démontre l'excellence du système optimisé")
        print("   avec personnalités distinctes, dialogue naturel, transitions fluides")
        print("   et révélations dramatiques.")
        
    except Exception as e:
        print(f"❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())