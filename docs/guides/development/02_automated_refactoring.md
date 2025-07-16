# Guide: Refactorisation Automatisée avec des Plans

Ce guide explique comment utiliser le moteur de refactorisation basé sur des plans pour appliquer des transformations de code à grande échelle sur le projet.

## 1. Principe de Fonctionnement

Le moteur de refactorisation, accessible via la commande `maintenance_manager.py refactor`, utilise un fichier JSON (un "plan") pour définir une série de transformations à appliquer au code source. Cela permet d'automatiser des tâches de migration de code, comme la mise à jour des imports ou le renommage de fonctions, de manière contrôlée et reproductible.

## 2. Comment Écrire un Plan de Refactorisation

Un plan est un fichier JSON contenant une clé `transformations`, qui est une liste d'objets. Chaque objet représente une action de refactorisation.

### 2.1 Structure d'un Plan

```json
{
  "transformations": [
    {
      "action": "update_import",
      "old_path": "ancien.module.chemin",
      "new_path": "nouveau.module.chemin"
    },
    {
      "action": "rename_function",
      "old_name": "ancienne_fonction",
      "new_name": "nouvelle_fonction"
    }
  ]
}
```

### 2.2 Actions Disponibles

#### `update_import`

Change un chemin d'import dans tous les fichiers Python du projet.

*   **`action`**: `update_import`
*   **`old_path`**: Le chemin d'import complet à remplacer (ex: `a.b.c`).
*   **`new_path`**: Le nouveau chemin d'import (ex: `x.y.z`).

#### `rename_function`

Renomme un appel de fonction.

*   **`action`**: `rename_function`
*   **`old_name`**: Le nom de la fonction à renommer.
*   **`new_name`**: Le nouveau nom de la fonction.

## 3. Comment Utiliser la Commande `refactor`

La commande se trouve dans `scripts/maintenance_manager.py`.

### Syntaxe

```bash
python scripts/maintenance_manager.py refactor --plan <chemin_vers_le_plan.json> [--dry-run]
```

### Arguments

*   `--plan <chemin_vers_le_plan.json>`: (Obligatoire) Spécifie le chemin vers le fichier de plan de refactorisation JSON.
*   `--dry-run`: (Optionnel) Si cet indicateur est présent, le script affichera les modifications qui seraient apportées (un `diff`) sans modifier réellement les fichiers. C'est très utile pour vérifier l'impact d'un plan avant de l'appliquer.

### Exemple d'Utilisation

1.  **Créer un plan `my_refactor_plan.json`:**
    ```json
    {
      "transformations": [
        {
          "action": "update_import",
          "old_path": "os.path",
          "new_path": "pathlib"
        }
      ]
    }
    ```
2.  **Lancer en mode `dry-run` pour prévisualiser:**
    ```bash
    python scripts/maintenance_manager.py refactor --plan my_refactor_plan.json --dry-run
    ```
3.  **Appliquer les changements:**
    ```bash
    python scripts/maintenance_manager.py refactor --plan my_refactor_plan.json