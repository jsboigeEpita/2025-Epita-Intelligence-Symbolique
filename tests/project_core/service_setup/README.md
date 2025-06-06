# Tests de l'Initialisation des Services Centraux

## Objectif

Ce répertoire contient les tests unitaires pour le module `analysis_services`, qui est responsable de l'initialisation et de la configuration de tous les services fondamentaux de l'application. L'objectif de ces tests est de s'assurer que le processus de démarrage des services est fiable, robuste et se comporte comme attendu dans différentes configurations.

La validation de cette étape est critique, car une initialisation incorrecte des services pourrait entraîner des défaillances en cascade dans l'ensemble de l'application.

## Composants Testés

Les tests se concentrent sur la fonction `initialize_analysis_services`, qui orchestre la mise en place des services suivants :

-   **Initialisation de la JVM**: Vérifie que la machine virtuelle Java, une dépendance essentielle pour certaines bibliothèques, est correctement démarrée.
-   **Création du LLMService**: S'assure que le service de grand modèle de langage (LLM) est instancié, ce qui est fondamental pour les capacités d'analyse de l'application.
-   **Chargement des variables d'environnement**: Valide que les configurations à partir des fichiers `.env` sont bien chargées.

## Dépendances Clés

-   **`pytest`**: Utilisé comme framework de test pour structurer les tests et gérer les fixtures.
-   **`unittest.mock`**: Essentiel pour mocker les dépendances externes et isoler la logique d'initialisation. Les tests mockent notamment :
    -   Les constructeurs des services individuels (`CryptoService`, `CacheService`, etc.) pour contrôler leur instanciation.
    -   Les fonctions `initialize_jvm` et `create_llm_service` pour simuler leur succès ou leur échec sans avoir à réellement démarrer ces services lourds.
    -   Les constantes de configuration (`ENCRYPTION_KEY`, `CONFIG_FILE`) pour tester le comportement avec des valeurs contrôlées.
-   **`pathlib`**: Utilisé pour créer des structures de répertoires temporaires (`tmp_path`) qui simulent l'environnement du projet, permettant de tester la résolution des chemins de fichiers de manière isolée.
