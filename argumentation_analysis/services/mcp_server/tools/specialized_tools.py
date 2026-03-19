"""MCP tools for specialized analysis capabilities."""

import logging
from typing import Any, Dict

from argumentation_analysis.services.mcp_server.tools._serialization import (
    safe_serialize,
)

logger = logging.getLogger("MCP.SpecializedTools")


def register_specialized_tools(mcp: Any, get_registry: Any) -> None:
    """Register specialized analysis MCP tools."""

    async def _invoke_by_capability(
        capability_name: str, text: str, tool_name: str
    ) -> Dict[str, Any]:
        """Helper: invoke a capability by name with standard error handling."""
        try:
            registry = get_registry()
            providers = registry.find_for_capability(capability_name)
            if not providers:
                return {
                    "error": f"Capability '{capability_name}' not available",
                    "tool": tool_name,
                    "message": "No provider registered for this capability.",
                }
            provider = providers[0]
            if provider.invoke is None:
                return {
                    "error": f"Provider '{provider.name}' has no invoke callable",
                    "tool": tool_name,
                }
            result = await provider.invoke(text, {})
            return {
                "tool": tool_name,
                "capability": capability_name,
                "provider": provider.name,
                "result": safe_serialize(result),
            }
        except Exception as e:
            logger.error(
                "Error in %s (%s): %s", tool_name, capability_name, e, exc_info=True
            )
            return {"error": f"{tool_name} failed", "message": str(e)}

    @mcp.tool()
    async def evaluate_quality(text: str) -> Dict[str, Any]:
        """Evaluate argument quality using 9 virtue detectors.

        Assesses clarity, coherence, relevance, sufficiency, accuracy,
        and other argument virtues. Returns per-virtue scores.

        Args:
            text: The argumentative text to evaluate.
        """
        return await _invoke_by_capability("argument_quality", text, "evaluate_quality")

    @mcp.tool()
    async def generate_counter_argument(text: str) -> Dict[str, Any]:
        """Generate counter-arguments using 5 rhetorical strategies.

        Strategies include reductio ad absurdum, counter-example, distinction,
        reformulation, and concession. Returns parsed arguments with evaluations.

        Args:
            text: The argument to counter.
        """
        return await _invoke_by_capability(
            "counter_argument_generation", text, "generate_counter_argument"
        )

    @mcp.tool()
    async def run_debate_analysis(text: str) -> Dict[str, Any]:
        """Analyze an argument through adversarial multi-personality debate.

        Uses Walton-Krabbe protocols with argument scoring and knowledge bases
        to provide a multi-perspective evaluation.

        Args:
            text: The argument or topic to debate.
        """
        return await _invoke_by_capability(
            "adversarial_debate", text, "run_debate_analysis"
        )

    @mcp.tool()
    async def run_governance_analysis(text: str) -> Dict[str, Any]:
        """Analyze proposals for collective decision-making.

        Uses 7 voting methods (majority, Borda, Condorcet, approval, etc.)
        with conflict resolution and consensus metrics.

        Args:
            text: The proposal or decision context to analyze.
        """
        return await _invoke_by_capability(
            "governance_simulation", text, "run_governance_analysis"
        )
