"""
Module définissant l'interface commune pour les agents opérationnels.

Cette interface définit les méthodes que tous les agents opérationnels
doivent implémenter pour fonctionner dans l'architecture hiérarchique.
"""

from typing import Dict, List, Any, Optional
from abc import ABC, abstractmethod
import logging

from argumentation_analysis.orchestration.hierarchical.operational.state import (
    OperationalState,
)
from argumentation_analysis.core.communication import (
    MessageMiddleware,
    create_default_middleware,
    OperationalAdapter,
)


class OperationalAgent(ABC):
    """
    Interface abstraite pour les agents opérationnels.

    Tous les agents opérationnels doivent implémenter cette interface
    pour être compatibles avec l'architecture hiérarchique à trois niveaux.
    """

    def __init__(
        self,
        name: str,
        operational_state: Optional[OperationalState] = None,
        middleware: Optional[MessageMiddleware] = None,
    ):
        """
        Initialise un nouvel agent opérationnel.

        Args:
            name: Nom de l'agent
            operational_state: État opérationnel à utiliser. Si None, un nouvel état est créé.
            middleware: Le middleware de communication à utiliser. Si None, un nouveau middleware est créé.
        """
        self.name = name
        self.operational_state = (
            operational_state if operational_state else OperationalState()
        )
        self.logger = logging.getLogger(f"OperationalAgent.{name}")

        # Initialiser le middleware de communication
        self.middleware = middleware if middleware else create_default_middleware()

        # Créer l'adaptateur opérationnel
        self.adapter = OperationalAdapter(agent_id=name, middleware=self.middleware)

    # #2415 : l'abonnement hiérarchique aux tâches (_subscribe_to_tasks) et
    # son traitement (_process_task_async) sont retirés : circuit mort de bout
    # en bout. L'émetteur réel (TaskCoordinator.assign_task_to_operational)
    # adressait des noms qu'aucun agent ne portait, sur un middleware qu'aucun
    # agent ne partageait ; même livré, le traitement appelait des méthodes
    # fantômes d'OperationalAdapter (send_status_update, send_task_result,
    # request_tactical_guidance, share_operational_data) ; et le consommateur
    # du résultat n'a jamais existé (handle_task_result : zéro appelant). Les
    # chemins d'exécution réels contournent le middleware : M3 par le seam
    # operational_executor, le ServiceManager par la file + Future de
    # OperationalManager._worker.

    @abstractmethod
    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Traite une tâche opérationnelle.

        Cette méthode doit être implémentée par tous les agents opérationnels.
        Elle reçoit une tâche opérationnelle et retourne un résultat.

        Args:
            task: La tâche opérationnelle à traiter

        Returns:
            Le résultat du traitement de la tâche
        """
        pass

    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """
        Retourne les capacités de l'agent.

        Cette méthode doit être implémentée par tous les agents opérationnels.
        Elle retourne la liste des capacités que l'agent peut fournir.

        Returns:
            Liste des capacités de l'agent
        """
        pass

    @abstractmethod
    def can_process_task(self, task: Dict[str, Any]) -> bool:
        """
        Vérifie si l'agent peut traiter une tâche donnée.

        Cette méthode doit être implémentée par tous les agents opérationnels.
        Elle vérifie si l'agent a les capacités nécessaires pour traiter la tâche.

        Args:
            task: La tâche à vérifier

        Returns:
            True si l'agent peut traiter la tâche, False sinon
        """
        pass

    def register_task(self, task: Dict[str, Any]) -> str:
        """
        Enregistre une tâche dans l'état opérationnel.

        Args:
            task: La tâche à enregistrer

        Returns:
            L'identifiant de la tâche
        """
        return self.operational_state.add_task(task)

    def update_task_status(
        self, task_id: str, status: str, details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Met à jour le statut d'une tâche.

        Args:
            task_id: L'identifiant de la tâche
            status: Le nouveau statut
            details: Détails supplémentaires sur le changement de statut

        Returns:
            True si la mise à jour a réussi, False sinon
        """
        return self.operational_state.update_task_status(task_id, status, details)

    def add_result(self, result_type: str, result_data: Dict[str, Any]) -> str:
        """
        Ajoute un résultat d'analyse à l'état opérationnel.

        Args:
            result_type: Le type de résultat
            result_data: Les données du résultat

        Returns:
            L'identifiant du résultat
        """
        return self.operational_state.add_analysis_result(result_type, result_data)

    def add_issue(self, issue: Dict[str, Any]) -> str:
        """
        Ajoute un problème à l'état opérationnel.

        Args:
            issue: Le problème à ajouter

        Returns:
            L'identifiant du problème
        """
        return self.operational_state.add_issue(issue)

    def update_metrics(self, task_id: str, metrics: Dict[str, Any]) -> bool:
        """
        Met à jour les métriques opérationnelles pour une tâche.

        Args:
            task_id: L'identifiant de la tâche
            metrics: Les métriques à mettre à jour

        Returns:
            True si la mise à jour a réussi, False sinon
        """
        return self.operational_state.update_metrics(task_id, metrics)

    def log_action(self, action: str, details: Dict[str, Any]) -> None:
        """
        Enregistre une action dans le journal des actions opérationnelles.

        Args:
            action: L'action effectuée
            details: Les détails de l'action
        """
        self.operational_state.log_action(action, details)

    def format_result(
        self,
        task: Dict[str, Any],
        results: List[Dict[str, Any]],
        metrics: Dict[str, Any],
        issues: List[Dict[str, Any]],
        task_id_to_report: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Formate le résultat d'une tâche pour le niveau tactique.

        Seule définition de l'arbre (#2345). Les quatre adaptateurs en
        portaient chacun une copie, qui avait dérivé de celle-ci : les copies
        vidaient la clé ``type`` des résultats de l'appelant (``pop``) et
        rangeaient un résultat sans type sous ``"unknown"``, là où cette
        version le jetait sans trace. Ce sont les copies qui tournaient en
        production : leur comportement est conservé, sans la mutation.

        Args:
            task: La tâche traitée
            results: Les résultats de l'analyse, chacun sous sa clé ``type``
            metrics: Les métriques d'exécution
            issues: Les problèmes rencontrés
            task_id_to_report: Identifiant rapporté à la place de ``task["id"]``

        Returns:
            Le résultat formaté
        """
        final_task_id = task_id_to_report or task.get("id")

        # Regrouper par type sur des copies : les résultats de l'appelant
        # restent intacts.
        outputs: Dict[Any, List[Dict[str, Any]]] = {}
        for result in results:
            result_copy = dict(result)
            result_type = result_copy.pop("type", "unknown")
            outputs.setdefault(result_type, []).append(result_copy)

        return {
            "id": f"result-{final_task_id}",
            "task_id": final_task_id,
            "tactical_task_id": task.get("tactical_task_id"),
            "status": "completed" if not issues else "completed_with_issues",
            "outputs": outputs,
            "metrics": metrics,
            "issues": issues,
        }
