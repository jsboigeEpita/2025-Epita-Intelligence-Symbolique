# Tests des Outils d'Analyse des Agents

Ce répertoire regroupe les tests pour les outils d'analyse utilisés par les agents d'argumentation. Ces outils sont responsables de l'identification, de la classification et de l'évaluation des composantes d'un argument, notamment les sophismes.

## Objectif

L'objectif de ces tests est de s'assurer que les outils d'analyse fonctionnent de manière fiable et précise. Les tests valident la capacité des outils à :
- Détecter différents types de sophismes.
- Analyser les arguments dans des contextes variés.
- Évaluer la gravité et la pertinence des sophismes identifiés.

## Sous-répertoires

- **[`enhanced/`](enhanced/README.md)**: Contient les tests pour les analyseurs de sophismes améliorés, qui gèrent des détections complexes, contextuelles et basées sur la gravité.

## Structure des Tests

Les tests sont organisés par fonctionnalité d'analyse. Chaque sous-répertoire se concentre sur un aspect spécifique de l'analyse d'arguments, permettant une validation ciblée et approfondie.

## Dépendances

- `pytest`
- Les modules applicatifs situés dans `argumentation_analysis/agents/tools/analysis/`.
