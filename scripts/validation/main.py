#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Système de Validation Unifié
============================

Consolide toutes les capacités de validation du système :
- Authenticité des composants (LLM, Tweety, Taxonomie)
- Écosystème complet (Sources, Orchestration, Verbosité, Formats)
- Orchestrateurs unifiés (Conversation, RealLLM)
import argumentation_analysis.core.environment
- Intégration et performance

Fichiers sources consolidés :
- scripts/validate_authentic_system.py
- scripts/validate_complete_ecosystem.py  
- scripts/validate_unified_orchestrations.py
- scripts/validate_unified_orchestrations_simple.py
"""

import argparse
import asyncio
import os
import sys
import json
import time
import traceback
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum  # Keep Enum for EnumEncoder if not moved

# Configuration de l'encodage pour Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# Ajout du chemin pour les imports
PROJECT_ROOT = (
    Path(__file__).resolve().parent.parent.parent
)  # Project root is three levels up
sys.path.insert(0, str(PROJECT_ROOT))  # Add the actual project root to sys.path

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("UnifiedValidatorMain")

# Importations depuis core.py et les validateurs
from .core import (
    ValidationMode,
    ValidationConfiguration,
    ValidationReport,
    EnumEncoder,
    AuthenticityReport,
)
from .validators import (
    authenticity_validator,
    ecosystem_validator,
    orchestration_validator,
    integration_validator,
    performance_validator,
    simple_validator,
    epita_diagnostic_validator,
)


class UnifiedValidationSystem:
    """Système de validation unifié consolidant toutes les capacités."""

    def __init__(self, config: ValidationConfiguration = None):
        """Initialise le système de validation."""
        self.config = config or ValidationConfiguration()
        self.logger = logging.getLogger(__name__)

        # Échantillons de texte pour les tests
        self.test_texts = self.config.test_text_samples or [
            "L'Ukraine a été créée par la Russie. Donc Poutine a raison.",
            "Si tous les hommes sont mortels et Socrate est un homme, alors Socrate est mortel.",
            "Le changement climatique est réel. Les politiques doivent agir maintenant.",
            "Tous les oiseaux volent. Les pingouins sont des oiseaux. Donc les pingouins volent.",
            "Cette affirmation est manifestement fausse car elle contient une contradiction logique.",
        ]

        # Composants disponibles
        self.available_components = self._detect_available_components()

        # Rapport de validation
        self.report = ValidationReport(
            validation_time=datetime.now().isoformat(),
            configuration=self.config,
            authenticity_results={},
            ecosystem_results={},
            orchestration_results={},
            integration_results={},
            performance_results={},
            summary={},
            errors=[],
            recommendations=[],
        )

    def _detect_available_components(self) -> Dict[str, bool]:
        """Détecte les composants disponibles."""
        components = {
            "unified_config": False,
            "llm_service": False,
            "fol_agent": False,
            "conversation_orchestrator": False,
            "real_llm_orchestrator": False,
            "source_selector": False,
            "tweety_analyzer": False,
            "unified_analysis": False,
        }

        # Test des imports
        try:
            from config.unified_config import (
                UnifiedConfig,
                MockLevel,
                TaxonomySize,
                LogicType,
                PresetConfigs,
            )

            components["unified_config"] = True
        except ImportError:
            pass

        try:
            from argumentation_analysis.core.services.llm_service import LLMService

            components["llm_service"] = True
        except ImportError:
            pass

        try:
            from argumentation_analysis.agents.core.logic.fol_logic_agent import (
                FirstOrderLogicAgent,
            )

            components["fol_agent"] = True
        except ImportError:
            pass

        try:
            from argumentation_analysis.orchestration.conversation_orchestrator import (
                ConversationOrchestrator,
            )

            components["conversation_orchestrator"] = True
        except ImportError:
            pass

        try:
            from argumentation_analysis.orchestration.real_llm_orchestrator import (
                RealLLMOrchestrator,
            )

            components["real_llm_orchestrator"] = True
        except ImportError:
            pass

        try:
            from scripts.core.unified_source_selector import UnifiedSourceSelector

            components["source_selector"] = True
        except ImportError:
            pass

        try:
            from argumentation_analysis.utils.tweety_error_analyzer import (
                TweetyErrorAnalyzer,
            )

            components["tweety_analyzer"] = True
        except ImportError:
            pass

        try:
            from argumentation_analysis.pipelines.unified_text_analysis import (
                UnifiedAnalysisConfig,
            )

            components["unified_analysis"] = True
        except ImportError:
            pass

        available_count = sum(components.values())
        total_count = len(components)

        self.logger.info(f"Composants détectés: {available_count}/{total_count}")
        for comp, available in components.items():
            status = "✓" if available else "✗"
            self.logger.debug(f"  {status} {comp}")

        return components

    async def run_validation(self) -> ValidationReport:
        """Exécute la validation complète selon le mode configuré."""
        self.logger.info(f"🚀 Démarrage validation mode: {self.config.mode.value}")

        start_time = time.time()

        try:
            # Sélection des validations selon le mode
            if (
                self.config.mode == ValidationMode.AUTHENTICITY
                or self.config.mode == ValidationMode.FULL
            ):
                self.report.authenticity_results = (
                    await authenticity_validator.validate_authenticity(
                        self.report.errors, self.available_components
                    )
                )

            if (
                self.config.mode == ValidationMode.ECOSYSTEM
                or self.config.mode == ValidationMode.FULL
            ):
                self.report.ecosystem_results = (
                    await ecosystem_validator.validate_ecosystem(
                        self.report.errors, self.available_components
                    )
                )

            if (
                self.config.mode == ValidationMode.ORCHESTRATION
                or self.config.mode == ValidationMode.FULL
            ):
                self.report.orchestration_results = (
                    await orchestration_validator.validate_orchestration(
                        self.report.errors, self.available_components, self.test_texts
                    )
                )

            if (
                self.config.mode == ValidationMode.INTEGRATION
                or self.config.mode == ValidationMode.FULL
            ):
                self.report.integration_results = (
                    await integration_validator.validate_integration(
                        self.report.errors, self.available_components, self.test_texts
                    )
                )

            if (
                self.config.mode == ValidationMode.PERFORMANCE
                or self.config.mode == ValidationMode.FULL
            ):
                if self.config.enable_performance_tests:  # Check from config
                    self.report.performance_results = (
                        await performance_validator.validate_performance(
                            self.report.errors,
                            self.available_components,
                            self.test_texts,
                        )
                    )
                else:
                    self.logger.info(
                        "Tests de performance désactivés par configuration."
                    )
                    self.report.performance_results = {
                        "status": "skipped",
                        "reason": "disabled_by_config",
                    }

            if self.config.mode == ValidationMode.SIMPLE:
                # Le validateur simple peut avoir besoin d'une configuration spécifique ou utiliser des valeurs par défaut
                self.report.ecosystem_results[
                    "simple_validation"
                ] = await simple_validator.validate_simple(
                    self.report.errors,
                    self.available_components,  # Pass config if needed by simple_validator
                )

            if self.config.mode == ValidationMode.EPITA_DIAGNOSTIC:
                self.report.ecosystem_results[
                    "epita_diagnostic"
                ] = await epita_diagnostic_validator.validate_epita_diagnostic(
                    self.report.errors,
                    self.available_components,  # Pass config if needed
                )

            # Génération du résumé
            self._generate_summary()

            # Génération des recommandations
            self._generate_recommendations()

        except Exception as e:
            self.report.errors.append(
                {
                    "context": "validation_main_run",  # More specific context
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                }
            )
            self.logger.error(
                f"❌ Erreur majeure lors de la validation: {e}", exc_info=True
            )  # Log with traceback

        total_time = time.time() - start_time
        # Ensure performance_results is a dict before updating
        if not isinstance(self.report.performance_results, dict):
            self.report.performance_results = {}
        self.report.performance_results["total_validation_time"] = total_time

        self.logger.info(f"✅ Validation terminée en {total_time:.2f}s")

        # Sauvegarde du rapport
        if self.config.save_report:
            await self._save_report()

        return self.report

    # Les méthodes _validate_authenticity, _validate_llm_service_authenticity,
    # _validate_tweety_service_authenticity, _validate_taxonomy_authenticity,
    # _validate_configuration_coherence, _validate_ecosystem, _validate_source_management,
    # _validate_orchestration_modes, _validate_verbosity_levels, _validate_output_formats,
    # _validate_cli_interface, _validate_orchestration, _test_conversation_orchestrator,
    # _test_real_llm_orchestrator, _validate_integration, _test_orchestrator_handoff,
    # _test_config_mapping, _validate_performance, _benchmark_orchestration,
    # _benchmark_throughput, et _validate_simple SONT SUPPRIMÉES ICI.
    # Leur logique est maintenant dans les modules validateurs séparés.

    def _generate_summary(self):
        """Génère un résumé de la validation."""
        summary = {
            "validation_mode": self.config.mode.value,
            "total_components_detected": sum(self.available_components.values()),
            "total_components_possible": len(self.available_components),
            "component_availability_percentage": (
                sum(self.available_components.values()) / len(self.available_components)
            )
            * 100,
            "validation_sections": {},
            "overall_status": "unknown",
            "error_count": len(self.report.errors),
        }

        # Statuts des sections
        sections = [
            ("authenticity", self.report.authenticity_results),
            ("ecosystem", self.report.ecosystem_results),
            ("orchestration", self.report.orchestration_results),
            ("integration", self.report.integration_results),
            ("performance", self.report.performance_results),
        ]

        successful_sections = 0
        total_sections = 0

        for section_name, section_results in sections:
            if section_results:
                total_sections += 1

                # Déterminer le statut de la section
                if isinstance(section_results, dict):
                    if section_results.get("errors"):
                        summary["validation_sections"][section_name] = "failed"
                    elif any(
                        sub_result.get("status") == "success"
                        for sub_result in section_results.values()
                        if isinstance(sub_result, dict)
                    ):
                        summary["validation_sections"][section_name] = "success"
                        successful_sections += 1
                    else:
                        summary["validation_sections"][section_name] = "partial"
                else:
                    summary["validation_sections"][section_name] = "unknown"

        # Statut global
        if total_sections == 0:
            summary["overall_status"] = "no_tests"
        elif successful_sections == total_sections and len(self.report.errors) == 0:
            summary["overall_status"] = "success"
        elif successful_sections > 0:
            summary["overall_status"] = "partial"
        else:
            summary["overall_status"] = "failed"

        summary["success_rate"] = (
            (successful_sections / total_sections * 100) if total_sections > 0 else 0
        )

        self.report.summary = summary

    def _generate_recommendations(self):
        """Génère des recommandations basées sur les résultats."""
        recommendations = []

        # Recommandations basées sur la disponibilité des composants
        unavailable_components = [
            comp
            for comp, available in self.available_components.items()
            if not available
        ]

        if unavailable_components:
            recommendations.append(
                f"Composants manquants ({len(unavailable_components)}): {', '.join(unavailable_components)}"
            )
            recommendations.append(
                "Installer les dépendances manquantes pour une validation complète"
            )

        # Recommandations basées sur les erreurs
        if self.report.errors:
            recommendations.append(
                f"Résoudre {len(self.report.errors)} erreur(s) détectée(s)"
            )

            # Erreurs spécifiques
            error_contexts = [
                error.get("context", "unknown") for error in self.report.errors
            ]
            unique_contexts = list(set(error_contexts))

            for context in unique_contexts:
                recommendations.append(
                    f"Examiner les erreurs dans le contexte: {context}"
                )

        # Recommandations basées sur l'authenticité
        if self.report.authenticity_results:
            auth_results = self.report.authenticity_results

            for component, result in auth_results.items():
                if isinstance(result, dict) and result.get("status") in [
                    "mock_or_invalid",
                    "incoherent",
                ]:
                    recommendations.append(
                        f"Configurer correctement le composant: {component}"
                    )

        # Recommandations de performance
        if self.report.performance_results:
            perf_results = self.report.performance_results
            total_time = perf_results.get("total_validation_time", 0)

            if total_time > 60:
                recommendations.append(
                    "Temps de validation élevé - optimiser les configurations de test"
                )

        # Recommandations générales
        if not recommendations:
            recommendations.append(
                "Système validé avec succès - aucune recommandation spécifique"
            )
        else:
            recommendations.insert(0, "Recommandations pour améliorer le système :")

        self.report.recommendations = recommendations

    async def _save_report(self):
        """Sauvegarde le rapport de validation."""
        if not self.config.report_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.config.report_path = f"validation_report_{timestamp}.json"

        try:
            # Conversion du rapport en dictionnaire
            report_dict = {
                "validation_time": self.report.validation_time,
                "configuration": {
                    "mode": self.config.mode.value,
                    "enable_real_components": self.config.enable_real_components,
                    "enable_performance_tests": self.config.enable_performance_tests,
                    "timeout_seconds": self.config.timeout_seconds,
                    "output_format": self.config.output_format,
                },
                "available_components": self.available_components,
                "authenticity_results": self.report.authenticity_results,
                "ecosystem_results": self.report.ecosystem_results,
                "orchestration_results": self.report.orchestration_results,
                "integration_results": self.report.integration_results,
                "performance_results": self.report.performance_results,
                "summary": self.report.summary,
                "errors": self.report.errors,
                "recommendations": self.report.recommendations,
            }

            # Sauvegarde JSON
            report_path = Path(self.config.report_path)
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(report_dict, f, indent=2, ensure_ascii=False, cls=EnumEncoder)

            self.logger.info(f"📄 Rapport sauvegardé: {report_path}")

            # Sauvegarde HTML si demandé
            if self.config.output_format == "html":
                html_path = report_path.with_suffix(".html")
                await self._save_html_report(html_path, report_dict)
                self.logger.info(f"🌐 Rapport HTML sauvegardé: {html_path}")

        except Exception as e:
            self.logger.error(f"❌ Erreur sauvegarde rapport: {e}")

    async def _save_html_report(self, html_path: Path, report_dict: Dict[str, Any]):
        """Sauvegarde le rapport en format HTML."""
        html_content = f"""
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Rapport de Validation - {report_dict['validation_time']}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background: #f0f0f0; padding: 20px; border-radius: 5px; }}
        .section {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
        .success {{ background: #d4edda; }}
        .warning {{ background: #fff3cd; }}
        .error {{ background: #f8d7da; }}
        .code {{ background: #f8f9fa; padding: 10px; border-radius: 3px; font-family: monospace; }}
        ul {{ margin: 10px 0; }}
        li {{ margin: 5px 0; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Rapport de Validation Unifié</h1>
        <p><strong>Date:</strong> {report_dict['validation_time']}</p>
        <p><strong>Mode:</strong> {report_dict['configuration']['mode']}</p>
        <p><strong>Statut global:</strong> {report_dict['summary'].get('overall_status', 'unknown')}</p>
    </div>
    
    <div class="section">
        <h2>Résumé</h2>
        <p><strong>Composants détectés:</strong> {report_dict['summary'].get('total_components_detected', 0)}/{report_dict['summary'].get('total_components_possible', 0)}</p>
        <p><strong>Taux de succès:</strong> {report_dict['summary'].get('success_rate', 0):.1f}%</p>
        <p><strong>Erreurs:</strong> {report_dict['summary'].get('error_count', 0)}</p>
    </div>
    
    <div class="section">
        <h2>Composants Disponibles</h2>
        <ul>
"""

        for component, available in report_dict["available_components"].items():
            status = "✅" if available else "❌"
            html_content += f"            <li>{status} {component}</li>\n"

        html_content += """        </ul>
    </div>
    
    <div class="section">
        <h2>Recommandations</h2>
        <ul>
"""

        for recommendation in report_dict["recommendations"]:
            html_content += f"            <li>{recommendation}</li>\n"

        html_content += (
            """        </ul>
    </div>
    
    <div class="section">
        <h2>Détails Techniques</h2>
        <div class="code">
            <pre>"""
            + json.dumps(report_dict, indent=2, ensure_ascii=False)
            + """</pre>
        </div>
    </div>
</body>
</html>"""
        )

        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)


def create_validation_factory(mode: str = "full", **kwargs) -> UnifiedValidationSystem:
    """Factory pour créer un système de validation avec configuration prédéfinie."""

    mode_configs = {
        "full": ValidationConfiguration(
            mode=ValidationMode.FULL,
            enable_real_components=True,
            enable_performance_tests=True,
            enable_integration_tests=True,
            verbose=True,
        ),
        "simple": ValidationConfiguration(
            mode=ValidationMode.SIMPLE,
            enable_real_components=False,
            enable_performance_tests=False,
            enable_integration_tests=False,
            verbose=False,
        ),
        "authenticity": ValidationConfiguration(
            mode=ValidationMode.AUTHENTICITY,
            enable_real_components=True,
            enable_performance_tests=False,
            enable_integration_tests=False,
        ),
        "ecosystem": ValidationConfiguration(
            mode=ValidationMode.ECOSYSTEM,
            enable_performance_tests=True,
            enable_integration_tests=True,
        ),
        "orchestration": ValidationConfiguration(
            mode=ValidationMode.ORCHESTRATION,
            enable_real_components=True,
            enable_performance_tests=True,
        ),
        "performance": ValidationConfiguration(
            mode=ValidationMode.PERFORMANCE,
            enable_performance_tests=True,
            timeout_seconds=600,
        ),
    }

    config = mode_configs.get(mode, mode_configs["full"])

    # Application des overrides
    for key, value in kwargs.items():
        if hasattr(config, key):
            setattr(config, key, value)

    return UnifiedValidationSystem(config)


async def main():
    """Point d'entrée principal."""
    parser = argparse.ArgumentParser(description="Système de Validation Unifié")
    # Updated choices to match ValidationMode enum values
    parser.add_argument(
        "--mode",
        choices=[mode.value for mode in ValidationMode],
        default=ValidationMode.FULL.value,
        help="Mode de validation",
    )
    parser.add_argument(
        "--output",
        choices=["json", "text", "html"],
        default="json",
        help="Format de sortie",
    )
    parser.add_argument("--report-path", help="Chemin du rapport de sortie")
    parser.add_argument("--timeout", type=int, default=300, help="Timeout en secondes")
    parser.add_argument(
        "--no-real-components",
        action="store_true",
        help="Désactiver les composants réels",
    )
    parser.add_argument(
        "--no-performance",
        action="store_true",
        help="Désactiver les tests de performance",
    )
    parser.add_argument("--verbose", action="store_true", help="Mode verbeux")

    args = parser.parse_args()

    # Configuration du système
    validator = create_validation_factory(
        mode=args.mode,
        output_format=args.output,
        report_path=args.report_path,
        timeout_seconds=args.timeout,
        enable_real_components=not args.no_real_components,
        enable_performance_tests=not args.no_performance,
        verbose=args.verbose,
    )

    try:
        # Exécution de la validation
        report = await validator.run_validation()

        # Affichage du résumé
        print("\n" + "=" * 60)
        print("RAPPORT DE VALIDATION UNIFIÉ")
        print("=" * 60)
        print(f"Mode: {args.mode}")
        print(f"Statut: {report.summary.get('overall_status', 'unknown')}")
        print(
            f"Composants: {report.summary.get('total_components_detected', 0)}/{report.summary.get('total_components_possible', 0)}"
        )
        print(f"Taux de succès: {report.summary.get('success_rate', 0):.1f}%")
        print(f"Erreurs: {len(report.errors)}")

        if report.recommendations:
            print("\nRecommandations:")
            for rec in report.recommendations[:5]:  # Limiter l'affichage
                print(f"  • {rec}")

        print("=" * 60)

        return 0 if report.summary.get("overall_status") == "success" else 1

    except Exception as e:
        logger.error(f"❌ Erreur lors de l'exécution: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
