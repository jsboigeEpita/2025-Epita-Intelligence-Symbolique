#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validation Web Interface JTMS - Phase 1
=======================================

Utilise le PlaywrightRunner de haut niveau pour la validation JTMS complète
en mode asynchrone non-bloquant.

Version: 1.0.0
Date: 11/06/2025
"""

import os
import sys
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, List

# Auto-activation environnement
try:
    # Remonte à la racine du projet depuis validation/web_interface/
    project_root = Path(__file__).resolve().parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    from scripts.core.auto_env import ensure_env
    ensure_env()
except ImportError as e:
    print(f"[ERROR] Auto-env OBLIGATOIRE manquant: {e}")
    print("Vérifiez que scripts/core/auto_env.py existe et est accessible")
    sys.exit(1)

# Import du runner JavaScript non-bloquant
from validation.runners.playwright_js_runner import PlaywrightJSRunner

class JTMSWebValidator:
    """
    Validateur Web Interface JTMS utilisant PlaywrightRunner
    
    Phase 1 - Validation Web Interface Complète :
    - Dashboard JTMS avec visualisation réseau
    - Gestion des sessions JTMS
    - Interface Sherlock/Watson
    - Tutoriel interactif
    - Playground JTMS
    - API et communication
    """
    
    def __init__(self):
        self.logger = self._setup_logging()
        self.config = self._get_jtms_test_config()
        self.playwright_runner = PlaywrightJSRunner(self.config, self.logger)
        
    def _setup_logging(self) -> logging.Logger:
        """Configuration logging avec formatage coloré"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            datefmt='%H:%M:%S'
        )
        return logging.getLogger(__name__)
    
    def _get_jtms_test_config(self) -> Dict[str, Any]:
        """Configuration spécialisée pour tests JTMS"""
        return {
            'enabled': True,
            'browser': 'chromium',
            'headless': False,  # Mode visible pour diagnostic
            'timeout_ms': 15000,
            'slow_timeout_ms': 30000,
            'test_paths': ['tests_playwright/tests/jtms-interface.spec.js'],
            'screenshots_dir': 'logs/screenshots/jtms',
            'traces_dir': 'logs/traces/jtms',
            'base_url': 'http://localhost:3000',
            'retry_attempts': 2,
            'parallel_workers': 1  # Séquentiel pour diagnostic
        }
    
    async def validate_web_interface(self) -> Dict[str, Any]:
        """
        Exécute la Phase 1 - Validation Web Interface JTMS Complète
        
        Returns:
            Dict contenant les résultats de validation
        """
        self.logger.info("=" * 60)
        self.logger.info("🧪 PHASE 1 - VALIDATION WEB INTERFACE JTMS COMPLÈTE")
        self.logger.info("=" * 60)
        
        # Configuration runtime pour tests JTMS
        runtime_config = {
            'backend_url': 'http://localhost:3000',
            'jtms_prefix': '/jtms',
            'test_mode': 'jtms_complete',
            'headless': False,
            'capture_screenshots': True,
            'capture_traces': True
        }
        
        self.logger.info("🔧 Configuration JTMS:")
        for key, value in runtime_config.items():
            self.logger.info(f"   {key}: {value}")
        
        try:
            # Exécution tests JTMS avec PlaywrightRunner
            self.logger.info("🚀 Lancement tests Web Interface JTMS...")
            
            success = await self.playwright_runner.run_tests(
                test_paths=['tests_playwright/tests/jtms-interface.spec.js'],
                runtime_config=runtime_config
            )
            
            # Récupération des résultats détaillés
            results = self.playwright_runner.last_results or {}
            
            # Analyse des résultats
            validation_result = {
                'phase': 'Phase 1 - Validation Web Interface JTMS',
                'success': success,
                'timestamp': '11/06/2025 10:34:00',
                'results': results,
                'components_tested': [
                    'Dashboard JTMS avec visualisation réseau',
                    'Gestion des sessions JTMS',
                    'Interface Sherlock/Watson',
                    'Tutoriel interactif',
                    'Playground JTMS',
                    'API et communication',
                    'Tests de performance',
                    'Utilitaires et nettoyage'
                ]
            }
            
            self._report_validation_results(validation_result)
            return validation_result
            
        except Exception as e:
            self.logger.error(f"❌ Erreur lors de la validation: {e}")
            return {
                'phase': 'Phase 1 - Validation Web Interface JTMS',
                'success': False,
                'error': str(e),
                'timestamp': '11/06/2025 10:34:00'
            }
    
    def _report_validation_results(self, results: Dict[str, Any]):
        """Rapport détaillé des résultats de validation"""
        self.logger.info("=" * 60)
        self.logger.info("📊 RAPPORT DE VALIDATION JTMS")
        self.logger.info("=" * 60)
        
        status = "✅ SUCCÈS" if results['success'] else "❌ ÉCHEC"
        self.logger.info(f"Statut: {status}")
        self.logger.info(f"Phase: {results['phase']}")
        
        if 'components_tested' in results:
            self.logger.info("🧪 Composants testés:")
            for component in results['components_tested']:
                self.logger.info(f"   • {component}")
        
        if 'results' in results and results['results']:
            test_results = results['results']
            self.logger.info("📈 Résultats détaillés:")
            for key, value in test_results.items():
                self.logger.info(f"   {key}: {value}")
        
        self.logger.info("=" * 60)

async def main():
    """Point d'entrée principal"""
    print("🧪 Démarrage Validation Web Interface JTMS")
    print("Utilisation du PlaywrightRunner asynchrone de haut niveau")
    print()
    
    validator = JTMSWebValidator()
    
    # Exécution de la validation
    results = await validator.validate_web_interface()
    
    # Statut final
    if results['success']:
        print("✅ Validation Web Interface JTMS terminée avec succès!")
        return 0
    else:
        print("❌ Validation Web Interface JTMS échouée.")
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n🛑 Validation interrompue par l'utilisateur")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Erreur critique: {e}")
        sys.exit(1)