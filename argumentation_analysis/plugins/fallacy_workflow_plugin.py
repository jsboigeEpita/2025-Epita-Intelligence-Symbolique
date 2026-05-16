"""FallacyWorkflowPlugin — hierarchical taxonomy-guided fallacy detection.

Rebuilt from commit d2fdd930 with improvements:
- Iterative deepening with double-selection pattern (confirm parent vs explore child)
- Parallel branch exploration via asyncio.gather
- One-shot fallback when iterative deepening fails
- Structured output via IdentifiedFallacy Pydantic model
- Full navigation trace for explainability

See docs/reports/issue_84_git_archaeology.md for architectural history.
"""

import asyncio
import csv
import json
import logging
from pathlib import Path
from typing import Annotated, Dict, List, Optional, Tuple

from semantic_kernel.kernel import Kernel
from semantic_kernel.functions.kernel_function_decorator import kernel_function
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

from argumentation_analysis.agents.utils.taxonomy_navigator import TaxonomyNavigator
from argumentation_analysis.plugins.exploration_plugin import ExplorationPlugin
from argumentation_analysis.plugins.identification_models import (
    IdentifiedFallacy,
    FallacyAnalysisResult,
)

logger = logging.getLogger(__name__)


class FallacyWorkflowPlugin:
    """Plugin orchestrating hierarchical taxonomy-guided fallacy detection.

    Uses a master-slave kernel architecture:
    - Master: orchestrates the workflow phases
    - Slave: constrained LLM with only ExplorationPlugin tools available

    Detection algorithm:
    1. Present root categories + their children to the LLM
    2. LLM selects candidate branches via explore_branch calls
    3. For each candidate, iterative deepening with double-selection:
       - Show parent (confirm) + children (explore deeper)
       - LLM calls confirm_fallacy OR explores a child
    4. Parallel exploration of multiple branches
    5. Fallback to one-shot if iterative approach fails
    """

    MAX_DEPTH_PER_BRANCH = 8
    MAX_BRANCHES = 4
    MIN_CONFIRM_DEPTH = 2  # Don't accept confirmations at depth < 2 (too generic)

    def __init__(
        self,
        master_kernel: Kernel,
        llm_service: OpenAIChatCompletion,
        taxonomy_file_path: Optional[str] = None,
        taxonomy_data: Optional[list] = None,
        logger: Optional[logging.Logger] = None,
    ):
        self.master_kernel = master_kernel
        self.llm_service = llm_service
        self.logger = logger or logging.getLogger(__name__)
        self.language = "fr"

        data = taxonomy_data or []
        if not data and taxonomy_file_path:
            try:
                with open(taxonomy_file_path, mode="r", encoding="utf-8") as infile:
                    reader = csv.DictReader(infile)
                    data = list(reader)
            except FileNotFoundError:
                self.logger.error(f"Taxonomy file not found at {taxonomy_file_path}")
            except Exception as e:
                self.logger.error(f"Error reading taxonomy file: {e}")

        self.taxonomy_navigator = TaxonomyNavigator(taxonomy_data=data)
        self.exploration_plugin = ExplorationPlugin(
            self.taxonomy_navigator, language=self.language
        )

        if self.taxonomy_navigator.get_root_nodes():
            self.logger.info(
                f"Taxonomy loaded: {len(data)} nodes, "
                f"{len(self.taxonomy_navigator.get_root_nodes())} root categories"
            )
        else:
            self.logger.warning("Taxonomy loading failed or has no root nodes.")

    def _create_slave_kernel(self) -> Tuple[Kernel, OpenAIPromptExecutionSettings]:
        """Create a constrained kernel with only ExplorationPlugin available.

        The slave LLM can ONLY call explore_branch, confirm_fallacy, or
        conclude_no_fallacy. It cannot respond with free text.
        """
        slave_kernel = Kernel()
        slave_kernel.add_service(self.llm_service)
        slave_kernel.add_plugin(self.exploration_plugin, "Exploration")

        slave_settings = OpenAIPromptExecutionSettings(
            function_choice_behavior=FunctionChoiceBehavior.Auto(auto_invoke=False)
        )
        return slave_kernel, slave_settings

    def _create_one_shot_kernel(self) -> Tuple[Kernel, OpenAIPromptExecutionSettings]:
        """Create a kernel for one-shot fallback analysis."""
        kernel = Kernel()
        kernel.add_service(self.llm_service)
        settings = OpenAIPromptExecutionSettings(
            function_choice_behavior=FunctionChoiceBehavior.NoneInvoke()
        )
        return kernel, settings

    def _build_root_presentation(self) -> str:
        """Build a formatted presentation of root categories + their children."""
        roots = self.taxonomy_navigator.get_root_nodes()
        lines = []
        for root in roots:
            pk = root.get("PK", "")
            name = root.get(f"text_{self.language}", root.get("nom_vulgarisé", pk))
            desc = root.get(f"desc_{self.language}", "")
            lines.append(f"\n## {name} (ID: {pk})")
            if desc:
                lines.append(f"   {desc}")

            children = self.taxonomy_navigator.get_children(pk)
            for child in children:
                cpk = child.get("PK", "")
                cname = child.get(
                    f"text_{self.language}", child.get("nom_vulgarisé", cpk)
                )
                cdesc = child.get(f"desc_{self.language}", "")[:120]
                lines.append(f"   - {cname} (ID: {cpk}): {cdesc}")

        return "\n".join(lines)

    async def _execute_tool_calls(
        self,
        response_items: list,
        slave_kernel: Kernel,
        history: ChatHistory,
    ) -> List[Dict]:
        """Execute function calls from the LLM response and feed results back."""
        results = []
        for item in response_items:
            if not isinstance(item, FunctionCallContent):
                continue

            func_name = item.name or ""
            # Handle both "Exploration-explore_branch" and "explore_branch" formats
            short_name = func_name.split("-")[-1] if "-" in func_name else func_name
            arguments = item.arguments or {}

            # Parse arguments if they're a string
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except (json.JSONDecodeError, TypeError):
                    arguments = {}

            try:
                plugin = slave_kernel.plugins.get("Exploration")
                if plugin and short_name in plugin:
                    func = plugin[short_name]
                    # Call the underlying Python method directly to avoid
                    # SK 1.40's KernelFunction.__call__ requiring kernel arg
                    method = getattr(self.exploration_plugin, short_name, None)
                    if method is not None:
                        result_str = str(method(**arguments))
                    else:
                        result_str = str(func(slave_kernel, **arguments))
                else:
                    result_str = json.dumps({"error": f"Unknown function: {func_name}"})
            except Exception as e:
                self.logger.warning(f"Tool call {func_name} failed: {e}")
                result_str = json.dumps({"error": str(e)})

            # Feed result back to history
            history.add_message(
                FunctionResultContent(
                    id=item.id, result=result_str
                ).to_chat_message_content()
            )

            # Parse result for caller
            try:
                parsed = json.loads(result_str)
            except (json.JSONDecodeError, TypeError):
                parsed = {"raw": result_str}
            parsed["function_name"] = short_name
            results.append(parsed)

        return results

    async def _explore_single_branch(
        self,
        argument_text: str,
        start_pk: str,
        slave_kernel: Kernel,
        slave_settings: OpenAIPromptExecutionSettings,
        reasoning_history: Optional[List[str]] = None,
    ) -> Optional[IdentifiedFallacy]:
        """Explore a single taxonomy branch using iterative deepening.

        At each level, the LLM sees:
        - The PARENT node (marked "CONFIRM this if it matches")
        - All CHILD nodes (marked "EXPLORE deeper")

        Memory of reasons: The LLM's justification at each level is captured
        and passed to the next level's prompt for context continuity.

        Double intention: After exploring to a node, the LLM sees BOTH the
        parent (to confirm/stop) AND children (to explore deeper).

        The LLM calls confirm_fallacy to stop, explore_branch to go deeper,
        or conclude_no_fallacy to abandon the branch.
        """
        current_pk = start_pk
        navigation_trace = [start_pk]
        reasoning_history = reasoning_history or []

        for iteration in range(self.MAX_DEPTH_PER_BRANCH):
            current_node = self.taxonomy_navigator.get_node(current_pk)
            if not current_node:
                break

            children = self.taxonomy_navigator.get_children(current_pk)

            # Leaf node — ask LLM for confirmation instead of auto-confirm (#471)
            if not children:
                self.logger.info(
                    f"  Leaf node reached: {current_pk} "
                    f"({current_node.get(f'text_{self.language}', '')})"
                )
                leaf_name = current_node.get(
                    f"text_{self.language}",
                    current_node.get("nom_vulgarisé", current_pk),
                )
                leaf_desc = current_node.get(f"desc_{self.language}", "")
                leaf_example = current_node.get(f"example_{self.language}", "")

                reasoning_context = ""
                if reasoning_history:
                    reasoning_context = (
                        "\n--- PREVIOUS REASONING ---\n"
                        + "\n".join(
                            f"{i+1}. {r}" for i, r in enumerate(reasoning_history[-3:])
                        )
                        + "\n"
                    )

                leaf_prompt = (
                    f'Text to analyze: "{argument_text[:500]}"\n\n'
                    f"You reached a LEAF node in the fallacy taxonomy.\n"
                    f"Node: {leaf_name} (PK: {current_pk})\n"
                    f"Description: {leaf_desc}\n"
                    f"{'Example: ' + leaf_example[:200] if leaf_example else ''}\n"
                    f"{reasoning_context}\n"
                    "Does this leaf node correctly identify a fallacy in the text?\n"
                    "IMPORTANT: Only confirm if the reasoning in the text is genuinely fallacious.\n"
                    "Legitimate uses of authority, emotion, or tradition are NOT fallacies.\n\n"
                    "Choose ONE action:\n"
                    f"- confirm_fallacy(node_pk='{current_pk}', justification='...', confidence=0.0-1.0) "
                    "if this matches\n"
                    "- conclude_no_fallacy(reason='...') if no match"
                )

                leaf_history = ChatHistory(
                    system_message=(
                        "You are a fallacy classifier. You MUST call exactly one function. "
                        "Do NOT respond with text."
                    )
                )
                leaf_history.add_user_message(leaf_prompt)

                try:
                    leaf_response = await asyncio.wait_for(
                        self.llm_service.get_chat_message_contents(
                            chat_history=leaf_history,
                            settings=slave_settings,
                            kernel=slave_kernel,
                        ),
                        timeout=30.0,
                    )
                except asyncio.TimeoutError:
                    self.logger.warning(
                        f"  Leaf confirmation timed out for {current_pk}"
                    )
                    break
                except Exception as e:
                    self.logger.warning(f"  Leaf confirmation LLM call failed: {e}")
                    break

                leaf_items = []
                if leaf_response:
                    for msg in leaf_response:
                        if hasattr(msg, "items"):
                            leaf_items.extend(msg.items)

                leaf_calls = [
                    i for i in leaf_items if isinstance(i, FunctionCallContent)
                ]
                if not leaf_calls:
                    self.logger.info("  No function call at leaf — branch abandoned")
                    break

                leaf_results = await self._execute_tool_calls(
                    leaf_calls, slave_kernel, leaf_history
                )

                for lr in leaf_results:
                    if lr.get("function_name") == "confirm_fallacy" and lr.get(
                        "confirmed"
                    ):
                        return IdentifiedFallacy(
                            fallacy_type=lr.get("name", lr.get("name_fr", leaf_name)),
                            taxonomy_pk=current_pk,
                            taxonomy_path=current_node.get("path", ""),
                            explanation=lr.get("justification", ""),
                            confidence=lr.get("confidence", 0.7),
                            navigation_trace=navigation_trace,
                        )
                    elif lr.get("function_name") == "conclude_no_fallacy":
                        self.logger.info(
                            f"  Leaf not confirmed: {lr.get('reason', '')}"
                        )
                        return None

                break

            # Build double-selection prompt with memory of reasons
            parent_name = current_node.get(
                f"text_{self.language}", current_node.get("nom_vulgarisé", current_pk)
            )
            parent_desc = current_node.get(f"desc_{self.language}", "")
            parent_example = current_node.get(f"example_{self.language}", "")

            # Memory of reasons: include previous reasoning
            reasoning_context = ""
            if reasoning_history:
                reasoning_context = (
                    "\n--- PREVIOUS REASONING (for context) ---\n"
                    + "\n".join(
                        f"{i+1}. {r}" for i, r in enumerate(reasoning_history[-3:])
                    )
                    + "\n"
                )

            options_text = (
                f"\n--- OPTIONS at depth {current_node.get('depth', '?')} ---\n"
            )
            # Double intention: Parent can be re-selected to confirm
            options_text += (
                f"[CONFIRM] {parent_name} (ID: {current_pk})\n"
                f"  Description: {parent_desc}\n"
            )
            if parent_example:
                options_text += f"  Example: {parent_example[:200]}\n"
            options_text += (
                "  → Select this node AGAIN (confirm_fallacy with pk='{current_pk}') "
                "if this level matches and you want to STOP here.\n"
            )

            options_text += "\n[EXPLORE DEEPER] Select one of these children:\n"
            for child in children:
                cpk = child.get("PK", "")
                cname = child.get(
                    f"text_{self.language}", child.get("nom_vulgarisé", cpk)
                )
                cdesc = child.get(f"desc_{self.language}", "")
                cexample = child.get(f"example_{self.language}", "")[:150]
                options_text += f"  - {cname} (ID: {cpk}): {cdesc}\n"
                if cexample:
                    options_text += f"    Example: {cexample}\n"
                options_text += f"    → Call explore_branch(node_pk='{cpk}') to explore this branch.\n"

            prompt = (
                f'Text to analyze: "{argument_text[:500]}"\n\n'
                f"You are navigating the fallacy taxonomy. Current position: {parent_name}\n"
                f"{reasoning_context}"
                f"{options_text}\n"
                "Choose ONE action:\n"
                "- Call explore_branch(node_pk='<child_pk>') to explore a child branch\n"
                f"- Call confirm_fallacy(node_pk='{current_pk}', ...) to confirm THIS level and stop\n"
                "- Call conclude_no_fallacy(reason='...') if no match in this branch\n"
                "You MUST call exactly one function."
            )

            history = ChatHistory(
                system_message=(
                    "You are a fallacy classifier navigating a taxonomy tree. "
                    "Your goal is to find the MOST SPECIFIC (deepest) matching fallacy. "
                    "You MUST call one of the available functions. "
                    "Do NOT respond with text — only function calls.\n\n"
                    "CRITICAL MULTI-BRANCH INSTRUCTION:\n"
                    "1. When selecting among children, PREFER exploring MULTIPLE children (call explore_branch "
                    "   multiple times) rather than confirming immediately at the current level.\n"
                    "2. Only confirm at the current level if you are at a LEAF node or if NO child "
                    "   matches even partially.\n"
                    "3. Do NOT call conclude_no_fallacy prematurely. The text likely contains "
                    "   fallacies in multiple branches. Abandon a branch only if you are CERTAIN "
                    "   there is no match at ANY descendant.\n\n"
                    "IMPORTANT: Only confirm a fallacy if the reasoning in the text is "
                    "genuinely fallacious. Legitimate uses of authority, emotion, "
                    "tradition are NOT fallacies."
                )
            )
            history.add_user_message(prompt)

            try:
                response = await asyncio.wait_for(
                    self.llm_service.get_chat_message_contents(
                        chat_history=history,
                        settings=slave_settings,
                        kernel=slave_kernel,
                    ),
                    timeout=30.0,
                )
            except asyncio.TimeoutError:
                self.logger.warning(
                    f"  LLM call timed out during branch exploration at {current_pk}"
                )
                break
            except Exception as e:
                self.logger.warning(f"  LLM call failed during branch exploration: {e}")
                break

            # Extract function calls from response
            all_items = []
            if response:
                for msg in response:
                    if hasattr(msg, "items"):
                        all_items.extend(msg.items)

            tool_calls = [i for i in all_items if isinstance(i, FunctionCallContent)]
            if not tool_calls:
                self.logger.info("  No function calls in response — branch exhausted")
                break

            # Execute tool calls
            tool_results = await self._execute_tool_calls(
                tool_calls, slave_kernel, history
            )

            for result in tool_results:
                func_name = result.get("function_name", "")

                if func_name == "confirm_fallacy" and result.get("confirmed"):
                    confirmed_pk = result.get("pk", "")
                    confirmed_node = self.taxonomy_navigator.get_node(confirmed_pk)
                    confirmed_depth = (
                        int(confirmed_node.get("depth", 0)) if confirmed_node else 0
                    )
                    justification = result.get("justification", "")

                    # Capture reasoning for memory
                    reasoning_summary = (
                        f"Confirmed {current_node.get(f'text_{self.language}', current_pk)} "
                        f"at depth {confirmed_depth}: {justification}"
                    )
                    reasoning_history.append(reasoning_summary)

                    # Reject too-shallow confirmations — force deeper exploration
                    if confirmed_depth < self.MIN_CONFIRM_DEPTH and children:
                        self.logger.info(
                            f"  Confirmation at depth {confirmed_depth} rejected "
                            f"(min={self.MIN_CONFIRM_DEPTH}), forcing deeper exploration"
                        )
                        # Pick the first child as default deeper path
                        first_child = children[0]
                        current_pk = first_child.get("PK", "")
                        navigation_trace.append(current_pk)
                        break  # continue outer loop with new current_pk

                    # Build full explanation with reasoning history
                    full_explanation = justification
                    if reasoning_history:
                        full_explanation += (
                            f" | Reasoning path: {'; '.join(reasoning_history)}"
                        )

                    return IdentifiedFallacy(
                        fallacy_type=result.get(
                            "name", result.get("name_fr", result.get("pk", ""))
                        ),
                        taxonomy_pk=confirmed_pk,
                        taxonomy_path=result.get("path", ""),
                        explanation=full_explanation,
                        confidence=result.get("confidence", 0.7),
                        navigation_trace=navigation_trace,
                    )

                elif func_name == "conclude_no_fallacy":
                    reason = result.get("reason", "no reason")
                    # Capture reasoning for memory
                    reasoning_summary = f"Abandoned {current_node.get(f'text_{self.language}', current_pk)}: {reason}"
                    reasoning_history.append(reasoning_summary)
                    self.logger.info(f"  Branch abandoned: {reason}")
                    return None

                elif func_name == "explore_branch":
                    # Navigate deeper
                    node_info = result.get("node", {})
                    next_pk = node_info.get("pk", "")
                    if next_pk and next_pk != current_pk:
                        # Capture reasoning for memory - why this branch was chosen
                        branch_name = node_info.get(
                            "name", node_info.get("name_fr", next_pk)
                        )
                        reasoning_summary = f"Explored {branch_name} from {current_node.get(f'text_{self.language}', current_pk)}"
                        reasoning_history.append(reasoning_summary)

                        current_pk = next_pk
                        navigation_trace.append(current_pk)
                        self.logger.info(
                            f"  Exploring deeper: {branch_name} "
                            f"(reasoning history: {len(reasoning_history)} steps)"
                        )
                    else:
                        self.logger.info("  explore_branch returned same/empty node")
                        break

        return None

    @kernel_function(
        name="run_guided_analysis",
        description=(
            "Analyze text for fallacies using hierarchical taxonomy navigation. "
            "Uses iterative deepening with parallel branch exploration, "
            "falling back to one-shot if needed."
        ),
    )
    async def run_guided_analysis(
        self,
        argument_text: Annotated[str, "The text to analyze for fallacies"],
        trace_log_path: Optional[str] = None,
        use_one_shot: bool = False,
    ) -> Annotated[str, "JSON result with identified fallacies"]:
        """Execute hierarchical fallacy detection with one-shot fallback.

        Algorithm:
        1. Present root categories to slave LLM
        2. Slave selects candidate branches (via explore_branch calls)
        3. For each candidate, iterative deepening with double-selection
        4. Parallel exploration of up to MAX_BRANCHES branches
        5. If no result, fall back to one-shot full-taxonomy approach
        """
        file_handler = None
        if trace_log_path and str(trace_log_path).strip() not in ("", "None", "null"):
            file_handler = logging.FileHandler(
                trace_log_path, mode="w", encoding="utf-8"
            )
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

        try:
            self.logger.info(f"--- Fallacy Analysis for: '{argument_text[:80]}...' ---")

            # Direct one-shot mode if requested
            if use_one_shot:
                return await self._run_one_shot(argument_text)

            # Phase 1: Root category selection
            slave_kernel, slave_settings = self._create_slave_kernel()
            root_presentation = self._build_root_presentation()

            selection_prompt = (
                f'Text to analyze: "{argument_text[:800]}"\n\n'
                f"Below are the ROOT CATEGORIES of the fallacy taxonomy:\n"
                f"{root_presentation}\n\n"
                "CRITICAL MULTI-BRANCH SELECTION:\n"
                "You MUST select 2-3 DIFFERENT candidate branches by calling explore_branch(node_pk='<ID>') "
                "for EACH branch that COULD POTENTIALLY contain a fallacy.\n\n"
                "Why multi-branch? The text may contain MULTIPLE fallacies from different families. "
                "Exploring multiple branches in parallel ensures comprehensive coverage.\n\n"
                "Instructions:\n"
                "- Call explore_branch 2-3 times with DIFFERENT root category IDs\n"
                "- Even if one branch seems most likely, explore 1-2 others as backup\n"
                "- Do NOT stop after a single branch selection\n"
                "- Consider: Appeal to authority (relevance), Ad hominem (attack), Slippery slope (relevance), etc."
            )

            history = ChatHistory(
                system_message=(
                    "You are a fallacy classifier. Your task is to select which taxonomy "
                    "branches might contain fallacies present in the given text.\n\n"
                    "IMPORTANT: The text likely contains MULTIPLE fallacies from DIFFERENT families. "
                    "You MUST call explore_branch 2-3 times for DIFFERENT root categories.\n\n"
                    "Call explore_branch for each candidate branch. "
                    "Do NOT respond with text — only function calls.\n"
                    "Note: Only select branches if you genuinely suspect fallacious "
                    "reasoning. Legitimate rhetorical techniques (citing authority "
                    "with proper credentials, emotional appeals grounded in facts, "
                    "referencing tradition as context) are not fallacies."
                )
            )
            history.add_user_message(selection_prompt)

            try:
                response = await asyncio.wait_for(
                    self.llm_service.get_chat_message_contents(
                        chat_history=history,
                        settings=slave_settings,
                        kernel=slave_kernel,
                    ),
                    timeout=30.0,
                )
            except asyncio.TimeoutError:
                self.logger.warning(
                    "Root selection LLM call timed out. Falling back to one-shot."
                )
                return await self._run_one_shot(argument_text)
            except Exception as e:
                self.logger.warning(
                    f"Root selection LLM call failed: {e}. Falling back to one-shot."
                )
                return await self._run_one_shot(argument_text)

            # Extract selected branches from function calls
            all_items = []
            if response:
                for msg in response:
                    if hasattr(msg, "items"):
                        all_items.extend(msg.items)

            tool_calls = [i for i in all_items if isinstance(i, FunctionCallContent)]
            if not tool_calls:
                self.logger.info("No branches selected — falling back to one-shot")
                return await self._run_one_shot(argument_text)

            # Extract candidate PKs from explore_branch calls
            candidate_pks = []
            for tc in tool_calls:
                args = tc.arguments or {}
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except (json.JSONDecodeError, TypeError):
                        args = {}
                pk = args.get("node_pk", "")
                if pk and pk not in candidate_pks:
                    candidate_pks.append(pk)

            candidate_pks = candidate_pks[: self.MAX_BRANCHES]
            self.logger.info(
                f"Phase 1: {len(candidate_pks)} candidate branches selected: {candidate_pks}"
            )

            # Phase 2: Parallel iterative deepening
            # Each branch gets its own reasoning history (no shared state)
            exploration_tasks = [
                self._explore_single_branch(
                    argument_text,
                    pk,
                    slave_kernel,
                    slave_settings,
                    reasoning_history=None,  # Each branch starts fresh
                )
                for pk in candidate_pks
            ]
            branch_results = await asyncio.gather(
                *exploration_tasks, return_exceptions=True
            )

            # Phase 3: Collect results
            identified = []
            total_iterations = 0
            for result in branch_results:
                if isinstance(result, Exception):
                    self.logger.warning(f"Branch exploration error: {result}")
                    continue
                if isinstance(result, IdentifiedFallacy):
                    identified.append(result)
                    total_iterations += len(result.navigation_trace)

            if identified:
                # Sort by confidence, take best
                identified.sort(key=lambda f: f.confidence, reverse=True)
                analysis_result = FallacyAnalysisResult(
                    fallacies=identified,
                    exploration_method="iterative_deepening",
                    branches_explored=len(candidate_pks),
                    total_iterations=total_iterations,
                )
                self.logger.info(
                    f"--- Analysis complete: {len(identified)} fallacies identified "
                    f"via iterative deepening ---"
                )
                result_json = analysis_result.model_dump_json(indent=2)
                self._persist_trace(trace_log_path, analysis_result, argument_text)
                return result_json

            # Phase 4: Fallback to one-shot
            self.logger.info(
                "No fallacies found via iterative deepening — falling back to one-shot"
            )
            one_shot_result = await self._run_one_shot(argument_text)
            if trace_log_path:
                try:
                    parsed = json.loads(one_shot_result)
                    if "fallacies" in parsed:
                        parsed["trace_note"] = "one_shot_fallback"
                        parsed["argument_excerpt"] = argument_text[:200]
                        trace_path = Path(trace_log_path)
                        trace_path.parent.mkdir(parents=True, exist_ok=True)
                        trace_path.write_text(
                            json.dumps(parsed, indent=2, ensure_ascii=False),
                            encoding="utf-8",
                        )
                except (json.JSONDecodeError, TypeError):
                    pass
            return one_shot_result

        except Exception as e:
            self.logger.error(f"Analysis error: {e}", exc_info=True)
            return json.dumps({"error": str(e), "fallacies": []})
        finally:
            if file_handler:
                self.logger.removeHandler(file_handler)
                file_handler.close()

    def _persist_trace(
        self, trace_log_path: Optional[str], result: "FallacyAnalysisResult", argument_text: str
    ) -> None:
        """Persist structured taxonomy traversal trace to JSON file."""
        if not trace_log_path:
            return
        try:
            trace_entries = []
            for fallacy in result.fallacies:
                node = self.taxonomy_navigator.get_node(fallacy.taxonomy_pk)
                parent_chain = []
                if node and node.get("path"):
                    parent_chain = node["path"].split(" > ")
                trace_entries.append({
                    "taxonomy_node_id": fallacy.taxonomy_pk,
                    "fallacy_type": fallacy.fallacy_type,
                    "parent_chain": parent_chain,
                    "navigation_trace": fallacy.navigation_trace,
                    "decision_rationale": fallacy.explanation,
                    "citation_excerpt": argument_text[:200],
                    "confidence": fallacy.confidence,
                })

            trace_data = {
                "exploration_method": result.exploration_method,
                "branches_explored": result.branches_explored,
                "total_iterations": result.total_iterations,
                "traversal_paths": trace_entries,
            }

            trace_path = Path(trace_log_path)
            trace_path.parent.mkdir(parents=True, exist_ok=True)
            trace_path.write_text(
                json.dumps(trace_data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            self.logger.info(f"Trace persisted to {trace_log_path}")
        except Exception as e:
            self.logger.warning(f"Failed to persist trace: {e}")

    def _build_compact_taxonomy(self, max_depth: int = 4) -> str:
        """Build a compact taxonomy representation (PK + name + path) to fit in context."""
        lines = []
        for node in self.taxonomy_navigator.taxonomy_data:
            depth = int(node.get("depth", 0))
            if depth > max_depth:
                continue
            pk = node.get("PK", "")
            name = node.get("text_fr", node.get("nom_vulgarisé", ""))
            path = node.get("path", "")
            if name and pk:
                indent = "  " * depth
                lines.append(f"{indent}PK={pk} [{path}] {name}")
        return "\n".join(lines)

    async def _run_one_shot(self, argument_text: str) -> str:
        """Fallback one-shot analysis — sends compact taxonomy to LLM."""
        self.logger.info("Running one-shot fallback analysis")

        kernel, settings = self._create_one_shot_kernel()
        # Use compact taxonomy (depth ≤ 4) to stay within token limits
        compact_taxonomy = self._build_compact_taxonomy(max_depth=6)

        prompt = (
            f"Analyze the following text:\n--- TEXT ---\n{argument_text}\n--- END TEXT ---\n\n"
            "Identify the single most relevant fallacy from the taxonomy below. "
            "CRITICAL: Choose the MOST SPECIFIC (deepest) node that matches — "
            "generic labels like 'Ad hominem' or 'Appel à l'autorité' are too shallow. "
            "Prefer leaf nodes or deep sub-types (e.g., 'Empoisonnement du puits' instead of 'Culpabilité par association'). "
            "IMPORTANT: Use the exact fallacy name as it appears in the taxonomy (in French). "
            "Respond with ONLY a JSON object: "
            '{"fallacy_name": "...", "taxonomy_pk": "...", "explanation": "...", "confidence": 0.0-1.0}\n\n'
            f"--- TAXONOMY ---\n{compact_taxonomy}\n--- END ---"
        )

        history = ChatHistory(
            system_message=(
                "You are an expert in logical fallacies. Identify the most specific "
                "and relevant fallacy from the taxonomy. Respond with ONLY a JSON object."
            )
        )
        history.add_user_message(prompt)

        try:
            response = await self.llm_service.get_chat_message_content(
                chat_history=history, settings=settings, kernel=kernel
            )
            raw = str(response).strip()

            # Try to parse structured response
            try:
                if "```json" in raw:
                    raw = raw.split("```json")[1].split("```")[0]
                elif "```" in raw:
                    raw = raw.split("```")[1].split("```")[0]
                start = raw.find("{")
                end = raw.rfind("}") + 1
                if start >= 0 and end > start:
                    parsed = json.loads(raw[start:end])
                    fallacy = IdentifiedFallacy(
                        fallacy_type=parsed.get("fallacy_name", raw),
                        taxonomy_pk=parsed.get("taxonomy_pk", ""),
                        explanation=parsed.get("explanation", ""),
                        confidence=float(parsed.get("confidence", 0.5)),
                        navigation_trace=[],
                    )
                    result = FallacyAnalysisResult(
                        fallacies=[fallacy],
                        exploration_method="one_shot",
                    )
                    return result.model_dump_json(indent=2)
            except (json.JSONDecodeError, ValueError, TypeError):
                pass

            # Plain text fallback
            fallacy = IdentifiedFallacy(
                fallacy_type=raw[:200],
                taxonomy_pk="",
                explanation="One-shot identification (plain text response)",
                confidence=0.3,
                navigation_trace=[],
            )
            result = FallacyAnalysisResult(
                fallacies=[fallacy], exploration_method="one_shot"
            )
            return result.model_dump_json(indent=2)

        except Exception as e:
            self.logger.error(f"One-shot fallback failed: {e}")
            return json.dumps({"error": str(e), "fallacies": []})
