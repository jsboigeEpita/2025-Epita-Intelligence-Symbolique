# Tutoriel 3: Analyse d'un discours complexe

## Objectif
Apprendre à analyser des discours avec structures imbriquées, arguments multiples et sophismes complexes

## Défis spécifiques
- Gestion des arguments imbriqués
- Détection de sophismes contextuels
- Analyse de discours sans balises explicites
- Gestion des contradictions internes

## Configuration avancée
```python
from argumentiation_analysis.orchestration.hierarchical.strategic.planner import StrategicPlanner
from argumentiation_analysis.orchestration.hierarchical.tactical.resolver import TacticalResolver

config = {
    "objectives": [
        {
            "id": "obj-1",
            "description": "Analyser un discours complexe avec structures imbriquées",
            "priority": "critical"
        },
        {
            "id": "obj-2",
            "description": "Identifier les relations entre arguments et objections",
            "priority": "high"
        }
    ],
    "agents": {
        "extract": "ExtractAgent",
        "informal": "InformalAgent",
        "pl": "PLAgent"
    },
    "max_depth": 3,
    "tolerance": 0.7,
    "fallback_strategies": ["contextual_analysis", "semantic_clustering"]
}

planner = StrategicPlanner(config)
resolver = TacticalResolver(planner)
```

## Utilisation des outils spécialisés
```python
from argumentiation_analysis.utils.taxonomy_loader import load_fallacy_taxonomy
from argumentiation_analysis.services.definition_service import DefinitionService

async def analyze_complex_discourse(text):
    # Initialisation des services
    ds = DefinitionService()
    taxonomy = load_fallacy_taxonomy()
    
    # Configuration de l'orchestrateur
    orchestrator = HierarchicalOrchestrator()
    orchestrator.set_fallacy_taxonomy(taxonomy)
    
    # Analyse avec suivi détaillé
    results = await orchestrator.analyze_text(
        text, 
        planner, 
        resolver,
        verbose=True
    )
    
    # Génération de rapports détaillés
    report = generate_analysis_report(results, taxonomy)
    return report
```

## Analyse des résultats détaillés
```python
def generate_analysis_report(results, taxonomy):
    report = {
        "structure": analyze_argument_structure(results),
        "fallacies": categorize_fallacies(results["fallacies"], taxonomy),
        "consistency": check_logical_consistency(results),
        "confidence": calculate_overall_confidence(results)
    }
    
    # Visualisation de la structure argumentative
    if "graph" in results:
        report["visualization"] = visualize_argument_graph(results["graph"])
    
    return report
```

## Exercice pratique
1. Analyser un discours sans balises d'extraction
2. Implémenter une stratégie de fallback personnalisée
3. Comparer les résultats avec différentes profondeurs d'analyse
4. Créer un rapport visuel de la structure argumentative

## Références
- Données complexes: `test_data/source_texts/no_markers/`
- Taxonomie des sophismes: `utils/taxonomy_loader.py`
- Exemple avancé: `examples/run_hierarchical_orchestration.py`