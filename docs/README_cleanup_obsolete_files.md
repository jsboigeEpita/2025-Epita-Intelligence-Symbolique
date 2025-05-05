# Script de nettoyage des fichiers obsolètes

Ce script permet de gérer la suppression sécurisée des fichiers obsolètes du projet, dont les fonctionnalités ont été migrées vers la nouvelle architecture.

## Contexte

Suite à la refactorisation du code et à la migration des fonctionnalités vers la nouvelle architecture, certains fichiers sont devenus obsolètes. Ce script permet de :

1. Sauvegarder ces fichiers dans un répertoire d'archives avant suppression
2. Vérifier que la sauvegarde est complète et valide
3. Supprimer les fichiers obsolètes de leur emplacement d'origine
4. Générer un rapport détaillé des opérations effectuées
5. Restaurer les fichiers si nécessaire

## Fichiers concernés

Les fichiers obsolètes identifiés sont :

1. Scripts d'extraction refactorisés :
   - `argumentiation_analysis/utils/extract_repair/repair_extract_markers.py`
   - `argumentiation_analysis/utils/extract_repair/verify_extracts.py`
   - `argumentiation_analysis/utils/extract_repair/fix_missing_first_letter.py`
   - `argumentiation_analysis/utils/extract_repair/verify_extracts_with_llm.py`
   - `argumentiation_analysis/utils/extract_repair/repair_extract_markers.ipynb`

2. Utilitaires remplacés par des services :
   - `argumentiation_analysis/ui/extract_utils.py`

## Utilisation

### Installation

Aucune installation particulière n'est nécessaire. Le script utilise uniquement des modules Python standards.

### Exécution de base

```bash
python cleanup_obsolete_files.py
```

Cette commande va :
1. Créer un répertoire d'archives avec horodatage
2. Sauvegarder les fichiers obsolètes
3. Vérifier l'intégrité de la sauvegarde
4. Supprimer les fichiers obsolètes
5. Générer un rapport de suppression

### Options disponibles

Le script propose plusieurs options pour contrôler son comportement :

| Option | Description |
|--------|-------------|
| `--dry-run` | Simule les opérations sans effectuer de modifications réelles |
| `--no-backup` | Supprime les fichiers sans sauvegarde (nécessite `--force`) |
| `--restore` | Restaure les fichiers depuis les archives |
| `--list` | Liste les fichiers obsolètes et leur statut sans effectuer d'actions |
| `--force` | Force la suppression même en cas d'erreur de sauvegarde |
| `--verbose` | Affiche des informations détaillées pendant l'exécution |

### Exemples d'utilisation

#### Simulation (dry-run)

Pour simuler l'exécution sans effectuer de modifications :

```bash
python cleanup_obsolete_files.py --dry-run
```

#### Lister les fichiers obsolètes

Pour simplement lister les fichiers obsolètes et leur statut :

```bash
python cleanup_obsolete_files.py --list
```

#### Suppression avec logs détaillés

Pour effectuer la suppression avec des logs détaillés :

```bash
python cleanup_obsolete_files.py --verbose
```

#### Restauration des fichiers

Pour restaurer les fichiers depuis la sauvegarde la plus récente :

```bash
python cleanup_obsolete_files.py --restore
```

#### Suppression sans sauvegarde (déconseillé)

Pour supprimer les fichiers sans sauvegarde (à utiliser avec précaution) :

```bash
python cleanup_obsolete_files.py --no-backup --force
```

## Structure des archives

Les archives sont organisées comme suit :

```
_archives/
  └── backup_YYYYMMDD_HHMMSS/
      ├── metadata.json
      ├── rapport_suppression_YYYYMMDD_HHMMSS.md
      └── argumentiation_analysis/
          ├── ui/
          │   └── extract_utils.py
          └── utils/
              └── extract_repair/
                  ├── repair_extract_markers.py
                  ├── verify_extracts.py
                  ├── fix_missing_first_letter.py
                  ├── verify_extracts_with_llm.py
                  └── repair_extract_markers.ipynb
```

- Le fichier `metadata.json` contient les métadonnées de chaque fichier (chemin, taille, hash, etc.)
- Le rapport de suppression (`rapport_suppression_YYYYMMDD_HHMMSS.md`) fournit un résumé des opérations effectuées
- La structure des répertoires est préservée pour faciliter la restauration

## Mécanismes de sécurité

Le script intègre plusieurs mécanismes de sécurité :

1. **Vérification de l'intégrité** : Calcul et vérification des hash SHA-256 avant et après sauvegarde
2. **Mode simulation** : Option `--dry-run` pour tester sans modifier les fichiers
3. **Rapport détaillé** : Génération d'un rapport complet des opérations effectuées
4. **Restauration** : Possibilité de restaurer les fichiers supprimés
5. **Confirmation forcée** : L'option `--no-backup` nécessite l'option `--force` pour confirmation

## Logs

Le script génère des logs détaillés dans :
- La console (stdout)
- Un fichier `cleanup_obsolete_files.log`

Ces logs permettent de suivre toutes les opérations effectuées et d'identifier d'éventuels problèmes.

## Bonnes pratiques

1. **Toujours exécuter en mode simulation d'abord** :
   ```bash
   python cleanup_obsolete_files.py --dry-run
   ```

2. **Vérifier les fichiers concernés** :
   ```bash
   python cleanup_obsolete_files.py --list
   ```

3. **Conserver les archives** : Ne pas supprimer le répertoire `_archives` après l'opération

4. **Vérifier le rapport** : Consulter le rapport de suppression généré pour s'assurer que tout s'est bien passé