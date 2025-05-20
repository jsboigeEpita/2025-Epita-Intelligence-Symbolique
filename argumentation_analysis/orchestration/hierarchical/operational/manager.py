"""
Module définissant le gestionnaire opérationnel.

Ce module fournit une classe pour gérer les agents opérationnels et servir
d'interface entre le niveau tactique et les agents opérationnels.
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Union, Callable
from datetime import datetime
import uuid

from argumentation_analysis.orchestration.hierarchical.operational.state import OperationalState
from argumentation_analysis.orchestration.hierarchical.operational.agent_registry import OperationalAgentRegistry
# Import différé pour éviter l'importation circulaire
from argumentation_analysis.paths import RESULTS_DIR
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from argumentation_analysis.orchestration.hierarchical.interfaces.tactical_operational import TacticalOperationalInterface
from argumentation_analysis.core.communication import (
    MessageMiddleware, OperationalAdapter, Message,
    ChannelType, MessagePriority, MessageType, AgentLevel
)


class OperationalManager:
    """
    Gestionnaire opérationnel.
    
    Cette classe gère les agents opérationnels et sert d'interface entre
    le niveau tactique et les agents opérationnels.
    """
    
    def __init__(self, operational_state: Optional[OperationalState] = None,
                tactical_operational_interface: Optional['TacticalOperationalInterface'] = None,
                middleware: Optional[MessageMiddleware] = None):
        """
        Initialise un nouveau gestionnaire opérationnel.
        
        Args:
            operational_state: État opérationnel à utiliser. Si None, un nouvel état est créé.
            tactical_operational_interface: Interface tactique-opérationnelle à utiliser.
                Si None, une nouvelle interface est créée.
            middleware: Le middleware de communication à utiliser. Si None, un nouveau middleware est créé.
        """
        self.operational_state = operational_state if operational_state else OperationalState()
        self.tactical_operational_interface = tactical_operational_interface
        self.agent_registry = OperationalAgentRegistry(self.operational_state)
        self.logger = logging.getLogger("OperationalManager")
        self.task_queue = asyncio.Queue()
        self.result_queue = asyncio.Queue()
        self.running = False
        self.worker_task = None
        
        # Initialiser le middleware de communication
        self.middleware = middleware if middleware else MessageMiddleware()
        
        # Créer l'adaptateur opérationnel
        self.adapter = OperationalAdapter(
            agent_id="operational_manager",
            middleware=self.middleware
        )
        
        # S'abonner aux tâches et aux messages
        self._subscribe_to_messages()
    
    def set_tactical_operational_interface(self, interface: 'TacticalOperationalInterface') -> None:
        """
        Définit l'interface tactique-opérationnelle.
        
        Args:
            interface: L'interface à utiliser
        """
        self.tactical_operational_interface = interface
        self.logger.info("Interface tactique-opérationnelle définie")
    
    async def start(self) -> None:
        """
        Démarre le gestionnaire opérationnel.
        """
        if self.running:
            self.logger.warning("Le gestionnaire opérationnel est déjà en cours d'exécution")
            return
        
        self.running = True
        self.worker_task = asyncio.create_task(self._worker())
        self.logger.info("Gestionnaire opérationnel démarré")
    
    async def stop(self) -> None:
        """
        Arrête le gestionnaire opérationnel.
        """
        if not self.running:
            self.logger.warning("Le gestionnaire opérationnel n'est pas en cours d'exécution")
            return
        
        self.running = False
        if self.worker_task:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass
            self.worker_task = None
        
        self.logger.info("Gestionnaire opérationnel arrêté")
    
    def _subscribe_to_messages(self) -> None:
        """S'abonne aux tâches et aux messages."""
        # Définir le callback pour les tâches
        def handle_task(message: Message) -> None:
            task_type = message.content.get("task_type")
            task_data = message.content.get("parameters", {})
            
            if task_type == "operational_task":
                # Ajouter la tâche à la file d'attente
                asyncio.create_task(self._process_task_async(task_data, message.sender))
        
        # S'abonner aux tâches opérationnelles
        self.middleware.get_channel(ChannelType.HIERARCHICAL).subscribe(
            subscriber_id="operational_manager",
            callback=handle_task,
            filter_criteria={
                "recipient": "operational_manager",
                "type": MessageType.COMMAND,
                "sender_level": AgentLevel.TACTICAL
            }
        )
        
        # S'abonner aux demandes de statut
        def handle_status_request(message: Message) -> None:
            request_type = message.content.get("request_type")
            
            if request_type == "operational_status":
                # Envoyer le statut opérationnel
                asyncio.create_task(self._send_operational_status(message.sender))
        
        self.middleware.get_channel(ChannelType.HIERARCHICAL).subscribe(
            subscriber_id="operational_manager_status",
            callback=handle_status_request,
            filter_criteria={
                "recipient": "operational_manager",
                "type": MessageType.REQUEST,
                "content.request_type": "operational_status"
            }
        )
        
        self.logger.info("Abonnement aux tâches et messages effectué")
    
    async def _process_task_async(self, task: Dict[str, Any], sender_id: str) -> None:
        """
        Traite une tâche de manière asynchrone et envoie le résultat.
        
        Args:
            task: La tâche à traiter
            sender_id: L'identifiant de l'expéditeur de la tâche
        """
        try:
            # Ajouter la tâche à la file d'attente
            await self.task_queue.put(task)
            
            # Envoyer une notification de début de traitement
            self.adapter.send_status_update(
                update_type="task_received",
                status={
                    "task_id": task.get("id"),
                    "tactical_task_id": task.get("tactical_task_id"),
                    "timestamp": asyncio.get_event_loop().time()
                },
                recipient_id=sender_id
            )
            
            # Attendre le résultat
            operational_result = await self.result_queue.get()
            
            # Traduire le résultat opérationnel en résultat tactique
            if self.tactical_operational_interface:
                tactical_result = self.tactical_operational_interface.process_operational_result(operational_result)
            else:
                tactical_result = operational_result
            
            # Envoyer le résultat
            self.adapter.send_task_result(
                task_id=task.get("id"),
                result_type="task_completion",
                result_data=tactical_result,
                recipient_id=sender_id,
                priority=self._map_priority_to_enum(task.get("priority", "medium"))
            )
            
            self.logger.info(f"Tâche {task.get('id')} traitée avec succès")
            
        except Exception as e:
            self.logger.error(f"Erreur lors du traitement de la tâche {task.get('id')}: {str(e)}")
            
            # Envoyer une notification d'échec
            self.adapter.send_task_result(
                task_id=task.get("id"),
                result_type="task_failure",
                result_data={
                    "task_id": task.get("id"),
                    "tactical_task_id": task.get("tactical_task_id"),
                    "error": str(e),
                    "status": "failed"
                },
                recipient_id=sender_id,
                priority=MessagePriority.HIGH
            )
    
    async def _send_operational_status(self, recipient_id: str) -> None:
        """
        Envoie le statut opérationnel.
        
        Args:
            recipient_id: L'identifiant du destinataire
        """
        try:
            # Récupérer les capacités des agents
            capabilities = await self.get_agent_capabilities()
            
            # Récupérer les tâches en cours
            tasks_in_progress = self.operational_state.get_tasks_in_progress()
            
            # Créer le statut
            status = {
                "timestamp": datetime.now().isoformat(),
                "agent_capabilities": capabilities,
                "tasks_in_progress": len(tasks_in_progress),
                "tasks_completed": len(self.operational_state.get_completed_tasks()),
                "tasks_failed": len(self.operational_state.get_failed_tasks()),
                "is_running": self.running
            }
            
            # Envoyer le statut
            self.adapter.send_response(
                request_id=f"status-{uuid.uuid4().hex[:8]}",
                content=status,
                recipient_id=recipient_id
            )
            
            self.logger.info(f"Statut opérationnel envoyé à {recipient_id}")
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'envoi du statut opérationnel: {str(e)}")
            
            # Envoyer une notification d'échec
            self.adapter.send_response(
                request_id=f"status-error-{uuid.uuid4().hex[:8]}",
                content={
                    "error": str(e),
                    "status": "failed"
                },
                recipient_id=recipient_id
            )
    
    async def process_tactical_task(self, tactical_task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Traite une tâche tactique.
        
        Args:
            tactical_task: La tâche tactique à traiter
            
        Returns:
            Le résultat du traitement de la tâche
        """
        self.logger.info(f"Traitement de la tâche tactique {tactical_task.get('id', 'unknown')}")
        
        # Vérifier si l'interface tactique-opérationnelle est définie
        if not self.tactical_operational_interface:
            self.logger.error("Interface tactique-opérationnelle non définie")
            return {
                "task_id": tactical_task.get("id"),
                "completion_status": "failed",
                RESULTS_DIR: {},
                "execution_metrics": {},
                "issues": [{
                    "type": "interface_error",
                    "description": "Interface tactique-opérationnelle non définie",
                    "severity": "high"
                }]
            }
        
        try:
            # Traduire la tâche tactique en tâche opérationnelle
            operational_task = self.tactical_operational_interface.translate_task(tactical_task)
            
            # Créer un futur pour attendre le résultat
            result_future = asyncio.Future()
            
            # Stocker le futur dans l'état opérationnel
            self.operational_state.add_result_future(operational_task["id"], result_future)
            
            # Ajouter la tâche à la file d'attente
            await self.task_queue.put(operational_task)
            
            # Attendre le résultat
            operational_result = await result_future
            
            # Traduire le résultat opérationnel en résultat tactique
            tactical_result = self.tactical_operational_interface.process_operational_result(operational_result)
            
            return tactical_result
        
        except Exception as e:
            self.logger.error(f"Erreur lors du traitement de la tâche tactique {tactical_task.get('id', 'unknown')}: {e}")
            return {
                "task_id": tactical_task.get("id"),
                "completion_status": "failed",
                RESULTS_DIR: {},
                "execution_metrics": {},
                "issues": [{
                    "type": "processing_error",
                    "description": f"Erreur lors du traitement: {str(e)}",
                    "severity": "high",
                    "details": {
                        "exception": str(e)
                    }
                }]
            }
    
    async def _worker(self) -> None:
        """
        Traite les tâches de la file d'attente.
        """
        self.logger.info("Worker opérationnel démarré")
        
        while self.running:
            try:
                # Récupérer une tâche de la file d'attente
                task = await self.task_queue.get()
                
                # Traiter la tâche
                result = await self.agent_registry.process_task(task)
                
                # Récupérer le futur associé à la tâche
                result_future = self.operational_state.get_result_future(task["id"])
                
                if result_future and not result_future.done():
                    # Définir le résultat du futur
                    result_future.set_result(result)
                
                # Ajouter le résultat à la file d'attente des résultats
                await self.result_queue.put(result)
                
                # Publier le résultat sur le canal de données
                self.middleware.publish(
                    topic_id=f"operational_results.{task['id']}",
                    sender="operational_manager",
                    sender_level=AgentLevel.OPERATIONAL,
                    content={
                        "result_type": "task_completion",
                        "result_data": result
                    },
                    priority=self._map_priority_to_enum(task.get("priority", "medium"))
                )
                
                # Marquer la tâche comme terminée
                self.task_queue.task_done()
            
            except asyncio.CancelledError:
                self.logger.info("Worker opérationnel annulé")
                break
            
            except Exception as e:
                self.logger.error(f"Erreur dans le worker opérationnel: {e}")
                
                # Créer un résultat d'erreur
                error_result = {
                    "id": f"result-error-{uuid.uuid4().hex[:8]}",
                    "task_id": task.get("id", "unknown") if 'task' in locals() else "unknown",
                    "tactical_task_id": task.get("tactical_task_id", "unknown") if 'task' in locals() else "unknown",
                    "status": "failed",
                    "outputs": {},
                    "metrics": {},
                    "issues": [{
                        "type": "worker_error",
                        "description": f"Erreur dans le worker opérationnel: {str(e)}",
                        "severity": "high",
                        "details": {
                            "exception": str(e)
                        }
                    }]
                }
                
                # Récupérer le futur associé à la tâche
                if 'task' in locals():
                    result_future = self.operational_state.get_result_future(task["id"])
                    
                    if result_future and not result_future.done():
                        # Définir le résultat du futur
                        result_future.set_result(error_result)
                
                # Ajouter le résultat d'erreur à la file d'attente des résultats
                try:
                    await self.result_queue.put(error_result)
                except Exception as e2:
                    self.logger.error(f"Erreur lors de l'ajout du résultat d'erreur à la file d'attente: {e2}")
        
        self.logger.info("Worker opérationnel arrêté")
    
    async def get_agent_capabilities(self) -> Dict[str, List[str]]:
        """
        Récupère les capacités de tous les agents.
        
        Returns:
            Un dictionnaire contenant les capacités de chaque agent
        """
        capabilities = {}
        
        for agent_type in self.agent_registry.get_agent_types():
            agent = await self.agent_registry.get_agent(agent_type)
            if agent:
                capabilities[agent_type] = agent.get_capabilities()
        
        return capabilities
    
    def get_operational_state(self) -> OperationalState:
        """
        Récupère l'état opérationnel.
        
        Returns:
            L'état opérationnel
        """
        return self.operational_state
    
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
    
    def broadcast_status(self) -> None:
        """
        Diffuse le statut opérationnel à tous les agents tactiques.
        """
        try:
            # Créer le statut
            status = {
                "timestamp": datetime.now().isoformat(),
                "tasks_in_progress": len(self.operational_state.get_tasks_in_progress()),
                "tasks_completed": len(self.operational_state.get_completed_tasks()),
                "tasks_failed": len(self.operational_state.get_failed_tasks()),
                "is_running": self.running
            }
            
            # Publier le statut
            self.middleware.publish(
                topic_id="operational_status",
                sender="operational_manager",
                sender_level=AgentLevel.OPERATIONAL,
                content={
                    "status_type": "operational_status",
                    "status_data": status
                },
                priority=MessagePriority.NORMAL
            )
            
            self.logger.info("Statut opérationnel diffusé")
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la diffusion du statut opérationnel: {str(e)}")