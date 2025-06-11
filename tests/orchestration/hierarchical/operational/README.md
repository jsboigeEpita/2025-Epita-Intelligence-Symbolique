# Tests de l'Orchestration Opérationnelle

## Objectif

Ce répertoire contient les tests qui valident la couche opérationnelle de l'architecture hiérarchique. La couche opérationnelle est responsable de l'exécution concrète des tâches déléguées par la couche tactique. Elle gère les agents spécialisés, leur cycle de vie, et la manière dont ils exécutent des actions spécifiques.

L'objectif de ces tests est de garantir que la couche opérationnelle peut recevoir des ordres, les traduire en actions concrètes pour les agents, et suivre leur exécution de manière fiable et robuste.

## Structure des Tests

Les tests de l'orchestration opérationnelle sont organisés dans les sous-répertoires suivants :

-   **`adapters/`**: Contient les tests pour les adaptateurs qui servent de pont entre le système d'orchestration et les agents spécialisés (par exemple, `ExtractAgent`). Ces tests valident que les adaptateurs peuvent correctement encapsuler la logique d'un agent, gérer son cycle de vie et son intégration dans le flux de travail opérationnel.

## Scénarios d'Orchestration

Les tests à ce niveau se concentrent sur la validation des mécanismes de bas niveau de l'orchestration :

-   **Délégation de Tâches**: S'assurer que les tâches peuvent être transmises de manière fiable à des agents spécifiques via leurs adaptateurs.
-   **Gestion du Cycle de Vie des Agents**: Valider que les agents sont correctement initialisés avant l'exécution d'une tâche et que leurs ressources sont gérées efficacement.
-   **Communication et Rapports**: Vérifier que l'état des tâches (en cours, succès, échec) est correctement suivi et rapporté aux couches supérieures.

## Importance pour l'Application

La couche opérationnelle est le "bras armé" de l'architecture d'orchestration. Les tests dans ce module sont essentiels pour garantir que les plans élaborés par les couches stratégique et tactique peuvent être exécutés de manière concrète et fiable. Sans une couche opérationnelle robuste, l'ensemble du système d'orchestration serait incapable de produire des résultats.
