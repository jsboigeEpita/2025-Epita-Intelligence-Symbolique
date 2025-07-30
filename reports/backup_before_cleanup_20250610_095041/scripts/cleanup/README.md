# Scripts de nettoyage

Ce répertoire contient les scripts de nettoyage du projet d'analyse argumentative.

## Scripts disponibles

### 1. cleanup_project.py

Script de nettoyage complet du projet qui effectue les opérations suivantes :
- Suppression des fichiers temporaires (*.pyc, __pycache__, etc.)
- Suppression des fichiers de logs obsolètes
- Création du répertoire `data` s'il n'existe pas
- Mise à jour du fichier `.gitignore`
- Suppression des rapports obsolètes
- Vérification que les fichiers sensibles ne sont pas suivis par Git

**Utilisation :**
```bash
python scripts/cleanup/cleanup_project.py
```

### 2. cleanup_obsolete_files.py

Script pour gérer la suppression sécurisée des fichiers obsolètes du projet, dont les fonctionnalités ont été migrées vers la nouvelle architecture. Ce script permet de :
- Sauvegarder les fichiers obsolètes dans un répertoire d'archives avant suppression
- Vérifier que la sauvegarde est complète et valide
- Supprimer les fichiers obsolètes de leur emplacement d'origine
- Générer un rapport de suppression
- Restaurer les fichiers supprimés si nécessaire

**Options disponibles :**
- `--dry-run` : Simule les opérations sans effectuer de modifications
- `--no-backup` : Supprime les fichiers sans sauvegarde (déconseillé)
- `--restore` : Restaure les fichiers depuis les archives
- `--list` : Liste les fichiers obsolètes sans effectuer d'actions
- `--force` : Force la suppression même en cas d'erreur de sauvegarde
- `--verbose` : Affiche des informations détaillées pendant l'exécution

**Utilisation :**
```bash
# Simulation (dry-run)
python scripts/cleanup/cleanup_obsolete_files.py --dry-run

# Lister les fichiers obsolètes
python scripts/cleanup/cleanup_obsolete_files.py --list

# Suppression avec logs détaillés
python scripts/cleanup/cleanup_obsolete_files.py --verbose

# Restauration des fichiers
python scripts/cleanup/cleanup_obsolete_files.py --restore
```

### 3. cleanup_repository.py

Script de nettoyage du dépôt Git qui effectue les opérations suivantes :
- Création d'un fichier `.env.example` comme modèle
- Suppression des dossiers vides qui ne devraient pas être versionnés
- Suppression des fichiers temporaires Python du suivi Git
- Vérification que les fichiers sensibles comme `.env` sont bien ignorés par Git

**Utilisation :**
```bash
python scripts/cleanup/cleanup_repository.py
```

## Bonnes pratiques

1. **Exécuter les scripts depuis la racine du projet** pour garantir que les chemins relatifs fonctionnent correctement.
2. **Toujours exécuter en mode simulation d'abord** avec l'option `--dry-run` pour les scripts qui la supportent.
3. **Vérifier les fichiers concernés** avant de procéder à des suppressions.
4. **Conserver les archives** générées par `cleanup_obsolete_files.py` pour pouvoir restaurer les fichiers si nécessaire.
## Choix Technologiques (Python vs PowerShell)

Les scripts de ce répertoire utilisent une combinaison de Python (.py) et de PowerShell (.ps1) :

- **PowerShell** est utilisé pour des opérations de nettoyage qui peuvent impliquer des commandes système directes ou la manipulation de fichiers/répertoires où PowerShell offre une syntaxe pratique (ex: `clean_project.ps1` pour certaines opérations de suppression globales, `cleanup_old_agent_dirs.ps1`).
- **Python** est privilégié pour les scripts de nettoyage qui nécessitent une logique plus élaborée, comme la lecture et la modification de fichiers de configuration, l'analyse de contenu de fichiers, ou des opérations conditionnelles complexes sur la structure du projet (ex: `cleanup_obsolete_files.py`, `cleanup_repository.py`, `reorganize_project.py`). Python offre de meilleures bibliothèques pour la manipulation de structures de données (JSON, etc.) et une logique de script plus avancée.

Le choix est fait au cas par cas pour utiliser l'outil le plus adapté à la tâche spécifique du script de nettoyage.