"""#3029 — an unmeasured confidence is None on the plugin path too.

The rule "un unmeasured confidence is None, not a number" (#1019 family,
#3011 helper ``fallacy_measured_fields``) held only on the conversational
lane: the plugin path filled ``0.7``/``0.5`` the moment the model's JSON
carried no ``confidence``, so the writer's None rule could never fire there —
and #3027 started printing the fabricated value in spectacular's conclusion.

Measured on the committed cassette population (678 files,
``tests/fixtures/llm_cassettes``): the plugin calls exist in the Semantic
Kernel shape (``value[i].function_calls[j]``, 158 calls — 113 explore, 37
confirm, 8 conclude), and **every recorded ``confirm_fallacy`` carries a
usable confidence** (30 lexical levels, 7 numerics; zero absent, zero
garbage) — the defect is latent on replay, so the fix is the schema change
plus these witnesses, not a campaign (issue #3029; the first measurement
here said "zero tool_calls", which is true of the OpenAI wire shape only —
corrected by the R1089 dispatch measure).

The exploration layer (#2746's ``_UNREADABLE_CONFIDENCE_SCORE`` 0.7) is the
second half, dispatched R1089: the named default had NO reader
(``confidence_note`` was produced and never consumed), so the named 0.7
reached the comparators as an ordinary number and beat measured ones. There,
unreadable or omitted ⇒ None, with the note travelling downstream.

These tests script the LLM dependency, never the classifier (#1097), and the
seam is the one #2746 established (real plugin, scripted service).
"""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, create_autospec

import pytest
from semantic_kernel import Kernel
from semantic_kernel.contents import FunctionCallContent

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.orchestration.invoke_callables import (
    _merge_fallacy_results,
)
from argumentation_analysis.orchestration.state_writers import (
    _write_hierarchical_fallacy_to_state,
)
from argumentation_analysis.plugins.fallacy_workflow_plugin import (
    FallacyWorkflowPlugin,
)

LEAF_PK = "9"
LEAF_NAME = "Appel à la peur"


def _leaf_root_taxonomy():
    """One root that has no children (same shape as the #2746 seam)."""
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
    return FallacyWorkflowPlugin(
        master_kernel=create_autospec(Kernel, instance=True),
        llm_service=MagicMock(),
        taxonomy_data=_leaf_root_taxonomy(),
    )


def _script_one_shot(plugin, reply_json: str):
    """The one-shot prompt's LLM seam returns exactly ``reply_json``."""
    plugin.llm_service.get_chat_message_content = AsyncMock(return_value=reply_json)
    return plugin


# ---------------------------------------------------------------------------
# (a) the hierarchical lane's state entry — a reply without confidence
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_one_shot_reply_without_confidence_is_none_end_to_end():
    """DoD #3029 (a): a model reply that carries no confidence leaves the
    plugin as ``None`` and lands in the hierarchical lane's state entry as
    ``None`` — never 0.5, never 0.7."""
    plugin = _script_one_shot(
        _make_plugin(),
        json.dumps(
            {
                "fallacy_name": LEAF_NAME,
                "taxonomy_pk": LEAF_PK,
                "explanation": "fear drives the persuasion",
            }
        ),
    )
    result = json.loads(await plugin._run_one_shot("Ce sera la fin de tout."))
    assert result["fallacies"], "the one-shot detection was dropped"
    assert result["fallacies"][0]["confidence"] is None, (
        "#3029: a reply without confidence was fabricated into "
        f"{result['fallacies'][0]['confidence']!r} by the plugin path"
    )

    state = UnifiedAnalysisState("test text")
    _write_hierarchical_fallacy_to_state(result, state, {})
    entries = list(state.identified_fallacies.values())
    assert entries, "the writer stored nothing"
    # ``add_fallacy`` stores honest absence as an ABSENT key (#2972/#3011):
    # an unmeasured confidence leaves no "confidence" key in the entry —
    # never a fabricated 0.5/0.7, never even an explicit None-valued key.
    assert "confidence" not in entries[0], (
        "#3029: the hierarchical lane's state entry must carry no confidence "
        f"for an unmeasured one, found {entries[0].get('confidence')!r}"
    )


@pytest.mark.asyncio
async def test_one_shot_reply_with_measured_confidence_stays_faithful():
    """Anti-'empty the guard': a measured confidence still travels as itself."""
    plugin = _script_one_shot(
        _make_plugin(),
        json.dumps(
            {
                "fallacy_name": LEAF_NAME,
                "taxonomy_pk": LEAF_PK,
                "explanation": "fear drives the persuasion",
                "confidence": 0.85,
            }
        ),
    )
    result = json.loads(await plugin._run_one_shot("Ce sera la fin de tout."))
    assert result["fallacies"][0]["confidence"] == 0.85


@pytest.mark.asyncio
async def test_one_shot_reply_with_garbage_confidence_is_none_not_kept():
    """A non-numeric confidence is unmeasured (#3015: a bool or a word is not
    a measurement) — None, not a kept string, not a fabricated number."""
    plugin = _script_one_shot(
        _make_plugin(),
        "```json\n"
        + json.dumps(
            {
                "fallacy_name": LEAF_NAME,
                "taxonomy_pk": LEAF_PK,
                "explanation": "fear drives the persuasion",
                "confidence": "beaucoup",
            }
        )
        + "\n```",
    )
    result = json.loads(await plugin._run_one_shot("Ce sera la fin de tout."))
    assert result["fallacies"], "the detection was dropped entirely"
    assert result["fallacies"][0]["confidence"] is None


# ---------------------------------------------------------------------------
# the dedup comparators consume the number — None must not crash nor win
# ---------------------------------------------------------------------------


def test_merge_prefers_a_measured_detection_over_an_unmeasured_one():
    """``_merge_fallacy_results`` keeps the highest confidence per pk; an
    unmeasured entry must lose to a measured one, not crash on None."""
    wide = [
        {
            "taxonomy_pk": "appael_peur",
            "fallacy_type": "Appel à la peur",
            "confidence": None,
            "explanation": "wide-net, model gave no confidence",
        }
    ]
    per_arg = [
        {
            "taxonomy_pk": "appael_peur",
            "fallacy_type": "Appel à la peur",
            "confidence": 0.8,
            "explanation": "per-argument, measured",
        }
    ]
    merged = _merge_fallacy_results(wide, per_arg)
    assert len(merged) == 1
    assert (
        merged[0]["confidence"] == 0.8
    ), "the measured detection must supersede the unmeasured one"


def test_merge_keeps_the_incumbent_when_none_is_measured():
    """Two unmeasured entries for one pk: the floor (wide-net) stays — no
    crash, no invented tiebreak."""
    wide = [
        {
            "taxonomy_pk": "p",
            "fallacy_type": "T",
            "confidence": None,
            "explanation": "wide-net floor",
        }
    ]
    per_arg = [
        {
            "taxonomy_pk": "p",
            "fallacy_type": "T",
            "confidence": None,
            "explanation": "per-arg late",
        }
    ]
    merged = _merge_fallacy_results(wide, per_arg)
    assert len(merged) == 1
    assert merged[0]["explanation"] == "wide-net floor"


def test_merge_two_measured_still_keeps_the_higher():
    """The pre-existing rule between two measured entries is unchanged."""
    wide = [{"taxonomy_pk": "p", "fallacy_type": "T", "confidence": 0.9}]
    per_arg = [{"taxonomy_pk": "p", "fallacy_type": "T", "confidence": 0.4}]
    merged = _merge_fallacy_results(wide, per_arg)
    assert merged[0]["confidence"] == 0.9


# ---------------------------------------------------------------------------
# R1089 — the exploration layer: the 0.7 "named" default had no reader
# ---------------------------------------------------------------------------


def _script_leaf_confirm(plugin, confirm_args: dict):
    """The #2746 descent seam: wide-net Phase 1 resolves the root, Phase 2's
    leaf call is a scripted ``confirm_fallacy`` with exactly ``confirm_args``
    (the caller decides whether the confidence key is present at all)."""
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
                        arguments=json.dumps(confirm_args),
                    )
                ]
            )
        ]
    )
    return plugin


async def _run_descent(plugin):
    result = await plugin.run_guided_analysis(
        "Ce sera la fin de tout si vous ne suivez pas notre avis."
    )
    return json.loads(result)


_CONFIRM_BASE = {
    "node_pk": LEAF_PK,
    "justification": "fear drives the persuasion",
}


@pytest.mark.asyncio
async def test_unreadable_confirm_confidence_is_none_with_note_travelling():
    """DoD R1089 (a): a ``confirm_fallacy`` whose confidence is unreadable
    confirms the fallacy with ``confidence is None`` — and the reason stays
    readable downstream: the note naming the rejected input travels to the
    ``IdentifiedFallacy``. The old layer returned a "named" 0.7 whose note no
    production code read (#3029 measure), so it beat measured 0.6s in the
    dedup comparators."""
    plugin = _script_leaf_confirm(
        _make_plugin(), {**_CONFIRM_BASE, "confidence": "tres sur"}
    )
    parsed = await _run_descent(plugin)
    assert parsed["fallacies"], "the confirmation was dropped"
    entry = parsed["fallacies"][0]
    assert entry["confidence"] is None, (
        "#3029: an unreadable confidence must not surface as a number — "
        f"found {entry['confidence']!r}"
    )
    note = entry.get("confidence_note", "")
    assert "tres sur" in note, (
        "the reason for the missing measurement must travel with the "
        f"detection, found note {note!r}"
    )


@pytest.mark.asyncio
async def test_omitted_confirm_confidence_is_none_not_medium():
    """DoD R1089 (b): a ``confirm_fallacy`` sent WITHOUT a confidence argument
    (the tool's parameter default, previously ``"medium"``) is unmeasured —
    None, not a fabricated 0.7."""
    plugin = _script_leaf_confirm(_make_plugin(), dict(_CONFIRM_BASE))
    parsed = await _run_descent(plugin)
    assert parsed["fallacies"], "the confirmation was dropped"
    entry = parsed["fallacies"][0]
    assert entry["confidence"] is None, (
        f"#3029: an omitted confidence became {entry['confidence']!r} — the "
        "signature default must not measure anything"
    )
    assert entry.get(
        "confidence_note"
    ), "an omitted confidence carries its own note (absent, not unreadable)"


@pytest.mark.asyncio
async def test_measured_lexical_confirm_confidence_stays_faithful():
    """Anti-'empty the guard': the lexical levels the recorded cassettes use
    (30 of the 37 committed confirms) keep their mapped score."""
    plugin = _script_leaf_confirm(
        _make_plugin(), {**_CONFIRM_BASE, "confidence": "high"}
    )
    parsed = await _run_descent(plugin)
    entry = parsed["fallacies"][0]
    assert entry["confidence"] == 0.9
    assert not entry.get("confidence_note"), "a faithful read needs no note"


# ---------------------------------------------------------------------------
# the tool's own contract, exercised directly (no LLM in the loop)
# ---------------------------------------------------------------------------


def _tool_confirm(**kwargs):
    from argumentation_analysis.plugins.exploration_plugin import ExplorationPlugin
    from argumentation_analysis.agents.utils.taxonomy_navigator import (
        TaxonomyNavigator,
    )

    tool = ExplorationPlugin(TaxonomyNavigator(_leaf_root_taxonomy()))
    return json.loads(tool.confirm_fallacy(**kwargs))


def test_tool_unreadable_confidence_is_none_with_named_note():
    result = _tool_confirm(node_pk=LEAF_PK, confidence="tres sur", justification="x")
    assert result["confirmed"] is True, "the confirmation must survive"
    assert result["confidence"] is None
    assert "tres sur" in result["confidence_note"]


def test_tool_absent_confidence_is_none_with_absent_note():
    """The signature default is absence (``""``): omitted ⇒ None, with a note
    that says the confidence was absent — a different reason from unreadable."""
    result = _tool_confirm(node_pk=LEAF_PK, justification="x")
    assert result["confirmed"] is True
    assert result["confidence"] is None
    note = result.get("confidence_note", "")
    assert note, "omission must be named too, not silent"
    assert "absent" in note.lower() or "absente" in note.lower()


def test_tool_lexical_and_numeric_readings_unchanged():
    """The faithful readings the cassettes rely on: levels and numbers."""
    assert (
        _tool_confirm(node_pk=LEAF_PK, confidence="high", justification="x")[
            "confidence"
        ]
        == 0.9
    )
    assert (
        _tool_confirm(node_pk=LEAF_PK, confidence="0,85", justification="x")[
            "confidence"
        ]
        == 0.85
    )
    measured = _tool_confirm(node_pk=LEAF_PK, confidence="high", justification="x")
    assert (
        "confidence_note" not in measured
    ), "a faithful read produces no note — the note is the degradation's name"
