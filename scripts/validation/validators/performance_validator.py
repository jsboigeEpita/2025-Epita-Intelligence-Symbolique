import project_core.core_from_scripts.auto_env
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validator for system performance.
"""

import logging
import traceback
import time
from typing import Dict, Any, List

# Ajout du chemin pour les imports si nécessaire
# from pathlib import Path
# PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
# sys.path.insert(0, str(PROJECT_ROOT))

logger = logging.getLogger(__name__)

async def validate_performance(report_errors_list: list, available_components: Dict[str, bool], test_texts: List[str]) -> Dict[str, Any]:
    """Validates system performance."""
    logger.info("⚡ Validation des performances...")
    
    performance_results = {
        "orchestration_times": {},
        "memory_usage": {}, # Note: La mesure de la mémoire n'était pas implémentée dans l'original
        "throughput": {},
        "errors": []
    }
    
    try:
        # Tests de performance orchestration
        if available_components.get('conversation_orchestrator', False):
            performance_results["orchestration_times"] = await _benchmark_orchestration(test_texts)
        else:
            performance_results["orchestration_times"] = {"status": "skipped", "reason": "ConversationOrchestrator non disponible"}
        
        # Tests de throughput
        if available_components.get('conversation_orchestrator', False): # Le benchmark original utilisait ConversationOrchestrator
            performance_results["throughput"] = await _benchmark_throughput(test_texts)
        else:
            performance_results["throughput"] = {"status": "skipped", "reason": "ConversationOrchestrator non disponible pour le benchmark de throughput"}
            
    except Exception as e:
        error_details = {
            "context": "performance_validation",
            "error": str(e),
            "traceback": traceback.format_exc()
        }
        performance_results["errors"].append(error_details)
        report_errors_list.append(error_details)
        
    return performance_results

async def _benchmark_orchestration(test_texts: List[str]) -> Dict[str, Any]:
    """Benchmarks orchestration times."""
    times = {"status": "unknown", "details": {}}
    
    try:
        from argumentation_analysis.orchestration.conversation_orchestrator import ConversationOrchestrator
        
        modes = ["micro", "demo"] # Modes testés dans l'original
        successful_benchmarks = 0
        
        for mode in modes:
            logger.info(f"  Benchmarking ConversationOrchestrator mode: {mode}")
            start_time = time.time()
            try:
                orchestrator = ConversationOrchestrator(mode=mode)
                # Utilise le premier texte de test, ou un texte par défaut si la liste est vide
                text_to_process = test_texts[0] if test_texts else "Texte de benchmark par défaut."
                result = orchestrator.run_orchestration(text_to_process)
                elapsed = time.time() - start_time
                
                if isinstance(result, str) and result: # Vérifie que le résultat est une chaîne non vide
                    times["details"][f"conversation_{mode}"] = elapsed
                    successful_benchmarks +=1
                    logger.info(f"    ✓ Benchmark mode {mode}: {elapsed:.2f}s")
                else:
                    times["details"][f"conversation_{mode}_error"] = f"Résultat invalide ou vide (type: {type(result)})"
                    logger.warning(f"    ✗ Benchmark mode {mode}: Résultat invalide ou vide.")

            except Exception as e:
                times["details"][f"conversation_{mode}_error"] = str(e)
                logger.warning(f"    ✗ Erreur benchmark ConversationOrchestrator mode {mode}: {e}", exc_info=True)
        
        if successful_benchmarks == len(modes):
            times["status"] = "success"
        elif successful_benchmarks > 0:
            times["status"] = "partial"
        else:
            times["status"] = "failed"

    except ImportError:
        times["status"] = "failed"
        times["error"] = "Import manquant pour ConversationOrchestrator"
        logger.error("  ✗ Benchmark orchestration échoué: Import ConversationOrchestrator manquant.")
    except Exception as e:
        times["status"] = "failed"
        times["error"] = str(e)
        logger.error(f"  ✗ Erreur générale durant le benchmark d'orchestration: {e}", exc_info=True)
            
    return times

async def _benchmark_throughput(test_texts: List[str]) -> Dict[str, Any]:
    """Benchmarks system throughput."""
    throughput_results = {"status": "unknown", "details": {}}
    
    # Test simple de throughput
    start_time = time.time()
    processed_texts_count = 0
    
    try:
        # Le benchmark original utilisait ConversationOrchestrator
        from argumentation_analysis.orchestration.conversation_orchestrator import ConversationOrchestrator
        orchestrator = ConversationOrchestrator(mode="micro") # Mode le plus léger pour le throughput
        
        # Limite le nombre de textes pour que le benchmark ne soit pas trop long
        texts_for_benchmark = test_texts[:3] if test_texts else ["Texte 1", "Texte 2", "Texte 3"]
        if not texts_for_benchmark:
             throughput_results["status"] = "skipped"
             throughput_results["reason"] = "Aucun texte de test fourni pour le benchmark de throughput."
             logger.info("  Benchmark de throughput sauté: aucun texte de test.")
             return throughput_results

        logger.info(f"  Benchmarking throughput avec {len(texts_for_benchmark)} textes...")
        for text in texts_for_benchmark:
            try:
                result = orchestrator.run_orchestration(text)
                if result and isinstance(result, str): # Vérifie un résultat valide
                    processed_texts_count += 1
            except Exception as e:
                logger.warning(f"    Erreur durant le traitement d'un texte pour le throughput: {e}")
                # On continue avec les autres textes
        
        elapsed = time.time() - start_time
        if elapsed > 0 and processed_texts_count > 0:
            throughput_results["details"]["texts_per_second"] = processed_texts_count / elapsed
            throughput_results["details"]["total_processed"] = processed_texts_count
            throughput_results["details"]["total_time"] = elapsed
            throughput_results["status"] = "success"
            logger.info(f"    ✓ Benchmark throughput: {processed_texts_count / elapsed:.2f} textes/s ({processed_texts_count} textes en {elapsed:.2f}s)")
        elif processed_texts_count == 0:
            throughput_results["status"] = "failed"
            throughput_results["reason"] = "Aucun texte n'a pu être traité."
            logger.error("    ✗ Benchmark throughput: Aucun texte traité.")
        else: # elapsed == 0
            throughput_results["status"] = "unknown" # Difficile à interpréter
            throughput_results["reason"] = "Temps écoulé nul."
            logger.warning("    ? Benchmark throughput: Temps écoulé nul.")

    except ImportError:
        throughput_results["status"] = "failed"
        throughput_results["error"] = "Import manquant pour ConversationOrchestrator"
        logger.error("  ✗ Benchmark throughput échoué: Import ConversationOrchestrator manquant.")
    except Exception as e:
        throughput_results["status"] = "failed"
        throughput_results["error"] = str(e)
        logger.error(f"  ✗ Erreur générale durant le benchmark de throughput: {e}", exc_info=True)
    
    return throughput_results