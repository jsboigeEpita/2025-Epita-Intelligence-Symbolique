"""
Module définissant l'état tactique de l'architecture hiérarchique.

L'état tactique contient les informations pertinentes pour le niveau tactique,
telles que les objectifs assignés, les tâches décomposées, les assignations,
la progression, les résultats intermédiaires, etc.
"""

from typing import Dict, List, Any, Optional
import json


class TacticalState:
    """
    Classe représentant l'état du niveau tactique de l'architecture hiérarchique.

    Cette classe encapsule toutes les informations nécessaires pour la coordination
    et le suivi des tâches au niveau tactique de l'analyse rhétorique.
    """

    def __init__(self):
        """Initialise un nouvel état tactique avec des valeurs par défaut."""
        # Objectifs reçus du niveau stratégique
        self.assigned_objectives: List[Dict[str, Any]] = []

        # Tâches décomposées
        self.tasks: Dict[str, List[Dict[str, Any]]] = {
            "pending": [],
            "in_progress": [],
            "completed": [],
            "failed": [],
        }

        # Assignations des tâches
        self.task_assignments: Dict[str, str] = {}  # task_id -> agent_id

        # Dépendances entre tâches
        self.task_dependencies: Dict[
            str, List[str]
        ] = {}  # task_id -> [dependent_task_ids]

        # Progression des tâches
        self.task_progress: Dict[
            str, float
        ] = {}  # task_id -> completion_rate (0.0 to 1.0)

        # Résultats intermédiaires
        self.intermediate_results: Dict[str, Any] = {}

        # Résultats des analyses rhétoriques améliorées
        self.rhetorical_analysis_results: Dict[str, Any] = {
            "complex_fallacy_analyses": {},
            "contextual_fallacy_analyses": {},
            "fallacy_severity_evaluations": {},
            "argument_structure_visualizations": {},
            "argument_coherence_evaluations": {},
            "semantic_argument_analyses": {},
            "contextual_fallacy_detections": {},
        }

        # Conflits identifiés
        self.identified_conflicts: List[Dict[str, Any]] = []

        # Métriques tactiques
        self.tactical_metrics: Dict[str, Any] = {
            "task_completion_rate": 0.0,
            "agent_utilization": {},
            "conflict_resolution_rate": 0.0,
        }

        # Journal des actions tactiques
        self.tactical_actions_log: List[Dict[str, Any]] = []

    def add_assigned_objective(self, objective: Dict[str, Any]) -> None:
        """
        Ajoute un objectif assigné par le niveau stratégique.

        Args:
            objective: Dictionnaire décrivant l'objectif avec au moins les clés
                      'id', 'description' et 'priority'
        """
        self.assigned_objectives.append(objective)

    def add_task(self, task: Dict[str, Any], status: str = "pending") -> None:
        """
        Ajoute une tâche à l'état tactique.

        Args:
            task: Dictionnaire décrivant la tâche avec au moins les clés
                 'id', 'description', 'objective_id' et 'estimated_duration'
            status: Statut initial de la tâche ('pending', 'in_progress', 'completed', 'failed')
        """
        if status in self.tasks:
            self.tasks[status].append(task)

    def update_task_status(self, task_id: str, new_status: str) -> bool:
        """
        Met à jour le statut d'une tâche.

        Args:
            task_id: Identifiant de la tâche
            new_status: Nouveau statut ('pending', 'in_progress', 'completed', 'failed')

        Returns:
            True si la mise à jour a réussi, False sinon
        """
        if new_status not in self.tasks:
            return False

        # Trouver la tâche dans les listes de statut
        task_found = False
        task_to_move = None

        for status, tasks in self.tasks.items():
            for i, task in enumerate(tasks):
                if task["id"] == task_id:
                    task_found = True
                    task_to_move = task
                    self.tasks[status].pop(i)
                    break
            if task_found:
                break

        if task_found and task_to_move:
            self.tasks[new_status].append(task_to_move)
            return True

        return False

    def assign_task(self, task_id: str, agent_id: str) -> bool:
        """
        Assigne une tâche à un agent.

        Args:
            task_id: Identifiant de la tâche
            agent_id: Identifiant de l'agent

        Returns:
            True si l'assignation a réussi, False sinon
        """
        # Vérifier que la tâche existe
        task_exists = False
        for status, tasks in self.tasks.items():
            for task in tasks:
                if task["id"] == task_id:
                    task_exists = True
                    break
            if task_exists:
                break

        if not task_exists:
            return False

        self.task_assignments[task_id] = agent_id
        return True

    def add_task_dependency(self, task_id: str, dependent_task_id: str) -> bool:
        """
        Ajoute une dépendance entre deux tâches.

        Args:
            task_id: Identifiant de la tâche
            dependent_task_id: Identifiant de la tâche dépendante

        Returns:
            True si l'ajout a réussi, False sinon
        """
        # Vérifier que les deux tâches existent
        task_exists = False
        dependent_task_exists = False

        for status, tasks in self.tasks.items():
            for task in tasks:
                if task["id"] == task_id:
                    task_exists = True
                if task["id"] == dependent_task_id:
                    dependent_task_exists = True
                if task_exists and dependent_task_exists:
                    break
            if task_exists and dependent_task_exists:
                break

        if not task_exists or not dependent_task_exists:
            return False

        if task_id not in self.task_dependencies:
            self.task_dependencies[task_id] = []

        if dependent_task_id not in self.task_dependencies[task_id]:
            self.task_dependencies[task_id].append(dependent_task_id)

        return True

    def update_task_progress(self, task_id: str, progress: float) -> bool:
        """
        Met à jour la progression d'une tâche.

        Args:
            task_id: Identifiant de la tâche
            progress: Taux de progression (0.0 à 1.0)

        Returns:
            True si la mise à jour a réussi, False sinon
        """
        # Vérifier que la tâche existe
        task_exists = False
        for status, tasks in self.tasks.items():
            for task in tasks:
                if task["id"] == task_id:
                    task_exists = True
                    break
            if task_exists:
                break

        if not task_exists:
            return False

        self.task_progress[task_id] = max(0.0, min(1.0, progress))

        # Mettre à jour le statut si nécessaire
        if progress >= 1.0 and task_id in self.task_assignments:
            for status, tasks in self.tasks.items():
                for task in tasks:
                    if task["id"] == task_id and status != "completed":
                        self.update_task_status(task_id, "completed")
                        break

        # Mettre à jour les métriques globales
        self._update_task_completion_rate()

        return True

    def add_intermediate_result(self, task_id: str, result: Any) -> bool:
        """
        Ajoute un résultat intermédiaire pour une tâche.

        Args:
            task_id: Identifiant de la tâche
            result: Résultat intermédiaire

        Returns:
            True si l'ajout a réussi, False sinon
        """
        # Vérifier que la tâche existe
        task_exists = False
        for status, tasks in self.tasks.items():
            for task in tasks:
                if task["id"] == task_id:
                    task_exists = True
                    break
            if task_exists:
                break

        if not task_exists:
            return False

        self.intermediate_results[task_id] = result
        return True

    def add_rhetorical_analysis_result(
        self, task_id: str, result_type: str, result: Any
    ) -> bool:
        """
        Ajoute un résultat d'analyse rhétorique améliorée.

        Args:
            task_id: Identifiant de la tâche
            result_type: Type de résultat d'analyse rhétorique
            result: Résultat de l'analyse

        Returns:
            True si l'ajout a réussi, False sinon
        """
        # Vérifier que la tâche existe
        task_exists = False
        for status, tasks in self.tasks.items():
            for task in tasks:
                if task["id"] == task_id:
                    task_exists = True
                    break
            if task_exists:
                break

        if not task_exists:
            return False

        # Vérifier que le type de résultat est valide
        if result_type not in self.rhetorical_analysis_results:
            return False

        self.rhetorical_analysis_results[result_type][task_id] = result
        return True

    def get_rhetorical_analysis_result(
        self, result_type: str, task_id: Optional[str] = None
    ) -> Any:
        """
        Récupère un résultat d'analyse rhétorique améliorée.

        Args:
            result_type: Type de résultat d'analyse rhétorique
            task_id: Identifiant de la tâche (optionnel)

        Returns:
            Le résultat de l'analyse ou None si non trouvé
        """
        if result_type not in self.rhetorical_analysis_results:
            return None

        if task_id:
            return self.rhetorical_analysis_results[result_type].get(task_id)

        return self.rhetorical_analysis_results[result_type]

    def add_conflict(self, conflict: Dict[str, Any]) -> None:
        """
        Ajoute un conflit identifié.

        Args:
            conflict: Dictionnaire décrivant le conflit avec au moins les clés
                     'id', 'description', 'involved_tasks' et 'severity'
        """
        self.identified_conflicts.append(conflict)

    def resolve_conflict(self, conflict_id: str, resolution: Dict[str, Any]) -> bool:
        """
        Marque un conflit comme résolu.

        Args:
            conflict_id: Identifiant du conflit
            resolution: Dictionnaire décrivant la résolution

        Returns:
            True si la résolution a réussi, False sinon
        """
        for i, conflict in enumerate(self.identified_conflicts):
            if conflict["id"] == conflict_id:
                self.identified_conflicts[i]["resolved"] = True
                self.identified_conflicts[i]["resolution"] = resolution

                # Mettre à jour le taux de résolution des conflits
                self._update_conflict_resolution_rate()

                return True

        return False

    def update_agent_utilization(self, agent_id: str, utilization: float) -> None:
        """
        Met à jour l'utilisation d'un agent.

        Args:
            agent_id: Identifiant de l'agent
            utilization: Taux d'utilisation (0.0 à 1.0)
        """
        self.tactical_metrics["agent_utilization"][agent_id] = max(
            0.0, min(1.0, utilization)
        )

    def log_tactical_action(self, action: Dict[str, Any]) -> None:
        """
        Enregistre une action tactique dans le journal.

        Args:
            action: Dictionnaire décrivant l'action avec au moins les clés
                   'timestamp', 'type', 'description' et 'agent_id'
        """
        self.tactical_actions_log.append(action)

    def _update_task_completion_rate(self) -> None:
        """Met à jour le taux global de complétion des tâches."""
        total_tasks = sum(len(tasks) for tasks in self.tasks.values())
        if total_tasks == 0:
            self.tactical_metrics["task_completion_rate"] = 0.0
            return

        completed_tasks = len(self.tasks["completed"])
        self.tactical_metrics["task_completion_rate"] = completed_tasks / total_tasks

    def _update_conflict_resolution_rate(self) -> None:
        """Met à jour le taux de résolution des conflits."""
        if not self.identified_conflicts:
            self.tactical_metrics["conflict_resolution_rate"] = 1.0
            return

        resolved_conflicts = sum(
            1
            for conflict in self.identified_conflicts
            if conflict.get("resolved", False)
        )

        self.tactical_metrics["conflict_resolution_rate"] = resolved_conflicts / len(
            self.identified_conflicts
        )

    def get_pending_tasks(self) -> List[Dict[str, Any]]:
        """
        Retourne la liste des tâches en attente.

        Returns:
            Liste des tâches en attente
        """
        return self.tasks["pending"]

    def get_tasks_for_agent(self, agent_id: str) -> List[Dict[str, Any]]:
        """
        Retourne la liste des tâches assignées à un agent.

        Args:
            agent_id: Identifiant de l'agent

        Returns:
            Liste des tâches assignées à l'agent
        """
        agent_tasks = []

        for task_id, assigned_agent in self.task_assignments.items():
            if assigned_agent == agent_id:
                # Trouver la tâche correspondante
                for status, tasks in self.tasks.items():
                    for task in tasks:
                        if task["id"] == task_id:
                            task_copy = task.copy()
                            task_copy["status"] = status
                            task_copy["progress"] = self.task_progress.get(task_id, 0.0)
                            agent_tasks.append(task_copy)
                            break

        return agent_tasks

    def get_task_dependencies(self, task_id: str) -> List[str]:
        """
        Retourne la liste des tâches dont dépend une tâche donnée.

        Args:
            task_id: Identifiant de la tâche

        Returns:
            Liste des identifiants des tâches dépendantes
        """
        return self.task_dependencies.get(task_id, [])

    def get_snapshot(self) -> Dict[str, Any]:
        """
        Retourne un instantané de l'état tactique actuel.

        Returns:
            Un dictionnaire représentant l'état tactique actuel
        """
        return {
            "objectives_count": len(self.assigned_objectives),
            "tasks": {status: len(tasks) for status, tasks in self.tasks.items()},
            "task_assignments_count": len(self.task_assignments),
            "conflicts": {
                "total": len(self.identified_conflicts),
                "resolved": sum(
                    1
                    for conflict in self.identified_conflicts
                    if conflict.get("resolved", False)
                ),
            },
            "metrics": self.tactical_metrics,
        }

    def to_json(self) -> str:
        """
        Convertit l'état tactique en chaîne JSON.

        Returns:
            Une représentation JSON de l'état tactique
        """
        state_dict = {
            "assigned_objectives": self.assigned_objectives,
            "tasks": self.tasks,
            "task_assignments": self.task_assignments,
            "task_dependencies": self.task_dependencies,
            "task_progress": self.task_progress,
            "intermediate_results": {
                k: str(v)
                if not isinstance(v, (dict, list, str, int, float, bool, type(None)))
                else v
                for k, v in self.intermediate_results.items()
            },
            "identified_conflicts": self.identified_conflicts,
            "tactical_metrics": self.tactical_metrics,
            "tactical_actions_log": self.tactical_actions_log,
            "rhetorical_analysis_results": self.rhetorical_analysis_results,
        }
        return json.dumps(state_dict, indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "TacticalState":
        """
        Crée une instance d'état tactique à partir d'une chaîne JSON.

        Args:
            json_str: La chaîne JSON représentant l'état

        Returns:
            Une nouvelle instance de TacticalState
        """
        state_dict = json.loads(json_str)
        state = cls()

        # Restaurer les propriétés à partir du dictionnaire
        if "assigned_objectives" in state_dict:
            state.assigned_objectives = state_dict["assigned_objectives"]

        if "tasks" in state_dict:
            state.tasks = state_dict["tasks"]

        if "task_assignments" in state_dict:
            state.task_assignments = state_dict["task_assignments"]

        if "task_dependencies" in state_dict:
            state.task_dependencies = state_dict["task_dependencies"]

        if "task_progress" in state_dict:
            state.task_progress = state_dict["task_progress"]

        if "intermediate_results" in state_dict:
            state.intermediate_results = state_dict["intermediate_results"]

        if "rhetorical_analysis_results" in state_dict:
            state.rhetorical_analysis_results = state_dict[
                "rhetorical_analysis_results"
            ]

        if "identified_conflicts" in state_dict:
            state.identified_conflicts = state_dict["identified_conflicts"]

        if "tactical_metrics" in state_dict:
            state.tactical_metrics = state_dict["tactical_metrics"]

        if "tactical_actions_log" in state_dict:
            state.tactical_actions_log = state_dict["tactical_actions_log"]

        return state

    def get_objective_results(self, objective_id: str) -> Dict[str, Any]:
        """
        Récupère les résultats associés à un objectif.

        Args:
            objective_id: Identifiant de l'objectif

        Returns:
            Un dictionnaire contenant les résultats de l'objectif
        """
        results = {}

        # Collecter les résultats intermédiaires des tâches associées à cet objectif
        for task_id, result in self.intermediate_results.items():
            # Trouver la tâche correspondante
            task_found = False
            task_obj = None

            for status, tasks in self.tasks.items():
                for task in tasks:
                    if (
                        task["id"] == task_id
                        and task.get("objective_id") == objective_id
                    ):
                        task_found = True
                        task_obj = task
                        break
                if task_found:
                    break

            if task_found and task_obj:
                if "results" not in results:
                    results["results"] = []

                # Ajouter le résultat avec des métadonnées de la tâche
                result_with_metadata = {
                    "task_id": task_id,
                    "task_description": task_obj.get("description", ""),
                    "result": result,
                }
                results["results"].append(result_with_metadata)

        return results
