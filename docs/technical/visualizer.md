# Visualiseur de résultats rhétoriques (`RhetoricalResultVisualizer`)

## Objectif
Génère des visualisations (graphes d'arguments, distributions de sophismes, cartes de chaleur, rapport HTML) à partir de l'état d'analyse rhétorique (`state`).

> Note : la classe réelle est **`RhetoricalResultVisualizer`** (le nom `RhetoricalVisualizer` utilisé précédemment dans ce document n'existe pas dans le code).

## Chemin d'import
```python
from argumentation_analysis.agents.tools.analysis.rhetorical_result_visualizer import RhetoricalResultVisualizer
```

## Utilisation
```python
from argumentation_analysis.agents.tools.analysis.rhetorical_result_visualizer import RhetoricalResultVisualizer

visualizer = RhetoricalResultVisualizer()
mermaid_graph = visualizer.generate_argument_graph(state)   # str : code Mermaid
all_viz = visualizer.generate_all_visualizations(state)     # Dict[str, str]
html = visualizer.generate_html_report(state)               # str : rapport HTML
```

## Constructeur
`RhetoricalResultVisualizer()` — aucun paramètre.

## Méthodes principales (toutes prennent un `state: dict`)
- `generate_argument_graph(state) -> str` — graphe Mermaid des arguments.
- `generate_fallacy_distribution(state) -> str` — distribution des sophismes.
- `generate_argument_quality_heatmap(state) -> str` — carte de chaleur de qualité.
- `generate_all_visualizations(state) -> dict[str, str]` — toutes les visualisations.
- `generate_html_report(state) -> str` — rapport HTML agrégé.

## Résultat
Chaque générateur retourne une chaîne (ou un dict de chaînes pour `generate_all_visualizations`). Source de vérité : `argumentation_analysis/agents/tools/analysis/rhetorical_result_visualizer.py`.
