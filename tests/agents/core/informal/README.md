# Tests de l'Agent d'Analyse Informelle

Ce répertoire contient les tests unitaires pour l'agent d'analyse informelle (`InformalAnalysisAgent`) et ses composants associés. Cet agent est spécialisé dans l'analyse d'arguments en langage naturel pour y détecter des sophismes et d'autres caractéristiques rhétoriques.

## Objectif des Tests

L'objectif principal est de garantir le bon fonctionnement de l'agent d'analyse informelle, notamment :
- Sa capacité à être initialisé correctement avec ses dépendances (comme le kernel sémantique).
- La validité de ses méthodes d'analyse (détection de sophismes, identification d'arguments).
- La gestion correcte de la taxonomie des sophismes.
- La robustesse de l'agent face à des erreurs ou des configurations manquantes.

## Modules et Fichiers Testés

- **`InformalAnalysisAgent`**: Le comportement général de l'agent, ses capacités et ses méthodes d'analyse principales sont testés dans :
    - [`test_informal_agent.py`](test_informal_agent.py:1): Valide les méthodes d'analyse de l'agent comme `analyze_fallacies`, `analyze_argument`, et `identify_arguments`.
    - [`test_informal_agent_creation.py`](test_informal_agent_creation.py:1): S'assure que l'agent est correctement initialisé, que ses composants sont configurés et que ses informations (capacités, nom) sont correctes.
    - [`test_informal_analysis_methods.py`](test_informal_analysis_methods.py:1): Se concentre sur les méthodes d'analyse de haut niveau comme `analyze_text` et la catégorisation des sophismes.
    - [`test_informal_error_handling.py`](test_informal_error_handling.py): (Fichier non lu, mais supposé exister basé sur le nom) Teste la gestion des erreurs, comme l'absence de fonctions sémantiques ou des problèmes avec le kernel.

- **`InformalAnalysisPlugin` et Définitions**: Les fonctions et la logique sous-jacentes à l'agent, notamment la gestion de la taxonomie des sophismes, sont testées dans :
    - [`test_informal_definitions.py`](test_informal_definitions.py:1): Valide le chargement et l'exploration de la taxonomie des sophismes, ainsi que la configuration du kernel sémantique avec le plugin informel.

## Structure des Tests

- **Fixtures `pytest`**: Des fixtures sont utilisées pour créer des instances mockées du kernel sémantique, des analyseurs et de l'agent lui-même, permettant des tests isolés et reproductibles. Voir [`fixtures.py`](fixtures.py:1).
- **Tests Asynchrones**: Les méthodes de l'agent étant asynchrones, les tests sont marqués avec `@pytest.mark.asyncio` et utilisent `async/await`.
- **Mocking**: `unittest.mock` est largement utilisé pour patcher les dépendances externes (comme le `semantic_kernel`) et simuler les retours des appels LLM.

## Dépendances

- `pytest` et `pytest-asyncio`
- `unittest.mock`
- `semantic_kernel`
- Les modules applicatifs de `argumentation_analysis/agents/core/informal/`.