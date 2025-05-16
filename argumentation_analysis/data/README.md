# Répertoire de données pour l'analyse d'argumentation

Ce répertoire contient les données utilisées par le système d'analyse d'argumentation, notamment les extraits de texte chiffrés et d'autres ressources nécessaires à l'analyse rhétorique.

## Contenu du répertoire

### Fichiers principaux

- **`extract_sources.json.gz.enc`**: Fichier chiffré contenant les définitions d'extraits de texte pour l'analyse rhétorique. Ce fichier est essentiel au fonctionnement du système.

### Structure du fichier extract_sources.json.gz.enc

Ce fichier est:
1. Un fichier JSON contenant des définitions d'extraits
2. Compressé avec gzip (.gz)
3. Chiffré avec une clé symétrique (.enc)

Une fois déchiffré et décompressé, il contient une liste de sources avec leurs extraits associés, utilisés pour l'analyse rhétorique.

## Utilisation

### Accès au fichier chiffré

Pour manipuler ce fichier, utilisez les fonctions fournies dans `argumentation_analysis/ui/extract_utils.py`:

```python
from argumentation_analysis.ui.extract_utils import load_extract_definitions_safely
from argumentation_analysis.ui.config import ENCRYPTION_KEY, CONFIG_FILE, CONFIG_FILE_JSON

# Charger les définitions d'extraits
extract_definitions, message = load_extract_definitions_safely(CONFIG_FILE, ENCRYPTION_KEY, CONFIG_FILE_JSON)
```

### Clé de chiffrement

La clé de chiffrement est définie dans `argumentation_analysis/ui/config.py` ou via des variables d'environnement. Consultez le fichier `.env.example` pour plus d'informations.

## Documentation détaillée

Pour une documentation complète sur le fichier `extract_sources.json.gz.enc`, son format, son rôle dans le système et comment l'utiliser efficacement, consultez:

- [Documentation des extraits chiffrés](../../docs/extraits_chiffres.md)

## Sécurité

Ce répertoire contient des données sensibles qui sont chiffrées pour des raisons de sécurité. Veuillez respecter les bonnes pratiques suivantes:

1. Ne jamais committer la clé de chiffrement dans le dépôt
2. Ne pas déchiffrer les données sensibles inutilement
3. Ne pas distribuer les données déchiffrées
4. Suivre les protocoles de sécurité définis pour le projet

## Maintenance

### Sauvegarde

Il est recommandé de sauvegarder régulièrement ce fichier, car il contient des définitions d'extraits qui peuvent être difficiles à recréer.

### Mise à jour

Pour mettre à jour les définitions d'extraits:

```python
from argumentation_analysis.ui.extract_utils import load_extract_definitions_safely, save_extract_definitions_safely
from argumentation_analysis.ui.config import ENCRYPTION_KEY, CONFIG_FILE, CONFIG_FILE_JSON

# Charger les définitions existantes
extract_definitions, _ = load_extract_definitions_safely(CONFIG_FILE, ENCRYPTION_KEY, CONFIG_FILE_JSON)

# Modifier les définitions...

# Sauvegarder les définitions mises à jour
success, message = save_extract_definitions_safely(extract_definitions, CONFIG_FILE, ENCRYPTION_KEY, CONFIG_FILE_JSON)
```

### Réparation

Si les extraits définis dans ce fichier présentent des problèmes (marqueurs introuvables, etc.), utilisez l'outil de réparation:

```bash
python argumentation_analysis/run_extract_repair.py --save