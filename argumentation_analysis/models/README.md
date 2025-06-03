# Package Models

Ce package contient les modèles de données utilisés dans le projet d'analyse d'argumentation. Les modèles définissent les structures de données et les classes qui représentent les concepts clés du projet.

## Structure

```
models/
├── __init__.py
├── extract_definition.py
├── extract_result.py
└── README.md
```

## Modèles disponibles

### ExtractDefinition (extract_definition.py)

Ce module définit les classes pour représenter les définitions d'extraits et de sources:

- `Extract`: Représente un extrait individuel avec ses marqueurs de début et de fin
- `SourceDefinition`: Représente une source de texte (URL, fichier, etc.) et ses extraits associés
- `ExtractDefinitions`: Collection de définitions de sources

Ces classes sont utilisées pour charger, manipuler et sauvegarder les définitions d'extraits à partir du fichier de configuration chiffré.

#### Exemple d'utilisation

```python
from argumentation_analysis.models.extract_definition import ExtractDefinitions, SourceDefinition, Extract

# Créer un extrait
extract = Extract(
    extract_name="Exemple d'extrait",
    start_marker="Début de l'extrait",
    end_marker="Fin de l'extrait",
    template_start="D{0}"  # Template pour ajouter une lettre manquante
)

# Créer une source
source = SourceDefinition(
    source_name="Source d'exemple",
    source_type="url",
    source_url="https://example.com/texte",
    extracts=[extract]
)

# Créer des définitions d'extraits
definitions = ExtractDefinitions(sources=[source])

# Convertir en dictionnaire pour la sérialisation
definitions_dict = definitions.to_dict()
```

### ExtractResult (extract_result.py)

Ce module définit la classe `ExtractResult` qui représente le résultat d'une extraction de texte à partir d'une source. Elle contient des informations sur le succès de l'extraction, le texte extrait, et les éventuelles erreurs rencontrées.

#### Exemple d'utilisation

```python
from argumentation_analysis.models.extract_result import ExtractResult

# Créer un résultat d'extraction
result = ExtractResult(
    source_name="Source d'exemple",
    extract_name="Exemple d'extrait",
    extracted_text="Texte extrait de la source",
    start_marker_found=True,
    end_marker_found=True,
    status="success"
)

# Vérifier si l'extraction a réussi
if result.is_success():
    print(f"Extraction réussie: {result.extracted_text}")
else:
    print(f"Échec de l'extraction: {result.status}")
```

## Intégration avec les services

Ces modèles sont utilisés par les services du projet, notamment:

- `DefinitionService`: Pour charger et sauvegarder les définitions d'extraits
- `ExtractService`: Pour extraire du texte à partir des sources en utilisant les définitions d'extraits
- `CryptoService`: Pour chiffrer et déchiffrer les définitions d'extraits

## Évolution future

Les modèles peuvent être étendus pour prendre en charge de nouveaux types de sources ou de nouvelles fonctionnalités d'extraction. Par exemple:

- Ajout de métadonnées supplémentaires aux extraits
- Support pour des formats de texte structurés (HTML, XML, etc.)
- Intégration avec des modèles d'analyse d'argumentation