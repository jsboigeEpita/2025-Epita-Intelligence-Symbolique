# Tests des Outils d'Analyse Rhétorique Améliorés

Ce répertoire contient les tests unitaires, d'intégration et de performance pour les outils d'analyse rhétorique améliorés et nouveaux.

## Structure du Répertoire

- `test_enhanced_complex_fallacy_analyzer.py` : Tests pour EnhancedComplexFallacyAnalyzer
- `test_enhanced_contextual_fallacy_analyzer.py` : Tests pour EnhancedContextualFallacyAnalyzer
- `test_enhanced_fallacy_severity_evaluator.py` : Tests pour EnhancedFallacySeverityEvaluator
- `test_enhanced_rhetorical_result_analyzer.py` : Tests pour EnhancedRhetoricalResultAnalyzer
- `test_enhanced_rhetorical_result_visualizer.py` : Tests pour EnhancedRhetoricalResultVisualizer
- `test_semantic_argument_analyzer.py` : Tests pour SemanticArgumentAnalyzer
- `test_contextual_fallacy_detector.py` : Tests pour ContextualFallacyDetector
- `test_argument_coherence_evaluator.py` : Tests pour ArgumentCoherenceEvaluator
- `test_argument_structure_visualizer.py` : Tests pour ArgumentStructureVisualizer
- `test_rhetorical_tools_integration.py` : Tests d'intégration pour les outils d'analyse rhétorique
- `test_rhetorical_tools_performance.py` : Tests de performance pour les outils d'analyse rhétorique
- `test_data/` : Jeu de données de test pour les outils d'analyse rhétorique
- `reports/` : Répertoire pour les rapports de tests et de couverture
- `rapport_tests_outils_rhetorique.md` : Rapport détaillé des tests effectués
- `run_rhetorical_tools_tests.py` : Script pour exécuter tous les tests

## Prérequis

Pour exécuter les tests, vous devez avoir installé les dépendances suivantes :

```bash
pip install unittest coverage
```

## Exécution des Tests

### Exécuter tous les tests

Pour exécuter tous les tests (unitaires, d'intégration et de performance) :

```bash
python -m argumentation_analysis.tests.tools.run_rhetorical_tools_tests
```

### Exécuter uniquement les tests unitaires

```bash
python -m argumentation_analysis.tests.tools.run_rhetorical_tools_tests --type unit
```

### Exécuter uniquement les tests d'intégration

```bash
python -m argumentation_analysis.tests.tools.run_rhetorical_tools_tests --type integration
```

### Exécuter uniquement les tests de performance

```bash
python -m argumentation_analysis.tests.tools.run_rhetorical_tools_tests --type performance
```

### Options supplémentaires

- `--verbose` : Afficher les détails des tests
- `--coverage` : Générer un rapport de couverture

Exemple :

```bash
python -m argumentation_analysis.tests.tools.run_rhetorical_tools_tests --type unit --verbose --coverage
```

## Rapports de Tests

Les rapports de tests sont générés dans le répertoire `reports/`. Ils incluent :

- Un rapport de test au format texte avec les résultats des tests
- Un rapport de couverture au format HTML (si l'option `--coverage` est utilisée)
- Un rapport de couverture au format XML (si l'option `--coverage` est utilisée)

## Jeu de Données de Test

Le jeu de données de test est défini dans le module `test_data/rhetorical_test_dataset.py`. Il comprend :

- Des textes argumentatifs dans différents contextes (politique, scientifique, commercial, juridique, académique)
- Des textes avec différents niveaux de complexité (simple, sophismes simples, sophismes complexes)
- Des mappings de sophismes et de contextes pour l'évaluation

## Rapport Détaillé

Un rapport détaillé des tests effectués est disponible dans le fichier `rapport_tests_outils_rhetorique.md`. Il comprend :

- Un résumé exécutif des résultats des tests
- Une description de la méthodologie de test
- Les résultats des tests unitaires, d'intégration et de performance
- Une analyse des résultats
- Des recommandations pour les améliorations futures

## Ajout de Nouveaux Tests

Pour ajouter de nouveaux tests :

1. Créez un nouveau fichier de test dans ce répertoire
2. Ajoutez le fichier à la liste des tests dans `run_rhetorical_tools_tests.py`
3. Exécutez les tests pour vérifier que tout fonctionne correctement

## Maintenance

Pour maintenir les tests à jour :

1. Mettez à jour les tests existants lorsque les outils sont modifiés
2. Ajoutez de nouveaux tests pour les nouvelles fonctionnalités
3. Exécutez régulièrement les tests pour vérifier que tout fonctionne correctement
4. Mettez à jour le rapport de test lorsque des changements significatifs sont apportés