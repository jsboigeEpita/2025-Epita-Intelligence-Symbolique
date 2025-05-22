# Compatibilité JPype1 avec Python 3.12+

Ce document explique les problèmes de compatibilité de JPype1 avec Python 3.12 et versions supérieures, ainsi que les solutions disponibles pour continuer à exécuter les tests du projet.

## Problèmes de compatibilité

JPype1 est une bibliothèque qui permet d'accéder à des classes Java depuis Python. Cependant, elle présente plusieurs problèmes de compatibilité avec Python 3.12 et versions supérieures :

1. **Problèmes de compilation** : JPype1 nécessite la compilation d'extensions C++ qui ne sont pas compatibles avec les changements introduits dans Python 3.12+.
2. **Dépendances de build** : L'installation de JPype1 nécessite des outils de compilation C++ qui peuvent ne pas être correctement configurés sur tous les environnements.
3. **Incompatibilités d'API** : Certaines API Python utilisées par JPype1 ont été modifiées ou dépréciées dans Python 3.12+.

## Solution : Utilisation du mock JPype1

Pour contourner ces problèmes, nous avons développé un mock de JPype1 qui simule les fonctionnalités essentielles utilisées par notre projet. Ce mock permet d'exécuter les tests sans avoir besoin d'installer la vraie bibliothèque JPype1.

### Comment utiliser le mock JPype1

#### 1. Configuration automatique

Le script `setup_jpype_mock.ps1` détecte automatiquement la version de Python et configure le mock JPype1 si nécessaire :

```powershell
# Exécuter depuis le répertoire racine du projet
.\scripts\setup\setup_jpype_mock.ps1
```

Ce script :
- Détecte la version de Python
- Configure automatiquement le mock JPype1 si Python 3.12+ est détecté
- Teste le mock pour s'assurer qu'il fonctionne correctement

#### 2. Exécution des tests avec le mock

Pour exécuter les tests avec le mock JPype1 :

```powershell
# Exécuter depuis le répertoire racine du projet
python .\scripts\setup\run_tests_with_mock.py
```

#### 3. Configuration manuelle (si nécessaire)

Si vous avez besoin de configurer manuellement le mock JPype1 dans votre code :

```python
# Importer le mock JPype1
from tests.mocks import jpype_mock

# Utiliser jpype comme d'habitude
import jpype
jpype.startJVM()
# ...
```

## Prérequis pour une installation complète de JPype1

Si vous préférez utiliser la vraie bibliothèque JPype1 (recommandé pour Python 3.11 ou moins), voici les prérequis :

### 1. Version de Python compatible

- **Recommandé** : Python 3.11 ou moins
- **Non compatible** : Python 3.12 et versions supérieures

### 2. Outils de compilation

- **Windows** : Visual Studio avec les outils de développement C++ (VS 2019 ou plus récent recommandé)
  - Composants requis : "Outils de build C++" et "SDK Windows"
  - Commande pour installer avec VS Build Tools : `vs_buildtools.exe --add Microsoft.VisualStudio.Workload.VCTools --add Microsoft.VisualStudio.Component.Windows10SDK`

- **Linux** : GCC et les headers de développement Python
  - Ubuntu/Debian : `sudo apt-get install build-essential python3-dev`
  - Fedora/RHEL : `sudo dnf install gcc gcc-c++ python3-devel`

- **macOS** : Xcode Command Line Tools
  - Installation : `xcode-select --install`

### 3. Java JDK

- **Version recommandée** : JDK 8 ou supérieur
- **Variable d'environnement** : `JAVA_HOME` doit être configurée correctement
- **PATH** : Le répertoire `bin` du JDK doit être dans le PATH

### 4. Installation de JPype1

Une fois les prérequis installés, vous pouvez installer JPype1 avec pip :

```bash
python -m pip install JPype1==1.4.1
```

## Dépannage

### Erreurs courantes

1. **Erreur de compilation** : Si vous rencontrez des erreurs de compilation lors de l'installation de JPype1, vérifiez que les outils de compilation sont correctement installés.

2. **JVM non trouvée** : Si JPype1 ne trouve pas la JVM, vérifiez que `JAVA_HOME` est correctement configuré.

3. **Incompatibilité avec Python 3.12+** : Utilisez le mock JPype1 comme décrit ci-dessus.

### Vérification de l'installation

Pour vérifier que JPype1 est correctement installé :

```python
import jpype
jpype.startJVM()
print(f"JVM démarrée : {jpype.isJVMStarted()}")
print(f"Version de JPype : {jpype.__version__}")
```

## Ressources supplémentaires

- [Documentation officielle de JPype1](https://jpype.readthedocs.io/)
- [Dépôt GitHub de JPype1](https://github.com/jpype-project/jpype)
- [Guide d'installation des outils de build Visual Studio](https://visualstudio.microsoft.com/fr/visual-cpp-build-tools/)