# Tests de l'Orchestration Tactique

## Objectif

Ce répertoire contient les tests pour la couche tactique de l'architecture d'orchestration hiérarchique. La couche tactique joue un rôle de pivot : elle reçoit des directives de haut niveau de la couche stratégique et les traduit en plans d'action concrets, sous forme de tâches, pour la couche opérationnelle.

L'objectif de ces tests est de valider la capacité du `TaskCoordinator` à décomposer des objectifs complexes, à planifier l'exécution des tâches, à gérer leurs dépendances et à communiquer efficacement avec les autres couches de l'architecture.

## Scénarios d'Orchestration

Les tests dans ce module se concentrent sur les scénarios de coordination et de planification suivants :

-   **Gestion des Directives Stratégiques**: Valide la capacité du coordinateur à recevoir et à interpréter des directives de la couche stratégique, qu'il s'agisse de nouveaux objectifs ou d'ajustements de plans existants.
-   **Décomposition d'Objectifs**: Teste la logique de décomposition d'objectifs variés (par exemple, "identifier les arguments", "détecter les sophismes") en une séquence de tâches plus petites et réalisables, chacune avec des capacités requises spécifiques.
-   **Planification et Dépendances**: S'assure que le coordinateur peut correctement établir les dépendances entre les tâches (par exemple, une tâche d'analyse doit dépendre d'une tâche d'extraction).
-   **Assignation des Tâches**: Vérifie que les tâches sont assignées à l'agent opérationnel le plus approprié en fonction des capacités requises, ou qu'elles sont publiées pour que des agents disponibles puissent s'en saisir.
-   **Gestion des Résultats**: Teste la manière dont le coordinateur gère les résultats des tâches opérationnelles, met à jour l'état tactique, et détermine si un objectif est complété.
-   **Génération de Rapports**: Valide la capacité du coordinateur à générer des rapports de statut et d'achèvement pour la couche stratégique.

## Dépendances Clés

-   **`pytest`**: Utilisé comme framework de test.
-   **`unittest.mock`**: Essentiel pour isoler la logique du coordinateur. Les principaux mocks incluent :
    -   **`TacticalState`**: Pour simuler l'état partagé de la couche tactique (listes de tâches, objectifs assignés) et vérifier que le coordinateur le met à jour correctement.
    -   **`MessageMiddleware`**: Pour simuler le bus de communication et vérifier que le coordinateur envoie les bons messages (assignations de tâches, rapports) aux bons destinataires.
    -   **`TacticalAdapter`**: L'adaptateur de communication de la couche tactique est mocké pour contrôler les interactions avec les autres couches.