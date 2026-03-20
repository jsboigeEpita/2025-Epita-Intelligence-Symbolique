"""Tests for SAT solver handler (PySAT integration).

Validates:
- PLSolverChoice enum and config extension
- SATHandler: variable mapping, Tseitin CNF conversion
- SAT solving (satisfiable / unsatisfiable)
- Entailment queries via SAT
- Solution enumeration
- MaxSAT solving
- MUS/MCS analysis (MARCO, if Z3 available)
- Solver benchmarking
- PLHandler SAT dispatch methods
"""

import pytest
from unittest.mock import patch, MagicMock

from argumentation_analysis.core.config import (
    PLSolverChoice,
    ArgAnalysisSettings,
)

try:
    from argumentation_analysis.agents.core.logic.sat_handler import (
        SATHandler,
        PYSAT_AVAILABLE,
        Z3_AVAILABLE,
    )
except ImportError:
    PYSAT_AVAILABLE = False
    Z3_AVAILABLE = False


# ──── Config Tests ────


class TestPLSolverChoiceEnum:
    """Tests for PLSolverChoice enum."""

    def test_pl_solver_values(self):
        assert PLSolverChoice.TWEETY.value == "tweety"
        assert PLSolverChoice.PYSAT.value == "pysat"

    def test_pl_solver_from_string(self):
        assert PLSolverChoice("pysat") == PLSolverChoice.PYSAT
        assert PLSolverChoice("tweety") == PLSolverChoice.TWEETY

    def test_invalid_pl_solver_raises(self):
        with pytest.raises(ValueError):
            PLSolverChoice("invalid")

    def test_settings_default_pl_solver(self):
        s = ArgAnalysisSettings()
        assert s.pl_solver == PLSolverChoice.TWEETY
        assert s.pysat_solver == "cadical195"

    def test_settings_env_override(self):
        with patch.dict(
            "os.environ",
            {
                "ARG_ANALYSIS_PL_SOLVER": "pysat",
                "ARG_ANALYSIS_PYSAT_SOLVER": "glucose42",
            },
        ):
            s = ArgAnalysisSettings()
            assert s.pl_solver == PLSolverChoice.PYSAT
            assert s.pysat_solver == "glucose42"


# ──── SATHandler Core Tests ────


@pytest.mark.skipif(not PYSAT_AVAILABLE, reason="PySAT not installed")
class TestSATHandlerInit:
    """Tests for SATHandler initialization."""

    def test_creation(self):
        handler = SATHandler()
        assert handler._default_solver == "cadical195"
        assert handler._var_map == {}
        assert handler._next_var == 1

    def test_custom_solver(self):
        handler = SATHandler(default_solver="glucose42")
        assert handler._default_solver == "glucose42"

    def test_supported_solvers(self):
        solvers = SATHandler.supported_solvers()
        assert "cadical195" in solvers
        assert "glucose42" in solvers
        assert "minisat22" in solvers
        assert len(solvers) == 6


@pytest.mark.skipif(not PYSAT_AVAILABLE, reason="PySAT not installed")
class TestVariableManagement:
    """Tests for variable mapping in SATHandler."""

    def test_get_var_creates_mapping(self):
        handler = SATHandler()
        v = handler._get_var("A")
        assert v == 1
        assert handler._var_map["A"] == 1

    def test_get_var_reuses_mapping(self):
        handler = SATHandler()
        v1 = handler._get_var("A")
        v2 = handler._get_var("A")
        assert v1 == v2

    def test_multiple_vars(self):
        handler = SATHandler()
        a = handler._get_var("A")
        b = handler._get_var("B")
        assert a != b
        assert handler._next_var == 3

    def test_reset_variables(self):
        handler = SATHandler()
        handler._get_var("A")
        handler._get_var("B")
        handler.reset_variables()
        assert handler._var_map == {}
        assert handler._next_var == 1

    def test_variable_map_property(self):
        handler = SATHandler()
        handler._get_var("X")
        handler._get_var("Y")
        vmap = handler.variable_map
        assert vmap == {"X": 1, "Y": 2}
        # Ensure it's a copy
        vmap["Z"] = 99
        assert "Z" not in handler._var_map

    def test_reverse_map(self):
        handler = SATHandler()
        handler._get_var("A")
        handler._get_var("B")
        rmap = handler.reverse_map
        assert rmap == {1: "A", 2: "B"}


# ──── Tseitin CNF Conversion Tests ────


@pytest.mark.skipif(not PYSAT_AVAILABLE, reason="PySAT not installed")
class TestTseitinConversion:
    """Tests for Tseitin formula-to-CNF transformation."""

    def test_single_atom(self):
        handler = SATHandler()
        clauses = handler.formulas_to_cnf(["A"])
        # Should produce at least one clause asserting A is true
        assert len(clauses) >= 1
        # The clause [1] means variable 1 (=A) is true
        assert [1] in clauses

    def test_negation(self):
        handler = SATHandler()
        clauses = handler.formulas_to_cnf(["! A"])
        # Should assert NOT A
        assert [-1] in clauses

    def test_conjunction(self):
        handler = SATHandler()
        clauses = handler.formulas_to_cnf(["A & B"])
        # A&B is satisfiable
        is_sat, model, _ = handler.solve(clauses)
        assert is_sat

    def test_disjunction(self):
        handler = SATHandler()
        clauses = handler.formulas_to_cnf(["A | B"])
        is_sat, model, _ = handler.solve(clauses)
        assert is_sat

    def test_implication(self):
        handler = SATHandler()
        clauses = handler.formulas_to_cnf(["A => B"])
        is_sat, _, _ = handler.solve(clauses)
        assert is_sat

    def test_biconditional(self):
        handler = SATHandler()
        clauses = handler.formulas_to_cnf(["A <=> B"])
        is_sat, _, _ = handler.solve(clauses)
        assert is_sat

    def test_contradiction_is_unsat(self):
        handler = SATHandler()
        clauses = handler.formulas_to_cnf(["A", "! A"])
        is_sat, model, _ = handler.solve(clauses)
        assert not is_sat
        assert model is None

    def test_complex_formula(self):
        handler = SATHandler()
        clauses = handler.formulas_to_cnf(["( A | B ) & ( ! A | C )"])
        is_sat, _, _ = handler.solve(clauses)
        assert is_sat

    def test_empty_formulas(self):
        handler = SATHandler()
        clauses = handler.formulas_to_cnf([])
        assert clauses == []

    def test_empty_string_skipped(self):
        handler = SATHandler()
        clauses = handler.formulas_to_cnf(["", "A"])
        assert len(clauses) >= 1

    def test_tokenizer(self):
        handler = SATHandler()
        tokens = handler._tokenize("A & ( B | ! C )")
        assert tokens == ["A", "&", "(", "B", "|", "!", "C", ")"]


# ──── SAT Solving Tests ────


@pytest.mark.skipif(not PYSAT_AVAILABLE, reason="PySAT not installed")
class TestSATSolving:
    """Tests for core SAT solving functionality."""

    def test_simple_sat(self):
        handler = SATHandler()
        # x1 OR x2, x1 OR NOT x2
        clauses = [[1, 2], [1, -2]]
        is_sat, model, stats = handler.solve(clauses)
        assert is_sat
        assert 1 in model or -1 in model
        assert stats["status"] == "SAT"
        assert "solve_time" in stats

    def test_simple_unsat(self):
        handler = SATHandler()
        # x1, NOT x1
        clauses = [[1], [-1]]
        is_sat, model, stats = handler.solve(clauses)
        assert not is_sat
        assert model is None
        assert stats["status"] == "UNSAT"

    def test_empty_clauses(self):
        handler = SATHandler()
        is_sat, model, stats = handler.solve([])
        assert is_sat

    def test_solve_with_assumptions(self):
        handler = SATHandler()
        clauses = [[1, 2], [-1, 2]]
        is_sat, model, stats = handler.solve(clauses, assumptions=[1])
        assert is_sat

    def test_unsat_with_assumptions(self):
        handler = SATHandler()
        clauses = [[1, 2]]
        is_sat, model, stats = handler.solve(clauses, assumptions=[-1, -2])
        assert not is_sat
        assert "unsat_core" in stats

    def test_solve_with_different_solvers(self):
        handler = SATHandler()
        clauses = [[1, 2], [-1, 2], [1, -2]]
        for solver in ["cadical195", "glucose42", "minisat22"]:
            try:
                is_sat, model, stats = handler.solve(clauses, solver_name=solver)
                assert is_sat
                assert stats["solver"] == solver
            except Exception:
                pytest.skip(f"Solver {solver} not available")


@pytest.mark.skipif(not PYSAT_AVAILABLE, reason="PySAT not installed")
class TestSolveFormulas:
    """Tests for formula-level SAT solving."""

    def test_satisfiable_formulas(self):
        handler = SATHandler()
        is_sat, model, stats = handler.solve_formulas(["A | B", "! A | C"])
        assert is_sat
        assert isinstance(model, dict)
        # Model should map proposition names to booleans
        for key in model:
            assert isinstance(key, str)
            assert isinstance(model[key], bool)

    def test_unsatisfiable_formulas(self):
        handler = SATHandler()
        is_sat, model, _ = handler.solve_formulas(["A", "! A"])
        assert not is_sat
        assert model is None

    def test_tautology(self):
        handler = SATHandler()
        is_sat, _, _ = handler.solve_formulas(["A | ! A"])
        assert is_sat


@pytest.mark.skipif(not PYSAT_AVAILABLE, reason="PySAT not installed")
class TestConsistencyCheck:
    """Tests for consistency checking via SAT."""

    def test_consistent_kb(self):
        handler = SATHandler()
        is_consistent, msg = handler.check_consistency(["A | B", "! A | C"])
        assert is_consistent
        assert "Consistent" in msg

    def test_inconsistent_kb(self):
        handler = SATHandler()
        is_consistent, msg = handler.check_consistency(["A", "! A"])
        assert not is_consistent
        assert "Inconsistent" in msg

    def test_empty_kb_consistent(self):
        handler = SATHandler()
        is_consistent, _ = handler.check_consistency([])
        assert is_consistent


@pytest.mark.skipif(not PYSAT_AVAILABLE, reason="PySAT not installed")
class TestEntailmentQuery:
    """Tests for entailment checking via SAT."""

    def test_simple_entailment(self):
        handler = SATHandler()
        # A, A => B  ⊨  B
        result = handler.query(["A", "A => B"], "B")
        assert result is True

    def test_no_entailment(self):
        handler = SATHandler()
        # A | B  ⊭  A
        result = handler.query(["A | B"], "A")
        assert result is False

    def test_tautology_entailment(self):
        handler = SATHandler()
        # Anything ⊨ A | !A
        result = handler.query(["X"], "A | ! A")
        assert result is True

    def test_contradiction_entails_everything(self):
        handler = SATHandler()
        # A, !A ⊨ B  (ex falso quodlibet)
        result = handler.query(["A", "! A"], "B")
        assert result is True


# ──── Solution Enumeration Tests ────


@pytest.mark.skipif(not PYSAT_AVAILABLE, reason="PySAT not installed")
class TestSolutionEnumeration:
    """Tests for enumerating multiple models."""

    def test_enumerate_solutions(self):
        handler = SATHandler()
        # x1 OR x2: has 3 solutions
        clauses = [[1, 2]]
        solutions = handler.enumerate_solutions(clauses, max_solutions=10)
        assert len(solutions) == 3

    def test_enumerate_with_limit(self):
        handler = SATHandler()
        clauses = [[1, 2]]
        solutions = handler.enumerate_solutions(clauses, max_solutions=2)
        assert len(solutions) == 2

    def test_enumerate_unsat(self):
        handler = SATHandler()
        clauses = [[1], [-1]]
        solutions = handler.enumerate_solutions(clauses)
        assert len(solutions) == 0

    def test_enumerate_single_solution(self):
        handler = SATHandler()
        clauses = [[1], [2]]  # x1=True, x2=True
        solutions = handler.enumerate_solutions(clauses)
        assert len(solutions) == 1


# ──── MaxSAT Tests ────


@pytest.mark.skipif(not PYSAT_AVAILABLE, reason="PySAT not installed")
class TestMaxSAT:
    """Tests for weighted MaxSAT solving."""

    def test_maxsat_basic(self):
        handler = SATHandler()
        hard = [[1, 2]]  # x1 OR x2 must hold
        soft = [
            ([1], 3),  # prefer x1=True (weight 3)
            ([-1], 1),  # prefer x1=False (weight 1)
        ]
        model, cost = handler.solve_maxsat(hard, soft)
        assert model is not None
        assert cost is not None
        # x1=True satisfies hard + soft[0] (weight 3), violates soft[1] (weight 1)
        # cost = 1 (unsatisfied soft weight)
        assert 1 in model  # x1 should be True

    def test_maxsat_all_hard_unsat(self):
        handler = SATHandler()
        hard = [[1], [-1]]  # contradictory hard clauses
        soft = [([2], 1)]
        model, cost = handler.solve_maxsat(hard, soft)
        assert model is None
        assert cost is None


# ──── MUS/MCS Tests ────


@pytest.mark.skipif(
    not PYSAT_AVAILABLE or not Z3_AVAILABLE,
    reason="PySAT or Z3 not installed",
)
class TestMUSAnalysis:
    """Tests for MUS (Minimal Unsatisfiable Subset) analysis."""

    def test_find_mus_on_inconsistent(self):
        handler = SATHandler()
        # 3 formulas, pair {0, 1} is a MUS
        mus_list = handler.find_mus(["A", "! A", "B"], max_mus=5)
        assert len(mus_list) >= 1
        # At least one MUS should be a subset of the formulas
        for mus in mus_list:
            assert len(mus) >= 1

    def test_find_mus_on_consistent(self):
        handler = SATHandler()
        mus_list = handler.find_mus(["A | B", "C"], max_mus=5)
        # Consistent — no MUS expected
        assert len(mus_list) == 0

    def test_z3_not_available_raises(self):
        handler = SATHandler()
        with patch(
            "argumentation_analysis.agents.core.logic.sat_handler.Z3_AVAILABLE",
            False,
        ):
            with pytest.raises(RuntimeError, match="Z3 not installed"):
                handler.find_mus(["A", "! A"])


# ──── Benchmark Tests ────


@pytest.mark.skipif(not PYSAT_AVAILABLE, reason="PySAT not installed")
class TestBenchmark:
    """Tests for solver benchmarking."""

    def test_benchmark_returns_results(self):
        handler = SATHandler()
        clauses = [[1, 2], [-1, 2], [1, -2]]
        results = handler.benchmark_solvers(clauses)
        assert isinstance(results, dict)
        # At least some solvers should have results
        assert len(results) >= 1
        for name, data in results.items():
            assert "status" in data


# ──── PLHandler SAT Dispatch Tests ────


@pytest.mark.skipif(not PYSAT_AVAILABLE, reason="PySAT not installed")
class TestPLHandlerSATDispatch:
    """Tests for PLHandler methods dispatching to PySAT."""

    @pytest.fixture
    def mock_pl_handler(self):
        """Create a PLHandler with mocked Tweety components."""
        with patch(
            "argumentation_analysis.agents.core.logic.pl_handler.jpype"
        ) as mock_jpype, patch(
            "argumentation_analysis.agents.core.logic.pl_handler.TweetyInitializer"
        ):
            mock_jpype.JClass.return_value = MagicMock
            mock_jpype.JString.return_value = "mock"
            mock_jpype.JException = Exception

            mock_init = MagicMock()
            mock_init.get_pl_parser.return_value = MagicMock()

            from argumentation_analysis.agents.core.logic.pl_handler import PLHandler

            handler = PLHandler(mock_init)
            return handler

    def test_pl_check_consistency_sat_consistent(self, mock_pl_handler):
        result = mock_pl_handler.pl_check_consistency_sat("A | B\nC")
        assert result is True

    def test_pl_check_consistency_sat_inconsistent(self, mock_pl_handler):
        result = mock_pl_handler.pl_check_consistency_sat("A\n! A")
        assert result is False

    def test_pl_check_consistency_sat_empty(self, mock_pl_handler):
        result = mock_pl_handler.pl_check_consistency_sat("")
        assert result is True

    def test_pl_query_sat_entails(self, mock_pl_handler):
        result = mock_pl_handler.pl_query_sat("A\nA => B", "B")
        assert result is True

    def test_pl_query_sat_not_entails(self, mock_pl_handler):
        result = mock_pl_handler.pl_query_sat("A | B", "A")
        assert result is False
