"""#3136 — the logic sites credit their verdicts to the units, not the head.

The R1105 passes measured the defect on doc_A: the reading record told the
reader that the formal checks "covered 4 000 of the N characters", while the
formulas cited 10 units spread from arg_14 to arg_86 — a 4 000-char head
cannot have produced them. The head reading (pass 1) fixed the vocabulary
(signature / atom inventory); the formulas come from the stratified units
(pass 2), whose reading was never recorded. It is #3105's twin on the logic
axis.

The repair is provenance, not prose: each logic arm records its units reading
as its own site (units read + population + span), the head line says what the
head actually fixed, and the record credits the verdicts to the units line.
The PL wide-net pass, which fed on the same bounded head, says so to the
model (excerpt, not "the FULL text") and records the formulas it produced on
the head site instead of leaving them uncredited.

Counts and opaque ids only; synthetic states, fake model, no corpus text.
"""

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from argumentation_analysis.reporting.restitution.reading_record import (
    _site_fed,
    build_reading_record,
    format_reading_block,
)

_HEAD = 4000
_SOURCE = 90_000


def _state(window_status=None, fol_results=(), pl_results=()):
    state = SimpleNamespace()
    state.raw_text = "x" * _SOURCE
    state.reading_window_status = dict(window_status or {})
    state.fol_analysis_results = list(fol_results)
    state.propositional_analysis_results = list(pl_results)
    state.argument_provenance = {}
    return state


def _result(formulas, sources, verdict=False):
    """One solver entry: formulas aligned with the units they came from, plus
    the verdict every producer writes.

    #3149 — the units line counts DECIDED records only, so a record without a
    boolean verdict would read as a #2970 « not evaluated » one and its
    formulas would drop out of the count. Every producer writes the field
    (``None`` when it did not decide), and both axes write their own name; the
    fixture feeds both, so it carries both.
    """
    return {
        "satisfiable": verdict,
        "consistent": verdict,
        "formulas": list(formulas),
        "formula_sources": [list(s) for s in sources],
    }


def _head_entry(**extra):
    entry = {"status": "selected", "offset": 0, "window": _HEAD}
    entry.update(extra)
    return entry


def _units_entry(units=10, unit_total=91, span_lo=1200, span_hi=61_200):
    return {
        "status": "selected",
        "offset": span_lo,
        "window": span_hi - span_lo,
        "units": units,
        "unit_total": unit_total,
        "span_lo": span_lo,
        "span_hi": span_hi,
    }


class TestTheHeadStopsCreditingTheVerdicts:
    def test_the_fol_head_line_names_the_signature(self):
        state = _state(
            {"fol_reasoning": _head_entry()},
            fol_results=[_result(["P(a)", "Q(a)"], [["arg_14"], ["arg_86"]])],
        )
        fed = _site_fed("fol_reasoning", state)
        assert "signature" in fed
        assert "verdict" not in fed, (
            "the formulas cite units spread across the text; the head only "
            "fixed the vocabulary — crediting the verdicts here is the #3105 "
            "defect on the logic axis"
        )

    def test_the_pl_head_line_names_the_atom_inventory(self):
        state = _state(
            {"propositional_logic": _head_entry()},
            pl_results=[_result(["p => q"], [["arg_40"]])],
        )
        fed = _site_fed("propositional_logic", state)
        assert "atomes" in fed
        assert "verdict" not in fed

    def test_the_head_states_the_formulas_its_wide_pass_produced(self):
        """The PL wide-net pass reads the same head: when it produced
        formulas, the head line names them instead of under-crediting the
        read (anti-pendulum — a site credits its own share)."""
        state = _state({"propositional_logic": _head_entry(head_formulas=2)})
        fed = _site_fed("propositional_logic", state)
        assert "2 formule(s) de structure globale" in fed


class TestTheUnitsLineCreditsWhatItFed:
    def test_the_fol_units_line_counts_sourced_formulas_and_verdicts(self):
        state = _state(
            {"fol_reasoning_units": _units_entry()},
            fol_results=[_result(["A", "B", "C"], [["arg_14"], [], ["arg_86"]])],
        )
        fed = _site_fed("fol_reasoning_units", state)
        assert "2 formule(s) sur 3" in fed, (
            "only the formulas whose formula_sources name the units are the "
            "units line's share — the wide-pass/upstream ones are not"
        )
        assert "1 verdict(s)" in fed

    def test_the_pl_units_line_counts_sourced_formulas_and_verdicts(self):
        state = _state(
            {"propositional_logic_units": _units_entry()},
            pl_results=[_result(["p", "q"], [["arg_40"], ["arg_41"]])],
        )
        fed = _site_fed("propositional_logic_units", state)
        assert "2 formule(s) sur 2" in fed
        assert "1 verdict(s)" in fed


class TestTheRecordSpeaksBothReads:
    def test_the_fol_block_carries_the_head_line_and_the_units_line(self):
        state = _state(
            {
                "fol_reasoning": _head_entry(),
                "fol_reasoning_units": _units_entry(),
            },
            fol_results=[_result(["P(a)"], [["arg_40"]])],
        )
        block = format_reading_block(build_reading_record(state))
        assert "logique du premier ordre — lecture par unités" in block
        assert "10 unités sur 91" in block, (
            "the units reading says how many units it translated, out of how "
            "many exist"
        )
        assert (
            "0.01" in block and "0.68" in block
        ), "the span the units cover must be stated as fractions of the text"
        assert "signature FOL" in block

    def test_the_pl_block_carries_the_head_line_and_the_units_line(self):
        state = _state(
            {
                "propositional_logic": _head_entry(),
                "propositional_logic_units": _units_entry(),
            },
            pl_results=[_result(["p"], [["arg_40"]])],
        )
        block = format_reading_block(build_reading_record(state))
        assert "logique propositionnelle — lecture par unités" in block
        assert "10 unités sur 91" in block
        assert "atomes propositionnels" in block


class TestAHeadOnlySiteKeepsItsLine:
    def test_fact_extraction_keeps_its_single_head_line(self):
        """Positive control: a site that truly reads only a head keeps one
        line — the fix narrows the logic sites, it does not split every
        record entry in two."""
        state = _state(
            {"fact_extraction": {"status": "selected", "offset": 0, "window": 3000}}
        )
        block = format_reading_block(build_reading_record(state))
        lines = [line for line in block.splitlines() if "extraction des unités" in line]
        assert len(lines) == 1
        assert "3000 des 90000" in lines[0]
        assert "unités lues" not in lines[0]


class TestTheArmRecordsTheUnitsSite:
    def test_the_helper_records_the_units_and_the_span_from_offsets(self):
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState
        from argumentation_analysis.orchestration.invoke_callables import (
            _record_logic_units_reading,
        )
        from argumentation_analysis.orchestration.selection import (
            merged_population_units,
            select_for_budget,
            state_text_length,
        )

        raw = " ".join(
            f"Sentence {i} carries one unit of the corpus." for i in range(400)
        )
        state = UnifiedAnalysisState(raw)
        state.identified_arguments = {
            f"arg_{i}": f"unit text number {i}" for i in range(20)
        }
        span = len(raw) // 20
        state.argument_provenance = {
            arg_id: {"producer": "llm_extract", "offset": i * span}
            for i, arg_id in enumerate(state.identified_arguments)
        }
        units = merged_population_units(state)
        selection = select_for_budget(units, 10, text_length=state_text_length(state))
        _record_logic_units_reading(state, "fol_reasoning_units", selection)

        entry = state.reading_window_status["fol_reasoning_units"]
        assert entry["status"] == "selected"
        assert entry["units"] == selection.k == 10
        assert entry["unit_total"] == 20
        assert entry["span_lo"] == min(u.offset for u in selection.selected)
        assert entry["span_hi"] <= len(raw)


def _mock_response(payload):
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = json.dumps(payload)
    return response


def _populated_state():
    raw = " ".join(f"Sentence {i} of the corpus carries one unit." for i in range(40))
    from argumentation_analysis.core.shared_state import UnifiedAnalysisState

    state = UnifiedAnalysisState(raw)
    state.identified_arguments = {
        f"arg_{i}": f"population unit {i} anchored in the corpus" for i in range(12)
    }
    span = len(raw) // 12
    state.argument_provenance = {
        arg_id: {"producer": "llm_extract", "offset": i * span}
        for i, arg_id in enumerate(state.identified_arguments)
    }
    return state


def _fake_client(captured, wide_formula=None):
    """A model that answers by reading the prompt — no call-count coupling."""

    async def _create(**kwargs):
        prompt = kwargs.get("messages", [{}])[0].get("content", "")
        captured.append(prompt)
        if "atomic propositions" in prompt and "Allowed propositions" not in prompt:
            return _mock_response({"propositions": ["atom_present", "atom_anchor"]})
        if "formal logic expert" in prompt:
            return _mock_response(
                {
                    "sorts": {"Person": ["speaker_a"]},
                    "predicates": {"Mortal": ["Person"]},
                }
            )
        if "EXCERPT" in prompt or "FULL text" in prompt:
            return _mock_response({"formulas": [wide_formula] if wide_formula else []})
        return _mock_response({"formulas": []})

    client = AsyncMock()
    client.chat.completions.create = AsyncMock(side_effect=_create)
    return client


def _no_translations():
    async def _capture(self, texts, logic_type=None, check_consistency=False):
        return SimpleNamespace(translations=[])

    return _capture


class TestTheArmsRecordBothReads:
    def test_the_pl_arm_records_units_and_sends_an_excerpt_prompt(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_propositional_logic,
        )

        state = _populated_state()
        captured = []
        client = _fake_client(captured)
        with patch("openai.AsyncOpenAI", return_value=client), patch.dict(
            "os.environ", {"OPENAI_API_KEY": "test-key"}
        ), patch(
            "argumentation_analysis.services.nl_to_logic.NLToLogicTranslator.translate_batch",
            _no_translations(),
        ):
            asyncio.run(
                _invoke_propositional_logic(state.raw_text, {"_state_object": state})
            )

        entry = state.reading_window_status["propositional_logic_units"]
        assert (
            entry["units"] == state.analysis_coverage["propositional_logic"]["k"] == 10
        )
        assert entry["unit_total"] == len(state.identified_arguments)
        texts = " ".join(captured)
        assert "FULL text" not in texts, (
            "the wide-net pass feeds on the 4000-char reading window: a prompt "
            "that calls it 'the FULL text' lies to the model"
        )
        assert (
            "EXCERPT" in texts
        ), "the wide-net prompt must name what the model actually receives"

    def test_the_pl_head_records_the_wide_pass_formulas(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_propositional_logic,
        )

        state = _populated_state()
        captured = []
        client = _fake_client(captured, wide_formula="atom_present => atom_anchor")
        with patch("openai.AsyncOpenAI", return_value=client), patch.dict(
            "os.environ", {"OPENAI_API_KEY": "test-key"}
        ), patch(
            "argumentation_analysis.services.nl_to_logic.NLToLogicTranslator.translate_batch",
            _no_translations(),
        ):
            asyncio.run(
                _invoke_propositional_logic(state.raw_text, {"_state_object": state})
            )

        head = state.reading_window_status["propositional_logic"]
        assert head["head_formulas"] >= 1, (
            "the head produced this formula — the record must name it on the "
            "head site rather than leave it uncredited or give it to the units"
        )

    def test_the_fol_arm_records_units_and_keeps_the_head_as_signature(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_fol_reasoning,
        )

        state = _populated_state()
        captured = []
        client = _fake_client(captured)
        with patch("openai.AsyncOpenAI", return_value=client), patch.dict(
            "os.environ", {"OPENAI_API_KEY": "test-key"}
        ), patch(
            "argumentation_analysis.services.nl_to_logic.NLToLogicTranslator.translate_batch",
            _no_translations(),
        ):
            asyncio.run(_invoke_fol_reasoning(state.raw_text, {"_state_object": state}))

        entry = state.reading_window_status["fol_reasoning_units"]
        assert entry["units"] == state.analysis_coverage["fol_reasoning"]["k"] == 10
        head = state.reading_window_status["fol_reasoning"]
        assert head["offset"] == 0 and head["window"] == _HEAD
        block = format_reading_block(build_reading_record(state))
        assert "signature FOL" in block
        assert "logique du premier ordre — lecture par unités" in block
