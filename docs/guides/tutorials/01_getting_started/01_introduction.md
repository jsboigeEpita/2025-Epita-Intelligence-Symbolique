# Tutoriel 1: Prise en main du système d'analyse rhétorique

## Objectif
Apprendre à installer, configurer et exécuter une analyse rhétorique de base

## Prérequis
- Python 3.10+
- Connaissance de base en NLP

## Installation
```bash
cd argumentiation_analysis
pip install -r requirements.txt
```

## Structure du projet
```
argumentiation_analysis/
├── orchestration/
│   └── hierarchical/  # Architecture à trois niveaux
├── agents/            # Agents spécialisés
├── services/          # Services d'infrastructure
├── tests/             # Tests unitaires et d'intégration
├── examples/          # Exemples d'utilisation
└── README.md          # Documentation principale
```

## Premier exemple d'analyse
```python
from argumentiation_analysis.examples.run_hierarchical_orchestration import HierarchicalOrchestrator

async def main():
    orchestrator = HierarchicalOrchestrator()
    text = "Les énergies renouvelables sont essentielles pour l'avenir de notre planète. Cependant, certains argumentent que les coûts sont trop élevés."
    results = await orchestrator.analyze_text(text)
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
```

## Exercice pratique
1. Modifier le texte d'analyse dans l'exemple ci-dessus
2. Exécuter le script et observer les résultats
3. Ajouter un nouveau type d'analyse dans le fichier `run_hierarchical_orchestration.py`

## Références
- Documentation technique: `docs/architecture_hierarchique_trois_niveaux.md`
- Exemple complet: `examples/hierarchical_architecture_example.py`