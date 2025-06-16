# Outils Rhétoriques Améliorés

Ce répertoire contient des versions améliorées des outils d'analyse rhétorique, offrant des fonctionnalités plus avancées et une meilleure précision par rapport aux versions de base.

## Vue d'ensemble

Les outils rhétoriques améliorés étendent les capacités des outils de base en intégrant :
- Des modèles de langage plus avancés
- Des analyses contextuelles plus approfondies
- Des mécanismes d'apprentissage continu
- Des analyses de structures argumentatives plus sophistiquées
- Des évaluations de cohérence inter-arguments

## Outils disponibles

### EnhancedComplexFallacyAnalyzer

L'analyseur amélioré de sophismes complexes permet d'identifier et d'analyser des structures sophistiquées de sophismes, notamment :
- Les combinaisons de sophismes (sophismes composés)
- Les sophismes qui s'étendent sur plusieurs arguments
- Les structures argumentatives sophistiquées avec des sophismes imbriqués

```python
from argumentation_analysis.agents.tools.analysis.enhanced.complex_fallacy_analyzer import EnhancedComplexFallacyAnalyzer

# Initialiser l'analyseur
analyzer = EnhancedComplexFallacyAnalyzer()

# Analyser un ensemble d'arguments pour détecter des sophismes complexes
results = analyzer.analyze_argument_set(
    arguments=[
        "Les experts sont unanimes : ce produit est sûr.",
        "Si vous n'achetez pas ce produit, vous risquez de regretter cette décision.",
        "Tous nos concurrents proposent des produits similaires, donc le nôtre est forcément bon."
    ],
    context="Discours commercial pour un produit controversé"
)

# Identifier les patterns de sophismes composés
patterns = analyzer.identify_composite_patterns(results)
```

### EnhancedContextualFallacyAnalyzer

L'analyseur contextuel amélioré offre une détection plus précise des sophismes en tenant compte du contexte élargi :
- Analyse approfondie du contexte culturel, social et historique
- Détection des nuances contextuelles qui influencent l'interprétation des arguments
- Prise en compte des intentions présumées de l'auteur

```python
from argumentation_analysis.agents.tools.analysis.enhanced.contextual_fallacy_analyzer import EnhancedContextualFallacyAnalyzer

# Initialiser l'analyseur
analyzer = EnhancedContextualFallacyAnalyzer()

# Analyser un argument dans son contexte élargi
results = analyzer.analyze_extended_context(
    text="Les experts sont unanimes : ce produit est sûr.",
    context="Discours commercial pour un produit controversé",
    audience="Consommateurs non spécialistes",
    historical_context="Plusieurs scandales récents dans l'industrie"
)
```

### EnhancedFallacySeverityEvaluator

L'évaluateur amélioré de gravité des sophismes permet une évaluation plus nuancée de l'impact des sophismes :
- Évaluation multi-factorielle de la gravité
- Prise en compte du public cible et du domaine
- Analyse de l'impact potentiel du sophisme sur la prise de décision

```python
from argumentation_analysis.agents.tools.analysis.enhanced.fallacy_severity_evaluator import EnhancedFallacySeverityEvaluator

# Initialiser l'évaluateur
evaluator = EnhancedFallacySeverityEvaluator()

# Évaluer la gravité d'un sophisme avec des paramètres contextuels étendus
severity = evaluator.evaluate_severity(
    fallacy_type="Appel à l'autorité",
    argument="Les experts sont unanimes : ce produit est sûr.",
    context="Discours commercial pour un produit controversé",
    audience="Public vulnérable",
    domain="Santé publique",
    potential_impact="Élevé"
)
```

### EnhancedRhetoricalResultAnalyzer

L'analyseur amélioré des résultats rhétoriques offre des insights plus profonds sur les analyses rhétoriques :
- Analyse de persuasion
- Évaluation de la qualité argumentative
- Analyse des stratégies rhétoriques
- Génération de résumés détaillés

```python
from argumentation_analysis.agents.tools.analysis.enhanced.rhetorical_result_analyzer import EnhancedRhetoricalResultAnalyzer

# Initialiser l'analyseur
analyzer = EnhancedRhetoricalResultAnalyzer()

# Analyser les résultats d'une analyse rhétorique
insights = analyzer.analyze_results(rhetorical_analysis_results)

# Générer un résumé détaillé
summary = analyzer.generate_detailed_summary(insights)
```

## Intégration avec les autres composants

Ces outils améliorés s'intègrent parfaitement avec :
- Les agents spécialistes, notamment l'agent Informel
- Le niveau opérationnel de l'architecture hiérarchique via les adaptateurs appropriés
- Les nouveaux outils d'analyse rhétorique pour des analyses plus complètes

## Développement

Pour étendre ces outils améliorés :

1. Respectez l'interface des classes de base tout en ajoutant des fonctionnalités avancées
2. Documentez clairement les nouvelles fonctionnalités et leurs cas d'utilisation
3. Ajoutez des tests unitaires et d'intégration pour les nouvelles fonctionnalités
4. Assurez la compatibilité avec les outils existants et les adaptateurs

## Voir aussi

- [Documentation des outils d'analyse rhétorique de base](../README.md)
- [Documentation des nouveaux outils d'analyse rhétorique](../new/README.md)
- [Documentation de l'analyseur de sophismes complexes](../enhanced/complex_fallacy_analyzer.py)
- [Documentation de l'architecture hiérarchique](../../../../orchestration/hierarchical/README.md)