# Analyse des Régressions E2E Post-Réparation (2025-08-31)

Ce document analyse les échecs de la suite de tests End-to-End (E2E) survenus après la réparation documentée dans `2025-08-31_reparation_suite_e2e_playwright.md`.

## 1. Contexte

Après la correction qui a résolu le problème de tests systématiquement marqués comme "SKIPPED", la suite de tests a révélé un grand nombre d'échecs (15+). L'analyse du rapport `tests/e2e/report.json` a été menée pour en identifier les causes.

## 2. Catégorisation des Échecs

Une seule catégorie d'échec a été identifiée, impactant tous les tests défaillants.

### Catégorie 1 : Échecs de Connexion (ECONNREFUSED)

*   **Description de l'échec :** Tous les tests qui interagissent avec les services web (API backend ou interface frontend) échouent avec une erreur `ECONNREFUSED`. Cela signifie que la connexion TCP a été refusée par la machine cible.

*   **Logs typiques :**
    ```
    Error: apiRequestContext.get: connect ECONNREFUSED ::1:5004
    ```
    ou
    ```
    Error: page.goto: net::ERR_CONNECTION_REFUSED at http://localhost:3000/
    ```

*   **Tests Concernés :**
    *   **Suite `api-backend.spec.js`**:
        *   Health Check - Vérification de l'état de l'API
        *   Test d'analyse argumentative via API
        *   Test de détection de sophismes
        *   Test de construction de framework
        *   Test de validation d'argument
        *   Test des endpoints avec données invalides
        *   Test des différents types d'analyse logique
        *   Test de performance et timeout
        *   Test de l'interface web backend via navigateur
        *   Test CORS et headers
        *   Test de la limite de requêtes simultanées
    *   **Suite `flask-interface.spec.js`**:
        *   Chargement de la page principale
        *   Interaction avec les exemples prédéfinis
        *   Test d'analyse avec texte simple
        *   Test de validation des limites
        *   Test de la récupération d'exemples via API
        *   Test responsive et accessibilité

*   **Hypothèse sur la Cause Racine :**
    La cause la plus probable est que l'orchestrateur de tests (`project_core/test_runner.py` ou un script associé) ne démarre pas les serveurs web nécessaires (l'API Flask et le serveur de développement React/Vite) avant de lancer la commande `pytest` pour les tests E2E. La réparation précédente a peut-être corrigé la logique de *skip* des tests, mais a omis ou altéré l'étape de démarrage des services.

*   **Étapes pour Reproduire :**
    1.  S'assurer qu'aucun serveur n'est en cours d'exécution sur les ports 3000 et 5004.
    2.  Lancer un seul test E2E qui dépend d'une connexion, par exemple :
        ```bash
        pytest tests/e2e/js/api-backend.spec.js -k "Health Check"
        ```
    3.  Observer l'échec avec l'erreur `ECONNREFUSED`.

## 3. Correction Appliquée

Pour résoudre les échecs de connexion `ECONNREFUSED`, le script `project_core/test_runner.py` a été modifié pour orchestrer correctement le démarrage des services web avant l'exécution des tests E2E.

Les modifications principales sont :
1.  **Démarrage Explicite des Deux Services :** La classe `ServiceManager` a été enrichie pour démarrer non seulement le backend (API Flask/Uvicorn) mais aussi le frontend (serveur de développement React/Vite) en tant que sous-processus distincts.
2.  **Configuration Correcte des Chemins et Commandes :** 
    - Le chemin vers le répertoire du frontend a été corrigé pour pointer vers `services/web_api/interface-web-argumentative`.
    - La commande de démarrage du frontend a été mise à jour de `npm run dev` à `npm start` pour correspondre au `package.json` du projet.
3.  **Polling Robuste :** La logique d'attente a été mise à jour pour vérifier que les ports des **deux** services (`5004` pour le backend, `3000` pour le frontend) sont ouverts et répondent avant de permettre à `pytest` de démarrer.
4.  **Terminaison des Processus :** Le script assure maintenant que les sous-processus des deux serveurs sont correctement terminés à la fin de la suite de tests, même en cas d'échec, pour éviter les processus orphelins.

Ces changements garantissent que l'environnement de test est dans un état stable et opérationnel avant que les interactions E2E ne soient tentées, éliminant ainsi la cause racine des échecs de connexion.
