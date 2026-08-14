"""
Définit le Coordinateur de Tâches, le cœur de la couche tactique.
"""

from typing import Dict, List, Any, Optional
import logging
from datetime import datetime
import uuid

from argumentation_analysis.orchestration.hierarchical.tactical.state import (
    TacticalState,
)
from argumentation_analysis.paths import RESULTS_DIR, DATA_DIR
from argumentation_analysis.core.communication.middleware import (
    MessageMiddleware,
    create_default_middleware,
)
from argumentation_analysis.core.communication.tactical_adapter import TacticalAdapter
from argumentation_analysis.core.communication.operational_adapter import (
    OperationalAdapter,
)
from argumentation_analysis.core.communication.message import (
    Message,
    MessageType,
    MessagePriority,
    AgentLevel,
)
from argumentation_analysis.core.communication.channel_interface import ChannelType


class TaskCoordinator:
    """
    Traduit les objectifs stratégiques en plans d'action et supervise leur exécution.

    Aussi connu sous le nom de `TacticalManager`, ce coordinateur est le pivot
    entre la stratégie et l'opérationnel. Sa logique principale est :
    1.  **Recevoir les Directives**: S'abonne aux directives de la couche
        stratégique via le middleware.
    2.  **Décomposer**: Lorsqu'un objectif stratégique est reçu, il le
        décompose en une séquence de tâches plus petites et concrètes.
    3.  **Ordonnancer**: Établit les dépendances entre ces tâches pour former
        un plan d'exécution logique.
    4.  **Assigner**: Détermine quel agent opérationnel est le plus apte à
        réaliser chaque tâche et la lui assigne.
    5.  **Superviser**: Traite les résultats des tâches terminées et met à jour
        l'état de l'objectif global.
    6.  **Rapporter**: Génère des rapports de progression et des alertes pour
        la couche stratégique, l'informant de l'avancement et des
        problèmes éventuels.

    Attributes:
        state (TacticalState): L'état interne qui suit l'avancement de toutes
            les tâches, leurs dépendances et leurs résultats.
        logger (logging.Logger): Le logger pour les événements.
        middleware (MessageMiddleware): Le système de communication.
        adapter (TacticalAdapter): Un adaptateur pour simplifier la
            communication tactique.
        agent_capabilities (Dict[str, List[str]]): Un registre local des
            compétences connues des agents opérationnels pour l'assignation.
    """

    def __init__(
        self,
        tactical_state: Optional[TacticalState] = None,
        middleware: Optional[MessageMiddleware] = None,
    ):
        """
        Initialise le `TaskCoordinator`.

        Args:
            tactical_state: L'état tactique à utiliser. Si None, un nouvel
                état est créé.
            middleware: Le middleware de communication. Si None, un nouveau
                middleware est créé.
        """
        self.state = tactical_state or TacticalState()
        self.logger = logging.getLogger(__name__)
        self.middleware = middleware or create_default_middleware()
        self.adapter = TacticalAdapter(
            agent_id="tactical_coordinator", middleware=self.middleware
        )
        self.agent_capabilities = {
            "informal_analyzer": [
                "argument_identification",
                "fallacy_detection",
                "rhetorical_analysis",
            ],
            "logic_analyzer": [
                "formal_logic",
                "validity_checking",
                "consistency_analysis",
            ],
            "extract_processor": ["text_extraction", "preprocessing"],
            "visualizer": ["argument_visualization", "summary_generation"],
        }
        self._subscribe_to_strategic_directives()

    def process_strategic_objectives(
        self, objectives: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Traite une liste d'objectifs stratégiques et génère un plan d'action.

        C'est le point d'entrée principal pour la planification. La méthode orchestre
        la décomposition, la gestion des dépendances et l'assignation initiale
        des tâches pour un ensemble d'objectifs.

        Args:
            objectives: Une liste d'objectifs à décomposer en plan tactique.

        Returns:
            Un résumé de l'opération, incluant le nombre de tâches créées.
        """
        self.logger.info(f"Traitement de {len(objectives)} objectifs stratégiques.")

        all_tasks = []
        for objective in objectives:
            self.state.add_assigned_objective(objective)
            tasks = self._decompose_objective_to_tasks(objective)
            all_tasks.extend(tasks)

        self._establish_task_dependencies(all_tasks)

        for task in all_tasks:
            self.state.add_task(task)
            self.assign_task_to_operational(task)

        self._log_action(
            "Décomposition des objectifs",
            f"{len(objectives)} objectifs décomposés en {len(all_tasks)} tâches.",
        )

        return {
            "tasks_created": len(all_tasks),
            "tasks_by_objective": {
                obj["id"]: [
                    t["id"] for t in all_tasks if t["objective_id"] == obj["id"]
                ]
                for obj in objectives
            },
        }

    def assign_task_to_operational(self, task: Dict[str, Any]) -> None:
        """
        Assigne une tâche à l'agent opérationnel le plus compétent.

        Utilise le registre `agent_capabilities` pour trouver le meilleur agent.
        Envoie ensuite une directive d'assignation via le middleware. Depuis
        #1735 T3, chaque allocation est aussi enregistrée dans l'état tactique
        — qui (``task_assignments``) **et pourquoi**
        (``task_assignments_motivation``) — pour que le forensic de trace du
        mode conversationnel s'applique au palier tactique hiérarchique.

        Args:
            task: La tâche à assigner.
        """
        required_capabilities = task.get("required_capabilities", [])
        recipient_id = self._determine_appropriate_agent(required_capabilities)
        message_priority = self._map_priority_to_enum(task.get("priority", "medium"))
        motivation = self._motivate_allocation(task, recipient_id)

        self.logger.info(
            f"Assignation de la tâche {task.get('id')} à l'agent {recipient_id} "
            f"— {motivation[:80]}"
        )
        self.adapter.assign_task(
            task_type="operational_task",
            parameters=task,
            recipient_id=recipient_id,
            priority=message_priority,
            requires_ack=True,
        )
        # #1735 T3: la désignation (qui + pourquoi) est écrite dans l'état
        # tactique. ``assign_task`` réanime le champ existant — le palier
        # enregistre désormais l'allocation réelle, pas seulement la directive
        # middleware. La motivation n'est tracée que si la tâche a bien été
        # assignée (cohérence : pas de motivation orpheline).
        if self.state.assign_task(task["id"], recipient_id):
            self.state.record_allocation_motivation(task["id"], motivation)

    def _motivate_allocation(self, task: Dict[str, Any], recipient_id: str) -> str:
        """Construit le *pourquoi* de l'allocation de ``task`` à ``recipient_id``.

        #1735 T3. Le palier tactique est déterministe : sa « motivation » est
        la règle de décision elle-même — la couverture de capacités qui a fait
        gagner cet agent au scoring — pas une narration. Anti-pendule #1732 :
        on refuse le template vide « tâche X → agent Y » (zéro information) ;
        le texte documente le score réellement appliqué.
        """
        required = task.get("required_capabilities", [])
        agent_caps = self.agent_capabilities.get(recipient_id, [])
        covered = [cap for cap in required if cap in agent_caps]
        if not required:
            return (
                f"Aucune capacité requise (tâche générique) — "
                f"{recipient_id} retenu par le fallback de décomposition"
            )
        return (
            f"{recipient_id} couvre {len(covered)}/{len(required)} "
            f"capacité(s) requise(s) de « {task.get('description', '')} » : "
            f"{', '.join(covered) if covered else 'aucune'}"
        )

    def handle_task_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Traite le résultat d'une tâche terminé par un agent opérationnel.

        Met à jour l'état de la tâche correspondante, stocke le résultat, et
        vérifie si la complétion de cette tâche permet de faire avancer ou de
        terminer un objectif plus large. Si un objectif est terminé, un rapport
        est envoyé à la couche stratégique.

        Args:
            result: Le dictionnaire de résultat envoyé par un agent.

        Returns:
            Une confirmation du traitement du résultat.
        """
        tactical_task_id = result.get("tactical_task_id")
        if not tactical_task_id:
            self.logger.warning(f"Résultat reçu sans ID de tâche tactique: {result}")
            return {"status": "error", "message": "ID de tâche manquant"}

        self.logger.info(f"Traitement du résultat pour la tâche {tactical_task_id}.")

        # Mettre à jour l'état
        status = result.get("completion_status", "failed")
        self.state.update_task_status(tactical_task_id, status)
        self.state.add_intermediate_result(tactical_task_id, result)

        # Vérifier si l'objectif parent est terminé
        objective_id = self.state.get_objective_for_task(tactical_task_id)
        if objective_id and self.state.are_all_tasks_for_objective_done(objective_id):
            self.logger.info(
                f"Objectif {objective_id} terminé. Envoi du rapport au stratégique."
            )
            self.adapter.send_report(
                report_type="objective_completion",
                content={
                    "objective_id": objective_id,
                    "status": "completed",
                    RESULTS_DIR: self.state.get_objective_results(objective_id),
                },
                recipient_id="strategic_manager",
                priority=MessagePriority.HIGH,
            )

        self._log_action(
            "Réception de résultat",
            f"Résultat pour la tâche {tactical_task_id} traité.",
        )
        return {"status": "success"}

    def generate_status_report(self) -> Dict[str, Any]:
        """
        Génère et envoie un rapport de statut complet à la couche stratégique.

        Ce rapport synthétise la progression globale, le statut des tâches,
        l'avancement par objectif, et les problèmes en cours.

        Returns:
            Le rapport de statut qui a été envoyé.
        """
        self.logger.info(
            "Génération d'un rapport de statut pour la couche stratégique."
        )
        report = self.state.get_status_summary()
        self.adapter.send_report(
            report_type="status_update",
            content=report,
            recipient_id="strategic_manager",
            priority=MessagePriority.NORMAL,
        )
        return report

    # ... Les méthodes privées restent inchangées comme détails d'implémentation ...
    def _log_action(self, action_type: str, description: str) -> None:
        action = {
            "timestamp": datetime.now().isoformat(),
            "type": action_type,
            "description": description,
        }
        self.state.log_tactical_action(action)
        self.logger.info(f"Action Tactique: {action_type} - {description}")

    def _subscribe_to_strategic_directives(self) -> None:
        # #1555 (Track C2, Epic #1500) — le handler est désormais enregistré
        # pour de vrai (plus de commentaire + log menteur). La signature est
        # synchrone : ``Topic.publish_message`` appelle le callback sans
        # ``await`` (pub_sub.py:121), un ``async def`` n'aurait jamais tourné.
        def handle_directive(message: Message) -> None:
            # Le publieur (``StrategicAdapter.broadcast_objective``) écrit la
            # clé ``objective_type`` (pas ``directive_type`` — celle-là vient
            # du point-à-point ``issue_directive``, un autre chemin).
            objective_type = message.content.get("objective_type")
            self.logger.info(f"Directive stratégique reçue : {objective_type}")
            if objective_type == "strategic_decision":
                # Le payload (decision_type/conclusion/evaluation) est niché
                # sous la clé ``DATA_DIR`` (un Path) — lu de la même façon
                # qu'écrit par le publieur (strategic_adapter.py:122). Le type
                # ignore reflète ce couplage : ``content`` est typé
                # ``Dict[str, Any]`` mais le publieur utilise le Path comme
                # clé (défaut latent pré-existant, hors périmètre #1555).
                payload = message.content.get(DATA_DIR, {}) or {}  # type: ignore[call-overload]
                self._log_action(
                    "strategic_decision_received",
                    (
                        f"decision_type={payload.get('decision_type', 'unknown')}; "
                        f"conclusion={payload.get('conclusion', '')}"
                    ),
                )

        self._directive_subscription_id = self.adapter.subscribe_to_directives(
            handle_directive
        )

    def _determine_appropriate_agent(self, required_capabilities: List[str]) -> str:
        # Toujours une chaîne : le fallback couvre cap inconnue ET vide.
        agent_scores = {}
        for cap in required_capabilities:
            for agent, agent_caps in self.agent_capabilities.items():
                if cap in agent_caps:
                    agent_scores[agent] = agent_scores.get(agent, 0) + 1

        if not agent_scores:
            return "default_operational_agent"  # Fallback

        return max(agent_scores, key=agent_scores.get)

    def _decompose_objective_to_tasks(
        self, objective: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        tasks = []
        obj_id = objective["id"]
        obj_description = objective["description"].lower()
        base_task_id = f"task-{obj_id}-"

        if "identifier" in obj_description and "arguments" in obj_description:
            tasks.append(
                {
                    "id": f"{base_task_id}1",
                    "description": "Extraire segments pertinents",
                    "objective_id": obj_id,
                    "required_capabilities": ["text_extraction"],
                }
            )
            tasks.append(
                {
                    "id": f"{base_task_id}2",
                    "description": "Identifier prémisses et conclusions",
                    "objective_id": obj_id,
                    "required_capabilities": ["argument_identification"],
                }
            )
        elif "détecter" in obj_description and "sophisme" in obj_description:
            tasks.append(
                {
                    "id": f"{base_task_id}1",
                    "description": "Analyser pour sophismes",
                    "objective_id": obj_id,
                    "required_capabilities": ["fallacy_detection"],
                }
            )
        else:
            tasks.append(
                {
                    "id": f"{base_task_id}1",
                    "description": f"Tâche générique pour {obj_description}",
                    "objective_id": obj_id,
                    "required_capabilities": [],
                }
            )  # Fallback

        for task in tasks:
            task["priority"] = objective.get("priority", "medium")

        return tasks

    def _establish_task_dependencies(self, tasks: List[Dict[str, Any]]) -> None:
        tasks_by_objective = {}
        for task in tasks:
            tasks_by_objective.setdefault(task["objective_id"], []).append(task)

        for obj_id, obj_tasks in tasks_by_objective.items():
            sorted_tasks = sorted(obj_tasks, key=lambda t: t["id"])
            for i in range(len(sorted_tasks) - 1):
                self.state.add_task_dependency(
                    sorted_tasks[i]["id"], sorted_tasks[i + 1]["id"]
                )

    def _apply_strategic_adjustments(self, adjustments: Dict[str, Any]) -> None:
        self.logger.info(f"Application des ajustements stratégiques : {adjustments}")
        # Logique pour modifier les tâches, priorités, etc.
        # ...
        self._log_action(
            "Application d'ajustement", f"Ajustements {adjustments.keys()} appliqués."
        )

    def _map_priority_to_enum(self, priority: str) -> MessagePriority:
        return {
            "high": MessagePriority.HIGH,
            "medium": MessagePriority.NORMAL,
            "low": MessagePriority.LOW,
        }.get(priority.lower(), MessagePriority.NORMAL)


# Alias pour compatibilité
TacticalCoordinator = TaskCoordinator
