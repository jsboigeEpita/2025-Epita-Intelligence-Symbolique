# Documentation : Nouvel Orchestrateur de Tests E2E pour `run_tests.ps1`

**Date:** 2025-09-04
**Auteur:** Roo
**Contexte:** Ce document a été rédigé dans le cadre de la refonte visant à stabiliser l'exécution des tests E2E lancés via `run_tests.ps1`, conformément aux recommandations du document [`docs/testing_entrypoints_audit.md`](docs/testing_entrypoints_audit.md).

## 1. Contexte : Résoudre l'Instabilité des Tests E2E

L'audit des points d'entrée de test a identifié que le script `project_core/test_runner.py`, bien que puissant, souffrait d'instabilités lors de la gestion des services pour les tests E2E. Celles-ci se manifestaient par des blocages intermittents, rendant le pipeline de validation peu fiable pour les développeurs utilisant `run_tests.ps1`.

Pour pallier ce problème, un nouvel orchestrateur, plus léger et spécialisé, a été développé pour gérer **uniquement** le cas des tests E2E.

## 2. Architecture du Nouvel Orchestrateur

### 2.1. Philosophie

Le nouvel orchestrateur suit une philosophie simple : être un "chef d'orchestre" **asynchrone, non bloquant et résilient**. Il s'appuie entièrement sur la bibliothèque `asyncio` de Python pour gérer les processus et les entrées/sorties, ce qui constitue sa différence fondamentale avec l'approche `subprocess` synchrone de l'ancien runner.

-   **Fichier Clé** : [`scripts/orchestration/run_e2e_tests.py`](scripts/orchestration/run_e2e_tests.py)
-   **Point d'Entrée** : Le script est exclusivement invoqué par [`run_tests.ps1`](run_tests.ps1) lorsque l'option `-Type "e2e"` est utilisée.

### 2.2. Flux d'Exécution

Le script exécute les étapes suivantes de manière asynchrone :

1.  **Démarrage Simultané des Services** : Le backend (API Uvicorn) et le frontend (serveur de développement NPM) sont lancés en parallèle.
2.  **Redirection des Logs en Temps Réel** : Les logs de chaque service sont immédiatement streamés vers des fichiers dédiés dans le répertoire `_e2e_logs/`. Cela permet de voir instantanément pourquoi un service ne démarrerait pas, sans attendre la fin d'un timeout.
3.  **Health Check Asynchrone** : Le script sonde les ports des services (`5004` et `3000`) de manière non bloquante. Il attend que les services soient réellement prêts à accepter des connexions avant de continuer.
4.  **Lancement de Pytest** : Une fois les services prêts, la suite de tests `pytest` est lancée. Sa sortie est affichée en temps réel dans la console.
5.  **Nettoyage Robuste** : Que les tests réussissent ou échouent, le script garantit la terminaison de tous les processus qu'il a lancés (backend, frontend), évitant les processus "zombies".

## 3. Avantages et Justification

Ce nouvel orchestrateur est une implémentation directe de la stratégie de fiabilisation proposée par l'audit :

-   **Stabilité Accrue** : En éliminant les opérations bloquantes, on supprime la cause principale des gels intermittents.
-   **Débogage Amélioré** : Les logs en temps réel sont un atout majeur pour diagnostiquer rapidement les problèmes de démarrage des services.
-   **Conformité à l'Architecture Cible** : Il fait de `run_tests.ps1` un point d'entrée plus fiable et cohérent pour les développeurs, comme préconisé.
-   **Spécialisation** : En se concentrant uniquement sur le cas E2E, le script reste simple et maintenable.

## 4. Utilisation

L'utilisation pour le développeur reste inchangée. La complexité est absorbée par le système de scripting.

```powershell
# Lance les tests E2E via le nouvel orchestrateur asynchrone.
./run_tests.ps1 -Type "e2e"