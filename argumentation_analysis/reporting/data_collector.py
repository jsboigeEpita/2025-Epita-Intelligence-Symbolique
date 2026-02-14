#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module pour la collecte de données brutes et de configuration nécessaires à la construction des rapports.
"""

import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

# Import des modèles de données depuis le module local
# On suppose que ReportMetadata, ReportConfiguration, et UnifiedReportTemplate sont définis dans models.py
from .models import ReportMetadata, ReportConfiguration, UnifiedReportTemplate

logger = logging.getLogger(__name__)

# Fonctions migrées et adaptées depuis argumentation_analysis/core/report_generation.py (UnifiedReportGenerator)


def load_reporting_config(config_file_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Charge la configuration pour la génération de rapports.
    Combine une configuration par défaut avec une configuration chargée depuis un fichier YAML.
    """
    default_config = {
        "default_format": "markdown",
        "output_directory": "./reports",  # Ce chemin sera relatif à l'endroit où la fonction est appelée
        "templates_directory": "./config/report_templates",  # Idem
        "unified_output": True,
        "component_specific_templates": True,
        "formats": {
            "console": {
                "max_lines": 25,
                "color_support": True,
                "highlight_errors": True,
                "show_orchestration_metrics": True,
            },
            "markdown": {
                "include_metadata": True,
                "conversation_format": True,
                "technical_details": True,
                "include_toc": False,
                "orchestration_details": True,
                "performance_metrics": True,
            },
            "json": {
                "pretty_print": True,
                "include_metadata": True,
                "structured_orchestration": True,
            },
            "html": {
                "responsive": True,
                "include_charts": False,
                "modern_styling": True,
                "component_badges": True,
            },
        },
        "component_settings": {
            "orchestrators": {
                "include_execution_plan": True,
                "include_agent_results": True,
                "include_timing_analysis": True,
            },
            "pipelines": {
                "include_pipeline_stages": True,
                "include_data_flow": True,
                "include_error_handling": True,
            },
            "analysis_components": {
                "include_detailed_results": True,
                "include_confidence_scores": True,
                "include_source_context": True,
            },
        },
    }

    if config_file_path and Path(config_file_path).exists():
        try:
            with open(config_file_path, "r", encoding="utf-8") as f:
                file_config = yaml.safe_load(f)
                if file_config:  # S'assurer que file_config n'est pas None
                    # Fusion: file_config écrase les clés de default_config, y compris les dictionnaires imbriqués.
                    for key, value in file_config.items():
                        if (
                            isinstance(value, dict)
                            and key in default_config
                            and isinstance(default_config[key], dict)
                        ):
                            default_config[key].update(
                                value
                            )  # Fusionner les sous-dictionnaires
                        else:
                            default_config[key] = value
            logger.info(
                f"Configuration de reporting chargée et fusionnée depuis {config_file_path}"
            )
        except Exception as e:
            logger.warning(
                f"Erreur lors du chargement ou de la fusion de la configuration {config_file_path}: {e}. Utilisation de la configuration par défaut."
            )
    else:
        logger.info(
            "Aucun fichier de configuration de reporting fourni ou trouvé. Utilisation de la configuration par défaut."
        )

    return default_config


def load_report_templates(
    templates_directory_path: str,
    base_templates_config: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, UnifiedReportTemplate]:
    """
    Charge les templates de rapport.
    Combine des templates de base (hardcodés ou passés en argument) avec ceux chargés depuis des fichiers YAML.
    Nécessite UnifiedReportTemplate de .models.
    """
    templates: Dict[str, UnifiedReportTemplate] = {}

    # Charger les templates de base si fournis
    if base_templates_config:
        for name, config_data in base_templates_config.items():
            try:
                templates[name] = UnifiedReportTemplate(config_data)
                logger.debug(f"Template de base chargé: {name}")
            except Exception as e:
                logger.error(
                    f"Erreur lors du chargement du template de base '{name}': {e}"
                )

    # Charger les templates personnalisés depuis le répertoire spécifié
    templates_dir = Path(templates_directory_path)
    if templates_dir.exists() and templates_dir.is_dir():
        for template_file in templates_dir.glob("*.yaml"):
            try:
                with open(template_file, "r", encoding="utf-8") as f:
                    template_config_from_file = yaml.safe_load(f)
                    if template_config_from_file:
                        template_name = template_file.stem
                        templates[template_name] = UnifiedReportTemplate(
                            template_config_from_file
                        )
                        logger.debug(
                            f"Template personnalisé chargé depuis fichier: {template_name}"
                        )
                    else:
                        logger.warning(
                            f"Fichier template YAML vide ignoré: {template_file}"
                        )
            except Exception as e:
                logger.warning(
                    f"Erreur lors du chargement du template depuis {template_file}: {e}"
                )
    else:
        logger.warning(
            f"Répertoire de templates non trouvé ou n'est pas un répertoire: {templates_directory_path}"
        )

    default_hardcoded_templates_config = {
        "default": {
            "name": "default",
            "format_type": "markdown",
            "sections": [
                "metadata",
                "summary",
                "informal_analysis",
                "formal_analysis",
                "recommendations",
            ],
        },
        "console_summary": {
            "name": "console_summary",
            "format_type": "console",
            "sections": ["summary", "informal_analysis", "performance"],
        },
        "detailed_analysis": {
            "name": "detailed_analysis",
            "format_type": "markdown",
            "sections": [
                "metadata",
                "summary",
                "informal_analysis",
                "formal_analysis",
                "conversation",
                "recommendations",
                "performance",
            ],
        },
        "web_presentation": {
            "name": "web_presentation",
            "format_type": "html",
            "sections": ["metadata", "summary", "informal_analysis", "performance"],
        },
        "orchestrator_execution": {
            "name": "orchestrator_execution",
            "format_type": "markdown",
            "sections": [
                "metadata",
                "orchestration_results",
                "summary",
                "performance",
                "recommendations",
            ],
        },
        "llm_orchestration": {
            "name": "llm_orchestration",
            "format_type": "markdown",
            "sections": [
                "metadata",
                "orchestration_results",
                "conversation",
                "informal_analysis",
                "recommendations",
            ],
        },
        "conversation_orchestration": {
            "name": "conversation_orchestration",
            "format_type": "markdown",
            "sections": [
                "metadata",
                "conversation",
                "orchestration_results",
                "summary",
                "recommendations",
            ],
        },
        "unified_text_analysis": {
            "name": "unified_text_analysis",
            "format_type": "markdown",
            "sections": [
                "metadata",
                "summary",
                "informal_analysis",
                "formal_analysis",
                "performance",
            ],
        },
        "source_management": {
            "name": "source_management",
            "format_type": "markdown",
            "sections": [
                "metadata",
                "source_summary",
                "processing_results",
                "recommendations",
            ],
        },
        "advanced_rhetoric": {
            "name": "advanced_rhetoric",
            "format_type": "markdown",
            "sections": [
                "metadata",
                "rhetorical_analysis",
                "sophistication_metrics",
                "manipulation_assessment",
                "recommendations",
            ],
        },
    }

    for name, config_data in default_hardcoded_templates_config.items():
        if name not in templates:
            try:
                templates[name] = UnifiedReportTemplate(config_data)
                logger.debug(f"Template par défaut (hardcodé) chargé: {name}")
            except Exception as e:
                logger.error(
                    f"Erreur lors du chargement du template par défaut (hardcodé) '{name}': {e}"
                )

    if not templates:
        logger.warning("Aucun template de rapport n'a été chargé.")

    return templates


class DataCollector:
    """
    Collects all necessary data for report generation.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initializes the DataCollector.

        Args:
            config: Configuration object.
        """
        self.config = config
        logger.info("DataCollector initialized.")

    def gather_all_data(self) -> Dict[str, Any]:
        """
        Gathers all data required for the report.
        This is a placeholder and should be implemented to collect actual data
        from various sources based on the configuration.

        Returns:
            A dictionary containing all collected data.
        """
        logger.info("Gathering all data for the report...")
        # Placeholder: In a real scenario, this method would interact with
        # various services or data sources to collect information.
        # Example:
        # raw_data = self._fetch_database_records()
        # analysis_results = self._run_analysis_pipeline()
        # system_metrics = self._get_system_metrics()

        # For now, returning a dummy structure
        report_data = {
            "title": "Rapport d'Analyse Automatique",
            "metadata": {
                "source_description": "Données d'exemple",
                "source_type": "Simulation",
                "text_length": 1024,
                "processing_time_ms": 150,
            },
            "summary": {
                "rhetorical_sophistication": "Modérée",
                "manipulation_level": "Faible",
                "logical_validity": "Acceptable",
                "confidence_score": 0.85,
                "orchestration_summary": {
                    "agents_count": 3,
                    "orchestration_time_ms": 120,
                    "execution_status": "Succès",
                },
            },
            "informal_analysis": {
                "fallacies": [
                    {
                        "type": "Ad Hominem",
                        "text_fragment": "...",
                        "explanation": "...",
                        "severity": "Modéré",
                        "confidence": 0.75,
                    }
                ]
            },
            "performance_metrics": {
                "total_execution_time_ms": 500,
                "memory_usage_mb": 128,
                "active_agents_count": 3,
                "success_rate": 1.0,
            },
            # Add other necessary data sections here
        }
        logger.info("Data gathering complete.")
        return report_data
