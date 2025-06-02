"""
Adaptateur pour les agents tactiques dans le système de communication multi-canal.

Cet adaptateur sert d'interface entre les agents tactiques et le middleware
de messagerie, traduisant les appels d'API spécifiques aux agents tactiques
en messages standardisés compréhensibles par le middleware.
"""

import uuid
import logging
import time # Ajout de l'import manquant
from typing import Dict, Any, Optional, List, Callable, Union
from datetime import datetime

from .message import Message, MessageType, MessagePriority, AgentLevel
from .channel_interface import ChannelType
from .middleware import MessageMiddleware

from argumentation_analysis.paths import DATA_DIR



class TacticalAdapter:
    """
    Adaptateur pour les agents tactiques.
    
    Cet adaptateur fournit une interface simplifiée pour les agents tactiques,
    leur permettant de recevoir des directives stratégiques, d'assigner des tâches
    aux agents opérationnels, et de collaborer avec d'autres agents tactiques.
    """
    
    def __init__(self, agent_id: str, middleware: MessageMiddleware):
        """
        Initialise un nouvel adaptateur pour un agent tactique.
        
        Args:
            agent_id: Identifiant de l'agent tactique
            middleware: Le middleware de messagerie à utiliser
        """
        self.agent_id = agent_id
        self.middleware = middleware
        self.logger = logging.getLogger(f"TacticalAdapter.{agent_id}")
        self.logger.setLevel(logging.INFO)
    
    def receive_directive(
        self,
        timeout: Optional[float] = None,
        filter_criteria: Optional[Dict[str, Any]] = None
    ) -> Optional[Message]:
        """
        Reçoit une directive stratégique.
        
        Args:
            timeout: Délai d'attente maximum en secondes (None pour attente indéfinie)
            filter_criteria: Critères de filtrage des directives (optionnel)
            
        Returns:
            La directive reçue ou None si timeout
        """
        # Recevoir un message via le middleware
        message = self.middleware.receive_message(
            recipient_id=self.agent_id,
            channel_type=ChannelType.HIERARCHICAL,
            timeout=timeout
        )
        
        if message:
            # Vérifier si le message est une directive
            is_directive = (
                message.type == MessageType.COMMAND and
                message.sender_level == AgentLevel.STRATEGIC
            )
            
            if is_directive:
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
                    ack.sender_level = AgentLevel.TACTICAL
                    self.middleware.send_message(ack)
                
                self.logger.info(f"Directive received from {message.sender}")
                return message
        
        return None
    
    def assign_task(
        self,
        task_type: str,
        parameters: Dict[str, Any],
        recipient_id: str,
        constraints: Optional[Dict[str, Any]] = None,
        priority: MessagePriority = MessagePriority.NORMAL,
        requires_ack: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Assigne une tâche à un agent opérationnel.
        
        Args:
            task_type: Type de tâche (analyze_text, detect_fallacies, etc.)
            parameters: Paramètres de la tâche
            recipient_id: Identifiant de l'agent opérationnel
            constraints: Contraintes d'exécution (optionnel)
            priority: Priorité de la tâche
            requires_ack: Indique si un accusé de réception est requis
            metadata: Métadonnées additionnelles (optionnel)
            
        Returns:
            L'identifiant de la tâche assignée
        """
        # Créer le message de tâche
        message = Message(
            message_type=MessageType.COMMAND,
            sender=self.agent_id,
            sender_level=AgentLevel.TACTICAL,
            content={
                "command_type": task_type,
                "parameters": parameters,
                "constraints": constraints or {}
            },
            recipient=recipient_id,
            channel=ChannelType.HIERARCHICAL.value,
            priority=priority,
            metadata={
                "conversation_id": f"task-{uuid.uuid4().hex[:8]}",
                "requires_ack": requires_ack,
                **(metadata or {})
            }
        )
        
        # Envoyer le message via le middleware
        success = self.middleware.send_message(message)
        
        if success:
            self.logger.info(f"Task {task_type} assigned to {recipient_id}")
        else:
            self.logger.error(f"Failed to assign task {task_type} to {recipient_id}")
        
        return message.id
    
    def send_report(
        self,
        report_type: str,
        content: Dict[str, Any],
        recipient_id: str,
        priority: MessagePriority = MessagePriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Envoie un rapport à un agent stratégique.
        
        Args:
            report_type: Type de rapport (status_update, analysis_results, etc.)
            content: Contenu du rapport
            recipient_id: Identifiant de l'agent stratégique
            priority: Priorité du rapport
            metadata: Métadonnées additionnelles (optionnel)
            
        Returns:
            L'identifiant du rapport envoyé
        """
        # Créer le message de rapport
        message = Message(
            message_type=MessageType.INFORMATION,
            sender=self.agent_id,
            sender_level=AgentLevel.TACTICAL,
            content={
                "info_type": "report",
                "report_type": report_type,
                "data": content
            },
            recipient=recipient_id,
            channel=ChannelType.HIERARCHICAL.value,
            priority=priority,
            metadata=metadata
        )
        
        # Envoyer le message via le middleware
        success = self.middleware.send_message(message)
        
        if success:
            self.logger.info(f"Report {report_type} sent to {recipient_id}")
        else:
            self.logger.error(f"Failed to send report {report_type} to {recipient_id}")
        
        return message.id
    
    def receive_task_result(
        self,
        timeout: Optional[float] = None,
        filter_criteria: Optional[Dict[str, Any]] = None
    ) -> Optional[Message]:
        """
        Reçoit un résultat de tâche d'un agent opérationnel.
        Boucle jusqu'à ce qu'un message de résultat de tâche soit trouvé ou que le timeout expire.
        
        Args:
            timeout: Délai d'attente maximum en secondes (None pour attente indéfinie)
            filter_criteria: Critères de filtrage pour le contenu du résultat (optionnel)
            
        Returns:
            Le résultat reçu ou None si timeout
        """
        start_time = time.monotonic()
        
        while True:
            current_timeout = None
            if timeout is not None:
                elapsed_time = time.monotonic() - start_time
                remaining_timeout = timeout - elapsed_time
                if remaining_timeout <= 0:
                    self.logger.warning(f"Timeout ({timeout}s) expired while waiting for task result for {self.agent_id}.")
                    return None
                current_timeout = remaining_timeout

            message = self.middleware.receive_message(
                recipient_id=self.agent_id,
                channel_type=ChannelType.HIERARCHICAL,
                timeout=current_timeout
            )
            
            if message:
                is_result_type = (
                    message.type == MessageType.INFORMATION and
                    message.sender_level == AgentLevel.OPERATIONAL and
                    message.content.get("info_type") == "task_result"
                )
                
                if is_result_type:
                    # Appliquer les critères de filtrage supplémentaires sur le contenu du message
                    if filter_criteria:
                        match = True
                        # Accéder au contenu potentiellement sous DATA_DIR
                        actual_content_payload = message.content.get(DATA_DIR, message.content)
                        if not isinstance(actual_content_payload, dict): # S'assurer que c'est un dict pour la recherche par clé
                            actual_content_payload = message.content

                        for key, expected_value in filter_criteria.items():
                            # Vérifier si la clé existe dans le payload ou au niveau supérieur du contenu
                            if key in actual_content_payload:
                                actual_value = actual_content_payload[key]
                            elif key in message.content: # Fallback au niveau supérieur si pas dans DATA_DIR
                                 actual_value = message.content[key]
                            else: # Clé non trouvée
                                match = False
                                break
                            
                            # Comparer la valeur
                            if isinstance(expected_value, list):
                                if actual_value not in expected_value:
                                    match = False
                                    break
                            elif actual_value != expected_value:
                                match = False
                                break
                        
                        if not match:
                            self.logger.debug(f"Message {message.id} (task_result) received by {self.agent_id} but did not match filter_criteria. Continuing to wait.")
                            continue # Ne correspond pas au filtre, continuer à chercher
                    
                    self.logger.info(f"Task result {message.id} received from {message.sender} by {self.agent_id} and matches criteria.")
                    return message
                else:
                    self.logger.debug(f"Ignored message {message.id} (type: {message.type}, info_type: {message.content.get('info_type')}) by {self.agent_id} while waiting for task_result.")
            
            # Si message is None (timeout de receive_message) et timeout global n'est pas encore atteint, la boucle continue.
            # Si timeout global est atteint, la condition au début de la boucle (remaining_timeout <= 0) gérera la sortie.
            if timeout is None and not message: # Si attente indéfinie et rien reçu, petit sleep pour éviter busy-loop sur des messages non pertinents
                time.sleep(0.01)
            elif timeout is not None and not message and current_timeout is not None and current_timeout <= 0: # Vérifier si le current_timeout calculé était déjà <=0
                 self.logger.warning(f"Timeout ({timeout}s) confirmed for {self.agent_id} as current_timeout was <=0 before receive_message.")
                 return None
            elif timeout is not None and not message : # Si receive_message a timeout (current_timeout > 0 initialement)
                 # La boucle while vérifiera le timeout global au prochain tour.
                 # Si remaining_timeout devient <=0, on sortira.
                 pass


        # Normalement, ne devrait pas être atteint si timeout est None, car la boucle est infinie.
        # Si timeout est spécifié, la condition de sortie est au début de la boucle.
        self.logger.error(f"Exited receive_task_result loop unexpectedly for {self.agent_id}.")
        return None
    
    def request_strategic_guidance(
        self,
        request_type: str,
        parameters: Dict[str, Any],
        recipient_id: str,
        timeout: float = 30.0,
        priority: MessagePriority = MessagePriority.NORMAL
    ) -> Optional[Dict[str, Any]]:
        """
        Demande des conseils à un agent stratégique.
        
        Args:
            request_type: Type de requête (clarification, resource_request, etc.)
            parameters: Paramètres de la requête
            recipient_id: Identifiant de l'agent stratégique
            timeout: Délai d'attente maximum en secondes
            priority: Priorité de la requête
            
        Returns:
            Les conseils demandés ou None si timeout
        """
        try:
            # Utiliser le protocole de requête-réponse du middleware
            response = self.middleware.send_request(
                sender=self.agent_id,
                sender_level=AgentLevel.TACTICAL,
                recipient=recipient_id,
                request_type=request_type,
                content=parameters,
                timeout=timeout,
                retry_count=1,  # Ajouter un réessai pour plus de robustesse
                retry_delay=1.0,
                priority=priority,
                channel=ChannelType.HIERARCHICAL.value
            )
            
            if response:
                self.logger.info(f"Received guidance from {recipient_id} for {request_type} request")
                # DATA_DIR est la clé correcte utilisée dans les tests et la logique de message
                return response.content.get(DATA_DIR)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error requesting guidance from {recipient_id}: {str(e)}")
            return None
    
    async def request_strategic_guidance_async(
        self,
        request_type: str,
        parameters: Dict[str, Any],
        recipient_id: str,
        timeout: float = 30.0,
        priority: MessagePriority = MessagePriority.NORMAL
    ) -> Optional[Dict[str, Any]]:
        """
        Version asynchrone de request_strategic_guidance.
        
        Args:
            request_type: Type de requête (clarification, resource_request, etc.)
            parameters: Paramètres de la requête
            recipient_id: Identifiant de l'agent stratégique
            timeout: Délai d'attente maximum en secondes
            priority: Priorité de la requête
            
        Returns:
            Les conseils demandés ou None si timeout
        """
        try:
            # Envoyer la requête via le protocole de requête-réponse
            response = await self.middleware.send_request_async(
                sender=self.agent_id,
                sender_level=AgentLevel.TACTICAL,
                recipient=recipient_id,
                request_type=request_type,
                content=parameters,
                timeout=timeout,
                priority=priority,
                channel=ChannelType.HIERARCHICAL.value
            )
            
            if response:
                self.logger.info(f"Received guidance from {recipient_id} for {request_type} request")
                # DATA_DIR est la clé correcte
                return response.content.get(DATA_DIR)
            
            self.logger.warning(f"Request {request_type} to {recipient_id} timed out")
            return None
            
        except Exception as e:
            self.logger.error(f"Error requesting guidance from {recipient_id}: {str(e)}")
            return None
    
    def collaborate_with_tactical(
        self,
        collaboration_type: str,
        content: Dict[str, Any],
        recipient_ids: List[str],
        group_id: Optional[str] = None,
        priority: MessagePriority = MessagePriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Collabore avec d'autres agents tactiques.
        
        Args:
            collaboration_type: Type de collaboration (task_coordination, resource_sharing, etc.)
            content: Contenu de la collaboration
            recipient_ids: Liste des identifiants des agents tactiques destinataires
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
                name=f"Tactical Collaboration: {collaboration_type}",
                description=f"Collaboration between tactical agents for {collaboration_type}",
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
            sender_level=AgentLevel.TACTICAL,
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
    
    def share_task_data(
        self,
        data_type: str,
        data: Dict[str, Any],
        recipient_ids: Optional[List[str]] = None,
        compress: bool = True,
        priority: MessagePriority = MessagePriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Partage des données de tâche avec d'autres agents.
        
        Args:
            data_type: Type de données (task_results, analysis_data, etc.)
            data: Les données à partager
            recipient_ids: Liste des identifiants des destinataires (None pour tous les agents tactiques)
            compress: Indique si les données doivent être compressées
            priority: Priorité du message
            metadata: Métadonnées additionnelles (optionnel)
            
        Returns:
            L'identifiant du message de données
        """
        # Stocker les données dans le canal de données
        data_channel = self.middleware.get_channel(ChannelType.DATA)
        data_id = f"tactical-data-{uuid.uuid4().hex[:8]}"
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
            sender_level=AgentLevel.TACTICAL,
            content={
                "info_type": "tactical_data",
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
            # Publier les données pour tous les agents tactiques
            topic_id = f"tactical_data.{data_type}"
            self.middleware.publish(
                topic_id=topic_id,
                sender=self.agent_id,
                sender_level=AgentLevel.TACTICAL,
                content=message.content,
                priority=priority,
                metadata=message.metadata
            )
        
        self.logger.info(f"Tactical data {data_type} shared with {len(recipient_ids) if recipient_ids else 'all tactical agents'}")
        return data_id
    
    def get_pending_directives(self, max_count: Optional[int] = None) -> List[Message]:
        """
        Récupère les directives stratégiques en attente.
        
        Args:
            max_count: Nombre maximum de directives à récupérer (None pour toutes)
            
        Returns:
            Liste des directives en attente
        """
        # Récupérer les messages en attente via le middleware
        messages = self.middleware.get_pending_messages(
            recipient_id=self.agent_id,
            channel_type=ChannelType.HIERARCHICAL,
            max_count=max_count
        )
        
        # Filtrer les directives
        directives = [
            message for message in messages
            if message.type == MessageType.COMMAND and
            message.sender_level == AgentLevel.STRATEGIC
        ]
        
        self.logger.info(f"Retrieved {len(directives)} pending directives")
        return directives
    
    def get_pending_task_results(self, max_count: Optional[int] = None) -> List[Message]:
        """
        Récupère les résultats de tâche en attente.
        
        Args:
            max_count: Nombre maximum de résultats à récupérer (None pour tous)
            
        Returns:
            Liste des résultats en attente
        """
        # Récupérer les messages en attente via le middleware
        messages = self.middleware.get_pending_messages(
            recipient_id=self.agent_id,
            channel_type=ChannelType.HIERARCHICAL,
            max_count=max_count
        )
        
        # Filtrer les résultats de tâche
        results = [
            message for message in messages
            if message.type == MessageType.INFORMATION and
            message.sender_level == AgentLevel.OPERATIONAL and
            message.content.get("info_type") == "task_result"
        ]
        
        self.logger.info(f"Retrieved {len(results)} pending task results")
        return results
    
    def subscribe_to_operational_updates(
        self,
        update_types: List[str],
        callback: Callable[[Message], None],
        filter_criteria: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        S'abonne aux mises à jour des agents opérationnels.
        
        Args:
            update_types: Types de mises à jour (task_progress, resource_usage, etc.)
            callback: Fonction de rappel à appeler lors de la réception d'une mise à jour
            filter_criteria: Critères de filtrage des mises à jour (optionnel)
            
        Returns:
            Un identifiant d'abonnement
        """
        # Créer les critères de filtrage
        if filter_criteria is None:
            filter_criteria = {}
        
        filter_criteria["info_type"] = "operational_update"
        filter_criteria["update_type"] = update_types
        
        # S'abonner au canal hiérarchique
        subscription_id = self.middleware.get_channel(ChannelType.HIERARCHICAL).subscribe(
            subscriber_id=self.agent_id,
            callback=callback,
            filter_criteria=filter_criteria
        )
        
        self.logger.info(f"Subscribed to operational updates: {', '.join(update_types)}")
        return subscription_id
    
    def send_status_update(
        self,
        update_type: str,
        status: Dict[str, Any],
        recipient_id: Optional[str] = None,
        priority: MessagePriority = MessagePriority.NORMAL
    ) -> str:
        """
        Envoie une mise à jour de statut à un agent stratégique.
        
        Args:
            update_type: Type de mise à jour (task_progress, resource_usage, etc.)
            status: Contenu de la mise à jour
            recipient_id: Identifiant de l'agent stratégique (None pour tous)
            priority: Priorité de la mise à jour
            
        Returns:
            L'identifiant de la mise à jour envoyée
        """
        # Créer le message de mise à jour
        message = Message(
            message_type=MessageType.INFORMATION,
            sender=self.agent_id,
            sender_level=AgentLevel.TACTICAL,
            content={
                "info_type": "tactical_update",
                "update_type": update_type,
                DATA_DIR: status
            },
            recipient=recipient_id,
            channel=ChannelType.HIERARCHICAL.value,
            priority=priority
        )
        
        if recipient_id:
            # Envoyer le message directement
            success = self.middleware.send_message(message)
            
            if success:
                self.logger.info(f"Status update {update_type} sent to {recipient_id}")
            else:
                self.logger.error(f"Failed to send status update {update_type} to {recipient_id}")
        else:
            # Publier la mise à jour pour tous les agents stratégiques
            topic_id = f"tactical_updates.{update_type}"
            self.middleware.publish(
                topic_id=topic_id,
                sender=self.agent_id,
                sender_level=AgentLevel.TACTICAL,
                content=message.content,
                priority=priority
            )
            
            self.logger.info(f"Status update {update_type} published to all strategic agents")
        
        return message.id