# Recommandations Corrigées - Environnement Dédié

## 🎯 Nouvelles Instructions de Démarrage

### ✅ Commandes Corrigées

| Ancien (Incorrect) | Nouveau (Correct) |
|-------------------|------------------|
| `python demos/webapp/run_webapp.py` | `.\setup_project_env.ps1 -CommandToRun "python demos/webapp/run_webapp.py"` |
| `python scripts/sherlock_watson/run_sherlock_watson_moriarty_robust.py` | `.\setup_project_env.ps1 -CommandToRun "python scripts/sherlock_watson/run_sherlock_watson_moriarty_robust.py"` |
| `python -m pytest tests/` | `.\setup_project_env.ps1 -CommandToRun "python -m pytest tests/"` |
| `pip install -r requirements.txt` | `conda env create -f environment.yml` puis `conda activate projet-is` |

### 🚀 Démarrage Rapide Corrigé

```powershell
# 1. Créer l'environnement (première fois seulement)
conda env create -f environment.yml

# 2. Vérification rapide
.\setup_project_env.ps1 -Status

# 3. Lancer des démonstrations
.\setup_project_env.ps1 -CommandToRun "python demos/webapp/run_webapp.py"
.\setup_project_env.ps1 -CommandToRun "python scripts/sherlock_watson/run_sherlock_watson_moriarty_robust.py"

# 4. Exécuter des tests
.\setup_project_env.ps1 -CommandToRun "python -m pytest tests/unit/ -v"

# 5. Diagnostic complet
.\setup_project_env.ps1 -CommandToRun "python scripts/env/diagnose_environment.py --full"
```

### ⚠️ Erreurs Précédentes Corrigées

1. **Installation pip vs conda**: Utiliser `environment.yml` au lieu de `requirements.txt`
2. **Python système**: Toujours utiliser l'environnement dédié `projet-is`
3. **PYTHONPATH manuel**: Automatiquement configuré par `setup_project_env.ps1`
4. **Dépendances manquantes**: Toutes incluses dans `environment.yml`

### 🔍 Outils de Diagnostic Nouveaux

```powershell
# Vérification rapide
.\setup_project_env.ps1 -Status

# Gestionnaire d'environnement
.\setup_project_env.ps1 -CommandToRun "python scripts/env/manage_environment.py help"

# Configuration initiale
.\setup_project_env.ps1 -Setup

# Réparation automatique
.\setup_project_env.ps1 -CommandToRun "python scripts/env/manage_environment.py fix"
```

### 📝 Pour les Nouveaux Agents

1. **TOUJOURS** utiliser `setup_project_env.ps1` pour l'exécution
2. **JAMAIS** exécuter directement avec `python <script>`
3. **VÉRIFIER** l'environnement avec `.\setup_project_env.ps1 -Status`
4. **CRÉER** l'environnement avec `conda env create -f environment.yml`

### 🛠️ Résolution de Problèmes

```powershell
# Si erreur "Python non trouvé"
conda env create -f environment.yml
conda activate projet-is

# Si erreur "Module non trouvé"
.\setup_project_env.ps1 -CommandToRun "python scripts/env/manage_environment.py fix"

# Si environnement corrompu
conda env remove -n projet-is
conda env create -f environment.yml
```

---
**Mise à jour**: 08/06/2025 - Corrections environnement dédié
**Statut**: ✅ Toutes les recommandations corrigées et validées