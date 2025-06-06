# Tests des Plugins d'Orchestration

## Objectif

Ce répertoire contient les tests pour les plugins du `semantic_kernel` qui sont utilisés dans le cadre de l'orchestration. Ces plugins servent de pont entre le monde du `semantic_kernel` (où les agents et les fonctions sémantiques opèrent) et l'état interne de l'orchestration.

L'objectif de ces tests est de garantir que les plugins exposent de manière fiable l'état et les fonctionnalités de l'orchestration, permettant ainsi aux agents sémantiques d'interagir avec le système de manière contrôlée et prévisible.

## Scénarios d'Orchestration

Les tests pour le `EnqueteStateManagerPlugin` se concentrent sur les scénarios d'interaction suivants :

-   **Initialisation du Plugin**: Vérifie que le plugin peut être correctement initialisé avec différents types d'états d'enquête (`EnquetePoliciereState`, `EnqueteCluedoState`) et qu'il est correctement enregistré dans le `semantic_kernel`.
-   **Accès à l'État**: Valide que les fonctions du plugin qui lisent l'état (par exemple, `get_case_description`, `get_cluedo_game_elements`) retournent les informations correctes.
-   **Modification de l'État**: S'assure que les fonctions du plugin qui modifient l'état (par exemple, `add_task`, `add_hypothesis`, `designate_next_agent`) mettent à jour correctement l'objet d'état sous-jacent.
-   **Interaction via le Kernel**: Les tests sont effectués en invoquant les fonctions du plugin à travers le `kernel`, simulant ainsi la manière dont un agent sémantique les utiliserait.

## Dépendances Clés

-   **`pytest` et `pytest-asyncio`**: Utilisés pour gérer les tests asynchrones, car les appels au `semantic_kernel` sont non bloquants.
-   **`semantic_kernel`**: Le framework `semantic_kernel` est une dépendance centrale, car les tests consistent à vérifier l'intégration du plugin dans le kernel.
-   **`EnquetePoliciereState` et `EnqueteCluedoState`**: Les objets d'état sont utilisés comme fixtures pour fournir un contexte contrôlé pour les tests.
