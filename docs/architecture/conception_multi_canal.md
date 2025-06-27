# Conception du Système de Communication Multi-Canal pour Agents d'Analyse Rhétorique

## Table des matières

1.  [Introduction](#1-introduction)
    *   [Contexte et objectifs](#11-contexte-et-objectifs)
    *   [Vision globale du système](#12-vision-globale-du-système)
2.  [Architecture Globale](#2-architecture-globale)
    *   [Vue d'ensemble](#21-vue-densemble)
    *   [Principes architecturaux](#22-principes-architecturaux)
    *   [Composants principaux](#23-composants-principaux)
3.  [Middleware de Messagerie (`MessageMiddleware`)](#3-middleware-de-messagerie-messagemiddleware)
    *   [Rôle et Fonctionnalités](#31-rôle-et-fonctionnalités)
    *   [Gestion des canaux et routage](#32-gestion-des-canaux-et-routage)
    *   [Protocoles intégrés](#33-protocoles-intégrés)
4.  [Canaux de Communication](#4-canaux-de-communication)
    *   [Définition et Types](#41-définition-et-types)
    *   [Canal Hiérarchique (`HierarchicalChannel`)](#42-canal-hiérarchique-hierarchicalchannel)
    *   [Canal de Collaboration (`CollaborationChannel`)](#43-canal-de-collaboration-collaborationchannel)
    *   [Canal de Données (`DataChannel`)](#44-canal-de-données-datachannel)
    *   [Canal Local (`LocalChannel`)](#45-canal-local-localchannel)
    *   [Autres types de canaux (conceptuels)](#46-autres-types-de-canaux-conceptuels)
5.  [Structures de Données pour les Messages (`Message`)](#5-structures-de-données-pour-les-messages-message)
    *   [Format de message commun](#51-format-de-message-commun)
    *   [Types de messages spécifiques](#52-types-de-messages-spécifiques)
6.  [Adaptateurs d'Agents (Concept)](#6-adaptateurs-dagents-concept)
7.  [Gestion des Erreurs et Résilience (Principes)](#7-gestion-des-erreurs-et-résilience-principes)
8.  [Cohérence avec les autres documents](#8-cohérence-avec-les-autres-documents)
9.  [Conclusion et Perspectives](#9-conclusion-et-perspectives)

## 1. Introduction

### 1.1 Contexte et objectifs

Le système d'analyse rhétorique s'appuie sur une architecture d'agents distribués. Initialement, la communication entre ces agents était principalement gérée via un état partagé et des interfaces hiérarchiques. Pour améliorer la flexibilité, le découplage et la richesse des interactions, un système de communication multi-canal a été introduit.

L'objectif de ce document est de décrire la conception et l'implémentation actuelle de ce système de communication multi-canal, en se concentrant sur le rôle central du `MessageMiddleware`, les différents types de canaux, le format des messages, et comment ces composants interagissent. Ce document vise à refléter l'état actuel du code et à identifier les aspects qui sont pleinement implémentés par rapport aux concepts de conception initiaux.

### 1.2 Vision globale du système

Le système de communication multi-canal repose sur un `MessageMiddleware` ([`middleware.py`](../../argumentation_analysis/core/communication/middleware.py:19)) central qui gère différents canaux de communication spécialisés. Chaque canal est optimisé pour un type spécifique d'interaction. Les agents communiquent via ce middleware, qui assure le routage et la distribution des messages. Cette architecture vise une séparation claire entre la logique métier des agents et les mécanismes de communication.

Pour une vue d'ensemble des flux de communication impliquant les agents et le middleware, veuillez consulter le document [Système de Communication entre Agents](communication_agents.md).

## 2. Architecture Globale

### 2.1 Vue d'ensemble

L'architecture du système de communication multi-canal est organisée autour du `MessageMiddleware` qui coordonne les échanges entre les agents à travers différents canaux spécialisés. Le diagramme suivant illustre les principaux composants et leurs interactions :

Référence au diagramme : [`docs/architecture/images/architecture_multi_canal.md`](images/architecture_multi_canal.md)

Ce diagramme montre le `MessageMiddleware` interagissant avec des canaux comme le `HierarchicalChannel`, `CollaborationChannel`, `DataChannel`, etc. Les adaptateurs d'agents, bien que conceptuellement importants, ont une implémentation qui reste à confirmer (voir [section 6](#6-adaptateurs-dagents-concept)).

### 2.2 Principes architecturaux

L'architecture s'efforce de suivre les principes suivants :

1.  **Séparation des préoccupations** : Distinguer la logique métier des agents des mécanismes de communication.
2.  **Communication découplée** : Permettre aux agents de communiquer via des canaux sans dépendances directes.
3.  **Extensibilité** : Faciliter l'ajout de nouveaux canaux ou protocoles.
4.  **Adaptabilité** : S'adapter aux différents besoins de communication.
5.  **Observabilité** : Fournir des moyens de suivre et journaliser les communications.
6.  **Standardisation** : Utiliser des formats de messages cohérents.

### 2.3 Composants principaux

Les composants clés du système de communication sont :

1.  **`MessageMiddleware`** : Le composant central. Voir [section 3](#3-middleware-de-messagerie-messagemiddleware).
2.  **Canaux de Communication** : Voies spécialisées pour les messages. Voir [section 4](#4-canaux-de-communication).
3.  **Messages (`Message`)** : Les unités d'information échangées. Voir [section 5](#5-structures-de-données-pour-les-messages-message).
4.  **Adaptateurs d'Agents** : (Conceptuel) Interfaces entre les agents et le middleware. Voir [section 6](#6-adaptateurs-dagents-concept).
5.  **Protocoles de Communication** : Modèles d'interaction spécifiques comme Requête-Réponse et Publication-Abonnement, intégrés au `MessageMiddleware`.

## 3. Middleware de Messagerie (`MessageMiddleware`)

Le `MessageMiddleware` ([`middleware.py`](../../argumentation_analysis/core/communication/middleware.py:19)) est le cœur du système de communication.

### 3.1 Rôle et Fonctionnalités

Le `MessageMiddleware` est responsable de :

*   **Gestion des Canaux** : Enregistrement ([`register_channel`](../../argumentation_analysis/core/communication/middleware.py:59)) et récupération ([`get_channel`](../../argumentation_analysis/core/communication/middleware.py:75)) des canaux de communication.
*   **Routage des Messages** : Détermination du canal approprié pour un message via la méthode [`determine_channel`](../../argumentation_analysis/core/communication/middleware.py:112), basée sur le type de message et certains aspects de son contenu.
*   **Envoi et Réception de Messages** : Fourniture de méthodes unifiées [`send_message`](../../argumentation_analysis/core/communication/middleware.py:157), [`receive_message`](../../argumentation_analysis/core/communication/middleware.py:212), et leurs équivalents asynchrones.
*   **Journalisation et Statistiques** : Maintien de logs et de statistiques sur les messages envoyés, reçus et les erreurs.
*   **Initialisation de Protocoles** : Intégration et initialisation de protocoles de communication spécifiques.

Les fonctionnalités de "Moniteur de communication" et de "Gestionnaire de canaux" décrites dans des versions antérieures de ce document sont en pratique intégrées au sein de la classe `MessageMiddleware`. Des aspects comme la transformation avancée de messages, le contrôle de flux explicite (throttling) au niveau du middleware, et la sécurité (authentification/autorisation) ne sont pas explicitement implémentés dans la version actuelle du code du middleware.

### 3.2 Gestion des canaux et routage

Le `MessageMiddleware` enregistre les instances des différents canaux. Lorsqu'un message est envoyé via [`send_message`](../../argumentation_analysis/core/communication/middleware.py:157), la méthode [`determine_channel`](../../argumentation_analysis/core/communication/middleware.py:112) est utilisée pour sélectionner le `ChannelType` approprié. Cette sélection est basée sur le `MessageType` du message et, dans certains cas (par exemple pour `MessageType.INFORMATION` ou `MessageType.REQUEST`), sur des champs spécifiques du contenu du message.

### 3.3 Protocoles intégrés

Le `MessageMiddleware` initialise et utilise des protocoles de communication pour des patterns d'interaction spécifiques :

*   **`RequestResponseProtocol`** ([`request_response.py`](../../argumentation_analysis/core/communication/request_response.py:25)) : Gère les interactions synchrones et asynchrones de type requête-réponse, incluant la gestion des timeouts et des correspondances entre requêtes et réponses.
*   **`PublishSubscribeProtocol`** ([`pub_sub.py`](../../argumentation_analysis/core/communication/pub_sub.py:235)) : Permet aux agents de publier des messages sur des "topics" et à d'autres agents de s'abonner à ces topics pour recevoir les messages pertinents.

## 4. Canaux de Communication

### 4.1 Définition et Types

Un canal de communication est une voie spécialisée pour l'échange de messages. L'interface de base pour tous les canaux est définie par la classe abstraite `Channel` dans [`channel_interface.py`](../../argumentation_analysis/core/communication/channel_interface.py:30).

Les types de canaux (`ChannelType`) sont définis dans l'énumération `ChannelType` ([`channel_interface.py`](../../argumentation_analysis/core/communication/channel_interface.py:19)) et incluent :
`HIERARCHICAL`, `COLLABORATION`, `DATA`, `NEGOTIATION`, `FEEDBACK`, `SYSTEM`, `LOCAL`.

### 4.2 Canal Hiérarchique (`HierarchicalChannel`)

*   **Implémentation** : [`hierarchical_channel.py`](../../argumentation_analysis/core/communication/hierarchical_channel.py:20)
*   **Objectif** : Communications formelles et structurées entre les différents niveaux hiérarchiques (Stratégique, Tactique, Opérationnel).
*   **Caractéristiques** :
    *   Utilise des files d'attente prioritaires (`PriorityQueue`) par destinataire pour gérer les messages.
    *   Supporte les messages de type `COMMAND`, `INFORMATION`, `REQUEST`, `RESPONSE`.
    *   Maintient des statistiques sur la direction des messages (ex: stratégique vers tactique).

### 4.3 Canal de Collaboration (`CollaborationChannel`)

*   **Implémentation** : [`collaboration_channel.py`](../../argumentation_analysis/core/communication/collaboration_channel.py:140)
*   **Objectif** : Interactions horizontales entre agents de même niveau, coordination, partage d'informations.
*   **Caractéristiques** :
    *   Supporte la création et la gestion de `CollaborationGroup` ([`collaboration_channel.py`](../../argumentation_analysis/core/communication/collaboration_channel.py:20)), permettant des communications many-to-many.
    *   Gère les messages directs entre agents et les messages de groupe.
    *   Permet aux agents de s'abonner pour recevoir des notifications.

### 4.4 Canal de Données (`DataChannel`)

*   **Implémentation** : [`data_channel.py`](../../argumentation_analysis/core/communication/data_channel.py:253)
*   **Objectif** : Transfert efficace de volumes importants de données structurées.
*   **Caractéristiques** :
    *   Intègre un `DataStore` ([`data_channel.py`](../../argumentation_analysis/core/communication/data_channel.py:26)) pour le stockage, la compression (gzip), et le versionnement simple des données.
    *   Si un message contient des données dépassant `max_inline_data_size`, les données sont stockées dans le `DataStore` et le message contient une référence à ces données.
    *   Lors de la réception, si une référence de données est présente, le `DataChannel` récupère les données depuis le `DataStore`.

### 4.5 Canal Local (`LocalChannel`)

*   **Implémentation** : [`channel_interface.py`](../../argumentation_analysis/core/communication/channel_interface.py:96)
*   **Objectif** : Canal simple en mémoire, principalement utilisé pour les tests ou la communication locale au sein d'un même processus.
*   **Caractéristiques** :
    *   Utilise une simple liste Python (`_message_queue`) comme file d'attente.
    *   Implémente les méthodes de base de l'interface `Channel`.

### 4.6 Autres types de canaux (conceptuels)

Les `ChannelType` suivants sont définis mais n'ont pas d'implémentation de classe dédiée trouvée dans le code actuel :

*   **`ChannelType.NEGOTIATION`**: Prévu pour les interactions de négociation.
*   **`ChannelType.FEEDBACK`**: Prévu pour la remontée de feedback.
*   **`ChannelType.SYSTEM`**: Prévu pour les messages de contrôle du système.

Leurs fonctionnalités pourraient être partiellement couvertes par les canaux existants ou représenter des extensions futures.

## 5. Structures de Données pour les Messages (`Message`)

### 5.1 Format de message commun

Tous les messages échangés dans le système sont des instances de la classe `Message` définie dans [`message.py`](../../argumentation_analysis/core/communication/message.py:47).

La structure de base d'un message inclut les champs principaux suivants :

*   `id` (str): Identifiant unique du message (ex: "command-xxxxxxxx").
*   `type` (`MessageType`): Type du message (ex: `COMMAND`, `INFORMATION`). Voir [`message.py`](../../argumentation_analysis/core/communication/message.py:18).
*   `sender` (str): Identifiant de l'agent émetteur.
*   `sender_level` (`AgentLevel`): Niveau hiérarchique de l'émetteur (ex: `STRATEGIC`, `TACTICAL`). Voir [`message.py`](../../argumentation_analysis/core/communication/message.py:38).
*   `recipient` (Optional[str]): Identifiant de l'agent destinataire (None pour broadcast/publication).
*   `channel` (Optional[str]): Nom du canal sur lequel le message transite (peut être défini par le middleware).
*   `priority` (`MessagePriority`): Priorité du message (ex: `NORMAL`, `HIGH`). Voir [`message.py`](../../argumentation_analysis/core/communication/message.py:30).
*   `content` (Dict[str, Any]): Contenu spécifique au type de message.
*   `metadata` (Dict[str, Any]): Métadonnées additionnelles (ex: `conversation_id`, `reply_to`, `topic`).
*   `timestamp` (datetime): Horodatage de la création du message.

La classe `Message` fournit des méthodes pour la conversion en dictionnaire ([`to_dict`](../../argumentation_analysis/core/communication/message.py:119)), la création à partir d'un dictionnaire ([`from_dict`](../../argumentation_analysis/core/communication/message.py:140)), la création de réponses ([`create_response`](../../argumentation_analysis/core/communication/message.py:187)), et d'accusés de réception ([`create_acknowledgement`](../../argumentation_analysis/core/communication/message.py:228)).

### 5.2 Types de messages spécifiques

Des sous-classes de `Message` sont définies dans [`message.py`](../../argumentation_analysis/core/communication/message.py) pour des types de messages courants, facilitant leur création :

*   `CommandMessage` ([`message.py`](../../argumentation_analysis/core/communication/message.py:253))
*   `InformationMessage` ([`message.py`](../../argumentation_analysis/core/communication/message.py:305))
*   `RequestMessage` ([`message.py`](../../argumentation_analysis/core/communication/message.py:346))
*   `EventMessage` ([`message.py`](../../argumentation_analysis/core/communication/message.py:400))

Les exemples de messages JSON fournis dans les versions antérieures de ce document sont conceptuellement alignés avec ces classes. La validation des messages est assurée par la structure des classes Python et le typage, plutôt que par des schémas JSON externes.

## 6. Adaptateurs d'Agents (Concept)

Le concept d'adaptateurs d'agents est mentionné dans ce document et dans [Système de Communication entre Agents](communication_agents.md) comme des interfaces entre les agents et le `MessageMiddleware`, traduisant les communications spécifiques des agents en messages standardisés.

Cependant, le fichier `argumentation_analysis/core/communication/adapters.py`, qui aurait dû contenir ces implémentations, n'a pas été trouvé lors de l'analyse. Par conséquent, cette partie de l'architecture est considérée comme conceptuelle ou son implémentation se trouve dans un emplacement non identifié. Les agents interagissent probablement directement avec le `MessageMiddleware` ou via des interfaces spécifiques à leur niveau hiérarchique qui utilisent le middleware.

## 7. Gestion des Erreurs et Résilience (Principes)

Le code actuel intègre des mécanismes de journalisation (`logging`) au sein du `MessageMiddleware` et des différentes classes de canaux pour tracer les opérations et les erreurs. Les protocoles comme `RequestResponseProtocol` incluent une gestion des timeouts.

Les concepts plus avancés décrits précédemment dans ce document, tels qu'un `ErrorNotificationSystem` centralisé ou des patterns de résilience comme `CircuitBreaker` sous forme de classes Python dédiées, ne sont pas explicitement implémentés. La gestion des erreurs est principalement basée sur la journalisation standard et les mécanismes d'exception Python. Les "Contrats de service" (garantie de livraison, performance, sécurité) sont des objectifs de conception plutôt que des garanties strictes imposées par des mécanismes de code dédiés et vérifiables dans l'implémentation actuelle.

## 8. Cohérence avec les autres documents

*   Ce document a été mis à jour pour mieux s'aligner avec l'implémentation actuelle du code et avec les informations présentées dans [Système de Communication entre Agents](communication_agents.md), qui fournit une vue d'ensemble des interactions entre agents.
*   Le diagramme de référence pour l'architecture multi-canal est [`docs/architecture/images/architecture_multi_canal.md`](images/architecture_multi_canal.md).

## 9. Conclusion et Perspectives

Le système de communication multi-canal, centré sur le `MessageMiddleware`, offre une base robuste et flexible pour les interactions entre agents. Il supporte divers types de canaux et protocoles de communication, permettant des échanges hiérarchiques, collaboratifs et de données.

Les aspects pleinement implémentés incluent le `MessageMiddleware` avec ses fonctionnalités de base de routage et de gestion de canaux, les classes `Message`, `HierarchicalChannel`, `CollaborationChannel`, `DataChannel`, `LocalChannel`, ainsi que les protocoles `RequestResponseProtocol` et `PublishSubscribeProtocol`.

Les aspects qui restent conceptuels, non implémentés en tant que composants dédiés, ou dont l'implémentation n'a pas été localisée incluent : les adaptateurs d'agents (fichier `adapters.py` manquant), les canaux de Négociation, Feedback et Système (en tant que classes distinctes), et les mécanismes avancés de routage, de filtrage/priorisation sophistiqués, d'équilibrage de charge, et de gestion des erreurs/résilience formalisée (comme `CircuitBreaker`).

Des évolutions futures pourraient se concentrer sur l'implémentation de ces concepts avancés si les besoins du projet le justifient, ainsi que sur le renforcement de la sécurité et des capacités de monitoring.