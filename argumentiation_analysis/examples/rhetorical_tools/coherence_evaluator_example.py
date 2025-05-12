# Coherence Evaluator Example

import asyncio
from argumentiation_analysis.tools.argument_coherence_evaluator import ArgumentCoherenceEvaluator

async def run_coherence_evaluation():
    """
    Exemple d'utilisation de l'Argument Coherence Evaluator
    """
    # Initialisation de l'évaluateur
    evaluator = ArgumentCoherenceEvaluator()
    
    # Texte à analyser
    text = """
    Les vaccins sont essentiels pour la santé publique. D'une part, ils ont permis d'éliminer
    la variole et de contrôler la polio. D'autre part, l'immunité de groupe protège les personnes
    qui ne peuvent pas être vaccinées. Cependant, certains prétendent que les vaccins causent
    l'autisme, ce qui est démenti par toutes les preuves scientifiques disponibles.
    """
    
    # Évaluation de la cohérence
    logger.info("Évaluation de la cohérence de l'argument...")
    results = await evaluator.evaluate_coherence(text)
    
    # Affichage des résultats
    logger.info("=== Résultats de l'évaluation de cohérence ===")
    logger.info(f"Score de cohérence global: {results['coherence_score']}/100")
    logger.info(f"Structure logique: {results['logical_structure']}")
    logger.info(f"Liens entre prémisses et conclusion: {results['premise_conclusion_links']}")
    logger.info(f"Fluidez du raisonnement: {results['reasoning_fluidity']}")
    logger.info(f"Recommandations: {json.dumps(results['recommendations'], indent=2)}")

if __name__ == "__main__":
    asyncio.run(run_coherence_evaluation())