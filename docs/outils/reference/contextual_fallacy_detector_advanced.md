# Détecteur Avancé de Sophismes Contextuels

## Description

Le Détecteur Avancé de Sophismes Contextuels est une version améliorée du détecteur de sophismes contextuels standard. Il se concentre spécifiquement sur les sophismes qui dépendent fortement du contexte et qui ne sont pas évidents hors de leur contexte spécifique. Cet outil utilise des techniques avancées d'analyse contextuelle pour identifier les sophismes subtils qui pourraient passer inaperçus avec des méthodes d'analyse plus simples.

## Fonctionnalités

- Analyse des facteurs contextuels (culturels, sociaux, historiques)
- Détection des sophismes qui ne sont pas évidents hors contexte
- Évaluation de l'adéquation des arguments au contexte
- Analyse de la pertinence contextuelle des preuves présentées
- Identification des présuppositions contextuelles implicites

## Utilisation

```python
from argumentation_analysis.agents.tools.analysis.new.contextual_fallacy_detector import ContextualFallacyDetector

# Initialiser le détecteur avancé
detector = ContextualFallacyDetector(mode="advanced")

# Détecter les sophismes contextuels avancés
fallacies = detector.detect_contextual_fallacies(
    text="Ce traitement a été utilisé pendant des siècles, il est donc sûr et efficace.",
    context="Discussion sur un traitement médical alternatif",
    audience="Public non-spécialiste",
    domain="Santé",
    cultural_factors=["Méfiance envers la médecine moderne", "Valorisation des traditions"]
)

# Analyser l'adéquation contextuelle avec paramètres avancés
contextual_fit = detector.analyze_contextual_fit(
    argument="Cette étude scientifique démontre l'efficacité du traitement.",
    context="Forum public sur la santé",
    audience="Public général sans formation scientifique",
    depth_level="advanced"
)
```

## Paramètres

| Paramètre | Description | Valeur par défaut |
|-----------|-------------|-------------------|
| `mode` | Mode d'analyse (basic, advanced) | "advanced" |
| `context_window` | Taille de la fenêtre contextuelle à considérer | 200 |
| `sensitivity` | Sensibilité de la détection | 0.8 |
| `cultural_awareness` | Niveau de prise en compte des facteurs culturels | 0.7 |
| `domain_specificity` | Niveau de spécificité au domaine | 0.6 |

## Intégration

Cet outil s'intègre avec les autres composants du système d'analyse rhétorique et peut être utilisé en complément du Détecteur Contextuel de Sophismes standard pour une analyse plus approfondie.