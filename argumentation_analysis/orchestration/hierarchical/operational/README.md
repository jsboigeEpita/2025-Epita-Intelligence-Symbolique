# Couche Opérationnelle

## Rôle et Responsabilités

La couche opérationnelle est la couche d'**exécution** de l'architecture. C'est ici que le travail concret est effectué par les agents spécialisés. Elle est responsable du "Faire".

Ses missions principales sont :

1.  **Exécuter les Tâches** : Recevoir des tâches atomiques et bien définies de la couche tactique (ex: "identifie les sophismes dans ce paragraphe").
2.  **Gérer les Agents** : Sélectionner l'agent ou l'outil le plus approprié pour une tâche donnée à partir d'un registre de capacités.
3.  **Communiquer via les Adaptateurs** : Utiliser le sous-répertoire `adapters/` pour traduire la tâche générique en un appel spécifique que l'agent cible peut comprendre. L'adaptateur est également responsable de standardiser la réponse de l'agent avant de la remonter. C'est un point clé pour l'extensibilité, permettant d'intégrer de nouveaux agents sans modifier le reste de la couche.
4.  **Gérer l'État d'Exécution** : Maintenir un état (`state.py`) qui suit les détails de l'exécution en cours : quelle tâche est active, quels sont les résultats bruts, etc.
5.  **Remonter les Résultats** : Transmettre les résultats de l'exécution à la couche tactique pour l'agrégation et l'analyse.

En résumé, la couche opérationnelle est le "bras armé" de l'orchestration, effectuant le travail demandé par les couches supérieures.

## Composants Clés

-   **`manager.py`** : L'`OperationalManager` reçoit les tâches de la couche tactique, utilise le registre pour trouver le bon agent, invoque cet agent via son adaptateur et remonte le résultat.
-   **`adapters/`** : Répertoire crucial contenant les traducteurs spécifiques à chaque agent. Chaque adaptateur garantit que la couche opérationnelle peut communiquer avec un agent de manière standardisée.
-   **`agent_registry.py`** : Maintient un catalogue des agents disponibles et de leurs capacités, permettant au `manager` de faire des choix éclairés.
-   **`state.py`** : Contient le `OperationalState` qui stocke les informations relatives à l'exécution des tâches en cours.