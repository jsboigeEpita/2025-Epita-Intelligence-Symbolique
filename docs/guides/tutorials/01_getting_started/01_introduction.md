# Tutoriel 1: Prise en main du système d'analyse rhétorique

> **⚠️ Tutoriel en sommeil (mode Hiérarchique dormant).**
> Ce tutoriel parcourt le mode d'orchestration **Hiérarchique**, actuellement
> **dormant** (voir la table *Orchestration Modes* de `CLAUDE.md`). Le code de
> référence reste présent à l'emplacement canonique
> `argumentation_analysis/orchestration/hierarchical/` (expérimental, non branché
> dans le pipeline actif). **Point d'entrée recommandé** aujourd'hui :
> [`demonstration_epita.py`](../../../../examples/02_core_system_demos/scripts_demonstration/demonstration_epita.py)
> et `run_unified_analysis` (mode Pipeline actif). Les exemples d'imports
> ci-dessous peuvent ne pas s'exécuter tels quels.

## Objectif
Apprendre à installer, configurer et exécuter une analyse rhétorique de base

## Prérequis
- Python 3.10+
- Connaissance de base en NLP

## Installation
```bash
cd argumentation_analysis
pip install -r requirements.txt
```

## Structure du projet
```
argumentation_analysis/
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
from argumentation_analysis.examples.run_hierarchical_orchestration import HierarchicalOrchestrator

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