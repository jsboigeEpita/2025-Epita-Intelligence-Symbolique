# Simple Hierarchical Architecture Example

import asyncio
from argumentiation_analysis.orchestration.hierarchical.operational.manager import OperationalManager
from argumentiation_analysis.orchestration.hierarchical.strategic.planner import StrategicPlanner
from argumentiation_analysis.orchestration.hierarchical.tactical.resolver import TacticalResolver

async def run_simple_hierarchy():
    """
    Exemple simplifié d'architecture hiérarchique à trois niveaux
    Montre l'interaction entre les niveaux stratégique, tactique et opérationnel
    """
    # Initialisation des composants
    strategic_planner = StrategicPlanner()
    tactical_resolver = TacticalResolver()
    operational_manager = OperationalManager()
    
    # Planification stratégique
    strategy = await strategic_planner.plan_analysis(
        text="La réforme éducative est nécessaire pour améliorer la qualité des enseignants.",
        objectives=["identifier_arguments", "analyser_coherence"]
    )
    
    # Résolution tactique
    tactics = await tactical_resolver.resolve_strategy(strategy)
    
    # Exécution opérationnelle
    results = await operational_manager.execute_tactics(tactics)
    
    # Affichage des résultats
    print("Résultats de l'analyse hiérarchique:")
    print(json.dumps(results, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(run_simple_hierarchy())