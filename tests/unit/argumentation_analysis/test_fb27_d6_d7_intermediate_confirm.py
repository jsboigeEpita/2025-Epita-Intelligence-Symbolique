"""FB-27 #1101 — D6/D7 intermediate-node confirmation (push past EDGES).

Target: the iterative-deepening CONFIRM-vs-EXPLORE decision in
``fallacy_workflow_plugin._explore_single_branch`` (the navigation prompt
system_message + the MIN_CONFIRM_DEPTH decision gate at
fallacy_workflow_plugin.py:~1089-1115).

Root cause this addresses (verified empirically, not memo):
- The canonical D6 node "Argument circulaire" is an INTERMEDIATE node (it has
  a single child "Cercle cartésien", a narrow specialization).
- The navigation prompt's rule 2 said "Only confirm at the current level if
  you are at a LEAF node or if NO child matches even partially" → the LLM
  always descended to the over-specific child, which didn't match the text's
  general circular pattern, then concluded_no_fallacy → D6 MISSED.
- Fix (this track, prompt-only, anti-pendule): rule 2 now ALSO allows
  confirming the current node when every child is a NARROWER SPECIALIZATION
  than the fallacy the text exhibits (case (c)). No threshold lowered, no
  heuristic added — it remains an LLM judgement gated by "genuinely fallacious".

These tests are LOAD-BEARING per the #1097 lesson: they exercise the REAL
plugin with the LLM dependency mocked (``llm_service.get_chat_message_contents``
returns scripted ``FunctionCallContent``), NOT a mock of the classifier.
A regression that removes the intermediate-confirm allowance would fail
test_intermediate_d6_confirm_is_accepted.
"""

import inspect
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from semantic_kernel.contents import FunctionCallContent

from argumentation_analysis.plugins.fallacy_workflow_plugin import (
    FallacyWorkflowPlugin,
)


def _msg_with_items(*items):
    """Wrap tool-call items in a fake chat message exposing ``.items``.

    ``_explore_single_branch`` iterates ``response`` and calls ``msg.items``
    (fallacy_workflow_plugin.py:1053-1055), so the mock return value must be a
    list of message-like objects, NOT a bare list of FunctionCallContent.
    """
    return [SimpleNamespace(items=list(items))]


# ---------------------------------------------------------------------------
# Synthetic taxonomy — a D6 branch that mirrors the real shape:
#   Erreur de raisonnement (depth 1)
#     └─ Causalité douteuse (depth 2)
#          └─ Pétition de principe (depth 3)
#               └─ Argument circulaire (depth 4)  ← intermediate, GENERAL circular
#                    └─ Cercle cartésien (depth 5)  ← narrow specialization
# A general circular argument matches depth 4 but NOT the depth-5 Cartesian
# specialization — exactly the FB-20 §5.2 MISSED scenario.
# ---------------------------------------------------------------------------


def _d6_d7_taxonomy():
    """Build a minimal taxonomy exercising the intermediate-confirm path."""
    nodes = [
        # depth, path, pk, text_fr, text_en, desc
        (1, "4", "4", "Erreur de raisonnement", "Faulty logics", "root"),
        (2, "4.1", "41", "Causalité douteuse", "Questionable causality", "sub"),
        (3, "4.1.1", "411", "Pétition de principe", "Begging the question", "sub"),
        (
            4,
            "4.1.1.1",
            "4111",
            "Argument circulaire",
            "Circular reasoning",
            "Conclusion re-injected as premise, often via paraphrase.",
        ),
        (
            5,
            "4.1.1.1.1",
            "41111",
            "Cercle cartésien",
            "Cartesian circle",
            "A specific named variant: God's existence proven by our clear-and-"
            "distinct perception, which is guaranteed by God. Narrow sub-case.",
        ),
        # D7 branch (Appel à l'émotion) — intermediate root with specialized leaves
        (1, "2", "2", "Influence", "Influence", "root"),
        (2, "2.2", "22", "Appel à l'émotion", "Appeal to emotion", "sub"),
        (
            3,
            "2.2.1",
            "221",
            "Connivence",
            "Complicity",
            "Emotion as primary persuasive operator.",
        ),
    ]
    data = []
    for depth, path, pk, text_fr, text_en, desc in nodes:
        data.append(
            {
                "PK": pk,
                "path": path,
                "depth": str(depth),
                "text_fr": text_fr,
                "text_en": text_en,
                "desc_fr": desc,
                "desc_en": desc,
                "Famille": "test",
                "Sous-Famille": text_fr,
                "nom_vulgarisé": text_fr,
                "example_fr": "",
                "example_en": "",
            }
        )
    return data


def _make_plugin(taxonomy_data=None):
    """Plugin with synthetic taxonomy + mocked LLM dependency (no real API)."""
    data = taxonomy_data or _d6_d7_taxonomy()
    mock_kernel = MagicMock()
    mock_service = MagicMock()
    plugin = FallacyWorkflowPlugin(
        master_kernel=mock_kernel,
        llm_service=mock_service,
        taxonomy_data=data,
    )
    return plugin


def _slave_kernel_stub():
    """A slave-kernel mock whose ``plugins.get('Exploration')`` returns an
    object that *contains* every function name, so ``_execute_tool_calls``
    reaches the real ``self.exploration_plugin.<func>`` call (line 734) and
    does NOT fall through to the ``Unknown function`` error branch.

    ``_execute_tool_calls`` resolves the real method via
    ``getattr(self.exploration_plugin, short_name, None)`` BEFORE the kernel's
    own ``func`` — so the kernel only needs to pass the ``plugin and short_name
    in plugin`` membership test. A plain MagicMock fails that test (its
    ``__contains__`` returns False), which misroutes confirm_fallacy to an
    error dict and breaks the decision gate.
    """

    class _FakePlugin:
        def __contains__(self, name):
            return True

        def __getitem__(self, name):
            return MagicMock()

    kernel = MagicMock()
    kernel.plugins.get.return_value = _FakePlugin()
    return kernel


def _confirm_call(node_pk, justification="matches the general pattern"):
    """A FunctionCallContent scripting the LLM to confirm at node_pk.

    ``confidence`` MUST be a label ('high'/'medium'/'low') — exploration_plugin's
    confirm_fallacy maps it to a numeric score, and passing a float would raise
    AttributeError inside the tool call (caught → error dict → no confirm).
    """
    return FunctionCallContent(
        name="confirm_fallacy",
        arguments=json.dumps(
            {"node_pk": node_pk, "justification": justification, "confidence": "high"}
        ),
    )


# ---------------------------------------------------------------------------
# Contract tests — the new directive must be present (regression-detectable)
# ---------------------------------------------------------------------------


class TestIntermediateConfirmDirectivePresent:
    """The navigation prompt must allow confirming an intermediate node when
    its children are narrower specializations than the text's pattern."""

    @pytest.fixture
    def plugin_source(self):
        return inspect.getsource(FallacyWorkflowPlugin)

    def test_directive_mentions_narrower_specialization(self, plugin_source):
        src = plugin_source.lower()
        assert "narrower" in src and "specialization" in src, (
            "FB-27: navigation prompt lost the 'narrower specialization' directive "
            "that lets the LLM confirm an intermediate node (e.g. general circular "
            "reasoning) instead of descending to an over-specific leaf that won't match."
        )

    def test_directive_preserves_genuinely_fallacious_gate(self, plugin_source):
        """Anti-pendule: the new allowance must NOT weaken the 'genuinely
        fallacious' negative boundary."""
        src = plugin_source.lower()
        assert "genuinely" in src and "fallacious" in src, (
            "FB-27 anti-pendule: the 'genuinely fallacious' gate was removed — "
            "the intermediate-confirm allowance must not open false positives."
        )

    def test_no_heuristic_added(self, plugin_source):
        """Anti-pendule HARD: no regex/string-match fallback introduced."""
        src_lower = plugin_source.lower()
        for forbidden in [
            "re.match",
            "re.search",
            "if 'circular' in",
            "startswith('circular",
        ]:
            assert forbidden.lower() not in src_lower, (
                f"FB-27 anti-pendule violation: heuristic '{forbidden}' added — "
                "detection must remain LLM-conducted."
            )


# ---------------------------------------------------------------------------
# Behaviour tests — the REAL decision logic with the LLM dependency mocked
# (load-bearing per #1097: we mock llm_service, not the classifier)
# ---------------------------------------------------------------------------


class TestIntermediateD6ConfirmAccepted:
    """When the LLM (mocked) confirms at the intermediate D6 node
    'Argument circulaire' (depth 4, which is >= MIN_CONFIRM_DEPTH), the
    decision gate must ACCEPT the confirmation — not force a descent to the
    over-specific Cartesian-circle child.

    This is the test that was non-load-bearing before the FB-27 fix: the old
    prompt rule 2 told the LLM never to confirm an intermediate node, so this
    confirmation path was never exercised. Now the prompt allows it and the
    decision logic (depth >= MIN_CONFIRM_DEPTH) accepts it.
    """

    @pytest.mark.asyncio
    async def test_intermediate_d6_confirm_is_accepted(self):
        plugin = _make_plugin()
        # Script the LLM dependency to confirm at the intermediate node (depth 4).
        plugin.llm_service.get_chat_message_contents = AsyncMock(
            return_value=_msg_with_items(_confirm_call("4111"))
        )
        # Minimal slave kernel: _execute_tool_calls uses self.exploration_plugin
        # directly (fallacy_workflow_plugin.py:734), but the kernel's plugin
        # lookup must still pass the membership test — see _slave_kernel_stub.
        slave_kernel = _slave_kernel_stub()

        result = await plugin._explore_single_branch(
            argument_text="X is true because Y, and Y holds since X is the case.",
            start_pk="4",  # start at the root of the reasoning branch
            slave_kernel=slave_kernel,
            slave_settings=MagicMock(),
        )

        # The classification must land on the intermediate D6 node the LLM
        # confirmed — NOT be rejected as too shallow, NOT forced to the
        # Cartesian-circle child.
        assert result is not None, (
            "FB-27: intermediate D6 confirm produced no classification — the "
            "decision gate rejected it or the LLM was forced to descend to a "
            "non-matching leaf."
        )
        assert result.taxonomy_pk == "4111", (
            f"FB-27: expected D6 intermediate node PK '4111' (Argument circulaire), "
            f"got '{result.taxonomy_pk}'. The confirmation was not accepted at the "
            "intermediate level."
        )

    @pytest.mark.asyncio
    async def test_negative_control_no_fallacy_text_not_confirmed(self):
        """Negative control (anti-#1019): text that is NOT circular must not
        produce a D6 match. The LLM is scripted to conclude_no_fallacy for
        a non-circular argument — the result must be None (honest MISSED),
        not a fabricated match."""
        plugin = _make_plugin()
        plugin.llm_service.get_chat_message_contents = AsyncMock(
            return_value=_msg_with_items(
                FunctionCallContent(
                    name="conclude_no_fallacy",
                    arguments=json.dumps({"reason": "no circular pattern"}),
                )
            )
        )
        slave_kernel = _slave_kernel_stub()

        result = await plugin._explore_single_branch(
            argument_text="The train arrives at 8pm because the schedule says so.",
            start_pk="4",
            slave_kernel=slave_kernel,
            slave_settings=MagicMock(),
        )

        assert result is None, (
            "FB-27 negative control failed: a non-circular argument produced a "
            "D6 match — false positive (anti-#1019 violation)."
        )
