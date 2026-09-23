# Fixtures pour les Tests

## Objectif

Ce répertoire contient des **fixtures** `pytest` réutilisables, conçues pour simplifier l'écriture des tests, en particulier pour les tests d'intégration et les tests d'agents. Les fixtures fournissent des objets, des données et des configurations de test standardisés, garantissant ainsi que les tests sont cohérents, lisibles et faciles à maintenir.

## Fixtures Fournies

> **Agents** : il n'y a pas de module de fixtures d'agents. Chaque test construit l'agent qu'il exerce avec son API actuelle (voir `tests/unit/argumentation_analysis/agents/`). L'ancien `agent_fixtures.py` a été retiré en #2416 : il ne s'importait plus depuis 2025-07 et aucun test ne le chargeait.

### 1. Fixtures pour les Tests d'Intégration

*   **`integration_fixtures.py`**: Ce module est essentiel pour les tests qui nécessitent une interaction avec des bibliothèques Java via JPype.
    *   **`integration_jvm`**: Une fixture de portée `session` qui démarre une véritable JVM et la rend disponible pour toute la durée de la session de test. Elle s'assure que le vrai module `jpype` est utilisé et que les JARs de Tweety sont correctement chargés.
    *   **Fixtures de classes Tweety**: Une série de fixtures (`dung_classes`, `tweety_logics_classes`, `dialogue_classes`, etc.) qui dépendent de `integration_jvm` pour fournir des objets `JClass` prêts à l'emploi pour les différentes classes de la bibliothèque Tweety. Cela évite de devoir redéfinir ces importations dans chaque fichier de test.

### 2. Fixtures de Données de Test

*   **`rhetorical_data_fixtures.py`**: Ce module fournit un ensemble de données standard pour tester les fonctionnalités d'analyse rhétorique et de détection de sophismes.
    *   **Textes et corpus**: Des textes d'exemple (`example_text`, `example_corpus`) contenant divers sophismes.
    *   **Fichiers temporaires**: Des fixtures qui créent des fichiers `.txt` ou `.json` temporaires (`example_text_file`, `example_analysis_result_file`) pour tester les opérations de lecture/écriture.
    *   **Résultats d'analyse**: Des exemples de résultats d'analyse (`example_fallacies`, `example_rhetorical_analysis`) pour vérifier que les agents produisent des sorties conformes au format attendu.
    *   **Définitions**: Des listes de définitions de sophismes et de catégories (`example_fallacy_definitions`, `example_fallacy_categories`) pour les tests qui nécessitent ces structures de données.

## Utilisation

Pour utiliser ces fixtures, il suffit de les déclarer comme arguments dans vos fonctions de test. `pytest` se chargera de les injecter automatiquement.

**Exemple :**

```python
# Dans un fichier de test (ex: tests/unit/test_my_analyzer.py)

from tests.fixtures.rhetorical_data_fixtures import example_text, example_fallacies

def test_fixtures_are_injected(example_text, example_fallacies):
    """
    `example_text` et `example_fallacies` sont fournis par les fixtures :
    les importer dans le module de test suffit pour que pytest les injecte.
    """
    assert example_text
    assert all("type" in f and "confidence" in f for f in example_fallacies)
```

L'utilisation de ces fixtures centralisées garantit que les objets complexes sont initialisés de manière cohérente à travers toute la suite de tests.
