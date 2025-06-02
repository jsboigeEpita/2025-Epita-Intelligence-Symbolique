# Scripts de Configuration de l'Environnement

Ce répertoire contient des scripts pour configurer l'environnement de développement, gérer les dépendances (notamment JPype), et diagnostiquer les problèmes d'installation.

## Compatibilité JPype1 avec Python 3.12+

Ce document explique les problèmes de compatibilité de JPype1 avec Python 3.12 et versions supérieures, ainsi que les solutions disponibles pour continuer à exécuter les tests du projet.

### Problèmes de compatibilité

JPype1 est une bibliothèque qui permet d'accéder à des classes Java depuis Python. Cependant, elle présente plusieurs problèmes de compatibilité avec Python 3.12 et versions supérieures :

1.  **Problèmes de compilation** : JPype1 nécessite la compilation d'extensions C++ qui ne sont pas compatibles avec les changements introduits dans Python 3.12+.
2.  **Dépendances de build** : L'installation de JPype1 nécessite des outils de compilation C++ qui peuvent ne pas être correctement configurés sur tous les environnements.
3.  **Incompatibilités d'API** : Certaines API Python utilisées par JPype1 ont été modifiées ou dépréciées dans Python 3.12+.

### Solution : Utilisation du mock JPype1

Pour contourner ces problèmes, nous avons développé un mock de JPype1 qui simule les fonctionnalités essentielles utilisées par notre projet. Ce mock permet d'exécuter les tests sans avoir besoin d'installer la vraie bibliothèque JPype1.

#### Comment utiliser le mock JPype1

##### 1. Configuration automatique

Le script `setup_jpype_mock.ps1` détecte automatiquement la version de Python et configure le mock JPype1 si nécessaire :

```powershell
# Exécuter depuis le répertoire racine du projet
.\scripts\setup\setup_jpype_mock.ps1
```

Ce script :
- Détecte la version de Python
- Configure automatiquement le mock JPype1 si Python 3.12+ est détecté
- Teste le mock pour s'assurer qu'il fonctionne correctement

##### 2. Exécution des tests avec le mock

Pour exécuter les tests avec le mock JPype1 :

```powershell
# Exécuter depuis le répertoire racine du projet
python .\scripts\setup\run_tests_with_mock.py
```

##### 3. Configuration manuelle (si nécessaire)

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

## Dépannage JPype

### Erreurs courantes

1.  **Erreur de compilation** : Si vous rencontrez des erreurs de compilation lors de l'installation de JPype1, vérifiez que les outils de compilation sont correctement installés.
2.  **JVM non trouvée** : Si JPype1 ne trouve pas la JVM, vérifiez que `JAVA_HOME` est correctement configuré.
3.  **Incompatibilité avec Python 3.12+** : Utilisez le mock JPype1 comme décrit ci-dessus.

### Vérification de l'installation de JPype

Pour vérifier que JPype1 est correctement installé et configuré :
- Utilisez le script `check_jpype_import.py` présent dans ce répertoire.
- Ou exécutez le code suivant :
```python
import jpype
jpype.startJVM()
print(f"JVM démarrée : {jpype.isJVMStarted()}")
print(f"Version de JPype : {jpype.__version__}")
```

## Autres Scripts de Setup et Diagnostic

Ce répertoire contient également d'autres scripts utiles pour la configuration et le diagnostic de l'environnement :

- `adapt_code_for_pyjnius.py`: Adapte le code pour une utilisation potentielle avec Pyjnius (alternative à JPype).
- `check_jpype_import.py`: Script de diagnostic détaillé pour l'importation et le fonctionnement de JPype.
- `diagnostic_environnement.py`: Effectue un diagnostic complet de l'environnement de développement.
- `download_test_jars.py`: Télécharge les fichiers JAR nécessaires pour certains tests d'intégration.
- `fix_all_dependencies.ps1` / `fix_all_dependencies.py`: Tentent de corriger l'ensemble des dépendances du projet.
- `fix_dependencies_for_python312.ps1`: Corrections spécifiques pour Python 3.12.
- `fix_dependencies.ps1` / `fix_dependencies.py`: Scripts plus généraux de correction de dépendances.
- `fix_environment_auto.py`: Tente de corriger automatiquement les problèmes d'environnement.
- `fix_pydantic_torch_deps.ps1`: Corrige les conflits entre Pydantic et Torch.
- `fix_pythonpath_manual.py` / `fix_pythonpath_simple.py`: Aident à corriger les problèmes de PYTHONPATH.
- `init_jpype_compatibility.py`: Initialise des configurations de compatibilité pour JPype.
- `install_build_tools.ps1`: Installe les outils de compilation nécessaires.
- `install_environment.py`: Script principal pour l'installation de l'environnement.
- `install_jpype_for_python312.ps1` / `install_jpype_for_python313.ps1`: Scripts spécifiques pour l'installation de JPype sur des versions Python récentes.
- `install_jpype_with_vcvars.ps1`: Installe JPype en utilisant l'environnement VCVars (pour Visual Studio).
- `install_prebuilt_dependencies.ps1` / `install_prebuilt_wheels.ps1`: Installent des dépendances précompilées.
- `run_mock_tests.py`: Exécute des tests en utilisant des mocks.
- `run_tests_with_mock.py`: Exécute les tests du projet avec le mock JPype.
- `run_with_vcvars.ps1`: Exécute une commande dans l'environnement VCVars.
- `setup_jpype_mock.ps1`: Script principal pour configurer le mock JPype.
- `setup_test_env.ps1` / `setup_test_env.py`: Configurent l'environnement de test.
- `test_all_dependencies.ps1` / `test_all_dependencies.py`: Testent toutes les dépendances du projet.
- `test_dependencies.ps1` / `test_dependencies.py`: Testent un sous-ensemble de dépendances.
- `test_jpype_mock.py`: Teste le fonctionnement du mock JPype.
- `validate_environment.py`: Valide la configuration de l'environnement.

Consultez les scripts individuels pour plus de détails sur leur utilisation.

## Ressources supplémentaires

- [Documentation officielle de JPype1](https://jpype.readthedocs.io/)
- [Dépôt GitHub de JPype1](https://github.com/jpype-project/jpype)
- [Guide d'installation des outils de build Visual Studio](https://visualstudio.microsoft.com/fr/visual-cpp-build-tools/)
- [`README_INSTALLATION_OUTILS_COMPILATION.md`](./README_INSTALLATION_OUTILS_COMPILATION.md): Guide spécifique pour l'installation des outils de compilation.
- [`README_PYTHON312_COMPATIBILITY.md`](./README_PYTHON312_COMPATIBILITY.md): Détails sur la compatibilité avec Python 3.12.