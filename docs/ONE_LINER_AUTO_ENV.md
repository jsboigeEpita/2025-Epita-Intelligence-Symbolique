# One-liner Auto-Activateur d'Environnement Intelligent

## 🎯 Objectif

Permettre aux agents AI et développeurs de lancer directement les scripts Python sans se soucier de l'état d'activation de l'environnement conda `projet-is`. Le one-liner détecte automatiquement si l'environnement est actif et l'active gracieusement si nécessaire.

## 🚀 Utilisation Ultra-Simple

### Méthode 1 : Import Auto-Exécutant (Recommandée)

```python
# Une seule ligne à ajouter en haut de votre script
import scripts.core.auto_env  # Auto-activation environnement intelligent

# Votre code s'exécute maintenant dans l'environnement projet
```

### Méthode 2 : Import Explicite

```python
from scripts.core.auto_env import ensure_env
ensure_env()  # Retourne True si succès
```

### Méthode 3 : One-liner Complet (Pour Copy-Paste)

```python
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__ if '__file__' in globals() else os.getcwd())), 'scripts', 'core')) if os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__ if '__file__' in globals() else os.getcwd())), 'scripts', 'core')) else None; exec('try:\n from auto_env import ensure_env; ensure_env()\nexcept: pass')
```

## 🧠 Intelligence du One-liner

### Détection Gracieuse
- ✅ **Environnement déjà actif** → Passage silencieux, aucune action
- ✅ **Environnement inactif** → Auto-activation automatique
- ✅ **Conda non disponible** → Mode dégradé, continue l'exécution
- ✅ **Environnement inexistant** → Mode dégradé avec warning

### Gestion d'Erreurs Robuste
- Import qui échoue → Continue sans bloquer
- Variables d'environnement manquantes → Configuration par défaut
- Chemins invalides → Détection automatique du projet

## 📁 Architecture

```
scripts/core/
├── auto_env.py              # Module one-liner principal
├── environment_manager.py   # Gestionnaire environnement (modifié)
└── common_utils.py          # Utilitaires partagés
```

## 🎮 Exemples Pratiques

### Script Test (Exemple Réel)

```python
#!/usr/bin/env python3

# ===== ONE-LINER AUTO-ACTIVATEUR =====
import scripts.core.auto_env  # Auto-activation environnement intelligent

# ===== SCRIPT PRINCIPAL =====
try:
    from semantic_kernel.agents.chat_completion.chat_completion_agent import ChatCompletionAgent
    print("Import works - ChatCompletionAgent found")
except ImportError as e:
    print(f"Import failed: {e}")
```

### Agent AI (Usage Type)

```python
#!/usr/bin/env python3
"""Script que l'agent AI peut lancer directement"""

import scripts.core.auto_env  # Auto-activation

# L'agent peut maintenant utiliser tous les modules du projet
from argumentation_analysis.agents.core.oracle.cluedo_dataset import CluedoDataset
from scripts.core.test_runner import TestRunner
```

## 🔧 Fonctionnalités Avancées

### Variables d'Environnement Auto-Configurées

Le one-liner configure automatiquement :
- `PROJECT_ROOT` → Racine du projet
- `PYTHONPATH` → Inclut la racine projet
- `PYTHONIOENCODING` → utf-8 par défaut
- `CONDA_DEFAULT_ENV` → projet-is

### Mode Silencieux par Défaut

```python
# Mode silencieux (défaut)
import scripts.core.auto_env

# Mode verbeux (pour debug)
from scripts.core.auto_env import ensure_env
ensure_env(silent=False)
```

## 🎯 Cas d'Usage Cibles

### ✅ Agents AI
- Lancent des scripts sans connaître l'état d'environnement
- Intégration zero-friction dans leurs workflows
- Robustesse face aux erreurs d'environnement

### ✅ Développeurs Distraits
- Oublient d'activer l'environnement → Auto-correction
- Lancent des scripts depuis VSCode → Fonctionnement transparent
- Tests rapides → Pas de setup manuel

### ✅ Scripts Automatisés
- CI/CD → Environnement auto-configuré
- Tâches cron → Activation automatique
- Scripts de déploiement → Zero-config

## 🔍 Test et Validation

### Test Direct
```bash
python scripts/core/auto_env.py
```

### Test avec Démo
```bash
python demo_one_liner_usage.py
```

### Intégration Vérifiée
- ✅ `tests/validation_sherlock_watson/test_import.py` (modifié)
- ✅ `demo_one_liner_usage.py` (créé)

## 🛡️ Sécurité et Robustesse

- **Fail-safe** : Continue en mode dégradé si problème
- **Non-intrusif** : N'interrompt jamais l'exécution
- **Idempotent** : Peut être appelé plusieurs fois sans effet de bord
- **Cross-platform** : Windows, Linux, macOS

## 📈 Performances

- **Lazy loading** : Import des modules lourds uniquement si nécessaire
- **Cache intelligent** : Détection d'état rapide
- **Overhead minimal** : ~10ms supplémentaires au démarrage

---

**Auteur :** Intelligence Symbolique EPITA  
**Date :** 09/06/2025  
**Version :** 1.0.0