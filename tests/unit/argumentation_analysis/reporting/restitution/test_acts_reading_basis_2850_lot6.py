"""#2850 lot 6 — the recorded reading bounds reach Acts II and III.

The "Acts silent" family: the trace has spoken each reading window since lot
4 (``Lecture : k des N``) and the #1737 table records every selection a
state-carrying site makes — but the restitution acts quoted none of it, so a
reader of the acts could not learn that the specialists read a bounded head
of the document. The fix is one record (``reading_record``, mirror of the
#3082 speaker record) grafted on Acts II and III: the act speaks the k of N
of every recorded site, and its rule's absent case forbids inventing a bound
when nothing was recorded.

Mutations that must redden it (rendered in the PR): dropping the reading
block from Acte II's prompt, and from Acte III's.

Every assertion is on the prompt string, from the #3082 harness — the test
touches no attribute a fix introduces, so a reverted production fails on the
behaviour, never on an import. Synthetic opaque values only.
"""

from types import SimpleNamespace

from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
    build_act2_evidence,
    build_act2_prompt,
)
from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    build_act3_evidence,
    build_act3_prompt,
)

_DOC_CHARS = 50_000
_EXTRACT_WINDOW = 3000
_COLLAB_WINDOW = 1500

_BLOCK_MARKER = "[LECTURES DU RUN"
_RULE_MARKER = "LES BORNES DE LECTURE SE DISENT PAR LES LIGNES LECTURES DU RUN"


def _state(recorded=True):
    state = SimpleNamespace()
    state.raw_text = "x" * _DOC_CHARS
    state.source_metadata = {}
    state.stakes_and_stakeholders = {
        "stakes": [],
        "stakeholders": [],
        "rhetorical_register": "",
        "discursive_arena": "",
    }
    state.deanonymized = True
    state.reading_window_status = (
        {
            "fact_extraction": {
                "status": "selected",
                "offset": 0,
                "window": _EXTRACT_WINDOW,
            },
            # The lot-5-measured-live row: the collaborative debate's
            # fallback window, whose Acts clause lot 5 explicitly deferred.
            "collaborative_debate": {
                "status": "selected",
                "offset": _DOC_CHARS - _COLLAB_WINDOW,
                "window": _COLLAB_WINDOW,
            },
        }
        if recorded
        else {}
    )
    return state


def _prompts(state):
    return (
        build_act2_prompt(build_act2_evidence(state)),
        build_act3_prompt(build_act3_evidence(state)),
    )


def test_both_acts_quote_the_recorded_bounds():
    """One record, two prompts: the k-of-N of every recorded site."""
    p2, p3 = _prompts(_state())
    for name, p in (("Acte II", p2), ("Acte III", p3)):
        assert _BLOCK_MARKER in p, (
            f"{name} quoted none of the recorded readings — the trace named "
            "each window since lot 4, the act must speak the basis"
        )
        assert (
            f"{_EXTRACT_WINDOW} des {_DOC_CHARS}" in p
        ), f"{name} dropped the extraction window's k of N"


def test_the_collaborative_fallback_window_is_quoted():
    """The row lot 5 measured live: its Acts clause arrives here."""
    p2, p3 = _prompts(_state())
    for name, p in (("Acte II", p2), ("Acte III", p3)):
        assert "débat collaboratif" in p, (
            f"{name} does not quote the collaborative_debate site the #1737 "
            "table recorded"
        )
        assert (
            f"{_COLLAB_WINDOW} des {_DOC_CHARS}" in p
        ), f"{name} dropped the collaborative window's k of N"


def test_the_naming_rule_travels_with_both_acts():
    """The contract ships unconditionally — its absent case is the guard
    against a fabricated bound."""
    p2, p3 = _prompts(_state(recorded=False))
    assert _RULE_MARKER in p2, "Acte II must carry the reading-basis rule"
    assert _RULE_MARKER in p3, "Acte III must carry the reading-basis rule"


def test_no_recorded_reading_no_block():
    """Control: nothing recorded → no block (and never an invented bound)."""
    p2, p3 = _prompts(_state(recorded=False))
    assert _BLOCK_MARKER not in p2, (
        "an empty #1737 table must not produce a reading block — there is "
        "no bound to quote"
    )
    assert _BLOCK_MARKER not in p3, "same for Acte III"


def test_a_short_document_read_whole_says_so():
    """A window at or above the document length is a full read, said as
    such — never as a truncation."""
    state = _state()
    state.raw_text = "y" * 1000
    p2, _ = _prompts(state)
    assert "lu en entier" in p2, (
        "a 3000-char window over a 1000-char document read the whole "
        "document — the line must say so"
    )
    assert "lecture de 3000 des 1000" not in p2
