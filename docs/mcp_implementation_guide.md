# Guide d'Implémentation Technique pour la Restauration de MCP

Ce document fournit les étapes techniques et les commandes pour mettre en œuvre le plan de restauration de la bibliothèque MCP, en se basant sur l'Approche B (Rétro-ingénierie) du plan de restauration.

## Étape 1 : Récupération du code (Approche B : Rétro-ingénierie)

Cette approche consiste à recréer la structure de base de la bibliothèque `mcp` et sa classe principale `FastMCP`.

1.  **Créer la structure des répertoires et des fichiers :**

    Exécutez les commandes suivantes pour créer l'arborescence nécessaire :

    ```bash
    mkdir -p libs/mcp/server
    touch libs/mcp/__init__.py
    touch libs/mcp/server/__init__.py
    touch libs/mcp/server/fastmcp.py
    ```

2.  **Définir la structure de la classe `FastMCP` :**

    Le fichier [`libs/mcp/server/fastmcp.py`](libs/mcp/server/fastmcp.py) doit contenir la classe `FastMCP`. En se basant sur son utilisation dans `services/mcp_server/main.py`, la classe devra implémenter les méthodes suivantes :
    *   `__init__(self, ...)`: Pour l'initialisation.
    *   `tool(self, ...)`: Pour décorer et enregistrer de nouveaux outils.
    *   `run(self, ...)`: Pour démarrer le serveur et écouter les requêtes.

## Étape 2 : Intégration avec Pytest

Pour que l'environnement de test reconnaisse la nouvelle bibliothèque `libs/mcp`, il est nécessaire de mettre à jour la configuration de `pytest`.

1.  **Modifier le fichier `pytest.ini` :**

    Ajoutez la configuration `pythonpath` suivante au fichier `pytest.ini` pour inclure les répertoires `.` et `libs` dans le chemin de recherche des modules Python.

    ```ini
    [pytest]
    pythonpath = . libs
    ```

## Étape 3 : Réparation des tests

Une fois la bibliothèque et la configuration de `pytest` en place, lancez les tests spécifiques au serveur MCP pour identifier et corriger les régressions.

1.  **Exécuter les tests pertinents :**

    Utilisez la commande suivante pour cibler uniquement les tests unitaires et d'intégration liés au serveur MCP :

    ```bash
    pytest tests/unit/services/test_mcp_server.py tests/integration/services/test_mcp_server_integration.py
    ```

## Étape 4 : Validation fonctionnelle

Après avoir corrigé les tests, l'étape finale consiste à valider que le serveur MCP démarre et fonctionne correctement en mode autonome.

1.  **Démarrer le serveur MCP :**

    Exécutez le script principal du serveur pour vous assurer qu'il se lance sans erreur.

    ```bash
    python services/mcp_server/main.py