# Feuille de Route d'Implémentation : Refactorisation des Scripts

Ce document transforme le plan architectural statique en une feuille de route dynamique et séquentielle. Il définit le "COMMENT" de la migration, en se concentrant sur une approche itérative, sécurisée et documentée.

## 1. Principes Directeurs de l'Implémentation

Toute cette phase de refactorisation sera guidée par les principes suivants pour garantir une transition réussie et sans friction :

*   **Approche Itérative et Incrémentale** : Nous allons "grignoter" la dette technique pas à pas. Chaque lot fonctionnel sera traité de manière atomique, évitant les "big bang" et permettant une validation continue.
*   **Qualité et Sécurité du Code** : Chaque nouvelle fonctionnalité ajoutée dans `project_core` doit être accompagnée de **tests unitaires** pertinents. Les modifications seront intégrées via des **commits atomiques**.
*   **Synchronisation Continue** : Après chaque commit validé, un cycle `git pull --rebase` suivi d'un `git push` sera effectué pour maintenir l'alignement avec la branche principale.
*   **Continuité de Service** : La migration sera conçue pour être la plus douce possible pour les utilisateurs (agents, élèves). Les anciens scripts ne seront supprimés qu'à la toute fin du processus, une fois que les nouvelles façades CLI seront pleinement fonctionnelles et validées.
*   **Documentation Continue** : La documentation sera mise à jour au fil de l'eau. Chaque lot inclura une tâche de documentation.
*   **Orchestration Claire** : Ce document sert de plan d'orchestration centralisé, décomposant l'effort complexe en une série de sous-tâches claires et gérables.

## 2. Stratégie de Migration en 3 Grandes Phases

### Phase I : Fondations et Consolidation des Managers

L'objectif de cette phase est de construire le "squelette" de notre architecture cible dans `project_core`. À la fin de cette phase, nous aurons une structure stable prête à accueillir la logique métier.

1.  **Créer les Squelettes des Nouveaux Managers** :
    *   Créer les fichiers Python vides pour les nouveaux managers identifiés dans `project_core/core_from_scripts/` :
        *   `repository_manager.py`
        *   `refactoring_manager.py`
        *   `organization_manager.py`
        *   `cleanup_manager.py`
        *   `jvm_manager.py` (pour la logique de `jvm_setup.py`)
2.  **Enrichir les Managers de Bas Niveau** :
    *   Intégrer les utilitaires découverts (`path_manager.py`, `tool_installer.py`) dans la logique des managers de plus haut niveau (`EnvironmentManager`, `ProjectSetup`).
3.  **Effectuer le "Lift & Shift" Initial** :
    *   Migrer la logique la plus évidente et la moins dépendante.
    *   **Tâche clé** : Déplacer le contenu de `argumentation_analysis/core/jvm_setup.py` vers `project_core/core_from_scripts/jvm_manager.py`. Mettre à jour les imports pour que `bootstrap.py` l'appelle depuis son nouvel emplacement.
4.  **Établir les Fondations des Tests** :
    *   Mettre en place la structure de test pour les nouveaux managers, avec des tests de base pour vérifier leur instanciation.

### Phase II : Migration Itérative par Lots Fonctionnels

C'est le cœur de l'implémentation. Chaque "lot" représente une fonctionnalité complète. L'ordre des lots est pensé pour construire sur des fondations solides.

#### Structure Standard d'un Lot d'Implémentation

Chaque lot suivra la structure détaillée ci-dessous pour garantir la cohérence, la qualité et la traçabilité du travail effectué.

```markdown
### Lot X : [Titre Clair de la Fonctionnalité]

*   **Référence Architecturale** : `docs/refactoring/06_final_architecture_plan.md` - Section(s) [Numéro de section]
*   **Objectif** : [Description concise de l'objectif du lot. Qu'est-ce qui sera fonctionnel à la fin ?]
*   **Description** : [Description plus détaillée du travail à effectuer, des anciens scripts remplacés et de la logique à migrer.]

**Checklist des Tâches :**

1.  **Implémentation du Manager (`project_core`)**
    *   [ ] Implémenter la fonction `[nom_de_la_fonction]` dans `[nom_du_manager].py`.
    *   [ ] S'assurer que la fonction s'appuie sur les utilitaires de `argumentation_analysis/core/utils` pour les opérations de bas niveau.
    *   [ ] Ajouter la gestion des erreurs et le logging pertinent.

2.  **Tests Unitaires (`tests/unit`)**
    *   [ ] Créer le fichier de test `tests/unit/project_core/managers/test_[nom_du_manager].py` s'il n'existe pas.
    *   [ ] Écrire un test unitaire `test_[nom_de_la_fonction]` qui valide le succès de l'opération.
    *   [ ] Écrire un test unitaire qui valide le comportement en cas d'erreur (ex: fichier non trouvé, permission refusée).

3.  **Façade CLI (`scripts`)**
    *   [ ] Créer le script `scripts/[nom_de_la_facade].py` s'il n'existe pas.
    *   [ ] Ajouter la commande (ex: `repo --find-orphans`) en utilisant `argparse` ou `click`.
    *   [ ] La commande doit uniquement parser les arguments et appeler la fonction correspondante dans le manager.
    *   [ ] Assurer une sortie utilisateur claire et informative.

4.  **Documentation**
    *   [ ] Dans le docstring de la fonction du manager, décrire son rôle, ses paramètres et ce qu'elle retourne.
    *   [ ] Mettre à jour (ou créer) un guide dans `docs/guides/cli/` expliquant comment utiliser la nouvelle commande.

5.  **Commit et Synchronisation**
    *   [ ] **Commit** : `git commit -m "[FEAT] [ManagerName] - Add [feature_name] functionality"`
    *   [ ] **Pull/Push** : Exécuter `git pull --rebase` puis `git push`.
```

### Phase III : Finalisation, Nettoyage et Documentation

Une fois que toute la logique a été migrée et validée.

1.  **Validation Globale** : Exécuter une campagne de tests complète (unitaires, intégration) pour s'assurer qu'il n'y a pas de régressions.
2.  **Suppression des Anciens Scripts** :
    *   Supprimer en une seule fois l'intégralité des scripts des répertoires `scripts/setup` et `scripts/maintenance` qui ont été remplacés.
3.  **Mise à Jour Massive de la Documentation** :
    *   Mettre à jour le `README.md` principal du projet.
    *   Mettre à jour tous les guides dans `docs/guides/`.
    *   Créer une nouvelle documentation dédiée à l'utilisation des nouvelles CLI (`setup_manager.py`, `maintenance_manager.py`).

---

## 3. Plan d'Orchestration Détaillé (Décomposition en Lots)

### Lot 1 : Gestion des Fichiers Orphelins (Validation du workflow Git)

*   **Référence Architecturale** : [`docs/refactoring/06_final_architecture_plan.md`](docs/refactoring/06_final_architecture_plan.md:280) - Section 5.2, Lot 12
*   **Objectif** : Activer la commande `maintenance_manager.py repo --find-orphans`. Ce lot sert de validation pour l'ensemble du processus (implémentation, test, CLI, commit, doc) sur une fonctionnalité à faible risque et bien isolée.
*   **Description** : Ce lot consiste à implémenter la détection des fichiers non suivis par Git. La logique, anciennement dans `real_orphan_files_processor.py`, sera déplacée dans le `RepositoryManager`. La fonction utilisera `git status --porcelain` pour identifier les fichiers et retournera une liste structurée.

**Checklist des Tâches :**

1.  **Implémentation du Manager (`project_core`)**
    *   [ ] Implémenter la fonction `find_untracked_files()` dans [`project_core/core_from_scripts/repository_manager.py`](project_core/core_from_scripts/repository_manager.py).
    *   [ ] La fonction doit appeler l'utilitaire `shell_utils.execute_command()` de `argumentation_analysis` pour lancer `git status --porcelain -u`.
    *   [ ] La sortie de la commande doit être parsée pour extraire les chemins des fichiers non suivis.
    *   [ ] La fonction doit retourner une liste de chemins de fichiers.
    *   [ ] Ajouter une gestion d'erreur si Git n'est pas installé ou si la commande échoue.

### Lot 2 : Nettoyage de Base (Fichiers Temporaires)

*   **Référence Architecturale** : [`docs/refactoring/06_final_architecture_plan.md`](docs/refactoring/06_final_architecture_plan.md:247) - Section 5.2, Lot 9
*   **Objectif** : Activer la commande `maintenance_manager.py cleanup --type temp-files`. Ce lot met en place le `CleanupManager` et une première fonctionnalité de nettoyage simple.
*   **Description** : Ce lot consiste à déplacer la logique de suppression des fichiers temporaires (répertoires `__pycache__` et fichiers `.log`) des anciens scripts vers une fonction dédiée dans un nouveau `CleanupManager`.

**Checklist des Tâches :**

1.  **Implémentation du Manager (`project_core`)**
    *   [ ] Créer le fichier [`project_core/core_from_scripts/cleanup_manager.py`](project_core/core_from_scripts/cleanup_manager.py)
    *   [ ] Implémenter la fonction `cleanup_temporary_files()` dans [`project_core/core_from_scripts/cleanup_manager.py`](project_core/core_from_scripts/cleanup_manager.py).
    *   [ ] La fonction doit utiliser `filesystem_utils` de `argumentation_analysis` pour trouver et supprimer récursivement les répertoires `__pycache__` et les fichiers se terminant par `.log`.
    *   [ ] La fonction doit retourner la liste des fichiers/dossiers supprimés.

2.  **Tests Unitaires (`tests/unit`)**
    *   [ ] Créer le fichier de test `tests/unit/project_core/managers/test_cleanup_manager.py`.
    *   [ ] Mettre en place un `setUp` qui crée une structure de répertoires et de fichiers de test (incluant des `__pycache__` et des `.log`).
    *   [ ] Écrire un test `test_cleanup_temporary_files` qui appelle la fonction et vérifie que les fichiers et dossiers ciblés ont bien été supprimés et que les autres sont intacts.
    *   [ ] Écrire un test `test_cleanup_temporary_files_no_files_to_clean` sur une structure propre et vérifier que la fonction retourne une liste vide.

3.  **Façade CLI (`scripts`)**
    *   [ ] Dans `scripts/maintenance_manager.py`, ajouter la sous-commande `cleanup --type temp-files` à `argparse`.
    *   [ ] La commande doit appeler `CleanupManager.cleanup_temporary_files()`.
    *   [ ] Si des fichiers ont été supprimés, afficher un message de succès avec le nombre de fichiers/dossiers nettoyés. Sinon, afficher "Aucun fichier temporaire à nettoyer."

4.  **Documentation**
    *   [ ] Rédiger le docstring de `cleanup_temporary_files` en expliquant son rôle et ce qu'elle retourne.
    *   [ ] Dans `docs/guides/cli/maintenance_manager.md`, ajouter une section pour la commande `cleanup --type temp-files`.

5.  **Commit et Synchronisation**
    *   [ ] **Commit** : `git commit -m "[FEAT] CleanupManager - Add temporary file cleanup functionality"`
    *   [ ] **Pull/Push** : Exécuter `git pull --rebase` puis `git push`.

2.  **Tests Unitaires (`tests/unit`)**
### Lot 3 : Refactoring du Code et Maintenance de la Documentation

*   **Référence Architecturale** : [`docs/refactoring/06_final_architecture_plan.md`](docs/refactoring/06_final_architecture_plan.md:265) - Section 5.2, Lots 11 & 13
*   **Objectif** : Activer `maintenance_manager.py refactor --type imports` et `repo --fix-docs`. Ce lot établit le `RefactoringManager` et enrichit le `RepositoryManager` avec des fonctionnalités de maintenance de la qualité du code et de la documentation.
*   **Description** : Ce lot est divisé en deux sous-tâches. La première s'attaque à la standardisation des imports Python pour les rendre absolus. La seconde s'occupe de la validation et de la correction automatique des liens internes dans la documentation Markdown.

---

**Partie A : Standardisation des Imports**

**Checklist des Tâches :**

1.  **Implémentation du Manager (`project_core`)**
    *   [ ] Créer le fichier [`project_core/core_from_scripts/refactoring_manager.py`](project_core/core_from_scripts/refactoring_manager.py).
    *   [ ] Implémenter la fonction `standardize_imports(path)` dans le `RefactoringManager`.
    *   [ ] La fonction devra scanner tous les fichiers `.py` dans le chemin fourni.
    *   [ ] Pour chaque fichier, elle utilisera l'AST (Abstract Syntax Tree) de Python pour identifier les imports relatifs et les transformer en imports absolus basés sur la racine du projet.
    *   [ ] La fonction doit modifier les fichiers sur place.

2.  **Tests Unitaires (`tests/unit`)**
    *   [ ] Créer le fichier de test `tests/unit/project_core/managers/test_refactoring_manager.py`.
    *   [ ] Préparer un fichier Python de test contenant un mélange d'imports absolus et relatifs.
    *   [ ] Écrire un test `test_standardize_imports` qui exécute la fonction sur le fichier de test et vérifie que le contenu du fichier a été correctement modifié et que seuls les imports relatifs ont changé.

3.  **Façade CLI (`scripts`)**
    *   [ ] Dans `scripts/maintenance_manager.py`, ajouter la commande `refactor --type imports --path [directory]`.
    *   [ ] La commande doit appeler `RefactoringManager.standardize_imports(path)`.

4.  **Documentation**
    *   [ ] Rédiger le docstring de `standardize_imports`.
    *   [ ] Dans `docs/guides/cli/maintenance_manager.md`, ajouter une section pour la commande `refactor`.

5.  **Commit et Synchronisation**
    *   [ ] **Commit** : `git commit -m "[FEAT] RefactoringManager - Add import standardization feature"`
    *   [ ] **Pull/Push** : Exécuter `git pull --rebase` puis `git push`.

---

**Partie B : Correction des Liens de la Documentation**

**Checklist des Tâches :**

1.  **Implémentation du Manager (`project_core`)**
    *   [ ] Dans `RepositoryManager`, implémenter la fonction `fix_documentation_links(path)`.
    *   [ ] La fonction devra scanner tous les fichiers `.md` dans le chemin fourni.
    *   [ ] Pour chaque fichier, elle extraira tous les liens internes (ex: `[lien](./vers/un/fichier.md)`) et vérifiera si la cible du lien existe.
    *   [ ] Pour les liens brisés, elle tentera de trouver le fichier correspondant dans l'arborescence et corrigera le chemin.
    *   [ ] La fonction doit générer un rapport des liens corrigés et de ceux qui n'ont pas pu être résolus.

2.  **Tests Unitaires (`tests/unit`)**
    *   [ ] Dans `test_repository_manager.py`, mettre en place une structure de faux fichiers `.md` avec des liens valides, des liens brisés mais réparables, et des liens irréparables.
    *   [ ] Écrire un test `test_fix_documentation_links` qui vérifie que les fichiers sont correctement modifiés et que le rapport généré est exact.
### Lot 4 : Validation Complète du Système

*   **Référence Architecturale** : [`docs/refactoring/06_final_architecture_plan.md`](docs/refactoring/06_final_architecture_plan.md:290) - Section 5.2, Lot 14
*   **Objectif** : Activer une suite de commandes de validation via `maintenance_manager.py validate`, culminant avec `validate --all`. Ce lot fournit un tableau de bord sur la santé du projet.
*   **Description** : Ce lot consiste à créer un `ValidationEngine` qui orchestrera plusieurs types de vérifications (imports, structure de fichiers, couverture de test). Il remplacera l'ancien script `final_system_validation.py` par une approche modulaire.

**Checklist des Tâches :**

1.  **Implémentation du Manager (`project_core`)**
    *   [ ] Créer le fichier [`project_core/core_from_scripts/validation_engine.py`](project_core/core_from_scripts/validation_engine.py).
    *   [ ] Implémenter une fonction `validate_critical_imports(config)` qui tente d'importer une liste de modules clés définis dans un fichier de configuration.
    *   [ ] Implémenter une fonction `validate_project_structure(config)` qui vérifie l'existence des répertoires et fichiers essentiels (ex: `docs/`, `tests/`, `README.md`).
    *   [ ] Implémenter une fonction `run_test_coverage()` qui utilise `shell_utils` pour lancer `pytest --cov` et retourne le taux de couverture.
    *   [ ] Implémenter la fonction principale `run_full_validation()` qui appelle les autres fonctions de validation et compile leurs résultats dans un rapport unique (un dictionnaire ou un objet de données).

2.  **Tests Unitaires (`tests/unit`)**
    *   [ ] Créer le fichier de test `tests/unit/project_core/managers/test_validation_engine.py`.
    *   [ ] Écrire des tests pour chaque fonction de validation individuelle, en mockant les dépendances (système de fichiers, `shell_utils`).
    *   [ ] Écrire un test pour `run_full_validation` pour s'assurer qu'il appelle correctement les sous-fonctions et agrège les résultats.

3.  **Façade CLI (`scripts`)**
    *   [ ] Dans `scripts/maintenance_manager.py`, créer une commande `validate` avec plusieurs options :
        *   `--imports`: Appelle `validate_critical_imports`.
        *   `--structure`: Appelle `validate_project_structure`.
        *   `--coverage`: Appelle `run_test_coverage`.
        *   `--all`: Appelle `run_full_validation` et affiche un rapport de santé formaté.

4.  **Documentation**
    *   [ ] Rédiger les docstrings pour chaque fonction du `ValidationEngine`.
    *   [ ] Dans `docs/guides/cli/maintenance_manager.md`, ajouter une section détaillée pour la commande `validate` et toutes ses options.

5.  **Commit et Synchronisation**
    *   [ ] **Commit** : `git commit -m "[FEAT] ValidationEngine - Implement system validation framework"`
### Lot 5 : Initialisation de la Gestion d'Environnement (Java & JVM)

*   **Référence Architecturale** : [`docs/refactoring/06_final_architecture_plan.md`](docs/refactoring/06_final_architecture_plan.md:123) - Section 5.1, Lot 1
*   **Objectif** : Mettre en place la façade `setup_manager.py` et les premières fonctionnalités de gestion de l'environnement liées à Java.
*   **Description** : Ce lot est le premier à s'attaquer à la complexité de la gestion de l'environnement. Il est divisé en trois parties, chacune implémentant une commande spécifique pour gérer la compatibilité du code, la validation du pont JVM, et le téléchargement des dépendances de test.

---

**Partie A : Compatibilité `pyjnius`**

1.  **Implémentation du Manager (`project_core`)**
    *   [ ] Créer le fichier [`project_core/core_from_scripts/environment_manager.py`](project_core/core_from_scripts/environment_manager.py) s'il n'existe pas.
    *   [ ] Y implémenter une fonction `apply_pyjnius_compatibility_patch(path)`.
    *   [ ] Cette fonction reprendra la logique de refactoring de l'ancien script `adapt_code_for_pyjnius.py` (utilisation de `regex` et de `mocks`).

2.  **Tests Unitaires (`tests/unit`)**
    *   [ ] Créer le fichier `tests/unit/project_core/managers/test_environment_manager.py`.
    *   [ ] Tester `apply_pyjnius_compatibility_patch` sur un fichier Python de test pour valider que le code est correctement modifié.

3.  **Façade CLI (`scripts`)**
    *   [ ] Créer le fichier [`scripts/setup_manager.py`](scripts/setup_manager.py).
    *   [ ] Ajouter la commande `compat --fix-pyjnius`.

4.  **Documentation & Commit**
    *   [ ] Rédiger le docstring et le guide pour la commande `compat`.
    *   [ ] **Commit** : `git commit -m "[FEAT] EnvironmentManager - Add pyjnius compatibility patch feature"`
    *   [ ] **Pull/Push**.

---

**Partie B : Validation du Pont JVM**

1.  **Implémentation du Manager (`project_core`)**
    *   [ ] Dans `ValidationEngine`, implémenter la fonction `validate_jvm_bridge()`.
    *   [ ] La fonction tentera d'importer `jpype` et retournera un statut de succès ou d'échec avec un message d'aide.

2.  **Tests Unitaires (`tests/unit`)**
    *   [ ] Dans `test_validation_engine.py`, tester `validate_jvm_bridge`. Un test où l'import réussit (en mockant `importlib`) et un autre où il échoue.

3.  **Façade CLI (`scripts`)**
    *   [ ] Dans `scripts/setup_manager.py`, ajouter la commande `validate --component jvm-bridge`.

4.  **Documentation & Commit**
    *   [ ] Rédiger le docstring et le guide pour la nouvelle option de validation.
    *   [ ] **Commit** : `git commit -m "[FEAT] ValidationEngine - Add JVM bridge validation"`
    *   [ ] **Pull/Push**.

---

**Partie C : Téléchargement des Jars de Test**

1.  **Implémentation du Manager (`project_core`)**
### Lot 6 : Correction des Dépendances (Installation Ciblée)

*   **Référence Architecturale** : [`docs/refactoring/06_final_architecture_plan.md`](docs/refactoring/06_final_architecture_plan.md:142) - Section 5.1, Lot 2
*   **Objectif** : Activer `setup_manager.py fix-deps --package numpy pandas ...`
*   **Description** : Ce lot introduit la fonctionnalité de base de la commande `fix-deps`. Il centralise la logique de réinstallation forcée de dépendances Python spécifiques, en remplacement des anciens scripts `fix_all_dependencies`. La fonction devra être capable de détecter la version de Python pour potentiellement adapter sa stratégie.

**Checklist des Tâches :**

1.  **Implémentation du Manager (`project_core`)**
    *   [ ] Dans `EnvironmentManager`, implémenter la fonction `fix_dependencies(packages: list[str], strategy: str = 'default')`.
    *   [ ] La fonction utilisera `shell_utils` pour construire et exécuter une commande `pip install --force-reinstall --no-cache-dir [package1] [package2]...`.
    *   [ ] Elle inclura une logique pour détecter la version de Python (`sys.version_info`) qui sera utilisée dans les lots futurs pour des stratégies plus complexes.

2.  **Tests Unitaires (`tests/unit`)**
    *   [ ] Dans `test_environment_manager.py`, ajouter un test `test_fix_dependencies`.
    *   [ ] Mocker l'appel à `shell_utils.execute_command` et vérifier que la commande `pip` construite contient les bons arguments (`--force-reinstall`) et les noms des paquets.

3.  **Façade CLI (`scripts`)**
    *   [ ] Dans `scripts/setup_manager.py`, ajouter la commande `fix-deps` avec un argument `--package` qui accepte plusieurs valeurs (`nargs='+`').

4.  **Documentation**
    *   [ ] Rédiger le docstring de `fix_dependencies`.
    *   [ ] Dans le guide `docs/guides/cli/setup_manager.md` (à créer si besoin), ajouter la documentation pour `fix-deps --package`.

5.  **Commit et Synchronisation**
    *   [ ] **Commit** : `git commit -m "[FEAT] EnvironmentManager - Add targeted dependency fixing"`
    *   [ ] **Pull/Push** : Exécuter `git pull --rebase` puis `git push`.

    *   [ ] Créer le fichier [`project_core/core_from_scripts/project_setup.py`](project_core/core_from_scripts/project_setup.py).
    *   [ ] Y implémenter une fonction `download_test_jars()`.
    *   [ ] La fonction téléchargera les `.jar` de test depuis une URL (qui sera stockée dans `argumentation_analysis/config/settings.py`).

2.  **Tests Unitaires (`tests/unit`)**
### Lot 7 : Réparation Avancée et Configuration du Chemin

*   **Référence Architecturale** : [`docs/refactoring/06_final_architecture_plan.md`](docs/refactoring/06_final_architecture_plan.md:155) - Section 5.1, Lot 3
*   **Objectif** : Activer `setup_manager.py fix-deps --from-requirements <file>` et `setup_manager.py set-path`.
*   **Description** : Ce lot étend les capacités de réparation et de configuration. La première partie permet d'installer des dépendances en masse depuis un fichier `requirements.txt`. La seconde partie fournit une méthode robuste pour configurer le `PYTHONPATH` via un fichier `.pth`, une solution de secours essentielle lorsque les installations en mode édition échouent.

---

**Partie A : Installation depuis `requirements.txt`**

1.  **Implémentation du Manager (`project_core`)**
    *   [ ] Modifier la fonction `fix_dependencies` dans `EnvironmentManager` pour accepter un paramètre optionnel `requirements_file: str = None`.
    *   [ ] Si `requirements_file` est fourni, la logique doit construire une commande `pip install -r [requirements_file]`. Si l'argument `packages` est également fourni, une erreur claire doit être levée (utilisation mutuellement exclusive).

2.  **Tests Unitaires (`tests/unit`)**
    *   [ ] Dans `test_environment_manager.py`, ajouter un test `test_fix_dependencies_from_requirements_file` qui vérifie que la bonne commande `pip` est générée.
    *   [ ] Ajouter un test `test_fix_dependencies_mutually_exclusive_args` qui vérifie qu'une exception est bien levée si `packages` et `requirements_file` sont fournis en même temps.

3.  **Façade CLI (`scripts`)**
    *   [ ] Dans `scripts/setup_manager.py`, modifier la commande `fix-deps` pour accepter une option `--from-requirements <file>`.

4.  **Documentation & Commit**
    *   [ ] Mettre à jour le docstring de `fix_dependencies` et la documentation de la commande CLI `fix-deps`.
    *   [ ] **Commit** : `git commit -m "[FEAT] EnvironmentManager - Add dependency installation from requirements file"`
    *   [ ] **Pull/Push**.

---

**Partie B : Configuration du `PYTHONPATH`**

1.  **Implémentation du Manager (`project_core`)**
    *   [ ] Dans `ProjectSetup`, implémenter une fonction `set_project_path_file()`.
    *   [ ] La fonction doit :
        1. Déterminer le chemin du répertoire `site-packages` de l'environnement Conda ou virtuel actuel.
        2. Créer (ou écraser) un fichier `argumentation_analysis_project.pth` dans ce répertoire.
        3. Écrire le chemin absolu de la racine du projet dans ce fichier.

2.  **Tests Unitaires (`tests/unit`)**
    *   [ ] Dans `test_project_setup.py`, ajouter un test `test_set_project_path_file`.
    *   [ ] Il faudra mocker les fonctions système pour obtenir le chemin de `site-packages` et pour écrire dans le fichier (`pathlib` ou `builtins.open`).
    *   [ ] Vérifier que la fonction `write` est appelée avec le bon chemin de fichier et le bon contenu.

3.  **Façade CLI (`scripts`)**
    *   [ ] Dans `scripts/setup_manager.py`, ajouter une nouvelle commande `set-path`.

4.  **Documentation & Commit**
    *   [ ] Rédiger le docstring de `set_project_path_file` et le guide pour la nouvelle commande `set-path`.
    *   [ ] **Commit** : `git commit -m "[FEAT] ProjectSetup - Add .pth file creation for PYTHONPATH"`
    *   [ ] **Pull/Push**.

    *   [ ] Créer le fichier `tests/unit/project_core/managers/test_project_setup.py`.
    *   [ ] Tester `download_test_jars` en mockant la requête de téléchargement (`requests` ou `httpx`).
### Lot 8 : Gestion des Dépendances Externes et Spécifiques

*   **Référence Architecturale** : [`docs/refactoring/06_final_architecture_plan.md`](docs/refactoring/06_final_architecture_plan.md:172) - Section 5.1, Lot 4
*   **Objectif** : Activer `setup_manager.py validate --component build-tools` et officialiser l'utilisation de `fix-deps` pour les sous-projets.
*   **Description** : Ce lot gère les dépendances qui sortent du cadre standard de `pip`. La première partie se concentre sur la validation des prérequis système externes, comme les outils de compilation C++. La seconde partie confirme et documente l'utilisation de la commande `fix-deps` (du Lot 7) pour gérer les dépendances de sous-modules comme `abs_arg_dung`.

---

**Partie A : Validation des Outils de Compilation**

1.  **Implémentation du Manager (`project_core`)**
    *   [ ] Dans `ValidationEngine`, implémenter une fonction `validate_build_tools()`.
    *   [ ] La fonction tentera de localiser un marqueur clé des Visual Studio Build Tools (par exemple, le script `vcvarsall.bat`) dans les emplacements d'installation courants sur Windows.
    *   [ ] Elle retournera un statut de succès si trouvé, et d'échec sinon.

2.  **Tests Unitaires (`tests/unit`)**
    *   [ ] Dans `test_validation_engine.py`, ajouter un test `test_validate_build_tools_found` et `test_validate_build_tools_not_found`, en mockant le système de fichiers (`os.path.exists` ou `pathlib.Path.exists`).

3.  **Façade CLI (`scripts`)**
    *   [ ] Dans `scripts/setup_manager.py`, à la commande `validate`, ajouter une option `--component build-tools`.
    *   [ ] Si la validation échoue, le script doit afficher un message clair guidant l'utilisateur sur la nécessité d'exécuter le script `scripts/setup/install_build_tools.ps1` manuellement avec des droits d'administrateur.

4.  **Documentation & Commit**
    *   [ ] Mettre à jour la documentation de la commande `validate` pour inclure la nouvelle option.
    *   [ ] **Commit** : `git commit -m "[FEAT] ValidationEngine - Add build tools validation"`
    *   [ ] **Pull/Push**.

---

**Partie B : Dépendances de Sous-Projets**

1.  **Implémentation du Manager (`project_core`)**
    *   [ ] Aucune nouvelle implémentation de code n'est requise. La fonctionnalité `fix-deps --from-requirements` implémentée au Lot 7 couvre ce besoin.

2.  **Tests Unitaires (`tests/unit`)**
    *   [ ] Dans `test_environment_manager.py`, ajouter un test spécifique `test_fix_dependencies_for_subproject` qui simule l'appel `fix-deps --from-requirements abs_arg_dung/requirements.txt` et vérifie que la bonne commande `pip` est générée.

3.  **Façade CLI (`scripts`)**
    *   [ ] Pas de modification nécessaire.

4.  **Documentation & Commit**
    *   [ ] Dans `docs/guides/cli/setup_manager.md`, ajouter un exemple spécifique dans la section `fix-deps` montrant comment installer les dépendances pour le sous-projet `abs_arg_dung`.
    *   [ ] **Commit** : `git commit -m "[DOCS] Add guide for subproject dependency installation"`
    *   [ ] **Pull/Push**.


3.  **Façade CLI (`scripts`)**
    *   [ ] Dans `scripts/setup_manager.py`, ajouter la commande `setup-deps --type test-jvm`.

4.  **Documentation & Commit**
    *   [ ] Rédiger le docstring et le guide pour la commande `setup-deps`.
### Lot 9 : Stratégies de Réparation en Cascade (La Saga JPype)

*   **Référence Architecturale** : [`docs/refactoring/06_final_architecture_plan.md`](docs/refactoring/06_final_architecture_plan.md:187) - Section 5.1, Lot 5
*   **Objectif** : Activer `setup_manager.py fix-deps --package JPype1 --strategy=aggressive`
*   **Description** : Ce lot est au cœur de la robustesse de l'outil de gestion de l'environnement. Il implémente une logique de réparation en cascade, inspirée par les multiples tentatives des anciens scripts pour installer `JPype`. Lorsqu'une stratégie "agressive" est demandée, `EnvironmentManager` essaiera une série de méthodes d'installation de plus en plus spécifiques jusqu'à ce que l'une d'elles réussisse.

**Checklist des Tâches :**

1.  **Implémentation du Manager (`project_core`)**
    *   [ ] Dans `EnvironmentManager`, modifier la fonction `fix_dependencies` pour implémenter la logique de stratégie.
    *   [ ] Si `strategy` est 'aggressive', la fonction doit exécuter une séquence de commandes `pip`. Elle ne passe à la suivante que si la précédente échoue.
    *   [ ] Séquence de stratégies pour un paquet :
        1.  Tenter une installation simple : `pip install "package_name"`.
        2.  Tenter une installation sans binaire : `pip install --no-binary :all: "package_name"`.
        3.  Sur Windows, tenter une installation via l'environnement de compilation `vcvars` (nécessite de trouver `vcvarsall.bat` et de l'exécuter dans un sous-shell avant `pip`).
    *   [ ] La fonction doit retourner un succès dès qu'une étape réussit. Si toutes échouent, elle retourne un échec.

2.  **Tests Unitaires (`tests/unit`)**
    *   [ ] Dans `test_environment_manager.py`, ajouter `test_fix_dependencies_aggressive_strategy_success_on_first_try`. Mocker `shell_utils.execute_command` pour qu'il réussisse au premier appel et vérifier que les autres stratégies ne sont pas tentées.
    *   [ ] Ajouter `test_fix_dependencies_aggressive_strategy_success_on_vcvars`. Mocker `shell_utils.execute_command` pour qu'il échoue pour les deux premières stratégies mais réussisse pour la troisième (avec `vcvars`), et vérifier que la séquence est correcte.
    *   [ ] Ajouter un test pour le cas où toutes les stratégies échouent.

3.  **Façade CLI (`scripts`)**
    *   [ ] Dans `scripts/setup_manager.py`, à la commande `fix-deps`, ajouter une option `--strategy` avec des choix possibles (`choices=['default', 'aggressive']`) et une valeur par défaut de `'default'`.

4.  **Documentation & Commit**
    *   [ ] Mettre à jour la documentation de `fix-deps` pour expliquer les différentes stratégies disponibles.
    *   [ ] **Commit** : `git commit -m "[FEAT] EnvironmentManager - Implement aggressive dependency fixing strategy"`
    *   [ ] **Pull/Push**.

    *   [ ] **Commit** : `git commit -m "[FEAT] ProjectSetup - Add test JARs downloader"`
    *   [ ] **Pull/Push**.

    *   [ ] **Pull/Push** : Exécuter `git pull --rebase` puis `git push`.


3.  **Façade CLI (`scripts`)**
    *   [ ] Dans `scripts/maintenance_manager.py`, ajouter la commande `repo --fix-docs --path [directory]`.
    *   [ ] La commande doit appeler `RepositoryManager.fix_documentation_links(path)` et afficher le rapport.

4.  **Documentation**
### Lot 10 : Wheels Précompilés et Migration de la Documentation

*   **Référence Architecturale** : [`docs/refactoring/06_final_architecture_plan.md`](docs/refactoring/06_final_architecture_plan.md:199) - Section 5.1, Lot 6
*   **Objectif** : Améliorer la stratégie de réparation avec la gestion des wheels précompilés et migrer la documentation critique des anciens `READMEs` vers le nouveau guide centralisé.
*   **Description** : Ce lot a deux volets. Le premier ajoute une étape intelligente à la stratégie de réparation "agressive" pour tenter de télécharger et d'installer un "wheel" binaire avant de tenter une compilation locale. Le second volet est une tâche de documentation cruciale pour ne pas perdre les informations de configuration vitales contenues dans les anciens fichiers.

---

**Partie A : Stratégie d'Installation par Wheel Précompilé**

1.  **Implémentation du Manager (`project_core`)**
    *   [ ] Dans `EnvironmentManager`, mettre à jour la séquence de la stratégie "aggressive" de la fonction `fix_dependencies`.
    *   [ ] Insérer une nouvelle étape (probablement en 3ème position) qui tente de deviner l'URL d'un wheel précompilé et de l'installer avec `pip`.
    *   [ ] La logique devra se baser sur la version de Python, l'architecture système (32/64 bit) et le nom du paquet pour construire l'URL du wheel.

2.  **Tests Unitaires (`tests/unit`)**
    *   [ ] Dans `test_environment_manager.py`, ajouter `test_fix_dependencies_aggressive_strategy_success_on_wheel`.
    *   [ ] Le test devra mocker les échecs des premières tentatives `pip`, puis un succès sur la tentative d'installation du wheel.

3.  **Façade CLI (`scripts`)**
    *   [ ] Aucun changement n'est nécessaire à la CLI. Cette logique est interne à la stratégie "aggressive".

4.  **Documentation & Commit**
    *   [ ] Mettre à jour le guide de la commande `fix-deps` pour expliquer que la stratégie "aggressive" inclut désormais la recherche de wheels précompilés.
    *   [ ] **Commit** : `git commit -m "[FEAT] EnvironmentManager - Add precompiled wheel strategy to dependency fixer"`
    *   [ ] **Pull/Push**.

---

**Partie B : Migration de la Documentation de Configuration**

1.  **Rédaction de la Documentation**
    *   [ ] Lire et analyser le contenu des anciens fichiers `scripts/setup/README_INSTALLATION_OUTILS_COMPILATION.md` et `scripts/setup/README_PYTHON312_COMPATIBILITY.md`.
    *   [ ] Créer le fichier `docs/guides/developpement/01_environment_setup.md` s'il n'existe pas.
    *   [ ] Fusionner, réécrire et réorganiser les informations de ces deux fichiers dans le nouveau guide. Le guide doit expliquer clairement les prérequis système (Build Tools) et les étapes de résolution de problèmes de compatibilité.

2.  **Revue et Validation**
    *   [ ] Faire relire le nouveau guide pour s'assurer qu'il est clair, complet et facile à suivre.

3.  **Commit et Synchronisation**
    *   [ ] **Commit** : `git commit -m "[DOCS] Migrate and consolidate environment setup guides"`
### Lot 11 : Simplification du Workflow de Test

*   **Référence Architecturale** : [`docs/refactoring/06_final_architecture_plan.md`](docs/refactoring/06_final_architecture_plan.md:214) - Section 5.1, Lot 7
*   **Objectif** : Activer `setup_manager.py setup-test-env --with-mocks` et supprimer les anciens lanceurs de test.
*   **Description** : Ce lot sépare la **configuration** de l'environnement de test de son **exécution**. Le `ProjectSetup` sera responsable de préparer l'environnement, y compris la mise en place de mocks. Le `TestRunner` déjà existant deviendra le seul et unique point d'entrée pour lancer `pytest`, rendant tous les scripts `run_*_tests.py` obsolètes.

**Checklist des Tâches :**

1.  **Implémentation du Manager (`project_core`)**
    *   [ ] Dans `ProjectSetup`, implémenter la fonction `setup_test_environment(with_mocks: bool)`.
    *   [ ] Si `with_mocks` est `True`, la fonction doit activer la logique de mocking pour `JPype` (similaire à la logique de compatibilité du Lot 5).
    *   [ ] Il faudra s'assurer que l'appel ultérieur à `python -m project_core.test_runner --all` fonctionne correctement après l'exécution de cette fonction.

2.  **Tests Unitaires (`tests/unit`)**
    *   [ ] Dans `test_project_setup.py`, ajouter des tests pour `setup_test_environment`.
    *   [ ] Tester le cas `with_mocks=True` et vérifier que les bonnes actions de mocking sont entreprises.
    *   [ ] Tester le cas `with_mocks=False`.

3.  **Façade CLI (`scripts`)**
    *   [ ] Dans `scripts/setup_manager.py`, ajouter la commande `setup-test-env`.
    *   [ ] Y ajouter une option `--with-mocks` (qui est un "store_true" flag).

4.  **Documentation & Commit**
    *   [ ] Migrer toute information pertinente de l'ancien `scripts/setup/README.md` vers la documentation centrale.
    *   [ ] Mettre à jour le guide de développement pour expliquer le nouveau workflow : 1. `setup-test-env`, 2. `test_runner`.
    *   [ ] **Commit 1** : `git commit -m "[FEAT] ProjectSetup - Add test environment setup command"`
    *   [ ] **Pull/Push**.
    *   [ ] **Commit 2** : `git commit -m "[DOCS] Migrate final setup README and document test workflow"`
    *   [ ] **Pull/Push**.

    *   [ ] **Pull/Push**.

    *   [ ] Mettre à jour le docstring de `fix_documentation_links`.
### Lot 12 : Orchestration Finale du Setup et de la Validation

*   **Référence Architecturale** : [`docs/refactoring/06_final_architecture_plan.md`](docs/refactoring/06_final_architecture_plan.md:229) - Section 5.1, Lot 8
*   **Objectif** : Activer les méta-commandes `setup_manager.py setup --env=test` et `validate --all`.
*   **Description** : Ce lot finalise le `setup_manager` en créant des commandes de haut niveau qui orchestrent plusieurs opérations en une seule fois. La commande `setup` devient le point d'entrée unique pour la configuration d'un environnement, et `validate --all` (déjà définie au lot 4) est confirmée comme le bilan de santé complet.

**Checklist des Tâches :**

1.  **Implémentation du Manager (`project_core`)**
    *   [ ] Dans `ProjectSetup`, implémenter la fonction `setup_environment(env_name: str)`.
    *   [ ] Cette fonction agira comme un routeur. Si `env_name` est `'test'`, elle appellera en séquence d'autres fonctions du manager, comme `download_test_jars()` (Lot 5) et `setup_test_environment()` (Lot 11).
    *   [ ] La fonction `ValidationEngine.run_full_validation()` a déjà été définie au Lot 4 et remplit ce rôle d'orchestrateur pour la validation. Aucune modification n'est nécessaire.

2.  **Tests Unitaires (`tests/unit`)**
    *   [ ] Dans `test_project_setup.py`, ajouter un test `test_setup_environment` qui vérifie que les bonnes sous-fonctions sont appelées lorsque `env_name` est `'test'`.

3.  **Façade CLI (`scripts`)**
    *   [ ] Dans `scripts/setup_manager.py`, implémenter la commande `setup --env <name>`, où `<name>` peut être 'test' ou 'dev'.
    *   [ ] La commande `validate --all` est déjà planifiée dans le cadre du Lot 4.

4.  **Documentation & Commit**
    *   [ ] Rédiger la documentation pour la nouvelle méta-commande `setup`.
    *   [ ] Mettre à jour la documentation générale pour présenter `setup --env=test` et `validate --all` comme les deux commandes principales à lancer pour un nouvel utilisateur.
    *   [ ] **Commit** : `git commit -m "[FEAT] ProjectSetup - Add high-level environment setup orchestrator"`
    *   [ ] **Pull/Push**.

---
**(La partie `setup` est maintenant entièrement planifiée. La suite des lots concernera la partie `maintenance`.)**

    *   [ ] Dans `docs/guides/cli/maintenance_manager.md`, mettre à jour la section sur la commande `repo` pour inclure `--fix-docs`.

---
## 4. Plan d'Orchestration Détaillé (Partie II : Maintenance)
---

### Lot 13 : Organisation du Répertoire `results`

*   **Référence Architecturale** : [`docs/refactoring/06_final_architecture_plan.md`](docs/refactoring/06_final_architecture_plan.md:247) - Section 5.2, Lot 9
*   **Objectif** : Activer `maintenance_manager.py organize --target results`.
*   **Description** : Ce lot met en place un nouveau `OrganizationManager` et sa première fonctionnalité, qui est la réorganisation structurée du répertoire `results/`. Cette fonction s'inspire de l'ancien workflow de `clean_project.ps1` et inclut la sauvegarde, le déplacement de fichiers et la génération d'un rapport.

**Checklist des Tâches :**

1.  **Implémentation du Manager (`project_core`)**
    *   [ ] Créer le fichier [`project_core/core_from_scripts/organization_manager.py`](project_core/core_from_scripts/organization_manager.py).
    *   [ ] Y implémenter une fonction `organize_results_directory()`.
    *   [ ] La logique de la fonction doit :
        1.   Sauvegarder le répertoire `results/` actuel dans un emplacement d'archive.
        2.   Parcourir les fichiers de la sauvegarde.
        3.   Créer une nouvelle structure de répertoires dans `results/` basée sur des patterns dans les noms de fichiers.
        4.   Déplacer les fichiers dans les bons répertoires.
        5.   Générer un `README.md` dans le nouveau `results/` qui résume les opérations effectuées.

2.  **Tests Unitaires (`tests/unit`)**
    *   [ ] Créer le fichier `tests/unit/project_core/managers/test_organization_manager.py`.
    *   [ ] Mettre en place un `setUp` qui crée un faux répertoire `results/` avec une variété de fichiers.
    *   [ ] Écrire un test `test_organize_results_directory` qui appelle la fonction et vérifie que la nouvelle structure de `results/` est correcte, que les fichiers ont été déplacés, et que le `README` a été créé.

3.  **Façade CLI (`scripts`)**
    *   [ ] Dans `scripts/maintenance_manager.py`, ajouter la commande `organize` avec une option `--target <name>`, où `<name>` peut être `results`.

4.  **Documentation & Commit**
    *   [ ] Rédiger un docstring détaillé pour `organize_results_directory`.
    *   [ ] Créer un nouveau guide `docs/guides/cli/maintenance_manager.md` et y ajouter la documentation pour la commande `organize`.
    *   [ ] **Commit** : `git commit -m "[FEAT] OrganizationManager - Add results directory organization feature"`
    *   [ ] **Pull/Push**.

### Lot 14 : Application des Plans de Réorganisation

*   **Référence Architecturale** : [`docs/refactoring/06_final_architecture_plan.md`](docs/refactoring/06_final_architecture_plan.md:280) - Section 5.2, Lot 12
*   **Objectif** : Activer `maintenance_manager.py organize --apply-plan <plan.json>`.
*   **Description** : Ce lot complète le workflow de gestion des fichiers orphelins. Le Lot 1 permet de générer un rapport de fichiers non suivis. Ce lot permet de consommer ce rapport (après une éventuelle édition manuelle de l'utilisateur) pour exécuter les actions de nettoyage (suppression, déplacement, etc.).

**Checklist des Tâches :**

1.  **Implémentation du Manager (`project_core`)**
    *   [ ] Dans `OrganizationManager`, implémenter la fonction `apply_organization_plan(plan_path: str)`.
    *   [ ] La fonction doit lire et parser le fichier JSON spécifié.
    *   [ ] Elle doit ensuite itérer sur les actions définies dans le plan (ex: `{"action": "delete", "path": "path/to/file.log"}` ou `{"action": "move", "source": "src", "destination": "dest"}`).
    *   [ ] Elle utilisera les `filesystem_utils` de `argumentation_analysis` pour exécuter les opérations de suppression et de déplacement de manière sécurisée.

2.  **Tests Unitaires (`tests/unit`)**
    *   [ ] Dans `test_organization_manager.py`, créer un test `test_apply_organization_plan`.
    *   [ ] Le test devra créer une structure de fichiers temporaires et un fichier de plan JSON d'exemple.
    *   [ ] Après avoir appelé la fonction, le test vérifiera que les fichiers ont bien été supprimés ou déplacés conformément au plan.

3.  **Façade CLI (`scripts`)**
    *   [ ] Dans `scripts/maintenance_manager.py`, à la commande `organize`, ajouter une option `--apply-plan <file_path>`.

4.  **Documentation & Commit**
    *   [ ] Mettre à jour la documentation de la commande `organize` pour expliquer le workflow complet : 1. `repo --find-orphans > plan.json`, 2. (optionnel) Éditer `plan.json`, 3. `organize --apply-plan plan.json`.
    *   [ ] **Commit** : `git commit -m "[FEAT] OrganizationManager - Add plan-based file organization"`
    *   [ ] **Pull/Push**.

*   **Objectif** : Activer `maintenance_manager.py cleanup --type temp-files`.

(... La liste des lots continuera ici, en suivant le même niveau de détail pour chaque fonctionnalité identifiée dans le document 06 ...)

---

### Lot 15 : Nettoyage des Fichiers Temporaires

*   **Référence Architecturale** : [`docs/refactoring/06_final_architecture_plan.md`](docs/refactoring/06_final_architecture_plan.md:247) - Section 5.2, Lot 9 (`cleanup_temp_files`)
*   **Objectif** : Activer `maintenance_manager.py cleanup --default`.
*   **Description** : Ce lot met en place le `CleanupManager` et sa fonctionnalité de base : la suppression récursive des fichiers et répertoires temporaires standards (fichiers `.pyc`, répertoires `__pycache__`, etc.). Cette fonctionnalité est essentielle pour maintenir la propreté du projet.

**Checklist des Tâches :**

1.  **Implémentation du Manager (`project_core`)**
    *   [ ] Créer le fichier [`project_core/core_from_scripts/cleanup_manager.py`](project_core/core_from_scripts/cleanup_manager.py).
    *   [ ] Y implémenter une fonction `cleanup_temporary_files()`.
    *   [ ] La fonction devra définir une liste de patterns à supprimer (ex: `*.pyc`, `__pycache__`, `.pytest_cache`).
    *   [ ] Elle utilisera une fonction utilitaire (probablement dans `argumentation_analysis.core.utils.filesystem_utils`) pour trouver tous les fichiers et répertoires correspondant à ces patterns dans l'ensemble du projet.
    *   [ ] Elle procédera ensuite à leur suppression et retournera un rapport simple listant les éléments supprimés.

2.  **Tests Unitaires (`tests/unit`)**
    *   [ ] Créer le fichier `tests/unit/project_core/managers/test_cleanup_manager.py`.
    *   [ ] Dans un `setUp`, créer une arborescence de test contenant des fichiers `.pyc`, des répertoires `__pycache__`, ainsi que des fichiers à conserver.
    *   [ ] Écrire un test `test_cleanup_temporary_files` qui vérifie que seuls les éléments ciblés sont supprimés.

3.  **Façade CLI (`scripts`)**
    *   [ ] Dans `scripts/maintenance_manager.py`, ajouter la commande `cleanup` avec une option `--default`. L'option est là pour anticiper de futurs modes de nettoyage plus spécifiques.

4.  **Documentation & Commit**
    *   [ ] Documenter la nouvelle commande `cleanup` dans `docs/guides/cli/maintenance_manager.md`.
    *   [ ] **Commit** : `git commit -m "[FEAT] CleanupManager - Add temporary file cleanup feature"`
    *   [ ] **Pull/Push**.


---

### Lot 16 : Mise à Jour du Fichier `.gitignore`

*   **Référence Architecturale** : [`docs/refactoring/06_final_architecture_plan.md`](docs/refactoring/06_final_architecture_plan.md:247) - Section 5.2, Lot 9 (`update_gitignore`)
*   **Objectif** : Activer `maintenance_manager.py repo --update-gitignore`.
*   **Description** : Ce lot ajoute une fonctionnalité au `RepositoryManager` pour standardiser et mettre à jour le fichier `.gitignore` du projet. Il s'assure que le projet ignore de manière cohérente tous les fichiers et répertoires qui ne doivent pas être versionnés, en se basant sur un template central.

**Checklist des Tâches :**

1.  **Création du Template**
    *   [ ] Créer un fichier de template central : [`project_core/templates/project.gitignore.template`](project_core/templates/project.gitignore.template).
    *   [ ] Remplir ce template avec toutes les règles standards pour un projet Python (`__pycache__/`, `*.pyc`, `*.egg-info/`) ainsi que les règles spécifiques à ce projet (ex: `results/`, `local_llm_data/`, etc.).

2.  **Implémentation du Manager (`project_core`)**
    *   [ ] Dans `RepositoryManager`, implémenter la fonction `update_gitignore_from_template()`.
    *   [ ] La fonction lira le contenu du fichier template.
    *   [ ] Elle lira le contenu du fichier `.gitignore` à la racine du projet.
    *   [ ] Elle identifiera les règles du template qui sont absentes du `.gitignore` actuel et les y ajoutera (en évitant les doublons). L'ajout se fera à la fin du fichier dans une section dédiée, par exemple sous un commentaire `# Managed by Project Core`.

3.  **Tests Unitaires (`tests/unit`)**
    *   [ ] Dans `test_repository_manager.py`, écrire un test `test_update_gitignore`.
    *   [ ] Le test devra utiliser un faux fichier `.gitignore`, un faux template, et vérifier que le fichier cible est correctement mis à jour (règles ajoutées, pas de doublons).

4.  **Façade CLI (`scripts`)**
    *   [ ] Dans `scripts/maintenance_manager.py`, à la commande `repo`, ajouter une option `--update-gitignore`.

5.  **Documentation & Commit**
    *   [ ] Documenter cette nouvelle capacité dans `docs/guides/cli/maintenance_manager.md`.
    *   [ ] **Commit** : `git commit -m "[FEAT] RepositoryManager - Add .gitignore update functionality"`
    *   [ ] **Pull/Push**.


---

### Lot 17 : Refactorisation Automatisée par Plan

*   **Référence Architecturale** : [`docs/refactoring/06_final_architecture_plan.md`](docs/refactoring/06_final_architecture_plan.md:259) - Section 5.2, Lot 10 (`refactor-entire-project`)
*   **Objectif** : Activer `maintenance_manager.py refactor --plan <plan.json> [--dry-run]`.
*   **Description** : Ce lot final et le plus avancé met en place un moteur de refactorisation capable d'appliquer des transformations de code à grande échelle basées sur un plan déclaratif. C'est l'outil qui permettra d'automatiser une grande partie de la migration finale du code legacy en modifiant les imports, les appels de fonction, etc.

**Checklist des Tâches :**

1.  **Implémentation du Manager (`project_core`)**
    *   [ ] Créer le fichier [`project_core/core_from_scripts/refactoring_manager.py`](project_core/core_from_scripts/refactoring_manager.py).
    *   [ ] Implémenter la fonction principale `apply_refactoring_plan(plan_path: str, dry_run: bool = False)`.
    *   [ ] La fonction lira un plan JSON, qui pourra contenir une liste de transformations. Ex: `{"action": "update_import", "old_path": "a.b.c", "new_path": "x.y.z"}`.
    *   [ ] Le manager s'appuiera sur des utilitaires d'analyse de code (probablement basés sur `ast` ou `libcst`) à développer dans `argumentation_analysis.core.utils.code_manipulation`.
    *   [ ] Types de transformations à supporter initialement :
        *   `update_import`: Change un chemin d'import.
        *   `rename_function`: Renomme un appel de fonction.
    *   [ ] La fonction devra générer un `diff` des changements pour le mode `dry-run` ou les appliquer directement.

2.  **Tests Unitaires (`tests/unit`)**
    *   [ ] Créer le fichier `tests/unit/project_core/managers/test_refactoring_manager.py`.
    *   [ ] Pour chaque type de transformation, écrire un test dédié qui :
        1.  Crée un fichier Python source temporaire.
        2.  Crée un plan de refactorisation JSON.
        3.  Appelle le manager.
        4.  Vérifie que le fichier source a été modifié exactement comme attendu.

3.  **Façade CLI (`scripts`)**
    *   [ ] Dans `scripts/maintenance_manager.py`, ajouter la commande `refactor` avec :
        *   `--plan <file_path>` (obligatoire).
        *   `--dry-run` (optionnel).

4.  **Documentation & Commit**
    *   [ ] Rédiger un guide de développement complet dans `docs/guides/development/02_automated_refactoring.md`, expliquant comment écrire des plans de refactorisation.
    *   [ ] Documenter la nouvelle commande `refactor` dans `docs/guides/cli/maintenance_manager.md`.
    *   [ ] **Commit** : `git commit -m "[FEAT] RefactoringManager - Add plan-based code refactoring engine"`
    *   [ ] **Pull/Push**.
