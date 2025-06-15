#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Configuration unifiée pour le moteur d'orchestration.
"""

import dataclasses
from typing import Dict, List, Any, Optional, Union
from enum import Enum

# Définition des Enums (copiés depuis unified_orchestration_pipeline.py pour autonomie)
# Idéalement, ces Enums seraient dans un module partagé pour éviter la duplication.

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


def create_config_from_legacy(legacy_config: object) -> OrchestrationConfig:
    """
    Crée une instance de OrchestrationConfig à partir d'une configuration legacy
    (UnifiedAnalysisConfig ou ExtendedOrchestrationConfig).
    """
    if not hasattr(legacy_config, '__class__'):
        raise TypeError("legacy_config doit être une instance de classe.")

    # Champs communs à UnifiedAnalysisConfig et ExtendedOrchestrationConfig
    # (ExtendedOrchestrationConfig hérite de UnifiedAnalysisConfig)
    
    # Valeurs par défaut pour OrchestrationConfig
    defaults = OrchestrationConfig()

    analysis_modes = getattr(legacy_config, 'analysis_modes', defaults.analysis_modes)
    
    # orchestration_mode peut être un string ou un Enum dans les legacy configs
    legacy_orch_mode_attr = getattr(legacy_config, 'orchestration_mode', defaults.orchestration_mode)
    if isinstance(legacy_orch_mode_attr, Enum): # Ex: ExtendedOrchestrationConfig.orchestration_mode_enum
        orchestration_mode = legacy_orch_mode_attr
    elif hasattr(legacy_config, 'orchestration_mode_enum'): # Spécifique à ExtendedOrchestrationConfig
         orchestration_mode = getattr(legacy_config, 'orchestration_mode_enum', defaults.orchestration_mode)
    else: # UnifiedAnalysisConfig.orchestration_mode est un str
        orchestration_mode = legacy_orch_mode_attr

    logic_type = getattr(legacy_config, 'logic_type', defaults.logic_type)
    use_mocks = getattr(legacy_config, 'use_mocks', defaults.use_mocks)
    use_advanced_tools = getattr(legacy_config, 'use_advanced_tools', defaults.use_advanced_tools)
    output_format = getattr(legacy_config, 'output_format', defaults.output_format)
    enable_conversation_logging = getattr(legacy_config, 'enable_conversation_logging', defaults.enable_conversation_logging)

    # Champs spécifiques à ExtendedOrchestrationConfig
    # Si legacy_config est une instance de UnifiedAnalysisConfig, ces champs prendront les valeurs par défaut de OrchestrationConfig
    
    analysis_type_attr = getattr(legacy_config, 'analysis_type', defaults.analysis_type)
    if isinstance(analysis_type_attr, Enum):
        analysis_type = analysis_type_attr
    else: # Peut être un string
        analysis_type = analysis_type_attr


    enable_hierarchical = getattr(legacy_config, 'enable_hierarchical', defaults.enable_hierarchical_orchestration)
    enable_specialized = getattr(legacy_config, 'enable_specialized_orchestrators', defaults.enable_specialized_orchestrators)
    enable_comm_middleware = getattr(legacy_config, 'enable_communication_middleware', defaults.enable_communication_middleware)
    max_concurrent = getattr(legacy_config, 'max_concurrent_analyses', defaults.max_concurrent_analyses)
    timeout = getattr(legacy_config, 'analysis_timeout', defaults.analysis_timeout_seconds) # ExtendedConfig a 'analysis_timeout'
    auto_select = getattr(legacy_config, 'auto_select_orchestrator', defaults.auto_select_orchestrator_enabled)
    hier_coord_level = getattr(legacy_config, 'hierarchical_coordination_level', defaults.hierarchical_coordination_level)
    spec_prio = getattr(legacy_config, 'specialized_orchestrator_priority', defaults.specialized_orchestrator_priority_order)
    save_trace = getattr(legacy_config, 'save_orchestration_trace', defaults.save_orchestration_trace_enabled)
    middleware_cfg = getattr(legacy_config, 'middleware_config', defaults.communication_middleware_config)

    return OrchestrationConfig(
        analysis_modes=analysis_modes,
        orchestration_mode=orchestration_mode,
        analysis_type=analysis_type,
        logic_type=logic_type,
        use_mocks=use_mocks,
        use_advanced_tools=use_advanced_tools,
        output_format=output_format,
        enable_conversation_logging=enable_conversation_logging,
        enable_hierarchical_orchestration=enable_hierarchical,
        enable_specialized_orchestrators=enable_specialized,
        enable_communication_middleware=enable_comm_middleware,
        max_concurrent_analyses=max_concurrent,
        analysis_timeout_seconds=timeout,
        auto_select_orchestrator_enabled=auto_select,
        hierarchical_coordination_level=hier_coord_level,
        specialized_orchestrator_priority_order=spec_prio,
        save_orchestration_trace_enabled=save_trace,
        communication_middleware_config=middleware_cfg
    )

# Pour les tests et la démonstration, nous pouvons importer les classes legacy ici.
# Dans une vraie structure de projet, ces imports seraient gérés différemment.
try:
    from argumentation_analysis.pipelines.unified_text_analysis import UnifiedAnalysisConfig
    from argumentation_analysis.pipelines.unified_orchestration_pipeline import ExtendedOrchestrationConfig
except ImportError:
    # Gérer le cas où les fichiers ne sont pas accessibles (par exemple, lors de tests unitaires isolés de ce fichier)
    UnifiedAnalysisConfig = type("UnifiedAnalysisConfig", (object,), {})
    ExtendedOrchestrationConfig = type("ExtendedOrchestrationConfig", (object,), {})