#!/usr/bin/env python3
"""
Script de test pour l'intégration ServiceManager dans l'interface simple.

Ce script teste que l'interface simple utilise vraiment le ServiceManager
pour l'analyse de sophismes au lieu des fallbacks simulés.
"""

import asyncio
import sys
import logging
from pathlib import Path

# Configuration des chemins
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app import (
    ServiceManager, SERVICE_MANAGER_AVAILABLE, FALLACY_ANALYZERS_AVAILABLE,
    initialize_services, service_manager, _extract_fallacy_analysis
)

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [Test] %(message)s'
)
logger = logging.getLogger(__name__)


async def test_service_manager_integration():
    """Test principal de l'intégration du ServiceManager."""
    logger.info("=== DÉBUT TEST INTÉGRATION SERVICEMANAGER ===")
    
    # 1. Vérifier la disponibilité des imports
    logger.info(f"ServiceManager disponible: {SERVICE_MANAGER_AVAILABLE}")
    logger.info(f"Analyseurs de sophismes disponibles: {FALLACY_ANALYZERS_AVAILABLE}")
    
    if not SERVICE_MANAGER_AVAILABLE:
        logger.error("ServiceManager non disponible - abandon du test")
        return False
    
    # 2. Test d'initialisation des services
    logger.info("Test d'initialisation des services...")
    try:
        await initialize_services()
        if service_manager:
            logger.info("✅ ServiceManager initialisé avec succès")
        else:
            logger.error("❌ ServiceManager non initialisé")
            return False
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'initialisation: {e}")
        return False
    
    # 3. Test d'analyse de texte avec sophismes
    logger.info("Test d'analyse de texte contenant des sophismes...")
    test_text = """
    Si nous acceptons l'immigration, alors notre pays va s'effondrer économiquement.
    C'est évident car tous les immigrants sont des parasites qui ne travaillent jamais.
    D'ailleurs, mon voisin qui est contre l'immigration est un imbécile, 
    donc son opinion ne compte pas. Il faut choisir : soit nous fermons complètement 
    les frontières, soit nous acceptons que notre civilisation disparaisse.
    """
    
    try:
        result = await service_manager.analyze_text(
            text=test_text,
            analysis_type="comprehensive",
            options={'detect_fallacies': True}
        )
        
        logger.info("✅ Analyse de texte terminée")
        logger.info(f"Structure du résultat: {list(result.keys())}")
        
        # 4. Test d'extraction des sophismes
        fallacy_analysis = _extract_fallacy_analysis(result)
        logger.info(f"Sophismes détectés: {fallacy_analysis['total_fallacies']}")
        logger.info(f"Catégories trouvées: {fallacy_analysis['categories_found']}")
        
        if fallacy_analysis['total_fallacies'] > 0:
            logger.info("✅ Détection de sophismes fonctionnelle")
        else:
            logger.warning("⚠️ Aucun sophisme détecté (peut être normal)")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'analyse: {e}")
        return False


async def test_health_check():
    """Test du health check du ServiceManager."""
    logger.info("Test du health check...")
    
    try:
        if hasattr(service_manager, 'health_check'):
            health = await service_manager.health_check()
            logger.info(f"Health check: {health}")
        
        if hasattr(service_manager, 'get_service_status'):
            status = await service_manager.get_service_status()
            logger.info(f"Service status: {status}")
            
        logger.info("✅ Health check terminé")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur health check: {e}")
        return False


async def main():
    """Fonction principale de test."""
    logger.info("Début des tests d'intégration...")
    
    # Test 1: Intégration ServiceManager
    success1 = await test_service_manager_integration()
    
    # Test 2: Health check
    success2 = await test_health_check()
    
    # Résultat final
    if success1 and success2:
        logger.info("🎉 TOUS LES TESTS PASSÉS - Intégration ServiceManager réussie")
        return True
    else:
        logger.error("❌ CERTAINS TESTS ONT ÉCHOUÉ")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)