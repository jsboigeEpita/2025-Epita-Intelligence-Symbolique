# API du Niveau Stratégique

## Introduction

Le Niveau Stratégique est responsable de la planification globale de l'analyse argumentative, de l'allocation des ressources et des décisions de haut niveau. Il définit les objectifs généraux et supervise l'ensemble du processus.

[Retour à l'API d'Orchestration Hiérarchique](./hierarchical_architecture_api.md)
[Retour au README de l'Orchestration](./README.md)

## Composants Principaux

### `StrategicManager`
-   **Rôle** : Coordonne les agents stratégiques, interface avec l'utilisateur et le niveau tactique, prend les décisions finales, évalue les résultats.
-   **Méthodes Clés** :
    -   `set_objective(objective)`: Définit l'objectif global de l'analyse.
    -   `execute()`: Lance le processus d'analyse stratégique.
    -   `get_final_results()`: Récupère les résultats finaux.

### `ResourceAllocator`
-   **Rôle** : Gère l'allocation des ressources (computationnelles, cognitives), détermine les agents opérationnels à activer, établit les priorités des tâches.

### `StrategicPlanner`
-   **Rôle** : Crée des plans d'analyse structurés, décompose les objectifs globaux en sous-objectifs, établit les dépendances.

### `StrategicState`
-   **Rôle** : Maintient les informations partagées au niveau stratégique (objectifs, avancement du plan, ressources, résultats agrégés).

### `StrategicTacticalInterface`
-   **Rôle** : Assure la communication entre les niveaux stratégique et tactique.
-   **Méthodes Clés** :
    -   `translate_objectives(objectives)`: Traduit les objectifs stratégiques en directives tactiques.
    -   `report_progress(progress_data)`: Permet au niveau tactique de remonter l'avancement.
    -   `submit_tactical_results(results)`: Permet au niveau tactique de soumettre ses résultats.

## Flux de Travail

1.  Le `StrategicManager` reçoit un objectif de l'utilisateur.
2.  Le `StrategicPlanner` élabore un plan d'analyse.
3.  Le `ResourceAllocator` alloue les ressources nécessaires.
4.  Le `StrategicManager` transmet les directives au niveau tactique via la `StrategicTacticalInterface`.
5.  Le `StrategicManager` reçoit les résultats agrégés du niveau tactique et formule une conclusion.

Cette page sera complétée avec les détails de l'API pour chaque composant.