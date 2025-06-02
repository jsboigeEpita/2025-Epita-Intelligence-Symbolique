# Tests du Niveau Tactique de l'Orchestration Hiérarchique

Ce répertoire contient les tests pour les composants du niveau tactique de l'architecture d'orchestration hiérarchique.

## Composants Testés

*   **`TaskCoordinator`** ([`test_coordinator.py`](test_coordinator.py:1)):
    *   Responsable de la réception des directives stratégiques (objectifs).
    *   Décompose les objectifs en tâches exécutables.
    *   Établit les dépendances entre les tâches.
    *   Assigne les tâches aux agents opérationnels appropriés ou les publie.
    *   Suit l'état d'avancement des tâches et des objectifs.
    *   Gère les résultats des tâches et les agrège au niveau des objectifs.
    *   Applique les ajustements stratégiques demandés.
    *   Communique avec le niveau stratégique (rapports d'état, achèvement d'objectifs) et le niveau opérationnel (assignation de tâches, réception de résultats).

## Objectifs des Tests

*   Valider la logique de décomposition des objectifs en tâches.
*   S'assurer de la correcte assignation des tâches en fonction des capacités requises.
*   Vérifier la gestion adéquate du cycle de vie des tâches et des objectifs (de la création à la complétion ou l'échec).
*   Tester la communication et l'intégration avec les niveaux stratégique et opérationnel (via des mocks).
*   Valider la robustesse du coordinateur face à différents scénarios et directives.