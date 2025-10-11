# Conception du Système de Communication Multi-Canal pour Agents d'Analyse Rhétorique

## Table des matières

1. [Introduction](#1-introduction)
   - [Contexte et objectifs](#11-contexte-et-objectifs)
   - [Limitations du système actuel](#12-limitations-du-système-actuel)
   - [Vision globale du nouveau système](#13-vision-globale-du-nouveau-système)

2. [Architecture Globale](#2-architecture-globale)
   - [Vue d'ensemble](#21-vue-densemble)
   - [Principes architecturaux](#22-principes-architecturaux)
   - [Composants principaux](#23-composants-principaux)

3. [Middleware de Messagerie](#3-middleware-de-messagerie)
   - [Fonctionnalités du middleware](#31-fonctionnalités-du-middleware)
   - [Gestionnaire de canaux](#32-gestionnaire-de-canaux)
   - [Moniteur de communication](#33-moniteur-de-communication)
   - [Adaptateurs d'agents](#34-adaptateurs-dagents)

4. [Canaux de Communication](#4-canaux-de-communication)
   - [Canal hiérarchique](#41-canal-hiérarchique)
   - [Canal de collaboration](#42-canal-de-collaboration)
   - [Canal de données](#43-canal-de-données)
   - [Canal de négociation](#44-canal-de-négociation)
   - [Canal de feedback](#45-canal-de-feedback)

5. [Protocoles de Communication](#5-protocoles-de-communication)
   - [Protocole de requête-réponse](#51-protocole-de-requête-réponse)
   - [Protocole de publication-abonnement](#52-protocole-de-publication-abonnement)
   - [Protocole de négociation](#53-protocole-de-négociation)
   - [Protocole de coordination](#54-protocole-de-coordination)

6. [Structures de Données pour les Messages](#6-structures-de-données-pour-les-messages)
   - [Format de message commun](#61-format-de-message-commun)
   - [Types de messages spécifiques](#62-types-de-messages-spécifiques)
   - [Schémas de validation](#63-schémas-de-validation)

7. [Mécanismes de Routage et Distribution](#7-mécanismes-de-routage-et-distribution)
   - [Routage basé sur les canaux](#71-routage-basé-sur-les-canaux)
   - [Routage basé sur le contenu](#72-routage-basé-sur-le-contenu)
   - [Filtrage et priorisation](#73-filtrage-et-priorisation)
   - [Distribution et équilibrage de charge](#74-distribution-et-équilibrage-de-charge)

8. [Interfaces et Contrats](#8-interfaces-et-contrats)
   - [Interface du middleware](#81-interface-du-middleware)
   - [Interface des adaptateurs](#82-interface-des-adaptateurs)
   - [Contrats de service](#83-contrats-de-service)
   - [API de communication](#84-api-de-communication)

9. [Gestion des Erreurs et Résilience](#9-gestion-des-erreurs-et-résilience)
   - [Détection et notification des erreurs](#91-détection-et-notification-des-erreurs)
   - [Stratégies de récupération](#92-stratégies-de-récupération)
   - [Mécanismes de reprise](#93-mécanismes-de-reprise)
   - [Journalisation et audit](#94-journalisation-et-audit)

10. [Considérations de Performance](#10-considérations-de-performance)
    - [Optimisation des messages](#101-optimisation-des-messages)
    - [Mise en cache](#102-mise-en-cache)
    - [Traitement asynchrone](#103-traitement-asynchrone)
    - [Métriques et surveillance](#104-métriques-et-surveillance)

11. [Plan d'Implémentation](#11-plan-dimplémentation)
    - [Phases de développement](#111-phases-de-développement)
    - [Stratégie de migration](#112-stratégie-de-migration)
    - [Tests et validation](#113-tests-et-validation)

12. [Conclusion](#12-conclusion)
    - [Avantages du nouveau système](#121-avantages-du-nouveau-système)
    - [Perspectives d'évolution](#122-perspectives-dévolution)

## 1. Introduction

### 1.1 Contexte et objectifs

Le système d'analyse rhétorique actuel est basé sur une architecture hiérarchique à trois niveaux (stratégique, tactique et opérationnel), où chaque niveau a des responsabilités spécifiques dans le processus d'analyse. La communication entre ces niveaux est actuellement assurée par des interfaces dédiées qui traduisent les informations d'un niveau à l'autre.

L'objectif de cette conception est de développer un système de communication multi-canal plus riche et flexible qui permettra :

- Une communication bidirectionnelle efficace entre tous les niveaux d'agents
- Des communications horizontales entre agents de même niveau
- Des mécanismes de communication adaptés à différents types d'interactions
- Une architecture extensible pouvant intégrer de nouveaux types de canaux ou protocoles
- Une meilleure gestion des erreurs et une plus grande résilience du système

### 1.2 Limitations du système actuel

Le système de communication actuel présente plusieurs limitations importantes :

1. **Communication unidirectionnelle** : Le flux d'information est principalement descendant (stratégique → tactique → opérationnel) avec un retour d'information limité dans le sens ascendant.

2. **Absence de communication horizontale** : Les agents de même niveau ne peuvent pas collaborer directement, limitant le partage de connaissances et la coordination.

3. **Couplage fort entre les niveaux** : Les interfaces créent une dépendance forte entre les niveaux, rendant difficile l'évolution indépendante de chaque niveau.

4. **Manque de flexibilité dans les formats de communication** : Le système impose un format unique pour la communication, limitant l'expressivité des messages.

5. **Absence de mécanismes de négociation** : Les conflits sont résolus de manière hiérarchique sans possibilité de négociation entre agents.

6. **Gestion limitée des erreurs** : Les erreurs sont journalisées mais pas toujours traitées efficacement, sans mécanisme de récupération automatique.

### 1.3 Vision globale du nouveau système

Le nouveau système de communication multi-canal s'appuiera sur un middleware de messagerie central qui gérera différents canaux de communication spécialisés. Chaque canal sera optimisé pour un type spécifique d'interaction, permettant une communication plus riche et plus flexible entre les agents.

Les agents interagiront avec le middleware via des adaptateurs qui traduiront leurs communications spécifiques en messages standardisés. Le système supportera différents protocoles de communication (requête-réponse, publication-abonnement, etc.) et fournira des mécanismes robustes pour la gestion des erreurs et la résilience.

Cette architecture permettra une séparation claire entre la logique métier des agents et les mécanismes de communication, facilitant l'évolution indépendante de ces deux aspects du système.
## 2. Architecture Globale

### 2.1 Vue d'ensemble

L'architecture du système de communication multi-canal est organisée autour d'un middleware de messagerie central qui coordonne les échanges entre les agents à travers différents canaux spécialisés.

```
┌─────────────────────────────────────────────────────────────────────┐
│                     MIDDLEWARE DE MESSAGERIE                         │
│                                                                     │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────────┐  │
│  │ Gestionnaire│    │ Moniteur de │    │ Mécanismes de Routage   │  │
│  │ de Canaux   │    │Communication│    │ et Distribution         │  │
│  └─────────────┘    └─────────────┘    └─────────────────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                 │               │                │
     ┌───────────┼───────────────┼────────────────┼───────────────┐
     │           │               │                │               │
     ▼           ▼               ▼                ▼               ▼
┌──────────┐ ┌──────────┐ ┌─────────────┐ ┌─────────────┐ ┌────────────┐
│  Canal   │ │  Canal   │ │   Canal     │ │   Canal     │ │   Canal    │
│Hiérarchiq│ │    de    │ │     de      │ │     de      │ │     de     │
│    ue    │ │Collaborat│ │   Données   │ │ Négociation │ │  Feedback  │
└──────────┘ └──────────┘ └─────────────┘ └─────────────┘ └────────────┘
     │           │               │                │               │
     └───────────┼───────────────┼────────────────┼───────────────┘
                 │               │                │
┌────────────────┼───────────────┼────────────────┼───────────────────┐
│                │               │                │                   │
│  ┌─────────────▼───────────────▼────────────────▼───────────────┐   │
│  │                      ADAPTATEURS D'AGENTS                     │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────┐
│                                                                    │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐             │
│  │   Agents    │    │   Agents    │    │   Agents    │             │
│  │ Stratégiques│    │  Tactiques  │    │Opérationnels│             │
│  └─────────────┘    └─────────────┘    └─────────────┘             │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

### 2.2 Principes architecturaux

L'architecture du système de communication multi-canal repose sur plusieurs principes fondamentaux :

1. **Séparation des préoccupations** : Séparation claire entre la logique métier des agents et les mécanismes de communication.

2. **Communication découplée** : Les agents communiquent via des canaux sans connaître les détails d'implémentation des autres agents.

3. **Extensibilité** : L'architecture permet d'ajouter facilement de nouveaux canaux, protocoles ou agents.

4. **Adaptabilité** : Le système s'adapte aux différents besoins de communication des agents.

5. **Résilience** : Le système est conçu pour résister aux pannes et récupérer automatiquement.

6. **Observabilité** : Tous les aspects de la communication sont surveillés et journalisés pour faciliter le débogage et l'optimisation.

7. **Standardisation** : Les messages suivent des formats standardisés pour assurer l'interopérabilité.

8. **Asynchronicité** : La communication est principalement asynchrone pour améliorer les performances et la scalabilité.

### 2.3 Composants principaux

Le système de communication multi-canal comprend les composants principaux suivants :

1. **Middleware de Messagerie** : Composant central qui gère tous les aspects de la communication entre les agents.

2. **Gestionnaire de Canaux** : Responsable de la création, configuration et gestion des différents canaux de communication.

3. **Moniteur de Communication** : Surveille et analyse les communications pour détecter les problèmes et optimiser les performances.

4. **Canaux de Communication** : Canaux spécialisés pour différents types d'interactions (hiérarchique, collaboration, données, négociation, feedback).

5. **Adaptateurs d'Agents** : Interfaces entre les agents et le middleware qui traduisent les communications spécifiques en messages standardisés.

6. **Mécanismes de Routage et Distribution** : Composants responsables d'acheminer les messages aux destinataires appropriés.

7. **Gestionnaire d'Erreurs** : Détecte et gère les erreurs de communication, avec des stratégies de récupération automatique.

## 3. Middleware de Messagerie

### 3.1 Fonctionnalités du middleware

Le middleware de messagerie est le composant central du système de communication multi-canal. Il fournit les fonctionnalités suivantes :

1. **Gestion des canaux** : Création, configuration et supervision des différents canaux de communication.

2. **Routage des messages** : Acheminement des messages aux destinataires appropriés en fonction de règles de routage.

3. **Transformation des messages** : Conversion des messages entre différents formats selon les besoins.

4. **Gestion des erreurs** : Détection, notification et récupération des erreurs de communication.

5. **Journalisation et monitoring** : Enregistrement et analyse des communications pour le débogage et l'optimisation.

6. **Gestion des adaptateurs** : Coordination des adaptateurs qui connectent les agents au middleware.

7. **Contrôle de flux** : Régulation du flux de messages pour éviter la surcharge des agents.

8. **Sécurité** : Authentification et autorisation des communications entre agents.

Le middleware expose une API permettant aux adaptateurs d'agents d'envoyer et de recevoir des messages, de s'abonner à des canaux, et de configurer leurs préférences de communication.

### 3.2 Gestionnaire de canaux

Le gestionnaire de canaux est responsable de la création, configuration et gestion des différents canaux de communication. Il fournit une interface unifiée pour interagir avec les canaux et gère leur cycle de vie.

Ses principales responsabilités sont :

1. **Création de canaux** : Instanciation des différents types de canaux (hiérarchique, collaboration, données, négociation, feedback).

2. **Configuration des canaux** : Paramétrage des canaux selon les besoins spécifiques (capacité, politique de rétention, etc.).

3. **Supervision des canaux** : Surveillance de l'état et des performances des canaux.

4. **Gestion du cycle de vie** : Démarrage, arrêt et redémarrage des canaux si nécessaire.

5. **Routage inter-canaux** : Coordination des échanges entre différents canaux lorsque nécessaire.

### 3.3 Moniteur de communication

Le moniteur de communication surveille et analyse les communications entre les agents pour détecter les problèmes, optimiser les performances et fournir des informations de diagnostic.

Ses principales fonctionnalités sont :

1. **Collecte de métriques** : Recueil de données sur le volume, la latence et les erreurs de communication.

2. **Détection d'anomalies** : Identification des patterns anormaux dans les communications.

3. **Génération d'alertes** : Notification des problèmes détectés aux composants concernés.

4. **Analyse de performance** : Évaluation des performances du système de communication.

5. **Visualisation** : Présentation des données de monitoring sous forme de tableaux de bord.

6. **Historique** : Conservation d'un historique des communications pour analyse rétrospective.

### 3.4 Adaptateurs d'agents

Les adaptateurs d'agents servent d'interface entre les agents et le middleware de messagerie. Ils traduisent les communications spécifiques des agents en messages standardisés compréhensibles par le middleware.

Chaque niveau d'agent (stratégique, tactique, opérationnel) dispose d'un adaptateur spécifique qui :

1. **Traduit les API** : Convertit les appels d'API spécifiques à l'agent en messages standardisés.

2. **Gère les abonnements** : S'abonne aux canaux pertinents pour l'agent.

3. **Filtre les messages** : Ne transmet à l'agent que les messages qui le concernent.

4. **Gère les erreurs** : Traite les erreurs de communication et les signale à l'agent.

5. **Optimise les communications** : Regroupe ou fractionne les messages selon les besoins.

Les adaptateurs permettent aux agents de communiquer sans connaître les détails d'implémentation du middleware, facilitant ainsi l'évolution indépendante des deux composants.

## 4. Canaux de Communication

### 4.1 Canal hiérarchique

Le canal hiérarchique est dédié aux communications formelles entre les différents niveaux de la hiérarchie (stratégique, tactique, opérationnel). Il est optimisé pour les communications verticales et suit un modèle de communication structuré.

**Caractéristiques principales :**

1. **Communication bidirectionnelle** : Supporte les flux descendants (directives, tâches) et ascendants (rapports, résultats).

2. **Garantie de livraison** : Assure que les messages critiques sont bien délivrés, avec confirmation de réception.

3. **Ordonnancement** : Maintient l'ordre des messages pour préserver la cohérence des directives et rapports.

4. **Traçabilité** : Enregistre l'historique complet des communications pour audit et débogage.

5. **Priorisation** : Permet de définir des priorités pour les messages critiques.

**Types de messages supportés :**

- **Directives** : Instructions du niveau stratégique au niveau tactique
- **Tâches** : Instructions du niveau tactique au niveau opérationnel
- **Rapports** : Informations remontées du niveau tactique au niveau stratégique
- **Résultats** : Informations remontées du niveau opérationnel au niveau tactique
- **Requêtes de clarification** : Demandes d'informations supplémentaires entre niveaux
- **Notifications d'état** : Mises à jour sur l'avancement des tâches et objectifs

### 4.2 Canal de collaboration

Le canal de collaboration facilite les interactions horizontales entre agents de même niveau, permettant la coordination, le partage d'informations et la résolution collaborative de problèmes.

**Caractéristiques principales :**

1. **Communication many-to-many** : Permet à plusieurs agents de communiquer simultanément.

2. **Flexibilité** : Supporte différents patterns d'interaction (point-à-point, diffusion, groupe).

3. **Contexte partagé** : Maintient un contexte de collaboration pour chaque interaction.

4. **Dynamisme** : Permet aux agents de rejoindre ou quitter dynamiquement les collaborations.

5. **Persistance configurable** : Conserve l'historique des collaborations selon les besoins.

**Types de messages supportés :**

- **Demandes de collaboration** : Invitations à participer à une activité collaborative
- **Partage d'informations** : Diffusion de connaissances pertinentes
- **Requêtes d'assistance** : Demandes d'aide pour résoudre un problème
- **Propositions** : Suggestions de solutions ou d'approches
- **Coordination d'actions** : Synchronisation des activités entre agents
- **Résolution de conflits** : Négociations pour résoudre des désaccords

### 4.3 Canal de données

Le canal de données est spécialisé dans le transfert efficace de volumes importants de données structurées entre agents, comme des résultats d'analyse, des extraits de texte ou des représentations formelles.

**Caractéristiques principales :**

1. **Haut débit** : Optimisé pour le transfert de grandes quantités de données.

2. **Compression** : Utilise des techniques de compression pour réduire le volume des données.

3. **Streaming** : Permet le transfert progressif de données volumineuses.

4. **Intégrité** : Vérifie l'intégrité des données transmises.

5. **Versionnement** : Gère les versions des données partagées.

**Types de données supportés :**

- **Extraits de texte** : Segments du texte à analyser
- **Résultats d'analyse** : Données structurées issues des analyses
- **Représentations formelles** : Formalisations logiques des arguments
- **Métadonnées** : Informations contextuelles sur les données
- **Références croisées** : Liens entre différentes parties des données
- **Visualisations** : Représentations graphiques des analyses

### 4.4 Canal de négociation

Le canal de négociation permet aux agents de résoudre des conflits, d'allouer des ressources et de prendre des décisions collaboratives à travers des protocoles de négociation structurés.

**Caractéristiques principales :**

1. **Protocoles formels** : Implémente des protocoles de négociation bien définis.

2. **États de négociation** : Maintient l'état des négociations en cours.

3. **Historique des propositions** : Conserve l'historique des offres et contre-offres.

4. **Mécanismes de vote** : Supporte différents mécanismes de prise de décision collective.

5. **Délais négociés** : Gère les contraintes temporelles des négociations.

**Types de négociations supportés :**

- **Résolution de conflits** : Négociations pour résoudre des interprétations contradictoires
- **Allocation de ressources** : Négociations pour l'attribution de ressources limitées
- **Priorisation** : Négociations sur l'ordre de traitement des tâches
- **Consensus** : Recherche d'accord sur des analyses ou conclusions
- **Médiation** : Résolution de désaccords avec l'aide d'un agent médiateur
- **Arbitrage** : Résolution de conflits par décision d'un agent arbitre

### 4.5 Canal de feedback

Le canal de feedback permet la remontée d'informations, de suggestions et d'évaluations à travers tous les niveaux de la hiérarchie, facilitant l'amélioration continue du système.

**Caractéristiques principales :**

1. **Anonymat configurable** : Permet le feedback anonyme ou identifié selon les besoins.

2. **Catégorisation** : Classifie les feedbacks par type et importance.

3. **Agrégation** : Regroupe les feedbacks similaires pour faciliter leur traitement.

4. **Suivi** : Trace l'état de traitement des feedbacks.

5. **Bidirectionnalité** : Permet des réponses aux feedbacks.

**Types de feedback supportés :**

- **Suggestions d'amélioration** : Propositions pour améliorer les processus ou analyses
- **Signalements de problèmes** : Identification de dysfonctionnements ou d'erreurs
- **Évaluations qualitatives** : Appréciations sur la qualité des analyses ou décisions
- **Métriques de satisfaction** : Indicateurs quantitatifs de satisfaction
- **Retours d'expérience** : Partage d'expériences et de leçons apprises
- **Demandes de fonctionnalités** : Suggestions de nouvelles capacités
## 5. Protocoles de Communication

### 5.1 Protocole de requête-réponse

Le protocole de requête-réponse est un modèle d'interaction synchrone où un agent envoie une requête et attend une réponse. Ce protocole est particulièrement adapté aux interactions qui nécessitent une réponse immédiate ou une confirmation.

**Caractéristiques principales :**

1. **Synchronisation** : L'émetteur attend la réponse avant de poursuivre.

2. **Corrélation** : Chaque réponse est associée à une requête spécifique via un identifiant.

3. **Timeout** : Un mécanisme de timeout permet de gérer les cas où la réponse n'arrive pas.

4. **Réessai** : Possibilité de réessayer automatiquement en cas d'échec.

5. **Confirmation** : Accusé de réception pour confirmer la bonne réception de la requête.

**Structure des messages :**

```json
// Requête
{
  "id": "req-123456",
  "type": "request",
  "sender": "agent-A",
  "recipient": "agent-B",
  "action": "get_analysis",
  "parameters": {
    "text_id": "text-789",
    "analysis_type": "fallacy_detection"
  },
  "timeout": 30000,  // millisecondes
  "timestamp": "2025-05-06T15:30:00Z"
}

// Réponse
{
  "id": "resp-654321",
  "type": "response",
  "request_id": "req-123456",
  "sender": "agent-B",
  "recipient": "agent-A",
  "status": "success",
  "result": {
    "fallacies": [
      {
        "type": "ad_hominem",
        "position": { "start": 120, "end": 145 },
        "confidence": 0.85
      }
    ]
  },
  "timestamp": "2025-05-06T15:30:05Z"
}
```

**Cas d'utilisation typiques :**

- Demande d'information spécifique entre agents
- Validation d'une analyse avant de poursuivre
- Requêtes de clarification sur une directive ou une tâche
- Vérification de la disponibilité d'un agent
- Demande d'autorisation pour une action

### 5.2 Protocole de publication-abonnement

Le protocole de publication-abonnement (pub/sub) permet à des agents de publier des messages sur des sujets (topics) auxquels d'autres agents peuvent s'abonner. Ce modèle découple les émetteurs des récepteurs et permet une communication one-to-many efficace.

**Caractéristiques principales :**

1. **Découplage** : Les émetteurs ne connaissent pas les récepteurs et vice versa.

2. **Filtrage** : Les abonnés peuvent filtrer les messages selon des critères spécifiques.

3. **Scalabilité** : Supporte un grand nombre d'émetteurs et de récepteurs.

4. **Asynchronicité** : Communication non bloquante pour l'émetteur.

5. **Durabilité** : Option de persistance des messages pour les abonnés non connectés.

**Structure des messages :**

```json
// Publication
{
  "id": "pub-789012",
  "type": "publication",
  "sender": "agent-C",
  "topic": "new_analysis_results",
  "content": {
    "analysis_id": "analysis-456",
    "text_id": "text-789",
    "analysis_type": "argument_structure",
    "summary": "3 arguments principaux identifiés",
    "timestamp": "2025-05-06T15:35:00Z"
  },
  "metadata": {
    "priority": "normal",
    "ttl": 3600  // secondes
  }
}

// Abonnement
{
  "id": "sub-345678",
  "type": "subscription",
  "subscriber": "agent-D",
  "topic": "new_analysis_results",
  "filter": {
    "analysis_type": "argument_structure",
    "priority": ["high", "normal"]
  },
  "expiration": "2025-06-06T00:00:00Z"
}
```

**Cas d'utilisation typiques :**

- Diffusion de mises à jour d'état à plusieurs agents intéressés
- Notification d'événements importants (nouvelle analyse, erreur critique)
- Partage de résultats intermédiaires avec plusieurs consommateurs
- Diffusion de directives globales à tous les agents d'un niveau
- Monitoring et collecte de métriques

### 5.3 Protocole de négociation

Le protocole de négociation définit un cadre structuré pour les interactions où les agents doivent parvenir à un accord, résoudre un conflit ou allouer des ressources. Il s'appuie sur des séquences d'offres, contre-offres et décisions.

**Caractéristiques principales :**

1. **Phases formelles** : Structuration de la négociation en phases (initialisation, proposition, discussion, résolution).

2. **Contraintes temporelles** : Délais définis pour chaque phase de la négociation.

3. **Règles d'engagement** : Définition claire des règles de la négociation.

4. **Traçabilité** : Enregistrement complet de l'historique des propositions et décisions.

5. **Mécanismes de résolution** : Procédures définies pour résoudre les impasses.

**Structure des messages :**

```json
// Initialisation de négociation
{
  "id": "neg-init-901234",
  "type": "negotiation_init",
  "sender": "agent-E",
  "participants": ["agent-F", "agent-G"],
  "topic": "resource_allocation",
  "context": {
    "resource_type": "processing_time",
    "available_amount": 100,
    "deadline": "2025-05-06T16:00:00Z"
  },
  "rules": {
    "protocol": "round_robin",
    "max_rounds": 3,
    "min_allocation": 10,
    "decision_rule": "majority"
  },
  "timestamp": "2025-05-06T15:40:00Z"
}

// Proposition
{
  "id": "neg-prop-567890",
  "type": "negotiation_proposal",
  "negotiation_id": "neg-init-901234",
  "sender": "agent-F",
  "round": 1,
  "proposal": {
    "agent-E": 30,
    "agent-F": 40,
    "agent-G": 30
  },
  "justification": "Allocation basée sur la complexité des tâches assignées",
  "timestamp": "2025-05-06T15:41:00Z"
}

// Acceptation/Rejet
{
  "id": "neg-resp-123789",
  "type": "negotiation_response",
  "negotiation_id": "neg-init-901234",
  "proposal_id": "neg-prop-567890",
  "sender": "agent-G",
  "response": "counter_proposal",
  "counter_proposal": {
    "agent-E": 25,
    "agent-F": 35,
    "agent-G": 40
  },
  "justification": "Besoin accru pour l'analyse de sophismes complexes",
  "timestamp": "2025-05-06T15:42:00Z"
}

// Résolution
{
  "id": "neg-res-456123",
  "type": "negotiation_resolution",
  "negotiation_id": "neg-init-901234",
  "sender": "agent-E",
  "status": "resolved",
  "final_agreement": {
    "agent-E": 25,
    "agent-F": 35,
    "agent-G": 40
  },
  "votes": {
    "agent-E": "approve",
    "agent-F": "approve",
    "agent-G": "approve"
  },
  "timestamp": "2025-05-06T15:45:00Z"
}
```

**Cas d'utilisation typiques :**

- Allocation de ressources limitées entre agents
- Résolution de conflits d'interprétation
- Priorisation collaborative des tâches
- Prise de décision collective sur des approches d'analyse
- Médiation entre agents ayant des objectifs contradictoires

### 5.4 Protocole de coordination

Le protocole de coordination permet aux agents de synchroniser leurs actions, de coordonner des tâches interdépendantes et de maintenir la cohérence globale du système. Il définit comment les agents planifient, exécutent et suivent des activités collaboratives.

**Caractéristiques principales :**

1. **Plans partagés** : Définition et partage de plans d'action entre agents.

2. **Dépendances** : Gestion explicite des dépendances entre tâches.

3. **Synchronisation** : Mécanismes pour synchroniser les actions des agents.

4. **Suivi de progression** : Reporting standardisé de l'avancement des tâches.

5. **Adaptation** : Ajustement dynamique des plans en fonction des événements.

**Structure des messages :**

```json
// Plan de coordination
{
  "id": "coord-plan-234567",
  "type": "coordination_plan",
  "sender": "agent-H",
  "participants": ["agent-I", "agent-J", "agent-K"],
  "objective": "Analyse complète du texte T-123",
  "tasks": [
    {
      "id": "task-1",
      "description": "Extraction des arguments",
      "assignee": "agent-I",
      "dependencies": [],
      "estimated_duration": 300,  // secondes
      "deadline": "2025-05-06T16:00:00Z"
    },
    {
      "id": "task-2",
      "description": "Détection des sophismes",
      "assignee": "agent-J",
      "dependencies": ["task-1"],
      "estimated_duration": 200,
      "deadline": "2025-05-06T16:05:00Z"
    },
    {
      "id": "task-3",
      "description": "Analyse de cohérence",
      "assignee": "agent-K",
      "dependencies": ["task-1", "task-2"],
      "estimated_duration": 150,
      "deadline": "2025-05-06T16:10:00Z"
    }
  ],
  "coordination_strategy": "sequential_with_overlap",
  "timestamp": "2025-05-06T15:50:00Z"
}

// Mise à jour de statut
{
  "id": "coord-update-345678",
  "type": "coordination_status",
  "plan_id": "coord-plan-234567",
  "sender": "agent-I",
  "task_id": "task-1",
  "status": "in_progress",
  "progress": 0.7,
  "estimated_completion": "2025-05-06T15:58:00Z",
  "issues": [],
  "timestamp": "2025-05-06T15:55:00Z"
}

// Notification d'événement
{
  "id": "coord-event-456789",
  "type": "coordination_event",
  "plan_id": "coord-plan-234567",
  "sender": "agent-I",
  "event_type": "task_completed",
  "task_id": "task-1",
  "details": {
    "result_location": "results/task-1-output.json",
    "quality_metrics": {
      "coverage": 0.95,
      "confidence": 0.88
    }
  },
  "timestamp": "2025-05-06T15:59:00Z"
}

// Ajustement de plan
{
  "id": "coord-adjust-567890",
  "type": "coordination_adjustment",
  "plan_id": "coord-plan-234567",
  "sender": "agent-H",
  "adjustments": [
    {
      "task_id": "task-2",
      "changes": {
        "deadline": "2025-05-06T16:08:00Z",
        "estimated_duration": 250
      },
      "reason": "Complexité plus élevée que prévue"
    }
  ],
  "timestamp": "2025-05-06T16:00:00Z"
}
```

**Cas d'utilisation typiques :**

- Orchestration d'analyses multi-agents
- Coordination de tâches interdépendantes
- Planification collaborative d'activités complexes
- Suivi de progression d'un plan d'analyse
- Adaptation dynamique face aux changements de contexte

## 6. Structures de Données pour les Messages

### 6.1 Format de message commun

Tous les messages échangés dans le système de communication multi-canal suivent un format commun qui assure la cohérence et facilite le traitement. Ce format définit une structure de base que tous les types de messages doivent respecter.

**Structure de base d'un message :**

```json
{
  "id": "msg-123456",              // Identifiant unique du message
  "type": "message_type",          // Type de message
  "sender": "agent-id",            // Identifiant de l'émetteur
  "sender_type": "agent_level",    // Niveau de l'émetteur (stratégique, tactique, opérationnel)
  "recipient": "agent-id",         // Identifiant du destinataire (null pour broadcast)
  "channel": "channel_type",       // Canal utilisé
  "priority": "normal",            // Priorité du message (low, normal, high, critical)
  "content": {},                   // Contenu spécifique au type de message
  "metadata": {                    // Métadonnées du message
    "conversation_id": "conv-789", // Identifiant de la conversation
    "reply_to": "msg-654321",      // Identifiant du message auquel celui-ci répond
    "ttl": 3600,                   // Durée de vie en secondes
    "encryption": "none",          // Type de chiffrement
    "compression": "none"          // Type de compression
  },
  "timestamp": "2025-05-06T16:05:00Z"  // Horodatage ISO 8601
}
```

**Champs obligatoires :**
- `id` : Identifiant unique du message
- `type` : Type de message
- `sender` : Identifiant de l'émetteur
- `timestamp` : Horodatage de création du message

**Champs optionnels :**
- `recipient` : Identifiant du destinataire (absent pour les messages broadcast)
- `channel` : Canal utilisé (peut être déterminé automatiquement)
- `priority` : Priorité du message (par défaut: "normal")
- `metadata` : Métadonnées additionnelles

### 6.2 Types de messages spécifiques

Le système définit plusieurs types de messages spécifiques adaptés aux différents besoins de communication entre agents. Chaque type de message étend le format commun avec des champs spécifiques.

#### Messages de commande

Utilisés pour transmettre des directives, des tâches ou des instructions.

```json
{
  "id": "cmd-123456",
  "type": "command",
  "sender": "strategic-agent-1",
  "sender_type": "strategic",
  "recipient": "tactical-agent-2",
  "channel": "hierarchical",
  "priority": "high",
  "content": {
    "command_type": "execute_analysis",
    "parameters": {
      "text_id": "text-789",
      "analysis_type": "comprehensive",
      "deadline": "2025-05-06T17:00:00Z"
    },
    "constraints": {
      "max_resources": 0.7,
      "min_confidence": 0.8
    }
  },
  "metadata": {
    "conversation_id": "analysis-task-456",
    "requires_ack": true
  },
  "timestamp": "2025-05-06T16:10:00Z"
}
```

#### Messages d'information

Utilisés pour partager des informations, des résultats ou des états.

```json
{
  "id": "info-234567",
  "type": "information",
  "sender": "operational-agent-3",
  "sender_type": "operational",
  "recipient": "tactical-agent-2",
  "channel": "hierarchical",
  "priority": "normal",
  "content": {
    "info_type": "analysis_result",
    "data": {
      "text_id": "text-789",
      "analysis_type": "fallacy_detection",
      "fallacies_found": 3,
      "confidence": 0.85,
      "details_url": "results/fallacy-analysis-789.json"
    }
  },
  "metadata": {
    "conversation_id": "analysis-task-456",
    "reply_to": "cmd-123456"
  },
  "timestamp": "2025-05-06T16:25:00Z"
}
```

#### Messages de requête

Utilisés pour demander des informations ou des actions.

```json
{
  "id": "req-345678",
  "type": "request",
  "sender": "tactical-agent-4",
  "sender_type": "tactical",
  "recipient": "tactical-agent-5",
  "channel": "collaboration",
  "priority": "normal",
  "content": {
    "request_type": "assistance",
    "description": "Besoin d'aide pour analyser un argument complexe",
    "context": {
      "text_id": "text-789",
      "segment": { "start": 1200, "end": 1450 },
      "current_analysis": "results/partial-analysis-789.json"
    },
    "response_format": "json",
    "timeout": 300  // secondes
  },
  "metadata": {
    "conversation_id": "collab-123"
  },
  "timestamp": "2025-05-06T16:30:00Z"
}
```

#### Messages d'événement

Utilisés pour notifier des événements importants dans le système.

```json
{
  "id": "evt-456789",
  "type": "event",
  "sender": "system",
  "sender_type": "system",
  "recipient": null,  // broadcast
  "channel": "feedback",
  "priority": "high",
  "content": {
    "event_type": "resource_warning",
    "description": "Utilisation élevée des ressources de calcul",
    "details": {
      "resource_type": "cpu",
      "current_usage": 0.85,
      "threshold": 0.8,
      "affected_agents": ["operational-agent-3", "operational-agent-6"]
    },
    "recommended_action": "reduce_parallel_processing"
  },
  "metadata": {
    "ttl": 1800  // 30 minutes
  },
  "timestamp": "2025-05-06T16:35:00Z"
}
```

#### Messages de contrôle

Utilisés pour gérer le système de communication lui-même.

```json
{
  "id": "ctrl-567890",
  "type": "control",
  "sender": "system",
  "sender_type": "system",
  "recipient": "all",
  "channel": "system",
  "priority": "critical",
  "content": {
    "control_type": "channel_status",
    "action": "throttle",
    "target": "data_channel",
    "parameters": {
      "rate_limit": 100,  // messages par seconde
      "duration": 300,    // secondes
      "reason": "high_load"
    }
  },
  "metadata": {
    "requires_ack": true
  },
  "timestamp": "2025-05-06T16:40:00Z"
}
```

### 6.3 Schémas de validation

Pour assurer la cohérence et la validité des messages échangés, le système utilise des schémas de validation JSON Schema. Ces schémas définissent formellement la structure attendue pour chaque type de message et permettent de valider les messages avant leur traitement.

**Schéma de base pour tous les messages :**

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Base Message Schema",
  "type": "object",
  "required": ["id", "type", "sender", "timestamp"],
  "properties": {
    "id": {
      "type": "string",
      "pattern": "^[a-z]+-[0-9a-f]{6,}$",
      "description": "Identifiant unique du message"
    },
    "type": {
      "type": "string",
      "enum": ["command", "information", "request", "response", "event", "control", "publication", "subscription", "negotiation_init", "negotiation_proposal", "negotiation_response", "negotiation_resolution", "coordination_plan", "coordination_status", "coordination_event", "coordination_adjustment"],
      "description": "Type de message"
    },
    "sender": {
      "type": "string",
      "description": "Identifiant de l'émetteur"
    },
    "sender_type": {
      "type": "string",
      "enum": ["strategic", "tactical", "operational", "system"],
      "description": "Niveau de l'émetteur"
    },
    "recipient": {
      "type": ["string", "null"],
      "description": "Identifiant du destinataire (null pour broadcast)"
    },
    "channel": {
      "type": "string",
      "enum": ["hierarchical", "collaboration", "data", "negotiation", "feedback", "system"],
      "description": "Canal utilisé"
    },
    "priority": {
      "type": "string",
      "enum": ["low", "normal", "high", "critical"],
      "default": "normal",
      "description": "Priorité du message"
    },
    "content": {
      "type": "object",
      "description": "Contenu spécifique au type de message"
    },
    "metadata": {
      "type": "object",
      "properties": {
        "conversation_id": {
          "type": "string",
          "description": "Identifiant de la conversation"
        },
        "reply_to": {
          "type": "string",
## 7. Mécanismes de Routage et Distribution

### 7.1 Routage basé sur les canaux

Le routage basé sur les canaux est le mécanisme fondamental qui achemine les messages vers le canal approprié en fonction de leur type et de leur contexte. Ce mécanisme assure que chaque message emprunte le canal le plus adapté à son objectif.

**Principes de fonctionnement :**

1. **Sélection automatique** : Le middleware détermine automatiquement le canal approprié en fonction du type de message et de son contenu.

2. **Règles de routage** : Des règles configurables définissent les associations entre types de messages et canaux.

3. **Routage multi-canal** : Possibilité de router un même message vers plusieurs canaux si nécessaire.

4. **Priorités de canal** : Définition d'un ordre de priorité entre canaux pour les cas ambigus.

5. **Routage par défaut** : Canal par défaut pour les messages ne correspondant à aucune règle.

**Implémentation :**

```python
class ChannelRouter:
    def __init__(self):
        # Règles de routage par défaut
        self.routing_rules = {
            "command": "hierarchical",
            "information": ["hierarchical", "data"],
            "request": "hierarchical",
            "response": "hierarchical",
            "event": "feedback",
            "control": "system",
            "publication": "data",
            "subscription": "system",
            "negotiation_init": "negotiation",
            "negotiation_proposal": "negotiation",
            "negotiation_response": "negotiation",
            "negotiation_resolution": "negotiation",
            "coordination_plan": "collaboration",
            "coordination_status": "collaboration",
            "coordination_event": "collaboration",
            "coordination_adjustment": "collaboration"
        }
        
        # Règles de routage spécifiques au contenu
        self.content_rules = [
            {
                "field": "content.info_type",
                "value": "analysis_result",
                "channel": "data"
            },
            {
                "field": "content.request_type",
                "value": "assistance",
                "channel": "collaboration"
            },
            {
                "field": "content.event_type",
                "value": "resource_warning",
                "channel": "feedback"
            }
        ]
        
        # Canal par défaut
        self.default_channel = "hierarchical"
    
    def determine_channels(self, message):
        """Détermine les canaux appropriés pour un message."""
        channels = []
        
        # Vérifier si le type de message a une règle de routage
        message_type = message.get("type")
        if message_type in self.routing_rules:
            rule = self.routing_rules[message_type]
            if isinstance(rule, list):
                channels.extend(rule)
            else:
                channels.append(rule)
        
        # Vérifier les règles basées sur le contenu
        for rule in self.content_rules:
            field_path = rule["field"].split(".")
            value = message
            for path in field_path:
                if isinstance(value, dict) and path in value:
                    value = value[path]
                else:
                    value = None
                    break
            
            if value == rule["value"]:
                channels.append(rule["channel"])
        
        # Si aucun canal n'a été déterminé, utiliser le canal par défaut
        if not channels:
            channels.append(self.default_channel)
        
        # Éliminer les doublons
        return list(set(channels))
```

### 7.2 Routage basé sur le contenu

Le routage basé sur le contenu analyse le contenu des messages pour déterminer leur destination, permettant un acheminement plus précis et contextuel que le simple routage par canal.

**Principes de fonctionnement :**

1. **Analyse de contenu** : Examen du contenu du message pour déterminer sa destination.

2. **Expressions de filtrage** : Utilisation d'expressions (regex, JSONPath, etc.) pour filtrer les messages.

3. **Routage conditionnel** : Acheminement basé sur des conditions complexes.

4. **Transformation contextuelle** : Possibilité de modifier le message en fonction du routage.

5. **Règles hiérarchiques** : Organisation des règles de routage en hiérarchie de priorité.

**Implémentation :**

```python
class ContentRouter:
    def __init__(self):
        # Règles de routage basées sur le contenu
        self.routing_rules = [
            {
                "name": "strategic_directives",
                "condition": lambda msg: msg.get("sender_type") == "strategic" and "directive" in msg.get("content", {}).get("command_type", ""),
                "recipients": lambda msg: self._get_tactical_agents_for_directive(msg)
            },
            {
                "name": "tactical_tasks",
                "condition": lambda msg: msg.get("sender_type") == "tactical" and "task" in msg.get("content", {}).get("command_type", ""),
                "recipients": lambda msg: self._get_operational_agents_for_task(msg)
            },
            {
                "name": "operational_results",
                "condition": lambda msg: msg.get("sender_type") == "operational" and msg.get("content", {}).get("info_type") == "analysis_result",
                "recipients": lambda msg: [msg.get("content", {}).get("original_requester")]
            },
            {
                "name": "resource_warnings",
                "condition": lambda msg: msg.get("content", {}).get("event_type") == "resource_warning",
                "recipients": lambda msg: ["strategic-resource-manager", "tactical-coordinator"]
            },
            {
                "name": "collaboration_requests",
                "condition": lambda msg: msg.get("content", {}).get("request_type") == "assistance",
                "recipients": lambda msg: self._get_agents_with_capability(msg.get("content", {}).get("required_capability"))
            }
        ]
    
    def determine_recipients(self, message):
        """Détermine les destinataires d'un message basé sur son contenu."""
        # Si le message a déjà un destinataire spécifique, le respecter
        if message.get("recipient") and message.get("recipient") != "all" and message.get("recipient") != "null":
            return [message.get("recipient")]
        
        # Appliquer les règles de routage
        for rule in self.routing_rules:
            if rule["condition"](message):
                recipients = rule["recipients"](message)
                if recipients:
                    return recipients
        
        # Si aucune règle ne s'applique et qu'il n'y a pas de destinataire,
        # considérer le message comme un broadcast dans son canal
        return []
    
    def _get_tactical_agents_for_directive(self, message):
        """Détermine les agents tactiques appropriés pour une directive stratégique."""
        # Logique pour déterminer les agents tactiques en fonction de la directive
        directive_type = message.get("content", {}).get("command_type", "")
        if "analyze" in directive_type:
            return ["tactical-analysis-coordinator"]
        elif "resource" in directive_type:
            return ["tactical-resource-manager"]
        elif "report" in directive_type:
            return ["tactical-reporting-agent"]
        else:
            return ["tactical-coordinator"]  # Agent par défaut
    
    def _get_operational_agents_for_task(self, message):
        """Détermine les agents opérationnels appropriés pour une tâche tactique."""
        # Logique pour déterminer les agents opérationnels en fonction de la tâche
        task_type = message.get("content", {}).get("task_type", "")
        required_capabilities = message.get("content", {}).get("required_capabilities", [])
        
        # Obtenir les agents ayant les capacités requises
        capable_agents = self._get_agents_with_capabilities(required_capabilities)
        
        # Filtrer en fonction du type de tâche si nécessaire
        if "fallacy_detection" in task_type:
            return [agent for agent in capable_agents if "fallacy_specialist" in agent]
        elif "argument_extraction" in task_type:
            return [agent for agent in capable_agents if "argument_specialist" in agent]
        elif "formal_analysis" in task_type:
            return [agent for agent in capable_agents if "formal_logic_specialist" in agent]
        else:
            return capable_agents
    
    def _get_agents_with_capabilities(self, capabilities):
        """Retourne les agents ayant les capacités spécifiées."""
        # Cette méthode consulterait normalement un registre d'agents
        # Exemple simplifié pour l'illustration
        agent_capabilities = {
            "operational-agent-1": ["argument_extraction", "fallacy_detection"],
            "operational-agent-2": ["formal_analysis", "consistency_checking"],
            "operational-agent-3": ["fallacy_detection", "bias_analysis"],
            "operational-agent-4": ["argument_extraction", "argument_visualization"]
        }
        
        matching_agents = []
        for agent, agent_caps in agent_capabilities.items():
            if all(cap in agent_caps for cap in capabilities):
                matching_agents.append(agent)
        
        return matching_agents
```

### 7.3 Filtrage et priorisation

Le mécanisme de filtrage et priorisation permet de trier, filtrer et ordonner les messages en fonction de critères comme la priorité, l'émetteur ou le contenu, assurant que les messages les plus importants sont traités en premier.

**Principes de fonctionnement :**

1. **Filtrage multi-critères** : Application de filtres basés sur plusieurs attributs du message.

2. **Priorisation dynamique** : Ajustement de la priorité des messages en fonction du contexte.

3. **Files d'attente prioritaires** : Organisation des messages en files d'attente selon leur priorité.

4. **Politiques de rejet** : Règles pour rejeter les messages de faible priorité en cas de surcharge.

5. **Vieillissement** : Augmentation progressive de la priorité des messages en attente.

**Implémentation :**

```python
class MessageFilter:
    def __init__(self):
        # Filtres prédéfinis
        self.predefined_filters = {
            "high_priority": lambda msg: msg.get("priority") in ["high", "critical"],
            "from_strategic": lambda msg: msg.get("sender_type") == "strategic",
            "from_tactical": lambda msg: msg.get("sender_type") == "tactical",
            "from_operational": lambda msg: msg.get("sender_type") == "operational",
            "commands": lambda msg: msg.get("type") == "command",
            "events": lambda msg: msg.get("type") == "event",
            "requires_ack": lambda msg: msg.get("metadata", {}).get("requires_ack", False)
        }
    
    def apply_filter(self, messages, filter_name=None, custom_filter=None):
        """Applique un filtre prédéfini ou personnalisé à une liste de messages."""
        if filter_name and filter_name in self.predefined_filters:
            filter_func = self.predefined_filters[filter_name]
        elif custom_filter and callable(custom_filter):
            filter_func = custom_filter
        else:
            return messages  # Aucun filtre valide, retourner tous les messages
        
        return [msg for msg in messages if filter_func(msg)]
    
    def combine_filters(self, filter_names, operator="and"):
        """Combine plusieurs filtres prédéfinis avec un opérateur logique."""
        filters = [self.predefined_filters[name] for name in filter_names if name in self.predefined_filters]
        
        if not filters:
            return lambda msg: True  # Aucun filtre valide, accepter tous les messages
        
        if operator == "and":
            return lambda msg: all(f(msg) for f in filters)
        elif operator == "or":
            return lambda msg: any(f(msg) for f in filters)
        else:
            return filters[0]  # Opérateur non reconnu, utiliser le premier filtre

class MessagePrioritizer:
    def __init__(self):
        # Poids de base pour les différentes priorités
        self.priority_weights = {
            "critical": 100,
            "high": 70,
            "normal": 40,
            "low": 10
        }
        
        # Facteurs d'ajustement
        self.adjustment_factors = {
            "sender_type": {
                "strategic": 1.5,
                "tactical": 1.2,
                "operational": 1.0,
                "system": 1.3
            },
            "message_type": {
                "command": 1.3,
                "event": 1.2,
                "request": 1.1,
                "information": 0.9,
                "publication": 0.8
            },
            "age": 0.1  # Augmentation de priorité par unité de temps d'attente
        }
    
    def calculate_priority_score(self, message, wait_time=0):
        """Calcule un score de priorité pour un message."""
        # Priorité de base
        base_priority = self.priority_weights.get(message.get("priority", "normal"), 40)
        
        # Ajustements
        sender_factor = self.adjustment_factors["sender_type"].get(message.get("sender_type", "operational"), 1.0)
        message_factor = self.adjustment_factors["message_type"].get(message.get("type", "information"), 1.0)
        age_factor = 1.0 + (wait_time * self.adjustment_factors["age"])
        
        # Calcul du score final
        score = base_priority * sender_factor * message_factor * age_factor
        
        # Ajustements supplémentaires basés sur des attributs spécifiques
        if message.get("metadata", {}).get("requires_ack", False):
            score *= 1.1
        
        if "deadline" in message.get("content", {}):
            # Augmenter la priorité à l'approche de la deadline
            deadline = message["content"]["deadline"]
            # Calculer le temps restant jusqu'à la deadline
            # (code simplifié pour l'exemple)
            time_to_deadline = 1.0  # valeur normalisée entre 0 et 1
            if time_to_deadline < 0.2:
                score *= 1.5  # Augmentation significative proche de la deadline
        
        return score
    
    def prioritize_messages(self, messages, wait_times=None):
        """Trie une liste de messages par priorité décroissante."""
        if wait_times is None:
            wait_times = {msg["id"]: 0 for msg in messages}
        
        # Calculer les scores de priorité
        message_scores = [(msg, self.calculate_priority_score(msg, wait_times.get(msg["id"], 0))) 
                          for msg in messages]
        
        # Trier par score décroissant
        sorted_messages = [msg for msg, score in sorted(message_scores, key=lambda x: x[1], reverse=True)]
        
        return sorted_messages
```

### 7.4 Distribution et équilibrage de charge

Le mécanisme de distribution et équilibrage de charge assure une répartition efficace des messages entre les agents, évitant la surcharge de certains agents tout en maximisant l'utilisation des ressources disponibles.

**Principes de fonctionnement :**

1. **Équilibrage de charge** : Distribution équitable des messages entre les agents disponibles.

2. **Affinité de session** : Maintien de la cohérence en routant les messages liés à la même conversation vers le même agent.

3. **Capacité adaptative** : Ajustement de la distribution en fonction de la charge et des capacités des agents.

4. **Répartition géographique** : Prise en compte de la localisation des agents pour minimiser la latence.

5. **Redondance** : Distribution des messages critiques à plusieurs agents pour assurer la fiabilité.

**Implémentation :**

```python
class LoadBalancer:
    def __init__(self):
        # État des agents
        self.agent_states = {}
        
        # Stratégies d'équilibrage disponibles
        self.balancing_strategies = {
            "round_robin": self._round_robin_strategy,
            "least_loaded": self._least_loaded_strategy,
            "capability_based": self._capability_based_strategy,
            "consistent_hashing": self._consistent_hashing_strategy
        }
        
        # Stratégie par défaut
        self.default_strategy = "least_loaded"
        
        # Pour le round-robin
        self.current_index = 0
    
    def update_agent_state(self, agent_id, state):
        """Met à jour l'état d'un agent."""
        self.agent_states[agent_id] = state
    
    def get_available_agents(self, required_capabilities=None):
        """Retourne la liste des agents disponibles avec les capacités requises."""
        available_agents = []
        
        for agent_id, state in self.agent_states.items():
            # Vérifier si l'agent est disponible
            if state.get("status") != "available":
                continue
            
            # Vérifier les capacités si spécifiées
            if required_capabilities:
                agent_capabilities = state.get("capabilities", [])
                if not all(cap in agent_capabilities for cap in required_capabilities):
                    continue
            
            available_agents.append(agent_id)
        
        return available_agents
    
    def distribute_message(self, message, strategy=None):
        """Distribue un message à un ou plusieurs agents selon la stratégie spécifiée."""
        # Déterminer la stratégie à utiliser
        strategy_name = strategy or self.default_strategy
        strategy_func = self.balancing_strategies.get(strategy_name, self._least_loaded_strategy)
        
        # Extraire les capacités requises du message si présentes
        required_capabilities = message.get("content", {}).get("required_capabilities", [])
        
        # Obtenir les agents disponibles
        available_agents = self.get_available_agents(required_capabilities)
        
        if not available_agents:
            return None  # Aucun agent disponible
        
        # Appliquer la stratégie d'équilibrage
        selected_agent = strategy_func(message, available_agents)
        
        return selected_agent
    
    def _round_robin_strategy(self, message, available_agents):
        """Stratégie d'équilibrage round-robin."""
        if not available_agents:
            return None
        
        # Sélectionner l'agent suivant dans la liste
        selected_index = self.current_index % len(available_agents)
        selected_agent = available_agents[selected_index]
        
        # Mettre à jour l'index pour la prochaine sélection
        self.current_index = (self.current_index + 1) % len(available_agents)
        
        return selected_agent
    
    def _least_loaded_strategy(self, message, available_agents):
        """Stratégie d'équilibrage basée sur la charge des agents."""
        if not available_agents:
            return None
        
        # Trouver l'agent le moins chargé
        min_load = float('inf')
        selected_agent = None
        
        for agent_id in available_agents:
            agent_state = self.agent_states.get(agent_id, {})
            current_load = agent_state.get("current_load", 0)
            
            if current_load < min_load:
                min_load = current_load
                selected_agent = agent_id
        
        return selected_agent
    
    def _capability_based_strategy(self, message, available_agents):
        """Stratégie d'équilibrage basée sur les capacités des agents."""
        if not available_agents:
            return None
        
        # Extraire les capacités requises du message
        required_capabilities = message.get("content", {}).get("required_capabilities", [])
        
        if not required_capabilities:
            # Si aucune capacité spécifique n'est requise, utiliser least_loaded
            return self._least_loaded_strategy(message, available_agents)
        
        # Calculer un score de correspondance pour chaque agent
        best_match_score = -1
        selected_agent = None
        
        for agent_id in available_agents:
            agent_state = self.agent_states.get(agent_id, {})
            agent_capabilities = agent_state.get("capabilities", [])
            
            # Calculer le score de correspondance (nombre de capacités requises présentes)
            match_score = sum(1 for cap in required_capabilities if cap in agent_capabilities)
            
            # En cas d'égalité, préférer l'agent le moins chargé
            if match_score > best_match_score or (match_score == best_match_score and 
                                                agent_state.get("current_load", 0) < self.agent_states.get(selected_agent, {}).get("current_load", float('inf'))):
                best_match_score = match_score
                selected_agent = agent_id
        
        return selected_agent
    
    def _consistent_hashing_strategy(self, message, available_agents):
        """Stratégie d'équilibrage basée sur le hachage cohérent pour l'affinité de session."""
        if not available_agents:
            return None
        
        # Utiliser l'ID de conversation comme clé de hachage si disponible
        conversation_id = message.get("metadata", {}).get("conversation_id")
        
        if not conversation_id:
            # Si pas d'ID de conversation, utiliser l'ID de l'émetteur
            conversation_id = message.get("sender", "default")
        
        # Calculer un hash simple
        hash_value = hash(conversation_id) % len(available_agents)
        
        # Sélectionner l'agent correspondant
        selected_agent = available_agents[hash_value]
        
        return selected_agent
```

## 8. Interfaces et Contrats

### 8.1 Interface du middleware

L'interface du middleware définit comment les composants externes (adaptateurs d'agents, moniteurs, etc.) interagissent avec le middleware de messagerie. Cette interface expose les fonctionnalités essentielles du middleware tout en masquant sa complexité interne.

**Principales opérations :**

1. **Envoi de messages** : Méthodes pour envoyer des messages via différents canaux.

2. **Réception de messages** : Méthodes pour recevoir des messages de manière synchrone ou asynchrone.

3. **Gestion des abonnements** : Fonctions pour s'abonner ou se désabonner des canaux.

4. **Administration** : Opérations pour configurer et surveiller le middleware.

5. **Gestion des erreurs** : Mécanismes pour signaler et traiter les erreurs.

**Interface API :**

```python
class MiddlewareInterface:
    """Interface publique du middleware de messagerie."""
    
    def send_message(self, message, channel=None, options=None):
        """
        Envoie un message via le middleware.
        
        Args:
            message: Le message à envoyer
            channel: Le canal à utiliser (optionnel)
            options: Options d'envoi (priorité, TTL, etc.)
            
        Returns:
            Un identifiant de confirmation ou None en cas d'échec
        """
        pass
    
    def receive_message(self, channels=None, filter_criteria=None, timeout=None):
        """
        Reçoit un message de manière synchrone.
        
        Args:
            channels: Liste des canaux à écouter
            filter_criteria: Critères de filtrage des messages
            timeout: Délai d'attente maximum en millisecondes
            
        Returns:
            Le message reçu ou None si timeout
        """
        pass
    
    async def receive_message_async(self, channels=None, filter_criteria=None, timeout=None):
        """
        Reçoit un message de manière asynchrone.
        
        Args:
            channels: Liste des canaux à écouter
            filter_criteria: Critères de filtrage des messages
            timeout: Délai d'attente maximum en millisecondes
            
        Returns:
            Le message reçu ou None si timeout
        """
        pass
    
    def subscribe(self, channel, callback=None, filter_criteria=None):
        """
        S'abonne à un canal pour recevoir des messages.
        
        Args:
            channel: Le canal auquel s'abonner
            callback: Fonction de rappel à appeler lors de la réception d'un message
            filter_criteria: Critères de filtrage des messages
            
        Returns:
            Un identifiant d'abonnement
        """
        pass
    
    def unsubscribe(self, subscription_id):
        """
        Se désabonne d'un canal.
        
        Args:
            subscription_id: L'identifiant d'abonnement à annuler
            
        Returns:
Args:
            result: Contenu du résultat
            recipient: Destinataire tactique
            priority: Priorité du résultat
            
        Returns:
            Un identifiant de résultat
        """
        pass
    
    def share_data(self, data, recipients=None, priority="normal"):
        """
        Partage des données avec d'autres agents opérationnels.
        
        Args:
            data: Contenu des données
            recipients: Liste des destinataires opérationnels
            priority: Priorité des données
            
        Returns:
            Un identifiant de partage
        """
        pass
    
    def request_assistance(self, request, recipients, priority="normal"):
        """
        Demande de l'assistance à d'autres agents opérationnels.
        
        Args:
            request: Contenu de la demande
            recipients: Liste des destinataires opérationnels
            priority: Priorité de la demande
            
        Returns:
            Un identifiant de demande
        """
        pass
```

### 8.3 Contrats de service

Les contrats de service définissent formellement les garanties et les responsabilités du système de communication envers ses utilisateurs (les agents). Ces contrats établissent un cadre clair pour les interactions et les attentes.

**Contrat de livraison des messages :**

- **Garantie de livraison** : Le système garantit la livraison des messages avec une priorité "high" ou "critical" tant que le destinataire est disponible.
- **Ordre des messages** : Les messages envoyés par un même émetteur à un même destinataire via le même canal sont délivrés dans l'ordre d'envoi.
- **Unicité** : Chaque message est délivré une seule fois, sauf en cas de réessai explicite.
- **Persistance** : Les messages avec l'attribut `persistent: true` sont stockés jusqu'à leur livraison réussie.
- **Expiration** : Les messages avec un TTL (Time-To-Live) expirent après la durée spécifiée.

**Contrat de performance :**

- **Latence** : Le système garantit une latence maximale de 100ms pour les messages "critical", 500ms pour "high", 1s pour "normal" et 5s pour "low" dans des conditions normales.
- **Débit** : Le système peut traiter jusqu'à 1000 messages par seconde en conditions normales.
- **Disponibilité** : Le système est disponible 99.9% du temps.
- **Récupération** : En cas de panne, le système récupère automatiquement et reprend la livraison des messages persistants.

**Contrat de sécurité :**

- **Authentification** : Tous les messages sont authentifiés pour garantir l'identité de l'émetteur.
- **Autorisation** : Les agents ne peuvent envoyer des messages que sur les canaux auxquels ils ont accès.
- **Confidentialité** : Les messages marqués comme confidentiels sont chiffrés pendant le transport.
- **Intégrité** : L'intégrité des messages est garantie par des mécanismes de vérification.

**Contrat de notification :**

- **Accusés de réception** : Les messages avec l'attribut `requires_ack: true` génèrent un accusé de réception.
- **Notifications d'erreur** : Les erreurs de livraison sont notifiées à l'émetteur.
- **Alertes de performance** : Les problèmes de performance sont signalés aux administrateurs.
- **Journalisation** : Toutes les opérations importantes sont journalisées pour audit.

### 8.4 API de communication

L'API de communication définit les interfaces programmatiques que les développeurs peuvent utiliser pour intégrer leurs agents au système de communication. Cette API est conçue pour être simple, cohérente et robuste.

**API REST pour l'administration :**

```
# Gestion des canaux
POST   /api/channels                # Créer un nouveau canal
GET    /api/channels                # Lister tous les canaux
GET    /api/channels/{channel_id}   # Obtenir les détails d'un canal
PUT    /api/channels/{channel_id}   # Mettre à jour un canal
DELETE /api/channels/{channel_id}   # Supprimer un canal

# Gestion des agents
POST   /api/agents                  # Enregistrer un nouvel agent
GET    /api/agents                  # Lister tous les agents
GET    /api/agents/{agent_id}       # Obtenir les détails d'un agent
PUT    /api/agents/{agent_id}       # Mettre à jour un agent
DELETE /api/agents/{agent_id}       # Désactiver un agent

# Monitoring
GET    /api/stats                   # Obtenir les statistiques globales
GET    /api/stats/channels          # Obtenir les statistiques par canal
GET    /api/stats/agents            # Obtenir les statistiques par agent
GET    /api/logs                    # Obtenir les journaux
GET    /api/alerts                  # Obtenir les alertes actives
```

**API WebSocket pour la messagerie en temps réel :**

```
# Connexion WebSocket
WS     /api/ws/{agent_id}           # Établir une connexion WebSocket pour un agent

# Messages envoyés par le client
{
  "action": "send",                 # Envoyer un message
  "channel": "channel_type",        # Canal à utiliser
  "message": { ... }                # Contenu du message
}

{
  "action": "subscribe",            # S'abonner à un canal
  "channel": "channel_type",        # Canal auquel s'abonner
  "filter": { ... }                 # Critères de filtrage
}

{
  "action": "unsubscribe",          # Se désabonner d'un canal
  "subscription_id": "sub-123"      # Identifiant d'abonnement
}

# Messages envoyés par le serveur
{
  "type": "message",                # Réception d'un message
  "channel": "channel_type",        # Canal source
  "message": { ... }                # Contenu du message
}

{
  "type": "ack",                    # Accusé de réception
  "message_id": "msg-123",          # Identifiant du message
  "status": "delivered"             # Statut de livraison
}

{
  "type": "error",                  # Notification d'erreur
  "code": "error_code",             # Code d'erreur
  "message": "Error description"    # Description de l'erreur
}
```

**API de bibliothèque cliente :**

```python
# Exemple d'utilisation de la bibliothèque cliente
from multichannel_comms import Agent, Message

# Créer un agent
agent = Agent(
    agent_id="tactical-agent-1",
    agent_type="tactical",
    capabilities=["task_coordination", "resource_management"]
)

# Connexion au middleware
agent.connect(middleware_url="ws://middleware.example.com/api/ws")

# Envoi d'un message
message_id = agent.send(
    message_type="task",
    content={
        "task_type": "analyze_text",
        "text_id": "text-123",
        "parameters": { ... }
    },
    recipient="operational-agent-2",
    priority="high"
)

# Réception d'un message
message = agent.receive(timeout=5000)  # 5 secondes

# Abonnement à un canal
subscription_id = agent.subscribe(
    channel="feedback",
    callback=lambda msg: print(f"Feedback reçu: {msg}"),
    filter_criteria={"priority": ["high", "critical"]}
)

# Désabonnement
agent.unsubscribe(subscription_id)

# Fermeture de la connexion
agent.disconnect()
```

## 9. Gestion des Erreurs et Résilience

### 9.1 Détection et notification des erreurs

Le système de communication multi-canal intègre des mécanismes robustes pour détecter, notifier et gérer les erreurs à tous les niveaux. Ces mécanismes assurent que les problèmes sont identifiés rapidement et traités de manière appropriée.

**Types d'erreurs détectées :**

1. **Erreurs de communication** : Échecs de connexion, timeouts, erreurs de protocole.
2. **Erreurs de validation** : Messages mal formés, violations de schéma, données invalides.
3. **Erreurs d'autorisation** : Tentatives d'accès non autorisées, violations de sécurité.
4. **Erreurs de routage** : Destinataires introuvables, canaux indisponibles.
5. **Erreurs de traitement** : Exceptions lors du traitement des messages.
6. **Erreurs système** : Problèmes de ressources, pannes de composants.

**Mécanismes de détection :**

1. **Validation proactive** : Vérification des messages avant leur traitement.
2. **Surveillance des délais** : Détection des opérations qui prennent trop de temps.
3. **Vérifications d'intégrité** : Contrôle de l'intégrité des messages et des états.
4. **Heartbeats** : Signaux périodiques pour vérifier la disponibilité des composants.
5. **Analyse de tendances** : Détection des anomalies dans les patterns de communication.

**Système de notification :**

```python
class ErrorNotificationSystem:
    def __init__(self):
        self.error_handlers = {}
        self.notification_channels = []
        self.error_log = []
        self.error_metrics = {
            "by_type": {},
            "by_severity": {},
            "by_component": {}
        }
    
    def register_error_handler(self, error_type, handler, priority=0):
        """Enregistre un gestionnaire d'erreurs pour un type d'erreur spécifique."""
        if error_type not in self.error_handlers:
            self.error_handlers[error_type] = []
        
        self.error_handlers[error_type].append({
            "handler": handler,
            "priority": priority
        })
        
        # Trier les gestionnaires par priorité décroissante
        self.error_handlers[error_type].sort(key=lambda h: h["priority"], reverse=True)
    
    def add_notification_channel(self, channel):
        """Ajoute un canal de notification pour les erreurs."""
        self.notification_channels.append(channel)
    
    def notify_error(self, error, context=None):
        """Notifie une erreur aux gestionnaires appropriés et aux canaux de notification."""
        error_type = type(error).__name__
        
        # Journaliser l'erreur
        error_entry = {
            "timestamp": datetime.now().isoformat(),
            "error_type": error_type,
            "error_message": str(error),
            "context": context,
            "severity": self._determine_severity(error, context)
        }
        self.error_log.append(error_entry)
        
        # Mettre à jour les métriques
        self._update_metrics(error_entry)
        
        # Notifier les gestionnaires d'erreurs
        handled = False
        
        # Gestionnaires spécifiques au type d'erreur
        if error_type in self.error_handlers:
            for handler_info in self.error_handlers[error_type]:
                try:
                    if handler_info["handler"](error, context):
                        handled = True
                        break
                except Exception as e:
                    # Éviter les erreurs en cascade
                    print(f"Error in error handler: {e}")
        
        # Gestionnaires génériques si aucun gestionnaire spécifique n'a géré l'erreur
        if not handled and "Exception" in self.error_handlers:
            for handler_info in self.error_handlers["Exception"]:
                try:
                    handler_info["handler"](error, context)
                except Exception as e:
                    print(f"Error in generic error handler: {e}")
        
        # Notifier les canaux de notification
        for channel in self.notification_channels:
            try:
                channel.notify(error_entry)
            except Exception as e:
                print(f"Error in notification channel: {e}")
    
    def _determine_severity(self, error, context):
        """Détermine la sévérité d'une erreur en fonction de son type et du contexte."""
        # Logique pour déterminer la sévérité
        if isinstance(error, (ConnectionError, TimeoutError)):
            return "high"
        elif isinstance(error, ValueError):
            return "medium"
        elif isinstance(error, Warning):
            return "low"
        else:
            # Vérifier le contexte pour des indices de sévérité
            if context and "priority" in context:
                if context["priority"] in ["critical", "high"]:
                    return "high"
            
            return "medium"  # Sévérité par défaut
    
    def _update_metrics(self, error_entry):
        """Met à jour les métriques d'erreur."""
        error_type = error_entry["error_type"]
        severity = error_entry["severity"]
        component = error_entry.get("context", {}).get("component", "unknown")
        
        # Mettre à jour les compteurs par type
        if error_type not in self.error_metrics["by_type"]:
            self.error_metrics["by_type"][error_type] = 0
        self.error_metrics["by_type"][error_type] += 1
        
        # Mettre à jour les compteurs par sévérité
        if severity not in self.error_metrics["by_severity"]:
            self.error_metrics["by_severity"][severity] = 0
        self.error_metrics["by_severity"][severity] += 1
        
        # Mettre à jour les compteurs par composant
        if component not in self.error_metrics["by_component"]:
            self.error_metrics["by_component"][component] = 0
        self.error_metrics["by_component"][component] += 1
    
    def get_error_metrics(self):
        """Retourne les métriques d'erreur actuelles."""
        return self.error_metrics
    
    def get_recent_errors(self, count=10, severity=None, error_type=None):
        """Retourne les erreurs récentes, éventuellement filtrées par sévérité ou type."""
        filtered_errors = self.error_log
        
        if severity:
            filtered_errors = [e for e in filtered_errors if e["severity"] == severity]
        
        if error_type:
            filtered_errors = [e for e in filtered_errors if e["error_type"] == error_type]
        
        # Trier par timestamp décroissant (plus récent d'abord)
        sorted_errors = sorted(filtered_errors, key=lambda e: e["timestamp"], reverse=True)
        
        return sorted_errors[:count]
```

### 9.2 Stratégies de récupération

Le système implémente diverses stratégies de récupération pour maintenir la continuité du service en cas d'erreur. Ces stratégies permettent au système de se rétablir automatiquement après des défaillances.

**Stratégies principales :**

1. **Réessai avec backoff exponentiel** : Tentatives répétées avec des délais croissants.
2. **Circuit breaker** : Prévention des appels répétés à des composants défaillants.
3. **Fallback** : Utilisation d'alternatives en cas d'échec du chemin principal.
4. **Bulkhead** : Isolation des défaillances pour éviter leur propagation.
5. **Timeout** : Limitation du temps d'attente pour éviter les blocages.

**Implémentation du pattern Circuit Breaker :**

```python
class CircuitBreaker:
    """Implémentation du pattern Circuit Breaker pour prévenir les appels répétés à des composants défaillants."""
    
    # États possibles
    CLOSED = "closed"      # Circuit fermé, les appels passent normalement
    OPEN = "open"          # Circuit ouvert, les appels échouent immédiatement
    HALF_OPEN = "half_open"  # Circuit semi-ouvert, un appel test est autorisé
    
    def __init__(self, failure_threshold=5, recovery_timeout=60, name="default"):
        self.name = name
        self.failure_threshold = failure_threshold  # Nombre d'échecs avant ouverture
        self.recovery_timeout = recovery_timeout    # Temps avant passage en semi-ouvert (secondes)
        
        self.state = self.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.successful_calls = 0
        
        self.logger = logging.getLogger(f"CircuitBreaker.{name}")
    
    def execute(self, func, *args, **kwargs):
        """Exécute une fonction en appliquant le pattern Circuit Breaker."""
        if self.state == self.OPEN:
            # Vérifier si le temps de récupération est écoulé
            if self.last_failure_time and (datetime.now() - self.last_failure_time).total_seconds() >= self.recovery_timeout:
                self.logger.info(f"Circuit {self.name} transitioning from OPEN to HALF_OPEN")
                self.state = self.HALF_OPEN
            else:
                # Circuit ouvert et temps de récupération non écoulé
                self.logger.warning(f"Circuit {self.name} is OPEN, fast failing")
                raise CircuitBreakerOpenError(f"Circuit {self.name} is open")
        
        try:
            result = func(*args, **kwargs)
            
            # En cas de succès
            if self.state == self.HALF_OPEN:
                # Réinitialiser le circuit après un succès en état semi-ouvert
                self.logger.info(f"Circuit {self.name} transitioning from HALF_OPEN to CLOSED")
                self.state = self.CLOSED
                self.failure_count = 0
                self.successful_calls = 0
            elif self.state == self.CLOSED:
                # Incrémenter le compteur de succès
                self.successful_calls += 1
            
            return result
            
        except Exception as e:
            # En cas d'échec
            self.last_failure_time = datetime.now()
            
            if self.state == self.HALF_OPEN:
                # Retour à l'état ouvert après un échec en état semi-ouvert
                self.logger.warning(f"Circuit {self.name} transitioning from HALF_OPEN to OPEN due to failure")
                self.state = self.OPEN
            elif self.state == self.CLOSED:
                # Incrémenter le compteur d'échecs
                self.failure_count += 1
                
                # Vérifier si le seuil d'échecs est atteint
                if self.failure_count >= self.failure_threshold:
                    self.logger.warning(f"Circuit {self.name} transitioning from CLOSED to OPEN due to too many failures")
                    self.state = self.OPEN
            
            # Propager l'exception
            raise
```

**Implémentation du pattern Retry :**

```python
class RetryWithBackoff:
    """Implémentation du pattern Retry avec backoff exponentiel."""
    
    def __init__(self, max_retries=3, initial_backoff=1000, max_backoff=30000, backoff_factor=2, jitter=0.1):
        self.max_retries = max_retries            # Nombre maximum de tentatives
        self.initial_backoff = initial_backoff    # Délai initial en millisecondes
        self.max_backoff = max_backoff            # Délai maximum en millisecondes
        self.backoff_factor = backoff_factor      # Facteur de multiplication du délai
        self.jitter = jitter                      # Facteur de variation aléatoire
        
        self.logger = logging.getLogger("RetryWithBackoff")
    
    def execute(self, func, *args, retry_on_exceptions=None, **kwargs):
        """Exécute une fonction avec réessai en cas d'échec."""
        if retry_on_exceptions is None:
            retry_on_exceptions = (Exception,)
        
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except retry_on_exceptions as e:
                last_exception = e
                
                if attempt < self.max_retries:
                    # Calculer le délai de backoff
                    backoff = min(
                        self.max_backoff,
                        self.initial_backoff * (self.backoff_factor ** attempt)
                    )
                    
                    # Ajouter un jitter pour éviter les tempêtes de réessais
                    jitter_amount = backoff * self.jitter
                    backoff = backoff + random.uniform(-jitter_amount, jitter_amount)
                    
                    self.logger.warning(f"Attempt {attempt + 1} failed, retrying in {backoff/1000:.2f}s: {str(e)}")
                    
                    # Attendre avant de réessayer
                    time.sleep(backoff / 1000)  # Convertir en secondes
                else:
                    self.logger.error(f"All {self.max_retries + 1} attempts failed")
        
        # Si toutes les tentatives ont échoué, lever la dernière exception
        raise last_exception
```

### 9.3 Mécanismes de reprise

Les mécanismes de reprise permettent au système de récupérer son état après une panne et de reprendre les opérations interrompues. Ces mécanismes assurent la continuité du service et minimisent la perte de données.

**Principales fonctionnalités :**

1. **Persistance des messages** : Stockage des messages critiques pour éviter leur perte.
2. **Journalisation des transactions** : Enregistrement des opérations pour permettre leur rejeu.
3. **Points de contrôle** : Sauvegarde périodique de l'état du système.
4. **Récupération d'état** : Restauration de l'état à partir des sauvegardes.
5. **Rejeu des messages** : Réémission des messages non traités après une panne.

**Implémentation de la persistance et du rejeu des messages :**

```python
class MessagePersistenceManager:
    """Gère la persistance et le rejeu des messages pour la récupération après panne."""
    
    def __init__(self, storage_path, max_batch_size=100):
        self.storage_path = storage_path
        self.max_batch_size = max_batch_size
        
        # Créer le répertoire de stockage s'il n'existe pas
        os.makedirs(storage_path, exist_ok=True)
        
        # File d'attente des messages à persister
        self.pending_messages = []
        
        # Verrou pour les opérations concurrentes
        self.lock = threading.Lock()
        
        # Démarrer le thread de persistance en arrière-plan
        self.running = True
        self.persistence_thread = threading.Thread(target=self._persistence_worker)
        self.persistence_thread.daemon = True
        self.persistence_thread.start()
        
        self.logger = logging.getLogger("MessagePersistenceManager")
    
    def persist_message(self, message, channel):
        """Persiste un message pour une éventuelle récupération."""
        # Vérifier si le message doit être persisté
        if not self._should_persist(message):
            return
        
        # Ajouter le message à la file d'attente
        with self.lock:
            self.pending_messages.append({
                "message": message,
                "channel": channel,
                "timestamp": datetime.now().isoformat()
            })
    
    def _persistence_worker(self):
        """Thread travailleur qui persiste les messages en arrière-plan."""
        while self.running:
            batch = []
            
            # Récupérer un lot de messages à persister
            with self.lock:
                if len(self.pending_messages) > 0:
                    batch = self.pending_messages[:self.max_batch_size]
                    self.pending_messages = self.pending_messages[self.max_batch_size:]
            
            if batch:
                try:
                    # Persister le lot de messages
                    self._write_batch(batch)
                except Exception as e:
                    self.logger.error(f"Error persisting messages: {str(e)}")
                    # Remettre les messages dans la file d'attente
                    with self.lock:
                        self.pending_messages = batch + self.pending_messages
            
            # Attendre un peu avant la prochaine vérification
            time.sleep(0.1)
    
    def _write_batch(self, batch):
        """Écrit un lot de messages dans le stockage persistant."""
        # Générer un nom de fichier unique
        filename = f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}.json"
        filepath = os.path.join(self.storage_path, filename)
        
        # Écrire les messages dans un fichier JSON
        with open(filepath, 'w') as f:
            json.dump(batch, f)
    
    def replay_messages(self, middleware, start_time=None, end_time=None, channels=None):
        """Rejoue les messages persistés dans le middleware."""
        # Récupérer la liste des fichiers de messages
        message_files = sorted(os.listdir(self.storage_path))
        
        replayed_count = 0
        
        for filename in message_files:
            filepath = os.path.join(self.storage_path, filename)
            
            try:
                # Charger les messages depuis le fichier
                with open(filepath, 'r') as f:
                    batch = json.load(f)
                
                # Filtrer et rejouer les messages
                for entry in batch:
                    message = entry["message"]
                    channel = entry["channel"]
                    timestamp = entry["timestamp"]
                    
                    # Appliquer les filtres
                    if start_time and timestamp < start_time:
                        continue
                    if end_time and timestamp > end_time:
                        continue
                    if channels and channel not in channels:
                        continue
                    
                    # Rejouer le message
                    try:
"recipient": message.get("recipient"),
            "message_type": message.get("type"),
            "priority": message.get("priority")
        }
        
        # Journaliser avec le niveau approprié
        if is_error:
            self.logger.error(f"{direction.upper()} {message.get('type')} message {message.get('id')} on {channel}")
        elif message.get("priority") == "critical":
            self.logger.critical(f"{direction.upper()} {message.get('type')} message {message.get('id')} on {channel}")
        elif message.get("priority") == "high":
            self.logger.warning(f"{direction.upper()} {message.get('type')} message {message.get('id')} on {channel}")
        else:
            self.logger.info(f"{direction.upper()} {message.get('type')} message {message.get('id')} on {channel}")
        
        # Journaliser les détails au niveau debug
        self.logger.debug(f"Message details: {json.dumps(message)}")
    
    def log_event(self, event_type, details, level=INFO):
        """Journalise un événement système."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "details": details
        }
        
        # Journaliser avec le niveau spécifié
        if level == self.DEBUG:
            self.logger.debug(f"EVENT {event_type}: {json.dumps(details)}")
        elif level == self.INFO:
            self.logger.info(f"EVENT {event_type}: {json.dumps(details)}")
        elif level == self.WARNING:
            self.logger.warning(f"EVENT {event_type}: {json.dumps(details)}")
        elif level == self.ERROR:
            self.logger.error(f"EVENT {event_type}: {json.dumps(details)}")
        elif level == self.CRITICAL:
            self.logger.critical(f"EVENT {event_type}: {json.dumps(details)}")
    
    def log_audit(self, action, actor, resource, result, details=None):
        """Journalise une entrée d'audit pour les opérations sensibles."""
        audit_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "actor": actor,
            "resource": resource,
            "result": result,
            "details": details or {}
        }
        
        # Ajouter au journal d'audit
        self.audit_log.append(audit_entry)
        
        # Journaliser également dans le journal principal
        self.logger.info(f"AUDIT: {action} by {actor} on {resource}: {result}")
        
        # Si configuré, écrire immédiatement dans un fichier d'audit séparé
        # (implémentation omise pour simplifier)
    
    def get_logs(self, start_time=None, end_time=None, level=None, filters=None):
        """Récupère les journaux filtrés."""
        # Cette méthode dépendrait de l'implémentation spécifique du stockage des journaux
        # Exemple simplifié pour l'illustration
        return {"message": "Log retrieval not implemented in this example"}
    
    def get_audit_logs(self, start_time=None, end_time=None, filters=None):
        """Récupère les journaux d'audit filtrés."""
        filtered_logs = self.audit_log
        
        # Filtrer par plage de temps
        if start_time:
            filtered_logs = [log for log in filtered_logs if log["timestamp"] >= start_time]
        if end_time:
            filtered_logs = [log for log in filtered_logs if log["timestamp"] <= end_time]
        
        # Appliquer des filtres supplémentaires
        if filters:
            for key, value in filters.items():
                if key in ["action", "actor", "resource", "result"]:
                    filtered_logs = [log for log in filtered_logs if log[key] == value]
        
        return filtered_logs
```

## 10. Considérations de Performance

### 10.1 Optimisation des messages

Pour maximiser les performances du système de communication, plusieurs techniques d'optimisation des messages sont mises en œuvre. Ces optimisations réduisent la taille des messages, minimisent la latence et augmentent le débit global.

**Techniques d'optimisation :**

1. **Compression des messages** : Réduction de la taille des messages pour économiser la bande passante.
2. **Sérialisation efficace** : Utilisation de formats de sérialisation compacts et rapides.
3. **Batching** : Regroupement de plusieurs messages en un seul envoi pour réduire les frais généraux.
4. **Filtrage côté source** : Élimination des données non essentielles avant l'envoi.
5. **Messages partiels** : Transmission des seules modifications plutôt que des messages complets.

**Implémentation de la compression et du batching :**

```python
class MessageOptimizer:
    """Optimise les messages pour améliorer les performances."""
    
    def __init__(self, compression_threshold=1024, max_batch_size=100, max_batch_delay=100):
        self.compression_threshold = compression_threshold  # Taille en octets
        self.max_batch_size = max_batch_size  # Nombre maximum de messages par lot
        self.max_batch_delay = max_batch_delay  # Délai maximum en millisecondes
        
        # Dictionnaire des lots en cours par destination et canal
        self.batches = {}
        
        # Verrou pour les opérations concurrentes
        self.lock = threading.Lock()
        
        # Démarrer le thread de traitement des lots
        self.running = True
        self.batch_thread = threading.Thread(target=self._batch_processor)
        self.batch_thread.daemon = True
        self.batch_thread.start()
    
    def optimize_message(self, message):
        """Optimise un message individuel."""
        # Copie du message pour éviter de modifier l'original
        optimized = message.copy()
        
        # Supprimer les champs vides ou nuls
        for key in list(optimized.keys()):
            if optimized[key] is None or (isinstance(optimized[key], (dict, list)) and not optimized[key]):
                del optimized[key]
        
        # Compresser le contenu si nécessaire
        content = optimized.get("content")
        if content and isinstance(content, dict):
            content_json = json.dumps(content)
            if len(content_json) > self.compression_threshold:
                # Compresser le contenu
                compressed = gzip.compress(content_json.encode('utf-8'))
                
                # Remplacer le contenu par sa version compressée
                optimized["content"] = None
                optimized["metadata"] = optimized.get("metadata", {})
                optimized["metadata"]["compression"] = "gzip"
                optimized["metadata"]["original_content_length"] = len(content_json)
                optimized["compressed_content"] = base64.b64encode(compressed).decode('utf-8')
        
        return optimized
    
    def add_to_batch(self, message, recipient, channel):
        """Ajoute un message à un lot pour envoi groupé."""
        # Clé unique pour ce destinataire et ce canal
        batch_key = f"{recipient}:{channel}"
        
        with self.lock:
            # Créer un nouveau lot si nécessaire
            if batch_key not in self.batches:
                self.batches[batch_key] = {
                    "messages": [],
                    "recipient": recipient,
                    "channel": channel,
                    "created_at": datetime.now()
                }
            
            # Ajouter le message au lot
            self.batches[batch_key]["messages"].append(message)
            
            # Vérifier si le lot doit être envoyé immédiatement
            if len(self.batches[batch_key]["messages"]) >= self.max_batch_size:
                return self._create_batch_message(self.batches.pop(batch_key))
        
        # Le message a été ajouté au lot, il sera envoyé plus tard
        return None
    
    def _batch_processor(self):
        """Thread qui traite les lots en attente."""
        while self.running:
            batches_to_send = []
            
            # Identifier les lots qui ont atteint leur délai maximum
            with self.lock:
                current_time = datetime.now()
                for key, batch in list(self.batches.items()):
                    elapsed = (current_time - batch["created_at"]).total_seconds() * 1000
                    if elapsed >= self.max_batch_delay:
                        batches_to_send.append(self.batches.pop(key))
            
            # Créer et envoyer les messages de lot
            for batch in batches_to_send:
                batch_message = self._create_batch_message(batch)
                # L'envoi serait géré par le middleware
                # middleware.send_message(batch_message, batch["channel"])
            
            # Attendre un peu avant la prochaine vérification
            time.sleep(0.01)  # 10ms
    
    def _create_batch_message(self, batch):
        """Crée un message de lot à partir d'un lot de messages individuels."""
        return {
            "id": f"batch-{uuid.uuid4().hex}",
            "type": "batch",
            "sender": "message_optimizer",
            "recipient": batch["recipient"],
            "channel": batch["channel"],
            "priority": self._determine_batch_priority(batch["messages"]),
            "content": {
                "message_count": len(batch["messages"]),
                "messages": batch["messages"]
            },
            "metadata": {
                "batch": True,
                "created_at": batch["created_at"].isoformat(),
                "sent_at": datetime.now().isoformat()
            },
            "timestamp": datetime.now().isoformat()
        }
    
    def _determine_batch_priority(self, messages):
        """Détermine la priorité d'un lot en fonction des messages qu'il contient."""
        # Utiliser la priorité la plus élevée des messages du lot
        priorities = {"critical": 3, "high": 2, "normal": 1, "low": 0}
        max_priority = "low"
        
        for message in messages:
            priority = message.get("priority", "normal")
            if priorities.get(priority, 0) > priorities.get(max_priority, 0):
                max_priority = priority
        
        return max_priority
    
    def decompress_message(self, message):
        """Décompresse un message si nécessaire."""
        # Vérifier si le message est compressé
        if "compressed_content" in message and message.get("metadata", {}).get("compression") == "gzip":
            # Décompresser le contenu
            compressed = base64.b64decode(message["compressed_content"])
            decompressed = gzip.decompress(compressed).decode('utf-8')
            
            # Restaurer le contenu original
            message["content"] = json.loads(decompressed)
            
            # Nettoyer les métadonnées de compression
            del message["compressed_content"]
            if "metadata" in message and "compression" in message["metadata"]:
                del message["metadata"]["compression"]
            if "metadata" in message and "original_content_length" in message["metadata"]:
                del message["metadata"]["original_content_length"]
        
        return message
    
    def unbatch_messages(self, batch_message):
        """Extrait les messages individuels d'un message de lot."""
        if batch_message.get("type") != "batch":
            return [batch_message]  # Pas un lot
        
        # Extraire les messages du lot
        messages = batch_message.get("content", {}).get("messages", [])
        
        # Restaurer les informations de contexte
        for message in messages:
            if "recipient" not in message:
                message["recipient"] = batch_message.get("recipient")
            if "channel" not in message and "channel" in batch_message:
                message["channel"] = batch_message.get("channel")
        
        return messages
    
    def shutdown(self):
        """Arrête proprement l'optimiseur de messages."""
        self.running = False
        self.batch_thread.join(timeout=5)
        
        # Traiter les lots restants
        with self.lock:
            for key, batch in list(self.batches.items()):
                batch_message = self._create_batch_message(batch)
                # L'envoi serait géré par le middleware
                # middleware.send_message(batch_message, batch["channel"])
            self.batches.clear()
```

### 10.2 Mise en cache

La mise en cache est utilisée pour améliorer les performances en stockant temporairement des données fréquemment utilisées, réduisant ainsi la nécessité de recalculer ou de récupérer ces données à chaque fois qu'elles sont nécessaires.

**Stratégies de mise en cache :**

1. **Cache de messages** : Stockage temporaire des messages fréquemment consultés.
2. **Cache de routage** : Mémorisation des décisions de routage pour accélérer les envois répétés.
3. **Cache de résultats** : Stockage des résultats de calculs coûteux.
4. **Cache distribué** : Partage du cache entre plusieurs instances du middleware.
5. **Invalidation intelligente** : Mise à jour sélective du cache lorsque les données sous-jacentes changent.

**Implémentation d'un cache de messages :**

```python
class MessageCache:
    """Cache pour les messages fréquemment utilisés."""
    
    def __init__(self, max_size=1000, ttl=300):
        self.max_size = max_size  # Nombre maximum d'entrées dans le cache
        self.ttl = ttl  # Durée de vie en secondes
        
        # Dictionnaire des messages mis en cache
        self.cache = {}
        
        # File pour l'algorithme LRU (Least Recently Used)
        self.lru_queue = collections.deque()
        
        # Verrou pour les opérations concurrentes
        self.lock = threading.Lock()
        
        # Démarrer le thread de nettoyage
        self.running = True
        self.cleanup_thread = threading.Thread(target=self._cleanup_worker)
        self.cleanup_thread.daemon = True
        self.cleanup_thread.start()
        
        # Statistiques du cache
        self.stats = {
            "hits": 0,
            "misses": 0,
            "inserts": 0,
            "evictions": 0,
            "expirations": 0
        }
    
    def get(self, message_id):
        """Récupère un message du cache."""
        with self.lock:
            # Vérifier si le message est dans le cache
            if message_id in self.cache:
                entry = self.cache[message_id]
                
                # Vérifier si l'entrée a expiré
                if datetime.now() > entry["expires_at"]:
                    # Supprimer l'entrée expirée
                    del self.cache[message_id]
                    self.lru_queue.remove(message_id)
                    self.stats["expirations"] += 1
                    self.stats["misses"] += 1
                    return None
                
                # Mettre à jour la position dans la file LRU
                self.lru_queue.remove(message_id)
                self.lru_queue.append(message_id)
                
                # Incrémenter le compteur de hits
                self.stats["hits"] += 1
                
                return entry["message"]
            
            # Le message n'est pas dans le cache
            self.stats["misses"] += 1
            return None
    
    def put(self, message_id, message):
        """Ajoute un message au cache."""
        with self.lock:
            # Vérifier si le message est déjà dans le cache
            if message_id in self.cache:
                # Mettre à jour l'entrée existante
                self.cache[message_id]["message"] = message
                self.cache[message_id]["expires_at"] = datetime.now() + timedelta(seconds=self.ttl)
                
                # Mettre à jour la position dans la file LRU
                self.lru_queue.remove(message_id)
                self.lru_queue.append(message_id)
            else:
                # Vérifier si le cache est plein
                if len(self.cache) >= self.max_size:
                    # Supprimer l'entrée la moins récemment utilisée
                    oldest_id = self.lru_queue.popleft()
                    del self.cache[oldest_id]
                    self.stats["evictions"] += 1
                
                # Ajouter la nouvelle entrée
                self.cache[message_id] = {
                    "message": message,
                    "added_at": datetime.now(),
                    "expires_at": datetime.now() + timedelta(seconds=self.ttl)
                }
                self.lru_queue.append(message_id)
                self.stats["inserts"] += 1
    
    def invalidate(self, message_id):
        """Invalide une entrée du cache."""
        with self.lock:
            if message_id in self.cache:
                del self.cache[message_id]
                self.lru_queue.remove(message_id)
    
    def clear(self):
        """Vide complètement le cache."""
        with self.lock:
            self.cache.clear()
            self.lru_queue.clear()
    
    def _cleanup_worker(self):
        """Thread qui nettoie périodiquement les entrées expirées."""
        while self.running:
            # Attendre un peu avant le prochain nettoyage
            time.sleep(60)  # Nettoyer toutes les minutes
            
            with self.lock:
                current_time = datetime.now()
                expired_ids = []
                
                # Identifier les entrées expirées
                for message_id, entry in self.cache.items():
                    if current_time > entry["expires_at"]:
                        expired_ids.append(message_id)
                
                # Supprimer les entrées expirées
                for message_id in expired_ids:
                    del self.cache[message_id]
                    self.lru_queue.remove(message_id)
                    self.stats["expirations"] += 1
    
    def get_stats(self):
        """Récupère les statistiques du cache."""
        with self.lock:
            stats = self.stats.copy()
            stats["size"] = len(self.cache)
            stats["max_size"] = self.max_size
            stats["hit_ratio"] = stats["hits"] / (stats["hits"] + stats["misses"]) if (stats["hits"] + stats["misses"]) > 0 else 0
            return stats
    
    def shutdown(self):
        """Arrête proprement le cache."""
        self.running = False
        self.cleanup_thread.join(timeout=5)
```

### 10.3 Traitement asynchrone

Le traitement asynchrone permet d'améliorer les performances en évitant les blocages et en maximisant l'utilisation des ressources. Cette approche est particulièrement adaptée aux systèmes de communication qui doivent gérer de nombreuses opérations d'entrée/sortie.

**Techniques de traitement asynchrone :**

1. **Opérations non bloquantes** : Utilisation d'API asynchrones pour les opérations d'E/S.
2. **Modèle basé sur les événements** : Réaction aux événements plutôt qu'attente active.
3. **Pools de threads** : Distribution du travail entre plusieurs threads.
4. **Traitement par lots** : Regroupement des opérations similaires pour un traitement efficace.
5. **Pipelines de traitement** : Division du travail en étapes qui peuvent s'exécuter en parallèle.

**Implémentation d'un gestionnaire de messages asynchrone :**

```python
class AsyncMessageHandler:
    """Gestionnaire de messages asynchrone pour le traitement parallèle."""
    
    def __init__(self, middleware, num_workers=10, queue_size=1000):
        self.middleware = middleware
        self.num_workers = num_workers
        
        # File d'attente des messages à traiter
        self.message_queue = asyncio.Queue(maxsize=queue_size)
        
        # Tâches de travail
        self.worker_tasks = []
        
        # État du gestionnaire
        self.running = False
        
        # Statistiques
        self.stats = {
            "messages_processed": 0,
            "messages_queued": 0,
            "processing_errors": 0,
            "avg_processing_time": 0
        }
    
    async def start(self):
        """Démarre le gestionnaire de messages."""
        if self.running:
            return
        
        self.running = True
        
        # Créer les tâches de travail
        self.worker_tasks = [
            asyncio.create_task(self._worker(i))
            for i in range(self.num_workers)
        ]
    
    async def stop(self):
        """Arrête le gestionnaire de messages."""
        if not self.running:
            return
        
        self.running = False
        
        # Attendre que toutes les tâches se terminent
        if self.worker_tasks:
            await asyncio.gather(*self.worker_tasks, return_exceptions=True)
            self.worker_tasks = []
    
    async def enqueue_message(self, message, handler):
        """Ajoute un message à la file d'attente pour traitement."""
        if not self.running:
            raise RuntimeError("AsyncMessageHandler is not running")
        
        # Ajouter le message et son gestionnaire à la file d'attente
        await self.message_queue.put({
            "message": message,
            "handler": handler,
            "enqueued_at": datetime.now()
        })
        
        self.stats["messages_queued"] += 1
    
    async def _worker(self, worker_id):
        """Tâche de travail qui traite les messages de la file d'attente."""
        while self.running:
            try:
                # Récupérer un message de la file d'attente
                item = await self.message_queue.get()
                
                message = item["message"]
                handler = item["handler"]
                enqueued_at = item["enqueued_at"]
                
                # Mesurer le temps de traitement
                start_time = datetime.now()
                
                try:
                    # Traiter le message
                    await handler(message)
                    
                    # Mettre à jour les statistiques
                    self.stats["messages_processed"] += 1
                    
                    # Calculer le temps de traitement
                    processing_time = (datetime.now() - start_time).total_seconds()
                    
                    # Mettre à jour le temps de traitement moyen
                    n = self.stats["messages_processed"]
                    avg = self.stats["avg_processing_time"]
                    self.stats["avg_processing_time"] = (avg * (n - 1) + processing_time) / n
                    
                except Exception as e:
                    # Journaliser l'erreur
                    self.middleware.logger.error(f"Error processing message {message.get('id')}: {str(e)}")
                    
                    # Mettre à jour les statistiques
                    self.stats["processing_errors"] += 1
                
                finally:
                    # Marquer la tâche comme terminée
                    self.message_queue.task_done()
            
            except asyncio.CancelledError:
                # La tâche a été annulée
                break
            
            except Exception as e:
                # Erreur inattendue dans le worker
                self.middleware.logger.error(f"Unexpected error in worker {worker_id}: {str(e)}")
                
                # Petite pause pour éviter une boucle d'erreurs trop rapide
                await asyncio.sleep(0.1)
    
    def get_stats(self):
        """Récupère les statistiques du gestionnaire."""
        stats = self.stats.copy()
        stats["queue_size"] = self.message_queue.qsize()
        stats["queue_capacity"] = self.message_queue.maxsize
        stats["active_workers"] = len(self.worker_tasks)
        return stats
```

### 10.4 Métriques et surveillance

Un système complet de métriques et de surveillance est mis en place pour suivre les performances du système de communication, détecter les problèmes et optimiser le fonctionnement.

**Types de métriques collectées :**

1. **Métriques de volume** : Nombre de messages envoyés/reçus par canal, agent, type, etc.
2. **Métriques de latence** : Temps de traitement, de transmission et de réponse.
3. **Métriques de ressources** : Utilisation du CPU, de la mémoire, du réseau, etc.
4. **Métriques de qualité** : Taux d'erreur, taux de réessai, taux de succès, etc.
5. **Métriques de disponibilité** : Temps de fonctionnement, temps de réponse, etc.

**Implémentation du système de métriques :**

```python
class MetricsCollector:
    """Collecte et expose des métriques sur le système de communication."""
    
    def __init__(self, collection_interval=60):
        self.collection_interval = collection_interval  # Intervalle en secondes
        
        # Métriques de base
        self.metrics = {
            "messages": {
                "sent": 0,
                "received": 0,
                "errors": 0,
                "by_channel": {},
                "by_type": {},
                "by_priority": {}
self.metrics[category][metric] = value
    
    def _collector_worker(self):
        """Thread qui collecte périodiquement les métriques système."""
        while self.running:
            try:
                # Collecter les métriques système
                self._collect_system_metrics()
                
                # Enregistrer un instantané des métriques actuelles
                with self.lock:
                    snapshot = {
                        "timestamp": datetime.now().isoformat(),
                        "metrics": copy.deepcopy(self.metrics)
                    }
                    self.metrics_history.append(snapshot)
                    
                    # Limiter la taille de l'historique
                    if len(self.metrics_history) > 1440:  # 24 heures à raison d'un instantané par minute
                        self.metrics_history.pop(0)
                
                # Attendre jusqu'au prochain intervalle de collecte
                time.sleep(self.collection_interval)
                
            except Exception as e:
                print(f"Error in metrics collector: {str(e)}")
                time.sleep(5)  # Attendre un peu en cas d'erreur
    
    def _collect_system_metrics(self):
        """Collecte les métriques système."""
        try:
            # Mettre à jour le temps de fonctionnement
            uptime = (datetime.now() - self.start_time).total_seconds()
            with self.lock:
                self.metrics["availability"]["uptime"] = uptime
            
            # Collecter l'utilisation du CPU et de la mémoire
            # (implémentation simplifiée pour l'exemple)
            cpu_usage = psutil.cpu_percent(interval=1)
            memory_usage = psutil.virtual_memory().percent
            
            with self.lock:
                self.metrics["resources"]["cpu_usage"] = cpu_usage
                self.metrics["resources"]["memory_usage"] = memory_usage
                
        except Exception as e:
            print(f"Error collecting system metrics: {str(e)}")
    
    def get_current_metrics(self):
        """Récupère les métriques actuelles."""
        with self.lock:
            return copy.deepcopy(self.metrics)
    
    def get_metrics_history(self, start_time=None, end_time=None):
        """Récupère l'historique des métriques dans une plage de temps."""
        with self.lock:
            if not start_time and not end_time:
                return copy.deepcopy(self.metrics_history)
            
            filtered_history = []
            for snapshot in self.metrics_history:
                timestamp = snapshot["timestamp"]
                if (not start_time or timestamp >= start_time) and (not end_time or timestamp <= end_time):
                    filtered_history.append(copy.deepcopy(snapshot))
            
            return filtered_history
    
    def shutdown(self):
        """Arrête proprement le collecteur de métriques."""
        self.running = False
        self.collector_thread.join(timeout=5)
```

## 11. Plan d'Implémentation

### 11.1 Phases de développement

L'implémentation du système de communication multi-canal sera réalisée en plusieurs phases, permettant une approche incrémentale et la validation progressive des fonctionnalités.

**Phase 1 : Fondations (2 mois)**

1. **Conception détaillée** :
   - Finalisation des spécifications techniques
   - Définition des interfaces et contrats
   - Conception des structures de données

2. **Middleware de base** :
   - Implémentation du noyau du middleware
   - Développement du gestionnaire de canaux
   - Création des mécanismes de routage de base

3. **Canaux essentiels** :
   - Implémentation du canal hiérarchique
   - Implémentation du canal de données
   - Tests unitaires des canaux

4. **Adaptateurs de base** :
   - Développement des adaptateurs pour les trois niveaux d'agents
   - Tests d'intégration avec les agents existants

**Phase 2 : Fonctionnalités avancées (2 mois)**

1. **Canaux supplémentaires** :
   - Implémentation du canal de collaboration
   - Implémentation du canal de négociation
   - Implémentation du canal de feedback

2. **Protocoles de communication** :
   - Développement du protocole de requête-réponse
   - Développement du protocole de publication-abonnement
   - Développement du protocole de négociation
   - Développement du protocole de coordination

3. **Mécanismes de routage avancés** :
   - Implémentation du routage basé sur le contenu
   - Développement des mécanismes de filtrage et priorisation
   - Tests de performance du routage

4. **Optimisations initiales** :
   - Implémentation de la compression des messages
   - Développement du batching de messages
   - Tests de performance

**Phase 3 : Résilience et monitoring (1,5 mois)**

1. **Gestion des erreurs** :
   - Implémentation du système de détection d'erreurs
   - Développement des stratégies de récupération
   - Tests de résilience

2. **Mécanismes de reprise** :
   - Implémentation de la persistance des messages
   - Développement des mécanismes de rejeu
   - Tests de récupération après panne

3. **Système de métriques** :
   - Implémentation du collecteur de métriques
   - Développement des tableaux de bord de monitoring
   - Tests de charge et benchmarking

4. **Journalisation et audit** :
   - Implémentation du système de journalisation
   - Développement des mécanismes d'audit
   - Tests de conformité

**Phase 4 : Optimisation et finalisation (1,5 mois)**

1. **Optimisations avancées** :
   - Implémentation du traitement asynchrone
   - Développement des mécanismes de mise en cache
   - Optimisation des performances globales

2. **Sécurité** :
   - Implémentation de l'authentification et autorisation
   - Développement du chiffrement des messages
   - Tests de sécurité

3. **Documentation et formation** :
   - Finalisation de la documentation technique
   - Création de guides d'utilisation
   - Formation des équipes de développement

4. **Déploiement et validation finale** :
   - Déploiement en environnement de pré-production
   - Tests d'acceptation utilisateur
   - Correction des derniers bugs

### 11.2 Stratégie de migration

La migration depuis le système de communication actuel vers le nouveau système multi-canal sera réalisée de manière progressive pour minimiser les perturbations et les risques.

**Approche de migration :**

1. **Analyse de l'existant** :
   - Cartographie complète du système actuel
   - Identification des points d'intégration
   - Analyse des dépendances

2. **Développement d'adaptateurs de compatibilité** :
   - Création d'adaptateurs pour les interfaces existantes
   - Implémentation de wrappers pour les agents actuels
   - Tests de compatibilité

3. **Migration par composant** :
   - Migration progressive des composants un par un
   - Validation de chaque composant migré
   - Possibilité de rollback en cas de problème

4. **Période de coexistence** :
   - Fonctionnement en parallèle des deux systèmes
   - Routage sélectif des messages
   - Comparaison des performances et résultats

5. **Basculement complet** :
   - Transfert de toutes les communications vers le nouveau système
   - Désactivation progressive de l'ancien système
   - Surveillance renforcée pendant la période de transition

**Plan de migration détaillé :**

1. **Phase préparatoire (2 semaines)** :
   - Analyse détaillée du système actuel
   - Définition des critères de succès de la migration
   - Préparation des environnements de test

2. **Développement des adaptateurs (3 semaines)** :
   - Création des adaptateurs pour les interfaces stratégique-tactique
   - Développement des adaptateurs pour les interfaces tactique-opérationnelle
   - Tests d'intégration avec les agents existants

3. **Migration du niveau stratégique (2 semaines)** :
   - Migration des agents stratégiques vers le nouveau système
   - Validation du fonctionnement avec les niveaux inférieurs
   - Période d'observation et ajustements

4. **Migration du niveau tactique (2 semaines)** :
   - Migration des agents tactiques vers le nouveau système
   - Validation du fonctionnement avec les niveaux supérieur et inférieur
   - Période d'observation et ajustements

5. **Migration du niveau opérationnel (3 semaines)** :
   - Migration progressive des agents opérationnels
   - Tests de fonctionnement de bout en bout
   - Validation des performances

6. **Période de coexistence (2 semaines)** :
   - Fonctionnement en parallèle des deux systèmes
   - Analyse comparative des performances
   - Correction des problèmes identifiés

7. **Basculement final (1 semaine)** :
   - Transfert de toutes les communications vers le nouveau système
   - Désactivation de l'ancien système
   - Surveillance intensive et support renforcé

### 11.3 Tests et validation

Une stratégie de test complète sera mise en œuvre pour assurer la qualité, la fiabilité et les performances du nouveau système de communication.

**Niveaux de tests :**

1. **Tests unitaires** :
   - Tests des composants individuels
   - Validation des fonctionnalités isolées
   - Couverture de code > 80%

2. **Tests d'intégration** :
   - Tests des interactions entre composants
   - Validation des interfaces
   - Tests des flux de communication

3. **Tests de performance** :
   - Benchmarks de débit et latence
   - Tests de charge
   - Tests de scalabilité

4. **Tests de résilience** :
   - Tests de récupération après panne
   - Simulation de défaillances
   - Tests de dégradation gracieuse

5. **Tests de sécurité** :
   - Tests de pénétration
   - Analyse de vulnérabilités
   - Validation des mécanismes de sécurité

6. **Tests d'acceptation** :
   - Validation des cas d'utilisation métier
   - Tests de bout en bout
   - Validation par les utilisateurs finaux

**Environnements de test :**

1. **Environnement de développement** :
   - Tests unitaires et d'intégration de base
   - Validation rapide des fonctionnalités
   - Exécution automatisée à chaque commit

2. **Environnement de test dédié** :
   - Tests d'intégration complets
   - Tests de performance
   - Tests de résilience

3. **Environnement de pré-production** :
   - Configuration identique à la production
   - Tests de charge réalistes
   - Validation finale avant déploiement

4. **Environnement de production surveillé** :
   - Déploiement progressif
   - Surveillance renforcée
   - Capacité de rollback rapide

**Outils et méthodologies :**

1. **Intégration continue** :
   - Exécution automatique des tests à chaque commit
   - Vérification de la qualité du code
   - Génération de rapports de couverture

2. **Tests automatisés** :
   - Framework de test pour chaque niveau
   - Scripts de test automatisés
   - Tests de non-régression

3. **Monitoring de test** :
   - Collecte de métriques pendant les tests
   - Analyse des performances
   - Détection des régressions

4. **Validation continue** :
   - Tests de non-régression réguliers
   - Validation des performances dans le temps
   - Surveillance des métriques clés

## 12. Conclusion

### 12.1 Avantages du nouveau système

Le système de communication multi-canal conçu dans ce document apporte de nombreux avantages par rapport au système actuel, répondant aux limitations identifiées et offrant de nouvelles capacités.

**Avantages principaux :**

1. **Communication bidirectionnelle riche** :
   - Flux d'information fluide dans les deux sens entre tous les niveaux
   - Mécanismes de feedback permettant l'amélioration continue
   - Communication contextuelle adaptée aux besoins spécifiques

2. **Communication horizontale efficace** :
   - Collaboration directe entre agents de même niveau
   - Partage de connaissances et d'expériences
   - Résolution collaborative des problèmes

3. **Flexibilité et extensibilité** :
   - Architecture modulaire facilitant l'ajout de nouveaux canaux
   - Support de différents protocoles de communication
   - Adaptateurs permettant l'intégration facile de nouveaux agents

4. **Performance et scalabilité** :
   - Optimisations pour gérer un grand nombre d'agents
   - Mécanismes de mise en cache et de traitement asynchrone
   - Distribution efficace des messages

5. **Résilience et fiabilité** :
   - Détection et gestion robuste des erreurs
   - Mécanismes de récupération automatique
   - Persistance des messages critiques

6. **Observabilité complète** :
   - Métriques détaillées sur tous les aspects du système
   - Journalisation structurée pour le débogage
   - Piste d'audit pour les opérations sensibles

7. **Sécurité intégrée** :
   - Authentification et autorisation des communications
   - Chiffrement des messages sensibles
   - Validation des messages pour prévenir les attaques

8. **Adaptabilité contextuelle** :
   - Canaux spécialisés pour différents types d'interactions
   - Protocoles adaptés aux besoins spécifiques
   - Priorisation intelligente des messages

### 12.2 Perspectives d'évolution

Le système de communication multi-canal a été conçu pour évoluer et s'adapter aux besoins futurs. Plusieurs axes d'évolution peuvent être envisagés.

**Évolutions à court terme :**

1. **Intégration avec d'autres systèmes** :
   - Connecteurs pour des systèmes de messagerie externes
   - Passerelles vers d'autres frameworks d'agents
   - APIs pour l'intégration avec des applications tierces

2. **Canaux spécialisés supplémentaires** :
   - Canal de diagnostic pour le débogage avancé
   - Canal d'apprentissage pour le partage de connaissances
   - Canal de coordination temporelle pour les opérations synchronisées

3. **Optimisations de performance** :
   - Algorithmes de routage plus sophistiqués
   - Compression adaptative des messages
   - Mécanismes de mise en cache distribués

**Évolutions à moyen terme :**

1. **Intelligence dans la communication** :
   - Routage adaptatif basé sur l'apprentissage
   - Priorisation contextuelle intelligente
   - Détection automatique des patterns de communication

2. **Fédération de systèmes de communication** :
   - Communication entre plusieurs instances du middleware
   - Synchronisation distribuée des états
   - Routage inter-systèmes

3. **Visualisation avancée** :
   - Représentation graphique des flux de communication
   - Tableaux de bord interactifs pour le monitoring
   - Outils de diagnostic visuel

**Évolutions à long terme :**

1. **Communication auto-organisée** :
   - Topologie de communication auto-adaptative
   - Optimisation autonome des paramètres
   - Auto-réparation en cas de défaillance

2. **Intégration de technologies émergentes** :
   - Support de nouveaux paradigmes de communication
   - Intégration avec des systèmes de calcul quantique
   - Utilisation de techniques d'IA pour l'optimisation

3. **Standardisation et interopérabilité** :
   - Contribution à des standards ouverts
   - Interopérabilité avec d'autres frameworks d'agents
   - Écosystème d'extensions et de plugins

Le système de communication multi-canal constitue une fondation solide pour l'évolution future du système d'analyse rhétorique, offrant la flexibilité et l'extensibilité nécessaires pour s'adapter à des besoins changeants et intégrer de nouvelles technologies.
            },
            "latency": {
                "avg_processing": 0,
                "avg_transmission": 0,
                "avg_end_to_end": 0,
                "p95_processing": 0,
                "p95_transmission": 0,
                "p95_end_to_end": 0
            },
            "resources": {
                "cpu_usage": 0,
                "memory_usage": 0,
                "queue_sizes": {}
            },
            "quality": {
                "error_rate": 0,
                "retry_rate": 0,
                "success_rate": 1.0
            },
            "availability": {
                "uptime": 0,
                "response_rate": 1.0
            }
        }
        
        # Historique des métriques pour l'analyse des tendances
        self.metrics_history = []
        
        # Horodatage de démarrage
        self.start_time = datetime.now()
        
        # Verrou pour les opérations concurrentes
        self.lock = threading.Lock()
        
        # Démarrer le thread de collecte
        self.running = True
        self.collector_thread = threading.Thread(target=self._collector_worker)
        self.collector_thread.daemon = True
        self.collector_thread.start()
    
    def record_message_sent(self, message, channel):
        """Enregistre un message envoyé."""
        with self.lock:
            # Incrémenter le compteur global
            self.metrics["messages"]["sent"] += 1
            
            # Mettre à jour les compteurs par canal
            if channel not in self.metrics["messages"]["by_channel"]:
                self.metrics["messages"]["by_channel"][channel] = {"sent": 0, "received": 0}
            self.metrics["messages"]["by_channel"][channel]["sent"] += 1
            
            # Mettre à jour les compteurs par type
            message_type = message.get("type", "unknown")
            if message_type not in self.metrics["messages"]["by_type"]:
                self.metrics["messages"]["by_type"][message_type] = 0
            self.metrics["messages"]["by_type"][message_type] += 1
            
            # Mettre à jour les compteurs par priorité
            priority = message.get("priority", "normal")
            if priority not in self.metrics["messages"]["by_priority"]:
                self.metrics["messages"]["by_priority"][priority] = 0
            self.metrics["messages"]["by_priority"][priority] += 1
    
    def record_message_received(self, message, channel):
        """Enregistre un message reçu."""
        with self.lock:
            # Incrémenter le compteur global
            self.metrics["messages"]["received"] += 1
            
            # Mettre à jour les compteurs par canal
            if channel not in self.metrics["messages"]["by_channel"]:
                self.metrics["messages"]["by_channel"][channel] = {"sent": 0, "received": 0}
            self.metrics["messages"]["by_channel"][channel]["received"] += 1
    
    def record_error(self, error_type):
        """Enregistre une erreur."""
        with self.lock:
            # Incrémenter le compteur d'erreurs
            self.metrics["messages"]["errors"] += 1
            
            # Mettre à jour le taux d'erreur
            total_messages = self.metrics["messages"]["sent"] + self.metrics["messages"]["received"]
            if total_messages > 0:
                self.metrics["quality"]["error_rate"] = self.metrics["messages"]["errors"] / total_messages
                self.metrics["quality"]["success_rate"] = 1.0 - self.metrics["quality"]["error_rate"]
    
    def record_latency(self, latency_type, value):
        """Enregistre une mesure de latence."""
        with self.lock:
            # Mettre à jour la latence moyenne
            if latency_type == "processing":
                self._update_average("latency", "avg_processing", value)
            elif latency_type == "transmission":
                self._update_average("latency", "avg_transmission", value)
            elif latency_type == "end_to_end":
                self._update_average("latency", "avg_end_to_end", value)
    
    def record_resource_usage(self, resource_type, value):
        """Enregistre une mesure d'utilisation des ressources."""
        with self.lock:
            if resource_type == "cpu":
                self.metrics["resources"]["cpu_usage"] = value
            elif resource_type == "memory":
                self.metrics["resources"]["memory_usage"] = value
            elif resource_type.startswith("queue_"):
                queue_name = resource_type[6:]  # Supprimer le préfixe "queue_"
                self.metrics["resources"]["queue_sizes"][queue_name] = value
    
    def _update_average(self, category, metric, value):
        """Met à jour une métrique de moyenne."""
        current = self.metrics[category][metric]
        count = self.metrics["messages"]["sent"] + self.metrics["messages"]["received"]
        
        if count > 1:
            # Formule de mise à jour incrémentale de la moyenne
            self.metrics[category][metric] = current + (value - current) / count
        else:
                        middleware.send_message(message, channel)
                        replayed_count += 1
                    except Exception as e:
                        self.logger.error(f"Error replaying message: {str(e)}")
                
                # Archiver le fichier après traitement
                archive_path = os.path.join(self.storage_path, "archived")
                os.makedirs(archive_path, exist_ok=True)
                shutil.move(filepath, os.path.join(archive_path, filename))
                
            except Exception as e:
                self.logger.error(f"Error processing message file {filename}: {str(e)}")
        
        return replayed_count
    
    def _should_persist(self, message):
        """Détermine si un message doit être persisté."""
        # Persister les messages critiques ou à haute priorité
        if message.get("priority") in ["critical", "high"]:
            return True
        
        # Persister les messages explicitement marqués comme persistants
        if message.get("metadata", {}).get("persistent", False):
            return True
        
        # Persister les messages de certains types
        if message.get("type") in ["command", "event"]:
            return True
        
        return False
    
    def shutdown(self):
        """Arrête proprement le gestionnaire de persistance."""
        self.running = False
        self.persistence_thread.join(timeout=5)
        
        # Persister les messages restants
        with self.lock:
            if self.pending_messages:
                self._write_batch(self.pending_messages)
                self.pending_messages = []
```

### 9.4 Journalisation et audit

Le système de journalisation et d'audit enregistre toutes les opérations importantes pour permettre le débogage, l'analyse des performances et la conformité réglementaire. Ce système fournit une trace complète des activités du système de communication.

**Fonctionnalités principales :**

1. **Journalisation structurée** : Enregistrement des événements dans un format structuré.
2. **Niveaux de détail configurables** : Contrôle de la verbosité des journaux.
3. **Rotation des journaux** : Gestion automatique de la taille et de l'archivage des journaux.
4. **Filtrage contextuel** : Sélection des événements à journaliser en fonction du contexte.
5. **Piste d'audit** : Enregistrement immuable des opérations sensibles.

**Implémentation du système de journalisation :**

```python
class CommunicationLogger:
    """Système de journalisation pour le système de communication multi-canal."""
    
    # Niveaux de journalisation
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50
    
    def __init__(self, log_level=INFO, log_file=None, max_file_size=10*1024*1024, backup_count=5):
        self.log_level = log_level
        self.log_file = log_file
        
        # Configuration des gestionnaires de journaux
        self.handlers = []
        
        # Gestionnaire de console
        console_handler = logging.StreamHandler()
        console_handler.setLevel(self.log_level)
        console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(console_formatter)
        self.handlers.append(console_handler)
        
        # Gestionnaire de fichier si spécifié
        if log_file:
            file_handler = logging.handlers.RotatingFileHandler(
                log_file, maxBytes=max_file_size, backupCount=backup_count
            )
            file_handler.setLevel(self.log_level)
            file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(file_formatter)
            self.handlers.append(file_handler)
        
        # Configurer le logger racine
        self.logger = logging.getLogger("multichannel_comms")
        self.logger.setLevel(self.log_level)
        
        for handler in self.handlers:
            self.logger.addHandler(handler)
        
        # Journal d'audit séparé
        self.audit_log = []
    
    def log_message(self, message, direction, channel=None, is_error=False):
        """Journalise un message envoyé ou reçu."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "message_id": message.get("id"),
            "direction": direction,  # "sent" ou "received"
            "channel": channel,
            "sender": message.get("sender"),
            True si succès, False sinon
        """
        pass
    
    def create_channel(self, channel_type, config=None):
        """
        Crée un nouveau canal.
        
        Args:
            channel_type: Le type de canal à créer
            config: Configuration du canal
            
        Returns:
            Un identifiant de canal
        """
        pass
    
    def get_channel_info(self, channel_type):
        """
        Récupère des informations sur un canal.
        
        Args:
            channel_type: Le type de canal
            
        Returns:
            Un dictionnaire d'informations sur le canal
        """
        pass
    
    def get_statistics(self):
        """
        Récupère des statistiques sur le middleware.
        
        Returns:
            Un dictionnaire de statistiques
        """
        pass
    
    def register_error_handler(self, handler):
        """
        Enregistre un gestionnaire d'erreurs.
        
        Args:
            handler: Fonction de gestion des erreurs
            
        Returns:
            Un identifiant de gestionnaire
        """
        pass
```

### 8.2 Interface des adaptateurs

L'interface des adaptateurs définit comment les agents interagissent avec le système de communication via leurs adaptateurs spécifiques. Cette interface simplifie l'utilisation du middleware en exposant des méthodes adaptées au niveau et au rôle de chaque agent.

**Interfaces communes :**

```python
class BaseAdapterInterface:
    """Interface de base pour tous les adaptateurs d'agents."""
    
    def send(self, message_type, content, recipient=None, metadata=None, priority="normal"):
        """
        Envoie un message.
        
        Args:
            message_type: Type de message
            content: Contenu du message
            recipient: Destinataire (optionnel)
            metadata: Métadonnées (optionnel)
            priority: Priorité du message
            
        Returns:
            Un identifiant de message
        """
        pass
    
    def receive(self, filter_criteria=None, timeout=None):
        """
        Reçoit un message.
        
        Args:
            filter_criteria: Critères de filtrage
            timeout: Délai d'attente maximum
            
        Returns:
            Le message reçu ou None si timeout
        """
        pass
    
    def subscribe(self, message_types=None, callback=None, filter_criteria=None):
        """
        S'abonne à des types de messages.
        
        Args:
            message_types: Types de messages
            callback: Fonction de rappel
            filter_criteria: Critères de filtrage
            
        Returns:
            Un identifiant d'abonnement
        """
        pass
    
    def unsubscribe(self, subscription_id):
        """
        Annule un abonnement.
        
        Args:
            subscription_id: Identifiant d'abonnement
            
        Returns:
            True si succès, False sinon
        """
        pass
```

**Interfaces spécifiques par niveau :**

```python
class StrategicAdapterInterface(BaseAdapterInterface):
    """Interface pour les adaptateurs d'agents stratégiques."""
    
    def issue_directive(self, directive, recipients=None, priority="high"):
        """
        Émet une directive stratégique.
        
        Args:
            directive: Contenu de la directive
            recipients: Liste des destinataires tactiques
            priority: Priorité de la directive
            
        Returns:
            Un identifiant de directive
        """
        pass
    
    def receive_report(self, timeout=None):
        """
        Reçoit un rapport tactique.
        
        Args:
            timeout: Délai d'attente maximum
            
        Returns:
            Le rapport reçu ou None si timeout
        """
        pass
    
    def broadcast_objective(self, objective, priority="high"):
        """
        Diffuse un objectif global.
        
        Args:
            objective: Contenu de l'objectif
            priority: Priorité de l'objectif
            
        Returns:
            Un identifiant d'objectif
        """
        pass

class TacticalAdapterInterface(BaseAdapterInterface):
    """Interface pour les adaptateurs d'agents tactiques."""
    
    def assign_task(self, task, recipient, priority="normal"):
        """
        Assigne une tâche à un agent opérationnel.
        
        Args:
            task: Contenu de la tâche
            recipient: Destinataire opérationnel
            priority: Priorité de la tâche
            
        Returns:
            Un identifiant de tâche
        """
        pass
    
    def receive_directive(self, timeout=None):
        """
        Reçoit une directive stratégique.
        
        Args:
            timeout: Délai d'attente maximum
            
        Returns:
            La directive reçue ou None si timeout
        """
        pass
    
    def send_report(self, report, recipient, priority="normal"):
        """
        Envoie un rapport à un agent stratégique.
        
        Args:
            report: Contenu du rapport
            recipient: Destinataire stratégique
            priority: Priorité du rapport
            
        Returns:
            Un identifiant de rapport
        """
        pass
    
    def collaborate(self, request, recipients, priority="normal"):
        """
        Initie une collaboration avec d'autres agents tactiques.
        
        Args:
            request: Contenu de la demande de collaboration
            recipients: Liste des destinataires tactiques
            priority: Priorité de la demande
            
        Returns:
            Un identifiant de collaboration
        """
        pass

class OperationalAdapterInterface(BaseAdapterInterface):
    """Interface pour les adaptateurs d'agents opérationnels."""
    
    def receive_task(self, timeout=None):
        """
        Reçoit une tâche tactique.
        
        Args:
            timeout: Délai d'attente maximum
            
        Returns:
            La tâche reçue ou None si timeout
        """
        pass
    
    def send_result(self, result, recipient, priority="normal"):
        """
        Envoie un résultat à un agent tactique.
          "description": "Identifiant du message auquel celui-ci répond"
        },
        "ttl": {
          "type": "number",
          "minimum": 0,
          "description": "Durée de vie en secondes"
        },
        "encryption": {
          "type": "string",
          "enum": ["none", "aes256", "rsa2048"],
          "default": "none",
          "description": "Type de chiffrement"
        },
        "compression": {
          "type": "string",
          "enum": ["none", "gzip", "zlib"],
          "default": "none",
          "description": "Type de compression"
        },
        "requires_ack": {
          "type": "boolean",
          "default": false,
          "description": "Indique si un accusé de réception est requis"
        }
      }
    },
    "timestamp": {
      "type": "string",
      "format": "date-time",
      "description": "Horodatage ISO 8601"
    }
  }
}
```

Des schémas spécifiques sont définis pour chaque type de message, étendant ce schéma de base avec des contraintes supplémentaires sur le contenu et les métadonnées.

Le système de validation des messages est implémenté à plusieurs niveaux :

1. **Validation côté émetteur** : Les adaptateurs d'agents valident les messages avant de les envoyer.
2. **Validation par le middleware** : Le middleware valide tous les messages entrants.
3. **Validation côté récepteur** : Les adaptateurs valident les messages reçus avant de les transmettre aux agents.

Cette approche multi-niveaux garantit la robustesse du système face à des messages mal formés ou invalides.