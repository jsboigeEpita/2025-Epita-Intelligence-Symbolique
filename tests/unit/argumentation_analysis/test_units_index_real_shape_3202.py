# -*- coding: utf-8 -*-
"""#3202 — the per-unit index reads the shape the producer writes.

``reading_license._index_units`` built its distinctive-token index from
``identified_arguments[arg_id]["description"]``. No producer writes a dict:
``UnifiedAnalysisState.add_argument`` stores the description STRING itself
(``shared_state.py``), and every stored paid state carries ``str`` values.
The index was therefore empty on every real run, and every check gated on
``units_indexed`` was inert — ``counter_on_wrong_unit``, the « seuls X et Y »
flag, and ``fallacy_name_without_record`` (open PR #3195).

The witnesses below build their state through the REAL class and its real
writers, so the shape under test is the shape a run produces. Synthetic
vocabulary only (phare, fournil, bonde — no corpus content, privacy HARD).
"""

import json
import pathlib
from types import SimpleNamespace

import pytest

from argumentation_analysis.agents.core.synthesis.reading_license import (
    check_reading_license,
)
from argumentation_analysis.core.shared_state import UnifiedAnalysisState

_DESCRIPTION_A = "Le phare octogonal domine la baie."
_DESCRIPTION_B = "Le fournil pétille dès l'aube."
_COUNTER_CONTENT = "La bonde océane reste ouverte."

#: A stored state from a paid run, under the gitignored results tree. The
#: real-state guard skips when the seat has none (this is not a fixture the
#: repo carries — the state is gitignored by construction).
_STORED_STATE = (
    pathlib.Path(__file__).parent.parent.parent.parent
    / "argumentation_analysis"
    / "evaluation"
    / "results"
    / "full_judgment"
    / "judge_A_po2023_state.json"
)


def _real_state():
    """A state built through the class and the writers a run uses."""
    state = UnifiedAnalysisState("Texte de départ synthétique.")
    arg_a = state.add_argument(_DESCRIPTION_A)
    arg_b = state.add_argument(_DESCRIPTION_B)
    state.add_counter_argument(
        original_arg=_DESCRIPTION_A,
        counter_content=_COUNTER_CONTENT,
        strategy="distinguo",
        score=0.5,
        target_arg_id=arg_a,
    )
    return state, arg_a, arg_b


class TestTheIndexReadsTheRealShape:
    def test_a_counter_in_another_units_paragraph_is_flagged(self):
        """Witness — the counter targets arg_a, and its distinctive tokens are
        cited in arg_b's paragraph. Red on main: ``units_indexed`` was empty,
        so no paragraph could be placed on any unit."""
        state, arg_a, arg_b = _real_state()
        weave = (
            "Le fournil pétille dès l'aube, et personne ne le conteste ; "
            "pourtant la bonde océane reste ouverte."
        )
        result = check_reading_license(weave, state)
        assert result["checked"]["units_indexed"] == 2
        flags = [f for f in result["flags"] if f["kind"] == "counter_on_wrong_unit"]
        assert len(flags) == 1, result["flags"]
        assert flags[0]["measured"]["target_arg_id"] == arg_a
        assert flags[0]["measured"]["paragraph_units"] == [arg_b]

    def test_the_counter_in_its_own_units_paragraph_passes(self):
        """Control — the paragraph is about arg_a, the counter's own target."""
        state, _, _ = _real_state()
        weave = (
            "Le phare octogonal domine la baie. "
            "Mais la bonde océane reste ouverte, dit l'objection."
        )
        result = check_reading_license(weave, state)
        assert [
            f["kind"] for f in result["flags"] if f["kind"] == "counter_on_wrong_unit"
        ] == []

    def test_the_producer_writes_a_string_and_the_index_reads_it(self):
        """The premise itself, measured: the real writer stores a str."""
        state, arg_a, _ = _real_state()
        assert isinstance(state.identified_arguments[arg_a], str)


class TestTheStoredStateIndexIsNotEmpty:
    def test_a_stored_state_yields_a_non_empty_unit_index(self):
        """Real state, 0 LLM calls. On main this reported ``units_indexed``
        0 on every paid state; the description strings now place the units.
        Only counts are read out — never the text (privacy HARD)."""
        if not _STORED_STATE.exists():
            pytest.skip("no stored state on this seat")
        data = json.loads(_STORED_STATE.read_text(encoding="utf-8"))
        state = SimpleNamespace(**data)
        result = check_reading_license(
            "Aucune phrase du rapport ne cite une unité.", state
        )
        units = len(state.identified_arguments)
        indexed = result["checked"]["units_indexed"]
        assert units > 0
        assert indexed > 0, f"units={units} indexed={indexed}"
