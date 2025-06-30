# Analyse Rhétorique des Extraits

Ce répertoire contient des scripts pour l'analyse rhétorique des extraits déchiffrés.

## Scripts disponibles

### 1. decrypt_extracts.py

Script pour déchiffrer et charger les extraits du fichier extract_sources.json.gz.enc.

```bash
python scripts/decrypt_extracts.py [--passphrase PASSPHRASE] [--output OUTPUT] [--verbose]
```

Options:
- `--passphrase`, `-p`: Phrase secrète pour dériver la clé de chiffrement (alternative à la variable d'environnement)
- `--output`, `-o`: Chemin du fichier de sortie pour les extraits déchiffrés
- `--verbose`, `-v`: Affiche des informations de débogage supplémentaires

### 2. rhetorical_analysis.py

Script pour effectuer une analyse rhétorique de base sur les extraits déchiffrés.

```bash
python scripts/rhetorical_analysis.py [--input INPUT] [--output OUTPUT] [--verbose]
```

Options:
- `--input`, `-i`: Chemin du fichier d'entrée contenant les extraits déchiffrés
- `--output`, `-o`: Chemin du fichier de sortie pour les résultats de l'analyse
- `--verbose`, `-v`: Affiche des informations de débogage supplémentaires

Ce script utilise les outils d'analyse rhétorique suivants:
- **ContextualFallacyDetector**: Détecte les sophismes contextuels dans les arguments
- **ArgumentCoherenceEvaluator**: Évalue la cohérence entre les arguments
- **SemanticArgumentAnalyzer**: Analyse la structure sémantique des arguments

Si le contenu textuel des extraits n'est pas disponible dans le fichier JSON, le script génère des textes d'exemple pour permettre l'analyse.

### 3. rhetorical_analysis_standalone.py

Version autonome du script d'analyse rhétorique qui ne dépend pas des modules externes.

```bash
python scripts/rhetorical_analysis_standalone.py [--input INPUT] [--output OUTPUT] [--verbose]
```

Options:
- `--input`, `-i`: Chemin du fichier d'entrée contenant les extraits déchiffrés
- `--output`, `-o`: Chemin du fichier de sortie pour les résultats de l'analyse
- `--verbose`, `-v`: Affiche des informations de débogage supplémentaires

Cette version utilise des outils simulés pour générer des résultats d'analyse:
- **MockContextualFallacyDetector**: Simule la détection de sophismes contextuels
- **MockArgumentCoherenceEvaluator**: Simule l'évaluation de la cohérence argumentative
- **MockSemanticArgumentAnalyzer**: Simule l'analyse sémantique des arguments

Utilisez cette version si vous rencontrez des problèmes avec les dépendances requises par la version standard.

### 4. test_rhetorical_analysis.py

Script de test pour vérifier que l'analyse rhétorique fonctionne correctement.

```bash
python scripts/test_rhetorical_analysis.py
```

Ce script exécute le script d'analyse rhétorique avec des paramètres par défaut et vérifie que les résultats sont générés correctement.

## Flux de travail typique

1. Déchiffrer les extraits:
   ```bash
   python scripts/decrypt_extracts.py
   ```

2. Analyser les extraits (choisir l'une des deux versions):
   ```bash
   python scripts/rhetorical_analysis.py
   ```
   ou
   ```bash
   python scripts/rhetorical_analysis_standalone.py
   ```

3. Consulter les résultats dans le répertoire `results/`.

## Format des résultats

Les résultats de l'analyse rhétorique sont sauvegardés au format JSON avec la structure suivante:

```json
[
  {
    "extract_name": "Nom de l'extrait",
    "source_name": "Nom de la source",
    "argument_count": 5,
    "timestamp": "2025-05-15T23:00:00.000000",
    "analyses": {
      "contextual_fallacies": {
        // Résultats de l'analyse des sophismes contextuels
      },
      "argument_coherence": {
        // Résultats de l'analyse de la cohérence argumentative
      },
      "semantic_analysis": {
        // Résultats de l'analyse sémantique
      }
    }
  },
  // Autres extraits...
]
```

## Dépendances

- Python 3.8+
- tqdm (pour la barre de progression)
- cryptography (pour le déchiffrement)
- networkx (pour l'analyse des relations entre arguments)
- numpy (pour les calculs numériques)

## Installation des dépendances

```bash
pip install tqdm cryptography networkx numpy
```

## Gestion des erreurs

Si vous rencontrez l'erreur "No module named 'networkx'", installez les dépendances manquantes:

```bash
pip install networkx numpy
```

Le script est conçu pour fonctionner même si certaines dépendances sont manquantes, en utilisant des méthodes alternatives ou des simulations pour les fonctionnalités non disponibles.