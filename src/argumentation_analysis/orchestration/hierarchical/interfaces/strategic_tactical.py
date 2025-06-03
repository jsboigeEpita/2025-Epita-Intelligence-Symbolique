"""
Module définissant l'interface entre les niveaux stratégique et tactique.

Cette interface définit comment les objectifs stratégiques sont traduits en plans tactiques
et comment les résultats tactiques sont remontés au niveau stratégique.
"""

from typing import Dict, List, Any, Optional
import logging
from datetime import datetime
import uuid

from argumentation_analysis.orchestration.hierarchical.strategic.state import StrategicState
from argumentation_analysis.orchestration.hierarchical.tactical.state import TacticalState
from argumentation_analysis.paths import DATA_DIR
from argumentation_analysis.core.communication import (
    MessageMiddleware, StrategicAdapter, TacticalAdapter,
    ChannelType, MessagePriority, Message, MessageType, AgentLevel
)


class StrategicTacticalInterface:
    """
    Classe représentant l'interface entre les niveaux stratégique et tactique.
    
    Cette interface est responsable de:
    - Traduire les objectifs stratégiques en directives tactiques
    - Transmettre le contexte global nécessaire au niveau tactique
    - Remonter les rapports de progression du niveau tactique au niveau stratégique
    - Remonter les résultats agrégés du niveau tactique au niveau stratégique
    - Gérer les demandes d'ajustement entre les niveaux
    
    Cette interface utilise le système de communication multi-canal pour faciliter
    les échanges entre les niveaux stratégique et tactique.
    """
    
    def __init__(self, strategic_state: Optional[StrategicState] = None,
               tactical_state: Optional[TacticalState] = None,
               middleware: Optional[MessageMiddleware] = None):
        """
        Initialise une nouvelle interface stratégique-tactique.
        
        Args:
            strategic_state: L'état stratégique à utiliser. Si None, un nouvel état est créé.
            tactical_state: L'état tactique à utiliser. Si None, un nouvel état est créé.
            middleware: Le middleware de communication à utiliser. Si None, un nouveau middleware est créé.
        """
        self.strategic_state = strategic_state if strategic_state else StrategicState()
        self.tactical_state = tactical_state if tactical_state else TacticalState()
        self.logger = logging.getLogger(__name__)
        
        # Initialiser le middleware de communication
        self.middleware = middleware if middleware else MessageMiddleware()
        
        # Créer les adaptateurs pour les niveaux stratégique et tactique
        self.strategic_adapter = StrategicAdapter(
            agent_id="strategic_interface",
            middleware=self.middleware
        )
        
        self.tactical_adapter = TacticalAdapter(
            agent_id="tactical_interface",
            middleware=self.middleware
        )
    
    def translate_objectives(self, objectives: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Traduit les objectifs stratégiques en directives tactiques.
        
        Args:
            objectives: Liste des objectifs stratégiques
            
        Returns:
            Un dictionnaire contenant les directives tactiques
        """
        self.logger.info(f"Traduction de {len(objectives)} objectifs stratégiques en directives tactiques")
        
        # Enrichir les objectifs avec des informations contextuelles
        enriched_objectives = []
        
        for objective in objectives:
            # Copier l'objectif de base
            enriched_obj = objective.copy()
            
            # Ajouter des informations contextuelles
            enriched_obj["context"] = {
                "global_plan_phase": self._determine_phase_for_objective(objective),
                "related_objectives": self._find_related_objectives(objective, objectives),
                "priority_level": self._translate_priority(objective.get("priority", "medium")),
                "success_criteria": self._extract_success_criteria(objective)
            }
            
            enriched_objectives.append(enriched_obj)
        
        # Créer les directives tactiques
        tactical_directives = {
            "objectives": enriched_objectives,
            "global_context": {
                "analysis_phase": self._determine_current_phase(),
                "global_priorities": self._extract_global_priorities(),
                "constraints": self._extract_constraints(),
                "expected_timeline": self._determine_expected_timeline(enriched_objectives)
            },
            "control_parameters": {
                "detail_level": self._determine_detail_level(),
                "precision_coverage_balance": self._determine_precision_coverage_balance(),
                "methodological_preferences": self._extract_methodological_preferences(),
                "resource_limits": self._extract_resource_limits()
            }
        }
        
        # Envoyer les directives tactiques via le système de communication
        conversation_id = f"directive-{uuid.uuid4().hex[:8]}"
        
        for i, objective in enumerate(enriched_objectives):
            # Envoyer chaque objectif comme une directive séparée
            self.strategic_adapter.send_directive(
                directive_type="objective",
                content={
                    "objective": objective,
                    "index": i,
                    "total": len(enriched_objectives),
                    "global_context": tactical_directives["global_context"],
                    "control_parameters": tactical_directives["control_parameters"]
                },
                recipient_id="tactical_coordinator",
                priority=self._map_priority_to_enum(objective.get("priority", "medium")),
                metadata={"conversation_id": conversation_id}
            )
        
        return tactical_directives
    
    def _determine_phase_for_objective(self, objective: Dict[str, Any]) -> str:
        """
        Détermine la phase du plan global à laquelle appartient un objectif.
        
        Args:
            objective: L'objectif à analyser
            
        Returns:
            La phase du plan global
        """
        # Cette méthode serait normalement plus sophistiquée
        # Exemple simple: utiliser les phases du plan stratégique
        
        obj_id = objective["id"]
        
        for phase in self.strategic_state.strategic_plan.get("phases", []):
            if obj_id in phase.get("objectives", []):
                return phase["id"]
        
        return "unknown"
    
    def _find_related_objectives(self, objective: Dict[str, Any], 
                               all_objectives: List[Dict[str, Any]]) -> List[str]:
        """
        Trouve les objectifs liés à un objectif donné.
        
        Args:
            objective: L'objectif à analyser
            all_objectives: Liste de tous les objectifs
            
        Returns:
            Liste des identifiants des objectifs liés
        """
        # Cette méthode serait normalement plus sophistiquée
        # Exemple simple: trouver les objectifs avec des mots-clés similaires
        
        related_objectives = []
        obj_description = objective["description"].lower()
        obj_id = objective["id"]
        
        # Extraire des mots-clés de la description
        keywords = [word for word in obj_description.split() if len(word) > 4]
        
        for other_obj in all_objectives:
            if other_obj["id"] == obj_id:
                continue
            
            other_description = other_obj["description"].lower()
            
            # Vérifier si des mots-clés sont présents dans l'autre description
            if any(keyword in other_description for keyword in keywords):
                related_objectives.append(other_obj["id"])
        
        return related_objectives
    
    def _translate_priority(self, strategic_priority: str) -> Dict[str, Any]:
        """
        Traduit une priorité stratégique en paramètres tactiques.
        
        Args:
            strategic_priority: La priorité stratégique
            
        Returns:
            Un dictionnaire contenant les paramètres tactiques
        """
        # Cette méthode serait normalement plus sophistiquée
        # Exemple simple: traduire la priorité en paramètres tactiques
        
        priority_mapping = {
            "high": {
                "urgency": "high",
                "resource_allocation": 0.4,
                "quality_threshold": 0.8
            },
            "medium": {
                "urgency": "medium",
                "resource_allocation": 0.3,
                "quality_threshold": 0.7
            },
            "low": {
                "urgency": "low",
                "resource_allocation": 0.2,
                "quality_threshold": 0.6
            }
        }
        
        return priority_mapping.get(strategic_priority, priority_mapping["medium"])
    
    def _extract_success_criteria(self, objective: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extrait les critères de succès pour un objectif.
        
        Args:
            objective: L'objectif à analyser
            
        Returns:
            Un dictionnaire contenant les critères de succès
        """
        # Cette méthode serait normalement plus sophistiquée
        # Exemple simple: extraire les critères de succès de l'objectif
        
        obj_id = objective["id"]
        
        # Chercher les critères de succès dans le plan stratégique
        for phase in self.strategic_state.strategic_plan.get("phases", []):
            if obj_id in phase.get("objectives", []):
                phase_id = phase["id"]
                if phase_id in self.strategic_state.strategic_plan.get("success_criteria", {}):
                    return {
                        "criteria": self.strategic_state.strategic_plan["success_criteria"][phase_id],
                        "threshold": 0.8
                    }
        
        # Critères par défaut
        return {
            "criteria": objective.get("success_criteria", "Complétion satisfaisante de l'objectif"),
            "threshold": 0.7
        }
    
    def _determine_current_phase(self) -> str:
        """
        Détermine la phase actuelle du plan global.
        
        Returns:
            La phase actuelle
        """
        # Cette méthode serait normalement plus sophistiquée
        # Exemple simple: utiliser les métriques globales pour déterminer la phase
        
        progress = self.strategic_state.global_metrics.get("progress", 0.0)
        
        if progress < 0.3:
            return "initial"
        elif progress < 0.7:
            return "intermediate"
        else:
            return "final"
    
    def _extract_global_priorities(self) -> Dict[str, Any]:
        """
        Extrait les priorités globales du plan stratégique.
        
        Returns:
            Un dictionnaire contenant les priorités globales
        """
        # Cette méthode serait normalement plus sophistiquée
        # Exemple simple: extraire les priorités du plan stratégique
        
        return {
            "primary_focus": self._determine_primary_focus(),
            "secondary_focus": self._determine_secondary_focus(),
            "priority_distribution": self.strategic_state.strategic_plan.get("priorities", {})
        }
    
    def _determine_primary_focus(self) -> str:
        """
        Détermine le focus principal de l'analyse.
        
        Returns:
            Le focus principal
        """
        # Cette méthode serait normalement plus sophistiquée
        # Exemple simple: déterminer le focus en fonction des objectifs
        
        # Compter les types d'objectifs
        objective_types = {
            "argument_identification": 0,
            "fallacy_detection": 0,
            "formal_analysis": 0,
            "coherence_evaluation": 0
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
        
        # Trouver le type le plus fréquent
        max_count = 0
        primary_focus = "general"
        
        for focus_type, count in objective_types.items():
            if count > max_count:
                max_count = count
                primary_focus = focus_type
        
        return primary_focus
    
    def _determine_secondary_focus(self) -> str:
        """
        Détermine le focus secondaire de l'analyse.
        
        Returns:
            Le focus secondaire
        """
        # Cette méthode serait normalement plus sophistiquée
        # Exemple simple: déterminer le focus secondaire en fonction des objectifs
        
        primary_focus = self._determine_primary_focus()
        
        # Compter les types d'objectifs
        objective_types = {
            "argument_identification": 0,
            "fallacy_detection": 0,
            "formal_analysis": 0,
            "coherence_evaluation": 0
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
        
        # Exclure le focus principal
        objective_types[primary_focus] = 0
        
        # Trouver le type le plus fréquent
        max_count = 0
        secondary_focus = "general"
        
        for focus_type, count in objective_types.items():
            if count > max_count:
                max_count = count
                secondary_focus = focus_type
        
        return secondary_focus
    
    def _extract_constraints(self) -> Dict[str, Any]:
        """
        Extrait les contraintes du plan stratégique.
        
        Returns:
            Un dictionnaire contenant les contraintes
        """
        # Cette méthode serait normalement plus sophistiquée
        # Exemple simple: définir des contraintes génériques
        
        return {
            "time_constraints": {
                "max_duration": "medium",
                "deadline": None
            },
            "resource_constraints": {
                "max_agents": len(self.strategic_state.resource_allocation.get("agent_assignments", {})),
                "max_parallel_tasks": 5
            },
            "quality_constraints": {
                "min_confidence": 0.7,
                "min_coverage": 0.8
            }
        }
    
    def _determine_expected_timeline(self, objectives: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Détermine la timeline attendue pour les objectifs.
        
        Args:
            objectives: Liste des objectifs
            
        Returns:
            Un dictionnaire contenant la timeline attendue
        """
        # Cette méthode serait normalement plus sophistiquée
        # Exemple simple: définir une timeline générique
        
        return {
            "total_duration": "medium",
            "phases": {
                "initial": {
                    "duration": "short",
                    "objectives": [obj["id"] for obj in objectives if self._determine_phase_for_objective(obj) == "phase-1"]
                },
                "intermediate": {
                    "duration": "medium",
                    "objectives": [obj["id"] for obj in objectives if self._determine_phase_for_objective(obj) == "phase-2"]
                },
                "final": {
                    "duration": "short",
                    "objectives": [obj["id"] for obj in objectives if self._determine_phase_for_objective(obj) == "phase-3"]
                }
            }
        }
    
    def _determine_detail_level(self) -> str:
        """
        Détermine le niveau de détail requis pour l'analyse.
        
        Returns:
            Le niveau de détail
        """
        # Cette méthode serait normalement plus sophistiquée
        # Exemple simple: déterminer le niveau de détail en fonction des objectifs
        
        # Compter les objectifs par priorité
        priority_counts = {
            "high": 0,
            "medium": 0,
            "low": 0
        }
        
        for objective in self.strategic_state.global_objectives:
            priority = objective.get("priority", "medium")
            priority_counts[priority] += 1
        
        # Déterminer le niveau de détail en fonction des priorités
        if priority_counts["high"] > priority_counts["medium"] + priority_counts["low"]:
            return "high"
        elif priority_counts["low"] > priority_counts["high"] + priority_counts["medium"]:
            return "low"
        else:
            return "medium"
    
    def _determine_precision_coverage_balance(self) -> float:
        """
        Détermine l'équilibre entre précision et couverture.
        
        Returns:
            Un score entre 0.0 (priorité à la couverture) et 1.0 (priorité à la précision)
        """
        # Cette méthode serait normalement plus sophistiquée
        # Exemple simple: déterminer l'équilibre en fonction du focus
        
        primary_focus = self._determine_primary_focus()
        
        # Définir l'équilibre en fonction du focus
        balance_mapping = {
            "argument_identification": 0.4,  # Priorité légère à la couverture
            "fallacy_detection": 0.7,  # Priorité à la précision
            "formal_analysis": 0.8,  # Forte priorité à la précision
            "coherence_evaluation": 0.5,  # Équilibre
            "general": 0.5  # Équilibre par défaut
        }
        
        return balance_mapping.get(primary_focus, 0.5)
    
    def _extract_methodological_preferences(self) -> Dict[str, Any]:
        """
        Extrait les préférences méthodologiques du plan stratégique.
        
        Returns:
            Un dictionnaire contenant les préférences méthodologiques
        """
        # Cette méthode serait normalement plus sophistiquée
        # Exemple simple: définir des préférences génériques
        
        primary_focus = self._determine_primary_focus()
        
        # Définir les préférences en fonction du focus
        if primary_focus == "argument_identification":
            return {
                "extraction_method": "comprehensive",
                "analysis_approach": "bottom_up",
                "formalization_level": "low"
            }
        elif primary_focus == "fallacy_detection":
            return {
                "extraction_method": "targeted",
                "analysis_approach": "pattern_matching",
                "formalization_level": "medium"
            }
        elif primary_focus == "formal_analysis":
            return {
                "extraction_method": "selective",
                "analysis_approach": "top_down",
                "formalization_level": "high"
            }
        elif primary_focus == "coherence_evaluation":
            return {
                "extraction_method": "comprehensive",
                "analysis_approach": "holistic",
                "formalization_level": "medium"
            }
        else:
            return {
                "extraction_method": "balanced",
                "analysis_approach": "mixed",
                "formalization_level": "medium"
            }
    
    def _extract_resource_limits(self) -> Dict[str, Any]:
        """
        Extrait les limites de ressources du plan stratégique.
        
        Returns:
            Un dictionnaire contenant les limites de ressources
        """
        # Cette méthode serait normalement plus sophistiquée
        # Exemple simple: définir des limites génériques
        
        return {
            "max_tasks_per_objective": 5,
            "max_parallel_tasks_per_agent": 2,
            "time_budget_per_task": {
                "short": 60,  # secondes
                "medium": 180,  # secondes
                "long": 300  # secondes
            }
        }
    
    def process_tactical_report(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """
        Traite un rapport tactique et le traduit en informations stratégiques.
        
        Args:
            report: Le rapport tactique
            
        Returns:
            Un dictionnaire contenant les informations stratégiques
        """
        self.logger.info("Traitement d'un rapport tactique")
        
        # Extraire les informations pertinentes du rapport
        overall_progress = report.get("overall_progress", 0.0)
        tasks_summary = report.get("tasks_summary", {})
        progress_by_objective = report.get("progress_by_objective", {})
        issues = report.get("issues", [])
        
        # Traduire en métriques stratégiques
        strategic_metrics = {
            "progress": overall_progress,
            "quality_indicators": self._derive_quality_indicators(report),
            "resource_utilization": self._derive_resource_utilization(report)
        }
        
        # Identifier les problèmes stratégiques
        strategic_issues = self._identify_strategic_issues(issues)
        
        # Déterminer les ajustements nécessaires
        strategic_adjustments = self._determine_strategic_adjustments(strategic_issues, strategic_metrics)
        
        # Mettre à jour l'état stratégique
        self.strategic_state.update_global_metrics(strategic_metrics)
        
        # Recevoir les rapports tactiques via le système de communication
        pending_reports = self.strategic_adapter.get_pending_reports(max_count=10)
        
        for tactical_report in pending_reports:
            report_content = tactical_report.content.get(DATA_DIR, {})
            report_type = tactical_report.content.get("report_type")
            
            if report_type == "progress_update":
                # Mettre à jour les métriques avec les informations du rapport
                if "progress" in report_content:
                    strategic_metrics["progress"] = max(
                        strategic_metrics["progress"],
                        report_content["progress"]
                    )
                
                # Ajouter les problèmes signalés
                if "issues" in report_content:
                    new_issues = self._identify_strategic_issues(report_content["issues"])
                    strategic_issues.extend(new_issues)
        
        return {
            "metrics": strategic_metrics,
            "issues": strategic_issues,
            "adjustments": strategic_adjustments,
            "progress_by_objective": self._translate_objective_progress(progress_by_objective)
        }
    
    def _derive_quality_indicators(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """
        Dérive des indicateurs de qualité à partir du rapport tactique.
        
        Args:
            report: Le rapport tactique
            
        Returns:
            Un dictionnaire contenant les indicateurs de qualité
        """
        # Cette méthode serait normalement plus sophistiquée
        # Exemple simple: dériver des indicateurs de qualité génériques
        
        tasks_summary = report.get("tasks_summary", {})
        issues = report.get("issues", [])
        conflicts = report.get("conflicts", {})
        
        # Calculer le taux de complétion
        total_tasks = tasks_summary.get("total", 0)
        completed_tasks = tasks_summary.get("completed", 0)
        failed_tasks = tasks_summary.get("failed", 0)
        
        completion_rate = completed_tasks / total_tasks if total_tasks > 0 else 0.0
        failure_rate = failed_tasks / total_tasks if total_tasks > 0 else 0.0
        
        # Calculer le taux de conflits
        total_conflicts = conflicts.get("total", 0)
        resolved_conflicts = conflicts.get("resolved", 0)
        
        conflict_rate = total_conflicts / total_tasks if total_tasks > 0 else 0.0
        conflict_resolution_rate = resolved_conflicts / total_conflicts if total_conflicts > 0 else 1.0
        
        # Calculer le score de qualité global
        quality_score = (
            completion_rate * 0.4 +
            (1.0 - failure_rate) * 0.3 +
            conflict_resolution_rate * 0.3
        )
        
        return {
            "completion_rate": completion_rate,
            "failure_rate": failure_rate,
            "conflict_rate": conflict_rate,
            "conflict_resolution_rate": conflict_resolution_rate,
            "quality_score": quality_score
        }
    
    def _derive_resource_utilization(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """
        Dérive des indicateurs d'utilisation des ressources à partir du rapport tactique.
        
        Args:
            report: Le rapport tactique
            
        Returns:
            Un dictionnaire contenant les indicateurs d'utilisation des ressources
        """
        # Cette méthode serait normalement plus sophistiquée
        # Exemple simple: dériver des indicateurs d'utilisation génériques
        
        metrics = report.get("metrics", {})
        agent_utilization = metrics.get("agent_utilization", {})
        
        # Calculer l'utilisation moyenne des agents
        avg_utilization = sum(agent_utilization.values()) / len(agent_utilization) if agent_utilization else 0.0
        
        # Identifier les agents sous-utilisés et sur-utilisés
        underutilized_agents = [agent for agent, util in agent_utilization.items() if util < 0.3]
        overutilized_agents = [agent for agent, util in agent_utilization.items() if util > 0.8]
        
        return {
            "average_utilization": avg_utilization,
            "underutilized_agents": underutilized_agents,
            "overutilized_agents": overutilized_agents,
            "utilization_balance": 1.0 - (len(underutilized_agents) + len(overutilized_agents)) / len(agent_utilization) if agent_utilization else 0.0
        }
    
    def _identify_strategic_issues(self, tactical_issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Identifie les problèmes stratégiques à partir des problèmes tactiques.
        
        Args:
            tactical_issues: Liste des problèmes tactiques
            
        Returns:
            Liste des problèmes stratégiques
        """
        # Cette méthode serait normalement plus sophistiquée
        # Exemple simple: traduire les problèmes tactiques en problèmes stratégiques
        
        strategic_issues = []
        
        for issue in tactical_issues:
            issue_type = issue.get("type")
            severity = issue.get("severity", "medium")
            
            if issue_type == "blocked_task":
                # Traduire en problème de dépendance stratégique
                task_id = issue.get("task_id")
                objective_id = issue.get("objective_id")
                
                if objective_id:
                    strategic_issues.append({
                        "type": "objective_dependency_issue",
                        "description": f"Objectif {objective_id} bloqué par des dépendances",
                        "severity": "high" if severity == "critical" else "medium",
                        "objective_id": objective_id,
                        "details": {
                            "blocked_task": task_id,
                            "blocking_dependencies": issue.get("blocked_by", [])
                        }
                    })
            
            elif issue_type == "conflict":
                # Traduire en problème de cohérence stratégique
                involved_tasks = issue.get("involved_tasks", [])
                
                strategic_issues.append({
                    "type": "coherence_issue",
                    "description": issue.get("description", "Conflit non résolu"),
                    "severity": severity,
                    "details": {
                        "involved_tasks": involved_tasks
                    }
                })
            
            elif issue_type == "high_failure_rate":
                # Traduire en problème d'approche stratégique
                strategic_issues.append({
                    "type": "approach_issue",
                    "description": "Taux d'échec élevé dans l'exécution des tâches",
                    "severity": "high",
                    "details": {
                        "failure_rate": issue.get("failed_tasks", 0) / issue.get("total_tasks", 1)
                    }
                })
        
        return strategic_issues
    
    def _determine_strategic_adjustments(self, issues: List[Dict[str, Any]], 
                                       metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Détermine les ajustements stratégiques nécessaires.
        
        Args:
            issues: Liste des problèmes stratégiques
            metrics: Métriques stratégiques
            
        Returns:
            Un dictionnaire contenant les ajustements stratégiques
        """
        # Cette méthode serait normalement plus sophistiquée
        # Exemple simple: déterminer des ajustements génériques
        
        adjustments = {
            "plan_updates": {},
            "resource_reallocation": {},
            "objective_modifications": []
        }
        
        for issue in issues:
            issue_type = issue.get("type")
            severity = issue.get("severity", "medium")
            
            if issue_type == "objective_dependency_issue":
                # Ajuster le plan pour résoudre les problèmes de dépendance
                objective_id = issue.get("objective_id")
                
                if objective_id:
                    # Trouver la phase associée à cet objectif
                    for phase in self.strategic_state.strategic_plan.get("phases", []):
                        if objective_id in phase.get("objectives", []):
                            phase_id = phase["id"]
                            
                            adjustments["plan_updates"][phase_id] = {
                                "estimated_duration": "long" if severity == "high" else "medium",
                                "priority": "high" if severity == "high" else "medium"
                            }
                            
                            break
            
            elif issue_type == "coherence_issue":
                # Ajuster les ressources pour résoudre les problèmes de cohérence
                adjustments["resource_reallocation"]["conflict_resolver"] = {
                    "priority": "high" if severity == "high" else "medium",
                    "budget_increase": 0.2 if severity == "high" else 0.1
                }
            
            elif issue_type == "approach_issue":
                # Modifier les objectifs pour résoudre les problèmes d'approche
                for objective in self.strategic_state.global_objectives:
                    adjustments["objective_modifications"].append({
                        "id": objective["id"],
                        "action": "modify",
                        "updates": {
                            "priority": "medium",
                            "success_criteria": "Critères ajustés pour améliorer le taux de succès"
                        }
                    })
        
        # Ajuster en fonction des métriques
        quality_indicators = metrics.get("quality_indicators", {})
        resource_utilization = metrics.get("resource_utilization", {})
        
        # Si la qualité est faible, augmenter les ressources
        if quality_indicators.get("quality_score", 0.0) < 0.6:
            adjustments["resource_reallocation"]["quality_focus"] = {
                "priority": "high",
                "budget_increase": 0.2
            }
        
        # Si l'utilisation des ressources est déséquilibrée, réallouer
        if resource_utilization.get("utilization_balance", 1.0) < 0.7:
            for agent in resource_utilization.get("overutilized_agents", []):
                adjustments["resource_reallocation"][agent] = {
                    "priority": "high",
                    "budget_increase": 0.1
                }
        
        return adjustments
    
    def _translate_objective_progress(self, progress_by_objective: Dict[str, Dict[str, Any]]) -> Dict[str, float]:
        """
        Traduit la progression par objectif en format stratégique.
        
        Args:
            progress_by_objective: Progression par objectif au format tactique
            
        Returns:
            Un dictionnaire contenant la progression par objectif au format stratégique
        """
        # Cette méthode serait normalement plus sophistiquée
        # Exemple simple: extraire simplement la progression
        
        return {obj_id: data.get("progress", 0.0) for obj_id, data in progress_by_objective.items()}
    
    def _map_priority_to_enum(self, priority: str) -> MessagePriority:
        """
        Convertit une priorité textuelle en valeur d'énumération MessagePriority.
        
        Args:
            priority: La priorité textuelle ("high", "medium", "low")
            
        Returns:
            La valeur d'énumération MessagePriority correspondante
        """
        priority_map = {
            "high": MessagePriority.HIGH,
            "medium": MessagePriority.NORMAL,
            "low": MessagePriority.LOW
        }
        
        return priority_map.get(priority.lower(), MessagePriority.NORMAL)
    
    def request_tactical_status(self, timeout: float = 5.0) -> Optional[Dict[str, Any]]:
        """
        Demande un rapport de statut au niveau tactique.
        
        Args:
            timeout: Délai d'attente maximum en secondes
            
        Returns:
            Le rapport de statut ou None si timeout
        """
        try:
            response = self.strategic_adapter.request_tactical_status(
                recipient_id="tactical_coordinator",
                timeout=timeout
            )
            
            if response:
                self.logger.info("Rapport de statut tactique reçu")
                return response
            else:
                self.logger.warning("Délai d'attente dépassé pour la demande de statut tactique")
                return None
                
        except Exception as e:
            self.logger.error(f"Erreur lors de la demande de statut tactique: {str(e)}")
            return None
    
    def send_strategic_adjustment(self, adjustment: Dict[str, Any]) -> bool:
        """
        Envoie un ajustement stratégique au niveau tactique.
        
        Args:
            adjustment: L'ajustement à envoyer
            
        Returns:
            True si l'ajustement a été envoyé avec succès, False sinon
        """
        try:
            # Déterminer la priorité en fonction de l'importance de l'ajustement
            priority = MessagePriority.HIGH if adjustment.get("urgent", False) else MessagePriority.NORMAL
            
            # Envoyer l'ajustement via le système de communication
            message_id = self.strategic_adapter.send_directive(
                directive_type="strategic_adjustment",
                content=adjustment,
                recipient_id="tactical_coordinator",
                priority=priority
            )
            
            self.logger.info(f"Ajustement stratégique envoyé avec l'ID {message_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'envoi de l'ajustement stratégique: {str(e)}")
            return False