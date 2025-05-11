# Analyseur de sophismes complexes

## Objectif
Analyse les structures argumentatives complexes pour détecter les sophismes imbriqués et les contradictions multiples.

## Utilisation
```python
from argumentiation_analysis.tools import EnhancedComplexFallacyAnalyzer

analyzer = EnhancedComplexFallacyAnalyzer()
result = analyzer.analyze(text="""
1. Les énergies renouvelables sont coûteuses.
2. Pourtant, les pays développés investissent massivement dedans.
3. Donc, les pays développés sont irresponsables financièrement.
4. Cependant, les énergies renouvelables réduisent les émissions.
""")
print(result.fallacy_tree)  # Structure hiérarchique des sophismes
```

## Paramètres
- `text` (str): Texte à analyser
- `analysis_depth` (int, optional): Profondeur d'analyse (1-5, défaut: 3)
- `explanations` (bool, optional): Activer les explications détaillées (défaut: False)
- `visualization` (bool, optional): Générer une visualisation (défaut: False)

## Résultats
Retourne un objet contenant:
- `fallacy_tree` (dict): Structure hiérarchique des sophismes détectés
- `confidence_matrix` (list): Matrice de confiance entre les arguments
- `suggestions` (list): Recommandations pour clarifier la structure
- `visualization_url` (str): Lien vers la visualisation générée

## Personnalisation
Pour ajouter un nouveau type d'analyse:
```python
class CustomComplexFallacyChecker:
    def analyze(self, argument_graph):
        # Implémentation personnalisée
        return fallacy_tree, confidence_scores
```

```mermaid
graph TD
    A[Texte d'entrée] --> B[Construction du graphe d'arguments]
    B --> C[Détection des cycles et contradictions]
    C --> D[Analyse des relations imbriquées]
    D --> E[Rapport structuré]