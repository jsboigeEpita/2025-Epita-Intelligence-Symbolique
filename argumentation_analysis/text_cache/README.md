# Répertoire de cache de textes

Ce répertoire est utilisé pour stocker en cache les textes traités par le système d'analyse d'argumentation.

## Objectif

Le répertoire `text_cache` sert à :
- Mettre en cache les textes analysés pour éviter de les retraiter
- Stocker temporairement des extraits de texte pendant l'analyse
- Conserver des versions intermédiaires de textes transformés
- Améliorer les performances en évitant de répéter des opérations coûteuses

## Structure du répertoire

Le répertoire contient actuellement uniquement un fichier `.gitkeep` pour maintenir le répertoire dans le dépôt Git. En fonctionnement normal, il contiendra :
- Des fichiers texte mis en cache
- Des fichiers JSON contenant des métadonnées sur les textes
- Des fichiers de cache avec des identifiants uniques

## Utilisation

Le cache de textes est utilisé par plusieurs composants du système :
- Les outils d'analyse rhétorique
- Les modules de traitement de texte
- Les utilitaires de réparation d'extraits

Exemple d'utilisation dans le code :

```python
from pathlib import Path
import hashlib
import json

def get_cached_text(text_id, cache_dir=None):
    """Récupère un texte depuis le cache s'il existe."""
    if cache_dir is None:
        cache_dir = Path(__file__).parent.parent / "text_cache"
    
    cache_file = cache_dir / f"{text_id}.json"
    
    if cache_file.exists():
        with open(cache_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def cache_text(text_id, text_data, cache_dir=None):
    """Met en cache un texte pour une utilisation ultérieure."""
    if cache_dir is None:
        cache_dir = Path(__file__).parent.parent / "text_cache"
    
    cache_file = cache_dir / f"{text_id}.json"
    
    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump(text_data, f, ensure_ascii=False, indent=2)
```

## Maintenance

Le cache de textes peut être nettoyé périodiquement pour libérer de l'espace disque. Les fichiers de cache sont temporaires et peuvent être supprimés en toute sécurité si nécessaire.

## Liens vers la documentation connexe

- [Utilitaires de réparation d'extraits](../utils/extract_repair/README.md)
- [Utilitaires système](../utils/README.md)