# Tests des Adaptateurs d'Agents Opérationnels

Ce répertoire contient les tests unitaires et d'intégration pour les adaptateurs d'agents utilisés au niveau opérationnel de l'architecture hiérarchique.

## Objectif des Adaptateurs

Les adaptateurs servent de pont entre le `OperationalManager` et les implémentations spécifiques des agents (par exemple, `ExtractAgent`, `InformalAgent`, `PLAgent`). Ils sont responsables de :
*   Initialiser et configurer l'agent sous-jacent.
*   Traduire les requêtes de tâches génériques du `OperationalManager` en appels spécifiques aux méthodes de l'agent.
*   Formater les résultats de l'agent pour qu'ils soient conformes à la structure attendue par le `OperationalManager`.
*   Gérer l'état et le cycle de vie de l'agent qu'ils encapsulent.

## Fichiers de Test Notables

*   [`test_extract_agent_adapter.py`](test_extract_agent_adapter.py:1): Teste l'`ExtractAgentAdapter`, couvrant son initialisation, la gestion des capacités, et le traitement de diverses tâches d'extraction et de normalisation.
*   (D'autres adaptateurs, comme `InformalAgentAdapter` ou `PLAgentAdapter`, auraient leurs tests ici également.)

## Approche de Test

Les tests dans ce répertoire utilisent typiquement `pytest` et des mocks pour isoler le comportement de l'adaptateur. Les dépendances externes comme l'agent réel ou le middleware sont souvent mockées pour se concentrer sur la logique de l'adaptateur lui-même.