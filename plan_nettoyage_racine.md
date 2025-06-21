# Plan de Nettoyage de la Racine du Projet

Ce document détaille le plan de réorganisation du répertoire racine du projet.

## Fichiers Essentiels à Conserver à la Racine

Les fichiers suivants sont jugés essentiels et resteront à la racine pour garantir un accès facile à la configuration, à la documentation et aux scripts de base.

1.  **Documentation & Métadonnées :**
    *   `README.md`
    *   `LICENSE`
    *   `CHANGELOG.md`
    *   `GUIDE_DEMARRAGE_RAPIDE_PROJET_EPITA.md`

2.  **Configuration Python :**
    *   `pyproject.toml`
    *   `setup.py`
    *   `pytest.ini`
    *   `environment.yml`

3.  **Configuration Node.js :**
    *   `package.json`
    *   `package-lock.json`
    *   `playwright.config.js`

4.  **Scripts d'Environnement :**
    *   `activate_project_env.ps1`
    *   `activate_project_env.sh`
    *   `setup_project_env.ps1`
    *   `setup_project_env.sh`
    *   `install_environment.py`

5.  **Scripts d'Exécution Principaux :**
    *   `start_webapp.py`
    *   `run_tests.ps1`

## Plan de Réorganisation

Les fichiers restants seront déplacés dans des sous-répertoires logiques pour améliorer la clarté de la structure du projet.

| Fichier(s) / Modèle | Destination Proposée |
| --- | --- |
| `*.log` | `logs/` |
| `run_sherlock_*.sh`, `run_sherlock_*.ps1`,`check_*.py`, `validation_*.py` | `scripts/validation/` |
| `test_*.py`, `test_*.ps1` (non-tests unitaires) | `tests/diagnostic/` |
| `generateur_*.py`, `run_all_new_component_tests.sh` | `scripts/` |
| `*.md` (sauf essentiels) | `docs/reports/` |
| `*.patch` | `patches/` |
| `temp_generated_config.yml` | `_temp/` |

## Plan d'Action pour l'Implémentation

L'agent `Code` devra exécuter les commandes suivantes pour appliquer ce plan.

### 1. Création des répertoires

```bash
mkdir -p scripts/validation tests/diagnostic docs/reports patches
```

### 2. Déplacement des fichiers avec `git mv`

```bash
# Déplacer les logs
git mv *.log logs/

# Déplacer les scripts de validation
git mv run_sherlock_watson_synthetic_validation.ps1 run_sherlock_watson_synthetic_validation.sh check_jar_content.py check_sk_module.py validation_point2_llm_authentique.py scripts/validation/

# Déplacer les scripts de diagnostic
git mv test_import_bypass_env.py test_import.py test_jpype_minimal.py test_startup.ps1 tests/diagnostic/

# Déplacer les scripts restants
git mv generateur_donnees_synthetiques_llm.py run_all_new_component_tests.sh scripts/

# Déplacer les rapports et la documentation non essentielle
git mv validation_*.md analysis_report.md playwright_test_summary.md revised_plan.md docs/reports/

# Déplacer les patches
git mv my_agent_fixes.patch patches/

# Déplacer les fichiers temporaires
git mv temp_generated_config.yml _temp/
```

### 3. Mise à jour du `.gitignore`

Il est recommandé d'ajouter les répertoires suivants au fichier `.gitignore` s'ils ne s'y trouvent pas déjà :
*   `logs/`
*   `_temp/`