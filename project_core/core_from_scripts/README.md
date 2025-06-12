# Modules Python Mutualisés - Scripts de Projet

## Vue d'ensemble

Ce répertoire contient les modules Python mutualisés utilisés par tous les scripts PowerShell et bash du projet. Ces modules centralisent les fonctionnalités communes pour améliorer la maintenabilité et la cohérence.

## Modules disponibles

### 📋 common_utils.py
**Utilitaires communs et logging**
- `Logger`: Système de logging centralisé avec couleurs
- `print_colored()`: Affichage coloré cross-platform
- `setup_logging()`: Configuration du logging
- `validate_python_requirements()`: Validation des prérequis Python
- Utilitaires de formatage, timestamps, et sauvegarde JSON

### 🔧 environment_manager.py
**Gestion des environnements conda/venv**
- `EnvironmentManager`: Gestionnaire principal d'environnement
- Activation/désactivation automatique d'environnements
- Détection de conda, venv, pipenv
- Validation des dépendances
- Exécution de commandes dans l'environnement

### 🧪 test_runner.py
**Orchestration des tests**
- `TestRunner`: Gestionnaire d'exécution des tests
- Support pytest, unittest, et scripts personnalisés
- Exécution par type (unit, integration, validation)
- Filtrage par composant et pattern
- Génération de rapports JSON

### ✅ validation_engine.py
**Moteur de validation système**
- `ValidationEngine`: Moteur de validation principal
- Vérification des prérequis système
- Validation des environnements authentiques
- Génération de rapports HTML
- Analyse de cohérence et robustesse

### ⚙️ project_setup.py
**Configuration de projet**
- `ProjectSetup`: Gestionnaire de configuration
- Installation automatique des dépendances
- Configuration des environnements
- Validation post-installation
- Support multi-plateforme

## Utilisation

### Import typique dans un script
```python
import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'scripts', 'core'))

from common_utils import setup_logging, print_colored
from environment_manager import EnvironmentManager
from test_runner import TestRunner
```

### Logger configuré
```python
logger = setup_logging(verbose=True)
logger.info("Message d'information")
logger.success("Message de succès")
logger.error("Message d'erreur")
```

### Affichage coloré
```python
print_colored("Message de succès", "green")
print_colored("Message d'erreur", "red")
print_colored("Information", "blue")
```

### Gestion d'environnement
```python
env_manager = EnvironmentManager()
result = env_manager.activate_environment()
if result['success']:
    env_manager.run_command_in_environment("python script.py")
```

### Exécution de tests
```python
test_runner = TestRunner()
result = test_runner.run_tests_by_type(
    test_type="unit",
    verbose=True,
    report_file="test_report.json"
)
```

## Architecture

```
scripts/core/
├── __init__.py                 # Package marker
├── common_utils.py            # Base utilities
├── environment_manager.py     # Environment handling
├── test_runner.py            # Test execution
├── validation_engine.py      # System validation
├── project_setup.py          # Project configuration
└── README.md                 # This documentation
```

## Compatibilité

- **Python**: 3.7+
- **Plateformes**: Windows, Linux, macOS
- **Shells**: PowerShell, Bash, Zsh
- **Environnements**: conda, venv, pipenv

## Scripts utilisateurs

Les scripts suivants utilisent ces modules :

### PowerShell (.ps1)
- `activate_project_env.ps1`
- `setup_project_env.ps1`
- `run_tests.ps1`
- `run_sherlock_watson_synthetic_validation.ps1`
- `run_all_new_component_tests.ps1`

### Bash (.sh)
- `activate_project_env.sh`
- `setup_project_env.sh`
- `run_tests.sh`
- `run_sherlock_watson_synthetic_validation.sh`
- `run_all_new_component_tests.sh`

## Avantages de la refactorisation

1. **✅ Code mutualisé**: Évite la duplication de code
2. **🔄 Maintenabilité**: Modifications centralisées
3. **🧪 Testabilité**: Modules Python facilement testables
4. **🌐 Cross-platform**: Fonctionne sur Windows, Linux, macOS
5. **📊 Monitoring**: Logging et rapports uniformes
6. **🔧 Extensibilité**: Ajout facile de nouvelles fonctionnalités

## Développement

Pour ajouter un nouveau module :

1. Créer le fichier `.py` dans `scripts/core/`
2. Implémenter les classes et fonctions nécessaires
3. Ajouter les imports dans `__init__.py`
4. Mettre à jour cette documentation
5. Créer des tests unitaires dans `tests/unit/scripts/`

## Logging et Debugging

Tous les modules supportent le mode verbeux :
```python
logger = setup_logging(verbose=True)
```

En mode verbeux, les modules affichent :
- Détails des opérations
- Chemins de fichiers utilisés
- Commandes exécutées
- Stack traces complètes en cas d'erreur

## Support

Pour des questions ou des améliorations :
- Consulter les logs détaillés avec `--verbose`
- Vérifier la documentation des classes individuelles
- Examiner les exemples dans les scripts utilisateurs

---

**Auteur**: Intelligence Symbolique EPITA  
**Date**: 09/06/2025  
**Version**: 1.0 - Refactorisation complète