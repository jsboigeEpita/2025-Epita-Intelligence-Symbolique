# Résolution des Problèmes de Dépendances pour les Tests

Ce document explique comment résoudre les problèmes de dépendances (numpy, pandas, jpype) pour exécuter les tests unitaires sans utiliser de mocks.

## Problèmes de Dépendances Identifiés

Les problèmes de dépendances suivants ont été identifiés :

1. **numpy** : Erreurs d'importation et incompatibilités avec l'environnement de test
2. **pandas** : Dépendance forte pour l'analyse de données structurées
3. **jpype** : Erreurs d'initialisation et problèmes de compatibilité

## Solution : Utilisation de Versions Spécifiques

Au lieu d'utiliser des mocks pour ces dépendances, nous avons opté pour l'utilisation de versions spécifiques connues pour être compatibles avec notre environnement de test :

- **numpy==1.24.3** : Cette version est compatible avec notre environnement de test et ne présente pas les erreurs d'importation observées avec d'autres versions.
- **pandas==2.0.3** : Cette version est compatible avec numpy 1.24.3 et fonctionne correctement dans notre environnement de test.
- **jpype1==1.4.1** : Cette version résout les erreurs d'initialisation et les problèmes de compatibilité.

## Installation des Dépendances

### Méthode Automatique (Recommandée)

Nous avons créé des scripts pour installer automatiquement les versions compatibles des dépendances :

#### Sous Windows (PowerShell)

```powershell
# Exécuter le script PowerShell
.\scripts\setup\fix_dependencies.ps1
```

Ce script :
1. Vérifie si Python est installé
2. Installe les versions spécifiques de numpy, pandas et jpype1
3. Crée un environnement virtuel pour les tests si nécessaire
4. Installe toutes les dépendances de test dans l'environnement virtuel

#### Sous Linux/macOS (Bash)

```bash
# Exécuter le script Python directement
python scripts/setup/fix_dependencies.py

# Ou créer un environnement virtuel et installer les dépendances
python -m venv venv_test
source venv_test/bin/activate  # Linux/macOS
pip install -r requirements-test.txt
```

### Méthode Manuelle

Si vous préférez installer les dépendances manuellement :

```bash
# Installer les versions spécifiques des dépendances problématiques
pip install numpy==1.24.3 pandas==2.0.3 jpype1==1.4.1

# Installer les autres dépendances de test
pip install -r requirements-test.txt
```

## Exécution des Tests

Une fois les dépendances installées, vous pouvez exécuter les tests comme suit :

```bash
# Activer l'environnement virtuel si vous en utilisez un
# Windows
.\venv_test\Scripts\activate
# Linux/macOS
source venv_test/bin/activate

# Exécuter tous les tests
pytest

# Exécuter les tests avec la couverture de code
pytest --cov=argumentation_analysis

# Générer un rapport HTML de couverture
pytest --cov=argumentation_analysis --cov-report=html
```

## Vérification de l'Installation des Dépendances

Pour vérifier que les dépendances sont correctement installées et fonctionnelles :

```python
# Créer un fichier test_dependencies.py
import numpy as np
import pandas as pd
import jpype

print(f"numpy version: {np.__version__}")
print(f"pandas version: {pd.__version__}")
print(f"jpype version: {jpype.__version__}")

# Tester numpy
arr = np.array([1, 2, 3, 4, 5])
print(f"numpy array: {arr}")
print(f"numpy mean: {np.mean(arr)}")

# Tester pandas
df = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6]})
print(f"pandas DataFrame:\n{df}")

# Tester jpype (sans initialiser la JVM)
print(f"jpype.isJVMStarted(): {jpype.isJVMStarted()}")

print("Toutes les dépendances sont correctement installées et fonctionnelles.")
```

Exécutez ce script pour vérifier que les dépendances sont correctement installées :

```bash
python test_dependencies.py
```

## Problèmes Connus et Solutions

### Problème : Erreur d'importation de numpy

**Symptôme** : `ImportError: DLL load failed while importing _multiarray_umath: Le module spécifié est introuvable.`

**Solution** : Réinstaller numpy avec la version spécifiée :
```bash
pip uninstall -y numpy
pip install numpy==1.24.3
```

### Problème : Erreur d'importation de pandas

**Symptôme** : `ImportError: C extension: No module named 'pandas._libs.window.aggregations' not built.`

**Solution** : Réinstaller pandas avec la version spécifiée :
```bash
pip uninstall -y pandas
pip install pandas==2.0.3
```

### Problème : Erreur d'initialisation de jpype

**Symptôme** : `JVMNotFoundException: No JVM shared library file (jvm.dll) found.`

**Solution** : 
1. Vérifier que Java est installé et que JAVA_HOME est correctement configuré
2. Réinstaller jpype avec la version spécifiée :
```bash
pip uninstall -y jpype1
pip install jpype1==1.4.1
```

## Conclusion

En utilisant des versions spécifiques des dépendances problématiques, nous pouvons exécuter les tests unitaires sans avoir recours à des mocks. Cette approche est préférable car elle permet de tester le code avec les bibliothèques réelles, ce qui garantit que les tests sont plus représentatifs du comportement en production.

Si vous rencontrez des problèmes avec cette approche, n'hésitez pas à consulter les scripts de résolution des dépendances dans le répertoire `scripts/setup/` ou à contacter l'équipe de développement.