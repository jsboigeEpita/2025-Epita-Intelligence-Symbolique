# Tests d'Intégration

## Objectif

Ce répertoire contient les tests d'intégration du projet. Contrairement aux tests unitaires qui valident des composants isolés, ces tests ont pour but de vérifier que plusieurs parties du système fonctionnent correctement ensemble pour réaliser des workflows complets et des scénarios d'utilisation réalistes.

L'objectif est de s'assurer de la robustesse des interactions entre les différents services, agents, et couches logiques du système.

## Organisation des Tests

Les tests d'intégration sont organisés en sous-répertoires et fichiers thématiques :

*   ### [jpype_tweety/](./jpype_tweety/README.md)
    *   **Rôle :** Valide l'intégration bas niveau entre Python et la bibliothèque de raisonnement Java **Tweety** via **JPype**.
    *   **Contenu :** Ces tests s'assurent que la JVM peut être démarrée, que les classes Java de Tweety peuvent être instanciées, et que les opérations logiques fondamentales (parsing, raisonnement, manipulation de théories) fonctionnent comme attendu depuis Python. C'est la base sur laquelle repose toute la logique formelle du projet.
    *   *Pour plus de détails, consultez le [README de jpype_tweety](./jpype_tweety/README.md).*

*   ### Tests d'Intégration de Haut Niveau (fichiers à la racine)

    Les fichiers `.py` situés directement dans ce répertoire testent des workflows applicatifs complets en assemblant plusieurs composants majeurs :

    *   **`test_agents_tools_integration.py` :** Vérifie que les agents d'analyse (ex: `InformalAnalysisAgent`) peuvent correctement utiliser et coordonner leurs outils internes (analyseurs de sophismes, évaluateurs de contexte, etc.) pour réaliser une analyse complète.

    *   **`test_cluedo_orchestration_integration.py` :** Simule un scénario complexe d'orchestration multi-agents (un jeu de Cluedo) pour valider la collaboration, la gestion d'état et le déroulement d'un dialogue entre plusieurs agents (Sherlock, Watson).

    *   **`test_logic_agents_integration.py` :** Teste le pipeline complet des agents logiques : conversion de texte en base de croyances formelle, génération de requêtes, exécution via le `TweetyBridge`, et interprétation des résultats.

    *   **`test_logic_api_integration.py` :** Valide les endpoints de l'API Web (Flask) qui exposent les services logiques. Ce test assure que la couche de service web est correctement intégrée avec la logique métier sous-jacente.

    *   **`test_notebooks_structure.py` :** Un test de "méta-intégration" qui garantit que les notebooks Jupyter fournis comme tutoriels sont bien formés et fonctionnels.

## Stratégie de Test

Ces tests utilisent fréquemment des **mocks** pour simuler les dépendances externes (comme les appels aux LLM ou les bases de données) afin de se concentrer exclusivement sur la validation des **interactions et des flux de données** entre les composants internes du projet.