# Cartographie de l'Architecture de l'Application Web

## 1. Vue d'Ensemble

L'application web constitue un point d'entrée majeur pour interagir avec les fonctionnalités d'analyse argumentative du projet. Elle fournit une interface utilisateur permettant de soumettre des textes, de configurer des options d'analyse et de visualiser les résultats de manière structurée.

## 2. Flux de Lancement de l'Application

Le processus de démarrage est entièrement unifié et géré par un script central :

-   **Script de Démarrage :** [`scripts/apps/start_webapp.py`](scripts/apps/start_webapp.py)
-   **Rôles :**
    -   Active automatiquement l'environnement Conda `projet-is` pour garantir que toutes les dépendances sont disponibles.
    -   Lance l'orchestrateur web unifié, qui est le véritable chef d'orchestre de l'application.

## 3. Composant Principal : L'Orchestrateur Unifié

Le composant central de l'architecture est le `UnifiedWebOrchestrator`, situé dans [`project_core/webapp_from_scripts/unified_web_orchestrator.py`](project_core/webapp_from_scripts/unified_web_orchestrator.py).

-   **Responsabilités Clés :**
    -   **Gestion du Cycle de Vie :** Il contrôle le démarrage, l'arrêt et le nettoyage de tous les processus liés à l'application web.
    -   **Gestion du Backend :** Il instancie et lance le `BackendManager`, qui est responsable du démarrage de l'application Flask principale.
    -   **Gestion du Frontend :** De manière optionnelle, il peut lancer un `FrontendManager` pour un serveur de développement React, bien que l'interface actuelle soit principalement rendue via les templates Flask.
    -   **Tests d'Intégration :** Il intègre et exécute des tests de bout en bout à l'aide de **Playwright**.
    -   **Configuration et Journalisation :** Il centralise la lecture de la configuration et la gestion des logs pour toute la session.

## 4. Architecture du Backend (Application Flask)

Le backend est une application web standard basée sur Flask, dont le code source principal se trouve dans [`interface_web/app.py`](interface_web/app.py).

-   **Point d'Entrée d'Analyse :** La route `POST /analyze` ([`interface_web/app.py:174`](interface_web/app.py:174)) est le point d'entrée principal pour soumettre un texte et recevoir une analyse complète.

-   **Routes Principales :**
    -   `GET /`: Affiche la page d'accueil de l'application.
    -   `POST /analyze`: Reçoit le texte et les options, puis délègue l'analyse au `ServiceManager`.
    -   `GET /status`: Fournit un diagnostic sur l'état de santé des différents services.
    -   `GET /api/examples`: Retourne des exemples de texte pour faciliter les tests et les démonstrations.

-   **Intégration du Module JTMS :**
    -   L'application intègre des fonctionnalités spécifiques au **JTMS (Justification and Truth Maintenance System)** via un blueprint Flask.
    -   Le blueprint, défini dans [`interface_web/routes/jtms_routes.py`](interface_web/routes/jtms_routes.py), est enregistré sous le préfixe d'URL `/jtms`.

## 5. Architecture du Frontend

L'interface utilisateur est principalement rendue côté serveur, en utilisant le moteur de templates Jinja2 de Flask.

-   **Fichiers de Templates :** Situés dans le répertoire [`interface_web/templates/`](interface_web/templates/).
    -   [`index.html`](interface_web/templates/index.html) est la page principale.
    -   Des templates spécifiques comme [`jtms/dashboard.html`](interface_web/templates/jtms/dashboard.html) sont dédiés à l'interface JTMS.

-   **Fichiers Statiques :** Les ressources CSS et JavaScript sont servies depuis [`interface_web/static/`](interface_web/static/).
    -   On note la présence de [`jtms_dashboard.js`](interface_web/static/js/jtms_dashboard.js), indiquant une logique d'interactivité côté client pour le tableau de bord JTMS, probablement pour gérer des communications en temps réel (WebSocket) ou des mises à jour dynamiques.

## 6. Points d'Intégration avec le Cœur du Projet

Le lien crucial entre l'interface web (la façade) et les algorithmes d'analyse (le cerveau) est le **`ServiceManager`**.

-   **Le Pont `ServiceManager` :**
    -   Dans [`interface_web/app.py`](interface_web/app.py:108), une instance de `ServiceManager` est créée au démarrage de l'application.
    -   La route `/analyze` utilise cette instance pour appeler la méthode `analyze_text()`.
    -   C'est cet appel qui déclenche les pipelines d'analyse complexes (stratégique, tactique, opérationnel), en passant le texte fourni par l'utilisateur.

## 7. Fichiers de Configuration

La configuration de l'application est flexible et séparée du code.

-   **Configuration de l'Orchestrateur :** [`scripts/apps/config/webapp_config.yml`](scripts/apps/config/webapp_config.yml). Ce fichier YAML définit des paramètres essentiels comme les ports, les chemins, les timeouts, et les options d'activation pour les différents composants (backend, frontend, Playwright).

-   **Surcharge par Ligne de Commande :** Le script de lancement [`scripts/apps/start_webapp.py`](scripts/apps/start_webapp.py) permet de surcharger dynamiquement certains paramètres de la configuration via des arguments CLI (par exemple, `--visible`, `--backend-only`).

## 8. Diagramme de Flux Architectural

```mermaid
graph TD
    subgraph "Phase 1: Lancement"
        A[Utilisateur exécute `start_webapp.py`] --> B{UnifiedWebOrchestrator};
        B --> C[BackendManager lance l'app Flask];
        B --> D[FrontendManager lance le serveur React (si activé)];
    end

    subgraph "Phase 2: Requête d'Analyse"
        E[Utilisateur soumet un texte via le Navigateur] --> F{Application Flask (`app.py`)};
        F -- "Requête sur /analyze" --> G[ServiceManager];
        G -- "Appel à `analyze_text()`" --> H[Pipelines d'Analyse (Coeur du projet)];
        H --> G;
        G --> F;
        F -- "Réponse JSON" --> E;
    end

    subgraph "Composants d'Analyse"
        G -.-> I[Orchestrateurs Spécialisés];
        G -.-> J[Gestionnaires Hiérarchiques];
    end