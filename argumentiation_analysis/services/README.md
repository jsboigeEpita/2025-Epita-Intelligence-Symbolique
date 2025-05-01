# Package Services

Ce package contient les services centralisés utilisés dans le projet d'analyse d'argumentation. Les services fournissent des fonctionnalités réutilisables pour manipuler les extraits, accéder aux sources, et gérer les données.

## Structure

```
services/
├── __init__.py
├── cache_service.py
├── crypto_service.py
├── definition_service.py
├── extract_service.py
├── fetch_service.py
└── README.md
```

## Services disponibles

### CacheService (cache_service.py)

Service de mise en cache des textes sources pour éviter de les télécharger ou de les lire à chaque fois. Améliore les performances et réduit la charge sur les serveurs externes.

#### Fonctionnalités principales
- Mise en cache des textes sources
- Vérification de la fraîcheur du cache
- Gestion du répertoire de cache

#### Exemple d'utilisation
```python
from argumentiation_analysis.services.cache_service import CacheService
from pathlib import Path

# Initialiser le service de cache
cache_dir = Path("./text_cache")
cache_service = CacheService(cache_dir)

# Vérifier si un texte est en cache
url = "https://example.com/texte"
if cache_service.is_cached(url):
    # Récupérer le texte depuis le cache
    text = cache_service.get_cached_text(url)
else:
    # Télécharger le texte et le mettre en cache
    text = download_text(url)
    cache_service.cache_text(url, text)
```

### CryptoService (crypto_service.py)

Service de chiffrement et déchiffrement des données sensibles, notamment les définitions d'extraits.

#### Fonctionnalités principales
- Chiffrement de fichiers et de données
- Déchiffrement de fichiers et de données
- Gestion des clés de chiffrement

#### Exemple d'utilisation
```python
from argumentiation_analysis.services.crypto_service import CryptoService

# Initialiser le service de chiffrement avec une clé
encryption_key = "clé_secrète"
crypto_service = CryptoService(encryption_key)

# Chiffrer des données
data = "Données sensibles"
encrypted_data = crypto_service.encrypt_data(data)

# Déchiffrer des données
decrypted_data = crypto_service.decrypt_data(encrypted_data)

# Chiffrer un fichier
crypto_service.encrypt_file("fichier.json", "fichier.json.enc")

# Déchiffrer un fichier
crypto_service.decrypt_file("fichier.json.enc", "fichier_déchiffré.json")
```

### DefinitionService (definition_service.py)

Service de gestion des définitions d'extraits, permettant de charger, manipuler et sauvegarder les définitions.

#### Fonctionnalités principales
- Chargement des définitions depuis un fichier chiffré
- Sauvegarde des définitions dans un fichier chiffré
- Exportation des définitions au format JSON pour vérification

#### Exemple d'utilisation
```python
from argumentiation_analysis.services.definition_service import DefinitionService
from argumentiation_analysis.services.crypto_service import CryptoService
from pathlib import Path

# Initialiser les services
crypto_service = CryptoService("clé_secrète")
definition_service = DefinitionService(
    crypto_service=crypto_service,
    config_file=Path("extract_sources.json.gz.enc"),
    fallback_file=Path("extract_sources.json")
)

# Charger les définitions
extract_definitions, error_message = definition_service.load_definitions()
if error_message:
    print(f"Avertissement: {error_message}")

# Manipuler les définitions
# ...

# Sauvegarder les définitions
success, error_message = definition_service.save_definitions(extract_definitions)
if success:
    print("Définitions sauvegardées avec succès")
else:
    print(f"Erreur: {error_message}")

# Exporter les définitions au format JSON pour vérification
success, message = definition_service.export_definitions_to_json(
    extract_definitions, Path("extract_sources_updated.json")
)
print(message)
```

### ExtractService (extract_service.py)

Service d'extraction de texte à partir de sources en utilisant des marqueurs de début et de fin.

#### Fonctionnalités principales
- Extraction de texte avec des marqueurs
- Recherche de texte similaire pour la réparation des bornes
- Création de résultats d'extraction

#### Exemple d'utilisation
```python
from argumentiation_analysis.services.extract_service import ExtractService

# Initialiser le service d'extraction
extract_service = ExtractService()

# Extraire du texte avec des marqueurs
source_text = "Texte source contenant un DÉBUT_EXTRAIT extrait à extraire FIN_EXTRAIT."
extracted_text, status, start_found, end_found = extract_service.extract_text_with_markers(
    source_text, "DÉBUT_EXTRAIT", "FIN_EXTRAIT", None
)

if start_found and end_found:
    print(f"Extraction réussie: {extracted_text}")
else:
    print(f"Échec de l'extraction: {status}")

# Rechercher du texte similaire pour la réparation des bornes
similar_texts = extract_service.find_similar_text(
    source_text, "DÉBUT", context_size=20, max_results=3
)
for context, position, found_text in similar_texts:
    print(f"Texte similaire trouvé à la position {position}: {found_text}")
    print(f"Contexte: {context}")
```

### FetchService (fetch_service.py)

Service de récupération de texte à partir de différentes sources (URL, fichiers, etc.).

#### Fonctionnalités principales
- Récupération de texte à partir d'URL
- Récupération de texte à partir de fichiers
- Utilisation du cache pour optimiser les performances

#### Exemple d'utilisation
```python
from argumentiation_analysis.services.fetch_service import FetchService
from argumentiation_analysis.services.cache_service import CacheService
from pathlib import Path

# Initialiser les services
cache_service = CacheService(Path("./text_cache"))
fetch_service = FetchService(
    cache_service=cache_service,
    temp_download_dir=Path("./temp_downloads")
)

# Récupérer du texte à partir d'une source
source_dict = {
    "source_type": "url",
    "source_url": "https://example.com/texte"
}
text, url = fetch_service.fetch_text(source_dict)

if text:
    print(f"Texte récupéré depuis {url}: {text[:100]}...")
else:
    print(f"Impossible de récupérer le texte depuis {url}")
```

## Intégration avec les modèles

Ces services utilisent les modèles définis dans le package `models` pour représenter les données manipulées:

- `DefinitionService` utilise `ExtractDefinitions`, `SourceDefinition` et `Extract`
- `ExtractService` utilise `ExtractResult`

## Évolution future

Les services peuvent être étendus pour prendre en charge de nouvelles fonctionnalités:

- Support pour de nouveaux types de sources (bases de données, API, etc.)
- Amélioration des algorithmes de recherche de texte similaire
- Intégration avec des services d'analyse d'argumentation
- Optimisation des performances pour les grands corpus de texte