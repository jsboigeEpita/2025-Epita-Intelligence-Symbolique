"""
Module définissant l'interface commune pour les agents opérationnels.

Cette interface définit les méthodes que tous les agents opérationnels
doivent implémenter pour fonctionner dans l'architecture hiérarchique.
"""

from typing import Dict, List, Any, Optional, Union, Callable
from abc import ABC, abstractmethod
import logging
import asyncio
import uuid

from argumentiation_analysis.orchestration.hierarchical.operational.state import OperationalState
from argumentiation_analysis.core.communication import (

from argumentiation_analysis.paths import RESULTS_DIR

    MessageMiddleware, OperationalAdapter, Message,
    ChannelType, MessagePriority, MessageType, AgentLevel
)


class OperationalAgent(ABC):
    """
    Interface abstraite pour les agents opérationnels.
    
    Tous les agents opérationnels doivent implémenter cette interface
    pour être compatibles avec l'architecture hiérarchique à trois niveaux.
    """
    
    def __init__(self, name: str, operational_state: Optional[OperationalState] = None,
                middleware: Optional[MessageMiddleware] = None):
        """
        Initialise un nouvel agent opérationnel.
        
        Args:
            name: Nom de l'agent
            operational_state: État opérationnel à utiliser. Si None, un nouvel état est créé.
            middleware: Le middleware de communication à utiliser. Si None, un nouveau middleware est créé.
        """
        self.name = name
        self.operational_state = operational_state if operational_state else OperationalState()
        self.logger = logging.getLogger(f"OperationalAgent.{name}")
        
        # Initialiser le middleware de communication
        self.middleware = middleware if middleware else MessageMiddleware()
        
        # Créer l'adaptateur opérationnel
        self.adapter = OperationalAdapter(
            agent_id=name,
            middleware=self.middleware
        )
        
        # S'abonner aux tâches opérationnelles
        self._subscribe_to_tasks()
    
    def _subscribe_to_tasks(self) -> None:
        """S'abonne aux tâches opérationnelles."""
        # Définir le callback pour les tâches
        def handle_task(message: Message) -> None:
            task_type = message.content.get("task_type")
            task_data = message.content.get("parameters", {})
            
            if task_type == "operational_task" and self.can_process_task(task_data):
                # Traiter la tâche de manière asynchrone
                asyncio.create_task(self._process_task_async(task_data, message.sender))
        
        # S'abonner aux tâches opérationnelles directes
        self.middleware.get_channel(ChannelType.HIERARCHICAL).subscribe(
            subscriber_id=self.name,
            callback=handle_task,
            filter_criteria={
                "recipient": self.name,
                "type": MessageType.COMMAND,
                "sender_level": AgentLevel.TACTICAL
            }
        )
        
        # S'abonner aux tâches publiées pour les capacités que cet agent possède
        capabilities = self.get_capabilities()
        for capability in capabilities:
            self.middleware.get_channel(ChannelType.COLLABORATION).subscribe(
                subscriber_id=f"{self.name}_{capability}",
                callback=handle_task,
                filter_criteria={
                    "topic": f"operational_tasks.{capability}",
                    "sender_level": AgentLevel.TACTICAL
                }
            )
        
        self.logger.info(f"Agent {self.name} abonné aux tâches opérationnelles")
    
    async def _process_task_async(self, task: Dict[str, Any], sender_id: str) -> None:
        """
        Traite une tâche de manière asynchrone et envoie le résultat.
        
        Args:
            task: La tâche à traiter
            sender_id: L'identifiant de l'expéditeur de la tâche
        """
        try:
            # Enregistrer la tâche
            self.register_task(task)
            
            # Mettre à jour le statut
            self.update_task_status(task.get("id"), "in_progress")
            
            # Envoyer une notification de début de traitement
            self.adapter.send_status_update(
                update_type="task_started",
                status={
                    "task_id": task.get("id"),
                    "tactical_task_id": task.get("tactical_task_id"),
                    "timestamp": asyncio.get_event_loop().time()
                },
                recipient_id=sender_id
            )
            
            # Traiter la tâche
            result = await self.process_task(task)
            
            # Mettre à jour le statut
            self.update_task_status(task.get("id"), "completed")
            
            # Formater le résultat
            formatted_result = self.format_result(
                task,
                result.get(RESULTS_DIR, []),
                result.get("metrics", {}),
                result.get("issues", [])
            )
            
            # Envoyer le résultat
            self.adapter.send_task_result(
                task_id=task.get("id"),
                result_type="task_completion",
                result_data=formatted_result,
                recipient_id=sender_id,
                priority=self._map_priority_to_enum(task.get("priority", "medium"))
            )
            
            self.logger.info(f"Tâche {task.get('id')} traitée avec succès")
            
        except Exception as e:
            self.logger.error(f"Erreur lors du traitement de la tâche {task.get('id')}: {str(e)}")
            
            # Mettre à jour le statut
            self.update_task_status(task.get("id"), "failed", {"error": str(e)})
            
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
    
    def update_task_status(self, task_id: str, status: str, details: Optional[Dict[str, Any]] = None) -> bool:
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
    
    async def execute_technique(self, technique: Dict[str, Any], text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Exécute une technique d'analyse sur un texte.
        
        Cette méthode peut être surchargée par les agents opérationnels
        pour fournir une implémentation spécifique.
        
        Args:
            technique: La technique à exécuter
            text: Le texte à analyser
            context: Le contexte d'exécution
            
        Returns:
            Le résultat de l'exécution de la technique
        """
        technique_name = technique.get('name', 'unknown')
        self.logger.warning(f"Méthode execute_technique non implémentée pour la technique {technique_name}.")
        
        # Publier une demande d'aide pour cette technique
        self.middleware.publish(
            topic_id=f"technique_help.{technique_name}",
            sender=self.name,
            sender_level=AgentLevel.OPERATIONAL,
            content={
                "technique": technique,
                "context": {
                    "text_sample": text[:100] + "..." if len(text) > 100 else text,
                    "agent": self.name
                }
            },
            priority=MessagePriority.HIGH
        )
        
        return {
            "status": "error",
            "message": f"Méthode execute_technique non implémentée pour la technique {technique_name}.",
            "technique": technique_name
        }
    
    def format_result(self, task: Dict[str, Any], results: List[Dict[str, Any]], metrics: Dict[str, Any], issues: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Formate le résultat d'une tâche pour le niveau tactique.
        
        Args:
            task: La tâche traitée
            results: Les résultats de l'analyse
            metrics: Les métriques d'exécution
            issues: Les problèmes rencontrés
            
        Returns:
            Le résultat formaté
        """
        return {
            "id": f"result-{task.get('id')}",
            "task_id": task.get("id"),
            "tactical_task_id": task.get("tactical_task_id"),
            "status": "completed" if not issues else "completed_with_issues",
            "outputs": self._format_outputs(results),
            "metrics": metrics,
            "issues": issues
        }
    
    def _format_outputs(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Formate les outputs pour le niveau tactique.
        
        Args:
            results: Les résultats de l'analyse
            
        Returns:
            Les outputs formatés
        """
        outputs = {}
        
        # Regrouper les résultats par type
        for result in results:
            result_type = result.get("type")
            if result_type:
                if result_type not in outputs:
                    outputs[result_type] = []
                
                # Copier le résultat sans le type
                result_copy = result.copy()
                if "type" in result_copy:
                    del result_copy["type"]
                
                outputs[result_type].append(result_copy)
        
        return outputs
    
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
    
    def request_resource(self, resource_type: str, parameters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Demande une ressource au niveau tactique.
        
        Args:
            resource_type: Le type de ressource demandé
            parameters: Les paramètres de la demande
            
        Returns:
            La ressource demandée ou None si la demande échoue
        """
        try:
            response = self.adapter.request_tactical_guidance(
                request_type="resource_request",
                parameters={
                    "resource_type": resource_type,
                    "parameters": parameters
                },
                recipient_id="tactical_coordinator",
                timeout=10.0
            )
            
            if response:
                self.logger.info(f"Ressource {resource_type} reçue")
                return response
            else:
                self.logger.warning(f"Délai d'attente dépassé pour la demande de ressource {resource_type}")
                return None
                
        except Exception as e:
            self.logger.error(f"Erreur lors de la demande de ressource {resource_type}: {str(e)}")
            return None
    
    def share_intermediate_result(self, result_type: str, result_data: Dict[str, Any],
                                recipients: Optional[List[str]] = None) -> str:
        """
        Partage un résultat intermédiaire avec d'autres agents.
        
        Args:
            result_type: Le type de résultat
            result_data: Les données du résultat
            recipients: Liste des identifiants des destinataires (None pour tous les agents opérationnels)
            
        Returns:
            L'identifiant du résultat partagé
        """
        result_id = f"result-{uuid.uuid4().hex[:8]}"
        
        # Stocker le résultat dans le canal de données
        data_channel = self.middleware.get_channel(ChannelType.DATA)
        data_id = f"operational-data-{uuid.uuid4().hex[:8]}"
        version_id = data_channel.store_data(
            data_id=data_id,
            data=result_data,
            metadata={
                "result_type": result_type,
                "sender": self.name,
                "timestamp": asyncio.get_event_loop().time()
            }
        )
        
        # Créer le message de données
        content = {
            "info_type": "intermediate_result",
            "result_type": result_type,
            "data_reference": {
                "data_id": data_id,
                "version_id": version_id
            }
        }
        
        if recipients:
            # Envoyer le résultat à chaque destinataire
            for recipient_id in recipients:
                self.adapter.share_operational_data(
                    data_type=result_type,
                    data=content,
                    recipient_ids=[recipient_id]
                )
        else:
            # Publier le résultat pour tous les agents opérationnels
            self.middleware.publish(
                topic_id=f"operational_results.{result_type}",
                sender=self.name,
                sender_level=AgentLevel.OPERATIONAL,
                content=content,
                priority=MessagePriority.NORMAL
            )
        
        self.logger.info(f"Résultat intermédiaire {result_type} partagé avec {len(recipients) if recipients else 'tous les agents opérationnels'}")
        return result_id
    
    def subscribe_to_results(self, result_types: List[str], callback: Callable[[Message], None]) -> str:
        """
        S'abonne aux résultats d'autres agents.
        
        Args:
            result_types: Types de résultats
            callback: Fonction de rappel à appeler lors de la réception d'un résultat
            
        Returns:
            Un identifiant d'abonnement
        """
        subscription_id = f"sub-{uuid.uuid4().hex[:8]}"
        
        for result_type in result_types:
            self.middleware.get_channel(ChannelType.DATA).subscribe(
                subscriber_id=f"{self.name}_{result_type}_{subscription_id}",
                callback=callback,
                filter_criteria={
                    "topic": f"operational_results.{result_type}"
                }
            )
        
        self.logger.info(f"Abonnement aux résultats de types: {', '.join(result_types)}")
        return subscription_id