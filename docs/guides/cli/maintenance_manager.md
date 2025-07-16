# Guide d'Utilisation : Maintenance Manager

Le `maintenance_manager.py` est un outil CLI puissant pour vous aider à maintenir la propreté, la cohérence et la qualité de votre projet.

## Commandes Disponibles

### `repo` : Opérations sur le Dépôt

Cette commande groupe les actions liées à la gestion du dépôt Git.

#### `repo update-gitignore`

Met à jour le fichier `.gitignore` à la racine du projet en se basant sur un template central.

**Usage :**

```bash
python scripts/maintenance_manager.py repo update-gitignore
```

**Description :**

Cette commande lit le template situé dans `project_core/templates/project.gitignore.template` et ajoute toutes les règles manquantes au fichier `.gitignore` de votre projet. C'est un excellent moyen de s'assurer que tous les fichiers non pertinents sont correctement ignorés par Git.

---

## Commande `refactor`

Cette commande permet d'appliquer des transformations de code automatisées.

### Syntaxe

```bash
python scripts/maintenance_manager.py refactor --plan <plan.json> [--dry-run]
```

### Options

*   `--plan <plan.json>`: **(Obligatoire)** Chemin vers le fichier JSON contenant le plan de refactorisation.
*   `--dry-run`: (Optionnel) Affiche les modifications sans les appliquer.

Pour des détails sur la création de plans de refactorisation, consultez le [guide de refactorisation automatisée](../development/02_automated_refactoring.md).