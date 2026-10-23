# -*- coding: utf-8 -*-
"""#3149 (remaining reader, dispatch R1109) — ``build_narrative`` counts the
#2970 « not evaluated » records as « resultat(s) ».

The census (issue comment, R1109) left one reader: the formal-logic block of
``plugins/narrative_synthesis_plugin.py`` ``build_narrative`` —
``formal_count = len(fol) + len(pl) + len(modal)``. On the standard and full
workflows (the ``narrative_synthesis`` capability) a PL leg holding one
decided record and two #2970 placeholders was reported as « 3 resultat(s) »:
three formal results where the state holds one verdict. #2970 turned those
records into explicit non-verdicts (``None``) precisely so that no reader
counts them; this reader counted them anyway — family #1019, a field and its
reader.

A record is DECIDED when its verdict field is a bool: ``satisfiable`` (PL),
``consistent`` (FOL), ``valid`` (modal) — the same per-axis rule
``reading_record._VERDICT_KEY`` (#3190) holds. The undecided records are
named apart, never folded into the count.

Synthetic fixtures only, no corpus text (privacy HARD).
"""

from types import SimpleNamespace

from argumentation_analysis.plugins.narrative_synthesis_plugin import build_narrative

# The #2970 placeholder shape, as the arms write it: verdict ``None``, an
# explicit « not evaluated » message, one placeholder string where a decided
# record carries its formulas.
_PL_DECIDED = {
    "satisfiable": False,
    "message": "unsatisfiable",
    "formulas": [f"clause_{i}" for i in range(30)],
}
_PL_PLACEHOLDER = {
    "satisfiable": None,
    "message": "Not evaluated — no query specified (#2970)",
    "formulas": ["CL(0 conditionals): no clause recorded"],
}
_FOL_DECIDED = {
    "consistent": True,
    "message": "consistent",
    "formulas": [f"p{i}" for i in range(11)],
}
_FOL_PLACEHOLDER = {
    "consistent": None,
    "message": "Not evaluated — empty knowledge base (#2970)",
    "formulas": ["DL: empty knowledge base"],
}


def _state(pl=None, fol=None, modal=None):
    return SimpleNamespace(
        propositional_analysis_results=list(pl or []),
        fol_analysis_results=list(fol or []),
        modal_analysis_results=list(modal or []),
    )


def _formal_sentence(narrative: str) -> str:
    """The formal-logic sentence — the surface this issue governs."""
    for sentence in narrative.split("."):
        if "analyse formelle" in sentence:
            return sentence
    raise AssertionError(
        f"the narrative must carry one formal-logic sentence: {narrative!r}"
    )


class TestDecidedCount:
    """A verdict is counted only when the record decided."""

    def test_one_decided_pl_and_two_placeholders_is_one_result(self):
        """Witness (DoD): 1 decided PL record + 2 #2970 placeholders — the
        narrative must not report « 3 resultat(s) »."""
        narrative = build_narrative(
            _state(pl=[_PL_DECIDED, _PL_PLACEHOLDER, dict(_PL_PLACEHOLDER)])
        )
        sentence = _formal_sentence(narrative)
        assert "3 resultat" not in sentence, sentence
        assert "1 resultat" in sentence, sentence

    def test_fol_leg_one_decided_and_one_placeholder_is_one_result(self):
        """The FOL leg of the same defect: 1 decided + 1 DL placeholder was
        reported as « 2 »."""
        narrative = build_narrative(_state(fol=[_FOL_PLACEHOLDER, _FOL_DECIDED]))
        sentence = _formal_sentence(narrative)
        assert "2 resultat" not in sentence, sentence
        assert "1 resultat" in sentence, sentence

    def test_two_decided_records_still_say_two(self):
        """Control (DoD): two decided records — the count stays « 2 »."""
        second = dict(_PL_DECIDED, satisfiable=True)
        narrative = build_narrative(_state(pl=[_PL_DECIDED, second]))
        sentence = _formal_sentence(narrative)
        assert "2 resultat" in sentence, sentence

    def test_the_undecided_records_are_named_apart(self):
        """The placeholders must not vanish either: they are named as
        undecided analyses, never folded into the result count."""
        narrative = build_narrative(
            _state(pl=[_PL_DECIDED, _PL_PLACEHOLDER, dict(_PL_PLACEHOLDER)])
        )
        sentence = _formal_sentence(narrative)
        assert "1 resultat" in sentence, sentence
        assert "non evalue" in narrative.lower(), narrative

    def test_all_placeholder_leg_says_zero_result(self):
        """A leg holding only placeholders produces no result — and the
        sentence says so instead of reporting the record count."""
        narrative = build_narrative(_state(pl=[_PL_PLACEHOLDER]))
        sentence = _formal_sentence(narrative)
        assert "1 resultat" not in sentence, sentence
        assert "aucun resultat" in sentence, sentence
        assert "non evalue" in narrative.lower(), narrative

    def test_no_formal_records_no_sentence(self):
        """Empty legs render nothing, exactly as before."""
        assert "analyse formelle" not in build_narrative(_state())
