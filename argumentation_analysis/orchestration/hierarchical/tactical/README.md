# Couche Tactique

## Rôle et Responsabilités

La couche tactique est le "chef de chantier" de l'orchestration. Elle fait le lien entre la vision de haut niveau de la couche stratégique et l'exécution concrète de la couche opérationnelle.

Ses missions principales se concentrent sur la **coordination**, la **résolution de conflits** et le **suivi des tâches** :

1.  **Décomposer et Planifier** : Recevoir les objectifs généraux de la couche stratégique (le "Quoi") et les décomposer en une séquence logique de tâches exécutables (le "Comment"). Cela inclut la gestion des dépendances entre les tâches.
2.  **Coordonner les Agents** : Assigner les tâches aux bons groupes d'agents (via la couche opérationnelle) et orchestrer le flux de travail entre eux.
3.  **Suivre la Progression** : Monitorer activement l'avancement des tâches, en s'assurant qu'elles sont complétées dans les temps et sans erreur.
4.  **Résoudre les Conflits** : Lorsque les résultats de différents agents sont contradictoires, la couche tactique est responsable d'initier un processus de résolution pour maintenir la cohérence de l'analyse.
5.  **Agréger et Rapporter** : Collecter les résultats des tâches individuelles, les agréger en un rapport cohérent et le transmettre à la couche stratégique.

En résumé, la couche tactique gère le **"Comment"** et le **"Quand"** de l'analyse.

## Composants Clés

-   **`manager.py` / `coordinator.py`**: Le `TacticalManager` ou `TaskCoordinator` est le composant central qui orchestre la décomposition des plans et la dispatch des tâches.
-   **`monitor.py`**: Contient la logique pour le suivi de la progression des tâches.
-   **`resolver.py`**: Implémente les stratégies pour détecter et résoudre les conflits entre les résultats des agents.
-   **`state.py`**: Modélise l'état interne de la couche tactique, incluant la liste des tâches, leur statut, et les résultats intermédiaires.