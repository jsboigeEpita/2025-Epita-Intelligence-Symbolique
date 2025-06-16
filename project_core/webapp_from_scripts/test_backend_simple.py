#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test simple du backend manager pour diagnostiquer les problèmes
"""

import asyncio
import logging
import sys
from pathlib import Path

# Configuration du logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Ajout du répertoire racine au path
sys.path.append(str(Path(__file__).parent.parent.parent))

from project_core.webapp_from_scripts.backend_manager import BackendManager

async def test_backend_simple():
    """Test simple du backend manager"""
    
    # Configuration minimale
    config = {
        'module': 'argumentation_analysis.services.web_api.app',
        'start_port': 5003,
        'fallback_ports': [5004],
        'timeout_seconds': 30,
        'health_endpoint': '/api/health'
    }
    
    logger = logging.getLogger("TestBackend")
    
    # Création du manager
    backend = BackendManager(config, logger)
    
    print("=== TEST BACKEND SIMPLE ===")
    
    try:
        print("[1] Démarrage backend...")
        result = await backend.start_with_failover()
        
        if result['success']:
            print(f"[OK] Backend démarré sur {result['url']}")
            print(f"     Port: {result['port']}")
            print(f"     PID: {result['pid']}")
            
            print("[2] Test health check...")
            health_ok = await backend.health_check()
            
            if health_ok:
                print("[OK] Health check réussi")
            else:
                print("[ERROR] Health check échoué")
            
            print("[3] Arrêt backend...")
            await backend.stop()
            print("[OK] Backend arrêté")
            
        else:
            print(f"[ERROR] Échec démarrage: {result['error']}")
            
    except Exception as e:
        print(f"[EXCEPTION] {e}")
        # Cleanup en cas d'erreur
        try:
            await backend.stop()
        except:
            pass

if __name__ == '__main__':
    asyncio.run(test_backend_simple())