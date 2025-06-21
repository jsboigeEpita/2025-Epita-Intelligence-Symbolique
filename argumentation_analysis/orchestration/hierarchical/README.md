# Architecture d'Orchestration Hiérarchique

Ce répertoire contient l'implémentation d'une architecture d'orchestration à trois niveaux, conçue pour gérer des tâches d'analyse complexes en décomposant le problème.

## Les Trois Niveaux

L'architecture est divisée en trois couches de responsabilité distinctes :

1.  **Stratégique (`strategic/`)**
    -   **Rôle :** C'est le plus haut niveau de l'abstraction. Le `StrategicManager` est responsable de l'analyse globale de la requête initiale. Il interprète l'entrée, détermine les objectifs généraux de l'analyse et élabore un plan stratégique de haut niveau.
    -   **Sortie :** Une liste d'objectifs clairs et un plan d'action global.

2.  **Tactique (`tactical/`)**
    -   **Rôle :** Le niveau intermédiaire. Le `TacticalCoordinator` prend en entrée les objectifs définis par le niveau stratégique et les décompose en une série de tâches plus petites, concrètes et exécutables. Il gère la dépendance entre les tâches et planifie leur ordre d'exécution.
    -   **Sortie :** Une liste de tâches prêtes à être exécutées par le niveau opérationnel.

3.  **Opérationnel (`operational/`)**
    -   **Rôle :** Le niveau le plus bas, responsable de l'exécution. L'`OperationalManager` prend les tâches définies par le niveau tactique et les exécute en faisant appel aux outils, agents ou services appropriés (par exemple, un analyseur de sophismes, un extracteur de revendications, etc.).
    -   **Sortie :** Les résultats concrets de chaque tâche exécutée.

## Interfaces (`interfaces/`)

Le répertoire `interfaces` définit les contrats de communication (les "frontières") entre les différentes couches. Ces interfaces garantissent que chaque niveau peut interagir avec ses voisins de manière standardisée, ce qui facilite la modularité et la testabilité du système.

-   `strategic_tactical.py`: Définit comment le niveau tactique consomme les données du niveau stratégique.
-   `tactical_operational.py`: Définit comment le niveau opérationnel consomme les tâches du niveau tactique.

Ce modèle hiérarchique permet de séparer les préoccupations, rendant le système plus facile à comprendre, à maintenir et à étendre.