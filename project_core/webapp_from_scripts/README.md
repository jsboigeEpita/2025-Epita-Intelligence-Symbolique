# Orchestration des Tests d'Applications Web

Ce document décrit comment utiliser l'Orchestrateur Web Unifié (`UnifiedWebOrchestrator`) pour gérer le cycle de vie des applications web du projet et exécuter les tests d'interface et d'intégration.

## 1. Orchestrateur Web Unifié (`UnifiedWebOrchestrator`)

Le script principal pour l'orchestration est [`scripts/webapp/unified_web_orchestrator.py`](scripts/webapp/unified_web_orchestrator.py:1). Il sert de point d'entrée unique pour :
- Démarrer et arrêter les applications web (backend Flask, frontend React optionnel).
- Exécuter les suites de tests Playwright.
- Générer des traces d'exécution et des rapports.

### Configuration

L'orchestrateur utilise un fichier de configuration YAML : [`config/webapp_config.yml`](config/webapp_config.yml:119). Ce fichier permet de définir :
- Les paramètres du backend (module à lancer, port de démarrage, ports de repli, etc.).
- Les paramètres du frontend (s'il est activé, chemin, port, commande de démarrage).
- Les paramètres pour Playwright (navigateur, mode headless, timeouts, chemins des tests par défaut).
- Les paramètres de logging et de nettoyage des processus.

### Utilisation en Ligne de Commande

Le script `unified_web_orchestrator.py` peut être appelé avec plusieurs arguments :

-   **Test d'intégration complet (par défaut) :**
    ```bash
    python scripts/webapp/unified_web_orchestrator.py
    ```
    Cette commande va :
    1.  Nettoyer les instances précédentes.
    2.  Démarrer le backend (et le frontend si activé).
    3.  Exécuter les tests Playwright configurés (par défaut, les tests Python dans `tests/functional/`).
    4.  Arrêter les applications.
    5.  Sauvegarder un rapport de trace.

-   **Démarrer seulement l'application :**
    ```bash
    python scripts/webapp/unified_web_orchestrator.py --start
    ```

-   **Arrêter l'application :**
    ```bash
    python scripts/webapp/unified_web_orchestrator.py --stop
    ```

-   **Exécuter seulement les tests (nécessite que l'application soit déjà démarrée) :**
    ```bash
    python scripts/webapp/unified_web_orchestrator.py --test
    ```

-   **Options courantes :**
    -   `--config <chemin_fichier_config>`: Spécifier un fichier de configuration alternatif.
    -   `--headless` / `--visible`: Contrôler le mode d'exécution du navigateur pour les tests.
    -   `--frontend`: Forcer l'activation du frontend.
    -   `--tests <chemin_test_1> <chemin_test_2>`: Spécifier des chemins de tests spécifiques à exécuter (principalement pour les tests Python/pytest).

## 2. Tests Playwright

Le projet utilise deux types de tests Playwright :

### a. Tests Playwright en Python

-   **Localisation :** Principalement dans le répertoire [`tests/functional/`](tests/functional/).
-   **Exécution :** Ces tests sont exécutés par `UnifiedWebOrchestrator` via `PlaywrightRunner` ([`scripts/webapp/playwright_runner.py`](scripts/webapp/playwright_runner.py:1)), qui utilise `pytest`.
-   **Configuration de l'URL :**
    -   Le `PlaywrightRunner` définit la variable d'environnement `BACKEND_URL` (et `FRONTEND_URL` si applicable) en se basant sur les ports réels sur lesquels les applications ont démarré (y compris la gestion des ports de repli).
    -   Les tests Python peuvent accéder à ces URLs via `os.environ.get('BACKEND_URL')`.
    -   Le `PlaywrightRunner` définit également `PLAYWRIGHT_BASE_URL` (généralement l'URL du frontend ou du backend) qui peut être utilisée par les tests ou la configuration Playwright.

### b. Tests Playwright en JavaScript (`.spec.js`)

-   **Localisation :** Dans le répertoire [`tests_playwright/tests/`](tests_playwright/tests/).
-   **Configuration Playwright Native :** Ces tests utilisent les fichiers de configuration Playwright standards comme [`tests_playwright/playwright.config.js`](tests_playwright/playwright.config.js:1).
-   **Configuration de l'URL (`baseURL`) :**
    -   Le fichier [`tests_playwright/playwright.config.js`](tests_playwright/playwright.config.js:1) a été modifié pour utiliser la variable d'environnement `PLAYWRIGHT_BASE_URL` :
        ```javascript
        use: {
          baseURL: process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:3000',
          // ...
        }
        ```
    -   Les fichiers de test (comme [`tests_playwright/tests/flask-interface.spec.js`](tests_playwright/tests/flask-interface.spec.js:1)) ont été modifiés pour utiliser des navigations relatives (par exemple, `await page.goto('/');`), qui se baseront sur cette `baseURL`.
-   **Exécution :**
    -   **Via l'Orchestrateur (Recommandé pour l'intégration) :**
        Pour l'instant, `UnifiedWebOrchestrator` n'a pas de commande directe pour lancer `npx playwright test`. Cependant, lorsque l'orchestrateur démarre les services (par exemple avec `python scripts/webapp/unified_web_orchestrator.py --start`), il configure la variable d'environnement `PLAYWRIGHT_BASE_URL`.
        Vous pouvez ensuite, dans un autre terminal, exécuter les tests JS :
        ```bash
        # Assurez-vous que l'environnement Node.js est configuré et les dépendances installées
        cd tests_playwright
        # PLAYWRIGHT_BASE_URL sera héritée si l'orchestrateur l'a définie dans le même shell
        # ou vous pouvez la transmettre explicitement si nécessaire.
        # L'orchestrateur définit cette variable pour les processus qu'il lance (comme pytest).
        # Pour une exécution manuelle, assurez-vous qu'elle est disponible dans votre shell.
        # Si l'orchestrateur tourne et a exporté la variable, ou si vous la positionnez :
        # export PLAYWRIGHT_BASE_URL="http://localhost:XXXX" # (remplacer XXXX par le port réel)
        npx playwright test tests/flask-interface.spec.js
        ```
        *(Note : L'intégration d'une commande directe dans `UnifiedWebOrchestrator` pour lancer `npx playwright test` pourrait être une amélioration future.)*
    -   **Manuellement (pour développement local) :**
        Si vous démarrez les serveurs manuellement, assurez-vous de définir la variable `PLAYWRIGHT_BASE_URL` dans votre terminal avant de lancer `npx playwright test` si l'application ne tourne pas sur `http://localhost:3000`.
        ```bash
        export PLAYWRIGHT_BASE_URL="http://actual_url:port" # Exemple pour Linux/macOS
        # set PLAYWRIGHT_BASE_URL=http://actual_url:port     # Exemple pour Windows (cmd)
        # $env:PLAYWRIGHT_BASE_URL="http://actual_url:port" # Exemple pour Windows (PowerShell)
        cd tests_playwright
        npx playwright test
        ```

## 3. Rapports de Test

-   **Tests Python (via `pytest` et `PlaywrightRunner`) :**
    -   Les logs de `pytest` sont sauvegardés dans `logs/traces/pytest_stdout.log` et `pytest_stderr.log`.
    -   Un rapport JSON détaillé est sauvegardé dans `logs/traces/test_report.json`.
    -   Les screenshots et vidéos/traces Playwright sont dans `logs/screenshots` et `logs/traces` (configurables).
-   **Tests JavaScript (via `npx playwright test`) :**
    -   Par défaut, un rapport HTML est généré dans `playwright-report/` (configurable dans `playwright.config.js`).
-   **Trace de l'Orchestrateur :**
    -   `UnifiedWebOrchestrator` génère un rapport de trace Markdown complet de ses actions dans `logs/webapp_integration_trace.md`.

## Conclusion

L'[`UnifiedWebOrchestrator`](scripts/webapp/unified_web_orchestrator.py:1) est le point d'entrée privilégié pour les tests d'intégration web. Il assure la cohérence de l'environnement et centralise la configuration. En configurant correctement la variable d'environnement `PLAYWRIGHT_BASE_URL` (ce que fait l'orchestrateur), les tests Playwright JavaScript peuvent également s'exécuter de manière flexible par rapport à l'URL de l'application.