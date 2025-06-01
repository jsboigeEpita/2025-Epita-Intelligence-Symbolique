# Guide d'Installation et de Configuration de l'Environnement de Développement

Ce guide vous accompagnera à travers les étapes nécessaires pour configurer votre environnement de développement pour le projet. L'utilisation des scripts fournis simplifie grandement ce processus.

## Prérequis Essentiels

Avant de commencer, assurez-vous d'avoir les éléments suivants installés sur votre machine :

*   **Git :** Pour cloner le dépôt du projet. Vous pouvez le télécharger depuis [git-scm.com](https://git-scm.com/).
*   **PowerShell :** Intégré à Windows. Sur macOS ou Linux, vous utiliserez votre terminal Bash/Zsh standard pour les commandes Git, mais les scripts d'environnement principaux sont conçus pour PowerShell.
*   Une connexion Internet stable.
*   Droits d'administrateur sur votre machine (peuvent être requis pour l'installation de Git ou si des stratégies d'exécution PowerShell doivent être modifiées).

## 1. Clonage du Projet

1.  Ouvrez PowerShell (ou votre terminal préféré pour Git).
2.  Naviguez jusqu'au répertoire où vous souhaitez cloner le projet.
3.  Clonez le dépôt du projet :
    ```powershell
    git clone [URL_DU_DEPOT_GIT] 2025-Epita-Intelligence-Symbolique
    cd 2025-Epita-Intelligence-Symbolique
    ```
    Remplacez `[URL_DU_DEPOT_GIT]` par l'URL réelle du dépôt.

## 2. Configuration Initiale de l'Environnement avec `setup_project_env.ps1`

Le script [`setup_project_env.ps1`](setup_project_env.ps1:1) est conçu pour automatiser la configuration complète de votre environnement. Il effectuera les actions suivantes :
*   Téléchargement et configuration du JDK portable (Java Development Kit 17).
*   Création d'un environnement virtuel Python 3.10 (`.venv`).
*   Installation des dépendances Python requises, y compris JPype 1.5.2, à partir du fichier `requirements.txt`.

**Étapes :**

1.  **Ouvrez PowerShell.**
2.  **Naviguez jusqu'à la racine de votre projet cloné** (où se trouve le script `setup_project_env.ps1`).
    ```powershell
    cd chemin\vers\votre\projet\2025-Epita-Intelligence-Symbolique
    ```
3.  **Exécutez le script de configuration :**
    ```powershell
    .\setup_project_env.ps1
    ```
    *   **Note sur la politique d'exécution PowerShell :** Si vous rencontrez une erreur concernant l'exécution des scripts, vous devrez peut-être ajuster la politique d'exécution pour votre session actuelle. Vous pouvez le faire avec la commande :
        ```powershell
        Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
        ```
        Puis réessayez d'exécuter le script.
4.  **Suivez les instructions :** Le script peut vous poser des questions ou afficher des informations pendant son exécution. Laissez-le se terminer complètement.

À la fin de ce script, votre JDK portable sera configuré, l'environnement virtuel Python sera créé et les dépendances seront installées.

## 3. Activation de l'Environnement de Développement avec `activate_project_env.ps1`

Chaque fois que vous souhaitez travailler sur le projet, vous devez activer l'environnement de développement. Le script [`activate_project_env.ps1`](activate_project_env.ps1:1) s'en charge. Il configure les variables d'environnement nécessaires (`JAVA_HOME`, `PATH`, `CLASSPATH` si défini) et active l'environnement virtuel Python.

**Étapes :**

1.  **Ouvrez une nouvelle session PowerShell.**
2.  **Naviguez jusqu'à la racine de votre projet.**
    ```powershell
    cd chemin\vers\votre\projet\2025-Epita-Intelligence-Symbolique
    ```
3.  **Exécutez le script d'activation :**
    ```powershell
    .\activate_project_env.ps1
    ```
4.  **Vérification :** Une fois le script exécuté, votre invite de commande PowerShell devrait être préfixée par `(.venv)`, indiquant que l'environnement virtuel Python est actif. De plus, les variables d'environnement comme `JAVA_HOME` seront configurées pour cette session.
    Vous pouvez vérifier avec :
    ```powershell
    echo $env:JAVA_HOME
    python --version
    pip list
    ```
    Vous devriez voir le chemin du JDK portable, Python 3.10.x, et la liste des paquets installés dans le venv.

**Important :** Vous devez exécuter `.\activate_project_env.ps1` dans chaque nouvelle session PowerShell où vous prévoyez de travailler sur le projet.

## 4. Vérification de l'Installation de JPype avec `check_jpype_env.py`

Après avoir activé votre environnement avec `.\activate_project_env.ps1`, vous pouvez utiliser le script [`check_jpype_env.py`](check_jpype_env.py:1) pour effectuer un diagnostic de base de votre configuration JPype.

**Étapes :**

1.  Assurez-vous que votre environnement est activé (voir Section 3).
2.  Exécutez le script de diagnostic :
    ```powershell
    python check_jpype_env.py
    ```
3.  **Interprétation de la sortie :**
    *   **Une exécution réussie** affichera des messages indiquant que `JAVA_HOME` est correctement défini, que le chemin de la JVM a été trouvé, que la JVM a démarré avec succès, et qu'un exemple simple d'utilisation d'une classe Java (comme `java.util.ArrayList` ou `java.lang.String`) fonctionne. Vous devriez voir des messages comme "JVM démarrée avec succès." et des informations sur le `CLASSPATH` Java.
    *   **En cas d'erreur,** le script tentera de fournir des indices sur la nature du problème (par exemple, `JAVA_HOME` non défini, JVM non trouvée, `ClassNotFoundException`). Référez-vous à la section "Dépannage" (Section 6) si nécessaire.

## 5. Exécution des Scripts de Démonstration

Une fois votre environnement configuré et activé, vous pouvez exécuter les scripts de démonstration pour vérifier l'intégration avec Tweety et comprendre les fonctionnalités de base.

### 5.1. Script de Démonstration Simplifié (Recommandé pour commencer) : `scripts/demo_tweety_interaction_simple.py`

Ce script est la première étape recommandée pour tester votre installation. Il est conçu pour être simple et rapide à exécuter.

**Ce que ce script démontre :**
*   L'initialisation correcte de la JVM via JPype.
*   Le parsing d'une formule logique simple (par exemple, `a and b`) en utilisant les classes de Tweety.
*   L'affichage de la formule parsée.

**Étapes :**

1.  Assurez-vous que votre environnement est activé (voir Section 3).
2.  Exécutez le script de démonstration simple :
    ```powershell
    python scripts/demo_tweety_interaction_simple.py
    ```
3.  **Sortie Attendue :**
    *   Message confirmant le démarrage de la JVM.
    *   Affichage de la formule logique qui a été parsée (par exemple, `a & b`).
    *   Message indiquant que le script s'est terminé avec succès.
    Une sortie sans erreur indique que les composants essentiels (Python, JPype, JVM, accès basique à Tweety) fonctionnent correctement.

### 5.2. Script de Démonstration Complet (Optionnel - Pour aller plus loin) : `scripts/demonstration_epita.py`

Le script [`scripts/demonstration_epita.py`](scripts/demonstration_epita.py:1) est une démonstration plus exhaustive des capacités du projet. Il est plus complexe et illustre des interactions plus avancées avec Tweety.

**Ce que ce script démontre (entre autres) :**
*   Des opérations logiques plus complexes (satisfiabilité, calcul de modèles).
*   L'utilisation potentielle de mocks pour simuler certains comportements.
*   Des exemples d'analyse de sophismes ou d'autres fonctionnalités avancées du projet.

**Étapes :**

1.  Assurez-vous que votre environnement est activé (voir Section 3).
2.  Exécutez le script de démonstration complet :
    ```powershell
    python scripts/demonstration_epita.py
    ```
3.  **Sortie Attendue :**
    Le script exécutera une série d'opérations avec Tweety. Vous devriez voir en sortie :
    *   Des messages indiquant le démarrage de la JVM.
    *   La création et l'affichage de formules logiques variées.
    *   Les résultats de l'analyse de ces formules (par exemple, vérification de la satisfiabilité, calcul de modèles).
    *   Des exemples d'utilisation d'agents logiques ou d'autres fonctionnalités spécifiques au projet.
    Une exécution sans erreurs et affichant les résultats des opérations logiques indique que votre environnement est prêt pour utiliser les fonctionnalités plus avancées du projet.

## 6. Dépannage des Problèmes JPype Courants

Cette section vous aidera à diagnostiquer et résoudre les problèmes fréquents rencontrés avec JPype, **principalement si le script [`check_jpype_env.py`](check_jpype_env.py:1) signale des erreurs après avoir utilisé les scripts d'installation et d'activation.**

### 6.1. Problèmes liés à `jpype.config` et au Démarrage de la JVM

*   **`jpype.config.jvm_path` (ou argument `jvmpath` de `startJVM`)**
    *   **Cause potentielle :** Chemin incorrect vers `jvm.dll` (Windows) ou `libjvm.so` (Linux/macOS), ou inadéquation entre les architectures Python/JVM (32/64 bits). Les scripts d'environnement tentent de gérer cela, mais une vérification manuelle peut être nécessaire en cas de problème persistant.
    *   **Diagnostic/Solution :**
        1.  **Vérifier la correspondance des architectures :** Assurez-vous que votre installation Python (3.10, typiquement 64 bits) correspond à l'architecture de votre JDK (Java 17, typiquement 64 bits).
        2.  **Vérifier `JAVA_HOME` :** Assurez-vous que `echo $env:JAVA_HOME` (après avoir lancé `.\activate_project_env.ps1`) pointe vers le répertoire `jdk-17.0.15+6` dans `portable_jdk`.
        3.  **Spécifier explicitement le chemin (en dernier recours) :** Si `jpype.getDefaultJVMPath()` échoue (ce qui est géré par les scripts), trouvez manuellement le fichier `jvm.dll` (Windows) ou `libjvm.so` (Linux/macOS) dans votre installation JDK 17 (généralement sous `JDK_HOME\bin\server` ou `JDK_HOME\lib\server`).
            *   **Exemple Windows :** `$env:JAVA_HOME\bin\server\jvm.dll`
            *   **Exemple Linux/macOS :** `$JAVA_HOME/lib/server/libjvm.so`
            Puis, modifiez temporairement un script Python de test :
            ```python
            import jpype
            jvm_path = "CHEMIN_VERS_VOTRE_JVM_DLL_OU_LIBJVM_SO" # Remplacer par le chemin réel
            if not jpype.isJVMStarted():
                jpype.startJVM(jvm_path)
            ```
*   **`jpype.config.classpath` (ou argument `classpath` de `startJVM`)**
    *   **Cause potentielle :** Fichiers JAR non trouvés, `CLASSPATH` incorrect. Source fréquente de `java.lang.ClassNotFoundException`. Le script `activate_project_env.ps1` devrait configurer le `CLASSPATH` nécessaire pour Tweety si les JARs sont dans `libs/tweety_jars`.
    *   **Diagnostic/Solution :**
        1.  **Vérifier le `CLASSPATH` :** Après `.\activate_project_env.ps1`, exécutez `echo $env:CLASSPATH`. Il devrait inclure le chemin vers `libs/tweety_jars/*` si ce dossier existe et contient des JARs.
        2.  **Afficher le `CLASSPATH` réel utilisé par Java :** Dans un script Python (comme [`check_jpype_env.py`](check_jpype_env.py:1) ou un script de test) après le démarrage de la JVM :
            ```python
            import jpype
            if jpype.isJVMStarted():
                java_class_path = jpype.JClass("java.lang.System").getProperty("java.class.path")
                print(f"CLASSPATH Java actuel : {java_class_path}")
            ```
*   **Arguments de la JVM (`*args` dans `startJVM`)**
    *   **Cause potentielle :** Options invalides passées à la JVM.
    *   **Diagnostic/Solution :** Vérifiez la documentation d'Oracle pour les options de ligne de commande de Java 17.
*   **Démarrages Multiples de la JVM**
    *   **Cause potentielle :** JPype ne supporte pas le démarrage multiple de la JVM dans le même processus Python.
    *   **Diagnostic/Solution :** Assurez-vous d'appeler `jpype.startJVM()` une seule fois. Utilisez `jpype.isJVMStarted()` pour vérifier si la JVM est déjà active. Les scripts de démonstration et de vérification gèrent cela.

### 6.2. Exceptions Java/JPype Courantes

*   **`java.lang.ClassNotFoundException`**
    *   **Cause :** Un fichier JAR est manquant dans le `CLASSPATH` ou le nom de la classe Java est incorrect.
    *   **Solution :**
        1.  Vérifiez que tous les JARs nécessaires (y compris ceux de Tweety dans `libs/tweety_jars`) sont correctement inclus dans le `CLASSPATH` (vérifiez `echo $env:CLASSPATH` après activation).
        2.  Assurez-vous que le nom de la classe Java que vous essayez d'appeler est exact (respect de la casse, package complet).
*   **`jpype.JVMNotFoundException`**
    *   **Cause :** JPype n'a pas pu trouver le chemin de la JVM. Cela peut être dû à une variable d'environnement `JAVA_HOME` mal configurée (non définie ou pointant incorrectement) avant que JPype ne tente de trouver la JVM.
    *   **Solution :**
        1.  Assurez-vous d'avoir exécuté `.\activate_project_env.ps1`.
        2.  Vérifiez la configuration de `JAVA_HOME` (voir Section 3 et 6.1).
*   **`java.lang.NoClassDefFoundError`**
    *   **Cause :** Similaire à `ClassNotFoundException`, mais se produit souvent lorsque la classe a été trouvée initialement mais qu'une de ses dépendances n'a pas pu être chargée lors de l'initialisation statique de la classe.
    *   **Solution :** Examinez la trace complète de l'erreur pour identifier la dépendance manquante et assurez-vous qu'elle est dans le `CLASSPATH`.

### 6.3. Script de Vérification `check_jpype_env.py` pour Auto-Diagnostic

Référez-vous à la Section 4 pour l'utilisation du script [`check_jpype_env.py`](check_jpype_env.py:1). Ce script est votre premier outil de diagnostic. Il vérifie `JAVA_HOME`, le chemin de la JVM, tente de démarrer la JVM et d'accéder à une classe Java simple.

Félicitations, votre environnement de développement devrait être prêt ! Si vous rencontrez d'autres problèmes, n'hésitez pas à demander de l'aide en fournissant les messages d'erreur complets que vous obtenez.