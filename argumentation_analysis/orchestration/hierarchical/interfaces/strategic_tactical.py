"""
Définit le contrat de communication entre les couches Stratégique et Tactique.

Ce module contient la classe `StrategicTacticalInterface`, qui agit comme un
médiateur et un traducteur, assurant un couplage faible entre la planification
de haut niveau (stratégique) et la coordination des tâches (tactique).

Fonctions principales :
- Traduire les objectifs stratégiques abstraits en directives tactiques concrètes.
- Agréger les rapports de progression tactiques en informations pertinentes pour
  la couche stratégique.
"""

from typing import Dict, List, Any, Optional
import logging
import uuid

from argumentation_analysis.orchestration.hierarchical.strategic.state import (
    StrategicState,
)
from argumentation_analysis.orchestration.hierarchical.tactical.state import (
    TacticalState,
)
from argumentation_analysis.paths import DATA_DIR
from argumentation_analysis.core.communication import (
    MessageMiddleware,
    StrategicAdapter,
    TacticalAdapter,
    ChannelType,
    MessagePriority,
    Message,
    MessageType,
    AgentLevel,
)


class StrategicTacticalInterface:
    """
    Assure la traduction et la médiation entre les couches stratégique et tactique.

    Cette interface est le point de passage obligé pour toute communication entre
    la stratégie et la tactique. Elle garantit que les deux couches peuvent
    évoluer indépendamment, tant que le contrat défini par cette interface est
    respecté.

    Attributes:
        strategic_state (StrategicState): L'état de la couche stratégique.
        tactical_state (TacticalState): L'état de la couche tactique.
        logger (logging.Logger): Le logger pour les événements de l'interface.
        middleware (MessageMiddleware): Le middleware pour la communication.
        strategic_adapter (StrategicAdapter): L'adaptateur pour envoyer des messages
                                              en tant que couche stratégique.
        tactical_adapter (TacticalAdapter): L'adaptateur pour envoyer des messages
                                            en tant que couche tactique.
    """

    def __init__(
        self,
        strategic_state: Optional[StrategicState] = None,
        tactical_state: Optional[TacticalState] = None,
        middleware: Optional[MessageMiddleware] = None,
    ):
        """
        Initialise l'interface stratégique-tactique.

        Args:
            strategic_state: Une référence à l'état de la couche
                stratégique.
            tactical_state: Une référence à l'état de la couche
                tactique.
            middleware: Le middleware de communication partagé.
        """
        self.strategic_state = strategic_state or StrategicState()
        self.tactical_state = tactical_state or TacticalState()
        self.logger = logging.getLogger(__name__)

        self.middleware = middleware or MessageMiddleware()
        self.strategic_adapter = StrategicAdapter(
            agent_id="strategic_interface", middleware=self.middleware
        )
        self.tactical_adapter = TacticalAdapter(
            agent_id="tactical_interface", middleware=self.middleware
        )

    def translate_objectives_to_directives(
        self, objectives: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Traduit des objectifs stratégiques en directives tactiques actionnables.

        C'est la méthode principale pour le flux descendant (top-down).
        Elle prend des objectifs généraux (le "Quoi") et les transforme en un
        plan détaillé (le "Comment") pour la couche tactique.

        Args:
            objectives: La liste des objectifs définis par la couche stratégique.

        Returns:
            Un dictionnaire structuré contenant les directives pour la couche tactique.
        """
        self.logger.info(
            f"Traduction de {len(objectives)} objectifs stratégiques en directives tactiques"
        )

        enriched_objectives = [
            self._enrich_objective(obj, objectives) for obj in objectives
        ]

        tactical_directives = {
            "objectives": enriched_objectives,
            "global_context": self._get_global_context(),
            "control_parameters": self._get_control_parameters(),
        }

        # Communication via le middleware
        conversation_id = f"directive-{uuid.uuid4().hex[:8]}"
        for i, objective in enumerate(enriched_objectives):
            self.strategic_adapter.issue_directive(
                directive_type="objective",
                parameters={
                    "objective": objective,
                    "index": i,
                    "total": len(enriched_objectives),
                    "global_context": tactical_directives["global_context"],
                    "control_parameters": tactical_directives["control_parameters"],
                },
                recipient_id="tactical_coordinator",
                priority=self._map_priority_to_enum(
                    objective.get("priority", "medium")
                ),
                metadata={"conversation_id": conversation_id},
            )

        return tactical_directives

    def process_tactical_report(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """
        Traite un rapport tactique et le consolide pour la couche stratégique.

        C'est la méthode principale pour le flux ascendant (bottom-up).
        Elle agrège des données d'exécution détaillées en métriques de haut niveau
        et en alertes qui sont pertinentes pour une décision stratégique.

        Args:
            report: Le rapport de statut envoyé par la couche tactique.

        Returns:
            Un résumé stratégique contenant des métriques, des problèmes
            identifiés et des suggestions d'ajustement.
        """
        self.logger.info("Traitement d'un rapport tactique")

        strategic_metrics = {
            "progress": report.get("overall_progress", 0.0),
            "quality_indicators": self._derive_quality_indicators(report),
            "resource_utilization": self._derive_resource_utilization(report),
        }

        strategic_issues = self._identify_strategic_issues(report.get("issues", []))

        strategic_adjustments = self._determine_strategic_adjustments(
            strategic_issues, strategic_metrics
        )

        self.strategic_state.update_global_metrics(strategic_metrics)

        return {
            "metrics": strategic_metrics,
            "issues": strategic_issues,
            "adjustments": strategic_adjustments,
            "progress_by_objective": self._translate_objective_progress(
                report.get("progress_by_objective", {})
            ),
        }

    def request_tactical_status(self, timeout: float = 5.0) -> Optional[Dict[str, Any]]:
        """
        Demande un rapport de statut complet à la couche tactique.

        Permet à la couche stratégique d'obtenir une image à la demande de l'état
        de l'exécution tactique, en dehors des rapports périodiques.

        Args:
            timeout: Le délai d'attente en secondes.

        Returns:
            Le rapport de statut, ou None en cas d'échec ou de timeout.
        """
        try:
            response = self.strategic_adapter.request_tactical_info(
                request_type="tactical_status",
                parameters={},
                recipient_id="tactical_coordinator",
                timeout=timeout,
            )
            if response:
                self.logger.info("Rapport de statut tactique reçu")
                return response

            self.logger.warning(
                "Délai d'attente dépassé pour la demande de statut tactique"
            )
            return None

        except Exception as e:
            self.logger.error(f"Erreur lors de la demande de statut tactique: {e}")
            return None

    def send_strategic_adjustment(self, adjustment: Dict[str, Any]) -> bool:
        """
        Envoie une directive d'ajustement à la couche tactique.

        Permet à la couche stratégique d'intervenir dans le plan tactique,
        par exemple pour changer la priorité d'un objectif ou réallouer des
        ressources suite à un événement imprévu.

        Args:
            adjustment: Un dictionnaire décrivant l'ajustement à effectuer.

        Returns:
            True si la directive a été envoyée, False sinon.
        """
        try:
            priority = (
                MessagePriority.HIGH
                if adjustment.get("urgent", False)
                else MessagePriority.NORMAL
            )
            message_id = self.strategic_adapter.issue_directive(
                directive_type="strategic_adjustment",
                content=adjustment,
                recipient_id="tactical_coordinator",
                priority=priority,
            )
            self.logger.info(f"Ajustement stratégique envoyé avec l'ID {message_id}")
            return True

        except Exception as e:
            self.logger.error(
                f"Erreur lors de l'envoi de l'ajustement stratégique: {e}"
            )
            return False

    # Les méthodes privées restent inchangées car elles sont des détails d'implémentation.
    # ... (le reste des méthodes privées de _enrich_objective à _map_priority_to_enum)
    def _enrich_objective(
        self, objective: Dict[str, Any], all_objectives: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        enriched_obj = objective.copy()
        enriched_obj["context"] = {
            "global_plan_phase": self._determine_phase_for_objective(objective),
            "related_objectives": self._find_related_objectives(
                objective, all_objectives
            ),
            "priority_level": self._translate_priority(
                objective.get("priority", "medium")
            ),
            "success_criteria": self._extract_success_criteria(objective),
        }
        return enriched_obj

    def _get_global_context(self) -> Dict[str, Any]:
        return {
            "analysis_phase": self._determine_current_phase(),
            "global_priorities": self._extract_global_priorities(),
            "constraints": self._extract_constraints(),
        }

    def _get_control_parameters(self) -> Dict[str, Any]:
        return {
            "detail_level": self._determine_detail_level(),
            "precision_coverage_balance": self._determine_precision_coverage_balance(),
            "methodological_preferences": self._extract_methodological_preferences(),
            "resource_limits": self._extract_resource_limits(),
        }

    def _determine_phase_for_objective(self, objective: Dict[str, Any]) -> str:
        obj_id = objective["id"]
        for phase in self.strategic_state.strategic_plan.get("phases", []):
            if obj_id in phase.get("objectives", []):
                return phase["id"]
        return "unknown"

    def _find_related_objectives(
        self, objective: Dict[str, Any], all_objectives: List[Dict[str, Any]]
    ) -> List[str]:
        related_objectives = []
        obj_description = objective["description"].lower()
        obj_id = objective["id"]
        keywords = [word for word in obj_description.split() if len(word) > 4]
        for other_obj in all_objectives:
            if other_obj["id"] == obj_id:
                continue
            other_description = other_obj["description"].lower()
            if any(keyword in other_description for keyword in keywords):
                related_objectives.append(other_obj["id"])
        return related_objectives

    def _translate_priority(self, strategic_priority: str) -> Dict[str, Any]:
        priority_mapping = {
            "high": {
                "urgency": "high",
                "resource_allocation": 0.4,
                "quality_threshold": 0.8,
            },
            "medium": {
                "urgency": "medium",
                "resource_allocation": 0.3,
                "quality_threshold": 0.7,
            },
            "low": {
                "urgency": "low",
                "resource_allocation": 0.2,
                "quality_threshold": 0.6,
            },
        }
        return priority_mapping.get(strategic_priority, priority_mapping["medium"])

    def _extract_success_criteria(self, objective: Dict[str, Any]) -> Dict[str, Any]:
        obj_id = objective["id"]
        for phase in self.strategic_state.strategic_plan.get("phases", []):
            if obj_id in phase.get("objectives", []):
                phase_id = phase["id"]
                if phase_id in self.strategic_state.strategic_plan.get(
                    "success_criteria", {}
                ):
                    return {
                        "criteria": self.strategic_state.strategic_plan[
                            "success_criteria"
                        ][phase_id],
                        "threshold": 0.8,
                    }
        return {
            "criteria": objective.get(
                "success_criteria", "Complétion satisfaisante de l'objectif"
            ),
            "threshold": 0.7,
        }

    def _determine_current_phase(self) -> str:
        progress = self.strategic_state.global_metrics.get("progress", 0.0)
        if progress < 0.3:
            return "initial"
        elif progress < 0.7:
            return "intermediate"
        else:
            return "final"

    def _extract_global_priorities(self) -> Dict[str, Any]:
        return {
            "primary_focus": self._determine_primary_focus(),
            "secondary_focus": self._determine_secondary_focus(),
            "priority_distribution": self.strategic_state.strategic_plan.get(
                "priorities", {}
            ),
        }

    def _determine_primary_focus(self) -> str:
        objective_types = {
            "argument_identification": 0,
            "fallacy_detection": 0,
            "formal_analysis": 0,
            "coherence_evaluation": 0,
        }
        for objective in self.strategic_state.global_objectives:
            description = objective["description"].lower()
            if "identifier" in description and "argument" in description:
                objective_types["argument_identification"] += 1
            elif "détecter" in description and "sophisme" in description:
                objective_types["fallacy_detection"] += 1
            elif "analyser" in description and "structure logique" in description:
                objective_types["formal_analysis"] += 1
            elif "évaluer" in description and "cohérence" in description:
                objective_types["coherence_evaluation"] += 1
        return max(objective_types, key=objective_types.get, default="general")

    def _determine_secondary_focus(self) -> str:
        primary_focus = self._determine_primary_focus()
        objective_types = {
            "argument_identification": 0,
            "fallacy_detection": 0,
            "formal_analysis": 0,
            "coherence_evaluation": 0,
        }
        for objective in self.strategic_state.global_objectives:
            description = objective["description"].lower()
            if "identifier" in description and "argument" in description:
                objective_types["argument_identification"] += 1
            elif "détecter" in description and "sophisme" in description:
                objective_types["fallacy_detection"] += 1
            elif "analyser" in description and "structure logique" in description:
                objective_types["formal_analysis"] += 1
            elif "évaluer" in description and "cohérence" in description:
                objective_types["coherence_evaluation"] += 1
        objective_types[primary_focus] = 0
        return max(objective_types, key=objective_types.get, default="general")

    def _extract_constraints(self) -> Dict[str, Any]:
        return {
            "time_constraints": {"max_duration": "medium", "deadline": None},
            "resource_constraints": {
                "max_agents": len(
                    self.strategic_state.resource_allocation.get(
                        "agent_assignments", {}
                    )
                ),
                "max_parallel_tasks": 5,
            },
            "quality_constraints": {"min_confidence": 0.7, "min_coverage": 0.8},
        }

    def _determine_expected_timeline(
        self, objectives: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        return {
            "total_duration": "medium",
            "phases": {
                "initial": {
                    "duration": "short",
                    "objectives": [
                        obj["id"]
                        for obj in objectives
                        if self._determine_phase_for_objective(obj) == "phase-1"
                    ],
                },
                "intermediate": {
                    "duration": "medium",
                    "objectives": [
                        obj["id"]
                        for obj in objectives
                        if self._determine_phase_for_objective(obj) == "phase-2"
                    ],
                },
                "final": {
                    "duration": "short",
                    "objectives": [
                        obj["id"]
                        for obj in objectives
                        if self._determine_phase_for_objective(obj) == "phase-3"
                    ],
                },
            },
        }

    def _determine_detail_level(self) -> str:
        priority_counts = {"high": 0, "medium": 0, "low": 0}
        for objective in self.strategic_state.global_objectives:
            priority = objective.get("priority", "medium")
            priority_counts[priority] += 1
        if priority_counts["high"] > priority_counts["medium"] + priority_counts["low"]:
            return "high"
        elif (
            priority_counts["low"] > priority_counts["high"] + priority_counts["medium"]
        ):
            return "low"
        else:
            return "medium"

    def _determine_precision_coverage_balance(self) -> float:
        primary_focus = self._determine_primary_focus()
        balance_mapping = {
            "argument_identification": 0.4,
            "fallacy_detection": 0.7,
            "formal_analysis": 0.8,
            "coherence_evaluation": 0.5,
            "general": 0.5,
        }
        return balance_mapping.get(primary_focus, 0.5)

    def _extract_methodological_preferences(self) -> Dict[str, Any]:
        primary_focus = self._determine_primary_focus()
        if primary_focus == "argument_identification":
            return {
                "extraction_method": "comprehensive",
                "analysis_approach": "bottom_up",
                "formalization_level": "low",
            }
        elif primary_focus == "fallacy_detection":
            return {
                "extraction_method": "targeted",
                "analysis_approach": "pattern_matching",
                "formalization_level": "medium",
            }
        elif primary_focus == "formal_analysis":
            return {
                "extraction_method": "selective",
                "analysis_approach": "top_down",
                "formalization_level": "high",
            }
        elif primary_focus == "coherence_evaluation":
            return {
                "extraction_method": "comprehensive",
                "analysis_approach": "holistic",
                "formalization_level": "medium",
            }
        else:
            return {
                "extraction_method": "balanced",
                "analysis_approach": "mixed",
                "formalization_level": "medium",
            }

    def _extract_resource_limits(self) -> Dict[str, Any]:
        return {
            "max_tasks_per_objective": 5,
            "max_parallel_tasks_per_agent": 2,
            "time_budget_per_task": {"short": 60, "medium": 180, "long": 300},
        }

    def _derive_quality_indicators(self, report: Dict[str, Any]) -> Dict[str, Any]:
        tasks_summary = report.get("tasks_summary", {})
        conflicts = report.get("conflicts", {})
        total_tasks = tasks_summary.get("total", 0)
        completed_tasks = tasks_summary.get("completed", 0)
        failed_tasks = tasks_summary.get("failed", 0)
        completion_rate = completed_tasks / total_tasks if total_tasks > 0 else 0.0
        failure_rate = failed_tasks / total_tasks if total_tasks > 0 else 0.0
        total_conflicts = conflicts.get("total", 0)
        resolved_conflicts = conflicts.get("resolved", 0)
        conflict_rate = total_conflicts / total_tasks if total_tasks > 0 else 0.0
        conflict_resolution_rate = (
            resolved_conflicts / total_conflicts if total_conflicts > 0 else 1.0
        )
        quality_score = (
            completion_rate * 0.4
            + (1.0 - failure_rate) * 0.3
            + conflict_resolution_rate * 0.3
        )
        return {
            "completion_rate": completion_rate,
            "failure_rate": failure_rate,
            "conflict_rate": conflict_rate,
            "conflict_resolution_rate": conflict_resolution_rate,
            "quality_score": quality_score,
        }

    def _derive_resource_utilization(self, report: Dict[str, Any]) -> Dict[str, Any]:
        agent_utilization = report.get("metrics", {}).get("agent_utilization", {})
        avg_utilization = (
            sum(agent_utilization.values()) / len(agent_utilization)
            if agent_utilization
            else 0.0
        )
        underutilized_agents = [
            agent for agent, util in agent_utilization.items() if util < 0.3
        ]
        overutilized_agents = [
            agent for agent, util in agent_utilization.items() if util > 0.8
        ]
        utilization_balance = (
            1.0
            - (len(underutilized_agents) + len(overutilized_agents))
            / len(agent_utilization)
            if agent_utilization
            else 0.0
        )
        return {
            "average_utilization": avg_utilization,
            "underutilized_agents": underutilized_agents,
            "overutilized_agents": overutilized_agents,
            "utilization_balance": utilization_balance,
        }

    def _identify_strategic_issues(
        self, tactical_issues: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        strategic_issues = []
        for issue in tactical_issues:
            issue_type = issue.get("type")
            severity = issue.get("severity", "medium")
            if issue_type == "blocked_task":
                objective_id = issue.get("objective_id")
                if objective_id:
                    strategic_issues.append(
                        {
                            "type": "objective_dependency_issue",
                            "description": f"Objectif {objective_id} bloqué",
                            "severity": "high" if severity == "critical" else "medium",
                            "objective_id": objective_id,
                            "details": issue,
                        }
                    )
            elif issue_type == "conflict":
                strategic_issues.append(
                    {
                        "type": "coherence_issue",
                        "description": issue.get("description", "Conflit non résolu"),
                        "severity": severity,
                        "details": issue,
                    }
                )
            elif issue_type == "high_failure_rate":
                strategic_issues.append(
                    {
                        "type": "approach_issue",
                        "description": "Taux d'échec élevé",
                        "severity": "high",
                        "details": issue,
                    }
                )
        return strategic_issues

    def _determine_strategic_adjustments(
        self, issues: List[Dict[str, Any]], metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        adjustments = {
            "plan_updates": {},
            "resource_reallocation": {},
            "objective_modifications": [],
        }
        for issue in issues:
            issue_type = issue.get("type")
            if issue_type == "objective_dependency_issue":
                objective_id = issue.get("objective_id")
                if objective_id:
                    for phase in self.strategic_state.strategic_plan.get("phases", []):
                        if objective_id in phase.get("objectives", []):
                            adjustments["plan_updates"][phase["id"]] = {
                                "priority": "high"
                            }
                            break
            elif issue_type == "coherence_issue":
                adjustments["resource_reallocation"]["conflict_resolver"] = {
                    "priority": "high"
                }
        if metrics.get("quality_indicators", {}).get("quality_score", 1.0) < 0.6:
            adjustments["resource_reallocation"]["quality_focus"] = {"priority": "high"}
        return adjustments

    def _translate_objective_progress(
        self, progress_by_objective: Dict[str, Dict[str, Any]]
    ) -> Dict[str, float]:
        return {
            obj_id: data.get("progress", 0.0)
            for obj_id, data in progress_by_objective.items()
        }

    def _map_priority_to_enum(self, priority: str) -> MessagePriority:
        return {
            "high": MessagePriority.HIGH,
            "medium": MessagePriority.NORMAL,
            "low": MessagePriority.LOW,
        }.get(priority.lower(), MessagePriority.NORMAL)
