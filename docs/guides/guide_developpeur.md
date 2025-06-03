# Guide du développeur du système de communication multi-canal

## Table des matières

1. [Introduction](#introduction)
   - [Objectifs du guide](#objectifs-du-guide)
   - [Prérequis techniques](#prérequis-techniques)

2. [Architecture détaillée](#architecture-détaillée)
   - [Diagramme de classes](#diagramme-de-classes)
   - [Diagramme de séquence](#diagramme-de-séquence)
   - [Principes de conception](#principes-de-conception)
   - [Patterns utilisés](#patterns-utilisés)

3. [Comment étendre le système avec de nouveaux canaux](#comment-étendre-le-système-avec-de-nouveaux-canaux)
   - [Structure d'un canal](#structure-dun-canal)
   - [Interface à implémenter](#interface-à-implémenter)
   - [Gestion des messages](#gestion-des-messages)
   - [Intégration avec le middleware](#intégration-avec-le-middleware)
   - [Exemple de création d'un nouveau canal](#exemple-de-création-dun-nouveau-canal)

4. [Comment implémenter de nouveaux protocoles](#comment-implémenter-de-nouveaux-protocoles)
   - [Structure d'un protocole](#structure-dun-protocole)
   - [Interface à implémenter](#interface-à-implémenter-1)
   - [Gestion des échanges](#gestion-des-échanges)
   - [Exemple de création d'un nouveau protocole](#exemple-de-création-dun-nouveau-protocole)

5. [Comment créer de nouveaux adaptateurs](#comment-créer-de-nouveaux-adaptateurs)
   - [Structure d'un adaptateur](#structure-dun-adaptateur)
   - [Interface à implémenter](#interface-à-implémenter-2)
   - [Traduction des messages](#traduction-des-messages)
   - [Exemple de création d'un nouvel adaptateur](#exemple-de-création-dun-nouvel-adaptateur)

6. [Bonnes pratiques de développement](#bonnes-pratiques-de-développement)
   - [Gestion des erreurs](#gestion-des-erreurs)
   - [Tests unitaires et d'intégration](#tests-unitaires-et-dintégration)
   - [Performance et optimisation](#performance-et-optimisation)
   - [Documentation du code](#documentation-du-code)

## Introduction

### Objectifs du guide

Ce guide du développeur a pour objectif de fournir une documentation détaillée sur l'architecture interne du système de communication multi-canal et d'expliquer comment l'étendre avec de nouveaux composants. Il s'adresse aux développeurs qui souhaitent :

- Comprendre en profondeur l'architecture et les principes de conception du système
- Étendre le système avec de nouveaux canaux de communication
- Implémenter de nouveaux protocoles d'échange
- Créer de nouveaux adaptateurs pour des types d'agents spécifiques
- Contribuer au développement du système en suivant les bonnes pratiques

Ce guide complète le guide d'utilisation en se concentrant sur les aspects techniques et architecturaux du système, plutôt que sur son utilisation.

### Prérequis techniques

Pour tirer le meilleur parti de ce guide, vous devriez avoir :

- Une bonne connaissance de Python (3.8+)
- Une compréhension des principes de la programmation orientée objet
- Une familiarité avec les concepts de communication entre agents
- Des connaissances de base en architecture logicielle et patterns de conception
- Une compréhension des principes de la programmation asynchrone (asyncio)

Il est également recommandé d'avoir lu le guide d'utilisation du système de communication multi-canal pour comprendre les fonctionnalités de base et les cas d'utilisation typiques.

## Architecture détaillée

### Diagramme de classes

Le système de communication multi-canal est organisé autour des classes principales suivantes :

```
┌───────────────────┐      ┌───────────────────┐
│  MessageMiddleware│◄─────┤ChannelInterface   │
└───────┬───────────┘      └───────────────────┘
        │                           ▲
        │                           │
        │                  ┌────────┴────────┐
        │                  │                 │
┌───────▼───────────┐    ┌─┴──────────────┐ ┌┴───────────────┐
│ProtocolInterface  │    │HierarchicalChan│ │CollaborationCha│...
└───────────────────┘    └────────────────┘ └────────────────┘
        ▲
        │
┌───────┴───────────┐
│                   │
┌─────────────────┐ ┌─────────────────┐
│RequestResponse  │ │PublishSubscribe │...
└─────────────────┘ └─────────────────┘

┌───────────────────┐
│  AgentAdapter     │
└───────┬───────────┘
        │
        ▼
┌───────────────────┐
│                   │
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│StrategicAdapter │ │TacticalAdapter  │ │OperationalAdapt│
└─────────────────┘ └─────────────────┘ └─────────────────┘

┌───────────────────┐
│  Message          │
└───────┬───────────┘
        │
        ▼
┌───────────────────┐
│                   │
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│CommandMessage   │ │InformationMessag│ │RequestMessage  │...
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

Les principales classes et leurs responsabilités sont :

1. **MessageMiddleware** : Composant central qui gère les canaux, les protocoles et le routage des messages.
2. **ChannelInterface** : Interface que tous les canaux de communication doivent implémenter.
3. **Canaux spécifiques** (HierarchicalChannel, CollaborationChannel, etc.) : Implémentations concrètes des canaux.
4. **ProtocolInterface** : Interface que tous les protocoles de communication doivent implémenter.
5. **Protocoles spécifiques** (RequestResponse, PublishSubscribe, etc.) : Implémentations concrètes des protocoles.
6. **AgentAdapter** : Classe de base pour tous les adaptateurs d'agents.
7. **Adaptateurs spécifiques** (StrategicAdapter, TacticalAdapter, etc.) : Implémentations concrètes des adaptateurs.
8. **Message** : Classe de base pour tous les types de messages.
9. **Types de messages spécifiques** (CommandMessage, InformationMessage, etc.) : Implémentations concrètes des messages.

### Diagramme de séquence

Voici un diagramme de séquence simplifié montrant le flux d'un message du niveau stratégique au niveau tactique :

```
┌─────────┐          ┌─────────┐          ┌─────────┐          ┌─────────┐          ┌─────────┐
│Strategic│          │Strategic│          │Message  │          │Hierarchi│          │Tactical │
│Agent    │          │Adapter  │          │Middlewar│          │calChanne│          │Adapter  │
└────┬────┘          └────┬────┘          └────┬────┘          └────┬────┘          └────┬────┘
     │                    │                    │                    │                    │
     │ issue_directive    │                    │                    │                    │
     │───────────────────>│                    │                    │                    │
     │                    │                    │                    │                    │
     │                    │ create_message     │                    │                    │
     │                    │────────────────────│                    │                    │
     │                    │                    │                    │                    │
     │                    │ send_message       │                    │                    │
     │                    │────────────────────>                    │                    │
     │                    │                    │                    │                    │
     │                    │                    │ route_message      │                    │
     │                    │                    │───────────────────>│                    │
     │                    │                    │                    │                    │
     │                    │                    │                    │ queue_message      │
     │                    │                    │                    │────────────────────│
     │                    │                    │                    │                    │
     │                    │                    │                    │                    │
     │                    │                    │                    │                    │
     │                    │                    │                    │  receive_directive │
     │                    │                    │                    │ <─────────────────│
     │                    │                    │                    │                    │
     │                    │                    │ get_message        │                    │
     │                    │                    │ <──────────────────│                    │
     │                    │                    │                    │                    │
     │                    │                    │ return_message     │                    │
     │                    │                    │────────────────────>                    │
     │                    │                    │                    │                    │
     │                    │                    │                    │ return_message     │
     │                    │                    │                    │───────────────────>│
     │                    │                    │                    │                    │
┌────┴────┐          ┌────┴────┐          ┌────┴────┐          ┌────┴────┐          ┌────┴────┐
│Strategic│          │Strategic│          │Message  │          │Hierarchi│          │Tactical │
│Agent    │          │Adapter  │          │Middlewar│          │calChanne│          │Adapter  │
└─────────┘          └─────────┘          └─────────┘          └─────────┘          └─────────┘
```

Le flux typique d'un message est le suivant :
1. L'agent appelle une méthode de son adaptateur
2. L'adaptateur crée un message approprié
3. L'adaptateur envoie le message au middleware
4. Le middleware détermine le canal approprié et lui transmet le message
5. Le canal met le message en file d'attente
6. L'adaptateur du destinataire demande les messages en attente
7. Le canal retourne le message au middleware
8. Le middleware retourne le message à l'adaptateur
9. L'adaptateur traite le message et le présente à l'agent

### Principes de conception

Le système de communication multi-canal est conçu selon plusieurs principes fondamentaux :

#### 1. Séparation des préoccupations

Le système sépare clairement les différentes responsabilités :
- Les **agents** se concentrent sur la logique métier
- Les **adaptateurs** traduisent les besoins des agents en messages standardisés
- Les **canaux** gèrent le transport des messages
- Le **middleware** coordonne l'ensemble du système
- Les **protocoles** définissent des patterns d'interaction standardisés

Cette séparation permet de modifier chaque composant indépendamment sans affecter les autres.

#### 2. Extensibilité

Le système est conçu pour être facilement extensible :
## Comment étendre le système avec de nouveaux canaux

### Structure d'un canal

Un canal de communication est responsable du transport des messages entre les agents. Chaque canal est spécialisé pour un type spécifique d'interaction et implémente des fonctionnalités adaptées à ce type d'interaction.

La structure typique d'un canal comprend :

1. **Gestion des messages** : Mécanismes pour envoyer, recevoir et stocker temporairement les messages
2. **Gestion des abonnements** : Mécanismes pour permettre aux agents de s'abonner et se désabonner du canal
3. **Filtrage et priorisation** : Mécanismes pour filtrer les messages et gérer leur priorité
4. **Gestion des erreurs** : Mécanismes pour détecter et gérer les erreurs de communication
5. **Métriques et monitoring** : Mécanismes pour collecter des métriques sur l'utilisation du canal

### Interface à implémenter

Tous les canaux de communication doivent implémenter l'interface `ChannelInterface` qui définit les méthodes requises pour interagir avec le middleware. Voici les principales méthodes de cette interface :

```python
class ChannelInterface:
    """Interface que tous les canaux de communication doivent implémenter."""
    
    def __init__(self, name, config=None):
        """
        Initialise un nouveau canal.
        
        Args:
            name: Nom unique du canal
            config: Configuration du canal (optionnel)
        """
        self.name = name
        self.config = config or {}
    
    def send_message(self, message):
        """
        Envoie un message via ce canal.
        
        Args:
            message: Le message à envoyer
            
        Returns:
            True si le message a été envoyé avec succès, False sinon
        """
        raise NotImplementedError("Les sous-classes doivent implémenter cette méthode")
    
    def receive_message(self, recipient_id, timeout=None):
        """
        Reçoit un message de ce canal.
        
        Args:
            recipient_id: Identifiant du destinataire
            timeout: Délai d'attente maximum en secondes (optionnel)
            
        Returns:
            Le message reçu ou None si aucun message n'est disponible
        """
        raise NotImplementedError("Les sous-classes doivent implémenter cette méthode")
    
    def get_pending_messages(self, recipient_id):
        """
        Récupère tous les messages en attente pour un destinataire.
        
        Args:
            recipient_id: Identifiant du destinataire
            
        Returns:
            Liste des messages en attente
        """
        raise NotImplementedError("Les sous-classes doivent implémenter cette méthode")
    
    def subscribe(self, subscriber_id, filter_criteria=None):
        """
        Abonne un agent à ce canal.
        
        Args:
            subscriber_id: Identifiant de l'abonné
            filter_criteria: Critères de filtrage (optionnel)
            
        Returns:
            Un identifiant d'abonnement
        """
        raise NotImplementedError("Les sous-classes doivent implémenter cette méthode")
    
    def unsubscribe(self, subscription_id):
        """
        Désabonne un agent de ce canal.
        
        Args:
            subscription_id: Identifiant de l'abonnement
            
        Returns:
            True si le désabonnement a réussi, False sinon
        """
        raise NotImplementedError("Les sous-classes doivent implémenter cette méthode")
    
    def get_statistics(self):
        """
        Récupère des statistiques sur l'utilisation du canal.
        
        Returns:
            Un dictionnaire de statistiques
        """
        raise NotImplementedError("Les sous-classes doivent implémenter cette méthode")
```

### Gestion des messages

La gestion des messages est au cœur de l'implémentation d'un canal. Voici les principales fonctionnalités à implémenter :

#### 1. File d'attente de messages

Chaque canal doit maintenir une file d'attente pour les messages en attente de livraison. Cette file peut être implémentée de différentes manières selon les besoins du canal :

```python
class MyChannel(ChannelInterface):
    def __init__(self, name, config=None):
        super().__init__(name, config)
        
        # File d'attente simple
        self.message_queue = {}  # Dictionnaire de files par destinataire
        
        # Verrou pour les accès concurrents
        self.lock = threading.Lock()
```

#### 2. Envoi de messages

La méthode `send_message` doit ajouter le message à la file d'attente appropriée :

```python
def send_message(self, message):
    with self.lock:
        recipient_id = message.recipient
        
        # Créer une file pour le destinataire si elle n'existe pas
        if recipient_id not in self.message_queue:
            self.message_queue[recipient_id] = []
        
        # Ajouter le message à la file
        self.message_queue[recipient_id].append(message)
        
        # Mettre à jour les statistiques
        self.stats["messages_sent"] += 1
        
        return True
```

#### 3. Réception de messages

La méthode `receive_message` doit récupérer le premier message disponible pour un destinataire :

```python
def receive_message(self, recipient_id, timeout=None):
    # Si un timeout est spécifié, attendre qu'un message soit disponible
    if timeout:
        start_time = time.time()
        while time.time() - start_time < timeout:
            with self.lock:
                if recipient_id in self.message_queue and self.message_queue[recipient_id]:
                    message = self.message_queue[recipient_id].pop(0)
                    self.stats["messages_received"] += 1
                    return message
            
            # Attendre un peu avant de vérifier à nouveau
            time.sleep(0.01)
        
        # Timeout atteint, aucun message disponible
        return None
    
    # Pas de timeout, vérifier immédiatement
    with self.lock:
        if recipient_id in self.message_queue and self.message_queue[recipient_id]:
            message = self.message_queue[recipient_id].pop(0)
            self.stats["messages_received"] += 1
            return message
        
        # Aucun message disponible
        return None
```

### Intégration avec le middleware

Pour intégrer un nouveau canal avec le middleware, vous devez :

1. Implémenter l'interface `ChannelInterface`
2. Enregistrer le canal auprès du middleware
3. Configurer les règles de routage pour le canal

```python
# Créer le canal
my_channel = MyChannel("my_channel", config={...})

# Enregistrer le canal auprès du middleware
middleware.register_channel(my_channel)

# Configurer les règles de routage
middleware.add_routing_rule(
    message_type=MessageType.MY_TYPE,
    channel_name="my_channel"
)
```

### Exemple de création d'un nouveau canal

Voici un exemple complet de création d'un nouveau canal de communication pour la gestion des alertes :

```python
from argumentiation_analysis.core.communication.channel_interface import ChannelInterface
from argumentiation_analysis.core.communication.message import MessagePriority
import threading
import time
import logging

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
        
        # Démarrer le thread de nettoyage
        self.running = True
        self.cleanup_thread = threading.Thread(target=self._cleanup_worker)
        self.cleanup_thread.daemon = True
        self.cleanup_thread.start()
    
    def send_message(self, message):
        """Envoie une alerte via ce canal."""
        with self.lock:
            # Vérifier que le message est une alerte
            if message.type != MessageType.ALERT:
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
    
    def _cleanup_worker(self):
        """Thread travailleur qui nettoie les alertes expirées."""
        while self.running:
            # Attendre un peu avant le prochain nettoyage
            time.sleep(60)  # Nettoyer toutes les minutes
            
            with self.lock:
                current_time = time.time()
                
                # Nettoyer les alertes spécifiques expirées
                for recipient_id in list(self.alerts.keys()):
                    self.alerts[recipient_id] = [
                        alert for alert in self.alerts[recipient_id]
                        if current_time - alert["timestamp"] < self.retention_period
                    ]
                    
                    # Supprimer l'entrée si la liste est vide
                    if not self.alerts[recipient_id]:
                        del self.alerts[recipient_id]
                
                # Nettoyer les alertes globales expirées
                self.global_alerts = [
                    alert for alert in self.global_alerts
                    if current_time - alert["timestamp"] < self.retention_period
                ]
    
    def shutdown(self):
        """Arrête proprement le canal."""
        self.running = False
        self.cleanup_thread.join(timeout=5)
        self.logger.info(f"Canal d'alertes {self.name} arrêté")
```

Pour utiliser ce nouveau canal :

```python
# Créer le canal d'alertes
alert_channel = AlertChannel("alert", config={"retention_period": 7200})  # 2 heures

# Enregistrer le canal auprès du middleware
middleware.register_channel(alert_channel)

# Configurer les règles de routage
middleware.add_routing_rule(
    message_type=MessageType.ALERT,
    channel_name="alert"
)

# Créer un type de message pour les alertes
class AlertMessage(Message):
    def __init__(self, sender, sender_level, alert_type, alert_level, details, recipient=None, priority=MessagePriority.HIGH):
        super().__init__(
            type=MessageType.ALERT,
            sender=sender,
            sender_level=sender_level,
### Tests pour les canaux

Il est crucial de tester vos implémentations de canaux. Vous pouvez vous inspirer des tests unitaires existants pour vérifier :
- L'envoi et la réception corrects des messages.
- La gestion des files d'attente.
- Le fonctionnement des abonnements et des filtres.
- La gestion des erreurs.

Par exemple, consultez les tests unitaires pour les composants principaux dans [`tests/unit/project_core/`](tests/unit/project_core/) pour des idées sur la structure des tests.

## Comment créer de nouveaux adaptateurs

### Structure d'un adaptateur

Un adaptateur d'agent sert d'interface entre un agent et le middleware de messagerie. Il traduit les appels d'API spécifiques à l'agent en messages standardisés compréhensibles par le middleware, et inversement.

La structure typique d'un adaptateur comprend :

1. **Méthodes d'envoi** : Méthodes pour envoyer différents types de messages
2. **Méthodes de réception** : Méthodes pour recevoir différents types de messages
3. **Gestion des abonnements** : Méthodes pour s'abonner et se désabonner des canaux
4. **Traduction des messages** : Mécanismes pour traduire les messages entre le format de l'agent et le format standardisé
5. **Gestion des erreurs** : Mécanismes pour détecter et gérer les erreurs de communication

### Interface à implémenter

Tous les adaptateurs d'agents doivent étendre la classe de base `AgentAdapter` qui fournit les fonctionnalités communes à tous les adaptateurs. Voici la structure de cette classe :

```python
class AgentAdapter:
    """Classe de base pour tous les adaptateurs d'agents."""
    
    def __init__(self, agent_id, middleware):
        """
        Initialise un nouvel adaptateur d'agent.
        
        Args:
            agent_id: Identifiant unique de l'agent
            middleware: Le middleware de messagerie
        """
        self.agent_id = agent_id
        self.middleware = middleware
        self.logger = logging.getLogger(f"AgentAdapter.{agent_id}")
    
    def send_message(self, message_type, content, recipient=None, priority=MessagePriority.NORMAL, metadata=None):
        """
        Envoie un message générique.
        
        Args:
            message_type: Type de message
            content: Contenu du message
            recipient: Destinataire (optionnel)
            priority: Priorité du message
            metadata: Métadonnées du message (optionnel)
            
        Returns:
            L'identifiant du message envoyé
        """
        # Créer le message
        message = Message(
            type=message_type,
            sender=self.agent_id,
            sender_level=self._get_agent_level(),
            recipient=recipient,
            content=content,
            priority=priority,
            metadata=metadata or {}
        )
        
        # Envoyer le message via le middleware
        return self.middleware.send_message(message)
    
    def receive_message(self, message_type=None, timeout=None, filter_criteria=None):
        """
        Reçoit un message.
        
        Args:
            message_type: Type de message à recevoir (optionnel)
            timeout: Délai d'attente maximum en secondes (optionnel)
            filter_criteria: Critères de filtrage supplémentaires (optionnel)
            
        Returns:
            Le message reçu ou None si aucun message n'est disponible
        """
        # Préparer les critères de filtrage
        criteria = filter_criteria or {}
        if message_type:
            criteria["type"] = message_type
        
        # Recevoir le message via le middleware
        return self.middleware.receive_message(
            recipient_id=self.agent_id,
            timeout=timeout,
            filter_criteria=criteria
        )
    
    def subscribe(self, topic, callback=None, filter_criteria=None):
        """
        S'abonne à un sujet.
        
        Args:
            topic: Sujet auquel s'abonner
            callback: Fonction de rappel à appeler lors de la réception d'un message (optionnel)
            filter_criteria: Critères de filtrage (optionnel)
            
        Returns:
            Un identifiant d'abonnement
        """
        return self.middleware.subscribe(
            subscriber_id=self.agent_id,
            topic_id=topic,
            callback=callback,
            filter_criteria=filter_criteria
        )
    
    def unsubscribe(self, subscription_id):
        """
        Désabonne d'un sujet.
        
        Args:
            subscription_id: Identifiant de l'abonnement
            
        Returns:
            True si le désabonnement a réussi, False sinon
        """
        return self.middleware.unsubscribe(subscription_id)
    
    def _get_agent_level(self):
        """
        Récupère le niveau de l'agent.
        
        Returns:
            Le niveau de l'agent (AgentLevel)
        """
        raise NotImplementedError("Les sous-classes doivent implémenter cette méthode")
```

### Traduction des messages

La traduction des messages est une fonctionnalité clé des adaptateurs. Elle consiste à convertir les appels d'API spécifiques à l'agent en messages standardisés, et inversement.

#### 1. Méthodes d'envoi spécifiques

Chaque adaptateur doit fournir des méthodes d'envoi spécifiques au type d'agent :

```python
class StrategicAdapter(AgentAdapter):
    """Adaptateur pour les agents stratégiques."""
    
    def _get_agent_level(self):
        """Récupère le niveau de l'agent."""
        return AgentLevel.STRATEGIC
    
    def issue_directive(self, directive_type, parameters, recipient_id, priority=MessagePriority.HIGH, requires_ack=False, metadata=None):
        """
        Émet une directive stratégique.
        
        Args:
            directive_type: Type de directive
            parameters: Paramètres de la directive
            recipient_id: Identifiant du destinataire tactique
            priority: Priorité de la directive
            requires_ack: Indique si un accusé de réception est requis
            metadata: Métadonnées supplémentaires (optionnel)
            
        Returns:
            L'identifiant de la directive émise
        """
        # Préparer le contenu du message
        content = {
            "command_type": directive_type,
            "parameters": parameters
        }
        
        # Préparer les métadonnées
        msg_metadata = metadata or {}
        msg_metadata["requires_ack"] = requires_ack
        
        # Envoyer le message
        return self.send_message(
            message_type=MessageType.COMMAND,
            content=content,
            recipient=recipient_id,
            priority=priority,
            metadata=msg_metadata
        )
```

#### 2. Méthodes de réception spécifiques

De même, chaque adaptateur doit fournir des méthodes de réception spécifiques :

```python
def receive_report(self, timeout=None, filter_criteria=None):
    """
    Reçoit un rapport tactique.
    
    Args:
        timeout: Délai d'attente maximum en secondes (optionnel)
        filter_criteria: Critères de filtrage supplémentaires (optionnel)
        
    Returns:
        Le rapport reçu ou None si aucun rapport n'est disponible
    """
    # Préparer les critères de filtrage
    criteria = filter_criteria or {}
    criteria["type"] = MessageType.INFORMATION
    criteria["content.info_type"] = "report"
    
    # Recevoir le message
    return self.receive_message(
        timeout=timeout,
        filter_criteria=criteria
    )
```

### Exemple de création d'un nouvel adaptateur

Voici un exemple complet de création d'un nouvel adaptateur pour un agent de visualisation :

```python
from argumentiation_analysis.core.communication.agent_adapter import AgentAdapter
from argumentiation_analysis.core.communication.message import MessageType, MessagePriority, AgentLevel
import logging

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
    
    def request_data_for_visualization(self, data_type, parameters, recipient_id, timeout=5.0, priority=MessagePriority.NORMAL):
        """
        Demande des données pour une visualisation.
        
        Args:
            data_type: Type de données demandées
            parameters: Paramètres de la demande
            recipient_id: Identifiant du destinataire
            timeout: Délai d'attente maximum en secondes
            priority: Priorité du message
            
        Returns:
            Les données reçues ou None si timeout
        """
        # Préparer le contenu du message
        content = {
            "request_type": "visualization_data",
            "data_type": data_type,
            "parameters": parameters
        }
        
        # Créer un identifiant de conversation unique
        conversation_id = f"vis-req-{uuid.uuid4().hex[:8]}"
        
        # Envoyer la requête
        message_id = self.send_message(
            message_type=MessageType.REQUEST,
            content=content,
            recipient=recipient_id,
            priority=priority,
            metadata={"conversation_id": conversation_id}
        )
        
        # Attendre la réponse
        response = self.receive_message(
            message_type=MessageType.RESPONSE,
            timeout=timeout,
            filter_criteria={
                "metadata.conversation_id": conversation_id,
                "metadata.request_id": message_id
            }
        )
        
        if response:
            # Extraire les données de la réponse
            return response.content.get("data")
        
        return None
    
    def notify_visualization_ready(self, visualization_id, access_info, recipient_id, priority=MessagePriority.NORMAL):
        """
        Notifie qu'une visualisation est prête.
        
        Args:
            visualization_id: Identifiant de la visualisation
            access_info: Informations d'accès à la visualisation
            recipient_id: Identifiant du destinataire
            priority: Priorité du message
            
        Returns:
            L'identifiant du message envoyé
        """
        # Préparer le contenu du message
        content = {
            "event_type": "visualization_ready",
            "visualization_id": visualization_id,
            "access_info": access_info
        }
        
        # Envoyer le message
        return self.send_message(
            message_type=MessageType.EVENT,
            content=content,
            recipient=recipient_id,
            priority=priority
        )
    
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
    
    def receive_data_update(self, timeout=None, data_type=None):
        """
        Reçoit une mise à jour de données.
        
        Args:
            timeout: Délai d'attente maximum en secondes (optionnel)
            data_type: Type de données à recevoir (optionnel)
            
        Returns:
            La mise à jour reçue ou None si aucune mise à jour n'est disponible
        """
        # Préparer les critères de filtrage
        criteria = {
            "content.info_type": "data_update"
        }
        
        if data_type:
            criteria["content.data_type"] = data_type
        
        return self.receive_message(
            message_type=MessageType.INFORMATION,
            timeout=timeout,
            filter_criteria=criteria
        )
    
    # Méthodes d'abonnement spécifiques
    
    def subscribe_to_data_updates(self, data_types=None, callback=None):
        """
        S'abonne aux mises à jour de données.
        
        Args:
            data_types: Types de données à surveiller (optionnel)
            callback: Fonction de rappel à appeler lors de la réception d'une mise à jour (optionnel)
            
        Returns:
            Un identifiant d'abonnement
        """
        # Préparer les critères de filtrage
        filter_criteria = {
            "type": MessageType.INFORMATION,
            "content.info_type": "data_update"
        }
        
        if data_types:
            filter_criteria["content.data_type"] = data_types
        
        # S'abonner au sujet
        return self.subscribe(
            topic="data_updates",
            callback=callback,
            filter_criteria=filter_criteria
        )
```

Pour utiliser ce nouvel adaptateur :

```python
# Créer l'adaptateur de visualisation
visualization_adapter = VisualizationAdapter("visualization-agent-1", middleware)

# Envoyer une visualisation
visualization_adapter.send_visualization(
    visualization_type="argument_graph",
    data={
        "nodes": [...],
        "edges": [...]
    },
    recipient_id="tactical-agent-1",
    priority=MessagePriority.NORMAL
)

# Demander des données pour une visualisation
argument_data = visualization_adapter.request_data_for_visualization(
    data_type="argument_structure",
    parameters={"text_id": "text-123"},
    recipient_id="operational-agent-1",
    timeout=5.0
)

# S'abonner aux mises à jour de données
def data_update_callback(message):
    print(f"Mise à jour de données reçue: {message.content}")

subscription_id = visualization_adapter.subscribe_to_data_updates(
    data_types=["argument_structure", "fallacy_detection"],
    callback=data_update_callback
)
```

### Tests pour les adaptateurs

Les adaptateurs doivent être testés pour s'assurer qu'ils traduisent correctement les appels et les messages.
- Testez chaque méthode spécifique de l'adaptateur.
- Vérifiez la création correcte des messages sortants.
- Assurez-vous que les messages entrants sont correctement interprétés.

Vous trouverez des exemples de tests d'adaptateurs dans le répertoire [`tests/unit/argumentation_analysis/`](tests/unit/argumentation_analysis/) ou en examinant les tests des modules principaux.

## Bonnes pratiques de développement

### Gestion des erreurs

La gestion des erreurs est un aspect crucial du développement du système de communication multi-canal. Voici les bonnes pratiques à suivre :

#### 1. Détection précoce des erreurs

Validez les entrées dès que possible pour détecter les erreurs au plus tôt :

```python
def send_directive(self, directive_type, parameters, recipient_id, priority=MessagePriority.HIGH):
    # Valider les entrées
    if not directive_type:
        raise ValueError("Le type de directive ne peut pas être vide")
    
    if not recipient_id:
        raise ValueError("L'identifiant du destinataire ne peut pas être vide")
    
    if not isinstance(parameters, dict):
        raise TypeError("Les paramètres doivent être un dictionnaire")
    
    # Continuer avec l'envoi du message
    ...
```

#### 2. Gestion des exceptions

Utilisez des blocs try-except pour gérer les exceptions de manière appropriée :

```python
def receive_with_retry(self, message_type, timeout=5.0, max_retries=3):
    retries = 0
    while retries < max_retries:
        try:
            message = self.receive_message(message_type=message_type, timeout=timeout)
            return message
        except TimeoutError:
            retries += 1
            self.logger.warning(f"Timeout lors de la réception, réessai {retries}/{max_retries}")
        except ConnectionError as e:
            self.logger.error(f"Erreur de connexion: {e}")
            # Réessayer avec un délai exponentiel
            time.sleep(2 ** retries)
            retries += 1
        except Exception as e:
            self.logger.error(f"Erreur inattendue: {e}")
            raise  # Propager les autres exceptions
    
    return None  # Échec après tous les réessais
```

#### 3. Journalisation des erreurs

Journalisez les erreurs avec suffisamment de contexte pour faciliter le débogage :

```python
def send_message(self, message):
    try:
        # Envoyer le message
        message_id = self.middleware.send_message(message)
        self.logger.debug(f"Message {message_id} envoyé avec succès")
        return message_id
    except Exception as e:
        self.logger.error(f"Erreur lors de l'envoi du message: {e}", exc_info=True)
        self.logger.debug(f"Contenu du message: {message.content}")
        raise
```

#### 4. Stratégies de repli

Prévoyez des stratégies de repli en cas d'échec :

```python
def get_agent_status(self, agent_id, timeout=2.0):
    try:
        # Essayer d'obtenir le statut via le canal principal
        status = self.request_agent_status(agent_id, timeout=timeout)
        if status:
            return status
    except Exception as e:
        self.logger.warning(f"Erreur lors de la demande de statut via le canal principal: {e}")
    
    # Stratégie de repli: utiliser le canal de secours
    try:
        status = self.request_agent_status_backup(agent_id, timeout=timeout)
        return status
    except Exception as e:
        self.logger.error(f"Erreur lors de la demande de statut via le canal de secours: {e}")
    
    # Retourner un statut par défaut
    return {"status": "unknown", "reason": "communication_failure"}
```

### Tests unitaires et d'intégration

Les tests sont essentiels pour garantir la qualité et la fiabilité du système de communication. Voici les bonnes pratiques à suivre :

#### 1. Tests unitaires

Écrivez des tests unitaires pour chaque composant du système :

```python
import unittest
from unittest.mock import MagicMock, patch

class TestStrategicAdapter(unittest.TestCase):
    def setUp(self):
        # Créer un mock du middleware
        self.middleware = MagicMock()
        
        # Créer l'adaptateur à tester
        self.adapter = StrategicAdapter("strategic-agent-1", self.middleware)
    
    def test_issue_directive(self):
        # Configurer le mock
        self.middleware.send_message.return_value = "msg-123"
        
        # Appeler la méthode à tester
        result = self.adapter.issue_directive(
            directive_type="analyze_text",
            parameters={"text_id": "text-123"},
            recipient_id="tactical-agent-1",
            priority=MessagePriority.HIGH
        )
        
        # Vérifier le résultat
        self.assertEqual(result, "msg-123")
        
        # Vérifier que le middleware a été appelé correctement
        self.middleware.send_message.assert_called_once()
        
        # Vérifier les arguments de l'appel
        args, kwargs = self.middleware.send_message.call_args
        message = args[0]
        
        self.assertEqual(message.type, MessageType.COMMAND)
        self.assertEqual(message.sender, "strategic-agent-1")
        self.assertEqual(message.sender_level, AgentLevel.STRATEGIC)
        self.assertEqual(message.recipient, "tactical-agent-1")
        self.assertEqual(message.content["command_type"], "analyze_text")
        self.assertEqual(message.content["parameters"]["text_id"], "text-123")
        self.assertEqual(message.priority, MessagePriority.HIGH)
```

Pour un exemple concret de test unitaire, vous pouvez examiner [`tests/unit/project_core/utils/test_file_utils.py`](tests/unit/project_core/utils/test_file_utils.py:0) qui teste les utilitaires de fichiers.

#### 2. Tests d'intégration

Écrivez des tests d'intégration pour valider les interactions entre les composants :

```python
class TestCommunicationIntegration(unittest.TestCase):
    def setUp(self):
        # Créer le middleware
        self.middleware = MessageMiddleware()
        
        # Enregistrer les canaux
        self.hierarchical_channel = HierarchicalChannel("hierarchical")
        self.middleware.register_channel(self.hierarchical_channel)
        
        # Initialiser les protocoles
        self.middleware.initialize_protocols()
        
        # Créer les adaptateurs
        self.strategic_adapter = StrategicAdapter("strategic-agent-1", self.middleware)
        self.tactical_adapter = TacticalAdapter("tactical-agent-1", self.middleware)
    
    def test_directive_report_flow(self):
        # Simuler un agent tactique qui reçoit une directive et envoie un rapport
        def tactical_agent():
            # Recevoir la directive
            directive = self.tactical_adapter.receive_directive(timeout=2.0)
            
            # Vérifier que la directive a été reçue
            self.assertIsNotNone(directive)
            self.assertEqual(directive.sender, "strategic-agent-1")
            self.assertEqual(directive.content["command_type"], "analyze_text")
            
            # Envoyer un rapport
            self.tactical_adapter.send_report(
                report_type="status_update",
                content={"status": "in_progress", "completion": 50},
                recipient_id="strategic-agent-1",
                priority=MessagePriority.NORMAL
            )
        
        # Démarrer un thread pour simuler l'agent tactique
        import threading
        tactical_thread = threading.Thread(target=tactical_agent)
        tactical_thread.start()
        
        # Simuler un agent stratégique qui émet une directive et reçoit un rapport
        # Émettre une directive
        self.strategic_adapter.issue_directive(
            directive_type="analyze_text",
            parameters={"text_id": "text-123"},
            recipient_id="tactical-agent-1",
            priority=MessagePriority.HIGH
        )
        
        # Recevoir un rapport
        report = self.strategic_adapter.receive_report(timeout=2.0)
        
        # Vérifier que le rapport a été reçu
        self.assertIsNotNone(report)
        self.assertEqual(report.sender, "tactical-agent-1")
        self.assertEqual(report.content["report_type"], "status_update")
        self.assertEqual(report.content["data"]["completion"], 50)
        
        # Attendre que le thread se termine
        tactical_thread.join()
```

Un exemple de test d'intégration pertinent est [`tests/integration/test_logic_agents_integration.py`](tests/integration/test_logic_agents_integration.py:0), qui vérifie l'interaction entre différents agents logiques.

#### 3. Tests de performance

Écrivez des tests de performance pour évaluer les performances du système :

```python
class TestCommunicationPerformance(unittest.TestCase):
    def setUp(self):
        # Créer le middleware
        self.middleware = MessageMiddleware()
        
        # Enregistrer les canaux
        self.hierarchical_channel = HierarchicalChannel("hierarchical")
        self.middleware.register_channel(self.hierarchical_channel)
        
        # Initialiser les protocoles
        self.middleware.initialize_protocols()
        
        # Créer les adaptateurs
        self.strategic_adapter = StrategicAdapter("strategic-agent-1", self.middleware)
        self.tactical_adapter = TacticalAdapter("tactical-agent-1", self.middleware)
    
    def test_message_throughput(self):
        # Nombre de messages à envoyer
        num_messages = 1000
        
        # Mesurer le temps d'envoi
        start_time = time.time()
        
        for i in range(num_messages):
            self.strategic_adapter.issue_directive(
                directive_type=f"test-{i}",
                parameters={"index": i},
                recipient_id="tactical-agent-1",
                priority=MessagePriority.NORMAL
            )
        
        end_time = time.time()
        
        # Calculer le débit
        elapsed_time = end_time - start_time
        throughput = num_messages / elapsed_time
        
        print(f"Débit: {throughput:.2f} messages/seconde")
        
        # Vérifier que le débit est acceptable
        self.assertGreater(throughput, 100)  # Au moins 100 messages par seconde
```

### Performance et optimisation

L'optimisation des performances est importante pour garantir l'efficacité du système de communication. Voici les bonnes pratiques à suivre :

#### 1. Profilage

Utilisez des outils de profilage pour identifier les goulots d'étranglement :

```python
import cProfile
import pstats

def profile_middleware():
    # Créer le middleware
    middleware = MessageMiddleware()
    
    # Enregistrer les canaux
    hierarchical_channel = HierarchicalChannel("hierarchical")
    middleware.register_channel(hierarchical_channel)
    
    # Initialiser les protocoles
    middleware.initialize_protocols()
    
    # Créer les adaptateurs
    strategic_adapter = StrategicAdapter("strategic-agent-1", middleware)
    tactical_adapter = TacticalAdapter("tactical-agent-1", middleware)
    
    # Profiler l'envoi de messages
    cProfile.runctx(
        "for i in range(1000): strategic_adapter.issue_directive('test', {'index': i}, 'tactical-agent-1')",
        globals(),
        locals(),
        "profile_results"
    )
    
    # Analyser les résultats
    stats = pstats.Stats("profile_results")
    stats.strip_dirs().sort_stats("cumulative").print_stats(20)

# Exécuter le profilage
profile_middleware()
```

#### 2. Optimisation des messages

Optimisez la taille et le format des messages :

```python
def optimize_message(message):
    # Copie du message pour éviter de modifier l'original
    optimized = message.copy()
    
    # Supprimer les champs vides ou nuls
    for key in list(optimized.content.keys()):
        if optimized.content[key] is None or (isinstance(optimized.content[key], (dict, list)) and not optimized.content[key]):
            del optimized.content[key]
    
    # Compresser le contenu si nécessaire
    if len(json.dumps(optimized.content)) > 1024:  # Si > 1KB
        import gzip
        import base64
        
        # Compresser le contenu
        content_json = json.dumps(optimized.content)
        compressed = gzip.compress(content_json.encode('utf-8'))
        
        # Remplacer le contenu par sa version compressée
        optimized.content = None
        optimized.metadata["compression"] = "gzip"
        optimized.metadata["original_content_length"] = len(content_json)
        optimized.metadata["compressed_content"] = base64.b64encode(compressed).decode('utf-8')
    
    return optimized
```

#### 3. Mise en cache

Utilisez des mécanismes de mise en cache pour éviter les opérations répétitives :

```python
class CachedAdapter(AgentAdapter):
    def __init__(self, agent_id, middleware, cache_size=100, cache_ttl=300):
        super().__init__(agent_id, middleware)
        
        # Cache LRU
        self.cache = {}
        self.cache_order = []
        self.cache_size = cache_size
        self.cache_ttl = cache_ttl  # Durée de vie en secondes
        self.cache_timestamps = {}
    
    def get_cached_response(self, request_type, parameters):
        # Créer une clé de cache
        cache_key = f"{request_type}:{json.dumps(parameters, sort_keys=True)}"
        
        # Vérifier si la réponse est dans le cache
        if cache_key in self.cache:
            # Vérifier si la réponse a expiré
            if time.time() - self.cache_timestamps[cache_key] > self.cache_ttl:
                # Supprimer la réponse expirée
                del self.cache[cache_key]
                self.cache_order.remove(cache_key)
                del self.cache_timestamps[cache_key]
                return None
            
            # Mettre à jour l'ordre LRU
            self.cache_order.remove(cache_key)
            self.cache_order.append(cache_key)
            
            return self.cache[cache_key]
        
        return None
    
    def cache_response(self, request_type, parameters, response):
        # Créer une clé de cache
        cache_key = f"{request_type}:{json.dumps(parameters, sort_keys=True)}"
        
        # Ajouter la réponse au cache
        self.cache[cache_key] = response
        self.cache_timestamps[cache_key] = time.time()
        self.cache_order.append(cache_key)
        
        # Supprimer les entrées les plus anciennes si le cache est plein
        while len(self.cache) > self.cache_size:
            oldest_key = self.cache_order.pop(0)
            del self.cache[oldest_key]
            del self.cache_timestamps[oldest_key]
```

#### 4. Traitement asynchrone

Utilisez le traitement asynchrone pour améliorer les performances :

```python
import asyncio

class AsyncAdapter(AgentAdapter):
    async def send_message_async(self, message_type, content, recipient=None, priority=MessagePriority.NORMAL, metadata=None):
        """
        Envoie un message de manière asynchrone.
        
        Args:
            message_type: Type de message
            content: Contenu du message
            recipient: Destinataire (
            recipient=recipient,
            content={
                "alert_type": alert_type,
                "alert_level": alert_level,
                "details": details
            },
            priority=priority
        )

# Ajouter une méthode d'aide à l'adaptateur tactique
def send_alert(self, alert_type, alert_level, details, recipient=None, priority=MessagePriority.HIGH):
    message = AlertMessage(
        sender=self.agent_id,
        sender_level=AgentLevel.TACTICAL,
        alert_type=alert_type,
        alert_level=alert_level,
        details=details,
        recipient=recipient,
        priority=priority
    )
    return self.middleware.send_message(message)

# Ajouter la méthode à la classe d'adaptateur
TacticalAdapter.send_alert = send_alert
```

## Comment implémenter de nouveaux protocoles

### Structure d'un protocole

Un protocole de communication définit un pattern d'interaction standardisé entre les agents. Chaque protocole implémente une séquence d'échanges de messages spécifique pour un type d'interaction particulier.

La structure typique d'un protocole comprend :

1. **Définition des messages** : Types de messages spécifiques au protocole
2. **Séquence d'échanges** : Ordre et règles des échanges de messages
3. **Gestion des états** : Suivi de l'état des interactions en cours
4. **Gestion des erreurs** : Mécanismes pour gérer les erreurs et les timeouts
5. **Validation** : Vérification de la conformité des messages au protocole

### Interface à implémenter

Tous les protocoles de communication doivent implémenter l'interface `ProtocolInterface` qui définit les méthodes requises pour interagir avec le middleware. Voici les principales méthodes de cette interface :

```python
class ProtocolInterface:
    """Interface que tous les protocoles de communication doivent implémenter."""
    
    def __init__(self, middleware):
        """
        Initialise un nouveau protocole.
        
        Args:
            middleware: Le middleware de messagerie
        """
        self.middleware = middleware
    
    def initialize(self):
        """
        Initialise le protocole.
        
        Returns:
            True si l'initialisation a réussi, False sinon
        """
        raise NotImplementedError("Les sous-classes doivent implémenter cette méthode")
    
    def handle_message(self, message):
        """
        Traite un message selon ce protocole.
        
        Args:
            message: Le message à traiter
            
        Returns:
            True si le message a été traité, False sinon
        """
        raise NotImplementedError("Les sous-classes doivent implémenter cette méthode")
    
    def get_protocol_name(self):
        """
        Récupère le nom du protocole.
        
        Returns:
            Le nom du protocole
        """
        raise NotImplementedError("Les sous-classes doivent implémenter cette méthode")
    
    def get_supported_message_types(self):
        """
        Récupère les types de messages supportés par ce protocole.
        
        Returns:
            Liste des types de messages supportés
        """
        raise NotImplementedError("Les sous-classes doivent implémenter cette méthode")
```

### Gestion des échanges

La gestion des échanges est au cœur de l'implémentation d'un protocole. Voici les principales fonctionnalités à implémenter :

#### 1. Suivi des conversations

Chaque protocole doit maintenir un suivi des conversations en cours pour associer les messages de réponse aux messages de requête :

```python
class MyProtocol(ProtocolInterface):
    def __init__(self, middleware):
        super().__init__(middleware)
        
        # Suivi des conversations
        self.conversations = {}
        
        # Verrou pour les accès concurrents
        self.lock = threading.Lock()
```

#### 2. Traitement des messages

La méthode `handle_message` doit traiter les messages selon les règles du protocole :

```python
def handle_message(self, message):
    # Vérifier si le message est supporté par ce protocole
    if message.type not in self.get_supported_message_types():
        return False
    
    # Traiter le message selon son type
    if message.type == MessageType.REQUEST:
        return self._handle_request(message)
    elif message.type == MessageType.RESPONSE:
        return self._handle_response(message)
    
    # Type de message non géré
    return False

def _handle_request(self, message):
    # Enregistrer la requête
    with self.lock:
        conversation_id = message.metadata.get("conversation_id")
        if not conversation_id:
            conversation_id = f"conv-{uuid.uuid4().hex}"
            message.metadata["conversation_id"] = conversation_id
        
        self.conversations[conversation_id] = {
            "request": message,
            "timestamp": time.time(),
            "status": "pending"
        }
    
    # Transmettre la requête au destinataire
    return self.middleware.send_message(message)

def _handle_response(self, message):
    # Associer la réponse à la requête
    with self.lock:
        conversation_id = message.metadata.get("conversation_id")
        request_id = message.metadata.get("request_id")
        
        if conversation_id and conversation_id in self.conversations:
            # Mettre à jour la conversation
            self.conversations[conversation_id]["response"] = message
            self.conversations[conversation_id]["status"] = "completed"
        elif request_id:
            # Rechercher la conversation par l'ID de la requête
            for conv_id, conv in self.conversations.items():
                if conv["request"].id == request_id:
                    conv["response"] = message
                    conv["status"] = "completed"
                    break
    
    # Transmettre la réponse à l'émetteur de la requête
    return self.middleware.send_message(message)
```

### Exemple de création d'un nouveau protocole

Voici un exemple complet de création d'un nouveau protocole de communication pour la négociation :

```python
from argumentiation_analysis.core.communication.protocol_interface import ProtocolInterface
from argumentiation_analysis.core.communication.message import MessageType, Message
import threading
import time
import uuid
import logging

class NegotiationProtocol(ProtocolInterface):
    """
    Protocole de négociation pour la résolution de conflits et l'allocation de ressources.
    
    Ce protocole implémente un processus de négociation en plusieurs étapes :
    1. Initialisation de la négociation
    2. Échange de propositions et contre-propositions
    3. Acceptation, rejet ou contre-proposition
    4. Résolution finale
    """
    
    def __init__(self, middleware):
        super().__init__(middleware)
        
        # Suivi des négociations
        self.negotiations = {}
        
        # Verrou pour les accès concurrents
        self.lock = threading.Lock()
        
        # Journalisation
        self.logger = logging.getLogger("NegotiationProtocol")
    
    def initialize(self):
        """Initialise le protocole de négociation."""
        self.logger.info("Initialisation du protocole de négociation")
        return True
    
    def handle_message(self, message):
        """Traite un message selon le protocole de négociation."""
        # Vérifier si le message est supporté par ce protocole
        if message.type not in self.get_supported_message_types():
            return False
        
        # Traiter le message selon son type
        if message.type == MessageType.NEGOTIATION_INIT:
            return self._handle_negotiation_init(message)
        elif message.type == MessageType.NEGOTIATION_PROPOSAL:
            return self._handle_negotiation_proposal(message)
        elif message.type == MessageType.NEGOTIATION_RESPONSE:
            return self._handle_negotiation_response(message)
        elif message.type == MessageType.NEGOTIATION_RESOLUTION:
            return self._handle_negotiation_resolution(message)
        
        # Type de message non géré
        return False
    
    def get_protocol_name(self):
        """Récupère le nom du protocole."""
        return "negotiation"
    
    def get_supported_message_types(self):
        """Récupère les types de messages supportés par ce protocole."""
        return [
            MessageType.NEGOTIATION_INIT,
            MessageType.NEGOTIATION_PROPOSAL,
            MessageType.NEGOTIATION_RESPONSE,
            MessageType.NEGOTIATION_RESOLUTION
        ]
    
    def _handle_negotiation_init(self, message):
        """Traite un message d'initialisation de négociation."""
        # Extraire les informations de la négociation
        negotiation_id = message.id
        participants = message.content.get("participants", [])
        topic = message.content.get("topic")
        
        # Enregistrer la négociation
        with self.lock:
            self.negotiations[negotiation_id] = {
                "initiator": message.sender,
                "participants": participants,
                "topic": topic,
                "status": "initialized",
                "rounds": 0,
                "proposals": {},
                "responses": {},
                "timestamp": time.time()
            }
        
        self.logger.info(f"Négociation {negotiation_id} initialisée par {message.sender} sur le sujet '{topic}'")
        
        # Transmettre le message à tous les participants
        for participant in participants:
            # Créer une copie du message pour chaque participant
            participant_message = Message(
                type=message.type,
                sender=message.sender,
                sender_level=message.sender_level,
                recipient=participant,
                content=message.content,
                priority=message.priority,
                metadata=message.metadata.copy()
            )
            
            # Envoyer le message
            self.middleware.send_message(participant_message)
        
        return True
    
    def _handle_negotiation_proposal(self, message):
        """Traite un message de proposition de négociation."""
        # Extraire les informations de la proposition
        negotiation_id = message.content.get("negotiation_id")
        round_number = message.content.get("round", 1)
        proposal = message.content.get("proposal", {})
        
        # Vérifier si la négociation existe
        with self.lock:
            if negotiation_id not in self.negotiations:
                self.logger.warning(f"Proposition reçue pour une négociation inconnue: {negotiation_id}")
                return False
            
            # Mettre à jour la négociation
            negotiation = self.negotiations[negotiation_id]
            negotiation["rounds"] = max(negotiation["rounds"], round_number)
            
            if "proposals" not in negotiation:
                negotiation["proposals"] = {}
            
            if round_number not in negotiation["proposals"]:
                negotiation["proposals"][round_number] = {}
            
            negotiation["proposals"][round_number][message.sender] = proposal
            negotiation["status"] = "proposal_received"
        
        self.logger.info(f"Proposition reçue de {message.sender} pour la négociation {negotiation_id}, round {round_number}")
        
        # Transmettre la proposition aux autres participants
        for participant in negotiation["participants"]:
            if participant != message.sender:
                # Créer une copie du message pour chaque participant
                participant_message = Message(
                    type=message.type,
                    sender=message.sender,
                    sender_level=message.sender_level,
                    recipient=participant,
                    content=message.content,
                    priority=message.priority,
                    metadata=message.metadata.copy()
                )
                
                # Envoyer le message
                self.middleware.send_message(participant_message)
        
        return True
    
    def _handle_negotiation_response(self, message):
        """Traite un message de réponse à une proposition de négociation."""
        # Extraire les informations de la réponse
        negotiation_id = message.content.get("negotiation_id")
        proposal_id = message.content.get("proposal_id")
        response = message.content.get("response")  # "accept
- Nouvelles implémentations de canaux
- Nouveaux protocoles de communication
- Nouveaux types d'adaptateurs
- Nouveaux types de messages

L'utilisation d'interfaces bien définies permet d'ajouter de nouveaux composants sans modifier le code existant.

#### 3. Découplage

Les agents communiquent sans connaître les détails d'implémentation des autres agents :
- Communication asynchrone
- Routage basé sur le contenu
- Abstraction des détails de transport

Ce découplage facilite l'évolution indépendante des différents composants du système.

#### 4. Robustesse

Le système est conçu pour être robuste face aux erreurs :
- Détection et notification des erreurs
- Stratégies de récupération
- Mécanismes de reprise
- Journalisation et audit

Ces mécanismes assurent la fiabilité du système même en cas de problèmes.

### Patterns utilisés

Le système de communication multi-canal utilise plusieurs patterns de conception :

#### 1. Adapter Pattern

Les adaptateurs d'agents (StrategicAdapter, TacticalAdapter, OperationalAdapter) implémentent le pattern Adapter en fournissant une interface simplifiée aux agents et en traduisant leurs appels en messages standardisés.

#### 2. Factory Method Pattern

Le middleware utilise le pattern Factory Method pour créer les instances appropriées de canaux et de protocoles en fonction de la configuration.

#### 3. Observer Pattern

Le protocole de publication-abonnement implémente le pattern Observer, où les abonnés (observers) sont notifiés des publications (events) sur les sujets auxquels ils sont abonnés.

#### 4. Strategy Pattern

Le système de routage des messages utilise le pattern Strategy pour déterminer le canal approprié pour chaque message en fonction de différentes stratégies (routage basé sur le type, routage basé sur le contenu, etc.).

#### 5. Chain of Responsibility Pattern

Le traitement des messages dans le middleware utilise le pattern Chain of Responsibility, où chaque gestionnaire de messages peut traiter le message ou le passer au gestionnaire suivant.

#### 6. Command Pattern

Les messages eux-mêmes implémentent le pattern Command, encapsulant une requête sous forme d'objet qui peut être transmis, mis en file d'attente et traité de manière asynchrone.