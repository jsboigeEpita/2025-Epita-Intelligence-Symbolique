"""Unified pipeline wiring all integrated student components via CapabilityRegistry.

This package was split from a single unified_pipeline.py file for maintainability.
All original public symbols are re-exported here for backward compatibility.

Provides:
- setup_registry(): register all available components (agents, services, adapters)
- Pre-built workflow definitions (light, standard, full, custom)
- run_unified_analysis(): convenience function for end-to-end analysis
"""

# Helpers
from argumentation_analysis.orchestration.unified_pipeline._helpers import (
    _aggregate_virtue_scores,
    _enrich_ranking_with_justification,
    _evaluate_counter_arguments,
    _extract_arguments_from_context,
    _generate_attacks_from_args,
    _get_openai_client,
    _increment_fallacy_rerun,
    _normalize_fallacies_with_quotes,
    _normalize_items_with_quotes,
    _python_ranking_fallback,
    _should_rerun_fallacy,
    logger,
)

# Invoke callables
from argumentation_analysis.orchestration.unified_pipeline.invoke_callables import (
    _invoke_aba,
    _invoke_adf,
    _invoke_aspic,
    _invoke_atms,
    _invoke_belief_revision,
    _invoke_bipolar,
    _invoke_camembert_fallacy,
    _invoke_cl,
    _invoke_counter_argument,
    _invoke_debate_analysis,
    _invoke_dl,
    _invoke_delp,
    _invoke_dialogue,
    _invoke_dung_extensions,
    _invoke_eaf,
    _invoke_fact_extraction,
    _invoke_fol_reasoning,
    _invoke_formal_synthesis,
    _invoke_governance,
    _invoke_hierarchical_fallacy,
    _invoke_jtms,
    _invoke_local_llm,
    _invoke_modal_logic,
    _invoke_nl_to_logic,
    _invoke_probabilistic,
    _invoke_propositional_logic,
    _invoke_qbf,
    _invoke_quality_evaluator,
    _invoke_ranking,
    _invoke_sat,
    _invoke_semantic_index,
    _invoke_setaf,
    _invoke_social,
    _invoke_speech_transcription,
    _invoke_weighted,
    _llm_enrich_quality,
    _python_aspic_fallback,
    _python_eaf_fallback,
    _python_social_fallback,
)

# State writers
from argumentation_analysis.orchestration.unified_pipeline.state_writers import (
    CAPABILITY_STATE_WRITERS,
    _write_aba_to_state,
    _write_adf_to_state,
    _write_aspic_to_state,
    _write_atms_to_state,
    _write_belief_revision_to_state,
    _write_bipolar_to_state,
    _write_camembert_to_state,
    _write_cl_to_state,
    _write_collaborative_analysis_to_state,
    _write_counter_argument_to_state,
    _write_debate_to_state,
    _write_delp_to_state,
    _write_dialogue_to_state,
    _write_dl_to_state,
    _write_dung_extensions_to_state,
    _write_eaf_to_state,
    _write_fact_extraction_to_state,
    _write_fol_to_state,
    _write_formal_synthesis_to_state,
    _write_governance_to_state,
    _write_hierarchical_fallacy_to_state,
    _write_jtms_to_state,
    _write_modal_to_state,
    _write_nl_to_logic_to_state,
    _write_probabilistic_to_state,
    _write_propositional_to_state,
    _write_qbf_to_state,
    _write_quality_to_state,
    _write_ranking_to_state,
    _write_sat_to_state,
    _write_semantic_index_to_state,
    _write_setaf_to_state,
    _write_social_to_state,
    _write_speech_to_state,
    _write_weighted_to_state,
)

# Registry setup
from argumentation_analysis.orchestration.unified_pipeline.registry_setup import (
    _declare_tweety_slots,
    setup_registry,
)

# Re-export CapabilityRegistry for tests that patch it on this module
from argumentation_analysis.core.capability_registry import (  # noqa: F401
    CapabilityRegistry,
)

# Workflow builders
from argumentation_analysis.orchestration.unified_pipeline.workflow_builders import (
    build_debate_governance_loop_workflow,
    build_full_workflow,
    build_hierarchical_fallacy_workflow,
    build_iterative_analysis_workflow,
    build_jtms_dung_loop_workflow,
    build_light_workflow,
    build_nl_to_logic_workflow,
    build_neural_symbolic_fallacy_workflow,
    build_quality_gated_counter_workflow,
    build_standard_workflow,
    get_workflow_catalog,
    reset_workflow_catalog,
    run_unified_analysis,
)
