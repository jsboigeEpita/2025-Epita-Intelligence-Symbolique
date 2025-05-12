# Système d'Analyse Rhétorique Amélioré

Ce document présente les nouvelles fonctionnalités du système d'analyse rhétorique intégrées dans la branche `integration-modifications-locales`. Ces améliorations visent à fournir des outils plus puissants et flexibles pour l'analyse des arguments et des sophismes dans différents contextes.

## Nouvelles Fonctionnalités

### 1. Outils d'Analyse Rhétorique Améliorés

#### 1.1 Analyseur de Résultats Rhétoriques Amélioré
L'`EnhancedRhetoricalResultAnalyzer` offre des capacités d'analyse plus avancées que la version de base, notamment :
- Analyse approfondie des sophismes et de leur impact persuasif
- Évaluation de la cohérence argumentative
- Identification des stratégies de persuasion et des appels rhétoriques (ethos, pathos, logos)
- Génération de recommandations personnalisées pour améliorer l'argumentation

```python
from argumentiation_analysis.agents.tools.analysis.enhanced.rhetorical_result_analyzer import EnhancedRhetoricalResultAnalyzer

analyzer = EnhancedRhetoricalResultAnalyzer()
results = {
    "complex_fallacy_analysis": {...},
    "contextual_fallacy_analysis": {...},
    "argument_coherence_evaluation": {...}
}
analysis = analyzer.analyze_rhetorical_results(results, context="politique")
```

#### 1.2 Analyseur de Sophismes Complexes Amélioré
L'`EnhancedComplexFallacyAnalyzer` permet d'identifier et d'analyser des structures sophistiquées de sophismes :
- Détection de combinaisons de sophismes avancées
- Analyse de la structure argumentative
- Évaluation de la cohérence inter-arguments

#### 1.3 Évaluateur de Gravité des Sophismes Amélioré
L'`EnhancedFallacySeverityEvaluator` fournit une évaluation plus nuancée de l'impact des sophismes :
- Prise en compte du contexte dans l'évaluation
- Analyse de l'impact persuasif
- Évaluation de la gravité composite des sophismes

### 2. Nouveaux Outils d'Analyse Rhétorique

#### 2.1 Visualiseur de Structure Argumentative
L'`ArgumentStructureVisualizer` permet de visualiser graphiquement la structure des arguments :
- Génération de cartes de chaleur des sophismes
- Visualisation des relations entre arguments
- Support pour différents formats de sortie (HTML, PNG, JSON)

```python
from argumentiation_analysis.agents.tools.analysis.new.argument_structure_visualizer import ArgumentStructureVisualizer

visualizer = ArgumentStructureVisualizer()
visualization = visualizer.visualize_argument_structure(
    arguments=["Argument 1", "Argument 2", "Argument 3"],
    context="scientifique",
    output_format="html"
)
```

#### 2.2 Évaluateur de Cohérence Argumentative
L'`ArgumentCoherenceEvaluator` analyse la cohérence logique et thématique entre les arguments :
- Détection des contradictions
- Évaluation de la cohérence thématique
- Analyse de la structure logique

#### 2.3 Analyseur Sémantique d'Arguments
Le `SemanticArgumentAnalyzer` fournit une analyse sémantique approfondie des arguments :
- Identification des thèmes principaux
- Analyse des relations sémantiques entre arguments
- Évaluation de la richesse sémantique

#### 2.4 Détecteur Contextuel de Sophismes
Le `ContextualFallacyDetector` détecte les sophismes en tenant compte du contexte spécifique :
- Adaptation au domaine (politique, scientifique, commercial, etc.)
- Prise en compte de l'audience cible
- Analyse contextuelle des sophismes

## Intégration dans le Système d'Orchestration

Ces outils sont intégrés dans le système d'orchestration hiérarchique à trois niveaux via l'adaptateur `RhetoricalToolsAdapter`, qui permet aux agents opérationnels d'utiliser ces outils de manière transparente.

```python
from argumentiation_analysis.orchestration.hierarchical.operational.adapters.rhetorical_tools_adapter import RhetoricalToolsAdapter

adapter = RhetoricalToolsAdapter()
adapter.initialize()

task = {
    "id": "task-1",
    "description": "Analyser les sophismes dans le texte",
    "techniques": [
        {
            "name": "complex_fallacy_analysis",
            "parameters": {"context": "politique"}
        }
    ],
    "text_extracts": [{"content": "Texte à analyser..."}]
}

result = await adapter.process_task(task)
```

## Exemples d'Utilisation

Vous trouverez des exemples d'utilisation détaillés dans le répertoire `examples/` :
- `examples/rhetorical_analysis_example.py` : Exemple d'utilisation des outils d'analyse rhétorique
- `examples/hierarchical_architecture_example.py` : Exemple d'intégration dans l'architecture hiérarchique

## Documentation Détaillée

Pour une documentation plus détaillée sur chaque outil, consultez les fichiers suivants :
- `docs/outils/complex_fallacy_analyzer.md` : Documentation de l'analyseur de sophismes complexes
- `docs/outils/argument_coherence_evaluator.md` : Documentation de l'évaluateur de cohérence argumentative
- `docs/outils/visualizer.md` : Documentation du visualiseur de structure argumentative
