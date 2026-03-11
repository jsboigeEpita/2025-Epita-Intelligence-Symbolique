# Résolution des Conflits de Version de la JVM

Ce document décrit la procédure de résolution des conflits de version de la JVM qui peuvent survenir lors de l'utilisation de JPype pour l'intégration de code Java dans un projet Python.

## Contexte

Le projet utilise JPype pour communiquer avec une base de code Java existante. Des conflits peuvent survenir si la version de la JVM installée sur le système n'est pas compatible avec celle attendue par le projet.

## Symptômes

Les symptômes d'un conflit de version de la JVM peuvent inclure :

*   Erreurs `java.lang.UnsupportedClassVersionError` lors de l'exécution des tests ou de l'application.
*   Crash de la JVM au démarrage.
*   Comportement inattendu des composants Java.

## Résolution

La résolution des conflits de version de la JVM passe par la configuration correcte de l'environnement pour utiliser une version compatible de la JVM.

### 1. Vérification de la version de la JVM

La première étape consiste à vérifier la version de la JVM actuellement utilisée par le système.

```bash
java -version
```

### 2. Configuration de la JVM

Le projet utilise un gestionnaire de configuration pour spécifier la version de la JVM à utiliser. Cette configuration se trouve dans le fichier `config/settings.toml`.

```toml
[java]
jdk_path = "/path/to/your/jdk"
```

Il est important de s'assurer que le chemin vers le JDK est correct et que la version du JDK est compatible avec le projet.

### 3. Installation d'une version compatible de la JVM

Si la version de la JVM installée sur le système n'est pas compatible, il est nécessaire d'installer une version compatible. Le projet utilise la version 11 de la JVM.

### 4. Nettoyage de l'environnement

Après avoir installé une version compatible de la JVM et configuré le projet pour l'utiliser, il est important de nettoyer l'environnement pour s'assurer que les anciennes versions de la JVM ne sont plus utilisées.

```bash
# Supprimer les anciens logs de test
rm pytest_failures.log

# Relancer les tests
powershell -ExecutionPolicy Bypass -File .\run_tests.ps1 -pytestArgs '-p no:opentelemetry' -LogFile 'pytest_failures.log'
```

## Validation

Après avoir suivi ces étapes, il est important de valider que le problème est résolu en exécutant la suite de tests et en s'assurant qu'il n'y a plus d'erreurs liées à la JVM.