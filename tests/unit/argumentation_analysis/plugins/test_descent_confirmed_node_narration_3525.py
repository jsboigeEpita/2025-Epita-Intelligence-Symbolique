"""#3525 — a confirmation narrates the node it CONFIRMS, not the one explored.

``_descend_branch``'s « Confirmed X at depth d » line is the only text a
finding carries when the model omitted its justification (measured on the
recorded panel states: c5 three such findings, c6 five, and in all eight the
printed name was the explored parent's while the depth and the taxonomy PK
belonged to the confirmed child). A writer reads that line; this witness pins
it to the confirmed node.

Synthetic taxonomy and one fake model reply — no LLM, no network, no corpus.
"""

from __future__ import annotations

from semantic_kernel.contents import FunctionCallContent

from argumentation_analysis.plugins.exploration_plugin import ExplorationPlugin
from argumentation_analysis.plugins.fallacy_workflow_plugin import FallacyWorkflowPlugin

PARENT_PK = "697"
CHILD_PK = "698"
PARENT_NAME = "Causalité douteuse"
CHILD_NAME = "Pétition de principe"
#: The measured case: the model confirms without stating why, so the
#: narration is the ONLY text the finding carries.
JUSTIFICATION = ""


class _FakeNavigator:
    """The two navigation calls the descent makes, on a two-node tree."""

    def __init__(self) -> None:
        self._nodes = {
            PARENT_PK: {
                "PK": PARENT_PK,
                "path": "4.1",
                "depth": 2,
                "text_fr": PARENT_NAME,
                "Famille": "Sophismes de causalité",
            },
            CHILD_PK: {
                "PK": CHILD_PK,
                "path": "4.1.1",
                "depth": 3,
                "text_fr": CHILD_NAME,
                "Famille": "Sophismes de causalité",
            },
        }
        self._children = {PARENT_PK: [self._nodes[CHILD_PK]]}

    def get_node(self, pk: str):
        return self._nodes.get(pk)

    def get_children(self, pk: str):
        return self._children.get(pk, [])


class _Reply:
    """One assistant message carrying the model's single function call."""

    def __init__(self, call: FunctionCallContent) -> None:
        self.items = [call]


class _FakeLLM:
    def __init__(self, call: FunctionCallContent) -> None:
        self._call = call

    async def get_chat_message_contents(self, chat_history, settings, kernel):
        return [_Reply(self._call)]


class _FakeKernel:
    """What ``_execute_tool_calls`` reads: a plugin registry by name."""

    plugins = {"Exploration": {"confirm_fallacy": object()}}


def _plugin() -> FallacyWorkflowPlugin:
    plugin = FallacyWorkflowPlugin(
        master_kernel=object(),
        llm_service=None,
        taxonomy_data=[],
    )
    navigator = _FakeNavigator()
    plugin.taxonomy_navigator = navigator
    plugin.exploration_plugin = ExplorationPlugin(navigator, language="fr")
    return plugin


def _confirm_child_call() -> FunctionCallContent:
    return FunctionCallContent(
        id="call-1",
        name="confirm_fallacy",
        arguments={
            "node_pk": CHILD_PK,
            "matches": True,
            "justification": JUSTIFICATION,
        },
    )


async def test_a_child_confirmation_narrates_the_child_not_the_explored_parent():
    plugin = _plugin()
    plugin.llm_service = _FakeLLM(_confirm_child_call())
    # Non-empty, so the descent appends to THIS list (an empty one would be
    # replaced by a fresh list at the top of the function).
    reasoning_history = ["départ"]

    result = await plugin._descend_branch(
        window_text="un texte",
        start_pk=PARENT_PK,
        slave_kernel=_FakeKernel(),
        slave_settings=object(),
        reasoning_history=reasoning_history,
    )

    assert result is not None, "the child's confirmation must identify a fallacy"
    assert result.taxonomy_pk == CHILD_PK
    assert result.depth == 3

    line = reasoning_history[-1]
    assert line.startswith(f"Confirmed {CHILD_NAME} at depth 3"), line
    assert PARENT_NAME not in line, (
        "the narration named the explored parent beside the confirmed child's "
        "depth — the only text an omitted-justification finding carries"
    )
