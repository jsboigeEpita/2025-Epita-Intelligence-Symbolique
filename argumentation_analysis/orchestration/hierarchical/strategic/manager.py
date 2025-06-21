"""
Définit le Gestionnaire Stratégique, le "cerveau" de l'orchestration.

Ce module contient la classe `StrategicManager`, qui est le point d'entrée
et le coordinateur principal de la couche stratégique. Il est responsable
de la prise de décision de haut niveau.
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
    Orchestre la couche stratégique de l'analyse hiérarchique.

    Le `StrategicManager` agit comme le décideur principal. Sa logique est
    centrée autour du cycle de vie d'une analyse :
    1.  **Initialisation**: Interprète la requête initiale et la transforme
        en objectifs et en un plan d'action de haut niveau.
    2.  **Délégation**: Communique ce plan à la couche tactique via des
        directives.
    3.  **Supervision**: Traite les rapports de progression et les alertes
        remontées par la couche tactique.
    4.  **Ajustement**: Si nécessaire, modifie la stratégie, réalloue les
        ressources ou change les priorités en fonction des feedbacks.
    5.  **Conclusion**: Lorsque l'analyse est terminée, il synthétise
        les résultats finaux en une conclusion globale.

    Attributes:
        state (StrategicState): L'état interne qui contient le plan,
            les objectifs, les métriques et l'historique des décisions.
        logger (logging.Logger): Le logger pour les événements.
        middleware (MessageMiddleware): Le système de communication pour
            interagir avec les autres couches.
        adapter (StrategicAdapter): Un adaptateur simplifiant l'envoi et la
            réception de messages via le middleware.
    """

    def __init__(self,
                 strategic_state: Optional[StrategicState] = None,
                 middleware: Optional[MessageMiddleware] = None):
        """
        Initialise le `StrategicManager`.

        Args:
            strategic_state: L'état stratégique à utiliser. Si None,
                un nouvel état est créé.
            middleware: Le middleware de communication. Si None, un
                nouveau middleware est créé.
        """
        self.state = strategic_state or StrategicState()
        self.logger = logging.getLogger(__name__)
        self.middleware = middleware or MessageMiddleware()
        self.adapter = StrategicAdapter(agent_id="strategic_manager", middleware=self.middleware)

    def initialize_analysis(self, text: str) -> Dict[str, Any]:
        """
        Démarre et configure une nouvelle analyse à partir d'un texte.

        C'est le point d'entrée principal. Cette méthode réinitialise l'état,
        effectue une analyse préliminaire pour définir des objectifs et un
        plan, et alloue les ressources initiales.

        Args:
            text: Le texte source à analyser.

        Returns:
            Un dictionnaire contenant le plan stratégique initial et les
            objectifs globaux.
        """
        self.logger.info("Initialisation d'une nouvelle analyse rhétorique")
        self.state.set_raw_text(text)
        
        self._define_initial_objectives()
        self._create_initial_strategic_plan()
        self._allocate_initial_resources()
        
        self._log_decision("Initialisation de l'analyse", 
                           "Analyse préliminaire et définition des objectifs initiaux")
        
        # Délègue le plan initial à la couche tactique
        self.adapter.issue_directive(
            directive_type="new_strategic_plan",
            content={"plan": self.state.strategic_plan, "objectives": self.state.global_objectives},
            recipient_id="tactical_coordinator",
            priority=MessagePriority.HIGH
        )

        return {
            "objectives": self.state.global_objectives,
            "strategic_plan": self.state.strategic_plan
        }
    
    def process_tactical_feedback(self, feedback: Dict[str, Any]) -> Dict[str, Any]:
        """
        Traite un rapport de la couche tactique et ajuste la stratégie.

        Cette méthode est appelée périodiquement ou en réponse à une alerte.
        Elle met à jour les métriques de progression et, si des problèmes
        sont signalés, détermine et applique les ajustements nécessaires.

        Args:
            feedback: Un rapport de la couche tactique, contenant
                les métriques de progression et les problèmes rencontrés.

        Returns:
            Un dictionnaire résumant les ajustements décidés et l'état
            actuel des métriques.
        """
        self.logger.info("Traitement du feedback du niveau tactique")
        
        # Mise à jour de l'état avec le nouveau feedback
        if "progress_metrics" in feedback:
            self.state.update_global_metrics(feedback["progress_metrics"])
        
        issues = feedback.get("issues", [])
        adjustments = {}
        
        if issues:
            adjustments = self._determine_strategic_adjustments(issues)
            self._apply_strategic_adjustments(adjustments)
            self._log_decision(
                "Ajustement stratégique",
                f"Réponse à {len(issues)} problème(s) signalé(s)."
            )
            # Communique les ajustements à la couche tactique
            self._send_strategic_adjustments(adjustments)
        
        return {
            "strategic_adjustments": adjustments,
            "updated_metrics": self.state.global_metrics
        }
    
    def evaluate_final_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Évalue les résultats finaux et formule une conclusion.

        C'est la dernière étape du processus. Elle compare les résultats
        consolidés aux objectifs initiaux, calcule un score de succès et
        génère une conclusion narrative.

        Args:
            results: Un dictionnaire contenant les résultats finaux de
                toutes les analyses.

        Returns:
            Un rapport final contenant la conclusion, l'évaluation
            détaillée et un snapshot de l'état final.
        """
        self.logger.info("Évaluation des résultats finaux de l'analyse")
        
        evaluation = self._evaluate_results_against_objectives(results)
        conclusion = self._formulate_conclusion(results, evaluation)
        self.state.set_final_conclusion(conclusion)
        
        self._log_decision("Évaluation finale", "Conclusion formulée.")
        
        self.adapter.publish_strategic_decision(
            decision_type="final_conclusion",
            content={"conclusion": conclusion, "evaluation": evaluation},
            priority=MessagePriority.HIGH
        )
        
        return {
            "conclusion": conclusion,
            "evaluation": evaluation,
            "final_state": self.state.get_snapshot()
        }

    def request_tactical_status(self) -> Optional[Dict[str, Any]]:
        """
        Demande un rapport de statut à la demande à la couche tactique.

        Permet de "sonder" l'état de la couche inférieure en dehors des
        rapports de feedback réguliers.

        Returns:
            Le statut actuel de la couche tactique, ou None en cas d'échec.
        """
        self.logger.info("Demande de statut au niveau tactique.")
        try:
            response = self.adapter.request_tactical_info(
                request_type="status_report",
                recipient_id="tactical_coordinator",
                timeout=5.0
            )
            if response:
                self.logger.info("Statut tactique reçu.")
                return response
            self.logger.warning("Timeout pour la demande de statut tactique.")
            return None
        except Exception as e:
            self.logger.error(f"Erreur lors de la demande de statut tactique: {e}")
            return None
    
    # ... Les méthodes privées restent inchangées comme détails d'implémentation ...
    def _define_initial_objectives(self) -> None:
        objectives = [
            {"id": "obj-1", "description": "Identifier les arguments principaux", "priority": "high"},
            {"id": "obj-2", "description": "Détecter les sophismes", "priority": "high"},
            {"id": "obj-3", "description": "Analyser la structure logique", "priority": "medium"},
            {"id": "obj-4", "description": "Évaluer la cohérence globale", "priority": "medium"}
        ]
        for objective in objectives:
            self.state.add_global_objective(objective)

    def _create_initial_strategic_plan(self) -> None:
        plan_update = {
            "phases": [
                {"id": "phase-1", "name": "Analyse préliminaire", "objectives": ["obj-1"]},
                {"id": "phase-2", "name": "Analyse approfondie", "objectives": ["obj-2", "obj-3"]},
                {"id": "phase-3", "name": "Synthèse", "objectives": ["obj-4"]}
            ],
            "dependencies": {"phase-2": ["phase-1"], "phase-3": ["phase-2"]},
            "priorities": {"phase-1": "high", "phase-2": "high", "phase-3": "medium"}
        }
        self.state.update_strategic_plan(plan_update)

    def _allocate_initial_resources(self) -> None:
        allocation_update = {
            "agent_assignments": {"informal_analyzer": ["phase-1", "phase-2"], "logic_analyzer": ["phase-2", "phase-3"]},
            "computational_budget": {"informal_analyzer": 0.5, "logic_analyzer": 0.5}
        }
        self.state.update_resource_allocation(allocation_update)

    def _determine_strategic_adjustments(self, issues: List[Dict[str, Any]]) -> Dict[str, Any]:
        adjustments = {"plan_updates": {}, "resource_reallocation": {}, "objective_modifications": []}
        for issue in issues:
            issue_type = issue.get("type")
            if issue_type == "resource_shortage":
                resource = issue.get("resource")
                if resource:
                    adjustments["resource_reallocation"][resource] = {"budget_increase": 0.2}
            elif issue_type == "objective_unrealistic":
                objective_id = issue.get("objective_id")
                if objective_id:
                    adjustments["objective_modifications"].append({"id": objective_id, "action": "modify", "updates": {"priority": "low"}})
        return adjustments

    def _apply_strategic_adjustments(self, adjustments: Dict[str, Any]) -> None:
        if "plan_updates" in adjustments:
            self.state.update_strategic_plan(adjustments["plan_updates"])
        if "resource_reallocation" in adjustments:
            self.state.update_resource_allocation(adjustments["resource_reallocation"])
        if "objective_modifications" in adjustments:
            for mod in adjustments["objective_modifications"]:
                for i, obj in enumerate(self.state.global_objectives):
                    if obj["id"] == mod["id"]:
                        self.state.global_objectives[i].update(mod.get("updates", {}))
                        break

    def _send_strategic_adjustments(self, adjustments: Dict[str, Any]) -> None:
        self.adapter.issue_directive(
            directive_type="strategic_adjustment",
            content=adjustments,
            recipient_id="tactical_coordinator",
            priority=MessagePriority.HIGH
        )
        self.logger.info("Ajustements stratégiques envoyés.")

    def _evaluate_results_against_objectives(self, results: Dict[str, Any]) -> Dict[str, Any]:
        evaluation = {"objectives_evaluation": {}, "overall_success_rate": 0.0, "strengths": [], "weaknesses": []}
        total_score = 0.0
        for objective in self.state.global_objectives:
            obj_id = objective["id"]
            success_rate = results.get(obj_id, {}).get("success_rate", 0.0)
            total_score += success_rate
            evaluation["objectives_evaluation"][obj_id] = {"success_rate": success_rate}
            if success_rate >= 0.8:
                evaluation["strengths"].append(objective['description'])
            elif success_rate <= 0.4:
                evaluation["weaknesses"].append(objective['description'])
        if self.state.global_objectives:
            evaluation["overall_success_rate"] = total_score / len(self.state.global_objectives)
        return evaluation

    def _formulate_conclusion(self, results: Dict[str, Any], evaluation: Dict[str, Any]) -> str:
        overall_rate = evaluation["overall_success_rate"]
        if overall_rate >= 0.7:
            return "Analyse réussie avec une performance globale élevée."
        elif overall_rate >= 0.5:
            return "Analyse satisfaisante avec quelques faiblesses."
        else:
            return "L'analyse a rencontré des difficultés significatives."

    def _log_decision(self, decision_type: str, description: str) -> None:
        decision = {"timestamp": datetime.now().isoformat(), "type": decision_type, "description": description}
        self.state.log_strategic_decision(decision)
        self.logger.info(f"Décision Stratégique: {decision_type} - {description}")