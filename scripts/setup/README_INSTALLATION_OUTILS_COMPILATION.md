# Installation des outils de compilation pour les dépendances Python sous Windows

Ce document explique comment installer les outils de compilation nécessaires pour résoudre les problèmes d'installation des dépendances Python (numpy, pandas, jpype) sous Windows.

## Problèmes identifiés

Les bibliothèques suivantes nécessitent des outils de compilation C++ pour être installées sous Windows :

1. **numpy** : Erreur d'importation - `ImportError: DLL load failed while importing _multiarray_umath: Le module spécifié est introuvable.`
2. **pandas** : Erreur d'importation - `ImportError: C extension: No module named 'pandas._libs.window.aggregations' not built.`
3. **jpype** : Erreur d'initialisation - `JVMNotFoundException: No JVM shared library file (jvm.dll) found.`

Ces erreurs se produisent car ces bibliothèques contiennent des extensions C/C++ qui doivent être compilées lors de l'installation si des versions précompilées (wheels) ne sont pas disponibles pour votre configuration spécifique.

## Solution recommandée : Visual Studio Build Tools

Pour résoudre ces problèmes, nous recommandons d'installer **Visual Studio Build Tools 2022**, qui est une version allégée des outils de compilation de Microsoft Visual Studio, sans l'IDE complet.

### Pourquoi Visual Studio Build Tools plutôt que Visual Studio Community ?

| Critère | Visual Studio Build Tools | Visual Studio Community |
|---------|---------------------------|-------------------------|
| Taille d'installation | ~2-3 Go | ~8-10 Go |
| Temps d'installation | Rapide | Long |
| Fonctionnalités | Uniquement les outils de compilation | IDE complet + outils de compilation |
| Suffisant pour notre cas | Oui | Oui (mais surdimensionné) |

Visual Studio Build Tools est l'option la plus légère et la plus adaptée à notre besoin spécifique de compilation d'extensions Python.

## Installation automatique des Visual Studio Build Tools

Nous avons créé un script PowerShell qui installe automatiquement Visual Studio Build Tools 2022 avec les composants nécessaires pour compiler les extensions Python.

### Prérequis

- Windows 10 ou 11
- PowerShell avec droits d'administrateur
- Connexion Internet

### Instructions

1. Ouvrez PowerShell en tant qu'administrateur
2. Naviguez vers le répertoire du projet
3. Exécutez le script d'installation :

```powershell
.\scripts\setup\install_build_tools.ps1
```

Le script va :
- Vérifier si Visual Studio Build Tools est déjà installé
- Télécharger l'installateur de Visual Studio Build Tools 2022
- Installer les composants nécessaires pour compiler les extensions Python
- Vérifier que l'installation a réussi

L'installation peut prendre plusieurs minutes. Un redémarrage peut être nécessaire après l'installation.

## Installation manuelle des Visual Studio Build Tools

Si vous préférez installer manuellement les outils de compilation :

1. Téléchargez Visual Studio Build Tools 2022 depuis le site officiel de Microsoft :
   - URL : https://visualstudio.microsoft.com/fr/downloads/ (section "Outils pour Visual Studio")
   - Ou directement : https://aka.ms/vs/17/release/vs_BuildTools.exe

2. Exécutez l'installateur et sélectionnez les composants suivants :
   - "Développement Desktop en C++"
   - Dans les détails d'installation, assurez-vous que les éléments suivants sont cochés :
     - MSVC v143 - VS 2022 C++ x64/x86 build tools
     - Windows 10/11 SDK
     - Outils C++ CMake pour Windows

3. Procédez à l'installation (environ 2-3 Go d'espace disque requis)

## Installation des dépendances Python après l'installation des outils de compilation

Une fois les outils de compilation installés, vous pouvez installer les dépendances Python en utilisant le script `fix_all_dependencies.ps1` :

```powershell
.\scripts\setup\fix_all_dependencies.ps1
```

Ce script va :
- Vérifier si Visual Studio Build Tools est installé
- Configurer l'environnement pour utiliser les outils de compilation
- Installer les versions spécifiques de numpy, pandas et jpype
- Vérifier que les installations ont réussi

## Vérification de l'installation des dépendances

Pour vérifier que les dépendances sont correctement installées, vous pouvez utiliser le script `test_all_dependencies.ps1` :

```powershell
.\scripts\setup\test_all_dependencies.ps1
```

Ce script va tester l'importation et les fonctionnalités de base de toutes les dépendances, y compris numpy, pandas et jpype.

## Problèmes connus et solutions

### Erreur : "Microsoft Visual C++ 14.0 is required"

**Symptôme** : Lors de l'installation d'une bibliothèque Python, vous obtenez l'erreur "Microsoft Visual C++ 14.0 is required".

**Solution** : Installez Visual Studio Build Tools 2022 comme décrit ci-dessus.

### Erreur : "ImportError: DLL load failed"

**Symptôme** : Après l'installation d'une bibliothèque, vous obtenez une erreur "ImportError: DLL load failed" lors de l'importation.

**Solution** :
1. Assurez-vous que Visual Studio Build Tools est correctement installé
2. Réinstallez la bibliothèque avec la version spécifique recommandée
3. Si le problème persiste, essayez de redémarrer votre ordinateur

### Erreur : "JVMNotFoundException"

**Symptôme** : Lors de l'utilisation de jpype, vous obtenez l'erreur "JVMNotFoundException: No JVM shared library file (jvm.dll) found".

**Solution** :
1. Assurez-vous que Java est installé et que la variable d'environnement JAVA_HOME est correctement configurée
2. Réinstallez jpype avec la version spécifique recommandée

## Conclusion

En installant Visual Studio Build Tools 2022 et en utilisant les scripts fournis, vous devriez pouvoir résoudre les problèmes d'installation des dépendances Python sous Windows. Cette approche est préférable à l'utilisation de mocks car elle permet d'utiliser les bibliothèques réelles, ce qui garantit que les tests sont plus représentatifs du comportement en production.

Si vous rencontrez des problèmes avec cette approche, n'hésitez pas à consulter les scripts de résolution des dépendances dans le répertoire `scripts/setup/` ou à contacter l'équipe de développement.