# Fixtures pour les Tests

## Objectif

Ce répertoire contient des **fixtures** `pytest` réutilisables, conçues pour simplifier l'écriture des tests, en particulier pour les tests d'intégration et les tests d'agents. Les fixtures fournissent des objets, des données et des configurations de test standardisés, garantissant ainsi que les tests sont cohérents, lisibles et faciles à maintenir.

## Fixtures Fournies

### 1. Fixtures d'Agents et d'Adaptateurs

*   **`agent_fixtures.py`**: Ce module est au cœur de la configuration des tests pour les agents d'analyse d'argumentation. Il fournit :
    *   Des instances pré-configurées d'agents (`InformalAgent`, `EnhancedInformalAgent`).
    *   Des instances des outils utilisés par ces agents (`FallacyDetector`, `RhetoricalAnalyzer`, etc.).
    *   Des versions réelles et mockées des adaptateurs d'agents (`ExtractAgentAdapter`, `InformalAgentAdapter`) et du `MessageMiddleware`.
    *   Des définitions de sophismes (`fallacy_definitions`) pour initialiser les détecteurs.

### 2. Fixtures pour les Tests d'Intégration

*   **`integration_fixtures.py`**: Ce module est essentiel pour les tests qui nécessitent une interaction avec des bibliothèques Java via JPype.
    *   **`integration_jvm`**: Une fixture de portée `session` qui démarre une véritable JVM et la rend disponible pour toute la durée de la session de test. Elle s'assure que le vrai module `jpype` est utilisé et que les JARs de Tweety sont correctement chargés.
    *   **Fixtures de classes Tweety**: Une série de fixtures (`dung_classes`, `tweety_logics_classes`, `dialogue_classes`, etc.) qui dépendent de `integration_jvm` pour fournir des objets `JClass` prêts à l'emploi pour les différentes classes de la bibliothèque Tweety. Cela évite de devoir redéfinir ces importations dans chaque fichier de test.

### 3. Fixtures de Données de Test

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

from tests.fixtures.agent_fixtures import informal_agent
from tests.fixtures.rhetorical_data_fixtures import example_text

def test_informal_agent_analysis(informal_agent, example_text):
    """
    Teste que l'agent informel analyse correctement un texte.
    `informal_agent` et `example_text` sont fournis par les fixtures.
    """
    # Act
    result = informal_agent.analyze_text(example_text)

    # Assert
    assert "fallacies" in result
    assert len(result["fallacies"]) > 0
```

L'utilisation de ces fixtures centralisées garantit que les objets complexes sont initialisés de manière cohérente à travers toute la suite de tests.
