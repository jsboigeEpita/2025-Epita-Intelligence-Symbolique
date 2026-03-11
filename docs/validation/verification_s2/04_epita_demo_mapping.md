# Documentation de Vérification du Système "Démo EPITA"

## Partie 1 : Rapport de Cartographie (Mapping)

**Date :** 25/06/2025
**Auteur :** Roo
**Version :** 1.0

### 1. Introduction

Ce document a pour objectif de réaliser une cartographie a posteriori du système "Démo EPITA". L'analyse se base sur le code source fonctionnel après correction, afin de reconstituer la logique et l'architecture du système tel qu'il opère actuellement. L'objectif est de fournir une vue d'ensemble claire des composants, de leurs interactions et des flux de données.

### 2. Architecture Générale

Le système est une application console en Python conçue pour présenter différentes démonstrations techniques de manière modulaire.

- **Orchestrateur Principal :** Le script [`demonstration_epita.py`](../../examples/scripts_demonstration/demonstration_epita.py) agit comme le point d'entrée et l'orchestrateur. Il est responsable de :
    - L'initialisation de l'environnement (gestion des chemins).
    - L'analyse des arguments de la ligne de commande.
    - Le chargement de la configuration des démonstrations.
    - L'affichage d'un menu interactif pour la sélection des modules.
    - Le chargement et l'exécution dynamiques du module de démonstration choisi.

- **Configuration :** Le fichier [`demo_categories.yaml`](../../examples/scripts_demonstration/configs/demo_categories.yaml) définit la structure hiérarchique des démonstrations, incluant les catégories, leurs icônes, descriptions et le nom du module Python associé.

- **Modules de Démonstration :** Les modules se trouvent dans le répertoire `examples/scripts_demonstration/modules/`. Chaque module est un script Python indépendant qui expose une fonction `demonstrate()` servant de point d'entrée pour l'orchestrateur.

### 3. Flux d'Exécution

1.  **Lancement :** L'utilisateur exécute [`demonstration_epita.py`](../../examples/scripts_demonstration/demonstration_epita.py).
2.  **Initialisation :**
    - Le script ajoute la racine du projet au `sys.path` pour garantir la stabilité des imports absolus.
    - Le répertoire de travail est défini à la racine du projet.
3.  **Chargement de la Configuration :** Le contenu de `demo_categories.yaml` est chargé en mémoire.
4.  **Menu Interactif :**
    - Une liste des catégories de démonstration disponibles est présentée à l'utilisateur.
    - L'utilisateur sélectionne une catégorie via une saisie numérique.
5.  **Sélection et Chargement du Module :**
    - Le nom du module Python correspondant à la catégorie sélectionnée est récupéré depuis la configuration.
    - **Correction Spécifique (Patch) :** Une modification manuelle du code force l'utilisation du module `demo_analyse_argumentation` pour la catégorie `agents_logiques`, outrepassant la valeur (potentiellement erronée) du fichier YAML.
    - Le module est importé dynamiquement en utilisant `importlib.import_module()`.
6.  **Exécution :** La fonction `demonstrate()` du module chargé est appelée, lançant la démonstration spécifique.

### 4. Cartographie des Composants

| Composant                                                                | Type          | Rôle                                                                                                                       | Dépendances                                                              |
| ------------------------------------------------------------------------ | ------------- | -------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| `demonstration_epita.py`                                                 | Orchestrateur | Point d'entrée, gestion du menu, chargement et exécution des modules.                                                      | `PyYAML`, `argparse`, `importlib`, `os`, `sys`, `pathlib`                  |
| `configs/demo_categories.yaml`                                           | Configuration | Définit la structure des menus et la correspondance entre les catégories et les noms de modules.                           | -                                                                        |
| `modules/`                                                               | Répertoire    | Contient l'ensemble des scripts de démonstration modulaires.                                                               | -                                                                        |
| `modules/demo_*.py` (ex: `demo_analyse_argumentation.py`)                 | Module        | Implémente une démonstration spécifique. Doit contenir une fonction `demonstrate()`.                                       | Variable (selon les besoins de la démo)                                  |