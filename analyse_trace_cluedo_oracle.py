#!/usr/bin/env python3
"""
ANALYSE DE LA TRACE ACTUELLE SHERLOCK-WATSON-MORIARTY

Script d'analyse pour évaluer la qualité des conversations entre les 3 agents
et identifier les axes d'amélioration vers une "trace idéale".

Objectifs:
1. Exécuter une session complète avec workflow 3-agents
2. Capturer intégralement la trace conversationnelle
3. Analyser la qualité sur plusieurs dimensions
4. Définir les critères de "trace idéale"
5. Proposer un plan d'optimisation incrémentale
"""

import asyncio
import json
import logging
import sys
import traceback
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

# Imports de l'infrastructure Oracle
from argumentation_analysis.orchestration.cluedo_extended_orchestrator import (
    CluedoExtendedOrchestrator, run_cluedo_oracle_game
)
from argumentation_analysis.core.cluedo_oracle_state import CluedoOracleState
from semantic_kernel import Kernel

# Configuration du logging pour une trace détaillée
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trace_analysis.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

# Forcer l'encodage UTF-8 pour éviter les problèmes avec les emojis
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'
logger = logging.getLogger(__name__)


@dataclass
class ConversationalMetrics:
    """Métriques d'évaluation de la qualité conversationnelle."""
    naturalite_score: float = 0.0
    pertinence_score: float = 0.0
    progression_logique_score: float = 0.0
    personnalite_distincte_score: float = 0.0
    fluidite_transitions_score: float = 0.0
    dosage_revelations_score: float = 0.0
    satisfaction_resolution_score: float = 0.0
    
    def moyenne_globale(self) -> float:
        """Calcule la moyenne globale des scores."""
        scores = [
            self.naturalite_score, self.pertinence_score, self.progression_logique_score,
            self.personnalite_distincte_score, self.fluidite_transitions_score,
            self.dosage_revelations_score, self.satisfaction_resolution_score
        ]
        return sum(scores) / len(scores)


@dataclass
class ConversationAnalysis:
    """Analyse complète d'une conversation entre agents."""
    total_messages: int = 0
    messages_par_agent: Dict[str, int] = None
    longueur_moyenne_messages: Dict[str, float] = None
    mots_cles_detectes: Dict[str, List[str]] = None
    transitions_abruptes: List[Dict[str, Any]] = None
    repetitions_detectees: List[Dict[str, Any]] = None
    progression_deductive: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.messages_par_agent is None:
            self.messages_par_agent = {}
        if self.longueur_moyenne_messages is None:
            self.longueur_moyenne_messages = {}
        if self.mots_cles_detectes is None:
            self.mots_cles_detectes = {}
        if self.transitions_abruptes is None:
            self.transitions_abruptes = []
        if self.repetitions_detectees is None:
            self.repetitions_detectees = []
        if self.progression_deductive is None:
            self.progression_deductive = []


class TraceQualityAnalyzer:
    """
    Analyseur de qualité des traces conversationnelles pour le workflow 3-agents.
    """
    
    def __init__(self):
        self.conversation_history: List[Dict[str, Any]] = []
        self.agent_personalities = {
            "Sherlock": ["méthodique", "déductif", "leader", "incisif", "observateur"],
            "Watson": ["logique", "analytique", "assistant", "rigoureux", "technique"],
            "Moriarty": ["mystérieux", "révélateur", "stratégique", "manipulateur", "oracle"]
        }
        self.conversation_patterns = {
            "suggestions": [],
            "validations": [], 
            "revelations": [],
            "transitions": []
        }
    
    def capture_conversation(self, workflow_result: Dict[str, Any]) -> None:
        """Capture et structure l'historique conversationnel."""
        logger.info("🔍 Capture de l'historique conversationnel...")
        
        self.conversation_history = workflow_result.get("conversation_history", [])
        self.oracle_stats = workflow_result.get("oracle_statistics", {})
        self.solution_analysis = workflow_result.get("solution_analysis", {})
        
        logger.info(f"✅ {len(self.conversation_history)} messages capturés")
        
        # Analyse des patterns conversationnels
        self._extract_conversation_patterns()
    
    def _extract_conversation_patterns(self) -> None:
        """Extrait les patterns conversationnels clés."""
        logger.info("🔍 Extraction des patterns conversationnels...")
        
        for i, message in enumerate(self.conversation_history):
            sender = message.get("sender", "Unknown")
            content = message.get("message", "").lower()
            
            # Détection des suggestions
            if "suggér" in content or "suspect" in content and "arme" in content:
                self.conversation_patterns["suggestions"].append({
                    "index": i,
                    "sender": sender,
                    "content_preview": message.get("message", "")[:100]
                })
            
            # Détection des validations logiques
            if "valide" in content or "logique" in content or "formula" in content:
                self.conversation_patterns["validations"].append({
                    "index": i,
                    "sender": sender,
                    "content_preview": message.get("message", "")[:100]
                })
            
            # Détection des révélations Oracle
            if "révèle" in content or "carte" in content or "réfutation" in content:
                self.conversation_patterns["revelations"].append({
                    "index": i,
                    "sender": sender,
                    "content_preview": message.get("message", "")[:100]
                })
            
            # Détection des transitions abruptes
            if i > 0:
                prev_sender = self.conversation_history[i-1].get("sender", "")
                if sender != prev_sender:
                    self.conversation_patterns["transitions"].append({
                        "from": prev_sender,
                        "to": sender,
                        "index": i,
                        "prev_content": self.conversation_history[i-1].get("message", "")[:50],
                        "curr_content": message.get("message", "")[:50]
                    })
    
    def analyze_conversational_quality(self) -> ConversationalMetrics:
        """Analyse la qualité conversationnelle selon les critères définis."""
        logger.info("📊 Analyse de la qualité conversationnelle...")
        
        metrics = ConversationalMetrics()
        
        # 1. Naturalité du dialogue
        metrics.naturalite_score = self._evaluate_naturalness()
        
        # 2. Pertinence des interventions
        metrics.pertinence_score = self._evaluate_relevance()
        
        # 3. Logique de progression
        metrics.progression_logique_score = self._evaluate_logical_progression()
        
        # 4. Personnalités distinctes
        metrics.personnalite_distincte_score = self._evaluate_personality_distinction()
        
        # 5. Fluidité des transitions
        metrics.fluidite_transitions_score = self._evaluate_transition_fluidity()
        
        # 6. Dosage des révélations Moriarty
        metrics.dosage_revelations_score = self._evaluate_revelation_dosage()
        
        # 7. Satisfaction de la résolution
        metrics.satisfaction_resolution_score = self._evaluate_resolution_satisfaction()
        
        logger.info(f"📊 Score global: {metrics.moyenne_globale():.2f}/10")
        return metrics
    
    def _evaluate_naturalness(self) -> float:
        """Évalue la naturalité du dialogue (0-10)."""
        score = 5.0  # Score de base
        
        # Pénalités pour répétitions
        repetitions = self._detect_repetitions()
        score -= min(len(repetitions) * 0.5, 2.0)
        
        # Bonus pour variété du vocabulaire
        unique_words = self._count_unique_words()
        if unique_words > 100:
            score += 1.0
        
        # Bonus pour longueur appropriée des messages
        avg_lengths = self._calculate_average_message_lengths()
        if all(20 <= length <= 200 for length in avg_lengths.values()):
            score += 1.0
        
        return max(0.0, min(10.0, score))
    
    def _evaluate_relevance(self) -> float:
        """Évalue la pertinence des interventions (0-10)."""
        score = 5.0
        
        # Vérifier que Sherlock mène l'enquête
        sherlock_suggestions = len([p for p in self.conversation_patterns["suggestions"] 
                                  if p["sender"] == "Sherlock"])
        total_suggestions = len(self.conversation_patterns["suggestions"])
        
        if total_suggestions > 0:
            sherlock_leadership = sherlock_suggestions / total_suggestions
            score += sherlock_leadership * 3.0  # Max +3 si Sherlock fait toutes les suggestions
        
        # Vérifier que Watson fait de la logique
        watson_logic = len([p for p in self.conversation_patterns["validations"] 
                          if p["sender"] == "Watson"])
        if watson_logic > 0:
            score += 1.0
        
        # Vérifier que Moriarty révèle des cartes
        moriarty_revelations = len([p for p in self.conversation_patterns["revelations"] 
                                  if p["sender"] == "Moriarty"])
        if moriarty_revelations > 0:
            score += 1.0
        
        return max(0.0, min(10.0, score))
    
    def _evaluate_logical_progression(self) -> float:
        """Évalue la logique de progression de l'enquête (0-10)."""
        score = 5.0
        
        # Vérifier que l'enquête progresse vers la solution
        if self.solution_analysis.get("success", False):
            score += 3.0
        elif self.solution_analysis.get("proposed_solution"):
            score += 1.5  # Tentative même si incorrecte
        
        # Vérifier l'utilisation progressive des révélations
        revelations_count = len(self.conversation_patterns["revelations"])
        if 2 <= revelations_count <= 5:  # Nombre optimal de révélations
            score += 1.0
        
        # Vérifier la structure cyclique Sherlock->Watson->Moriarty
        cycle_adherence = self._check_cycle_adherence()
        score += cycle_adherence * 1.0
        
        return max(0.0, min(10.0, score))
    
    def _evaluate_personality_distinction(self) -> float:
        """Évalue la distinction des personnalités (0-10)."""
        score = 5.0
        
        # Analyser les mots-clés par agent
        agent_keywords = self._extract_agent_keywords()
        
        for agent, keywords in agent_keywords.items():
            expected_keywords = self.agent_personalities.get(agent, [])
            matching_keywords = sum(1 for kw in expected_keywords 
                                  if any(kw in keyword.lower() for keyword in keywords))
            if matching_keywords > 0:
                score += 0.5  # Bonus par agent avec personnalité distincte
        
        return max(0.0, min(10.0, score))
    
    def _evaluate_transition_fluidity(self) -> float:
        """Évalue la fluidité des transitions entre agents (0-10)."""
        score = 8.0  # Score de base élevé (transitions généralement fluides)
        
        # Analyser les transitions abruptes
        abrupt_transitions = 0
        for transition in self.conversation_patterns["transitions"]:
            # Transition abrupte si pas de référence au message précédent
            curr_content = transition["curr_content"].lower()
            prev_content = transition["prev_content"].lower()
            
            # Simple heuristique: chercher des mots de liaison
            liaison_words = ["donc", "ainsi", "cependant", "de plus", "en effet", "par ailleurs"]
            has_liaison = any(word in curr_content for word in liaison_words)
            
            if not has_liaison and len(curr_content) > 20:
                abrupt_transitions += 1
        
        # Pénalité pour transitions abruptes
        score -= abrupt_transitions * 0.5
        
        return max(0.0, min(10.0, score))
    
    def _evaluate_revelation_dosage(self) -> float:
        """Évalue le dosage des révélations Moriarty (0-10)."""
        score = 5.0
        
        revelations = self.conversation_patterns["revelations"]
        total_messages = len(self.conversation_history)
        
        if total_messages > 0:
            revelation_density = len(revelations) / total_messages
            
            # Densité optimale: 10-30% des messages
            if 0.1 <= revelation_density <= 0.3:
                score += 3.0
            elif 0.05 <= revelation_density <= 0.5:
                score += 1.5
            else:
                score -= 1.0
        
        # Vérifier que les révélations sont bien réparties
        if len(revelations) >= 2:
            # Calcul de la variance des positions
            positions = [r["index"] for r in revelations]
            if self._is_well_distributed(positions, total_messages):
                score += 2.0
        
        return max(0.0, min(10.0, score))
    
    def _evaluate_resolution_satisfaction(self) -> float:
        """Évalue la satisfaction de la résolution (0-10)."""
        score = 3.0  # Score de base
        
        # Bonus si solution trouvée
        if self.solution_analysis.get("success", False):
            score += 5.0
        elif self.solution_analysis.get("proposed_solution"):
            score += 2.0  # Tentative
        
        # Bonus si résolution logique et cohérente
        oracle_interactions = self.oracle_stats.get("workflow_metrics", {}).get("oracle_interactions", 0)
        if oracle_interactions >= 3:  # Interactions suffisantes
            score += 1.0
        
        # Bonus pour efficacité (résolution en moins de 10 tours)
        total_turns = self.oracle_stats.get("agent_interactions", {}).get("total_turns", 0)
        if total_turns <= 10:
            score += 1.0
        
        return max(0.0, min(10.0, score))
    
    # Méthodes utilitaires d'analyse
    
    def _detect_repetitions(self) -> List[Dict[str, Any]]:
        """Détecte les répétitions dans les messages."""
        repetitions = []
        seen_patterns = {}
        
        for i, message in enumerate(self.conversation_history):
            content = message.get("message", "").lower()
            # Simplifier pour détecter les patterns répétitifs
            words = content.split()[:10]  # Prendre les 10 premiers mots
            pattern = " ".join(words)
            
            if pattern in seen_patterns:
                repetitions.append({
                    "pattern": pattern,
                    "first_occurrence": seen_patterns[pattern],
                    "repeat_at": i,
                    "sender": message.get("sender", "")
                })
            else:
                seen_patterns[pattern] = i
        
        return repetitions
    
    def _count_unique_words(self) -> int:
        """Compte les mots uniques dans toute la conversation."""
        all_words = set()
        for message in self.conversation_history:
            content = message.get("message", "").lower()
            words = content.split()
            all_words.update(words)
        return len(all_words)
    
    def _calculate_average_message_lengths(self) -> Dict[str, float]:
        """Calcule la longueur moyenne des messages par agent."""
        agent_lengths = {}
        agent_counts = {}
        
        for message in self.conversation_history:
            sender = message.get("sender", "Unknown")
            length = len(message.get("message", ""))
            
            if sender not in agent_lengths:
                agent_lengths[sender] = 0
                agent_counts[sender] = 0
            
            agent_lengths[sender] += length
            agent_counts[sender] += 1
        
        return {agent: agent_lengths[agent] / agent_counts[agent] 
                for agent in agent_lengths if agent_counts[agent] > 0}
    
    def _check_cycle_adherence(self) -> float:
        """Vérifie l'adhérence au cycle Sherlock->Watson->Moriarty (0-1)."""
        if len(self.conversation_history) < 3:
            return 0.0
        
        expected_cycle = ["Sherlock", "Watson", "Moriarty"]
        cycle_matches = 0
        total_cycles = 0
        
        for i in range(0, len(self.conversation_history) - 2, 3):
            total_cycles += 1
            if (i + 2 < len(self.conversation_history) and
                self.conversation_history[i].get("sender") == expected_cycle[0] and
                self.conversation_history[i + 1].get("sender") == expected_cycle[1] and
                self.conversation_history[i + 2].get("sender") == expected_cycle[2]):
                cycle_matches += 1
        
        return cycle_matches / total_cycles if total_cycles > 0 else 0.0
    
    def _extract_agent_keywords(self) -> Dict[str, List[str]]:
        """Extrait les mots-clés caractéristiques par agent."""
        agent_keywords = {}
        
        for message in self.conversation_history:
            sender = message.get("sender", "Unknown")
            content = message.get("message", "").lower()
            
            if sender not in agent_keywords:
                agent_keywords[sender] = []
            
            # Extraire mots significatifs (plus de 4 caractères, pas de stop words)
            stop_words = {"avec", "dans", "pour", "vous", "nous", "quel", "cette", "faire"}
            words = [word for word in content.split() 
                    if len(word) > 4 and word not in stop_words]
            agent_keywords[sender].extend(words)
        
        return agent_keywords
    
    def _is_well_distributed(self, positions: List[int], total: int) -> bool:
        """Vérifie si les positions sont bien distribuées."""
        if len(positions) < 2:
            return True
        
        # Calculer les intervalles
        intervals = []
        for i in range(1, len(positions)):
            intervals.append(positions[i] - positions[i-1])
        
        # Vérifier que la variance des intervalles n'est pas trop élevée
        mean_interval = sum(intervals) / len(intervals)
        variance = sum((x - mean_interval) ** 2 for x in intervals) / len(intervals)
        
        # Seuil arbitraire pour une bonne distribution
        return variance < (mean_interval ** 2)
    
    def analyze_detailed_conversation(self) -> ConversationAnalysis:
        """Analyse détaillée de la structure conversationnelle."""
        analysis = ConversationAnalysis()
        
        analysis.total_messages = len(self.conversation_history)
        
        # Messages par agent
        for message in self.conversation_history:
            sender = message.get("sender", "Unknown")
            analysis.messages_par_agent[sender] = analysis.messages_par_agent.get(sender, 0) + 1
        
        # Longueur moyenne des messages
        analysis.longueur_moyenne_messages = self._calculate_average_message_lengths()
        
        # Mots-clés détectés
        analysis.mots_cles_detectes = self._extract_agent_keywords()
        
        # Transitions abruptes
        analysis.transitions_abruptes = [
            {
                "de": t["from"],
                "vers": t["to"],
                "position": t["index"],
                "fluidite": "abrupte" if "donc" not in t["curr_content"] else "fluide"
            }
            for t in self.conversation_patterns["transitions"][:5]  # Limiter à 5
        ]
        
        # Répétitions détectées
        analysis.repetitions_detectees = self._detect_repetitions()[:5]  # Limiter à 5
        
        # Progression déductive
        analysis.progression_deductive = [
            {
                "etape": i + 1,
                "type": "suggestion" if "suggér" in p["content_preview"].lower() else "autre",
                "agent": p["sender"],
                "contenu": p["content_preview"]
            }
            for i, p in enumerate(self.conversation_patterns["suggestions"][:5])
        ]
        
        return analysis
    
    def generate_improvement_recommendations(self, metrics: ConversationalMetrics) -> List[Dict[str, Any]]:
        """Génère des recommandations d'amélioration basées sur l'analyse."""
        recommendations = []
        
        # Naturalité
        if metrics.naturalite_score < 6.0:
            recommendations.append({
                "domaine": "Naturalité du dialogue",
                "score_actuel": metrics.naturalite_score,
                "probleme": "Dialogue peu naturel, répétitions ou longueurs inappropriées",
                "solutions": [
                    "Enrichir le vocabulaire des prompts agents",
                    "Ajouter de la variété dans les expressions",
                    "Calibrer la longueur des réponses"
                ],
                "priorite": "élevée" if metrics.naturalite_score < 4.0 else "moyenne"
            })
        
        # Pertinence
        if metrics.pertinence_score < 6.0:
            recommendations.append({
                "domaine": "Pertinence des interventions",
                "score_actuel": metrics.pertinence_score,
                "probleme": "Agents ne respectent pas leurs rôles définis",
                "solutions": [
                    "Renforcer les prompts de rôle spécifiques",
                    "Ajouter des contraintes comportementales",
                    "Améliorer la sélection cyclique"
                ],
                "priorite": "élevée"
            })
        
        # Progression logique
        if metrics.progression_logique_score < 6.0:
            recommendations.append({
                "domaine": "Progression logique",
                "score_actuel": metrics.progression_logique_score,
                "probleme": "Enquête ne progresse pas logiquement vers la solution",
                "solutions": [
                    "Améliorer la stratégie de révélation Moriarty",
                    "Ajouter des mécanismes de progression forcée",
                    "Optimiser les critères de terminaison"
                ],
                "priorite": "élevée"
            })
        
        # Personnalités distinctes
        if metrics.personnalite_distincte_score < 6.0:
            recommendations.append({
                "domaine": "Personnalités distinctes",
                "score_actuel": metrics.personnalite_distincte_score,
                "probleme": "Agents manquent de personnalité distinctive",
                "solutions": [
                    "Enrichir les prompts avec des traits de personnalité",
                    "Ajouter des expressions caractéristiques",
                    "Développer des styles de communication différenciés"
                ],
                "priorite": "moyenne"
            })
        
        # Fluidité des transitions
        if metrics.fluidite_transitions_score < 6.0:
            recommendations.append({
                "domaine": "Fluidité des transitions",
                "score_actuel": metrics.fluidite_transitions_score,
                "probleme": "Transitions abruptes entre agents",
                "solutions": [
                    "Ajouter des mots de liaison dans les prompts",
                    "Implémenter une mémoire contextuelle",
                    "Améliorer la passation de tour"
                ],
                "priorite": "moyenne"
            })
        
        # Dosage des révélations
        if metrics.dosage_revelations_score < 6.0:
            recommendations.append({
                "domaine": "Dosage des révélations Moriarty",
                "score_actuel": metrics.dosage_revelations_score,
                "probleme": "Révélations mal timées ou mal dosées",
                "solutions": [
                    "Calibrer la stratégie de révélation",
                    "Implémenter des révélations progressives",
                    "Améliorer les critères de pertinence"
                ],
                "priorite": "élevée"
            })
        
        # Satisfaction de résolution
        if metrics.satisfaction_resolution_score < 6.0:
            recommendations.append({
                "domaine": "Satisfaction de la résolution",
                "score_actuel": metrics.satisfaction_resolution_score,
                "probleme": "Résolution insatisfaisante ou incomplète",
                "solutions": [
                    "Améliorer la logique de terminaison",
                    "Ajouter des vérifications de cohérence",
                    "Optimiser l'efficacité du workflow"
                ],
                "priorite": "élevée"
            })
        
        return recommendations


async def execute_workflow_analysis():
    """Exécute une session complète et analyse la qualité conversationnelle."""
    logger.info("[DÉBUT] ANALYSE DE LA TRACE CLUEDO ORACLE")
    logger.info("=" * 60)
    
    try:
        # 1. Configuration du kernel (simulation)
        logger.info("[CONFIG] Configuration du kernel Semantic...")
        kernel = Kernel()
        # NOTE: En production, configurez ici votre service LLM
        
        # 2. Exécution du workflow 3-agents
        logger.info("🎭 Lancement du workflow 3-agents...")
        workflow_result = await run_cluedo_oracle_game(
            kernel=kernel,
            initial_question="L'enquête commence. Sherlock, menez l'investigation !",
            max_turns=12,
            max_cycles=4,
            oracle_strategy="balanced"
        )
        
        logger.info("✅ Workflow terminé avec succès")
        
        # 3. Analyse de la qualité conversationnelle
        logger.info("🔍 Analyse de la qualité conversationnelle...")
        analyzer = TraceQualityAnalyzer()
        analyzer.capture_conversation(workflow_result)
        
        # Métriques de qualité
        metrics = analyzer.analyze_conversational_quality()
        
        # Analyse détaillée
        detailed_analysis = analyzer.analyze_detailed_conversation()
        
        # Recommandations d'amélioration
        recommendations = analyzer.generate_improvement_recommendations(metrics)
        
        # 4. Génération du rapport complet
        report = generate_comprehensive_report(
            workflow_result, metrics, detailed_analysis, recommendations
        )
        
        # 5. Sauvegarde des résultats
        save_analysis_results(report)
        
        # 6. Affichage du résumé
        display_analysis_summary(metrics, recommendations)
        
        logger.info("✅ ANALYSE TERMINÉE AVEC SUCCÈS")
        return report
        
    except Exception as e:
        logger.error(f"❌ Erreur durant l'analyse: {e}")
        traceback.print_exc()
        raise


def generate_comprehensive_report(
    workflow_result: Dict[str, Any],
    metrics: ConversationalMetrics,
    detailed_analysis: ConversationAnalysis,
    recommendations: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Génère un rapport complet d'analyse."""
    
    return {
        "metadata": {
            "analyse_timestamp": datetime.now().isoformat(),
            "version_oracle": "1.0.0",
            "workflow_strategy": workflow_result.get("workflow_info", {}).get("strategy", "unknown")
        },
        "trace_complete": {
            "conversation_history": workflow_result.get("conversation_history", []),
            "solution_analysis": workflow_result.get("solution_analysis", {}),
            "oracle_statistics": workflow_result.get("oracle_statistics", {}),
            "final_state": workflow_result.get("final_state", {})
        },
        "analyse_qualitative": {
            "metriques_conversationnelles": asdict(metrics),
            "analyse_detaillee": asdict(detailed_analysis),
            "score_global": metrics.moyenne_globale(),
            "diagnostic": generate_quality_diagnostic(metrics)
        },
        "recommandations_amelioration": recommendations,
        "criteres_trace_ideale": define_ideal_trace_criteria(),
        "plan_optimisation": generate_optimization_plan(recommendations),
        "benchmark_2vs3_agents": compare_with_2agent_system(workflow_result)
    }


def generate_quality_diagnostic(metrics: ConversationalMetrics) -> Dict[str, str]:
    """Génère un diagnostic de qualité basé sur les métriques."""
    score = metrics.moyenne_globale()
    
    if score >= 8.0:
        level = "EXCELLENT"
        description = "Conversation de très haute qualité, proche de la trace idéale"
    elif score >= 6.5:
        level = "BON"
        description = "Conversation de bonne qualité avec quelques améliorations possibles"
    elif score >= 5.0:
        level = "MOYEN"
        description = "Conversation acceptable mais nécessitant des optimisations"
    elif score >= 3.0:
        level = "FAIBLE"
        description = "Conversation de qualité insuffisante, optimisations importantes nécessaires"
    else:
        level = "TRÈS FAIBLE"
        description = "Conversation de très mauvaise qualité, refonte nécessaire"
    
    return {
        "niveau": level,
        "score": f"{score:.2f}/10",
        "description": description,
        "statut": "ACCEPTABLE" if score >= 5.0 else "À AMÉLIORER"
    }


def define_ideal_trace_criteria() -> Dict[str, Any]:
    """Définit les critères d'une trace idéale."""
    return {
        "dialogue_naturel": {
            "description": "Échanges fluides et humains entre agents",
            "criteres": [
                "Variété du vocabulaire (>150 mots uniques)",
                "Longueur appropriée des messages (50-150 mots)",
                "Absence de répétitions (< 5% des messages)",
                "Expressions naturelles et variées"
            ],
            "score_cible": 8.0
        },
        "personnalites_distinctes": {
            "description": "Chaque agent a une personnalité unique et reconnaissable",
            "criteres": [
                "Sherlock: Leadership, méthode, déduction",
                "Watson: Logique, assistance, rigueur",
                "Moriarty: Mystère, révélation, stratégie"
            ],
            "score_cible": 7.5
        },
        "progression_logique": {
            "description": "Enquête progresse méthodiquement vers la solution",
            "criteres": [
                "Suggestions de Sherlock pertinentes",
                "Validations logiques de Watson",
                "Révélations stratégiques de Moriarty",
                "Convergence vers la solution correcte"
            ],
            "score_cible": 8.5
        },
        "revelations_strategiques": {
            "description": "Informations révélées au bon moment",
            "criteres": [
                "Dosage approprié (20-30% des tours)",
                "Répartition équilibrée dans le temps",
                "Pertinence par rapport aux suggestions",
                "Progression vers la résolution"
            ],
            "score_cible": 8.0
        },
        "resolution_satisfaisante": {
            "description": "Conclusion logique et satisfaisante",
            "criteres": [
                "Solution correcte proposée",
                "Justification logique claire",
                "Efficacité temporelle (<10 tours)",
                "Cohérence narrative"
            ],
            "score_cible": 9.0
        }
    }


def generate_optimization_plan(recommendations: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Génère un plan d'optimisation incrémentale."""
    
    # Tri des recommandations par priorité
    high_priority = [r for r in recommendations if r.get("priorite") == "élevée"]
    medium_priority = [r for r in recommendations if r.get("priorite") == "moyenne"]
    
    return {
        "phase_A_prompts_personnalites": {
            "description": "Optimisation des prompts et personnalités d'agents",
            "actions": [
                "Enrichir le prompt Sherlock avec expressions caractéristiques",
                "Améliorer la différenciation Watson/Sherlock",
                "Développer la personnalité mystérieuse de Moriarty",
                "Ajouter des mots de liaison pour fluidité"
            ],
            "priorite": "ÉLEVÉE",
            "effort_estime": "2-3 jours",
            "impact_attendu": "+1.5 points sur personnalités distinctes"
        },
        "phase_B_logique_revelations": {
            "description": "Amélioration de la logique de révélations Moriarty",
            "actions": [
                "Calibrer la stratégie de révélation 'balanced'",
                "Implémenter révélations progressives",
                "Améliorer timing des révélations",
                "Optimiser critères de pertinence"
            ],
            "priorite": "ÉLEVÉE",
            "effort_estime": "3-4 jours",
            "impact_attendu": "+2.0 points sur dosage révélations"
        },
        "phase_C_transitions_fluidite": {
            "description": "Affinement des transitions et fluidité",
            "actions": [
                "Implémenter mémoire contextuelle entre tours",
                "Ajouter références au message précédent",
                "Améliorer la sélection adaptative",
                "Optimiser la passation de tour"
            ],
            "priorite": "MOYENNE",
            "effort_estime": "2-3 jours",
            "impact_attendu": "+1.0 point sur fluidité transitions"
        },
        "phase_D_validation_metriques": {
            "description": "Validation et métriques qualitatives",
            "actions": [
                "Implémenter métriques automatiques",
                "Tests A/B avec différentes stratégies",
                "Validation utilisateur",
                "Benchmark performance"
            ],
            "priorite": "MOYENNE",
            "effort_estime": "2-3 jours",
            "impact_attendu": "Mesure objective des améliorations"
        }
    }


def compare_with_2agent_system(workflow_result: Dict[str, Any]) -> Dict[str, Any]:
    """Compare avec le système 2-agents théorique."""
    oracle_stats = workflow_result.get("oracle_statistics", {})
    
    return {
        "efficacite_temporelle": {
            "tours_3_agents": oracle_stats.get("agent_interactions", {}).get("total_turns", 0),
            "estimation_2_agents": oracle_stats.get("agent_interactions", {}).get("total_turns", 0) * 1.5,
            "gain_estime": "25-30% reduction in turns"
        },
        "richesse_informationnelle": {
            "cartes_revelees": oracle_stats.get("workflow_metrics", {}).get("cards_revealed", 0),
            "interactions_oracle": oracle_stats.get("workflow_metrics", {}).get("oracle_interactions", 0),
            "avantage_3_agents": "Révélations stratégiques vs aléatoires"
        },
        "qualite_resolution": {
            "succes_actuel": workflow_result.get("solution_analysis", {}).get("success", False),
            "methode": "Déduction assistée par Oracle",
            "vs_2_agents": "Élimination pure par suggestions"
        }
    }


def save_analysis_results(report: Dict[str, Any]) -> None:
    """Sauvegarde les résultats d'analyse."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Sauvegarde du rapport complet
    with open(f"analyse_trace_complete_{timestamp}.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    # Sauvegarde du résumé exécutif
    summary = {
        "timestamp": report["metadata"]["analyse_timestamp"],
        "score_global": report["analyse_qualitative"]["score_global"],
        "diagnostic": report["analyse_qualitative"]["diagnostic"],
        "recommandations_prioritaires": [
            r for r in report["recommandations_amelioration"] 
            if r.get("priorite") == "élevée"
        ][:3],
        "prochaines_etapes": list(report["plan_optimisation"].keys())[:2]
    }
    
    with open(f"resume_executif_{timestamp}.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    logger.info(f"📄 Résultats sauvegardés: analyse_trace_complete_{timestamp}.json")


def display_analysis_summary(metrics: ConversationalMetrics, recommendations: List[Dict[str, Any]]) -> None:
    """Affiche le résumé de l'analyse."""
    print("\n" + "="*80)
    print("🎯 RÉSUMÉ DE L'ANALYSE DE LA TRACE SHERLOCK-WATSON-MORIARTY")
    print("="*80)
    
    print(f"\n📊 SCORE GLOBAL: {metrics.moyenne_globale():.2f}/10")
    print(f"🎭 Naturalité: {metrics.naturalite_score:.1f}/10")
    print(f"🎯 Pertinence: {metrics.pertinence_score:.1f}/10")
    print(f"🧠 Progression logique: {metrics.progression_logique_score:.1f}/10")
    print(f"👤 Personnalités distinctes: {metrics.personnalite_distincte_score:.1f}/10")
    print(f"🔄 Fluidité transitions: {metrics.fluidite_transitions_score:.1f}/10")
    print(f"💎 Dosage révélations: {metrics.dosage_revelations_score:.1f}/10")
    print(f"✅ Satisfaction résolution: {metrics.satisfaction_resolution_score:.1f}/10")
    
    print(f"\n🚨 POINTS D'AMÉLIORATION PRIORITAIRES:")
    high_priority = [r for r in recommendations if r.get("priorite") == "élevée"]
    for i, rec in enumerate(high_priority[:3], 1):
        print(f"{i}. {rec['domaine']} (Score: {rec['score_actuel']:.1f}/10)")
        print(f"   → {rec['probleme']}")
    
    print(f"\n📈 PROCHAINES ÉTAPES:")
    print("1. Phase A: Optimisation prompts et personnalités (2-3 jours)")
    print("2. Phase B: Amélioration logique révélations Moriarty (3-4 jours)")
    print("3. Phase C: Affinement transitions et fluidité (2-3 jours)")
    
    print("\n" + "="*80)


if __name__ == "__main__":
    asyncio.run(execute_workflow_analysis())