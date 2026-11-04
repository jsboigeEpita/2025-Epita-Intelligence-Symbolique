# -*- coding: utf-8 -*-
"""#3391 — on the false-positive control, legitimate mobilisation and the
speaker's own self-correction are read as fallacies.

Read on the v1 panel, cycle 0. The panel's legitimate-emotion control carried
an « appel à l'élévation morale » recorded as a firm detection, and the
synthesis then described the mobilisation through fallacy anchors with no
counter-reading; the speaker restricted his own preceding statement in the
next breath and Act II read that revision as a firm « fausse implication ».
The zero-shot called the same register fitting for its occasion.

The issue's asks, as witnesses:

* the emotion / loyalty / flag family **carries its test** — is the emotion
  and the call proportionate to what the text itself states? The taxonomy
  node's own conditions ARE the test, so no new rule is invented. The test is
  a FIELD, recorded on the detection when the flag stands;
* an outcome **« legitimate in its register »** exists: a proportionate appeal
  is not a fallacy, and the verdict is RECORDED (named outcome + state trace),
  not dropped into a bare refusal;
* the synthesis **does not describe a strategy through bare flags**: a
  register-family line carries the test that stands it, or says the test is
  unrecorded;
* a **self-correction** is not a false implication of the wording it corrects
  — that reading lives in the descent's own instructions, witnessed on the
  messages the plugin actually sends.

Anti-pendulum, pinned in the prompts and in the note: a disproportionate
appeal stays flagged, whoever the speaker. The cap is the same map for every
side.

Privacy: synthetic taxonomy, invented filler, opaque ids. Deterministic: no
JVM, no LLM, no network.
"""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, create_autospec

import pytest
from semantic_kernel import Kernel
from semantic_kernel.contents import FunctionCallContent

from argumentation_analysis.agents.core.synthesis.deep_synthesis_agent import (
    DeepSynthesisAgent,
)

# Les symboles NEUFS du fix sont importés DANS les seuls tests qui les
# testent : sur ``main``, le fichier doit collector pour que les témoins
# rougissent sur leurs ASSERTIONS, jamais sur une erreur de collection qui ne
# prouverait rien (fiche [[nerouge_new_symbol_collection]]).

_AFFIRMING_JUSTIFICATION = (
    "L'appel reste proportionné à ce que le texte énonce : les faits cités "
    "portent la mobilisation demandée."
)
_PROPORTIONATE_JUSTIFICATION = (
    "L'appel à l'élévation morale reste proportionné aux faits que le texte "
    "énonce lui-même : légitime dans son registre."
)
_DISPROPORTIONATE_JUSTIFICATION = (
    "L'appel dépasse les faits énoncés : la crainte invoquée n'est étayée par "
    "aucune donnée du texte."
)


def _taxonomy():
    """One register-family node above its leaf, plus an unrelated branch.

    The family is decided by the NAME (the taxonomy splits the register across
    ``Influence`` and ``Insuffisance``), so both spellings are represented.
    """
    data = []
    for depth, path, pk, text_fr, desc in [
        (1, "2", "2", "Influence", "root"),
        (2, "2.2", "22", "Appel à l'émotion", "L'émotion porte la persuasion."),
        (
            3,
            "2.2.1",
            "221",
            "Appel à la peur",
            "La crainte est invoquée à la place des raisons.",
        ),
        (1, "1", "1", "Insuffisance", "root"),
        (2, "1.2", "12", "Appel à la loyauté", "La loyauté tient lieu d'argument."),
        (1, "4", "4", "Erreur de raisonnement", "root"),
        (2, "4.1", "41", "Ad hominem", "L'argument attaque la personne."),
    ]:
        data.append(
            {
                "PK": pk,
                "path": path,
                "depth": str(depth),
                "text_fr": text_fr,
                "text_en": text_fr,
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


def _msg_with_items(*items):
    return [SimpleNamespace(items=list(items))]


def _confirm_call(
    node_pk, matches=True, justification=_AFFIRMING_JUSTIFICATION, **extra
):
    args = {"node_pk": node_pk, "justification": justification, "confidence": "high"}
    args["matches"] = matches
    args.update(extra)
    return FunctionCallContent(name="confirm_fallacy", arguments=json.dumps(args))


def _state(fallacies=None, arena=None):
    state = SimpleNamespace(
        propositional_analysis_results=None,
        fol_analysis_results=None,
        modal_analysis_results=None,
        raw_text="un texte synthétique quelconque",
        identified_arguments={
            "arg_1": {"id": "arg_1", "description": "Une position du texte."},
        },
        identified_fallacies=fallacies or {},
    )
    stakes = {}
    if arena is not None:
        stakes["discursive_arena"] = arena
    if stakes:
        state.stakes_and_stakeholders = stakes
    return state


def _fallacy_record(**overrides):
    record = {
        "type": "Appel à la peur",
        "family": "Influence",
        "justification": "La crainte est invoquée à la place des raisons.",
        "target_argument_id": "arg_1",
    }
    record.update(overrides)
    return record


class TestTheFamilyCarriesItsTest:
    """Ask 1 — the register family is identifiable, and the test it applied is
    a closed-vocabulary FIELD: what the detector measured, or nothing."""

    def test_the_register_family_is_named_by_the_detection_name(self):
        from argumentation_analysis.core.fallacy_attribution import (
            is_register_family_detection,
        )

        for name in (
            "Appel à l’émotion",  # U+2019, the taxonomy's own spelling
            "Appel à la loyauté",
            "Appel au drapeau",
            "Appel à la peur",
            "Argument du pathos",
            "Sophisme affectif",
        ):
            assert is_register_family_detection(name), name
        # The family is the NAME, never the whole CSV 'Influence' famille:
        # 420 nodes carry no such test (anti-pendulum — an unrelated flag is
        # not exempted from its author by mistake).
        for name in ("Ad hominem", "Pente glissante", "Faux dilemme", "Épouvantail"):
            assert not is_register_family_detection(name), name

    def test_only_the_closed_vocabulary_is_a_measurement(self):
        from argumentation_analysis.core.fallacy_attribution import (
            normalize_register_test,
        )

        assert normalize_register_test("Disproportionate") == "disproportionate"
        assert normalize_register_test(" proportionate ") == "proportionate"
        for bogus in ("", "yes", "maybe", None, True):
            assert normalize_register_test(bogus) == ""

    def test_the_state_door_records_the_test(self):
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState

        state = UnifiedAnalysisState("un texte quelconque")
        fid = state.add_fallacy(
            "Appel à la peur",
            "La crainte est invoquée à la place des raisons.",
            register_test="disproportionate",
        )
        assert state.identified_fallacies[fid]["register_test"] == "disproportionate"

    def test_an_unknown_value_is_absence_not_a_measurement(self):
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState

        state = UnifiedAnalysisState("un texte quelconque")
        fid = state.add_fallacy("Appel à la peur", "justif", register_test="bogus")
        assert "register_test" not in state.identified_fallacies[fid]


class TestTheToolEchoesTheTest:
    """The verdict rides BOTH halves of the tool result: a proportionate
    appeal is the family's own negative answer, and its test must stay
    readable on the refusal."""

    def _tool(self):
        from argumentation_analysis.agents.utils.taxonomy_navigator import (
            TaxonomyNavigator,
        )
        from argumentation_analysis.plugins.exploration_plugin import (
            ExplorationPlugin,
        )

        plugin = ExplorationPlugin.__new__(ExplorationPlugin)
        plugin.taxonomy_navigator = TaxonomyNavigator(taxonomy_data=_taxonomy())
        plugin.language = "fr"
        plugin._alt_lang = "en"
        return plugin

    def test_a_confirmation_echoes_the_test(self):
        result = json.loads(
            self._tool().confirm_fallacy(
                node_pk="221",
                confidence="high",
                matches=True,
                justification=_DISPROPORTIONATE_JUSTIFICATION,
                register_test="disproportionate",
            )
        )
        assert result["confirmed"] is True
        assert result["register_test"] == "disproportionate"

    def test_a_refusal_echoes_the_test(self):
        result = json.loads(
            self._tool().confirm_fallacy(
                node_pk="221",
                confidence="high",
                matches=False,
                justification=_PROPORTIONATE_JUSTIFICATION,
                register_test="proportionate",
            )
        )
        assert result["confirmed"] is False
        assert result["register_test"] == "proportionate"


class TestALegitimateRegisterIsAnAnswer:
    """Ask 1, second half — the proportionate verdict is a NAMED outcome of
    the descent, not a bare refusal and never a stored fallacy."""

    @pytest.mark.asyncio
    async def test_a_proportionate_refusal_is_named_legitimate_in_register(self):
        plugin = _plugin()
        plugin.llm_service.get_chat_message_contents = AsyncMock(
            return_value=_msg_with_items(
                _confirm_call(
                    "221",
                    matches=False,
                    justification=_PROPORTIONATE_JUSTIFICATION,
                    register_test="proportionate",
                )
            )
        )
        outcomes = []
        result = await plugin._explore_single_branch(
            argument_text="Le texte appelle à l'élévation morale sur ses propres faits.",
            start_pk="22",
            slave_kernel=_slave_kernel_stub(),
            slave_settings=MagicMock(),
            outcomes=outcomes,
        )
        assert result is None
        assert outcomes and outcomes[0]["action"] == "legitimate_in_register"
        assert outcomes[0]["reason"] == _PROPORTIONATE_JUSTIFICATION

    @pytest.mark.asyncio
    async def test_a_proportionate_confirm_wins_over_the_boolean(self):
        """The test is the family's own answer: a model that passes
        ``matches=true`` while recording the appeal proportionate has said the
        node does NOT apply. The field decides, like every other verdict."""
        plugin = _plugin()
        plugin.llm_service.get_chat_message_contents = AsyncMock(
            return_value=_msg_with_items(
                _confirm_call(
                    "221",
                    matches=True,
                    justification=_PROPORTIONATE_JUSTIFICATION,
                    register_test="proportionate",
                )
            )
        )
        outcomes = []
        result = await plugin._explore_single_branch(
            argument_text="Le texte appelle à l'élévation morale sur ses propres faits.",
            start_pk="22",
            slave_kernel=_slave_kernel_stub(),
            slave_settings=MagicMock(),
            outcomes=outcomes,
        )
        assert result is None
        assert outcomes[0]["action"] == "legitimate_in_register"

    @pytest.mark.asyncio
    async def test_a_disproportionate_verdict_stands_the_flag_and_rides_it(self):
        """Anti-pendulum: the same family, disproportionate — the detection
        stands and carries the test that stands it."""
        plugin = _plugin()
        plugin.llm_service.get_chat_message_contents = AsyncMock(
            return_value=_msg_with_items(
                _confirm_call(
                    "221",
                    matches=True,
                    justification=_DISPROPORTIONATE_JUSTIFICATION,
                    register_test="disproportionate",
                )
            )
        )
        result = await plugin._explore_single_branch(
            argument_text="Le texte agite une crainte sans citer un seul fait.",
            start_pk="221",  # start AT the leaf
            slave_kernel=_slave_kernel_stub(),
            slave_settings=MagicMock(),
        )
        assert result is not None
        assert result.register_test == "disproportionate"


class TestTheLegitimateVerdictIsRecordedNotDropped:
    """'It is recorded, not dropped' — the named outcome reaches the state
    through the phase output, and the model result carries the branch record
    (the shape that actually reaches the state writer)."""

    def test_the_model_result_carries_the_branch_record(self):
        from argumentation_analysis.plugins.identification_models import (
            FallacyAnalysisResult,
        )

        result = FallacyAnalysisResult(
            branch_outcomes=[
                {
                    "start_pk": "22",
                    "action": "legitimate_in_register",
                    "reason": _PROPORTIONATE_JUSTIFICATION,
                }
            ]
        )
        assert result.model_dump()["branch_outcomes"][0]["action"] == (
            "legitimate_in_register"
        )

    def test_the_state_trace_names_the_legitimate_verdict(self):
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState
        from argumentation_analysis.orchestration.state_writers import (
            _write_hierarchical_fallacy_to_state,
        )

        state = UnifiedAnalysisState("un texte quelconque")
        _write_hierarchical_fallacy_to_state(
            {
                "fallacies": [],
                "branch_outcomes": [
                    {
                        "start_pk": "22",
                        "action": "legitimate_in_register",
                        "reason": _PROPORTIONATE_JUSTIFICATION,
                    }
                ],
            },
            state,
            {},
        )
        summaries = [entry.get("summary", "") for entry in state.analysis_trace]
        assert any("REGISTRE LÉGITIME" in summary for summary in summaries), summaries
        # And the refusal-like action names are NOT what carries it: a plain
        # 'refused' branch leaves no such trace.
        state2 = UnifiedAnalysisState("un texte quelconque")
        _write_hierarchical_fallacy_to_state(
            {
                "fallacies": [],
                "branch_outcomes": [{"action": "refused", "reason": "x"}],
            },
            state2,
            {},
        )
        assert not any(
            "REGISTRE LÉGITIME" in entry.get("summary", "")
            for entry in state2.analysis_trace
        )


class TestTheSynthesisCarriesTheCounterReading:
    """Ask 3 — no strategy through bare flags: a register-family line carries
    the test that stands it, or names the test as unrecorded."""

    def test_the_line_carries_the_test_that_stands_the_flag(self):
        briefing = DeepSynthesisAgent.build_artifact_briefing(
            _state(
                fallacies={
                    "fallacy_1": _fallacy_record(register_test="disproportionate")
                }
            )
        )
        assert "REGISTRE : l'appel dépasse ce que le texte énonce" in briefing

    def test_the_line_names_an_unrecorded_test(self):
        briefing = DeepSynthesisAgent.build_artifact_briefing(
            _state(fallacies={"fallacy_1": _fallacy_record()})
        )
        assert "REGISTRE : test de proportionnalité non enregistré" in briefing

    def test_a_non_family_flag_carries_no_register_clause(self):
        """Control, vert des deux côtés : le test n'est dû que là où la famille
        le porte — une ligne d'« Ad hominem » n'en reçoit pas."""
        briefing = DeepSynthesisAgent.build_artifact_briefing(
            _state(
                fallacies={
                    "fallacy_1": _fallacy_record(
                        type="Ad hominem", family="Erreur de raisonnement"
                    )
                }
            )
        )
        assert "REGISTRE" not in briefing


class TestThePromptsCarryTheTestAndTheSelfCorrection:
    """Ask 1 and ask 2 are instructions the classifier must receive: the test
    comes from the node's own conditions, and a self-correction is not a
    false implication of the wording it corrects. Witnessed on the messages
    the plugin actually sends, not on the source text."""

    @pytest.mark.asyncio
    async def test_the_descent_leaf_prompt_carries_both_readings(self):
        plugin = _plugin()
        plugin.llm_service.get_chat_message_contents = AsyncMock(
            return_value=_msg_with_items(
                _confirm_call("221", matches=True, register_test="disproportionate")
            )
        )
        await plugin._explore_single_branch(
            argument_text="Le texte agite une crainte sans citer un seul fait.",
            start_pk="221",
            slave_kernel=_slave_kernel_stub(),
            slave_settings=MagicMock(),
        )
        history = plugin.llm_service.get_chat_message_contents.call_args.kwargs[
            "chat_history"
        ]
        sent = " ".join(str(getattr(message, "content", "")) for message in history)
        assert "REGISTER TEST" in sent
        assert "SELF-CORRECTION" in sent
        assert "proportionate" in sent and "disproportionate" in sent
        # The anti-pendulum travels with the test: no reading can pass the
        # test by lowering every flag.
        assert "stays flagged, whoever the speaker" in sent

    @pytest.mark.asyncio
    async def test_the_descent_navigation_prompt_carries_both_readings(self):
        plugin = _plugin()
        plugin.llm_service.get_chat_message_contents = AsyncMock(
            return_value=_msg_with_items(
                _confirm_call("22", matches=True, register_test="disproportionate")
            )
        )
        await plugin._explore_single_branch(
            argument_text="Le texte agite une crainte sans citer un seul fait.",
            start_pk="2",  # a non-leaf: the navigation prompt runs
            slave_kernel=_slave_kernel_stub(),
            slave_settings=MagicMock(),
        )
        history = plugin.llm_service.get_chat_message_contents.call_args.kwargs[
            "chat_history"
        ]
        sent = " ".join(str(getattr(message, "content", "")) for message in history)
        assert "REGISTER TEST" in sent
        assert "SELF-CORRECTION" in sent
