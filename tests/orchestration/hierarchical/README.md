# Tests de l'Orchestration Hiérarchique

## Objectif

Ce répertoire contient les tests qui valident l'architecture d'orchestration hiérarchique du système. Cette architecture est conçue pour décomposer des problèmes complexes en plusieurs niveaux d'abstraction, allant de la stratégie globale à l'exécution concrète.

L'objectif de ces tests est de garantir que les différentes couches de l'architecture (tactique et opérationnelle) interagissent de manière cohérente et fiable pour atteindre les objectifs fixés par la couche stratégique.

## Structure des Tests

Les tests de l'orchestration hiérarchique sont organisés dans les sous-répertoires suivants, qui correspondent aux couches de l'architecture :

-   **`tactical/`**: Contient les tests pour la couche tactique. Cette couche est responsable de recevoir des directives de haut niveau, de les décomposer en plans d'action (tâches), de gérer les dépendances et d'assigner ces tâches à la couche inférieure. Les tests ici valident la logique de planification et de coordination.

-   **`operational/`**: Contient les tests pour la couche opérationnelle. Cette couche est responsable de l'exécution concrète des tâches. Elle gère les agents spécialisés et leur cycle de vie. Les tests ici valident la capacité de la couche à exécuter des ordres de manière fiable et à rapporter les résultats.

## Scénarios d'Orchestration

Les tests à ce niveau valident le flux de communication et de contrôle vertical à travers l'architecture :

-   **De la Stratégie à l'Action**: S'assurer qu'un objectif stratégique peut être correctement reçu par la couche tactique, décomposé en tâches, et que ces tâches peuvent être exécutées par la couche opérationnelle.
-   **Communication Inter-Couches**: Valider que les messages (directives, assignations de tâches, rapports de statut, résultats) sont correctement transmis et interprétés entre les couches tactique et opérationnelle.
-   **Gestion des États**: Vérifier que l'état de l'orchestration est maintenu de manière cohérente à travers les différentes couches (par exemple, le statut d'une tâche doit être synchronisé entre la couche qui l'assigne et celle qui l'exécute).

## Importance pour l'Application

L'architecture hiérarchique est le cœur du système de raisonnement et de prise de décision de l'application. Les tests dans ce module sont donc fondamentaux pour garantir la capacité du système à gérer des problèmes complexes de manière structurée et évolutive. Ils s'assurent que la "chaîne de commandement" de l'orchestration est fonctionnelle et robuste.
