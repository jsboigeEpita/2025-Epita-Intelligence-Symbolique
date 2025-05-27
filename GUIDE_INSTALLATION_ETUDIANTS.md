# Guide d'Installation - Intelligence Symbolique EPITA

## 🎯 Résumé Rapide

**Problème résolu** : Configuration automatique de l'environnement pour Python 3.12+ avec contournement des problèmes de pip/JPype.

**Solution en 1 commande** :
```bash
python scripts/setup/fix_pythonpath_simple.py
```

## 📋 Diagnostic des Problèmes Résolus

### Problèmes Identifiés et Corrigés

1. **Package non installé en mode développement** ✅ RÉSOLU
   - **Cause** : Problèmes de permissions avec pip sur Python 3.13
   - **Solution** : Configuration manuelle du PYTHONPATH

2. **Dépendances manquantes** ✅ PARTIELLEMENT RÉSOLU
   - **Dépendances essentielles** : numpy, pandas, matplotlib, cryptography ✅ DISPONIBLES
   - **Dépendances de test** : pytest, etc. ⚠️ À installer manuellement si nécessaire

3. **Configuration Java/JPype** ✅ RÉSOLU
   - **Cause** : JPype1 incompatible avec Python 3.12+
   - **Solution** : Mock JPype automatiquement configuré

## 🚀 Installation Automatique

### Étape 1 : Exécuter le Script de Correction
```bash
cd c:/dev/2025-Epita-Intelligence-Symbolique
python scripts/setup/fix_pythonpath_simple.py
```

### Étape 2 : Vérifier l'Installation
```bash
python -c "import argumentation_analysis; print('SUCCESS: Package accessible!')"
```

## 🔧 Installation Manuelle (si nécessaire)

### Si le script automatique échoue :

1. **Configurer le PYTHONPATH manuellement** :
```python
import sys
from pathlib import Path
project_root = Path("c:/dev/2025-Epita-Intelligence-Symbolique")
sys.path.insert(0, str(project_root))
```

2. **Utiliser le script de démarrage** :
```bash
python setup_env.py
```

## 📦 Dépendances

### Dépendances Essentielles (Disponibles)
- ✅ numpy 2.2.1
- ✅ pandas 2.2.3  
- ✅ matplotlib 3.10.0
- ✅ cryptography 42.0.8
- ✅ cffi 1.17.1
- ✅ psutil 7.0.0

### Dépendances Optionnelles (À installer si nécessaire)
```bash
# Pour les tests
pip install --user pytest pytest-cov pytest-asyncio

# Pour l'analyse avancée
pip install --user scikit-learn networkx

# Pour l'IA/ML
pip install --user torch transformers

# Pour les notebooks
pip install --user notebook jupyter
```

## ☕ Configuration Java/JPype

### Statut Actuel
- ✅ Java 21 détecté et fonctionnel
- ✅ Mock JPype configuré automatiquement
- ⚠️ JAVA_HOME non défini (optionnel)

### Pour une Configuration Java Complète (Optionnel)
```bash
# Définir JAVA_HOME (optionnel)
set JAVA_HOME=C:\Program Files\Java\jdk-21

# Ou utiliser le mock JPype (recommandé)
from tests.mocks import jpype_mock
```

## 🔑 Configuration des Clés API (Optionnel)

### Fichier .env Disponible
Un fichier `.env` existe déjà. Pour ajouter des clés API :

```bash
# Copier le template
copy .env.template .env.local

# Éditer avec vos clés
# OPENAI_API_KEY=your_key_here
# AZURE_OPENAI_KEY=your_azure_key_here
```

## ✅ Validation de l'Installation

### Test Rapide
```bash
python -c "import argumentation_analysis; import numpy; import pandas; print('TOUT FONCTIONNE!')"
```

### Test Complet
```bash
python scripts/setup/diagnostic_environnement.py
```

## 🎓 Utilisation pour les Étudiants

### Démarrage Rapide
```python
# Au début de vos scripts Python
import sys
from pathlib import Path
sys.path.insert(0, str(Path("c:/dev/2025-Epita-Intelligence-Symbolique")))

# Maintenant vous pouvez importer
import argumentation_analysis
from argumentation_analysis.agents import informal_agent
```

### Ou Utiliser le Script de Configuration
```python
# Importer le script de configuration
exec(open('setup_env.py').read())

# Puis utiliser normalement
import argumentation_analysis
```

## 🐛 Dépannage

### Problème : "No module named 'argumentation_analysis'"
**Solution** :
```bash
python scripts/setup/fix_pythonpath_simple.py
```

### Problème : Erreurs de permissions pip
**Solution** : Utiliser `--user` ou un environnement virtuel
```bash
pip install --user package_name
```

### Problème : JPype non disponible
**Solution** : Le mock JPype est automatiquement configuré
```python
from tests.mocks import jpype_mock  # Active le mock
import jpype  # Fonctionne maintenant
```

## 📁 Fichiers Créés par l'Installation

- ✅ `setup_env.py` - Script de configuration de l'environnement
- ✅ `tests/mocks/jpype_mock.py` - Mock JPype pour Python 3.12+
- ✅ `scripts/setup/validate_environment.py` - Script de validation
- ✅ `.env.template` - Template de configuration des clés API
- ✅ `diagnostic_report.json` - Rapport détaillé du diagnostic

## 🎯 Résumé pour les Étudiants

1. **Exécutez** : `python scripts/setup/fix_pythonpath_simple.py`
2. **Vérifiez** : `python -c "import argumentation_analysis; print('OK!')"`
3. **Utilisez** : Importez normalement dans vos projets

**En cas de problème** : Consultez ce guide ou exécutez le diagnostic complet.

---

*Guide créé automatiquement par le système de diagnostic d'environnement*
*Dernière mise à jour : 27/05/2025*