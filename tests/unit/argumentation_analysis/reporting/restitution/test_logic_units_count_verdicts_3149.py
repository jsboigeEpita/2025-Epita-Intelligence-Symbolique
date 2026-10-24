"""#3149 — the logic-units line counts FORMAL VERDICTS and TESTED FORMULAS.

The reading-bounds passage printed, for the R1106 doc_A run:

- « la traduction propositionnelle (7 formule(s) sur **32** … ) et ses **3**
  verdict(s) formel(s) » — while the state held **1** decided record over
  **30** formulas (the other two are the #2970 « not evaluated » records, one
  placeholder string each);
- « la traduction FOL (11 formule(s) sur **12** … ) et ses **2** verdict(s)
  formel(s) » — while the state held **1** decided record over **11**
  formulas.

A `satisfiable`/`consistent` of `None` is not a verdict, and a writer
placeholder is not a tested formula. Both were counted.
"""

from __future__ import annotations

from types import SimpleNamespace

from argumentation_analysis.reporting.restitution.reading_record import _site_fed

_PLACEHOLDER = "CL(0 conditionals): not evaluated (#2970)"


def _pl_formulas(count: int) -> list:
    return [f"p{i}" for i in range(count)]


def _state() -> SimpleNamespace:
    pl_real = {
        "satisfiable": False,
        "formulas": _pl_formulas(30),
        "formula_sources": [[f"unit_{i}"] for i in range(30)],
    }
    pl_undecided = [
        {
            "satisfiable": None,
            "message": "Not evaluated — no query specified (#2970)",
            "formulas": [_PLACEHOLDER],
        },
        {
            "satisfiable": None,
            "message": "not evaluated (#2970)",
            "formulas": [_PLACEHOLDER],
        },
    ]
    fol_real = {
        "consistent": True,
        "formulas": [f"pred_{i}(a)" for i in range(11)],
        "formula_sources": [[f"unit_{i}"] for i in range(11)],
    }
    fol_undecided = {
        "consistent": None,
        "message": "Not evaluated — empty knowledge base (#2970)",
        "formulas": [_PLACEHOLDER],
    }
    return SimpleNamespace(
        propositional_analysis_results=[pl_real, *pl_undecided],
        fol_analysis_results=[fol_undecided, fol_real],
    )


class TestPropositional:
    def test_verdict_count_ignores_the_not_evaluated_records(self):
        line = _site_fed("propositional_logic_units", _state())
        assert " 1 verdict formel" in line, line

    def test_formula_count_excludes_the_placeholder_strings(self):
        line = _site_fed("propositional_logic_units", _state())
        assert "30 formules sur 30" in line, line
        assert "32" not in line, line


class TestPlaceholderInsideADecidedRecord:
    """A DECIDED record can still carry a writer placeholder among its real
    formulas (the writer-placeholder vocabulary `is_real_formula` exists for,
    #1914/#2960). The record-level filter above cannot see it: the count must
    exclude it on its own, or a decided record inflates the line exactly the
    way the undecided ones did."""

    def test_a_decided_record_counts_only_its_real_formulas(self):
        state = SimpleNamespace(
            propositional_analysis_results=[
                {
                    "satisfiable": True,
                    "formulas": ["p", "q", "CL(0 conditionals): not evaluated (#2970)"],
                    "formula_sources": [["unit_0"], ["unit_1"], []],
                }
            ],
            fol_analysis_results=[],
        )
        line = _site_fed("propositional_logic_units", state)
        assert "2 formules sur 2" in line, line
        assert "sur 3" not in line, line


class TestFol:
    def test_verdict_count_ignores_the_not_evaluated_record(self):
        line = _site_fed("fol_reasoning_units", _state())
        assert " 1 verdict formel" in line, line

    def test_formula_count_excludes_the_placeholder_string(self):
        line = _site_fed("fol_reasoning_units", _state())
        assert "11 formules sur 11" in line, line
        assert "sur 12" not in line, line
