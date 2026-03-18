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
import argparse
from pathlib import Path
from typing import Dict, Any, List

# L'activation de l'environnement est gérée par le script de lancement.

# Import du runner JavaScript non-bloquant
from tests.e2e.runners.playwright_js_runner import PlaywrightJSRunner
from scripts.apps.webapp.unified_web_orchestrator import UnifiedWebOrchestrator


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

    def __init__(
        self, headless: bool = True, backend_port: int = 5001, frontend_port: int = 3000
    ):
        self.headless = headless
        self.backend_port = backend_port
        self.frontend_port = frontend_port
        self.logger = self._setup_logging()

        # L'orchestrateur sera initialisé plus tard
        self.orchestrator = None

    def _setup_logging(self) -> logging.Logger:
        """Configuration logging avec formatage coloré"""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        )
        return logging.getLogger(__name__)

    async def validate_web_interface(self) -> Dict[str, Any]:
        """
        Exécute la Phase 1 - Validation Web Interface JTMS Complète

        Returns:
            Dict contenant les résultats de validation
        """
        self.logger.info("=" * 60)
        self.logger.info("🧪 PHASE 1 - VALIDATION WEB INTERFACE JTMS COMPLÈTE")
        self.logger.info("=" * 60)

        # Configuration de l'orchestrateur
        # Fournir un mock pour `args`
        mock_args = argparse.Namespace(
            config="argumentation_analysis/webapp/config/webapp_config.yml",
            log_level="INFO",
            headless=self.headless,
            visible=not self.headless,
            timeout=20,
            no_trace=False,
        )
        self.orchestrator = UnifiedWebOrchestrator(args=mock_args)
        self.orchestrator.headless = self.headless

        try:
            # Démarrage des services
            self.logger.info("📡 Démarrage des services web (Backend & Frontend)...")
            success_start = await self.orchestrator.start_webapp(
                headless=self.headless, frontend_enabled=True
            )

            if not success_start:
                self.logger.error("❌ Échec du démarrage des services web.")
                return {"success": False, "error": "Failed to start web services"}

            self.logger.info(
                f"🌐 Frontend démarré sur: {self.orchestrator.app_info.frontend_url}"
            )

            # Création du runner Playwright AVEC la bonne URL
            playwright_config = self._get_jtms_test_config(
                self.headless, self.orchestrator.app_info.frontend_url
            )
            playwright_runner = PlaywrightJSRunner(playwright_config, self.logger)

            # Exécution des tests
            success = await playwright_runner.run_tests(
                runtime_config={"base_url": self.orchestrator.app_info.frontend_url}
            )

            results = playwright_runner.last_results or {}

            validation_result = {
                "phase": "Phase 1 - Validation Web Interface JTMS",
                "success": success,
                "results": results,
            }

            self._report_validation_results(validation_result)
            return validation_result

        except Exception as e:
            self.logger.error(f"❌ Erreur lors de la validation: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
        finally:
            if self.orchestrator:
                self.logger.info("🔄 Arrêt des services web...")
                await self.orchestrator.stop_webapp()
                self.logger.info("✅ Services web arrêtés.")

    def _get_jtms_test_config(self, headless: bool, base_url: str) -> Dict[str, Any]:
        """Configuration spécialisée pour tests JTMS"""
        return {
            "enabled": True,
            "browser": "chromium",
            "headless": headless,
            "timeout_ms": 300000,
            "slow_timeout_ms": 600000,
            "test_paths": ["tests/e2e/js/jtms-interface.spec.js"],
            "screenshots_dir": "logs/screenshots/jtms",
            "traces_dir": "logs/traces/jtms",
            "base_url": base_url,  # Utilisation de l'URL dynamique
            "retry_attempts": 2,
            "parallel_workers": 1,
        }

    def _report_validation_results(self, results: Dict[str, Any]):
        """Rapport détaillé des résultats de validation"""
        self.logger.info("=" * 60)
        self.logger.info("📊 RAPPORT DE VALIDATION JTMS")
        self.logger.info("=" * 60)

        status = "✅ SUCCÈS" if results["success"] else "❌ ÉCHEC"
        self.logger.info(f"Statut: {status}")
        self.logger.info(f"Phase: {results['phase']}")

        if "components_tested" in results:
            self.logger.info("🧪 Composants testés:")
            for component in results["components_tested"]:
                self.logger.info(f"   • {component}")

        if "results" in results and results["results"]:
            test_results = results["results"]
            self.logger.info("📈 Résultats détaillés:")
            for key, value in test_results.items():
                self.logger.info(f"   {key}: {value}")

        self.logger.info("=" * 60)


async def main():
    """Point d'entrée principal"""
    parser = argparse.ArgumentParser(description="Validation Web Interface JTMS")
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Lancer les tests en mode visible (non-headless)",
    )
    parser.add_argument(
        "--backend-port", type=int, default=5001, help="Port du serveur backend"
    )
    parser.add_argument(
        "--frontend-port", type=int, default=3000, help="Port du serveur frontend"
    )
    args = parser.parse_args()

    print("🧪 Démarrage Validation Web Interface JTMS")
    print("Utilisation de l'orchestrateur web pour démarrer les services.")
    print(f"Mode headless: {not args.headed}")
    print(f"Port backend: {args.backend_port}")
    print(f"Port frontend: {args.frontend_port}")
    print()

    validator = JTMSWebValidator(
        headless=not args.headed,
        backend_port=args.backend_port,
        frontend_port=args.frontend_port,
    )

    # Exécution de la validation
    results = await validator.validate_web_interface()

    # Statut final
    if results["success"]:
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
