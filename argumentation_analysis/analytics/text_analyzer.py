# -*- coding: utf-8 -*-
"""
Module for performing text analysis using various services.
"""
import logging
from typing import Dict, Any

# Importation au niveau du module pour une meilleure clarté
try:
    from argumentation_analysis.orchestration.analysis_runner import run_analysis_conversation
except ImportError:
    # Gérer le cas où le script est exécuté d'une manière qui perturbe les imports relatifs
    logging.error("Failed to import 'run_analysis_conversation'. Check PYTHONPATH and module structure.")
    # Rendre la fonction inutilisable si l'import échoue
    async def run_analysis_conversation(*args: Any, **kwargs: Any) -> None: # type: ignore
        """Placeholder if import fails."""
        raise ImportError("run_analysis_conversation could not be imported.")


async def perform_text_analysis(text: str, services: Dict[str, Any], analysis_type: str = "default") -> Any:
    """
    Performs text analysis based on the provided text, services, and analysis type.

    This function orchestrates the analysis by calling the appropriate
    underlying analysis functions (currently `run_analysis_conversation`).
    It expects an initialized LLM service to be present in the `services` dictionary.

    Args:
        text (str): The input text to analyze.
        services (Dict[str, Any]): A dictionary of initialized analysis services.
                                   Must contain 'llm_service'. It may also contain
                                   'jvm_ready' status, though it's not directly
                                   used by this function but might be by underlying services.
        analysis_type (str): The type of analysis to perform. This parameter is
                             intended for future expansion, allowing routing to
                             different specialized analysis functions (e.g., "rhetoric",
                             "fallacies"). Currently, it's primarily for logging and
                             doesn't change the core analysis logic which defaults to
                             `run_analysis_conversation`.

    Returns:
        Any: The results of the analysis. Currently, `run_analysis_conversation`
             does not explicitly return a value in its original usage context;
             it logs outcomes. This function mirrors that behavior by returning None
             upon successful completion (implying results are logged or handled
             elsewhere) or in case of critical errors like a missing LLM service.
             Future enhancements might involve returning structured analysis results.
             Returns None if essential services are missing or an error occurs.
    """
    logging.info(f"Initiating text analysis of type '{analysis_type}' on text of length {len(text)} chars.")

    llm_service = services.get("llm_service")
    # jvm_ready_status = services.get("jvm_ready", False) # Available if needed

    if not llm_service:
        logging.critical("❌ LLM service is not available in the provided services. Analysis cannot proceed.")
        return None # Indicates critical failure

    # Future logic for routing based on analysis_type can be added here.
    # Example:
    # if analysis_type == "rhetoric_specific":
    #     return await analyze_rhetoric_specifically(text, llm_service, services)
    # elif analysis_type == "fallacy_specific":
    #     return await detect_fallacies_specifically(text, llm_service, services)

    try:
        logging.info(f"Launching core analysis (type: {analysis_type}) via run_analysis_conversation...")
        # `run_analysis_conversation` is awaited. Its original usage in `run_analysis.py`
        # doesn't involve capturing a return value for further processing within that script.
        # It handles its own logging of success or failure.
        await run_analysis_conversation(
            texte_a_analyser=text,
            llm_service=llm_service
            # If `analysis_type` or other `services` become relevant to `run_analysis_conversation`,
            # they should be passed here.
        )
        logging.info(f"🏁 Core analysis (type: '{analysis_type}') completed successfully (via run_analysis_conversation).")
        # Mimic original behavior: no explicit result returned by this path, success is logged.
        return # Or a more specific success indicator if the caller needs it.

    except ImportError as ie:
        # This would typically be caught at module load if run_analysis_conversation is critical
        logging.error(f"❌ Failed to import or use analysis components for type '{analysis_type}': {ie}", exc_info=True)
        return None
    except Exception as e:
        logging.error(f"❌ Error during text analysis (type: {analysis_type}): {e}", exc_info=True)
        return None

# Placeholder for more specific analysis functions if `analysis_type` routing is implemented:
# async def analyze_rhetoric_specifically(text: str, llm_service: Any, all_services: Dict[str, Any]):
#     logging.info("Performing specific rhetoric analysis...")
#     # ... specific logic ...
#     return "Rhetoric analysis results"

# async def detect_fallacies_specifically(text: str, llm_service: Any, all_services: Dict[str, Any]):
#     logging.info("Performing specific fallacy detection...")
#     # ... specific logic ...
#     return "Fallacy detection results"