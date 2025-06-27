#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Gestion des Traces et Logs d'Orchestration
===========================================

Ce module centralise les fonctions pour enregistrer, sauvegarder et 
récupérer les traces d'exécution et les logs de communication du pipeline.
"""

import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

from argumentation_analysis.paths import RESULTS_DIR

logger = logging.getLogger(__name__)


def trace_orchestration(pipeline: 'UnifiedOrchestrationPipeline', event_type: str, data: Dict[str, Any]):
    """Enregistre un événement dans la trace d'orchestration."""
    if pipeline.config.save_orchestration_trace:
        trace_entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "data": data
        }
        pipeline.orchestration_trace.append(trace_entry)


def get_communication_log(pipeline: 'UnifiedOrchestrationPipeline') -> List[Dict[str, Any]]:
    """Récupère le log de communication du middleware."""
    if pipeline.middleware and hasattr(pipeline.middleware, 'get_message_history'):
        try:
            return pipeline.middleware.get_message_history(limit=50)
        except Exception as e:
            logger.warning(f"Erreur récupération log communication: {e}")
    return []


async def save_orchestration_trace(pipeline: 'UnifiedOrchestrationPipeline', analysis_id: str, results: Dict[str, Any]):
    """Sauvegarde la trace d'orchestration."""
    try:
        trace_file = RESULTS_DIR / f"orchestration_trace_{analysis_id}.json"
        
        trace_data = {
            "analysis_id": analysis_id,
            "timestamp": datetime.now().isoformat(),
            "config": {
                "orchestration_mode": pipeline.config.orchestration_mode_enum.value,
                "analysis_type": pipeline.config.analysis_type.value,
                "hierarchical_enabled": pipeline.config.enable_hierarchical,
                "specialized_enabled": pipeline.config.enable_specialized_orchestrators
            },
            "trace": pipeline.orchestration_trace,
            "final_results": {
                "status": results.get("status"),
                "execution_time": results.get("execution_time"),
                "recommendations": results.get("recommendations", [])
            }
        }
        
        with open(trace_file, 'w', encoding='utf-8') as f:
            json.dump(trace_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"[TRACE] Trace d'orchestration sauvegardée: {trace_file}")
    
    except Exception as e:
        logger.error(f"Erreur sauvegarde trace: {e}")
