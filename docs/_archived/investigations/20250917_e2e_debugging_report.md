# Rapport d'Investigation : Débogage des Tests E2E (17/09/2025)

## Contexte

Suite à des blocages systématiques (timeouts) de la suite de tests E2E, une investigation approfondie a été menée. Ce document synthétise la chronologie des actions, le diagnostic final et les recommandations pour la suite.

## Synthèse de l'Investigation

### Chronologie des Tentatives de Débogage

1.  **Exécution Initiale :** Blocage systématique sans logs.
2.  **Mise en place d'un Superviseur :** Création d'un wrapper avec timeout pour capturer les logs.
3.  **Correctif 1 (Variables d'environnement) :** Résolution d'un problème de propagation de `OPENAI_API_KEY`. Le blocage a persisté.
4.  **Correctif 2 (Nettoyage des ports) :** Résolution d'une erreur `EADDRINUSE` sur le port du backend. Le blocage a persisté.
5.  **Correctif 3 (Fiabilisation avec `psutil`) :** Remplacement d'un appel `npx` externe par une solution Python native. Le blocage a persisté.
6.  **Instrumentation `pytest` :** Ajout de logging verbeux pour tracer l'exécution des tests.
7.  **Isolation du Test :** Identification et exécution isolée de `test_api_dung_integration.py`, qui a continué de provoquer le timeout.

### Diagnostic Actuel

*   **Source du problème :** Le blocage est localisé avec certitude dans le code métier du backend, spécifiquement celui appelé par l'endpoint **`/api/v1/framework/analyze`**.
*   **Hypothèse technique :** Une boucle infinie ou un deadlock se produit dans la logique d'analyse du framework, probablement dans le service `FrameworkService` ou une de ses dépendances.
*   **Impact :** L'intégralité de la suite de tests E2E est inutilisable tant que ce problème n'est pas résolu.

## Recommandations pour la Suite

### Stratégie de Journalisation

Il est impératif d'ajouter une journalisation (logging) détaillée dans le code du backend, en particulier au sein des méthodes du `FrameworkService` qui sont impliquées dans le traitement de l'endpoint `/api/v1/framework/analyze`. Les logs doivent tracer l'entrée et la sortie de chaque fonction critique.

### Points d'Instrumentation Critiques

*   Le début et la fin de la méthode principale du service qui gère la route `/api/v1/framework/analyze`.
*   Les boucles de traitement de données (arguments, relations d'attaque, etc.).
*   Les appels à des services externes ou à des bibliothèques complexes depuis ce service.

### Approche "Fail Early"

Il est recommandé de modifier temporairement le test `test_api_dung_integration.py` pour qu'il utilise un timeout très court (ex: 10 secondes) directement au niveau du client HTTP (`httpx` ou `requests`). Cela permettra d'itérer plus rapidement sur les correctifs du backend sans attendre l'expiration du timeout global de 30 minutes.

## Grounding pour l'Orchestrateur (SDDD)

Une recherche sémantique avec la requête `\"architecture backend Flask framework analysis deadlock\"` est recommandée pour la prochaine phase de débogage afin d'identifier les documents d'architecture pertinents qui pourraient éclairer la logique métier complexe à l'origine du blocage.