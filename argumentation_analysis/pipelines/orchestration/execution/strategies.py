#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Stratégies d'Exécution pour le Moteur de Pipeline.

Objectif:
    Ce module est conçu pour héberger différentes classes de "Stratégies"
    d'exécution. Une stratégie définit la logique de haut niveau sur la
    manière dont les processeurs d'un pipeline doivent être exécutés. En
    découplant l'`ExecutionEngine` de la stratégie d'exécution, on gagne en
    flexibilité pour créer des workflows simples ou très complexes.

Concept Clé:
    Chaque stratégie est une classe qui implémente une interface commune,
    typiquement une méthode `execute(state, processors)`. L'`ExecutionEngine`
    délègue entièrement sa logique d'exécution à l'objet `Strategy` qui lui
    est fourni lors de son initialisation. La stratégie est responsable de
    l'itération à travers les processeurs et de la gestion du flux de contrôle.

Stratégies Principales (Exemples cibles):
    -   `SequentialStrategy`:
        La stratégie la plus fondamentale. Elle exécute chaque processeur de
        la liste l'un après l'autre, dans l'ordre où ils ont été ajoutés.
    -   `ParallelStrategy`:
        Pour les tâches indépendantes, cette stratégie exécute un ensemble de
        processeurs en parallèle en utilisant `asyncio.gather`, ce qui peut
        considérablement accélérer le pipeline.
    -   `ConditionalStrategy`:
        Une stratégie plus avancée qui prend une condition et deux autres
        stratégies (une pour le `if`, une pour le `else`). Elle exécute l'une
        ou l'autre en fonction de l'état actuel de l'analyse.
    -   `FallbackStrategy`:
        Tente d'exécuter une stratégie primaire. Si une exception se produit,
        elle l'attrape et exécute une stratégie secondaire de secours.
    -   `HybridStrategy`:
        Combine plusieurs stratégies pour créer des workflows complexes, par
        exemple en exécutant certains groupes de tâches en parallèle et d'autres
        séquentiellement.

Utilisation:
    Une instance de stratégie est passée au constructeur de l'`ExecutionEngine`
    pour dicter son comportement.

    Exemple (conceptuel):
    ```python
    from .engine import ExecutionEngine
    from .strategies import SequentialStrategy, ParallelStrategy
    from ..analysis.processors import (
        ExtractProcessor,
        InformalAnalysisProcessor,
        FormalAnalysisProcessor
    )

    # Créer un moteur avec une stratégie séquentielle
    engine = ExecutionEngine(initial_state, strategy=SequentialStrategy())
    engine.add_processor(ExtractProcessor())
    engine.add_processor(InformalAnalysisProcessor())
    await engine.run()

    # Utiliser une stratégie parallèle pour des tâches indépendantes
    parallel_engine = ExecutionEngine(state, strategy=ParallelStrategy())
    parallel_engine.add_processor(CheckSourcesProcessor())
    parallel_engine.add_processor(CheckAuthorReputationProcessor())
    await parallel_engine.run()
    ```
"""

import logging
import time
from typing import Dict, List, Any, Optional, Callable

from argumentation_analysis.pipelines.orchestration.config.enums import OrchestrationMode, AnalysisType
from argumentation_analysis.pipelines.orchestration.config.base_config import ExtendedOrchestrationConfig

logger = logging.getLogger(__name__)


async def select_orchestration_strategy(
    pipeline: 'UnifiedOrchestrationPipeline', 
    text: str, 
    custom_config: Optional[Dict[str, Any]] = None
) -> str:
    """
    Sélectionne la stratégie d'orchestration appropriée.
    
    Args:
        pipeline: Instance du pipeline principal pour accéder à la config et aux composants.
        text: Texte à analyser
        custom_config: Configuration personnalisée
        
    Returns:
        Nom de la stratégie d'orchestration sélectionnée
    """
    config = pipeline.config
    # Mode manuel
    if config.orchestration_mode_enum != OrchestrationMode.AUTO_SELECT:
        logger.info("Path taken: Manual selection")
        mode_strategy_map = {
            OrchestrationMode.HIERARCHICAL_FULL: "hierarchical_full",
            OrchestrationMode.STRATEGIC_ONLY: "strategic_only",
            OrchestrationMode.TACTICAL_COORDINATION: "tactical_coordination",
            OrchestrationMode.OPERATIONAL_DIRECT: "operational_direct",
            OrchestrationMode.CLUEDO_INVESTIGATION: "specialized_direct",
            OrchestrationMode.LOGIC_COMPLEX: "specialized_direct",
            OrchestrationMode.ADAPTIVE_HYBRID: "hybrid"
        }
        strategy = mode_strategy_map.get(config.orchestration_mode_enum, "fallback")
        return strategy
    
    # Sélection automatique basée sur le type d'analyse
    logger.info("Path taken: AUTO_SELECT logic")
    if not config.auto_select_orchestrator:
        logger.info("Path taken: Fallback (auto_select disabled)")
        return "fallback"
    
    # Critères de sélection
    strategy = "hybrid"  # Fallback par défaut

    if config.analysis_type.value == AnalysisType.INVESTIGATIVE.value:
        logger.info("Path taken: Auto -> specialized_direct (INVESTIGATIVE)")
        strategy = "specialized_direct"
    elif config.analysis_type.value == AnalysisType.LOGICAL.value:
        logger.info("Path taken: Auto -> specialized_direct (LOGICAL)")
        strategy = "specialized_direct"
    elif config.enable_hierarchical and len(text) > 1000:
        logger.info("Path taken: Auto -> hierarchical_full (long text)")
        strategy = "hierarchical_full"
    elif config.analysis_type.value == AnalysisType.COMPREHENSIVE.value and pipeline.service_manager and pipeline.service_manager._initialized:
        logger.info("Path taken: Auto -> service_manager (COMPREHENSIVE)")
        strategy = "service_manager"
    
    if strategy == "hybrid":
         logger.info("Path taken: Auto -> hybrid (default fallback case)")

    return strategy


async def execute_hierarchical_full_orchestration(pipeline: 'UnifiedOrchestrationPipeline', text: str, results: Dict[str, Any]) -> Dict[str, Any]:
    """Exécute l'orchestration hiérarchique complète."""
    logger.info("[HIERARCHICAL] Exécution de l'orchestration hiérarchique complète...")
    
    try:
        # Niveau stratégique
        if pipeline.strategic_manager:
            strategic_results = pipeline.strategic_manager.initialize_analysis(text)
            results["strategic_analysis"] = strategic_results
            pipeline._trace_orchestration("strategic_analysis_completed", {"objectives_count": len(strategic_results.get("objectives", []))})
        
        # Niveau tactique
        if pipeline.tactical_coordinator and pipeline.strategic_manager:
            objectives = results["strategic_analysis"].get("objectives", [])
            tactical_results = await pipeline.tactical_coordinator.process_strategic_objectives(objectives)
            results["tactical_coordination"] = tactical_results
            pipeline._trace_orchestration("tactical_coordination_completed", {"tasks_created": tactical_results.get("tasks_created", 0)})
        
        # Niveau opérationnel (exécution des tâches)
        if pipeline.operational_manager:
            operational_results = await pipeline._execute_operational_tasks(text, results["tactical_coordination"])
            results["operational_results"] = operational_results
            pipeline._trace_orchestration("operational_execution_completed", {"tasks_executed": len(operational_results.get("task_results", []))})
        
        # Synthèse hiérarchique
        results["hierarchical_coordination"] = await pipeline._synthesize_hierarchical_results(results)
        
    except Exception as e:
        logger.error(f"[HIERARCHICAL] Erreur dans l'orchestration hiérarchique: {e}")
        results["strategic_analysis"]["error"] = str(e)
    
    return results


async def execute_specialized_orchestration(pipeline: 'UnifiedOrchestrationPipeline', text: str, results: Dict[str, Any]) -> Dict[str, Any]:
    """Exécute l'orchestration spécialisée."""
    logger.info("[SPECIALIZED] Exécution de l'orchestration spécialisée...")
    
    try:
        selected_orchestrator = await select_specialized_orchestrator(pipeline)
        
        if selected_orchestrator:
            orchestrator_name, orchestrator_data = selected_orchestrator
            orchestrator = orchestrator_data["orchestrator"]
            logger.info(f"[SPECIALIZED] Utilisation de l'orchestrateur: {orchestrator_name}")
            
            if orchestrator_name == "cluedo" and hasattr(orchestrator, 'run_investigation'):
                specialized_results = await orchestrator.run_investigation(text)
            elif hasattr(orchestrator, 'analyze'):
                specialized_results = await orchestrator.analyze(text, context={"source": "specialized_orchestration"})
            else:
                specialized_results = {"status": "unsupported", "orchestrator": orchestrator_name}

            results["specialized_orchestration"] = {
                "orchestrator_used": orchestrator_name,
                "results": specialized_results
            }
            pipeline._trace_orchestration("specialized_orchestration_completed", {"orchestrator": orchestrator_name, "status": specialized_results.get("status", "unknown")})
        else:
            results["specialized_orchestration"] = {"status": "no_orchestrator_available"}
    
    except Exception as e:
        logger.error(f"[SPECIALIZED] Erreur dans l'orchestration spécialisée: {e}")
        results["specialized_orchestration"]["error"] = str(e)
    
    return results


async def execute_fallback_orchestration(pipeline: 'UnifiedOrchestrationPipeline', text: str, results: Dict[str, Any]) -> Dict[str, Any]:
    """Exécute l'orchestration de fallback avec le pipeline original."""
    logger.info("[FALLBACK] Exécution de l'orchestration de fallback...")
    
    try:
        if pipeline._fallback_pipeline:
            fallback_results = await pipeline._fallback_pipeline.analyze_text_unified(text)
            results.update(fallback_results)
            pipeline._trace_orchestration("fallback_orchestration_completed", {"fallback_status": fallback_results.get("status", "unknown")})
        else:
            results["fallback_analysis"] = {"status": "fallback_unavailable"}
    
    except Exception as e:
        logger.error(f"[FALLBACK] Erreur dans l'orchestration de fallback: {e}")
        results["fallback_analysis"] = {"error": str(e), "status": "error"}
    
    return results


async def execute_hybrid_orchestration(pipeline: 'UnifiedOrchestrationPipeline', text: str, results: Dict[str, Any]) -> Dict[str, Any]:
    """Exécute l'orchestration hybride combinant plusieurs approches."""
    logger.info("[HYBRID] Exécution de l'orchestration hybride...")
    
    try:
        if pipeline.config.enable_hierarchical:
            results = await execute_hierarchical_full_orchestration(pipeline, text, results)
        
        if pipeline.config.enable_specialized_orchestrators:
            specialized_results = await execute_specialized_orchestration(pipeline, text, {})
            results["specialized_orchestration"] = specialized_results.get("specialized_orchestration", {})
        
        fallback_results = await execute_fallback_orchestration(pipeline, text, {})
        results.update(fallback_results)
        
        pipeline._trace_orchestration("hybrid_orchestration_completed", {"hierarchical_used": pipeline.config.enable_hierarchical, "specialized_used": pipeline.config.enable_specialized_orchestrators})
    
    except Exception as e:
        logger.error(f"[HYBRID] Erreur dans l'orchestration hybride: {e}")
        results["error"] = str(e)
    
    return results


async def select_specialized_orchestrator(pipeline: 'UnifiedOrchestrationPipeline') -> Optional[tuple]:
    """Sélectionne l'orchestrateur spécialisé approprié."""
    if not pipeline.specialized_orchestrators:
        return None
    
    compatible_orchestrators = []
    for name, data in pipeline.specialized_orchestrators.items():
        if pipeline.config.analysis_type in data["types"]:
            compatible_orchestrators.append((name, data))
    
    if not compatible_orchestrators:
        compatible_orchestrators = list(pipeline.specialized_orchestrators.items())
    
    compatible_orchestrators.sort(key=lambda x: x[1]["priority"])
    
    return compatible_orchestrators[0] if compatible_orchestrators else None
