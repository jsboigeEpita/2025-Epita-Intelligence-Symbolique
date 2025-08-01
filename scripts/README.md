# Guide des Scripts du Projet

Ce document sert de guide central pour tous les scripts fonctionnels du projet. Il a pour but de clarifier le rôle de chaque script et de fournir des instructions claires sur leur utilisation.

## Philosophie

La plupart des scripts de haut niveau dans ce répertoire (ex: `setup_manager.py`, `maintenance_manager.py`) agissent comme des **points d'entrée** ou des **façades**. Ils délèguent la logique métier complexe à des modules dédiés situés dans le répertoire `project_core/`. Cette approche permet de :

- **Simplifier les points d'entrée** : Les scripts restent légers et faciles à comprendre.
- **Centraliser la logique métier** : La complexité est gérée dans `project_core`, favorisant la réutilisabilité et la maintenabilité.
- **Améliorer la testabilité** : La logique dans `project_core` peut être testée unitairement de manière plus robuste.

---

##  Scripts de Lancement Principaux

Ces scripts sont utilisés pour démarrer les composants clés de l'application.

### Lancement du Backend pour les Tests End-to-End

Utilisé pour démarrer le serveur API nécessaire à l'exécution de la suite de tests E2E.

- **Script** : `run_e2e_backend.py`
- **Rôle** : Lance un serveur Uvicorn sur le port `5003` qui sert l'application web définie dans `argumentation_analysis.services.web_api.app`.
- **Exemple d'utilisation** :
  ```bash
  python scripts/run_e2e_backend.py
  ```

---

## Gestionnaires de Scripts (CLI)

Ces scripts fournissent des interfaces en ligne de commande (CLI) pour exécuter une variété de tâches de configuration, de maintenance et de test.

### 1. Gestionnaire de Configuration (`setup_manager.py`)

Ce script est le point d'entrée unique pour toutes les opérations de configuration et de validation de l'environnement du projet.

- **Script** : `setup_manager.py`
- **Délègue à** : `project_core.core_from_scripts.project_setup`
- **Rôle** : Gère l'installation des dépendances, la configuration des environnements (`.env`), et la validation de la configuration système.
- **Exemples de commandes** :
  ```bash
  # Installer toutes les dépendances requises
  python scripts/setup_manager.py install

  # Configurer l'environnement pour les tests
  python scripts/setup_manager.py setup --env test

  # Valider l'ensemble de la configuration
  python scripts/setup_manager.py validate --all
  ```

### 2. Gestionnaire de Maintenance (`maintenance_manager.py`)

Ce script fournit un ensemble d'outils pour la maintenance courante du projet, du nettoyage du code à la gestion du référentiel Git.

- **Script** : `maintenance_manager.py`
- **Délègue à** :
    - `project_core.core_from_scripts.cleanup_manager`
    - `project_core.core_from_scripts.environment_manager`
    - `project_core.core_from_scripts.organization_manager`
    - `project_core.core_from_scripts.repository_manager`
    - `project_core.core_from_scripts.refactoring_manager`
- **Rôle** : Offre des commandes pour le refactoring, le nettoyage, la gestion des environnements et du dépôt.
- **Exemples de commandes** :
    ```bash
    # Nettoyer les fichiers et répertoires temporaires
    python scripts/maintenance_manager.py cleanup --default

    # Basculer l'environnement .env principal vers la configuration de 'production'
    python scripts/maintenance_manager.py env --switch-to production

    # Trouver les fichiers non suivis par Git (orphelins)
    python scripts/maintenance_manager.py repo find-orphans

    # Appliquer un plan de refactoring défini dans un fichier JSON
    python scripts/maintenance_manager.py refactor --plan ./path/to/your/refactoring-plan.json
    ```

---
*Ce document doit être maintenu à jour à chaque ajout ou modification de script.*