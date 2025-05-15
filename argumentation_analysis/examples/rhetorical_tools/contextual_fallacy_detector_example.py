# Contextual Fallacy Detector Example

import asyncio
from argumentation_analysis.tools.contextual_fallacy_detector import ContextualFallacyDetector

async def run_fallacy_detection():
    """
    Exemple d'utilisation du Contextual Fallacy Detector
    """
    # Initialisation du détecteur
    detector = ContextualFallacyDetector()
    
    # Texte à analyser
    text = """
    Les vaccins causent des autisme. Cela a été prouvé par un médecin réputé dans un article scientifique.
    """
    
    # Détection des sophismes contextuels
    logger.info("Détection des sophismes contextuels...")
    results = await detector.detect_fallacies(text)
    
    # Affichage des résultats
    logger.info("=== Résultats de détection des sophismes ===")
    logger.info(f"Nombre de sophismes détectés: {len(results['fallacies'])}")
    for fallacy in results['fallacies']:
        logger.info(f"- {fallacy['type']}: {fallacy['description']}")
        logger.info(f"  Contexte: {fallacy['context']}")
        logger.info(f"  Gravité: {fallacy['severity']}")

if __name__ == "__main__":
    asyncio.run(run_fallacy_detection())