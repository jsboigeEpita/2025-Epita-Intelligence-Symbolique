# Composants du Système d'Analyse Argumentative

Cette section documente les différents **concepts et modules logiques** qui constituent le système d'analyse argumentative, leur fonctionnement et leurs interactions. La documentation détaillée de chaque aspect se trouve dans les fichiers Markdown dédiés listés sous "Documents Disponibles" ou dans les sections ultérieures de ce document.

## Documents Disponibles

### [`Agent Management`](./agent_management.md)
Décrit les mécanismes de création, configuration, enregistrement, cycle de vie et gestion des dépendances des agents au sein du système.

### [`Agents Spécialistes`](./agents_specialistes.md)
Description détaillée des agents spécialistes qui composent le système, incluant leurs rôles, responsabilités et interactions. Sous-documents :
*   [`Pont Tweety (Tweety Bridge)`](./tweety_bridge.md) : Décrit le composant `TweetyBridge` qui sert d'interface avec les bibliothèques Java de TweetyProject pour le raisonnement formel.
*   [`Sous-système d'Évaluation (Evaluation Subsystem)`](./evaluation_subsystem.md) : Décrit l'ensemble des fonctionnalités et outils distribués responsables de l'évaluation de la qualité, de la cohérence et de la pertinence au sein du projet.

### [`API Web Applicative`](./api_web.md)
Décrit l'API RESTful basée sur Flask qui expose les fonctionnalités du projet, y compris ses points de terminaison et formats de données.

### [`Argument Parser`](./argument_parser.md)
Détaille le processus d'identification, d'extraction, de structuration et de validation des arguments (extraits) à partir des textes sources, principalement via l'`ExtractAgent`.

### [`Knowledge Base Interface`](./knowledge_base_interface.md)
Décrit le concept et l'implémentation d'une interface permettant aux agents d'accéder à des informations structurées ou non structurées (bases de données, ontologies, etc.) pour enrichir leur analyse.

### [`Reasoning Engine`](./reasoning_engine.md)
Présente l'ensemble des composants et capacités dédiés à l'évaluation de la structure logique, la validité, la cohérence des arguments, et à l'exécution d'inférences logiques.

### [`Structure du Projet`](./structure_projet.md)
Documentation complète de la structure du projet, incluant l'organisation des dossiers et des fichiers.

### [`Synthèse de la Collaboration entre Agents`](./synthese_collaboration.md)
Analyse de la collaboration entre les différents agents du système et des mécanismes qui la rendent possible.

## Composants Principaux

Le système d'analyse argumentative est composé de plusieurs composants principaux :

### Agents Spécialistes

Les agents spécialistes sont au cœur du système et incluent :

- **Agent Extract** : Responsable de l'identification et de l'extraction des arguments dans le texte
- **Agent Informal** : Analyse les arguments pour détecter les sophismes et évaluer leur qualité
- **Agent PL (Propositional Logic)** : Formalise les arguments en logique propositionnelle et vérifie leur validité

### État Partagé

L'état partagé est le mécanisme central qui permet aux agents de communiquer et de construire une analyse collaborative.

### Services Partagés

Les services partagés fournissent des fonctionnalités communes à tous les composants du système :

- **LLM Service** : Interface avec les modèles de langage
- **JVM Service** : Interface avec la machine virtuelle Java pour l'utilisation de Tweety
- **Cache Service** : Optimisation des performances via la mise en cache
- **Crypto Service** : Sécurisation des données sensibles

### Orchestration

Les mécanismes d'orchestration coordonnent les interactions entre les agents et gèrent le flux d'analyse.

## Interactions entre Composants

Les composants du système interagissent selon des patterns bien définis :

1. L'orchestrateur initialise l'analyse et délègue aux agents appropriés
2. Les agents accèdent et modifient l'état partagé pour communiquer
3. Les services fournissent des fonctionnalités communes à tous les composants
4. L'interface utilisateur permet d'interagir avec le système

## Extensibilité

Le système est conçu pour être extensible, permettant l'ajout de nouveaux agents et composants. Pour plus d'informations sur l'extension du système, consultez le [Guide du Développeur](../guides/guide_developpeur.md).