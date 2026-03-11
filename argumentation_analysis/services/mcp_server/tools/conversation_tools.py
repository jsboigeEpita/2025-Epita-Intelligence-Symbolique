"""MCP tools for multi-turn conversational analysis."""

import logging
from typing import Any, Dict, Optional

from argumentation_analysis.services.mcp_server.tools._serialization import (
    safe_serialize,
)

logger = logging.getLogger("MCP.ConversationTools")


def register_conversation_tools(
    mcp: Any, get_registry: Any, get_session_manager: Any
) -> None:
    """Register conversation-related MCP tools."""

    @mcp.tool()
    async def start_conversation(
        text: str,
        workflow_name: str = "standard",
        max_rounds: int = 3,
        confidence_threshold: float = 0.8,
    ) -> Dict[str, Any]:
        """Start a multi-turn conversational analysis session.

        Creates a session and runs the first analysis round. Use
        continue_conversation to run additional rounds for refinement.

        Args:
            text: The text to analyze.
            workflow_name: Workflow to use (light, standard, full, etc.).
            max_rounds: Maximum rounds allowed for this conversation.
            confidence_threshold: Confidence level to consider analysis converged.
        """
        try:
            sm = get_session_manager()
            session = sm.create_session(
                text,
                workflow_name=workflow_name,
                config={
                    "max_rounds": max_rounds,
                    "confidence_threshold": confidence_threshold,
                },
            )

            # Run first round
            round_result = await _execute_round(
                get_registry, session, round_number=1
            )
            sm.update_session(session.session_id, round_result)

            return {
                "session_id": session.session_id,
                "status": "active",
                "round": 1,
                "max_rounds": max_rounds,
                "result": round_result,
            }
        except Exception as e:
            logger.error("Error starting conversation: %s", e, exc_info=True)
            return {"error": "Failed to start conversation", "message": str(e)}

    @mcp.tool()
    async def continue_conversation(
        session_id: str,
        additional_input: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Continue an existing conversational analysis session.

        Runs the next round of analysis, building on previous results.

        Args:
            session_id: The session ID from start_conversation.
            additional_input: Optional additional text or feedback for this round.
        """
        try:
            sm = get_session_manager()
            session = sm.get_session(session_id)
            if session is None:
                return {
                    "error": "Session not found or expired",
                    "session_id": session_id,
                }

            round_number = len(session.conversation_history) + 1
            max_rounds = session.config.get("max_rounds", 3)

            if round_number > max_rounds:
                return {
                    "session_id": session_id,
                    "status": "max_rounds_reached",
                    "rounds_completed": len(session.conversation_history),
                    "message": f"Maximum of {max_rounds} rounds reached.",
                }

            text = additional_input or session.text
            round_result = await _execute_round(
                get_registry, session, round_number=round_number, text_override=text
            )
            sm.update_session(session.session_id, round_result)

            return {
                "session_id": session_id,
                "status": "active",
                "round": round_number,
                "max_rounds": max_rounds,
                "result": round_result,
            }
        except Exception as e:
            logger.error("Error continuing conversation: %s", e, exc_info=True)
            return {"error": "Failed to continue conversation", "message": str(e)}

    @mcp.tool()
    async def get_conversation_status(session_id: str) -> Dict[str, Any]:
        """Get the current status of a conversation session.

        Args:
            session_id: The session ID to check.
        """
        try:
            sm = get_session_manager()
            session = sm.get_session(session_id)
            if session is None:
                return {
                    "error": "Session not found or expired",
                    "session_id": session_id,
                }

            return {
                "session_id": session.session_id,
                "workflow": session.workflow_name,
                "rounds_completed": len(session.conversation_history),
                "max_rounds": session.config.get("max_rounds", 3),
                "created_at": session.created_at,
                "last_accessed": session.last_accessed,
                "history_summary": [
                    {
                        "round": i + 1,
                        "status": r.get("status", "unknown"),
                        "confidence": r.get("confidence"),
                    }
                    for i, r in enumerate(session.conversation_history)
                ],
            }
        except Exception as e:
            logger.error("Error getting conversation status: %s", e, exc_info=True)
            return {"error": "Failed to get status", "message": str(e)}


async def _execute_round(
    get_registry: Any,
    session: Any,
    round_number: int,
    text_override: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute a single conversation round using WorkflowTurnStrategy."""
    from argumentation_analysis.orchestration.unified_pipeline import (
        CAPABILITY_STATE_WRITERS,
        get_workflow_catalog,
    )
    from argumentation_analysis.orchestration.conversational_executor import (
        WorkflowTurnStrategy,
    )

    registry = get_registry()
    catalog = get_workflow_catalog()
    workflow = catalog.get(session.workflow_name, catalog.get("standard"))

    strategy = WorkflowTurnStrategy(
        workflow=workflow,
        registry=registry,
        state_writers=CAPABILITY_STATE_WRITERS if session.state else None,
    )

    text = text_override or session.text
    context = {
        "turn_number": round_number,
        "session_id": session.session_id,
    }

    turn_result = await strategy.execute_turn(text, context, state=session.state)

    return {
        "status": "completed",
        "turn_number": turn_result.turn_number,
        "confidence": turn_result.confidence,
        "needs_refinement": turn_result.needs_refinement,
        "questions": turn_result.questions_for_user,
        "duration_seconds": turn_result.duration_seconds,
        "phase_results": safe_serialize(turn_result.phase_results),
    }
