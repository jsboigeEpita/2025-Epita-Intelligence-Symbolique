"""#3416 — an attribution the document itself refutes is not confirmed.

Cycle 1 of the v1 panel measured the M2 defect: a fallacy attribution lands
on a unit the document has ALREADY qualified — the speaker concedes two
sentences later the very limitation the attribution reads as missing, and
the descent, which only ever sees the extracted unit, confirms a circular
reasoning or hasty generalisation the document refutes in its own words.

The fix is evidence, not a new rule: before confirming a guarded family the
descent is shown what the DOCUMENT says about the claim (a concession the
first reading recorded, overlapping or immediately after the unit) and, when
that statement refutes the attribution, refuses it WITH the citation.

Anti-pendulum, pinned here as controls: no global threshold moves, no family
outside the guarded set is asked anything new, and a document that says
nothing about the claim leaves every prompt byte-identical — the attribution
then stands on the text as before.

Privacy: invented filler, opaque ids, no corpus text. Deterministic: no JVM,
no LLM, no network.
"""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, create_autospec

import pytest
from semantic_kernel import Kernel
from semantic_kernel.contents import FunctionCallContent

from argumentation_analysis.agents.core.reading.first_reading import (
    DOCUMENT_STATEMENT_AFTER_UNIT,
    document_statements_for_unit,
)
from argumentation_analysis.core.fallacy_attribution import (
    is_document_guarded_family,
    normalize_document_statement,
)
from argumentation_analysis.plugins.exploration_plugin import ExplorationPlugin


# --- fixtures ---------------------------------------------------------------

#: The unit the descent reads: a claim, no caveat inside it.
UNIT_TEXT = "La mesure est juste et nous la maintenons."

#: What the DOCUMENT says two sentences later — invented filler, the shape of
#: the August method's concession: the speaker qualifies the claim herself.
CONCESSION_TEXT = (
    "Nous concédons toutefois que la mesure n'a pas été évaluée sur ce point."
)

_GUARDED_LEAF_PK = "411"
_PLAIN_LEAF_PK = "421"


def _taxonomy():
    """Two leaves: one in the guarded families, one deliberately outside."""
    rows = [
        (1, "4", "4", "Erreur de raisonnement", "root"),
        (2, "4.1", "41", "Insuffisance", "sub"),
        (
            3,
            "4.1.1",
            _GUARDED_LEAF_PK,
            "Argument circulaire",
            "La conclusion est réinjectée comme prémisse.",
        ),
        (2, "4.2", "42", "Pertinence", "sub"),
        (
            3,
            "4.2.1",
            _PLAIN_LEAF_PK,
            "Appel à l'autorité",
            "Une autorité tient lieu de preuve.",
        ),
    ]
    data = []
    for depth, path, pk, text_fr, desc in rows:
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


def _state(moves):
    return SimpleNamespace(defining_moves={"status": "completed", "moves": list(moves)})


def _concession(quote=CONCESSION_TEXT, offset=0, kind="concession"):
    return {
        "kind": kind,
        "reading": "le locuteur concède une limite",
        "quote": quote,
        "offset": offset,
        "basis": "first_reading",
    }


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


def _confirm_call(node_pk, matches=True, justification="", **extra):
    args = {
        "node_pk": node_pk,
        "justification": justification,
        "confidence": "high",
        "matches": matches,
    }
    args.update(extra)
    return FunctionCallContent(name="confirm_fallacy", arguments=json.dumps(args))


def _install_llm(plugin, *items):
    """Script the descent's LLM and SNAPSHOT every prompt at call time.

    The descent keeps mutating the same ``ChatHistory`` after the call (the
    tool results land in it), so reading ``call_args`` afterwards returns the
    tail of the conversation, not the prompt the model was shown.
    """
    seen = []

    async def _call(chat_history=None, settings=None, kernel=None, **kwargs):
        seen.append([m.content or "" for m in chat_history.messages])
        return _msg_with_items(*items)

    plugin.llm_service.get_chat_message_contents = _call
    return seen


def _last_prompt(seen):
    return seen[-1][-1]


# --- ask 2, the producer ----------------------------------------------------


class TestTheDocumentStatementsAreLocated:
    """The producer hands over the document's words, and nothing it cannot place."""

    def test_a_concession_overlapping_the_unit_is_carried(self):
        state = _state([_concession(offset=5)])
        statements = document_statements_for_unit(
            state, unit_text=UNIT_TEXT, offset=0
        )
        assert [s["relation"] for s in statements] == ["overlap"]
        assert statements[0]["quote"] == CONCESSION_TEXT
        assert statements[0]["source"] == "first_reading_concession"

    def test_a_concession_right_after_the_unit_is_carried(self):
        """The August method's case: the speaker concedes in the NEXT
        sentence — just past the unit's end, still about the claim."""
        state = _state([_concession(offset=len(UNIT_TEXT) + 12)])
        statements = document_statements_for_unit(
            state, unit_text=UNIT_TEXT, offset=0
        )
        assert [s["relation"] for s in statements] == ["adjacent"]

    def test_a_concession_too_far_away_is_not_about_this_claim(self):
        state = _state(
            [_concession(offset=len(UNIT_TEXT) + DOCUMENT_STATEMENT_AFTER_UNIT + 1)]
        )
        assert document_statements_for_unit(state, unit_text=UNIT_TEXT, offset=0) == []

    def test_moves_that_are_not_concessions_are_not_carried(self):
        """Only a concession says what the document grants about the claim;
        a thesis or a refutation would be someone else's words about
        something else."""
        state = _state([_concession(offset=0, kind="thesis")])
        assert document_statements_for_unit(state, unit_text=UNIT_TEXT, offset=0) == []

    def test_no_geometry_means_no_statement(self):
        """A citation that cannot be placed is not evidence about this claim
        (the same rule as ``defining_move_spans``)."""
        state = _state([_concession(offset=None)])
        assert document_statements_for_unit(state, unit_text=UNIT_TEXT, offset=0) == []
        assert (
            document_statements_for_unit(
                _state([_concession(offset=0)]), unit_text=UNIT_TEXT, offset=None
            )
            == []
        )


class TestTheGuardedSetIsClosed:
    """The predicate names the two families, never a whole branch."""

    @pytest.mark.parametrize(
        "name",
        [
            "Argument circulaire",
            "Définition circulaire",
            "Référencement circulaire",
            "Généralisation hâtive",
            "Généralisation abusive",
            "Généralisation excessive",
            "Conclusion hâtive",
        ],
    )
    def test_the_guarded_names_are_recognised(self, name):
        assert is_document_guarded_family(name) is True

    @pytest.mark.parametrize(
        "name",
        [
            "Appel à l'autorité",
            "Homme de paille",
            "Insuffisance",
            "",
            None,
        ],
    )
    def test_a_node_outside_the_set_is_never_asked(self, name):
        assert is_document_guarded_family(name) is False

    def test_an_absent_citation_is_absence_not_an_empty_citation(self):
        assert normalize_document_statement("   ") == ""
        assert normalize_document_statement(None) == ""
        assert normalize_document_statement(CONCESSION_TEXT) == CONCESSION_TEXT


# --- ask 2, the descent -----------------------------------------------------


class TestTheDescentReadsTheDocument:
    """The real descent, LLM dependency mocked (#1097)."""

    @pytest.mark.asyncio
    async def test_the_guarded_leaf_hears_the_document_and_the_caveat(self):
        plugin = _plugin()
        seen = _install_llm(plugin, _confirm_call(_GUARDED_LEAF_PK))
        await plugin._explore_single_branch(
            argument_text=UNIT_TEXT,
            start_pk=_GUARDED_LEAF_PK,
            slave_kernel=_slave_kernel_stub(),
            slave_settings=MagicMock(),
            document_statements=[{"quote": CONCESSION_TEXT}],
        )
        prompt = _last_prompt(seen)
        assert CONCESSION_TEXT in prompt
        assert "THE DOCUMENT ITSELF SAYS" in prompt
        assert "DOCUMENT CAVEAT" in prompt
        assert "document_statement" in prompt

    @pytest.mark.asyncio
    async def test_a_cited_concession_refutes_the_attribution(self):
        """The issue's witness: the document's own words settle the question,
        the attribution is refused, and the CITATION travels with the outcome
        so the report can show what refuted it."""
        plugin = _plugin()
        plugin.llm_service.get_chat_message_contents = AsyncMock(
            return_value=_msg_with_items(
                _confirm_call(
                    _GUARDED_LEAF_PK,
                    matches=False,
                    justification="le document énonce lui-même cette limite",
                    document_statement=CONCESSION_TEXT,
                )
            )
        )
        outcomes = []
        result = await plugin._explore_single_branch(
            argument_text=UNIT_TEXT,
            start_pk=_GUARDED_LEAF_PK,
            slave_kernel=_slave_kernel_stub(),
            slave_settings=MagicMock(),
            document_statements=[{"quote": CONCESSION_TEXT}],
            outcomes=outcomes,
        )
        assert result is None
        assert outcomes[-1]["action"] == "refuted_by_document"
        assert outcomes[-1]["document_statement"] == CONCESSION_TEXT

    @pytest.mark.asyncio
    async def test_a_refusal_without_a_citation_is_still_just_a_refusal(self):
        """An absent citation is not a refutation: the branch keeps the
        historical outcome, and nothing is invented to fill the field."""
        plugin = _plugin()
        plugin.llm_service.get_chat_message_contents = AsyncMock(
            return_value=_msg_with_items(
                _confirm_call(
                    _GUARDED_LEAF_PK,
                    matches=False,
                    justification="ce n'est pas ce sophisme",
                )
            )
        )
        outcomes = []
        await plugin._explore_single_branch(
            argument_text=UNIT_TEXT,
            start_pk=_GUARDED_LEAF_PK,
            slave_kernel=_slave_kernel_stub(),
            slave_settings=MagicMock(),
            document_statements=[{"quote": CONCESSION_TEXT}],
            outcomes=outcomes,
        )
        assert outcomes[-1]["action"] == "refused"
        assert "document_statement" not in outcomes[-1]

    @pytest.mark.asyncio
    async def test_a_document_that_says_nothing_keeps_the_attribution(self):
        """Anti-pendulum control: with a statement carried, a guarded node the
        document does NOT refute is confirmed exactly as before — the caveat
        is a question, not a veto."""
        plugin = _plugin()
        plugin.llm_service.get_chat_message_contents = AsyncMock(
            return_value=_msg_with_items(
                _confirm_call(
                    _GUARDED_LEAF_PK,
                    matches=True,
                    justification="la prémisse présuppose la conclusion",
                )
            )
        )
        result = await plugin._explore_single_branch(
            argument_text=UNIT_TEXT,
            start_pk=_GUARDED_LEAF_PK,
            slave_kernel=_slave_kernel_stub(),
            slave_settings=MagicMock(),
            document_statements=[{"quote": "Nous n'avons pas d'autre élément."}],
        )
        assert result is not None and result.taxonomy_pk == _GUARDED_LEAF_PK

    @pytest.mark.asyncio
    async def test_a_node_outside_the_guarded_families_is_not_asked(self):
        """Scope control: the same document statements reach the prompt, but a
        node outside the two families carries no caveat — the guard does not
        spread to the tree (anti-pendulum)."""
        plugin = _plugin()
        seen = _install_llm(plugin, _confirm_call(_PLAIN_LEAF_PK))
        result = await plugin._explore_single_branch(
            argument_text=UNIT_TEXT,
            start_pk=_PLAIN_LEAF_PK,
            slave_kernel=_slave_kernel_stub(),
            slave_settings=MagicMock(),
            document_statements=[{"quote": CONCESSION_TEXT}],
        )
        prompt = _last_prompt(seen)
        assert "THE DOCUMENT ITSELF SAYS" in prompt
        assert "DOCUMENT CAVEAT" not in prompt
        assert result is not None and result.taxonomy_pk == _PLAIN_LEAF_PK

    @pytest.mark.asyncio
    async def test_no_concession_leaves_the_prompt_byte_identical(self):
        """The DoD control, byte for byte: with nothing recorded, the leaf
        prompt is the pre-#3416 string — same prefix, no block, no caveat —
        and a call with an empty list is identical to a call with none."""
        captured = []
        for statements in (None, [], [{"quote": "   "}]):
            plugin = _plugin()
            seen = _install_llm(plugin, _confirm_call(_GUARDED_LEAF_PK))
            await plugin._explore_single_branch(
                argument_text=UNIT_TEXT,
                start_pk=_GUARDED_LEAF_PK,
                slave_kernel=_slave_kernel_stub(),
                slave_settings=MagicMock(),
                document_statements=statements,
            )
            captured.append(_last_prompt(seen))

        for prompt in captured:
            assert prompt.startswith(
                f'Text to analyze: "{UNIT_TEXT}"\n\n'
                "You reached a LEAF node in the fallacy taxonomy.\n"
            ), "the no-statement prompt no longer opens with the pre-#3416 text"
            assert "THE DOCUMENT ITSELF SAYS" not in prompt
            assert "DOCUMENT CAVEAT" not in prompt
        assert captured[0] == captured[1] == captured[2], (
            "an empty or blank statement list changed the prompt — absence "
            "must be byte-identical to no argument at all"
        )

    @pytest.mark.asyncio
    async def test_a_citation_without_a_statement_carried_settles_nothing(self):
        """A model that volunteers a citation when no statement was carried is
        not a refutation read from the document: without the evidence in front
        of it there is nothing to have read, and the record stays unchanged."""
        plugin = _plugin()
        plugin.llm_service.get_chat_message_contents = AsyncMock(
            return_value=_msg_with_items(
                _confirm_call(
                    _GUARDED_LEAF_PK,
                    matches=False,
                    justification="refusé",
                    document_statement=CONCESSION_TEXT,
                )
            )
        )
        outcomes = []
        await plugin._explore_single_branch(
            argument_text=UNIT_TEXT,
            start_pk=_GUARDED_LEAF_PK,
            slave_kernel=_slave_kernel_stub(),
            slave_settings=MagicMock(),
            outcomes=outcomes,
        )
        assert outcomes[-1]["action"] == "refused"
        assert "document_statement" not in outcomes[-1]


# --- ask 2, the tool --------------------------------------------------------


class TestTheToolCarriesTheCitation:
    """The citation rides the REFUSAL only: a confirmed attribution has
    nothing to cite, and carrying it there would contradict the verdict."""

    def _tool(self):
        from argumentation_analysis.agents.utils.taxonomy_navigator import (
            TaxonomyNavigator,
        )

        plugin = ExplorationPlugin.__new__(ExplorationPlugin)
        plugin.taxonomy_navigator = TaxonomyNavigator(taxonomy_data=_taxonomy())
        plugin.language = "fr"
        plugin._alt_lang = "en"
        return plugin

    def test_a_refusal_echoes_the_document_statement(self):
        result = json.loads(
            self._tool().confirm_fallacy(
                node_pk=_GUARDED_LEAF_PK,
                confidence="high",
                matches=False,
                justification="le document concède cette limite",
                document_statement=CONCESSION_TEXT,
            )
        )
        assert result["confirmed"] is False
        assert result["document_statement"] == CONCESSION_TEXT

    def test_a_confirmation_does_not_carry_it(self):
        result = json.loads(
            self._tool().confirm_fallacy(
                node_pk=_GUARDED_LEAF_PK,
                confidence="high",
                matches=True,
                justification="la prémisse présuppose la conclusion",
                document_statement=CONCESSION_TEXT,
            )
        )
        assert result["confirmed"] is True
        assert "document_statement" not in result

    def test_a_blank_citation_is_absence(self):
        result = json.loads(
            self._tool().confirm_fallacy(
                node_pk=_GUARDED_LEAF_PK,
                matches=False,
                justification="refusé",
                document_statement="   ",
            )
        )
        assert "document_statement" not in result


# --- ask 2, the fallback ----------------------------------------------------


class TestTheOneShotFallbackReadsItToo:
    """The same document must not get a different contract because the
    descent timed out."""

    def _reply(self, **fields):
        payload = {
            "fallacy_name": "Argument circulaire",
            "taxonomy_pk": _GUARDED_LEAF_PK,
            "explanation": "la conclusion revient comme prémisse",
            "confidence": 0.6,
        }
        payload.update(fields)
        return json.dumps(payload, ensure_ascii=False)

    @pytest.mark.asyncio
    async def test_a_cited_concession_refutes_the_chosen_fallacy(self):
        plugin = _plugin()
        plugin.llm_service.get_chat_message_content = AsyncMock(
            return_value=self._reply(
                document_statement=CONCESSION_TEXT,
                explanation="le document énonce lui-même la limite",
            )
        )
        result = json.loads(
            await plugin._run_one_shot(
                UNIT_TEXT, [{"quote": CONCESSION_TEXT}]
            )
        )
        assert result["fallacies"] == []
        assert result["exploration_method"] == "one_shot_refuted_by_document"
        assert result["document_statement"] == CONCESSION_TEXT

    @pytest.mark.asyncio
    async def test_without_a_statement_the_prompt_and_the_result_are_untouched(self):
        captured = []
        for statements in (None, []):
            plugin = _plugin()
            plugin.llm_service.get_chat_message_content = AsyncMock(
                return_value=self._reply(
                    document_statement=CONCESSION_TEXT,
                )
            )
            result = json.loads(await plugin._run_one_shot(UNIT_TEXT, statements))
            assert len(result["fallacies"]) == 1, (
                "a citation volunteered with no statement carried refuted a "
                "detection it could not have read"
            )
            captured.append(
                plugin.llm_service.get_chat_message_content.call_args.kwargs[
                    "chat_history"
                ].messages[-1].content
            )
        assert captured[0] == captured[1]
        assert "THE DOCUMENT ITSELF SAYS" not in captured[0]
        assert "DOCUMENT CAVEAT" not in captured[0]
        assert "document_statement" not in captured[0]
