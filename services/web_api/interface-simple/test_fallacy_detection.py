#!/usr/bin/env python3
"""
Test de détection de sophismes avec le ServiceManager intégré.
"""

import asyncio
import sys
import logging
from pathlib import Path

# Configuration des chemins
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


async def test_fallacy_detection():
    """Test de détection de sophismes avec le ServiceManager."""
    logger.info("=== TEST DÉTECTION DE SOPHISMES ===")
    
    try:
        from app import initialize_services, service_manager, _extract_fallacy_analysis
        
        # Initialisation
        await initialize_services()
        
        if not service_manager:
            logger.error("ServiceManager non disponible")
            return False
        
        # Texte de test contenant plusieurs sophismes
        texte_test = """
        Si nous laissons les immigrants entrer dans notre pays, 
        alors bientôt ils vont tous prendre nos emplois et notre économie va s'effondrer complètement. 
        
        C'est évident car mon voisin Jean, qui est un ignorant notoire, 
        pense que l'immigration est bénéfique, donc il a forcément tort.
        
        Nous devons choisir : soit nous fermons complètement nos frontières, 
        soit nous acceptons que notre civilisation disparaisse à jamais.
        
        D'ailleurs, tous les économistes sont payés par les lobbies, 
        donc leurs études sur l'immigration ne valent rien.
        """
        
        logger.info("Analyse d'un texte contenant des sophismes...")
        logger.info(f"Texte: {texte_test[:100]}...")
        
        # Analyse avec le ServiceManager
        result = await service_manager.analyze_text(
            text=texte_test,
            analysis_type="comprehensive",
            options={'detect_fallacies': True}
        )
        
        logger.info(f"Analyse terminée en {result.get('duration', 0):.2f}s")
        logger.info(f"Statut: {result.get('status', 'unknown')}")
        
        # Extraction des analyses de sophismes
        fallacy_analysis = _extract_fallacy_analysis(result)
        
        logger.info("=== RÉSULTATS ===")
        logger.info(f"Sophismes détectés: {fallacy_analysis['total_fallacies']}")
        logger.info(f"Catégories: {fallacy_analysis['categories_found']}")
        logger.info(f"Distribution sévérité: {fallacy_analysis['severity_distribution']}")
        
        # Affichage des détails des résultats
        if 'results' in result:
            results = result['results']
            logger.info("Structure des résultats:")
            for key in results.keys():
                logger.info(f"  - {key}")
                
        # Analyse des composants utilisés
        hierarchical = results.get('hierarchical', {})
        if hierarchical:
            logger.info("Analyses hiérarchiques:")
            for level in ['strategic', 'tactical', 'operational']:
                if level in hierarchical:
                    logger.info(f"  - {level}: {type(hierarchical[level])}")
        
        logger.info("SUCCESS: Test de détection de sophismes terminé")
        return True
        
    except Exception as e:
        logger.error(f"Erreur dans le test: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_fallacy_detection())
    print(f"\nTest {'RÉUSSI' if success else 'ÉCHOUÉ'}")
    sys.exit(0 if success else 1)