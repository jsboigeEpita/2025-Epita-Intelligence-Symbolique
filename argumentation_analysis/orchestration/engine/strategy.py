#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Logique de sélection de la stratégie d'orchestration.
"""

from enum import Enum
from typing import Dict, Any, TYPE_CHECKING, Optional
import logging
from config.unified_config import UnifiedConfig

if TYPE_CHECKING:
    from .config import OrchestrationConfig, OrchestrationMode, AnalysisType

# Pour éviter une dépendance circulaire à l'exécution si OrchestrationConfig importe des éléments
# qui pourraient indirectement dépendre de strategy.py à l'avenir.
# Cependant, pour ce cas précis, .config est safe.
# from argumentation_analysis.orchestration.engine.config import OrchestrationConfig, OrchestrationMode, AnalysisType


class OrchestrationStrategy(Enum):
    """Stratégies d'orchestration possibles."""
    HIERARCHICAL_FULL = "hierarchical_full"
    STRATEGIC_ONLY = "strategic_only"
    TACTICAL_COORDINATION = "tactical_coordination"
    OPERATIONAL_DIRECT = "operational_direct"
    SPECIALIZED_DIRECT = "specialized_direct"
    HYBRID = "hybrid"
    FALLBACK = "fallback"
    SERVICE_MANAGER = "service_manager" # Ajouté basé sur l'analyse du code source
    MANUAL_SELECTION = "manual_selection"
    COMPLEX_PIPELINE = "complex_pipeline"

logger = logging.getLogger(__name__)

async def _analyze_text_features_for_strategy(text: str) -> Dict[str, Any]:
    """Analyse les caractéristiques du texte pour la sélection de stratégie."""
    features = {
        "length": len(text),
        "word_count": len(text.split()),
        "sentence_count": text.count('.') + text.count('!') + text.count('?'),
        "has_questions": '?' in text,
        "has_logical_connectors": any(connector in text.lower() for connector in
                                    ['donc', 'par conséquent', 'si...alors', 'parce que', 'car']),
        "has_debate_markers": any(marker in text.lower() for marker in
                                  ['argument', 'contre-argument', 'objection', 'réfutation']),
        "complexity_score": min(len(text) / 500, 5.0)  # Score de 0 à 5
    }
    return features

async def select_strategy(
    config: 'OrchestrationConfig',
    text_input: str,
    source_info: Optional[Dict[str, Any]] = None,
    custom_config: Optional[Dict[str, Any]] = None
) -> OrchestrationStrategy:
    """
    Sélectionne la stratégie d'orchestration appropriée.

    Args:
        config: La configuration d'orchestration unifiée.
        text_input: Le texte d'entrée à analyser.
        source_info: Informations optionnelles sur la source du texte.
        custom_config: Configuration optionnelle personnalisée pour l'analyse.

    Returns:
        La stratégie d'orchestration sélectionnée.
    """
    # Priorité 1: Vérifier le mode manuel global
    if UnifiedConfig().manual_mode:
        logger.info("Defaulting to MANUAL_SELECTION strategy due to global settings.")
        return OrchestrationStrategy.MANUAL_SELECTION

    if custom_config and "force_strategy" in custom_config:
        forced_strategy_name = custom_config["force_strategy"]
        try:
            # Tenter de faire correspondre la chaîne à un membre de l'enum
            strategy = OrchestrationStrategy[forced_strategy_name.upper()]
            logger.info(f"Forcing strategy to {strategy.name} based on custom_config.")
            return strategy
        except KeyError:
            logger.warning(
                f"Invalid strategy '{forced_strategy_name}' requested in custom_config. "
                "Falling back to default strategy selection."
            )
    
    # NOUVELLE LOGIQUE : Sélection basée sur source_info.
    if source_info and source_info.get("type") == "monitoring":
        logger.info("Selecting OPERATIONAL_DIRECT strategy for source type 'monitoring'.")
        return OrchestrationStrategy.OPERATIONAL_DIRECT

    # Importation des types nécessaires pour la logique suivante
    # Assurez-vous que .config peut être importé sans causer de dépendance circulaire.
    # Si OrchestrationConfig, OrchestrationMode, AnalysisType sont déjà disponibles via
    # TYPE_CHECKING et que l'interpréteur les gère correctement, cet import peut être redondant.
    # Cependant, le maintenir assure la disponibilité des types pour la logique d'exécution.
    from .config import OrchestrationMode, AnalysisType

    # Mode manuel
    if config.orchestration_mode and config.orchestration_mode.value != "auto_select":
        mode_strategy_map = {
            OrchestrationMode.HIERARCHICAL_FULL: OrchestrationStrategy.HIERARCHICAL_FULL,
            OrchestrationMode.STRATEGIC_ONLY: OrchestrationStrategy.STRATEGIC_ONLY,
            OrchestrationMode.TACTICAL_COORDINATION: OrchestrationStrategy.TACTICAL_COORDINATION,
            OrchestrationMode.OPERATIONAL_DIRECT: OrchestrationStrategy.OPERATIONAL_DIRECT,
            OrchestrationMode.CLUEDO_INVESTIGATION: OrchestrationStrategy.SPECIALIZED_DIRECT,
            OrchestrationMode.LOGIC_COMPLEX: OrchestrationStrategy.SPECIALIZED_DIRECT,
            OrchestrationMode.ADAPTIVE_HYBRID: OrchestrationStrategy.HYBRID
        }
        # Utiliser HIERARCHICAL_FULL comme fallback si le mode manuel n'est pas explicitement mappé
        selected_strategy = mode_strategy_map.get(config.orchestration_mode, OrchestrationStrategy.HIERARCHICAL_FULL)
        logger.info(f"Manual mode selection: OrchestrationMode.{config.orchestration_mode.name} -> OrchestrationStrategy.{selected_strategy.name}")
        return selected_strategy

    # Sélection automatique (si config.orchestration_mode == OrchestrationMode.AUTO_SELECT)
    if not config.auto_select_orchestrator_enabled:
        logger.info("Auto-select orchestrator disabled. Defaulting to HIERARCHICAL_FULL strategy.")
        return OrchestrationStrategy.HIERARCHICAL_FULL

    # Critères de sélection pour le mode AUTO_SELECT
    if config.analysis_type == AnalysisType.INVESTIGATIVE:
        logger.info("AnalysisType is INVESTIGATIVE. Selecting SPECIALIZED_DIRECT strategy.")
        return OrchestrationStrategy.SPECIALIZED_DIRECT
    elif config.analysis_type == AnalysisType.LOGICAL:
        logger.info("AnalysisType is LOGICAL. Selecting SPECIALIZED_DIRECT strategy.")
        return OrchestrationStrategy.SPECIALIZED_DIRECT
    elif config.enable_hierarchical_orchestration and len(text_input) > 1000:
        logger.info("Hierarchical orchestration enabled and text is long. Selecting HIERARCHICAL_FULL strategy.")
        return OrchestrationStrategy.HIERARCHICAL_FULL
    # La condition pour SERVICE_MANAGER est omise comme dans le code original pour autonomie.
    # elif service_manager and service_manager._initialized: # Supposons que cette info soit dans config
    #     logger.info("Service manager initialized. Selecting SERVICE_MANAGER strategy.")
    #     return OrchestrationStrategy.SERVICE_MANAGER
    
    # Logique de fallback basée sur la configuration globale
    # La logique de fallback basée sur global_config est supprimée car
    # la configuration est maintenant gérée par l'objet `config` (UnifiedConfig)
    # passé en paramètre. Le comportement de fallback est déjà géré
    # par la logique de sélection de stratégie ci-dessus.
    
    # Comportement par défaut final si aucune autre condition n'est remplie
    logger.info("Defaulting to a standard pipeline as a fallback.")
    return OrchestrationStrategy.COMPLEX_PIPELINE