# Tests du Projet d'Intelligence Symbolique

Ce répertoire contient les tests unitaires, d'intégration et fonctionnels du projet d'Intelligence Symbolique.

## Deux Approches pour les Tests

Nous proposons deux approches pour exécuter les tests, en fonction de vos besoins et de votre environnement :

### 1. Approche avec Résolution des Dépendances (Recommandée)

Cette approche consiste à résoudre les problèmes de dépendances (numpy, pandas, jpype) en utilisant des versions spécifiques connues pour être compatibles avec notre environnement de test. Cette approche est recommandée car elle permet de tester le code avec les bibliothèques réelles, ce qui garantit que les tests sont plus représentatifs du comportement en production.

Pour plus de détails sur cette approche, consultez le fichier [README_RESOLUTION_DEPENDANCES.md](README_RESOLUTION_DEPENDANCES.md).

#### Installation des Dépendances

```bash
# Windows (PowerShell)
.\scripts\setup\fix_dependencies.ps1

# Linux/macOS
python scripts/setup/fix_dependencies.py
```

#### Vérification des Dépendances

```bash
# Windows (PowerShell)
.\scripts\setup\test_dependencies.ps1

# Linux/macOS
python scripts/setup/test_dependencies.py
```

### 2. Approche avec Mocks

Cette approche consiste à utiliser des mocks pour les dépendances problématiques (numpy, pandas, jpype). Cette approche peut être utile pour les environnements où l'installation des dépendances réelles est difficile ou impossible, ou pour des tests rapides qui ne nécessitent pas toutes les fonctionnalités des bibliothèques réelles.

Pour plus de détails sur cette approche, consultez le fichier [README_TESTS_UNITAIRES.md](README_TESTS_UNITAIRES.md).

## Structure du Répertoire

- `test_*.py` : Tests unitaires et d'intégration pour les différents modules. (Note: `tests/test_dependencies.py` est en cours d'évaluation pour refactorisation/remplacement par des tests pytest dédiés et des scripts de `scripts/setup/`.)
- `standalone_mock_tests.py` : Script de test autonome avec des mocks internes pour une logique de communication (potentiellement redondant avec les tests de `core.communication`, à évaluer pour refactorisation/suppression).
- `mocks/` : Mocks pour les dépendances problématiques (numpy, pandas, jpype)
- `conftest.py` : Configuration pour pytest
- `fixtures/` : Fixtures réutilisables pour les tests
- `functional/` : Tests fonctionnels de bout en bout
- `integration/` : Tests d'intégration entre modules
- `ADVANCED_TEST_PATTERNS.md` : Documentation des patterns de test avancés
- `test_error_recovery.py` : Script exploratoire pour la récupération d'erreurs (à évaluer pour intégration/refactorisation).

## Modules Prioritaires

Les modules suivants ont été identifiés comme prioritaires pour l'amélioration de la couverture de tests :

1. **orchestration.hierarchical.tactical** (11.78%)
2. **orchestration.hierarchical.operational.adapters** (12.44%)
  - `orchestration/hierarchical/operational/adapters/test_extract_agent_adapter.py` : Tests pour l'adaptateur d'agent d'extraction.
  - (D'autres tests d'adaptateurs à lister ici lorsqu'ils seront traités/créés)
3. **agents.tools.analysis.enhanced** (12.90%)
4. **agents.core.informal** (16.23%)
5. **agents.tools.analysis** (16.46%)

Des tests unitaires avancés ont été implémentés pour ces modules prioritaires afin d'augmenter significativement leur couverture.

### Tests Avancés par Module

#### orchestration.hierarchical.tactical
- `test_tactical_coordinator_advanced.py` : Tests avancés pour le coordinateur tactique
- `test_tactical_monitor_advanced.py` : Tests avancés pour le moniteur tactique
- `test_tactical_resolver_advanced.py` : Tests avancés pour le résolveur de conflits tactique

#### agents.tools.analysis.enhanced
- `agents/tools/analysis/enhanced/test_contextual_fallacy_analyzer.py` : Tests pour l'analyseur contextuel de sophismes amélioré (nouvel emplacement proposé)
- `agents/tools/analysis/enhanced/test_fallacy_severity_evaluator.py` : Tests pour l'évaluateur de gravité des sophismes amélioré (nouvel emplacement proposé)
- `agents/tools/analysis/enhanced/test_complex_fallacy_analyzer.py` : Tests pour l'analyseur de sophismes complexes amélioré (nouvel emplacement proposé)

#### agents.core.informal
- `test_informal_agent_creation.py` : Tests pour la création et l'initialisation des agents informels
- `test_informal_analysis_methods.py` : Tests pour les méthodes d'analyse des agents informels
- `test_informal_error_handling.py` : Tests pour la gestion des erreurs des agents informels

#### agents.tools.analysis
- ~~`test_fallacy_analyzer.py` : Tests pour l'analyseur de sophismes~~ (Obsolète, marqué pour suppression)
- `test_contextual_analyzer.py` : Tests pour l'analyseur contextuel
- `test_rhetorical_results_analyzer.py` : Tests pour l'analyseur de résultats rhétoriques

## Exécution des Tests

### Tests Unitaires et d'Intégration

Pour exécuter tous les tests :

```bash
pytest
```

Pour exécuter un test spécifique :

```bash
pytest tests/test_specific_module.py
```

Pour exécuter les tests d'un module prioritaire spécifique :

```bash
# Pour le module orchestration.hierarchical.tactical
pytest tests/test_tactical_*

# Pour le module agents.tools.analysis.enhanced
pytest tests/test_enhanced_*

# Pour le module agents.core.informal
pytest tests/test_informal_*

# Pour le module agents.tools.analysis
pytest tests/test_fallacy_analyzer.py tests/test_contextual_analyzer.py tests/test_rhetorical_results_analyzer.py
```

### Tests avec Couverture de Code

Pour exécuter les tests avec génération d'un rapport de couverture :

```bash
pytest --cov=argumentation_analysis
```

Pour générer un rapport HTML détaillé :

```bash
pytest --cov=argumentation_analysis --cov-report=html
```

Pour exécuter les tests avec couverture pour un module spécifique :

```bash
pytest --cov=argumentation_analysis.orchestration.hierarchical.tactical tests/test_tactical_*
```

### Interprétation des Résultats des Tests

Lorsque vous exécutez `pytest`, vous obtiendrez un résumé des résultats :
- **`.` (point)** : Indique un test réussi.
- **`F` (FAIL)** : Indique un test qui a échoué à cause d'une assertion (`assert`) incorrecte. Le rapport détaillera quelle assertion a échoué.
- **`E` (ERROR)** : Indique un test qui a provoqué une erreur inattendue (par exemple, une exception non gérée dans le code testé ou dans le test lui-même).
- **`s` (skip)** : Indique un test qui a été sauté (généralement marqué avec `@pytest.mark.skip` ou une condition de saut).
- **`x` (xfail)** : Indique un test qui était attendu comme échouant (`@pytest.mark.xfail`) et qui a effectivement échoué.
- **`X` (XPASS)** : Indique un test qui était attendu comme échouant (`@pytest.mark.xfail`) mais qui a réussi. Cela peut indiquer que le bug attendu a été corrigé.

Le rapport de couverture (généré avec `--cov`) vous montrera quelles parties de votre code ont été exécutées par les tests. Un taux de couverture élevé est souhaitable, mais ne garantit pas l'absence de bugs. Concentrez-vous sur le test des logiques critiques et des cas limites. Le rapport HTML (`--cov-report=html`) est particulièrement utile pour explorer la couverture en détail.

## Conventions de Test

1. **Nommage des fichiers de test** :
   - Les fichiers de test doivent être nommés `test_*.py`
   - Le nom doit clairement indiquer le module testé
   - Les tests avancés doivent inclure `_advanced` dans leur nom

2. **Structure des tests** :
   - Utiliser des fixtures pytest pour la configuration
   - Organiser les tests par fonctionnalité
   - Inclure des tests positifs et négatifs
   - Utiliser des mocks pour isoler les dépendances

3. **Documentation des tests** :
   - Chaque test doit avoir une docstring expliquant son objectif
   - Les cas de test complexes doivent être documentés en détail
   - Les patterns de test avancés sont documentés dans [ADVANCED_TEST_PATTERNS.md](ADVANCED_TEST_PATTERNS.md)

## Patterns de Test Avancés

Pour améliorer la couverture et la qualité des tests, nous avons développé des patterns de test avancés spécifiques à chaque module prioritaire. Ces patterns sont documentés en détail dans le fichier [ADVANCED_TEST_PATTERNS.md](ADVANCED_TEST_PATTERNS.md).

Les principaux patterns incluent :
- Pattern de Test Complet
- Pattern de Test des Cas Limites
- Pattern de Test des Interactions
- Patterns spécifiques pour chaque module prioritaire

## Objectifs de Couverture

| Module | Couverture initiale | Couverture actuelle | Objectif |
|--------|---------------------|---------------------|----------|
| orchestration.hierarchical.tactical | 11.78% | - | 30% |
| orchestration.hierarchical.operational.adapters | 12.44% | - | 30% |
| agents.tools.analysis.enhanced | 12.90% | - | 30% |
| agents.core.informal | 16.23% | - | 30% |
| agents.tools.analysis | 16.46% | - | 30% |
| **Global** | **17.89%** | - | **25%** |

## Documentation Associée

### Plan d'Action pour l'Amélioration des Tests

Un plan d'action détaillé pour l'amélioration des tests et de la couverture de code est disponible dans :
- [Plan d'action pour l'amélioration des tests](../docs/tests/plan_action_tests.md)

### Rapport sur l'État du Dépôt et la Couverture des Tests

Un rapport détaillé sur l'état actuel du dépôt et la couverture des tests est disponible dans :
- [Rapport sur l'état du dépôt et la couverture des tests](../docs/reports/etat_depot_couverture_tests.md)

### Documentation des Patterns de Test Avancés

Une documentation détaillée des patterns de test avancés utilisés pour améliorer la couverture des tests est disponible dans :
- [Patterns de Test Avancés](ADVANCED_TEST_PATTERNS.md)