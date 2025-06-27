# Outils d'Analyse Rhétorique

Cette section documente les outils d'analyse rhétorique disponibles dans le système d'analyse argumentative, leur fonctionnement et leur utilisation.

## Vue d'Ensemble

Les outils d'analyse rhétorique offrent une infrastructure modulaire pour l'analyse argumentative, intégrant trois couches d'abstraction :

- **Niveau Stratégique** : Planification de l'analyse
- **Niveau Tactique** : Coordination des outils
- **Niveau Opérationnel** : Exécution de l'analyse

Les outils sont organisés en trois catégories :

- **[Outils de base](../../argumentation_analysis/agents/tools/analysis/README.md)** : Fonctionnalités fondamentales d'analyse rhétorique
- **[Outils améliorés](../../argumentation_analysis/agents/tools/analysis/enhanced/README.md)** : Versions avancées des outils de base avec des capacités étendues
- **[Nouveaux outils](../../argumentation_analysis/agents/tools/analysis/new/README.md)** : Outils innovants introduisant de nouvelles approches d'analyse

## Documents Disponibles

### [API des Outils Rhétoriques](./api_outils.md)
Documentation de l'API des outils d'analyse rhétorique, incluant les interfaces et les méthodes disponibles.

### [Développement des Outils Rhétoriques](./developpement_outils.md)
Guide pour le développement de nouveaux outils d'analyse rhétorique.

### [Intégration des Outils Rhétoriques](./integration_outils.md)
Documentation sur l'intégration des outils d'analyse rhétorique dans le système.

## Outils Disponibles

Les outils d'analyse rhétorique sont documentés en détail dans le répertoire [reference](./reference/) :

### Outils de base

### [Évaluateur de Cohérence](./reference/coherence_evaluator.md)
Outil pour évaluer la cohérence globale d'un texte argumentatif.

### [Analyseur de Sophismes Complexes](./reference/complex_fallacy_analyzer.md)
Outil pour identifier et analyser les sophismes complexes dans un texte.

### [Détecteur Contextuel de Sophismes](./reference/contextual_fallacy_detector.md)
Outil pour détecter les sophismes en tenant compte du contexte spécifique.

### Outils améliorés

### [Analyseur Amélioré de Sophismes Complexes](./reference/enhanced_complex_fallacy_analyzer.md)
Version améliorée de l'analyseur de sophismes complexes avec des fonctionnalités avancées.

### [Analyseur Contextuel Amélioré de Sophismes](./reference/enhanced_contextual_fallacy_analyzer.md)
Version améliorée du détecteur contextuel de sophismes avec analyse contextuelle approfondie.

### [Évaluateur Amélioré de Gravité des Sophismes](./reference/enhanced_fallacy_severity_evaluator.md)
Outil pour évaluer la gravité des sophismes en tenant compte du contexte et du public cible.

### [Analyseur Amélioré des Résultats Rhétoriques](./reference/enhanced_rhetorical_result_analyzer.md)
Outil pour analyser en profondeur les résultats d'une analyse rhétorique.

### Nouveaux outils

### [ArgumentCoherenceEvaluator](./reference/argument_coherence_evaluator.md)
Outil pour évaluer la cohérence logique et thématique entre les arguments.

### [ArgumentStructureVisualizer](./reference/visualizer.md)
Outil pour visualiser graphiquement la structure des arguments.

### [SemanticArgumentAnalyzer](./reference/semantic_argument_analyzer.md)
Outil implémentant le modèle de Toulmin pour analyser la structure sémantique des arguments.

### [ContextualFallacyDetector (Avancé)](./reference/contextual_fallacy_detector_advanced.md)
Version avancée du détecteur de sophismes contextuels avec analyse des facteurs contextuels.

## Objectifs des Outils

1. **Analyse de cohérence argumentative** : Évaluation des liens logiques entre arguments
2. **Détection de sophismes contextuels** : Identification des erreurs rhétoriques dans leur contexte
3. **Analyse de complexité logique** : Étude des structures argumentatives complexes
4. **Visualisation des résultats** : Représentation graphique des analyses
5. **Analyse sémantique des arguments** : Étude de la structure sémantique selon le modèle de Toulmin
6. **Évaluation de la gravité des sophismes** : Mesure de l'impact des sophismes selon le contexte

## Exemple d'Utilisation

```python
from argumentation_analysis import RhetoricalAnalysisSystem

# Initialisation du système
system = RhetoricalAnalysisSystem()

# Configuration des outils
system.configure_tool("CoherenceEvaluator", {
    "threshold": 0.7,
    "explanations": True
})

# Création d'un pipeline
pipeline = system.create_pipeline([
    "CoherenceEvaluator",
    "ContextualFallacyDetector",
    "EnhancedComplexFallacyAnalyzer",
    "SemanticArgumentAnalyzer"
])

# Exécution de l'analyse
results = pipeline.analyze(text="Argumentation complexe à analyser")
print(results.visualization)
```

## Paramètres Clés

| Outil | Paramètres | Valeurs par défaut |
|-------|------------|-------------------|
| `CoherenceEvaluator` | `threshold`, `explanations` | 0.65, False |
| `ContextualFallacyDetector` | `sensitivity`, `context_window` | 0.8, 100 |
| `EnhancedComplexFallacyAnalyzer` | `depth`, `strict_mode` | 3, False |
| `SemanticArgumentAnalyzer` | `model_type`, `toulmin_components` | "standard", ["claim", "data", "warrant", "backing", "rebuttal", "qualifier"] |
| `ArgumentCoherenceEvaluator` | `coherence_types`, `min_score` | ["logical", "semantic", "contextual"], 0.6 |

## Améliorations Récentes

1. **Gestion des contextes complexes** : Nouveau système de fenêtrage contextuel
2. **Performance optimisée** : Architecture asynchrone pour les analyses parallèles
3. **Extensibilité** : API standardisée pour l'ajout de nouveaux critères
4. **Robustesse** : Mécanismes de validation des extraits d'arguments
5. **Analyse sémantique avancée** : Implémentation du modèle de Toulmin pour l'analyse argumentative
6. **Détection de sophismes composés** : Identification des patterns complexes de sophismes
7. **Visualisation interactive** : Représentation graphique interactive des structures argumentatives

## Prochaines Étapes

Pour contribuer au développement des outils d'analyse rhétorique, consultez le [Guide de Développement des Outils Rhétoriques](./developpement_outils.md).

## Documentation des Implémentations

Pour une documentation technique détaillée des implémentations :

- [Documentation des outils de base](../../argumentation_analysis/agents/tools/analysis/README.md)
- [Documentation des outils améliorés](../../argumentation_analysis/agents/tools/analysis/enhanced/README.md)
- [Documentation des nouveaux outils](../../argumentation_analysis/agents/tools/analysis/new/README.md)