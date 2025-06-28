#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Configuration unifiée pour le moteur d'orchestration.
"""

import dataclasses
from typing import Dict, List, Any, Optional, Union
from enum import Enum

# Définition des Enums pour la configuration de l'orchestration.

class OrchestrationMode(Enum):
    """Modes d'orchestration disponibles."""
    PIPELINE = "pipeline"
    REAL = "real"
    CONVERSATION = "conversation"
    HIERARCHICAL_FULL = "hierarchical_full"
    STRATEGIC_ONLY = "strategic_only"
    TACTICAL_COORDINATION = "tactical_coordination"
    OPERATIONAL_DIRECT = "operational_direct"
    CLUEDO_INVESTIGATION = "cluedo_investigation"
    LOGIC_COMPLEX = "logic_complex"
    ADAPTIVE_HYBRID = "adaptive_hybrid"
    AUTO_SELECT = "auto_select"

class AnalysisType(Enum):
    """Types d'analyse supportés."""
    COMPREHENSIVE = "comprehensive"
    RHETORICAL = "rhetorical"
    LOGICAL = "logical"
    INVESTIGATIVE = "investigative"
    FALLACY_FOCUSED = "fallacy_focused"
    ARGUMENT_STRUCTURE = "argument_structure"
    DEBATE_ANALYSIS = "debate_analysis"
    CUSTOM = "custom"

@dataclasses.dataclass
class OrchestrationConfig:
    """
    Configuration unifiée et non redondante pour le moteur d'orchestration.
    Synthétise UnifiedAnalysisConfig et ExtendedOrchestrationConfig.
    """
    analysis_modes: List[str] = dataclasses.field(default_factory=lambda: ["informal", "formal"])
    orchestration_mode: Union[str, OrchestrationMode] = OrchestrationMode.PIPELINE
    analysis_type: Union[str, AnalysisType] = AnalysisType.COMPREHENSIVE
    logic_type: str = "fol"
    use_mocks: bool = False
    use_advanced_tools: bool = True
    output_format: str = "detailed"
    enable_conversation_logging: bool = True
    enable_hierarchical_orchestration: bool = True
    enable_specialized_orchestrators: bool = True
    enable_communication_middleware: bool = True
    max_concurrent_analyses: int = 10
    analysis_timeout_seconds: int = 300
    auto_select_orchestrator_enabled: bool = True
    hierarchical_coordination_level: str = "full"
    specialized_orchestrator_priority_order: List[str] = dataclasses.field(
        default_factory=lambda: ["cluedo_investigation", "logic_complex", "conversation", "real"]
    )
    save_orchestration_trace_enabled: bool = True
    communication_middleware_config: Dict[str, Any] = dataclasses.field(default_factory=dict)

    def __post_init__(self):
        if isinstance(self.orchestration_mode, str):
            try:
                self.orchestration_mode = OrchestrationMode(self.orchestration_mode)
            except ValueError:
                # Garder la string si elle ne correspond pas à un membre de l'Enum
                pass
        if isinstance(self.analysis_type, str):
            try:
                self.analysis_type = AnalysisType(self.analysis_type)
            except ValueError:
                pass

