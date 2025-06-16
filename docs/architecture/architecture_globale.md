# Architecture Globale du Système d'Analyse Argumentative

Ce document décrit l'architecture globale du système d'analyse argumentative, en mettant en évidence les principaux composants et leurs interactions. Il vise à refléter l'état actuel du projet tout en considérant les évolutions proposées.

## Vue d'ensemble

Le projet est construit autour d'une architecture multi-agents où différents agents spécialisés collaborent pour analyser des textes argumentatifs. Cette architecture modulaire permet une séparation claire des responsabilités et facilite l'extension du système avec de nouveaux agents ou fonctionnalités.

L'objectif principal est de fournir une plateforme robuste et flexible pour l'analyse rhétorique, combinant les capacités des Grands Modèles de Langage (LLMs) avec la rigueur des approches d'Intelligence Artificielle symbolique.

## Diagramme d'Architecture

Le diagramme suivant illustre les principaux composants du système et leurs relations. (Note: Ce diagramme est une représentation de haut niveau, le flux d'orchestration précis peut varier).

```mermaid
graph TD
    UI[Interface Utilisateur] --> ORCH{Orchestration / Agent PM};
    ORCH --> EXTRACT[Agent Extract];
    ORCH --> INFORMAL[Agent Informal];
    ORCH --> LOGIC[Agents Logiques];
    
    EXTRACT --> SHARED_STATE[(État Partagé)];
    INFORMAL --> SHARED_STATE;
    LOGIC --> SHARED_STATE;
    
    SHARED_STATE --> EXTRACT;
    SHARED_STATE --> INFORMAL;
    SHARED_STATE --> LOGIC;
    SHARED_STATE --> ORCH;

    LOGIC --> JVM[JVM (Tweety)];
    EXTRACT --> LLM[LLM Service];
    INFORMAL --> LLM;
    LOGIC --> LLM;
    ORCH --> LLM;

    subgraph Agents Spécialisés
        direction LR
        EXTRACT;
        INFORMAL;
        LOGIC;
    end

    subgraph Services Externes
        direction LR
        LLM;
        JVM;
        OTHERS[Autres Services];
    end
    
    style ORCH fill:#f9f,stroke:#333,stroke-width:2px
    style SHARED_STATE fill:#ccf,stroke:#333,stroke-width:2px
```

## Composants Principaux

-   **Interface Utilisateur (UI)** : Permet aux utilisateurs de soumettre des textes pour analyse, de configurer les paramètres et de visualiser les résultats. Elle peut prendre la forme d'une application web, d'un notebook Jupyter ou d'une interface en ligne de commande.

-   **Orchestration** : Le cœur du système qui gère le flux de travail de l'analyse.
    *   Le fichier [`argumentation_analysis/core/orchestration_service.py`](../../argumentation_analysis/core/orchestration_service.py) (décrivant un service d'orchestration centralisé) est **actuellement manquant** dans le code source.
    *   L'orchestration actuelle pourrait être gérée par des scripts spécifiques ou s'appuyer davantage sur l'Agent Project Manager pour la définition et la séquence des tâches.
    *   L'**Agent Project Manager (PM)** ([`argumentation_analysis/agents/core/pm/README.md`](../../argumentation_analysis/agents/core/pm/README.md:1)) joue un rôle clé dans la planification stratégique, la définition des tâches pour les autres agents et la synthèse finale. Il ne gère pas directement l'état ou l'exécution mais fournit l'intelligence pour guider le flux.
    *   Une architecture d'orchestration hiérarchique plus formelle est une proposition et est détaillée dans le document ([`analyse_architecture_orchestration.md`](./analyse_architecture_orchestration.md:0)).

-   **Agents Spécialisés** : Chaque agent est responsable d'une tâche spécifique dans le processus d'analyse. Ils héritent de classes de base définies dans [`argumentation_analysis/agents/core/abc/agent_bases.py`](../../argumentation_analysis/agents/core/abc/agent_bases.py:1).
    -   **Agent Extract** ([`argumentation_analysis/agents/core/extract/README.md`](../../argumentation_analysis/agents/core/extract/README.md:1)): Identifie et extrait les arguments, les prémisses et les conclusions du texte source.
    -   **Agent Informal** ([`argumentation_analysis/agents/core/informal/README.md`](../../argumentation_analysis/agents/core/informal/README.md:1)): Analyse les arguments extraits pour détecter les sophismes, évaluer la pertinence et la force des arguments d'un point de vue informel.
    -   **Agents Logiques** ([`argumentation_analysis/agents/core/logic/README.md`](../../argumentation_analysis/agents/core/logic/README.md:1)): Formalisent les arguments dans différentes logiques (propositionnelle, premier ordre, modale) et utilisent des solveurs logiques (par exemple, via Tweety) pour vérifier la validité, la cohérence et d'autres propriétés formelles.
    -   D'autres agents peuvent être ajoutés pour des analyses plus spécifiques.

-   **État Partagé** ([`argumentation_analysis/core/shared_state.py`](../../argumentation_analysis/core/shared_state.py:1)): Un composant central où les informations et les résultats intermédiaires produits par les agents sont stockés et accessibles. Cela permet aux agents de travailler de manière asynchrone et de s'appuyer sur les résultats des autres. Le fichier [`RhetoricalAnalysisState`](../../argumentation_analysis/core/shared_state.py:12) (alias `SharedState`) en est l'implémentation principale.

-   **Communication et Middleware** :
    -   Le système dispose d'un **MessageMiddleware** ([`argumentation_analysis/core/communication/middleware.py`](../../argumentation_analysis/core/communication/middleware.py:1)) conçu pour gérer la communication entre les agents à travers différents canaux spécialisés.
    -   Ce middleware fournit une infrastructure pour l'envoi et la réception de messages, le routage, et supporte des protocoles comme requête-réponse et publication-abonnement.
    -   Son intégration et son rôle exact dans le flux d'orchestration actuel ne sont pas explicitement définis en l'absence d'un `orchestration_service.py` centralisé, mais il constitue la base pour la communication inter-agents.
    -   Plus de détails sur la communication sont disponibles dans ([`communication_agents.md`](./communication_agents.md:0)).

-   **Services Externes** :
    -   **LLM Service** : Fournit l'accès aux Grands Modèles de Langage (par exemple, GPT, Claude) pour des tâches telles que la compréhension du langage naturel, la génération de texte et l'assistance à l'analyse.
    -   **JVM (Tweety)** : Intègre les bibliothèques de logique symbolique de TweetyProject pour l'analyse formelle des arguments, utilisée par les Agents Logiques.
    -   **Autres Services** : Peuvent inclure des bases de données, des services de cryptographie, des outils de visualisation, etc. (Actuellement, pas d'autres services externes majeurs identifiés comme activement utilisés au niveau de l'architecture globale).

## Flux de Données Typique

Le flux de données peut varier en fonction de l'orchestrateur spécifique mis en place. Un flux typique, potentiellement guidé par l'Agent PM, pourrait être :

1.  **Soumission** : L'utilisateur soumet un texte via l'Interface Utilisateur.
2.  **Planification Initiale** : L'Orchestrateur (ou l'Agent PM) reçoit la requête, analyse l'état initial et définit la première tâche (par exemple, extraction).
3.  **Exécution de Tâche (Exemple : Extraction)** :
    *   L'Orchestrateur active l'Agent Extract.
    *   L'Agent Extract traite le texte et stocke les arguments identifiés dans l'État Partagé.
4.  **Planification Itérative** :
    *   L'Orchestrateur (ou l'Agent PM) consulte l'État Partagé.
    *   Il définit la prochaine tâche (par exemple, analyse informelle) et désigne l'agent approprié (Agent Informal).
5.  **Exécution de Tâche (Exemple : Analyse Informelle)** :
    *   L'Agent Informal récupère les données nécessaires de l'État Partagé, effectue son analyse et met à jour l'État Partagé.
6.  **Répétition** : Les étapes 4 et 5 sont répétées pour d'autres analyses (par exemple, analyse formelle par les Agents Logiques).
7.  **Synthèse et Conclusion** :
    *   Une fois les analyses jugées suffisantes, l'Orchestrateur (ou l'Agent PM) initie la phase de conclusion.
    *   L'Agent PM peut être sollicité pour générer une synthèse ou une conclusion finale basée sur l'ensemble des résultats dans l'État Partagé.
8.  **Présentation** : Les résultats finaux sont récupérés de l'État Partagé et présentés à l'utilisateur via l'Interface Utilisateur.

Ce flux est une généralisation. Le document sur le [`flux_donnees_analyse.md`](./flux_donnees_analyse.md:0) (s'il existe et est à jour) devrait fournir une description plus détaillée et spécifique.

## Principes Clés de l'Architecture

-   **Modularité** : Les composants sont faiblement couplés, ce qui facilite leur développement, leur test et leur maintenance indépendants.
-   **Extensibilité** : De nouveaux agents ou services peuvent être facilement intégrés dans le système.
-   **Flexibilité** : Le flux d'orchestration peut être adapté pour différents types d'analyses ou de textes, notamment grâce au rôle de planification de l'Agent PM.
-   **Hybride (Symbolique et Connexionniste)** : Combine la puissance des LLMs pour la compréhension du langage avec la rigueur de l'IA symbolique pour l'analyse logique.

Ce document sera complété par des descriptions plus détaillées de chaque composant et de leurs interactions dans des documents dédiés au sein de ce dossier `docs/architecture/`.