# Référence de l'API du système de communication multi-canal

## Table des matières

1. [Introduction](#introduction)
   - [Objectif de la documentation](#objectif-de-la-documentation)
   - [Conventions utilisées](#conventions-utilisées)

2. [Middleware de messagerie](#middleware-de-messagerie)
   - [MessageMiddleware](#messagemiddleware)
   - [Méthodes publiques](#méthodes-publiques-du-middleware)
   - [Configuration](#configuration-du-middleware)

3. [Canaux de communication](#canaux-de-communication)
   - [ChannelInterface](#channelinterface)
   - [HierarchicalChannel](#hierarchicalchannel)
   - [CollaborationChannel](#collaborationchannel)
   - [DataChannel](#datachannel)
   - [NegotiationChannel](#negotiationchannel)
   - [FeedbackChannel](#feedbackchannel)

4. [Adaptateurs d'agents](#adaptateurs-dagents)
   - [AgentAdapter](#agentadapter)
   - [StrategicAdapter](#strategicadapter)
   - [TacticalAdapter](#tacticaladapter)
   - [OperationalAdapter](#operationaladapter)

5. [Messages](#messages)
   - [Message](#message)
   - [MessageType](#messagetype)
   - [MessagePriority](#messagepriority)
   - [AgentLevel](#agentlevel)

6. [Protocoles de communication](#protocoles-de-communication)
   - [ProtocolInterface](#protocolinterface)
   - [RequestResponseProtocol](#requestresponseprotocol)
   - [PublishSubscribeProtocol](#publishsubscribeprotocol)
   - [NegotiationProtocol](#negotiationprotocol)

7. [Utilitaires](#utilitaires)
   - [MessageFilter](#messagefilter)
   - [MessageRouter](#messagerouter)
   - [MessageSerializer](#messageserializer)
   - [CommunicationMonitor](#communicationmonitor)

## Introduction

### Objectif de la documentation

Cette documentation de référence de l'API fournit une description détaillée de toutes les classes, méthodes et constantes publiques du système de communication multi-canal. Elle est destinée aux développeurs qui ont besoin de comprendre en profondeur le fonctionnement du système, que ce soit pour l'utiliser, l'étendre ou le maintenir.

Contrairement au guide d'utilisation et au guide du développeur qui se concentrent sur des cas d'utilisation et des scénarios spécifiques, cette documentation de référence est exhaustive et couvre l'ensemble de l'API publique du système.

### Conventions utilisées

Dans cette documentation, les conventions suivantes sont utilisées :

- Les noms de classes sont en `PascalCase`
- Les noms de méthodes et de variables sont en `snake_case`
- Les constantes sont en `MAJUSCULES_AVEC_UNDERSCORES`
- Les paramètres optionnels sont indiqués par `[paramètre]`
- Les types de retour sont indiqués après le symbole `→`
- Les exceptions sont indiquées par `raises ExceptionType`

## Middleware de messagerie

### MessageMiddleware

Le middleware de messagerie est le composant central du système de communication multi-canal. Il gère les canaux, les protocoles et le routage des messages.

```python
class MessageMiddleware:
    """
    Middleware de messagerie central qui coordonne les échanges entre les agents.
    """
    
    def __init__(self, config=None):
        """
        Initialise un nouveau middleware de messagerie.
        
        Args:
            config (dict, optional): Configuration du middleware.
                Valeurs possibles:
                - message_retention (int): Nombre de messages à conserver en mémoire (défaut: 100)
                - default_timeout (float): Timeout par défaut en secondes (défaut: 5.0)
                - enable_monitoring (bool): Activer le monitoring (défaut: True)
                - log_level (str): Niveau de journalisation (défaut: "INFO")
        """
```

### Méthodes publiques du middleware

#### Gestion des canaux

```python
def register_channel(self, channel):
    """
    Enregistre un canal auprès du middleware.
    
    Args:
        channel (ChannelInterface): Le canal à enregistrer
        
    Returns:
        bool: True si l'enregistrement a réussi, False sinon
        
    Raises:
        ValueError: Si un canal avec le même nom est déjà enregistré
    """

def unregister_channel(self, channel_name):
    """
    Désenregistre un canal du middleware.
    
    Args:
        channel_name (str): Nom du canal à désenregistrer
        
    Returns:
        bool: True si le désenregistrement a réussi, False sinon
        
    Raises:
        ValueError: Si le canal n'est pas enregistré
    """

def get_channel(self, channel_name):
    """
    Récupère un canal par son nom.
    
    Args:
        channel_name (str): Nom du canal à récupérer
        
    Returns:
        ChannelInterface: Le canal correspondant ou None s'il n'existe pas
    """

def get_registered_channels(self):
    """
    Récupère la liste des canaux enregistrés.
    
    Returns:
        list: Liste des noms de canaux enregistrés
    """
```

#### Gestion des protocoles

```python
def register_protocol(self, protocol):
    """
    Enregistre un protocole auprès du middleware.
    
    Args:
        protocol (ProtocolInterface): Le protocole à enregistrer
        
    Returns:
        bool: True si l'enregistrement a réussi, False sinon
        
    Raises:
        ValueError: Si un protocole avec le même nom est déjà enregistré
    """

def initialize_protocols(self):
    """
    Initialise tous les protocoles enregistrés.
    
    Returns:
        bool: True si l'initialisation a réussi, False sinon
    """

def get_protocol(self, protocol_name):
    """
    Récupère un protocole par son nom.
    
    Args:
        protocol_name (str): Nom du protocole à récupérer
        
    Returns:
        ProtocolInterface: Le protocole correspondant ou None s'il n'existe pas
    """
#### Gestion des messages

```python
def send_message(self, message):
    """
    Envoie un message via le middleware.
    
    Args:
        message (Message): Le message à envoyer
        
    Returns:
        str: L'identifiant du message envoyé
        
    Raises:
        ValueError: Si le message est invalide
        RuntimeError: Si le middleware n'est pas initialisé
    """

def receive_message(self, recipient_id, timeout=None, filter_criteria=None):
    """
    Reçoit un message via le middleware.
    
    Args:
        recipient_id (str): Identifiant du destinataire
        timeout (float, optional): Délai d'attente maximum en secondes
        filter_criteria (dict, optional): Critères de filtrage
        
    Returns:
        Message: Le message reçu ou None si aucun message n'est disponible
        
    Raises:
        TimeoutError: Si le timeout est atteint
        RuntimeError: Si le middleware n'est pas initialisé
    """

def get_pending_messages(self, recipient_id, channel_type=None):
    """
    Récupère tous les messages en attente pour un destinataire.
    
    Args:
        recipient_id (str): Identifiant du destinataire
        channel_type (ChannelType, optional): Type de canal
        
    Returns:
        list: Liste des messages en attente
    """

def wait_for_ack(self, message_id, timeout=5.0):
    """
    Attend un accusé de réception pour un message.
    
    Args:
        message_id (str): Identifiant du message
        timeout (float, optional): Délai d'attente maximum en secondes
        
    Returns:
        bool: True si l'accusé de réception a été reçu, False sinon
        
    Raises:
        TimeoutError: Si le timeout est atteint
    """
```

#### Publication-abonnement

```python
def subscribe(self, subscriber_id, topic_id, callback=None, filter_criteria=None):
    """
    Abonne un agent à un sujet.
    
    Args:
        subscriber_id (str): Identifiant de l'abonné
        topic_id (str): Identifiant du sujet
        callback (callable, optional): Fonction de rappel à appeler lors de la réception d'un message
        filter_criteria (dict, optional): Critères de filtrage
        
    Returns:
        str: Un identifiant d'abonnement
        
    Raises:
        ValueError: Si les paramètres sont invalides
    """

def unsubscribe(self, subscription_id):
    """
    Désabonne un agent d'un sujet.
    
    Args:
        subscription_id (str): Identifiant de l'abonnement
        
    Returns:
        bool: True si le désabonnement a réussi, False sinon
        
    Raises:
        ValueError: Si l'identifiant d'abonnement est invalide
    """

def publish(self, topic_id, sender, sender_level, content, priority=MessagePriority.NORMAL):
    """
    Publie un message sur un sujet.
    
    Args:
        topic_id (str): Identifiant du sujet
        sender (str): Identifiant de l'émetteur
        sender_level (AgentLevel): Niveau de l'émetteur
        content (dict): Contenu du message
        priority (MessagePriority, optional): Priorité du message
        
    Returns:
        str: L'identifiant du message publié
        
    Raises:
        ValueError: Si les paramètres sont invalides
    """
```

#### Routage des messages

```python
def add_routing_rule(self, message_type, channel_name):
    """
    Ajoute une règle de routage basée sur le type de message.
    
    Args:
        message_type (MessageType): Type de message
        channel_name (str): Nom du canal
        
    Returns:
        bool: True si l'ajout a réussi, False sinon
        
    Raises:
        ValueError: Si le canal n'est pas enregistré
    """

def add_content_routing_rule(self, field, value, channel):
    """
    Ajoute une règle de routage basée sur le contenu du message.
    
    Args:
        field (str): Chemin du champ dans le contenu (ex: "content.command_type")
        value (any): Valeur du champ
        channel (str): Nom du canal
        
    Returns:
        bool: True si l'ajout a réussi, False sinon
        
    Raises:
        ValueError: Si le canal n'est pas enregistré
    """

def get_routing_rules(self):
    """
    Récupère toutes les règles de routage.
    
    Returns:
        dict: Dictionnaire des règles de routage
    """
```

#### Monitoring et statistiques

```python
def get_statistics(self):
    """
    Récupère des statistiques sur l'utilisation du middleware.
    
    Returns:
        dict: Dictionnaire de statistiques
    """

def cleanup_expired_messages(self):
    """
    Nettoie les messages expirés.
    
    Returns:
        int: Nombre de messages nettoyés
    """

def is_initialized(self):
    """
    Vérifie si le middleware est initialisé.
    
    Returns:
        bool: True si le middleware est initialisé, False sinon
    """

def initialize(self):
    """
    Initialise le middleware.
    
    Returns:
        bool: True si l'initialisation a réussi, False sinon
    """

def shutdown(self):
    """
    Arrête proprement le middleware.
    
    Returns:
        bool: True si l'arrêt a réussi, False sinon
    """
```

### Configuration du middleware

Le middleware peut être configuré avec les options suivantes :

| Option | Type | Description | Valeur par défaut |
|--------|------|-------------|-------------------|
| `message_retention` | int | Nombre de messages à conserver en mémoire | 100 |
| `default_timeout` | float | Timeout par défaut en secondes | 5.0 |
| `enable_monitoring` | bool | Activer le monitoring | True |
| `log_level` | str | Niveau de journalisation | "INFO" |
| `max_message_size` | int | Taille maximale des messages en octets | 1048576 (1MB) |
| `compression_threshold` | int | Seuil de compression en octets | 10240 (10KB) |
| `compression_enabled` | bool | Activer la compression | True |
| `message_ttl` | int | Durée de vie des messages en secondes | 3600 (1h) |
| `max_subscribers_per_topic` | int | Nombre maximum d'abonnés par sujet | 100 |
| `max_topics` | int | Nombre maximum de sujets | 1000 |
| `max_routing_rules` | int | Nombre maximum de règles de routage | 100 |
| `max_channels` | int | Nombre maximum de canaux | 10 |
| `max_protocols` | int | Nombre maximum de protocoles | 10 |

## Canaux de communication

### ChannelInterface

L'interface que tous les canaux de communication doivent implémenter.

```python
class ChannelInterface:
    """
    Interface que tous les canaux de communication doivent implémenter.
    """
    
    def __init__(self, name, config=None):
        """
        Initialise un nouveau canal.
        
        Args:
            name (str): Nom unique du canal
            config (dict, optional): Configuration du canal
        """
```

#### Méthodes de l'interface

```python
def send_message(self, message):
    """
    Envoie un message via ce canal.
    
    Args:
        message (Message): Le message à envoyer
        
    Returns:
        bool: True si le message a été envoyé avec succès, False sinon
        
    Raises:
        NotImplementedError: Les sous-classes doivent implémenter cette méthode
    """

def receive_message(self, recipient_id, timeout=None):
    """
    Reçoit un message de ce canal.
    
    Args:
        recipient_id (str): Identifiant du destinataire
        timeout (float, optional): Délai d'attente maximum en secondes
        
    Returns:
        Message: Le message reçu ou None si aucun message n'est disponible
        
    Raises:
        NotImplementedError: Les sous-classes doivent implémenter cette méthode
        TimeoutError: Si le timeout est atteint
    """

def get_pending_messages(self, recipient_id):
    """
    Récupère tous les messages en attente pour un destinataire.
    
    Args:
        recipient_id (str): Identifiant du destinataire
        
    Returns:
        list: Liste des messages en attente
        
    Raises:
        NotImplementedError: Les sous-classes doivent implémenter cette méthode
    """

def subscribe(self, subscriber_id, filter_criteria=None):
    """
    Abonne un agent à ce canal.
    
    Args:
        subscriber_id (str): Identifiant de l'abonné
        filter_criteria (dict, optional): Critères de filtrage
        
    Returns:
        str: Un identifiant d'abonnement
        
    Raises:
        NotImplementedError: Les sous-classes doivent implémenter cette méthode
    """

def unsubscribe(self, subscription_id):
    """
    Désabonne un agent de ce canal.
    
    Args:
        subscription_id (str): Identifiant de l'abonnement
        
    Returns:
        bool: True si le désabonnement a réussi, False sinon
        
    Raises:
        NotImplementedError: Les sous-classes doivent implémenter cette méthode
    """

### HierarchicalChannel

Canal de communication hiérarchique pour les échanges formels entre les différents niveaux de la hiérarchie.

```python
class HierarchicalChannel(ChannelInterface):
    """
    Canal de communication hiérarchique pour les échanges formels entre les différents niveaux de la hiérarchie.
    """
    
    def __init__(self, name, config=None):
        """
        Initialise un nouveau canal hiérarchique.
        
        Args:
            name (str): Nom unique du canal
            config (dict, optional): Configuration du canal.
                Valeurs possibles:
                - priority_levels (int): Nombre de niveaux de priorité (défaut: 4)
                - message_ordering (bool): Préserver l'ordre des messages (défaut: True)
                - delivery_guarantee (bool): Garantir la livraison des messages (défaut: True)
        """
```

#### Méthodes spécifiques

```python
def set_priority_levels(self, levels):
    """
    Définit le nombre de niveaux de priorité.
    
    Args:
        levels (int): Nombre de niveaux de priorité
        
    Returns:
        bool: True si la modification a réussi, False sinon
        
    Raises:
        ValueError: Si le nombre de niveaux est inférieur à 1
    """

def set_message_ordering(self, enabled):
    """
    Active ou désactive la préservation de l'ordre des messages.
    
    Args:
        enabled (bool): True pour activer, False pour désactiver
        
    Returns:
        bool: True si la modification a réussi, False sinon
    """

def set_delivery_guarantee(self, enabled):
    """
    Active ou désactive la garantie de livraison des messages.
    
    Args:
        enabled (bool): True pour activer, False pour désactiver
        
    Returns:
        bool: True si la modification a réussi, False sinon
    """
```

### CollaborationChannel

Canal de communication pour les interactions horizontales entre agents de même niveau.

```python
class CollaborationChannel(ChannelInterface):
    """
    Canal de communication pour les interactions horizontales entre agents de même niveau.
    """
    
    def __init__(self, name, config=None):
        """
        Initialise un nouveau canal de collaboration.
        
        Args:
            name (str): Nom unique du canal
            config (dict, optional): Configuration du canal.
                Valeurs possibles:
                - max_participants (int): Nombre maximum de participants (défaut: 10)
                - context_retention (bool): Conserver le contexte des collaborations (défaut: True)
                - broadcast_enabled (bool): Autoriser les diffusions (défaut: True)
        """
```

#### Méthodes spécifiques

```python
def create_collaboration_group(self, group_name, participants):
    """
    Crée un groupe de collaboration.
    
    Args:
        group_name (str): Nom du groupe
        participants (list): Liste des identifiants des participants
        
    Returns:
        str: Identifiant du groupe
        
    Raises:
        ValueError: Si le nom du groupe est invalide ou si la liste des participants est vide
    """

def join_collaboration_group(self, group_id, participant_id):
    """
    Ajoute un participant à un groupe de collaboration.
    
    Args:
        group_id (str): Identifiant du groupe
        participant_id (str): Identifiant du participant
        
    Returns:
        bool: True si l'ajout a réussi, False sinon
        
    Raises:
        ValueError: Si le groupe n'existe pas
    """

def leave_collaboration_group(self, group_id, participant_id):
    """
    Retire un participant d'un groupe de collaboration.
    
    Args:
        group_id (str): Identifiant du groupe
        participant_id (str): Identifiant du participant
        
    Returns:
        bool: True si le retrait a réussi, False sinon
        
    Raises:
        ValueError: Si le groupe n'existe pas ou si le participant n'est pas membre du groupe
    """

def broadcast_to_group(self, group_id, message):
    """
    Diffuse un message à tous les membres d'un groupe de collaboration.
    
    Args:
        group_id (str): Identifiant du groupe
        message (Message): Le message à diffuser
        
    Returns:
        bool: True si la diffusion a réussi, False sinon
        
    Raises:
        ValueError: Si le groupe n'existe pas
    """
```

### DataChannel

Canal de communication pour le transfert efficace de volumes importants de données structurées.

```python
class DataChannel(ChannelInterface):
    """
    Canal de communication pour le transfert efficace de volumes importants de données structurées.
    """
    
    def __init__(self, name, config=None):
        """
        Initialise un nouveau canal de données.
        
        Args:
            name (str): Nom unique du canal
            config (dict, optional): Configuration du canal.
                Valeurs possibles:
                - compression_enabled (bool): Activer la compression (défaut: True)
                - max_data_size (str): Taille maximale des données (défaut: "10MB")
                - versioning_enabled (bool): Activer le versionnement (défaut: True)
        """
```

#### Méthodes spécifiques

```python
def set_compression_enabled(self, enabled):
    """
    Active ou désactive la compression des données.
    
    Args:
        enabled (bool): True pour activer, False pour désactiver
        
    Returns:
        bool: True si la modification a réussi, False sinon
    """

def set_compression_threshold(self, threshold):
    """
    Définit le seuil de compression en octets.
    
    Args:
        threshold (int): Seuil de compression en octets
        
    Returns:
        bool: True si la modification a réussi, False sinon
        
    Raises:
        ValueError: Si le seuil est inférieur à 0
    """

def set_max_data_size(self, max_size):
    """
    Définit la taille maximale des données.
    
    Args:
        max_size (str): Taille maximale des données (ex: "10MB")
        
    Returns:
        bool: True si la modification a réussi, False sinon
        
    Raises:
        ValueError: Si la taille est invalide
    """

def send_data_chunk(self, chunk_id, data, recipient_id, total_chunks, chunk_index, metadata=None):
    """
    Envoie un fragment de données.
    
    Args:
        chunk_id (str): Identifiant du fragment
        data (bytes): Données du fragment
        recipient_id (str): Identifiant du destinataire
        total_chunks (int): Nombre total de fragments
        chunk_index (int): Index du fragment
        metadata (dict, optional): Métadonnées du fragment
        
    Returns:
        bool: True si l'envoi a réussi, False sinon
        
    Raises:
        ValueError: Si les paramètres sont invalides
    """

def receive_data_chunk(self, recipient_id, chunk_id=None, timeout=None):
    """
    Reçoit un fragment de données.
    
    Args:
        recipient_id (str): Identifiant du destinataire
        chunk_id (str, optional): Identifiant du fragment
        timeout (float, optional): Délai d'attente maximum en secondes
        
    Returns:
        dict: Le fragment reçu ou None si aucun fragment n'est disponible
        
    Raises:
        TimeoutError: Si le timeout est atteint
    """

def is_data_complete(self, recipient_id, chunk_id):
    """
    Vérifie si tous les fragments d'un ensemble de données ont été reçus.
    
    Args:
        recipient_id (str): Identifiant du destinataire
        chunk_id (str): Identifiant du fragment
        
    Returns:
        bool: True si tous les fragments ont été reçus, False sinon
    """

def assemble_data(self, recipient_id, chunk_id):
    """
    Assemble les fragments d'un ensemble de données.
    
    Args:
        recipient_id (str): Identifiant du destinataire
        chunk_id (str): Identifiant du fragment
        
    Returns:
        bytes: Les données assemblées ou None si tous les fragments n'ont pas été reçus
        
    Raises:
        ValueError: Si l'identifiant du fragment est invalide
    """
```

### NegotiationChannel

Canal de communication pour la résolution de conflits et la prise de décisions collaboratives.

```python
class NegotiationChannel(ChannelInterface):
    """
    Canal de communication pour la résolution de conflits et la prise de décisions collaboratives.
    """
    
    def __init__(self, name, config=None):
        """
        Initialise un nouveau canal de négociation.
        
        Args:
            name (str): Nom unique du canal
            config (dict, optional): Configuration du canal.
                Valeurs possibles:
                - max_rounds (int): Nombre maximum de tours de négociation (défaut: 10)
                - timeout_per_round (float): Timeout par tour en secondes (défaut: 60.0)
                - auto_resolution (bool): Résolution automatique des conflits (défaut: False)
        """
```

#### Méthodes spécifiques

```python
def create_negotiation(self, initiator_id, participants, topic, initial_proposal=None):
    """
    Crée une nouvelle négociation.
    
    Args:
        initiator_id (str): Identifiant de l'initiateur
        participants (list): Liste des identifiants des participants
        topic (str): Sujet de la négociation
        initial_proposal (dict, optional): Proposition initiale
        
    Returns:
        str: Identifiant de la négociation
        
    Raises:
        ValueError: Si les paramètres sont invalides
    """

def submit_proposal(self, negotiation_id, participant_id, proposal, round_number=None):
    """
    Soumet une proposition dans le cadre d'une négociation.
    
    Args:
        negotiation_id (str): Identifiant de la négociation
        participant_id (str): Identifiant du participant
        proposal (dict): Proposition
        round_number (int, optional): Numéro du tour
        
    Returns:
        bool: True si la soumission a réussi, False sinon
        
    Raises:
        ValueError: Si les paramètres sont invalides
    """

def respond_to_proposal(self, negotiation_id, participant_id, proposal_id, response, counter_proposal=None):
    """
    Répond à une proposition dans le cadre d'une négociation.
    
    Args:
        negotiation_id (str): Identifiant de la négociation
        participant_id (str): Identifiant du participant
        proposal_id (str): Identifiant de la proposition
        response (str): Réponse ("accept", "reject", "counter")
        counter_proposal (dict, optional): Contre-proposition
        
    Returns:
        bool: True si la réponse a réussi, False sinon
        
    Raises:
        ValueError: Si les paramètres sont invalides
    """

def get_negotiation_status(self, negotiation_id):
    """
    Récupère le statut d'une négociation.
    
    Args:
        negotiation_id (str): Identifiant de la négociation
        
    Returns:
        dict: Statut de la négociation
        
    Raises:
        ValueError: Si l'identifiant de la négociation est invalide
    """

def resolve_negotiation(self, negotiation_id, resolution, resolver_id=None):
    """
    Résout une négociation.
    
    Args:
        negotiation_id (str): Identifiant de la négociation
        resolution (dict): Résolution
        resolver_id (str, optional): Identifiant du résolveur
        
    Returns:
        bool: True si la résolution a réussi, False sinon
        
    Raises:
        ValueError: Si les paramètres sont invalides
    """
```

### FeedbackChannel

Canal de communication pour la remontée d'informations, de suggestions et d'évaluations.

```python
class FeedbackChannel(ChannelInterface):
    """
    Canal de communication pour la remontée d'informations, de suggestions et d'évaluations.
    """
    
    def __init__(self, name, config=None):
        """
        Initialise un nouveau canal de feedback.
        
        Args:
            name (str): Nom unique du canal
            config (dict, optional): Configuration du canal.
                Valeurs possibles:
                - feedback_categories (list): Catégories de feedback (défaut: ["general", "performance", "quality"])
                - anonymous_allowed (bool): Autoriser les feedbacks anonymes (défaut: True)
                - aggregation_enabled (bool): Activer l'agrégation des feedbacks (défaut: True)
        """
```

#### Méthodes spécifiques

```python
def send_feedback(self, sender_id, recipient_id, feedback_type, content, category="general", anonymous=False):
    """
    Envoie un feedback.
    
    Args:
        sender_id (str): Identifiant de l'émetteur
        recipient_id (str): Identifiant du destinataire
        feedback_type (str): Type de feedback
        content (dict): Contenu du feedback
        category (str, optional): Catégorie du feedback
        anonymous (bool, optional): Feedback anonyme
        
    Returns:
        str: Identifiant du feedback
        
    Raises:
        ValueError: Si les paramètres sont invalides
    """

def get_feedback(self, recipient_id, feedback_id=None, category=None, feedback_type=None):
    """
    Récupère des feedbacks.
    
    Args:
        recipient_id (str): Identifiant du destinataire
        feedback_id (str, optional): Identifiant du feedback
        category (str, optional): Catégorie du feedback
        feedback_type (str, optional): Type de feedback
        
    Returns:
        list: Liste des feedbacks
        
    Raises:
        ValueError: Si les paramètres sont invalides
    """

def aggregate_feedback(self, recipient_id, category=None, feedback_type=None, aggregation_function=None):
    """
    Agrège des feedbacks.
    
    Args:
        recipient_id (str): Identifiant du destinataire
        category (str, optional): Catégorie du feedback
        feedback_type (str, optional): Type de feedback
        aggregation_function (callable, optional): Fonction d'agrégation
        
    Returns:
        dict: Résultat de l'agrégation
        
    Raises:
        ValueError: Si les paramètres sont invalides
    """

def get_feedback_categories(self):
    """
    Récupère les catégories de feedback disponibles.
    
    Returns:
        list: Liste des catégories de feedback
    """

def add_feedback_category(self, category):
    """
    Ajoute une catégorie de feedback.
    
    Args:
        category (str): Catégorie de feedback
        
    Returns:
        bool: True si l'ajout a réussi, False sinon
        
    Raises:
        ValueError: Si la catégorie est invalide
    """
```
def get_statistics(self):
    """
    Récupère des statistiques sur l'utilisation du canal.
    
    Returns:
        dict: Un dictionnaire de statistiques
        
## Adaptateurs d'agents

### AgentAdapter

Classe de base pour tous les adaptateurs d'agents.

```python
class AgentAdapter:
    """
    Classe de base pour tous les adaptateurs d'agents.
    """
    
    def __init__(self, agent_id, middleware):
        """
        Initialise un nouvel adaptateur d'agent.
        
        Args:
            agent_id (str): Identifiant unique de l'agent
            middleware (MessageMiddleware): Le middleware de messagerie
        """
```

#### Méthodes communes

```python
def send_message(self, message_type, content, recipient=None, priority=MessagePriority.NORMAL, metadata=None):
    """
    Envoie un message générique.
    
    Args:
        message_type (MessageType): Type de message
        content (dict): Contenu du message
        recipient (str, optional): Destinataire
        priority (MessagePriority, optional): Priorité du message
        metadata (dict, optional): Métadonnées du message
        
    Returns:
        str: L'identifiant du message envoyé
        
    Raises:
        ValueError: Si les paramètres sont invalides
        RuntimeError: Si le middleware n'est pas initialisé
    """

def receive_message(self, message_type=None, timeout=None, filter_criteria=None):
    """
    Reçoit un message.
    
    Args:
        message_type (MessageType, optional): Type de message à recevoir
        timeout (float, optional): Délai d'attente maximum en secondes
        filter_criteria (dict, optional): Critères de filtrage supplémentaires
        
    Returns:
        Message: Le message reçu ou None si aucun message n'est disponible
        
    Raises:
        TimeoutError: Si le timeout est atteint
        RuntimeError: Si le middleware n'est pas initialisé
    """

def subscribe(self, topic, callback=None, filter_criteria=None):
    """
    S'abonne à un sujet.
    
    Args:
        topic (str): Sujet auquel s'abonner
        callback (callable, optional): Fonction de rappel à appeler lors de la réception d'un message
        filter_criteria (dict, optional): Critères de filtrage
        
    Returns:
        str: Un identifiant d'abonnement
        
    Raises:
        ValueError: Si les paramètres sont invalides
    """

def unsubscribe(self, subscription_id):
    """
    Désabonne d'un sujet.
    
    Args:
        subscription_id (str): Identifiant de l'abonnement
        
    Returns:
        bool: True si le désabonnement a réussi, False sinon
        
    Raises:
        ValueError: Si l'identifiant d'abonnement est invalide
    """

def _get_agent_level(self):
    """
    Récupère le niveau de l'agent.
    
    Returns:
        AgentLevel: Le niveau de l'agent
        
    Raises:
        NotImplementedError: Les sous-classes doivent implémenter cette méthode
    """
```

### StrategicAdapter

Adaptateur pour les agents stratégiques.

```python
class StrategicAdapter(AgentAdapter):
    """
    Adaptateur pour les agents stratégiques.
    """
    
    def __init__(self, agent_id, middleware):
        """
        Initialise un nouvel adaptateur stratégique.
        
        Args:
            agent_id (str): Identifiant unique de l'agent
            middleware (MessageMiddleware): Le middleware de messagerie
        """
```

#### Méthodes spécifiques

```python
def issue_directive(self, directive_type, parameters, recipient_id, priority=MessagePriority.HIGH, requires_ack=False, metadata=None):
    """
    Émet une directive stratégique.
    
    Args:
        directive_type (str): Type de directive
        parameters (dict): Paramètres de la directive
        recipient_id (str): Identifiant du destinataire tactique
        priority (MessagePriority, optional): Priorité de la directive
        requires_ack (bool, optional): Indique si un accusé de réception est requis
        metadata (dict, optional): Métadonnées supplémentaires
        
    Returns:
        str: L'identifiant de la directive émise
        
    Raises:
        ValueError: Si les paramètres sont invalides
    """

def receive_report(self, timeout=None, filter_criteria=None):
    """
    Reçoit un rapport tactique.
    
    Args:
        timeout (float, optional): Délai d'attente maximum en secondes
        filter_criteria (dict, optional): Critères de filtrage supplémentaires
        
    Returns:
        Message: Le rapport reçu ou None si aucun rapport n'est disponible
        
    Raises:
        TimeoutError: Si le timeout est atteint
    """

def request_tactical_status(self, recipient_id, timeout=5.0, priority=MessagePriority.NORMAL):
    """
    Demande le statut d'un agent tactique.
    
    Args:
        recipient_id (str): Identifiant de l'agent tactique
        timeout (float, optional): Délai d'attente maximum en secondes
        priority (MessagePriority, optional): Priorité de la demande
        
    Returns:
        dict: Le statut de l'agent tactique ou None si timeout
        
    Raises:
        TimeoutError: Si le timeout est atteint
    """

def broadcast_strategic_update(self, update_type, content, recipients=None, priority=MessagePriority.NORMAL):
    """
    Diffuse une mise à jour stratégique.
    
    Args:
        update_type (str): Type de mise à jour
        content (dict): Contenu de la mise à jour
        recipients (list, optional): Liste des destinataires
        priority (MessagePriority, optional): Priorité de la mise à jour
        
    Returns:
        list: Liste des identifiants des messages envoyés
        
    Raises:
        ValueError: Si les paramètres sont invalides
    """
```

### TacticalAdapter

Adaptateur pour les agents tactiques.

```python
class TacticalAdapter(AgentAdapter):
    """
    Adaptateur pour les agents tactiques.
    """
    
    def __init__(self, agent_id, middleware):
        """
        Initialise un nouvel adaptateur tactique.
        
        Args:
            agent_id (str): Identifiant unique de l'agent
            middleware (MessageMiddleware): Le middleware de messagerie
        """
```

#### Méthodes spécifiques

```python
def receive_directive(self, timeout=None, filter_criteria=None):
    """
    Reçoit une directive stratégique.
    
    Args:
        timeout (float, optional): Délai d'attente maximum en secondes
        filter_criteria (dict, optional): Critères de filtrage supplémentaires
        
    Returns:
        Message: La directive reçue ou None si aucune directive n'est disponible
        
    Raises:
        TimeoutError: Si le timeout est atteint
    """

def send_report(self, report_type, content, recipient_id, priority=MessagePriority.NORMAL, metadata=None):
    """
    Envoie un rapport à un agent stratégique.
    
    Args:
        report_type (str): Type de rapport
        content (dict): Contenu du rapport
        recipient_id (str): Identifiant du destinataire stratégique
        priority (MessagePriority, optional): Priorité du rapport
        metadata (dict, optional): Métadonnées supplémentaires
        
    Returns:
        str: L'identifiant du rapport envoyé
        
    Raises:
        ValueError: Si les paramètres sont invalides
    """

def assign_task(self, task_type, parameters, recipient_id, priority=MessagePriority.NORMAL, deadline=None, metadata=None):
    """
    Assigne une tâche à un agent opérationnel.
    
    Args:
        task_type (str): Type de tâche
        parameters (dict): Paramètres de la tâche
        recipient_id (str): Identifiant du destinataire opérationnel
        priority (MessagePriority, optional): Priorité de la tâche
        deadline (float, optional): Date limite d'exécution en secondes depuis l'époque
        metadata (dict, optional): Métadonnées supplémentaires
        
    Returns:
        str: L'identifiant de la tâche assignée
        
    Raises:
        ValueError: Si les paramètres sont invalides
    """

def receive_task_result(self, timeout=None, filter_criteria=None):
    """
    Reçoit un résultat de tâche d'un agent opérationnel.
    
    Args:
        timeout (float, optional): Délai d'attente maximum en secondes
        filter_criteria (dict, optional): Critères de filtrage supplémentaires
        
    Returns:
        Message: Le résultat reçu ou None si aucun résultat n'est disponible
        
    Raises:
        TimeoutError: Si le timeout est atteint
    """

def request_operational_status(self, recipient_id, timeout=5.0, priority=MessagePriority.NORMAL):
    """
    Demande le statut d'un agent opérationnel.
    
    Args:
        recipient_id (str): Identifiant de l'agent opérationnel
        timeout (float, optional): Délai d'attente maximum en secondes
        priority (MessagePriority, optional): Priorité de la demande
        
    Returns:
        dict: Le statut de l'agent opérationnel ou None si timeout
        
    Raises:
        TimeoutError: Si le timeout est atteint
    """

def request_strategic_guidance(self, request_type, parameters, recipient_id, timeout=5.0, priority=MessagePriority.NORMAL):
    """
    Demande des conseils à un agent stratégique.
    
    Args:
        request_type (str): Type de demande
        parameters (dict): Paramètres de la demande
        recipient_id (str): Identifiant du destinataire stratégique
        timeout (float, optional): Délai d'attente maximum en secondes
        priority (MessagePriority, optional): Priorité de la demande
        
    Returns:
        dict: Les conseils reçus ou None si timeout
        
    Raises:
        TimeoutError: Si le timeout est atteint
    """

def request_tactical_assistance(self, request_type, parameters, recipient_id, timeout=5.0, priority=MessagePriority.NORMAL):
    """
    Demande de l'aide à un autre agent tactique.
    
    Args:
        request_type (str): Type de demande
        parameters (dict): Paramètres de la demande
        recipient_id (str): Identifiant du destinataire tactique
        timeout (float, optional): Délai d'attente maximum en secondes
        priority (MessagePriority, optional): Priorité de la demande
        
    Returns:
        dict: L'aide reçue ou None si timeout
        
    Raises:
        TimeoutError: Si le timeout est atteint
    """

def receive_assistance_request(self, timeout=None, filter_criteria=None):
    """
    Reçoit une demande d'aide d'un autre agent tactique.
    
    Args:
        timeout (float, optional): Délai d'attente maximum en secondes
        filter_criteria (dict, optional): Critères de filtrage supplémentaires
        
    Returns:
        Message: La demande reçue ou None si aucune demande n'est disponible
        
    Raises:
        TimeoutError: Si le timeout est atteint
    """

def send_assistance_response(self, request_id, response, recipient_id, priority=MessagePriority.NORMAL):
    """
    Envoie une réponse à une demande d'aide.
    
    Args:
        request_id (str): Identifiant de la demande
        response (dict): Réponse à la demande
        recipient_id (str): Identifiant du destinataire tactique
        priority (MessagePriority, optional): Priorité de la réponse
        
    Returns:
        str: L'identifiant de la réponse envoyée
        
    Raises:
        ValueError: Si les paramètres sont invalides
    """
```

### OperationalAdapter

Adaptateur pour les agents opérationnels.

```python
class OperationalAdapter(AgentAdapter):
    """
    Adaptateur pour les agents opérationnels.
    """
    
    def __init__(self, agent_id, middleware):
        """
        Initialise un nouvel adaptateur opérationnel.
        
        Args:
            agent_id (str): Identifiant unique de l'agent
            middleware (MessageMiddleware): Le middleware de messagerie
        """
```

#### Méthodes spécifiques

```python
def receive_task(self, timeout=None, filter_criteria=None):
    """
    Reçoit une tâche d'un agent tactique.
    
    Args:
        timeout (float, optional): Délai d'attente maximum en secondes
        filter_criteria (dict, optional): Critères de filtrage supplémentaires
        
    Returns:
        Message: La tâche reçue ou None si aucune tâche n'est disponible
        
    Raises:
        TimeoutError: Si le timeout est atteint
    """

def send_task_result(self, task_id, result, recipient_id, priority=MessagePriority.NORMAL, metadata=None):
    """
    Envoie un résultat de tâche à un agent tactique.
    
    Args:
        task_id (str): Identifiant de la tâche
        result (dict): Résultat de la tâche
        recipient_id (str): Identifiant du destinataire tactique
        priority (MessagePriority, optional): Priorité du résultat
        metadata (dict, optional): Métadonnées supplémentaires
        
    Returns:
        str: L'identifiant du résultat envoyé
        
    Raises:
        ValueError: Si les paramètres sont invalides
    """

def send_status_update(self, status, progress, details, recipient_id, priority=MessagePriority.NORMAL):
    """
    Envoie une mise à jour de statut à un agent tactique.
    
    Args:
        status (str): Statut de l'agent
        progress (int): Progression en pourcentage
        details (dict): Détails du statut
        recipient_id (str): Identifiant du destinataire tactique
        priority (MessagePriority, optional): Priorité de la mise à jour
        
    Returns:
        str: L'identifiant de la mise à jour envoyée
        
    Raises:
        ValueError: Si les paramètres sont invalides
    """

def request_task_clarification(self, task_id, question, recipient_id, timeout=5.0, priority=MessagePriority.NORMAL):
    """
    Demande des clarifications sur une tâche à un agent tactique.
    
    Args:
        task_id (str): Identifiant de la tâche
        question (str): Question à poser
        recipient_id (str): Identifiant du destinataire tactique
        timeout (float, optional): Délai d'attente maximum en secondes
        priority (MessagePriority, optional): Priorité de la demande
        
    Returns:
        dict: Les clarifications reçues ou None si timeout
        
    Raises:
        TimeoutError: Si le timeout est atteint
    """

def request_operational_assistance(self, request_type, parameters, recipient_id, timeout=5.0, priority=MessagePriority.NORMAL):
    """
    Demande de l'aide à un autre agent opérationnel.
    
    Args:
        request_type (str): Type de demande
        parameters (dict): Paramètres de la demande
        recipient_id (str): Identifiant du destinataire opérationnel
        timeout (float, optional): Délai d'attente maximum en secondes
        priority (MessagePriority, optional): Priorité de la demande
        
    Returns:
        dict: L'aide reçue ou None si timeout
        
    Raises:
        TimeoutError: Si le timeout est atteint
    """
```

## Messages

### Message

Classe de base pour tous les messages.

```python
class Message:
    """
    Classe de base pour tous les messages.
    """
    
    def __init__(self, type, sender, sender_level, recipient=None, content=None, priority=MessagePriority.NORMAL, metadata=None):
        """
        Initialise un nouveau message.
        
        Args:
            type (MessageType): Type de message
            sender (str): Identifiant de l'émetteur
            sender_level (AgentLevel): Niveau de l'émetteur
            recipient (str, optional): Identifiant du destinataire
            content (dict, optional): Contenu du message
            priority (MessagePriority, optional): Priorité du message
            metadata (dict, optional): Métadonnées du message
        """
```

#### Propriétés et méthodes

```python
@property
def id(self):
    """
    Récupère l'identifiant unique du message.
    
    Returns:
        str: L'identifiant du message
    """

@property
def timestamp(self):
    """
    Récupère l'horodatage de création du message.
    
    Returns:
        float: L'horodatage en secondes depuis l'époque
    """

def to_dict(self):
    """
    Convertit le message en dictionnaire.
    
    Returns:
        dict: Le message sous forme de dictionnaire
    """

@classmethod
def from_dict(cls, data):
    """
    Crée un message à partir d'un dictionnaire.
    
    Args:
        data (dict): Dictionnaire contenant les données du message
        
    Returns:
        Message: Le message créé
        
    Raises:
        ValueError: Si les données sont invalides
    """

def copy(self):
    """
    Crée une copie du message.
    
    Returns:
        Message: Une copie du message
    """

def is_expired(self, ttl=None):
    """
    Vérifie si le message a expiré.
    
    Args:
        ttl (float, optional): Durée de vie en secondes
        
    Returns:
        bool: True si le message a expiré, False sinon
    """
```

### MessageType

Énumération des types de messages.

```python
class MessageType(Enum):
    """
    Énumération des types de messages.
    """
    
    COMMAND = "command"  # Directive, tâche ou instruction
    INFORMATION = "information"  # Partage d'informations, résultats ou états
    REQUEST = "request"  # Demande d'informations ou d'actions
    RESPONSE = "response"  # Réponse à une demande
    EVENT = "event"  # Notification d'événement
    CONTROL = "control"  # Gestion du système de communication
    ALERT = "alert"  # Alerte ou avertissement
    NEGOTIATION_INIT = "negotiation_init"  # Initialisation d'une négociation
    NEGOTIATION_PROPOSAL = "negotiation_proposal"  # Proposition dans le cadre d'une négociation
    NEGOTIATION_RESPONSE = "negotiation_response"  # Réponse à une proposition
    NEGOTIATION_RESOLUTION = "negotiation_resolution"  # Résolution d'une négociation
```

### MessagePriority

Énumération des priorités de messages.

```python
class MessagePriority(Enum):
    """
    Énumération des priorités de messages.
    """
    
    CRITICAL = 0  # Priorité critique, traitement immédiat requis
    HIGH = 1  # Priorité élevée, traitement rapide requis
    NORMAL = 2  # Priorité normale, traitement standard
    LOW = 3  # Priorité basse, traitement quand les ressources sont disponibles
    BACKGROUND = 4  # Priorité très basse, traitement en arrière-plan
```

### AgentLevel

Énumération des niveaux d'agents.

```python
class AgentLevel(Enum):
    """
    Énumération des niveaux d'agents.
    """
    
    STRATEGIC = "strategic"  # Niveau stratégique
    TACTICAL = "tactical"  # Niveau tactique
    OPERATIONAL = "operational"  # Niveau opérationnel
    SYSTEM = "system"  # Niveau système
```
    Raises:
        NotImplementedError: Les sous-classes doivent implémenter cette méthode
    """
```
## Protocoles de communication

### ProtocolInterface

Interface que tous les protocoles de communication doivent implémenter.

```python
class ProtocolInterface:
    """
    Interface que tous les protocoles de communication doivent implémenter.
    """
    
    def __init__(self, middleware):
        """
        Initialise un nouveau protocole.
        
        Args:
            middleware (MessageMiddleware): Le middleware de messagerie
        """
```

#### Méthodes de l'interface

```python
def initialize(self):
    """
    Initialise le protocole.
    
    Returns:
        bool: True si l'initialisation a réussi, False sinon
        
    Raises:
        NotImplementedError: Les sous-classes doivent implémenter cette méthode
    """

def handle_message(self, message):
    """
    Traite un message selon ce protocole.
    
    Args:
        message (Message): Le message à traiter
        
    Returns:
        bool: True si le message a été traité, False sinon
        
    Raises:
        NotImplementedError: Les sous-classes doivent implémenter cette méthode
    """

def get_protocol_name(self):
    """
    Récupère le nom du protocole.
    
    Returns:
        str: Le nom du protocole
        
    Raises:
        NotImplementedError: Les sous-classes doivent implémenter cette méthode
    """

def get_supported_message_types(self):
    """
    Récupère les types de messages supportés par ce protocole.
    
    Returns:
        list: Liste des types de messages supportés
        
    Raises:
        NotImplementedError: Les sous-classes doivent implémenter cette méthode
    """
```

### RequestResponseProtocol

Protocole de requête-réponse pour les interactions synchrones.

```python
class RequestResponseProtocol(ProtocolInterface):
    """
    Protocole de requête-réponse pour les interactions synchrones.
    """
    
    def __init__(self, middleware):
        """
        Initialise un nouveau protocole de requête-réponse.
        
        Args:
            middleware (MessageMiddleware): Le middleware de messagerie
        """
```

#### Méthodes spécifiques

```python
def send_request(self, sender, sender_level, recipient, request_type, parameters, timeout=5.0, priority=MessagePriority.NORMAL):
    """
    Envoie une requête et attend une réponse.
    
    Args:
        sender (str): Identifiant de l'émetteur
        sender_level (AgentLevel): Niveau de l'émetteur
        recipient (str): Identifiant du destinataire
        request_type (str): Type de requête
        parameters (dict): Paramètres de la requête
        timeout (float, optional): Délai d'attente maximum en secondes
        priority (MessagePriority, optional): Priorité de la requête
        
    Returns:
        dict: La réponse reçue ou None si timeout
        
    Raises:
        TimeoutError: Si le timeout est atteint
        ValueError: Si les paramètres sont invalides
    """

def send_response(self, request_id, sender, sender_level, recipient, response, priority=MessagePriority.NORMAL):
    """
    Envoie une réponse à une requête.
    
    Args:
        request_id (str): Identifiant de la requête
        sender (str): Identifiant de l'émetteur
        sender_level (AgentLevel): Niveau de l'émetteur
        recipient (str): Identifiant du destinataire
        response (dict): Réponse à la requête
        priority (MessagePriority, optional): Priorité de la réponse
        
    Returns:
        str: L'identifiant de la réponse envoyée
        
    Raises:
        ValueError: Si les paramètres sont invalides
    """

def get_pending_requests(self, recipient_id):
    """
    Récupère toutes les requêtes en attente pour un destinataire.
    
    Args:
        recipient_id (str): Identifiant du destinataire
        
    Returns:
        list: Liste des requêtes en attente
    """

def get_request_statistics(self):
    """
    Récupère des statistiques sur les requêtes.
    
    Returns:
        dict: Dictionnaire de statistiques
    """
```

### PublishSubscribeProtocol

Protocole de publication-abonnement pour les interactions asynchrones.

```python
class PublishSubscribeProtocol(ProtocolInterface):
    """
    Protocole de publication-abonnement pour les interactions asynchrones.
    """
    
    def __init__(self, middleware):
        """
        Initialise un nouveau protocole de publication-abonnement.
        
        Args:
            middleware (MessageMiddleware): Le middleware de messagerie
        """
```

#### Méthodes spécifiques

```python
def create_topic(self, topic_id, owner_id, description=None, access_control=None):
    """
    Crée un nouveau sujet.
    
    Args:
        topic_id (str): Identifiant du sujet
        owner_id (str): Identifiant du propriétaire
        description (str, optional): Description du sujet
        access_control (dict, optional): Contrôle d'accès
        
    Returns:
        bool: True si la création a réussi, False sinon
        
    Raises:
        ValueError: Si les paramètres sont invalides
    """

def delete_topic(self, topic_id, owner_id):
    """
    Supprime un sujet.
    
    Args:
        topic_id (str): Identifiant du sujet
        owner_id (str): Identifiant du propriétaire
        
    Returns:
        bool: True si la suppression a réussi, False sinon
        
    Raises:
        ValueError: Si les paramètres sont invalides
    """

def publish(self, topic_id, sender, sender_level, content, priority=MessagePriority.NORMAL):
    """
    Publie un message sur un sujet.
    
    Args:
        topic_id (str): Identifiant du sujet
        sender (str): Identifiant de l'émetteur
        sender_level (AgentLevel): Niveau de l'émetteur
        content (dict): Contenu du message
        priority (MessagePriority, optional): Priorité du message
        
    Returns:
        str: L'identifiant du message publié
        
    Raises:
        ValueError: Si les paramètres sont invalides
    """

def subscribe(self, subscriber_id, topic_id, callback=None, filter_criteria=None):
    """
    Abonne un agent à un sujet.
    
    Args:
        subscriber_id (str): Identifiant de l'abonné
        topic_id (str): Identifiant du sujet
        callback (callable, optional): Fonction de rappel à appeler lors de la réception d'un message
        filter_criteria (dict, optional): Critères de filtrage
        
    Returns:
        str: Un identifiant d'abonnement
        
    Raises:
        ValueError: Si les paramètres sont invalides
    """

def unsubscribe(self, subscription_id):
    """
    Désabonne un agent d'un sujet.
    
    Args:
        subscription_id (str): Identifiant de l'abonnement
        
    Returns:
        bool: True si le désabonnement a réussi, False sinon
        
    Raises:
        ValueError: Si l'identifiant d'abonnement est invalide
    """

def get_topics(self):
    """
    Récupère la liste des sujets disponibles.
    
    Returns:
        list: Liste des sujets disponibles
    """

def get_topic_subscribers(self, topic_id):
    """
    Récupère la liste des abonnés à un sujet.
    
    Args:
        topic_id (str): Identifiant du sujet
        
    Returns:
        list: Liste des identifiants des abonnés
        
    Raises:
        ValueError: Si l'identifiant du sujet est invalide
    """

def get_subscription_statistics(self):
    """
    Récupère des statistiques sur les abonnements.
    
    Returns:
        dict: Dictionnaire de statistiques
    """
```

### NegotiationProtocol

Protocole de négociation pour la résolution de conflits et la prise de décisions collaboratives.

```python
class NegotiationProtocol(ProtocolInterface):
    """
    Protocole de négociation pour la résolution de conflits et la prise de décisions collaboratives.
    """
    
    def __init__(self, middleware):
        """
        Initialise un nouveau protocole de négociation.
        
        Args:
            middleware (MessageMiddleware): Le middleware de messagerie
        """
```

#### Méthodes spécifiques

```python
def create_negotiation(self, initiator_id, initiator_level, participants, topic, initial_proposal=None):
    """
    Crée une nouvelle négociation.
    
    Args:
        initiator_id (str): Identifiant de l'initiateur
        initiator_level (AgentLevel): Niveau de l'initiateur
        participants (list): Liste des identifiants des participants
        topic (str): Sujet de la négociation
        initial_proposal (dict, optional): Proposition initiale
        
    Returns:
        str: Identifiant de la négociation
        
    Raises:
        ValueError: Si les paramètres sont invalides
    """

def submit_proposal(self, negotiation_id, participant_id, participant_level, proposal, round_number=None):
    """
    Soumet une proposition dans le cadre d'une négociation.
    
    Args:
        negotiation_id (str): Identifiant de la négociation
        participant_id (str): Identifiant du participant
        participant_level (AgentLevel): Niveau du participant
        proposal (dict): Proposition
        round_number (int, optional): Numéro du tour
        
    Returns:
        str: Identifiant de la proposition
        
    Raises:
        ValueError: Si les paramètres sont invalides
    """

def respond_to_proposal(self, negotiation_id, participant_id, participant_level, proposal_id, response, counter_proposal=None):
    """
    Répond à une proposition dans le cadre d'une négociation.
    
    Args:
        negotiation_id (str): Identifiant de la négociation
        participant_id (str): Identifiant du participant
        participant_level (AgentLevel): Niveau du participant
        proposal_id (str): Identifiant de la proposition
        response (str): Réponse ("accept", "reject", "counter")
        counter_proposal (dict, optional): Contre-proposition
        
    Returns:
        str: Identifiant de la réponse
        
    Raises:
        ValueError: Si les paramètres sont invalides
    """

def get_negotiation_status(self, negotiation_id):
    """
    Récupère le statut d'une négociation.
    
    Args:
        negotiation_id (str): Identifiant de la négociation
        
    Returns:
        dict: Statut de la négociation
        
    Raises:
        ValueError: Si l'identifiant de la négociation est invalide
    """

def resolve_negotiation(self, negotiation_id, resolution, resolver_id, resolver_level):
    """
    Résout une négociation.
    
    Args:
        negotiation_id (str): Identifiant de la négociation
        resolution (dict): Résolution
        resolver_id (str): Identifiant du résolveur
        resolver_level (AgentLevel): Niveau du résolveur
        
    Returns:
        bool: True si la résolution a réussi, False sinon
        
    Raises:
        ValueError: Si les paramètres sont invalides
    """

def get_negotiation_history(self, negotiation_id):
    """
    Récupère l'historique d'une négociation.
    
    Args:
        negotiation_id (str): Identifiant de la négociation
        
    Returns:
        list: Historique de la négociation
        
    Raises:
        ValueError: Si l'identifiant de la négociation est invalide
    """

def get_negotiation_statistics(self):
    """
    Récupère des statistiques sur les négociations.
    
    Returns:
        dict: Dictionnaire de statistiques
    """
```

## Utilitaires

### MessageFilter

Utilitaire pour filtrer les messages.

```python
class MessageFilter:
    """
    Utilitaire pour filtrer les messages.
    """
    
    @staticmethod
    def filter_messages(messages, filter_criteria):
        """
        Filtre une liste de messages selon des critères.
        
        Args:
            messages (list): Liste de messages à filtrer
            filter_criteria (dict): Critères de filtrage
            
        Returns:
            list: Liste des messages filtrés
        """
```

#### Méthodes statiques

```python
@staticmethod
def matches_criteria(message, filter_criteria):
    """
    Vérifie si un message correspond à des critères de filtrage.
    
    Args:
        message (Message): Message à vérifier
        filter_criteria (dict): Critères de filtrage
        
    Returns:
        bool: True si le message correspond aux critères, False sinon
    """

@staticmethod
def create_filter_function(filter_criteria):
    """
    Crée une fonction de filtrage à partir de critères.
    
    Args:
        filter_criteria (dict): Critères de filtrage
        
    Returns:
        callable: Fonction de filtrage
    """

@staticmethod
def filter_by_type(messages, message_type):
    """
    Filtre une liste de messages par type.
    
    Args:
        messages (list): Liste de messages à filtrer
        message_type (MessageType): Type de message
        
    Returns:
        list: Liste des messages filtrés
    """

@staticmethod
def filter_by_sender(messages, sender_id):
    """
    Filtre une liste de messages par émetteur.
    
    Args:
        messages (list): Liste de messages à filtrer
        sender_id (str): Identifiant de l'émetteur
        
    Returns:
        list: Liste des messages filtrés
    """

@staticmethod
def filter_by_recipient(messages, recipient_id):
    """
    Filtre une liste de messages par destinataire.
    
    Args:
        messages (list): Liste de messages à filtrer
        recipient_id (str): Identifiant du destinataire
        
    Returns:
        list: Liste des messages filtrés
    """

@staticmethod
def filter_by_priority(messages, priority):
    """
    Filtre une liste de messages par priorité.
    
    Args:
        messages (list): Liste de messages à filtrer
        priority (MessagePriority): Priorité des messages
        
    Returns:
        list: Liste des messages filtrés
    """

@staticmethod
def filter_by_content(messages, content_criteria):
    """
    Filtre une liste de messages par contenu.
    
    Args:
        messages (list): Liste de messages à filtrer
        content_criteria (dict): Critères de filtrage du contenu
        
    Returns:
        list: Liste des messages filtrés
    """
```

### MessageRouter

Utilitaire pour router les messages.

```python
class MessageRouter:
    """
    Utilitaire pour router les messages.
    """
    
    def __init__(self, middleware):
        """
        Initialise un nouveau routeur de messages.
        
        Args:
            middleware (MessageMiddleware): Le middleware de messagerie
        """
```

#### Méthodes

```python
def add_type_rule(self, message_type, channel_name):
    """
    Ajoute une règle de routage basée sur le type de message.
    
    Args:
        message_type (MessageType): Type de message
        channel_name (str): Nom du canal
        
    Returns:
        bool: True si l'ajout a réussi, False sinon
        
    Raises:
        ValueError: Si le canal n'est pas enregistré
    """

def add_content_rule(self, field, value, channel_name):
    """
    Ajoute une règle de routage basée sur le contenu du message.
    
    Args:
        field (str): Chemin du champ dans le contenu (ex: "content.command_type")
        value (any): Valeur du champ
        channel_name (str): Nom du canal
        
    Returns:
        bool: True si l'ajout a réussi, False sinon
        
    Raises:
        ValueError: Si le canal n'est pas enregistré
    """

def add_sender_rule(self, sender_level, channel_name):
    """
    Ajoute une règle de routage basée sur le niveau de l'émetteur.
    
    Args:
        sender_level (AgentLevel): Niveau de l'émetteur
        channel_name (str): Nom du canal
        
    Returns:
        bool: True si l'ajout a réussi, False sinon
        
    Raises:
        ValueError: Si le canal n'est pas enregistré
    """

def add_priority_rule(self, priority, channel_name):
    """
    Ajoute une règle de routage basée sur la priorité du message.
    
    Args:
        priority (MessagePriority): Priorité du message
        channel_name (str): Nom du canal
        
    Returns:
        bool: True si l'ajout a réussi, False sinon
        
    Raises:
        ValueError: Si le canal n'est pas enregistré
    """

def route_message(self, message):
    """
    Route un message vers le canal approprié.
    
    Args:
        message (Message): Message à router
        
    Returns:
        str: Nom du canal vers lequel le message a été routé
        
    Raises:
        ValueError: Si aucun canal approprié n'a été trouvé
    """

def get_rules(self):
    """
    Récupère toutes les règles de routage.
    
    Returns:
        dict: Dictionnaire des règles de routage
    """
```

### MessageSerializer

Utilitaire pour sérialiser et désérialiser les messages.

```python
class MessageSerializer:
    """
    Utilitaire pour sérialiser et désérialiser les messages.
    """
```

#### Méthodes statiques

```python
@staticmethod
def serialize(message):
    """
    Sérialise un message en JSON.
    
    Args:
        message (Message): Message à sérialiser
        
    Returns:
        str: Message sérialisé en JSON
        
    Raises:
        ValueError: Si le message ne peut pas être sérialisé
    """

@staticmethod
def deserialize(json_str):
    """
    Désérialise un message depuis JSON.
    
    Args:
        json_str (str): Message sérialisé en JSON
        
    Returns:
        Message: Message désérialisé
        
    Raises:
        ValueError: Si le message ne peut pas être désérialisé
    """

@staticmethod
def serialize_to_bytes(message, compression=False):
    """
    Sérialise un message en bytes.
    
    Args:
        message (Message): Message à sérialiser
        compression (bool, optional): Activer la compression
        
    Returns:
        bytes: Message sérialisé en bytes
        
    Raises:
        ValueError: Si le message ne peut pas être sérialisé
    """

@staticmethod
def deserialize_from_bytes(bytes_data):
    """
    Désérialise un message depuis bytes.
    
    Args:
        bytes_data (bytes): Message sérialisé en bytes
        
    Returns:
        Message: Message désérialisé
        
    Raises:
        ValueError: Si le message ne peut pas être désérialisé
    """

@staticmethod
def serialize_batch(messages):
    """
    Sérialise un lot de messages en JSON.
    
    Args:
        messages (list): Liste de messages à sérialiser
        
    Returns:
        str: Lot de messages sérialisé en JSON
        
    Raises:
        ValueError: Si les messages ne peuvent pas être sérialisés
    """

@staticmethod
def deserialize_batch(json_str):
    """
    Désérialise un lot de messages depuis JSON.
    
    Args:
        json_str (str): Lot de messages sérialisé en JSON
        
    Returns:
        list: Liste de messages désérialisés
        
    Raises:
        ValueError: Si les messages ne peuvent pas être désérialisés
    """
```

### CommunicationMonitor

Utilitaire pour surveiller les communications.

```python
class CommunicationMonitor:
    """
    Utilitaire pour surveiller les communications.
    """
    
    def __init__(self, middleware):
        """
        Initialise un nouveau moniteur de communication.
        
        Args:
            middleware (MessageMiddleware): Le middleware de messagerie
        """
```

#### Méthodes

```python
def start_monitoring(self):
    """
    Démarre la surveillance des communications.
    
    Returns:
        bool: True si le démarrage a réussi, False sinon
    """

def stop_monitoring(self):
    """
    Arrête la surveillance des communications.
    
    Returns:
        bool: True si l'arrêt a réussi, False sinon
    """

def get_message_statistics(self, time_range=None):
    """
    Récupère des statistiques sur les messages.
    
    Args:
        time_range (tuple, optional): Plage de temps (début, fin) en secondes depuis l'époque
        
    Returns:
        dict: Dictionnaire de statistiques
    """

def get_channel_statistics(self, channel_name=None):
    """
    Récupère des statistiques sur les canaux.
    
    Args:
        channel_name (str, optional): Nom du canal
        
    Returns:
        dict: Dictionnaire de statistiques
    """

def get_agent_statistics(self, agent_id=None):
    """
    Récupère des statistiques sur les agents.
    
    Args:
        agent_id (str, optional): Identifiant de l'agent
        
    Returns:
        dict: Dictionnaire de statistiques
    """

def get_protocol_statistics(self, protocol_name=None):
    """
    Récupère des statistiques sur les protocoles.
    
    Args:
        protocol_name (str, optional): Nom du protocole
        
    Returns:
        dict: Dictionnaire de statistiques
    """

def get_communication_graph(self, time_range=None):
    """
    Récupère un graphe des communications.
    
    Args:
        time_range (tuple, optional): Plage de temps (début, fin) en secondes depuis l'époque
        
    Returns:
        dict: Graphe des communications
    """

def get_bottlenecks(self):
    """
    Identifie les goulots d'étranglement dans les communications.
    
    Returns:
        list: Liste des goulots d'étranglement
    """

def get_alerts(self):
    """
    Récupère les alertes de communication.
    
    Returns:
        list: Liste des alertes
    """

def add_alert_rule(self, rule_type, parameters):
    """
    Ajoute une règle d'alerte.
    
    Args:
        rule_type (str): Type de règle
        parameters (dict): Paramètres de la règle
        
    Returns:
        str: Identifiant de la règle
        
    Raises:
        ValueError: Si les paramètres sont invalides
    """

def remove_alert_rule(self, rule_id):
    """
    Supprime une règle d'alerte.
    
    Args:
        rule_id (str): Identifiant de la règle
        
    Returns:
        bool: True si la suppression a réussi, False sinon
        
    Raises:
        ValueError: Si l'identifiant de la règle est invalide
    """

def get_alert_rules(self):
    """
    Récupère les règles d'alerte.
    
    Returns:
        list: Liste des règles d'alerte
    """
```