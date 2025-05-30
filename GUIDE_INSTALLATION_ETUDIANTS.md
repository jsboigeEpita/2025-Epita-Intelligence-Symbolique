# Guide d'Installation et de Configuration de l'Environnement de Développement

Ce guide vous accompagnera à travers les étapes nécessaires pour configurer votre environnement de développement avec Java JDK 17, Python 3.10 et JPype 1.5.2.

## Prérequis

*   Une connexion Internet stable.
*   Droits d'administrateur sur votre machine (pour l'installation de JDK et Python).

## 1. Utilisation du JDK Portable (Java Development Kit 17)

Ce projet utilise une version portable du JDK 17, située dans le répertoire `portable_jdk/` à la racine du projet. Il n'est donc pas nécessaire d'installer un JDK système.

## 2. Configuration de la variable d'environnement `JAVA_HOME` et du `PATH`

La variable d'environnement `JAVA_HOME` est cruciale pour que les applications (y compris JPype) puissent localiser votre installation JDK portable. Le `PATH` doit également être mis à jour pour inclure le répertoire `bin` du JDK.

Le chemin complet du JDK portable est : `[CHEMIN_VERS_LE_REPERTOIRE_DU_PROJET]/portable_jdk/jdk-17.0.15+6/`

### Sur Windows (PowerShell) :

1.  Ouvrez PowerShell.
2.  Naviguez jusqu'à la racine de votre projet (où se trouve ce guide).
    ```powershell
    cd d:\Dev\2025-Epita-Intelligence-Symbolique
    ```
3.  Définissez la variable `JAVA_HOME` et mettez à jour le `PATH` pour cette session PowerShell :
    ```powershell
    $project_root = Get-Location
    $env:JAVA_HOME = "$project_root\portable_jdk\jdk-17.0.15+6"
    $env:Path = "$env:JAVA_HOME\bin;$env:Path"
    ```
    *Note :* Ces commandes configurent les variables pour la session PowerShell actuelle. Pour une configuration permanente, vous devrez les ajouter à votre profil PowerShell (généralement `$PROFILE`).

4.  **Vérification :** Dans la même session PowerShell, tapez :
    ```powershell
    java -version
    echo $env:JAVA_HOME
    ```
    Vous devriez voir la version de Java et le chemin de `JAVA_HOME` pointer vers le JDK portable.

### Sur macOS / Linux :

1.  Ouvrez votre terminal.
2.  Naviguez jusqu'à la racine de votre projet (où se trouve ce guide).
    ```bash
    cd /chemin/vers/votre/projet/2025-Epita-Intelligence-Symbolique
    ```
3.  Définissez la variable `JAVA_HOME` et mettez à jour le `PATH` pour cette session de terminal :
    ```bash
    export PROJECT_ROOT=$(pwd)
    export JAVA_HOME="$PROJECT_ROOT/portable_jdk/jdk-17.0.15+6"
    export PATH="$JAVA_HOME/bin:$PATH"
    ```
    *Note :* Pour rendre ces changements permanents, ajoutez ces lignes à votre fichier de configuration de shell (par exemple, `~/.bashrc`, `~/.zshrc`, ou `~/.profile`) et exécutez `source ~/.zshrc` (ou le fichier approprié).

4.  **Vérification :** Dans la même session de terminal, tapez :
    ```bash
    java -version
    echo $JAVA_HOME
    ```
    Vous devriez voir la version de Java et le chemin de `JAVA_HOME` pointer vers le JDK portable.

### Note Importante sur l'Automatisation :

Il est possible qu'un script d'automatisation (par exemple, un script PowerShell ou Bash) soit fourni avec le projet pour gérer la récupération, la décompression et la configuration dynamique de ce JDK portable. **Il est fortement recommandé de vérifier l'existence d'un tel script et de l'utiliser en priorité**, car il simplifiera grandement la configuration de votre environnement. Référez-vous à la documentation du projet ou aux fichiers `scripts/` pour plus d'informations.

## 3. Installation de Python 3.10

1.  **Télécharger Python 3.10 :**
    Rendez-vous sur le site officiel de Python : [https://www.python.org/downloads/release/python-3100/](https://www.python.org/downloads/release/python-3100/)
    Téléchargez l'installeur adapté à votre système d'exploitation.

2.  **Exécuter l'installeur :**
    *   **Important (Windows) :** Lors de l'installation, assurez-vous de cocher la case "Add Python 3.10 to PATH" (Ajouter Python 3.10 au PATH) sur la première page de l'installeur. Cela simplifiera grandement la configuration.
    *   Suivez les instructions pour terminer l'installation.

3.  **Vérification :** Ouvrez une nouvelle invite de commande/terminal et tapez :
    ```powershell
    python --version
    ```
    Vous devriez voir `Python 3.10.x`.

## 4. Création et Activation d'un Environnement Virtuel Python (`venv`)

Il est fortement recommandé d'utiliser un environnement virtuel pour isoler les dépendances de votre projet et éviter les conflits avec d'autres projets Python.

1.  **Naviguez vers votre répertoire de projet :**
    Ouvrez votre terminal ou invite de commande et utilisez `cd` pour aller à la racine de votre projet (là où se trouve ce guide).
    ```powershell
    cd d:\Dev\2025-Epita-Intelligence-Symbolique
    ```

2.  **Créez l'environnement virtuel :**
    ```powershell
    python -m venv venv
    ```
    Cela créera un dossier `venv` dans votre répertoire de projet.

3.  **Activez l'environnement virtuel :**

    *   **Sur Windows (PowerShell) :**
        ```powershell
        .\venv\Scripts\Activate.ps1
        ```
    *   **Sur Windows (CMD) :**
        ```cmd
        venv\Scripts\activate.bat
        ```
    *   **Sur macOS / Linux :**
        ```bash
        source venv/bin/activate
        ```
    Une fois activé, vous verrez `(venv)` apparaître au début de votre ligne de commande, indiquant que vous êtes dans l'environnement virtuel.

## 5. Installation de JPype 1.5.2 et autres dépendances

Avec votre environnement virtuel activé, vous pouvez installer les bibliothèques Python nécessaires.

1.  **Installation de JPype :**
    ```powershell
    pip install JPype1==1.5.2
    ```

2.  **Installation des autres dépendances (si un `requirements.txt` existe) :**
    Si votre projet contient un fichier `requirements.txt` (qui liste toutes les dépendances Python), vous pouvez les installer en une seule commande :
    ```powershell
    pip install -r requirements.txt
    ```
    *Hypothèse :* Si un `requirements.txt` n'est pas fourni, vous devrez installer les dépendances manuellement au fur et à mesure de vos besoins.

## 6. Configuration de la variable `CLASSPATH` (si nécessaire pour Tweety)

La variable `CLASSPATH` est utilisée par la JVM (Java Virtual Machine) pour trouver les classes Java nécessaires. Si Tweety (ou d'autres bibliothèques Java) nécessite des fichiers JAR spécifiques qui ne sont pas dans le chemin par défaut de votre JDK, vous devrez les ajouter ici.

*Hypothèse :* Pour le moment, nous allons supposer que les JARs de Tweety sont gérés par JPype ou sont déjà accessibles via le JDK. Si vous rencontrez des erreurs `ClassNotFoundException` ou similaires, vous devrez ajouter les chemins vers les fichiers JAR de Tweety à votre `CLASSPATH`.

### Exemple de configuration `CLASSPATH` (à adapter) :

Si vous avez des fichiers JAR de Tweety dans un dossier `libs/tweety_jars` à la racine de votre projet, vous pourriez configurer `CLASSPATH` comme suit :

### Sur Windows (PowerShell) :

```powershell
$env:CLASSPATH = ".;$env:CLASSPATH;D:\Dev\2025-Epita-Intelligence-Symbolique\libs\tweety_jars\*"
# Ou si vous avez des JARs spécifiques :
# $env:CLASSPATH = ".;$env:CLASSPATH;D:\Dev\2025-Epita-Intelligence-Symbolique\libs\tweety_jars\tweety.jar;D:\Dev\2025-Epita-Intelligence-Symbolique\libs\tweety_jars\autre_dependance.jar"
```
*Note :* Le `.` au début du `CLASSPATH` inclut le répertoire courant. Le `*` à la fin du chemin du dossier inclut tous les JARs dans ce dossier.

### Sur macOS / Linux :

```bash
export CLASSPATH=".:$CLASSPATH:/chemin/vers/votre/projet/libs/tweety_jars/*"
# Ou si vous avez des JARs spécifiques :
# export CLASSPATH=".:$CLASSPATH:/chemin/vers/votre/projet/libs/tweety_jars/tweety.jar:/chemin/vers/votre/projet/libs/tweety_jars/autre_dependance.jar"
```
*Note :* Vous devrez ajouter ces lignes à votre fichier `~/.bashrc` ou `~/.zshrc` et le `source` pour que les changements soient permanents.

**Vérification (optionnel) :**
Vous pouvez vérifier la valeur de `CLASSPATH` avec :
```powershell
echo $env:CLASSPATH # Windows PowerShell
echo $CLASSPATH # macOS / Linux
```

## 7. Test de l'environnement

Pour vérifier que tout est correctement configuré, vous pouvez essayer d'exécuter un script Python simple qui utilise JPype.

1.  Créez un fichier `test_jpype.py` à la racine de votre projet avec le contenu suivant :
    ```python
    import jpype
    import jpype.imports
    from jpype.types import *

    if not jpype.isJVMStarted():
        # Assurez-vous que JAVA_HOME est correctement configuré
        # Si vous avez des JARs spécifiques à ajouter, utilisez jpype.startJVM(jpype.getDefaultJVMPath(), "-Djava.class.path=/chemin/vers/votre/jar.jar")
        jpype.startJVM(jpype.getDefaultJVMPath())
        print("JVM démarrée avec succès.")
    else:
        print("JVM déjà démarrée.")

    # Exemple simple d'utilisation de Java via JPype
    try:
        java_util = jpype.JClass("java.util.ArrayList")
        my_list = java_util()
        my_list.add("Hello")
        my_list.add("JPype")
        print(f"Liste Java créée : {my_list}")
        print(f"Taille de la liste : {my_list.size()}")
    except Exception as e:
        print(f"Erreur lors de l'accès à une classe Java : {e}")

    # jpype.shutdownJVM() # Décommenter si vous voulez arrêter la JVM après l'exécution
    ```

2.  Exécutez le script (assurez-vous que votre environnement virtuel est activé) :
    ```powershell
    python test_jpype.py
    ```
    Si vous voyez les messages de succès et la liste Java, votre environnement est correctement configuré !

Félicitations, votre environnement de développement est prêt !

## 8. Dépannage des Problèmes JPype Courants

Cette section vous aidera à diagnostiquer et résoudre les problèmes fréquents rencontrés avec JPype.

### 8.1. Problèmes liés à `jpype.config` et au Démarrage de la JVM

*   **`jpype.config.jvm_path` (ou argument `jvmpath` de `startJVM`)**
    *   **Cause potentielle :** Chemin incorrect vers `jvm.dll` (Windows) ou `libjvm.so` (Linux/macOS), ou inadéquation entre les architectures Python/JVM (32/64 bits).
    *   **Diagnostic/Solution :**
        1.  **Vérifier la correspondance des architectures :** Assurez-vous que votre installation Python (32 ou 64 bits) correspond à l'architecture de votre JDK (Java 17). Il est fortement recommandé d'utiliser des versions 64 bits pour les deux.
        2.  **Spécifier explicitement le chemin :** Si `jpype.getDefaultJVMPath()` ne fonctionne pas, trouvez manuellement le fichier `jvm.dll` (Windows) ou `libjvm.so` (Linux/macOS) dans votre installation JDK 17 (généralement sous `JDK_HOME\bin\server` ou `JDK_HOME\jre\lib\amd64\server`).
            *   **Exemple Windows :** `C:\Program Files\Java\jdk-17\bin\server\jvm.dll`
            *   **Exemple Linux/macOS :** `/chemin/vers/votre/jdk-17/lib/server/libjvm.so`
            Puis, utilisez :
            ```python
            import jpype
            jvm_path = "CHEMIN_VERS_VOTRE_JVM_DLL_OU_LIBJVM_SO"
            if not jpype.isJVMStarted():
                jpype.startJVM(jvm_path)
            ```
*   **`jpype.config.classpath` (ou argument `classpath` de `startJVM`)**
    *   **Cause potentielle :** Fichiers JAR non trouvés, `CLASSPATH` incorrect. Source fréquente de `java.lang.ClassNotFoundException`.
    *   **Diagnostic/Solution :**
        1.  **Définir le `CLASSPATH` avant `startJVM()` :** Utilisez `jpype.addClassPath()` ou l'argument `classpath` lors du démarrage de la JVM.
            ```python
            import jpype
            # Ajoutez les JARs de Tweety ou autres dépendances Java
            jpype.addClassPath("D:/Dev/2025-Epita-Intelligence-Symbolique/libs/tweety_jars/*")
            # Ou pour des JARs spécifiques :
            # jpype.addClassPath("D:/Dev/2025-Epita-Intelligence-Symbolique/libs/tweety_jars/tweety.jar")

            if not jpype.isJVMStarted():
                jpype.startJVM(jpype.getDefaultJVMPath())
            ```
        2.  **Afficher le `CLASSPATH` réel :** Après le démarrage de la JVM, vous pouvez vérifier le `CLASSPATH` utilisé par Java :
            ```python
            import jpype
            if jpype.isJVMStarted():
                java_class_path = jpype.JClass("java.lang.System").getProperty("java.class.path")
                print(f"CLASSPATH Java actuel : {java_class_path}")
            ```
*   **Arguments de la JVM (`*args` dans `startJVM`)**
    *   **Cause potentielle :** Options invalides passées à la JVM.
    *   **Diagnostic/Solution :** Vérifiez la documentation d'Oracle pour les options de ligne de commande de Java 17. Des options courantes incluent `-Xmx512m` pour la mémoire.
*   **Démarrages Multiples de la JVM**
    *   **Cause potentielle :** JPype ne supporte pas le démarrage multiple de la JVM dans le même processus Python.
    *   **Diagnostic/Solution :** Assurez-vous d'appeler `jpype.startJVM()` une seule fois. Utilisez `jpype.isJVMStarted()` pour vérifier si la JVM est déjà active.

### 8.2. Exceptions Java/JPype Courantes

*   **`java.lang.ClassNotFoundException`**
    *   **Cause :** Un fichier JAR est manquant dans le `CLASSPATH` ou le nom de la classe Java est incorrect.
    *   **Solution :**
        1.  Vérifiez que tous les JARs nécessaires (y compris ceux de Tweety) sont correctement ajoutés au `CLASSPATH` comme décrit ci-dessus.
        2.  Assurez-vous que le nom de la classe Java que vous essayez d'appeler est exact (respect de la casse, package complet).
*   **`jpype.JVMNotFoundException`**
    *   **Cause :** JPype n'a pas pu trouver le chemin de la JVM. Cela peut être dû à un `jvm_path` incorrect ou à une variable d'environnement `JAVA_HOME` mal configurée.
    *   **Solution :**
        1.  Vérifiez la configuration de `JAVA_HOME` (Section 2 du guide).
        2.  Spécifiez explicitement le `jvm_path` comme expliqué dans la section 8.1.
*   **`java.lang.NoClassDefFoundError`**
    *   **Cause :** Similaire à `ClassNotFoundException`, mais se produit souvent lorsque la classe a été trouvée initialement mais qu'une de ses dépendances n'a pas pu être chargée lors de l'initialisation statique de la classe.
    *   **Solution :** Examinez la trace complète de l'erreur pour identifier la dépendance manquante et assurez-vous qu'elle est dans le `CLASSPATH`.

### 8.3. Script de Vérification Basique pour Auto-Diagnostic

Utilisez ce script pour vérifier rapidement votre configuration JPype.

```python
import jpype
import os

print("--- Vérification de l'environnement JPype ---")

# 1. Vérification de JAVA_HOME
java_home = os.environ.get('JAVA_HOME')
print(f"JAVA_HOME : {java_home}")
if not java_home:
    print("ATTENTION : JAVA_HOME n'est pas défini. Veuillez le configurer (Section 2).")
else:
    # Tente de trouver le chemin de la JVM basé sur JAVA_HOME
    # Adaptez ce chemin si votre structure JDK est différente
    jvm_path_candidates = [
        os.path.join(java_home, 'bin', 'server', 'jvm.dll'), # Windows
        os.path.join(java_home, 'jre', 'bin', 'server', 'jvm.dll'), # Anciens JDK Windows
        os.path.join(java_home, 'lib', 'server', 'libjvm.so'), # Linux
        os.path.join(java_home, 'jre', 'lib', 'amd64', 'server', 'libjvm.so'), # Anciens JDK Linux
        os.path.join(java_home, 'lib', 'server', 'libjvm.dylib') # macOS
    ]
    found_jvm_path = None
    for path in jvm_path_candidates:
        if os.path.exists(path):
            found_jvm_path = path
            break
    
    if found_jvm_path:
        print(f"Chemin JVM potentiel trouvé via JAVA_HOME : {found_jvm_path}")
    else:
        print("AVERTISSEMENT : Impossible de trouver jvm.dll/libjvm.so/libjvm.dylib sous JAVA_HOME. Vérifiez votre installation JDK.")

# 2. Vérification du chemin JVM par défaut de JPype
default_jvm_path = None
try:
    default_jvm_path = jpype.getDefaultJVMPath()
    print(f"Chemin JVM par défaut de JPype : {default_jvm_path}")
    if not os.path.exists(default_jvm_path):
        print("ATTENTION : Le chemin JVM par défaut de JPype n'existe pas. Vérifiez votre installation Java.")
except Exception as e:
    print(f"Erreur lors de la récupération du chemin JVM par défaut de JPype : {e}")
    print("Cela peut indiquer un problème avec votre installation Java ou JAVA_HOME.")

# 3. Tentative de démarrage de la JVM
print("\n--- Tentative de démarrage de la JVM ---")
if not jpype.isJVMStarted():
    try:
        # Ajoutez ici les chemins vers vos JARs si nécessaire
        # Exemple pour les JARs de Tweety :
        # jpype.addClassPath("D:/Dev/2025-Epita-Intelligence-Symbolique/libs/tweety_jars/*")
        
        # Utilisez le chemin par défaut ou un chemin spécifique si le défaut échoue
        if default_jvm_path and os.path.exists(default_jvm_path):
            jpype.startJVM(default_jvm_path)
        elif found_jvm_path and os.path.exists(found_jvm_path):
            jpype.startJVM(found_jvm_path)
        else:
            print("ERREUR : Aucun chemin JVM valide trouvé pour démarrer. Veuillez corriger JAVA_HOME ou jvm_path.")
            exit() # Quitte le script si la JVM ne peut pas démarrer

        print("JVM démarrée avec succès.")
        java_class_path = jpype.JClass("java.lang.System").getProperty("java.class.path")
        print(f"CLASSPATH Java après démarrage : {java_class_path}")

        # Exemple d'accès à une classe Java simple
        java_string = jpype.JClass("java.lang.String")
        test_str = java_string("Hello from Java!")
        print(f"Accès à java.lang.String : {test_str}")

    except Exception as e:
        print(f"ERREUR lors du démarrage ou de l'utilisation de la JVM : {e}")
        print("Causes possibles : chemin JVM incorrect, CLASSPATH manquant, architecture incompatible.")
else:
    print("JVM déjà démarrée (ce script ne la redémarrera pas).")
    java_class_path = jpype.JClass("java.lang.System").getProperty("java.class.path")
    print(f"CLASSPATH Java actuel : {java_class_path}")

# 4. Vérification de la correspondance d'architecture (manuel)
print("\n--- Vérification de l'architecture ---")
print("Assurez-vous que votre Python (3.10) et votre JDK (Java 17) sont de la même architecture (64 bits recommandé).")
print("Pour Python, exécutez 'python -c \"import platform; print(platform.architecture())\"'")
print("Pour Java, vérifiez votre téléchargement JDK (x64 pour 64 bits).")

# jpype.shutdownJVM() # Décommenter si vous voulez arrêter la JVM après l'exécution
print("\n--- Fin de la vérification ---")
```