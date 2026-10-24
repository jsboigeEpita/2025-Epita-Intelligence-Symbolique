"""#3217 — the provenance side-table carries verbatim corpus text.

``argument_provenance`` is written by ``UnifiedAnalysisState.add_argument``
(``core/shared_state.py``): each entry records ``producer`` (closed
vocabulary), ``offset`` (int), ``offset_basis`` (closed vocabulary) — and
``source_quote``, the VERBATIM quote the producer extracted, stored in full
(the writer truncates only the copy embedded in the argument text,
``state_writers.py:1618``). Measured on the 49 stored campaign states:
360/360 non-empty quotes survived ``sanitize_state`` byte-identical while the
argument text beside them was stripped — the container sat outside every
allowlist table, and the module docstring says such a container traverses
intact.

This witness closes that one leaf: the quote must go, the record must stay.
The control pins ``producer`` / ``offset`` / ``offset_basis`` so the fix
cannot be "drop the container" — the table is the provenance carrier #2850
measured and #3162 needs (drop the nominative leaf, keep the record).
"""

from __future__ import annotations

import pytest

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.evaluation.sanitize_state import sanitize_state

# Synthetic strings invented for this witness — they appear in no corpus.
_QUOTE = "CANARY_3217 la citation verbatim que le sanitiseur doit retirer du record"
_ARGUMENT = "CANARY_3217 unite argumentative synthetique portant la citation"
_RAW_TEXT = (
    "texte synthetique invente pour ce temoin, sans aucune valeur de corpus. "
    + _QUOTE
    + " suite du texte synthetique pour donner une longueur realiste apres la citation."
)


@pytest.fixture(autouse=True)
def _synthetic_opaque_salt(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin the salt the scrubber demands (#1973) — everything here is fabricated."""
    monkeypatch.setenv("OPAQUE_ID_SALT", "synthetic-test-salt-3217")


def _state_with_one_quoted_argument() -> UnifiedAnalysisState:
    """One argument planted through the real producer path the writer uses.

    ``state_writers.py:1623`` calls ``add_argument(text, producer=...,
    source_quote=...)`` — the witness plants the quote through that same
    ``add_*`` API, never a hand-built dict (the #1664 anti-pattern).
    """
    state = UnifiedAnalysisState(_RAW_TEXT)
    state.add_argument(
        _ARGUMENT,
        producer="llm_extract",
        source_quote=_QUOTE,
    )
    return state


def _sanitized(state: UnifiedAnalysisState) -> dict:
    """The guard's convention (#1702): the scrubber eats the snapshot dict."""
    return sanitize_state(state.get_state_snapshot())


def _strings(obj: object) -> list[str]:
    """Every string reachable in the sanitized output, wherever it hides."""
    found: list[str] = []
    if isinstance(obj, str):
        found.append(obj)
    elif isinstance(obj, dict):
        for key, value in obj.items():
            found.append(str(key))
            found.extend(_strings(value))
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            found.extend(_strings(item))
    return found


class TestProvenanceQuoteIsStripped:
    def test_the_quote_does_not_survive(self) -> None:
        out = _sanitized(_state_with_one_quoted_argument())
        entries = out.get("argument_provenance") or {}
        assert entries, (
            "the provenance container itself vanished — the fix must drop the "
            "leaf, not the record (#3217 anti-pendulum: #2850/#3162 read it)"
        )
        assert not any(
            "CANARY_3217" in s for s in _strings(out)
        ), "the verbatim quote survived somewhere in the sanitized output"

    def test_the_structural_keys_are_unchanged(self) -> None:
        state = _state_with_one_quoted_argument()
        before = {
            arg_id: dict(entry) for arg_id, entry in state.argument_provenance.items()
        }
        assert before, "the producer wrote no provenance entry — witness is vacuous"

        after = _sanitized(state)["argument_provenance"]

        assert set(after) == set(before)
        for arg_id, entry_before in before.items():
            entry_after = after[arg_id]
            for structural_key in ("producer", "offset", "offset_basis"):
                assert entry_before.get(structural_key) == entry_after.get(
                    structural_key
                ), (
                    f"{arg_id}.{structural_key} changed — the fix must drop only "
                    "source_quote"
                )

    def test_the_quote_leaf_is_gone_not_emptied(self) -> None:
        """The pass-4 gesture drops the leaf; a future "" placeholder would be
        a softer fix that still names the corpus-adjacent key."""
        out = _sanitized(_state_with_one_quoted_argument())
        entry = next(iter(out["argument_provenance"].values()))
        assert "source_quote" not in entry, (
            "source_quote survived (as a key or an emptied value) — pass 4 "
            "must drop the leaf"
        )
