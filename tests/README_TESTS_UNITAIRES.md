# Tests Unitaires pour les Modules Prioritaires

Ce document explique comment exécuter les tests unitaires pour les modules prioritaires identifiés avec une faible couverture de tests.

## Modules Prioritaires

Les modules prioritaires suivants ont été identifiés avec une faible couverture de tests :

1. **orchestration.hierarchical.tactical** (11.78%)
2. **orchestration.hierarchical.operational.adapters** (12.44%)
3. **agents.tools.analysis.enhanced** (12.90%)
4. **agents.core.informal** (16.23%)
5. **agents.tools.analysis** (16.46%)

## Tests Unitaires Implémentés

Les tests unitaires suivants ont été implémentés pour les modules prioritaires :

1. **orchestration.hierarchical.tactical**
   - `tests/test_tactical_coordinator.py` : Tests pour le coordinateur tactique
   - `tests/test_tactical_monitor.py` : Tests pour le moniteur tactique
   - `tests/test_tactical_resolver.py` : Tests pour le résolveur de conflits tactique

2. **orchestration.hierarchical.operational.adapters**
   - `tests/test_extract_agent_adapter.py` : Tests pour l'adaptateur d'agent d'extraction

3. **agents.tools.analysis.enhanced**
   - `tests/test_enhanced_complex_fallacy_analyzer.py` : Tests pour l'analyseur de sophismes complexes amélioré

4. **agents.core.informal**
   - `tests/test_informal_definitions.py` : Tests pour les définitions de l'agent informel

## Mocks pour les Dépendances Problématiques

Les mocks suivants ont été créés pour les dépendances problématiques :

1. **numpy** : `tests/mocks/numpy_mock.py`
2. **pandas** : `tests/mocks/pandas_mock.py`
3. **jpype** : `tests/mocks/jpype_mock.py` (déjà existant)

Ces mocks sont automatiquement utilisés lors de l'exécution des tests grâce aux fixtures définies dans `tests/conftest.py`.

## Exécution des Tests

### Exécuter tous les tests

Pour exécuter tous les tests unitaires :

```bash
pytest
```

### Exécuter les tests pour un module spécifique

Pour exécuter les tests pour un module spécifique :

```bash
pytest tests/test_tactical_coordinator.py
pytest tests/test_tactical_monitor.py
pytest tests/test_tactical_resolver.py
pytest tests/test_extract_agent_adapter.py
pytest tests/test_enhanced_complex_fallacy_analyzer.py
pytest tests/test_informal_definitions.py
```

### Exécuter les tests avec la couverture de code

Pour exécuter les tests avec la génération d'un rapport de couverture :

```bash
pytest --cov=argumentation_analysis
```

Pour générer un rapport HTML détaillé :

```bash
pytest --cov=argumentation_analysis --cov-report=html
```

Le rapport HTML sera généré dans le répertoire `htmlcov/`.

## Approche d'Isolation des Dépendances

L'approche d'isolation des dépendances problématiques (numpy, pandas, jpype) a été mise en œuvre comme suit :

1. **Création de mocks** : Des mocks ont été créés pour simuler les fonctionnalités des dépendances problématiques.
2. **Configuration automatique** : Les mocks sont automatiquement configurés lors de l'exécution des tests grâce aux fixtures définies dans `conftest.py`.
3. **Patching des modules** : Les modules qui utilisent les dépendances problématiques sont patchés pour utiliser les mocks.

Cette approche permet d'exécuter les tests sans avoir besoin des dépendances réelles, ce qui résout les problèmes d'importation et d'incompatibilités avec l'environnement de test.

## Cas de Test Implémentés

Les tests unitaires implémentés couvrent les cas suivants :

1. **Tests d'initialisation** : Vérification que les objets sont correctement initialisés.
2. **Tests de fonctionnalités de base** : Vérification que les méthodes de base fonctionnent correctement.
3. **Tests de cas limites** : Vérification du comportement dans des cas limites (entrées invalides, etc.).
4. **Tests de conditions d'erreur** : Vérification du comportement en cas d'erreur.

## Amélioration de la Couverture

Ces tests unitaires devraient améliorer significativement la couverture de code des modules prioritaires. Pour continuer à améliorer la couverture, les actions suivantes peuvent être entreprises :

1. **Ajouter des tests pour les autres modules** : Créer des tests unitaires pour les autres modules avec une faible couverture.
2. **Ajouter des tests pour les cas non couverts** : Identifier les parties du code qui ne sont pas couvertes par les tests existants et ajouter des tests pour ces parties.
3. **Ajouter des tests d'intégration** : Créer des tests d'intégration pour vérifier l'interaction entre les différents modules.

## Problèmes Connus

Si vous rencontrez des problèmes lors de l'exécution des tests, veuillez vérifier les points suivants :

1. **Dépendances manquantes** : Assurez-vous que toutes les dépendances requises sont installées.
2. **Mocks incomplets** : Si un test échoue en raison d'une fonctionnalité manquante dans un mock, vous devrez peut-être mettre à jour le mock correspondant.
3. **Problèmes d'importation** : Si un test échoue en raison d'un problème d'importation, vérifiez que le module est correctement importé et que les mocks sont correctement configurés.

## Conclusion

Ces tests unitaires constituent une première étape importante pour améliorer la couverture de code des modules prioritaires. Ils fournissent une base solide pour continuer à améliorer la qualité du code et la fiabilité du système.