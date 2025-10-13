# 🎭 Démonstrations

## 📋 Vue d'Ensemble

Les démonstrations fournissent des exemples fonctionnels complets du système d'argumentation de l'Intelligence Symbolique EPITA. Chaque démo illustre un aspect spécifique ou un cas d'usage particulier, permettant de comprendre rapidement les capacités du système.

Ces démonstrations sont organisées en 4 catégories selon leur objectif : **validation**, **intégration**, **debugging** et **showcases**.

## 📂 Structure

```
demos/
├── validation/         # Démonstrations de validation et tests complets
├── integration/        # Exemples d'intégration système et workflows
├── debugging/          # Outils et démos de débogage ciblé
└── showcases/          # Présentations des fonctionnalités principales
```

## 🚀 Démarrage Rapide

### Prérequis

- Python 3.8+
- Environnement virtuel activé
- Dépendances installées (`pip install -r requirements.txt`)

### Lancer votre première démo

```bash
# Démo one-liner : usage simplifié du système
python demos/showcases/demo_one_liner_usage.py

# Validation complète EPITA : test exhaustif
python demos/validation/validation_complete_epita.py
```

## 📚 Catégories de Démonstrations

### 🔍 Validation

**Objectif** : Démonstrations de validation exhaustive et tests de qualité du système

| Démo | Description | Niveau |
|------|-------------|--------|
| [validation_complete_epita.py](./validation/validation_complete_epita.py) | Validation complète du système avec bootstrap robuste et détection automatique de la racine projet | Avancé |
| [validation_deep_taxonomy.py](./validation/validation_deep_taxonomy.py) | Validation approfondie de la taxonomie des sophismes | Intermédiaire |
| [validation_report.md](./validation/validation_report.md) | Rapport de validation consolidé avec métriques | Documentation |

**📖 [Documentation détaillée](./validation/README.md)**

### 🔗 Integration

**Objectif** : Exemples d'intégration système et tests de workflows parallèles

| Démo | Description | Niveau |
|------|-------------|--------|
| [test_parallel_workflow_integration.py](./integration/test_parallel_workflow_integration.py) | Test d'intégration des workflows parallèles avec gestion des dépendances | Avancé |

**📖 [Documentation détaillée](./integration/README.md)**

### 🐛 Debugging

**Objectif** : Outils et démonstrations pour le débogage ciblé d'un sophisme ou d'une analyse

| Démo | Description | Niveau |
|------|-------------|--------|
| [debug_single_fallacy.py](./debugging/debug_single_fallacy.py) | Outil de débogage pour analyser un sophisme spécifique avec Semantic Kernel | Avancé |

**📖 [Documentation détaillée](./debugging/README.md)**

### 🌟 Showcases

**Objectif** : Présentations des fonctionnalités principales et usages simplifiés

| Démo | Description | Niveau |
|------|-------------|--------|
| [demo_one_liner_usage.py](./showcases/demo_one_liner_usage.py) | Démonstration du one-liner auto-activateur intelligent pour agents IA | Débutant |
| [simple_exploration_tool.py](./showcases/simple_exploration_tool.py) | Outil d'exploration simplifié de la taxonomie des sophismes | Débutant |

**📖 [Documentation détaillée](./showcases/README.md)**

## 🔗 Ressources Connexes

- **[Tutoriels](../tutorials/README.md)** : Guides pas-à-pas pour apprendre le système
- **[Exemples](../examples/README.md)** : Code réutilisable et patterns d'implémentation
- **[Documentation](../docs/)** : Documentation technique complète et référence API
- **[Tests](../tests/)** : Suite de tests automatisés

## 🎯 Cas d'Usage

### Pour les Débutants
1. Commencez par `showcases/demo_one_liner_usage.py` pour comprendre l'usage de base
2. Explorez `showcases/simple_exploration_tool.py` pour découvrir la taxonomie

### Pour les Développeurs
1. Étudiez `validation/validation_complete_epita.py` pour les bonnes pratiques de bootstrap
2. Analysez `integration/test_parallel_workflow_integration.py` pour l'intégration avancée

### Pour le Debugging
1. Utilisez `debugging/debug_single_fallacy.py` pour diagnostiquer un sophisme spécifique
2. Consultez `validation/validation_report.md` pour comprendre les résultats de validation

## 💡 Contribuer

### Ajouter une Nouvelle Démo

1. **Choisir la catégorie** : validation, integration, debugging ou showcases
2. **Créer le fichier** : Suivre la convention de nommage `[category]_[description].py`
3. **Inclure le bootstrap** : Utiliser le pattern de bootstrap robuste (voir `validation_complete_epita.py`)
4. **Documenter** : Ajouter docstring complète et commentaires explicatifs
5. **Tester** : Vérifier que la démo fonctionne de manière autonome
6. **Mettre à jour** : Ajouter une entrée dans ce README et dans le sous-README correspondant

### Pattern de Bootstrap Recommandé

```python
#!/usr/bin/env python3
from pathlib import Path
import sys

# Bootstrap robuste avec détection automatique de la racine
current_file = Path(__file__).resolve()
project_root = next((p for p in current_file.parents if (p / "pyproject.toml").exists()), None)
if project_root and str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
    
from argumentation_analysis.core.environment import ensure_env
ensure_env()
```

## 📊 Statistiques

- **Total démos** : 7
- **Catégories** : 4
- **Niveaux** : Débutant (2), Intermédiaire (1), Avancé (4)
- **Langages** : Python (6), Markdown (1)

---

**Dernière mise à jour** : Phase D2.3 - Documentation Structure  
**Mainteneur** : Intelligence Symbolique EPITA  
**Licence** : Voir LICENSE à la racine du projet