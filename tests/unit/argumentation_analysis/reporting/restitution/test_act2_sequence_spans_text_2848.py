"""#2848 (carried by #2850 slice A) — the Act II chronological thread spans
the text, born-red guard.

The measured defect (#2841 pass, document 8fa89437_ext1): Act I announces 94
extracted arguments, Act II narrates 6 movements — all mapping onto arguments
1-3; the writer anchored only the first 12 asserts (_EXTRACT_ASSERT_CAP) and
the renderer took the first 8 of those. The narrative covered the opening.

This guard builds a synthetic 94-argument state through the PRODUCTION
writer (``_write_fact_extraction_to_state``), then the Act II prompt through
the production evidence+prompt builders, and asserts:

1. the sequence block carries a move from the LAST THIRD of the text
   (offset > 2/3 of the source length) — selection spans the text;
2. every one of the 94 arguments is anchored (the anchor is not a budget
   item; the budget lives at the render);
3. the truncation is SAID where it is read: « k coups montrés sur N ancrés,
   couvrant a–b sur L caractères ».

Deterministic, no LLM, invented prose only (no dataset content).
"""

import re

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.orchestration.state_writers import (
    _write_fact_extraction_to_state,
)
from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
    build_act2_evidence,
    build_act2_prompt,
)

_N_ARGS = 94  # the #2841-measured volume
_FILLER = (
    "The harbour commission publishes its maintenance ledger every spring, "
    "and every spring the same entries reappear with the same amounts. "
)


def _build_state() -> UnifiedAnalysisState:
    """A 94-argument state whose quotes are spread over a long text."""
    parts: list[str] = []
    total = 0
    quotes: list[str] = []
    step = 60000 // (_N_ARGS + 1)

    def fill_to(target: int) -> None:
        nonlocal total
        while total < target:
            parts.append(_FILLER)
            total += len(_FILLER)

    for i in range(_N_ARGS):
        target = (i + 1) * step
        fill_to(target)
        quote = f"ARGQUOTE{i} the dredging line has tripled since 2019, unit {i}. "
        parts.append(quote)
        total += len(quote)
        quotes.append(quote)
    fill_to(60000)
    raw = "".join(parts)

    state = UnifiedAnalysisState(raw)
    output = {
        "arguments": [
            {"text": f"Claim {i} about the ledger", "source_quote": q}
            for i, q in enumerate(quotes)
        ],
        "claims": [],
        "fallacies": [],
        "summary": "",
    }
    _write_fact_extraction_to_state(output, state, {})
    return state


def test_every_extracted_argument_is_anchored():
    """#2848 DoD 'the anchor is not a budget item': the writer anchors ALL
    94 — no first-12 gate, no truncation note."""
    state = _build_state()
    assert len(state.identified_arguments) == _N_ARGS
    anchored = [
        e
        for e in state.analysis_trace
        if e.get("move") == "assert" and isinstance(e.get("anchor"), dict)
    ]
    assert len(anchored) == _N_ARGS, (
        f"anchored asserts: {len(anchored)} of {_N_ARGS} — the writer cap is "
        "back (the anchor became a budget item again)"
    )
    max_offset = max(e["anchor"]["offset"] for e in anchored)
    assert max_offset > 2 * 60000 // 3, "anchors must span into the last third"


def test_act2_sequence_carries_a_last_third_move():
    """The k moves handed to the narrative span the text — at least one
    from the last third, the exact position the first-8-of-first-12 thread
    could never reach."""
    state = _build_state()
    evidence = build_act2_evidence(state)
    assert evidence.text_sequence is not None
    assert len(evidence.text_sequence.moves) == _N_ARGS
    prompt = build_act2_prompt(evidence)
    seq_block = prompt.split("SÉQUENCE DU TEXTE", 1)
    assert len(seq_block) == 2, "the sequence block is missing from the prompt"
    offsets = [int(m) for m in re.findall(r"\(offset (\d+)\)", seq_block[1])]
    assert offsets, "no anchored move rendered in the sequence block"
    last_third_floor = 2 * len(state.raw_text) // 3
    assert any(
        o >= last_third_floor for o in offsets
    ), f"no move from the last third (offsets max {max(offsets)}, floor {last_third_floor})"


def test_the_truncation_is_said_where_it_is_read():
    """k shown over N anchored, covering a–b over L characters — the
    truncation sentence exists and its numbers are the real ones."""
    state = _build_state()
    evidence = build_act2_evidence(state)
    prompt = build_act2_prompt(evidence)
    match = re.search(
        r"\((\d+) coups montrés sur (\d+) ancrés, couvrant les positions "
        r"(\d+)–(\d+) sur (\d+) caractères\)",
        prompt,
    )
    assert match, "the truncation sentence is missing from the sequence block"
    k, n, a, b, length = (int(g) for g in match.groups())
    assert n == _N_ARGS
    assert k < n, "with N > k the sentence must be there; k == N means no truncation"
    assert 0 <= a < b <= length == len(state.raw_text)
