# Tests d'Intégration

Ce répertoire contient les tests d'intégration du projet. Ces tests vérifient l'interaction correcte entre plusieurs composants ou modules du système.

## Objectifs des Tests d'Intégration

*   S'assurer que les différents modules collaborent comme prévu.
*   Valider les flux de données et de contrôle entre les composants.
*   Détecter les problèmes d'interface et d'interaction.

## Fichiers de Test Notables

*   [`test_agents_tools_integration.py`](test_agents_tools_integration.py:1): Teste l'intégration entre les agents (par exemple, `InformalAgent`) et leurs outils d'analyse (détecteurs de sophismes, analyseurs contextuels, etc.).
*   [`test_logic_agents_integration.py`](test_logic_agents_integration.py:1): Valide l'intégration des `LogicAgentFactory` et des agents logiques (propositionnel, premier ordre, modal) avec un Kernel sémantique mocké et TweetyBridge.
*   [`test_logic_api_integration.py`](test_logic_api_integration.py:1): Teste l'intégration des endpoints de l'API web pour les fonctionnalités logiques (ex: `/api/logic/*`) et du `LogicService` sous-jacent, en utilisant des mocks pour les agents logiques et le Kernel.
*   [`test_notebooks_execution.py`](test_notebooks_execution.py:1): (À compléter en fonction du contenu de ce fichier)
*   [`test_tactical_operational_integration.py`](test_tactical_operational_integration.py:1): (À compléter en fonction du contenu de ce fichier)
*   `jpype_tweety/`: Contient des tests d'intégration spécifiques à l'interaction avec TweetyLib via JPype.

## Exécution des Tests

Ces tests sont généralement exécutés avec les autres tests du projet via la commande pytest standard. Consulter le `README.md` principal du répertoire `tests/` pour plus de détails sur l'exécution des tests.