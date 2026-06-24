"""SAT solver handler — bridges propositional logic to PySAT/MARCO/MaxSAT.

Provides CNF conversion from Tweety PL formulas, SAT solving via multiple
backends (CaDiCaL, Glucose, MiniSat, etc.), MUS/MCS analysis, and MaxSAT.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

try:
    from pysat.solvers import Solver
    from pysat.formula import CNF, WCNF
    from pysat.examples.rc2 import RC2

    PYSAT_AVAILABLE = True
except ImportError:
    PYSAT_AVAILABLE = False

try:
    from z3 import (
        Bool,
        Not,
        Or,
        Implies,
        Solver as Z3Solver,
        sat,
        unsat,
        is_false,
        Z3_get_ast_id,
    )

    Z3_AVAILABLE = True
except ImportError:
    Z3_AVAILABLE = False

RECOMMENDED_SOLVERS = [
    "cadical195",
    "cryptominisat5",
    "glucose42",
    "maplechrono",
    "lingeling",
    "minisat22",
]


class SATHandler:
    """SAT/MaxSAT/MUS solver using PySAT and Z3-MARCO.

    This handler works at the CNF level (lists of integer-literal clauses)
    and also provides helpers for converting propositional formulas expressed
    as strings into CNF via Tseitin transformation.
    """

    def __init__(self, default_solver: str = "cadical195"):
        if not PYSAT_AVAILABLE:
            raise RuntimeError("PySAT is not installed. Run: pip install python-sat")
        self._default_solver = default_solver
        self._var_map: Dict[str, int] = {}
        self._next_var = 1

    # ── Variable management ──────────────────────────────────────────

    @staticmethod
    def supported_solvers() -> List[str]:
        return list(RECOMMENDED_SOLVERS)

    def _get_var(self, name: str) -> int:
        """Get or create a DIMACS variable number for a proposition name."""
        if name not in self._var_map:
            self._var_map[name] = self._next_var
            self._next_var += 1
        return self._var_map[name]

    def _new_aux_var(self) -> int:
        """Create auxiliary (Tseitin) variable."""
        v = self._next_var
        self._next_var += 1
        return v

    def reset_variables(self):
        """Clear variable mapping (between independent problems)."""
        self._var_map.clear()
        self._next_var = 1

    @property
    def variable_map(self) -> Dict[str, int]:
        """Current proposition→DIMACS mapping (read-only copy)."""
        return dict(self._var_map)

    @property
    def reverse_map(self) -> Dict[int, str]:
        """DIMACS→proposition name mapping."""
        return {v: k for k, v in self._var_map.items()}

    # ── Formula-to-CNF conversion (Tseitin) ──────────────────────────

    def formulas_to_cnf(self, formulas: List[str]) -> List[List[int]]:
        """Convert a list of propositional formula strings to CNF clauses.

        Supports: & (and), | (or), ! (not), => (implies), <=> (iff),
                  parentheses, proposition names.

        Uses Tseitin transformation to keep clause count linear.
        """
        self.reset_variables()
        all_clauses: List[List[int]] = []
        for formula in formulas:
            formula = formula.strip()
            if not formula:
                continue
            lit, clauses = self._tseitin(formula)
            all_clauses.extend(clauses)
            all_clauses.append([lit])  # assert the formula is true
        return all_clauses

    def _tokenize(self, formula: str) -> List[str]:
        """Tokenize a PL formula string.

        SAT-native grammar uses the SINGLE-form operators ``&``, ``|``, ``!``,
        ``=>``, ``<=>``. Tweety's PlParser instead requires the DOUBLE-form
        ``&&``/``||`` (#1132), so formulas normalized for Tweety would silently
        corrupt SAT tokenization (``&&`` → ``['&','&']`` → ``a && !a`` parsed
        as the atom ``&`` and wrongly reported consistent). Accept both forms
        here and canonicalise to single-form so the SAT path is robust
        regardless of upstream normalization.
        """
        # Collapse any run of & or | to the single-form operator first, then
        # space operators/parens. Longest-first so <=> wins =>.
        formula = re.sub(r"&+", "&", formula)
        formula = re.sub(r"\|+", "|", formula)
        formula = re.sub(r"(<=>|=>|&|\||!|\(|\))", r" \1 ", formula)
        return [t for t in formula.split() if t]

    def _tseitin(self, formula: str) -> Tuple[int, List[List[int]]]:
        """Tseitin transformation: returns (root_literal, cnf_clauses)."""
        tokens = self._tokenize(formula)
        pos = [0]
        clauses: List[List[int]] = []

        def parse_equiv():
            left = parse_implies()
            while pos[0] < len(tokens) and tokens[pos[0]] == "<=>":
                pos[0] += 1
                right = parse_implies()
                aux = self._new_aux_var()
                # aux <=> (left <=> right)
                # Encoded as: (aux => (left => right)) & (aux => (right => left)) &
                #              ((left => right) & (right => left) => aux)
                # Simplified CNF:
                clauses.extend(
                    [
                        [-aux, -left, right],
                        [-aux, left, -right],
                        [aux, left, right],
                        [aux, -left, -right],
                    ]
                )
                left = aux
            return left

        def parse_implies():
            left = parse_or()
            while pos[0] < len(tokens) and tokens[pos[0]] == "=>":
                pos[0] += 1
                right = parse_or()
                aux = self._new_aux_var()
                # aux <=> (left => right) i.e. aux <=> (!left | right)
                clauses.extend(
                    [
                        [-aux, -left, right],
                        [aux, left],
                        [aux, -right],
                    ]
                )
                left = aux
            return left

        def parse_or():
            left = parse_and()
            or_lits = [left]
            while pos[0] < len(tokens) and tokens[pos[0]] == "|":
                pos[0] += 1
                or_lits.append(parse_and())
            if len(or_lits) == 1:
                return left
            aux = self._new_aux_var()
            # aux <=> (l1 | l2 | ...)
            clauses.append([-aux] + or_lits)
            for lit in or_lits:
                clauses.append([aux, -lit])
            return aux

        def parse_and():
            left = parse_not()
            and_lits = [left]
            while pos[0] < len(tokens) and tokens[pos[0]] == "&":
                pos[0] += 1
                and_lits.append(parse_not())
            if len(and_lits) == 1:
                return left
            aux = self._new_aux_var()
            # aux <=> (l1 & l2 & ...)
            clauses.append([aux] + [-lit for lit in and_lits])
            for lit in and_lits:
                clauses.append([-aux, lit])
            return aux

        def parse_not():
            if pos[0] < len(tokens) and tokens[pos[0]] == "!":
                pos[0] += 1
                inner = parse_not()
                return -inner
            return parse_atom()

        def parse_atom():
            if pos[0] >= len(tokens):
                raise ValueError("Unexpected end of formula")
            token = tokens[pos[0]]
            if token == "(":
                pos[0] += 1
                result = parse_equiv()
                if pos[0] < len(tokens) and tokens[pos[0]] == ")":
                    pos[0] += 1
                return result
            pos[0] += 1
            return self._get_var(token)

        root = parse_equiv()
        return root, clauses

    # ── SAT solving ──────────────────────────────────────────────────

    def solve(
        self,
        clauses: List[List[int]],
        solver_name: Optional[str] = None,
        assumptions: Optional[List[int]] = None,
    ) -> Tuple[bool, Optional[List[int]], dict]:
        """Solve a SAT problem.

        Returns (is_sat, model_or_none, statistics).
        """
        solver_name = solver_name or self._default_solver
        import time

        stats = {
            "solver": solver_name,
            "num_clauses": len(clauses),
            "num_variables": max(
                (abs(lit) for clause in clauses for lit in clause), default=0
            ),
        }
        start = time.time()
        try:
            with Solver(name=solver_name, bootstrap_with=clauses) as s:
                result = s.solve(assumptions=assumptions) if assumptions else s.solve()
                stats["solve_time"] = time.time() - start
                if result:
                    model = s.get_model()
                    stats["status"] = "SAT"
                    return True, model, stats
                else:
                    stats["status"] = "UNSAT"
                    if assumptions:
                        stats["unsat_core"] = s.get_core()
                    return False, None, stats
        except Exception as e:
            stats["solve_time"] = time.time() - start
            stats["error"] = str(e)
            return False, None, stats

    def solve_formulas(
        self,
        formulas: List[str],
        solver_name: Optional[str] = None,
    ) -> Tuple[bool, Optional[Dict[str, bool]], dict]:
        """Convert formulas to CNF and solve. Returns human-readable model."""
        clauses = self.formulas_to_cnf(formulas)
        is_sat, model, stats = self.solve(clauses, solver_name)
        if model:
            rmap = self.reverse_map
            named_model = {}
            for lit in model:
                var = abs(lit)
                if var in rmap:
                    named_model[rmap[var]] = lit > 0
            return is_sat, named_model, stats
        return is_sat, None, stats

    def check_consistency(
        self,
        formulas: List[str],
        solver_name: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """Check if a set of propositional formulas is consistent (satisfiable)."""
        is_sat, model, stats = self.solve_formulas(formulas, solver_name)
        if is_sat:
            return True, f"Consistent (SAT). Model: {model}"
        return False, f"Inconsistent (UNSAT). Solver: {stats.get('solver')}"

    def query(
        self,
        kb_formulas: List[str],
        query_formula: str,
        solver_name: Optional[str] = None,
    ) -> bool:
        """Check if KB entails query (KB ∧ ¬query is UNSAT)."""
        negated = f"! ( {query_formula} )"
        all_formulas = list(kb_formulas) + [negated]
        is_sat, _, _ = self.solve_formulas(all_formulas, solver_name)
        return not is_sat  # entails iff negation is UNSAT

    def enumerate_solutions(
        self,
        clauses: List[List[int]],
        solver_name: Optional[str] = None,
        max_solutions: int = 10,
    ) -> List[List[int]]:
        """Enumerate up to max_solutions models."""
        solver_name = solver_name or self._default_solver
        solutions = []
        with Solver(name=solver_name, bootstrap_with=clauses) as s:
            while len(solutions) < max_solutions:
                if not s.solve():
                    break
                model = s.get_model()
                solutions.append(model)
                s.add_clause([-lit for lit in model])
        return solutions

    # ── MaxSAT ───────────────────────────────────────────────────────

    def solve_maxsat(
        self,
        hard_clauses: List[List[int]],
        soft_clauses: List[Tuple[List[int], int]],
    ) -> Tuple[Optional[List[int]], Optional[int]]:
        """Solve a weighted MaxSAT problem.

        Args:
            hard_clauses: Must be satisfied.
            soft_clauses: List of (clause, weight) pairs.

        Returns:
            (model, cost) or (None, None) if UNSAT.
        """
        wcnf = WCNF()
        for clause in hard_clauses:
            wcnf.append(clause)
        for clause, weight in soft_clauses:
            wcnf.append(clause, weight=weight)
        with RC2(wcnf) as solver:
            model = solver.compute()
            if model is None:
                return None, None
            return model, solver.cost

    # ── MUS/MCS (MARCO via Z3) ───────────────────────────────────────

    def find_mus(
        self,
        formulas: List[str],
        max_mus: int = 5,
    ) -> List[List[int]]:
        """Find Minimal Unsatisfiable Subsets using MARCO algorithm.

        Returns list of MUS (each MUS is a list of formula indices).
        Requires z3-solver.
        """
        if not Z3_AVAILABLE:
            raise RuntimeError("Z3 not installed. Run: pip install z3-solver")

        cnf_clauses = self.formulas_to_cnf(formulas)
        if not cnf_clauses:
            return []

        # Convert clauses to Z3 constraints
        z3_vars = {}
        constraints = []
        for clause in cnf_clauses:
            z3_lits = []
            for lit in clause:
                var_id = abs(lit)
                if var_id not in z3_vars:
                    z3_vars[var_id] = Bool(f"v{var_id}")
                z3_lits.append(z3_vars[var_id] if lit > 0 else Not(z3_vars[var_id]))
            constraints.append(Or(z3_lits) if len(z3_lits) > 1 else z3_lits[0])

        return self._marco_mus(constraints, max_mus)

    def _marco_mus(self, constraints, max_mus: int) -> List[List[int]]:
        """MARCO MUS enumeration on Z3 constraints."""
        n = len(constraints)
        sub_solver = Z3Solver()
        ctrl_vars = [Bool(f"c{i}") for i in range(n)]
        for i in range(n):
            sub_solver.add(Implies(ctrl_vars[i], constraints[i]))

        map_solver = Z3Solver()

        mus_list = []
        while len(mus_list) < max_mus:
            if map_solver.check() == unsat:
                break
            seed = set(range(n))
            model = map_solver.model()
            for x in model:
                if is_false(model[x]):
                    name = x.name()
                    if name.startswith("x"):
                        idx = int(name[1:])
                        if idx in seed:
                            seed.remove(idx)

            assumptions = [ctrl_vars[i] for i in seed]
            if sub_solver.check(assumptions) == sat:
                # MSS — block down
                map_solver.add(Or([Bool(f"x{i}") for i in range(n) if i not in seed]))
            else:
                # MUS — shrink and block up
                core_ids = set()
                for c in sub_solver.unsat_core():
                    cid = Z3_get_ast_id(c.ctx.ref(), c.as_ast())
                    for i, cv in enumerate(ctrl_vars):
                        if Z3_get_ast_id(cv.ctx.ref(), cv.as_ast()) == cid:
                            core_ids.add(i)
                            break
                mus_list.append(sorted(core_ids))
                map_solver.add(Or([Not(Bool(f"x{i}")) for i in core_ids]))

        return mus_list

    # ── Benchmark ────────────────────────────────────────────────────

    def benchmark_solvers(
        self, clauses: List[List[int]], timeout: float = 10.0
    ) -> Dict[str, dict]:
        """Benchmark all available solvers on a problem."""
        import time

        results = {}
        for solver_name in RECOMMENDED_SOLVERS:
            try:
                start = time.time()
                is_sat, _, stats = self.solve(clauses, solver_name)
                elapsed = time.time() - start
                if elapsed > timeout:
                    results[solver_name] = {"status": "TIMEOUT", "time": elapsed}
                else:
                    results[solver_name] = {
                        "status": stats.get("status", "UNKNOWN"),
                        "time": elapsed,
                    }
            except Exception as e:
                results[solver_name] = {"status": "ERROR", "error": str(e)}
        return results


async def compare_pl_backends(formulas: List[str]) -> Dict[str, Any]:
    """Run ALL available PL/SAT backends on the same formula set and compare.

    FP-20 #1244, Epic #1191, mandate R468 ("tous les solvers handy … pour
    comparer les résultats"). Each backend runs INDEPENDENTLY on the same
    formulas; verdicts are cross-validated. DISAGREEMENT is surfaced explicitly
    and NEVER silently reconciled — the comparison is the point (#1019).

    Backends:
    - pysat/cadical195, pysat/cryptominisat5, pysat/glucose42, pysat/maplechrono,
      pysat/lingeling, pysat/minisat22  — Python-side DPLL/CDCL solvers (PySAT)
    - sat4j    — Pure-Java Tweety 1.29 Sat4jSolver (SAT4J library, DPLL)
    - tweety_pl — Pure-Java Tweety 1.29 SimplePlReasoner (model enumeration, cross-check)

    Returns a JSON-serialisable dict::

        {
          "backends": {name: {"verdict": Optional[bool], "note": str,
                              "elapsed_ms": float, "available": bool}},
          "decided":  {name: bool, ...},  # only backends that returned a bool
          "agreement": Optional[bool],    # True=all agree, False=disagree, None<2 decided
          "disagreement": [str, ...],     # explicit, never auto-reconciled
        }
    """
    import time

    backends: Dict[str, Any] = {}

    def _record(name: str, fn: Any, *args: Any) -> None:
        """Run fn(*args) synchronously, record verdict + timing into backends."""
        start = time.perf_counter()
        try:
            verdict, note = fn(*args)
            elapsed = (time.perf_counter() - start) * 1000.0
            backends[name] = {
                "verdict": verdict,
                "note": note,
                "elapsed_ms": round(elapsed, 1),
                "available": True,
            }
        except Exception as exc:
            elapsed = (time.perf_counter() - start) * 1000.0
            backends[name] = {
                "verdict": None,
                "note": f"unavailable: {exc}",
                "elapsed_ms": round(elapsed, 1),
                "available": False,
            }

    def _pysat_check(solver_name: str) -> Tuple[bool, str]:
        handler = SATHandler(solver_name)
        clauses = handler.formulas_to_cnf(list(formulas))
        is_sat, _, stats = handler.solve(clauses, solver_name)
        if "error" in stats:
            raise RuntimeError(stats["error"])
        if is_sat:
            return True, f"Consistent (SAT) via pysat/{solver_name}"
        return False, f"Inconsistent (UNSAT) via pysat/{solver_name}"

    def _sat4j_check() -> Tuple[bool, str]:
        import jpype

        if not jpype.isJVMStarted():
            raise RuntimeError("JVM not started")
        PlParser = jpype.JClass("org.tweetyproject.logics.pl.parser.PlParser")
        PlBeliefSet = jpype.JClass("org.tweetyproject.logics.pl.syntax.PlBeliefSet")
        Sat4jSolver = jpype.JClass("org.tweetyproject.logics.pl.sat.Sat4jSolver")
        parser = PlParser()
        kb = PlBeliefSet()
        for f in formulas:
            tweety_f = re.sub(r"&+", "&&", re.sub(r"\|+", "||", f.strip()))
            if tweety_f:
                kb.add(parser.parseFormula(tweety_f))
        verdict = bool(Sat4jSolver().isConsistent(kb))
        return verdict, f"Sat4jSolver (Tweety 1.29): {'consistent' if verdict else 'inconsistent'}"

    def _tweety_pl_check() -> Tuple[bool, str]:
        import jpype

        if not jpype.isJVMStarted():
            raise RuntimeError("JVM not started")
        PlParser = jpype.JClass("org.tweetyproject.logics.pl.parser.PlParser")
        PlBeliefSet = jpype.JClass("org.tweetyproject.logics.pl.syntax.PlBeliefSet")
        SimplePlReasoner = jpype.JClass(
            "org.tweetyproject.logics.pl.reasoner.SimplePlReasoner"
        )
        Contradiction = jpype.JClass(
            "org.tweetyproject.logics.pl.syntax.Contradiction"
        )
        parser = PlParser()
        kb = PlBeliefSet()
        for f in formulas:
            tweety_f = re.sub(r"&+", "&&", re.sub(r"\|+", "||", f.strip()))
            if tweety_f:
                kb.add(parser.parseFormula(tweety_f))
        entails_contradiction = bool(SimplePlReasoner().query(kb, Contradiction()))
        verdict = not entails_contradiction
        return verdict, f"SimplePlReasoner (model enumeration): {'consistent' if verdict else 'inconsistent'}"

    # ── PySAT backends (Python-side, sequential) ──────────────────────
    if not PYSAT_AVAILABLE:
        for solver_name in RECOMMENDED_SOLVERS:
            backends[f"pysat/{solver_name}"] = {
                "verdict": None,
                "note": "PySAT not installed",
                "elapsed_ms": 0.0,
                "available": False,
            }
    else:
        for solver_name in RECOMMENDED_SOLVERS:
            _record(f"pysat/{solver_name}", _pysat_check, solver_name)

    # ── Java backends (Tweety 1.29, lazy jpype, sequential) ───────────
    _record("sat4j", _sat4j_check)
    _record("tweety_pl", _tweety_pl_check)

    decided = {
        name: b["verdict"]
        for name, b in backends.items()
        if isinstance(b["verdict"], bool)
    }
    verdict_values = set(decided.values())
    agreement: Optional[bool] = None if len(decided) < 2 else (len(verdict_values) <= 1)

    disagreement: List[str] = []
    if agreement is False:
        consistent = sorted(n for n, v in decided.items() if v is True)
        inconsistent = sorted(n for n, v in decided.items() if not v)
        disagreement.append(
            f"DISAGREEMENT (NOT reconciled): {consistent} report CONSISTENT, "
            f"{inconsistent} report INCONSISTENT. "
            "All PySAT and Sat4j backends are sound and complete for propositional "
            "logic; disagreement here indicates a formula parsing or solver invocation "
            "discrepancy. Inspect the per-backend notes before drawing a conclusion."
        )

    return {
        "backends": backends,
        "decided": decided,
        "agreement": agreement,
        "disagreement": disagreement,
    }
