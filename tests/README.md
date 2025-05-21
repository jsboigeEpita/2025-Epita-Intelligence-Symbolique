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

- `test_*.py` : Tests unitaires et d'intégration pour les différents modules
- `standalone_mock_tests.py` : Tests utilisant des mocks pour isoler les dépendances problématiques
- `mocks/` : Mocks pour les dépendances problématiques (numpy, pandas, jpype)
- `conftest.py` : Configuration pour pytest

## Modules Prioritaires

Les modules suivants ont été identifiés comme prioritaires pour l'amélioration de la couverture de tests :

1. **orchestration.hierarchical.tactical** (11.78%)
2. **orchestration.hierarchical.operational.adapters** (12.44%)
3. **agents.tools.analysis.enhanced** (12.90%)
4. **agents.core.informal** (16.23%)
5. **agents.tools.analysis** (16.46%)

Des tests unitaires ont été implémentés pour ces modules prioritaires.

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

### Tests avec Couverture de Code

Pour exécuter les tests avec génération d'un rapport de couverture :

```bash
pytest --cov=argumentation_analysis
```

Pour générer un rapport HTML détaillé :

```bash
pytest --cov=argumentation_analysis --cov-report=html
```

## Conventions de Test

1. **Nommage des fichiers de test** :
   - Les fichiers de test doivent être nommés `test_*.py`
   - Le nom doit clairement indiquer le module testé

2. **Structure des tests** :
   - Utiliser des fixtures pytest pour la configuration
   - Organiser les tests par fonctionnalité
   - Inclure des tests positifs et négatifs

3. **Documentation des tests** :
   - Chaque test doit avoir une docstring expliquant son objectif
   - Les cas de test complexes doivent être documentés en détail

## Objectifs de Couverture

| Module | Couverture actuelle | Objectif à 4 semaines | Objectif à 8 semaines |
|--------|---------------------|----------------------|----------------------|
| Services | 14-17% | 50% | 80% |
| Modules d'analyse | 10-14% | 40% | 75% |
| Communication | 43% | 60% | 85% |
| Gestion d'état | 46% | 65% | 90% |
| **Global** | **44.48%** | **60%** | **80%** |

## Documentation Associée

### Plan d'Action pour l'Amélioration des Tests

Un plan d'action détaillé pour l'amélioration des tests et de la couverture de code est disponible dans :
- [Plan d'action pour l'amélioration des tests](../docs/tests/plan_action_tests.md)

### Rapport sur l'État du Dépôt et la Couverture des Tests

Un rapport détaillé sur l'état actuel du dépôt et la couverture des tests est disponible dans :
- [Rapport sur l'état du dépôt et la couverture des tests](../docs/reports/etat_depot_couverture_tests.md)