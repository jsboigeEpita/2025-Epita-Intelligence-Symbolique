# Périmètre de l'Audit Post-Refactorisation

**Date :** 22/06/2025
**Auteur :** Roo

## 1. Introduction

Ce document définit le périmètre de l'audit technique à mener suite à la phase intensive de refactorisation et de stabilisation du projet. Il consolide et dédoublonne l'ensemble des fichiers, modules, concepts architecturaux et dettes techniques qui ont été modifiés, analysés ou identifiés comme critiques dans les rapports suivants :
- `docs/commit_analysis_reports/diagnostic_report.md`
- `docs/commit_analysis_reports/targeted_analysis_summary.md`
- `docs/validation/validation_plan.md`
- Les 20 rapports de `docs/commit_analysis_reports/20250622_400_commits/`

L'objectif est de fournir une base de travail claire et exhaustive pour valider la stabilité, la maintenabilité et la robustesse de l'application.

---

## 2. Périmètre de l'Audit

### 2.1. Architecture Web et Orchestration d'Application

| Élément | Description | Fichiers Clés |
| --- | --- | --- |
| **Pile Web ASGI/Uvicorn** | Migration de Flask/WSGI vers une architecture asynchrone pour la scalabilité. | `interface_web/app.py`, `interface_web/asgi.py` |
| **Gestionnaire `lifespan` ASGI** | Implémentation du cycle de vie de l'application pour une gestion propre des ressources. | `interface_web/app.py` |
| **Wrapper `WsgiToAsgi`** | Couche de compatibilité pour intégrer d'anciens composants WSGI. | `interface_web/app.py` |
| **Orchestrateur Web Unifié** | Script central pour démarrer/arrêter l'ensemble de l'application (backend, frontend, E2E). | `scripts/apps/webapp/unified_web_orchestrator.py` |
| **Gestionnaire de Backend** | Logique de démarrage du serveur backend, utilisant `activate_project_env.ps1`. | `scripts/apps/webapp/backend_manager.py` |
| **Gestionnaire de Frontend** | Stratégie "build & serve" pour fiabiliser le démarrage du frontend React pour les tests. | `scripts/apps/webapp/frontend_manager.py`, `package.json` |
| **Runner de Tests Playwright** | Exécuteur unifié pour les tests E2E Python et JavaScript. | `scripts/apps/webapp/playwright_runner.py` |

### 2.2. Moteur d'Orchestration d'Analyse (Core)

| Élément | Description | Fichiers Clés |
| --- | --- | --- |
| **Moteur d'Orchestration à Stratégies** | Refactorisation du moteur monolithique vers un design pattern "Strategy". | `argumentation_analysis/orchestration/engine/` |
| **Orchestrateur Principal** | `MainOrchestrator` qui délègue les tâches aux différentes stratégies. | `argumentation_analysis/orchestration/engine/main_orchestrator.py` |
| **Façade d'Orchestration (Strangler Fig)** | Ancien pipeline conservé comme façade pour une migration progressive. | `argumentation_analysis/pipelines/unified_orchestration_pipeline.py` |

### 2.3. Architecture des Agents

| Élément | Description | Fichiers Clés |
| --- | --- | --- |
| **Décomposition de `WatsonJTMSAgent`** | Division de l'agent monolithique en services spécialisés (SRP). | `argumentation_analysis/agents/watson_jtms/` |
| **Services Spécialisés** | `ConsistencyChecker`, `FormalValidator`, `CritiqueEngine`, `SynthesisEngine`. | `argumentation_analysis/agents/watson_jtms/service/` |
| **Standardisation de l'API des Agents** | Harmonisation de l'interface des agents (`invoke`/`invoke_single`). | `argumentation_analysis/agents/core/`, `argumentation_analysis/agents/` |

### 2.4. Infrastructure de Test et Fiabilisation

| Élément | Description | Fichiers Clés |
| --- | --- | --- |
| **Isolation des Tests JVM** | Exécution des tests JVM dans des subprocessus pour éviter les crashs fatals. | `tests/conftest.py`, `tests/fixtures/integration_fixtures.py` |
| **Répertoire de Tests E2E Unifié** | Centralisation de tous les tests End-to-End. | `tests/e2e/` |
| **Serveur de Test Frontend** | Utilisation de `http.server` de Python pour servir les "builds" statiques React. | `scripts/apps/webapp/frontend_manager.py` |
| **Allocation Dynamique de Ports** | Système pour éviter les conflits de ports en CI/CD. | `scripts/utils/port_manager.py` |

### 2.5. Environnement, Configuration et Dette Technique

| Élément | Description | Fichiers Clés |
| --- | --- | --- |
| **Script d'Environnement Centralisé** | Point d'entrée unique et obligatoire pour configurer l'environnement. | `activate_project_env.ps1` |
| **Gestion des Dépendances** | Fichier Conda unifié pour maîtriser les dépendances (ex: OpenMP). | `environment.yml` |
| **Bibliothèque `semantic-kernel`** | Source d'instabilité majeure nécessitant une surveillance continue. | `environment.yml`, tous les agents |
| **Communication par Fichier (Dette)** | Utilisation de `logs/frontend_url.txt` à remplacer par des variables d'environnement. | `scripts/apps/webapp/playwright_runner.py`, `playwright.config.js` |
| **Centralisation de la Configuration (Cible)** | Effort pour extraire les valeurs hardcodées (ports, URLs) vers des fichiers de config. | `config/` (à créer/utiliser) |

### 2.6. Documentation Technique

| Élément | Description | Fichiers Clés |
| --- | --- | --- |
| **Documentation de Conception** | Document principal reflétant la nouvelle architecture. | `docs/sherlock_watson/guide_unifie_sherlock_watson.md` |
| **Rapports d'Analyse et de Validation** | Justification et planification des changements effectués. | `docs/commit_analysis_reports/`, `docs/validation/` |