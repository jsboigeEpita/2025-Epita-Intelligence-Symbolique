# Enhanced Complex Fallacy Analyzer Example

import asyncio
from argumentiation_analysis.tools.enhanced_complex_fallacy_analyzer import EnhancedComplexFallacyAnalyzer

async def run_complex_fallacy_analysis():
    """
    Exemple d'utilisation de l'Enhanced Complex Fallacy Analyzer
    """
    # Initialisation de l'analyseur
    analyzer = EnhancedComplexFallacyAnalyzer()
    
    # Texte à analyser (contenant des sophismes complexes)
    text = """
    Les vaccins causent l'autisme car un médecin l'a dit. De plus, tous les parents vaccinés 
    ont des enfants en bonne santé, donc le vaccin est efficace. Enfin, les opposants sont 
    des criminels qui mettent en danger la société.
    """
    
    # Analyse des sophismes complexes
    logger.info("Analyse des sophismes complexes...")
    results = await analyzer.analyze_complex_fallacies(text)
    
    # Affichage des résultats détaillés
    logger.info("=== Résultats de l'analyse des sophismes complexes ===")
    logger.info(f"Score de gravité total: {results['total_severity']}")
    logger.info(f"Répartition des sophismes: {json.dumps(results['fallacy_distribution'], indent=2)}")
    logger.info("Détails des sophismes détectés:")
    
    for fallacy in results['detailed_analysis']:
        logger.info(f"\n- {fallacy['type']}")
        logger.info(f"  Contexte: {fallacy['context']}")
        logger.info(f"  Gravité: {fallacy['severity']}")
        logger.info(f"  Preuves: {json.dumps(fallacy['evidence'], indent=2)}")
        logger.info(f"  Réparation suggérée: {fallacy['suggested_repair']}")

if __name__ == "__main__":
    asyncio.run(run_complex_fallacy_analysis())