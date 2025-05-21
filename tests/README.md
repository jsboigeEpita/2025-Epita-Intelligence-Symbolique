# Tests du Projet d'Intelligence Symbolique

Ce répertoire contient les tests unitaires, d'intégration et fonctionnels du projet d'Intelligence Symbolique.

## Structure du Répertoire

- `test_*.py` : Tests unitaires et d'intégration pour les différents modules
- `standalone_mock_tests.py` : Tests utilisant des mocks pour isoler les dépendances problématiques
- `test_load_extract_definitions.py` : Tests spécifiques pour les fonctions d'extraction de définitions

## Documentation Associée

### Plan d'Action pour l'Amélioration des Tests

Un plan d'action détaillé pour l'amélioration des tests et de la couverture de code est disponible dans:
- [Plan d'action pour l'amélioration des tests](../docs/tests/plan_action_tests.md)

Ce document décrit:
- Les problèmes initiaux identifiés
- Les solutions mises en œuvre
- Les améliorations apportées à la structure du projet
- Un plan d'action détaillé pour résoudre les problèmes restants
- Un calendrier réaliste pour la mise en œuvre du plan d'action

### Rapport sur l'État du Dépôt et la Couverture des Tests

Un rapport détaillé sur l'état actuel du dépôt et la couverture des tests est disponible dans:
- [Rapport sur l'état du dépôt et la couverture des tests](../docs/reports/etat_depot_couverture_tests.md)

Ce rapport présente:
- L'état actuel du dépôt Git
- La structure du projet après rangement
- L'état actuel de la couverture des tests
- Les problèmes identifiés
- Des recommandations pour améliorer la couverture

## Exécution des Tests

### Tests Unitaires et d'Intégration

Pour exécuter tous les tests:

```bash
pytest
```

Pour exécuter un test spécifique:

```bash
pytest tests/test_specific_module.py
```

### Tests avec Couverture de Code

Pour exécuter les tests avec génération d'un rapport de couverture:

```bash
pytest --cov=argumentation_analysis
```

Pour générer un rapport HTML détaillé:

```bash
pytest --cov=argumentation_analysis --cov-report=html
```

## Conventions de Test

1. **Nommage des fichiers de test**:
   - Les fichiers de test doivent être nommés `test_*.py`
   - Le nom doit clairement indiquer le module testé

2. **Structure des tests**:
   - Utiliser des fixtures pytest pour la configuration
   - Organiser les tests par fonctionnalité
   - Inclure des tests positifs et négatifs

3. **Documentation des tests**:
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