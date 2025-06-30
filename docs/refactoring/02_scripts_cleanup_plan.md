# Plan de Refactoring du Répertoire `scripts/` (Version Révisée - Stabilité Prioritaire)

## 1. Contexte et Objectifs

Ce document présente un plan de refactoring **révisé** pour le répertoire `scripts/`. Suite à de nouvelles contraintes, l'objectif est de rationaliser la structure **existante** pour la rendre plus claire et maintenable, **sans introduire de changements majeurs à la racine du projet (comme la création d'un répertoire `src/`)**.

Les objectifs sont de :
*   **Clarifier les responsabilités** : Isoler le code applicatif (`scripts/apps/`) des scripts d'outillage.
*   **Centraliser** : Regrouper tous les tests, outils, et scripts de maintenance dans des répertoires dédiés.
*   **Nettoyer** : Supprimer les fichiers temporaires, les logs et archiver le code redondant ou obsolète.

## 2. Analyse de la Structure Actuelle

L'analyse de la cartographie fournie révèle plusieurs problèmes majeurs :

*   **Mélange des genres** : Le répertoire contient à la fois des scripts d'outillage, du code source d'applications (`webapp`, `sherlock_watson`), des fichiers de documentation (`.md`), et des logs (`.log`).
*   **Redondance structurelle** : Des applications comme `webapp` et `sherlock_watson` existent à la fois à la racine de `scripts/` et dans le sous-répertoire `scripts/apps/`. C'est une source majeure de confusion.
*   **Dispersion des scripts** : Les scripts de test, de validation et d'environnement sont disséminés à plusieurs endroits (`scripts/dev/tools`, `scripts/testing`, `scripts/run_integration_tests.ps1`, etc.).
*   **Présence d'artefacts** : De nombreux répertoires `__pycache__` et fichiers `.log` polluent l'arborescence et ne devraient pas être versionnés.
*   **Documentation mal placée** : La présence d'un répertoire `docs/` à l'intérieur de `scripts/` est une mauvaise pratique.

## 3. Stratégie de Consolidation Interne

L'approche est de **consolider** les scripts existants dans les répertoires thématiques **déjà présents** (`testing`, `tools`, `maintenance`, `setup`) pour clarifier les responsabilités sans créer de nouvelles structures.

1.  **`scripts/apps/`** : Conserve sa vocation d'héberger le code source applicatif. Reste inchangé.
2.  **`scripts/testing/`** : Deviendra le point central pour tous les scripts de test, y compris ceux de `scripts/validation`.
3.  **`scripts/maintenance/`** : Restera le répertoire pour le nettoyage, la migration et la refonte. Son contenu sera harmonisé.
4.  **`scripts/tools/`** : Collectera les outils de développement génériques qui sont actuellement dispersés.
5.  **`scripts/setup/`** : Collectera les scripts liés à l'installation et à la configuration de l'environnement, absorbant le contenu de `scripts/env`.

L'objectif secondaire, une fois la consolidation terminée, sera d'analyser le contenu de chaque répertoire pour identifier et fusionner les scripts redondants en des versions plus génériques et paramétrables.

## 4. Plan de Migration par Consolidation

### Phase 1 : Consolidation des Tests et de la Validation

1.  **Action** : Déplacer le contenu de `scripts/validation/` vers `scripts/testing/`.
2.  **Action** : Parcourir `scripts/` à la racine et les sous-dossiers pour déplacer tous les scripts manifestement liés aux tests (ex: `run_integration_tests.ps1`, `run_functional_tests.ps1`, `run_e2e_tests.bat`) vers `scripts/testing/`.
3.  **Objectif** : Avoir un seul et unique endroit pour lancer et trouver tous les types de tests.

### Phase 2 : Consolidation de l'Environnement et des Outils

1.  **Action** : Déplacer le contenu de `scripts/env/` vers `scripts/setup/`.
2.  **Action** : Déplacer les outils épars (ex: `scripts/utils/`, `scripts/tools/debugging/`) dans le répertoire `scripts/tools/`.
3.  **Objectif** : Clarifier où se trouvent les scripts pour configurer l'environnement (`setup`) et les utilitaires de développement (`tools`).

### Phase 3 : Nettoyage et Archivage

1.  **Action** : Identifier et archiver les répertoires redondants ou obsolètes (ex: `scripts/webapp` si différent de `scripts/apps/webapp`) dans `archived_scripts/`.
2.  **Action** : S'assurer que les fichiers temporaires (`*.log`, `__pycache__`) sont bien ignorés et les supprimer du suivi Git s'ils existent. Le `.gitignore` est déjà correct.
3.  **Objectif** : Alléger le répertoire `scripts` de tout ce qui n'est pas essentiel à son fonctionnement.

### Phase 4 : Refactoring Interne (Post-consolidation)

1.  **Analyse** : Examiner le contenu des répertoires maintenant consolidés (`testing`, `tools`, `maintenance`).
2.  **Refactoring** : Identifier les scripts aux fonctionnalités similaires et planifier leur fusion en scripts uniques et paramétrables. (Exemple: fusionner plusieurs `cleanup_*.py` en un seul `cleanup.py` avec des arguments).
3.  **Documentation** : Mettre à jour le `README.md` de chaque sous-répertoire pour décrire le rôle de chaque script consolidé.