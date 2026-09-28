"""#2746 — the leaf prompt and confirm_fallacy share one confidence contract.

The leaf prompt (fallacy_workflow_plugin.py:909) asks the LLM for
``confidence=0.0-1.0`` — a number. The tool it calls
(exploration_plugin.confirm_fallacy) annotated ``str`` 'high'|'medium'|'low'
and did ``confidence.lower().strip()``: a float 0.85 raised AttributeError
inside the tool call, was caught by _execute_tool_calls, came back as an
error dict without ``confirmed``, and the branch was abandoned — a genuine
confirmation silently treated as no confirmation. A string '0.85' fell
through the level map to 0.5, silently overwriting the asked confidence.

These tests exercise the REAL plugin through ``run_guided_analysis`` (the
public door) with the LLM dependency scripted as FunctionCallContent, not a
mock of the classifier (#1097). The taxonomy is a single root that is also
a leaf, so the first descent call IS the prompt-driven leaf call the issue
names.
"""

import inspect
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, create_autospec

import pytest
from semantic_kernel import Kernel
from semantic_kernel.contents import FunctionCallContent

from argumentation_analysis.agents.utils.taxonomy_navigator import TaxonomyNavigator
from argumentation_analysis.plugins.exploration_plugin import ExplorationPlugin
from argumentation_analysis.plugins.fallacy_workflow_plugin import (
    FallacyWorkflowPlugin,
)

LEAF_PK = "9"
LEAF_NAME = "Appel à la peur"


def _leaf_root_taxonomy():
    """One root that has no children: descent step 1 is the leaf call."""
    return [
        {
            "PK": LEAF_PK,
            "path": LEAF_PK,
            "depth": "1",
            "text_fr": LEAF_NAME,
            "text_en": "Appeal to fear",
            "desc_fr": "La peur est l'operateur persuasif principal.",
            "desc_en": "Fear is the primary persuasive operator.",
            "Famille": "test",
            "Sous-Famille": LEAF_NAME,
            "nom_vulgarisé": LEAF_NAME,
            "example_fr": "",
            "example_en": "",
        }
    ]


def _make_plugin():
    """Real plugin on a MagicMock service (network-free), taxonomy synthetic."""
    plugin = FallacyWorkflowPlugin(
        master_kernel=create_autospec(Kernel, instance=True),
        llm_service=MagicMock(),
        taxonomy_data=_leaf_root_taxonomy(),
    )
    return plugin


def _script_llm(plugin, leaf_confidence):
    """Phase 1 wide-net resolves the root; phase 2 leaf call confirms it.

    ``leaf_confidence`` lands in the tool-call arguments JSON exactly as a
    real LLM following the leaf prompt would send it.
    """
    plugin.llm_service.get_chat_message_content = AsyncMock(
        return_value=json.dumps(
            [
                {
                    "fallacy_name": LEAF_NAME,
                    "root_category": LEAF_NAME,
                    "confidence": 0.9,
                }
            ]
        )
    )
    plugin.llm_service.get_chat_message_contents = AsyncMock(
        return_value=[
            SimpleNamespace(
                items=[
                    FunctionCallContent(
                        name="confirm_fallacy",
                        arguments=json.dumps(
                            {
                                "node_pk": LEAF_PK,
                                "confidence": leaf_confidence,
                                "justification": "fear drives the persuasion",
                            }
                        ),
                    )
                ]
            )
        ]
    )
    return plugin


async def _run(plugin):
    result = await plugin.run_guided_analysis(
        "Ce sera la fin de tout si vous ne suivez pas notre avis."
    )
    return json.loads(result)


@pytest.mark.asyncio
async def test_numeric_confidence_from_leaf_prompt_is_kept_faithful():
    """0.85 asked by the prompt, 0.85 in the result — not a lost branch."""
    plugin = _script_llm(_make_plugin(), 0.85)
    parsed = await _run(plugin)
    assert parsed["exploration_method"] == "wide_net_parallel", (
        f"#2746: the numeric-confidence leaf confirmation was lost — the funnel "
        f"fell back to {parsed.get('exploration_method')!r}"
    )
    assert parsed["fallacies"], "the leaf confirmation produced no fallacy"
    assert parsed["fallacies"][0]["confidence"] == 0.85


@pytest.mark.asyncio
async def test_numeric_confidence_as_string_is_kept_faithful():
    """A schema-following LLM sends '0.85' (string) — same contract."""
    plugin = _script_llm(_make_plugin(), "0.85")
    parsed = await _run(plugin)
    assert parsed["exploration_method"] == "wide_net_parallel"
    assert parsed["fallacies"][0]["confidence"] == 0.85


@pytest.mark.asyncio
async def test_level_name_still_confirms_with_its_mapped_score():
    """Anti-'empty the guard': the legacy lexical levels keep working."""
    plugin = _script_llm(_make_plugin(), "high")
    parsed = await _run(plugin)
    assert parsed["exploration_method"] == "wide_net_parallel"
    assert parsed["fallacies"][0]["confidence"] == 0.9


@pytest.mark.asyncio
async def test_malformed_confidence_keeps_the_confirmation_named():
    """Unreadable confidence must not drop the confirmation nor stay silent."""
    plugin = _script_llm(_make_plugin(), "tres sur")
    parsed = await _run(plugin)
    assert parsed["exploration_method"] == "wide_net_parallel", (
        "#2746: a malformed confidence silently turned the confirmation "
        "into no confirmation"
    )
    assert parsed["fallacies"], "the confirmation was dropped entirely"
    assert parsed["fallacies"][0]["confidence"] == 0.7, (
        "unreadable confidence must degrade to the documented medium default, "
        "not to the old silent 0.5"
    )


# ---------------------------------------------------------------------------
# The tool's own contract, exercised directly (no LLM in the loop)
# ---------------------------------------------------------------------------


def _explorer():
    return ExplorationPlugin(TaxonomyNavigator(_leaf_root_taxonomy()))


def _confirmed(confidence):
    raw = _explorer().confirm_fallacy(
        node_pk=LEAF_PK, confidence=confidence, justification="x"
    )
    return json.loads(raw)


def test_tool_accepts_a_number_faithfully():
    assert _confirmed(0.85)["confidence"] == 0.85


def test_tool_accepts_a_numeric_string_faithfully():
    assert _confirmed("0.85")["confidence"] == 0.85


def test_tool_clamps_an_out_of_range_number():
    assert _confirmed(1.7)["confidence"] == 1.0
    assert _confirmed(-0.5)["confidence"] == 0.0


def test_tool_maps_level_names_as_before():
    assert _confirmed("high")["confidence"] == 0.9
    assert _confirmed("Medium ")["confidence"] == 0.7
    assert _confirmed("low")["confidence"] == 0.4


def test_tool_names_the_unreadable_input_instead_of_ignoring_it():
    result = _confirmed("tres sur")
    assert result["confirmed"] is True
    assert result["confidence"] == 0.7
    assert (
        "tres sur" in result["confidence_note"]
    ), "the degradation must be named, not silent (#2746)"


def test_tool_signature_documents_the_numeric_contract():
    """The tool's parameter description must not contradict the leaf prompt."""
    signature = inspect.signature(
        ExplorationPlugin.confirm_fallacy.__wrapped__
        if hasattr(ExplorationPlugin.confirm_fallacy, "__wrapped__")
        else ExplorationPlugin.confirm_fallacy
    )
    description = signature.parameters["confidence"].annotation.__metadata__[0]
    assert "0.0" in description and "1.0" in description, (
        "confirm_fallacy's confidence annotation no longer documents the "
        "numeric range the leaf prompt asks for — the two contracts diverged again"
    )
