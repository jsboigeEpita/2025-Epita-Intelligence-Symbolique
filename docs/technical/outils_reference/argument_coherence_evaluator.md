# Évaluateur de cohérence argumentative (`ArgumentCoherenceEvaluator`)

## Objectif
Évalue la cohérence d'un ensemble d'arguments selon cinq dimensions (logique, thématique, structurelle, rhétorique, épistémique) et produit un score global pondéré ainsi que des recommandations.

> ⚠️ **Statut d'implémentation — simulation.** Le module est actuellement un squelette : les scores par dimension sont pré-définis et ne dérivent pas d'une analyse sémantique réelle. Il sert de cadre pour une future implémentation. Source de vérité : la docstring du module `argumentation_analysis/agents/tools/analysis/new/argument_coherence_evaluator.py`.

## Chemin d'import
```python
from argumentation_analysis.agents.tools.analysis.new.argument_coherence_evaluator import ArgumentCoherenceEvaluator
```

## Utilisation
```python
from argumentation_analysis.agents.tools.analysis.new.argument_coherence_evaluator import ArgumentCoherenceEvaluator

evaluator = ArgumentCoherenceEvaluator()
result = evaluator.evaluate_coherence(
    arguments=[
        "Tous les chats sont des mammifères.",
        "Les mammifères sont des vertébrés.",
        "Donc, les chats sont des vertébrés.",
    ],
    context="Déduction catégorique",  # optionnel
)
print(result["overall_coherence"])
```

## Constructeur
`ArgumentCoherenceEvaluator()` — aucun paramètre.

## Méthode principale
`evaluate_coherence(arguments: list[str], context: str | None = None) -> dict`

## Résultat (dictionnaire)
| Clé | Type | Description |
|-----|------|-------------|
| `overall_coherence` | float | Score global (moyenne pondérée des 5 axes, 0–1) |
| `coherence_evaluations` | dict | Scores détaillés par axe (`logique`, `thématique`, `structurelle`, `rhétorique`, `épistémique`) |
| `recommendations` | list | Recommandations basées sur les points faibles identifiés |
| `context` | str | Contexte utilisé (`"Analyse d'arguments"` par défaut) |
| `timestamp` | str | Horodatage ISO 8601 de l'évaluation |

## Axes d'évaluation (et pondérations)
| Axe | Poids |
|-----|-------|
| logique | 0.30 |
| thématique | 0.20 |
| structurelle | 0.20 |
| rhétorique | 0.15 |
| épistémique | 0.15 |

## Tests
`tests/unit/argumentation_analysis/agents/tools/analysis/new/test_argument_coherence_evaluator.py`
