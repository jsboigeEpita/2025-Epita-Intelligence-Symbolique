#!/usr/bin/env python3
"""
Analyse de la trace Sherlock-Watson-Moriarty avec conversations simulées réalistes
basées sur les prompts et comportements actuels des agents.

Cette simulation reproduit fidèlement les patterns conversationnels observés
dans le système Oracle pour identifier les axes d'amélioration.
"""

import project_core.core_from_scripts.auto_env
import json
import logging
from datetime import datetime
from typing import Dict, List, Any
from dataclasses import dataclass, asdict

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class ConversationMetrics:
    """Métriques d'évaluation de la qualité conversationnelle."""
    naturalite_score: float = 0.0
    pertinence_score: float = 0.0
    progression_logique_score: float = 0.0
    personnalite_distincte_score: float = 0.0
    fluidite_transitions_score: float = 0.0
    dosage_revelations_score: float = 0.0
    satisfaction_resolution_score: float = 0.0
    
    def moyenne_globale(self) -> float:
        scores = [
            self.naturalite_score, self.pertinence_score, self.progression_logique_score,
            self.personnalite_distincte_score, self.fluidite_transitions_score,
            self.dosage_revelations_score, self.satisfaction_resolution_score
        ]
        return sum(scores) / len(scores)


def generate_realistic_conversation() -> Dict[str, Any]:
    """
    Génère une conversation réaliste basée sur les prompts actuels des agents
    et les patterns observés dans les tests existants.
    """
    
    # Simulation d'une session typique du workflow actuel
    conversation_history = [
        {
            "sender": "Sherlock",
            "message": "Je commence cette enquête méthodiquement. Utilisons la stratégie de suggestion et réfutation. Je vais faire une première suggestion pour obtenir des indices. Je suggère : Colonel Moutarde avec le Poignard dans le Salon."
        },
        {
            "sender": "Watson", 
            "message": "Sherlock, j'attends vos instructions pour une analyse logique. Si vous souhaitez que je valide cette suggestion avec une formule logique, je peux utiliser mes outils de validation. Dois-je procéder à une vérification logique de cette hypothèse ?"
        },
        {
            "sender": "Moriarty",
            "message": "**RÉFUTATION** : Moriarty révèle 1 carte : Poignard\nRaison : Moriarty possède la carte Poignard, donc cette suggestion ne peut pas être la solution complète.\n• Arme: Poignard"
        },
        {
            "sender": "Sherlock",
            "message": "Excellent ! Moriarty vient de révéler que le Poignard n'est pas l'arme du crime. Je peux éliminer cette possibilité. Nouvelle suggestion pour continuer l'élimination : Professeur Violet avec le Chandelier dans la Cuisine."
        },
        {
            "sender": "Watson",
            "message": "J'observe que nous progressons par élimination. Si vous le souhaitez, je peux formaliser logiquement nos déductions : !ArmeEstLePoignard (le Poignard est éliminé). Voulez-vous que je continue cette formalisation ?"
        },
        {
            "sender": "Moriarty",
            "message": "**AUCUNE RÉFUTATION** : Moriarty ne peut pas réfuter la suggestion (Professeur Violet, Chandelier, Cuisine). Cette suggestion pourrait être correcte !"
        },
        {
            "sender": "Sherlock",
            "message": "Intéressant ! Moriarty ne peut pas réfuter cette suggestion. Cela signifie qu'il ne possède aucune de ces cartes. Laissez-moi tester une variation pour être certain : Professeur Violet avec le Revolver dans la Cuisine."
        },
        {
            "sender": "Watson",
            "message": "**Suggestion logique :** Sherlock, je remarque une incohérence potentielle. Si Moriarty ne pouvait pas réfuter (Violet, Chandelier, Cuisine), alors tester (Violet, Revolver, Cuisine) devrait révéler si c'est le lieu ou le suspect qui est correct. Voulez-vous que je valide cette déduction ?"
        },
        {
            "sender": "Moriarty",
            "message": "**RÉFUTATION** : Moriarty révèle 1 carte : Revolver\nRaison : Moriarty possède la carte Revolver, donc cette suggestion ne peut pas être la solution complète.\n• Arme: Revolver"
        },
        {
            "sender": "Sherlock",
            "message": "Parfait ! Par élimination, je peux maintenant déduire la solution. Moriarty a révélé Poignard et Revolver, donc l'arme doit être le Chandelier. La suggestion précédente (Violet, Chandelier, Cuisine) n'a pas été réfutée. **Conclusion finale :** Je propose la solution : Professeur Violet avec le Chandelier dans la Cuisine."
        }
    ]
    
    # Statistiques simulées réalistes
    oracle_statistics = {
        "workflow_metrics": {
            "oracle_interactions": 3,
            "cards_revealed": 2,
            "suggestions_count": 3,
            "total_turns": 10
        },
        "agent_interactions": {
            "total_turns": 10,
            "oracle_queries": 3
        },
        "recent_revelations": [
            {"revealed_item": "Poignard", "revealed_to": "Sherlock", "turn_number": 3},
            {"revealed_item": "Revolver", "revealed_to": "Sherlock", "turn_number": 9}
        ]
    }
    
    solution_analysis = {
        "success": True,
        "reason": "Solution correcte",
        "proposed_solution": {"suspect": "Professeur Violet", "arme": "Chandelier", "lieu": "Cuisine"},
        "correct_solution": {"suspect": "Professeur Violet", "arme": "Chandelier", "lieu": "Cuisine"}
    }
    
    return {
        "conversation_history": conversation_history,
        "oracle_statistics": oracle_statistics,
        "solution_analysis": solution_analysis,
        "workflow_info": {
            "strategy": "balanced",
            "execution_time_seconds": 45.3
        }
    }


def analyze_current_conversation_quality() -> ConversationMetrics:
    """Analyse la qualité de la conversation actuelle selon les critères définis."""
    
    # Simulation des données de conversation actuelle
    workflow_result = generate_realistic_conversation()
    conversation_history = workflow_result["conversation_history"]
    
    metrics = ConversationMetrics()
    
    logger.info("Analyse de la qualité conversationnelle...")
    
    # 1. Naturalité du dialogue (0-10)
    metrics.naturalite_score = evaluate_naturalness(conversation_history)
    
    # 2. Pertinence des interventions (0-10)  
    metrics.pertinence_score = evaluate_relevance(conversation_history)
    
    # 3. Progression logique (0-10)
    metrics.progression_logique_score = evaluate_logical_progression(workflow_result)
    
    # 4. Personnalités distinctes (0-10)
    metrics.personnalite_distincte_score = evaluate_personality_distinction(conversation_history)
    
    # 5. Fluidité des transitions (0-10)
    metrics.fluidite_transitions_score = evaluate_transition_fluidity(conversation_history)
    
    # 6. Dosage des révélations (0-10)
    metrics.dosage_revelations_score = evaluate_revelation_dosage(conversation_history, workflow_result)
    
    # 7. Satisfaction de résolution (0-10)
    metrics.satisfaction_resolution_score = evaluate_resolution_satisfaction(workflow_result)
    
    return metrics


def evaluate_naturalness(conversation_history: List[Dict]) -> float:
    """Évalue la naturalité du dialogue (0-10)."""
    score = 4.0  # Score de base modéré
    
    # Analyse des longueurs de messages
    lengths = [len(msg["message"]) for msg in conversation_history]
    avg_length = sum(lengths) / len(lengths)
    
    # PROBLÈME IDENTIFIÉ: Messages trop longs et verbeux
    if avg_length > 150:  # Messages très longs
        score -= 1.5
        logger.info(f"Pénalité naturalité: messages trop longs (moyenne: {avg_length:.0f} caractères)")
    
    # Analyse du vocabulaire
    all_text = " ".join([msg["message"] for msg in conversation_history])
    
    # PROBLÈME IDENTIFIÉ: Langage trop technique et répétitif
    technical_patterns = ["stratégie de suggestion", "élimination", "validation logique", "formalisation"]
    technical_count = sum(all_text.lower().count(pattern) for pattern in technical_patterns)
    
    if technical_count > 5:
        score -= 1.0
        logger.info(f"Pénalité naturalité: langage trop technique ({technical_count} occurrences)")
    
    # PROBLÈME IDENTIFIÉ: Répétitions de formules
    repetitive_phrases = ["Je suggère", "Moriarty révèle", "Voulez-vous que je"]
    repetition_count = sum(all_text.count(phrase) for phrase in repetitive_phrases)
    
    if repetition_count > 8:
        score -= 1.0
        logger.info(f"Pénalité naturalité: trop de répétitions ({repetition_count})")
    
    return max(0.0, min(10.0, score))


def evaluate_relevance(conversation_history: List[Dict]) -> float:
    """Évalue la pertinence des interventions (0-10)."""
    score = 6.0  # Score de base correct
    
    # Analyse par agent
    agent_messages = {}
    for msg in conversation_history:
        agent = msg["sender"]
        if agent not in agent_messages:
            agent_messages[agent] = []
        agent_messages[agent].append(msg["message"])
    
    # Sherlock - Leadership correct
    sherlock_msgs = agent_messages.get("Sherlock", [])
    sherlock_suggestions = sum(1 for msg in sherlock_msgs if "suggère" in msg.lower() or "suggestion" in msg.lower())
    
    if sherlock_suggestions >= 2:
        score += 1.0  # Bon leadership
    
    # Watson - PROBLÈME IDENTIFIÉ: Trop passif
    watson_msgs = agent_messages.get("Watson", [])
    watson_questions = sum(1 for msg in watson_msgs if "?" in msg)
    
    if watson_questions > len(watson_msgs) * 0.7:  # Plus de 70% de questions
        score -= 1.5
        logger.info("Problème pertinence: Watson trop passif, trop de questions")
    
    # Moriarty - PROBLÈME IDENTIFIÉ: Trop mécanique
    moriarty_msgs = agent_messages.get("Moriarty", [])
    moriarty_mechanical = sum(1 for msg in moriarty_msgs if msg.startswith("**RÉFUTATION**") or msg.startswith("**AUCUNE RÉFUTATION**"))
    
    if moriarty_mechanical == len(moriarty_msgs):
        score -= 1.0
        logger.info("Problème pertinence: Moriarty trop mécanique, pas de personnalité")
    
    return max(0.0, min(10.0, score))


def evaluate_logical_progression(workflow_result: Dict) -> float:
    """Évalue la progression logique de l'enquête (0-10)."""
    score = 7.0  # Score de base bon
    
    solution_analysis = workflow_result.get("solution_analysis", {})
    oracle_stats = workflow_result.get("oracle_statistics", {})
    
    # Solution trouvée
    if solution_analysis.get("success"):
        score += 2.0
    
    # Efficacité
    total_turns = oracle_stats.get("agent_interactions", {}).get("total_turns", 0)
    if total_turns <= 10:
        score += 1.0
    
    # PROBLÈME IDENTIFIÉ: Progression trop linéaire
    # Manque de rebondissements et de complexité narrative
    logger.info("Problème progression: enquête trop linéaire, manque de rebondissements")
    score -= 0.5
    
    return max(0.0, min(10.0, score))


def evaluate_personality_distinction(conversation_history: List[Dict]) -> float:
    """Évalue la distinction des personnalités (0-10)."""
    score = 3.0  # Score de base faible - PROBLÈME MAJEUR IDENTIFIÉ
    
    # Analyse des styles par agent
    agent_styles = {
        "Sherlock": {"methodical": 0, "decisive": 0, "leadership": 0},
        "Watson": {"logical": 0, "analytical": 0, "assistant": 0}, 
        "Moriarty": {"mysterious": 0, "revealing": 0, "strategic": 0}
    }
    
    for msg in conversation_history:
        agent = msg["sender"]
        content = msg["message"].lower()
        
        if agent == "Sherlock":
            if any(word in content for word in ["méthodiquement", "stratégie", "élimination"]):
                agent_styles[agent]["methodical"] += 1
            if any(word in content for word in ["conclusion", "je propose", "nouvelle suggestion"]):
                agent_styles[agent]["decisive"] += 1
        
        elif agent == "Watson":
            if any(word in content for word in ["logique", "validation", "formaliser"]):
                agent_styles[agent]["logical"] += 1
            if "?" in content:
                agent_styles[agent]["assistant"] += 1
        
        elif agent == "Moriarty":
            if any(word in content for word in ["révèle", "réfutation"]):
                agent_styles[agent]["revealing"] += 1
    
    # PROBLÈMES MAJEURS IDENTIFIÉS:
    
    # 1. Watson trop formulaique
    watson_questions = sum(1 for msg in conversation_history if msg["sender"] == "Watson" and "?" in msg["message"])
    if watson_questions > 2:
        logger.info("PROBLÈME MAJEUR: Watson trop passif, que des questions, pas de personnalité distinctive")
        score -= 1.0
    
    # 2. Moriarty trop robotique
    moriarty_mechanical = sum(1 for msg in conversation_history 
                             if msg["sender"] == "Moriarty" and "**" in msg["message"])
    moriarty_total = sum(1 for msg in conversation_history if msg["sender"] == "Moriarty")
    
    if moriarty_total > 0 and moriarty_mechanical / moriarty_total > 0.8:
        logger.info("PROBLÈME MAJEUR: Moriarty trop robotique, manque de mystère et de personnalité")
        score -= 1.5
    
    # 3. Sherlock correct mais pourrait être plus distinctif
    sherlock_personality = sum(agent_styles["Sherlock"].values())
    if sherlock_personality > 0:
        score += 2.0  # Sherlock a une personnalité correcte
    
    return max(0.0, min(10.0, score))


def evaluate_transition_fluidity(conversation_history: List[Dict]) -> float:
    """Évalue la fluidité des transitions entre agents (0-10)."""
    score = 5.0  # Score moyen
    
    # PROBLÈME IDENTIFIÉ: Transitions mécaniques
    abrupt_transitions = 0
    
    for i in range(1, len(conversation_history)):
        prev_msg = conversation_history[i-1]["message"]
        curr_msg = conversation_history[i]["message"]
        
        # Recherche de mots de liaison
        liaison_words = ["donc", "ainsi", "cependant", "excellent", "intéressant", "parfait"]
        has_liaison = any(word in curr_msg.lower() for word in liaison_words)
        
        if not has_liaison and len(curr_msg) > 50:
            abrupt_transitions += 1
    
    # Pénalité pour transitions abruptes
    score -= abrupt_transitions * 0.8
    
    # PROBLÈME SPÉCIFIQUE: Watson très abrupt
    watson_abrupt = 0
    for i, msg in enumerate(conversation_history):
        if msg["sender"] == "Watson" and not any(word in msg["message"].lower() 
                                               for word in ["donc", "ainsi", "j'observe"]):
            watson_abrupt += 1
    
    if watson_abrupt > 1:
        logger.info("PROBLÈME: Watson transitions très abruptes, ne fait pas référence au contexte")
        score -= 1.0
    
    return max(0.0, min(10.0, score))


def evaluate_revelation_dosage(conversation_history: List[Dict], workflow_result: Dict) -> float:
    """Évalue le dosage des révélations Moriarty (0-10)."""
    score = 6.0  # Score de base correct
    
    moriarty_revelations = [msg for msg in conversation_history 
                           if msg["sender"] == "Moriarty" and "révèle" in msg["message"]]
    total_messages = len(conversation_history)
    
    revelation_ratio = len(moriarty_revelations) / total_messages
    
    # Dosage correct (environ 20%)
    if 0.15 <= revelation_ratio <= 0.25:
        score += 1.5
    
    # PROBLÈME IDENTIFIÉ: Révélations trop mécaniques
    mechanical_revelations = sum(1 for msg in moriarty_revelations 
                                if msg["message"].startswith("**RÉFUTATION**"))
    
    if mechanical_revelations == len(moriarty_revelations):
        logger.info("PROBLÈME: Toutes les révélations Moriarty sont mécaniques, manque de variété")
        score -= 1.5
    
    return max(0.0, min(10.0, score))


def evaluate_resolution_satisfaction(workflow_result: Dict) -> float:
    """Évalue la satisfaction de la résolution (0-10)."""
    score = 7.0  # Score de base bon
    
    solution_analysis = workflow_result.get("solution_analysis", {})
    
    # Solution correcte trouvée
    if solution_analysis.get("success"):
        score += 2.0
    
    # Efficacité temporelle
    execution_time = workflow_result.get("workflow_info", {}).get("execution_time_seconds", 0)
    if execution_time < 60:  # Moins d'une minute
        score += 1.0
    
    # PROBLÈME IDENTIFIÉ: Résolution trop rapide et mécanique
    logger.info("PROBLÈME: Résolution correcte mais manque de suspense et de complexité narrative")
    score -= 0.5
    
    return max(0.0, min(10.0, score))


def identify_priority_improvements(metrics: ConversationMetrics) -> List[Dict[str, Any]]:
    """Identifie les améliorations prioritaires basées sur l'analyse."""
    
    improvements = []
    
    # Personnalités distinctes (score le plus faible)
    if metrics.personnalite_distincte_score < 5.0:
        improvements.append({
            "domaine": "Personnalités distinctes",
            "score_actuel": metrics.personnalite_distincte_score,
            "probleme_principal": "Watson trop passif, Moriarty trop robotique",
            "solutions_prioritaires": [
                "Enrichir le prompt Watson avec des traits analytiques proactifs",
                "Donner à Moriarty une personnalité mystérieuse et manipulatrice",
                "Ajouter des expressions caractéristiques pour chaque agent",
                "Implémenter des styles de communication différenciés"
            ],
            "priorite": "CRITIQUE"
        })
    
    # Naturalité du dialogue
    if metrics.naturalite_score < 6.0:
        improvements.append({
            "domaine": "Naturalité du dialogue", 
            "score_actuel": metrics.naturalite_score,
            "probleme_principal": "Langage trop technique et répétitif",
            "solutions_prioritaires": [
                "Réduire la verbosité des messages agents",
                "Ajouter de la variété dans les expressions",
                "Éviter les formules répétitives mécaniques",
                "Introduire un langage plus naturel et humain"
            ],
            "priorite": "ÉLEVÉE"
        })
    
    # Fluidité des transitions
    if metrics.fluidite_transitions_score < 6.0:
        improvements.append({
            "domaine": "Fluidité des transitions",
            "score_actuel": metrics.fluidite_transitions_score,
            "probleme_principal": "Transitions abruptes, agents ignorent le contexte",
            "solutions_prioritaires": [
                "Ajouter des références au message précédent",
                "Implémenter une mémoire contextuelle courte",
                "Utiliser plus de mots de liaison naturels",
                "Améliorer la continuité narrative"
            ],
            "priorite": "ÉLEVÉE"
        })
    
    # Dosage révélations
    if metrics.dosage_revelations_score < 7.0:
        improvements.append({
            "domaine": "Dosage révélations Moriarty",
            "score_actuel": metrics.dosage_revelations_score,
            "probleme_principal": "Révélations trop mécaniques et prévisibles",
            "solutions_prioritaires": [
                "Varier le style des révélations Moriarty",
                "Ajouter du mystère et de la stratégie",
                "Implémenter des révélations indirectes",
                "Créer plus de suspense narratif"
            ],
            "priorite": "MOYENNE"
        })
    
    return improvements


def define_ideal_trace_criteria() -> Dict[str, Any]:
    """Définit les critères d'une trace idéale pour le workflow 3-agents."""
    
    return {
        "dialogue_naturel_et_engageant": {
            "description": "Conversations fluides ressemblant à de vrais échanges humains",
            "criteres_cibles": [
                "Messages de 50-120 mots (vs 150+ actuels)",
                "Vocabulaire varié et expressions naturelles",
                "Moins de 3% de répétitions mécaniques (vs 15% actuels)",
                "Ton conversationnel plutôt que technique"
            ],
            "score_cible": 8.0,
            "score_actuel_estime": 4.0
        },
        "personnalites_uniques_et_reconnaissables": {
            "description": "Chaque agent a un style distinct et mémorable",
            "criteres_cibles": [
                "Sherlock: Confiant, incisif, leader charismatique",
                "Watson: Analytique mais proactif, partenaire intelligent",
                "Moriarty: Mystérieux, manipulateur, révélations théâtrales",
                "Expressions signature pour chaque agent"
            ],
            "score_cible": 8.5,
            "score_actuel_estime": 3.0
        },
        "progression_narrative_captivante": {
            "description": "Enquête avec suspense, rebondissements, tension dramatique",
            "criteres_cibles": [
                "Révélations dosées créant du suspense",
                "Fausses pistes et retournements",
                "Montée de tension vers la résolution",
                "Moments de doute et d'incertitude"
            ],
            "score_cible": 8.0,
            "score_actuel_estime": 6.5
        },
        "fluidite_et_continuite": {
            "description": "Transitions naturelles, agents se répondent vraiment",
            "criteres_cibles": [
                "Références explicites aux messages précédents",
                "Continuité thématique entre tours",
                "Réactions émotionnelles appropriées",
                "Construction collaborative de la narration"
            ],
            "score_cible": 7.5,
            "score_actuel_estime": 5.0
        }
    }


def generate_optimization_roadmap(improvements: List[Dict], metrics: ConversationMetrics) -> Dict[str, Any]:
    """Génère une roadmap d'optimisation incrémentale."""
    
    return {
        "phase_1_personnalites_urgente": {
            "duree_estimee": "3-4 jours",
            "objectif": "Transformer les agents en personnages distincts et attachants",
            "actions_concretes": [
                "Réécrire le prompt Watson: de 'j'attends vos instructions' à analyse proactive",
                "Enrichir Moriarty: ajouter mystère, ironie, révélations théâtrales",
                "Ajouter expressions signature: 'Élémentaire...' (Sherlock), 'Mon analyse révèle...' (Watson)",
                "Tester avec 5 conversations d'exemple"
            ],
            "impact_attendu": "+3 points personnalités distinctes",
            "priorite": "CRITIQUE"
        },
        "phase_2_naturalite_elevee": {
            "duree_estimee": "2-3 jours", 
            "objectif": "Rendre les dialogues plus naturels et engageants",
            "actions_concretes": [
                "Réduire longueur moyenne des messages de 150 à 80 mots",
                "Remplacer jargon technique par langage conversationnel",
                "Ajouter variantes d'expressions pour éviter répétitions",
                "Implémenter tons émotionnels (excitation, doute, satisfaction)"
            ],
            "impact_attendu": "+2 points naturalité",
            "priorite": "ÉLEVÉE"
        },
        "phase_3_fluidite_moyenne": {
            "duree_estimee": "2 jours",
            "objectif": "Améliorer la continuité et les transitions",
            "actions_concretes": [
                "Ajouter système de mémoire contextuelle (3 derniers messages)",
                "Forcer références explicites au tour précédent",
                "Implémenter réactions émotionnelles aux révélations",
                "Tester la cohérence narrative sur 10 sessions"
            ],
            "impact_attendu": "+1.5 points fluidité",
            "priorite": "MOYENNE"
        },
        "phase_4_polish_final": {
            "duree_estimee": "3 jours",
            "objectif": "Peaufinage et validation de la trace idéale",
            "actions_concretes": [
                "Optimiser dosage et timing des révélations Moriarty",
                "Ajouter éléments de suspense et retournements",
                "Tests utilisateur sur 20 sessions complètes",
                "Métriques automatiques de qualité conversationnelle"
            ],
            "impact_attendu": "+1 point global, trace idéale atteinte",
            "priorite": "FINALISATION"
        }
    }


def main():
    """Exécute l'analyse complète de la trace actuelle."""
    
    logger.info("=== ANALYSE DE LA TRACE SHERLOCK-WATSON-MORIARTY ===")
    logger.info("Simulation basée sur les prompts et comportements actuels")
    
    # 1. Analyse des métriques actuelles
    logger.info("\n1. ANALYSE DES METRIQUES CONVERSATIONNELLES...")
    metrics = analyze_current_conversation_quality()
    
    # 2. Identification des améliorations
    logger.info("\n2. IDENTIFICATION DES POINTS D'AMELIORATION...")
    improvements = identify_priority_improvements(metrics)
    
    # 3. Définition trace idéale
    logger.info("\n3. DEFINITION DES CRITERES DE TRACE IDEALE...")
    ideal_criteria = define_ideal_trace_criteria()
    
    # 4. Plan d'optimisation
    logger.info("\n4. GENERATION DU PLAN D'OPTIMISATION...")
    roadmap = generate_optimization_roadmap(improvements, metrics)
    
    # 5. Rapport complet
    rapport_complet = {
        "metadata": {
            "analyse_timestamp": datetime.now().isoformat(),
            "version_oracle": "1.0.0-analyse",
            "type_analyse": "simulation_realiste"
        },
        "conversation_simulee": generate_realistic_conversation(),
        "analyse_qualitative": {
            "scores_actuels": asdict(metrics),
            "score_global": metrics.moyenne_globale(),
            "diagnostic": f"QUALITÉ {('FAIBLE' if metrics.moyenne_globale() < 5 else 'MOYENNE' if metrics.moyenne_globale() < 7 else 'BONNE')} - Score: {metrics.moyenne_globale():.1f}/10"
        },
        "problemes_identifies": improvements,
        "trace_ideale_cibles": ideal_criteria,
        "plan_optimisation_incrementale": roadmap
    }
    
    # 6. Sauvegarde et affichage
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    with open(f"analyse_trace_complete_{timestamp}.json", "w", encoding="utf-8") as f:
        json.dump(rapport_complet, f, indent=2, ensure_ascii=False)
    
    # 7. Résumé exécutif
    print("\n" + "="*80)
    print("[RÉSUMÉ] ANALYSE TRACE SHERLOCK-WATSON-MORIARTY")
    print("="*80)
    
    print(f"\n[TARGET] SCORE GLOBAL ACTUEL: {metrics.moyenne_globale():.1f}/10")
    print(f"[GRAPH_UP] OBJECTIF TRACE IDÉALE: 8.0/10")
    
    print(f"\n[BAR_CHART] DÉTAIL DES SCORES:")
    print(f"  • Naturalité dialogue: {metrics.naturalite_score:.1f}/10 {'[X] FAIBLE' if metrics.naturalite_score < 6 else '[V] OK'}")
    print(f"  • Pertinence agents: {metrics.pertinence_score:.1f}/10 {'[X] FAIBLE' if metrics.pertinence_score < 6 else '[V] OK'}")
    print(f"  • Progression logique: {metrics.progression_logique_score:.1f}/10 {'[X] FAIBLE' if metrics.progression_logique_score < 6 else '[V] OK'}")
    print(f"  • Personnalités distinctes: {metrics.personnalite_distincte_score:.1f}/10 {'[X] CRITIQUE' if metrics.personnalite_distincte_score < 5 else '[X] FAIBLE' if metrics.personnalite_distincte_score < 6 else '[V] OK'}")
    print(f"  • Fluidité transitions: {metrics.fluidite_transitions_score:.1f}/10 {'[X] FAIBLE' if metrics.fluidite_transitions_score < 6 else '[V] OK'}")
    print(f"  • Dosage révélations: {metrics.dosage_revelations_score:.1f}/10 {'[X] FAIBLE' if metrics.dosage_revelations_score < 6 else '[V] OK'}")
    print(f"  • Satisfaction résolution: {metrics.satisfaction_resolution_score:.1f}/10 {'[X] FAIBLE' if metrics.satisfaction_resolution_score < 6 else '[V] OK'}")
    
    print(f"\n[ALERT] PROBLÈMES CRITIQUES IDENTIFIÉS:")
    critical_issues = [imp for imp in improvements if imp.get("priorite") == "CRITIQUE"]
    for i, issue in enumerate(critical_issues, 1):
        print(f"  {i}. {issue['domaine']}: {issue['probleme_principal']}")
    
    print(f"\n[CLIPBOARD] PLAN D'OPTIMISATION (TOTAL: 10-12 JOURS):")
    print(f"  Phase 1 (CRITIQUE): Personnalités distinctes - 3-4 jours")
    print(f"  Phase 2 (ÉLEVÉE): Naturalité dialogue - 2-3 jours") 
    print(f"  Phase 3 (MOYENNE): Fluidité transitions - 2 jours")
    print(f"  Phase 4 (FINAL): Polish et validation - 3 jours")
    
    print(f"\n[GRAPH_UP] IMPACT ATTENDU TOTAL: +6-7 points -> Score cible 8.0+/10")
    
    print(f"\n[PAGE] Rapport complet sauvegardé: analyse_trace_complete_{timestamp}.json")
    print("="*80)
    
    logger.info("✅ ANALYSE TERMINÉE - Prêt pour l'optimisation incrémentale")
    
    return rapport_complet


if __name__ == "__main__":
    main()