"""
Composable multi-turn conversational pipeline.

Provides ConversationalPipeline (the multi-turn loop) and two built-in
TurnStrategy implementations:

- WorkflowTurnStrategy: executes a WorkflowDefinition (DAG) per turn
- GroupChatTurnStrategy: runs an AgentGroupChat (SK-native) per turn

Any custom TurnStrategy can be plugged in.

Usage:
    from argumentation_analysis.orchestration.conversational_executor import (
        ConversationalPipeline, WorkflowTurnStrategy, GroupChatTurnStrategy,
    )

    strategy = WorkflowTurnStrategy(workflow, registry)
    pipeline = ConversationalPipeline(strategy, config=ConversationConfig(max_rounds=5))
    result = await pipeline.execute("Analyze this argument", state=state)
"""

import logging
import time
from typing import Any, Dict, List, Optional

from argumentation_analysis.orchestration.turn_protocol import (
    ConversationConfig,
    TurnResult,
    TurnStrategy,
)
from argumentation_analysis.orchestration.workflow_dsl import (
    PhaseResult,
    PhaseStatus,
    WorkflowDefinition,
    WorkflowExecutor,
)

logger = logging.getLogger("ConversationalExecutor")


class ConversationalPipeline:
    """
    Multi-turn pipeline using any TurnStrategy.

    Executes turns in a loop, passing context between rounds, until
    convergence, confidence threshold, or max_rounds is reached.
    """

    def __init__(
        self,
        turn_strategy: TurnStrategy,
        config: Optional[ConversationConfig] = None,
    ):
        self._strategy = turn_strategy
        self._config = config or ConversationConfig()

    async def execute(
        self,
        input_data: Any,
        context: Optional[Dict[str, Any]] = None,
        state: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Execute multi-turn conversation.

        Returns:
            Dict with keys:
                - status: "converged" | "high_confidence" | "max_rounds" | "failed"
                - rounds: List of (round_number, TurnResult) tuples
                - final_turn_result: Last TurnResult
                - total_duration: Total time in seconds
                - summary: Text summary
        """
        start_time = time.time()
        rounds: List[Dict[str, Any]] = []
        prev_result: Optional[TurnResult] = None

        for round_num in range(1, self._config.max_rounds + 1):
            ctx = self._build_context(round_num, prev_result, context)

            try:
                turn_result = await self._strategy.execute_turn(
                    input_data, ctx, state=state
                )
            except Exception as e:
                logger.error(f"Round {round_num} failed: {e}")
                rounds.append({"round_number": round_num, "error": str(e)})
                return {
                    "status": "failed",
                    "rounds": rounds,
                    "final_turn_result": prev_result,
                    "total_duration": time.time() - start_time,
                    "summary": f"Failed at round {round_num}: {e}",
                }

            rounds.append({"round_number": round_num, "turn_result": turn_result})

            logger.info(
                f"Round {round_num}: confidence={turn_result.confidence:.2f}, "
                f"needs_refinement={turn_result.needs_refinement}"
            )

            # Check convergence with custom function
            if prev_result is not None and self._has_converged(
                prev_result, turn_result
            ):
                logger.info(f"Converged at round {round_num}")
                return self._build_result("converged", rounds, turn_result, start_time)

            # Check confidence threshold
            if turn_result.confidence >= self._config.confidence_threshold:
                logger.info(
                    f"Confidence threshold ({self._config.confidence_threshold}) "
                    f"reached at round {round_num}"
                )
                return self._build_result(
                    "high_confidence", rounds, turn_result, start_time
                )

            prev_result = turn_result

        # Max rounds reached
        logger.info(f"Max rounds ({self._config.max_rounds}) reached")
        return self._build_result("max_rounds", rounds, prev_result, start_time)

    def _build_context(
        self,
        round_num: int,
        prev_result: Optional[TurnResult],
        base_context: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Build context dict for a round."""
        ctx = dict(base_context or {})
        ctx["turn_number"] = round_num
        ctx["previous_turn_result"] = prev_result
        if prev_result is not None:
            ctx["previous_outputs"] = {
                name: r.output
                for name, r in prev_result.phase_results.items()
                if r.output is not None
            }
        return ctx

    def _has_converged(self, prev_result: TurnResult, curr_result: TurnResult) -> bool:
        """Check convergence between two turns."""
        if self._config.convergence_fn is not None:
            try:
                return self._config.convergence_fn(prev_result, curr_result)
            except Exception as e:
                logger.warning(f"Convergence check failed: {e} — continuing")
        return False

    def _build_result(
        self,
        status: str,
        rounds: List[Dict[str, Any]],
        final: Optional[TurnResult],
        start_time: float,
    ) -> Dict[str, Any]:
        """Build the final result dict."""
        return {
            "status": status,
            "rounds": rounds,
            "final_turn_result": final,
            "total_duration": time.time() - start_time,
            "summary": self._generate_summary(status, rounds),
        }

    def _generate_summary(self, status: str, rounds: List[Dict[str, Any]]) -> str:
        """Generate text summary of the conversation."""
        lines = [f"Conversation: {len(rounds)} round(s), status={status}"]
        for r in rounds:
            tr = r.get("turn_result")
            if tr:
                lines.append(
                    f"  Round {tr.turn_number}: "
                    f"conf={tr.confidence:.2f}, "
                    f"refinement={'yes' if tr.needs_refinement else 'no'}"
                )
            else:
                lines.append(
                    f"  Round {r['round_number']}: error={r.get('error', '?')}"
                )
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Built-in TurnStrategy implementations
# ---------------------------------------------------------------------------


class WorkflowTurnStrategy(TurnStrategy):
    """
    Execute a WorkflowDefinition (DAG) as one conversational turn.

    Wraps WorkflowExecutor — each turn runs the full workflow once.
    """

    def __init__(
        self,
        workflow: WorkflowDefinition,
        registry: Any,
        state_writers: Optional[Dict[str, Any]] = None,
    ):
        self._workflow = workflow
        self._executor = WorkflowExecutor(registry)
        self._state_writers = state_writers

    async def execute_turn(
        self,
        input_data: Any,
        context: Dict[str, Any],
        state: Optional[Any] = None,
    ) -> TurnResult:
        """Execute workflow and convert results to TurnResult."""
        start = time.time()

        phase_results = await self._executor.execute(
            self._workflow,
            input_data,
            context=context,
            state=state,
            state_writers=self._state_writers,
        )

        duration = time.time() - start
        confidence = _extract_confidence(phase_results)
        questions = _extract_questions(phase_results)

        has_failures = any(
            r.status == PhaseStatus.FAILED for r in phase_results.values()
        )

        return TurnResult(
            turn_number=context.get("turn_number", 1),
            phase_results=phase_results,
            confidence=confidence,
            needs_refinement=has_failures,
            questions_for_user=questions,
            duration_seconds=duration,
        )


class GroupChatTurnStrategy(TurnStrategy):
    """
    Execute an AgentGroupChat round as one conversational turn.

    Uses the **native SK AgentGroupChat** (async generator API) when
    available, falling back to the sequential compatibility shim in
    ``cluedo_extended_orchestrator`` only when the SK import fails.

    Accepts SelectionStrategy / TerminationStrategy from either
    ``orchestration/base.py`` (project-local) or ``semantic_kernel``
    directly.  Project-local strategies are wrapped automatically via
    ``_wrap_selection_strategy`` / ``_wrap_termination_strategy``.
    """

    def __init__(
        self,
        agents: List[Any],
        selection_strategy: Optional[Any] = None,
        termination_strategy: Optional[Any] = None,
    ):
        self._agents = agents
        self._selection = selection_strategy
        self._termination = termination_strategy

    # ------------------------------------------------------------------
    # Strategy adapters: project base.py → SK native
    # ------------------------------------------------------------------

    @staticmethod
    def _wrap_selection_strategy(strategy: Any) -> Any:
        """Wrap a base.py SelectionStrategy as an SK-native one if needed."""
        if strategy is None:
            return None
        try:
            from semantic_kernel.agents.strategies.selection.selection_strategy import (
                SelectionStrategy as SKSelectionStrategy,
            )

            if isinstance(strategy, SKSelectionStrategy):
                return strategy
        except ImportError:
            return strategy

        # Build an SK-compatible adapter
        try:
            from semantic_kernel.agents.strategies.selection.selection_strategy import (
                SelectionStrategy as SKSelectionStrategy,
            )

            class _Adapter(SKSelectionStrategy):
                _inner: Any

                def __init__(self, inner: Any, **kwargs: Any):
                    super().__init__(**kwargs)
                    object.__setattr__(self, "_inner", inner)

                async def next(self, agents: list, history: list) -> Any:
                    return await self._inner.next(agents, history)

            return _Adapter(inner=strategy)
        except Exception:
            return strategy

    @staticmethod
    def _wrap_termination_strategy(strategy: Any) -> Any:
        """Wrap a base.py TerminationStrategy as an SK-native one if needed."""
        if strategy is None:
            return None
        try:
            from semantic_kernel.agents.strategies.termination.termination_strategy import (
                TerminationStrategy as SKTerminationStrategy,
            )

            if isinstance(strategy, SKTerminationStrategy):
                return strategy
        except ImportError:
            return strategy

        try:
            from semantic_kernel.agents.strategies.termination.termination_strategy import (
                TerminationStrategy as SKTerminationStrategy,
            )

            class _Adapter(SKTerminationStrategy):
                _inner: Any

                def __init__(self, inner: Any, **kwargs: Any):
                    super().__init__(**kwargs)
                    object.__setattr__(self, "_inner", inner)

                async def should_terminate(self, agent: Any, history: list) -> bool:
                    return await self._inner.should_terminate(agent, history)

            return _Adapter(inner=strategy, maximum_iterations=100)
        except Exception:
            return strategy

    # ------------------------------------------------------------------
    # Core execution
    # ------------------------------------------------------------------

    async def execute_turn(
        self,
        input_data: Any,
        context: Dict[str, Any],
        state: Optional[Any] = None,
    ) -> TurnResult:
        """Run AgentGroupChat and convert messages to TurnResult."""
        start = time.time()

        messages = await self._run_sk_native(input_data, context)
        if messages is None:
            messages = await self._run_fallback(input_data)

        if messages is None:
            logger.warning("AgentGroupChat not available — returning empty turn")
            return TurnResult(
                turn_number=context.get("turn_number", 1),
                phase_results={},
                confidence=0.0,
                needs_refinement=True,
                duration_seconds=time.time() - start,
            )

        duration = time.time() - start
        phase_results = self._messages_to_phase_results(messages)
        confidence = _extract_confidence(phase_results)
        questions = _extract_questions(phase_results)

        return TurnResult(
            turn_number=context.get("turn_number", 1),
            phase_results=phase_results,
            confidence=confidence,
            needs_refinement=len(phase_results) == 0,
            questions_for_user=questions,
            duration_seconds=duration,
        )

    async def _run_sk_native(
        self, input_data: Any, context: Dict[str, Any]
    ) -> Optional[List[Any]]:
        """Try running with the real SK AgentGroupChat (async generator)."""
        try:
            from semantic_kernel.agents.group_chat.agent_group_chat import (
                AgentGroupChat,
            )
            from semantic_kernel.contents.chat_message_content import (
                ChatMessageContent,
            )
            from semantic_kernel.contents.utils.author_role import AuthorRole
        except ImportError:
            return None

        try:
            selection = self._wrap_selection_strategy(self._selection)
            termination = self._wrap_termination_strategy(self._termination)

            kwargs: Dict[str, Any] = {"agents": list(self._agents)}
            if selection is not None:
                kwargs["selection_strategy"] = selection
            if termination is not None:
                kwargs["termination_strategy"] = termination

            chat = AgentGroupChat(**kwargs)

            # Seed the chat history with the user input so agents have
            # something to respond to.
            if input_data is not None:
                chat.add_chat_message(
                    ChatMessageContent(
                        role=AuthorRole.USER,
                        content=str(input_data),
                    )
                )

            # Collect messages from the async generator
            collected: List[ChatMessageContent] = []
            async for msg in chat.invoke():
                collected.append(msg)

            logger.info(
                "SK AgentGroupChat produced %d messages from %d agents",
                len(collected),
                len(self._agents),
            )
            return collected

        except Exception as exc:
            logger.warning("SK native AgentGroupChat failed (%s), falling back", exc)
            return None

    async def _run_fallback(self, input_data: Any) -> Optional[List[Any]]:
        """Fallback to the compatibility shim in cluedo_extended_orchestrator."""
        try:
            from argumentation_analysis.orchestration.cluedo_extended_orchestrator import (
                AgentGroupChat as FallbackGroupChat,
            )
        except ImportError:
            return None

        chat = FallbackGroupChat(
            agents=self._agents,
            selection_strategy=self._selection,
            termination_strategy=self._termination,
        )
        return await chat.invoke(str(input_data) if input_data else None)

    def _messages_to_phase_results(self, messages: Any) -> Dict[str, PhaseResult]:
        """Convert AgentGroupChat messages to PhaseResult dict."""
        results: Dict[str, PhaseResult] = {}
        if not messages or not isinstance(messages, list):
            return results

        for i, msg in enumerate(messages):
            agent_name = f"agent_{i}"
            # Extract agent name from message if available
            if hasattr(msg, "name") and msg.name:
                agent_name = msg.name
            elif hasattr(msg, "role") and msg.role:
                agent_name = str(msg.role)

            # Extract content
            content = msg
            if hasattr(msg, "content"):
                content = msg.content

            results[agent_name] = PhaseResult(
                phase_name=agent_name,
                status=PhaseStatus.COMPLETED,
                capability="group_chat",
                component_used=agent_name,
                output=content,
            )

        return results


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _extract_confidence(phase_results: Dict[str, PhaseResult]) -> float:
    """Extract average confidence from phase outputs."""
    scores = []
    for result in phase_results.values():
        if result.status == PhaseStatus.COMPLETED and result.output is not None:
            if isinstance(result.output, dict):
                conf = result.output.get("confidence")
                if conf is not None:
                    try:
                        scores.append(float(conf))
                    except (TypeError, ValueError):
                        pass
    return sum(scores) / len(scores) if scores else 0.5


def _extract_questions(phase_results: Dict[str, PhaseResult]) -> List[str]:
    """Extract user questions from phase outputs."""
    questions: List[str] = []
    for result in phase_results.values():
        if result.status == PhaseStatus.COMPLETED and isinstance(result.output, dict):
            q = result.output.get("user_question")
            if q and isinstance(q, str):
                questions.append(q)
    return questions
