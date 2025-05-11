"""
Exemple d'extension du système de communication multi-canal.

Ce script démontre comment étendre le système de communication avec un nouveau canal
personnalisé (AlertChannel) et un nouvel adaptateur (VisualizationAdapter). Il illustre
le processus complet d'extension, de l'implémentation des nouvelles classes à leur
intégration dans le système existant.
"""

import time
import threading
import logging
from enum import Enum
from argumentiation_analysis.core.communication.middleware import MessageMiddleware
from argumentiation_analysis.core.communication.channel_interface import ChannelInterface
from argumentiation_analysis.core.communication.agent_adapter import AgentAdapter
from argumentiation_analysis.core.communication.message import Message, MessageType, MessagePriority, AgentLevel


# 1. Définition d'un nouveau type de message pour les alertes
class ExtendedMessageType(Enum):
    """Extension des types de messages avec un nouveau type pour les alertes."""
    ALERT = "alert"  # Nouveau type pour les alertes


# 2. Implémentation d'un nouveau canal pour les alertes
class AlertChannel(ChannelInterface):
    """
    Canal spécialisé pour la diffusion d'alertes.
    
    Ce canal est optimisé pour la diffusion rapide d'alertes à tous les agents concernés,
    avec des fonctionnalités de filtrage par niveau d'alerte et par type d'alerte.
    """
    
    def __init__(self, name, config=None):
        super().__init__(name, config)
        
        # Configuration
        self.config = config or {}
        self.retention_period = self.config.get("retention_period", 3600)  # 1 heure par défaut
        
        # Files d'attente
        self.alerts = {}  # Alertes par destinataire
        self.global_alerts = []  # Alertes globales
        
        # Abonnements
        self.subscriptions = {}  # Abonnements par abonné
        self.subscription_counter = 0
        
        # Statistiques
        self.stats = {
            "alerts_sent": 0,
            "alerts_received": 0,
            "active_subscriptions": 0
        }
        
        # Verrou
        self.lock = threading.Lock()
        
        # Journalisation
        self.logger = logging.getLogger(f"AlertChannel.{name}")
    
    def send_message(self, message):
        """Envoie une alerte via ce canal."""
        with self.lock:
            # Vérifier que le message est une alerte
            if message.type != ExtendedMessageType.ALERT.value:
                self.logger.warning(f"Message de type {message.type} reçu sur le canal d'alertes")
                return False
            
            # Extraire les informations de l'alerte
            alert_level = message.content.get("alert_level", "info")
            alert_type = message.content.get("alert_type", "general")
            
            # Déterminer les destinataires
            recipient_id = message.recipient
            
            if recipient_id:
                # Alerte destinée à un agent spécifique
                if recipient_id not in self.alerts:
                    self.alerts[recipient_id] = []
                
                self.alerts[recipient_id].append({
                    "message": message,
                    "timestamp": time.time()
                })
            else:
                # Alerte globale
                self.global_alerts.append({
                    "message": message,
                    "timestamp": time.time()
                })
            
            # Mettre à jour les statistiques
            self.stats["alerts_sent"] += 1
            
            self.logger.info(f"Alerte de niveau {alert_level} de type {alert_type} envoyée")
            
            return True
    
    def receive_message(self, recipient_id, timeout=None):
        """Reçoit une alerte de ce canal."""
        start_time = time.time()
        
        while timeout is None or time.time() - start_time < timeout:
            with self.lock:
                # Vérifier les alertes spécifiques
                if recipient_id in self.alerts and self.alerts[recipient_id]:
                    alert = self.alerts[recipient_id].pop(0)
                    self.stats["alerts_received"] += 1
                    return alert["message"]
                
                # Vérifier les alertes globales
                for i, alert in enumerate(self.global_alerts):
                    # Vérifier si l'alerte correspond aux abonnements de l'agent
                    if self._matches_subscriptions(recipient_id, alert["message"]):
                        # Ne pas supprimer l'alerte globale, elle peut être destinée à d'autres agents
                        self.stats["alerts_received"] += 1
                        return alert["message"]
            
            # Pas d'alerte disponible, attendre un peu avant de vérifier à nouveau
            if timeout is not None:
                time.sleep(min(0.01, timeout / 10))
            else:
                time.sleep(0.01)
        
        # Timeout atteint ou pas de timeout et pas d'alerte disponible
        return None
    
    def get_pending_messages(self, recipient_id):
        """Récupère toutes les alertes en attente pour un destinataire."""
        with self.lock:
            pending_alerts = []
            
            # Récupérer les alertes spécifiques
            if recipient_id in self.alerts:
                pending_alerts.extend([alert["message"] for alert in self.alerts[recipient_id]])
            
            # Récupérer les alertes globales qui correspondent aux abonnements
            for alert in self.global_alerts:
                if self._matches_subscriptions(recipient_id, alert["message"]):
                    pending_alerts.append(alert["message"])
            
            return pending_alerts
    
    def subscribe(self, subscriber_id, filter_criteria=None):
        """Abonne un agent aux alertes."""
        with self.lock:
            # Créer un nouvel abonnement
            subscription_id = f"sub-{self.subscription_counter}"
            self.subscription_counter += 1
            
            # Enregistrer l'abonnement
            if subscriber_id not in self.subscriptions:
                self.subscriptions[subscriber_id] = {}
            
            self.subscriptions[subscriber_id][subscription_id] = {
                "filter_criteria": filter_criteria or {},
                "created_at": time.time()
            }
            
            # Mettre à jour les statistiques
            self.stats["active_subscriptions"] += 1
            
            self.logger.info(f"Agent {subscriber_id} abonné aux alertes avec ID {subscription_id}")
            
            return subscription_id
    
    def unsubscribe(self, subscription_id):
        """Désabonne un agent des alertes."""
        with self.lock:
            # Rechercher l'abonnement
            for subscriber_id, subscriptions in self.subscriptions.items():
                if subscription_id in subscriptions:
                    # Supprimer l'abonnement
                    del subscriptions[subscription_id]
                    
                    # Mettre à jour les statistiques
                    self.stats["active_subscriptions"] -= 1
                    
                    self.logger.info(f"Abonnement {subscription_id} supprimé")
                    
                    # Supprimer l'entrée de l'abonné si c'était son dernier abonnement
                    if not subscriptions:
                        del self.subscriptions[subscriber_id]
                    
                    return True
            
            # Abonnement non trouvé
            self.logger.warning(f"Abonnement {subscription_id} non trouvé")
            return False
    
    def get_statistics(self):
        """Récupère des statistiques sur l'utilisation du canal."""
        with self.lock:
            # Copier les statistiques de base
            stats = self.stats.copy()
            
            # Ajouter des statistiques supplémentaires
            stats["pending_alerts"] = sum(len(alerts) for alerts in self.alerts.values())
            stats["global_alerts"] = len(self.global_alerts)
            stats["subscribers"] = len(self.subscriptions)
            
            return stats
    
    def _matches_subscriptions(self, subscriber_id, message):
        """Vérifie si un message correspond aux abonnements d'un agent."""
        # Si l'agent n'a pas d'abonnements, il ne reçoit pas d'alertes globales
        if subscriber_id not in self.subscriptions:
            return False
        
        # Vérifier chaque abonnement
        for subscription in self.subscriptions[subscriber_id].values():
            filter_criteria = subscription["filter_criteria"]
            
            # Si pas de critères, l'abonnement correspond à toutes les alertes
            if not filter_criteria:
                return True
            
            # Vérifier les critères de filtrage
            matches = True
            
            for key, value in filter_criteria.items():
                if key == "alert_level":
                    # Filtrage par niveau d'alerte
                    message_level = message.content.get("alert_level", "info")
                    if isinstance(value, list):
                        if message_level not in value:
                            matches = False
                            break
                    elif message_level != value:
                        matches = False
                        break
                
                elif key == "alert_type":
                    # Filtrage par type d'alerte
                    message_type = message.content.get("alert_type", "general")
                    if isinstance(value, list):
                        if message_type not in value:
                            matches = False
                            break
                    elif message_type != value:
                        matches = False
                        break
            
            # Si un abonnement correspond, le message est accepté
            if matches:
                return True
        
        # Aucun abonnement ne correspond
        return False


# 3. Implémentation d'un nouvel adaptateur pour les agents de visualisation
class VisualizationAdapter(AgentAdapter):
    """
    Adaptateur pour les agents de visualisation.
    
    Cet adaptateur fournit des méthodes spécifiques pour les agents responsables
    de la visualisation des résultats d'analyse, comme la génération de graphiques
    d'arguments, de diagrammes de sophismes, etc.
    """
    
    def __init__(self, agent_id, middleware):
        super().__init__(agent_id, middleware)
        self.logger = logging.getLogger(f"VisualizationAdapter.{agent_id}")
    
    def _get_agent_level(self):
        """Récupère le niveau de l'agent."""
        return AgentLevel.OPERATIONAL
    
    # Méthodes d'envoi spécifiques
    
    def send_visualization(self, visualization_type, data, recipient_id, priority=MessagePriority.NORMAL, metadata=None):
        """
        Envoie une visualisation.
        
        Args:
            visualization_type: Type de visualisation (graph, chart, diagram, etc.)
            data: Données de la visualisation
            recipient_id: Identifiant du destinataire
            priority: Priorité du message
            metadata: Métadonnées supplémentaires (optionnel)
            
        Returns:
            L'identifiant du message envoyé
        """
        # Préparer le contenu du message
        content = {
            "info_type": "visualization",
            "visualization_type": visualization_type,
            "data": data
        }
        
        # Préparer les métadonnées
        msg_metadata = metadata or {}
        
        # Envoyer le message
        return self.send_message(
            message_type=MessageType.INFORMATION,
            content=content,
            recipient=recipient_id,
            priority=priority,
            metadata=msg_metadata
        )
    
    def send_alert(self, alert_type, alert_level, details, recipient=None, priority=MessagePriority.HIGH):
        """
        Envoie une alerte.
        
        Args:
            alert_type: Type d'alerte
            alert_level: Niveau d'alerte (critical, warning, info)
            details: Détails de l'alerte
            recipient: Destinataire (optionnel, None pour une alerte globale)
            priority: Priorité de l'alerte
            
        Returns:
            L'identifiant de l'alerte envoyée
        """
        # Créer le message d'alerte
        message = Message(
            type=ExtendedMessageType.ALERT.value,
            sender=self.agent_id,
            sender_level=self._get_agent_level(),
            recipient=recipient,
            content={
                "alert_type": alert_type,
                "alert_level": alert_level,
                "details": details
            },
            priority=priority
        )
        
        # Envoyer le message via le middleware
        return self.middleware.send_message(message)
    
    # Méthodes de réception spécifiques
    
    def receive_visualization_request(self, timeout=None):
        """
        Reçoit une demande de visualisation.
        
        Args:
            timeout: Délai d'attente maximum en secondes (optionnel)
            
        Returns:
            La demande reçue ou None si aucune demande n'est disponible
        """
        return self.receive_message(
            message_type=MessageType.REQUEST,
            timeout=timeout,
            filter_criteria={"content.request_type": "visualization"}
        )
    
    def receive_alert(self, timeout=None, alert_type=None, alert_level=None):
        """
        Reçoit une alerte.
        
        Args:
            timeout: Délai d'attente maximum en secondes (optionnel)
            alert_type: Type d'alerte à recevoir (optionnel)
            alert_level: Niveau d'alerte à recevoir (optionnel)
            
        Returns:
            L'alerte reçue ou None si aucune alerte n'est disponible
        """
        # Préparer les critères de filtrage
        filter_criteria = {}
        
        if alert_type:
            filter_criteria["content.alert_type"] = alert_type
        
        if alert_level:
            filter_criteria["content.alert_level"] = alert_level
        
        return self.receive_message(
            message_type=ExtendedMessageType.ALERT.value,
            timeout=timeout,
            filter_criteria=filter_criteria
        )


# 4. Exemple d'utilisation des extensions
def main():
    # Configurer la journalisation
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Créer et initialiser le middleware
    print("Initialisation du middleware...")
    middleware = MessageMiddleware()
    middleware.initialize()

    # Créer et enregistrer le canal d'alertes
    print("Création du canal d'alertes...")
    alert_channel = AlertChannel(
        name="alert",
        config={"retention_period": 7200}  # 2 heures
    )
    middleware.register_channel(alert_channel)
    
    # Configurer le routage pour le canal d'alertes
    middleware.add_routing_rule(ExtendedMessageType.ALERT.value, "alert")
    
    middleware.initialize_protocols()

    # Créer les adaptateurs
    print("Création des adaptateurs...")
    visualization_adapter = VisualizationAdapter("visualization-agent-1", middleware)
    tactical_adapter = AgentAdapter("tactical-agent-1", middleware)
    tactical_adapter._get_agent_level = lambda: AgentLevel.TACTICAL  # Méthode temporaire pour l'exemple

    # Fonction simulant un agent de visualisation
    def visualization_agent():
        print("Agent de visualisation démarré...")
        
        # S'abonner aux alertes de niveau critique
        subscription_id = alert_channel.subscribe(
            "visualization-agent-1",
            filter_criteria={
                "alert_level": ["critical", "warning"]
            }
        )
        print(f"Abonné aux alertes avec ID: {subscription_id}")
        
        # Créer une visualisation
        print("Création d'une visualisation...")
        graph_data = {
            "nodes": [
                {"id": "p1", "label": "Tous les hommes sont mortels", "type": "premise"},
                {"id": "p2", "label": "Socrate est un homme", "type": "premise"},
                {"id": "c1", "label": "Socrate est mortel", "type": "conclusion"}
            ],
            "edges": [
                {"from": "p1", "to": "c1", "type": "support"},
                {"from": "p2", "to": "c1", "type": "support"}
            ]
        }
        
        # Envoyer la visualisation
        print("Envoi de la visualisation...")
        visualization_adapter.send_visualization(
            visualization_type="argument_graph",
            data=graph_data,
            recipient_id="tactical-agent-1",
            priority=MessagePriority.NORMAL
        )
        
        # Simuler une détection d'anomalie
        print("Détection d'une anomalie dans les données...")
        time.sleep(1.0)
        
        # Envoyer une alerte
        print("Envoi d'une alerte...")
        visualization_adapter.send_alert(
            alert_type="data_anomaly",
            alert_level="warning",
            details={
                "description": "Incohérence détectée dans la structure argumentative",
                "location": {"node_id": "c1", "edge_ids": ["p1-c1"]},
                "severity": 0.7,
                "recommendation": "Vérifier la relation entre la prémisse universelle et la conclusion"
            },
            recipient="tactical-agent-1",
            priority=MessagePriority.HIGH
        )
        
        # Envoyer une alerte globale
        print("Envoi d'une alerte globale...")
        visualization_adapter.send_alert(
            alert_type="system_performance",
            alert_level="critical",
            details={
                "description": "Ressources système insuffisantes pour le traitement graphique",
                "metrics": {"cpu": 95, "memory": 87, "gpu": 99},
                "impact": "Ralentissement des rendus graphiques",
                "recommendation": "Réduire la complexité des visualisations ou augmenter les ressources"
            },
            recipient=None,  # Alerte globale
            priority=MessagePriority.CRITICAL
        )
        
        print("Agent de visualisation: tâches terminées.")

    # Fonction simulant un agent tactique
    def tactical_agent():
        print("Agent tactique démarré...")
        
        # Recevoir la visualisation
        print("En attente de la visualisation...")
        visualization = tactical_adapter.receive_message(
            timeout=5.0,
            filter_criteria={
                "content.info_type": "visualization"
            }
        )
        
        if visualization:
            print(f"Visualisation reçue: {visualization.content}")
            
            # Traiter la visualisation
            print("Traitement de la visualisation...")
            time.sleep(1.0)
        
        # Recevoir l'alerte spécifique
        print("En attente d'alertes...")
        alert = tactical_adapter.receive_message(
            timeout=5.0,
            filter_criteria={
                "type": ExtendedMessageType.ALERT.value
            }
        )
        
        if alert:
            print(f"Alerte reçue: {alert.content}")
            
            # Traiter l'alerte
            print("Traitement de l'alerte...")
            time.sleep(1.0)
        
        print("Agent tactique: tâches terminées.")

    # Démarrer les threads pour les agents
    vis_thread = threading.Thread(target=visualization_agent)
    tac_thread = threading.Thread(target=tactical_agent)
    
    vis_thread.start()
    tac_thread.start()
    
    # Attendre que les threads se terminent
    vis_thread.join()
    tac_thread.join()
    
    # Afficher les statistiques du canal d'alertes
    print("\nStatistiques du canal d'alertes:")
    stats = alert_channel.get_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("Extension du système terminée.")


if __name__ == "__main__":
    main()