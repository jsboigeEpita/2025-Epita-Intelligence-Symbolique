# Complex Hierarchical Architecture Example

import asyncio
import json
from argumentation_analysis.orchestration.hierarchical.strategic.planner import StrategicPlanner
from argumentation_analysis.orchestration.hierarchical.tactical.resolver import TacticalResolver
from argumentation_analysis.orchestration.hierarchical.operational.manager import OperationalManager
from argumentation_analysis.orchestration.hierarchical.interfaces.strategic_tactical import StrategicTacticalInterface
from argumentation_analysis.orchestration.hierarchical.interfaces.tactical_operational import TacticalOperationalInterface

from argumentation_analysis.paths import RESULTS_DIR


async def run_complex_hierarchy():
    """
    Exemple complexe d'architecture hiérarchique à trois niveaux
    Illustration complète du flux d'analyse rhétorique à travers les trois niveaux
    """
    # Initialisation des interfaces
    strategic_tactical_interface = StrategicTacticalInterface()
    tactical_operational_interface = TacticalOperationalInterface()
    
    # Initialisation des composants
    strategic_planner = StrategicPlanner(strategic_tactical_interface)
    tactical_resolver = TacticalResolver(tactical_operational_interface)
    operational_manager = OperationalManager()
    
    # Texte à analyser
    text = """
    La vaccination devrait être obligatoire pour tous les enfants. Les vaccins ont été prouvés sûrs par de nombreuses études scientifiques. 
    De plus, la vaccination de masse crée une immunité collective qui protège les personnes vulnérables qui ne peuvent pas être vaccinées pour des raisons médicales. 
    Certains parents s'inquiètent des effets secondaires, mais ces effets sont généralement mineurs et temporaires. 
    Le risque de complications graves dues aux maladies évitables par la vaccination est bien plus élevé que le risque d'effets secondaires graves des vaccins.
    """
    
    # Phase 1: Planification stratégique
    logger.info("=== Phase 1: Planification stratégique ===")
    strategic_plan = await strategic_planner.plan_analysis(
        text=text,
        objectives=[
            "identifier_arguments",
            "analyser_coherence",
            "detecter_sophismes",
            "evaluer_validite"
        ],
        constraints={
            "max_duration": "10s",
            "required_capabilities": ["text_analysis", "formal_logic"]
        }
    )
    
    # Phase 2: Résolution tactique
    logger.info("=== Phase 2: Résolution tactique ===")
    tactical_plan = await tactical_resolver.resolve_strategy(
        strategic_plan,
        resource_constraints={
            "max_parallel_tasks": 3,
            "priority": "high"
        }
    )
    
    # Phase 3: Exécution opérationnelle
    logger.info("=== Phase 3: Exécution opérationnelle ===")
    results = await operational_manager.execute_tactics(
        tactical_plan,
        execution_context={
            "text": text,
            "format": "json"
        }
    )
    
    # Affichage des résultats détaillés
    logger.info("=== Résultats complets de l'analyse ===")
    logger.info(f"Plan stratégique: {json.dumps(strategic_plan, indent=2)}")
    logger.info(f"Plan tactique: {json.dumps(tactical_plan, indent=2)}")
    logger.info(f"Résultats opérationnels: {json.dumps(results, indent=2)}")
    
    # Génération de rapport final
    final_report = {
        "text_analyzed": text,
        "strategic_plan": strategic_plan,
        "tactical_plan": tactical_plan,
        RESULTS_DIR: results,
        "summary": {
            "total_arguments_identified": len(results.get("arguments", [])),
            "fallacies_detected": len(results.get("fallacies", [])),
            "validity_score": results.get("validity_score", 0)
        }
    }
    
    logger.info("=== Rapport final ===")
    logger.info(json.dumps(final_report, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(run_complex_hierarchy())