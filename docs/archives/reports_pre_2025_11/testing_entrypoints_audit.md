# Audit des Points d'Entrée pour l'Exécution des Tests

Ce document cartographie les différents scripts et mécanismes utilisés pour lancer les tests dans ce projet. Il met en évidence les différences d'approche, les technologies utilisées et le but de chaque point d'entrée.

---

## 1. Orchestrateur Centralisé (Approche Moderne)

### 1.1. `project_core/test_runner.py`

*   **Nom et Emplacement:** [`project_core/test_runner.py`](project_core/test_runner.py:1)
*   **Type de Tests Lancés:** Orchestrateur complet pour `unit`, `integration`, `functional`, `playwright`, et `e2e`. Il est configurable et gère des configurations distinctes pour chaque type.
*   **Mécanisme d'Activation de l'Environnement:** Autonome. Contient une classe `EnvironmentManager` capable d'activer un environnement `conda` directement depuis Python, le rendant indépendant des scripts shell.
*   **Commande(s) d'Exécution:** Construit et exécute des commandes `pytest` de manière programmatique, en ajoutant dynamiquement des options pour le parallélisme (`pytest-xdist`), les timeouts et Playwright.
*   **Dépendances d'Orchestration:** **Oui.** Utilise un `ServiceManager` pour démarrer et arrêter les serveurs `backend-flask` et `frontend-react` nécessaires pour les tests d'intégration et e2e. Il gère le cycle de vie complet des services.
*   **Objectif Général Supposé:** Le runner de tests unifié et multi-plateforme. C'est la solution cible pour exécuter tous les tests de manière cohérente et fiable.

### 1.2. `run_tests.sh`

*   **Nom et Emplacement:** [`run_tests.sh`](run_tests.sh:1) (racine)
*   **Type de Tests Lancés:** Flexible. Permet de choisir `unit`, `integration`, `validation`, ou `all` via des arguments CLI.
*   **Mécanisme d'Activation de l'Environnement:** Aucun. Il s'attend à ce que l'environnement Python soit déjà activé.
*   **Commande(s) d'Exécution:** Utilise une technique de `heredoc` pour exécuter un bloc de code Python qui invoque `project_core/test_runner.py`. C'est le principal point d'entrée Unix pour l'orchestrateur centralisé.
*   **Dépendances d'Orchestration:** Dépend de `project_core/test_runner.py`.
*   **Objectif Général Supposé:** Servir de point d'entrée en ligne de commande pratique et multi-plateforme (pour les systèmes Unix) pour l'orchestrateur Python.

---

## 2. Lanceurs Simples (Approche Wrapper)

### 2.1. `run_tests.ps1`

*   **Nom et Emplacement:** [`run_tests.ps1`](run_tests.ps1:1) (racine)
*   **Type de Tests Lancés:** Générique. Lance `pytest` sur un chemin de test optionnel.
*   **Mécanisme d'Activation de l'Environnement:** Délègue l'activation au script `activate_project_env.ps1`. Ne gère pas l'activation lui-même.
*   **Commande(s) d'Exécution:** `python -m pytest [TestPath]`.
*   **Dépendances d'Orchestration:** Aucune. Ne gère pas le cycle de vie des serveurs.
*   **Objectif Général Supposé:** Lancement simple et rapide des tests `pytest` pour les utilisateurs Windows, en s'assurant que l'environnement de base est activé. Il est beaucoup moins sophistiqué que son homologue `.sh`.

---

## 3. Scripts Autonomes et Spécifiques (Approche Silo)

### 3.1. `scripts/run_all_and_test.ps1`

*   **Nom et Emplacement:** [`scripts/run_all_and_test.ps1`](scripts/run_all_and_test.ps1:2)
*   **Type de Tests Lancés:** Uniquement un test fonctionnel spécifique: `tests/functional/test_logic_graph.py`.
*   **Mécanisme d'Activation de l'Environnement:** Active l'environnement via `activate_project_env.ps1` puis utilise `conda run` pour chaque commande.
*   **Commande(s) d'Exécution:** Lance `pytest` sur un seul fichier de test.
*   **Dépendances d'Orchestration:** **Oui.** Démarre manuellement les serveurs backend et frontend en utilisant des `Start-Job` PowerShell. Il implémente sa propre logique de *health check* pour attendre que les serveurs soient prêts.
*   **Objectif Général Supposé:** Script de test d'intégration plus ancien ou spécifique à un cas d'usage qui n'a pas été migré vers le `TestRunner` unifié. Représente une ancienne façon de faire.

### 3.2. `scripts/testing/test_playwright_headless.ps1`

*   **Nom et Emplacement:** [`scripts/testing/test_playwright_headless.ps1`](scripts/testing/test_playwright_headless.ps1:1)
*   **Type de Tests Lancés:** Tests e2e avec Playwright.
*   **Mécanisme d'Activation de l'Environnement:** Aucun environnement Python/Conda. Gère son propre écosystème Node.js/npm.
*   **Commande(s) d'Exécution:** `npx playwright test`.
*   **Dépendances d'Orchestration:** Gère le cycle de vie des dépendances `npm` et Playwright (`npx playwright install`), mais **ne démarre pas** les serveurs applicatifs. Il suppose qu'ils sont déjà en cours d'exécution.
*   **Objectif Général Supposé:** Runner complet et dédié pour les tests Playwright, avec une gestion fine de l'installation et de la génération de rapports. Fonctionne en silo par rapport aux tests Python.

---

## 4. Scripts de Diagnostic et de Secours

### 4.1. `scripts/diagnostic/test_validation_environnement.py`

*   **Nom et Emplacement:** [`scripts/diagnostic/test_validation_environnement.py`](scripts/diagnostic/test_validation_environnement.py:2)
*   **Type de Tests Lancés:** Pas un test d'application. Valide la configuration de l'environnement de développement.
*   **Mécanisme d'Activation de l'Environnement:** Aucun.
*   **Commande(s) d'Exécution:** Exécution directe du script Python.
*   **Dépendances d'Orchestration:** Aucune.
*   **Objectif Général Supposé:** Script de diagnostic pour vérifier rapidement la santé du projet (fichiers, répertoires, imports) avant de commencer à travailler.

### 4.2. `scripts/testing/test_runner_simple.py`

*   **Nom et Emplacement:** [`scripts/testing/test_runner_simple.py`](scripts/testing/test_runner_simple.py:1)
*   **Type de Tests Lancés:** Lance les tests basés sur `unittest.TestCase`.
*   **Mécanisme d'Activation de l'Environnement:** Aucun.
*   **Commande(s) d'Exécution:** Utilise le module `unittest` de Python pour découvrir et lancer les tests.
*   **Dépendances d'Orchestration:** Aucune.
*   **Objectif Général Supposé:** Runner de secours pour diagnostiquer les problèmes lorsque `pytest` est défaillant.

---

## Conclusion et Recommandations

L'écosystème de test de ce projet est hétérogène, montrant une transition d'anciens scripts spécifiques (PowerShell, silos) vers un orchestrateur Python centralisé (`TestRunner`).

*   **Points d'entrée principaux recommandés:**
    *   Pour les systèmes Unix/Linux: [`run_tests.sh`](run_tests.sh:1)
    *   Directement en Python (plus de contrôle): `python -m project_core.test_runner [commande]`

*   **Dette technique:**
    *   Le script [`run_tests.ps1`](run_tests.ps1:1) est en retard par rapport à son équivalent `.sh`. Il devrait être mis à jour pour utiliser également `project_core.test_runner.py` afin d'unifier l'expérience de développement entre Windows et Unix.
    *   Les scripts comme [`scripts/run_all_and_test.ps1`](scripts/run_all_and_test.ps1:2) et [`scripts/testing/test_playwright_headless.ps1`](scripts/testing/test_playwright_headless.ps1:1) devraient idéalement être intégrés ou remplacés par des configurations dans le `TestRunner` central pour éliminer les silos de test.
## Proposition d'Architecture Cible

Suite à l'audit, cette section propose une architecture de test unifiée pour résoudre les incohérences et les redondances identifiées. L'objectif est de s'appuyer sur l'orchestrateur Python existant ([`project_core/test_runner.py`](project_core/test_runner.py:1)) comme pierre angulaire du système de test.

### 1. Point d'Entrée Unifié : `run_tests.ps1`

Le script [`run_tests.ps1`](run_tests.ps1:1) sera promu comme **unique point d'entrée multi-plateforme** pour tous les tests.

*   **Responsabilités :**
    1.  **Parsing d'arguments :** Accepter des arguments clairs pour sélectionner le type de test (`-Type <unit|functional|e2e|all>`), le chemin (`-Path <path:str>`), etc.
    2.  **Activation d'environnement :** Appeler systématiquement `scripts/activate_project_env.ps1` pour garantir que l'environnement Conda est correctement activé.
    3.  **Invocation de l'Orchestrateur :** Exécuter l'orchestrateur central `python -m project_core.test_runner` en lui transmettant les arguments parsés.
*   **Avantage :** Un seul script à apprendre et à maintenir pour tous les développeurs et pour la CI/CD, quel que soit l'OS.

### 2. Standardisation de l'Activation de l'Environnement

*   **Principe :** La responsabilité de l'activation de l'environnement est déléguée **exclusivement** aux scripts appelants (wrappers), et non à l'orchestrateur Python.
*   **Implémentation :**
    *   L'[`EnvironmentManager`](project_core/test_runner.py:13) au sein de `test_runner.py` sera simplifié ou supprimé. L'orchestrateur partira du principe que l'environnement est déjà actif.
    *   Le script `scripts/activate_project_env.ps1` devient la méthode canonique d'activation, utilisée par `run_tests.ps1`.

### 3. Orchestration Centralisée et Complète

L'orchestrateur [`project_core/test_runner.py`](project_core/test_runner.py:1) deviendra le seul gestionnaire du cycle de vie des tests.

*   **Intégration des Silos :**
    *   **Tests Playwright :** Le `test_runner` sera étendu pour lancer les tests Playwright (`npx playwright test`). Il utilisera son `ServiceManager` pour démarrer le backend/frontend au préalable, ce que le script `test_playwright_headless.ps1` ne faisait pas.
    *   **Tests Fonctionnels Spécifiques :** Le test lancé par `scripts/run_all_and_test.ps1` sera intégré comme une suite de tests standard dans la configuration du `test_runner`.
*   **Avantage :** Toute la logique complexe (démarrage de services, health checks, sélection de tests, reporting) est centralisée, maintenable et réutilisable.

### 4. Plan de Nettoyage et de Refactoring

La mise en place de cette architecture permettra de supprimer les scripts suivants, réduisant ainsi la dette technique :

*   **À supprimer :**
    *   `run_tests.sh` (remplacé par `run_tests.ps1`)
    *   `scripts/run_all_and_test.ps1` (fonctionnalité absorbée)
    *   `scripts/testing/test_playwright_headless.ps1` (fonctionnalité absorbée)
    *   `scripts/testing/test_runner_simple.py` (peut être remplacé par un mode de diagnostic dans le runner principal)

### Schéma de l'Architecture Cible (Mermaid)

```mermaid
graph TD
    subgraph "Point d'Entrée Unifié (PowerShell Core)"
        A[run_tests.ps1 -Type e2e]
    end

    subgraph "Activation Standardisée"
        B[scripts/activate_project_env.ps1]
    end

    subgraph "Orchestrateur Central (Python)"
        C[project_core/test_runner.py]
        D[ServiceManager: Gère Backend/Frontend]
        E[Exécution PyTest]
        F[Exécution Playwright]
    end

    subgraph "Services Applicatifs"
        G[Backend (Flask)]
        H[Frontend (React)]
    end

    A --> B
    B --> C
    C --> D
    D --> G
    D --> H
    C --> E
    C --> F
```