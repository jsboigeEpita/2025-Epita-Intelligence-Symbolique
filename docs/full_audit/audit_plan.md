# Plan de Test de l'Audit Post-Refactorisation

**Date :** 22/06/2025
**Auteur :** Roo

## 1. Introduction

Ce document présente le plan de test détaillé pour l'audit technique du projet. Chaque point du périmètre défini dans `docs/full_audit/audit_scope.md` est associé à une ou plusieurs actions de validation concrètes, mesurables et si possible automatisées.

L'objectif est d'exécuter systématiquement ces vérifications pour garantir la stabilité, la robustesse et la maintenabilité de l'application après la refactorisation.

---

## 2. Plan de Validation Détaillé

### 2.1. Architecture Web et Orchestration d'Application

| Élément | Action(s) de Validation | Commande(s) / Méthode |
| --- | --- | --- |
| **Pile Web ASGI/Uvicorn** | 1. Lancer l'orchestrateur web. <br> 2. Envoyer une requête HTTP simple au serveur backend. <br> 3. Vérifier que la requête reçoit une réponse `200 OK`. | `python scripts/apps/webapp/unified_web_orchestrator.py` <br> `Invoke-WebRequest -Uri http://localhost:[PORT_BACKEND]/health` |
| **Gestionnaire `lifespan` ASGI** | 1. Lancer l'orchestrateur. <br> 2. Inspecter les logs de sortie. <br> 3. Confirmer la présence des messages "INFO: Application startup complete." et "INFO: Application shutdown complete.". | `Select-String -Path logs/backend.log -Pattern "Application startup complete|Application shutdown complete"` |
| **Wrapper `WsgiToAsgi`** | 1. Identifier un endpoint servi par l'ancien wrapper WSGI. <br> 2. Exécuter un test d'intégration qui cible ce endpoint. <br> 3. Valider que la réponse est conforme à l'attendu. | Test d'intégration spécifique à écrire (ex: `tests/integration/test_wsgi_compatibility.py`). |
| **Orchestrateur Web Unifié** | 1. Lancer le script en mode "run all". <br> 2. Vérifier que les logs indiquent le démarrage successif du backend, du frontend, puis l'exécution des tests Playwright. <br> 3. S'assurer que le script se termine avec un code de sortie `0`. | `python scripts/apps/webapp/unified_web_orchestrator.py --run-all` |
| **Gestionnaire de Backend** | 1. Inspecter le code source du gestionnaire. <br> 2. Confirmer que le démarrage du backend utilise bien `activate_project_env.ps1` pour configurer l'environnement. | `Select-String -Path scripts/apps/webapp/backend_manager.py -Pattern "activate_project_env.ps1"` |
| **Gestionnaire de Frontend** | 1. Exécuter le gestionnaire de manière isolée. <br> 2. Vérifier la création d'un répertoire `build` dans `interface_web/`. <br> 3. Confirmer qu'un serveur `http.server` est lancé sur un port disponible. | `python scripts/apps/webapp/frontend_manager.py` |
| **Runner de Tests Playwright** | 1. Lancer le runner de tests. <br> 2. Vérifier dans les logs de sortie que les suites de tests JS (`*.spec.js`) et Python (`*_test.py`) sont toutes deux exécutées. | `python scripts/apps/webapp/playwright_runner.py` |

### 2.2. Moteur d'Orchestration d'Analyse (Core)

| Élément | Action(s) de Validation | Commande(s) / Méthode |
| --- | --- | --- |
| **Moteur d'Orchestration à Stratégies** | 1. Exécuter une recherche sur tout le code. <br> 2. S'assurer que l'ancien moteur (`OldOrchestrationEngine`) n'est plus importé ni utilisé nulle part, sauf dans les modules de compatibilité. | `Select-String -Path argumentation_analysis/ -Pattern "OldOrchestrationEngine" -Exclude argumentation_analysis/pipelines/unified_orchestration_pipeline.py` |
| **Orchestrateur Principal** | 1. Exécuter un test d'intégration via le pipeline unifié. <br> 2. Placer un log ou un point d'arrêt dans `MainOrchestrator.execute()`. <br> 3. Confirmer que le `MainOrchestrator` est bien appelé et qu'il délègue à la bonne stratégie. | Test d'intégration + debugger/log. |
| **Façade d'Orchestration (Strangler Fig)** | 1. Lancer les tests de régression existants qui ciblent l'ancien pipeline. <br> 2. Valider que tous les tests passent, prouvant que la façade fonctionne comme l'ancienne implémentation. | `pytest tests/regression/test_unified_pipeline.py` |

### 2.3. Architecture des Agents

| Élément | Action(s) de Validation | Commande(s) / Méthode |
| --- | --- | --- |
| **Décomposition de `WatsonJTMSAgent`** | 1. Rechercher les instanciations de `WatsonJTMSAgent`. <br> 2. S'assurer qu'il n'est utilisé que dans les contextes de tests de rétrocompatibilité. | `Select-String -Path . -Pattern "WatsonJTMSAgent\("` |
| **Services Spécialisés** | 1. Exécuter les tests unitaires pour chaque service. <br> 2. Valider que la couverture de code pour ces nouveaux services est supérieure à 90%. | `pytest argumentation_analysis/agents/watson_jtms/service/ --cov` |
| **Standardisation de l'API des Agents** | 1. Lister toutes les méthodes publiques des classes d'agents. <br> 2. Confirmer que l'interface principale se limite à `invoke()` et `invoke_single()`. | Script d'analyse statique ou recherche manuelle. `Get-ChildItem -Path argumentation_analysis/agents -Recurse -Filter "*.py" | Select-String -Pattern "def invoke|def invoke_single"` |

### 2.4. Infrastructure de Test et Fiabilisation

| Élément | Action(s) de Validation | Commande(s) / Méthode |
| --- | --- | --- |
| **Isolation des Tests JVM** | 1. Créer un test d'intégration qui provoque une `OutOfMemoryError` dans la JVM. <br> 2. Lancer ce test via `pytest`. <br> 3. Vérifier que `pytest` ne crashe pas et rapporte l'échec du test proprement. | Créer `tests/integration/test_jvm_crash.py`. |
| **Répertoire de Tests E2E Unifié** | 1. Lister les fichiers dans `tests/e2e/`. <br> 2. S'assurer qu'il n'existe pas d'autres tests E2E dispersés dans l'arborescence. | `Get-ChildItem -Path tests/e2e -Recurse` |
| **Serveur de Test Frontend** | 1. Démarrer le `frontend_manager`. <br> 2. Effectuer une requête `curl` sur l'`URL` du serveur. <br> 3. Vérifier que le contenu du `index.html` est bien retourné. | `Invoke-WebRequest -Uri http://localhost:[PORT_FRONTEND]` |
| **Allocation Dynamique de Ports** | 1. Lancer `unified_web_orchestrator.py` deux fois en parallèle. <br> 2. Capturer les logs. <br> 3. Confirmer que les ports alloués pour le backend et le frontend sont différents pour chaque instance. | Analyse des logs de deux exécutions concurrentes. |

### 2.5. Environnement, Configuration et Dette Technique

| Élément | Action(s) de Validation | Commande(s) / Méthode |
| --- | --- | --- |
| **Script d'Environnement Centralisé** | 1. Ouvrir un NOUVEAU terminal. <br> 2. Tenter de lancer un script (ex: `pytest`) et vérifier qu'il échoue. <br> 3. Exécuter `. ./activate_project_env.ps1`. <br> 4. Relancer le script et vérifier qu'il réussit. | Procédure manuelle ou script de test d'environnement. |
| **Gestion des Dépendances** | 1. Construire l'environnement Conda à partir de zéro. <br> 2. Lancer la suite de tests complète. <br> 3. S'assurer que tous les tests passent sans nécessiter l'installation manuelle de paquets. | `conda env create -f environment.yml && conda activate [ENV_NAME] && pytest` |
| **Bibliothèque `semantic-kernel`** | 1. Rechercher tous les appels aux fonctions de `semantic-kernel`. <br> 2. Vérifier que chaque appel est encapsulé dans un bloc `try...except` avec une gestion d'erreur spécifique. | `Select-String -Path . -Pattern "semantic_kernel\."` |
| **Communication par Fichier (Dette)** | 1. Rechercher l'usage de `logs/frontend_url.txt`. <br> 2. **Action :** Remplacer ce mécanisme par une méthode plus robuste (variable d'environnement, communication directe entre processus). <br> 3. **Validation :** La commande de recherche ne doit plus retourner aucun résultat. | `Select-String -Path . -Pattern "logs/frontend_url.txt"` |
| **Centralisation de la Configuration (Cible)** | 1. Rechercher les valeurs hardcodées (ports > 1024, "http://", "localhost"). <br> 2. **Action :** Extraire ces valeurs dans un fichier de configuration central (ex: `config/settings.toml`). <br> 3. **Validation :** La commande de recherche ne doit plus retourner de valeurs modifiables. | `Select-String -Path . -Pattern "(?i)localhost|http://|:[1-9][0-9]{3,}"` |

### 2.6. Documentation Technique

| Élément | Action(s) de Validation | Commande(s) / Méthode |
| --- | --- | --- |
| **Documentation de Conception** | 1. Lire `docs/DOC_CONCEPTION_SHERLOCK_WATSON.md`. <br> 2. Confronter chaque section avec les éléments du périmètre d'audit (`audit_scope.md`). <br> 3. S'assurer que l'architecture décrite est à jour. | Relecture croisée manuelle. |
| **Rapports d'Analyse** | 1. Vérifier l'existence de tous les rapports listés dans `audit_scope.md`. <br> 2. S'assurer que les conclusions des rapports justifient bien les changements effectués. | `Get-ChildItem -Path docs/commit_analysis_reports/`, `docs/validation/` |