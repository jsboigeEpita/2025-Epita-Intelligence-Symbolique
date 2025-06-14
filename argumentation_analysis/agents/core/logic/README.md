# Module des Agents Logiques (`argumentation_analysis.agents.core.logic`)

Ce module fournit les composants nécessaires à la création et à l'utilisation d'agents capables d'effectuer des raisonnements basés sur différentes logiques formelles. Il s'appuie sur `TweetyProject` pour les capacités de raisonnement sous-jacentes.

## Structure et Composants Clés

### Hiérarchie des Classes d'Agents
Les agents logiques de ce module suivent la hiérarchie suivante :

1.  **`BaseAgent`** ([`argumentation_analysis.agents.core.abc.agent_bases.BaseAgent`](../../abc/agent_bases.py:24)): Classe de base abstraite pour tous les agents du système.
2.  **`BaseLogicAgent`** ([`argumentation_analysis.agents.core.abc.agent_bases.BaseLogicAgent`](../../abc/agent_bases.py:159)): Hérite de `BaseAgent` et sert de classe de base abstraite pour tous les agents logiques. Elle définit l'interface commune pour la manipulation d'ensembles de croyances, la génération et l'exécution de requêtes, etc.
3.  **Agents Logiques Concrets** :
    *   [`PropositionalLogicAgent`](propositional_logic_agent.py:0) : Agent pour la logique propositionnelle. Sert de référence et est bien documenté.
    *   [`FirstOrderLogicAgent`](first_order_logic_agent.py:0) : Agent pour la logique du premier ordre.
    *   [`ModalLogicAgent`](modal_logic_agent.py:0) : Agent pour la logique modale.

### Autres Composants Essentiels

*   **[`BeliefSet`](belief_set.py:0) et ses sous-classes (`PropositionalBeliefSet`, `FirstOrderBeliefSet`, `ModalBeliefSet`)**:
    Ces classes représentent les ensembles de croyances (bases de connaissances) dans les différentes logiques. Elles encapsulent le contenu formel des croyances.

*   **[`TweetyBridge`](tweety_bridge.py:0)**:
    Cette classe cruciale sert de pont entre le code Python et la bibliothèque Java `TweetyProject`. Elle gère l'initialisation de la JVM et fournit des méthodes pour :
    *   Parser et valider des formules et des ensembles de croyances.
    *   Exécuter des requêtes logiques pour la logique propositionnelle, la logique du premier ordre et la logique modale.

*   **[`LogicAgentFactory`](logic_factory.py:0)**:
    Une factory responsable de la création d'instances des agents logiques appropriés (`PropositionalLogicAgent`, `FirstOrderLogicAgent`, `ModalLogicAgent`) en fonction d'un type de logique spécifié.

*   **[`QueryExecutor`](query_executor.py:0)**:
    Fournit une interface unifiée pour exécuter des requêtes logiques sur un `BeliefSet`. Il utilise `TweetyBridge` en interne et sélectionne la méthode d'exécution appropriée en fonction du type de logique de l'ensemble de croyances.

## Flux de Travail Typique

1.  Un `LogicAgentFactory` est utilisé pour créer une instance d'un agent logique spécifique (par exemple, `FirstOrderLogicAgent`).
2.  L'agent utilise ses fonctions sémantiques (prompts LLM) pour convertir un texte en langage naturel en un `BeliefSet` spécifique à sa logique (par exemple, `FirstOrderBeliefSet`). Cette conversion peut impliquer une validation via `TweetyBridge`.
3.  L'agent génère ensuite des requêtes logiques pertinentes, également via des fonctions sémantiques.
4.  Les requêtes sont exécutées sur le `BeliefSet` en utilisant `QueryExecutor` (qui s'appuie sur `TweetyBridge`).
5.  Enfin, l'agent interprète les résultats des requêtes en langage naturel, à nouveau à l'aide de fonctions sémantiques.

Ce module vise à abstraire la complexité de l'interaction avec les solveurs logiques et à fournir une interface de haut niveau pour intégrer le raisonnement formel dans des systèmes d'IA plus larges.