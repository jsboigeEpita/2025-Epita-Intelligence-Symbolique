"""#3545 (U3) — the FOL phase asks entailment, not only consistency.

Measured on the recorded cycle-6 panel (10 documents): 18 ``fol_analysis_results``
entries, **0** items in ``inferences``, and 0 acts matching the consequence
motifs. The phase produced a consistency verdict and returned the empty
``inferences`` list #1631 left as a placeholder ("Tweety can do deduction;
wiring it is a separate question").

The wiring this witness guards:

* one conclusion query per MARKED argument unit — the unit text splits at the
  last sentence-initial conclusion marker ("So ", "Donc ", …), a closed list;
* the KB is that unit's STATED premises only (ask 3): the spans come from the
  unit's own text, and the historian's note never adds a premise — when the
  note was in the translation context the record says so (``minted_under``,
  ask 2, #3377);
* the query is answered through ``FOLHandler.execute_fol_query`` ->
  ``_in_jvm_entailment`` (#2502): tri-state, and ``None`` never reads as
  "not entailed" (#2447);
* the verdict lands in ``inferences`` with the unit ids it concerns (ask 5);
* one reader turns a record into a sentence (ask 6) — nothing for no verdict.

Planted texts (ask 1, invented content, tests only — no corpus document):

* **valid:** "Every licensed pilot passed the medical. Dana is a licensed
  pilot. So Dana passed the medical." — the premises entail the conclusion;
* **suppressed premise:** "Every licensed pilot passed the medical. Dana
  flies the night route. So Dana passed the medical." — they do not.

Born red on ``main``: ``inferences`` is the empty list there for both
arguments. The positive control (consistency verdict present) is green on
``main``, so the witness sees the record it extends.
"""

import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.orchestration.invoke_callables import (
    _invoke_fol_reasoning,
)
from argumentation_analysis.orchestration.selection import SelectableUnit


def _helper():
    """Lazy: the helper does not exist on ``main`` — the positive control
    must still import and run green there (it guards the record the wiring
    extends, not the wiring)."""
    from argumentation_analysis.orchestration.invoke_callables import (
        _fol_entailment_inferences,
    )

    return _fol_entailment_inferences


# ── Planted arguments (ask 1) ────────────────────────────────────────────────

_ARG_VALID = (
    "Every licensed pilot passed the medical. Dana is a licensed pilot. "
    "So Dana passed the medical."
)
_ARG_SUPPRESSED = (
    "Every licensed pilot passed the medical. Dana flies the night route. "
    "So Dana passed the medical."
)

_VALID_SPAN = "Every licensed pilot passed the medical. Dana is a licensed pilot."
_SUPPRESSED_SPAN = (
    "Every licensed pilot passed the medical. Dana flies the night route."
)
_CONCLUSION_SPAN = "Dana passed the medical."

# Tweety FOL: variables are UPPERCASE-starting (lowercase = constant).
_RULE = "forall X: (LicensedPilot(X) => PassedMedical(X))"
_VALID_PREMISES = f"{_RULE}; LicensedPilot(dana)"
_SUPPRESSED_PREMISES = f"{_RULE}; FliesNightRoute(dana)"
_CONCLUSION = "PassedMedical(dana)"

#: One reply table serves every consumer of the patched translator: the
#: premise/conclusion SPANS (what the query minting asks) and the FULL unit
#: texts (what the phase's NL fallback arm asks). Keys are whitespace-folded.
_REPLIES = {
    " ".join(_VALID_SPAN.split()): _VALID_PREMISES,
    " ".join(_SUPPRESSED_SPAN.split()): _SUPPRESSED_PREMISES,
    " ".join(_CONCLUSION_SPAN.split()): _CONCLUSION,
    " ".join(_ARG_VALID.split()): _VALID_PREMISES,
    " ".join(_ARG_SUPPRESSED.split()): _SUPPRESSED_PREMISES,
}


def _fold(text: str) -> str:
    return " ".join(str(text).split())


def _fake_translator_factory(extra_replies=None):
    """A ``NLToLogicTranslator`` double: every asked text gets its formula."""

    class _FakeBatch:
        def __init__(self, translations):
            self.translations = translations

    replies = dict(_REPLIES)
    if extra_replies:
        replies.update({_fold(k): v for k, v in extra_replies.items()})

    def _factory(*_args, **_kwargs):
        translator = MagicMock()

        async def _translate_batch(texts, **_kwargs):
            items = []
            for text in texts:
                formula = replies.get(_fold(text), "")
                items.append(
                    SimpleNamespace(
                        original_text=str(text),
                        formula=formula,
                        is_valid=bool(formula),
                        validation_message="",
                    )
                )
            return _FakeBatch(items)

        translator.translate_batch = _translate_batch
        translator.translate = AsyncMock(
            return_value=SimpleNamespace(
                formula="", is_valid=False, validation_message="unused"
            )
        )
        return translator

    return _factory


def _planted_state() -> UnifiedAnalysisState:
    """Two identified argument units: the planted pair, in document order."""
    raw = f"{_ARG_VALID} {_ARG_SUPPRESSED}"
    state = UnifiedAnalysisState(raw)
    state.identified_arguments = {"arg_1": _ARG_VALID, "arg_2": _ARG_SUPPRESSED}
    state.argument_provenance = {
        "arg_1": {"producer": "extract", "offset": 0},
        "arg_2": {"producer": "extract", "offset": len(_ARG_VALID) + 1},
    }
    return state


def _context(state: UnifiedAnalysisState) -> dict:
    return {
        "_state_object": state,
        "source_metadata": {"opaque_id": "corpus_witness"},
        "phase_extract_output": {
            "arguments": [{"text": _ARG_VALID}, {"text": _ARG_SUPPRESSED}]
        },
    }


#: Hermetic on every seat: the 2-pass arm's client is forced absent, so the
#: phase's own NL fallback (patched translator) is the only producer.
_PATCH_CLIENT = (
    "argumentation_analysis.orchestration.invoke_callables._get_openai_client"
)


# ── The witness: red on main, green on the branch ────────────────────────────


def _jpype_is_mocked() -> bool:
    return isinstance(sys.modules.get("jpype"), MagicMock)


@pytest.fixture
def require_real_jvm():
    """The real-Tweety half needs the JVM the CI provisions (portable JDK)."""
    if _jpype_is_mocked():
        pytest.skip(
            "jpype is mocked (--disable-jvm-session); the fake-solver test "
            "below covers the wiring without a JVM."
        )


async def _run_phase(extra_replies=None):
    state = _planted_state()
    with patch(
        "argumentation_analysis.services.nl_to_logic.NLToLogicTranslator",
        _fake_translator_factory(extra_replies),
    ), patch(_PATCH_CLIENT, return_value=(None, "")):
        return await _invoke_fol_reasoning(
            f"{_ARG_VALID} {_ARG_SUPPRESSED}", _context(state)
        )


def _records_by_unit(result: dict) -> dict:
    records = result.get("inferences") or []
    assert all(
        isinstance(r, dict) for r in records
    ), "inferences carries #3545 records (dicts), not bare strings"
    by_unit: dict = {}
    for record in records:
        for unit_id in record.get("unit_ids", []):
            by_unit[unit_id] = record
    return by_unit


async def test_the_two_planted_arguments_get_a_verdict(require_real_jvm):
    """Valid → entailed; suppressed premise → not entailed (red on main)."""
    result = await _run_phase()
    by_unit = _records_by_unit(result)
    assert "arg_1" in by_unit, "the valid argument produced no inference record"
    assert by_unit["arg_1"]["verdict"] == "entailed"
    assert "arg_2" in by_unit, "the suppressed-premise argument produced no record"
    assert by_unit["arg_2"]["verdict"] == "not_entailed"


async def test_positive_control_the_consistency_verdict_is_present(require_real_jvm):
    """Green on ``main``: the record the wiring extends is really produced."""
    result = await _run_phase()
    assert result.get("consistent") is not None or isinstance(
        result.get("fol_status"), str
    ), "the consistency verdict the wiring extends is absent"


async def test_negated_query_flips_the_verdict(require_real_jvm):
    """Mutation control: the conclusion negated flips both verdicts."""
    result = await _run_phase(extra_replies={_CONCLUSION_SPAN: f"!{_CONCLUSION}"})
    by_unit = _records_by_unit(result)
    assert (
        by_unit["arg_1"]["verdict"] == "not_entailed"
    ), "the valid KB does not entail the negated conclusion"
    assert by_unit["arg_2"]["verdict"] == "not_entailed"


# ── Second test: a fake solver covers the wiring without a JVM ───────────────


class _FakeSolver:
    """Answers from the KB's own content: licensed-pilot premises entail."""

    def __init__(self):
        self.calls: list = []

    def execute_fol_query(self, belief_set, query):
        self.calls.append((str(belief_set), str(query)))
        kb = str(belief_set)
        if "LicensedPilot" in kb and "FliesNightRoute" not in kb:
            return True, "fake solver: entailed"
        return False, "fake solver: not entailed"


class _FakeBridge:
    """Stands in for TweetyBridge on a JVM-less seat."""

    def __init__(self, solver):
        self._solver = solver
        self.initializer = MagicMock()

    @property
    def fol_handler(self):
        return self._solver

    def check_consistency(self, _belief_set, _logic_type):
        return True, "fake bridge: consistent"


async def test_fake_solver_covers_the_wiring_without_a_jvm():
    solver = _FakeSolver()
    state = _planted_state()
    with patch(
        "argumentation_analysis.services.nl_to_logic.NLToLogicTranslator",
        _fake_translator_factory(),
    ), patch(_PATCH_CLIENT, return_value=(None, "")), patch(
        "argumentation_analysis.agents.core.logic.tweety_bridge.TweetyBridge",
        lambda *a, **k: _FakeBridge(solver),
    ):
        result = await _invoke_fol_reasoning(
            f"{_ARG_VALID} {_ARG_SUPPRESSED}", _context(state)
        )
    by_unit = _records_by_unit(result)
    assert by_unit["arg_1"]["verdict"] == "entailed"
    assert by_unit["arg_2"]["verdict"] == "not_entailed"
    assert solver.calls, "the solver was never reached"
    queried = {query for _kb, query in solver.calls}
    assert _CONCLUSION in queried, "the minted query is the conclusion formula"


# ── The record's honesty: labelling, absence, and the act sentence ───────────


class _RecordingHandler:
    def __init__(self, answer=True):
        self.answer = answer
        self.queries: list = []

    def execute_fol_query(self, belief_set, query):
        self.queries.append((str(belief_set), str(query)))
        return self.answer, "recording handler"


def _unit(unit_id: str, text: str) -> SelectableUnit:
    return SelectableUnit(unit_id=unit_id, text=text)


async def test_the_record_labels_what_the_premises_are():
    """Ask 2/3: stated spans, and the historian's note named when it was used."""
    handler = _RecordingHandler(answer=True)
    with patch(
        "argumentation_analysis.services.nl_to_logic.NLToLogicTranslator",
        _fake_translator_factory(),
    ):
        records = await _helper()(
            [_unit("arg_1", _ARG_VALID)],
            fol_handler=handler,
            situation_note="The historian supplies background.",
        )
    assert len(records) == 1
    record = records[0]
    assert record["unit_ids"] == ["arg_1"]
    assert record["premises"] == [_RULE, "LicensedPilot(dana)"]
    assert record["query"] == _CONCLUSION
    assert record["premise_texts_source"] == "stated"
    assert record["minted_under"] == "historian_note"
    assert record["verdict"] == "entailed"
    # The KB the solver saw carries the stated premises only — the note
    # itself never enters it.
    kb_seen = handler.queries[0][0]
    assert "historian" not in kb_seen and "LicensedPilot" in kb_seen


async def test_without_the_note_the_premises_are_stated_plain():
    handler = _RecordingHandler(answer=False)
    with patch(
        "argumentation_analysis.services.nl_to_logic.NLToLogicTranslator",
        _fake_translator_factory(),
    ):
        records = await _helper()(
            [_unit("arg_2", _ARG_SUPPRESSED)],
            fol_handler=handler,
            situation_note="",
        )
    assert records[0]["minted_under"] == "document_text"
    assert records[0]["verdict"] == "not_entailed"


async def test_a_unit_without_a_conclusion_marker_yields_no_record():
    handler = _RecordingHandler()
    with patch(
        "argumentation_analysis.services.nl_to_logic.NLToLogicTranslator",
        _fake_translator_factory(),
    ):
        records = await _helper()(
            [_unit("arg_9", "Dana flies at night. The route is long.")],
            fol_handler=handler,
        )
    assert records == []
    assert handler.queries == []


async def test_no_handler_records_no_verdict():
    with patch(
        "argumentation_analysis.services.nl_to_logic.NLToLogicTranslator",
        _fake_translator_factory(),
    ):
        records = await _helper()([_unit("arg_1", _ARG_VALID)])
    assert len(records) == 1
    assert records[0]["verdict"] == "no_verdict"


def test_the_act_sentence():
    """Ask 6: one reader, three answers — nothing for no verdict (#2447)."""
    from argumentation_analysis.reporting.restitution.formal_derivation import (
        fol_inference_sentence,
    )

    assert (
        fol_inference_sentence({"verdict": "not_entailed"})
        == "la conclusion ne s'ensuit pas des prémisses énoncées"
    )
    assert (
        fol_inference_sentence({"verdict": "entailed"})
        == "la conclusion s'ensuit des prémisses énoncées"
    )
    assert fol_inference_sentence({"verdict": "no_verdict"}) == ""
    assert fol_inference_sentence("not a dict") == ""
