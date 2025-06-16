#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Moteur d'Exécution du Pipeline d'Orchestration
==============================================

Ce module contient la logique principale pour exécuter une analyse
orchestrée. Il sélectionne une stratégie et gère le flux d'exécution.
"""

import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional

# Imports des nouvelles stratégies et processeurs
from .strategies import (
    select_orchestration_strategy,
    execute_hierarchical_full_orchestration,
    execute_specialized_orchestration,
    execute_fallback_orchestration,
    execute_hybrid_orchestration
)
from ..analysis.post_processors import post_process_orchestration_results
from ..analysis.traces import save_orchestration_trace

# L'import pour le type hinting de UnifiedOrchestrationPipeline a été supprimé car la classe est obsolète.

logger = logging.getLogger(__name__)


async def analyze_text_orchestrated(
    pipeline: 'UnifiedOrchestrationPipeline',
    text: str,
    source_info: Optional[str] = None,
    custom_config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Lance l'analyse orchestrée d'un texte.
    """
    if not pipeline.initialized:
        raise RuntimeError("Pipeline non initialisé. Appelez initialize() d'abord.")
    
    analysis_start = time.time()
    analysis_id = f"analysis_{int(analysis_start)}"
    
    logger.info(f"[ORCHESTRATION] Début de l'analyse orchestrée {analysis_id}")
    pipeline._trace_orchestration("analysis_started", {"analysis_id": analysis_id})
    
    results = {
        "metadata": {
            "analysis_id": analysis_id,
            "analysis_timestamp": datetime.now().isoformat(),
            "pipeline_version": "unified_orchestration_2.0",
            "orchestration_mode": pipeline.config.orchestration_mode_enum.value,
        },
        "status": "in_progress"
    }

    try:
        orchestration_strategy = await select_orchestration_strategy(pipeline, text, custom_config)
        logger.info(f"[ORCHESTRATION] Stratégie sélectionnée: {orchestration_strategy}")
        
        if orchestration_strategy == "hierarchical_full":
            results = await execute_hierarchical_full_orchestration(pipeline, text, results)
        elif orchestration_strategy == "specialized_direct":
            results = await execute_specialized_orchestration(pipeline, text, results)
        elif orchestration_strategy == "fallback":
            results = await execute_fallback_orchestration(pipeline, text, results)
        else: # hybrid
            results = await execute_hybrid_orchestration(pipeline, text, results)
        
        results = await post_process_orchestration_results(pipeline, results)
        results["status"] = "success"

    except Exception as e:
        logger.error(f"[ORCHESTRATION] Erreur durant l'analyse orchestrée: {e}")
        results["status"] = "error"
        results["error"] = str(e)
        pipeline._trace_orchestration("analysis_error", {"error": str(e)})

    results["execution_time"] = time.time() - analysis_start
    results["orchestration_trace"] = pipeline.orchestration_trace.copy()
    
    if pipeline.config.save_orchestration_trace:
        await save_orchestration_trace(pipeline, analysis_id, results)
        
    logger.info(f"[ORCHESTRATION] Analyse {analysis_id} terminée en {results['execution_time']:.2f}s")
    
    return results
