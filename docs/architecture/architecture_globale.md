# Architecture Globale du Système d'Analyse Argumentative

Ce document décrit l'architecture globale du système d'analyse argumentative, en mettant en évidence les principaux composants et leurs interactions.

## Vue d'ensemble

Le projet est construit autour d'une architecture multi-agents où différents agents spécialisés collaborent pour analyser des textes argumentatifs. Cette architecture modulaire permet une séparation claire des responsabilités et facilite l'extension du système avec de nouveaux agents ou fonctionnalités.

L'objectif principal est de fournir une plateforme robuste et flexible pour l'analyse rhétorique, combinant les capacités des Grands Modèles de Langage (LLMs) avec la rigueur des approches d'Intelligence Artificielle symbolique.

## Diagramme d'Architecture

Le diagramme suivant illustre les principaux composants du système et leurs relations :

```
┌─────────────────────────────────────────────────────────────┐
│                      Interface Utilisateur                   │
└───────────────────────────────┬─────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────┐
│                        Orchestration                         │
└───────┬─────────────────┬─────────────────┬─────────────────┘
        │                 │                 │
┌───────▼───────┐ ┌───────▼───────┐ ┌───────▼───────┐
│  Agent Extract │ │ Agent Informal│ │   Agent PL    │ ...
└───────┬───────┘ └───────┬───────┘ └───────┬───────┘
        │                 │                 │
┌───────▼─────────────────▼─────────────────▼───────┐
│                   État Partagé                     │
└───────────────────────────────────────────────────┘
        │                 │                 │
┌───────▼───────┐ ┌───────▼───────┐ ┌───────▼───────┐
│  LLM Service  │ │  JVM (Tweety) │ │ Autres Services│
└───────────────┘ └───────────────┘ └───────────────┘
```

## Composants Principaux

- **Interface Utilisateur (UI)** : Permet aux utilisateurs de soumettre des textes pour analyse, de configurer les paramètres et de visualiser les résultats. Elle peut prendre la forme d'une application web, d'un notebook Jupyter ou d'une interface en ligne de commande.

- **Orchestration** : Le cœur du système qui gère le flux de travail de l'analyse. Il coordonne les différents agents, gère la communication entre eux et s'assure que les tâches sont exécutées dans le bon ordre. Voir aussi ([`analyse_architecture_orchestration.md`](./analyse_architecture_orchestration.md:0)).

- **Agents Spécialisés** : Chaque agent est responsable d'une tâche spécifique dans le processus d'analyse :
    - **Agent Extract** : Identifie et extrait les arguments, les prémisses et les conclusions du texte source.
    - **Agent Informal** : Analyse les arguments extraits pour détecter les sophismes, évaluer la pertinence et la force des arguments d'un point de vue informel.
    - **Agent PL (Propositional Logic)** : Formalise les arguments en logique propositionnelle et utilise des solveurs logiques (par exemple, via Tweety) pour vérifier la validité, la cohérence et d'autres propriétés formelles.
    - D'autres agents peuvent être ajoutés pour des analyses plus spécifiques (par exemple, analyse émotionnelle, détection de biais, etc.).

- **État Partagé** : Un composant central où les informations et les résultats intermédiaires produits par les agents sont stockés et accessibles. Cela permet aux agents de travailler de manière asynchrone et de s'appuyer sur les résultats des autres.

- **Services Externes** :
    - **LLM Service** : Fournit l'accès aux Grands Modèles de Langage (par exemple, GPT, Claude) pour des tâches telles que la compréhension du langage naturel, la génération de texte et l'assistance à l'analyse.
    - **JVM (Tweety)** : Intègre les bibliothèques de logique symbolique de TweetyProject pour l'analyse formelle des arguments.
    - **Autres Services** : Peuvent inclure des bases de données, des services de cryptographie, des outils de visualisation, etc.

## Flux de Données Typique

1.  **Soumission** : L'utilisateur soumet un texte via l'Interface Utilisateur.
2.  **Dispatching** : L'Orchestrateur reçoit la requête et initie le processus d'analyse.
3.  **Extraction** : L'Orchestrateur envoie le texte à l'Agent Extract. L'Agent Extract traite le texte et stocke les arguments identifiés dans l'État Partagé.
4.  **Analyse Informelle** : L'Orchestrateur notifie l'Agent Informal. L'Agent Informal récupère les arguments de l'État Partagé, effectue son analyse et met à jour l'État Partagé avec ses résultats.
5.  **Analyse Formelle** : L'Orchestrateur notifie l'Agent PL. L'Agent PL récupère les arguments (potentiellement enrichis par l'Agent Informal) de l'État Partagé, les formalise et utilise le service JVM (Tweety) pour l'analyse logique. Les résultats sont stockés dans l'État Partagé.
6.  **Agrégation et Synthèse** : L'Orchestrateur peut avoir une étape pour agréger et synthétiser les résultats des différents agents.
7.  **Présentation** : Les résultats finaux sont récupérés de l'État Partagé et présentés à l'utilisateur via l'Interface Utilisateur.

## Principes Clés de l'Architecture

- **Modularité** : Les composants sont faiblement couplés, ce qui facilite leur développement, leur test et leur maintenance indépendants.
- **Extensibilité** : De nouveaux agents ou services peuvent être facilement intégrés dans le système.
- **Flexibilité** : Le flux d'orchestration peut être adapté pour différents types d'analyses ou de textes.
- **Hybride (Symbolique et Connexionniste)** : Combine la puissance des LLMs pour la compréhension du langage avec la rigueur de l'IA symbolique pour l'analyse logique.

Ce document sera complété par des descriptions plus détaillées de chaque composant et de leurs interactions dans des documents dédiés au sein de ce dossier `docs/architecture/`.