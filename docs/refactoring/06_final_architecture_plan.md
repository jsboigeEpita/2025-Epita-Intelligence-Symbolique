# Plan de Refactoring v4 : Architecture Noyau Unifié

Ce document définit l'architecture finale pour la refactorisation des scripts du projet. Il prend en compte la hiérarchie des composants et servira de guide pour la ventilation de la logique.

## 1. Vision Architecturale Cible

Le projet s'articulera autour de trois couches de responsabilité distinctes :

1.  **`argumentation_analysis` (Noyau Applicatif Profond)**
    *   Contient toute la logique métier fondamentale de l'application (analyse d'arguments, modèles, etc.).
    *   **Responsabilité clé pour ce refactoring** : Doit fournir tous les helpers, configurations et classes de bas niveau pour la gestion de l'environnement d'exécution (chemins, API keys, configurations de logging, etc.). C'est la source de vérité pour la configuration de l'application.

2.  **`project_core` (Noyau Projet de Surface)**
    *   Contient toute la logique liée à la gestion du projet lui-même : initialisation, maintenance, validation, nettoyage, etc.
    *   Il s'appuie sur `argumentation_analysis` pour obtenir sa configuration et interagir avec l'environnement applicatif.
    *   Il expose des fonctions claires et de haut niveau (ex: `cleanup_repository()`, `validate_environment()`).

3.  **`scripts` (Façades CLI)**
    *   Contient uniquement des scripts "façades" extrêmement légers.
    *   Leur seul rôle est de parser les arguments de la ligne de commande et d'appeler les fonctions correspondantes dans `project_core`.
    *   Aucune logique métier ne doit y résider.

## 2. Plan d'Action

1.  [ ] **Phase 1 : Exploration du Noyau Profond**
    *   [ ] Lister et analyser le contenu de `argumentation_analysis` pour identifier les modules pertinents (ex: `core`, `config`, `utils`, `setup`).
    *   [ ] Identifier les singletons, les classes de configuration et les helpers d'environnement existants.
    *   [ ] Documenter les points d'entrée pour la configuration dans ce plan.

2.  [ ] **Phase 2 : Définition des Modules Cibles**
    *   [ ] Sur la base de l'exploration, définir précisément quels modules dans `argumentation_analysis` seront enrichis.
    *   [ ] Définir la structure des nouveaux modules à créer dans `project_core/core_from_scripts`.

3.  [ ] **Phase 3 : Ventilation de la Logique**
    *   [ ] Reprendre l'analyse systématique des scripts du répertoire `scripts/`.
    *   [ ] Pour chaque fonctionnalité, la mapper à sa destination finale : un module dans `argumentation_analysis` ou `project_core`.

4.  [ ] **Phase 4 : Implémentation**
    *   [ ] Migration incrémentale de la logique vers les modules cibles.
    *   [ ] Remplacement des anciens scripts par les nouvelles façades.

## 3. Exploration `argumentation_analysis`

L'exploration du répertoire `argumentation_analysis/core/` a révélé des composants clés.

*   **`environment.py`** :
    *   **Rôle** : Agit comme un **garde-fou**. Il ne tente plus d'activer l'environnement, mais vérifie que l'environnement Conda correct est déjà actif.
    *   **Mécanisme** : S'exécute à l'import. Un simple `import argumentation_analysis.core.environment` en tête de script suffit à sécuriser son exécution.
    *   **Conclusion** : Toute logique d'activation manuelle dans les anciens scripts est obsolète et doit être remplacée par cet import.

*   **`bootstrap.py`** :
    *   **Rôle** : C'est le **chef d'orchestre** de l'initialisation.
    *   **Mécanisme** : La fonction `initialize_project_environment()` retourne un objet `ProjectContext` qui contient tous les services initialisés et prêts à l'emploi (CryptoService, DefinitionService, état de la JVM, etc.).
    *   **Conclusion** : Les modules de `project_core` devront appeler cette fonction pour obtenir un contexte applicatif fonctionnel avant d'exécuter leur logique.

*   **`utils/` (Répertoire)** :
    *   **Rôle** : Une **boîte à outils** complète et granulaire pour les opérations de bas niveau (fichiers, logs, shell, etc.).
    *   **Conclusion** : La logique des scripts de maintenance sera principalement migrée vers ces utilitaires, qui seront ensuite appelés par les modules de `project_core`.

*   **`activate_project_env.ps1` et Chaînon Retrouvé**
    *   **Rôle** : `activate_project_env.ps1` est un **délégateur**.
    *   **Problème** : Il pointe vers un script manquant (`scripts/run_in_env.py`).
    *   **Découverte** : Le fichier **`project_core/core_from_scripts/environment_manager.py`** remplit déjà ce rôle de "runner". Il contient la logique pour trouver et exécuter des commandes dans le bon environnement Conda.
    *   **Solution** :
        1.  **Corriger `activate_project_env.ps1`** pour qu'il appelle `python project_core/core_from_scripts/environment_manager.py --run-command ...`.
    *   **Conclusion** : Le chaînon manquant est retrouvé. La base d'exécution des scripts est saine, elle nécessite juste une correction de pointeur.

*Cette section sera complétée par l'analyse des autres répertoires (`config`, `agents/utils`, etc.).*

## 4. Phase 2 : Architecture Cible et Modules Managers Réels

L'analyse de `project_core` révèle une architecture existante robuste. Nous allons bâtir sur celle-ci.

### 4.1. Enrichissement du Noyau Applicatif (`argumentation_analysis`)

L'analyse confirme que ce noyau contient des briques fondamentales et robustes.
*   **`argumentation_analysis/config/settings.py`**: C'est la **source de vérité unique** pour toute la configuration (clés, versions, chemins), gérée via Pydantic. Toute valeur codée en dur dans les anciens scripts devra migrer vers ce système ou être passée en argument de la CLI.
*   **`argumentation_analysis/core/jvm_setup.py`**: **Module à déplacer**. Contient la logique experte pour provisionner un JDK portable et les JARs Tweety. Il sera déplacé vers `project_core/core_from_scripts/jvm_manager.py` pour centraliser la gestion de l'outillage.
*   **`argumentation_analysis/services/`**: Contient des services de haut niveau (`CryptoService`, `DefinitionService`) qui seront appelés par les managers de `project_core` via le `ProjectContext` fourni par `bootstrap.py`.
*   **`argumentation_analysis/core/utils/`**: Ces utilitaires (`filesystem_utils`, `shell_utils`) sont les briques de base pour nos futurs managers. Au lieu de réimplémenter des appels à `os` ou `subprocess`, les managers utiliseront systématiquement ces fonctions.

### 4.2. Consolidation dans les Managers du Noyau Projet (`project_core`)

La logique d'orchestration de haut niveau sera intégrée dans les managers existants.

*   **`project_core/core_from_scripts/environment_manager.py`** (Orchestrateur de haut niveau) :
    *   **Rôle Actuel** : Trouver l'environnement Conda et exécuter des commandes.
    *   **Évolution** : Deviendra le cœur de la **réparation de l'environnement**. Il n'appellera plus `subprocess` directement, mais orchestrera les managers de plus bas niveau.
    *   **Dépendances Clés** :
        *   Utilisera `project_core/environment/conda_manager.py` pour toute interaction avec Conda (lister/créer/exécuter).
        *   Utilisera `project_core/environment/python_manager.py` pour gérer les dépendances `pip` (installer/vérifier).
    *   **Logique à intégrer** : Les stratégies complexes de `fix-deps` (cascade de méthodes, `vcvars`, wheels précompilés) et de `compat`.

*   **`project_core/core_from_scripts/project_setup.py`** :
    *   **Rôle Actuel** : Orchestrer le setup et la vérification du projet.
    *   **Évolution** : Deviendra le manager `setup` de haut niveau, qui utilisera `EnvironmentManager` et `ValidationEngine` pour gérer l'installation de dépendances, la configuration du `PYTHONPATH`, et la gestion des prérequis système (Build Tools).

*   **`project_core/core_from_scripts/validation_engine.py`** :
    *   **Rôle Actuel** : Valider les prérequis.
    *   **Évolution** : S'enrichira de toutes les logiques de **validation** : intégrité des imports, structure des fichiers, couverture de code, etc.

*   **`project_core/test_runner.py`** :
    *   **Rôle Actuel** : Orchestrateur de tests `pytest`.
    *   **Conclusion** : Reste le point d'entrée unique pour tous les tests. Il remplace nativement tous les anciens scripts `run_..._tests.py` ou `validate_...tests.ps1`.

*   **`project_core/service_manager.py`** :
    *   **Rôle Actuel** : Gestionnaire de services backend/frontend.
    *   **Évolution** : Son rôle est renforcé par la découverte de `PortManager`. Il sera le consommateur exclusif de `project_core/config/port_manager.py` pour allouer les ports dynamiquement avant de démarrer les services.
    *   **Conclusion** : C'est une brique fondamentale qui absorbe la logique de démarrage/arrêt de services. Il sera utilisé par le `TestRunner` pour les tests d'intégration et E2E.

*   **Nouveaux Managers à créer (inspirés du plan 05)** :
    *   **`project_core/core_from_scripts/repository_manager.py`**: Pour les interactions Git (`.gitignore`, `find-orphans`).
    *   **`project_core/core_from_scripts/refactoring_manager.py`**: Pour les transformations de code (`standardize_imports`).
    *   **`project_core/core_from_scripts/organization_manager.py`**: Pour les opérations de restructuration de fichiers (réorganisation de `results/`, nettoyage de la racine).
    *   **`project_core/core_from_scripts/cleanup_manager.py`**: Pour le nettoyage de bas niveau (fichiers temporaires, logs).
    *   **`project_core/core_from_scripts/environment_manager.py`**: Pour la gestion des fichiers d'environnement `.env`. Il permet de basculer, créer et valider des configurations d'environnement.

*   **`project_core/core_from_scripts/validation/validation_engine.py`** :
    *   **Rôle** : Moteur de validation centralisé, conçu pour être extensible.
    *   **Architecture** :
        *   Le `ValidationEngine` ne contient plus de logique de validation en dur. Il est responsable de charger et d'exécuter une série de "règles".
        *   Chaque règle est une classe qui hérite de `ValidationRule` et implémente une méthode `validate()`.
        *   Les règles sont stockées dans le sous-répertoire `project_core/core_from_scripts/validation/rules/`.
    *   **Exemple** : `ConfigValidationRule` est la première implémentation, vérifiant la présence des fichiers de configuration essentiels.
    *   **Conclusion** : Cette conception permet d'ajouter de nouvelles validations (tests d'imports, vérification de la structure des répertoires, etc.) de manière modulaire sans modifier le moteur principal. C'est un service de diagnostic essentiel pour les autres managers et pour les workflows de CI/CD.

## 5. Phase 3 : Ventilation de la Logique

Cette section mappe la logique des anciens scripts vers les modules cibles identifiés.

### 5.1. Ventilation de la Logique (Setup)

### Lot 1 : Gestion de l'environnement Java (ex `scripts/setup` lot 1)

*   **Anciens Scripts**:
    *   `scripts/setup/adapt_code_for_pyjnius.py`
    *   `scripts/setup/check_jpype_import.py`
    *   `scripts/setup/download_test_jars.py`
*   **Fonctionnalités**:
    *   `adapt`: Refactoring de `jpype` vers `pyjnius` (mocking, regex).
    *   `check`: validation de l'import `jpype`.
    *   `download`: téléchargement des `.jar` de test.
*   **Nouvelle Destination**:
    *   La logique de **compatibilité** (`adapt`) et de **réparation** sera dans `EnvironmentManager`.
    *   La logique de **validation** (`check`) ira dans `ValidationEngine` (ex: `validate_jvm_bridge()`).
    *   Le téléchargement des dépendances (`download`) fait partie du setup et ira dans `ProjectSetup`.
*   **Appel via Façade (`setup_manager.py`)**:
    *   `python setup_manager.py compat --fix-pyjnius`
    *   `python setup_manager.py validate --component jvm-bridge`
    *   `python setup_manager.py setup-deps --type test-jvm`

### Lot 2 : Correction des Dépendances (ex `scripts/setup` lot 2)

*   **Anciens Scripts**:
    *   `scripts/setup/fix_all_dependencies.ps1`
    *   `scripts/setup/fix_all_dependencies.py`
    *   `scripts/setup/fix_dependencies_for_python312.ps1`
*   **Fonctionnalité**: Réinstallation forcée et ciblée de dépendances Python.
*   **Nouvelle Destination**:
    *   La logique sera centralisée dans une fonction `fix_dependencies()` au sein de `EnvironmentManager`. Cette fonction détectera la version de Python et appliquera les stratégies adéquates en cascade.
*   **Appel via Façade (`setup_manager.py`)**:
    *   `python setup_manager.py fix-deps --package numpy pandas`

### Lot 3 : Réparation Avancée de l'Environnement (ex `scripts/setup` lot 3)

*   **Anciens Scripts**:
    *   `scripts/setup/fix_dependencies.py`
    *   `scripts/setup/fix_environment_auto.py`
    *   `scripts/setup/fix_pydantic_torch_deps.ps1`
    *   `scripts/setup/fix_pythonpath_manual.py`
*   **Fonctionnalités**:
    *   Installation depuis `requirements.txt`.
    *   Réparation spécifique de `pydantic` et `torch`.
    *   Création manuelle de fichier `.pth` pour le `PYTHONPATH`.
*   **Nouvelle Destination**:
    *   Logique d'installation depuis `requirements.txt` et réparation `pydantic/torch` -> `EnvironmentManager`.
    *   Gestion du `.pth` -> `ProjectSetup`.
*   **Appel via Façade (`setup_manager.py`)**:
    *   `python setup_manager.py fix-deps --from-requirements requirements-test.txt`
    *   `python setup_manager.py set-path`

### Lot 4 : Outils de Compilation et Dépendances Spécifiques (ex `scripts/setup` lot 4)

*   **Anciens Scripts**:
    *   `scripts/setup/install_build_tools.ps1`
    *   `scripts/setup/install_dung_deps.py`
*   **Fonctionnalités**:
    *   Installation des Visual Studio Build Tools.
    *   Installation des dépendances d'un sous-projet (`abs_arg_dung`).
*   **Nouvelle Destination**:
    *   Le script `install_build_tools.ps1` est **conservé** en tant qu'outil externe. Le `ValidationEngine` vérifiera si les outils sont installés et guidera l'utilisateur pour lancer le script si besoin.
    *   La logique de `install_dung_deps.py` sera une simple option de la commande `fix-deps` de `EnvironmentManager`.
*   **Appel via Façade (`setup_manager.py`)**:
    *   `python setup_manager.py validate --component build-tools`
    *   `python setup_manager.py fix-deps --from-requirements abs_arg_dung/requirements.txt`

### Lot 5 : La Saga de l'Installation de JPype (ex `scripts/setup` lot 5)

*   **Anciens Scripts**:
    *   `scripts/setup/install_jpype_for_python312.ps1`
    *   `scripts/setup/install_jpype_for_python313.ps1`
    *   `scripts/setup/install_jpype_with_vcvars.ps1`
*   **Fonctionnalité**: Logiques de réparation en cascade pour `JPype`.
*   **Nouvelle Destination**:
    *   Toute la logique sera implémentée dans `EnvironmentManager` en tant que routine de réparation configurable. Il utilisera `CondaManager` et `PythonManager` pour exécuter les commandes dans un environnement `vcvars` si nécessaire.
*   **Appel via Façade (`setup_manager.py`)**:
    *   `python setup_manager.py fix-deps --package JPype1 --strategy=aggressive`

### Lot 6 : Wheels Précompilés et Documentation (ex `scripts/setup` lot 6)

*   **Anciens Scripts**:
    *   `scripts/setup/install_prebuilt_wheels.ps1`
    *   `README_INSTALLATION_OUTILS_COMPILATION.md`
    *   `README_PYTHON312_COMPATIBILITY.md`
*   **Fonctionnalités**:
    *   Stratégie pour trouver et installer des wheels précompilés.
    *   Documentation critique pour l'utilisateur.
*   **Nouvelle Destination**:
    *   La stratégie de `install_prebuilt_wheels.ps1` sera une des étapes de la routine de réparation de `EnvironmentManager`.
    *   Le contenu des `READMEs` sera migré vers `docs/guides/developpement/01_environment_setup.md`.
*   **Appel via Façade (`setup_manager.py`)**:
    *   Il n'y a pas d'appel direct, cela fait partie de la logique interne de `fix-deps`.

### Lot 7 : Wrappers de Test et Documentation Finale (ex `scripts/setup` lot 7)

*   **Anciens Scripts**:
    *   `scripts/setup/run_mock_tests.py`
    *   `scripts/setup/run_tests_with_mock.py`
    *   `README.md`
*   **Fonctionnalités**:
    *   Lanceurs de `pytest` avec configuration de mock.
*   **Nouvelle Destination**:
    *   La configuration de l'environnement de test (avec ou sans mocks) est la responsabilité de `ProjectSetup`. Le `TestRunner` est ensuite le seul responsable du lancement des tests. Les scripts deviennent inutiles.
    *   Le `README.md` est migré vers la documentation centrale.
*   **Appel via Façade (`setup_manager.py` et `test_runner.py`)**:
    *   `python setup_manager.py setup-test-env --with-mocks`
    *   `python -m project_core.test_runner --all`

### Lot 8 : Configuration et Validation de l'Environnement de Test (ex `scripts/setup` lot 8)

*   **Anciens Scripts**:
    *   `scripts/setup/setup_test_env.py`
    *   `scripts/setup/validate_environment.py`
    *   Et 6 autres scripts de validation/setup.
*   **Fonctionnalités**:
    *   Orchestration du setup de l'environnement de test.
    *   Validation exhaustive des dépendances.
*   **Nouvelle Destination**:
    *   La logique de setup est absorbée par `ProjectSetup`, qui agit comme un orchestrateur de haut niveau.
    *   La logique de validation est entièrement transférée à `ValidationEngine`, qui devient un outil de diagnostic très puissant.
*   **Appel via Façade (`setup_manager.py`)**:
    *   `python setup_manager.py setup --env=test`
    *   `python setup_manager.py validate --all`

### 5.2. Ventilation de la Logique (Maintenance)

### Lot 9 : Le Grand Nettoyage (ex `scripts/maintenance` lot 9)

*   **Anciens Scripts**:
    *   `scripts/maintenance/cleanup/clean_project.ps1`
    *   `scripts/maintenance/cleanup/cleanup_project.py`
*   **Fonctionnalités**:
    *   Workflow complet de réorganisation du répertoire `results/` (sauvegarde, déplacement, génération de README).
    *   Nettoyage des fichiers temporaires (`__pycache__`, logs).
    *   Mise à jour du `.gitignore`.
*   **Nouvelle Destination**:
    *   La réorganisation de `results/` devient une fonction `organize_results_directory()` dans le nouveau `OrganizationManager`.
    *   Le nettoyage des fichiers temporaires ira dans `CleanupManager`.
    *   La mise à jour du `.gitignore` ira dans `RepositoryManager`.
*   **Appel via Façade (`maintenance_manager.py`)**:
    *   `python maintenance_manager.py organize --target results`
    *   `python maintenance_manager.py cleanup --type temp-files`
    *   `python maintenance_manager.py repo --update-gitignore`

### Lot 11 & 13 : Refactoring et Maintenance de la Documentation

*   **Anciens Scripts**:
    *   `scripts/maintenance/refactoring/update_imports.py`
    *   `scripts/maintenance/refactoring/comprehensive_documentation_fixer_safe.py`
*   **Fonctionnalités**:
    *   Standardisation des imports pour être absolus.
    *   Correction automatique des liens brisés dans la documentation.
*   **Nouvelle Destination**:
    *   La standardisation des imports sera une fonction `standardize_imports()` dans `RefactoringManager`.
    *   La correction des liens sera une fonction `fix_documentation_links()` dans `RepositoryManager`.
*   **Appel via Façade (`maintenance_manager.py`)**:
    *   `python maintenance_manager.py refactor --type imports --path argumentation_analysis/`
    *   `python maintenance_manager.py repo --fix-docs`

### Lot 12 : Gestion des Fichiers Orphelins

*   **Ancien Script**: `scripts/maintenance/refactoring/real_orphan_files_processor.py`
*   **Fonctionnalité**: Détection des fichiers non suivis par Git via `git status --porcelain`.
*   **Nouvelle Destination**:
    *   La logique est implémentée dans la fonction `find_untracked_files()` du `RepositoryManager`.
*   **Appel via Façade (`maintenance_manager.py`)**:
    *   `python maintenance_manager.py repo --find-orphans`

### Lot 14 : Validation Complète du Système

*   **Ancien Script**: `scripts/maintenance/refactoring/final_system_validation.py`
*   **Fonctionnalité**: Orchestration d'une série de tests (imports, structure, couverture, etc.) pour produire un rapport de santé global.
*   **Nouvelle Destination**:
    *   La logique d'orchestration sera dans `ProjectSetup` ou un nouveau manager `ValidationOrchestrator`. Il appellera les fonctions de `ValidationEngine` pour chaque étape.
    *   Le but est de reproduire le `final_system_validation.py` en s'appuyant sur les briques de `project_core`.
*   **Appel via Façade (`maintenance_manager.py`)**:
    *   `python maintenance_manager.py validate --all`
