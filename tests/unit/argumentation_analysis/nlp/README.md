# Tests Unitaires pour les Utilitaires NLP

## Objectif

Ce répertoire contient les tests unitaires pour les modules liés au traitement du langage naturel (NLP), et plus spécifiquement à la génération et à la gestion des "embeddings" (plongements sémantiques).

L'objectif est de garantir la fiabilité des fonctions qui interagissent avec des modèles de langage externes (via des API ou des bibliothèques locales) pour transformer du texte en vecteurs numériques, et de valider les processus de sauvegarde de ces données.

## Fonctionnalités Testées

### `embedding_utils`

-   **Génération d'Embeddings (`get_embeddings_for_chunks`)** :
    -   **Intégration avec les Modèles OpenAI** : Vérification que la fonction appelle correctement l'API d'OpenAI pour générer des embeddings lorsque le nom d'un modèle OpenAI est fourni.
    -   **Intégration avec les Modèles Sentence Transformers** : Validation de l'utilisation de la bibliothèque `sentence-transformers` pour générer des embeddings localement.
    -   **Gestion des Dépendances** : Test de la levée d'une `ImportError` si la bibliothèque requise (OpenAI ou Sentence Transformers) n'est pas installée, empêchant ainsi une exécution échouée.
    -   **Gestion des Erreurs d'API** : S'assure que les erreurs provenant de l'API d'OpenAI (ex: `APIError`) sont correctement gérées et propagées.

-   **Sauvegarde des Embeddings (`save_embeddings_data`)** :
    -   **Écriture de Fichier** : Vérification que les données d'embeddings (contenant les textes, les vecteurs et les métadonnées du modèle) sont correctement écrites dans un fichier JSON.
    -   **Création de Répertoire** : S'assure que le répertoire de destination est créé s'il n'existe pas.
    -   **Gestion des Erreurs d'E/S** : Test de la robustesse de la fonction face à des erreurs du système de fichiers (`IOError`, `OSError`) lors de la création du répertoire ou de l'écriture du fichier.

## Dépendances Clés

-   **`pytest`** : Utilisé comme framework de test, avec des fixtures pour fournir des données de test (morceaux de texte, données d'embeddings simulées).
-   **`unittest.mock`** : Essentiel pour ces tests afin d'isoler les fonctions des appels réseau et du système de fichiers.
    -   Les clients `OpenAI` et `SentenceTransformer` sont entièrement mockés pour simuler leurs réponses sans effectuer de réels appels coûteux ou nécessitant une connexion.
    -   Les interactions avec le système de fichiers (`pathlib.Path.mkdir`, `builtins.open`) sont mockées pour tester la logique de sauvegarde sans écrire de fichiers réels sur le disque.
