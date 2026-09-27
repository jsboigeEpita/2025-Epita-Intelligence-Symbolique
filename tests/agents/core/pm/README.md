# Tests des Agents de Gestion de Projet (PM)

Ce répertoire contient les tests de l'agent d'enquête du paquet `agents/core/pm/`.

## Modules Testés

- **`SherlockEnqueteAgent`** : testé dans [`test_sherlock_enquete_agent.py`](test_sherlock_enquete_agent.py:1). Cet agent hérite directement de `BaseAgent` (et non d'un PM — la classe `ProjectManagerAgent` qui cohabitait avec lui a été retirée en #2699) et mène des « enquêtes ». Les tests vérifient :
    - L'instanciation et l'héritage (`BaseAgent`).
    - Le prompt système par défaut et sa personnalisation.
    - Les interactions JTMS (ajout de croyance, formulation d'hypothèse).
    - La gestion d'erreurs et la validation de configuration.

## Structure des Tests

- **Fixtures `pytest`** : `sherlock_agent` et `agent_factory` construisent l'agent sur un kernel réel.
- **Authentique, sans mocks** : « Phase 3A — purge complète des mocks » ; les tests n'espionnent plus un constructeur parent ni ne mockent le kernel.
- **Tests asynchrones** : les méthodes de l'agent qui dialoguent avec le kernel sont asynchrones (`asyncio_mode = auto`).

## Dépendances

- `pytest` et `pytest-asyncio`
- `semantic_kernel`
- `argumentation_analysis/agents/core/pm/sherlock_enquete_agent.py`
