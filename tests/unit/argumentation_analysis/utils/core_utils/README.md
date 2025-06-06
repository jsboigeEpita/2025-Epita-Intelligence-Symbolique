# Tests Unitaires pour les Utilitaires de Base

## Objectif

Ce répertoire contient les tests unitaires pour les modules utilitaires fondamentaux et transverses du projet. Ces utilitaires gèrent des opérations essentielles telles que la manipulation de fichiers, la cryptographie, l'exécution de commandes système, le traitement de texte et la journalisation.

L'objectif est de garantir que ces briques de base sont extrêmement fiables, robustes et se comportent de manière prévisible, car de nombreux autres composants du système en dépendent.

## Fonctionnalités Testées

### `cli_utils`

-   **Analyse d'Arguments de Ligne de Commande** : Valide plusieurs fonctions basées sur `argparse` pour différents scripts. Les tests s'assurent que les arguments (avec leurs alias courts et longs) sont correctement reconnus et que les valeurs par défaut sont appliquées lorsque les arguments sont absents.

### `crypto_utils`

-   **Dérivation de Clé** : Vérifie que la dérivation de clé de chiffrement à partir d'une phrase de passe est déterministe et sécurisée.
-   **Chargement de Clé** : Teste la logique de chargement de la clé, en validant la priorité entre un argument direct et une variable d'environnement.
-   **Chiffrement/Déchiffrement** : Valide le cycle complet de chiffrement et déchiffrement avec Fernet, y compris la gestion des erreurs (mauvaise clé, données invalides).

### `file_utils`

-   **Manipulation de Fichiers** : Valide un large éventail de fonctions, incluant :
    -   La normalisation des noms de fichiers (`sanitize_filename`).
    -   La lecture et l'écriture de fichiers texte et JSON, avec une gestion robuste des erreurs (fichiers non trouvés, problèmes d'encodage, JSON mal formé).
    -   La conversion de Markdown en HTML.
    -   La vérification de l'existence et du type des chemins.
    -   L'archivage de fichiers.
    -   Les fonctions de chargement de plus haut niveau pour les extraits et les résultats d'analyse.

### `logging_utils`

-   **Configuration de la Journalisation** : Valide la fonction `setup_logging`. Les tests s'assurent que le niveau de log est correctement configuré, que les handlers sont gérés proprement (suppression des anciens, ajout des nouveaux), et que la verbosité des bibliothèques tierces est réduite comme attendu.

### `network_utils`

-   **Téléchargement de Fichiers** : Valide la fonction `download_file`. Les tests mockent les appels réseau pour simuler des téléchargements réussis, des erreurs HTTP, des problèmes de taille de fichier et des erreurs d'écriture, en vérifiant que les fichiers partiels sont correctement supprimés en cas d'échec.

### `system_utils`

-   **Exécution de Commandes Shell** : Valide le wrapper `run_shell_command` autour de `subprocess.run`. Les tests mockent le sous-processus pour vérifier la gestion des succès, des erreurs, des codes de retour et des exceptions comme `TimeoutExpired` ou `FileNotFoundError`.

### `text_utils`

-   **Traitement de Texte** : Valide les fonctions de base `normalize_text` (mise en minuscule, suppression de ponctuation, etc.) et `tokenize_text` (segmentation en mots).
