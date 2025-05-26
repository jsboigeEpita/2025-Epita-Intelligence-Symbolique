# API du Niveau Tactique

## Introduction

Le Niveau Tactique est responsable de la coordination des tâches d'analyse, de la résolution des conflits entre les résultats des agents, et de la supervision des agents opérationnels. Il fait le lien entre la planification stratégique et l'exécution opérationnelle.

[Retour à l'API d'Orchestration Hiérarchique](./hierarchical_architecture_api.md)
[Retour au README de l'Orchestration](./README.md)

## Composants Principaux

### `TaskCoordinator`
-   **Rôle** : Décompose les directives stratégiques en tâches opérationnelles, assigne les tâches aux agents, gère les dépendances et l'ordonnancement, adapte le plan d'exécution.
-   **Méthodes Clés** :
    -   `decompose_objective(objective)`: Décompose un objectif stratégique en tâches tactiques/opérationnelles.
    -   `assign_tasks(tasks)`: Assigne les tâches aux agents via le niveau opérationnel.
    -   `aggregate_results()`: Agrège les résultats des tâches opérationnelles.

### `ProgressMonitor`
-   **Rôle** : Suit l'avancement des tâches en temps réel, identifie les retards ou blocages, collecte les métriques de performance du niveau opérationnel.

### `ConflictResolver`
-   **Rôle** : Détecte et analyse les contradictions ou incohérences dans les résultats fournis par les agents opérationnels, applique des heuristiques pour résoudre ces conflits ou les remonte au niveau stratégique.

### `TacticalState`
-   **Rôle** : Maintient les informations partagées au niveau tactique (tâches en cours, résultats intermédiaires, métriques de progression, conflits identifiés).

### `TacticalOperationalInterface`
-   **Rôle** : Assure la communication entre les niveaux tactique et opérationnel.
-   **Méthodes Clés** :
    -   `translate_task(task)`: Traduit une tâche tactique en une ou plusieurs tâches opérationnelles.
    -   `submit_operational_results(results)`: Permet au niveau opérationnel de soumettre ses résultats.
    -   `report_operational_status(status_data)`: Permet au niveau opérationnel de remonter son état.

## Flux de Travail

1.  Le `TaskCoordinator` reçoit des directives de la `StrategicTacticalInterface`.
2.  Il décompose ces directives en tâches et les transmet à la `TacticalOperationalInterface`.
3.  Le `ProgressMonitor` suit l'exécution des tâches au niveau opérationnel.
4.  Les résultats remontent via la `TacticalOperationalInterface`.
5.  Le `ConflictResolver` analyse les résultats pour détecter les incohérences.
6.  Le `TaskCoordinator` agrège les résultats validés et les transmet à la `StrategicTacticalInterface`.

Cette page sera complétée avec les détails de l'API pour chaque composant.