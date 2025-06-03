# Package Scripts

Ce package contient les scripts utilitaires pour la gestion des extraits sources dans le projet d'analyse d'argumentation. Ces scripts sont conçus pour être exécutés directement ou via les points d'entrée à la racine du projet.

## Structure

```
scripts/
├── __init__.py
├── repair_extract_markers.py
├── verify_extracts.py
└── README.md
```

## Scripts disponibles

### repair_extract_markers.py

Script de réparation des bornes défectueuses dans les extraits définis dans le fichier de configuration. Il se concentre particulièrement sur le corpus de discours d'Hitler qui est volumineux.

#### Fonctionnalités principales
- Analyse des extraits existants pour détecter les bornes défectueuses
- Correction automatique des bornes avec des algorithmes de correspondance approximative
- Traitement spécifique pour le corpus de discours d'Hitler
- Validation et sauvegarde des corrections
- Génération d'un rapport détaillé des modifications

#### Utilisation
Le script peut être exécuté directement ou via le point d'entrée `run_extract_repair.py` à la racine du projet:

```bash
# Exécution directe
python -m argumentation_analysis.scripts.repair_extract_markers --output repair_report.html --save

# Via le point d'entrée
python run_extract_repair.py --output repair_report.html --save
```

#### Options
- `--output`, `-o`: Fichier de sortie pour le rapport HTML (défaut: repair_report.html)
- `--save`, `-s`: Sauvegarder les modifications
- `--hitler-only`: Traiter uniquement le corpus de discours d'Hitler
- `--verbose`, `-v`: Activer le mode verbeux
- `--input`, `-i`: Fichier d'entrée personnalisé
- `--output-json`: Fichier de sortie JSON pour vérification (défaut: extract_sources_updated.json)

### verify_extracts.py

Script de vérification des extraits définis dans le fichier de configuration. Il s'assure que les marqueurs de début et de fin sont présents dans les textes sources.

#### Fonctionnalités principales
- Vérification de la présence des marqueurs dans les textes sources
- Génération d'un rapport détaillé des problèmes détectés
- Prise en charge des templates pour les marqueurs de début
- Vérification spécifique pour le corpus de discours d'Hitler

#### Utilisation
Le script peut être exécuté directement ou via le point d'entrée `run_verify_extracts.py` à la racine du projet:

```bash
# Exécution directe
python -m argumentation_analysis.scripts.verify_extracts --output verify_report.html

# Via le point d'entrée
python run_verify_extracts.py --output verify_report.html
```

#### Options
- `--output`, `-o`: Fichier de sortie pour le rapport HTML (défaut: verify_report.html)
- `--verbose`, `-v`: Activer le mode verbeux
- `--input`, `-i`: Fichier d'entrée personnalisé
- `--hitler-only`: Traiter uniquement le corpus de discours d'Hitler

## Intégration avec les services et modèles

Ces scripts utilisent les services et modèles définis dans les packages `services` et `models`:

- `ExtractService` pour l'extraction de texte et la recherche de texte similaire
- `FetchService` pour la récupération de texte à partir de sources
- `DefinitionService` pour le chargement et la sauvegarde des définitions d'extraits
- `CryptoService` pour le chiffrement et le déchiffrement des données
- `CacheService` pour la mise en cache des textes sources
- `ExtractDefinitions`, `SourceDefinition` et `Extract` pour représenter les définitions d'extraits
- `ExtractResult` pour représenter les résultats d'extraction

## Points d'entrée à la racine du projet

Pour faciliter l'utilisation des scripts, deux points d'entrée sont disponibles à la racine du projet:

- `run_extract_repair.py`: Pour exécuter le script de réparation des bornes défectueuses
- `run_verify_extracts.py`: Pour exécuter le script de vérification des extraits

Ces points d'entrée configurent automatiquement l'environnement d'exécution et transmettent les arguments aux scripts correspondants.

## Évolution future

Les scripts peuvent être étendus pour prendre en charge de nouvelles fonctionnalités:

- Ajout de nouveaux types de réparations automatiques
- Amélioration des rapports générés
- Intégration avec des outils d'analyse d'argumentation
- Support pour de nouveaux formats de sources