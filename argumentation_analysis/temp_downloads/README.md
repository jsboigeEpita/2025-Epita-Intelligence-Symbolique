# Répertoire de téléchargements temporaires

Ce répertoire est utilisé pour stocker temporairement les fichiers téléchargés par le système d'analyse d'argumentation.

## Objectif

Le répertoire `temp_downloads` sert de zone de stockage temporaire pour :
- Les fichiers téléchargés depuis des sources externes
- Les données intermédiaires générées pendant le traitement
- Les ressources temporaires nécessaires à l'analyse

## Utilisation

Ce répertoire est automatiquement utilisé par différents composants du système, notamment :
- Les modules de récupération de données
- Les outils d'analyse qui nécessitent des téléchargements
- Les scripts qui traitent des ressources externes

## Maintenance

Ce répertoire est conçu pour contenir uniquement des fichiers temporaires qui peuvent être supprimés en toute sécurité lorsqu'ils ne sont plus nécessaires. Quelques points importants :

- Les fichiers dans ce répertoire sont considérés comme temporaires et peuvent être supprimés à tout moment
- Le répertoire est automatiquement nettoyé périodiquement par le système
- Ne pas stocker de données importantes ou permanentes dans ce répertoire
- Le fichier `.gitkeep` est le seul fichier qui doit rester de façon permanente (pour maintenir le répertoire dans le dépôt Git)

## Bonnes pratiques

Lors de l'utilisation de ce répertoire dans le code :

```python
import os
from pathlib import Path

# Obtenir le chemin du répertoire temp_downloads
temp_dir = Path(__file__).parent.parent / "temp_downloads"

# Créer un fichier temporaire avec un nom unique
temp_file_path = os.path.join(temp_dir, f"temp_data_{unique_id}.json")

# Après utilisation, supprimer le fichier temporaire
if os.path.exists(temp_file_path):
    os.remove(temp_file_path)
```

## Liens vers la documentation connexe

- [Utilitaires système](../utils/README.md)
- [Scripts d'exécution](../../scripts/execution/README.md)