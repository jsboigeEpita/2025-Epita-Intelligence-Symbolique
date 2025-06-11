# Tests des Agents Logiques

Ce répertoire contient les tests unitaires pour les agents basés sur la logique formelle. Ces agents sont conçus pour traduire le langage naturel en représentations logiques formelles, effectuer des raisonnements sur ces représentations et interpréter les résultats.

## Objectif des Tests

L'objectif principal est de valider la chaîne de traitement complète des agents logiques, de la conversion du texte à l'interprétation des résultats de raisonnement. Les tests visent à garantir :
- La conversion correcte du langage naturel en ensembles de croyances (`BeliefSet`) pour différentes logiques (propositionnelle, premier ordre, modale).
- La génération de requêtes logiques valides et pertinentes.
- L'interaction correcte avec le `TweetyBridge` pour l'exécution des requêtes.
- La gestion des succès, des échecs et des erreurs tout au long du processus.
- La validation de la syntaxe des formules et des ensembles de croyances.

## Modules Testés

- **`PropositionalLogicAgent`**: Testé dans [`test_propositional_logic_agent.py`](test_propositional_logic_agent.py:1).
- **`FirstOrderLogicAgent`**: Testé dans [`test_first_order_logic_agent.py`](test_first_order_logic_agent.py:1).
- **`ModalLogicAgent`**: Testé dans [`test_modal_logic_agent.py`](test_modal_logic_agent.py:1).
- **`LogicFactory`**: Testé dans [`test_logic_factory.py`](test_logic_factory.py:1), qui valide la création des bons types d'agents.
- **`BeliefSet`**: Testé dans [`test_belief_set.py`](test_belief_set.py:1), qui vérifie la manipulation des ensembles de croyances.
- **`TweetyBridge`**: Testé dans [`test_tweety_bridge.py`](test_tweety_bridge.py:1), qui assure la communication avec la bibliothèque de raisonnement Java Tweety.

## Structure des Tests

Chaque fichier de test d'agent (propositionnel, premier ordre, modal) suit une structure similaire :
1.  **Initialisation (`setup_method`)**: Met en place un `Kernel` sémantique mocké et un `TweetyBridge` mocké pour isoler l'agent.
2.  **Tests de Conversion (`text_to_belief_set`)**: Vérifient que le texte est correctement converti en un `BeliefSet` syntaxiquement valide.
3.  **Tests de Génération de Requêtes (`generate_queries`)**: S'assurent que des requêtes pertinentes et valides sont générées à partir d'un texte et d'un `BeliefSet`.
4.  **Tests d'Exécution de Requêtes (`execute_query`)**: Valident que l'agent appelle correctement le `TweetyBridge` et gère les résultats (accepté, rejeté, erreur).
5.  **Tests d'Interprétation (`interpret_results`)**: Vérifient que l'agent peut formuler une interprétation en langage naturel des résultats du raisonnement.

## Dépendances

- `pytest` et `pytest-asyncio`
- `unittest.mock` pour le mocking intensif du `Kernel` et du `TweetyBridge`.
- `semantic_kernel`
- Les modules applicatifs de `argumentation_analysis/agents/core/logic/`.