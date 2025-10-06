# Plan de Nettoyage de la Racine du Projet

Ce document présente une proposition pour réorganiser la racine du projet afin d'améliorer sa clarté et sa maintenabilité.

## 1. État Actuel

Le tableau suivant liste les fichiers et répertoires actuellement à la racine du projet et leur fonction supposée.

| Élément                                | Type        | Rôle / Fonction                                         |
| -------------------------------------- | ----------- | ------------------------------------------------------- |
| **Scripts & Lanceurs**                 |             |                                                         |
| `activate_project_env.ps1`             | Fichier     | Script d'activation de l'environnement (PowerShell)     |
| `activate_project_env.sh`              | Fichier     | Script d'activation de l'environnement (Bash)           |
| `setup_project_env.ps1`                | Fichier     | Script d'installation de l'environnement (PowerShell)   |
| `setup_project_env.sh`                 | Fichier     | Script d'installation de l'environnement (Bash)         |
| `run_tests.ps1`                        | Fichier     | Lanceur principal des tests                             |
| `run_simple_test.ps1`                  | Fichier     | Lanceur de tests simplifié                              |
| `run_tests_standalone.ps1`             | Fichier     | Lanceur de tests autonome                               |
| `install_environment.py`               | Fichier     | Script d'installation Python                            |
| `run_pytest.py`                        | Fichier     | Lanceur pour Pytest                                     |
| `run_unit_tests.py`                    | Fichier     | Lanceur pour les tests unitaires                        |
| `start_webapp.py`                      | Fichier     | Script de démarrage de l'application web                |
| `debug_imports.py`                     | Fichier     | Utilitaire de débogage pour les imports                 |
| `temp_remove_pycache.py`               | Fichier     | Script temporaire pour nettoyer le cache Python         |
| **Configuration**                      |             |                                                         |
| `pyproject.toml`                       | Fichier     | Fichier de configuration standard pour les projets Python|
| `setup.py`                             | Fichier     | Ancien script de configuration de projet Python (setuptools)|
| `environment.yml`                      | Fichier     | Fichier de dépendances pour Conda                       |
| `conda-lock.yml`                       | Fichier     | Fichier de verrouillage des dépendances Conda           |
| `package.json`                         | Fichier     | Dépendances et scripts pour projets Node.js/NPM         |
| `package-lock.json`                    | Fichier     | Fichier de verrouillage des dépendances NPM             |
| `conftest.py`                          | Fichier     | Configuration et fixtures pour Pytest                   |
| `pytest.ini` / `empty_pytest.ini`      | Fichier     | Fichiers de configuration pour Pytest                   |
| `playwright.config.js`                 | Fichier     | Fichier de configuration pour Playwright                |
| **Documentation**                      |             |                                                         |
| `README.md`                            | Fichier     | Documentation principale du projet                      |
| `LICENSE`                              | Fichier     | Licence du projet                                       |
| `CHANGELOG.md`                         | Fichier     | Journal des modifications                               |
| `GUIDE_DEMARRAGE_RAPIDE_PROJET_EPITA.md`| Fichier     | Guide de démarrage spécifique                           |
| `JPYPE_WINDOWS_CRASH_FIX.md`           | Fichier     | Notes de dépannage pour JPype sur Windows               |
| [`PLAN.md`](../maintenance/PLAN.md:1)  | Fichier     | ✅ Déplacé vers docs/maintenance/                      |
| **Logs & Rapports**                     |             |                                                         |
| `*.log`                                | Fichiers    | Fichiers de log divers                                  |
| `console_logs.txt`                     | Fichier     | Logs de la console                                      |
| `*.json`                               | Fichiers    | Rapports de tests ou de traces au format JSON           |
| `rapport_*.md`                         | Fichiers    | Rapports d'analyse au format Markdown                   |
| `validation_report.md`                 | Fichier     | Rapport de validation                                   |
| **Fichiers Temporaires & Divers**    |             |                                                         |
| `pr1_diff.txt`                         | Fichier     | Diff de code, probablement temporaire                   |
| `backend_info.json`                    | Fichier     | Informations sur le backend, probablement temporaire    |
| `temp_*.py` / `temp_*.txt`            | Fichiers    | Fichiers de test ou temporaires                         |
| **Répertoires**                        |             |                                                         |
| `*` (tous les répertoires)             | Répertoires | Modules de code source, sous-projets, données, etc.     |


## 2. Plan de Nettoyage Proposé

Le tableau suivant détaille les actions proposées pour chaque type d'élément.

| Élément / Catégorie                    | Action                  | Destination Proposée (`/`)                                |
| -------------------------------------- | ----------------------- | --------------------------------------------------------- |
| **À Conserver à la Racine**            | **Conserver**           | **N/A**                                                   |
| `activate_project_env.ps1` / `.sh`     | Conserver               | -                                                         |
| `setup_project_env.ps1` / `.sh`        | Conserver               | -                                                         |
| `run_tests.ps1`                        | Conserver               | -                                                         |
| `pyproject.toml`                       | Conserver               | -                                                         |
| `setup.py`                             | Conserver               | -                                                         |
| `environment.yml`                      | Conserver               | -                                                         |
| `conda-lock.yml`                       | Conserver               | -                                                         |
| `package.json` / `package-lock.json`   | Conserver               | -                                                         |
| `.gitignore` (si existant)             | Conserver               | -                                                         |
| `README.md`                            | Conserver               | -                                                         |
| `LICENSE`                              | Conserver               | -                                                         |
| **À Déplacer**                         | **Déplacer**            |                                                           |
| **Scripts**                            | Déplacer                | `scripts/`                                                |
| `run_simple_test.ps1`                  | Déplacer                | `scripts/testing/`                                        |
| `run_tests_standalone.ps1`             | Déplacer                | `scripts/testing/`                                        |
| Autres lanceurs (`*.py`, `*.ps1`)      | Déplacer                | `scripts/` (ou sous-dossiers `webapp/`, `analysis/`)  |
| **Configuration de Tests**             | Déplacer                | `tests/`                                                  |
| `conftest.py`, `pytest.ini`, etc.      | Déplacer                | `tests/`                                                  |
| `playwright.config.js`                 | Déplacer                | `tests/e2e/`                                              |
| **Documentation**                      | Déplacer                | `docs/`                                                   |
| `CHANGELOG.md`                         | Déplacer                | `docs/`                                                   |
| Autres `*.md`                          | Déplacer                | `docs/guides/` ou `docs/internal/`                        |
| **Fichiers de Code Source (Répertoires)** | Déplacer            | `src/` (à discuter, structure de plus haut niveau)       |
| **Logs**                               | Déplacer                | `logs/` (et ajouter `logs/` au `.gitignore`)               |
| `*.log`, `console_logs.txt`, etc.      | Déplacer                | `logs/`                                                   |
| **Rapports**                           | Déplacer                | `reports/` (et ajouter `reports/` au `.gitignore`)         |
| `rapport_*.md`, `*.json` (traces)      | Déplacer                | `reports/`                                                |
| **À Archiver ou Supprimer**            | **Déplacer / Archiver** | `archived_root/`                                          |
| Fichiers temporaires ou uniques        | Déplacer                | `archived_root/`                                          |
| `pr1_diff.txt`, `backend_info.json`    | Déplacer                | `archived_root/`                                          |


## 3. Justification

La nouvelle structure proposée vise à :

1.  **Simplifier la Racine :** Ne laisser que les points d'entrée et les fichiers de configuration essentiels. Un nouvel arrivant peut rapidement comprendre comment installer, activer l'environnement et lancer les tests.
2.  **Centraliser les Scripts :** Regrouper tous les scripts utilitaires dans le répertoire `scripts/` améliore la découvrabilité et la cohérence.
3.  **Isoler les Artefacts :** Les logs, rapports et autres fichiers générés par les builds ou les analyses sont séparés du code source dans les répertoires `logs/` et `reports/`. Ces répertoires devraient être ignorés par Git.
4.  **Organiser la Configuration :** Les fichiers de configuration spécifiques aux tests sont déplacés avec les tests eux-mêmes.
5.  **Archiver l'Incertain :** Plutôt que de supprimer des fichiers potentiellement utiles, nous les déplaçons dans `archived_root/` pour une évaluation future.

Cette réorganisation est une première étape cruciale pour clarifier l'architecture du projet.