# Plan pour le Document d'Architecture : Python-Java Intégration (JPype/Tweety)

## 1. Introduction

*   **Objectif du document** : Expliquer l'intégration Python-Java via JPype pour utiliser la bibliothèque Tweety.
*   **Public cible** : Développeurs rejoignant le projet ou ayant besoin de comprendre/modifier cette intégration.

## 2. Vue d'Ensemble de l'Architecture

*   **Brève description des technologies** : Python, Java, JPype, Tweety.
*   **Diagramme de haut niveau** (Mermaid) :
    ```mermaid
    graph LR
        subgraph Environnement Python
            direction LR
            A[Script Python App/Test] --> B{JPype};
        end

        subgraph Configuration
            direction TB
            C1[setup_project_env.ps1] --> D1[portable_jdk/];
            C1 --> E1[venv_py310/];
            C1 --> F1[.env (JAVA_HOME)];
            C2[activate_project_env.ps1] --> F1;
            F1 --> G[Variables d'Env (JAVA_HOME, PATH)];
        end

        subgraph Pont JPype & JVM
            direction LR
            B --> H{initialize_jvm / JVMService};
            H --> I[Découverte JVM (JAVA_HOME, Portable)];
            H --> J[Construction Classpath (libs/*.jar)];
            H --> K[Démarrage JVM (jpype.startJVM)];
        end

        subgraph Environnement Java
            direction LR
            K --> L[JVM Active];
            L --> M[Bibliothèques Tweety (libs/*.jar)];
            M --> N[Bibliothèques Natives (libs/native/*.dll)];
        end

        A --> C2;
        G --> I;
        J --> K;
        B --> M;
        M --> B;

        style A fill:#cde4ff,stroke:#333,stroke-width:2px
        style M fill:#ffdac1,stroke:#333,stroke-width:2px
        style K fill:#e6ffc1,stroke:#333,stroke-width:2px
        style C1 fill:#f9f7c1,stroke:#333,stroke-width:1px
        style C2 fill:#f9f7c1,stroke:#333,stroke-width:1px
    ```

## 3. Composants Clés et Leurs Rôles

### 3.1. Environnement Python
*   Rôle de `venv_py310` : Isolation des dépendances Python.
*   Dépendance principale : `JPype1` (installée via `requirements.txt`).

### 3.2. Environnement Java (JDK)
*   Utilisation d'un JDK portable :
    *   Téléchargement et extraction gérés par `setup_project_env.ps1` (OpenJDK 17 via `jdkUrl`).
    *   Stockage dans le répertoire `portable_jdk/`.
    *   Détection dynamique du nom du répertoire JDK extrait (fonction `Get-JdkSubDir` dans `setup_project_env.ps1`).
*   Configuration de `JAVA_HOME` :
    *   Définie dans le fichier `.env` par `setup_project_env.ps1`.
    *   Chargée par `activate_project_env.ps1` et utilisée pour configurer le `PATH`.
*   Logique de découverte de la JVM par `argumentation_analysis.core.jvm_setup.find_valid_java_home()`:
    *   Priorité 1 : JDK portable (référence à `jdk-17.0.15+6` dans le code, noter l'incohérence potentielle avec la version téléchargée `17.0.11+9` et comment `Get-JdkSubDir` pourrait la gérer).
    *   Priorité 2 : Variable d'environnement `JAVA_HOME`.
    *   Priorité 3 : Heuristiques système.
    *   Priorité 4 : Chemin par défaut de JPype (`jpype.getDefaultJVMPath()` utilisé dans `check_jpype_env.py` et `initialize_jvm`).

### 3.3. Scripts d'Environnement
*   `setup_project_env.ps1` :
    *   Vérification de la version Python.
    *   Téléchargement/Extraction du JDK portable.
    *   Création du `venv`.
    *   Installation des dépendances Python (`requirements.txt`).
    *   Création/Mise à jour du fichier `.env` avec `JAVA_HOME`.
*   `activate_project_env.ps1` :
    *   Activation du `venv`.
    *   Chargement des variables d'environnement depuis `.env` (notamment `JAVA_HOME`).
    *   Ajout du `bin` du JDK au `PATH`.

### 3.4. JPype : Le Pont Python-Java
*   Rôle : Permettre à Python d'interagir avec du code Java.
*   Initialisation de la JVM :
    *   Gérée par `argumentation_analysis.core.jvm_setup.initialize_jvm()`.
    *   Utilisation de `jpype.startJVM()`.
    *   Arguments de la JVM : `-Djava.library.path` pour les DLLs natives (`libs/native/`), options mémoire.
*   Gestion du Classpath :
    *   Construit dynamiquement par `initialize_jvm()` en scannant `libs/*.jar` et potentiellement `argumentation_analysis/tests/resources/libs/*.jar`.
    *   Utilisé lors du démarrage de la JVM.
*   Importation de classes Java : `jpype.JClass("...")` ou `from java... import ...` après `jpype.imports.registerDomain(...)`.
*   Conversion de types : Mentionner brièvement `convertStrings=False`.

### 3.5. Bibliothèque Tweety
*   Rôle : Fournir les fonctionnalités d'analyse argumentative formelle.
*   Stockage : Fichiers JAR dans le répertoire `libs/` (listés dans `libs/README.md`).
*   Exemples de classes utilisées (tirés de `check_jpype_env.py` et `libs/README.md`) :
    *   `org.tweetyproject.logics.pl.syntax.PlSignature`
    *   `org.tweetyproject.logics.pl.syntax.PlParser`

### 3.6. Script de Diagnostic
*   `check_jpype_env.py` :
    *   Vérifie la configuration de l'environnement (Python, `JAVA_HOME`, chemin JVM).
    *   Construit le classpath pour Tweety.
    *   Tente de démarrer la JVM avec ce classpath.
    *   Teste l'importation et l'instanciation de classes Java standard et Tweety.
    *   Sert d'outil de débogage pour l'intégration.

### 3.7. Gestion Centralisée de la JVM (potentiellement)
*   `JVMService` (mentionné dans `libs/README.md`, probablement dans `argumentation_analysis/services/`) : Décrire son rôle si l'analyse du code le confirme comme point d'entrée principal pour l'application.
*   Fixture `integration_jvm` dans `tests/conftest.py` : Rôle dans le cycle de vie de la JVM pour les tests d'intégration, utilisation de `initialize_jvm`.

## 4. Flux d'Interaction Typique

*   Un développeur active l'environnement (`activate_project_env.ps1`).
*   Un script Python (applicatif ou test) a besoin d'une fonctionnalité Tweety.
*   Appel à `initialize_jvm()` (directement ou via `JVMService` / fixture `integration_jvm`).
    *   Localisation de la JVM.
    *   Construction du classpath.
    *   Démarrage de la JVM avec JPype.
*   Le script Python importe et utilise les classes Tweety via JPype.
*   Les résultats sont retournés à Python.
*   Arrêt de la JVM (géré par `JVMService` ou la fixture `integration_jvm`).

## 5. Choix Clés d'Architecture

*   **JDK Portable** : Avantages (pas de dépendance système, version contrôlée). Inconvénient (taille du dépôt, incohérence de version notée).
*   **Gestion du Classpath Dynamique** : Avantages (facilité d'ajout de JARs dans `libs/`).
*   **Centralisation de l'Initialisation JVM** (via `initialize_jvm` et potentiellement `JVMService`) : Avantages (maintenance, configuration unique).
*   **Utilisation de `.env` pour `JAVA_HOME`** : Flexibilité et séparation de la configuration.

## 6. Prérequis pour les Développeurs

*   Python (version spécifiée dans `setup_project_env.ps1`, actuellement 3.10).
*   Avoir exécuté `setup_project_env.ps1` au moins une fois.
*   Activer l'environnement avec `activate_project_env.ps1` avant de travailler.
*   Compréhension de base de Python et Java (pour interagir avec Tweety).
*   (Optionnel) Connaissance de JPype pour des modifications avancées.
*   Système d'exploitation : Windows x64 si les DLLs natives de `libs/native/` sont utilisées.

## 7. Points d'Attention et Maintenance

*   **Incohérence de version du JDK portable** : Documenter la différence entre `setup_project_env.ps1` (`17.0.11+9`) et `jvm_setup.py` (référence à `17.0.15+6`). Expliquer comment `Get-JdkSubDir` pourrait aider mais qu'une harmonisation serait préférable.
*   Mise à jour des JARs Tweety : Suivre les instructions de `libs/README.md`.
*   Gestion des bibliothèques natives (`libs/native/`).

## 8. Conclusion

*   Résumé des points clés de l'architecture.
*   Importance de cette intégration pour le projet.