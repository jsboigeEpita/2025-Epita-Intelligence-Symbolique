# Documentation des Correctifs - Audit Section 1

Ce document détaille les corrections apportées pour résoudre les échecs identifiés dans la section 2.1 de l'audit (`audit_results.md`).

---

### 1. (Réf. 2.1.2) Gestionnaire `lifespan` ASGI

-   **Problème :** Les logs de cycle de vie d'Uvicorn (`startup` et `shutdown`) n'étaient pas visibles. La cause était une double absence : pas de configuration de logging pour Uvicorn et une redirection des sorties (stdout/stderr) vers un fichier qui n'était pas celui attendu par le plan d'audit.
-   **Solution :**
    1.  **Création d'une configuration de logging centralisée** (`argumentation_analysis/config/uvicorn_logging.json`). Ce fichier définit le format, le niveau (`INFO`) et la destination (`logs/backend.log`) des logs Uvicorn.
    2.  **Modification de `scripts/apps/webapp/backend_manager.py`** pour utiliser cette configuration via l'argument `--log-config` lors du lancement d'Uvicorn.
    3.  Suppression de la redirection manuelle des flux `stdout` et `stderr`, maintenant gérée proprement par la configuration de logging.

---

### 2. (Réf. 2.1.3) Wrapper `WsgiToAsgi`

-   **Problème :** Le test était "Non Réalisable" car le fichier de test d'intégration `tests/integration/test_wsgi_compatibility.py` n'existait pas.
-   **Solution :**
    1.  **Création du fichier de test**.
    2.  Le test utilise `pytest` et `httpx` pour interroger l'endpoint `/api/health`, qui est servi par l'application Flask sous-jacente.
    3.  Le test vérifie que la réponse a un statut `200 OK` et que le corps JSON est conforme, validant ainsi que le wrapper `WsgiToAsgi` expose correctement les routes Flask.

---

### 3. (Réf. 2.1.4 & 2.1.7) Orchestrateur Web Unifié & Runner Playwright

-   **Problème :** L'orchestrateur échouait car les tests Playwright retournaient une "usage error" (code `4`). De plus, le `playwright_runner.py` ne pouvait pas être exécuté seul. Les causes étaient un mauvais répertoire de travail pour `pytest`, l'absence de chemin de test par défaut, et l'absence d'un point d'entrée pour l'exécution directe.
-   **Solution :**
    1.  **Modification de `scripts/apps/webapp/playwright_runner.py` :**
        -   Le répertoire d'exécution (`cwd`) de `pytest` a été changé de `tests/integration/webapp` à `tests/` pour permettre la découverte des fixtures globales (`conftest.py`).
        -   Un chemin de test par défaut (`integration/webapp/`) a été ajouté pour éviter que `pytest` ne soit appelé sans cible.
        -   Une section `if __name__ == "__main__":` a été ajoutée pour permettre l'exécution directe du script, résolvant ainsi le point d'audit 2.1.7.

---

### 4. (Réf. 2.1.5) Gestionnaire de Backend

-   **Problème :** Le `backend_manager.py` utilisait une invocation directe de `conda run` au lieu du script d'activation d'environnement centralisé (`activate_project_env.ps1`) requis par le plan d'audit.
-   **Solution :**
    1.  **Modification de `scripts/apps/webapp/backend_manager.py` :** La construction de la commande de démarrage a été modifiée pour utiliser explicitement le script d'activation défini dans la configuration, garantissant ainsi une activation cohérente de l'environnement.

---

### 5. (Réf. 2.1.6) Gestionnaire de Frontend

-   **Problème :** Le script était inutilisable en l'état pour l'intégration : désactivé par défaut, il lançait un serveur de développement au lieu d'un build, et le plan de test était incohérent (mauvais chemins, mauvaises attentes).
-   **Solution :**
    1.  **Refactorisation majeure de `scripts/apps/webapp/frontend_manager.py` :**
        -   Le script est maintenant **activé par défaut**.
        -   La logique a été scindée en deux méthodes claires : `build()` (qui exécute `npm run build`) et `start_dev_server()`.
        -   Une section `if __name__ == "__main__":` a été ajoutée pour permettre une exécution en ligne de commande (ex: `python ... frontend_manager.py build`).
        -   La détection du chemin du projet frontend a été rendue plus intelligente pour éviter les erreurs liées aux chemins hardcodés.