#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Modèles de données pour la génération de rapports.
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional


@dataclass
class ReportMetadata:
    """Métadonnées standardisées pour tous les rapports."""

    source_component: str  # Composant source (orchestrator, pipeline, etc.)
    analysis_type: str  # Type d'analyse (conversation, LLM, rhetoric, etc.)
    generated_at: datetime
    version: str = "1.0.0"
    generator: str = "UnifiedReportGeneration"
    format_type: str = "markdown"
    template_name: str = "default"


@dataclass
class ReportConfiguration:
    """Configuration complète pour la génération de rapports."""

    output_format: str = "markdown"  # console, markdown, json, html
    template_name: str = "default"
    output_mode: str = "file"  # file, console, both
    include_metadata: bool = True
    include_visualizations: bool = False
    include_recommendations: bool = True
    output_directory: Optional[Path] = None
    custom_sections: Optional[List[str]] = None
