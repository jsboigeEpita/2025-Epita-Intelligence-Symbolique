# Tests des Agents de Gestion de Projet (PM)

Ce répertoire contient les tests pour les agents de type "Project Manager" (PM), qui sont conçus pour orchestrer des tâches complexes, gérer un état et interagir avec d'autres composants ou agents.

## Objectif des Tests

L'objectif est de valider le comportement des agents PM, en particulier leur capacité à gérer un état et à exécuter des actions spécifiques à leur domaine.

## Modules Testés

- **`SherlockEnqueteAgent`**: Testé dans [`test_sherlock_enquete_agent.py`](test_sherlock_enquete_agent.py:1). Cet agent est une spécialisation de `ProjectManagerAgent` et est conçu pour mener des "enquêtes". Les tests vérifient :
    - L'initialisation correcte de l'agent, y compris l'appel au constructeur de la classe parente.
    - La capacité à interagir avec un `EnqueteStatePlugin` (mocké) pour récupérer la description d'une affaire et ajouter de nouvelles hypothèses.
    - La gestion des erreurs lorsque les interactions avec le plugin échouent.

## Structure des Tests

- **Fixtures `pytest`**: Une fixture est utilisée pour fournir un `Kernel` sémantique mocké.
- **Spying**: `mocker.spy` est utilisé pour s'assurer que le constructeur de la classe parente (`ProjectManagerAgent`) est appelé correctement.
- **Tests Asynchrones**: Les méthodes de l'agent qui interagissent avec le kernel sont asynchrones et testées avec `@pytest.mark.asyncio`.
- **Mocking**: `unittest.mock` est utilisé pour simuler le `Kernel` et ses plugins, permettant de tester la logique de l'agent de manière isolée.

## Dépendances

- `pytest` et `pytest-asyncio`
- `unittest.mock`
- `semantic_kernel`
- Les modules applicatifs de `argumentation_analysis/agents/core/pm/`.
