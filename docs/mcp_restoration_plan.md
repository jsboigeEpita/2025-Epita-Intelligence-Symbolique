# Restauration de la fonctionnalité MCP

## Analyse de la Situation

L'analyse de l'historique du projet et de la base de code actuelle révèle plusieurs points clés concernant la fonctionnalité du Model-Context-Protocol (MCP) :

*   **Origine :** La fonctionnalité a été initialement introduite dans le cadre d'une Pull Request soumise par un groupe d'étudiants.
*   **Dépendance manquante :** Le cœur du problème réside dans l'absence de la bibliothèque `mcp` (ou `FastMCP`). Cette dépendance, cruciale pour le serveur MCP, n'a pas été incluse dans la PR, probablement parce qu'il s'agissait d'une bibliothèque développée localement et non publiée sur un registre de paquets public.
*   **Tests non fonctionnels :** Des tests unitaires et d'intégration existent pour la fonctionnalité MCP. Cependant, ils échouent systématiquement en raison de l'erreur `ModuleNotFoundError` pour la dépendance `mcp`, ce qui empêche toute validation automatisée.

## Plan de Restauration

Pour restaurer la fonctionnalité MCP et la rendre à nouveau opérationnelle, une approche méthodique en plusieurs étapes est nécessaire.

### Étape 1 : Récupération du code source de `mcp`/`FastMCP`

L'obtention du code source de la bibliothèque est le prérequis indispensable. Deux approches sont envisageables :

*   **Approche A (Idéale) : Contacter les auteurs originaux**
    *   **Action :** Tenter de retrouver et de contacter les étudiants auteurs de la PR initiale.
    *   **Objectif :** Obtenir le code source original et complet de la bibliothèque `mcp`/`FastMCP`. Cela garantirait une compatibilité maximale et réduirait l'effort d'intégration.

*   **Approche B (Alternative) : Rétro-ingénierie**
    *   **Action :** Si l'approche A échoue, recréer une implémentation minimale et fonctionnelle de la bibliothèque en se basant sur les éléments disponibles.
    *   **Sources d'information :**
        *   Le code du serveur : `services/mcp_server/main.py`
        *   Les tests existants : `tests/` (pour comprendre les interfaces et les comportements attendus).
        *   La documentation d'intégration : `docs/projets/sujets/aide/GUIDE_INTEGRATION_PROJETS.md`.
    *   **Implémentation :** Le nouveau code source de la bibliothèque sera placé dans un répertoire dédié : `libs/mcp`.

### Étape 2 : Intégration de la bibliothèque

Une fois le code source disponible (`libs/mcp`), il devra être correctement intégré pour que l'interpréteur Python puisse le trouver.

*   **Action :** Modifier la configuration du projet pour inclure le répertoire `libs` dans le `PYTHONPATH` lors de l'exécution et des tests.
*   **Méthode :** Ajouter `libs` au chemin de recherche, par exemple via une modification du fichier `setup.py`, `pyproject.toml`, ou en configurant `pytest.ini` pour les sessions de test.

### Étape 3 : Réparation des tests

Avec la bibliothèque en place, les tests existants serviront de guide pour la validation et la correction.

*   **Action :** Lancer la suite de tests complète relative au MCP.
*   **Processus :** Analyser les erreurs (autres que `ModuleNotFoundError`) et corriger le code de manière itérative.
*   **Objectif :** Obtenir un passage réussi de 100% des tests liés au MCP, assurant que l'implémentation (recréée ou originale) est conforme aux attentes initiales.

### Étape 4 : Validation fonctionnelle

Une dernière vérification manuelle permettra de confirmer que le système est pleinement opérationnel.

*   **Action :** Démarrer le serveur MCP localement.
*   **Test :** Exécuter une commande ou un script client simple (par exemple, un `curl` ou un petit client Python) pour envoyer une requête basique au serveur.
*   **Objectif :** Vérifier que le serveur démarre sans erreur et qu'il retourne une réponse correcte et attendue, validant ainsi la restauration de bout en bout.