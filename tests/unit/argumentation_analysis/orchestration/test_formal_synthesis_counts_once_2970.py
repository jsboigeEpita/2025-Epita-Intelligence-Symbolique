"""#2970 item 2 — formal_synthesis counts each decided result once.

Measured on the saved 06/10 doc_A state (the issue's numbers):
``_invoke_formal_synthesis`` averaged one score per verdict KEY it found, so

* ``fol`` and ``fol_solver`` — which carry the same 4 formulas and asked two
  reasoners the same question — were counted twice;
* "not evaluated" producers entered the population as soon as they named a
  field, so a run where nothing was decided still published a figure;
* the summary's ``elif`` chain read ``consistent`` then ``satisfiable`` and
  never ``valid``, so modal, modal_solver and qbf vanished from the stored
  summary; and it counted extensions only when they were a DICT, so bipolar,
  ABA and ASPIC (bare lists) printed "0 extensions" over real results.

The issue's witness: over {fol consistent, fol_solver same formulas
consistent, pl UNSAT} main returns 2/3; the fix returns 1/2, with the positive
control "two producers with DIFFERENT formulas are both counted".

Witness discipline: synthetic inputs only (opaque atoms, no corpus sentence);
the persistence witness runs against the REAL ``UnifiedAnalysisState``, never a
MagicMock (that mock-where-a-real-state-can-stand pattern was the root of the
sibling items). Born red on main: every assertion below is checked against the
pre-fix function in the task's mutation run, and the class docstrings say which
main behaviour each one pins.
"""

from typing import Any, Dict

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.orchestration.invoke_callables import (
    _invoke_formal_synthesis,
)
from argumentation_analysis.orchestration.state_writers import (
    _write_formal_synthesis_to_state,
)

_FOL_FORMULAS = ["P(a)", "Q(a)", "P(a) -> Q(a)", "Q(a) -> R(a)"]
_OTHER_FORMULAS = ["S(b)", "T(b)"]


def _context(**outputs: Dict[str, Any]) -> Dict[str, Any]:
    """A context whose ``phase_<name>_output`` keys carry the given outputs."""
    return {f"phase_{name}_output": value for name, value in outputs.items()}


class TestSamePopulationCountsOnce:
    """Main appends one score per verdict key, so fol and fol_solver — the same
    4 formulas to two reasoners — are two entries in the population."""

    async def test_the_issue_witness_one_half_not_two_thirds(self):
        result = await _invoke_formal_synthesis(
            "texte",
            _context(
                fol={
                    "consistent": True,
                    "logic_type": "first_order",
                    "formulas": _FOL_FORMULAS,
                },
                fol_solver={
                    "consistent": True,
                    "logic_type": "first_order",
                    # Same formulas, whitespace-respelled: the same population.
                    "formulas": [" P(a) ", "Q(a)", "P(a)   -> Q(a)", "Q(a) -> R(a)"],
                },
                pl={
                    "satisfiable": False,
                    "logic_type": "propositional",
                    "formulas": _OTHER_FORMULAS,
                },
            ),
        )

        assert result["overall_validity"] == 0.5  # main: 2/3
        assert len(result["decided_results"]) == 2  # main: 3 scored keys
        assert [entry["score"] for entry in result["decided_results"]] == [1.0, 0.0]

        fol_entry = next(
            entry
            for entry in result["decided_results"]
            if entry["field"] == "consistent"
        )
        assert fol_entry["producers"] == ["fol", "fol_solver"]
        assert fol_entry["formula_fingerprint"]

    async def test_positive_control_different_formulas_both_counted(self):
        result = await _invoke_formal_synthesis(
            "texte",
            _context(
                fol={
                    "consistent": True,
                    "logic_type": "first_order",
                    "formulas": _FOL_FORMULAS,
                },
                fol_solver={
                    "consistent": True,
                    "logic_type": "first_order",
                    "formulas": _OTHER_FORMULAS,
                },
            ),
        )

        assert len(result["decided_results"]) == 2
        assert result["overall_validity"] == 1.0
        assert sorted(entry["producers"][0] for entry in result["decided_results"]) == [
            "fol",
            "fol_solver",
        ]

    async def test_two_logics_over_the_same_strings_are_two_results(self):
        """A propositional satisfiability claim and a first-order consistency
        claim over identical strings are different formal claims."""
        result = await _invoke_formal_synthesis(
            "texte",
            _context(
                fol={
                    "consistent": True,
                    "logic_type": "first_order",
                    "formulas": ["P"],
                },
                pl={
                    "satisfiable": False,
                    "logic_type": "propositional",
                    "formulas": ["P"],
                },
            ),
        )

        assert len(result["decided_results"]) == 2
        assert result["overall_validity"] == 0.5

    async def test_producers_without_formulas_are_never_deduped(self):
        """Nothing proves two formula-less producers measured the same thing."""
        result = await _invoke_formal_synthesis(
            "texte",
            _context(
                dl={"consistent": True},
                cl={"consistent": True},
            ),
        )

        assert len(result["decided_results"]) == 2
        assert result["overall_validity"] == 1.0

    async def test_disagreement_stays_two_results_and_the_population_shows_it(self):
        """Two producers that decided the same population differently are two
        results, not a duplicate — and no dedicated key names it: the
        population carries the disagreement itself (one fingerprint, same
        field, opposite verdicts)."""
        result = await _invoke_formal_synthesis(
            "texte",
            _context(
                fol={
                    "consistent": True,
                    "logic_type": "first_order",
                    "formulas": _FOL_FORMULAS,
                },
                fol_solver={
                    "consistent": False,
                    "logic_type": "first_order",
                    "formulas": _FOL_FORMULAS,
                },
            ),
        )

        assert len(result["decided_results"]) == 2
        assert result["overall_validity"] == 0.5
        assert "conflicts" not in result
        fingerprints = {
            entry["formula_fingerprint"] for entry in result["decided_results"]
        }
        assert len(fingerprints) == 1  # the same population, decided twice
        assert {entry["verdict"] for entry in result["decided_results"]} == {
            True,
            False,
        }
        assert {
            entry["producers"][0]: entry["verdict"]
            for entry in result["decided_results"]
        } == {"fol": True, "fol_solver": False}


class TestNotEvaluatedIsNamedNotAveraged:
    """Main excluded None from ``overall_scores`` but published nothing about
    it — a reader could not tell "agreed" from "nobody decided"."""

    async def test_none_verdict_is_excluded_and_named(self):
        result = await _invoke_formal_synthesis(
            "texte",
            _context(
                fol={
                    "consistent": True,
                    "logic_type": "first_order",
                    "formulas": _FOL_FORMULAS,
                },
                dl={"consistent": None, "message": "not evaluated (#2970)"},
            ),
        )

        assert len(result["decided_results"]) == 1
        assert result["overall_validity"] == 1.0
        assert result["not_evaluated"] == ["dl"]
        assert result["summary"].count("dl: consistent=not evaluated") == 1

    async def test_a_non_verdict_phase_is_not_a_not_evaluated_formal_axis(self):
        """An extension axis (bipolar) and a synthesis phase that errored carry
        no verdict field: they are reported in the summary, but they are not
        formal verdict axes, so `not_evaluated` must not be padded with them."""
        result = await _invoke_formal_synthesis(
            "texte",
            _context(
                fol={
                    "consistent": True,
                    "logic_type": "first_order",
                    "formulas": _FOL_FORMULAS,
                },
                bipolar={"extensions": None, "degraded": True},
                deep_synthesis={"error": "No shared state available"},
            ),
        )

        assert result["not_evaluated"] == []
        assert len(result["decided_results"]) == 1
        assert "bipolar: extensions not computed" in result["summary"]
        assert "deep_synthesis: error (No shared state available)" in result["summary"]

    async def test_none_verdict_does_not_swallow_the_decided_producer(self):
        """Same formulas, one producer degraded: the decided one still counts."""
        result = await _invoke_formal_synthesis(
            "texte",
            _context(
                fol={
                    "consistent": True,
                    "logic_type": "first_order",
                    "formulas": _FOL_FORMULAS,
                },
                fol_solver={
                    "consistent": None,
                    "logic_type": "first_order",
                    "formulas": _FOL_FORMULAS,
                },
            ),
        )

        assert len(result["decided_results"]) == 1
        assert result["overall_validity"] == 1.0
        assert result["not_evaluated"] == ["fol_solver"]

    async def test_empty_population_is_half_and_the_population_says_so(self):
        result = await _invoke_formal_synthesis("texte", _context(dl={}))

        assert len(result["decided_results"]) == 0
        assert result["decided_results"] == []
        assert [entry["score"] for entry in result["decided_results"]] == []
        assert result["overall_validity"] == 0.5


class TestSummaryReadsListsAndTheValidKey:
    """Main's ``elif`` chain stopped at ``satisfiable``: ``valid`` producers
    disappeared, and list-shaped extensions printed "0 extensions"."""

    async def test_valid_key_reaches_the_summary(self):
        result = await _invoke_formal_synthesis(
            "texte",
            _context(
                modal={"valid": True, "logic_type": "modal"},
                modal_solver={"valid": False, "logic_type": "modal"},
                qbf={"valid": None, "status": "not_evaluated"},
            ),
        )

        summary = result["summary"]
        assert "modal: valid=True" in summary  # main: absent
        assert "modal_solver: valid=False" in summary  # main: absent
        assert "qbf: valid=not evaluated" in summary  # main: absent

    async def test_list_shaped_extensions_are_counted(self):
        result = await _invoke_formal_synthesis(
            "texte",
            _context(
                bipolar={"extensions": [["a"], ["a", "b"]]},
                aba={"extensions": [["x"]]},
            ),
        )

        summary = result["summary"]
        assert "bipolar: 2 extensions" in summary  # main: "0 extensions"
        assert "aba: 1 extensions" in summary  # main: "0 extensions"

    async def test_not_computed_is_not_a_fabricated_zero(self):
        result = await _invoke_formal_synthesis(
            "texte", _context(bipolar={"extensions": None})
        )

        assert "bipolar: extensions not computed" in result["summary"]
        assert "0 extensions" not in result["summary"]

    async def test_computed_empty_extensions_are_a_real_zero(self):
        result = await _invoke_formal_synthesis(
            "texte", _context(bipolar={"extensions": []})
        )

        assert "bipolar: 0 extensions" in result["summary"]


class TestExtensionShapes:
    """Every shape the producers emit, counted by its own rules.

    ``_count_extensions`` is imported inside each test on purpose: it is a NEW
    symbol, and a module-level import of it would make collection fail on main
    (a collection error masks the born-red signal — measured lesson).
    """

    def test_dung_enriched_entry_uses_its_own_count(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _count_extensions,
        )

        assert _count_extensions({"extensions": [["a"], ["b"]], "count": 2}) == 2

    def test_dung_semantics_map_sums_its_semantics(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _count_extensions,
        )

        assert (
            _count_extensions(
                {
                    "grounded": {"extensions": [["a"]], "count": 1},
                    "preferred": {"extensions": [["a"], ["b"]], "count": 2},
                }
            )
            == 3
        )

    def test_bare_list_counts_its_elements(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _count_extensions,
        )

        assert _count_extensions([["a"], ["a", "b"]]) == 2

    def test_none_is_not_computed(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _count_extensions,
        )

        assert _count_extensions(None) is None

    def test_empty_map_is_not_computed(self):
        """Dung's timeout path returns ``{}`` — nothing was computed."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _count_extensions,
        )

        assert _count_extensions({}) is None


class TestThePopulationIsReDerivableFromTheState:
    """The issue asks the figure to be re-derivable: the population travels to
    the state with it, through the REAL ``UnifiedAnalysisState``."""

    async def test_state_entry_re_derives_overall_validity(self):
        output = await _invoke_formal_synthesis(
            "texte",
            _context(
                fol={
                    "consistent": True,
                    "logic_type": "first_order",
                    "formulas": _FOL_FORMULAS,
                },
                fol_solver={
                    "consistent": True,
                    "logic_type": "first_order",
                    "formulas": _FOL_FORMULAS,
                },
                pl={
                    "satisfiable": False,
                    "logic_type": "propositional",
                    "formulas": _OTHER_FORMULAS,
                },
                dl={"consistent": None},
            ),
        )
        state = UnifiedAnalysisState("texte")

        _write_formal_synthesis_to_state(output, state, {})

        entry = state.formal_synthesis_reports[-1]
        scores = [result["score"] for result in entry["decided_results"]]
        assert sum(scores) / len(scores) == entry["overall_validity"] == 0.5
        assert entry["not_evaluated"] == ["dl"]
        assert len(entry["decided_results"]) == 2
        # The population is symbolic only: no formula text is republished here.
        for result in entry["decided_results"]:
            assert "formulas" not in result

    async def test_writer_keeps_the_former_shape_when_the_producer_is_silent(self):
        """A pre-#2970 output dict must not grow phantom keys in the state."""
        state = UnifiedAnalysisState("texte")

        _write_formal_synthesis_to_state(
            {"summary": "s", "phase_results": {}, "overall_validity": 0.5},
            state,
            {},
        )

        entry = state.formal_synthesis_reports[-1]
        assert "decided_results" not in entry
        assert "not_evaluated" not in entry

    async def test_malformed_population_is_dropped_not_propagated(self):
        state = UnifiedAnalysisState("texte")

        _write_formal_synthesis_to_state(
            {
                "summary": "s",
                "phase_results": {},
                "overall_validity": 0.5,
                "decided_results": "not-a-list",
                "not_evaluated": {"not": "a list"},
            },
            state,
            {},
        )

        entry = state.formal_synthesis_reports[-1]
        assert "decided_results" not in entry
        assert "not_evaluated" not in entry
