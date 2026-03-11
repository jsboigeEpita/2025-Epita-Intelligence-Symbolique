"""MCP tools for capability registry introspection and invocation."""

import logging
from typing import Any, Dict, List, Optional

from argumentation_analysis.services.mcp_server.tools._serialization import (
    safe_serialize,
)

logger = logging.getLogger("MCP.CapabilityTools")


def register_capability_tools(mcp: Any, get_registry: Any) -> None:
    """Register capability-related MCP tools."""

    @mcp.tool()
    async def list_capabilities() -> Dict[str, Any]:
        """List all registered capabilities with their providers and unfilled slots.

        Returns a map of capability names to provider lists, plus any unfilled
        capability slots that are declared but not yet implemented.
        """
        try:
            registry = get_registry()
            caps = registry.get_all_capabilities()
            slots = registry.get_all_slots()
            summary = registry.summary()
            return {
                "capabilities": safe_serialize(caps),
                "unfilled_slots": {
                    name: s.description for name, s in slots.items()
                },
                "summary": safe_serialize(summary),
            }
        except Exception as e:
            logger.error("Error listing capabilities: %s", e, exc_info=True)
            return {"error": "Failed to list capabilities", "message": str(e)}

    @mcp.tool()
    async def invoke_capability(
        capability_name: str,
        text: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Directly invoke a registered capability by name.

        Finds the best provider for the capability and calls its invoke function.

        Args:
            capability_name: The capability to invoke (e.g. 'argument_quality').
            text: The input text to process.
            context: Optional context dict passed to the provider.
        """
        try:
            registry = get_registry()
            providers = registry.find_for_capability(capability_name)
            if not providers:
                all_caps = registry.get_all_capabilities()
                return {
                    "error": f"No provider for capability: {capability_name}",
                    "available_capabilities": list(all_caps.keys()),
                }
            provider = providers[0]
            if provider.invoke is None:
                return {
                    "error": f"Provider '{provider.name}' has no invoke callable",
                    "capability": capability_name,
                }
            result = await provider.invoke(text, context or {})
            return {
                "capability": capability_name,
                "provider": provider.name,
                "result": safe_serialize(result),
            }
        except Exception as e:
            logger.error(
                "Error invoking capability %s: %s", capability_name, e, exc_info=True
            )
            return {"error": "Capability invocation failed", "message": str(e)}

    @mcp.tool()
    async def get_registry_summary() -> Dict[str, Any]:
        """Get a detailed summary of the capability registry.

        Returns counts of agents, plugins, services, capabilities, and
        a full list of all registered components.
        """
        try:
            registry = get_registry()
            summary = registry.summary()
            registrations = registry.get_all_registrations()
            return {
                "summary": safe_serialize(summary),
                "registrations": [
                    {
                        "name": r.name,
                        "type": r.component_type.value,
                        "capabilities": r.capabilities,
                        "has_invoke": r.invoke is not None,
                        "metadata": safe_serialize(r.metadata),
                    }
                    for r in registrations
                ],
            }
        except Exception as e:
            logger.error("Error getting registry summary: %s", e, exc_info=True)
            return {"error": "Failed to get registry summary", "message": str(e)}
