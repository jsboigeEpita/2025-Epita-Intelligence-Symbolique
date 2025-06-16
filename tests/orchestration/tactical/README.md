# Tests de l'Orchestration Tactique

## Objectif

Ce répertoire contient les tests pour les composants de la couche tactique de l'architecture d'orchestration. La couche tactique est le "cerveau" de l'orchestration, responsable de la planification, de la coordination et de la supervision de l'exécution des tâches.

L'objectif de ces tests est de valider que les composants tactiques peuvent non seulement créer des plans d'action à partir d'objectifs stratégiques, mais aussi surveiller leur exécution, détecter les problèmes et suggérer des solutions, assurant ainsi une exécution robuste et résiliente.

## Composants Testés

Les tests dans ce module se concentrent sur deux composants principaux :

-   **`TaskCoordinator`**: Le coordinateur de tâches est responsable de :
    -   Recevoir des objectifs de la couche stratégique.
    -   Décomposer ces objectifs en tâches plus petites et gérables.
    -   Établir les dépendances entre les tâches.
    -   Assigner les tâches aux agents opérationnels appropriés.
    -   Gérer les résultats des tâches et rapporter l'état d'avancement.

-   **`ProgressMonitor`**: Le moniteur de progression est responsable de :
    -   Suivre la progression de chaque tâche.
    -   Détecter les anomalies telles que les retards, la stagnation ou les blocages dus à des dépendances échouées.
    -   Identifier les problèmes systémiques comme un taux d'échec élevé.
    -   Suggérer des actions correctives pour résoudre les problèmes détectés (par exemple, réassigner une tâche, allouer plus de ressources).

## Scénarios d'Orchestration

Les tests couvrent un large éventail de scénarios de gestion de projet et de résolution de problèmes :

-   **Planification de bout en bout**: De la réception d'un objectif à l'assignation des tâches décomposées.
-   **Détection d'Anomalies**: Simulation de divers problèmes (tâches en retard, bloquées, en régression) pour vérifier que le moniteur les détecte correctement.
-   **Suggestion d'Actions Correctives**: Vérification que le moniteur propose des solutions pertinentes et logiques pour les problèmes identifiés.
-   **Gestion des Ajustements Stratégiques**: Teste la capacité du coordinateur à modifier un plan en cours d'exécution en réponse à de nouvelles directives de la couche stratégique.
-   **Génération de Rapports**: Valide la capacité des composants à générer des rapports de statut complets, incluant la progression, les problèmes et les métriques.

## Dépendances Clés

-   **`unittest` et `pytest`**: Utilisés comme frameworks de test.
-   **`unittest.mock`**: Essentiel pour mocker les dépendances et isoler la logique tactique. Les principaux mocks incluent :
    -   **`TacticalState`**: Pour simuler l'état partagé de la couche tactique et vérifier que les composants le lisent et le mettent à jour correctement.
    -   **`MessageMiddleware` et `TacticalAdapter`**: Pour simuler le système de communication et vérifier que les composants interagissent correctement avec les autres couches.