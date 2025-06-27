# Guide d'Utilisation : `setup_manager.py`

Le script `setup_manager.py` est une façade CLI pour toutes les opérations liées à la configuration et à la réparation de l'environnement de développement.

## Commande `fix-deps`

La commande `fix-deps` permet de réinstaller des dépendances Python, soit individuellement, soit en masse à partir d'un fichier `requirements.txt`. C'est l'outil principal pour corriger les problèmes de paquets corrompus ou de versions incorrectes.

### Utilisation

Il y a deux façons mutuellement exclusives d'utiliser cette commande :

1.  **Par paquet** : Spécifiez un ou plusieurs paquets à réinstaller.
    ```bash
    python scripts/setup_manager.py fix-deps --package <package1> <package2> ...
    ```

2.  **Depuis un fichier `requirements.txt`** : Spécifiez un fichier contenant la liste des dépendances.
    ```bash
    python scripts/setup_manager.py fix-deps --from-requirements <chemin/vers/requirements.txt>
    ```

### Exemples

*   Forcer la réinstallation de `numpy` et `pandas` :
    ```bash
    python scripts/setup_manager.py fix-deps --package numpy pandas
    ```

*   Installer toutes les dépendances listées dans le fichier `requirements.txt` du sous-projet `abs_arg_dung` :
    ```bash
    python scripts/setup_manager.py fix-deps --from-requirements abs_arg_dung/requirements.txt
    ```

---

## Commande `set-path`

La commande `set-path` fournit une solution de secours robuste pour s'assurer que les modules du projet sont correctement ajoutés au `PYTHONPATH` de l'interpréteur.

### Problème résolu

Dans certains cas complexes (environnements virtuels corrompus, conflits), l'installation en "mode édition" (`pip install -e .`) peut échouer. En conséquence, l'interpréteur Python ne trouve pas les modules du projet (ex: `project_core`).

### Solution

Cette commande crée un fichier `argumentation_analysis_project.pth` dans le répertoire `site-packages` de votre environnement Python. Ce fichier contient simplement le chemin absolu vers la racine de ce projet. Python scanne automatiquement les fichiers `.pth` au démarrage et ajoute leur contenu au `sys.path`, rendant les modules du projet importables.

### Utilisation

```bash
python scripts/setup_manager.py set-path
```
Cette commande ne prend aucun argument. Elle détecte automatiquement le bon répertoire `site-packages` et y écrit le fichier de configuration.