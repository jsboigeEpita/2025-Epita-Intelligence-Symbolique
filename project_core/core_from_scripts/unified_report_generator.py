#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
UnifiedReportGenerator - Interface CLI pour le générateur de rapports unifié.

Ce script offre une interface en ligne de commande pour utiliser le nouveau
système de génération de rapports unifié, tout en préservant la compatibilité
avec l'ancienne interface.

REFACTORISÉ: Maintenant délègue vers argumentation_analysis.core.report_generation
"""

import sys
import json
import logging
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

# Import du nouveau système unifié
try:
    from argumentation_analysis.core.report_generation import (
        UnifiedReportGenerator,
        ReportMetadata,
        ReportConfiguration,
        generate_quick_report,
        create_component_report_factory,
    )
except ImportError as e:
    print(f"❌ Erreur d'import du système unifié: {e}")
    print(
        "Assurez-vous que le module argumentation_analysis.core.report_generation est disponible"
    )
    sys.exit(1)

logger = logging.getLogger("UnifiedReportGeneratorCLI")


# Classes de compatibilité pour préserver l'interface existante
class ReportTemplate:
    """Wrapper de compatibilité pour l'ancienne interface ReportTemplate."""

    def __init__(self, template_config: Dict[str, Any]):
        self.config = template_config
        self.name = template_config.get("name", "default")
        self.format_type = template_config.get("format", "markdown")
        self.sections = template_config.get("sections", [])
        self.metadata = template_config.get("metadata", {})

    def render(self, data: Dict[str, Any]) -> str:
        """Compatibilité: délègue vers le générateur unifié."""
        logger.warning(
            "Utilisation de l'ancienne interface ReportTemplate - migration recommandée vers UnifiedReportGenerator"
        )

        # Créer le générateur unifié
        generator = UnifiedReportGenerator()

        # Créer les métadonnées
        metadata = ReportMetadata(
            source_component="LegacyReportTemplate",
            analysis_type="compatibility_mode",
            generated_at=datetime.now(),
            template_name=self.name,
        )

        # Configuration basée sur l'ancienne interface
        config = ReportConfiguration(
            output_format=self.format_type,
            template_name=self.name,
            output_mode="console",  # Pour compatibilité, retourne seulement le contenu
        )

        return generator.generate_unified_report(data, metadata, config)


class UnifiedReportGeneratorLegacy:
    """Wrapper de compatibilité pour l'ancienne interface UnifiedReportGenerator."""

    def __init__(self, config_path: Optional[str] = None):
        """Interface de compatibilité."""
        self.unified_generator = UnifiedReportGenerator(config_path)
        logger.info("Générateur de rapports unifié initialisé (mode compatibilité)")

    def generate_report(
        self,
        analysis_data: Dict[str, Any],
        format_type: str = "markdown",
        output_mode: str = "file",
        template: str = "default",
        output_path: Optional[str] = None,
    ) -> str:
        """Interface de compatibilité pour generate_report."""
        logger.info(
            f"Génération rapport (compatibilité) - Format: {format_type}, Template: {template}"
        )

        # Créer les métadonnées pour le nouveau système
        metadata = ReportMetadata(
            source_component="LegacyUnifiedReportGenerator",
            analysis_type="compatibility_generation",
            generated_at=datetime.now(),
            template_name=template,
        )

        # Configuration basée sur l'ancienne interface
        config = ReportConfiguration(
            output_format=format_type,
            template_name=template,
            output_mode=output_mode,
            output_directory=Path(output_path).parent if output_path else None,
        )

        return self.unified_generator.generate_unified_report(
            analysis_data, metadata, config
        )

    def list_available_templates(self) -> List[str]:
        """Interface de compatibilité."""
        return self.unified_generator.get_available_templates()

    def get_supported_formats(self) -> List[str]:
        """Interface de compatibilité."""
        return self.unified_generator.get_supported_formats()

    # Méthodes internes maintenues pour compatibilité
    def _enrich_analysis_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Compatibilité: délègue l'enrichissement vers le système unifié."""
        return self.unified_generator._enrich_analysis_data(data)

    def _assess_sophistication(self, fallacies: List[Dict]) -> str:
        """Compatibilité: délègue l'évaluation vers le système unifié."""
        return self.unified_generator._assess_sophistication(fallacies)

    def _assess_manipulation_level(self, fallacies: List[Dict]) -> str:
        """Compatibilité: délègue l'évaluation vers le système unifié."""
        return self.unified_generator._assess_manipulation_level(fallacies)


# Fonction de compatibilité pour usage direct
def create_legacy_generator(
    config_path: Optional[str] = None,
) -> UnifiedReportGeneratorLegacy:
    """Crée un générateur avec l'ancienne interface pour compatibilité."""
    return UnifiedReportGeneratorLegacy(config_path)


# API programmable pour les composants refactorisés
def create_orchestrator_report_api():
    """Crée une API de rapport spécialisée pour les orchestrateurs."""
    return create_component_report_factory("Orchestrator")


def create_pipeline_report_api():
    """Crée une API de rapport spécialisée pour les pipelines."""
    return create_component_report_factory("Pipeline")


def create_analysis_report_api():
    """Crée une API de rapport spécialisée pour les composants d'analyse."""
    return create_component_report_factory("AnalysisComponent")


def generate_component_report(
    component_name: str,
    analysis_data: Dict[str, Any],
    analysis_type: str = "analysis",
    output_format: str = "markdown",
    save_file: bool = True,
) -> str:
    """
    API simplifiée pour générer un rapport depuis n'importe quel composant refactorisé.

    Args:
        component_name: Nom du composant (RealLLMOrchestrator, ConversationOrchestrator, etc.)
        analysis_data: Données d'analyse à inclure
        analysis_type: Type d'analyse (orchestration, conversation, text_analysis, etc.)
        output_format: Format de sortie (markdown, json, html, console)
        save_file: Si True, sauvegarde le rapport dans un fichier

    Returns:
        str: Contenu du rapport généré
    """
    generator = UnifiedReportGenerator()

    metadata = ReportMetadata(
        source_component=component_name,
        analysis_type=analysis_type,
        generated_at=datetime.now(),
    )

    config = ReportConfiguration(
        output_format=output_format, output_mode="both" if save_file else "console"
    )

    return generator.generate_unified_report(analysis_data, metadata, config)


# Interface CLI principale
def main():
    """Interface en ligne de commande pour le générateur de rapports unifié."""
    parser = argparse.ArgumentParser(
        description="Générateur de rapports unifié pour l'analyse argumentative",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples d'utilisation:
  python unified_report_generator.py --data analysis_results.json --format markdown
  python unified_report_generator.py --data data.json --format html --template web
  python unified_report_generator.py --data results.json --format console --output-mode console
  
Modes de compatibilité:
  python unified_report_generator.py --legacy --data results.json  # Utilise l'ancienne interface
        """,
    )

    # Arguments principaux
    parser.add_argument(
        "--data",
        required=True,
        help="Chemin vers le fichier de données JSON à analyser",
    )
    parser.add_argument(
        "--format",
        choices=["markdown", "json", "html", "console"],
        default="markdown",
        help="Format de sortie du rapport",
    )
    parser.add_argument("--template", default="default", help="Template à utiliser")
    parser.add_argument(
        "--output-mode",
        choices=["file", "console", "both"],
        default="file",
        help="Mode de sortie",
    )
    parser.add_argument("--output-path", help="Chemin de sortie personnalisé")
    parser.add_argument("--config", help="Chemin vers le fichier de configuration")

    # Arguments pour le nouveau système unifié
    parser.add_argument(
        "--component", help="Nom du composant source (pour métadonnées)"
    )
    parser.add_argument("--analysis-type", default="general", help="Type d'analyse")

    # Mode de compatibilité
    parser.add_argument(
        "--legacy",
        action="store_true",
        help="Utilise l'ancienne interface pour compatibilité",
    )

    # Options de logging
    parser.add_argument("--verbose", action="store_true", help="Logging détaillé")
    parser.add_argument("--quiet", action="store_true", help="Sortie minimale")

    args = parser.parse_args()

    # Configuration du logging
    if args.verbose:
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
    elif args.quiet:
        logging.basicConfig(level=logging.ERROR)
    else:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    try:
        # Charger les données d'analyse
        data_path = Path(args.data)
        if not data_path.exists():
            logger.error(f"Fichier de données non trouvé: {data_path}")
            sys.exit(1)

        with open(data_path, "r", encoding="utf-8") as f:
            analysis_data = json.load(f)

        if args.legacy:
            # Mode de compatibilité avec l'ancienne interface
            logger.info("Utilisation du mode de compatibilité")
            generator = UnifiedReportGeneratorLegacy(args.config)

            report_content = generator.generate_report(
                analysis_data=analysis_data,
                format_type=args.format,
                output_mode=args.output_mode,
                template=args.template,
                output_path=args.output_path,
            )
        else:
            # Nouveau système unifié
            logger.info("Utilisation du système unifié")
            generator = UnifiedReportGenerator(args.config)

            # Métadonnées
            metadata = ReportMetadata(
                source_component=args.component or "CLI",
                analysis_type=args.analysis_type,
                generated_at=datetime.now(),
            )

            # Configuration
            config = ReportConfiguration(
                output_format=args.format,
                template_name=args.template,
                output_mode=args.output_mode,
                output_directory=Path(args.output_path).parent
                if args.output_path
                else None,
            )

            report_content = generator.generate_unified_report(
                analysis_data, metadata, config
            )

        if args.output_mode == "console":
            print("\n" + "=" * 60)
            print("RAPPORT GÉNÉRÉ AVEC SUCCÈS")
            print("=" * 60)
            print(f"Format: {args.format}")
            print(f"Template: {args.template}")
            print(f"Longueur: {len(report_content)} caractères")

    except Exception as e:
        logger.error(f"Erreur lors de la génération du rapport: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
