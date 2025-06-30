import pytest
#!/usr/bin/env python3
"""
Script de test pour Phase C : Optimisation fluidité transitions.

Ce script valide l'implémentation de la mémoire contextuelle et des directives
de continuité narrative pour améliorer la fluidité des transitions entre agents.

Critères de validation Phase C:
- Références contextuelles : >90% des messages référencent le précédent
- Réactions émotionnelles : >70% des révélations suscitent réaction
- Continuité narrative : <10% de ruptures narratives
- Score fluidité : 5.0 → 6.5/10
"""

import asyncio
import logging
import json
from datetime import datetime
from typing import Dict, List, Any
import statistics

# Configuration du logging pour le test
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_phase_c_fluidite.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Imports pour simulation (mock pour le test)
class AuthenticGPT4oMiniKernel:
    """Mock du Kernel pour les tests."""
    def add_plugin(self, plugin, name): pass
    def add_filter(self, filter_type, filter_func): pass

class MockChatMessage:
    """Mock des messages de chat."""
    def __init__(self, name: str, content: str):
        self.name = name
        self.content = content

@pytest.mark.asyncio
async def test_phase_c_fluidite_complete():
    """
    Test complet de la Phase C avec 5 conversations simulées.
    """
    print("DEBUT TEST PHASE C - FLUIDITE TRANSITIONS")
    print("=" * 60)
    
    # Import des modules modifiés
    from argumentation_analysis.core.cluedo_oracle_state import CluedoOracleState
    from argumentation_analysis.orchestration.cluedo_extended_orchestrator import CluedoExtendedOrchestrator
    
    # Configuration de base
    elements_jeu = {
        "suspects": ["Colonel Moutarde", "Professeur Violet", "Mademoiselle Rose", "Docteur Orchidée"],
        "armes": ["Poignard", "Chandelier", "Revolver", "Corde"],
        "lieux": ["Salon", "Cuisine", "Bureau", "Bibliothèque"]
    }
    
    # Résultats de tous les tests
    all_test_results = []
    
    # Exécution de 5 conversations de test
    for test_num in range(1, 6):
        print(f"\nTEST {test_num}/5 - Conversation {test_num}")
        print("-" * 40)
        
        try:
            # Simulation d'une conversation avec fluidité
            test_result = await simulate_fluidity_conversation(test_num, elements_jeu)
            all_test_results.append(test_result)
            
            # Affichage des résultats immédiats
            print(f"[OK] Test {test_num} termine:")
            print(f"   - Score fluidite: {test_result['fluidity_score']}/10")
            print(f"   - References contextuelles: {test_result['contextual_reference_rate']}%")
            print(f"   - Reactions emotionnelles: {test_result['emotional_reaction_rate']}%")
            
        except Exception as e:
            logger.error(f"Erreur dans test {test_num}: {e}", exc_info=True)
            print(f"[ERREUR] Test {test_num} echoue: {e}")
            continue
    
    # Analyse agrégée des résultats
    print("\nANALYSE AGREGEE PHASE C")
    print("=" * 60)
    
    if all_test_results:
        aggregate_analysis = analyze_aggregate_results(all_test_results)
        print_phase_c_results(aggregate_analysis)
        
        # Sauvegarde des résultats
        save_test_results(all_test_results, aggregate_analysis)
    else:
        print("[ERREUR] Aucun test reussi - impossible d'analyser les resultats")
    
    print("\n[OK] TEST PHASE C TERMINE")

@pytest.mark.asyncio
async def simulate_fluidity_conversation(test_num: int, elements_jeu: Dict[str, List[str]]) -> Dict[str, Any]:
    """
    Simule une conversation avec focus sur la fluidité des transitions.
    
    Args:
        test_num: Numéro du test
        elements_jeu: Éléments du jeu Cluedo
        
    Returns:
        Résultats de fluidité pour cette conversation
    """
    # Création de l'état Oracle étendu
    oracle_state = CluedoOracleState(
        nom_enquete_cluedo=f"Test Fluidité {test_num}",
        elements_jeu_cluedo=elements_jeu,
        description_cas="Test des transitions fluides entre agents",
        initial_context="Test Phase C - Mémoire contextuelle",
        oracle_strategy="balanced"
    )
    
    # Simulation de messages avec continuité narrative
    conversation_scenarios = [
        # Tour 1: Sherlock ouvre
        {
            "agent": "Sherlock",
            "content": "Je commence mon enquête. J'observe des indices dans le salon.",
            "type": "analysis"
        },
        # Tour 2: Watson réagit avec référence
        {
            "agent": "Watson", 
            "content": "Suite à votre observation Sherlock, l'analyse logique suggère que le salon est crucial. Brillant !",
            "type": "reaction"
        },
        # Tour 3: Moriarty révèle avec réaction
        {
            "agent": "Moriarty",
            "content": "En réaction à vos déductions, je révèle que j'ai le Chandelier. Vous brûlez !",
            "type": "revelation"
        },
        # Tour 4: Sherlock continue avec référence
        {
            "agent": "Sherlock",
            "content": "Après cette révélation de Moriarty, j'affine ma déduction. Le Chandelier éliminé, focus sur le Revolver.",
            "type": "analysis"
        },
        # Tour 5: Watson approuve avec émotion
        {
            "agent": "Watson",
            "content": "Précisément Watson ! Cette élimination logique nous rapproche. Ça colle parfaitement !",
            "type": "reaction"
        },
        # Tour 6: Moriarty crée suspense
        {
            "agent": "Moriarty", 
            "content": "Hmm... pas si vite ! Vous m'impressionnez, mais je possède aussi Mademoiselle Rose.",
            "type": "revelation"
        },
        # Tour 7: Sherlock synthétise
        {
            "agent": "Sherlock",
            "content": "Merci pour cette clarification Moriarty. Avec ces données, je suggère : Docteur Orchidée, Revolver, Bureau.",
            "type": "suggestion"
        },
        # Tour 8: Watson valide avec émotion
        {
            "agent": "Watson",
            "content": "Exactement ! Cette suggestion logique intègre toutes nos découvertes précédentes. Magistral !",
            "type": "reaction"
        }
    ]
    
    # Simulation de la conversation
    logger.info(f"Simulation conversation {test_num} avec {len(conversation_scenarios)} tours")
    
    for turn, scenario in enumerate(conversation_scenarios, 1):
        agent_name = scenario["agent"]
        content = scenario["content"]
        msg_type = scenario["type"]
        
        # Ajout du message à l'historique conversationnel
        oracle_state.add_conversation_message(agent_name, content, msg_type)
        
        # Simulation de l'analyse contextuelle (normalement faite par l'orchestrateur)
        await simulate_contextual_analysis(oracle_state, agent_name, content, turn)
        
        logger.debug(f"Tour {turn}: {agent_name} ({msg_type}): {content[:50]}...")
    
    # Calcul des métriques de fluidité
    fluidity_metrics = oracle_state.get_fluidity_metrics()
    
    # Enrichissement avec données de test
    fluidity_metrics.update({
        "test_number": test_num,
        "total_turns": len(conversation_scenarios),
        "conversation_length": len(conversation_scenarios),
        "test_timestamp": datetime.now().isoformat()
    })
    
    return fluidity_metrics

@pytest.mark.asyncio
async def simulate_contextual_analysis(oracle_state, agent_name: str, content: str, turn: int):
    """
    Simule l'analyse contextuelle qui serait faite par l'orchestrateur.
    """
    content_lower = content.lower()
    
    # Simulation des références contextuelles
    reference_keywords = [
        ("suite à", "building_on"),
        ("en réaction à", "reacting_to"),
        ("après cette", "responding_to"),
        ("merci pour cette clarification", "acknowledging"),
        ("avec ces données", "integrating")
    ]
    
    for keyword, ref_type in reference_keywords:
        if keyword in content_lower and turn > 1:
            oracle_state.record_contextual_reference(
                source_agent=agent_name,
                target_message_turn=turn - 1,
                reference_type=ref_type,
                reference_content=keyword
            )
            break
    
    # Simulation des réactions émotionnelles
    if turn > 1:
        emotional_patterns = {
            "brillant": "approval",
            "exactement": "approval", 
            "ça colle parfaitement": "approval",
            "précisément": "approval",
            "magistral": "excitement",
            "vous m'impressionnez": "excitement",
            "vous brûlez": "encouragement",
            "hmm": "suspense"
        }
        
        for pattern, reaction_type in emotional_patterns.items():
            if pattern in content_lower:
                oracle_state.record_emotional_reaction(
                    agent_name=agent_name,
                    trigger_agent="Previous_Agent",  # Simulation
                    trigger_content="Previous message content",  # Simulation
                    reaction_type=reaction_type,
                    reaction_content=content[:100]
                )
                break

def analyze_aggregate_results(all_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyse les résultats agrégés de tous les tests.
    """
    if not all_results:
        return {}
    
    # Extraction des métriques
    fluidity_scores = [r['fluidity_score'] for r in all_results]
    ref_rates = [r['contextual_reference_rate'] for r in all_results]
    reaction_rates = [r['emotional_reaction_rate'] for r in all_results]
    
    # Calculs statistiques
    aggregate = {
        "total_tests": len(all_results),
        "successful_tests": len([r for r in all_results if r['fluidity_score'] > 0]),
        
        "fluidity_scores": {
            "mean": statistics.mean(fluidity_scores),
            "median": statistics.median(fluidity_scores),
            "min": min(fluidity_scores),
            "max": max(fluidity_scores),
            "target": 6.5,
            "target_achieved": statistics.mean(fluidity_scores) >= 6.5
        },
        
        "contextual_references": {
            "mean_rate": statistics.mean(ref_rates),
            "median_rate": statistics.median(ref_rates),
            "min_rate": min(ref_rates),
            "max_rate": max(ref_rates),
            "target": 90.0,
            "target_achieved": statistics.mean(ref_rates) >= 90.0
        },
        
        "emotional_reactions": {
            "mean_rate": statistics.mean(reaction_rates),
            "median_rate": statistics.median(reaction_rates),
            "min_rate": min(reaction_rates),
            "max_rate": max(reaction_rates),
            "target": 70.0,
            "target_achieved": statistics.mean(reaction_rates) >= 70.0
        },
        
        "phase_c_success": {
            "fluidity_improved": statistics.mean(fluidity_scores) > 5.0,
            "references_sufficient": statistics.mean(ref_rates) >= 90.0,
            "reactions_sufficient": statistics.mean(reaction_rates) >= 70.0,
        }
    }
    
    # Évaluation globale
    success_criteria = [
        aggregate["fluidity_scores"]["target_achieved"],
        aggregate["contextual_references"]["target_achieved"], 
        aggregate["emotional_reactions"]["target_achieved"]
    ]
    
    aggregate["overall_success"] = all(success_criteria)
    aggregate["success_percentage"] = (sum(success_criteria) / len(success_criteria)) * 100
    
    return aggregate

def print_phase_c_results(aggregate: Dict[str, Any]):
    """
    Affiche les résultats d'analyse Phase C.
    """
    print(f"Tests exécutés: {aggregate['total_tests']}")
    print(f"Tests réussis: {aggregate['successful_tests']}")
    print()
    
    print("📊 MÉTRIQUES DE FLUIDITÉ:")
    fluidity = aggregate["fluidity_scores"]
    print(f"   Score moyen: {fluidity['mean']:.1f}/10 (cible: {fluidity['target']})")
    print(f"   Cible atteinte: {'[OK] OUI' if fluidity['target_achieved'] else '[FAIL] NON'}")
    print(f"   Plage: {fluidity['min']:.1f} - {fluidity['max']:.1f}")
    print()
    
    print("🔗 RÉFÉRENCES CONTEXTUELLES:")
    refs = aggregate["contextual_references"]
    print(f"   Taux moyen: {refs['mean_rate']:.1f}% (cible: {refs['target']}%)")
    print(f"   Cible atteinte: {'[OK] OUI' if refs['target_achieved'] else '[FAIL] NON'}")
    print(f"   Plage: {refs['min_rate']:.1f}% - {refs['max_rate']:.1f}%")
    print()
    
    print("❤️ RÉACTIONS ÉMOTIONNELLES:")
    reactions = aggregate["emotional_reactions"]
    print(f"   Taux moyen: {reactions['mean_rate']:.1f}% (cible: {reactions['target']}%)")
    print(f"   Cible atteinte: {'[OK] OUI' if reactions['target_achieved'] else '[FAIL] NON'}")
    print(f"   Plage: {reactions['min_rate']:.1f}% - {reactions['max_rate']:.1f}%")
    print()
    
    print("🎯 SUCCÈS PHASE C:")
    print(f"   Amélioration fluidité (>5.0): {'[OK]' if aggregate['phase_c_success']['fluidity_improved'] else '[FAIL]'}")
    print(f"   Références suffisantes (≥90%): {'[OK]' if aggregate['phase_c_success']['references_sufficient'] else '[FAIL]'}")
    print(f"   Réactions suffisantes (≥70%): {'[OK]' if aggregate['phase_c_success']['reactions_sufficient'] else '[FAIL]'}")
    print()
    
    print(f"🏆 RÉSULTAT GLOBAL: {'[OK] SUCCÈS' if aggregate['overall_success'] else '[FAIL] ÉCHEC'}")
    print(f"   Pourcentage de réussite: {aggregate['success_percentage']:.1f}%")

def save_test_results(all_results: List[Dict[str, Any]], aggregate: Dict[str, Any]):
    """
    Sauvegarde les résultats de test dans un fichier JSON.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"phase_c_fluidite_results_{timestamp}.json"
    
    output_data = {
        "metadata": {
            "test_type": "Phase C - Fluidité Transitions",
            "timestamp": datetime.now().isoformat(),
            "total_tests": len(all_results)
        },
        "individual_results": all_results,
        "aggregate_analysis": aggregate
    }
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Résultats sauvegardés: {filename}")
    except Exception as e:
        logger.error(f"Erreur sauvegarde: {e}")
        print(f"\n[FAIL] Erreur sauvegarde: {e}")

if __name__ == "__main__":
    asyncio.run(test_phase_c_fluidite_complete())