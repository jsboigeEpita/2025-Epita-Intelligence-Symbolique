# Tutoriel 2: Analyse d'un discours simple

## Objectif
Apprendre à configurer et exécuter une analyse rhétorique complète sur un discours simple

## Prérequis
- Avoir suivi le tutoriel 1 (prise en main)
- Comprendre le concept d'agents spécialisés

## Préparation des données
```python
# Exemple de discours simple avec balises d'extraction
texte = """
[EXTRAIT:ARGUMENT] Les énergies renouvelables sont essentielles pour l'avenir de notre planète. 
[EXTRAIT:OBJECTION] Cependant, certains argumentent que les coûts sont trop élevés.
[EXTRAIT:CONCLUSION] Malgré cela, l'investissement initial est justifié par les bénéfices à long terme.
"""
```

## Configuration de l'analyse
```python
from argumentiation_analysis.orchestration.hierarchical.strategic.planner import StrategicPlanner

config = {
    "objectives": [
        {
            "id": "obj-1",
            "description": "Identifier les arguments et objections dans le discours",
            "priority": "high"
        }
    ],
    "agents": {
        "extract": "ExtractAgent",
        "informal": "InformalAgent"
    },
    "max_depth": 2
}

planner = StrategicPlanner(config)
```

## Exécution de l'analyse
```python
from argumentiation_analysis.examples.run_hierarchical_orchestration import HierarchicalOrchestrator

async def main():
    orchestrator = HierarchicalOrchestrator()
    results = await orchestrator.analyze_text(texte, planner)
    
    # Affichage structuré des résultats
    print("Arguments détectés:")
    for arg in results.get("arguments", []):
        print(f"- {arg['content']} ({arg['confidence']:.2f})")
    
    print("\nSophismes détectés:")
    for fallacy in results.get("fallacies", []):
        print(f"- {fallacy['type']}: {fallacy['description']}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Interprétation des résultats
1. **Arguments** : Correspondent aux extrait marqués [EXTRAIT:ARGUMENT]
2. **Objections** : Correspondent aux extrait marqués [EXTRAIT:OBJECTION]
3. **Sophismes détectés** : L'agent informel identifie automatiquement des sophismes potentiels
4. **Confiance** : Indique la probabilité d'identification correcte (0-1)

## Exercice pratique
1. Modifier le texte d'analyse en ajoutant un nouveau type d'extrait
2. Ajouter l'agent PLAgent à la configuration pour formaliser les arguments
3. Comparer les résultats avec et sans l'agent de logique propositionnelle

## Références
- Données d'entrée formatées: `test_data/source_texts/with_markers/`
- Documentation technique: `docs/api_outils_rhetorique.md`
- Exemple complet: `examples/hierarchical_architecture_example.py`