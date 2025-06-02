# Comparaison des performances des agents d'analyse rhétorique

Ce script permet de comparer les performances des différents agents spécialistes d'analyse rhétorique.

## Fonctionnalités

Le script `compare_rhetorical_agents_simple.py` :

1. Charge les résultats des analyses de base et avancée
2. Compare les performances des agents sur plusieurs critères :
   - Précision de détection des sophismes
   - Richesse de l'analyse contextuelle
   - Pertinence des évaluations de cohérence
   - Temps d'exécution
   - Complexité des résultats
3. Génère des métriques quantitatives pour chaque agent :
   - Nombre de sophismes détectés
   - Scores de confiance moyens
   - Taux de faux positifs/négatifs (estimés)
   - Temps d'exécution moyen
4. Produit des visualisations comparatives :
   - Graphiques de performance
   - Matrices de confusion
   - Diagrammes de comparaison
5. Génère un rapport détaillé sur la pertinence des différents agents

## Prérequis

Le script nécessite les dépendances suivantes :
- matplotlib
- numpy
- pandas
- seaborn
- tqdm

Ces dépendances sont incluses dans le fichier `setup.py` du projet.

## Utilisation

Pour exécuter le script avec les paramètres par défaut :

```bash
python scripts/compare_rhetorical_agents_simple.py
```

Le script utilisera automatiquement les fichiers de résultats les plus récents dans le répertoire `results/`.

### Options

Le script accepte les options suivantes :

- `--base-results` ou `-b` : Chemin du fichier contenant les résultats de l'analyse de base
- `--advanced-results` ou `-a` : Chemin du fichier contenant les résultats de l'analyse avancée
- `--output-dir` ou `-o` : Répertoire de sortie pour les visualisations et le rapport (par défaut : `results/performance_comparison`)
- `--verbose` ou `-v` : Affiche des informations de débogage supplémentaires

Exemple d'utilisation avec des options :

```bash
python scripts/compare_rhetorical_agents_simple.py --base-results results/rhetorical_analysis_20250515_231321.json --advanced-results results/advanced_rhetorical_analysis_20250515_231911.json --output-dir results/custom_comparison --verbose
```

## Résultats

Le script génère les fichiers suivants dans le répertoire de sortie :

- `fallacy_counts.png` : Graphique de comparaison des nombres de sophismes détectés
- `confidence_scores.png` : Graphique de comparaison des scores de confiance
- `contextual_richness.png` : Graphique de comparaison de la richesse contextuelle
- `performance_matrix.png` : Matrice de comparaison des performances
- `performance_metrics.csv` : Données brutes des métriques de performance
- `rapport_performance.md` : Rapport détaillé sur la pertinence des différents agents

## Agents comparés

Le script compare les performances des agents suivants :

### Agents de base
- `base_contextual` : ContextualFallacyDetector
- `base_coherence` : ArgumentCoherenceEvaluator
- `base_semantic` : SemanticArgumentAnalyzer

### Agents avancés
- `advanced_contextual` : EnhancedContextualFallacyAnalyzer
- `advanced_complex` : EnhancedComplexFallacyAnalyzer
- `advanced_severity` : EnhancedFallacySeverityEvaluator
- `advanced_rhetorical` : EnhancedRhetoricalResultAnalyzer