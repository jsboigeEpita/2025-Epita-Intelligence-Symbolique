"""#2972 — the fallacy descent's verdict is a field, not prose.

The paid run of 06/10 stored 38 confirmed fallacies; reading their
justifications, **5 conclude against their own classification** (« ne
correspond pas », « pas réellement instancié ») — all at confidence 0.90 —
and 2 are weak admissions at 0.40. The model said no in prose while calling
``confirm_fallacy``, because the descent prompt instructed it to confirm
when no child matched better. No guard compared the two halves, and a regex
over the prose found only 4 of 5 plus a false positive — not a detector.

The fix is structural, per the issue's own design: the tool call carries an
explicit verdict (``matches``), the code obeys the field and never reads the
prose, and the prompt no longer offers "confirm for lack of a better child"
as an exit — ``conclude_no_fallacy`` / ``matches=false`` is the honest exit.
``confidence`` and ``problematic_quote`` become fields of the stored fallacy
(the writer folded the first into the justification and dropped the second;
measured before the move: **zero readers** of the ``[confidence:...]``
marker in the tree).

These witnesses are LOAD-BEARING per the #1097 lesson: the real plugin runs
with the LLM dependency mocked (scripted ``FunctionCallContent``), not a mock
of the classifier.

Privacy: synthetic taxonomy, invented filler, opaque ids. Deterministic: no
JVM, no LLM, no network.
"""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, create_autospec

import pytest
from semantic_kernel import Kernel
from semantic_kernel.contents import FunctionCallContent

from argumentation_analysis.plugins.exploration_plugin import ExplorationPlugin


def _taxonomy():
    """Two levels, enough for the MIN_CONFIRM_DEPTH gate to stay out of the
    way: the confirmed node sits at depth 4."""
    data = []
    for depth, path, pk, text_fr, desc in [
        (1, "4", "4", "Erreur de raisonnement", "root"),
        (2, "4.1", "41", "Causalité douteuse", "sub"),
        (3, "4.1.1", "411", "Pétition de principe", "sub"),
        (
            4,
            "4.1.1.1",
            "4111",
            "Argument circulaire",
            "Conclusion re-injected as premise, often via paraphrase.",
        ),
        (
            5,
            "4.1.1.1.1",
            "41111",
            "Cercle cartésien",
            "A narrow named variant the text does not instantiate.",
        ),
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


#: Paraphrases of the paid run's justifications — invented filler, NOT corpus
#: text; they carry the same *speech act* (the justification denies the
#: classification it accompanies).
_DENIAL_JUSTIFICATION = (
    "Le texte ne tire aucune conclusion argumentative de ce schéma : le "
    "nœud ne correspond pas réellement, ce n'est pas ce sophisme."
)
_AFFIRMING_JUSTIFICATION = (
    "La conclusion est réinjectée comme prémisse paraphrasée : le nœud "
    "nomme bien le sophisme que le texte exhibe."
)


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


def _confirm_call(node_pk, matches=None, justification=_AFFIRMING_JUSTIFICATION):
    """A scripted confirm call. ``matches=None`` omits the field entirely —
    the shape of every recorded cassette call (measured on the committed
    cassettes: exactly node_pk, confidence, justification)."""
    args = {"node_pk": node_pk, "justification": justification, "confidence": "high"}
    if matches is not None:
        args["matches"] = matches
    return FunctionCallContent(name="confirm_fallacy", arguments=json.dumps(args))


def _explore_call(node_pk):
    return FunctionCallContent(
        name="explore_branch", arguments=json.dumps({"node_pk": node_pk})
    )


class TestTheVerdictIsAField:
    """The tool exposes the channel the paid run lacked, and echoes the
    verdict back so no reader ever interprets prose."""

    def test_a_negative_verdict_is_not_a_confirmation(self):
        plugin = ExplorationPlugin.__new__(ExplorationPlugin)
        from argumentation_analysis.agents.utils.taxonomy_navigator import (
            TaxonomyNavigator,
        )

        plugin.taxonomy_navigator = TaxonomyNavigator(taxonomy_data=_taxonomy())
        plugin.language = "fr"
        plugin._alt_lang = "en"
        result = json.loads(
            plugin.confirm_fallacy(
                node_pk="4111",
                confidence="high",
                matches=False,
                justification=_DENIAL_JUSTIFICATION,
            )
        )
        assert result["confirmed"] is False
        assert result["matches"] is False
        assert result["reason"] == _DENIAL_JUSTIFICATION

    def test_a_positive_verdict_confirms_and_echoes_the_field(self):
        plugin = ExplorationPlugin.__new__(ExplorationPlugin)
        from argumentation_analysis.agents.utils.taxonomy_navigator import (
            TaxonomyNavigator,
        )

        plugin.taxonomy_navigator = TaxonomyNavigator(taxonomy_data=_taxonomy())
        plugin.language = "fr"
        plugin._alt_lang = "en"
        result = json.loads(
            plugin.confirm_fallacy(
                node_pk="4111",
                confidence="high",
                matches=True,
                justification=_AFFIRMING_JUSTIFICATION,
            )
        )
        assert result["confirmed"] is True
        assert result["matches"] is True

    def test_the_prose_is_never_read_for_the_verdict(self):
        """Design boundary, pinned: a denial-shaped justification with a
        POSITIVE verdict is confirmed, and an affirming justification with a
        NEGATIVE verdict is refused. The code must not grow a prose detector —
        the measured regex caught 4 of 5 and one false positive, which is why
        the channel exists instead."""
        plugin = ExplorationPlugin.__new__(ExplorationPlugin)
        from argumentation_analysis.agents.utils.taxonomy_navigator import (
            TaxonomyNavigator,
        )

        plugin.taxonomy_navigator = TaxonomyNavigator(taxonomy_data=_taxonomy())
        plugin.language = "fr"
        plugin._alt_lang = "en"
        denial_prose_positive_verdict = json.loads(
            plugin.confirm_fallacy(
                node_pk="4111",
                confidence="high",
                matches=True,
                justification=_DENIAL_JUSTIFICATION,
            )
        )
        affirming_prose_negative_verdict = json.loads(
            plugin.confirm_fallacy(
                node_pk="4111",
                confidence="high",
                matches=False,
                justification=_AFFIRMING_JUSTIFICATION,
            )
        )
        assert denial_prose_positive_verdict["confirmed"] is True
        assert affirming_prose_negative_verdict["confirmed"] is False


class TestTheDescentObeysTheVerdict:
    """The real decision logic, LLM dependency mocked (#1097)."""

    @pytest.mark.asyncio
    async def test_negative_verdict_stores_nothing(self):
        """The issue's witness: the model refuses the node AT the call —
        nothing is stored as confirmed."""
        plugin = _plugin()
        plugin.llm_service.get_chat_message_contents = AsyncMock(
            return_value=_msg_with_items(
                _confirm_call(
                    "4111", matches=False, justification=_DENIAL_JUSTIFICATION
                )
            )
        )
        result = await plugin._explore_single_branch(
            argument_text="X is true because Y, and Y holds since X is the case.",
            start_pk="4",
            slave_kernel=_slave_kernel_stub(),
            slave_settings=MagicMock(),
        )
        assert result is None, (
            "#2972: a confirm call whose verdict field says NO produced a "
            "stored fallacy — the prose denial was ignored twice."
        )

    @pytest.mark.asyncio
    async def test_positive_control_an_affirming_confirm_still_confirms(self):
        """Positive control (the issue's own): a genuine confirm is stored,
        with confidence as a field the reader can filter on."""
        plugin = _plugin()
        plugin.llm_service.get_chat_message_contents = AsyncMock(
            return_value=_msg_with_items(
                _confirm_call(
                    "4111", matches=True, justification=_AFFIRMING_JUSTIFICATION
                )
            )
        )
        result = await plugin._explore_single_branch(
            argument_text="X is true because Y, and Y holds since X is the case.",
            start_pk="4",
            slave_kernel=_slave_kernel_stub(),
            slave_settings=MagicMock(),
        )
        assert result is not None
        assert result.taxonomy_pk == "4111"
        assert result.confidence == 0.9  # 'high' per the #2746 contract

    @pytest.mark.asyncio
    async def test_a_refusal_ends_the_branch_it_is_not_an_order_to_keep_going(
        self,
    ):
        """A refusal in a batch decides the branch. Without the refusal
        branch the call would fall through the classifier, the paired
        explore_branch would advance the walk, and the descent would drill
        INTO a node the model just refused — one more LLM call spent on a
        branch that is already dead."""
        plugin = _plugin()
        plugin.llm_service.get_chat_message_contents = AsyncMock(
            return_value=_msg_with_items(
                _confirm_call(
                    "4111", matches=False, justification=_DENIAL_JUSTIFICATION
                ),
                _explore_call("41111"),
            )
        )
        result = await plugin._explore_single_branch(
            argument_text="X is true because Y, and Y holds since X is the case.",
            start_pk="4",
            slave_kernel=_slave_kernel_stub(),
            slave_settings=MagicMock(),
        )
        assert result is None
        assert plugin.llm_service.get_chat_message_contents.await_count == 1, (
            "the refusal did not end the branch: the descent kept calling "
            "the LLM after the model said no"
        )

    @pytest.mark.asyncio
    async def test_leaf_refusal_is_read_too(self):
        """The leaf confirmation path reads the same field: a leaf the model
        refuses is not confirmed, and the refusal is named in the log rather
        than falling through the loop into a silent abandonment."""
        plugin = _plugin()
        plugin.llm_service.get_chat_message_contents = AsyncMock(
            return_value=_msg_with_items(
                _confirm_call(
                    "41111", matches=False, justification=_DENIAL_JUSTIFICATION
                )
            )
        )
        result = await plugin._explore_single_branch(
            argument_text="X is true because Y, and Y holds since X is the case.",
            start_pk="41111",  # start AT the leaf
            slave_kernel=_slave_kernel_stub(),
            slave_settings=MagicMock(),
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_a_call_without_the_field_keeps_the_recorded_semantics(self):
        """Band witness: every committed cassette's confirm call carries
        exactly node_pk/confidence/justification (measured). The defaulted
        verdict keeps those replays running — an omitted field is the
        pre-#2972 semantics, and it is the PROMPT that makes answering
        mandatory."""
        plugin = _plugin()
        plugin.llm_service.get_chat_message_contents = AsyncMock(
            return_value=_msg_with_items(
                _confirm_call(
                    "4111", matches=None, justification=_AFFIRMING_JUSTIFICATION
                )
            )
        )
        result = await plugin._explore_single_branch(
            argument_text="X is true because Y, and Y holds since X is the case.",
            start_pk="4",
            slave_kernel=_slave_kernel_stub(),
            slave_settings=MagicMock(),
        )
        assert result is not None and result.taxonomy_pk == "4111"


class TestTheStoredFallacyCarriesFields:
    """confidence and problematic_quote are fields of the stored fallacy,
    written by the descent writer — not prose, not dropped."""

    def _write_and_read(self, fallacy):
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_hierarchical_fallacy_to_state,
        )

        state = UnifiedAnalysisState("Test text")
        _write_hierarchical_fallacy_to_state({"fallacies": [fallacy]}, state, {})
        return list(state.identified_fallacies.values())[0]

    def test_confidence_is_a_float_a_reader_can_filter_on(self):
        entry = self._write_and_read(
            {
                "fallacy_type": "Straw man",
                "explanation": "Misrepresents the position",
                "taxonomy_pk": "99",
                "confidence": 0.4,
                "navigation_trace": [],
                "problematic_quote": "they claim the opposite of what they said",
            }
        )
        assert entry["confidence"] == 0.4
        assert isinstance(entry["confidence"], float)
        assert "[confidence:" not in entry["justification"]

    def test_problematic_quote_survives_the_writer(self):
        entry = self._write_and_read(
            {
                "fallacy_type": "Straw man",
                "explanation": "Misrepresents the position",
                "taxonomy_pk": "99",
                "confidence": 0.9,
                "navigation_trace": [],
                "problematic_quote": "they claim the opposite of what they said",
            }
        )
        assert entry["problematic_quote"] == "they claim the opposite of what they said"

    def test_absent_confidence_is_absent_not_zero(self):
        """Honest absence (#1019): a fallacy recorded without a confidence
        carries no confidence field — it must not read as a measured 0.0,
        which a filter would treat as the weakest possible detection."""
        entry = self._write_and_read(
            {
                "fallacy_type": "Straw man",
                "explanation": "Misrepresents the position",
                "taxonomy_pk": "99",
                "navigation_trace": [],
            }
        )
        assert "confidence" not in entry

    def test_the_csv_export_reads_the_new_field_without_knowing_it(self):
        """A real reader, already in the tree: the CSV bundle flattens state
        entries generically, so the new fields flow into fallacies.csv —
        the field is not declared into a void."""
        import csv as _csv
        import tempfile
        from pathlib import Path

        from argumentation_analysis.core.shared_state import UnifiedAnalysisState
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_hierarchical_fallacy_to_state,
        )
        from argumentation_analysis.reporting.multi_format_exporter import (
            MultiFormatExporter,
        )

        state = UnifiedAnalysisState("Test text")
        state.add_argument("arg_1", "a claim")
        _write_hierarchical_fallacy_to_state(
            {
                "fallacies": [
                    {
                        "fallacy_type": "Straw man",
                        "explanation": "Misrepresents the position",
                        "taxonomy_pk": "99",
                        "confidence": 0.4,
                        "navigation_trace": [],
                        "problematic_quote": "they claim the opposite of what they said",
                        "target_argument_id": "arg_1",
                    }
                ]
            },
            state,
            {},
        )
        exporter = MultiFormatExporter(state)
        with tempfile.TemporaryDirectory() as tmp:
            written = exporter.to_csv_bundle(Path(tmp))
            fallacies_csv = [p for p in written if p.name == "fallacies.csv"]
            assert fallacies_csv, f"no fallacies.csv among {[p.name for p in written]}"
            with open(fallacies_csv[0], encoding="utf-8") as fh:
                rows = list(_csv.DictReader(fh))
        assert rows and rows[0].get("confidence") == "0.4"
        assert rows[0].get("problematic_quote") == (
            "they claim the opposite of what they said"
        )


class TestThePromptNoLongerPushesConfirmation:
    """DoD 3: the descent prompt stops instructing 'confirm when no child
    matches' as a default, and names the honest exit."""

    def test_source_drops_the_confirm_for_lack_of_a_better_child_rule(self):
        import inspect

        from argumentation_analysis.plugins.fallacy_workflow_plugin import (
            FallacyWorkflowPlugin,
        )

        src = inspect.getsource(FallacyWorkflowPlugin)
        assert "NO child matches even partially" not in src, (
            "#2972: the descent prompt still tells the model to confirm when "
            "no child matches — the very instruction that manufactured "
            "confirmations the justification denied"
        )

    def test_source_names_the_negative_verdict_as_the_honest_exit(self):
        import inspect

        from argumentation_analysis.plugins.fallacy_workflow_plugin import (
            FallacyWorkflowPlugin,
        )

        src = inspect.getsource(FallacyWorkflowPlugin)
        assert (
            "matches=false" in src
            and "Never pass matches=true to avoid returning nothing" in src
        )
