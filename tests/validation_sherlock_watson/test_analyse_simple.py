import pytest
#!/usr/bin/env python3
"""
Test simple d'analyse de trace Sherlock-Watson-Moriarty
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
import pytest

# Imports de l'infrastructure Oracle
# from argumentation_analysis.orchestration.cluedo_extended_orchestrator import run_cluedo_oracle_game
from semantic_kernel import Kernel

# Configuration du logging simple
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_workflow_simple():
    """Test simple du workflow 3-agents."""
    logger.info("DEBUT - Test du workflow 3-agents")
    
    try:
        # Configuration du kernel
        logger.info("Configuration du kernel...")
        kernel = Kernel()
        
        # Exécution du workflow
        logger.info("Lancement du workflow...")
        workflow_result = await run_cluedo_oracle_game(
            kernel=kernel,
            initial_question="L'enquête commence. Sherlock, menez l'investigation !",
            max_turns=8,
            max_cycles=3,
            oracle_strategy="balanced"
        )
        
        logger.info("Workflow terminé")
        
        # Analyse basique
        conversation_history = workflow_result.get("conversation_history", [])
        solution_analysis = workflow_result.get("solution_analysis", {})
        oracle_stats = workflow_result.get("oracle_statistics", {})
        
        print("\n" + "="*60)
        print("RESULTATS DE L'ANALYSE SIMPLE")
        print("="*60)
        
        print(f"\nMessages capturés: {len(conversation_history)}")
        print(f"Solution trouvée: {solution_analysis.get('success', False)}")
        print(f"Tours total: {oracle_stats.get('agent_interactions', {}).get('total_turns', 0)}")
        print(f"Interactions Oracle: {oracle_stats.get('workflow_metrics', {}).get('oracle_interactions', 0)}")
        print(f"Cartes révélées: {oracle_stats.get('workflow_metrics', {}).get('cards_revealed', 0)}")
        
        # Analyse des messages par agent
        print("\nMessages par agent:")
        agent_counts = {}
        for msg in conversation_history:
            sender = msg.get("sender", "Unknown")
            # Conversion en string pour éviter les objets property
            sender_str = str(sender) if sender is not None else "Unknown"
            agent_counts[sender_str] = agent_counts.get(sender_str, 0) + 1
        
        for agent, count in agent_counts.items():
            print(f"  {agent}: {count} messages")
        
        # Exemples de conversations
        print("\nEchantillon de conversation:")
        for i, msg in enumerate(conversation_history[:6]):  # 6 premiers messages
            sender = msg.get("sender", "Unknown")
            sender_str = str(sender) if sender is not None else "Unknown"
            content = msg.get("message", "")[:100]  # 100 premiers caractères
            print(f"{i+1}. [{sender_str}]: {content}...")
        
        # Analyse qualitative simple
        naturalite_score = analyze_naturalness(conversation_history)
        pertinence_score = analyze_relevance(conversation_history, agent_counts)
        progression_score = analyze_progression(solution_analysis, oracle_stats)
        
        print(f"\nScores de qualité (sur 10):")
        print(f"  Naturalité: {naturalite_score:.1f}")
        print(f"  Pertinence: {pertinence_score:.1f}")
        print(f"  Progression: {progression_score:.1f}")
        print(f"  Score global: {(naturalite_score + pertinence_score + progression_score) / 3:.1f}")
        
        # Points d'amélioration identifiés
        print(f"\nPoints d'amélioration identifiés:")
        improvements = identify_improvements(naturalite_score, pertinence_score, progression_score)
        for i, improvement in enumerate(improvements, 1):
            print(f"{i}. {improvement}")
        
        print("\n" + "="*60)
        
        # Sauvegarde simple
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Nettoyer les données pour la sérialisation JSON
        def clean_for_json(obj):
            """Convertit récursivement les objets en structures sérialisables JSON"""
            if obj is None:
                return None
            elif isinstance(obj, (str, int, float, bool)):
                return obj
            elif isinstance(obj, property):
                return str(obj)
            elif isinstance(obj, dict):
                cleaned_dict = {}
                for k, v in obj.items():
                    # Nettoyer la clé aussi
                    clean_key = str(k) if isinstance(k, property) or hasattr(k, '__dict__') else k
                    cleaned_dict[clean_key] = clean_for_json(v)
                return cleaned_dict
            elif isinstance(obj, (list, tuple)):
                return [clean_for_json(item) for item in obj]
            elif hasattr(obj, '__dict__') and not isinstance(obj, type):
                return f"<{obj.__class__.__name__} object>"
            else:
                return str(obj)
        
        # Nettoyer complètement toutes les données
        sample_conversation_cleaned = clean_for_json(conversation_history[:6])
        agent_counts_cleaned = clean_for_json(agent_counts)
        workflow_result_cleaned = clean_for_json(workflow_result)
        
        simple_report = {
            "timestamp": datetime.now().isoformat(),
            "conversation_summary": {
                "total_messages": len(conversation_history),
                "messages_by_agent": agent_counts_cleaned,
                "sample_conversation": sample_conversation_cleaned
            },
            "quality_scores": {
                "naturalite": naturalite_score,
                "pertinence": pertinence_score,
                "progression": progression_score,
                "global": (naturalite_score + pertinence_score + progression_score) / 3
            },
            "improvements": improvements,
            "full_results": workflow_result_cleaned
        }
        
        with open(f"rapport_simple_{timestamp}.json", "w", encoding="utf-8") as f:
            json.dump(simple_report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Rapport sauvegardé: rapport_simple_{timestamp}.json")
        logger.info("Test terminé avec succès")
        
        return simple_report
        
    except Exception as e:
        logger.error(f"Erreur durant le test: {e}")
        import traceback
        traceback.print_exc()
        raise


def analyze_naturalness(conversation_history):
    """Analyse simple de la naturalité (0-10)."""
    if not conversation_history:
        return 0.0
    
    score = 5.0  # Base
    
    # Vérifier la variété des longueurs
    lengths = [len(msg.get("message", "")) for msg in conversation_history]
    avg_length = sum(lengths) / len(lengths)
    
    if 50 <= avg_length <= 200:  # Longueur appropriée
        score += 1.5
    
    # Vérifier la variété du vocabulaire
    all_words = set()
    for msg in conversation_history:
        content = msg.get("message", "").lower()
        words = content.split()
        all_words.update(words)
    
    unique_words = len(all_words)
    if unique_words > 50:
        score += 1.0
    if unique_words > 100:
        score += 1.0
    
    return min(10.0, max(0.0, score))


def analyze_relevance(conversation_history, agent_counts):
    """Analyse simple de la pertinence (0-10)."""
    score = 5.0  # Base
    
    # Vérifier que Sherlock est actif
    sherlock_msgs = agent_counts.get("Sherlock", 0)
    total_msgs = sum(agent_counts.values())
    
    if total_msgs > 0:
        sherlock_ratio = sherlock_msgs / total_msgs
        if sherlock_ratio >= 0.3:  # Sherlock au moins 30% des messages
            score += 1.5
    
    # Vérifier que Watson fait de la logique
    watson_logic_count = 0
    for msg in conversation_history:
        if msg.get("sender") == "Watson":
            content = msg.get("message", "").lower()
            if any(word in content for word in ["logique", "formule", "validation", "analyse"]):
                watson_logic_count += 1
    
    if watson_logic_count > 0:
        score += 1.5
    
    # Vérifier que Moriarty révèle des informations
    moriarty_reveals = 0
    for msg in conversation_history:
        if msg.get("sender") == "Moriarty":
            content = msg.get("message", "").lower()
            if any(word in content for word in ["révèle", "carte", "réfutation", "possess"]):
                moriarty_reveals += 1
    
    if moriarty_reveals > 0:
        score += 2.0
    
    return min(10.0, max(0.0, score))


def analyze_progression(solution_analysis, oracle_stats):
    """Analyse simple de la progression (0-10)."""
    score = 3.0  # Base
    
    # Vérifier si solution trouvée
    if solution_analysis.get("success", False):
        score += 4.0
    elif solution_analysis.get("proposed_solution"):
        score += 2.0  # Tentative
    
    # Vérifier efficacité
    total_turns = oracle_stats.get("agent_interactions", {}).get("total_turns", 0)
    if total_turns <= 9:  # Efficace
        score += 1.5
    
    # Vérifier utilisation Oracle
    oracle_interactions = oracle_stats.get("workflow_metrics", {}).get("oracle_interactions", 0)
    if oracle_interactions >= 2:
        score += 1.5
    
    return min(10.0, max(0.0, score))


def identify_improvements(naturalite, pertinence, progression):
    """Identifie les améliorations prioritaires."""
    improvements = []
    
    if naturalite < 6.0:
        improvements.append("Améliorer la naturalité du dialogue (variété vocabulaire, longueur messages)")
    
    if pertinence < 6.0:
        improvements.append("Renforcer les rôles spécifiques de chaque agent")
    
    if progression < 6.0:
        improvements.append("Optimiser la logique de progression vers la solution")
    
    if naturalite < 4.0:
        improvements.append("URGENT: Dialogue trop mécanique, revoir les prompts")
    
    if pertinence < 4.0:
        improvements.append("URGENT: Agents ne respectent pas leurs rôles")
    
    if progression < 4.0:
        improvements.append("URGENT: Workflow ne converge pas vers la solution")
    
    if not improvements:
        improvements.append("Qualité satisfaisante - optimisations mineures possibles")
    
    return improvements


if __name__ == "__main__":
    asyncio.run(test_workflow_simple())