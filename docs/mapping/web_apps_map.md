# Cartographie des Applications Web et des Tests

Ce document décrit l'architecture des composants web, l'orchestration des services et l'interaction avec les suites de tests.

## 1. Architecture de l'Application Web (`interface_web/`)

L'application principale est une application **Flask**, située dans le répertoire `interface_web/`.

- **Point d'entrée** : [`app.py`](interface_web/app.py:0) initialise et lance l'application Flask.
- **Routes** : Le sous-répertoire [`routes/`](interface_web/routes/) définit les points de terminaison de l'API et les vues web.
- **Services** : Le sous-répertoire [`services/`](interface_web/services/) contient la logique métier, y compris l'intégration avec d'autres composants comme JTMS via WebSocket.
- **Contenus Statiques** : Le répertoire [`static/`](interface_web/static/) héberge les fichiers CSS et JavaScript.
- **Templates** : Le répertoire [`templates/`](interface_web/templates/) contient les modèles HTML (Jinja2) pour le rendu des pages.

## 2. Orchestration et Configuration (`scripts/webapp/`)

La gestion des services web pour le développement et les tests est centralisée par des scripts.

- **Orchestrateur** : `scripts/webapp/unified_web_orchestrator.py` est le script principal pour démarrer, arrêter et gérer l'ensemble des services web en mode normal ou test.
- **Configuration** : Le fichier [`config/webapp_config.yml`](scripts/webapp/config/webapp_config.yml:0) contient les paramètres de configuration de l'application web, tels que les ports, les hôtes et les modes de fonctionnement.

## 3. Suites de Tests

Le projet utilise deux principales suites de tests pour valider les applications web.

### 3.1. Tests `pytest` (`tests/unit/webapp/`)

Ces tests sont axés sur la validation unitaire et d'intégration des composants backend.

- **Localisation** : Les tests se trouvent dans `tests/unit/webapp/`.
- **Cible** : Ils valident la logique des services, des gestionnaires (`backend_manager`, `frontend_manager`), et la configuration de l'orchestrateur.
- **Exécution** : Ils sont lancés avec la commande `pytest tests/unit/webapp/`.

### 3.2. Tests `Playwright` (`tests_playwright/`)

Ces tests effectuent une validation fonctionnelle et de bout en bout (end-to-end) en simulant des interactions utilisateur dans un navigateur.

- **Localisation** : Les tests et leur configuration sont dans `tests_playwright/`.
- **Cible** : Ils interagissent directement avec l'interface web rendue par le serveur Flask pour tester le flux utilisateur, l'affichage des éléments et les fonctionnalités JavaScript.
- **Exécution** : Ils sont lancés via une commande `playwright test`.

## 4. Flux d'Interaction pour la Validation

1.  L'**orchestrateur unifié** (`unified_web_orchestrator.py`) est exécuté en mode test. Il démarre l'application Flask et tout autre service dépendant.
2.  La suite de tests **`pytest`** est exécutée pour valider l'intégrité du backend.
3.  La suite de tests **`Playwright`** est lancée, interagissant avec l'application web en direct pour valider le comportement du frontend et les parcours utilisateur.