# Référence API du Système

Cette section contient la documentation de référence pour les API du système d'analyse argumentative, fournissant des informations détaillées sur les interfaces, les classes et les méthodes disponibles.

## Documents Disponibles

### [Référence API du Système de Communication](./reference_api.md)
Documentation complète de l'API du système de communication entre agents.

### [API des Agents](./agents/README.md)
Documentation des agents spécialistes et de leurs interfaces.

### [API d'Orchestration](./orchestration/README.md)
Documentation des systèmes d'orchestration et de l'architecture hiérarchique.

## Organisation de la Référence API

La documentation de référence est organisée selon les principaux modules du système :

### API du Système de Communication

L'API du système de communication définit les interfaces et les classes permettant aux agents de communiquer efficacement. Elle inclut :

- **Interfaces de communication** : Définition des contrats pour la communication entre agents
- **Classes de messages** : Structures de données pour l'échange d'informations
- **Gestionnaires de communication** : Composants responsables de la gestion des flux de communication

### API des Agents

L'API des agents définit les interfaces et les classes pour l'implémentation des agents spécialistes. Elle inclut :

- **[Agent Project Manager (PM)](./agents/pm_agent_api.md)** : Documentation de l'agent orchestrateur principal
- **[Agent d'Analyse Informelle](./agents/informal_agent_api.md)** : Documentation de l'agent d'analyse des arguments et sophismes
- **[Agent de Logique Propositionnelle (PL)](./agents/pl_agent_api.md)** : Documentation de l'agent de formalisation logique
- **[Agent d'Extraction](./agents/extract_agent_api.md)** : Documentation de l'agent d'extraction de segments pertinents

### API d'Orchestration

L'API d'orchestration définit les interfaces et les classes pour la coordination des agents. Elle inclut :

- **[Architecture Hiérarchique](./orchestration/hierarchical_architecture_api.md)** : Documentation de l'architecture à trois niveaux
- **Interfaces d'orchestration** : Contrats pour les orchestrateurs
- **Stratégies d'orchestration** : Implémentations de différentes stratégies
- **Gestionnaires d'état** : Composants pour la gestion de l'état partagé

### API des Services

L'API des services définit les interfaces et les classes pour les services partagés. Elle inclut :

- **Interfaces de service** : Contrats pour les services
- **Implémentations de service** : Implémentations concrètes des services
- **Utilitaires de service** : Fonctions utilitaires pour les services

## Utilisation de la Référence API

La référence API est destinée aux développeurs qui souhaitent :

- Comprendre en détail le fonctionnement interne du système
- Étendre le système avec de nouveaux composants
- Intégrer le système avec d'autres applications

Pour une introduction plus générale au système, consultez le [Guide du Développeur](../guides/guide_developpeur.md).

## Conventions de Nommage

Les conventions de nommage suivantes sont utilisées dans la référence API :

- **Interfaces** : Préfixées par `I` (ex: `IAgent`, `IService`)
- **Classes abstraites** : Suffixées par `Base` (ex: `AgentBase`, `ServiceBase`)
- **Implémentations** : Nommées selon leur fonctionnalité (ex: `ExtractAgent`, `LLMService`)
- **Méthodes** : Nommées en camelCase (ex: `processMessage`, `updateState`)

## Versionnement de l'API

L'API du système suit les principes du versionnement sémantique (SemVer) :

- **Changements majeurs** : Modifications incompatibles avec les versions précédentes
- **Changements mineurs** : Ajouts de fonctionnalités compatibles avec les versions précédentes
- **Correctifs** : Corrections de bugs sans modification de l'API

Pour plus d'informations sur les changements d'API, consultez le [CHANGELOG](../../CHANGELOG.md).

## Structure de la Documentation

```
docs/reference/
├── README.md                           # Ce fichier
├── reference_api.md                    # API du système de communication
├── agents/                             # Documentation des agents
│   ├── README.md                       # Vue d'ensemble des agents
│   ├── pm_agent_api.md                 # API de l'agent Project Manager
│   ├── informal_agent_api.md           # API de l'agent d'analyse informelle
│   ├── pl_agent_api.md                 # API de l'agent de logique propositionnelle
│   └── extract_agent_api.md            # API de l'agent d'extraction
└── orchestration/                      # Documentation de l'orchestration
    ├── README.md                       # Vue d'ensemble de l'orchestration
    ├── hierarchical_architecture_api.md # Architecture hiérarchique
    ├── strategic_level_api.md          # Niveau stratégique
    ├── tactical_level_api.md           # Niveau tactique
    └── operational_level_api.md        # Niveau opérationnel