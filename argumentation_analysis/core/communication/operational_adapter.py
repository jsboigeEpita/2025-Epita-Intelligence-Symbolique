"""
Adaptateur pour les agents opérationnels dans le système de communication multi-canal.

Cet adaptateur sert d'interface entre les agents opérationnels et le middleware
de messagerie, traduisant les appels d'API spécifiques aux agents opérationnels
en messages standardisés compréhensibles par le middleware.
"""

import uuid
import logging
from typing import Dict, Any, Optional, List, Callable, Union
from datetime import datetime

from .message import Message, MessageType, MessagePriority, AgentLevel
from .channel_interface import ChannelType
from .middleware import MessageMiddleware

from argumentation_analysis.paths import DATA_DIR



class OperationalAdapter:
    """
    Adaptateur pour les agents opérationnels.
    
    Cet adaptateur fournit une interface simplifiée pour les agents opérationnels,
    leur permettant de recevoir des tâches des agents tactiques, d'envoyer des
    résultats, et de collaborer avec d'autres agents opérationnels.
    """
    
    def __init__(self, agent_id: str, middleware: MessageMiddleware):
        """
        Initialise un nouvel adaptateur pour un agent opérationnel.
        
        Args:
            agent_id: Identifiant de l'agent opérationnel
            middleware: Le middleware de messagerie à utiliser
        """
        self.agent_id = agent_id
        self.middleware = middleware
        self.logger = logging.getLogger(f"OperationalAdapter.{agent_id}")
        self.logger.setLevel(logging.INFO)
    
    def receive_task(
        self,
        timeout: Optional[float] = None,
        filter_criteria: Optional[Dict[str, Any]] = None
    ) -> Optional[Message]:
        """
        Reçoit une tâche d'un agent tactique.
        
        Args:
            timeout: Délai d'attente maximum en secondes (None pour attente indéfinie)
            filter_criteria: Critères de filtrage des tâches (optionnel)
            
        Returns:
            La tâche reçue ou None si timeout
        """
        # Recevoir un message via le middleware
        message = self.middleware.receive_message(
            recipient_id=self.agent_id,
            channel_type=ChannelType.HIERARCHICAL,
            timeout=timeout
        )
        
        if message:
            # Vérifier si le message est une tâche
            is_task = (
                message.type == MessageType.COMMAND and
                message.sender_level == AgentLevel.TACTICAL
            )
            
            if is_task:
                # Vérifier les critères de filtrage
                if filter_criteria:
                    for key, value in filter_criteria.items():
                        if key in message.content:
                            if isinstance(value, list):
                                if message.content[key] not in value:
                                    return None
                            elif message.content[key] != value:
                                return None
                
                # Envoyer un accusé de réception si nécessaire
                if message.requires_acknowledgement():
                    ack = message.create_acknowledgement()
                    ack.sender = self.agent_id
                    ack.sender_level = AgentLevel.OPERATIONAL
                    self.middleware.send_message(ack)
                
                self.logger.info(f"Task received from {message.sender}")
                return message
        
        return None
    
    def send_result(
        self,
        task_id: str,
        result_type: str,
        result: Dict[str, Any],
        recipient_id: str,
        priority: MessagePriority = MessagePriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Envoie un résultat de tâche à un agent tactique.
        
        Args:
            task_id: Identifiant de la tâche
            result_type: Type de résultat (analysis_result, fallacy_detection, etc.)
            result: Contenu du résultat
            recipient_id: Identifiant de l'agent tactique
            priority: Priorité du résultat
            metadata: Métadonnées additionnelles (optionnel)
            
        Returns:
            L'identifiant du résultat envoyé
        """
        # Créer le message de résultat
        message = Message(
            message_type=MessageType.INFORMATION,
            sender=self.agent_id,
            sender_level=AgentLevel.OPERATIONAL,
            content={
                "info_type": "task_result",
                "task_id": task_id,
                "result_type": result_type,
                DATA_DIR: result
            },
            recipient=recipient_id,
            channel=ChannelType.HIERARCHICAL.value,
            priority=priority,
            metadata={
                "reply_to": task_id,
                **(metadata or {})
            }
        )
        
        # Envoyer le message via le middleware
        success = self.middleware.send_message(message)
        
        if success:
            self.logger.info(f"Result for task {task_id} sent to {recipient_id}")
        else:
            self.logger.error(f"Failed to send result for task {task_id} to {recipient_id}")
        
        return message.id
    
    def request_task_clarification(
        self,
        task_id: str,
        question: str,
        context: Dict[str, Any],
        recipient_id: str,
        timeout: float = 30.0,
        priority: MessagePriority = MessagePriority.NORMAL
    ) -> Optional[Dict[str, Any]]:
        """
        Demande des clarifications sur une tâche à un agent tactique.
        
        Args:
            task_id: Identifiant de la tâche
            question: Question à poser
            context: Contexte de la question
            recipient_id: Identifiant de l'agent tactique
            timeout: Délai d'attente maximum en secondes
            priority: Priorité de la requête
            
        Returns:
            Les clarifications demandées ou None si timeout
        """
        try:
            # Envoyer la requête via le protocole de requête-réponse
            response = self.middleware.send_request(
                sender=self.agent_id,
                sender_level=AgentLevel.OPERATIONAL,
                recipient=recipient_id,
                request_type="task_clarification",
                content={
                    "task_id": task_id,
                    "question": question,
                    "context": context
                },
                timeout=timeout,
                priority=priority,
                channel=ChannelType.HIERARCHICAL.value
            )
            
            if response:
                self.logger.info(f"Received clarification from {recipient_id} for task {task_id}")
                return response.content.get(DATA_DIR)
            
            self.logger.warning(f"Clarification request for task {task_id} timed out")
            return None
            
        except Exception as e:
            self.logger.error(f"Error requesting clarification for task {task_id}: {str(e)}")
            return None
    
    async def request_task_clarification_async(
        self,
        task_id: str,
        question: str,
        context: Dict[str, Any],
        recipient_id: str,
        timeout: float = 30.0,
        priority: MessagePriority = MessagePriority.NORMAL
    ) -> Optional[Dict[str, Any]]:
        """
        Version asynchrone de request_task_clarification.
        
        Args:
            task_id: Identifiant de la tâche
            question: Question à poser
            context: Contexte de la question
            recipient_id: Identifiant de l'agent tactique
            timeout: Délai d'attente maximum en secondes
            priority: Priorité de la requête
            
        Returns:
            Les clarifications demandées ou None si timeout
        """
        try:
            # Envoyer la requête via le protocole de requête-réponse
            response = await self.middleware.send_request_async(
                sender=self.agent_id,
                sender_level=AgentLevel.OPERATIONAL,
                recipient=recipient_id,
                request_type="task_clarification",
                content={
                    "task_id": task_id,
                    "question": question,
                    "context": context
                },
                timeout=timeout,
                priority=priority,
                channel=ChannelType.HIERARCHICAL.value
            )
            
            if response:
                self.logger.info(f"Received clarification from {recipient_id} for task {task_id}")
                return response.content.get(DATA_DIR)
            
            self.logger.warning(f"Clarification request for task {task_id} timed out")
            return None
            
        except Exception as e:
            self.logger.error(f"Error requesting clarification for task {task_id}: {str(e)}")
            return None
    
    def collaborate_with_operational(
        self,
        collaboration_type: str,
        content: Dict[str, Any],
        recipient_ids: List[str],
        group_id: Optional[str] = None,
        priority: MessagePriority = MessagePriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Collabore avec d'autres agents opérationnels.
        
        Args:
            collaboration_type: Type de collaboration (joint_analysis, data_sharing, etc.)
            content: Contenu de la collaboration
            recipient_ids: Liste des identifiants des agents opérationnels destinataires
            group_id: Identifiant du groupe de collaboration (optionnel)
            priority: Priorité du message
            metadata: Métadonnées additionnelles (optionnel)
            
        Returns:
            L'identifiant du message de collaboration
        """
        # Créer ou récupérer le groupe de collaboration
        if group_id is None:
            # Créer un nouveau groupe
            group_id = self.middleware.get_channel(ChannelType.COLLABORATION).create_group(
                name=f"Operational Collaboration: {collaboration_type}",
                description=f"Collaboration between operational agents for {collaboration_type}",
                members=[self.agent_id] + recipient_ids
            )
        else:
            # Ajouter les destinataires au groupe existant
            collab_channel = self.middleware.get_channel(ChannelType.COLLABORATION)
            for recipient_id in recipient_ids:
                collab_channel.add_group_member(group_id, recipient_id)
        
        # Créer le message de collaboration
        message = Message(
            message_type=MessageType.INFORMATION,
            sender=self.agent_id,
            sender_level=AgentLevel.OPERATIONAL,
            content={
                "info_type": "collaboration",
                "collaboration_type": collaboration_type,
                DATA_DIR: content
            },
            recipient=None,  # Destiné au groupe
            channel=ChannelType.COLLABORATION.value,
            priority=priority,
            metadata={
                "group_id": group_id,
                **(metadata or {})
            }
        )
        
        # Envoyer le message via le middleware
        success = self.middleware.send_message(message)
        
        if success:
            self.logger.info(f"Collaboration message sent to group {group_id}")
        else:
            self.logger.error(f"Failed to send collaboration message to group {group_id}")
        
        return message.id
    
    def share_analysis_data(
        self,
        data_type: str,
        data: Dict[str, Any],
        recipient_ids: Optional[List[str]] = None,
        compress: bool = True,
        priority: MessagePriority = MessagePriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Partage des données d'analyse avec d'autres agents.
        
        Args:
            data_type: Type de données (fallacy_detection, argument_structure, etc.)
            data: Les données à partager
            recipient_ids: Liste des identifiants des destinataires (None pour tous les agents opérationnels)
            compress: Indique si les données doivent être compressées
            priority: Priorité du message
            metadata: Métadonnées additionnelles (optionnel)
            
        Returns:
            L'identifiant du message de données
        """
        # Stocker les données dans le canal de données
        data_channel = self.middleware.get_channel(ChannelType.DATA)
        data_id = f"operational-data-{uuid.uuid4().hex[:8]}"
        version_id = data_channel.store_data(
            data_id=data_id,
            data=data,
            metadata={
                "data_type": data_type,
                "sender": self.agent_id,
                "timestamp": datetime.now().isoformat(),
                **(metadata or {})
            },
            compress=compress
        )
        
        # Créer le message de données
        message = Message(
            message_type=MessageType.INFORMATION,
            sender=self.agent_id,
            sender_level=AgentLevel.OPERATIONAL,
            content={
                "info_type": "operational_data",
                "data_type": data_type,
                "data_reference": {
                    "data_id": data_id,
                    "version_id": version_id
                }
            },
            recipient=None,  # Sera défini pour chaque destinataire
            channel=ChannelType.DATA.value,
            priority=priority,
            metadata=metadata
        )
        
        # Envoyer le message à chaque destinataire
        if recipient_ids:
            for recipient_id in recipient_ids:
                message.recipient = recipient_id
                self.middleware.send_message(message)
        else:
            # Publier les données pour tous les agents opérationnels
            topic_id = f"operational_data.{data_type}"
            self.middleware.publish(
                topic_id=topic_id,
                sender=self.agent_id,
                sender_level=AgentLevel.OPERATIONAL,
                content=message.content,
                priority=priority,
                metadata=message.metadata
            )
        
        self.logger.info(f"Analysis data {data_type} shared with {len(recipient_ids) if recipient_ids else 'all operational agents'}")
        return data_id
    
    def request_assistance(
        self,
        assistance_type: str,
        problem: Dict[str, Any],
        recipient_ids: List[str],
        priority: MessagePriority = MessagePriority.NORMAL,
        timeout: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Demande de l'assistance à d'autres agents opérationnels.
        
        Args:
            assistance_type: Type d'assistance (analysis_help, verification, etc.)
            problem: Description du problème
            recipient_ids: Liste des identifiants des agents opérationnels à solliciter
            priority: Priorité de la demande
            timeout: Délai d'attente maximum en secondes (None pour attente indéfinie)
            
        Returns:
            Liste des réponses reçues
        """
        # Créer un groupe de collaboration pour cette demande d'assistance
        group_id = self.middleware.get_channel(ChannelType.COLLABORATION).create_group(
            name=f"Assistance Request: {assistance_type}",
            description=f"Assistance request from {self.agent_id} for {assistance_type}",
            members=[self.agent_id] + recipient_ids
        )
        
        # Créer le message de demande d'assistance
        message = Message(
            message_type=MessageType.REQUEST,
            sender=self.agent_id,
            sender_level=AgentLevel.OPERATIONAL,
            content={
                "request_type": "assistance",
                "assistance_type": assistance_type,
                "problem": problem,
                "response_format": "json"
            },
            recipient=None,  # Destiné au groupe
            channel=ChannelType.COLLABORATION.value,
            priority=priority,
            metadata={
                "group_id": group_id,
                "conversation_id": f"assist-{uuid.uuid4().hex[:8]}",
                "requires_response": True
            }
        )
        
        # Envoyer le message via le middleware
        self.middleware.send_message(message)
        
        self.logger.info(f"Assistance request {assistance_type} sent to {len(recipient_ids)} agents")
        
        # Attendre les réponses
        responses = []
        start_time = datetime.now()
        
        while True:
            # Vérifier si le timeout est atteint
            if timeout is not None:
                elapsed = (datetime.now() - start_time).total_seconds()
                if elapsed >= timeout:
                    break
                
                remaining = timeout - elapsed
            else:
                remaining = None
            
            # Recevoir un message du canal de collaboration
            response = self.middleware.receive_message(
                recipient_id=self.agent_id,
                channel_type=ChannelType.COLLABORATION,
                timeout=remaining
            )
            
            if response:
                # Vérifier si le message est une réponse à notre demande
                is_response = (
                    response.type == MessageType.RESPONSE and
                    response.metadata.get("reply_to") == message.id
                )
                
                if is_response:
                    responses.append(response.content.get(DATA_DIR, {}))
                    
                    # Si tous les agents ont répondu, on peut arrêter
                    if len(responses) >= len(recipient_ids):
                        break
            elif remaining is None:
                # Pas de timeout et pas de message, on continue d'attendre
                continue
            else:
                # Timeout atteint
                break
        
        self.logger.info(f"Received {len(responses)} responses to assistance request {assistance_type}")
        return responses
    
    def get_pending_tasks(self, max_count: Optional[int] = None) -> List[Message]:
        """
        Récupère les tâches en attente.
        
        Args:
            max_count: Nombre maximum de tâches à récupérer (None pour toutes)
            
        Returns:
            Liste des tâches en attente
        """
        # Récupérer les messages en attente via le middleware
        messages = self.middleware.get_pending_messages(
            recipient_id=self.agent_id,
            channel_type=ChannelType.HIERARCHICAL,
            max_count=max_count
        )
        
        # Filtrer les tâches
        tasks = [
            message for message in messages
            if message.type == MessageType.COMMAND and
            message.sender_level == AgentLevel.TACTICAL
        ]
        
        self.logger.info(f"Retrieved {len(tasks)} pending tasks")
        return tasks
    
    def send_progress_update(
        self,
        task_id: str,
        progress: float,
        status: str,
        recipient_id: str,
        details: Optional[Dict[str, Any]] = None,
        priority: MessagePriority = MessagePriority.NORMAL
    ) -> str:
        """
        Envoie une mise à jour de progression d'une tâche.
        
        Args:
            task_id: Identifiant de la tâche
            progress: Progression de la tâche (0.0 à 1.0)
            status: Statut de la tâche (in_progress, completed, error, etc.)
            details: Détails supplémentaires (optionnel)
            recipient_id: Identifiant de l'agent tactique
            priority: Priorité de la mise à jour
            
        Returns:
            L'identifiant de la mise à jour envoyée
        """
        # Créer le message de mise à jour
        message = Message(
            message_type=MessageType.INFORMATION,
            sender=self.agent_id,
            sender_level=AgentLevel.OPERATIONAL,
            content={
                "info_type": "operational_update",
                "update_type": "task_progress",
                "task_id": task_id,
                "progress": progress,
                "status": status,
                "details": details or {}
            },
            recipient=recipient_id,
            channel=ChannelType.HIERARCHICAL.value,
            priority=priority,
            metadata={
                "reply_to": task_id
            }
        )
        
        # Envoyer le message via le middleware
        success = self.middleware.send_message(message)
        
        if success:
            self.logger.info(f"Progress update for task {task_id} sent to {recipient_id}")
        else:
            self.logger.error(f"Failed to send progress update for task {task_id} to {recipient_id}")
        
        return message.id
    
    def subscribe_to_collaboration_group(
        self,
        group_id: str,
        callback: Callable[[Message], None],
        filter_criteria: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        S'abonne à un groupe de collaboration.
        
        Args:
            group_id: Identifiant du groupe
            callback: Fonction de rappel à appeler lors de la réception d'un message
            filter_criteria: Critères de filtrage des messages (optionnel)
            
        Returns:
            Un identifiant d'abonnement
        """
        # Ajouter l'agent au groupe s'il n'en est pas déjà membre
        collab_channel = self.middleware.get_channel(ChannelType.COLLABORATION)
        collab_channel.add_group_member(group_id, self.agent_id)
        
        # Créer les critères de filtrage
        if filter_criteria is None:
            filter_criteria = {}
        
        filter_criteria["metadata.group_id"] = group_id
        
        # S'abonner au canal de collaboration
        subscription_id = collab_channel.subscribe(
            subscriber_id=self.agent_id,
            callback=callback,
            filter_criteria=filter_criteria
        )
        
        self.logger.info(f"Subscribed to collaboration group {group_id}")
        return subscription_id
    
    def get_data(
        self,
        data_id: str,
        version_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Récupère des données du canal de données.
        
        Args:
            data_id: Identifiant des données
            version_id: Identifiant de version (None pour la dernière version)
            
        Returns:
            Les données récupérées
        """
        try:
            # Récupérer les données via le canal de données
            data_channel = self.middleware.get_channel(ChannelType.DATA)
            data, metadata = data_channel.get_data(data_id, version_id)
            
            self.logger.info(f"Data {data_id} retrieved successfully")
            return data
            
        except Exception as e:
            self.logger.error(f"Error retrieving data {data_id}: {str(e)}")
            return {}