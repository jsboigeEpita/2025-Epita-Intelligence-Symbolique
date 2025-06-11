# Tests Unitaires pour l'Analyse Informelle

## Objectif

Ce répertoire contient les tests unitaires pour les composants liés à l'analyse des sophismes informels. L'objectif principal est de valider la capacité du système à charger, interpréter et exposer une taxonomie de sophismes à travers un plugin dédié pour le `Semantic Kernel`.

Ces tests garantissent que la taxonomie des sophismes, qui sert de base de connaissances pour l'analyse, est correctement gérée et que les fonctions d'exploration de cette taxonomie sont fiables.

## Fonctionnalités Testées

### `InformalAnalysisPlugin`

-   **Chargement et Mise en Cache de la Taxonomie** :
    -   Vérification que la taxonomie des sophismes est correctement chargée à partir d'un fichier de données (simulé par un `DataFrame` pandas).
    -   Test du mécanisme de mise en cache pour éviter les lectures répétées du fichier.
    -   Gestion des erreurs lors du chargement de la taxonomie.

-   **Exploration de la Hiérarchie** :
    -   Test de la fonction `explore_fallacy_hierarchy`, qui permet de naviguer dans la structure arborescente des sophismes.
    -   Vérification de la récupération correcte des nœuds parents et enfants.
    -   Gestion des cas où un identifiant (PK) de sophisme est invalide ou non trouvé.

-   **Récupération de Détails** :
    -   Test de la fonction `get_fallacy_details`, qui fournit des informations détaillées sur un sophisme spécifique (description, nom, etc.).
    -   Validation du format de sortie (JSON).

### `setup_informal_kernel`

-   **Intégration au Kernel** :
    -   Vérification que le `InformalAnalysisPlugin` est correctement instancié et ajouté à une instance du `Kernel` de Semantic Kernel.
    -   Test de la configuration avec et sans service LLM associé.
    -   Gestion des erreurs lors de l'initialisation du plugin pendant le processus de configuration.

## Dépendances Clés

-   **`unittest.mock`** : Essentiel pour isoler le `InformalAnalysisPlugin` du système de fichiers et des dépendances externes. Le patching est utilisé pour :
    -   Simuler le chargement de la taxonomie (`_get_taxonomy_dataframe`).
    -   Mocker le module `taxonomy_loader` pour contrôler le chemin du fichier de taxonomie et sa validation.
-   **`pandas.DataFrame`** : Un `DataFrame` est utilisé pour simuler la taxonomie en mémoire, permettant de tester la logique de manipulation des données sans dépendre d'un fichier réel.
-   **`semantic_kernel.Kernel`** : Les tests de `setup_informal_kernel` utilisent une instance réelle du `Kernel` pour s'assurer que l'intégration du plugin se déroule comme prévu.
