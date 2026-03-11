#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import Dict, List, Any, Union
from argumentation_analysis.pipelines.unified_text_analysis import UnifiedAnalysisConfig
from .enums import OrchestrationMode, AnalysisType


class ExtendedOrchestrationConfig(UnifiedAnalysisConfig):
    """Configuration étendue pour l'orchestration hiérarchique."""

    def __init__(
        self,
        # Paramètres de base (hérités)
        analysis_modes: List[str] = None,
        orchestration_mode: Union[str, OrchestrationMode] = OrchestrationMode.PIPELINE,
        logic_type: str = "fol",
        use_mocks: bool = False,
        use_advanced_tools: bool = True,
        output_format: str = "detailed",
        enable_conversation_logging: bool = True,
        # Nouveaux paramètres pour l'orchestration hiérarchique
        analysis_type: Union[str, AnalysisType] = AnalysisType.COMPREHENSIVE,
        enable_hierarchical: bool = True,
        enable_specialized_orchestrators: bool = True,
        enable_communication_middleware: bool = True,
        max_concurrent_analyses: int = 10,
        analysis_timeout: int = 300,
        auto_select_orchestrator: bool = True,
        hierarchical_coordination_level: str = "full",
        specialized_orchestrator_priority: List[str] = None,
        save_orchestration_trace: bool = True,
        middleware_config: Dict[str, Any] = None,
        use_new_orchestrator: bool = True,
    ):
        """
        Initialise la configuration étendue.

        Args:
            analysis_type: Type d'analyse à effectuer
            enable_hierarchical: Active l'architecture hiérarchique
            enable_specialized_orchestrators: Active les orchestrateurs spécialisés
            enable_communication_middleware: Active le middleware de communication
            max_concurrent_analyses: Nombre max d'analyses simultanées
            analysis_timeout: Timeout en secondes pour les analyses
            auto_select_orchestrator: Sélection automatique de l'orchestrateur
            hierarchical_coordination_level: Niveau de coordination ("full", "strategic", "tactical")
            specialized_orchestrator_priority: Ordre de priorité des orchestrateurs spécialisés
            save_orchestration_trace: Sauvegarde la trace d'orchestration
            middleware_config: Configuration du middleware
            use_new_orchestrator: Active le nouveau MainOrchestrator
        """
        # Initialiser la configuration de base
        super().__init__(
            analysis_modes=analysis_modes,
            orchestration_mode=(
                orchestration_mode
                if isinstance(orchestration_mode, str)
                else orchestration_mode.value
            ),
            logic_type=logic_type,
            use_mocks=use_mocks,
            use_advanced_tools=use_advanced_tools,
            output_format=output_format,
            enable_conversation_logging=enable_conversation_logging,
        )

        # Configuration étendue
        self.analysis_type = (
            analysis_type
            if isinstance(analysis_type, AnalysisType)
            else AnalysisType(analysis_type)
        )
        self.orchestration_mode_enum = (
            orchestration_mode
            if isinstance(orchestration_mode, OrchestrationMode)
            else OrchestrationMode(orchestration_mode)
        )

        # Configuration hiérarchique
        self.enable_hierarchical = enable_hierarchical
        self.enable_specialized_orchestrators = enable_specialized_orchestrators
        self.enable_communication_middleware = enable_communication_middleware
        self.max_concurrent_analyses = max_concurrent_analyses
        self.analysis_timeout = analysis_timeout
        self.auto_select_orchestrator = auto_select_orchestrator
        self.hierarchical_coordination_level = hierarchical_coordination_level
        self.specialized_orchestrator_priority = specialized_orchestrator_priority or [
            "cluedo_investigation",
            "logic_complex",
            "conversation",
            "real",
        ]
        self.save_orchestration_trace = save_orchestration_trace
        self.middleware_config = middleware_config or {}
        self.use_new_orchestrator = use_new_orchestrator
