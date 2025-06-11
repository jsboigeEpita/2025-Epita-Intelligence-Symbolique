"""
Module définissant le Gestionnaire Stratégique de l'architecture hiérarchique.

Le Gestionnaire Stratégique est l'agent principal du niveau stratégique, responsable
de la coordination globale entre les agents stratégiques, de l'interface avec l'utilisateur
et le niveau tactique, et de l'évaluation des résultats finaux.
"""

from typing import Dict, List, Any, Optional
import logging
from datetime import datetime
import uuid

from argumentation_analysis.orchestration.hierarchical.strategic.state import StrategicState
from argumentation_analysis.paths import DATA_DIR, RESULTS_DIR
from argumentation_analysis.core.communication import (
    MessageMiddleware, StrategicAdapter, MessagePriority,
    ChannelType, Message, MessageType, AgentLevel
)


class StrategicManager:
    """
    Classe représentant le Gestionnaire Stratégique de l'architecture hiérarchique.
    
    Le Gestionnaire Stratégique est responsable de:
    - La coordination globale entre les agents stratégiques
    - L'interface principale avec l'utilisateur et le niveau tactique
    - La prise de décisions finales concernant la stratégie d'analyse
    - L'évaluation des résultats finaux et la formulation de la conclusion globale
    """
    
    def __init__(self, strategic_state: Optional[StrategicState] = None,
                middleware: Optional[MessageMiddleware] = None):
        """
        Initialise un nouveau Gestionnaire Stratégique.
        
        Args:
            strategic_state: L'état stratégique à utiliser. Si None, un nouvel état est créé.
            middleware: Le middleware de communication à utiliser. Si None, un nouveau middleware est créé.
        """
        self.state = strategic_state if strategic_state else StrategicState()
        self.logger = logging.getLogger(__name__)
        
        # Initialiser le middleware de communication
        self.middleware = middleware if middleware else MessageMiddleware()
        
        # Créer l'adaptateur stratégique
        self.adapter = StrategicAdapter(
            agent_id="strategic_manager",
            middleware=self.middleware
        )

    def define_strategic_goal(self, goal: Dict[str, Any]):
        """Définit un objectif stratégique et le publie pour le niveau tactique."""
        self.logger.info(f"Définition du but stratégique: {goal.get('id')}")
        self.state.add_global_objective(goal)
        # Simuler la publication d'une directive pour le coordinateur tactique
        self.adapter.issue_directive(
            directive_type="new_strategic_goal",
            parameters=goal,
            recipient_id="tactical_coordinator"
        )
    
    def initialize_analysis(self, text: str) -> Dict[str, Any]:
        """
        Initialise une nouvelle analyse rhétorique.
        
        Args:
            text: Le texte à analyser
            
        Returns:
            Un dictionnaire contenant les objectifs initiaux et le plan stratégique
        """
        self.logger.info("Initialisation d'une nouvelle analyse rhétorique")
        self.state.set_raw_text(text)
        
        # Définir les objectifs globaux initiaux
        self._define_initial_objectives()
        
        # Créer un plan stratégique initial
        self._create_initial_strategic_plan()
        
        # Allouer les ressources initiales
        self._allocate_initial_resources()
        
        # Journaliser la décision d'initialisation
        self._log_decision("Initialisation de l'analyse", 
                          "Analyse préliminaire du texte et définition des objectifs initiaux")
        
        return {
            "objectives": self.state.global_objectives,
            "strategic_plan": self.state.strategic_plan
        }
    
    def _define_initial_objectives(self) -> None:
        """Définit les objectifs globaux initiaux basés sur le texte à analyser."""
        # Ces objectifs seraient normalement définis en fonction d'une analyse préliminaire du texte
        # Pour l'instant, nous définissons des objectifs génériques
        
        objectives = [
            {
                "id": "obj-1",
                "description": "Identifier les arguments principaux du texte",
                "priority": "high",
                "success_criteria": "Au moins 90% des arguments principaux identifiés"
            },
            {
                "id": "obj-2",
                "description": "Détecter les sophismes et fallacies",
                "priority": "high",
                "success_criteria": "Identification précise des sophismes avec justification"
            },
            {
                "id": "obj-3",
                "description": "Analyser la structure logique des arguments",
                "priority": "medium",
                "success_criteria": "Formalisation correcte des arguments principaux"
            },
            {
                "id": "obj-4",
                "description": "Évaluer la cohérence globale de l'argumentation",
                "priority": "medium",
                "success_criteria": "Évaluation quantitative de la cohérence avec justification"
            }
        ]
        
        for objective in objectives:
            self.state.add_global_objective(objective)
    
    def _create_initial_strategic_plan(self) -> None:
        """Crée un plan stratégique initial pour l'analyse."""
        plan_update = {
            "phases": [
                {
                    "id": "phase-1",
                    "name": "Analyse préliminaire",
                    "description": "Identification des éléments clés du texte",
                    "objectives": ["obj-1"],
                    "estimated_duration": "short"
                },
                {
                    "id": "phase-2",
                    "name": "Analyse approfondie",
                    "description": "Détection des sophismes et analyse logique",
                    "objectives": ["obj-2", "obj-3"],
                    "estimated_duration": "medium"
                },
                {
                    "id": "phase-3",
                    "name": "Synthèse et évaluation",
                    "description": "Évaluation de la cohérence et synthèse finale",
                    "objectives": ["obj-4"],
                    "estimated_duration": "short"
                }
            ],
            "dependencies": {
                "phase-2": ["phase-1"],
                "phase-3": ["phase-2"]
            },
            "priorities": {
                "phase-1": "high",
                "phase-2": "high",
                "phase-3": "medium"
            },
            "success_criteria": {
                "phase-1": "Identification d'au moins 5 arguments principaux",
                "phase-2": "Détection d'au moins 80% des sophismes",
                "phase-3": "Score de cohérence calculé avec justification"
            }
        }
        
        self.state.update_strategic_plan(plan_update)
    
    def _allocate_initial_resources(self) -> None:
        """Alloue les ressources initiales pour l'analyse."""
        allocation_update = {
            "agent_assignments": {
                "informal_analyzer": ["phase-1", "phase-2"],
                "logic_analyzer": ["phase-2", "phase-3"],
                "extract_processor": ["phase-1"],
                "visualizer": ["phase-3"]
            },
            "priority_levels": {
                "informal_analyzer": "high",
                "logic_analyzer": "high",
                "extract_processor": "medium",
                "visualizer": "low"
            },
            "computational_budget": {
                "informal_analyzer": 0.4,
                "logic_analyzer": 0.3,
                "extract_processor": 0.2,
                "visualizer": 0.1
            }
        }
        
        self.state.update_resource_allocation(allocation_update)
    
    def process_tactical_feedback(self, feedback: Dict[str, Any]) -> Dict[str, Any]:
        """
        Traite le feedback du niveau tactique et ajuste la stratégie si nécessaire.
        
        Args:
            feedback: Dictionnaire contenant le feedback du niveau tactique
            
        Returns:
            Un dictionnaire contenant les ajustements stratégiques à appliquer
        """
        self.logger.info("Traitement du feedback du niveau tactique")
        
        # Mettre à jour les métriques globales
        if "progress_metrics" in feedback:
            self.state.update_global_metrics({
                "progress": feedback["progress_metrics"].get("overall_progress", 0.0),
                "quality_indicators": feedback["progress_metrics"].get("quality_indicators", {})
            })
        
        # Identifier les problèmes signalés
        issues = feedback.get("issues", [])
        adjustments = {}
        
        # Recevoir les rapports tactiques via le système de communication
        pending_reports = self.adapter.get_pending_reports(max_count=10)
        
        for report in pending_reports:
            report_content = report.content.get(DATA_DIR, {})
            report_type = report.content.get("report_type")
            
            if report_type == "progress_update":
                # Mettre à jour les métriques avec les informations du rapport
                if "progress" in report_content:
                    self.state.update_global_metrics({
                        "progress": report_content["progress"]
                    })
                
                # Ajouter les problèmes signalés
                if "issues" in report_content:
                    issues.extend(report_content["issues"])
        
        if issues:
            # Analyser les problèmes et déterminer les ajustements nécessaires
            adjustments = self._determine_strategic_adjustments(issues)
            
            # Appliquer les ajustements à l'état stratégique
            self._apply_strategic_adjustments(adjustments)
            
            # Journaliser la décision d'ajustement
            self._log_decision(
                "Ajustement stratégique",
                f"Ajustement de la stratégie en réponse à {len(issues)} problème(s) signalé(s)"
            )
            
            # Envoyer les ajustements aux agents tactiques
            self._send_strategic_adjustments(adjustments)
        
        return {
            "strategic_adjustments": adjustments,
            "updated_metrics": self.state.global_metrics
        }
    
    def _determine_strategic_adjustments(self, issues: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Détermine les ajustements stratégiques nécessaires en fonction des problèmes signalés.
        
        Args:
            issues: Liste des problèmes signalés par le niveau tactique
            
        Returns:
            Un dictionnaire contenant les ajustements à appliquer
        """
        adjustments = {
            "plan_updates": {},
            "resource_reallocation": {},
            "objective_modifications": []
        }
        
        for issue in issues:
            issue_type = issue.get("type")
            severity = issue.get("severity", "medium")
            
            if issue_type == "resource_shortage":
                # Ajuster l'allocation des ressources
                resource = issue.get("resource")
                if resource:
                    adjustments["resource_reallocation"][resource] = {
                        "priority": "high" if severity == "high" else "medium",
                        "budget_increase": 0.2 if severity == "high" else 0.1
                    }
            
            elif issue_type == "objective_unrealistic":
                # Modifier un objectif
                objective_id = issue.get("objective_id")
                if objective_id:
                    adjustments["objective_modifications"].append({
                        "id": objective_id,
                        "action": "modify",
                        "updates": {
                            "priority": "medium" if severity == "high" else "low",
                            "success_criteria": issue.get("suggested_criteria", "")
                        }
                    })
            
            elif issue_type == "phase_delay":
                # Ajuster le plan stratégique
                phase_id = issue.get("phase_id")
                if phase_id:
                    adjustments["plan_updates"][phase_id] = {
                        "estimated_duration": "long" if severity == "high" else "medium",
                        "priority": "high" if severity == "high" else "medium"
                    }
        
        return adjustments
    
    def _apply_strategic_adjustments(self, adjustments: Dict[str, Any]) -> None:
        """
        Applique les ajustements stratégiques à l'état.
        
        Args:
            adjustments: Dictionnaire contenant les ajustements à appliquer
        """
        # Appliquer les mises à jour du plan
        if "plan_updates" in adjustments and adjustments["plan_updates"]:
            plan_updates = {
                "priorities": {},
                "phases": []
            }
            
            for phase_id, updates in adjustments["plan_updates"].items():
                if "priority" in updates:
                    plan_updates["priorities"][phase_id] = updates["priority"]
                
                # Trouver et mettre à jour la phase dans le plan existant
                for i, phase in enumerate(self.state.strategic_plan["phases"]):
                    if phase["id"] == phase_id:
                        updated_phase = phase.copy()
                        updated_phase.update({k: v for k, v in updates.items() 
                                             if k != "priority"})
                        plan_updates["phases"].append(updated_phase)
                        break
            
            self.state.update_strategic_plan(plan_updates)
        
        # Appliquer les réallocations de ressources
        if "resource_reallocation" in adjustments and adjustments["resource_reallocation"]:
            resource_updates = {
                "priority_levels": {},
                "computational_budget": {}
            }
            
            for resource, updates in adjustments["resource_reallocation"].items():
                if "priority" in updates:
                    resource_updates["priority_levels"][resource] = updates["priority"]
                
                if "budget_increase" in updates:
                    # Calculer le nouveau budget en augmentant le budget actuel
                    current_budget = self.state.resource_allocation["computational_budget"].get(resource, 0)
                    resource_updates["computational_budget"][resource] = current_budget + updates["budget_increase"]
            
            self.state.update_resource_allocation(resource_updates)
        
        # Appliquer les modifications d'objectifs
        if "objective_modifications" in adjustments:
            for mod in adjustments["objective_modifications"]:
                obj_id = mod.get("id")
                action = mod.get("action")
                
                if action == "modify" and obj_id:
                    # Trouver et modifier l'objectif
                    for i, obj in enumerate(self.state.global_objectives):
                        if obj["id"] == obj_id:
                            self.state.global_objectives[i].update(mod.get("updates", {}))
                            break
    
    def evaluate_final_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Évalue les résultats finaux de l'analyse et formule une conclusion globale.
        
        Args:
            results: Dictionnaire contenant les résultats finaux de l'analyse
            
        Returns:
            Un dictionnaire contenant la conclusion finale et l'évaluation
        """
        self.logger.info("Évaluation des résultats finaux de l'analyse")
        
        # Recevoir les résultats finaux via le système de communication
        final_results = {}
        
        # Demander les résultats finaux à tous les agents tactiques
        response = self.adapter.request_tactical_status(
            recipient_id="tactical_coordinator",
            timeout=10.0
        )
        
        if response:
            # Fusionner les résultats reçus avec ceux fournis en paramètre
            if RESULTS_DIR in response:
                for key, value in response[RESULTS_DIR].items():
                    if key in results:
                        # Si la clé existe déjà, fusionner les valeurs
                        if isinstance(results[key], list) and isinstance(value, list):
                            results[key].extend(value)
                        elif isinstance(results[key], dict) and isinstance(value, dict):
                            results[key].update(value)
                        else:
                            # Priorité aux nouvelles valeurs
                            results[key] = value
                    else:
                        # Sinon, ajouter la nouvelle clé-valeur
                        results[key] = value
        
        # Analyser les résultats par rapport aux objectifs
        evaluation = self._evaluate_results_against_objectives(results)
        
        # Formuler une conclusion globale
        conclusion = self._formulate_conclusion(results, evaluation)
        
        # Enregistrer la conclusion finale
        self.state.set_final_conclusion(conclusion)
        
        # Journaliser la décision d'évaluation finale
        self._log_decision(
            "Évaluation finale",
            "Formulation de la conclusion finale basée sur l'analyse des résultats"
        )
        
        # Publier la conclusion finale
        self.adapter.publish_strategic_decision(
            decision_type="final_conclusion",
            content={
                "conclusion": conclusion,
                "evaluation": evaluation
            },
            priority=MessagePriority.HIGH
        )
        
        return {
            "conclusion": conclusion,
            "evaluation": evaluation,
            "final_state": self.state.get_snapshot()
        }
    
    def _evaluate_results_against_objectives(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Évalue les résultats par rapport aux objectifs définis.
        
        Args:
            results: Les résultats de l'analyse
            
        Returns:
            Un dictionnaire contenant l'évaluation par objectif
        """
        evaluation = {
            "objectives_evaluation": {},
            "overall_success_rate": 0.0,
            "strengths": [],
            "weaknesses": []
        }
        
        total_score = 0.0
        
        for objective in self.state.global_objectives:
            obj_id = objective["id"]
            obj_results = results.get(obj_id, {})
            
            # Évaluer l'objectif en fonction de ses critères de succès
            success_rate = obj_results.get("success_rate", 0.0)
            total_score += success_rate
            
            evaluation["objectives_evaluation"][obj_id] = {
                "description": objective["description"],
                "success_rate": success_rate,
                "comments": obj_results.get("comments", "")
            }
            
            # Identifier les forces et faiblesses
            if success_rate >= 0.8:
                evaluation["strengths"].append(f"Objectif '{objective['description']}' atteint avec succès")
            elif success_rate <= 0.4:
                evaluation["weaknesses"].append(f"Objectif '{objective['description']}' insuffisamment atteint")
        
        # Calculer le taux de succès global
        if self.state.global_objectives:
            evaluation["overall_success_rate"] = total_score / len(self.state.global_objectives)
        
        return evaluation
    
    def _formulate_conclusion(self, results: Dict[str, Any], evaluation: Dict[str, Any]) -> str:
        """
        Formule une conclusion globale basée sur les résultats et l'évaluation.
        
        Args:
            results: Les résultats de l'analyse
            evaluation: L'évaluation des résultats
            
        Returns:
            La conclusion globale de l'analyse
        """
        # Cette méthode serait normalement plus sophistiquée, utilisant potentiellement un LLM
        # pour générer une conclusion cohérente basée sur les résultats
        
        overall_rate = evaluation["overall_success_rate"]
        strengths = evaluation["strengths"]
        weaknesses = evaluation["weaknesses"]
        
        conclusion_parts = []
        
        # Introduction
        if overall_rate >= 0.8:
            conclusion_parts.append("L'analyse rhétorique a été réalisée avec un haut niveau de succès.")
        elif overall_rate >= 0.6:
            conclusion_parts.append("L'analyse rhétorique a été réalisée avec un niveau de succès satisfaisant.")
        elif overall_rate >= 0.4:
            conclusion_parts.append("L'analyse rhétorique a été réalisée avec un niveau de succès modéré.")
        else:
            conclusion_parts.append("L'analyse rhétorique a rencontré des difficultés significatives.")
        
        # Forces
        if strengths:
            conclusion_parts.append("\n\nPoints forts de l'analyse:")
            for strength in strengths[:3]:  # Limiter à 3 forces principales
                conclusion_parts.append(f"- {strength}")
        
        # Faiblesses
        if weaknesses:
            conclusion_parts.append("\n\nPoints à améliorer:")
            for weakness in weaknesses[:3]:  # Limiter à 3 faiblesses principales
                conclusion_parts.append(f"- {weakness}")
        
        # Synthèse des résultats clés
        conclusion_parts.append("\n\nSynthèse des résultats clés:")
        
        # Ajouter quelques résultats clés
        if "identified_arguments" in results:
            arg_count = len(results["identified_arguments"])
            conclusion_parts.append(f"- {arg_count} arguments principaux identifiés")
        
        if "identified_fallacies" in results:
            fallacy_count = len(results["identified_fallacies"])
            conclusion_parts.append(f"- {fallacy_count} sophismes détectés")
        
        # Conclusion finale
        conclusion_parts.append("\n\nConclusion générale:")
        if overall_rate >= 0.7:
            conclusion_parts.append("Le texte présente une argumentation globalement solide avec quelques faiblesses mineures.")
        elif overall_rate >= 0.5:
            conclusion_parts.append("Le texte présente une argumentation de qualité moyenne avec des forces et des faiblesses notables.")
        else:
            conclusion_parts.append("Le texte présente une argumentation faible avec des problèmes logiques significatifs.")
        
        return "\n".join(conclusion_parts)
    
    def _log_decision(self, decision_type: str, description: str) -> None:
        """
        Enregistre une décision stratégique dans l'historique.
        
        Args:
            decision_type: Le type de décision
            description: La description de la décision
        """
        decision = {
            "timestamp": datetime.now().isoformat(),
            "type": decision_type,
            "description": description
        }
        
        self.state.log_strategic_decision(decision)
        self.logger.info(f"Décision stratégique: {decision_type} - {description}")
    
    def _send_strategic_adjustments(self, adjustments: Dict[str, Any]) -> None:
        """
        Envoie les ajustements stratégiques aux agents tactiques.
        
        Args:
            adjustments: Les ajustements à envoyer
        """
        # Déterminer si les ajustements sont urgents
        has_high_priority = False
        
        if "plan_updates" in adjustments:
            for phase_id, updates in adjustments["plan_updates"].items():
                if updates.get("priority") == "high":
                    has_high_priority = True
                    break
        
        if "resource_reallocation" in adjustments:
            for resource, updates in adjustments["resource_reallocation"].items():
                if updates.get("priority") == "high":
                    has_high_priority = True
                    break
        
        # Envoyer les ajustements via le système de communication
        priority = MessagePriority.HIGH if has_high_priority else MessagePriority.NORMAL
        
        self.adapter.send_directive(
            directive_type="strategic_adjustment",
            content=adjustments,
            recipient_id="tactical_coordinator",
            priority=priority,
            metadata={
                "timestamp": datetime.now().isoformat(),
                "urgent": has_high_priority
            }
        )
        
        self.logger.info(f"Ajustements stratégiques envoyés avec priorité {priority}")
    
    def request_tactical_status(self) -> Optional[Dict[str, Any]]:
        """
        Demande le statut actuel au niveau tactique.
        
        Returns:
            Le statut tactique ou None si la demande échoue
        """
        try:
            response = self.adapter.request_tactical_status(
                recipient_id="tactical_coordinator",
                timeout=5.0
            )
            
            if response:
                self.logger.info("Statut tactique reçu")
                return response
            else:
                self.logger.warning("Délai d'attente dépassé pour la demande de statut tactique")
                return None
                
        except Exception as e:
            self.logger.error(f"Erreur lors de la demande de statut tactique: {str(e)}")
            return None