"""
Module définissant le Moniteur de Progression de l'architecture hiérarchique.

Le Moniteur de Progression est responsable du suivi de l'avancement des tâches,
de l'identification des retards et blocages, et de la génération de rapports
de progression pour le niveau stratégique.
"""

from typing import Dict, List, Any, Optional
import logging
from datetime import datetime

from argumentation_analysis.orchestration.hierarchical.tactical.state import TacticalState


class ProgressMonitor:
    """
    Classe représentant le Moniteur de Progression de l'architecture hiérarchique.
    
    Le Moniteur de Progression est responsable de:
    - Suivre l'avancement des tâches en temps réel
    - Identifier les retards, blocages ou déviations
    - Collecter les métriques de performance
    - Générer des rapports de progression pour le niveau stratégique
    - Déclencher des alertes en cas de problèmes significatifs
    """
    
    def __init__(self, tactical_state: Optional[TacticalState] = None):
        """
        Initialise un nouveau Moniteur de Progression.
        
        Args:
            tactical_state: L'état tactique à utiliser. Si None, un nouvel état est créé.
        """
        self.state = tactical_state if tactical_state else TacticalState()
        self.logger = logging.getLogger(__name__)
        
        # Seuils pour les alertes
        self.thresholds = {
            "task_delay": 0.3,  # Retard relatif par rapport à la durée estimée
            "progress_stagnation": 0.1,  # Progression minimale attendue par unité de temps
            "conflict_ratio": 0.2  # Ratio de conflits par rapport au nombre de tâches
        }
    
    def _log_action(self, action_type: str, description: str) -> None:
        """
        Enregistre une action tactique dans le journal.
        
        Args:
            action_type: Le type d'action
            description: La description de l'action
        """
        action = {
            "timestamp": datetime.now().isoformat(),
            "type": action_type,
            "description": description,
            "agent_id": "progress_monitor"
        }
        
        self.state.log_tactical_action(action)
        self.logger.info(f"Action tactique: {action_type} - {description}")
    
    def update_task_progress(self, task_id: str, progress: float) -> Dict[str, Any]:
        """
        Met à jour la progression d'une tâche et vérifie les anomalies.
        
        Args:
            task_id: Identifiant de la tâche
            progress: Taux de progression (0.0 à 1.0)
            
        Returns:
            Un dictionnaire contenant le statut de la mise à jour et les anomalies détectées
        """
        self.logger.info(f"Mise à jour de la progression de la tâche {task_id}: {progress:.2f}")
        
        # Vérifier la progression précédente
        previous_progress = self.state.task_progress.get(task_id, 0.0)
        
        # Mettre à jour la progression dans l'état
        update_success = self.state.update_task_progress(task_id, progress)
        
        if not update_success:
            return {"status": "error", "message": f"Tâche {task_id} non trouvée"}
        
        # Vérifier les anomalies
        anomalies = self._check_task_anomalies(task_id, previous_progress, progress)
        
        # Journaliser l'action
        self._log_action("Mise à jour de progression", 
                        f"Progression de la tâche {task_id} mise à jour: {previous_progress:.2f} -> {progress:.2f}")
        
        return {
            "status": "success",
            "task_id": task_id,
            "previous_progress": previous_progress,
            "current_progress": progress,
            "anomalies": anomalies
        }
    
    def _check_task_anomalies(self, task_id: str, previous_progress: float, 
                            current_progress: float) -> List[Dict[str, Any]]:
        """
        Vérifie les anomalies dans la progression d'une tâche.
        
        Args:
            task_id: Identifiant de la tâche
            previous_progress: Progression précédente
            current_progress: Progression actuelle
            
        Returns:
            Liste des anomalies détectées
        """
        anomalies = []
        
        # Trouver la tâche dans l'état
        task_obj = None
        for status, tasks in self.state.tasks.items():
            for task in tasks:
                if task["id"] == task_id:
                    task_obj = task
                    break
            if task_obj:
                break
        
        if not task_obj:
            return anomalies
        
        # Vérifier la stagnation
        if current_progress - previous_progress < self.thresholds["progress_stagnation"] and current_progress < 0.9:
            anomalies.append({
                "type": "stagnation",
                "description": f"Progression insuffisante: {current_progress - previous_progress:.2f}",
                "severity": "medium"
            })
        
        # Vérifier la régression
        if current_progress < previous_progress:
            anomalies.append({
                "type": "regression",
                "description": f"Régression de progression: {current_progress - previous_progress:.2f}",
                "severity": "high"
            })
        
        # Vérifier les dépendances bloquantes
        dependencies = self.state.get_task_dependencies(task_id)
        for dep_id in dependencies:
            dep_status = "unknown"
            for status, tasks in self.state.tasks.items():
                for task in tasks:
                    if task["id"] == dep_id:
                        dep_status = status
                        break
                if dep_status != "unknown":
                    break
            
            if dep_status == "failed":
                anomalies.append({
                    "type": "blocked_dependency",
                    "description": f"Dépendance échouée: {dep_id}",
                    "severity": "high",
                    "dependency_id": dep_id
                })
        
        return anomalies
    
    def generate_progress_report(self) -> Dict[str, Any]:
        """
        Génère un rapport complet sur la progression des tâches.
        
        Returns:
            Un rapport détaillé sur la progression
        """
        self.logger.info("Génération d'un rapport de progression")
        
        # Calculer les métriques globales
        total_tasks = sum(len(tasks) for tasks in self.state.tasks.values())
        completed_tasks = len(self.state.tasks["completed"])
        in_progress_tasks = len(self.state.tasks["in_progress"])
        pending_tasks = len(self.state.tasks["pending"])
        failed_tasks = len(self.state.tasks["failed"])
        
        # Calculer la progression globale
        overall_progress = 0.0
        if total_tasks > 0:
            # Pondérer la progression par l'état des tâches et leur progression individuelle
            task_weights = {
                "completed": 1.0,
                "in_progress": 0.5,
                "pending": 0.0,
                "failed": 0.0
            }
            
            weighted_sum = 0.0
            for status, tasks in self.state.tasks.items():
                status_weight = task_weights.get(status, 0.0)
                for task in tasks:
                    task_id = task["id"]
                    if status == "in_progress":
                        # Utiliser la progression spécifique de la tâche
                        progress = self.state.task_progress.get(task_id, 0.0)
                        weighted_sum += progress
                    else:
                        weighted_sum += status_weight
            
            overall_progress = weighted_sum / total_tasks
        
        # Calculer la progression par objectif
        progress_by_objective = {}
        for objective in self.state.assigned_objectives:
            obj_id = objective["id"]
            obj_tasks = []
            
            # Collecter toutes les tâches pour cet objectif
            for status, tasks in self.state.tasks.items():
                for task in tasks:
                    if task.get("objective_id") == obj_id:
                        task_with_status = task.copy()
                        task_with_status["status"] = status
                        task_with_status["progress"] = self.state.task_progress.get(task["id"], 0.0)
                        obj_tasks.append(task_with_status)
            
            # Calculer la progression pour cet objectif
            obj_total_tasks = len(obj_tasks)
            obj_completed_tasks = sum(1 for t in obj_tasks if t["status"] == "completed")
            obj_progress = 0.0
            
            if obj_total_tasks > 0:
                weighted_sum = 0.0
                for task in obj_tasks:
                    if task["status"] == "completed":
                        weighted_sum += 1.0
                    elif task["status"] == "in_progress":
                        weighted_sum += task["progress"]
                
                obj_progress = weighted_sum / obj_total_tasks
            
            progress_by_objective[obj_id] = {
                "total_tasks": obj_total_tasks,
                "completed_tasks": obj_completed_tasks,
                "progress": obj_progress
            }
        
        # Identifier les problèmes et blocages
        issues = []
        
        # Ajouter les conflits non résolus
        for conflict in self.state.identified_conflicts:
            if not conflict.get("resolved", False):
                issues.append({
                    "type": "conflict",
                    "description": conflict.get("description", "Conflit non résolu"),
                    "severity": conflict.get("severity", "medium"),
                    "involved_tasks": conflict.get("involved_tasks", [])
                })
        
        # Ajouter les tâches échouées
        for task in self.state.tasks["failed"]:
            issues.append({
                "type": "task_failure",
                "description": f"Échec de la tâche: {task.get('description', '')}",
                "severity": "high",
                "task_id": task["id"],
                "objective_id": task.get("objective_id")
            })
        
        # Ajouter les tâches bloquées (en attente avec des dépendances non satisfaites)
        for task in self.state.tasks["pending"]:
            dependencies = self.state.get_task_dependencies(task["id"])
            blocked_by_failed = False
            
            for dep_id in dependencies:
                for failed_task in self.state.tasks["failed"]:
                    if failed_task["id"] == dep_id:
                        blocked_by_failed = True
                        break
                if blocked_by_failed:
                    break
            
            if blocked_by_failed:
                issues.append({
                    "type": "blocked_task",
                    "description": f"Tâche bloquée par une dépendance échouée: {task.get('description', '')}",
                    "severity": "high",
                    "task_id": task["id"],
                    "objective_id": task.get("objective_id"),
                    "blocked_by": [dep_id for dep_id in dependencies if any(
                        failed_task["id"] == dep_id for failed_task in self.state.tasks["failed"])]
                })
        
        # Journaliser l'action
        self._log_action("Génération de rapport", 
                        f"Rapport de progression généré avec {len(issues)} problèmes identifiés")
        
        return {
            "timestamp": datetime.now().isoformat(),
            "overall_progress": overall_progress,
            "tasks_summary": {
                "total": total_tasks,
                "completed": completed_tasks,
                "in_progress": in_progress_tasks,
                "pending": pending_tasks,
                "failed": failed_tasks
            },
            "progress_by_objective": progress_by_objective,
            "issues": issues,
            "conflicts": {
                "total": len(self.state.identified_conflicts),
                "resolved": sum(1 for c in self.state.identified_conflicts if c.get("resolved", False))
            },
            "metrics": self.state.tactical_metrics
        }
    
    def detect_critical_issues(self) -> List[Dict[str, Any]]:
        """
        Détecte les problèmes critiques nécessitant une attention immédiate.
        
        Returns:
            Liste des problèmes critiques détectés
        """
        self.logger.info("Détection des problèmes critiques")
        
        critical_issues = []
        
        # Vérifier les tâches bloquées
        for task in self.state.tasks["pending"]:
            dependencies = self.state.get_task_dependencies(task["id"])
            blocked_by_failed = False
            
            for dep_id in dependencies:
                for failed_task in self.state.tasks["failed"]:
                    if failed_task["id"] == dep_id:
                        blocked_by_failed = True
                        break
                if blocked_by_failed:
                    break
            
            if blocked_by_failed:
                critical_issues.append({
                    "type": "blocked_task",
                    "description": f"Tâche bloquée par une dépendance échouée: {task.get('description', '')}",
                    "severity": "critical",
                    "task_id": task["id"],
                    "objective_id": task.get("objective_id"),
                    "blocked_by": [dep_id for dep_id in dependencies if any(
                        failed_task["id"] == dep_id for failed_task in self.state.tasks["failed"])]
                })
        
        # Vérifier les tâches en retard
        for task in self.state.tasks["in_progress"]:
            task_id = task["id"]
            progress = self.state.task_progress.get(task_id, 0.0)
            
            # Si la progression est faible mais la tâche est en cours depuis longtemps
            # (cette logique serait normalement plus sophistiquée avec des timestamps)
            if progress < 0.5 and task.get("estimated_duration") == "short":
                critical_issues.append({
                    "type": "delayed_task",
                    "description": f"Tâche en retard: {task.get('description', '')}",
                    "severity": "high",
                    "task_id": task_id,
                    "objective_id": task.get("objective_id"),
                    "current_progress": progress
                })
        
        # Vérifier le taux d'échec global
        total_tasks = sum(len(tasks) for tasks in self.state.tasks.values())
        failed_tasks = len(self.state.tasks["failed"])
        
        if total_tasks > 0 and failed_tasks / total_tasks > 0.2:
            critical_issues.append({
                "type": "high_failure_rate",
                "description": f"Taux d'échec élevé: {failed_tasks / total_tasks:.2f}",
                "severity": "critical",
                "failed_tasks": failed_tasks,
                "total_tasks": total_tasks
            })
        
        # Journaliser l'action
        self._log_action("Détection de problèmes", 
                        f"Détection de {len(critical_issues)} problèmes critiques")
        
        return critical_issues
    
    def suggest_corrective_actions(self, issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Suggère des actions correctives pour résoudre les problèmes identifiés.
        
        Args:
            issues: Liste des problèmes identifiés
            
        Returns:
            Liste des actions correctives suggérées
        """
        self.logger.info(f"Suggestion d'actions correctives pour {len(issues)} problèmes")
        
        corrective_actions = []
        
        for issue in issues:
            issue_type = issue.get("type")
            
            if issue_type == "blocked_task":
                # Suggérer de réassigner ou de contourner la dépendance
                task_id = issue.get("task_id")
                blocked_by = issue.get("blocked_by", [])
                
                corrective_actions.append({
                    "issue_id": id(issue),
                    "action_type": "reassign_dependency",
                    "description": f"Réassigner la dépendance de la tâche {task_id}",
                    "details": {
                        "task_id": task_id,
                        "blocked_by": blocked_by,
                        "suggestion": "Modifier la tâche pour qu'elle ne dépende plus des tâches échouées"
                    }
                })
            
            elif issue_type == "delayed_task":
                # Suggérer d'allouer plus de ressources ou de simplifier la tâche
                task_id = issue.get("task_id")
                
                corrective_actions.append({
                    "issue_id": id(issue),
                    "action_type": "allocate_resources",
                    "description": f"Allouer plus de ressources à la tâche {task_id}",
                    "details": {
                        "task_id": task_id,
                        "suggestion": "Augmenter la priorité de la tâche ou assigner des agents supplémentaires"
                    }
                })
            
            elif issue_type == "conflict":
                # Suggérer de résoudre le conflit
                involved_tasks = issue.get("involved_tasks", [])
                
                corrective_actions.append({
                    "issue_id": id(issue),
                    "action_type": "resolve_conflict",
                    "description": f"Résoudre le conflit entre les tâches {', '.join(involved_tasks)}",
                    "details": {
                        "involved_tasks": involved_tasks,
                        "suggestion": "Arbitrer entre les résultats contradictoires ou demander une clarification"
                    }
                })
            
            elif issue_type == "high_failure_rate":
                # Suggérer de revoir la stratégie globale
                corrective_actions.append({
                    "issue_id": id(issue),
                    "action_type": "review_strategy",
                    "description": "Revoir la stratégie globale d'analyse",
                    "details": {
                        "suggestion": "Escalader au niveau stratégique pour une révision des objectifs et de l'approche"
                    }
                })
        
        # Journaliser l'action
        self._log_action("Suggestion d'actions", 
                        f"Suggestion de {len(corrective_actions)} actions correctives")
        
        return corrective_actions