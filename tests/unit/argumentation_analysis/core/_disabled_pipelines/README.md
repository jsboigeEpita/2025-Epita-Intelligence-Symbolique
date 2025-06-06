# Tests Unitaires pour les Pipelines de Base (Désactivés)

## Objectif

Ce répertoire contient les tests unitaires pour un ensemble de pipelines utilitaires fondamentaux. Bien que situés dans un répertoire "_disabled", ces tests valident la logique d'orchestration pour des tâches essentielles à la configuration et à la maintenance de l'environnement, telles que la gestion des dépendances, le téléchargement de fichiers, le diagnostic système et l'archivage.

L'objectif est de garantir que chaque pipeline exécute sa séquence d'opérations de manière fiable, gère correctement les succès et les échecs, et interagit comme prévu avec le système de fichiers et les commandes externes.

## Fonctionnalités Testées

### `archival_pipeline`

-   **Orchestration de l'Archivage** : Valide la capacité du pipeline à trouver des fichiers correspondant à un motif, à construire un chemin de destination en préservant l'arborescence, et à archiver les fichiers.
-   **Gestion des Erreurs** : Teste la robustesse du pipeline face à des répertoires source/destination manquants ou des erreurs lors de l'archivage d'un fichier individuel (le pipeline doit continuer avec les autres fichiers).

### `dependency_management_pipeline`

-   **Installation de Dépendances** : Valide la lecture d'un fichier `requirements.txt` et l'exécution des commandes `pip install` pour chaque dépendance.
-   **Gestion des Options** : Teste la prise en compte des options comme `--force-reinstall` et d'autres options `pip`.
-   **Gestion des Échecs** : S'assure que le pipeline identifie et rapporte les échecs d'installation pour des paquets spécifiques et retourne un statut d'échec global.

### `diagnostic_pipeline`

-   **Orchestration du Diagnostic** : Valide l'appel à la classe `EnvironmentDiagnostic` qui exécute une série de vérifications (environnement Python, Java, JPype, dépendances).
-   **Rapport de Statut** : Teste le retour d'un code de sortie approprié (0 pour succès, 1 pour échec) en fonction du résultat des diagnostics.

### `download_pipeline`

-   **Orchestration du Téléchargement** : Valide la capacité du pipeline à itérer sur une liste de configurations de JARs et à appeler une fonction de téléchargement pour chacun.
-   **Gestion des Fichiers Existants** : Teste la logique pour ignorer le téléchargement si le fichier existe déjà et que l'option `force_download` est désactivée.
-   **Gestion des Erreurs** : S'assure que le pipeline continue même si un fichier échoue à être téléchargé et retourne un statut d'échec global.

### `setup_pipeline`

-   **Orchestration Globale** : Valide le pipeline de plus haut niveau qui appelle séquentiellement les autres pipelines (téléchargement, installation de dépendances, etc.).
-   **Logique Conditionnelle** : Teste la capacité du pipeline à activer ou désactiver des étapes en fonction de ses paramètres (ex: `config_path` pour le téléchargement, `mock_jpype` pour le mock de JPype).
-   **Gestion des Échecs en Cascade** : S'assure que l'échec d'un sous-pipeline (ex: téléchargement) empêche l'exécution des pipelines suivants et entraîne un échec global.

## Dépendances Clés

-   **`pytest`** : Utilisé pour structurer les tests avec des fixtures.
-   **`unittest.mock`** : Essentiel pour ces tests, car toutes les interactions avec le monde extérieur sont mockées. Cela inclut :
    -   Les appels aux autres pipelines (ex: `run_download_jars_pipeline` est mocké dans le test de `setup_pipeline`).
    -   Les interactions avec le système de fichiers (`pathlib.Path`, `open`).
    -   Les appels à des commandes externes (`run_shell_command`).
    -   La journalisation (`logging`, `logger`).
