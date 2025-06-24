"""
Définit le Gestionnaire Opérationnel, responsable de l'exécution des tâches.

Ce module fournit la classe `OperationalManager`, le "chef d'atelier" qui
reçoit les commandes de la couche tactique et les fait exécuter par des
agents spécialisés.
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Union, Callable
from datetime import datetime
import uuid
import semantic_kernel as sk

from argumentation_analysis.orchestration.hierarchical.operational.state import OperationalState
from argumentation_analysis.orchestration.hierarchical.operational.agent_registry import OperationalAgentRegistry
from argumentation_analysis.core.bootstrap import ProjectContext
from argumentation_analysis.paths import RESULTS_DIR
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from argumentation_analysis.orchestration.hierarchical.interfaces.tactical_operational import TacticalOperationalInterface
from argumentation_analysis.core.communication.middleware import MessageMiddleware
from argumentation_analysis.core.communication.operational_adapter import OperationalAdapter
from argumentation_analysis.core.communication.message import Message, MessageType, MessagePriority, AgentLevel
from argumentation_analysis.core.communication.channel_interface import ChannelType


class OperationalManager:
    """
    Gère le cycle de vie de l'exécution des tâches par les agents spécialisés.

    La logique de ce manager est asynchrone et repose sur un système de files
    d'attente (`asyncio.Queue`) pour découpler la réception des tâches de leur
    exécution.
    1.  **Réception**: S'abonne aux directives de la couche tactique et place
        les nouvelles tâches dans une `task_queue`.
    2.  **Worker**: Une boucle `_worker` asynchrone tourne en arrière-plan,
        prenant les tâches de la file une par une.
    3.  **Délégation**: Pour chaque tâche, le worker consulte le
        `OperationalAgentRegistry` pour trouver l'agent le plus compétent.
    4.  **Exécution**: L'agent sélectionné exécute la tâche.
    5.  **Rapport**: Le résultat est placé dans une `result_queue` et renvoyé
        à la couche tactique via le middleware.

    Attributes:
        operational_state (OperationalState): L'état interne qui suit le statut
            de chaque tâche en cours.
        agent_registry (OperationalAgentRegistry): Le registre qui contient et
            gère les instances d'agents disponibles.
        logger (logging.Logger): Le logger.
        task_queue (asyncio.Queue): La file d'attente pour les tâches entrantes.
        result_queue (asyncio.Queue): La file d'attente pour les résultats sortants.
        adapter (OperationalAdapter): L'adaptateur pour la communication.
    """

    def __init__(self,
                 operational_state: Optional[OperationalState] = None,
                 tactical_operational_interface: Optional['TacticalOperationalInterface'] = None,
                 middleware: Optional[MessageMiddleware] = None,
                 project_context: Optional[ProjectContext] = None,
                 kernel: Optional[sk.Kernel] = None):
        """
        Initialise le `OperationalManager`.

        Args:
            operational_state: L'état pour stocker le statut des tâches.
            tactical_operational_interface: L'interface de communication.
            middleware: Le middleware de communication.
            project_context: Le contexte global du projet.
            kernel: Le kernel Semantic Kernel (pour tests et injection de dépendances).
        """
        self.operational_state = operational_state or OperationalState()
        self.tactical_operational_interface = tactical_operational_interface
        self.project_context = project_context
        
        # Le kernel peut être passé directement (tests) ou via le project_context (prod)
        kernel_to_use = kernel or (project_context.kernel if project_context else None)
        llm_service_id_to_use = project_context.llm_service_id if project_context else None

        self.agent_registry = OperationalAgentRegistry(
            operational_state=self.operational_state,
            kernel=kernel_to_use,
            llm_service_id=llm_service_id_to_use,
            project_context=project_context
        )
        self.logger = logging.getLogger(__name__)
        self.task_queue = asyncio.Queue()
        self.result_queue = asyncio.Queue()
        self.running = False
        self.worker_task = None
        self.middleware = middleware or MessageMiddleware()
        self.adapter = OperationalAdapter(agent_id="operational_manager", middleware=self.middleware)
        self._subscribe_to_messages()

    async def start(self) -> None:
        """Démarre le worker asynchrone pour traiter les tâches en arrière-plan."""
        if self.running:
            self.logger.warning("Le gestionnaire opérationnel est déjà en cours.")
            return
        
        self.running = True
        self.worker_task = asyncio.create_task(self._worker())
        self.logger.info("Gestionnaire opérationnel démarré.")

    async def stop(self) -> None:
        """Arrête proprement le worker asynchrone."""
        if not self.running:
            self.logger.warning("Le gestionnaire opérationnel n'est pas en cours.")
            return
        
        self.running = False
        if self.worker_task:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass
        self.logger.info("Gestionnaire opérationnel arrêté.")

    async def process_tactical_task(self, tactical_task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Orchestre le traitement d'une tâche de haut niveau de la couche tactique.

        Cette méthode est le point d'entrée principal pour une nouvelle tâche.
        Elle utilise l'interface pour traduire la tâche, la met en file d'attente,
        et attend son résultat de manière asynchrone en utilisant un `Future`.

        Args:
            tactical_task: La tâche à traiter.

        Returns:
            Le résultat de la tâche, formaté pour la couche tactique.
        """
        self.logger.info(f"Traitement de la tâche tactique {tactical_task.get('id', 'unknown')}")
        if not self.tactical_operational_interface:
            self.logger.error("Interface tactique-opérationnelle non définie")
            return {"status": "failed", "error": "Interface non définie"}
        
        try:
            operational_task = self.tactical_operational_interface.translate_task_to_command(tactical_task)
            result_future = asyncio.Future()
            self.operational_state.add_result_future(operational_task["id"], result_future)
            await self.task_queue.put(operational_task)
            operational_result = await result_future
            return self.tactical_operational_interface.process_operational_result(operational_result)
        
        except Exception as e:
            self.logger.error(f"Erreur lors du traitement de la tâche tactique {tactical_task.get('id')}: {e}")
            return {"status": "failed", "error": str(e)}

    async def _worker(self) -> None:
        """
        Le worker principal qui traite les tâches de la file en continu.

        Cette boucle asynchrone prend des tâches de `task_queue`, les délègue
        au `agent_registry` pour exécution, et place le résultat dans
        `result_queue` tout en notifiant les `Future` en attente.
        """
        self.logger.info("Worker opérationnel démarré.")
        while self.running:
            try:
                task = await self.task_queue.get()
                self.logger.info(f"Worker a pris la tâche {task.get('id')}")
                
                result = await self.agent_registry.process_task(task)
                
                result_future = self.operational_state.get_result_future(task["id"])
                if result_future and not result_future.done():
                    result_future.set_result(result)
                
                await self.result_queue.put(result)
                self.task_queue.task_done()
            
            except asyncio.CancelledError:
                self.logger.info("Worker opérationnel annulé.")
                break
            
            except Exception as e:
                self.logger.error(f"Erreur dans le worker opérationnel: {e}", exc_info=True)
                if 'task' in locals():
                    self._handle_worker_error(e, task)
        
        self.logger.info("Worker opérationnel arrêté.")

    def _handle_worker_error(self, error: Exception, task: Dict[str, Any]):
        """Gère les erreurs survenant dans le worker."""
        error_result = {
            "id": f"result-error-{uuid.uuid4().hex[:8]}",
            "task_id": task.get("id", "unknown"),
            "tactical_task_id": task.get("tactical_task_id", "unknown"),
            "status": "failed",
            "issues": [{"type": "worker_error", "description": str(error)}]
        }
        result_future = self.operational_state.get_result_future(task["id"])
        if result_future and not result_future.done():
            result_future.set_result(error_result)
        self.result_queue.put_nowait(error_result)

    def _handle_result_message(self, message: Message) -> None:
        """
        Gestionnaire pour les messages de résultat entrants.

        Ce callback est appelé par le middleware lorsqu'un message de résultat
        est reçu. Il trouve la Future correspondante et la résout.
        """
        if message.type == MessageType.INFORMATION and \
           message.content.get("info_type") == "task_completion_report":
            
            result_data = message.content.get("data", {})
            tactical_task_id = result_data.get("tactical_task_id")
            
            # Note: Le `operational_task_id` est nécessaire pour trouver la future,
            # mais le résultat de l'agent ne le contient pas toujours.
            # On va le reconstituer ou le chercher dans l'état.
            # Pour l'instant, on se base sur le `tactical_task_id` pour le retrouver.
            op_task_id = self.operational_state.find_operational_task_by_tactical_id(tactical_task_id)

            if op_task_id:
                self.logger.info(f"Résultat reçu pour la tâche tactique {tactical_task_id} (op: {op_task_id})")
                future = self.operational_state.get_result_future(op_task_id)
                if future and not future.done():
                    future.set_result(result_data)
                else:
                    self.logger.warning(f"Future pour la tâche {op_task_id} non trouvée ou déjà résolue.")
            else:
                self.logger.warning(f"Impossible de trouver la tâche opérationnelle pour la tâche tactique {tactical_task_id}")

    def _subscribe_to_messages(self) -> None:
        """Met en place les abonnements aux messages entrants."""
        # Enregistrement du gestionnaire pour les résultats de tâches
        # Note : ceci est une simplification. Dans un système réel, on aurait
        # besoin de démultiplexer les messages d'information.
        self.middleware.register_message_handler(
            MessageType.INFORMATION,
            self._handle_result_message
        )
        self.logger.info("Abonné aux messages de résultat opérationnel.")

        async def handle_task_message(message: Message) -> None:
            """Gestionnaire pour les commandes de tâches entrantes."""
            task_data = message.content.get("parameters", {})
            self.logger.info(f"Tâche reçue via message: {task_data.get('id')}")
            await self.task_queue.put(task_data)

        # L'abonnement aux tâches directes est désactivé pour forcer l'utilisation
        # du pattern `process_tactical_task` qui utilise des Futures.
        # self.adapter.subscribe_to_tasks(handle_task_message)
        self.logger.warning("Subscription to direct tasks is disabled; using Future-based processing.")
        self.logger.info("Abonnement aux messages de tâches configuré (inactif).")


    def _map_priority_to_enum(self, priority: str) -> MessagePriority:
        """Convertit une priorité textuelle en énumération `MessagePriority`."""
        return {"high": MessagePriority.HIGH, "medium": MessagePriority.NORMAL, "low": MessagePriority.LOW}.get(priority.lower(), MessagePriority.NORMAL)