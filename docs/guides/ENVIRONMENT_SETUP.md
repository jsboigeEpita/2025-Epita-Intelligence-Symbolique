# Configuration de l'Environnement Dédié - Oracle Enhanced v2.1.0

## Vue d'ensemble

Ce projet utilise un **environnement Python dédié** pour isoler les dépendances et garantir la reproductibilité. Il est **CRITIQUE** d'utiliser l'environnement dédié plutôt que Python système.

## 🎯 Environnement Recommandé : Conda

### Nom de l'environnement : `projet-is`

```bash
# Création de l'environnement (première fois)
conda env create -f environment.yml

# Activation manuelle
conda activate projet-is

# Vérification
conda env list
```

## 🔧 Configuration Automatique

### Script d'activation principal

```powershell
# Utilisation recommandée - avec commande
.\setup_project_env.ps1 -CommandToRun "python -m pytest tests/"

# Script direct
powershell -File .\scripts\env\activate_project_env.ps1 -CommandToRun "python --version"
```

### Détection automatique d'environnement

Le script `activate_project_env.ps1` recherche automatiquement :

1. **Environnements conda** contenant : `oracle`, `argum`, `intelligence`
2. **Environnements venv** dans : `venv/`, `env/`, `.venv/`
3. **Fallback** vers Python système avec avertissement

## 📋 Variables d'environnement configurées

```powershell
$env:PYTHONPATH = "racine;project_core;libs;argumentation_analysis;$env:PYTHONPATH"
$env:PYTHONIOENCODING = "utf-8"
```

## 🔍 Vérification de l'environnement

### Script de diagnostic rapide

```bash
python scripts/setup/test_all_dependencies.py
```

### Nouveau script de diagnostic complet

```bash
python scripts/env/diagnose_environment.py
```

## ⚠️ Différences Environnement Système vs Dédié

| Aspect | Système | Dédié (projet-is) |
|--------|---------|-------------------|
| **Python** | Version variable | Python 3.10 fixe |
| **NumPy** | Version variable | NumPy 2.0.2 |
| **Semantic Kernel** | ❌ Absent | ✅ v1.32.2 + fallback |
| **Pydantic** | Version variable | v2.9.2 compatible |
| **PYTHONPATH** | Non configuré | ✅ Modules projet |
| **JPype** | ❌ Souvent absent | ✅ v1.4.0+ |

## 🚀 Instructions pour nouveaux agents/utilisateurs

### 1. Première installation

```powershell
# 1. Cloner le projet
git clone <url-projet>
cd 2025-Epita-Intelligence-Symbolique

# 2. Créer l'environnement conda
conda env create -f environment.yml

# 3. Tester l'installation
.\setup_project_env.ps1 -CommandToRun "python scripts/setup/test_all_dependencies.py"
```

### 2. Utilisation quotidienne

```powershell
# Lancer des tests
.\setup_project_env.ps1 -CommandToRun "python -m pytest tests/unit/"

# Démarrer une démo
.\setup_project_env.ps1 -CommandToRun "python demos/webapp/run_webapp.py"

# Exécuter un script
.\setup_project_env.ps1 -CommandToRun "python scripts/maintenance/analyze_documentation.py"
```

### 3. Résolution de problèmes

```powershell
# Diagnostic complet
.\setup_project_env.ps1 -CommandToRun "python scripts/env/diagnose_environment.py"

# Vérification des dépendances
.\setup_project_env.ps1 -CommandToRun "pip list | grep -E '(semantic|pydantic|numpy)'"

# Réinstallation si nécessaire
conda env remove -n projet-is
conda env create -f environment.yml
```

## 🛠️ Activation automatique dans les scripts

### Pattern recommandé pour nouveaux scripts

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
from pathlib import Path

# Auto-détection et ajout du projet au PYTHONPATH
project_root = Path(__file__).resolve().parent.parent  # Ajuster selon niveau
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Vérification environnement (optionnel)
try:
    import scripts.env.environment_helpers as env_helpers
    env_helpers.ensure_project_environment()
except ImportError:
    print("⚠️  Exécutez via setup_project_env.ps1 pour l'environnement optimal")
```

## 📊 Statut des dépendances critiques

### ✅ Opérationnelles

- **semantic-kernel**: v1.32.2 avec fallback agents
- **pytest-asyncio**: Tests asynchrones compatibles
- **AuthorRole**: Disponible via fallback
- **NumPy 2.x**: Compatible avec Scikit-learn 1.x
- **JPype**: Pour intégration Java

### 🔄 Fallbacks implémentés

- `project_core/semantic_kernel_agents_fallback.py`
- `project_core/semantic_kernel_agents_import.py`
- Mocks JPype dans `tests/mocks/`

## 🎯 Commandes de démarrage rapide

```powershell
# Tests de base
.\setup_project_env.ps1 -CommandToRun "python -m pytest tests/unit/ -v"

# Démo Sherlock Watson
.\setup_project_env.ps1 -CommandToRun "python scripts/sherlock_watson/run_sherlock_watson_moriarty_robust.py"

# Web API
.\setup_project_env.ps1 -CommandToRun "python demos/webapp/run_webapp.py"

# Validation complète
.\setup_project_env.ps1 -CommandToRun "python scripts/env/diagnose_environment.py --full"
```

## 📝 Notes importantes

1. **TOUJOURS** utiliser `setup_project_env.ps1` pour l'exécution
2. **JAMAIS** installer de packages dans l'environnement système
3. **VÉRIFIER** l'activation via les messages de logging
4. **REPORTER** les problèmes d'environnement avec diagnostic complet

---

**Dernière mise à jour**: 08/06/2025  
**Version environnement**: Oracle Enhanced v2.1.0  
**Python**: 3.10 (Conda)  
**Score opérationnalité**: 100%