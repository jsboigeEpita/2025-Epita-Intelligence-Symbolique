# Plan de Refactorisation v4 : Consolidation dans `project_core`

## 1. Contexte et Mandat Final

À la suite des analyses architecturales et de la découverte du répertoire `project_core`, cette nouvelle version du plan de refactorisation annule et remplace les précédentes.

Le mandat est désormais clair et définitif : **centraliser et renforcer la logique de gestion du projet au sein de `project_core`**. Ce répertoire est la nouvelle source de vérité pour toute la logique métier des scripts. Les scripts situés dans le répertoire `scripts/` deviendront de simples **façades CLI** légères, dont le seul rôle sera d'appeler les fonctions exposées par `project_core`.

Cette architecture finale favorise :
-   **La Centralisation Stratégique** : Toute la logique de maintenance et de configuration vit en un seul endroit.
-   **Le Découplage Robuste** : L'interface (CLI) est totalement découplée de l'implémentation (logique dans `project_core`).
-   **La Cohérence Architecturale** : Le projet suit une philosophie claire, séparant le noyau applicatif (`argumentation_analysis`) du noyau de gestion de projet (`project_core`).
-   **La Maintenabilité** : La mise à jour des outils se fait en modifiant les modules de `project_core`, sans toucher aux façades CLI.

## 2. Analyse de l'Architecture Existant dans `project_core`

L'exploration de `project_core` a révélé une base solide et parfaitement alignée avec nos objectifs. Il faut construire *sur* cet existant.

-   **Noyau Mutualisé (`core_from_scripts/`)** : Ce répertoire contient déjà les piliers de notre future architecture :
    -   `environment_manager.py` : embryon du gestionnaire d'environnement.
    -   `project_setup.py` : embryon du gestionnaire de configuration.
    -   `validation_engine.py` : embryon du moteur de validation.
    -   `common_utils.py` : utilitaires de base (logging, etc.).

-   **Logique Applicative Externalisée (`rhetorical_analysis_from_scripts/`)** : Ce sous-répertoire démontre la viabilité de l'architecture "façade", servant de preuve de concept réussie.

-   **Point Manquant** : La logique complexe de gestion de la JVM et du JDK, actuellement dans `argumentation_analysis/core/jvm_setup.py`, n'a pas d'équivalent dans `project_core`. Elle est donc une candidate parfaite à la migration pour achever la centralisation.

## 3. Architecture Cible Détaillée et Granulaire

L'architecture s'articulera autour de l'enrichissement de `project_core` avec la logique identifiée dans l'analyse de `scripts/setup` et `scripts/maintenance`, et de la création de deux façades CLI.

---

### Domaine 1 : Gestion de l'Environnement (ex `scripts/setup`)

L'objectif est de fusionner les 36 scripts de `setup` dans les modules existants et nouveaux de `project_core`.

#### 3.1. Évolution du Noyau (`project_core/`)

-   **`core_from_scripts/environment_manager.py`** (Enrichi) :
    -   Intégrera les stratégies de réparation en cascade pour les dépendances (notamment `JPype`) depuis `install_jpype_for_python312.ps1`.
    -   Gérera la détection de version Python pour appliquer des correctifs ciblés.
    -   Intégrera la gestion des wheels précompilés de `install_prebuilt_wheels.ps1`.
    -   Absorbera la gestion de l'environnement de compilation `vcvars` de `install_jpype_with_vcvars.ps1`.

-   **`core_from_scripts/project_setup.py`** (Enrichi) :
    -   Intégrera la logique de configuration manuelle du `PYTHONPATH` (`.pth`) de `fix_pythonpath_manual.py`.
    -   Gérera les dépendances par contexte (ex: `install_dung_deps.py`).
    -   Absorbera la logique de compatibilité (mock JPype) de `init_jpype_compatibility.py`.

-   **`core_from_scripts/validation_engine.py`** (Enrichi) :
    -   Deviendra un outil de diagnostic complet, vérifiant les dépendances (`test_all_dependencies.py`), les outils système externes comme les Build Tools (`install_build_tools.ps1`), et l'intégrité des imports (`check_imports.py`).
    -   Intégrera une routine de validation de la structure du projet et de l'intégrité des fichiers (`verify_files.py`).

-   **Nouveau module `core_from_scripts/jvm_manager.py`** :
    -   Hébergera **toute la logique** de `argumentation_analysis/core/jvm_setup.py`.
    -   Responsabilités : téléchargement et validation du JDK portable, téléchargement des JARs Tweety, et gestion complète du cycle de vie de la JVM (initialisation/shutdown).

#### 3.2. Façade CLI (`scripts/setup_manager.py`)

Un nouveau script, `scripts/setup_manager.py`, utilisera `argparse` pour fournir une CLI claire. **Il ne contiendra aucune logique métier**.

```python
# Exemple de contenu pour scripts/setup_manager.py
import argparse
# Les imports pointeront vers les nouveaux modules de project_core
from project_core.core_from_scripts import environment_manager, validation_engine, jvm_manager

def main():
    parser = argparse.ArgumentParser(description="Unified Environment Manager.")
    # ... Définition des commandes : setup, validate, fix-deps, compat, setup-jvm ...
    args = parser.parse_args()

    if args.command == "validate":
        validation_engine.run_full_validation()
    elif args.command == "fix-deps":
        environment_manager.fix_dependencies(package=args.package, strategy=args.strategy)
    elif args.command == "setup-jvm":
        jvm_manager.ensure_jvm_is_ready()
    # ... etc.

if __name__ == "__main__":
    main()
```

---

### Domaine 2 : Maintenance du Projet (ex `scripts/maintenance`)

L'objectif est de fusionner les ~30 scripts de `maintenance` dans de nouveaux modules au sein de `project_core`.

#### 3.3. Évolution du Noyau (`project_core/`)

-   **Nouveau module `core_from_scripts/cleanup_manager.py`** :
    -   Intégrera la logique de nettoyage de bas niveau : suppression des fichiers temporaires (`__pycache__`, `.pyc`) et nettoyage des logs anciens, en s'inspirant de `cleanup_project.py` et `clean_project.ps1`.

-   **Nouveau module `core_from_scripts/repository_manager.py`** :
    -   Gérera toutes les interactions avec Git.
    -   **`update_gitignore()`** : Logique de `cleanup_project.py`.
    -   **`find_untracked_files()`** : Stratégie `git status --porcelain` de `real_orphan_files_processor.py`.
    -   **`untrack_file(path)`** : Logique `git rm --cached` de `cleanup_repository.py`.
    -   **`update_documentation(plan)`** : Logique de correction de liens (`comprehensive_documentation_fixer_safe.py`) et de mise à jour de références (`update_references.ps1`).

-   **Nouveau module `core_from_scripts/refactoring_manager.py`** :
    -   Centralisera les outils de transformation de code.
    -   **`standardize_imports(path)`** : Logique de `update_imports.py`.
    -   **`centralize_paths(path)`** : Logique de `update_paths.py`.

-   **Nouveau module `core_from_scripts/organization_manager.py`** :
    -   Contiendra les workflows de restructuration de fichiers.
    -   **`organize_results_directory()`** : Logique de `clean_project.ps1`.
    -   **`clean_project_root()`** : Logique de `organize_root_files.py`.
    -   **`archive_and_delete(file_list)`** : Logique de `cleanup_obsolete_files.py`.
    -   **`apply_organization_plan(plan_file)`** : Logique pour exécuter un plan de migration JSON (généré par le `repository_manager`), incluant la suppression sécurisée post-déplacement de `cleanup_redundant_files.ps1`.

#### 3.4. Façade CLI (`scripts/maintenance_manager.py`)

Un second script, `scripts/maintenance_manager.py`, servira de façade pour les tâches de maintenance.

```python
# Exemple de contenu pour scripts/maintenance_manager.py
import argparse
# Les imports pointeront vers les nouveaux modules de project_core
from project_core.core_from_scripts import repository_manager, cleanup_manager, organization_manager

def main():
    parser = argparse.ArgumentParser(description="Project Maintenance Manager.")
    # ... Définition des commandes: cleanup, repo, refactor, organize, validate ...
    args = parser.parse_args()

    if args.command == "repo" and args.subcommand == "find-orphans":
        report_path = repository_manager.find_untracked_files()
        print(f"Rapport sur les orphelins généré : {report_path}")
    elif args.command == "organize" and args.subcommand == "apply-plan":
        organization_manager.apply_organization_plan(args.plan_file)
    # ... etc.

if __name__ == "__main__":
    main()
```

## 4. Prochaines Étapes

Avec ce plan finalisé et validé, la prochaine étape sera de passer à l'implémentation, en migrant la logique fonctionnelle identifiée dans `04_scripts_maintenance_consolidation_plan.md` vers les modules cibles de `project_core`.
