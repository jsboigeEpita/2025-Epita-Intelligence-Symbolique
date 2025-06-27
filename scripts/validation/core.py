import argumentation_analysis.core.environment
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Core components for the Unified Validation System.
"""

import json
from enum import Enum
from dataclasses import dataclass
from typing import Dict, Any, List, Optional

class ValidationMode(Enum):
    """Modes de validation disponibles."""
    AUTHENTICITY = "authenticity"        # Validation de l'authenticité des composants
    ECOSYSTEM = "ecosystem"              # Validation complète de l'écosystème
    ORCHESTRATION = "orchestration"      # Validation des orchestrateurs
    INTEGRATION = "integration"          # Validation de l'intégration
    PERFORMANCE = "performance"          # Tests de performance
    FULL = "full"                       # Validation complète
    SIMPLE = "simple"                   # Version simplifiée sans emojis
    EPITA_DIAGNOSTIC = "epita-diagnostic"  # Diagnostic spécialisé pour le contexte Épita

@dataclass
class ValidationConfiguration:
    """Configuration pour la validation unifiée."""
    mode: ValidationMode = ValidationMode.FULL
    enable_real_components: bool = True
    enable_performance_tests: bool = True
    enable_integration_tests: bool = True
    timeout_seconds: int = 300
    output_format: str = "json"          # json, text, html
    save_report: bool = True
    report_path: Optional[str] = None
    verbose: bool = True
    test_text_samples: List[str] = None

@dataclass
class ValidationReport:
    """Rapport complet de validation."""
    validation_time: str
    configuration: ValidationConfiguration
    authenticity_results: Dict[str, Any]
    ecosystem_results: Dict[str, Any]
    orchestration_results: Dict[str, Any]
    integration_results: Dict[str, Any]
    performance_results: Dict[str, Any]
    summary: Dict[str, Any]
    errors: List[Dict[str, Any]]
    recommendations: List[str]

class EnumEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Enum):
            return obj.value
        return super().default(obj)

@dataclass
class AuthenticityReport:
    """Rapport d'authenticité du système."""
    total_components: int
    authentic_components: int
    mock_components: int
    authenticity_percentage: float
    is_100_percent_authentic: bool
    component_details: Dict[str, Any]
    validation_errors: List[str]
    performance_metrics: Dict[str, float]
    recommendations: List[str]

# Il n'y avait pas d'exceptions personnalisées explicitement définies dans le fichier original.
# Si elles existent ailleurs ou sont implicites, elles devront être ajoutées ici.