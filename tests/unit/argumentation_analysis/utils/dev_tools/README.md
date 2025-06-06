# Tests Unitaires pour les Outils de Développement

## Objectif

Ce répertoire contient les tests unitaires pour les modules utilitaires destinés à faciliter le développement, le formatage et la validation du code du projet. Ces outils ne font pas partie de la logique métier principale de l'analyse d'argumentation, mais sont essentiels pour maintenir la qualité et l'intégrité du code base.

L'objectif est de garantir que ces outils de développement sont fiables et fonctionnent comme prévu.

## Fonctionnalités Testées

### `code_formatting_utils`

-   **Formatage de Code (`format_python_file_with_autopep8`)** : Valide le wrapper autour de l'outil `autopep8`. Les tests mockent l'appel au sous-processus pour s'assurer que la fonction :
    -   Construit et exécute la bonne commande `autopep8`.
    -   Gère les cas de succès (avec ou sans modification du fichier).
    -   Gère les erreurs (fichier non trouvé, `autopep8` non installé, échec de la commande).
    -   Permet de passer des arguments personnalisés à `autopep8`.

### `code_validation`

-   **Validation de Syntaxe (`check_python_syntax`)** : Valide l'utilisation de `ast.parse` pour vérifier la syntaxe d'un fichier Python. Les tests confirment la détection correcte des fichiers valides et invalides.
-   **Validation des Tokens (`check_python_tokens`)** : Valide l'utilisation du module `tokenize` pour trouver des erreurs de bas niveau, comme les problèmes d'indentation.

### `encoding_utils`

-   **Correction d'Encodage (`fix_file_encoding`)** : Valide la fonction qui tente de détecter l'encodage d'un fichier et de le convertir en UTF-8. Les tests utilisent des fichiers temporaires avec différents encodages (Latin-1, CP1252, etc.) pour confirmer que la conversion est réussie et que les cas d'échec sont bien gérés.

### `format_utils`

-   **Correction d'Apostrophes (`fix_docstrings_apostrophes`)** : Valide un outil de formatage spécifique qui remplace les apostrophes simples par des guillemets dans les docstrings pour éviter les conflits. Les tests vérifient que les remplacements sont corrects et que la fonction est idempotente.

### `mock_utils`

-   **Simulation de JPype (`setup_jpype_mock`)** : Valide un utilitaire de test crucial qui injecte un mock complet du module `jpype` dans `sys.modules`. Les tests s'assurent que le mock est correctement installé et nettoyé, et qu'il simule de manière réaliste l'état de la JVM (démarrée/arrêtée) et l'accès à des classes Java simulées.

## Dépendances Clés

-   **`pytest`** : Utilisé intensivement, notamment avec des fixtures complexes pour créer des environnements de test contrôlés (fichiers temporaires, gestion de `sys.modules`).
-   **`unittest.mock`** : La pierre angulaire de ces tests. Elle est utilisée pour :
    -   Simuler les appels à des processus externes (`subprocess.run` pour `autopep8`).
    -   Injecter des modules mockés dans le système (`sys.modules` pour `jpype`).
    -   Isoler les fonctions du système de fichiers (`open`, `pathlib.Path`).
