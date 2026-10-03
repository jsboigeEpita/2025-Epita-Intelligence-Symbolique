# -*- coding: utf-8 -*-
"""#2896 (c): the counter phase and the ATMS thread read the merged
population, not the extraction's opening window.

Both phases built their unit lists from ``extract_output["arguments"]``
alone — the LLM extraction that reads the first 3,000 characters. On the
#2850 paid run the counter's targets were ``arg_1``…``arg_7`` (0.00–0.05)
and ``arg_13``: nothing beyond the window is ever countered, even though
the merged population carries located units across the whole text. Both
now select through ``merged_population_units`` + ``select_for_budget``
(the coverage layer), with their budget unchanged.
"""

import asyncio

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.orchestration import invoke_callables
from argumentation_analysis.orchestration.invoke_callables import (
    _invoke_atms,
    _invoke_counter_argument,
)

_N_UNITS = 20
_STEP = 1_480  # offsets 0 … 28_120 over a ~29_600-char text


def _population_state():
    text = " ".join(
        f"Sentence {i:02d} of the source document unfolds here." for i in range(600)
    )
    state = UnifiedAnalysisState(text)
    state.identified_arguments = {}
    state.argument_provenance = {}
    for i in range(1, _N_UNITS + 1):
        # Units the 3,000-char reading window cannot see announce it in
        # their text, so the witness asserts on a distinctive marker.
        marker = "beyond the reading window" if i * _STEP > 3_000 else "at the opening"
        state.identified_arguments[f"arg_{i}"] = (
            f"Unit {i:02d} sits {marker} and claims something specific."
        )
        state.argument_provenance[f"arg_{i}"] = {
            "producer": "test",
            "offset": i * _STEP,
        }
    return state


def _context_for(state):
    # What the extraction phase (reading window = first 3,000 chars)
    # would have emitted: the opening units ONLY — every unit carrying
    # the "beyond" marker sits past the window, so the extract cannot
    # contain it (arg_3 at offset 4_440 would leak the marker in).
    extract_args = [
        {"text": state.identified_arguments[f"arg_{i}"], "source_quote": ""}
        for i in (1, 2)
    ]
    return {
        "_state_object": state,
        "phase_extract_output": {"arguments": extract_args, "claims": []},
        "phase_hierarchical_fallacy_output": {"fallacies": []},
        "phase_quality_output": {},
    }


def test_counter_targets_reach_beyond_the_window(monkeypatch):
    """The counter's LLM targets include units the reading window never
    saw. The generator is captured, so the run makes zero network calls
    (the fake key is never exercised)."""
    state = _population_state()
    captured: dict = {}

    async def _capture(client, model_id, targets):
        captured["targets"] = list(targets)
        return []

    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-witness-zero-bill-2896")
    monkeypatch.setattr(invoke_callables, "_generate_counters_for_targets", _capture)

    asyncio.run(_invoke_counter_argument(state.raw_text, _context_for(state)))

    targets = captured.get("targets") or []
    assert targets, "the counter built no targets at all"
    beyond = [t for t in targets if "beyond the reading window" in t]
    assert beyond, (
        "every counter target comes from the extraction's opening window — "
        f"units beyond it are never countered ({len(targets)} targets)"
    )
    coverage = (getattr(state, "analysis_coverage", None) or {}).get("counter")
    assert coverage is not None, "the counter phase records no coverage entry"


def test_atms_assumptions_reach_beyond_the_window():
    """The ATMS assumption set includes units beyond the window (born red:
    ``raw_args[:8]`` reads the extraction alone, so only the opening
    becomes an assumption)."""
    state = _population_state()
    result = asyncio.run(_invoke_atms(state.raw_text, _context_for(state)))

    assumptions = result.get("assumptions") or []
    beyond = [a for a in assumptions if "beyond the reading window" in str(a)]
    assert beyond, (
        "every ATMS assumption comes from the extraction's opening window "
        f"({len(assumptions)} assumptions)"
    )
