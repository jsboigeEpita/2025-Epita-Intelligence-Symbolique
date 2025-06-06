# Tests des Adaptateurs d'Agents Opérationnels

## Objectif

Ce répertoire contient les tests pour les adaptateurs qui font le lien entre la couche d'orchestration opérationnelle et les agents spécialisés. L'objectif principal est de valider que ces adaptateurs peuvent correctement encapsuler la logique d'un agent, gérer son cycle de vie (initialisation, exécution de tâches) et s'intégrer de manière fiable dans le système d'orchestration.

Ces tests garantissent que la couche opérationnelle peut déléguer des tâches spécifiques à des agents compétents de manière transparente et robuste.

## Scénarios d'Orchestration

Les tests dans ce module se concentrent sur les scénarios de coordination et de communication suivants pour l'`ExtractAgentAdapter` :

-   **Initialisation de l'Adaptateur**: Vérifie que l'adaptateur peut être instancié et que son état initial est correct.
-   **Initialisation de l'Agent sous-jacent**: S'assure que l'adaptateur peut correctement initialiser l'agent qu'il encapsule (ici, `ExtractAgent`), en lui passant les dépendances nécessaires comme le `kernel` et le `llm_service_id`. Les cas d'échec de l'initialisation sont également testés.
-   **Gestion des Capacités**: Valide que l'adaptateur expose correctement les capacités de l'agent sous-jacent et peut déterminer s'il est apte à traiter une tâche donnée.
-   **Traitement des Tâches**: Teste le flux complet de traitement d'une tâche, de sa réception à sa complétion. Cela inclut :
    -   L'enregistrement de la tâche dans l'état opérationnel.
    -   L'appel à la méthode de l'agent correspondante (par exemple, `extract_from_name`).
    -   La gestion des résultats (succès, échec, erreurs) et la mise à jour du statut de la tâche.
    -   La gestion des cas où la tâche est invalide ou si une erreur inattendue se produit.
-   **Normalisation du Texte**: Vérifie les capacités de prétraitement de texte de l'adaptateur, comme la suppression des mots vides.

## Dépendances Clés

-   **`pytest` et `pytest-asyncio`**: Utilisés pour gérer les tests asynchrones, car les interactions avec les agents sont non bloquantes.
-   **`unittest.mock`**: Essentiel pour mocker les dépendances complexes et isoler le comportement de l'adaptateur. Les principaux mocks incluent :
    -   **`OperationalState`**: Pour simuler l'état partagé de la couche opérationnelle et vérifier que l'adaptateur met à jour correctement le statut des tâches.
    -   **`MessageMiddleware`**: Pour simuler le système de communication entre les composants.
    -   **`ExtractAgent`**: L'agent lui-même est mocké pour contrôler son comportement et vérifier que l'adaptateur l'appelle avec les bons paramètres.
    -   **`semantic_kernel.Kernel`**: Le noyau sémantique est mocké car il s'agit d'une dépendance lourde qui n'est pas nécessaire pour tester la logique de l'adaptateur.