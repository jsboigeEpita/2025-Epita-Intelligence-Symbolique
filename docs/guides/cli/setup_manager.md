# Guide d'Utilisation : `setup_manager.py`

Le script `setup_manager.py` est la façade CLI centralisée pour toutes les opérations de **configuration, de réparation et de validation** de l'environnement de développement et de test du projet. Il remplace des dizaines d'anciens scripts par une interface unifiée et robuste.

## Commandes Principales

### 1. Configuration Complète d'un Environnement (`setup`)

C'est la commande à utiliser pour préparer un environnement de travail.

```bash
# Configurer l'environnement de développement
powershell -c "./activate_project_env.ps1; python scripts/setup_manager.py setup --env dev"

# Configurer l'environnement de test (avec mocks)
powershell -c "./activate_project_env.ps1; python scripts/setup_manager.py setup --env test --with-mocks"
```

**Que fait cette commande ?**

*   `--env dev` : S'assure que les prérequis de base sont là et configure les variables d'environnement.
*   `--env test` : Orchestre la préparation complète de l'environnement de test, incluant :
    *   Le téléchargement des dépendances JAR nécessaires.
    *   L'activation des mocks (si `--with-mocks` est utilisé) pour simuler des composants comme la JVM.

### 2. Validation Complète du Projet (`validate`)

Cette commande lance un bilan de santé complet sur le projet.

```bash
# Lancer une validation complète de tous les composants
powershell -c "./activate_project_env.ps1; python scripts/maintenance_manager.py validate --all"
```

*Note : La commande `validate --all` est implémentée via le `maintenance_manager.py` pour regrouper toutes les actions de "vérification" de l'état du projet.*

**Que fait cette commande ?**

Elle exécute une série de vérifications et produit un rapport sur :
*   L'existence des fichiers et répertoires critiques.
*   La validité des imports majeurs du projet.
*   La couverture de code des tests.

## Commandes de Réparation (Dépannage)

### 3. Réparation des Dépendances (`fix-deps`)

Utilisez cette commande lorsque vous rencontrez des problèmes avec des paquets Python.

**Par paquet :**
```bash
# Réinstaller de force `numpy` et `pandas`
powershell -c "./activate_project_env.ps1; python scripts/setup_manager.py fix-deps --package numpy pandas"

# Tenter une réparation agressive pour JPype1 (essaie plusieurs stratégies)
powershell -c "./activate_project_env.ps1; python scripts/setup_manager.py fix-deps --package JPype1 --strategy=aggressive"
```

**Depuis un fichier `requirements.txt`:**
```bash
# Installer les dépendances pour un sous-projet
powershell -c "./activate_project_env.ps1; python scripts/setup_manager.py fix-deps --from-requirements abs_arg_dung/requirements.txt"
```

### 4. Configuration Manuelle du `PYTHONPATH` (`set-path`)

En dernier recours, si le projet n'est pas trouvé par Python, cette commande crée un fichier `.pth` dans votre environnement pour forcer la reconnaissance du chemin du projet.

```bash
powershell -c "./activate_project_env.ps1; python scripts/setup_manager.py set-path"
```

Cette commande est particulièrement utile si `pip install -e .` a échoué.
