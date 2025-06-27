# Tests Unitaires pour les Agents de Base

## Objectif

Ce répertoire regroupe les tests unitaires pour les composants fondamentaux et les agents de base du système d'analyse d'argumentation. Ces tests sont cruciaux car ils valident les briques élémentaires sur lesquelles reposent des fonctionnalités plus complexes.

L'objectif est de s'assurer que les agents de bas niveau et leurs définitions associées fonctionnent de manière fiable et prévisible.

## Sous-répertoires

-   **[extract](./extract/README.md)** : Contient les tests pour l'agent d'extraction (`ExtractAgent`) et ses structures de données. Ces tests valident la capacité du système à identifier et extraire des fragments de texte (arguments, prémisses) en se basant sur des marqueurs sémantiques.

-   **[informal](./informal/README.md)** : Contient les tests pour le plugin d'analyse informelle (`InformalAnalysisPlugin`). Ces tests garantissent le bon chargement et la bonne exploration de la taxonomie des sophismes informels, qui est une base de connaissances essentielle pour l'analyse.