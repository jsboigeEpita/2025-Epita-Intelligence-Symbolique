# Évaluateur de cohérence argumentative

## Objectif
Évalue la cohérence logique des arguments dans un texte en vérifiant l'alignement entre les prémisses et la conclusion.

## Utilisation
```python
from argumentiation_analysis.tools import ArgumentCoherenceEvaluator

evaluator = ArgumentCoherenceEvaluator()
result = evaluator.analyze(text="Tous les chats sont des mammifères. Les mammifères sont des vertébrés. Donc, les chats sont des vertébrés.")
print(result.coherence_score)
```

## Paramètres
- `text` (str): Texte à analyser
- `threshold` (float, optional): Seuil de cohérence minimal (défaut: 0.7)
- `explanation` (bool, optional): Activer les explications détaillées (défaut: False)

## Résultats
Retourne un objet contenant:
- `coherence_score` (float): Note entre 0 et 1
- `inconsistencies` (list): Liste des incohérences détectées
- `suggestions` (list): Recommandations pour améliorer la cohérence

## Personnalisation
Pour ajouter un nouveau critère d'évaluation:
```python
class CustomCoherenceCriterion:
    def evaluate(self, argument):
        # Implémentation personnalisée
        return score, feedback