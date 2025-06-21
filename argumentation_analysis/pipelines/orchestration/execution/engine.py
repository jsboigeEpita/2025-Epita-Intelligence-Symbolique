#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Moteur d'Exécution de Pipeline.

Objectif:
    Ce module définit la classe `ExecutionEngine`, le cœur de l'architecture
    de pipeline. L'`ExecutionEngine` est le chef d'orchestre qui prend une
    séquence de processeurs (`Processors` et `PostProcessors`) et les exécute
    dans le bon ordre, en gérant le flux de données et l'état de l'analyse.

Concept Clé:
    L'`ExecutionEngine` est initialisé avec un état de base (généralement
    contenant le texte d'entrée). Il maintient une liste de processeurs
    enregistrés. Lorsqu'il est exécuté, il applique chaque processeur
    séquentiellement, passant l'état mis à jour d'un processeur au suivant.
    Il s'appuie sur des stratégies d'exécution (définies dans `strategies.py`)
    pour déterminer comment exécuter les processeurs (ex: séquentiellement,
    en parallèle, conditionnellement).

Fonctionnalités Principales:
    -   **Gestion de l'État**: Maintient et met à jour un objet d'état
        (`RhetoricalAnalysisState` ou un dictionnaire) tout au long du pipeline.
    -   **Enregistrement des Processeurs**: Fournit des méthodes pour ajouter
        des étapes d'analyse (`add_processor`) et des étapes de
        post-traitement (`add_post_processor`).
    -   **Exécution Stratégique**: Utilise un objet `Strategy` pour contrôler
        le flux d'exécution, permettant une flexibilité maximale (séquentiel,
        parallèle, etc.).
    -   **Gestion des Erreurs**: Encapsule la logique de gestion des erreurs
        pour rendre les pipelines plus robustes.
    -   **Traçabilité**: Peut intégrer un système de logging ou de traçage pour
        suivre le déroulement de l'analyse à chaque étape.

Utilisation:
    L'utilisateur du moteur assemble un pipeline en instanciant l'engine et
    en y ajoutant les briques de traitement souhaitées.

    Exemple (conceptuel):
    ```python
    from .strategies import SequentialStrategy
    from ..analysis.processors import ExtractProcessor, InformalAnalysisProcessor
    from ..analysis.post_processors import ResultFormattingProcessor

    # 1. Initialiser l'état et le moteur avec une stratégie
    initial_state = {"text": "Le texte à analyser..."}
    engine = ExecutionEngine(initial_state, strategy=SequentialStrategy())

    # 2. Enregistrer les étapes du pipeline
    engine.add_processor(ExtractProcessor())
    engine.add_processor(InformalAnalysisProcessor())
    engine.add_post_processor(ResultFormattingProcessor(format="json"))

    # 3. Exécuter le pipeline
    final_results = await engine.run()
    print(final_results)
    ```
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
