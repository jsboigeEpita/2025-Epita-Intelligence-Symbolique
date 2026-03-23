"""
Conversational multi-agent orchestrator (#208-D).

Entry point for running the argumentation analysis pipeline in
**conversational mode**: real multi-agent dialogue with SK-native
AgentGroupChat, shared kernel, and LLM-backed agents.

Three macro-phases:
    1. Extraction  — FactExtractionAgent + InformalAnalysisAgent
    2. Formal      — PropositionalLogicAgent + (FOL if available)
    3. Synthesis   — CounterArgumentAgent + DebateAgent + quality plugins

Each phase runs a ConversationalPipeline (multi-turn loop) using
GroupChatTurnStrategy (SK-native AgentGroupChat).

Usage:
    from argumentation_analysis.orchestration.conversational_orchestrator import (
        run_conversational_analysis,
    )
    result = await run_conversational_analysis("Text to analyze")
"""

import logging
import os
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ConversationalOrchestrator")

# ---------------------------------------------------------------------------
# Kernel + LLM setup
# ---------------------------------------------------------------------------


def _create_shared_kernel() -> Any:
    """Create a Semantic Kernel instance with an LLM service configured.

    Reads OPENAI_API_KEY / OPENAI_CHAT_MODEL_ID from the environment.
    Returns (kernel, llm_service_id) or (None, None) if no API key.
    """
    try:
        from semantic_kernel.kernel import Kernel
        from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
    except ImportError:
        logger.warning("semantic_kernel not available — cannot create kernel")
        return None, None

    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        logger.warning("No OPENAI_API_KEY — conversational mode requires an LLM")
        return None, None

    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    model_id = os.environ.get("OPENAI_CHAT_MODEL_ID", "gpt-4o-mini")

    kernel = Kernel()
    service_id = "conversational_llm"

    try:
        llm_service = OpenAIChatCompletion(
            ai_model_id=model_id,
            api_key=api_key,
            service_id=service_id,
        )
        # Set base_url if custom
        if base_url != "https://api.openai.com/v1":
            llm_service.client._base_url = base_url
        kernel.add_service(llm_service)
        logger.info("Kernel created with LLM service: %s (%s)", service_id, model_id)
    except Exception as e:
        logger.error("Failed to create LLM service: %s", e)
        return None, None

    return kernel, service_id


def _load_plugins_for_phase(kernel: Any, phase: str) -> List[str]:
    """Load relevant plugins onto the kernel for a given macro-phase.

    Returns list of loaded plugin names.
    """
    loaded = []

    if phase == "extraction":
        try:
            from argumentation_analysis.plugins.french_fallacy_plugin import (
                FrenchFallacyPlugin,
            )

            kernel.add_plugin(FrenchFallacyPlugin(), plugin_name="french_fallacy")
            loaded.append("french_fallacy")
        except Exception as e:
            logger.debug("french_fallacy plugin not loaded: %s", e)

    elif phase == "formal":
        try:
            from argumentation_analysis.plugins.tweety_logic_plugin import (
                TweetyLogicPlugin,
            )

            kernel.add_plugin(TweetyLogicPlugin(), plugin_name="tweety_logic")
            loaded.append("tweety_logic")
        except Exception as e:
            logger.debug("tweety_logic plugin not loaded: %s", e)

        try:
            from argumentation_analysis.plugins.semantic_kernel.jtms_plugin import (
                JTMSPlugin,
            )

            kernel.add_plugin(JTMSPlugin(), plugin_name="jtms")
            loaded.append("jtms")
        except Exception as e:
            logger.debug("jtms plugin not loaded: %s", e)

    elif phase == "synthesis":
        try:
            from argumentation_analysis.plugins.quality_scoring_plugin import (
                QualityScoringPlugin,
            )

            kernel.add_plugin(QualityScoringPlugin(), plugin_name="quality_scoring")
            loaded.append("quality_scoring")
        except Exception as e:
            logger.debug("quality_scoring plugin not loaded: %s", e)

        try:
            from argumentation_analysis.plugins.governance_plugin import (
                GovernancePlugin,
            )

            kernel.add_plugin(GovernancePlugin(), plugin_name="governance")
            loaded.append("governance")
        except Exception as e:
            logger.debug("governance plugin not loaded: %s", e)

    logger.info("Phase '%s' plugins loaded: %s", phase, loaded)
    return loaded


# ---------------------------------------------------------------------------
# Agent creation per phase
# ---------------------------------------------------------------------------


def _create_phase_agents(kernel: Any, service_id: str, phase: str) -> List[Any]:
    """Create agents for a given macro-phase using AgentFactory."""
    agents = []

    try:
        from argumentation_analysis.agents.factory import AgentFactory

        factory = AgentFactory(kernel=kernel, llm_service_id=service_id)
    except Exception as e:
        logger.warning("AgentFactory not available: %s", e)
        return agents

    if phase == "extraction":
        try:
            agents.append(factory.create_project_manager_agent())
            logger.debug("Created ProjectManagerAgent for extraction")
        except Exception as e:
            logger.warning("ProjectManagerAgent creation failed: %s", e)

        try:
            agents.append(factory.create_informal_fallacy_agent())
            logger.debug("Created InformalFallacyAgent for extraction")
        except Exception as e:
            logger.warning("InformalFallacyAgent creation failed: %s", e)

    elif phase == "formal":
        try:
            agents.append(factory.create_watson_agent(agent_name="LogicAgent"))
            logger.debug("Created LogicAgent for formal phase")
        except Exception as e:
            logger.warning("LogicAgent creation failed: %s", e)

    elif phase == "synthesis":
        try:
            agents.append(factory.create_counter_argument_agent())
            logger.debug("Created CounterArgumentAgent for synthesis")
        except Exception as e:
            logger.warning("CounterArgumentAgent creation failed: %s", e)

        try:
            agents.append(
                factory.create_debate_agent(
                    agent_name="SynthesisDebater",
                    personality="The Scholar",
                    position="neutral",
                )
            )
            logger.debug("Created DebateAgent for synthesis")
        except Exception as e:
            logger.warning("DebateAgent creation failed: %s", e)

    logger.info(
        "Phase '%s' agents: %s",
        phase,
        [getattr(a, "name", str(a)) for a in agents],
    )
    return agents


# ---------------------------------------------------------------------------
# Termination strategy for conversational rounds
# ---------------------------------------------------------------------------


def _create_termination_strategy(max_iterations: int = 3) -> Any:
    """Create an SK-native termination strategy or None."""
    try:
        from semantic_kernel.agents.strategies.termination.default_termination_strategy import (
            DefaultTerminationStrategy,
        )

        return DefaultTerminationStrategy(maximum_iterations=max_iterations)
    except ImportError:
        return None


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

MACRO_PHASES = ["extraction", "formal", "synthesis"]


async def run_conversational_analysis(
    text: str,
    max_rounds: int = 3,
    confidence_threshold: float = 0.8,
    phases: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Run the full conversational multi-agent analysis pipeline.

    Args:
        text: The input text to analyze.
        max_rounds: Maximum conversation rounds per macro-phase.
        confidence_threshold: Stop early if confidence exceeds this.
        phases: Which macro-phases to run (default: all three).

    Returns:
        Dict with keys: status, phases, state_snapshot, duration_seconds.
    """
    from argumentation_analysis.orchestration.conversational_executor import (
        ConversationalPipeline,
        GroupChatTurnStrategy,
    )
    from argumentation_analysis.orchestration.turn_protocol import (
        ConversationConfig,
    )

    start = time.time()
    active_phases = phases or MACRO_PHASES
    phase_results: Dict[str, Any] = {}

    # --- Load .env if available ---
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass

    # --- Create shared kernel ---
    kernel, service_id = _create_shared_kernel()
    if kernel is None:
        logger.warning("No kernel available — returning fallback result")
        return {
            "status": "no_llm",
            "phases": {},
            "state_snapshot": {},
            "duration_seconds": time.time() - start,
            "error": "No OPENAI_API_KEY or semantic_kernel not available",
        }

    # --- Create state ---
    state = None
    try:
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState

        state = UnifiedAnalysisState(initial_text=text)
    except ImportError:
        logger.warning("UnifiedAnalysisState not available")

    # --- Run each macro-phase ---
    config = ConversationConfig(
        max_rounds=max_rounds,
        confidence_threshold=confidence_threshold,
    )

    for phase_name in active_phases:
        if phase_name not in MACRO_PHASES:
            logger.warning("Unknown phase '%s' — skipping", phase_name)
            continue

        logger.info("=== Starting macro-phase: %s ===", phase_name)
        phase_start = time.time()

        # Load plugins for this phase
        _load_plugins_for_phase(kernel, phase_name)

        # Create agents for this phase
        agents = _create_phase_agents(kernel, service_id, phase_name)
        if not agents:
            logger.warning("No agents for phase '%s' — skipping", phase_name)
            phase_results[phase_name] = {
                "status": "skipped",
                "reason": "no agents available",
            }
            continue

        # Create termination strategy
        termination = _create_termination_strategy(max_iterations=max_rounds * 2)

        # Build the turn strategy and pipeline
        strategy = GroupChatTurnStrategy(
            agents=agents,
            termination_strategy=termination,
        )
        pipeline = ConversationalPipeline(strategy, config=config)

        # Execute the conversational pipeline for this phase
        try:
            result = await pipeline.execute(
                input_data=text,
                context={"phase": phase_name},
                state=state,
            )
            phase_results[phase_name] = {
                "status": result.get("status", "unknown"),
                "rounds": len(result.get("rounds", [])),
                "summary": result.get("summary", ""),
                "duration_seconds": round(time.time() - phase_start, 2),
            }
            logger.info(
                "Phase '%s' completed: status=%s, rounds=%d",
                phase_name,
                result.get("status"),
                len(result.get("rounds", [])),
            )
        except Exception as e:
            logger.error("Phase '%s' failed: %s", phase_name, e)
            phase_results[phase_name] = {
                "status": "error",
                "error": str(e),
                "duration_seconds": round(time.time() - phase_start, 2),
            }

    # --- Build final result ---
    state_snapshot = {}
    if state and hasattr(state, "get_state_snapshot"):
        state_snapshot = state.get_state_snapshot()

    total_duration = round(time.time() - start, 2)
    completed_phases = sum(
        1 for r in phase_results.values() if r.get("status") not in ("skipped", "error")
    )

    return {
        "status": "completed" if completed_phases > 0 else "failed",
        "phases": phase_results,
        "state_snapshot": state_snapshot,
        "duration_seconds": total_duration,
        "completed_phases": completed_phases,
        "total_phases": len(active_phases),
    }
