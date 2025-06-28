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

### `cleanup`

Commandes pour nettoyer le projet des fichiers et répertoires temporaires.

#### `cleanup --default`

Supprime les fichiers et répertoires temporaires courants générés par Python et `pytest`. La commande cible spécifiquement :
- Les répertoires `__pycache__`
- Les répertoires `.pytest_cache`
- Les fichiers se terminant par `.pyc`

Elle parcourt l'ensemble du projet depuis la racine et supprime les éléments correspondants, en ignorant les liens symboliques pour éviter les erreurs.

**Usage :**
```bash
python scripts/maintenance_manager.py cleanup --default
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
|
#### `organize --apply-plan <plan.json>`
|
Applique une série d'opérations de système de fichiers (suppression, déplacement) définies dans un fichier JSON.
|
**Usage :**
```bash
python scripts/maintenance_manager.py organize --apply-plan mon_plan.json
```
|
**Format du Fichier de Plan :**
Le fichier de plan doit être un JSON contenant une clé `"actions"`. Chaque action est un objet avec une `action` et des chemins.
|
```json
{
  "actions": [
    {
      "action": "delete",
      "path": "path/relative/au/projet/a_supprimer.log"
    },
    {
      "action": "move",
      "source": "path/source",
      "destination": "path/destination"
    }
  ]
}
```
|
### Workflow Complet : Nettoyage des Fichiers Orphelins
|
Ces commandes sont conçues pour fonctionner ensemble afin de faciliter le nettoyage des fichiers non suivis.
|
**Étape 1 : Générer le rapport des fichiers orphelins**
|
Utilisez `repo find-orphans` et redirigez la sortie pour créer une première ébauche de plan. Vous pouvez ensuite éditer ce fichier.
|
```bash
# Crée un rapport simple des fichiers.
# Pour une utilisation avancée, un script pourrait générer directement le JSON.
python scripts/maintenance_manager.py repo find-orphans > rapport_orphelins.txt
```
|
**Étape 2 : Créer ou éditer le plan d'action JSON**
|
À partir du rapport, créez un fichier `plan.json` avec les actions `delete` ou `move` que vous souhaitez effectuer.
|
**Étape 3 : Appliquer le plan**
|
Exécutez le plan pour nettoyer le projet.
|
```bash
python scripts/maintenance_manager.py organize --apply-plan plan.json
```

---