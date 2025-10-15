"""
Module définissant l'état stratégique de l'architecture hiérarchique.

L'état stratégique contient les informations pertinentes pour le niveau stratégique,
telles que les objectifs globaux, le plan stratégique, l'allocation des ressources, etc.
"""

from typing import Dict, List, Any, Optional
import json


class StrategicState:
    """
    Classe représentant l'état du niveau stratégique de l'architecture hiérarchique.

    Cette classe encapsule toutes les informations nécessaires pour la planification
    stratégique et la supervision globale de l'analyse rhétorique.
    """

    def __init__(self):
        """Initialise un nouvel état stratégique avec des valeurs par défaut."""
        # Texte à analyser
        self.raw_text: Optional[str] = None

        # Objectifs globaux de l'analyse
        self.global_objectives: List[Dict[str, Any]] = []

        # Plan stratégique structuré
        self.strategic_plan: Dict[str, Any] = {
            "phases": [],
            "dependencies": {},
            "priorities": {},
            "success_criteria": {},
        }

        # Allocation des ressources
        self.resource_allocation: Dict[str, Any] = {
            "agent_assignments": {},
            "priority_levels": {},
            "computational_budget": {},
        }

        # Métriques globales
        self.global_metrics: Dict[str, Any] = {
            "progress": 0.0,
            "quality_indicators": {},
            "resource_utilization": {},
        }

        # Résultats d'analyse rhétorique consolidés
        self.rhetorical_analysis_summary: Dict[str, Any] = {
            "complex_fallacy_summary": {},
            "contextual_fallacy_summary": {},
            "fallacy_severity_summary": {},
            "argument_structure_summary": {},
            "argument_coherence_summary": {},
            "semantic_argument_summary": {},
        }

        # Conclusion finale
        self.final_conclusion: Optional[str] = None

        # Historique des décisions stratégiques
        self.strategic_decisions_log: List[Dict[str, Any]] = []

    def set_raw_text(self, text: str) -> None:
        """
        Définit le texte brut à analyser.

        Args:
            text: Le texte à analyser
        """
        self.raw_text = text

    def add_global_objective(self, objective: Dict[str, Any]) -> None:
        """
        Ajoute un objectif global à l'analyse.

        Args:
            objective: Dictionnaire décrivant l'objectif avec au moins les clés
                      'id', 'description' et 'priority'
        """
        self.global_objectives.append(objective)

    def update_strategic_plan(self, plan_update: Dict[str, Any]) -> None:
        """
        Met à jour le plan stratégique avec de nouvelles informations.

        Args:
            plan_update: Dictionnaire contenant les mises à jour à appliquer au plan
        """
        for key, value in plan_update.items():
            if key in self.strategic_plan:
                if isinstance(value, dict) and isinstance(
                    self.strategic_plan[key], dict
                ):
                    self.strategic_plan[key].update(value)
                else:
                    self.strategic_plan[key] = value

    def update_resource_allocation(self, allocation_update: Dict[str, Any]) -> None:
        """
        Met à jour l'allocation des ressources.

        Args:
            allocation_update: Dictionnaire contenant les mises à jour à appliquer
        """
        for key, value in allocation_update.items():
            if key in self.resource_allocation:
                if isinstance(value, dict) and isinstance(
                    self.resource_allocation[key], dict
                ):
                    self.resource_allocation[key].update(value)
                else:
                    self.resource_allocation[key] = value

    def update_global_metrics(self, metrics_update: Dict[str, Any]) -> None:
        """
        Met à jour les métriques globales.

        Args:
            metrics_update: Dictionnaire contenant les mises à jour à appliquer
        """
        for key, value in metrics_update.items():
            if key in self.global_metrics:
                if isinstance(value, dict) and isinstance(
                    self.global_metrics[key], dict
                ):
                    self.global_metrics[key].update(value)
                else:
                    self.global_metrics[key] = value

    def update_rhetorical_analysis_summary(
        self, summary_update: Dict[str, Any]
    ) -> None:
        """
        Met à jour le résumé des analyses rhétoriques.

        Args:
            summary_update: Dictionnaire contenant les mises à jour à appliquer
        """
        for key, value in summary_update.items():
            if key in self.rhetorical_analysis_summary:
                if isinstance(value, dict) and isinstance(
                    self.rhetorical_analysis_summary[key], dict
                ):
                    self.rhetorical_analysis_summary[key].update(value)
                else:
                    self.rhetorical_analysis_summary[key] = value

    def set_final_conclusion(self, conclusion: str) -> None:
        """
        Définit la conclusion finale de l'analyse.

        Args:
            conclusion: La conclusion finale
        """
        self.final_conclusion = conclusion

    def log_strategic_decision(self, decision: Dict[str, Any]) -> None:
        """
        Enregistre une décision stratégique dans l'historique.

        Args:
            decision: Dictionnaire décrivant la décision avec au moins les clés
                     'timestamp', 'description' et 'rationale'
        """
        self.strategic_decisions_log.append(decision)

    def get_snapshot(self) -> Dict[str, Any]:
        """
        Retourne un instantané de l'état stratégique actuel.

        Returns:
            Un dictionnaire représentant l'état stratégique actuel
        """
        return {
            "raw_text_length": len(self.raw_text) if self.raw_text else 0,
            "global_objectives": self.global_objectives,
            "strategic_plan": self.strategic_plan,
            "resource_allocation": self.resource_allocation,
            "global_metrics": self.global_metrics,
            "rhetorical_analysis_summary": self.rhetorical_analysis_summary,
            "final_conclusion": self.final_conclusion,
            "strategic_decisions_count": len(self.strategic_decisions_log),
        }

    def to_json(self) -> str:
        """
        Convertit l'état stratégique en chaîne JSON.

        Returns:
            Une représentation JSON de l'état stratégique
        """
        state_dict = {
            "raw_text_length": len(self.raw_text) if self.raw_text else 0,
            "global_objectives": self.global_objectives,
            "strategic_plan": self.strategic_plan,
            "resource_allocation": self.resource_allocation,
            "global_metrics": self.global_metrics,
            "rhetorical_analysis_summary": self.rhetorical_analysis_summary,
            "final_conclusion": self.final_conclusion,
            "strategic_decisions_log": self.strategic_decisions_log,
        }
        return json.dumps(state_dict, indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "StrategicState":
        """
        Crée une instance d'état stratégique à partir d'une chaîne JSON.

        Args:
            json_str: La chaîne JSON représentant l'état

        Returns:
            Une nouvelle instance de StrategicState
        """
        state_dict = json.loads(json_str)
        state = cls()

        # Restaurer les propriétés à partir du dictionnaire
        if "global_objectives" in state_dict:
            state.global_objectives = state_dict["global_objectives"]

        if "strategic_plan" in state_dict:
            state.strategic_plan = state_dict["strategic_plan"]

        if "resource_allocation" in state_dict:
            state.resource_allocation = state_dict["resource_allocation"]

        if "global_metrics" in state_dict:
            state.global_metrics = state_dict["global_metrics"]

        if "rhetorical_analysis_summary" in state_dict:
            state.rhetorical_analysis_summary = state_dict[
                "rhetorical_analysis_summary"
            ]

        if "final_conclusion" in state_dict:
            state.final_conclusion = state_dict["final_conclusion"]

        if "strategic_decisions_log" in state_dict:
            state.strategic_decisions_log = state_dict["strategic_decisions_log"]

        return state
