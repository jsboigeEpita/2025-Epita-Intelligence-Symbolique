# Tests des Agents Fondamentaux (Core)

Ce répertoire contient les tests pour les agents fondamentaux du système d'analyse d'argumentation. Ces agents représentent les briques de base pour différents types de raisonnement et d'analyse.

## Objectif

L'objectif de ces tests est de valider individuellement chaque type d'agent fondamental pour s'assurer de leur fiabilité, de leur exactitude et de leur robustesse.

## Sous-répertoires

- **[`informal/`](informal/README.md)**: Contient les tests pour l'`InformalAnalysisAgent`, qui est spécialisé dans l'analyse d'arguments en langage naturel, la détection de sophismes et l'analyse rhétorique.

- **[`logic/`](logic/README.md)**: Regroupe les tests pour les agents basés sur la logique formelle, y compris les agents pour la logique propositionnelle, la logique du premier ordre et la logique modale. Ces tests valident la chaîne de conversion texte-logique, le raisonnement et l'interprétation.

- **[`pm/`](pm/README.md)**: Contient les tests pour les agents de type "Project Manager", comme le `SherlockEnqueteAgent`, qui sont conçus pour orchestrer des tâches complexes et gérer un état sur le long terme.

## Structure Générale des Tests

Les tests dans ce répertoire partagent plusieurs caractéristiques communes :
- **Isolation**: Chaque agent est testé de manière isolée en utilisant des mocks pour ses dépendances externes (par exemple, `semantic_kernel`, `TweetyBridge`).
- **Fixtures `pytest`**: Des fixtures sont utilisées pour standardiser l'initialisation des agents et des mocks.
- **Tests Asynchrones**: La plupart des interactions avec les agents sont asynchrones, nécessitant l'utilisation de `pytest-asyncio`.