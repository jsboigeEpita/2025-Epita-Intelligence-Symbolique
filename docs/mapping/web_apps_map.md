# Cartographie de l'Architecture des Applications Web

Ce document détaille l'architecture des composants web et des suites de tests associées.

## 1. Architecture des Services Web

L'application web principale est construite avec Flask et est située dans le répertoire `interface_web/`.

### 1.1. `interface_web/`

*   **`app.py`**: C'est le point d'entrée principal de l'application Flask. Il initialise l'application, configure les routes et gère le cycle de vie de l'application.

*   **`api/`**: Ce répertoire contient la logique d'intégration avec les services externes et les API.
    *   `jtms_integration.py`: Gère la communication avec le système JTMS.

*   **`routes/`**: Définit les différentes routes (URLs) de l'application.
    *   `jtms_routes.py`: Contient les routes spécifiques à l'interface JTMS.

*   **`services/`**: Implémente la logique métier et les services de l'application.
    *   `jtms_websocket.py`: Gère la communication WebSocket pour les mises à jour en temps réel.

*   **`static/`**: Contient les fichiers statiques.
    *   `css/`: Feuilles de style CSS.
    *   `js/`: Fichiers JavaScript pour l'interactivité côté client.

*   **`templates/`**: Modèles HTML utilisés pour rendre les pages web.
    *   `jtms/`: Modèles spécifiques à l'interface JTMS.
    *   `index.html`: Page d'accueil.

## 2. Architecture des Tests

Les tests sont divisés en deux catégories principales : les tests backend (`pytest`) et les tests end-to-end (`playwright`).

### 2.1. `tests/webapp/`

Ce répertoire contient les tests unitaires et d'intégration pour l'application Flask.

*   `__init__.py`: Fichier d'initialisation du module de test.

### 2.2. `tests_playwright/`

Ce répertoire contient les tests end-to-end qui simulent les interactions des utilisateurs avec l'interface web.

*   `node_modules/`: Dépendances pour Playwright.
*   `playwright-report/`: Rapports de test générés par Playwright.
*   `test-results/`: Résultats bruts des exécutions de test.