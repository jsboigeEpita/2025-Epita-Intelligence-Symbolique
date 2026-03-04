"""MCP tools for workflow management and execution."""

import logging
from typing import Any, Dict, Optional

from argumentation_analysis.services.mcp_server.tools._serialization import (
    safe_serialize,
)

logger = logging.getLogger("MCP.WorkflowTools")


def register_workflow_tools(mcp: Any, get_registry: Any) -> None:
    """Register workflow-related MCP tools."""

    @mcp.tool()
    async def list_workflows() -> Dict[str, Any]:
        """List all available analysis workflows with their phases and capabilities.

        Returns a catalog of pre-built workflows including light, standard,
        full, and specialized loop workflows.
        """
        try:
            from argumentation_analysis.orchestration.unified_pipeline import (
                get_workflow_catalog,
            )

            catalog = get_workflow_catalog()
            result = {}
            for name, wf in catalog.items():
                result[name] = {
                    "phases": [
                        {
                            "name": p.name,
                            "capability": p.capability,
                            "optional": p.optional,
                            "depends_on": p.depends_on,
                        }
                        for p in wf.phases
                    ],
                    "phase_count": len(wf.phases),
                    "required_capabilities": wf.get_required_capabilities(),
                }
            return {"workflows": result, "total": len(result)}
        except Exception as e:
            logger.error("Error listing workflows: %s", e, exc_info=True)
            return {"error": "Failed to list workflows", "message": str(e)}

    @mcp.tool()
    async def run_workflow(
        text: str,
        workflow_name: str = "standard",
        create_state: bool = True,
    ) -> Dict[str, Any]:
        """Run a named analysis workflow on input text.

        Available workflows: light, standard, full, quality_gated,
        debate_governance, jtms_dung, neural_symbolic.

        Args:
            text: The text to analyze.
            workflow_name: Name of the workflow to run.
            create_state: Whether to create a UnifiedAnalysisState.
        """
        try:
            from argumentation_analysis.orchestration.unified_pipeline import (
                run_unified_analysis,
            )

            registry = get_registry()
            result = await run_unified_analysis(
                text,
                workflow_name=workflow_name,
                registry=registry,
                create_state=create_state,
            )
            return {
                "workflow_name": result.get("workflow_name", workflow_name),
                "phases": safe_serialize(result.get("phases", {})),
                "summary": safe_serialize(result.get("summary", {})),
                "capabilities_used": result.get("capabilities_used", []),
                "capabilities_missing": result.get("capabilities_missing", []),
                "state_snapshot": safe_serialize(result.get("state_snapshot")),
            }
        except ValueError as e:
            return {"error": "Invalid workflow", "message": str(e)}
        except Exception as e:
            logger.error("Error running workflow: %s", e, exc_info=True)
            return {"error": "Workflow execution failed", "message": str(e)}

    @mcp.tool()
    async def get_workflow_details(workflow_name: str) -> Dict[str, Any]:
        """Get detailed information about a specific workflow.

        Args:
            workflow_name: Name of the workflow to inspect.
        """
        try:
            from argumentation_analysis.orchestration.unified_pipeline import (
                get_workflow_catalog,
            )

            catalog = get_workflow_catalog()
            if workflow_name not in catalog:
                return {
                    "error": f"Unknown workflow: {workflow_name}",
                    "available": list(catalog.keys()),
                }
            wf = catalog[workflow_name]
            return {
                "name": wf.name,
                "phases": [
                    {
                        "name": p.name,
                        "capability": p.capability,
                        "optional": p.optional,
                        "depends_on": p.depends_on,
                        "has_condition": p.condition is not None,
                        "has_loop": p.loop_config is not None,
                        "timeout_seconds": p.timeout_seconds,
                    }
                    for p in wf.phases
                ],
                "execution_order": wf.get_execution_order(),
                "required_capabilities": wf.get_required_capabilities(),
                "validation_errors": wf.validate(),
            }
        except Exception as e:
            logger.error("Error getting workflow details: %s", e, exc_info=True)
            return {"error": "Failed to get workflow details", "message": str(e)}
