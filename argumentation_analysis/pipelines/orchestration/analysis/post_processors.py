#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Post-Processeurs d'Analyse
===========================

Ce module contient les fonctions de post-traitement des résultats 
d'orchestration, comme la génération de recommandations finales.
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


async def post_process_orchestration_results(pipeline: 'UnifiedOrchestrationPipeline', results: Dict[str, Any]) -> Dict[str, Any]:
    """Post-traite les résultats d'orchestration."""
    try:
        recommendations = []
        
        hierarchical_coord = results.get("hierarchical_coordination", {})
        if hierarchical_coord.get("overall_score", 0) > 0.7:
            recommendations.append("Architecture hiérarchique très performante")
        
        specialized = results.get("specialized_orchestration", {})
        if specialized.get("results", {}).get("status") == "completed":
            orchestrator_used = specialized.get("orchestrator_used", "inconnu")
            recommendations.append(f"Orchestrateur spécialisé '{orchestrator_used}' efficace")
        
        if not recommendations:
            recommendations.append("Analyse orchestrée complétée - examen des résultats recommandé")
        
        results["recommendations"] = recommendations
        
        if pipeline.middleware:
            results["communication_log"] = pipeline._get_communication_log()
            
    except Exception as e:
        logger.error(f"Erreur post-traitement: {e}")
        results["post_processing_error"] = str(e)
    
    return results
