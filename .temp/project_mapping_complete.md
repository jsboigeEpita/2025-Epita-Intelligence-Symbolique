# Cartographie Complète des Points d'Entrée du Projet

Ce document détaille tous les points d'entrée identifiés dans le projet, organisés par composant et par type.
## Répertoire `scripts/`

### Points d'entrée principaux

- **[`scripts/run_all_and_test.ps1`](scripts/run_all_and_test.ps1:1)**: Lance une suite complète de tests et de validations.
- **[`scripts/run_webapp_integration.py`](scripts/run_webapp_integration.py:1)**: Script d'intégration pour l'application web.
- **[`scripts/sprint3_final_validation.py`](scripts/sprint3_final_validation.py:1)**: Script de validation finale pour le sprint 3.
- **[`scripts/start_full_app.ps1`](scripts/start_full_app.ps1:1)**: Démarre l'application complète.
- **[`scripts/test_environment_simple.py`](scripts/test_environment_simple.py:1)**: Script de test simple de l'environnement.
- **[`scripts/test_playwright_headless.ps1`](scripts/test_playwright_headless.ps1:1)**: Lance les tests Playwright en mode headless.

### Maintenance (`scripts/maintenance/`)

- **[`scripts/maintenance/final_system_validation_corrected.py`](scripts/maintenance/final_system_validation_corrected.py:1)**: Validation système corrigée.
- **[`scripts/maintenance/run_documentation_maintenance.py`](scripts/maintenance/run_documentation_maintenance.py:1)**: Lance les tâches de maintenance de la documentation.
- **[`scripts/maintenance/auto_resolve_git_conflicts.ps1`](scripts/maintenance/auto_resolve_git_conflicts.ps1:1)**: Tente de résoudre automatiquement les conflits Git.
- **[`scripts/maintenance/validate_migration.ps1`](scripts/maintenance/validate_migration.ps1:1)**: Valide la migration des données ou du schéma.

### Pipelines (`scripts/pipelines/`)

- **[`scripts/pipelines/run_rhetorical_analysis_pipeline.py`](scripts/pipelines/run_rhetorical_analysis_pipeline.py:1)**: Exécute le pipeline d'analyse rhétorique.
- **[`scripts/pipelines/run_web_e2e_pipeline.py`](scripts/pipelines/run_web_e2e_pipeline.py:1)**: Exécute le pipeline de tests de bout en bout pour le web.

### Reporting (`scripts/reporting/`)

- **[`scripts/reporting/generate_comprehensive_report.py`](scripts/reporting/generate_comprehensive_report.py:1)**: Génère un rapport complet.
- **[`scripts/reporting/generate_coverage_report.py`](scripts/reporting/generate_coverage_report.py:1)**: Génère un rapport de couverture de tests.
- **[`scripts/reporting/visualize_test_coverage.py`](scripts/reporting/visualize_test_coverage.py:1)**: Visualise la couverture des tests.

### Analyse Rhétorique (`scripts/rhetorical_analysis/`)

- **[`scripts/rhetorical_analysis/educational_showcase_system.py`](scripts/rhetorical_analysis/educational_showcase_system.py:1)**: Système de démonstration pour l'analyse rhétorique (éducatif).
- **[`scripts/rhetorical_analysis/unified_production_analyzer.py`](scripts/rhetorical_analysis/unified_production_analyzer.py:1)**: Analyseur unifié pour la production (analyse rhétorique).

### Setup (`scripts/setup/`)

- **[`scripts/setup/fix_all_dependencies.ps1`](scripts/setup/fix_all_dependencies.ps1:1)**: Répare toutes les dépendances du projet.
- **[`scripts/setup/fix_dependencies.ps1`](scripts/setup/fix_dependencies.ps1:1)**: Répare les dépendances.
- **[`scripts/setup/install_environment.py.old`](scripts/setup/install_environment.py.old:1)**: Ancien script d'installation de l'environnement (à vérifier).
- **[`scripts/setup/validate_environment.py`](scripts/setup/validate_environment.py:1)**: Valide la configuration de l'environnement.
- **[`scripts/setup/setup_test_env.ps1`](scripts/setup/setup_test_env.ps1:1)**: Configure l'environnement de test.

### Sherlock/Watson (`scripts/sherlock_watson/`)

- **[`scripts/sherlock_watson/orchestrate_dynamic_cases.py`](scripts/sherlock_watson/orchestrate_dynamic_cases.py:1)**: Orchestre des cas de test dynamiques pour Sherlock/Watson.
- **[`scripts/sherlock_watson/run_authentic_sherlock_watson_no_java.py`](scripts/sherlock_watson/run_authentic_sherlock_watson_no_java.py:1)**: Lance une version de Sherlock/Watson sans dépendance Java.
- **[`scripts/sherlock_watson/run_cluedo_oracle_enhanced.py`](scripts/sherlock_watson/run_cluedo_oracle_enhanced.py:1)**: Lance la démo Cluedo avec l'oracle amélioré.
- **[`scripts/sherlock_watson/run_einstein_oracle_demo.py`](scripts/sherlock_watson/run_einstein_oracle_demo.py:1)**: Lance la démo de l'oracle d'Einstein.
- **[`scripts/sherlock_watson/run_real_sherlock_watson_moriarty.py`](scripts/sherlock_watson/run_real_sherlock_watson_moriarty.py:1)**: Lance la simulation complète Sherlock/Watson/Moriarty.
- **[`scripts/sherlock_watson/test_oracle_behavior_demo.py`](scripts/sherlock_watson/test_oracle_behavior_demo.py:1)**: Teste le comportement de l'oracle (démo).

### Testing (`scripts/testing/`)

- **[`scripts/testing/run_embed_tests.py`](scripts/testing/run_embed_tests.py:1)**: Lance les tests d'intégration (embed tests).
- **[`scripts/testing/run_tests_alternative.py`](scripts/testing/run_tests_alternative.py:1)**: Runner de test alternatif.
- **[`scripts/testing/simple_test_runner.py`](scripts/testing/simple_test_runner.py:1)**: Runner de test simple.

### Validation (`scripts/validation/`)

- **[`scripts/validation/unified_validation.py`](scripts/validation/unified_validation.py:1)**: Script de validation unifié.
- **[`scripts/validation/test_epita_custom_data_processing.py`](scripts/validation/test_epita_custom_data_processing.py:1)**: Teste le traitement des données personnalisées Epita.
## Répertoire `api/`

### Points d'entrée principaux (Serveur API)

- **[`api/main.py`](api/main.py:1)**: Point d'entrée principal de l'API (probablement FastAPI ou Flask).
- **[`api/main_simple.py`](api/main_simple.py:1)**: Version simplifiée du point d'entrée de l'API, potentiellement pour des tests ou une configuration minimale.
- **[`api/endpoints.py`](api/endpoints.py:1)**: Définit les routes/endpoints de l'API.
- **[`api/endpoints_simple.py`](api/endpoints_simple.py:1)**: Version simplifiée des définitions de routes.

### Dépendances et Modèles

- **[`api/dependencies.py`](api/dependencies.py:1)**: Gestion des dépendances pour l'API (ex: injections).
- **[`api/dependencies_simple.py`](api/dependencies_simple.py:1)**: Version simplifiée de la gestion des dépendances.
- **[`api/models.py`](api/models.py:1)**: Modèles de données Pydantic ou SQLAlchemy utilisés par l'API.
- **[`api/services.py`](api/services.py:1)**: Logique métier ou services appelés par les endpoints.
## Répertoire `services/`

### Gestion des Services Web (`services/web_api/`)

- **[`services/web_api/start_full_system.py`](services/web_api/start_full_system.py:1)**: Démarre l'ensemble des services du système web.
- **[`services/web_api/start_simple_only.py`](services/web_api/start_simple_only.py:1)**: Démarre uniquement les services web simples.
- **[`services/web_api/stop_all_services.py`](services/web_api/stop_all_services.py:1)**: Arrête tous les services web en cours d'exécution.
- **[`services/web_api/health_check.py`](services/web_api/health_check.py:1)**: Script pour vérifier l'état de santé des services web.
- **[`services/web_api/trace_analyzer.py`](services/web_api/trace_analyzer.py:1)**: Analyseur de traces pour les services web.

### Interface Web Simple (`services/web_api/interface-simple/`)

- **[`services/web_api/interface-simple/app.py`](services/web_api/interface-simple/app.py:1)**: Application Flask/FastAPI pour l'interface web simple.
- **[`services/web_api/interface-simple/templates/index.html`](services/web_api/interface-simple/templates/index.html:1)**: Fichier HTML principal pour l'interface simple.
- **Tests pour l'interface simple**:
    - [`services/web_api/interface-simple/test_api_validation.py`](services/web_api/interface-simple/test_api_validation.py:1)
    - [`services/web_api/interface-simple/test_fallacy_detection.py`](services/web_api/interface-simple/test_fallacy_detection.py:1)
    - [`services/web_api/interface-simple/test_integration.py`](services/web_api/interface-simple/test_integration.py:1)
    - [`services/web_api/interface-simple/test_simple.py`](services/web_api/interface-simple/test_simple.py:1)
    - [`services/web_api/interface-simple/test_webapp.py`](services/web_api/interface-simple/test_webapp.py:1)

### Interface Web Argumentative (React) (`services/web_api/interface-web-argumentative/`)

- **[`services/web_api/interface-web-argumentative/package.json`](services/web_api/interface-web-argumentative/package.json:1)**: Fichier de configuration du projet Node.js/React. Points d'entrée typiques via les scripts `start`, `build`, `test`.
- **[`services/web_api/interface-web-argumentative/src/App.js`](services/web_api/interface-web-argumentative/src/App.js:1)**: Composant React principal de l'application.
- **[`services/web_api/interface-web-argumentative/src/index.js`](services/web_api/interface-web-argumentative/src/index.js:1)**: Point d'entrée JavaScript pour le rendu de l'application React.
- **[`services/web_api/interface-web-argumentative/public/index.html`](services/web_api/interface-web-argumentative/public/index.html:1)**: Fichier HTML hôte pour l'application React.

### API Web depuis `libs` (`services/web_api_from_libs/`)

- **[`services/web_api_from_libs/app.py`](services/web_api_from_libs/app.py:1)**: Application Flask/FastAPI construite à partir des bibliothèques.
- **[`services/web_api_from_libs/example_usage.html`](services/web_api_from_libs/example_usage.html:1)**: Exemple d'utilisation de cette API.
- **Tests pour l'API depuis `libs`**:
    - [`services/web_api_from_libs/test_api.py`](services/web_api_from_libs/test_api.py:1)
## Répertoire `libs/`

Ce répertoire contient principalement des bibliothèques Java (`.jar`) et des bibliothèques natives (`.dll`). Les points d'entrée directs sont moins courants ici, mais ces bibliothèques sont cruciales pour le fonctionnement d'autres composants.

### Bibliothèques Java (TweetyProject et autres)

- **Fichiers `.jar` à la racine de `libs/` et dans `libs/tweety/`**:
    - Ces fichiers sont des dépendances pour les fonctionnalités basées sur Java, notamment celles utilisant TweetyProject pour la logique et l'argumentation.
    - Exemples :
        - [`libs/org.tweetyproject.tweety-full-1.28.jar`](libs/org.tweetyproject.tweety-full-1.28.jar)
        - [`libs/tweety/org.tweetyproject.arg.dung-1.28-with-dependencies.jar`](libs/tweety/org.tweetyproject.arg.dung-1.28-with-dependencies.jar)
    - Le point d'entrée se fait généralement via des appels depuis du code Python (par exemple, avec JPype).

### Bibliothèques Natives (`libs/native/` et `libs/tweety/native/`)

- **Fichiers `.dll`**:
    - Bibliothèques compilées (Dynamic Link Libraries) pour Windows.
    - Exemples :
        - [`libs/native/lingeling.dll`](libs/native/lingeling.dll)
        - [`libs/native/minisat.dll`](libs/native/minisat.dll)
        - [`libs/native/picosat.dll`](libs/native/picosat.dll)
    - Utilisées par d'autres parties du code (Python ou Java via JNI) pour des tâches spécifiques (ex: solveurs SAT).

### JDK Portable (`libs/portable_jdk/`)

- Contient une version portable du Java Development Kit.
- Point d'entrée : les exécutables Java comme `java.exe`, `javac.exe` situés dans le sous-répertoire `bin/` (non listé ici, mais structure typique d'un JDK).

### Octave Portable (`libs/portable_octave/`)

- Contient une version portable d'Octave.
- Point d'entrée : l'exécutable `octave.exe` ou `octave-cli.exe` situé dans le sous-répertoire `bin/` (non listé ici, mais structure typique).

### Documentation

- **[`libs/README.md`](libs/README.md:1)**: Peut contenir des informations sur la manière d'utiliser ou d'intégrer ces bibliothèques.
- **[`libs/native/README.md`](libs/native/README.md:1)**: Informations spécifiques aux bibliothèques natives.
## Répertoire `project_core/`

Ce répertoire semble contenir des éléments centraux pour la gestion et l'exécution du projet.

### Gestionnaires et Utilitaires Centraux

- **[`project_core/service_manager.py`](project_core/service_manager.py:1)**: Probablement responsable de la gestion (démarrage, arrêt, surveillance) des différents services du projet. Peut être un point d'entrée pour des opérations de gestion de services.
- **[`project_core/test_runner.py`](project_core/test_runner.py:1)**: Un script pour exécuter des tests à travers le projet. Point d'entrée pour lancer des suites de tests spécifiques ou générales.

### Configuration Centrale (`project_core/config/`)

- **[`project_core/config/port_manager.py`](project_core/config/port_manager.py:1)**: Gère l'allocation ou la configuration des ports pour les différents services, essentiel pour éviter les conflits.
## Répertoire `config/`

Ce répertoire centralise divers fichiers de configuration essentiels au projet.

### Fichiers de Configuration Principaux

- **[`config/unified_config.py`](config/unified_config.py:1)**: Script Python pour une gestion unifiée de la configuration. Peut charger, valider et fournir des configurations à d'autres modules.
- **[`config/orchestration_config.yaml`](config/orchestration_config.yaml:1)**: Fichier YAML pour la configuration de l'orchestration des services ou des tâches.
- **[`config/webapp_config.yml`](config/webapp_config.yml:1)**: Fichier YAML pour la configuration spécifique à l'application web.
- **[`config/ports.json`](config/ports.json:1)**: Fichier JSON définissant les ports utilisés par les services, probablement lié à [`project_core/config/port_manager.py`](project_core/config/port_manager.py:1).
- **Fichiers d'environnement (`.env.*`)**:
    - [`config/.env.authentic`](config/.env.authentic:1): Contient potentiellement des configurations authentiques/sensibles.
    - [`config/.env.example`](config/.env.example:1): Modèle pour créer un fichier `.env` local.
    - [`config/.env.template`](config/.env.template:1): Autre modèle de fichier d'environnement.
- **[`config/performance_config.ini`](config/performance_config.ini:1)**: Fichier INI pour les configurations liées à la performance.
- **[`config/utf8_environment.conf`](config/utf8_environment.conf:1)**: Fichier de configuration pour assurer un environnement UTF-8.

### Configuration des Tests (Pytest)

- **[`config/pytest.ini`](config/pytest.ini:1)**: Fichier de configuration principal pour Pytest.
- **Sous-répertoire `config/pytest/`**: Contient des configurations Pytest spécifiques pour différentes phases ou types de tests.
    - [`config/pytest/pytest_jvm_only.ini`](config/pytest/pytest_jvm_only.ini:1)
    - [`config/pytest/pytest_phase2.ini`](config/pytest/pytest_phase2.ini:1)
    - [`config/pytest/pytest_phase3.ini`](config/pytest/pytest_phase3.ini:1)
    - [`config/pytest/pytest_phase4_final.ini`](config/pytest/pytest_phase4_final.ini:1)
    - [`config/pytest/pytest_recovery.ini`](config/pytest/pytest_recovery.ini:1)
    - [`config/pytest/pytest_simple.ini`](config/pytest/pytest_simple.ini:1)
    - [`config/pytest/pytest_stable.ini`](config/pytest/pytest_stable.ini:1)
    - [`config/pytest/pytest.ini`](config/pytest/pytest.ini:1) (peut surcharger ou être surchargé par celui à la racine de `config/`)

### Scripts de Configuration et Nettoyage (`config/clean/`)

- **[`config/clean/backend_validation_script.ps1`](config/clean/backend_validation_script.ps1:1)**: Script PowerShell pour la validation du backend, potentiellement lié à une configuration propre.
- **[`config/clean/web_application_launcher.ps1`](config/clean/web_application_launcher.ps1:1)**: Script PowerShell pour lancer l'application web dans un environnement propre ou configuré.
- **[`config/clean/test_environment.env`](config/clean/test_environment.env:1)**: Fichier d'environnement spécifique pour un environnement de test "propre".

### Documentation

- **[`config/README.md`](config/README.md:1)**: Fournit des explications sur les fichiers de configuration et leur utilisation.
## Répertoire `archived_scripts/`

Ce répertoire contient des scripts qui ne sont plus activement utilisés ou qui ont été remplacés, mais qui peuvent encore avoir une valeur historique ou de débogage.

### Scripts Archivés à la Racine

- **Scripts de test et de débogage (Python et PowerShell)**:
    - [`archived_scripts/debug_agent_instantiation.py`](archived_scripts/debug_agent_instantiation.py:1)
    - [`archived_scripts/debug_pytest.ps1`](archived_scripts/debug_pytest.ps1:1)
    - [`archived_scripts/integration_test_trace_simple_success.ps1`](archived_scripts/integration_test_trace_simple_success.ps1:1)
    - [`archived_scripts/integration_test_with_trace.ps1`](archived_scripts/integration_test_with_trace.ps1:1)
    - [`archived_scripts/phase3_complex_diagnostics.py`](archived_scripts/phase3_complex_diagnostics.py:1)
    - [`archived_scripts/test_investigation_rhetorique_crypto.py`](archived_scripts/test_investigation_rhetorique_crypto.py:1)
    - [`archived_scripts/test_orchestrateur_simple.py`](archived_scripts/test_orchestrateur_simple.py:1)
- **Rapports CSV**:
    - [`archived_scripts/applied_corrections_report.csv`](archived_scripts/applied_corrections_report.csv)
    - [`archived_scripts/corrections_report.csv`](archived_scripts/corrections_report.csv)
    - [`archived_scripts/unresolved_references_report.csv`](archived_scripts/unresolved_references_report.csv)

### Scripts Archivés (Migration Obsolète 2025) (`archived_scripts/obsolete_migration_2025/`)

Ce sous-répertoire contient une structure de projet plus ancienne, probablement d'une version ou d'une tentative de migration précédente. Il est important de noter que ces scripts sont explicitement marqués comme obsolètes.

- **Points d'entrée potentiels (mais obsolètes)**:
    - **Démos**:
        - [`archived_scripts/obsolete_migration_2025/directories/demo/demo_epita_showcase.py`](archived_scripts/obsolete_migration_2025/directories/demo/demo_epita_showcase.py:1)
        - [`archived_scripts/obsolete_migration_2025/directories/demo/demo_unified_authentic_system.ps1`](archived_scripts/obsolete_migration_2025/directories/demo/demo_unified_authentic_system.ps1:1)
    - **Applications**:
        - [`archived_scripts/obsolete_migration_2025/directories/apps/start_webapp.py`](archived_scripts/obsolete_migration_2025/directories/apps/start_webapp.py:1)
    - **Scripts d'exécution principaux (legacy)**:
        - [`archived_scripts/obsolete_migration_2025/directories/legacy_root/activate_project_env.ps1`](archived_scripts/obsolete_migration_2025/directories/legacy_root/activate_project_env.ps1:1)
        - [`archived_scripts/obsolete_migration_2025/directories/legacy_root/run_all_new_component_tests.ps1`](archived_scripts/obsolete_migration_2025/directories/legacy_root/run_all_new_component_tests.ps1:1)
        - [`archived_scripts/obsolete_migration_2025/directories/legacy_root/run_sherlock_watson_synthetic_validation.ps1`](archived_scripts/obsolete_migration_2025/directories/legacy_root/run_sherlock_watson_synthetic_validation.ps1:1)
    - **Sherlock/Watson (obsolète)**:
        - Divers scripts `run_*.py` dans [`archived_scripts/obsolete_migration_2025/directories/sherlock_watson/`](archived_scripts/obsolete_migration_2025/directories/sherlock_watson/)
    - **Scripts de validation (obsolète)**:
        - [`archived_scripts/obsolete_migration_2025/directories/validation/unified_validation.py`](archived_scripts/obsolete_migration_2025/directories/validation/unified_validation.py:1)
        - [`archived_scripts/obsolete_migration_2025/scripts/validate_unified_system.py`](archived_scripts/obsolete_migration_2025/scripts/validate_unified_system.py:1)

Il est crucial de ne pas considérer les scripts dans `obsolete_migration_2025/` comme des points d'entrée actuels, mais ils peuvent être utiles pour comprendre l'évolution du projet.
## Fichiers à la Racine du Projet

Ces fichiers sont souvent des points d'entrée directs pour la configuration, l'exécution de tâches courantes ou la compréhension globale du projet.

### Scripts d'Activation et de Configuration d'Environnement

- **[`activate_project_env.ps1`](activate_project_env.ps1:1)** et **[`activate_project_env.sh`](activate_project_env.sh:1)**: Scripts pour activer l'environnement virtuel du projet (PowerShell et Bash).
- **[`setup_project_env.ps1`](setup_project_env.ps1:1)** et **[`setup_project_env.sh`](setup_project_env.sh:1)**: Scripts pour configurer l'environnement du projet (installation de dépendances, etc.).
- **[`environment.yml`](environment.yml:1)**: Fichier de configuration d'environnement Conda.
- **[`requirements.txt`](requirements.txt:1)**: Liste des dépendances Python pour `pip`.
- **[`pyproject.toml`](pyproject.toml:1)**: Fichier de configuration de projet Python (peut inclure des dépendances, des configurations d'outils comme Black, Flake8, etc.).
- **[`setup.py`](setup.py:1)**: Script de configuration pour `setuptools`, utilisé pour packager le projet Python.

### Scripts d'Exécution et de Test Principaux

- **[`run_tests.ps1`](run_tests.ps1:1)** et **[`run_tests.sh`](run_tests.sh:1)**: Scripts principaux pour lancer les suites de tests.
- **[`run_all_new_component_tests.sh`](run_all_new_component_tests.sh:1)**: Lance les tests pour les nouveaux composants.
- **[`run_sherlock_watson_synthetic_validation.ps1`](run_sherlock_watson_synthetic_validation.ps1:1)** et **[`run_sherlock_watson_synthetic_validation.sh`](run_sherlock_watson_synthetic_validation.sh:1)**: Scripts pour la validation synthétique de Sherlock/Watson.
- **[`start_webapp.py`](start_webapp.py:1)**: Script Python pour démarrer l'application web.
- **[`test_api_connectivity.py`](test_api_connectivity.py:1)**: Teste la connectivité de l'API.

### Scripts d'Orchestration et d'Analyse

- **[`orchestrate_complex_analysis.py`](orchestrate_complex_analysis.py:1)**: Orchestre une analyse complexe.
- **[`orchestrate_with_existing_tools.py`](orchestrate_with_existing_tools.py:1)**: Orchestre des tâches en utilisant les outils existants.
- **[`analyze_random_extract.py`](analyze_random_extract.py:1)**: Analyse un extrait aléatoire.
- **[`investigate_semantic_kernel.py`](investigate_semantic_kernel.py:1)**: Script d'investigation pour Semantic Kernel.

### Configuration de Tests

- **[`pytest.ini`](pytest.ini:1)**: Configuration Pytest à la racine (peut être prioritaire ou complémentaire à celui dans `config/`).
- **[`conftest.py`](conftest.py:1)**: Fichier de configuration Pytest pour les fixtures et plugins locaux.
- **[`playwright.config.js`](playwright.config.js:1)**: Fichier de configuration pour Playwright (tests E2E web).

### Documentation et Rapports Principaux

- **[`README.md`](README.md:1)**: Le fichier README principal du projet, point d'entrée crucial pour la compréhension.
- **[`CHANGELOG.md`](CHANGELOG.md:1)**: Journal des modifications du projet.
- **[`LICENSE`](LICENSE:1)**: Informations sur la licence du projet.
- **Divers fichiers `RAPPORT_*.md` et `CARTOGRAPHIE_*.md`**: Ces fichiers semblent être des rapports et des cartographies générés ou manuels importants pour le suivi du projet.
    - [`CARTOGRAPHIE_5_POINTS_ENTREE_PRINCIPAUX.md`](CARTOGRAPHIE_5_POINTS_ENTREE_PRINCIPAUX.md:1)
    - [`DIAGNOSTIC_SYSTÈME_AGENTIQUE_COMPLET_20250610.md`](DIAGNOSTIC_SYSTÈME_AGENTIQUE_COMPLET_20250610.md:1)
    - [`GUIDE_DEMARRAGE_RAPIDE_PROJET_EPITA.md`](GUIDE_DEMARRAGE_RAPIDE_PROJET_EPITA.md:1)

### Fichiers de Log

- Plusieurs fichiers `.log` (ex: [`agents_logiques_production.log`](agents_logiques_production.log:1), [`cluedo_oracle_complete.log`](cluedo_oracle_complete.log:1)) : Contiennent des traces d'exécution, utiles pour le débogage mais pas des points d'entrée.
## Fichiers Spéciaux (Docker, Makefile, Notebooks)

### Docker et Docker Compose

- Aucun fichier `Dockerfile` ou `docker-compose.yml` principal n'a été identifié à la racine du projet ou dans les répertoires principaux (`scripts/`, `api/`, `services/`, `libs/`, `project_core/`, `config/`).
- Des mentions de `Dockerfile` existent dans le code source de la bibliothèque Python `docker` (par exemple, dans [`venv_test/Lib/site-packages/docker/api/build.py`](venv_test/Lib/site-packages/docker/api/build.py:1)) et dans les métadonnées de `torch` ([`venv_test/Lib/site-packages/torch-2.7.1.dist-info/METADATA`](venv_test/Lib/site-packages/torch-2.7.1.dist-info/METADATA:1) qui référence `docker.Makefile`).
- Le serveur de langage pour Dockerfiles est mentionné dans les entry_points de `jupyter_lsp` ([`venv_test/Lib/site-packages/jupyter_lsp-2.2.5.dist-info/entry_points.txt`](venv_test/Lib/site-packages/jupyter_lsp-2.2.5.dist-info/entry_points.txt:1)).

### Makefiles

- Aucun `Makefile` principal pour le projet n'a été identifié à la racine ou dans les répertoires principaux.
- Des mentions de `Makefile` apparaissent dans les fichiers `.npmignore` de certains `node_modules` (par exemple, [`services/web_api/interface-web-argumentative/node_modules/utils-merge/.npmignore`](services/web_api/interface-web-argumentative/node_modules/utils-merge/.npmignore:1)), indiquant qu'ils sont utilisés pour la construction de ces modules spécifiques.
- Le code source de `urllib3` et `pip/_vendor/urllib3` contient des références à `makefile.py` pour la gestion des connexions.

### Notebooks Jupyter (`.ipynb`)

- La recherche initiale a trouvé des notebooks, mais principalement dans les répertoires `venv_test/Lib/site-packages/` (ex: `tqdm`, `transformers`, `nbformat`, `nbconvert`, `jupyter_ui_poll`). Ce sont des exemples ou des fichiers de documentation des bibliothèques elles-mêmes, et non des points d'entrée directs du projet pour l'analyse ou la démo.
- Une recherche plus ciblée est nécessaire pour identifier les notebooks spécifiques au projet dans des répertoires comme `demos/`, `examples/`, `tutorials/` ou `argumentation_analysis/`.
## Points d'Entrée par Composant

### 1. Tests

#### Scripts de Lancement de Tests Principaux
- **[`run_tests.ps1`](run_tests.ps1:1)** (Racine): Script PowerShell principal pour lancer les tests.
- **[`run_tests.sh`](run_tests.sh:1)** (Racine): Script Shell principal pour lancer les tests.
- **[`scripts/run_all_and_test.ps1`](scripts/run_all_and_test.ps1:1)**: Lance une suite complète de tests et de validations.
- **[`project_core/test_runner.py`](project_core/test_runner.py:1)**: Runner de test Python centralisé.
- **[`scripts/testing/simple_test_runner.py`](scripts/testing/simple_test_runner.py:1)**: Runner de test simple.
- **[`scripts/testing/run_tests_alternative.py`](scripts/testing/run_tests_alternative.py:1)**: Runner de test alternatif.
- **[`run_all_new_component_tests.sh`](run_all_new_component_tests.sh:1)** (Racine): Lance les tests pour les nouveaux composants.

#### Configurations Pytest
- **[`pytest.ini`](pytest.ini:1)** (Racine): Configuration Pytest globale.
- **[`conftest.py`](conftest.py:1)** (Racine): Fixtures et plugins Pytest locaux.
- **[`config/pytest.ini`](config/pytest.ini:1)**: Configuration Pytest dans le répertoire `config/`.
- **Répertoire [`config/pytest/`](config/pytest/):** Contient des configurations Pytest spécifiques :
    - [`config/pytest/pytest_jvm_only.ini`](config/pytest/pytest_jvm_only.ini:1)
    - [`config/pytest/pytest_phase2.ini`](config/pytest/pytest_phase2.ini:1)
    - [`config/pytest/pytest_phase3.ini`](config/pytest/pytest_phase3.ini:1)
    - [`config/pytest/pytest_phase4_final.ini`](config/pytest/pytest_phase4_final.ini:1)
    - [`config/pytest/pytest_recovery.ini`](config/pytest/pytest_recovery.ini:1)
    - [`config/pytest/pytest_simple.ini`](config/pytest/pytest_simple.ini:1)
    - [`config/pytest/pytest_stable.ini`](config/pytest/pytest_stable.ini:1)
- **Répertoire [`tests/unit/orchestration/`](tests/unit/orchestration/):**
    - [`tests/unit/orchestration/pytest.ini`](tests/unit/orchestration/pytest.ini:1)

#### Tests d'Intégration et E2E Spécifiques
- **[`scripts/run_webapp_integration.py`](scripts/run_webapp_integration.py:1)**: Script d'intégration pour l'application web.
- **[`scripts/pipelines/run_web_e2e_pipeline.py`](scripts/pipelines/run_web_e2e_pipeline.py:1)**: Exécute le pipeline de tests de bout en bout pour le web.
- **[`scripts/test_playwright_headless.ps1`](scripts/test_playwright_headless.ps1:1)**: Lance les tests Playwright en mode headless.
- **[`playwright.config.js`](playwright.config.js:1)** (Racine): Fichier de configuration pour Playwright.
- **Répertoire [`tests_playwright/`](tests_playwright/):** Contient les tests Playwright.
    - [`tests_playwright/playwright.config.js`](tests_playwright/playwright.config.js:1)
    - [`tests_playwright/tests/api-backend.spec.js`](tests_playwright/tests/api-backend.spec.js:1)
    - [`tests_playwright/tests/flask-interface.spec.js`](tests_playwright/tests/flask-interface.spec.js:1)
- **[`services/web_api/test_interfaces_integration.py`](services/web_api/test_interfaces_integration.py:1)**: Tests d'intégration des interfaces web.
- **[`services/web_api/interface-simple/test_integration.py`](services/web_api/interface-simple/test_integration.py:1)**: Tests d'intégration pour l'interface simple.

#### Scripts de Validation (pouvant inclure des tests)
- **[`scripts/sprint3_final_validation.py`](scripts/sprint3_final_validation.py:1)**
- **[`scripts/maintenance/final_system_validation_corrected.py`](scripts/maintenance/final_system_validation_corrected.py:1)**
- **[`scripts/validation/unified_validation.py`](scripts/validation/unified_validation.py:1)**
- **[`scripts/validation/test_epita_custom_data_processing.py`](scripts/validation/test_epita_custom_data_processing.py:1)**
- **[`validate_jdk_installation.py`](validate_jdk_installation.py:1)** (Racine)
- **[`validate_lot2_purge.py`](validate_lot2_purge.py:1)** (Racine)

#### Scripts de Test d'Environnement
- **[`scripts/test_environment_simple.py`](scripts/test_environment_simple.py:1)**
- **[`scripts/setup/validate_environment.py`](scripts/setup/validate_environment.py:1)**

#### Fichiers de Test Spécifiques (Exemples)
- Le répertoire `tests/` contient de nombreux scripts de test unitaires et d'intégration. Par exemple :
    - [`tests/unit/config/test_unified_config.py`](tests/unit/config/test_unified_config.py:1)
    - [`tests/validation_sherlock_watson/test_diagnostic.py`](tests/validation_sherlock_watson/test_diagnostic.py:1)
    - [`test_api_connectivity.py`](test_api_connectivity.py:1) (Racine)
### 2. Démo Epita

Les points d'entrée spécifiques à la démo Epita peuvent inclure des scripts de lancement dédiés, des configurations particulières ou des notebooks de présentation.

#### Scripts de Lancement et de Démonstration
- **[`scripts/start_full_app.ps1`](scripts/start_full_app.ps1:1)**: Pourrait être utilisé pour lancer l'application complète en mode démo.
- **[`services/web_api/start_full_system.py`](services/web_api/start_full_system.py:1)**: Similaire, pour démarrer tous les services nécessaires à une démo.
- **[`services/web_api/start_simple_only.py`](services/web_api/start_simple_only.py:1)**: Pourrait servir à une démo simplifiée.
- **[`scripts/rhetorical_analysis/educational_showcase_system.py`](scripts/rhetorical_analysis/educational_showcase_system.py:1)**: Système de démonstration spécifiquement pour l'analyse rhétorique, potentiellement pour Epita.
- **[`scripts/sherlock_watson/run_cluedo_oracle_enhanced.py`](scripts/sherlock_watson/run_cluedo_oracle_enhanced.py:1)**: Démo Cluedo, un cas d'usage classique pour Epita.
- **[`scripts/sherlock_watson/run_einstein_oracle_demo.py`](scripts/sherlock_watson/run_einstein_oracle_demo.py:1)**: Démo de l'oracle d'Einstein.
- **[`scripts/sherlock_watson/run_real_sherlock_watson_moriarty.py`](scripts/sherlock_watson/run_real_sherlock_watson_moriarty.py:1)**: Simulation complète qui pourrait être utilisée en démo.
- **[`start_webapp.py`](start_webapp.py:1)** (Racine): Script Python pour démarrer l'application web, potentiellement pour la démo.

#### Interfaces Web Utilisables pour la Démo
- **Interface Web Simple**:
    - Point d'entrée principal: [`services/web_api/interface-simple/app.py`](services/web_api/interface-simple/app.py:1)
    - Fichier HTML: [`services/web_api/interface-simple/templates/index.html`](services/web_api/interface-simple/templates/index.html:1)
- **Interface Web Argumentative (React)**:
    - Point d'entrée (via `npm start` ou équivalent, configuré dans [`services/web_api/interface-web-argumentative/package.json`](services/web_api/interface-web-argumentative/package.json:1))
    - Fichier HTML hôte: [`services/web_api/interface-web-argumentative/public/index.html`](services/web_api/interface-web-argumentative/public/index.html:1)
- **API depuis `libs` avec exemple HTML**:
    - Point d'entrée API: [`services/web_api_from_libs/app.py`](services/web_api_from_libs/app.py:1)
    - Exemple d'utilisation: [`services/web_api_from_libs/example_usage.html`](services/web_api_from_libs/example_usage.html:1)

#### Scripts de Validation Spécifiques à Epita (pouvant servir de démo de capacités)
- **[`scripts/validation/test_epita_custom_data_processing.py`](scripts/validation/test_epita_custom_data_processing.py:1)**

#### Documentation et Rapports de Démo
- **[`GUIDE_DEMARRAGE_RAPIDE_PROJET_EPITA.md`](GUIDE_DEMARRAGE_RAPIDE_PROJET_EPITA.md:1)** (Racine): Guide de démarrage qui pourrait être utilisé pour préparer ou exécuter une démo.
- **[`RAPPORT_VALIDATION_DEMO_EPITA.md`](RAPPORT_VALIDATION_DEMO_EPITA.md:1)** (Racine): Rapport de validation de la démo Epita.
- **[`RAPPORT_CONSOLIDATION_DEMO_EPITA_20250610_115359.md`](RAPPORT_CONSOLIDATION_DEMO_EPITA_20250610_115359.md:1)** (Racine)

#### Notebooks Jupyter
- Aucuns notebooks spécifiques pour la démo Epita n'ont été trouvés dans les répertoires `demos/`, `examples/`, `tutorials/`. Si des notebooks sont utilisés pour la démo, ils pourraient se trouver ailleurs ou être générés dynamiquement.
### 3. Analyse Rhétorique

Ce composant se concentre sur l'analyse rhétorique de textes.

#### Scripts d'Analyse et Pipelines
- **[`scripts/pipelines/run_rhetorical_analysis_pipeline.py`](scripts/pipelines/run_rhetorical_analysis_pipeline.py:1)**: Point d'entrée principal pour exécuter le pipeline complet d'analyse rhétorique.
- **[`scripts/rhetorical_analysis/unified_production_analyzer.py`](scripts/rhetorical_analysis/unified_production_analyzer.py:1)**: Analyseur unifié pour la production, utilisé dans le cadre de l'analyse rhétorique.
- **[`scripts/rhetorical_analysis/educational_showcase_system.py`](scripts/rhetorical_analysis/educational_showcase_system.py:1)**: Système de démonstration éducatif pour l'analyse rhétorique, peut aussi servir de point d'entrée pour des analyses spécifiques.
- **[`orchestrate_complex_analysis.py`](orchestrate_complex_analysis.py:1)** (Racine): Pourrait être utilisé pour orchestrer des tâches d'analyse rhétorique complexes.
- **[`analyze_random_extract.py`](analyze_random_extract.py:1)** (Racine): Pourrait être utilisé pour des tests ou des analyses ponctuelles d'extraits.

#### API Endpoints (potentiels)
- L'API principale définie dans [`api/main.py`](api/main.py:1) et [`api/endpoints.py`](api/endpoints.py:1) pourrait exposer des endpoints pour l'analyse rhétorique. Les services correspondants seraient dans [`api/services.py`](api/services.py:1).
- L'API construite à partir des bibliothèques, définie dans [`services/web_api_from_libs/app.py`](services/web_api_from_libs/app.py:1), pourrait également avoir des routes dédiées à l'analyse rhétorique, via [`services/web_api_from_libs/services/analysis_service.py`](services/web_api_from_libs/services/analysis_service.py:1).

#### Interfaces Utilisateur
- **Interface Web Argumentative (React)**: Accessible via `npm start` (voir [`services/web_api/interface-web-argumentative/package.json`](services/web_api/interface-web-argumentative/package.json:1)). Cette interface pourrait inclure des fonctionnalités d'analyse rhétorique.
    - Composants potentiellement liés :
        - [`services/web_api/interface-web-argumentative/src/components/ArgumentAnalyzer.js`](services/web_api/interface-web-argumentative/src/components/ArgumentAnalyzer.js:1)
        - [`services/web_api/interface-web-argumentative/src/components/FallacyDetector.js`](services/web_api/interface-web-argumentative/src/components/FallacyDetector.js:1)
- **Interface Web Simple**: Accessible via [`services/web_api/interface-simple/app.py`](services/web_api/interface-simple/app.py:1). Pourrait offrir des fonctionnalités d'analyse de base.

#### Configurations Spécifiques
- **[`scripts/rhetorical_analysis/comprehensive_config_example.json`](scripts/rhetorical_analysis/comprehensive_config_example.json:1)**: Exemple de configuration complète pour l'analyse rhétorique.
- **[`scripts/rhetorical_analysis/config_example.json`](scripts/rhetorical_analysis/config_example.json:1)**: Exemple de configuration de base.
- **[`scripts/rhetorical_analysis/educational_config_example.json`](scripts/rhetorical_analysis/educational_config_example.json:1)**: Exemple de configuration pour le système éducatif.

#### Tests et Validation
- **[`scripts/validation/validation_point4_rhetorical_analysis.py`](archived_scripts/obsolete_migration_2025/scripts/validation_point4_rhetorical_analysis.py:1)** (script archivé mais indicatif) : Validait spécifiquement l'analyse rhétorique.
- Des tests unitaires pour les modules d'analyse rhétorique devraient exister dans le répertoire `tests/`.

#### Documentation
- **[`scripts/rhetorical_analysis/README_ARCHITECTURE_CENTRALE.md`](scripts/rhetorical_analysis/README_ARCHITECTURE_CENTRALE.md:1)**: Documentation sur l'architecture centrale de l'analyse rhétorique.
- **[`RAPPORT_VALIDATION_SYSTEME_RHETORIQUE.md`](RAPPORT_VALIDATION_SYSTEME_RHETORIQUE.md:1)** (Racine): Rapport de validation du système rhétorique.

#### Notebooks Jupyter
- Aucuns notebooks spécifiques à l'analyse rhétorique n'ont été trouvés dans les répertoires principaux.
### 4. Sherlock/Watson/Moriarty

Ce composant est axé sur la simulation et l'analyse de scénarios de type Cluedo, impliquant les agents Sherlock, Watson et Moriarty.

#### Scripts d'Orchestration et de Simulation Principaux
- **[`scripts/sherlock_watson/run_real_sherlock_watson_moriarty.py`](scripts/sherlock_watson/run_real_sherlock_watson_moriarty.py:1)**: Lance la simulation complète et "réelle" avec les trois agents. C'est un point d'entrée majeur.
- **[`scripts/sherlock_watson/run_authentic_sherlock_watson_no_java.py`](scripts/sherlock_watson/run_authentic_sherlock_watson_no_java.py:1)**: Version sans dépendance Java, potentiellement pour des environnements spécifiques ou des tests.
- **[`scripts/sherlock_watson/run_cluedo_oracle_enhanced.py`](scripts/sherlock_watson/run_cluedo_oracle_enhanced.py:1)**: Lance la démo Cluedo avec un oracle amélioré, un scénario clé pour ce composant.
- **[`scripts/sherlock_watson/run_einstein_oracle_demo.py`](scripts/sherlock_watson/run_einstein_oracle_demo.py:1)**: Démo de l'oracle d'Einstein, un autre scénario de test/démonstration.
- **[`scripts/sherlock_watson/orchestrate_dynamic_cases.py`](scripts/sherlock_watson/orchestrate_dynamic_cases.py:1)**: Permet d'orchestrer des cas de test dynamiques pour ce composant.
- **[`run_sherlock_watson_synthetic_validation.ps1`](run_sherlock_watson_synthetic_validation.ps1:1)** (Racine) et **[`run_sherlock_watson_synthetic_validation.sh`](run_sherlock_watson_synthetic_validation.sh:1)** (Racine): Scripts pour la validation synthétique de Sherlock/Watson.

#### Scripts de Test et de Validation Spécifiques
- **[`scripts/sherlock_watson/test_oracle_behavior_demo.py`](scripts/sherlock_watson/test_oracle_behavior_demo.py:1)**: Teste le comportement de l'oracle en mode démo.
- **[`scripts/sherlock_watson/test_oracle_behavior_simple.py`](scripts/sherlock_watson/test_oracle_behavior_simple.py:1)**: Teste le comportement de l'oracle en mode simple.
- **[`scripts/sherlock_watson/validation_point1_simple.py`](scripts/sherlock_watson/validation_point1_simple.py:1)**: Script de validation simple pour un point de contrôle.
- **Répertoire [`tests/validation_sherlock_watson/`](tests/validation_sherlock_watson/):** Contient de nombreux scripts de tests dédiés à la validation des scénarios Sherlock/Watson.
    - Exemples:
        - [`tests/validation_sherlock_watson/test_analyse_simple.py`](tests/validation_sherlock_watson/test_analyse_simple.py:1)
        - [`tests/validation_sherlock_watson/test_cluedo_dataset_simple.py`](tests/validation_sherlock_watson/test_cluedo_dataset_simple.py:1)
        - [`tests/validation_sherlock_watson/test_diagnostic.py`](tests/validation_sherlock_watson/test_diagnostic.py:1)
        - [`tests/validation_sherlock_watson/test_final_oracle_simple.py`](tests/validation_sherlock_watson/test_final_oracle_simple.py:1)

#### Dépendances Clés
- Les bibliothèques TweetyProject (fichiers `.jar` dans [`libs/`](libs/) et [`libs/tweety/`](libs/tweety/)) sont essentielles pour la logique et l'argumentation sous-jacentes à ces simulations. L'interaction se fait probablement via JPype.

#### Fichiers de Log (pour le débogage)
- [`sherlock_watson_authentic.log`](sherlock_watson_authentic.log:1) (Racine)
- [`sherlock_watson_moriarty_real_trace.log`](sherlock_watson_moriarty_real_trace.log:1) (Racine)
- [`cluedo_oracle_complete.log`](cluedo_oracle_complete.log:1) (Racine)

#### Notebooks Jupyter
- Aucuns notebooks spécifiques à Sherlock/Watson n'ont été trouvés dans les répertoires principaux. Les analyses ou visualisations pourraient être faites via des scripts Python générant des rapports.
### 5. Applications Web

Ce composant regroupe les différentes applications et interfaces web du projet.

#### Serveurs d'Application Principaux
- **API Principale (FastAPI/Flask)**:
    - Point d'entrée: [`api/main.py`](api/main.py:1) (ou [`api/main_simple.py`](api/main_simple.py:1))
    - Configuration: [`config/webapp_config.yml`](config/webapp_config.yml:1), variables d'environnement (`.env.*`)
- **Application Web Simple (Flask/FastAPI)**:
    - Point d'entrée: [`services/web_api/interface-simple/app.py`](services/web_api/interface-simple/app.py:1)
- **Application Web construite depuis `libs` (Flask/FastAPI)**:
    - Point d'entrée: [`services/web_api_from_libs/app.py`](services/web_api_from_libs/app.py:1)

#### Applications Client (Frontend)
- **Interface Web Argumentative (React)**:
    - Point d'entrée: `npm start` (ou `yarn start`) dans le répertoire [`services/web_api/interface-web-argumentative/`](services/web_api/interface-web-argumentative/). Le script est défini dans [`services/web_api/interface-web-argumentative/package.json`](services/web_api/interface-web-argumentative/package.json:1).
    - Fichier HTML principal: [`services/web_api/interface-web-argumentative/public/index.html`](services/web_api/interface-web-argumentative/public/index.html:1)
    - Code source principal: [`services/web_api/interface-web-argumentative/src/App.js`](services/web_api/interface-web-argumentative/src/App.js:1) et [`services/web_api/interface-web-argumentative/src/index.js`](services/web_api/interface-web-argumentative/src/index.js:1).

#### Scripts de Démarrage et de Gestion des Applications Web
- **[`start_webapp.py`](start_webapp.py:1)** (Racine): Script Python pour démarrer l'application web (probablement l'API principale ou une combinaison).
- **[`scripts/start_full_app.ps1`](scripts/start_full_app.ps1:1)**: Démarre l'application complète, y compris potentiellement les serveurs web et les clients.
- **[`services/web_api/start_full_system.py`](services/web_api/start_full_system.py:1)**: Démarre l'ensemble des services du système web.
- **[`services/web_api/start_simple_only.py`](services/web_api/start_simple_only.py:1)**: Démarre uniquement les services web simples.
- **[`services/web_api/stop_all_services.py`](services/web_api/stop_all_services.py:1)**: Arrête tous les services web.
- **[`config/clean/web_application_launcher.ps1`](config/clean/web_application_launcher.ps1:1)**: Script PowerShell pour lancer l'application web, potentiellement avec une configuration spécifique.

#### Tests E2E et d'Intégration Web
- **Playwright**:
    - Configuration: [`playwright.config.js`](playwright.config.js:1) (Racine) et [`tests_playwright/playwright.config.js`](tests_playwright/playwright.config.js:1).
    - Scripts de test: Dans [`tests_playwright/tests/`](tests_playwright/tests/), par exemple [`tests_playwright/tests/flask-interface.spec.js`](tests_playwright/tests/flask-interface.spec.js:1).
    - Lancement via: [`scripts/test_playwright_headless.ps1`](scripts/test_playwright_headless.ps1:1).
- **Autres tests d'intégration**:
    - [`scripts/run_webapp_integration.py`](scripts/run_webapp_integration.py:1)
    - [`services/web_api/test_interfaces_integration.py`](services/web_api/test_interfaces_integration.py:1)
    - [`services/web_api/interface-simple/test_webapp.py`](services/web_api/interface-simple/test_webapp.py:1)
    - [`services/web_api/interface-simple/test_api_validation.py`](services/web_api/interface-simple/test_api_validation.py:1)

#### Configurations Docker/Docker-compose
- Aucuns fichiers `Dockerfile` ou `docker-compose.yml` dédiés aux applications web n'ont été trouvés dans les répertoires principaux. Si la conteneurisation est utilisée, elle pourrait être gérée par des scripts ou des configurations externes, ou les fichiers sont situés plus profondément dans la structure non explorée en détail.
- Des références à `Dockerfile` existent dans les dépendances (ex: `torch`, `docker` Python lib).

#### Rapports de Validation Web
- **[`RAPPORT_VALIDATION_WEB_API_FINAL.md`](RAPPORT_VALIDATION_WEB_API_FINAL.md:1)** (Racine).