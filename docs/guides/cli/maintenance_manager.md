# Guide d'Utilisation : Maintenance Manager CLI

Le `maintenance_manager.py` est un outil en ligne de commande conçu pour vous aider à maintenir la propreté et la cohérence de votre projet.

## Commandes Disponibles

### `repo`

Commandes relatives à la gestion du dépôt Git.

#### `repo find-orphans`

Identifie les fichiers présents dans votre répertoire de travail mais qui ne sont pas suivis par Git.

**Usage :**
```bash
python scripts/maintenance_manager.py repo find-orphans
```

---

### `organize`

Commandes pour réorganiser les répertoires du projet.

#### `organize --target results`

Cette commande déclenche une réorganisation complète du répertoire `results/`. Le processus est le suivant :

1.  **Archivage** : Le contenu actuel de `results/` est déplacé dans un nouveau sous-répertoire horodaté à l'intérieur de `results_archive/`.
2.  **Création d'une nouvelle structure** : Un nouveau répertoire `results/` vide est créé.
3.  **Organisation** : Les fichiers de l'archive sont parcourus. Selon des règles prédéfinies (par exemple, basées sur l'extension du fichier), ils sont déplacés dans des sous-répertoires thématiques (`images`, `logs`, etc.) dans le nouveau `results/`.
4.  **Rapport** : Un fichier `README.md` est généré à la racine de `results/`, résumant les opérations qui ont été effectuées.

**Usage :**
```bash
python scripts/maintenance_manager.py organize --target results
```

---
*D'autres commandes seront documentées ici au fur et à mesure de leur implémentation.*