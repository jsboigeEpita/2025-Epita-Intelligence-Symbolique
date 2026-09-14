#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Moteur d'exécution de l'orchestration — une fonction libre, sans appelant.

Ce module ne définit **aucune classe**. Sa seule entrée est
`analyze_text_orchestrated` : sélection d'une stratégie
(`strategies.select_orchestration_strategy`), dispatch par la table
`STRATEGY_EXECUTORS`, post-traitement du résultat, sauvegarde de la trace.

Il n'est **pas** le moteur d'exécution du dépôt : le pipeline unifié moderne
exécute ses phases via le `WorkflowExecutor` de `orchestration/workflow_dsl.py`
(:356). Ce sous-paquet n'a **aucun appelant de production** — le chemin est
refusé en amont (`pipelines/unified_pipeline.py:82`
`ORCHESTRATION_PIPELINE_AVAILABLE = False` ; refus `:297-308`).

La docstring d'origine décrivait une classe `ExecutionEngine` avec
`add_processor` / `add_post_processor` et une méthode `run()` — aucun de ces
symboles n'a jamais existé dans ce dépôt. Elle est retirée, pas réécrite
(#2110).

Le dispatch est fail-loud : toute stratégie absente de `STRATEGY_EXECUTORS`
lève `ValueError`, jamais de repli silencieux vers l'hybride (#2109).
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
    execute_hybrid_orchestration,
)

# Table de dispatch explicite des stratégies d'orchestration. Toute valeur
# hors de cette table fait lever ValueError au dispatch — l'ancien `else`
# routait silencieusement vers l'hybride (#2109). La cohérence avec
# strategies.DISPATCHABLE_STRATEGIES est gardée par
# test_strategy_dispatch_coherence_2109.py.
STRATEGY_EXECUTORS = {
    "hierarchical_full": execute_hierarchical_full_orchestration,
    "specialized_direct": execute_specialized_orchestration,
    "fallback": execute_fallback_orchestration,
    "hybrid": execute_hybrid_orchestration,
}
from ..analysis.post_processors import post_process_orchestration_results
from ..analysis.traces import save_orchestration_trace

# L'import pour le type hinting de UnifiedOrchestrationPipeline a été supprimé car la classe est obsolète.

logger = logging.getLogger(__name__)


async def analyze_text_orchestrated(
    pipeline: "UnifiedOrchestrationPipeline",
    text: str,
    source_info: Optional[str] = None,
    custom_config: Optional[Dict[str, Any]] = None,
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
        "status": "in_progress",
    }

    try:
        orchestration_strategy = await select_orchestration_strategy(
            pipeline, text, custom_config
        )
        logger.info(f"[ORCHESTRATION] Stratégie sélectionnée: {orchestration_strategy}")

        executor = STRATEGY_EXECUTORS.get(orchestration_strategy)
        if executor is None:
            raise ValueError(
                f"Stratégie d'orchestration inconnue du moteur d'exécution : "
                f"{orchestration_strategy!r} (dispatchables : "
                f"{sorted(STRATEGY_EXECUTORS)}). (#2109)"
            )
        results = await executor(pipeline, text, results)

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

    logger.info(
        f"[ORCHESTRATION] Analyse {analysis_id} terminée en {results['execution_time']:.2f}s"
    )

    return results
