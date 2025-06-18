# Cartographie de l'Architecture de l'Application Web

## 1. Vue d'Ensemble

L'application web constitue un point d'entrée majeur pour interagir avec les fonctionnalités d'analyse argumentative du projet. Elle fournit une interface utilisateur permettant de soumettre des textes, de configurer des options d'analyse et de visualiser les résultats de manière structurée.

## 2. Point d'Entrée Canonique et Lancement

Après la phase de stabilisation, le lancement de l'application web et de ses dépendances a été consolidé en un **point d'entrée unique et fiable**.

-   **Orchestrateur Principal :** [`project_core/webapp_from_scripts/unified_web_orchestrator.py`](project_core/webapp_from_scripts/unified_web_orchestrator.py)

Toute interaction avec l'application (lancement, tests, etc.) **doit** passer par ce script. Il garantit que l'environnement est correctement configuré et que tous les composants (backend, frontend, tests) sont démarrés de manière cohérente.

### Commande de Référence

La commande suivante illustre l'utilisation standard pour lancer l'application en mode visible, avec le frontend, et en exécutant un jeu de tests spécifiques. Elle a été utilisée pour la validation finale et sert d'exemple canonique :

```powershell
powershell -File ./activate_project_env.ps1 -CommandToRun "python project_core/webapp_from_scripts/unified_web_orchestrator.py --visible --frontend --tests tests/e2e/python/test_argument_analyzer.py"
```

## 3. Contexte Technique : Corrections Clés Post-Stabilisation

L'état actuel de l'application intègre plusieurs corrections critiques issues de la phase de test intensive :

-   **Chargement Asynchrone du Backend :** Pour améliorer la réactivité et la robustesse, le chargement des modèles lourds au démarrage du backend a été rendu asynchrone. Cela évite les timeouts et permet à l'application de démarrer plus rapidement.
-   **Fiabilisation de la Connexion API :** La communication entre le frontend et le backend a été stabilisée pour résoudre des problèmes de connexion intermittents, garantissant une transmission de données fiable pour l'analyse.

Ces modifications sont désormais gérées nativement par l'orchestrateur.

## 4. Composant Principal : L'Orchestrateur Unifié

Le composant central de l'architecture reste le `UnifiedWebOrchestrator`.

-   **Responsabilités Clés :**
    -   **Gestion du Cycle de Vie :** Il contrôle le démarrage, l'arrêt et le nettoyage de tous les processus liés à l'application web.
    -   **Gestion du Backend :** Il instancie et lance le `BackendManager`, qui est responsable du démarrage de l'application Flask principale.
    -   **Gestion du Frontend :** Il gère le serveur de développement React (si activé).
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

-   **Configuration de l'Orchestrateur :** La configuration est gérée via des fichiers YAML et peut être surchargée par des arguments en ligne de commande directement passés à `unified_web_orchestrator.py` (par exemple, `--visible`, `--frontend`, `--tests`).

## 8. Diagramme de Flux Architectural

```mermaid
graph TD
    subgraph "Phase 1: Lancement Unifié"
        A[Utilisateur exécute `unified_web_orchestrator.py` via PowerShell] --> B{UnifiedWebOrchestrator};
        B --> C[BackendManager lance l'app Flask (chargement asynchrone)];
        B --> D[FrontendManager lance le serveur React (si activé)];
        B --> E[Playwright Test Runner (si activé)];
    end

    subgraph "Phase 2: Requête d'Analyse"
        F[Utilisateur soumet un texte via le Navigateur] --> G{Application Flask (`app.py`)};
        G -- "Requête sur /analyze" --> H[ServiceManager];
        H -- "Appel à `analyze_text()`" --> I[Pipelines d'Analyse (Coeur du projet)];
        I --> H;
        H --> G;
        G -- "Réponse JSON" --> F;
    end

    subgraph "Composants d'Analyse"
        H -.-> J[Orchestrateurs Spécialisés];
        H -.-> K[Gestionnaires Hiérarchiques];
    end