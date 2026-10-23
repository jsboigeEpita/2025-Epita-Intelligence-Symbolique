# -*- coding: utf-8 -*-
"""#3180 producer rework (R1109) — the author pair reaches the PRIMARY regime
and the conversational registration path.

PR #3186 landed ``move_author``/``move_author_label`` on the schema, on the
state writer and on the one-shot prompt. The coordinator review measured the
gaps this file pins:

* the descent (wide-net → exploration → confirmation) is the primary regime,
  and its two detection sites built ``IdentifiedFallacy`` without the pair;
* the tools that END a descent (leaf confirmation, confirm) never asked for
  it, so the model had no channel to say it;
* the conversational system prompt makes ``add_identified_fallacy`` the
  mandatory registration path, and neither kernel function accepted the pair.

Witnesses are LOAD-BEARING (#1097): the real plugin runs against a scripted
LLM transport (``FunctionCallContent``), not a mocked classifier. The absent,
speaker, reported and invalid controls pin the tri-state: an unknown value
degrades to silence, silence stays silent, no party is invented.

Privacy: synthetic taxonomy, invented filler, opaque labels. Deterministic:
no JVM, no LLM, no network.
"""

import inspect
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, create_autospec

import pytest
from semantic_kernel import Kernel
from semantic_kernel.contents import AuthorRole, FunctionCallContent

from argumentation_analysis.agents.utils.taxonomy_navigator import TaxonomyNavigator
from argumentation_analysis.core.phase_scoped_state import ExtractionPhaseState
from argumentation_analysis.core.shared_state import RhetoricalAnalysisState
from argumentation_analysis.core.state_manager_plugin import StateManagerPlugin
from argumentation_analysis.plugins.exploration_plugin import ExplorationPlugin

_LABEL = "l'opposant"
_JUSTIFICATION = (
    "Le locuteur rapporte une riposte d'un tiers ; sa réponse est correcte."
)


def _taxonomy():
    """Depth 1 → 5; the confirm target sits at depth 4 (past MIN_CONFIRM_DEPTH)."""
    data = []
    for depth, path, pk, text_fr in [
        (1, "4", "4", "Erreur de raisonnement"),
        (2, "4.1", "41", "Causalité douteuse"),
        (3, "4.1.1", "411", "Pétition de principe"),
        (4, "4.1.1.1", "4111", "Argument circulaire"),
        (5, "4.1.1.1.1", "41111", "Cercle cartésien"),
    ]:
        data.append(
            {
                "PK": pk,
                "path": path,
                "depth": str(depth),
                "text_fr": text_fr,
                "text_en": text_fr,
                "desc_fr": f"desc {pk}",
                "desc_en": f"desc {pk}",
                "Famille": "test",
                "Sous-Famille": text_fr,
                "nom_vulgarisé": text_fr,
                "example_fr": "",
                "example_en": "",
            }
        )
    return data


def _plugin():
    from argumentation_analysis.plugins.fallacy_workflow_plugin import (
        FallacyWorkflowPlugin,
    )

    return FallacyWorkflowPlugin(
        master_kernel=create_autospec(Kernel, instance=True),
        llm_service=MagicMock(),
        taxonomy_data=_taxonomy(),
    )


def _slave_kernel_stub():
    class _FakePlugin:
        def __contains__(self, name):
            return True

        def __getitem__(self, name):
            return MagicMock()

    kernel = create_autospec(Kernel, instance=True)
    kernel.plugins = {"Exploration": _FakePlugin()}
    return kernel


def _confirm_call(node_pk, move_author=None, move_author_label=None):
    args = {
        "node_pk": node_pk,
        "justification": _JUSTIFICATION,
        "confidence": "high",
        "matches": True,
    }
    if move_author is not None:
        args["move_author"] = move_author
    if move_author_label is not None:
        args["move_author_label"] = move_author_label
    return FunctionCallContent(name="confirm_fallacy", arguments=json.dumps(args))


class _ScriptedService:
    """Answers every call with the scripted tool call; records the prompts."""

    def __init__(self, call):
        self._call = call
        self.prompts = []

    async def get_chat_message_contents(
        self, chat_history=None, settings=None, kernel=None, **kw
    ):
        users = [
            str(m.content)
            for m in (chat_history.messages or [])
            if getattr(m, "role", None) == AuthorRole.USER
        ]
        self.prompts.append("\n".join(users))
        return [SimpleNamespace(items=[self._call])]


async def _descent(call, start_pk):
    plugin = _plugin()
    service = _ScriptedService(call)
    plugin.llm_service = service
    result = await plugin._explore_single_branch(
        argument_text="X tient parce que Y, et Y tient parce que X.",
        start_pk=start_pk,
        slave_kernel=_slave_kernel_stub(),
        slave_settings=MagicMock(),
    )
    return result, service


class TestTheLeafConfirmationCarriesTheAuthor:
    """Site ~1053: the leaf verdict builds the stored detection."""

    @pytest.mark.asyncio
    async def test_a_reported_leaf_move_says_so_with_its_party(self):
        result, _ = await _descent(
            _confirm_call("41111", move_author="reported", move_author_label=_LABEL),
            start_pk="41111",
        )
        assert result is not None and result.taxonomy_pk == "41111"
        assert result.move_author == "reported"
        assert result.move_author_label == _LABEL

    @pytest.mark.asyncio
    async def test_a_speaker_leaf_move_says_speaker(self):
        result, _ = await _descent(
            _confirm_call("41111", move_author="speaker"), start_pk="41111"
        )
        assert result is not None
        assert result.move_author == "speaker"
        assert result.move_author_label == ""

    @pytest.mark.asyncio
    async def test_an_absent_author_stays_absent(self):
        result, _ = await _descent(_confirm_call("41111"), start_pk="41111")
        assert result is not None
        assert result.move_author == "" and result.move_author_label == ""

    @pytest.mark.asyncio
    async def test_an_unknown_author_degrades_to_silence(self):
        """A value outside the pair is not a third state; no party is invented."""
        result, _ = await _descent(
            _confirm_call("41111", move_author="quelqu'un", move_author_label=_LABEL),
            start_pk="41111",
        )
        assert result is not None
        assert result.move_author == "" and result.move_author_label == ""

    @pytest.mark.asyncio
    async def test_a_label_without_an_author_is_not_a_measurement(self):
        result, _ = await _descent(
            _confirm_call("41111", move_author_label=_LABEL), start_pk="41111"
        )
        assert result is not None
        assert result.move_author == "" and result.move_author_label == ""


class TestTheNavigationConfirmationCarriesTheAuthor:
    """Site ~1306: the confirm verdict on an interior node."""

    @pytest.mark.asyncio
    async def test_a_reported_confirm_says_so_with_its_party(self):
        result, _ = await _descent(
            _confirm_call("4111", move_author="reported", move_author_label=_LABEL),
            start_pk="4",
        )
        assert result is not None and result.taxonomy_pk == "4111"
        assert result.move_author == "reported"
        assert result.move_author_label == _LABEL

    @pytest.mark.asyncio
    async def test_an_absent_confirm_stays_absent(self):
        result, _ = await _descent(_confirm_call("4111"), start_pk="4")
        assert result is not None
        assert result.move_author == "" and result.move_author_label == ""

    @pytest.mark.asyncio
    async def test_an_unknown_confirm_author_degrades_to_silence(self):
        result, _ = await _descent(
            _confirm_call("4111", move_author="unknown"), start_pk="4"
        )
        assert result is not None
        assert result.move_author == ""


class TestTheDescentPromptsAskForTheAuthor:
    """The model needs a channel; the prompt names the pair and the omission."""

    @pytest.mark.asyncio
    async def test_the_leaf_prompt_asks_the_pair(self):
        _, service = await _descent(
            _confirm_call("41111", move_author="speaker"), start_pk="41111"
        )
        prompt = service.prompts[0]
        assert "move_author='speaker|reported'" in prompt
        assert "omit both when the text does not let you tell" in prompt

    @pytest.mark.asyncio
    async def test_the_navigation_prompt_asks_the_pair(self):
        _, service = await _descent(
            _confirm_call("4111", move_author="speaker"), start_pk="4"
        )
        prompt = service.prompts[0]
        assert "move_author='speaker|reported'" in prompt
        assert "omit both when the text does not let you tell" in prompt


class TestTheRegistrationToolsCarryTheAuthor:
    """The conversational lane registers through these kernel functions."""

    def _plugin_and_state(self):
        state = RhetoricalAnalysisState("Un texte de test.")
        state.add_argument("Une unité du texte.")
        return StateManagerPlugin(state), state

    def test_the_state_manager_tool_declares_the_pair(self):
        parameters = inspect.signature(
            StateManagerPlugin.add_identified_fallacy
        ).parameters
        assert {"move_author", "move_author_label"} <= set(parameters)
        assert parameters["move_author"].default is None

    def test_a_reported_move_is_stored_with_its_party(self):
        plugin, state = self._plugin_and_state()
        fid = plugin.add_identified_fallacy(
            "Tu quoque",
            _JUSTIFICATION,
            move_author="reported",
            move_author_label=_LABEL,
        )
        entry = state.identified_fallacies[fid]
        assert entry["move_author"] == "reported"
        assert entry["move_author_label"] == _LABEL

    def test_a_speaker_move_is_stored(self):
        plugin, state = self._plugin_and_state()
        fid = plugin.add_identified_fallacy(
            "Tu quoque", _JUSTIFICATION, move_author="speaker"
        )
        assert state.identified_fallacies[fid]["move_author"] == "speaker"

    def test_an_absent_author_is_not_stored(self):
        plugin, state = self._plugin_and_state()
        fid = plugin.add_identified_fallacy("Tu quoque", _JUSTIFICATION)
        entry = state.identified_fallacies[fid]
        assert "move_author" not in entry and "move_author_label" not in entry

    def test_an_unknown_author_is_not_stored(self):
        plugin, state = self._plugin_and_state()
        fid = plugin.add_identified_fallacy(
            "Tu quoque",
            _JUSTIFICATION,
            move_author="quelqu'un",
            move_author_label=_LABEL,
        )
        entry = state.identified_fallacies[fid]
        assert "move_author" not in entry and "move_author_label" not in entry

    def test_the_phase_scoped_tool_declares_the_pair(self):
        parameters = inspect.signature(
            ExtractionPhaseState.add_identified_fallacy
        ).parameters
        assert {"move_author", "move_author_label"} <= set(parameters)

    def test_the_phase_scoped_tool_stores_a_reported_move(self):
        state = RhetoricalAnalysisState("Un texte de test.")
        state.add_argument("Une unité du texte.")
        fid = ExtractionPhaseState(state).add_identified_fallacy(
            "Tu quoque",
            _JUSTIFICATION,
            move_author="reported",
            move_author_label=_LABEL,
        )
        entry = state.identified_fallacies[fid]
        assert entry["move_author"] == "reported"
        assert entry["move_author_label"] == _LABEL

    def test_the_phase_scoped_tool_keeps_silence_silent(self):
        state = RhetoricalAnalysisState("Un texte de test.")
        state.add_argument("Une unité du texte.")
        fid = ExtractionPhaseState(state).add_identified_fallacy(
            "Tu quoque", _JUSTIFICATION
        )
        entry = state.identified_fallacies[fid]
        assert "move_author" not in entry and "move_author_label" not in entry


class TestTheVerdictToolEchoesTheAuthor:
    """``confirm_fallacy`` is the channel the model speaks on: the pair it
    accepted as a parameter comes back in the verdict result as a FIELD, so
    the detection sites read it from the tool's own answer — no transport
    carries it beside the call anymore."""

    def _verdict(self, **overrides):
        plugin = ExplorationPlugin(TaxonomyNavigator(_taxonomy()))
        kwargs = {
            "node_pk": "4111",
            "justification": _JUSTIFICATION,
            "confidence": "high",
            "matches": True,
        }
        kwargs.update(overrides)
        return json.loads(plugin.confirm_fallacy(**kwargs))

    def test_a_reported_verdict_echoes_the_pair(self):
        verdict = self._verdict(move_author="reported", move_author_label=_LABEL)
        assert verdict["move_author"] == "reported"
        assert verdict["move_author_label"] == _LABEL

    def test_a_speaker_verdict_echoes_the_pair(self):
        """The echo mirrors the writer's rule exactly: a valid author with a
        non-empty label travels whole — the readers, not the transport,
        decide what a label under ``speaker`` is worth."""
        verdict = self._verdict(move_author="speaker", move_author_label=_LABEL)
        assert verdict["move_author"] == "speaker"
        assert verdict["move_author_label"] == _LABEL

    def test_an_absent_author_stays_out_of_the_verdict(self):
        verdict = self._verdict()
        assert "move_author" not in verdict and "move_author_label" not in verdict

    def test_an_unknown_author_is_not_echoed(self):
        verdict = self._verdict(move_author="quelqu'un", move_author_label=_LABEL)
        assert "move_author" not in verdict and "move_author_label" not in verdict

    def test_a_refusal_carries_no_author(self):
        """``matches=False`` abandons the branch: nothing is detected, so
        whose move it was is not a measurement the state could store."""
        verdict = self._verdict(matches=False, move_author="reported")
        assert "move_author" not in verdict


class TestTheBatchRegistrationKeepsTheAuthor:
    """The batch kernel function must not be the lane that forgets the pair:
    both plugins delegate to ``add_identified_fallacies``, whose writer now
    forwards the pair under the same known-values-only rule."""

    def _batch(self, plugin, **extra):
        record = {
            "nom": "Tu quoque",
            "explication": _JUSTIFICATION,
            "famille": "Obstruction",
        }
        record.update(extra)
        return plugin.add_identified_fallacies([record])

    def _state(self):
        state = RhetoricalAnalysisState("Un texte de test.")
        state.add_argument("Une unité du texte.")
        return state

    def test_the_state_manager_batch_stores_a_reported_party(self):
        state = self._state()
        self._batch(
            StateManagerPlugin(state),
            move_author="reported",
            move_author_label=_LABEL,
        )
        entry = next(iter(state.identified_fallacies.values()))
        assert entry["move_author"] == "reported"
        assert entry["move_author_label"] == _LABEL

    def test_the_phase_scoped_batch_stores_a_reported_party(self):
        state = self._state()
        self._batch(
            ExtractionPhaseState(state),
            move_author="reported",
            move_author_label=_LABEL,
        )
        entry = next(iter(state.identified_fallacies.values()))
        assert entry["move_author"] == "reported"
        assert entry["move_author_label"] == _LABEL

    def test_the_batch_stores_a_speaker_move(self):
        state = self._state()
        self._batch(StateManagerPlugin(state), move_author="speaker")
        entry = next(iter(state.identified_fallacies.values()))
        assert entry["move_author"] == "speaker"
        assert "move_author_label" not in entry

    def test_an_absent_batch_author_stays_absent(self):
        state = self._state()
        self._batch(StateManagerPlugin(state))
        entry = next(iter(state.identified_fallacies.values()))
        assert "move_author" not in entry and "move_author_label" not in entry

    def test_an_unknown_batch_author_is_not_stored(self):
        state = self._state()
        self._batch(
            StateManagerPlugin(state),
            move_author="quelqu'un",
            move_author_label=_LABEL,
        )
        entry = next(iter(state.identified_fallacies.values()))
        assert "move_author" not in entry and "move_author_label" not in entry
