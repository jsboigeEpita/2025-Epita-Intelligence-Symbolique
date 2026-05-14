"""Reusable iterative deepening pattern for taxonomy-like navigation.

Extracted from FallacyWorkflowPlugin (#471) for reuse in:
- Tweety query refinement
- Dung semantics exploration
- FOL signature drill-down

The pattern:
1. Present a tree-structured taxonomy to an LLM
2. LLM selects branches via tool calls
3. Iterative deepening with double-selection (confirm parent vs explore child)
4. Parallel branch exploration via asyncio.gather
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Protocol, Tuple, runtime_checkable

from semantic_kernel.kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import (
    OpenAIChatCompletion,
    OpenAIPromptExecutionSettings,
)
from semantic_kernel.connectors.ai.function_choice_behavior import (
    FunctionChoiceBehavior,
)
from semantic_kernel.contents import (
    ChatHistory,
    FunctionCallContent,
    FunctionResultContent,
)

logger = logging.getLogger(__name__)


@runtime_checkable
class TaxonomyLike(Protocol):
    """Protocol for tree-structured taxonomies navigable by the orchestrator."""

    def get_root_nodes(self) -> List[Dict[str, Any]]: ...
    def get_children(self, pk: str) -> List[Dict[str, Any]]: ...
    def get_node(self, pk: str) -> Optional[Dict[str, Any]]: ...


@runtime_checkable
class LeafConfirmer(Protocol):
    """Protocol for confirming leaf nodes via LLM tool calls."""

    async def confirm_leaf(
        self,
        node: Dict[str, Any],
        context: str,
        slave_kernel: Kernel,
        slave_settings: OpenAIPromptExecutionSettings,
        timeout: float = 30.0,
    ) -> Optional[Dict[str, Any]]:
        """Ask the LLM to confirm a leaf node. Returns confirmed dict or None."""
        ...


class IterativeDeepeningOrchestrator:
    """Generic orchestrator for iterative deepening over tree structures.

    Given a TaxonomyLike tree and a set of tool functions, the orchestrator:
    1. Presents root nodes to the LLM
    2. LLM selects candidate branches via tool calls
    3. For each branch, iterative deepening with configurable depth
    4. Parallel exploration of up to max_branches branches

    Args:
        taxonomy: A TaxonomyLike tree structure.
        llm_service: OpenAI-compatible LLM service.
        max_depth_per_branch: Max iterations per branch.
        max_branches: Max parallel branches.
        min_confirm_depth: Minimum depth before accepting confirmations.
        timeout_seconds: Timeout per LLM call.
        language: Language code for node text fields.
    """

    def __init__(
        self,
        taxonomy: TaxonomyLike,
        llm_service: OpenAIChatCompletion,
        max_depth_per_branch: int = 8,
        max_branches: int = 4,
        min_confirm_depth: int = 2,
        timeout_seconds: float = 30.0,
        language: str = "fr",
    ):
        self.taxonomy = taxonomy
        self.llm_service = llm_service
        self.max_depth_per_branch = max_depth_per_branch
        self.max_branches = max_branches
        self.min_confirm_depth = min_confirm_depth
        self.timeout_seconds = timeout_seconds
        self.language = language

    def _create_constrained_kernel(
        self, plugin: Any, plugin_name: str
    ) -> Tuple[Kernel, OpenAIPromptExecutionSettings]:
        """Create a kernel with only the navigation plugin available."""
        kernel = Kernel()
        kernel.add_service(self.llm_service)
        kernel.add_plugin(plugin, plugin_name)
        settings = OpenAIPromptExecutionSettings(
            function_choice_behavior=FunctionChoiceBehavior.Auto(auto_invoke=False)
        )
        return kernel, settings

    async def _execute_tool_calls(
        self,
        response_items: list,
        kernel: Kernel,
        history: ChatHistory,
        plugin_instance: Any,
        plugin_name: str,
    ) -> List[Dict]:
        """Execute function calls from the LLM response and feed results back."""
        results = []
        for item in response_items:
            if not isinstance(item, FunctionCallContent):
                continue

            func_name = item.name or ""
            short_name = func_name.split("-")[-1] if "-" in func_name else func_name
            arguments = item.arguments or {}

            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except (json.JSONDecodeError, TypeError):
                    arguments = {}

            try:
                method = getattr(plugin_instance, short_name, None)
                if method is not None:
                    result_str = str(method(**arguments))
                else:
                    result_str = json.dumps({"error": f"Unknown function: {func_name}"})
            except Exception as e:
                logger.warning(f"Tool call {func_name} failed: {e}")
                result_str = json.dumps({"error": str(e)})

            history.add_message(
                FunctionResultContent(
                    id=item.id, result=result_str
                ).to_chat_message_content()
            )

            try:
                parsed = json.loads(result_str)
            except (json.JSONDecodeError, TypeError):
                parsed = {"raw": result_str}
            parsed["function_name"] = short_name
            results.append(parsed)

        return results

    async def _llm_call_with_timeout(
        self,
        history: ChatHistory,
        settings: OpenAIPromptExecutionSettings,
        kernel: Kernel,
    ) -> Optional[list]:
        """Make an LLM call with timeout protection."""
        try:
            response = await asyncio.wait_for(
                self.llm_service.get_chat_message_contents(
                    chat_history=history,
                    settings=settings,
                    kernel=kernel,
                ),
                timeout=self.timeout_seconds,
            )
            return response
        except asyncio.TimeoutError:
            logger.warning("LLM call timed out")
            return None
        except Exception as e:
            logger.warning(f"LLM call failed: {e}")
            return None

    def _extract_tool_calls(self, response: Optional[list]) -> List:
        """Extract FunctionCallContent items from LLM response."""
        if not response:
            return []
        all_items = []
        for msg in response:
            if hasattr(msg, "items"):
                all_items.extend(msg.items)
        return [i for i in all_items if isinstance(i, FunctionCallContent)]
