# Analyseur Sémantique d'Arguments

## Description

L'Analyseur Sémantique d'Arguments est un outil avancé qui implémente le modèle de Toulmin pour analyser la structure sémantique des arguments. Il permet d'identifier et de caractériser les différents composants d'un argument selon ce modèle théorique.

## Fonctionnalités

- Identification des revendications (claims)
- Extraction des données/preuves (data/evidence)
- Identification des garanties (warrants)
- Reconnaissance des fondements (backings)
- Détection des réfutations (rebuttals)
- Analyse des qualificateurs (qualifiers)

## Utilisation

```python
from argumentation_analysis.agents.tools.analysis.new.semantic_argument_analyzer import SemanticArgumentAnalyzer

# Initialiser l'analyseur
analyzer = SemanticArgumentAnalyzer()

# Analyser un argument selon le modèle de Toulmin
toulmin_structure = analyzer.analyze_toulmin_structure(
    text="Bien que la plupart des oiseaux puissent voler (qualificateur), 
          les pingouins ne peuvent pas voler (revendication) 
          car leurs ailes sont adaptées à la nage plutôt qu'au vol (données). 
          Les ailes des oiseaux doivent avoir certaines caractéristiques aérodynamiques 
          pour permettre le vol (garantie), 
          comme l'ont démontré de nombreuses études en biomécanique (fondement), 
          à moins qu'il ne s'agisse d'espèces artificiellement sélectionnées pour d'autres traits (réfutation)."
)

# Visualiser la structure de Toulmin
toulmin_diagram = analyzer.visualize_toulmin_structure(toulmin_structure)
```

## Paramètres

| Paramètre | Description | Valeur par défaut |
|-----------|-------------|-------------------|
| `model_type` | Type de modèle de Toulmin à utiliser | "standard" |
| `toulmin_components` | Composants du modèle à identifier | ["claim", "data", "warrant", "backing", "rebuttal", "qualifier"] |
| `min_confidence` | Seuil minimal de confiance pour l'identification | 0.7 |

## Intégration

Cet outil s'intègre avec les autres composants du système d'analyse rhétorique, notamment avec l'architecture hiérarchique via les adaptateurs appropriés.