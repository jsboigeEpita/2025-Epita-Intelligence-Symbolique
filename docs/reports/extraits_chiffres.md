# Documentation des Extraits Chiffrés

## Vue d'ensemble

Le fichier `argumentation_analysis/data/extract_sources.json.gz.enc` est un composant central du système d'analyse rhétorique. Il contient des définitions d'extraits de texte provenant de diverses sources, y compris des contenus sensibles comme des discours d'Hitler et des débats Lincoln Douglas.

Ce document explique en détail le rôle de ce fichier, sa structure, et comment l'utiliser efficacement dans le système d'analyse rhétorique.

## Table des matières

1. [Structure et format du fichier](#structure-et-format-du-fichier)
2. [Sécurité et chiffrement](#sécurité-et-chiffrement)
3. [Rôle dans le système d'analyse rhétorique](#rôle-dans-le-système-danalyse-rhétorique)
4. [Outils de manipulation des extraits](#outils-de-manipulation-des-extraits)
5. [Réparation des extraits](#réparation-des-extraits)
6. [Exemples d'utilisation](#exemples-dutilisation)
7. [Bonnes pratiques](#bonnes-pratiques)
8. [Dépannage](#dépannage)

## Structure et format du fichier

### Format général

Le fichier `extract_sources.json.gz.enc` est un fichier JSON compressé avec gzip puis chiffré. Une fois déchiffré et décompressé, il contient une liste de définitions d'extraits au format JSON.

### Structure des données

La structure des données dans le fichier est la suivante:

```json
[
  {
    "source_name": "Nom de la source",
    "source_type": "Type de source (url, file, etc.)",
    "source_url": "URL ou chemin du fichier source (utilisé en fallback)",
    "full_text": "Contenu textuel complet de la source (optionnel, prioritaire si présent)",
    "extracts": [
      {
        "extract_name": "Nom de l'extrait",
        "start_marker": "Texte marquant le début de l'extrait",
        "end_marker": "Texte marquant la fin de l'extrait",
        "template_start": "Modèle optionnel pour le début (ex: I{0})"
      },
      // Autres extraits...
    ]
  },
  // Autres sources...
]
```

### Champs principaux

- **source_name**: Nom identifiant la source (ex: "Discours d'Hitler à Nuremberg")
- **source_type**: Type de source ("url", "file", "text")
- **source_url**: URL ou chemin d'accès au fichier source. Ce champ est maintenant utilisé comme fallback si `full_text` n'est pas fourni ou est vide.
- **full_text**: (Optionnel) Contenu textuel complet de la source. Si ce champ est présent et non vide, il est utilisé en priorité pour l'extraction des textes. Cela permet d'embarquer directement les contenus dans le fichier `extract_sources.json.gz.enc`, réduisant la dépendance aux sources externes et potentiellement améliorant les performances de récupération initiale. Ce champ peut être peuplé manuellement ou à l'aide du script [`scripts/embed_all_sources.py`](../../scripts/embed_all_sources.py).
- **extracts**: Liste des extraits définis pour cette source. Les marqueurs (`start_marker`, `end_marker`) s'appliquent au `full_text` si disponible, sinon au texte récupéré via `source_url`.

### Champs des extraits

- **extract_name**: Nom identifiant l'extrait (ex: "Passage sur la propagande")
- **start_marker**: Texte exact qui marque le début de l'extrait dans la source
- **end_marker**: Texte exact qui marque la fin de l'extrait dans la source
- **template_start**: Modèle optionnel pour le début, utilisé pour gérer les cas spéciaux comme la première lettre manquante

## Sécurité et chiffrement

### Pourquoi le chiffrement?

Le fichier est chiffré pour plusieurs raisons:
1. Protection des contenus sensibles (discours extrémistes, contenus controversés)
2. Respect des droits d'auteur pour certains textes
3. Prévention de l'utilisation abusive des extraits

### Mécanisme de chiffrement

Le chiffrement est géré par le `CryptoService` dans `argumentation_analysis/services/crypto_service.py`. Le processus utilise:
- Une clé de chiffrement symétrique
- Un algorithme de chiffrement standard (AES)
- Un vecteur d'initialisation (IV) unique

### Clé de chiffrement

La clé de chiffrement est définie dans le fichier de configuration (`argumentation_analysis/ui/config.py`) via la variable `ENCRYPTION_KEY`. Cette clé peut être:
- Définie directement dans le code (déconseillé)
- Chargée depuis une variable d'environnement (recommandé)
- Stockée dans un fichier `.env` (pour le développement)

## Rôle dans le système d'analyse rhétorique

### Fonction principale

Le fichier `extract_sources.json.gz.enc` joue plusieurs rôles essentiels:

1. **Source de vérité** pour les extraits à analyser
2. **Catalogue structuré** de passages rhétoriquement intéressants
3. **Référentiel partagé** pour tous les agents d'analyse

### Intégration dans l'architecture

Dans l'architecture hiérarchique à trois niveaux du système:

1. **Niveau stratégique**: Utilise les extraits pour planifier l'analyse globale
2. **Niveau tactique**: Coordonne l'analyse des extraits spécifiques
3. **Niveau opérationnel**: Exécute l'analyse détaillée sur chaque extrait

### Flux de travail typique

1. Chargement des définitions d'extraits depuis le fichier chiffré.
2. Pour chaque source :
    a. Vérification de la présence du champ `full_text`.
    b. Si `full_text` est présent et non vide, il est utilisé comme texte source.
    c. Sinon (si `full_text` est absent ou vide), récupération du texte source via `source_url` (mécanisme de fallback).
3. Extraction des segments de texte (définis par les `extracts` avec leurs marqueurs) à partir du texte source obtenu à l'étape 2.
4. Analyse rhétorique des extraits par différents agents spécialisés.
5. Consolidation des résultats d'analyse.

### Impact de l'intégration de `full_text`

L'ajout du champ `full_text` a plusieurs implications :

- **Taille du fichier :** Le fichier `extract_sources.json.gz.enc` peut devenir significativement plus volumineux si les textes complets de nombreuses sources y sont stockés.
- **Performances :**
    - La récupération initiale des textes sources peut être plus rapide car elle évite des accès disque ou réseau si `full_text` est utilisé.
    - Le chargement du fichier `extract_sources.json.gz.enc` lui-même peut prendre plus de temps en raison de sa taille accrue.
- **Autonomie :** Le système devient plus autonome car les textes sources peuvent être embarqués, réduisant la dépendance à la disponibilité des URLs externes ou des fichiers locaux.
- **Gestion des données :** La mise à jour des sources nécessite de mettre à jour le champ `full_text` si celui-ci est utilisé.

Pour une analyse détaillée de ces impacts, veuillez vous référer au "Rapport d'Évaluation de l'Impact" du projet.

## Outils de manipulation des extraits

### Chargement et sauvegarde

Les fonctions principales pour manipuler le fichier sont définies dans `argumentation_analysis/ui/extract_utils.py`:

- **`load_extract_definitions_safely`**: Charge les définitions d'extraits de manière sécurisée
  ```python
  from argumentation_analysis.ui.extract_utils import load_extract_definitions_safely
  from argumentation_analysis.ui.config import ENCRYPTION_KEY, CONFIG_FILE, CONFIG_FILE_JSON
  
  extract_definitions, message = load_extract_definitions_safely(CONFIG_FILE, ENCRYPTION_KEY, CONFIG_FILE_JSON)
  ```

- **`save_extract_definitions_safely`**: Sauvegarde les définitions d'extraits de manière sécurisée
  ```python
  from argumentation_analysis.ui.extract_utils import save_extract_definitions_safely
  
  # Note: La fonction save_extract_definitions_safely sauvegarde les définitions telles quelles.
  # Pour forcer l'embarquement des textes sources complets lors de la sauvegarde,
  # il faut s'assurer que le champ 'full_text' est déjà peuplé dans 'extract_definitions'
  # ou utiliser des outils spécifiques comme le script embed_all_sources.py.
  success, message = save_extract_definitions_safely(extract_definitions, CONFIG_FILE, ENCRYPTION_KEY, CONFIG_FILE_JSON)
  ```

### Extraction de texte

Pour extraire le texte délimité par les marqueurs:

```python
from argumentation_analysis.ui.extract_utils import extract_text_with_markers

extracted_text, status, start_found, end_found = extract_text_with_markers(
    source_text, 
    start_marker, 
    end_marker, 
    template_start
)
```

### Recherche de texte similaire

Pour trouver des textes similaires aux marqueurs:

```python
from argumentation_analysis.ui.extract_utils import find_similar_text

similar_texts = find_similar_text(
    source_text, 
    marker, 
    context_size=50, 
    max_results=5
)
```

### Script d'embarquement des textes sources

Le script [`scripts/embed_all_sources.py`](../../scripts/embed_all_sources.py) est un outil dédié pour s'assurer que toutes les sources dans un fichier de configuration d'extraits ont leur champ `full_text` renseigné. Il parcourt chaque source, récupère le texte complet si `full_text` est manquant ou vide, puis sauvegarde la configuration mise à jour.

**Utilité :**
- Garantir l'autonomie du fichier de configuration en embarquant tous les textes.
- Préparer un fichier de configuration pour des environnements sans accès aux sources externes.
- Faciliter la distribution d'un dataset complet et autonome.

**Arguments du script :**
- `--input-config` (requis) : Chemin vers le fichier de configuration chiffré d'entrée (ex: `extract_sources.json.gz.enc`).
- `--output-config` (requis) : Chemin vers le fichier de configuration chiffré de sortie où sera sauvegardée la version avec les textes embarqués.
- `--passphrase` (optionnel) : Passphrase pour déchiffrer le fichier d'entrée et chiffrer celui de sortie. Si non fournie, le script tente d'utiliser la variable d'environnement `TEXT_CONFIG_PASSPHRASE`.
- `--force` (optionnel) : Si présent, écrase le fichier de sortie s'il existe déjà.

**Exemple d'utilisation :**
```bash
python scripts/embed_all_sources.py \
  --input-config argumentation_analysis/data/extract_sources.json.gz.enc \
  --output-config argumentation_analysis/data/extract_sources_embedded.json.gz.enc \
  --passphrase "votre_passphrase_secrete" \
  --force
```
Ce script utilise les fonctions `load_extract_definitions` et `save_extract_definitions` (la sauvegarde via ce script s'assure que `full_text` est traité pour l'embarquement) du module `argumentation_analysis.ui.file_operations` pour lire et écrire le fichier de configuration.

## Réparation des extraits

### Problèmes courants

Les extraits peuvent présenter plusieurs problèmes:
1. **Première lettre manquante** dans le marqueur de début
2. **Marqueurs introuvables** dans le texte source
3. **Marqueurs imprécis** qui ne délimitent pas correctement l'extrait voulu

### Outils de réparation

Le système offre plusieurs outils pour réparer les extraits:

- **Script de réparation principal**: `argumentation_analysis/run_extract_repair.py`
  ```bash
  python argumentation_analysis/run_extract_repair.py --output rapport.html --save
  ```

- **Options disponibles**:
  - `--output` ou `-o`: Spécifie le fichier de sortie pour le rapport HTML
  - `--save` ou `-s`: Sauvegarde les modifications apportées aux extraits
  - `--hitler-only`: Traite uniquement le corpus de discours d'Hitler

### Processus de réparation

Le processus de réparation comprend:
1. **Réparation automatique simple** (première lettre manquante)
2. **Réparation avancée avec IA** pour les cas complexes
3. **Validation** des corrections proposées
4. **Génération de rapport** détaillant les modifications

## Exemples d'utilisation

### Exemple 1: Chargement et analyse des extraits

```python
from argumentation_analysis.ui.extract_utils import load_extract_definitions_safely
from argumentation_analysis.ui.config import ENCRYPTION_KEY, CONFIG_FILE, CONFIG_FILE_JSON
from argumentation_analysis.services.fetch_service import FetchService
from argumentation_analysis.services.cache_service import CacheService
from argumentation_analysis.services.extract_service import ExtractService

# Initialiser les services
cache_service = CacheService("./cache")
fetch_service = FetchService(cache_service)
extract_service = ExtractService()

# Charger les définitions d'extraits
extract_definitions, _ = load_extract_definitions_safely(CONFIG_FILE, ENCRYPTION_KEY, CONFIG_FILE_JSON)

# Pour chaque source
for source_definition in extract_definitions:
    source_text = None
    # Priorité au full_text si disponible
    if "full_text" in source_definition and source_definition["full_text"]:
        source_text = source_definition["full_text"]
        print(f"Utilisation de full_text pour la source : {source_definition['source_name']}")
    else:
        # Fallback: Récupérer le texte source via fetch_service
        print(f"Récupération dynamique pour la source : {source_definition['source_name']}")
        source_text, _ = fetch_service.fetch_text(source_definition) # fetch_text doit pouvoir gérer l'objet source_definition
    
    if source_text:
        # Pour chaque extrait
        for extract_definition in source_definition.get("extracts", []):
            # Extraire le texte
            extracted_text, status, start_found, end_found = extract_service.extract_text_with_markers(
                source_text,
                extract_definition["start_marker"],
                extract_definition["end_marker"],
                extract_definition.get("template_start")
            )
            
            if start_found and end_found:
                print(f"Extrait '{extract_definition['extract_name']}' trouvé:")
                print(extracted_text[:100] + "...")  # Afficher le début de l'extrait
            else:
                print(f"Extrait '{extract_definition['extract_name']}' non trouvé dans la source '{source_definition['source_name']}'.")
    else:
        print(f"Impossible d'obtenir le texte source pour : {source_definition['source_name']}")
```

### Exemple 2: Réparation des extraits

```python
import asyncio
from argumentation_analysis.ui.extract_utils import load_extract_definitions_safely, save_extract_definitions_safely
from argumentation_analysis.ui.config import ENCRYPTION_KEY, CONFIG_FILE, CONFIG_FILE_JSON
from argumentation_analysis.utils.extract_repair.repair_extract_markers import repair_extract_markers, generate_report
from argumentation_analysis.services.llm_service import create_llm_service

async def repair_extracts():
    # Charger les définitions d'extraits
    extract_definitions, _ = load_extract_definitions_safely(CONFIG_FILE, ENCRYPTION_KEY, CONFIG_FILE_JSON)
    
    # Créer le service LLM
    llm_service = create_llm_service()
    
    # Réparer les extraits
    updated_definitions, results = await repair_extract_markers(extract_definitions, llm_service)
    
    # Générer un rapport
    generate_report(results, "repair_report.html")
    
    # Sauvegarder les définitions mises à jour
    success, message = save_extract_definitions_safely(
        updated_definitions, CONFIG_FILE, ENCRYPTION_KEY, CONFIG_FILE_JSON
    )
    
    print(f"Sauvegarde: {message}")
    
    return updated_definitions, results

# Exécuter la réparation
if __name__ == "__main__":
    asyncio.run(repair_extracts())
```

### Exemple 3: Ajout d'un nouvel extrait

```python
from argumentation_analysis.ui.extract_utils import load_extract_definitions_safely, save_extract_definitions_safely
from argumentation_analysis.ui.config import ENCRYPTION_KEY, CONFIG_FILE, CONFIG_FILE_JSON

# Charger les définitions existantes
extract_definitions, _ = load_extract_definitions_safely(CONFIG_FILE, ENCRYPTION_KEY, CONFIG_FILE_JSON)

# Trouver la source ou en créer une nouvelle
source_found = False
for source in extract_definitions:
    if source["source_name"] == "Discours d'Hitler à Munich":
        # Ajouter un nouvel extrait à cette source
        source["extracts"].append({
            "extract_name": "Passage sur l'économie",
            "start_marker": "Notre économie nationale doit être organisée",
            "end_marker": "pour le bien de notre peuple.",
            "template_start": None
        })
        source_found = True
        break

# Si la source n'existe pas, la créer
if not source_found:
    extract_definitions.append({
        "source_name": "Discours d'Hitler à Munich",
        "source_type": "url",
        "source_url": "https://example.com/hitler_munich_speech.html",
        "extracts": [
            {
                "extract_name": "Passage sur l'économie",
                "start_marker": "Notre économie nationale doit être organisée",
                "end_marker": "pour le bien de notre peuple.",
                "template_start": None
            }
        ]
    })

# Sauvegarder les définitions mises à jour
success, message = save_extract_definitions_safely(
    extract_definitions, CONFIG_FILE, ENCRYPTION_KEY, CONFIG_FILE_JSON
)

print(f"Sauvegarde: {message}")
```

## Bonnes pratiques

### Création de marqueurs efficaces

Pour créer des marqueurs efficaces:
1. **Choisir des séquences uniques** dans le texte source
2. **Privilégier les débuts/fins de paragraphe** pour une meilleure délimitation
3. **Éviter les caractères spéciaux** qui pourraient être mal encodés
4. **Utiliser des marqueurs suffisamment longs** (au moins 10-15 caractères)
5. **Vérifier l'unicité** des marqueurs dans le texte source

### Gestion de la clé de chiffrement

Pour une gestion sécurisée de la clé:
1. **Ne jamais stocker la clé en clair** dans le code source
2. **Utiliser des variables d'environnement** pour la configuration
3. **Limiter l'accès** à la clé aux personnes autorisées
4. **Changer régulièrement** la clé et mettre à jour le fichier chiffré

### Sauvegarde et versionnement

Pour une gestion efficace des extraits:
1. **Créer des sauvegardes régulières** du fichier chiffré
2. **Versionner les définitions** pour suivre les modifications
3. **Documenter les changements** apportés aux extraits
4. **Tester les extraits** après chaque modification

## Dépannage

### Problèmes courants et solutions

| Problème | Cause possible | Solution |
|----------|----------------|----------|
| Erreur de déchiffrement | Clé incorrecte | Vérifier la valeur de `ENCRYPTION_KEY` |
| Marqueur introuvable | Texte source modifié | Utiliser `find_similar_text` pour trouver des alternatives |
| Première lettre manquante | Problème d'encodage | Utiliser `template_start` (ex: "I{0}") |
| Extraits incorrects | Marqueurs non uniques | Allonger les marqueurs pour les rendre uniques |
| Fichier corrompu | Erreur lors de la sauvegarde | Restaurer depuis une sauvegarde |

### Outils de diagnostic

- **Vérification des extraits**: `argumentation_analysis/utils/run_verify_extracts.py`
- **Vérification avec LLM**: `argumentation_analysis/utils/run_verify_extracts_with_llm.py`
- **Réparation des extraits**: `argumentation_analysis/run_extract_repair.py`

### Journalisation

Le système utilise le module `logging` pour journaliser les opérations:
- Les erreurs sont enregistrées dans les journaux
- Le niveau de détail peut être configuré
- Les journaux peuvent aider à diagnostiquer les problèmes

---

## Conclusion

Le fichier `extract_sources.json.gz.enc` est un composant essentiel du système d'analyse rhétorique, fournissant une source structurée et sécurisée d'extraits de texte pour l'analyse. Sa gestion correcte est cruciale pour le bon fonctionnement du système.

Cette documentation devrait vous aider à comprendre son rôle, sa structure et comment l'utiliser efficacement dans vos analyses rhétoriques.