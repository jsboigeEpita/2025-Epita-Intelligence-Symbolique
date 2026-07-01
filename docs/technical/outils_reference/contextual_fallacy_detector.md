# Détecteur de sophismes contextuels (`ContextualFallacyDetector`)

## Objectif
Détecte les sophismes contextuels dans un argument : pour chaque sophisme de la base de règles, recherche ses marqueurs dans le texte, calcule une gravité selon le contexte, et signale le sophisme si sa gravité dépasse 0.5.

## Chemin d'import
```python
from argumentation_analysis.agents.tools.analysis.new.contextual_fallacy_detector import ContextualFallacyDetector
```

## Utilisation
```python
from argumentation_analysis.agents.tools.analysis.new.contextual_fallacy_detector import ContextualFallacyDetector

detector = ContextualFallacyDetector()
result = detector.detect_contextual_fallacies(
    argument="Cet argument...",
    context_description="Débat parlementaire sur l'énergie",
    # contextual_factors={"audience": "experts"},  # optionnel ; inféré depuis la description sinon
)
print(result)  # Dict[str, Any] : sophismes détectés pour cet argument
```

## Constructeur
`ContextualFallacyDetector()` — aucun paramètre.

## Méthodes principales
- `detect_contextual_fallacies(argument: str, context_description: str, contextual_factors: dict | None = None) -> dict` — un seul argument.
- `detect_multiple_contextual_fallacies(...)` — plusieurs arguments.

## Résultat
`Dict[str, Any]` contenant la liste des sophismes détectés pour l'argument (gravité > 0.5). Source de vérité : `argumentation_analysis/agents/tools/analysis/new/contextual_fallacy_detector.py`.
