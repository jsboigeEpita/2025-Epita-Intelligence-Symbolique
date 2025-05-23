# API du Niveau Opérationnel

## Introduction

Le Niveau Opérationnel est responsable de l'exécution concrète des tâches d'analyse argumentative. Il gère les agents spécialistes et leur interaction directe avec les données et les outils d'analyse.

[Retour à l'API d'Orchestration Hiérarchique](./hierarchical_architecture_api.md)
[Retour au README de l'Orchestration](./README.md)

## Composants Principaux

### `OperationalManager`
-   **Rôle** : Sert d'interface entre le niveau tactique et les agents opérationnels. Reçoit les tâches de la `TacticalOperationalInterface`, les traduit si nécessaire, et les assigne aux agents appropriés via l'`AgentRegistry`. Collecte les résultats des agents et les remonte.
-   **Méthodes Clés** :
    -   `start()`: Démarre le gestionnaire.
    -   `stop()`: Arrête le gestionnaire.
    -   `process_tactical_task(task)`: Traite une tâche reçue du niveau tactique.

### `AgentRegistry`
-   **Rôle** : Maintient une liste des agents spécialistes disponibles, gère leur cycle de vie (création, initialisation), et sélectionne l'agent le plus pertinent pour une tâche donnée en fonction de ses capacités.

### `OperationalAgent` (Interface)
-   **Rôle** : Définit le contrat que tous les agents spécialistes doivent implémenter.
-   **Méthodes Clés** :
    -   `process_task(task)`: Exécute une tâche spécifique.
    -   `get_capabilities()`: Retourne la liste des capacités de l'agent.
    -   `can_process_task(task)`: Indique si l'agent est capable de traiter une tâche donnée.

### Adaptateurs d'Agents (`adapters/`)
-   **Rôle** : Fournissent une couche d'abstraction entre l'`OperationalManager` et les implémentations concrètes des agents (par exemple, `ExtractAgentAdapter`, `InformalAgentAdapter`). Ils s'assurent que chaque agent respecte l'interface `OperationalAgent`.

### `OperationalState`
-   **Rôle** : Maintient les informations partagées au niveau opérationnel (tâches assignées, extraits de texte, résultats d'analyse, problèmes rencontrés, métriques, logs).

## Flux de Travail

1.  L'`OperationalManager` reçoit une tâche de la `TacticalOperationalInterface`.
2.  Il consulte l'`AgentRegistry` pour identifier l'agent (ou les agents) capable(s) de traiter la tâche.
3.  L'agent sélectionné exécute la tâche, potentiellement en interagissant avec des services externes (LLM, JVM) ou l'état opérationnel.
4.  L'agent retourne son résultat à l'`OperationalManager`.
5.  L'`OperationalManager` transmet le résultat à la `TacticalOperationalInterface`.

Cette page sera complétée avec les détails de l'API pour chaque composant.