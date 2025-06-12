# Documentation : Orchestration de l'Application Web et Tests E2E

Ce document explique comment utiliser l'orchestrateur web unifié pour démarrer l'application (backend et frontend) et comment lancer les tests end-to-end (E2E) avec Playwright.

## 1. Contexte

L'application web est composée d'un backend (généralement une API FastAPI ou Flask) et d'un frontend (une application React ou Vue). L'orchestrateur unifié est conçu pour gérer le cycle de vie complet de l'application :
- Démarrage et arrêt du backend.
- Build et service du frontend.
- Exécution des tests d'intégration et E2E.

## 2. Script Principal

Le script d'orchestration principal est `scripts/webapp/unified_web_orchestrator.py`. Ce script est hautement configurable via un fichier YAML ou des arguments en ligne de commande.

## 3. Lancement des Tests Playwright

Les tests Playwright sont utilisés pour simuler l'interaction d'un utilisateur réel avec l'application dans un vrai navigateur.

Pour lancer les tests, vous devez utiliser une commande qui exécute le runner de tests Playwright. Bien que l'orchestrateur puisse le faire, une méthode plus directe est souvent utilisée pour les tests, en utilisant le pipeline dédié.

### Commande de Test

La commande standard pour lancer les tests est :
```bash
npx playwright test
```
Cette commande doit être exécutée depuis le répertoire racine du projet, car elle dépend du fichier de configuration `playwright.config.js` (ou `.ts`) qui s'y trouve.

Le script `scripts/pipelines/run_web_e2e_pipeline.py` automatise ce processus.

## 4. Génération d'une Trace de Démonstration

Pour générer une trace de démonstration "headed" (c'est-à-dire avec le navigateur visible), nous pouvons directement utiliser la commande `npx playwright test` avec l'option `--headed`.

```bash
npx playwright test --headed
```

Cette commande va :
1. Lancer un navigateur (Chromium par défaut).
2. Exécuter tous les scénarios de test définis dans le répertoire `tests_playwright`.
3. Afficher les interactions en temps réel.
4. Générer un rapport de test à la fin de l'exécution.