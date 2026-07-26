# tests/unit/argumentation_analysis/orchestration/test_cf1538_growth_validation_groupchat.py
"""Track CF of #1538 — re-establish growth validation on the AgentGroupChat path.

CD #1534 (PR #1536) removed the growth-validation re-prompt from the
AgentGroupChat path because the pre-CD block used ``chat.add_chat_message()``
plus a nested ``chat.invoke()`` — both forbidden while ``AgentChat._is_active``
is set (``semantic_kernel/agents/group_chat/agent_chat.py:41-46``, "Unable to
proceed while another agent is active."). That residue had no home (#597 is
CLOSED), so the mode that CD had just repaired (AgentGroupChat finally
constructs) silently lost the re-prompt of an agent whose turn produced no
state growth.

CF #1538 re-establishes the validation by invoking the SPEAKING AGENT directly
via ``agent.invoke()``, which is a ``ChatCompletionAgent`` method and never
touches ``AgentChat._is_active`` (the flag lives on the chat, not the agent —
verified firsthand against the SK source, not assumed). The group-chat's own
history is NOT mutated: a deep copy (``chat.history.model_copy(deep=True)``)
plus the re-prompt feedback is passed, so the selection/termination strategies
read an undisturbed history.

These tests are JVM/LLM-free and deterministic. They prove the WIRING (the
re-prompt path is reached on the group-chat path, uses ``agent.invoke`` not
``chat.add_chat_message``, records the #609 trace) and two non-regression
guards (no re-prompt when growth is present, none when validation is disabled).
The LLM-bearing DoD (#1 a real zero-growth group-chat turn triggers a re-prompt
firsthand; #2 no ``_is_active`` exception on a full run) is left to a live run —
see the PR body / dashboard [DONE].
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from semantic_kernel.contents.chat_history import ChatHistory

from argumentation_analysis.orchestration.conversational_orchestrator import (
    _run_phase,
)
from argumentation_analysis.reporting.reprompt_trace import RepromptTraceExtractor

# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------


class _FakeGroupChat:
    """CF #1538 test double: mimics the AgentGroupChat surface ``_run_phase``
    uses (``add_chat_message``, ``invoke`` async-gen, ``history``) so the
    growth-re-prompt path is exercised without a real SK group chat / LLM call.
    """

    def __init__(self, agents, selection_strategy=None, **kwargs):
        self.agents = agents
        self.history = ChatHistory()
        self.history.add_user_message("seed group-chat message")
        self.add_chat_message_calls = []

    async def add_chat_message(self, message):
        self.add_chat_message_calls.append(message)

    async def invoke(self):
        resp = MagicMock()
        resp.name = "Extractor"
        resp.content = "I looked at the text but added nothing to the state."
        yield resp


def _empty_growth_state():
    """A state where every growth-fingerprint collection is empty, so the
    fingerprint is ``(0,)*11`` and any turn that does not mutate it reads as
    zero-growth (the trigger condition for CF #1538's re-prompt)."""
    return SimpleNamespace(
        identified_arguments={},
        identified_fallacies={},
        counter_arguments=[],
        jtms_beliefs={},
        dung_frameworks={},
        aspic_results=[],
        belief_revision_results=[],
        nl_to_logic_translations=[],
        fol_analysis_results=[],
        propositional_analysis_results=[],
        modal_analysis_results=[],
        final_conclusion=None,
        # NOTE: no `consume_next_agent_designation` attr → hasattr() is False →
        # _run_phase does NOT wire DelegatingSelectionStrategy (keeps the test
        # isolated from that code path).
    )


def _make_speaking_agent(name="Extractor"):
    """A ChatCompletionAgent-like double whose ``invoke`` is an async generator
    that records the history it received (to assert copy-vs-live semantics)."""
    agent = MagicMock()
    agent.name = name
    agent.invoke_calls = []

    async def _invoke(history):
        agent.invoke_calls.append(history)
        rp = MagicMock()
        rp.content = "OK, now adding an argument."
        yield rp

    agent.invoke = _invoke
    return agent


_GC_PATCH = "semantic_kernel.agents.group_chat.agent_group_chat.AgentGroupChat"


# ---------------------------------------------------------------------------
# DoD (LLM-free wiring): the re-prompt fires on the AgentGroupChat path,
# via agent.invoke — NOT chat.add_chat_message.
# ---------------------------------------------------------------------------


class TestCF1538GroupChatGrowthReprompt:
    def test_reprompt_invokes_speaking_agent_via_agent_invoke(self):
        """DoD #1 (LLM-free part): a zero-growth group-chat turn triggers a
        re-prompt of the speaking agent via ``agent.invoke`` (the mechanism that
        bypasses ``_is_active``; ``chat.add_chat_message`` is the forbidden one).
        """
        agent = _make_speaking_agent()
        state = _empty_growth_state()
        fake_chat = _FakeGroupChat(agents=[agent])
        with patch(_GC_PATCH, return_value=fake_chat):
            asyncio.run(
                _run_phase(
                    agents=[agent],
                    initial_prompt="extract",
                    max_turns=2,
                    phase_name="Extraction & Detection",
                    state=state,
                    enable_growth_validation=True,
                    growth_re_prompt_limit=2,
                )
            )
        assert len(agent.invoke_calls) >= 1, (
            "speaking agent.invoke() not called for the re-prompt — the CF #1538 "
            "wiring (agent.invoke bypasses _is_active) did not fire"
        )

    def test_reprompt_does_not_call_chat_add_chat_message_in_loop(self):
        """DoD #2 (LLM-free part): the re-prompt must NOT use
        ``chat.add_chat_message`` (forbidden by ``_is_active``). The chat's
        ``add_chat_message`` is called exactly once — for the initial prompt —
        and never inside the re-prompt loop.
        """
        agent = _make_speaking_agent()
        state = _empty_growth_state()
        fake_chat = _FakeGroupChat(agents=[agent])
        with patch(_GC_PATCH, return_value=fake_chat):
            asyncio.run(
                _run_phase(
                    agents=[agent],
                    initial_prompt="extract",
                    max_turns=2,
                    phase_name="Extraction & Detection",
                    state=state,
                    enable_growth_validation=True,
                    growth_re_prompt_limit=2,
                )
            )
        assert len(fake_chat.add_chat_message_calls) == 1, (
            f"chat.add_chat_message called "
            f"{len(fake_chat.add_chat_message_calls)} times — expected exactly 1 "
            f"(initial prompt only); the re-prompt must use agent.invoke on a "
            f"history copy, not chat.add_chat_message (CF #1538 / anti-_is_active)"
        )

    def test_reprompt_uses_chat_history_copy_not_live_history(self):
        """DoD #2 (LLM-free part): ``agent.invoke`` receives a deep COPY of
        ``chat.history``, never ``chat.history`` itself — mutating the live
        history would desync the group-chat's selection/termination strategies.
        Also asserts the live history is not polluted with the feedback text.
        """
        agent = _make_speaking_agent()
        state = _empty_growth_state()
        fake_chat = _FakeGroupChat(agents=[agent])
        with patch(_GC_PATCH, return_value=fake_chat):
            asyncio.run(
                _run_phase(
                    agents=[agent],
                    initial_prompt="extract",
                    max_turns=2,
                    phase_name="Extraction & Detection",
                    state=state,
                    enable_growth_validation=True,
                    growth_re_prompt_limit=2,
                )
            )
        assert len(agent.invoke_calls) >= 1
        for h in agent.invoke_calls:
            assert (
                h is not fake_chat.history
            ), "agent.invoke received the LIVE chat.history — must be a deep copy"
        # The live history is not polluted with the re-prompt feedback.
        live_contents = [
            getattr(m, "content", str(m)) for m in fake_chat.history.messages
        ]
        assert not any(
            "did not produce any state changes" in c for c in live_contents
        ), "re-prompt feedback leaked into the live chat.history (CF #1538 copy isolation)"

    def test_reprompt_records_trace_via_reprompt_extractor(self):
        """DoD #3: the #609 reprompt trace is recorded on the group-chat path
        just like on the round-robin path (so the two paths stay comparable).
        """
        agent = _make_speaking_agent()
        state = _empty_growth_state()
        extractor = RepromptTraceExtractor()
        fake_chat = _FakeGroupChat(agents=[agent])
        with patch(_GC_PATCH, return_value=fake_chat):
            asyncio.run(
                _run_phase(
                    agents=[agent],
                    initial_prompt="extract",
                    max_turns=2,
                    phase_name="Extraction & Detection",
                    state=state,
                    enable_growth_validation=True,
                    growth_re_prompt_limit=2,
                    reprompt_extractor=extractor,
                )
            )
        assert len(extractor.traces) >= 1, (
            "reprompt trace empty — RepromptTraceExtractor.record() was not "
            "called on the group-chat path (CF #1538 DoD #3)"
        )
        # The trace carries the speaking agent's name (group-chat path specifics).
        assert all(t.agent_name == "Extractor" for t in extractor.traces)


# ---------------------------------------------------------------------------
# Non-regression guards
# ---------------------------------------------------------------------------


class TestCF1538NonRegression:
    def test_no_reprompt_when_growth_present(self):
        """If the turn DID produce growth (fingerprint changed), no re-prompt."""
        agent = _make_speaking_agent()
        state = _empty_growth_state()
        fake_chat = _FakeGroupChat(agents=[agent])
        with patch(
            "argumentation_analysis.orchestration.conversational_orchestrator."
            "_validate_state_growth",
            return_value=True,
        ):
            with patch(_GC_PATCH, return_value=fake_chat):
                asyncio.run(
                    _run_phase(
                        agents=[agent],
                        initial_prompt="extract",
                        max_turns=2,
                        phase_name="Extraction & Detection",
                        state=state,
                        enable_growth_validation=True,
                        growth_re_prompt_limit=2,
                    )
                )
        assert len(agent.invoke_calls) == 0, (
            "agent.invoke called despite growth being present — the re-prompt "
            "must be gated on a MEASURED absence of growth (CF #1538 anti-pendule)"
        )

    def test_no_reprompt_when_validation_disabled(self):
        """``enable_growth_validation=False`` → no re-prompt (this is the
        contract the C1 / CD #1534 tests rely on; CF #1538 must not regress it).
        """
        agent = _make_speaking_agent()
        state = _empty_growth_state()
        fake_chat = _FakeGroupChat(agents=[agent])
        with patch(_GC_PATCH, return_value=fake_chat):
            asyncio.run(
                _run_phase(
                    agents=[agent],
                    initial_prompt="extract",
                    max_turns=2,
                    phase_name="Extraction & Detection",
                    state=state,
                    enable_growth_validation=False,
                    growth_re_prompt_limit=2,
                )
            )
        assert len(agent.invoke_calls) == 0, (
            "agent.invoke called despite enable_growth_validation=False — "
            "regression of the CD #1534 / C1 contract"
        )

    def test_find_agent_by_name_returns_none_for_unknown(self):
        """The ``_find_agent_by_name`` helper returns None for a missing/unknown
        name — the caller must skip the re-prompt (safe no-op), not raise."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _find_agent_by_name,
        )

        a = _make_speaking_agent("Known")
        assert _find_agent_by_name([a], "Known") is a
        assert _find_agent_by_name([a], "Unknown") is None
        assert _find_agent_by_name([a], None) is None
        assert _find_agent_by_name([], "Anybody") is None
