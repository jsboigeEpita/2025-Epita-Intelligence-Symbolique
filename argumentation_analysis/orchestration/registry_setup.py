"""Registry setup for the unified pipeline.

setup_registry() creates and populates a CapabilityRegistry with all
available components (agents, services, adapters).

Split from unified_pipeline.py (#310).
"""

import logging
from typing import Dict, Any

from argumentation_analysis.core.capability_registry import (
    CapabilityRegistry,
    ServiceDiscovery,
    ComponentType,
)
from argumentation_analysis.orchestration.invoke_callables import (
    _invoke_quality_evaluator,
    _invoke_counter_argument,
    _invoke_debate_analysis,
    _invoke_governance,
    _invoke_jtms,
    _invoke_atms,
    _invoke_camembert_fallacy,
    _invoke_local_llm,
    _invoke_semantic_index,
    _invoke_speech_transcription,
    _invoke_hierarchical_fallacy,
    _invoke_fact_extraction,
    _invoke_propositional_logic,
    _invoke_fol_reasoning,
    _invoke_modal_logic,
    _invoke_dung_extensions,
    _invoke_formal_synthesis,
    _invoke_nl_to_logic,
    _invoke_sat,
    _invoke_ranking,
    _invoke_bipolar,
    _invoke_aba,
    _invoke_adf,
    _invoke_aspic,
    _invoke_belief_revision,
    _invoke_probabilistic,
    _invoke_dialogue,
    _invoke_dl,
    _invoke_cl,
    _invoke_setaf,
    _invoke_weighted,
    _invoke_social,
    _invoke_eaf,
    _invoke_delp,
    _invoke_qbf,
)

logger = logging.getLogger("UnifiedPipeline")


def setup_registry(
    include_optional: bool = True,
) -> CapabilityRegistry:
    """
    Create and populate a CapabilityRegistry with all available components.

    Registers agents, services, and adapters from the integrated student projects.
    Each registration is wrapped in try/except so missing optional dependencies
    don't prevent the registry from being created.

    Args:
        include_optional: If True, attempt to register components with optional
                         dependencies (CamemBERT, Dung/JVM, speech-to-text).

    Returns:
        Populated CapabilityRegistry instance.
    """
    registry = CapabilityRegistry()
    registered = []
    skipped = []

    # --- Core agents (always available) ---

    # Counter-argument generation (2.3.3)
    try:
        from argumentation_analysis.agents.core.counter_argument import (
            register_with_capability_registry as register_counter_arg,
        )

        register_counter_arg(registry)  # type: ignore[no-untyped-call]
        # Wire invoke callable (registration was created by register_counter_arg)
        if "counter_argument_agent" in registry._registrations:
            registry._registrations["counter_argument_agent"].invoke = (
                _invoke_counter_argument
            )
        registered.append("counter_argument_agent")
    except ImportError as e:
        skipped.append(("counter_argument_agent", str(e)))

    # Argument quality evaluation (2.3.5)
    try:
        from argumentation_analysis.agents.core.quality.quality_evaluator import (
            ArgumentQualityEvaluator,
        )

        registry.register_agent(
            name="quality_evaluator",
            agent_class=ArgumentQualityEvaluator,
            capabilities=[
                "argument_quality",
                "virtue_detection",
                "quality_scoring",
            ],
            metadata={"description": "9-virtue argument quality evaluator"},
            invoke=_invoke_quality_evaluator,
        )
        registered.append("quality_evaluator")
    except ImportError as e:
        skipped.append(("quality_evaluator", str(e)))

    # Debate agent (1.2.7)
    try:
        from argumentation_analysis.agents.core.debate.debate_agent import (
            DebateAgent,
        )

        registry.register_agent(
            name="debate_agent",
            agent_class=DebateAgent,
            capabilities=[
                "adversarial_debate",
                "argument_stress_test",
                "debate_scoring",
            ],
            metadata={"description": "Multi-personality adversarial debate agent"},
            invoke=_invoke_debate_analysis,
        )
        registered.append("debate_agent")
    except ImportError as e:
        skipped.append(("debate_agent", str(e)))

    # Governance agent (2.1.6)
    try:
        from argumentation_analysis.agents.core.governance.governance_agent import (
            Agent as GovernanceAgent,
        )

        registry.register_agent(
            name="governance_agent",
            agent_class=GovernanceAgent,
            capabilities=[
                "governance_simulation",
                "multi_method_voting",
                "preference_aggregation",
            ],
            metadata={"description": "7-method governance voting agent"},
            invoke=_invoke_governance,
        )
        registered.append("governance_agent")
    except ImportError as e:
        skipped.append(("governance_agent", str(e)))

    # --- Core services ---

    # JTMS belief maintenance (1.4.1)
    try:
        from argumentation_analysis.services.jtms.jtms_core import JTMS

        registry.register_service(
            name="jtms_service",
            service_class=JTMS,
            capabilities=["belief_maintenance", "truth_maintenance", "jtms_reasoning"],
            metadata={"description": "Justification-based Truth Maintenance System"},
            invoke=_invoke_jtms,
        )
        registered.append("jtms_service")
    except ImportError as e:
        skipped.append(("jtms_service", str(e)))

    # ATMS assumption-based reasoning (1.4.1) (#292)
    try:
        from argumentation_analysis.services.jtms.atms_core import ATMS as ATMSCore

        registry.register_service(
            name="atms_service",
            service_class=ATMSCore,
            capabilities=[
                "atms_reasoning",
                "environment_tracking",
            ],
            metadata={
                "description": "Assumption-based Truth Maintenance System (ATMS)"
            },
            invoke=_invoke_atms,
        )
        registered.append("atms_service")
    except ImportError as e:
        skipped.append(("atms_service", str(e)))

    # Local LLM service (2.3.6)
    try:
        from argumentation_analysis.services.local_llm_service import (
            LocalLLMService,
        )

        registry.register_service(
            name="local_llm_service",
            service_class=LocalLLMService,
            capabilities=["local_llm", "chat_completion"],
            metadata={"description": "OpenAI-compatible local LLM adapter"},
            invoke=_invoke_local_llm,
        )
        registered.append("local_llm_service")
    except ImportError as e:
        skipped.append(("local_llm_service", str(e)))

    # --- Optional adapters (may need heavy dependencies) ---

    if include_optional:
        # Self-hosted LLM fallacy detector (replaces CamemBERT, #297)
        try:
            registry.register_service(
                name="self_hosted_fallacy_detector",
                capabilities=["neural_fallacy_detection", "fallacy_detection"],
                metadata={
                    "description": (
                        "Self-hosted LLM fallacy detector via function calling "
                        "(replaces CamemBERT Tier 2.5, #297)"
                    )
                },
                invoke=_invoke_camembert_fallacy,
            )
            registered.append("self_hosted_fallacy_detector")
        except Exception as e:
            skipped.append(("self_hosted_fallacy_detector", str(e)))

        # Hierarchical taxonomy-guided fallacy detection (#84)
        try:
            from argumentation_analysis.plugins.fallacy_workflow_plugin import (
                FallacyWorkflowPlugin,
            )

            registry.register_service(
                name="hierarchical_fallacy_detector",
                service_class=FallacyWorkflowPlugin,
                capabilities=[
                    "hierarchical_fallacy_detection",
                    "fallacy_detection",
                ],
                metadata={
                    "description": (
                        "Hierarchical taxonomy-guided fallacy detection "
                        "with iterative deepening and one-shot fallback (#84)"
                    )
                },
                invoke=_invoke_hierarchical_fallacy,
            )
            registered.append("hierarchical_fallacy_detector")
        except ImportError as e:
            skipped.append(("hierarchical_fallacy_detector", str(e)))

        # Semantic index service (Arg_Semantic_Index)
        try:
            from argumentation_analysis.services.semantic_index_service import (
                SemanticIndexService,
            )

            registry.register_service(
                name="semantic_index_service",
                service_class=SemanticIndexService,
                capabilities=["semantic_indexing", "argument_search"],
                metadata={"description": "Semantic argument indexing service"},
                invoke=_invoke_semantic_index,
            )
            registered.append("semantic_index_service")
        except ImportError as e:
            skipped.append(("semantic_index_service", str(e)))

        # Speech transcription service (speech-to-text)
        try:
            from argumentation_analysis.services.speech_transcription_service import (
                SpeechTranscriptionService,
            )

            registry.register_service(
                name="speech_transcription_service",
                service_class=SpeechTranscriptionService,
                capabilities=["speech_transcription", "speech_to_text"],
                metadata={"description": "Whisper-based speech transcription service"},
                invoke=_invoke_speech_transcription,
            )
            registered.append("speech_transcription_service")
        except ImportError as e:
            skipped.append(("speech_transcription_service", str(e)))

    # --- Declare unfilled slots for future Tweety extensions ---
    _declare_tweety_slots(registry)

    # --- TweetyLogicPlugin: SK wrapper for all handlers (#91) ---
    try:
        from argumentation_analysis.plugins.tweety_logic_plugin import TweetyLogicPlugin

        registry.register_plugin(
            name="tweety_logic_plugin",
            plugin_class=TweetyLogicPlugin,
            capabilities=["tweety_logic"],
            metadata={
                "description": (
                    "SK plugin exposing all Tweety logic handlers as "
                    "@kernel_function methods for LLM agents (#91)"
                )
            },
        )
        registered.append("tweety_logic_plugin")
    except ImportError as e:
        skipped.append(("tweety_logic_plugin", str(e)))

    # --- TextToKBPlugin: NL → KB extraction (#474) ---
    try:
        from argumentation_analysis.plugins.text_to_kb_plugin import TextToKBPlugin

        registry.register_plugin(
            name="text_to_kb_plugin",
            plugin_class=TextToKBPlugin,
            capabilities=["nl_extraction", "argument_extraction", "kb_construction"],
            metadata={
                "description": (
                    "SK plugin for NL→KB extraction with iterative descent (#474)"
                )
            },
        )
        registered.append("text_to_kb_plugin")
    except ImportError as e:
        skipped.append(("text_to_kb_plugin", str(e)))

    # --- KBToTweetyPlugin: KB → Tweety formula translation (#475) ---
    try:
        from argumentation_analysis.plugins.kb_to_tweety_plugin import KBToTweetyPlugin

        registry.register_plugin(
            name="kb_to_tweety_plugin",
            plugin_class=KBToTweetyPlugin,
            capabilities=["kb_to_tweety", "formula_translation", "tweety_validation"],
            metadata={
                "description": (
                    "SK plugin for KB→Tweety formula translation with "
                    "translate-validate-retry loop (#475)"
                )
            },
        )
        registered.append("kb_to_tweety_plugin")
    except ImportError as e:
        skipped.append(("kb_to_tweety_plugin", str(e)))

    # --- Logic agent capabilities (#71 Formal Verification) ---
    logic_capabilities = [
        (
            "fact_extraction_service",
            ["fact_extraction"],
            "Heuristic claim extraction from text",
            _invoke_fact_extraction,
        ),
        (
            "propositional_logic_service",
            ["propositional_logic"],
            "Propositional logic analysis via Tweety",
            _invoke_propositional_logic,
        ),
        (
            "fol_reasoning_service",
            ["fol_reasoning"],
            "First-order logic analysis via Tweety",
            _invoke_fol_reasoning,
        ),
        (
            "modal_logic_service",
            ["modal_logic"],
            "Modal logic analysis via Tweety",
            _invoke_modal_logic,
        ),
        (
            "dung_extensions_service",
            ["dung_extensions"],
            "Dung AF extension computation via AFHandler",
            _invoke_dung_extensions,
        ),
        (
            "formal_synthesis_service",
            ["formal_synthesis"],
            "Aggregate formal analysis into unified report",
            _invoke_formal_synthesis,
        ),
        # SAT handler — no JVM dependency, uses PySAT+Z3 (#86)
        (
            "sat_handler",
            ["sat_solving"],
            "SAT/MaxSAT/MUS solver (PySAT + Z3)",
            _invoke_sat,
        ),
        # NL-to-formal-logic translation (#173)
        (
            "nl_to_logic_service",
            ["nl_to_logic_translation"],
            "NL→formal logic with LLM + Tweety validation",
            _invoke_nl_to_logic,
        ),
    ]
    for name, caps, desc, invoke_fn in logic_capabilities:
        try:
            registry.register_service(
                name=name,
                service_class=type(name, (), {}),
                capabilities=caps,
                metadata={"description": desc},
                invoke=invoke_fn,
            )
            registered.append(name)
        except Exception as e:
            skipped.append((name, str(e)))

    # --- Collaborative multi-agent debate (#175) ---
    try:
        from argumentation_analysis.orchestration.collaborative_debate import (
            _invoke_collaborative_analysis,
        )

        registry.register_service(
            name="collaborative_debate_service",
            service_class=type("collaborative_debate_service", (), {}),
            capabilities=["collaborative_analysis"],
            metadata={
                "description": (
                    "Multi-agent collaborative debate with 4 distinct roles "
                    "(critic, validator, devil's advocate, synthesizer)"
                )
            },
            invoke=_invoke_collaborative_analysis,
        )
        registered.append("collaborative_debate_service")
    except ImportError as e:
        skipped.append(("collaborative_debate_service", str(e)))

    logger.info(
        f"Registry setup complete: {len(registered)} registered, "
        f"{len(skipped)} skipped"
    )
    if skipped:
        logger.debug(f"Skipped components: {[s[0] for s in skipped]}")

    return registry


def _declare_tweety_slots(registry: CapabilityRegistry) -> None:
    """Register Tweety handler capabilities (Track A #55-#62, #85-#86)."""
    tweety_handlers = [
        (
            "ranking_semantics_handler",
            ["ranking_semantics"],
            "Qualitative argument ranking (12 reasoners: categorizer, burden, discussion, counting, tuples, strategy, propagation, saf, counter_transitivity, probabilistic_ranking, iterated_graded_defense, serialisable)",
            _invoke_ranking,
        ),
        (
            "bipolar_handler",
            ["bipolar_argumentation"],
            "Bipolar argumentation (support + attack)",
            _invoke_bipolar,
        ),
        (
            "aba_handler",
            ["aba_reasoning"],
            "Assumption-Based Argumentation",
            _invoke_aba,
        ),
        (
            "adf_handler",
            ["adf_reasoning"],
            "Abstract Dialectical Frameworks",
            _invoke_adf,
        ),
        (
            "aspic_handler",
            ["aspic_plus_reasoning"],
            "ASPIC+ structured argumentation",
            _invoke_aspic,
        ),
        (
            "belief_revision_handler",
            ["belief_revision"],
            "Belief dynamics and revision operators",
            _invoke_belief_revision,
        ),
        (
            "probabilistic_handler",
            ["probabilistic_argumentation"],
            "Probabilistic argument acceptance",
            _invoke_probabilistic,
        ),
        (
            "dialogue_handler",
            ["dialogue_protocols"],
            "Agent dialogue and negotiation protocols",
            _invoke_dialogue,
        ),
        # New handlers (#86)
        (
            "dl_handler",
            ["description_logic"],
            "ALC Description Logic (TBox/ABox reasoning)",
            _invoke_dl,
        ),
        (
            "cl_handler",
            ["conditional_logic"],
            "Conditional Logic (System Z, non-monotonic)",
            _invoke_cl,
        ),
        # AF variants (#87)
        (
            "setaf_handler",
            ["setaf_reasoning"],
            "Set Argumentation Frameworks (collective attacks)",
            _invoke_setaf,
        ),
        (
            "weighted_handler",
            ["weighted_argumentation"],
            "Weighted Argumentation Frameworks (attack weights)",
            _invoke_weighted,
        ),
        (
            "social_handler",
            ["social_argumentation"],
            "Social Abstract Argumentation (voting + attacks)",
            _invoke_social,
        ),
        # New handlers (#88, #89, #90)
        (
            "eaf_handler",
            ["epistemic_argumentation"],
            "Epistemic AF (belief-aware multi-agent argumentation)",
            _invoke_eaf,
        ),
        (
            "delp_handler",
            ["defeasible_logic"],
            "Defeasible Logic Programming (dialectical trees)",
            _invoke_delp,
        ),
        (
            "qbf_handler",
            ["qbf_reasoning"],
            "Quantified Boolean Formulas (∀/∃ over PL)",
            _invoke_qbf,
        ),
    ]
    for name, caps, desc, invoke_fn in tweety_handlers:
        try:
            registry.register_service(
                name=name,
                service_class=type(name, (), {}),  # placeholder class
                capabilities=caps,
                metadata={"description": desc, "requires": ["jvm"]},
                invoke=invoke_fn,
            )
        except Exception as e:
            logger.debug(f"Tweety handler {name} registration deferred: {e}")
            # Fall back to slot declaration if JVM not available
            for cap in caps:
                registry.declare_slot(cap, requires=["jvm"], description=desc)
