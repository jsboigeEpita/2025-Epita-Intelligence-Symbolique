# -*- coding: utf-8 -*-
"""#3488 — the cross-passage note hands the writer reader words, never ids.

``cross_passage_note`` is the one producer of the Act II block for the
cross-passage check, and the Act II prompt forbids raw snake_case in the
prose because writers copied such tokens onto the reader surface (#3311,
#3328). Before this fix the producer itself handed three of them over:

- the single-passage case printed the batch's internal entry ids — ``s3``
  names nothing a reader can find;
- the no-located-pair line printed the raw ``reason`` key;
- the undecided / unreachable lines printed ``({reason})``, plus the typo
  « non tranche ».

The fix: each contradicting passage is named by its slot, its recorded
quote and its position (the same line a located pair prints); every
``reason`` the module can write has one French clause in a closed table
kept beside the reasons — the RECORD keeps the raw key, only the NOTE
translates it; and the note spells « non tranché ».

Synthetic only — no key, no network, no corpus: the records are built by
hand over made-up moves.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

import argumentation_analysis.agents.core.reading.cross_passage as cp

_SID = re.compile(r"\bs\d+\b")
_SNAKE = re.compile(r"[a-z]+(?:_[a-z_]+)+")

_MODULE_PATH = (
    Path(cp.__file__)
    if not str(cp.__file__).endswith("__init__.py")
    else Path(cp.__file__).parent / "cross_passage.py"
)

# Every (status, reason) the module can write — the record shapes the note
# reads, including the two dynamic reasons by a representative value.
_STATUS_REASON_CASES = [
    ("unreachable", "no_first_reading_slots"),
    ("unreachable", "no_verbatim_quote_on_any_slot"),
    ("unreachable", "no_llm_translation_route"),
    ("unreachable", "translation_failed: RuntimeError"),
    ("unreachable", "translation_produced_no_formula"),
    ("undecided", "the_reasoner_did_not_decide_a_batch_theory"),
    (
        "inconsistent",
        "unsat_theory_without_a_decided_positioned_pair",
    ),
    ("inconsistent", "unsat_theory_including_single_passage: s2"),
    # #3683 — the executor's failure sink writes these two, not the module:
    # a check cut at its phase budget must not print its raw key.
    ("unreachable", "phase_budget_exceeded"),
    ("unreachable", "phase_failed"),
    ("checked", ""),
    ("undecided", ""),
]

_QUOTE_2 = "Le pilier repose sur un compte rendu non vérifié des échanges."
_QUOTE_1 = "La thèse soutient que la mesure a fait ses preuves."


def _moves() -> list:
    return [
        {
            "slot": "thesis",
            "kind": "claim",
            "quote": _QUOTE_1,
            "offset": 0,
        },
        {
            "slot": "pillar",
            "kind": "support",
            "quote": _QUOTE_2,
            "offset": 900,
        },
    ]


def _state(record: dict, moves: list | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        cross_passage_consistency=record,
        defining_moves={"moves": _moves() if moves is None else moves},
    )


def _record(status: str, reason: str, **extra) -> dict:
    base = {
        "status": status,
        "reason": reason,
        "checked": 12,
        "dropped_formulas": 0,
        "unquoted_slots": [],
        "pairs_decided": 0,
        "findings": [],
        "single_passage_unsat": [],
        "cross_batch_pairs_not_decided": 0,
        "batches": 1,
        "basis": "cross_passage_consistency",
    }
    base.update(extra)
    return base


class TestNoTokenReachesTheWriter:
    """Parametrised over every status × reason: the note carries no entry
    id and no snake_case token — RED on main, where the raw key and the
    ``s2`` id are printed."""

    @pytest.mark.parametrize(
        "status,reason", _STATUS_REASON_CASES, ids=lambda v: str(v)[:40]
    )
    def test_the_note_carries_no_id_and_no_snake_token(
        self, status: str, reason: str
    ) -> None:
        record = _record(status, reason)
        if reason.startswith("unsat_theory_including_single_passage"):
            record["single_passage_unsat"] = ["s2"]
        note = cp.cross_passage_note(_state(record))
        assert note, f"the note is empty for status={status!r}"
        assert not _SID.search(
            note
        ), f"an internal entry id reaches the writer: {_SID.search(note).group()!r}"
        assert not _SNAKE.search(
            note
        ), f"a raw token reaches the writer: {_SNAKE.search(note).group()!r}"

    def test_the_single_passage_note_carries_the_quote(self) -> None:
        """The contradicting passage is named the way a located pair is:
        slot label, recorded quote between « », position in characters."""
        record = _record(
            "inconsistent",
            "unsat_theory_including_single_passage: s2",
            single_passage_unsat=["s2"],
        )
        note = cp.cross_passage_note(_state(record))
        assert f"« {_QUOTE_2} »" in note
        assert "(position 900)" in note
        assert "pilier" in note  # the slot's reader name, not the id

    def test_an_unresolvable_id_is_named_unlocalizable_never_printed(
        self,
    ) -> None:
        """A record whose id matches no move any more (a replay on a state
        that changed) still says something a reader can act on — the id
        itself never prints."""
        record = _record(
            "inconsistent",
            "unsat_theory_including_single_passage: s7",
            single_passage_unsat=["s7"],
        )
        note = cp.cross_passage_note(_state(record))
        assert "localisable" in note
        assert "s7" not in note

    def test_non_tranche_is_spelled(self) -> None:
        record = _record("undecided", "the_reasoner_did_not_decide_a_batch_theory")
        note = cp.cross_passage_note(_state(record))
        assert "non tranché" in note
        assert "non tranche" not in note


class TestTheReasonTableIsClosed:
    """The coordinator's completeness control: walk the AST of the module
    and fail when a ``payload["reason"] =`` value has no clause — RED on
    main, where no table exists."""

    @staticmethod
    def _reason_literals() -> set:
        tree = ast.parse(_MODULE_PATH.read_text(encoding="utf-8"))
        literals = set()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue
            targets = [
                t
                for t in node.targets
                if isinstance(t, ast.Subscript)
                and isinstance(t.value, ast.Name)
                and t.value.id == "payload"
                and isinstance(t.slice, ast.Constant)
                and t.slice.value == "reason"
            ]
            if not targets:
                continue
            value = node.value
            parts: list = []
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                parts = [value.value]
            elif isinstance(value, ast.JoinedStr):
                parts = [
                    p.value
                    for p in value.values
                    if isinstance(p, ast.Constant) and isinstance(p.value, str)
                ]
            elif isinstance(value, ast.BinOp):
                stack = [value]
                while stack:
                    item = stack.pop()
                    if isinstance(item, ast.BinOp) and isinstance(item.op, ast.Add):
                        stack.extend([item.left, item.right])
                    elif isinstance(item, ast.Constant) and isinstance(item.value, str):
                        parts.append(item.value)
            for part in parts:
                if part.strip() and part != "":
                    literals.add(part.split(":", 1)[0].strip().rstrip(":").strip())
        return {lit for lit in literals if lit}

    def test_every_written_reason_has_a_clause(self) -> None:
        table = getattr(cp, "_REASON_CLAUSES", {})
        literals = self._reason_literals()
        assert literals, "the AST walk found no reason assignment — the test is blind"
        missing = {lit for lit in literals if lit not in table}
        assert not missing, (
            f"reason keys without a French clause: {sorted(missing)!r} — "
            f"the note would print or drop them raw"
        )

    def test_every_clause_is_reader_words(self) -> None:
        """The table itself carries no token: translating a reason must
        never introduce what the reason key was banned for."""
        table = getattr(cp, "_REASON_CLAUSES", {})
        assert table, "no reason table on this module"
        for key, clause in table.items():
            assert not _SNAKE.search(clause), f"clause of {key!r} carries a token"
            assert not _SID.search(clause), f"clause of {key!r} carries an entry id"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
