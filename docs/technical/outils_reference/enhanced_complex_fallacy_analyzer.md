# Analyseur de sophismes complexes (`EnhancedComplexFallacyAnalyzer`)

## Objectif
Analyse la structure globale d'un ensemble d'arguments : identifie les patrons structurels de chaque argument, les relations (support, contradiction) entre arguments, puis évalue la cohérence globale et les vulnérabilités potentielles.

## Chemin d'import
```python
from argumentation_analysis.plugins.analysis_tools.logic.complex_fallacy_analyzer import EnhancedComplexFallacyAnalyzer
```

## Utilisation
```python
from argumentation_analysis.plugins.analysis_tools.logic.complex_fallacy_analyzer import EnhancedComplexFallacyAnalyzer

# La construction requiert un détecteur de sophismes (AbstractFallacyDetector) injecté.
analyzer = EnhancedComplexFallacyAnalyzer(fallacy_detector=mon_detecteur)
result = analyzer.analyze_argument_structure(
    arguments=["Argument 1.", "Argument 2.", "Argument 3."],
    context="général",  # optionnel
)
print(result)  # Dict[str, Any] : structures, relations, cohérence, vulnérabilités
```

## Constructeur
`EnhancedComplexFallacyAnalyzer(fallacy_detector: AbstractFallacyDetector)` — un détecteur de sophismes **requis**.

## Méthodes principales
- `analyze_argument_structure(arguments: list[str], context: str = "général") -> dict`
- `detect_composite_fallacies(...)`
- `analyze_inter_argument_coherence(...)`

## Résultat
`Dict[str, Any]` riche : structures identifiées, relations entre arguments, évaluation de cohérence, vulnérabilités potentielles. Source de vérité : `argumentation_analysis/plugins/analysis_tools/logic/complex_fallacy_analyzer.py`.

> Note : ce document et `complex_fallacy_analyzer.md` décrivent la même classe (`EnhancedComplexFallacyAnalyzer`).
