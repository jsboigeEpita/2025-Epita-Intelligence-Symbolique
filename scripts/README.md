# Scripts pour résoudre les problèmes structurels du projet

Ce répertoire contient des scripts pour résoudre les problèmes structurels du projet "argumentiation_analysis".

## Problèmes identifiés

1. **Problèmes d'importation**
   - Incohérence entre les chemins d'importation et la structure réelle des répertoires
   - Importations absolues non qualifiées (`from core import...` au lieu de `from argumentiation_analysis.core import...`)
   - Module `extract_agent.py` situé dans `agents/core/extract/` mais importé comme `agents.extract.extract_agent`

2. **Références incohérentes aux dossiers**
   - Références à un dossier `config/` dans les commentaires mais à `data/` dans le code
   - Chemins codés en dur dans plusieurs fichiers
   - Absence de centralisation pour la gestion des chemins

3. **Gestion du dossier `libs/` créé dynamiquement**
   - Dossier `libs/` créé dynamiquement par `download_tweety_jars`
   - Dépendance aux JARs Tweety pour les tests utilisant la JVM
   - Téléchargement des JARs à chaque exécution des tests

## Scripts disponibles

### Script principal

- **`fix_project_structure.py`** : Script principal qui exécute toutes les étapes nécessaires pour résoudre les problèmes structurels du projet.

```bash
# Mode dry-run (analyse sans modification)
python scripts/fix_project_structure.py --dry-run

# Mode normal (applique les modifications)
python scripts/fix_project_structure.py

# Options disponibles
python scripts/fix_project_structure.py --help
```

### Scripts individuels

- **`update_imports.py`** : Met à jour les importations dans les fichiers existants.

```bash
# Mode dry-run (analyse sans modification)
python scripts/update_imports.py --dry-run

# Mode normal (applique les modifications)
python scripts/update_imports.py
```

- **`update_paths.py`** : Met à jour les références aux chemins dans les fichiers existants.

```bash
# Mode dry-run (analyse sans modification)
python scripts/update_paths.py --dry-run

# Mode normal (applique les modifications)
python scripts/update_paths.py
```

- **`download_test_jars.py`** : Télécharge les JARs minimaux nécessaires pour les tests.

```bash
# Télécharge les JARs s'ils n'existent pas déjà
python scripts/download_test_jars.py

# Force le téléchargement même si les JARs existent déjà
python scripts/download_test_jars.py --force
```

- **`test_imports.py`** : Vérifie que les importations fonctionnent correctement.

```bash
python scripts/test_imports.py
```

- **`analyze_directory_usage.py`** : Analyse l'utilisation des répertoires `config/` et `data/` dans le code.

```bash
python scripts/analyze_directory_usage.py
```

- **`check_imports.py`** : Vérifie que toutes les importations fonctionnent correctement.

```bash
python scripts/check_imports.py
```

## Utilisation recommandée

1. **Analyse des problèmes** : Exécutez d'abord les scripts en mode dry-run pour analyser les problèmes sans modifier les fichiers.

```bash
python scripts/fix_project_structure.py --dry-run
```

2. **Application des modifications** : Une fois que vous êtes satisfait des modifications proposées, exécutez le script principal sans l'option `--dry-run`.

```bash
python scripts/fix_project_structure.py
```

3. **Vérification des modifications** : Exécutez les tests unitaires pour vérifier que les modifications n'ont pas introduit de régressions.

```bash
cd argumentiation_analysis/tests
python run_tests.py
```

## Structure des répertoires créés

- **`argumentiation_analysis/libs/`** : Contient les JARs Tweety principaux
  - **`native/`** : Contient les bibliothèques natives spécifiques à la plateforme

- **`argumentiation_analysis/tests/resources/libs/`** : Contient les JARs minimaux pour les tests
  - **`native/`** : Contient les bibliothèques natives spécifiques à la plateforme pour les tests

## Fichiers créés ou modifiés

- **`argumentiation_analysis/paths.py`** : Module de gestion centralisée des chemins
- **`argumentiation_analysis/__init__.py`** : Fichier d'initialisation du package mis à jour
- **`argumentiation_analysis/core/__init__.py`** : Fichier d'initialisation du module core mis à jour
- **`argumentiation_analysis/agents/__init__.py`** : Fichier d'initialisation du module agents avec redirections
- **`argumentiation_analysis/orchestration/__init__.py`** : Fichier d'initialisation du module orchestration mis à jour
- **`argumentiation_analysis/tests/jvm_test_case.py`** : Classe de base pour les tests qui dépendent de la JVM
- **`argumentiation_analysis/tests/test_jvm_example.py`** : Exemple de test utilisant la classe JVMTestCase
- **`argumentiation_analysis/tests/run_tests.ps1`** : Script de test mis à jour pour vérifier les JARs de test