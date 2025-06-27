# Tests des Analyseurs de Sophismes Améliorés

Ce répertoire contient les tests unitaires pour les composants d'analyse de sophismes améliorés, qui font partie des outils d'analyse des agents. Ces tests garantissent la fiabilité et la précision des analyseurs chargés d'identifier des patrons de sophismes complexes, de prendre en compte le contexte et d'évaluer la gravité des erreurs de raisonnement.

## Objectif des Tests

L'objectif principal de ces tests est de valider le comportement des analyseurs de sophismes améliorés dans divers scénarios. Ils couvrent :
- La détection de sophismes composites et de combinaisons de sophismes.
- L'analyse contextuelle pour affiner la détection des sophismes.
- L'évaluation de la gravité des sophismes en fonction de multiples facteurs.
- La robustesse des analyseurs face à différents types d'arguments et de contextes.

## Modules Testés

- **`EnhancedComplexFallacyAnalyzer`**: Testé dans [`test_enhanced_complex_fallacy_analyzer.py`](test_enhanced_complex_fallacy_analyzer.py:1). Ces tests vérifient la capacité de l'analyseur à identifier des structures d'arguments complexes, des raisonnements circulaires et des combinaisons de sophismes.
- **`EnhancedContextualFallacyAnalyzer`**: Testé dans [`test_enhanced_contextual_fallacy_analyzer.py`](test_enhanced_contextual_fallacy_analyzer.py:1). Ces tests s'assurent que l'analyseur utilise correctement le contexte (par exemple, politique, commercial) pour identifier les sophismes pertinents et ajuster sa confiance.
- **`EnhancedFallacySeverityEvaluator`**: Testé dans [`test_enhanced_fallacy_severity_evaluator.py`](test_enhanced_fallacy_severity_evaluator.py:1). Ces tests valident la logique d'évaluation qui pondère la gravité d'un sophisme en fonction du type de sophisme, du contexte, de l'audience et du domaine de l'argument.

## Structure des Tests

Chaque fichier de test est structuré pour couvrir les fonctionnalités clés du module correspondant :
- **Fixtures `pytest`**: Pour initialiser les instances des analyseurs et fournir des données de test communes (arguments, sophismes).
- **Tests d'Initialisation**: Pour vérifier que les analyseurs sont créés avec une configuration correcte.
- **Tests de Fonctionnalités**: Chaque test cible une méthode spécifique de l'analyseur pour en valider la logique et les résultats.
- **Tests Paramétrés**: Utilisés pour évaluer le comportement des analyseurs sur une gamme de contextes et de données d'entrée.

## Dépendances

- `pytest` pour le framework de test.
- `unittest.mock` pour mocker les dépendances externes et isoler les composants testés.
- Les modules applicatifs situés dans `argumentation_analysis/agents/tools/analysis/enhanced/`.