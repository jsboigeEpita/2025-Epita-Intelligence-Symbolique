"""
Adaptateur pour les agents stratégiques dans le système de communication multi-canal.

Cet adaptateur sert d'interface entre les agents stratégiques et le middleware
de messagerie, traduisant les appels d'API spécifiques aux agents stratégiques
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



class StrategicAdapter:
    """
    Adaptateur pour les agents stratégiques.
    
    Cet adaptateur fournit une interface simplifiée pour les agents stratégiques,
    leur permettant d'émettre des directives, de recevoir des rapports et de
    communiquer avec d'autres agents stratégiques.
    """
    
    def __init__(self, agent_id: str, middleware: MessageMiddleware):
        """
        Initialise un nouvel adaptateur pour un agent stratégique.
        
        Args:
            agent_id: Identifiant de l'agent stratégique
            middleware: Le middleware de messagerie à utiliser
        """
        self.agent_id = agent_id
        self.middleware = middleware
        self.logger = logging.getLogger(f"StrategicAdapter.{agent_id}")
        self.logger.setLevel(logging.INFO)
    
    def issue_directive(
        self,
        directive_type: str,
        parameters: Dict[str, Any],
        recipient_id: Optional[str] = None,
        priority: MessagePriority = MessagePriority.HIGH,
        requires_ack: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Émet une directive stratégique à destination d'un ou plusieurs agents tactiques.
        
        Args:
            directive_type: Type de directive (analyze_text, allocate_resources, etc.)
            content: Contenu de la directive
            recipient_id: Identifiant du destinataire tactique (None pour tous les agents tactiques)
            priority: Priorité de la directive
            requires_ack: Indique si un accusé de réception est requis
            metadata: Métadonnées additionnelles (optionnel)
            
        Returns:
            L'identifiant de la directive émise
        """
        # Créer le message de directive
        message = Message(
            message_type=MessageType.COMMAND,
            sender=self.agent_id,
            sender_level=AgentLevel.STRATEGIC,
            content={
                "command_type": directive_type,
                "parameters": parameters
            },
            recipient=recipient_id,
            channel=ChannelType.HIERARCHICAL.value,
            priority=priority,
            metadata={
                "conversation_id": f"dir-{uuid.uuid4().hex[:8]}",
                "requires_ack": requires_ack,
                **(metadata or {})
            }
        )
        
        # Envoyer le message via le middleware
        success = self.middleware.send_message(message)
        
        if success:
            self.logger.info(f"Directive {directive_type} issued to {recipient_id or 'all tactical agents'}")
        else:
            self.logger.error(f"Failed to issue directive {directive_type}")
        
        return message.id
    
    def broadcast_objective(
        self,
        objective_type: str,
        content: Dict[str, Any],
        priority: MessagePriority = MessagePriority.HIGH,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Diffuse un objectif global à tous les agents.
        
        Args:
            objective_type: Type d'objectif (global_strategy, performance_target, etc.)
            content: Contenu de l'objectif
            priority: Priorité de l'objectif
            metadata: Métadonnées additionnelles (optionnel)
            
        Returns:
            L'identifiant de l'objectif diffusé
        """
        # Créer le message d'objectif
        message = Message(
            message_type=MessageType.INFORMATION,
            sender=self.agent_id,
            sender_level=AgentLevel.STRATEGIC,
            content={
                "info_type": "global_objective",
                "objective_type": objective_type,
                DATA_DIR: content
            },
            recipient=None,  # Broadcast
            channel=ChannelType.HIERARCHICAL.value,
            priority=priority,
            metadata={
                "broadcast": True,
                **(metadata or {})
            }
        )
        
        # Publier le message via le middleware
        topic_id = f"objectives.{objective_type}"
        recipients = self.middleware.publish(
            topic_id=topic_id,
            sender=self.agent_id,
            sender_level=AgentLevel.STRATEGIC,
            content=message.content,
            priority=priority,
            metadata=message.metadata
        )
        
        self.logger.info(f"Objective {objective_type} broadcasted to {len(recipients)} agents")
        return message.id
    
    def receive_report(
        self,
        timeout: Optional[float] = None,
        filter_criteria: Optional[Dict[str, Any]] = None
    ) -> Optional[Message]:
        """
        Reçoit un rapport tactique.
        
        Args:
            timeout: Délai d'attente maximum en secondes (None pour attente indéfinie)
            filter_criteria: Critères de filtrage des rapports (optionnel)
            
        Returns:
            Le rapport reçu ou None si timeout
        """
        # Recevoir un message via le middleware
        message = self.middleware.receive_message(
            recipient_id=self.agent_id,
            channel_type=ChannelType.HIERARCHICAL,
            timeout=timeout
        )
        
        if message:
            # Vérifier si le message est un rapport
            is_report = (
                message.type == MessageType.INFORMATION and
                message.content.get("info_type") == "report"
            )
            
            if is_report:
                # Vérifier les critères de filtrage
                if filter_criteria:
                    for key, value in filter_criteria.items():
                        if key in message.content:
                            if isinstance(value, list):
                                if message.content[key] not in value:
                                    return None
                            elif message.content[key] != value:
                                return None
                
                self.logger.info(f"Report received from {message.sender}")
                return message
        
        return None
    
    def request_tactical_info(
        self,
        request_type: str,
        parameters: Dict[str, Any],
        recipient_id: str,
        timeout: float = 30.0,
        priority: MessagePriority = MessagePriority.NORMAL
    ) -> Optional[Dict[str, Any]]:
        """
        Demande des informations à un agent tactique.
        
        Args:
            request_type: Type de requête (status_update, resource_usage, etc.)
            parameters: Paramètres de la requête
            recipient_id: Identifiant de l'agent tactique
            timeout: Délai d'attente maximum en secondes
            priority: Priorité de la requête
            
        Returns:
            Les informations demandées ou None si timeout
        """
        try:
            # Envoyer la requête via le protocole de requête-réponse
            response = self.middleware.send_request(
                sender=self.agent_id,
                sender_level=AgentLevel.STRATEGIC,
                recipient=recipient_id,
                request_type=request_type,
                content=parameters,
                timeout=timeout,
                priority=priority,
                channel=ChannelType.HIERARCHICAL.value
            )
            
            if response:
                self.logger.info(f"Received response to {request_type} request from {recipient_id}")
                return response.content.get(DATA_DIR)
            
            self.logger.warning(f"Request {request_type} to {recipient_id} timed out")
            return None
            
        except Exception as e:
            self.logger.error(f"Error requesting information from {recipient_id}: {str(e)}")
            return None
    
    async def request_tactical_info_async(
        self,
        request_type: str,
        parameters: Dict[str, Any],
        recipient_id: str,
        timeout: float = 30.0,
        priority: MessagePriority = MessagePriority.NORMAL
    ) -> Optional[Dict[str, Any]]:
        """
        Version asynchrone de request_tactical_info.
        
        Args:
            request_type: Type de requête (status_update, resource_usage, etc.)
            parameters: Paramètres de la requête
            recipient_id: Identifiant de l'agent tactique
            timeout: Délai d'attente maximum en secondes
            priority: Priorité de la requête
            
        Returns:
            Les informations demandées ou None si timeout
        """
        try:
            # Envoyer la requête via le protocole de requête-réponse
            response = await self.middleware.send_request_async(
                sender=self.agent_id,
                sender_level=AgentLevel.STRATEGIC,
                recipient=recipient_id,
                request_type=request_type,
                content=parameters,
                timeout=timeout,
                priority=priority,
                channel=ChannelType.HIERARCHICAL.value
            )
            
            if response:
                self.logger.info(f"Received response to {request_type} request from {recipient_id}")
                return response.content.get(DATA_DIR)
            
            self.logger.warning(f"Request {request_type} to {recipient_id} timed out")
            return None
            
        except Exception as e:
            self.logger.error(f"Error requesting information from {recipient_id}: {str(e)}")
            return None
    
    def collaborate_with_strategic(
        self,
        collaboration_type: str,
        content: Dict[str, Any],
        recipient_ids: List[str],
        group_id: Optional[str] = None,
        priority: MessagePriority = MessagePriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Collabore avec d'autres agents stratégiques.
        
        Args:
            collaboration_type: Type de collaboration (joint_planning, resource_sharing, etc.)
            content: Contenu de la collaboration
            recipient_ids: Liste des identifiants des agents stratégiques destinataires
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
                name=f"Strategic Collaboration: {collaboration_type}",
                description=f"Collaboration between strategic agents for {collaboration_type}",
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
            sender_level=AgentLevel.STRATEGIC,
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
    
    def share_strategic_data(
        self,
        data_type: str,
        data: Dict[str, Any],
        recipient_ids: Optional[List[str]] = None,
        compress: bool = True,
        priority: MessagePriority = MessagePriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Partage des données stratégiques avec d'autres agents.
        
        Args:
            data_type: Type de données (strategic_plan, performance_metrics, etc.)
            data: Les données à partager
            recipient_ids: Liste des identifiants des destinataires (None pour tous les agents stratégiques)
            compress: Indique si les données doivent être compressées
            priority: Priorité du message
            metadata: Métadonnées additionnelles (optionnel)
            
        Returns:
            L'identifiant du message de données
        """
        # Stocker les données dans le canal de données
        data_channel = self.middleware.get_channel(ChannelType.DATA)
        data_id = f"strategic-data-{uuid.uuid4().hex[:8]}"
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
            sender_level=AgentLevel.STRATEGIC,
            content={
                "info_type": "strategic_data",
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
            # Publier les données pour tous les agents stratégiques
            topic_id = f"strategic_data.{data_type}"
            self.middleware.publish(
                topic_id=topic_id,
                sender=self.agent_id,
                sender_level=AgentLevel.STRATEGIC,
                content=message.content,
                priority=priority,
                metadata=message.metadata
            )
        
        self.logger.info(f"Strategic data {data_type} shared with {len(recipient_ids) if recipient_ids else 'all strategic agents'}")
        return data_id
    
    def get_pending_reports(self, max_count: Optional[int] = None) -> List[Message]:
        """
        Récupère les rapports tactiques en attente.
        
        Args:
            max_count: Nombre maximum de rapports à récupérer (None pour tous)
            
        Returns:
            Liste des rapports en attente
        """
        # Récupérer les messages en attente via le middleware
        messages = self.middleware.get_pending_messages(
            recipient_id=self.agent_id,
            channel_type=ChannelType.HIERARCHICAL,
            max_count=max_count
        )
        
        # Filtrer les rapports
        reports = [
            message for message in messages
            if message.type == MessageType.INFORMATION and
            message.content.get("info_type") == "report"
        ]
        
        self.logger.info(f"Retrieved {len(reports)} pending reports")
        return reports
    
    def subscribe_to_tactical_updates(
        self,
        update_types: List[str],
        callback: Callable[[Message], None],
        filter_criteria: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        S'abonne aux mises à jour des agents tactiques.
        
        Args:
            update_types: Types de mises à jour (status_update, resource_usage, etc.)
            callback: Fonction de rappel à appeler lors de la réception d'une mise à jour
            filter_criteria: Critères de filtrage des mises à jour (optionnel)
            
        Returns:
            Un identifiant d'abonnement
        """
        # Créer les critères de filtrage
        if filter_criteria is None:
            filter_criteria = {}
        
        filter_criteria["info_type"] = "tactical_update"
        filter_criteria["update_type"] = update_types
        
        # S'abonner au canal hiérarchique
        subscription_id = self.middleware.get_channel(ChannelType.HIERARCHICAL).subscribe(
            subscriber_id=self.agent_id,
            callback=callback,
            filter_criteria=filter_criteria
        )
        
        self.logger.info(f"Subscribed to tactical updates: {', '.join(update_types)}")
        return subscription_id
        
    def allocate_resources(
        self,
        resource_type: str,
        amount: int,
        recipient_id: str,
        priority: MessagePriority = MessagePriority.HIGH,
        requires_ack: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Alloue des ressources à un agent tactique.
        
        Args:
            resource_type: Type de ressource (cpu, memory, etc.)
            amount: Quantité de ressources à allouer
            recipient_id: Identifiant de l'agent tactique
            priority: Priorité de l'allocation
            requires_ack: Indique si un accusé de réception est requis
            metadata: Métadonnées additionnelles (optionnel)
            
        Returns:
            L'identifiant de l'allocation émise
        """
        # Créer le message d'allocation
        message = Message(
            message_type=MessageType.COMMAND,
            sender=self.agent_id,
            sender_level=AgentLevel.STRATEGIC,
            content={
                "command_type": "allocate_resources",
                "parameters": {
                    "resource_type": resource_type,
                    "amount": amount
                }
            },
            recipient=recipient_id,
            channel=ChannelType.HIERARCHICAL.value,
            priority=priority,
            metadata={
                "conversation_id": f"alloc-{uuid.uuid4().hex[:8]}",
                "requires_ack": requires_ack,
                **(metadata or {})
            }
        )
        
        # Envoyer le message via le middleware
        success = self.middleware.send_message(message)
        
        if success:
            self.logger.info(f"Resources {resource_type} allocated to {recipient_id}")
        else:
            self.logger.error(f"Failed to allocate resources {resource_type} to {recipient_id}")
        
        return message.id
        
    def broadcast_announcement(
        self,
        announcement_type: str,
        content: Dict[str, Any],
        priority: MessagePriority = MessagePriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Diffuse une annonce à tous les agents.
        
        Args:
            announcement_type: Type d'annonce (system_update, policy_change, etc.)
            content: Contenu de l'annonce
            priority: Priorité de l'annonce
            metadata: Métadonnées additionnelles (optionnel)
            
        Returns:
            L'identifiant de l'annonce diffusée
        """
        # Créer le message d'annonce
        message = Message(
            message_type=MessageType.INFORMATION,
            sender=self.agent_id,
            sender_level=AgentLevel.STRATEGIC,
            content={
                "info_type": "announcement",
                "announcement_type": announcement_type,
                DATA_DIR: content
            },
            recipient=None,  # Broadcast
            channel=ChannelType.HIERARCHICAL.value,
            priority=priority,
            metadata={
                "broadcast": True,
                **(metadata or {})
            }
        )
        
        # Publier le message via le middleware
        topic_id = f"announcements.{announcement_type}"
        recipients = self.middleware.publish(
            topic_id=topic_id,
            sender=self.agent_id,
            sender_level=AgentLevel.STRATEGIC,
            content=message.content,
            priority=priority,
            metadata=message.metadata
        )
        
        self.logger.info(f"Announcement {announcement_type} broadcasted to {len(recipients)} agents")
        return message.id
        
    def receive_guidance_request(
        self,
        timeout: Optional[float] = None,
        filter_criteria: Optional[Dict[str, Any]] = None
    ) -> Optional[Message]:
        """
        Reçoit une demande de conseils d'un agent tactique.
        
        Args:
            timeout: Délai d'attente maximum en secondes (None pour attente indéfinie)
            filter_criteria: Critères de filtrage des demandes (optionnel)
            
        Returns:
            La demande reçue ou None si timeout
        """
        # Recevoir un message via le middleware
        message = self.middleware.receive_message(
            recipient_id=self.agent_id,
            channel_type=ChannelType.HIERARCHICAL,
            timeout=timeout
        )
        
        if message:
            # Vérifier si le message est une demande de conseils
            is_guidance_request = (
                message.type == MessageType.REQUEST and
                message.sender_level == AgentLevel.TACTICAL and
                message.content.get("request_type") == "guidance"
            )
            
            if is_guidance_request:
                # Vérifier les critères de filtrage
                if filter_criteria:
                    for key, value in filter_criteria.items():
                        if key in message.content:
                            if isinstance(value, list):
                                if message.content[key] not in value:
                                    return None
                            elif message.content[key] != value:
                                return None
                
                self.logger.info(f"Guidance request received from {message.sender}")
                return message
        
        return None
        
    def provide_guidance(
        self,
        request_id: str,
        guidance: Dict[str, Any],
        priority: MessagePriority = MessagePriority.HIGH,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Fournit des conseils en réponse à une demande.
        
        Args:
            request_id: Identifiant de la demande
            guidance: Contenu des conseils
            priority: Priorité de la réponse
            metadata: Métadonnées additionnelles (optionnel)
            
        Returns:
            L'identifiant de la réponse envoyée
        """
        # Créer le message de réponse
        message = Message(
            message_type=MessageType.RESPONSE,
            sender=self.agent_id,
            sender_level=AgentLevel.STRATEGIC,
            content={
                "status": "success",
                DATA_DIR: guidance
            },
            recipient=None,  # Sera défini par le middleware
            channel=ChannelType.HIERARCHICAL.value,
            priority=priority,
            metadata={
                "reply_to": request_id,
                **(metadata or {})
            }
        )
        
        # Envoyer le message via le middleware
        success = self.middleware.send_message(message)
        
        if success:
            self.logger.info(f"Guidance provided in response to request {request_id}")
        else:
            self.logger.error(f"Failed to provide guidance for request {request_id}")
        
        return message.id