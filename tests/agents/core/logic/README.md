# Tests des Composants Logiques des Agents

Ce répertoire contient les tests unitaires pour les composants logiques fondamentaux des agents, tels que la représentation des croyances, les moteurs de raisonnement pour différentes logiques (propositionnelle, premier ordre, modale), et les usines de création d'objets logiques.

## Objectifs des Tests :

*   Valider la correction et la robustesse des structures de données logiques (ex: ensembles de croyances).
*   Assurer le bon fonctionnement des opérations sur ces structures (ex: ajout, suppression, révision de croyances).
*   Tester l'implémentation des différents agents logiques et leur capacité à effectuer des inférences.
*   Vérifier la conformité des composants avec les formalismes logiques sous-jacents.
*   Valider l'intégration avec des bibliothèques externes de raisonnement (ex: Tweety).

## Fichiers Inclus (liste non exhaustive) :

*   [`test_belief_set.py`](test_belief_set.py:1): Teste la classe `BeliefSet` qui est cruciale pour la gestion des connaissances et des croyances des agents logiques. Valide les opérations d'ajout, de suppression, de révision et de requête sur les ensembles de croyances.
*   [`test_examples.py`](test_examples.py:1): Contient des tests basés sur des exemples concrets d'utilisation des agents et des systèmes logiques, illustrant des scénarios de raisonnement.
*   [`test_first_order_logic_agent.py`](test_first_order_logic_agent.py:1): Tests spécifiques à l'agent basé sur la logique du premier ordre, incluant la gestion des quantificateurs et des prédicats.
*   [`test_logic_factory.py`](test_logic_factory.py:1): Valide la `LogicFactory` responsable de la création des différents types d'agents logiques et de leurs composants.
*   [`test_propositional_logic_agent.py`](test_propositional_logic_agent.py:1): Tests pour l'agent basé sur la logique propositionnelle, couvrant l'initialisation, l'interaction avec le Kernel sémantique, la conversion texte-croyances, la validation et l'exécution de requêtes via TweetyBridge (mocké).
*   [`test_modal_logic_agent.py`](test_modal_logic_agent.py:1): Tests pour l'agent basé sur la logique modale, couvrant l'initialisation, l'interaction avec le Kernel sémantique, la conversion texte-croyances, la validation et l'exécution de requêtes via TweetyBridge (mocké).
*   [`test_abstract_logic_agent.py`](test_abstract_logic_agent.py:1): Tests pour la classe de base abstraite des agents logiques.
*   [`test_query_executor.py`](test_query_executor.py:1): Tests pour l'exécuteur de requêtes logiques.
*   [`test_tweety_bridge.py`](test_tweety_bridge.py:1): Tests pour le pont avec la bibliothèque Tweety.

Ces tests sont fondamentaux pour garantir la fiabilité du raisonnement des agents au sein du système.