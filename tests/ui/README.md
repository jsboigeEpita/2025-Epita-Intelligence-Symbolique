# Tests du Module UI

## Objectif

Ce répertoire contient les tests pour les composants liés à la logique de l'interface utilisateur (UI) et à la gestion des données sous-jacentes. Bien que nommés "UI", ces tests ne valident pas des éléments graphiques. Ils se concentrent sur les **opérations de fichiers, la récupération de données distantes, et la gestion de la configuration** qui sont essentielles au bon fonctionnement de l'application.

L'objectif est de garantir la robustesse et la fiabilité des mécanismes de manipulation de données, incluant la lecture, l'écriture, le chiffrement, la mise en cache et la récupération depuis des sources externes.

## Workflows et Fonctionnalités Testés

Les tests de ce répertoire couvrent les fonctionnalités suivantes :

1.  **Persistance des Définitions d'Extraction (`test_extract_definition_persistence.py`)**
    *   **Description :** Valide la sauvegarde et le chargement des fichiers de configuration (`extract_definitions.json`) qui décrivent comment extraire des données de diverses sources.
    *   **Scénarios Clés :**
        *   Sauvegarde et chargement de définitions dans un fichier chiffré.
        *   Gestion des erreurs : clé de chiffrement incorrecte, fichier non trouvé, fichier mal formé.
        *   Assure que le processus de sérialisation et de désérialisation des objets de configuration est fiable.
    *   **Prérequis :** Utilise un environnement de test temporaire créé par `pytest` pour les opérations de fichiers.

2.  **Utilitaires de l'UI (`test_utils.py`)**
    *   **Description :** Contient une suite de tests complète pour un ensemble de fonctions utilitaires critiques pour l'UI.
    *   **Fonctionnalités Validées :**
        *   **Récupération de Texte :** Teste la fonction `get_full_text_for_source` qui orchestre la récupération de contenu depuis des URLs en utilisant différentes stratégies (téléchargement direct, services externes comme Jina ou Tika).
        *   **Gestion du Cache :** Valide le système de cache pour éviter les téléchargements répétitifs. Les tests couvrent la création des fichiers de cache, la sauvegarde, le chargement et la gestion des erreurs (cache manquant, erreurs de lecture/écriture).
        *   **Opérations de Fichiers (Sauvegarde) :** Teste la fonction `save_extract_definitions` dans des scénarios plus complexes, notamment l'intégration du texte complet (`embed_full_text`) dans le fichier de configuration, ce qui implique de le récupérer si nécessaire.
        *   **Chiffrement :** Tests de base pour les fonctions d'encapsulation du chiffrement/déchiffrement.
        *   **Construction d'URL :** Vérifie que la fonction `reconstruct_url` assemble correctement les URLs à partir de leurs différentes parties.

## Prérequis de Lancement

*   **Dépendances :** Les tests nécessitent `pytest` et les bibliothèques listées dans `requirements.txt`, notamment `cryptography`.
*   **Environnement Isolé :** Les tests sont conçus pour être exécutés dans un environnement isolé. Toutes les interactions avec le système de fichiers sont effectuées dans des répertoires temporaires gérés par `pytest`.
*   **Mocks :** Les dépendances externes (services réseau, API Jina/Tika) sont systématiquement simulées (*mocked*). **Aucune connexion réseau ou clé d'API n'est nécessaire** pour lancer ces tests.
*   **Exécution :** Lancez les tests avec la commande `pytest` depuis la racine du projet.