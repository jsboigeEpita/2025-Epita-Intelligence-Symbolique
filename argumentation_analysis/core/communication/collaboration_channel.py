"""
Implémentation du canal de collaboration pour le système de communication multi-canal.

Ce canal facilite les interactions horizontales entre agents de même niveau,
permettant la coordination, le partage d'informations et la résolution
collaborative de problèmes.
"""

import uuid
import threading
import logging
from typing import Dict, Any, Optional, List, Callable, Set
from datetime import datetime
from collections import defaultdict

from .channel_interface import Channel, ChannelType, ChannelException
from .message import Message, MessageType, MessagePriority, AgentLevel


class CollaborationGroup:
    """
    Représentation d'un groupe de collaboration entre agents.

    Un groupe de collaboration est un espace partagé où plusieurs agents
    peuvent échanger des messages et coordonner leurs activités.
    """

    def __init__(
        self,
        group_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        members: Optional[List[str]] = None,
    ):
        """
        Initialise un nouveau groupe de collaboration.

        Args:
            group_id: Identifiant unique du groupe
            name: Nom du groupe (optionnel)
            description: Description du groupe (optionnel)
            members: Liste des identifiants des membres initiaux (optionnel)
        """
        self.id = group_id
        self.name = name or f"Group-{group_id}"
        self.description = description
        self.members = set(members or [])
        self.messages = []
        self.created_at = datetime.now()
        self.lock = threading.RLock()

    def add_member(self, member_id: str) -> bool:
        """
        Ajoute un membre au groupe.

        Args:
            member_id: Identifiant du membre à ajouter

        Returns:
            True si le membre a été ajouté, False s'il était déjà présent
        """
        with self.lock:
            if member_id in self.members:
                return False

            self.members.add(member_id)
            return True

    def remove_member(self, member_id: str) -> bool:
        """
        Retire un membre du groupe.

        Args:
            member_id: Identifiant du membre à retirer

        Returns:
            True si le membre a été retiré, False s'il n'était pas présent
        """
        with self.lock:
            if member_id not in self.members:
                return False

            self.members.remove(member_id)
            return True

    def add_message(self, message: Message) -> None:
        """
        Ajoute un message à l'historique du groupe.

        Args:
            message: Le message à ajouter
        """
        with self.lock:
            self.messages.append({"message": message, "timestamp": datetime.now()})

    def get_messages(self, count: Optional[int] = None) -> List[Message]:
        """
        Récupère les messages récents du groupe.

        Args:
            count: Nombre maximum de messages à récupérer (None pour tous)

        Returns:
            Liste des messages récents
        """
        with self.lock:
            messages = [entry["message"] for entry in self.messages]

            if count is not None:
                messages = messages[-count:]

            return messages

    def get_member_count(self) -> int:
        """
        Récupère le nombre de membres du groupe.

        Returns:
            Le nombre de membres
        """
        with self.lock:
            return len(self.members)

    def get_group_info(self) -> Dict[str, Any]:
        """
        Récupère des informations sur le groupe.

        Returns:
            Un dictionnaire d'informations sur le groupe
        """
        with self.lock:
            return {
                "id": self.id,
                "name": self.name,
                "description": self.description,
                "member_count": len(self.members),
                "message_count": len(self.messages),
                "created_at": self.created_at.isoformat(),
            }


class CollaborationChannel(Channel):
    """
    Canal de communication pour la collaboration entre agents de même niveau.

    Ce canal supporte les communications many-to-many, la création de groupes
    de collaboration et le partage de contexte entre agents.
    """

    def __init__(self, channel_id: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialise un nouveau canal de collaboration.

        Args:
            channel_id: Identifiant unique du canal
            config: Configuration spécifique au canal (optionnel)
        """
        super().__init__(channel_id, ChannelType.COLLABORATION, config)

        # Groupes de collaboration
        self.groups = {}

        # Messages directs entre agents
        self.direct_messages = defaultdict(list)

        # Verrou pour les opérations concurrentes
        self.lock = threading.RLock()

        # Configuration du logger
        self.logger = logging.getLogger(f"CollaborationChannel.{channel_id}")
        self.logger.setLevel(logging.INFO)

        # Statistiques
        self.stats = {
            "messages_sent": 0,
            "messages_received": 0,
            "direct_messages": 0,
            "group_messages": 0,
            "by_agent_level": {
                "strategic": 0,
                "tactical": 0,
                "operational": 0,
                "system": 0,
            },
        }

    def send_message(self, message: Message) -> bool:
        """
        Envoie un message via ce canal.

        Args:
            message: Le message à envoyer

        Returns:
            True si le message a été envoyé avec succès, False sinon
        """
        try:
            # Vérifier si le message est destiné à un groupe
            group_id = message.metadata.get("group_id")

            if group_id:
                # Message de groupe
                return self._send_group_message(message, group_id)
            else:
                # Message direct
                return self._send_direct_message(message)

        except Exception as e:
            self.logger.error(f"Error sending message: {str(e)}")
            return False

    def _send_group_message(self, message: Message, group_id: str) -> bool:
        """
        Envoie un message à un groupe de collaboration.

        Args:
            message: Le message à envoyer
            group_id: Identifiant du groupe

        Returns:
            True si le message a été envoyé avec succès, False sinon
        """
        with self.lock:
            # Vérifier si le groupe existe
            if group_id not in self.groups:
                self.logger.error(f"Group {group_id} not found")
                return False

            group = self.groups[group_id]

            # Vérifier si l'émetteur est membre du groupe
            if message.sender not in group.members:
                self.logger.error(
                    f"Sender {message.sender} is not a member of group {group_id}"
                )
                return False

            # Ajouter le message à l'historique du groupe
            group.add_message(message)

            # Mettre à jour les statistiques
            self.stats["messages_sent"] += 1
            self.stats["group_messages"] += 1
            self.stats["by_agent_level"][message.sender_level.value] += 1

            # Notifier les abonnés
            self._notify_subscribers(message)

            self.logger.info(f"Group message {message.id} sent to group {group_id}")
            return True

    def _send_direct_message(self, message: Message) -> bool:
        """
        Envoie un message direct à un agent.

        Args:
            message: Le message à envoyer

        Returns:
            True si le message a été envoyé avec succès, False sinon
        """
        # Vérifier que le message a un destinataire
        if not message.recipient:
            self.logger.error(f"Message {message.id} has no recipient")
            return False

        with self.lock:
            # Ajouter le message à la liste des messages du destinataire
            self.direct_messages[message.recipient].append(
                {"message": message, "timestamp": datetime.now(), "read": False}
            )

            # Mettre à jour les statistiques
            self.stats["messages_sent"] += 1
            self.stats["direct_messages"] += 1
            self.stats["by_agent_level"][message.sender_level.value] += 1

            # Notifier les abonnés
            self._notify_subscribers(message)

            self.logger.info(f"Direct message {message.id} sent to {message.recipient}")
            return True

    def receive_message(
        self, recipient_id: str, timeout: Optional[float] = None
    ) -> Optional[Message]:
        """
        Reçoit un message de ce canal pour un destinataire spécifique.

        Args:
            recipient_id: Identifiant du destinataire
            timeout: Délai d'attente maximum en secondes (None pour attente indéfinie)

        Returns:
            Le message reçu ou None si timeout
        """
        # Note: Cette implémentation ne gère pas réellement le timeout
        # Une implémentation complète utiliserait des files d'attente avec blocage

        with self.lock:
            # Vérifier s'il y a des messages directs non lus
            if (
                recipient_id in self.direct_messages
                and self.direct_messages[recipient_id]
            ):
                for i, entry in enumerate(self.direct_messages[recipient_id]):
                    if not entry["read"]:
                        # Marquer le message comme lu
                        self.direct_messages[recipient_id][i]["read"] = True

                        # Mettre à jour les statistiques
                        self.stats["messages_received"] += 1

                        self.logger.info(
                            f"Direct message {entry['message'].id} received by {recipient_id}"
                        )
                        return entry["message"]

            # Vérifier s'il y a des messages de groupe non lus
            for group_id, group in self.groups.items():
                if recipient_id in group.members:
                    for entry in group.messages:
                        message = entry["message"]

                        # Vérifier si le message n'est pas de l'agent lui-même
                        if message.sender != recipient_id:
                            # Mettre à jour les statistiques
                            self.stats["messages_received"] += 1

                            self.logger.info(
                                f"Group message {message.id} received by {recipient_id} from group {group_id}"
                            )
                            return message

        return None

    def subscribe(
        self,
        subscriber_id: str,
        callback: Optional[Callable[[Message], None]] = None,
        filter_criteria: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Abonne un agent à ce canal.

        Args:
            subscriber_id: Identifiant de l'abonné
            callback: Fonction de rappel à appeler lors de la réception d'un message (optionnel)
            filter_criteria: Critères de filtrage des messages (optionnel)

        Returns:
            Un identifiant d'abonnement
        """
        subscription_id = f"sub-{uuid.uuid4().hex[:8]}"

        with self.lock:
            self.subscribers[subscription_id] = {
                "subscriber_id": subscriber_id,
                "callback": callback,
                "filter_criteria": filter_criteria,
                "created_at": datetime.now(),
            }

        self.logger.info(
            f"Subscriber {subscriber_id} registered with ID {subscription_id}"
        )
        return subscription_id

    def unsubscribe(self, subscription_id: str) -> bool:
        """
        Désabonne un agent de ce canal.

        Args:
            subscription_id: Identifiant d'abonnement

        Returns:
            True si désabonnement réussi, False sinon
        """
        with self.lock:
            if subscription_id in self.subscribers:
                subscriber_id = self.subscribers[subscription_id]["subscriber_id"]
                del self.subscribers[subscription_id]
                self.logger.info(
                    f"Subscriber {subscriber_id} unregistered (ID {subscription_id})"
                )
                return True

            self.logger.warning(f"Subscription ID {subscription_id} not found")
            return False

    def get_pending_messages(
        self, recipient_id: str, max_count: Optional[int] = None
    ) -> List[Message]:
        """
        Récupère les messages en attente pour un destinataire spécifique.

        Args:
            recipient_id: Identifiant du destinataire
            max_count: Nombre maximum de messages à récupérer (None pour tous)

        Returns:
            Liste des messages en attente
        """
        messages = []

        with self.lock:
            # Récupérer les messages directs non lus
            if recipient_id in self.direct_messages:
                for entry in self.direct_messages[recipient_id]:
                    if not entry["read"]:
                        messages.append(entry["message"])

            # Récupérer les messages de groupe
            for group_id, group in self.groups.items():
                if recipient_id in group.members:
                    for entry in group.messages:
                        message = entry["message"]
                        if message.sender != recipient_id:
                            messages.append(message)

            # Limiter le nombre de messages
            if max_count is not None and len(messages) > max_count:
                messages = messages[:max_count]

        return messages

    def get_channel_info(self) -> Dict[str, Any]:
        """
        Récupère des informations sur ce canal.

        Returns:
            Un dictionnaire d'informations sur le canal
        """
        with self.lock:
            return {
                "id": self.id,
                "type": self.type.value,
                "stats": self.stats,
                "group_count": len(self.groups),
                "subscriber_count": len(self.subscribers),
            }

    def _notify_subscribers(self, message: Message) -> None:
        """
        Notifie les abonnés intéressés par un message.

        Args:
            message: Le message à notifier
        """
        with self.lock:
            for subscription_id, subscriber in self.subscribers.items():
                # Vérifier si le message correspond aux critères de filtrage
                if self.matches_filter(message, subscriber.get("filter_criteria")):
                    # Appeler le callback si présent
                    if subscriber.get("callback"):
                        try:
                            subscriber["callback"](message)
                        except Exception as e:
                            self.logger.error(f"Error in subscriber callback: {str(e)}")

    def create_group(
        self,
        group_id: Optional[str] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        members: Optional[List[str]] = None,
    ) -> str:
        """
        Crée un nouveau groupe de collaboration.

        Args:
            group_id: Identifiant du groupe (généré automatiquement si None)
            name: Nom du groupe (optionnel)
            description: Description du groupe (optionnel)
            members: Liste des identifiants des membres initiaux (optionnel)

        Returns:
            L'identifiant du groupe créé
        """
        group_id = group_id or f"group-{uuid.uuid4().hex[:8]}"

        with self.lock:
            if group_id in self.groups:
                self.logger.warning(f"Group {group_id} already exists")
                return group_id

            group = CollaborationGroup(group_id, name, description, members)
            self.groups[group_id] = group

            self.logger.info(
                f"Group {group_id} created with {len(group.members)} members"
            )
            return group_id

    def delete_group(self, group_id: str) -> bool:
        """
        Supprime un groupe de collaboration.

        Args:
            group_id: Identifiant du groupe

        Returns:
            True si suppression réussie, False sinon
        """
        with self.lock:
            if group_id not in self.groups:
                self.logger.warning(f"Group {group_id} not found")
                return False

            del self.groups[group_id]
            self.logger.info(f"Group {group_id} deleted")
            return True

    def add_group_member(self, group_id: str, member_id: str) -> bool:
        """
        Ajoute un membre à un groupe de collaboration.

        Args:
            group_id: Identifiant du groupe
            member_id: Identifiant du membre à ajouter

        Returns:
            True si ajout réussi, False sinon
        """
        with self.lock:
            if group_id not in self.groups:
                self.logger.warning(f"Group {group_id} not found")
                return False

            result = self.groups[group_id].add_member(member_id)
            if result:
                self.logger.info(f"Member {member_id} added to group {group_id}")
            else:
                self.logger.info(f"Member {member_id} already in group {group_id}")

            return result

    def remove_group_member(self, group_id: str, member_id: str) -> bool:
        """
        Retire un membre d'un groupe de collaboration.

        Args:
            group_id: Identifiant du groupe
            member_id: Identifiant du membre à retirer

        Returns:
            True si retrait réussi, False sinon
        """
        with self.lock:
            if group_id not in self.groups:
                self.logger.warning(f"Group {group_id} not found")
                return False

            result = self.groups[group_id].remove_member(member_id)
            if result:
                self.logger.info(f"Member {member_id} removed from group {group_id}")
            else:
                self.logger.info(f"Member {member_id} not in group {group_id}")

            return result

    def get_group_messages(
        self, group_id: str, count: Optional[int] = None
    ) -> List[Message]:
        """
        Récupère les messages d'un groupe de collaboration.

        Args:
            group_id: Identifiant du groupe
            count: Nombre maximum de messages à récupérer (None pour tous)

        Returns:
            Liste des messages du groupe
        """
        with self.lock:
            if group_id not in self.groups:
                self.logger.warning(f"Group {group_id} not found")
                return []

            return self.groups[group_id].get_messages(count)

    def get_group_info(self, group_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupère des informations sur un groupe de collaboration.

        Args:
            group_id: Identifiant du groupe

        Returns:
            Un dictionnaire d'informations sur le groupe ou None s'il n'existe pas
        """
        with self.lock:
            if group_id not in self.groups:
                self.logger.warning(f"Group {group_id} not found")
                return None

            return self.groups[group_id].get_group_info()

    def get_groups(self) -> List[str]:
        """
        Récupère la liste des identifiants de tous les groupes.

        Returns:
            Liste des identifiants de groupes
        """
        with self.lock:
            return list(self.groups.keys())

    def get_agent_groups(self, agent_id: str) -> List[str]:
        """
        Récupère la liste des groupes dont un agent est membre.

        Args:
            agent_id: Identifiant de l'agent

        Returns:
            Liste des identifiants de groupes
        """
        with self.lock:
            return [
                group_id
                for group_id, group in self.groups.items()
                if agent_id in group.members
            ]
