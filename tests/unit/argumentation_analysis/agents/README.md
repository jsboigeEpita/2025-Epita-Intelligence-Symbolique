# Tests Unitaires pour les Agents d'Analyse d'Argumentation

## Objectif

Ce répertoire est le point central pour tous les tests unitaires concernant les agents du système d'analyse d'argumentation. Il couvre à la fois les composants de base des agents et les outils spécialisés qu'ils utilisent pour effectuer des analyses approfondies.

L'objectif global est de garantir que chaque composant d'agent, du plus simple au plus complexe, est fiable, robuste et se comporte comme attendu de manière isolée.

## Sous-répertoires

-   **[core](./core/README.md)** : Contient les tests pour les briques fondamentales des agents. Cela inclut les mécanismes d'extraction de texte et la gestion des taxonomies de sophismes, qui sont des dépendances essentielles pour les agents de plus haut niveau.

-   **[tools](./tools/README.md)** : Contient les tests pour les outils d'analyse avancée. Ces tests valident des logiques complexes comme la détection de combinaisons de sophismes et l'analyse de leur pertinence contextuelle.