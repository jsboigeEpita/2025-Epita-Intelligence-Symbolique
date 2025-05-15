# Outils d'Analyse Rhétorique

Cette section documente les outils d'analyse rhétorique disponibles dans le système d'analyse argumentative, leur fonctionnement et leur utilisation.

## Vue d'Ensemble

Les outils d'analyse rhétorique offrent une infrastructure modulaire pour l'analyse argumentative, intégrant trois couches d'abstraction :

- **Niveau Stratégique** : Planification de l'analyse
- **Niveau Tactique** : Coordination des outils
- **Niveau Opérationnel** : Exécution de l'analyse

## Documents Disponibles

### [API des Outils Rhétoriques](./api_outils.md)
Documentation de l'API des outils d'analyse rhétorique, incluant les interfaces et les méthodes disponibles.

### [Développement des Outils Rhétoriques](./developpement_outils.md)
Guide pour le développement de nouveaux outils d'analyse rhétorique.

### [Intégration des Outils Rhétoriques](./integration_outils.md)
Documentation sur l'intégration des outils d'analyse rhétorique dans le système.

## Outils Disponibles

Les outils d'analyse rhétorique sont documentés en détail dans le répertoire [reference](./reference/) :

### [Évaluateur de Cohérence Argumentative](./reference/argument_coherence_evaluator.md)
Outil pour évaluer la cohérence logique et thématique entre les arguments.

### [Évaluateur de Cohérence](./reference/coherence_evaluator.md)
Outil pour évaluer la cohérence globale d'un texte argumentatif.

### [Analyseur de Sophismes Complexes](./reference/complex_fallacy_analyzer.md)
Outil pour identifier et analyser les sophismes complexes dans un texte.

### [Détecteur Contextuel de Sophismes](./reference/contextual_fallacy_detector.md)
Outil pour détecter les sophismes en tenant compte du contexte spécifique.

### [Analyseur Amélioré de Sophismes Complexes](./reference/enhanced_complex_fallacy_analyzer.md)
Version améliorée de l'analyseur de sophismes complexes avec des fonctionnalités avancées.

### [Visualiseur de Structure Argumentative](./reference/visualizer.md)
Outil pour visualiser graphiquement la structure des arguments.

## Objectifs des Outils

1. **Analyse de cohérence argumentative** : Évaluation des liens logiques entre arguments
2. **Détection de sophismes contextuels** : Identification des erreurs rhétoriques dans leur contexte
3. **Analyse de complexité logique** : Étude des structures argumentatives complexes
4. **Visualisation des résultats** : Représentation graphique des analyses

## Exemple d'Utilisation

```python
from argumentiation_analysis import RhetoricalAnalysisSystem

# Initialisation du système
system = RhetoricalAnalysisSystem()

# Configuration des outils
system.configure_tool("coherence_evaluator", {
    "threshold": 0.7,
    "explanations": True
})

# Création d'un pipeline
pipeline = system.create_pipeline([
    "coherence_evaluator",
    "contextual_fallacy_detector",
    "enhanced_complex_fallacy_analyzer"
])

# Exécution de l'analyse
results = pipeline.analyze(text="Argumentation complexe à analyser")
print(results.visualization)
```

## Paramètres Clés

| Outil | Paramètres | Valeurs par défaut |
|-------|------------|-------------------|
| `coherence_evaluator` | `threshold`, `explanations` | 0.65, False |
| `contextual_fallacy_detector` | `sensitivity`, `context_window` | 0.8, 100 |
| `enhanced_complex_fallacy_analyzer` | `depth`, `strict_mode` | 3, False |

## Améliorations Récentes

1. **Gestion des contextes complexes** : Nouveau système de fenêtrage contextuel
2. **Performance optimisée** : Architecture asynchrone pour les analyses parallèles
3. **Extensibilité** : API standardisée pour l'ajout de nouveaux critères
4. **Robustesse** : Mécanismes de validation des extraits d'arguments

## Prochaines Étapes

Pour contribuer au développement des outils d'analyse rhétorique, consultez le [Guide de Développement des Outils Rhétoriques](./developpement_outils.md).