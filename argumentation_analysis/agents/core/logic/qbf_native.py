"""Pure-Python QBF (Quantified Boolean Formula) solver — JVM-free fallback.

Provides basic QBF reasoning without requiring Tweety/JPype:
- Naive truth-table enumeration for small formulas
- Argumentation-to-QBF conversion (credulous/skeptical acceptance)
- Formula construction and evaluation

This complements the JVM-based QBFHandler for environments where
Java is not available.
"""

import itertools
import logging
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# ── Formula AST ──────────────────────────────────────────────


class QBFFormula:
    """Base class for QBF formula AST nodes."""

    def evaluate(self, assignment: Dict[str, bool]) -> bool:
        raise NotImplementedError


class Var(QBFFormula):
    """Propositional variable."""

    def __init__(self, name: str):
        self.name = name

    def evaluate(self, assignment: Dict[str, bool]) -> bool:
        return assignment.get(self.name, False)

    def variables(self) -> Set[str]:
        return {self.name}

    def __repr__(self):
        return self.name


class Not(QBFFormula):
    """Negation."""

    def __init__(self, inner: QBFFormula):
        self.inner = inner

    def evaluate(self, assignment: Dict[str, bool]) -> bool:
        return not self.inner.evaluate(assignment)

    def variables(self) -> Set[str]:
        return self.inner.variables()

    def __repr__(self):
        return f"!{self.inner}"


class And(QBFFormula):
    """Conjunction."""

    def __init__(self, left: QBFFormula, right: QBFFormula):
        self.left = left
        self.right = right

    def evaluate(self, assignment: Dict[str, bool]) -> bool:
        return self.left.evaluate(assignment) and self.right.evaluate(assignment)

    def variables(self) -> Set[str]:
        return self.left.variables() | self.right.variables()

    def __repr__(self):
        return f"({self.left} & {self.right})"


class Or(QBFFormula):
    """Disjunction."""

    def __init__(self, left: QBFFormula, right: QBFFormula):
        self.left = left
        self.right = right

    def evaluate(self, assignment: Dict[str, bool]) -> bool:
        return self.left.evaluate(assignment) or self.right.evaluate(assignment)

    def variables(self) -> Set[str]:
        return self.left.variables() | self.right.variables()

    def __repr__(self):
        return f"({self.left} | {self.right})"


class Implies(QBFFormula):
    """Implication."""

    def __init__(self, left: QBFFormula, right: QBFFormula):
        self.left = left
        self.right = right

    def evaluate(self, assignment: Dict[str, bool]) -> bool:
        return (not self.left.evaluate(assignment)) or self.right.evaluate(assignment)

    def variables(self) -> Set[str]:
        return self.left.variables() | self.right.variables()

    def __repr__(self):
        return f"({self.left} => {self.right})"


# ── Quantified formulas ─────────────────────────────────────


class ForAll(QBFFormula):
    """Universal quantifier: ∀vars. formula."""

    def __init__(self, vars: List[str], formula: QBFFormula):
        self.vars = vars
        self.formula = formula

    def evaluate(self, assignment: Dict[str, bool]) -> bool:
        return _evaluate_forall(self.vars, self.formula, assignment)

    def variables(self) -> Set[str]:
        return self.formula.variables() - set(self.vars)

    def __repr__(self):
        return f"∀{','.join(self.vars)}.{self.formula}"


class Exists(QBFFormula):
    """Existential quantifier: ∃vars. formula."""

    def __init__(self, vars: List[str], formula: QBFFormula):
        self.vars = vars
        self.formula = formula

    def evaluate(self, assignment: Dict[str, bool]) -> bool:
        return _evaluate_exists(self.vars, self.formula, assignment)

    def variables(self) -> Set[str]:
        return self.formula.variables() - set(self.vars)

    def __repr__(self):
        return f"∃{','.join(self.vars)}.{self.formula}"


def _evaluate_forall(
    vars: List[str], formula: QBFFormula, base_assignment: Dict[str, bool]
) -> bool:
    """Check formula holds for ALL assignments of vars."""
    for combo in itertools.product([True, False], repeat=len(vars)):
        assignment = dict(base_assignment)
        for var, val in zip(vars, combo):
            assignment[var] = val
        if not formula.evaluate(assignment):
            return False
    return True


def _evaluate_exists(
    vars: List[str], formula: QBFFormula, base_assignment: Dict[str, bool]
) -> bool:
    """Check formula holds for SOME assignment of vars."""
    for combo in itertools.product([True, False], repeat=len(vars)):
        assignment = dict(base_assignment)
        for var, val in zip(vars, combo):
            assignment[var] = val
        if formula.evaluate(assignment):
            return True
    return False


# ── Formula parser ───────────────────────────────────────────


def parse_formula(s: str) -> QBFFormula:
    """Parse a simple propositional formula string.

    Supports: ! (negation), & (and), | (or), => (implies).
    Operator precedence: ! > & > | > =>
    No parentheses support (keep formulas simple).
    """
    s = s.strip()
    # Implication (lowest precedence, right-associative)
    if "=>" in s:
        parts = s.split("=>", 1)
        return Implies(parse_formula(parts[0]), parse_formula(parts[1]))
    # Disjunction
    if "|" in s:
        parts = s.split("|")
        result = parse_formula(parts[0])
        for p in parts[1:]:
            result = Or(result, parse_formula(p))
        return result
    # Conjunction
    if "&" in s:
        parts = s.split("&")
        result = parse_formula(parts[0])
        for p in parts[1:]:
            result = And(result, parse_formula(p))
        return result
    # Negation
    if s.startswith("!"):
        return Not(parse_formula(s[1:]))
    # Variable
    return Var(s.strip())


# ── QBF solver ───────────────────────────────────────────────


def check_qbf(
    quantifiers: List[Dict[str, Any]],
    formula_str: str,
) -> Tuple[bool, str]:
    """Check QBF validity using naive enumeration.

    Args:
        quantifiers: List of {"type": "forall"|"exists", "vars": ["x","y"]}.
        formula_str: The matrix formula (propositional, using var names).

    Returns:
        (is_valid, message)
    """
    matrix = parse_formula(formula_str)

    # Build nested quantified formula (outermost first)
    formula = matrix
    for q in reversed(quantifiers):
        q_type = q.get("type", "forall")
        q_vars = q.get("vars", [])
        if q_type == "exists":
            formula = Exists(q_vars, formula)
        else:
            formula = ForAll(q_vars, formula)

    result = formula.evaluate({})
    return result, f"QBF {'VALID' if result else 'INVALID'}: {formula_str}"


def analyze_qbf(
    quantifiers: List[Dict[str, Any]],
    formula_str: str,
) -> Dict[str, Any]:
    """Full QBF analysis with statistics.

    Args:
        quantifiers: List of {"type": "forall"|"exists", "vars": ["x","y"]}.
        formula_str: The matrix formula.

    Returns:
        Dict with validity result and statistics.
    """
    is_valid, message = check_qbf(quantifiers, formula_str)
    all_vars = []
    for q in quantifiers:
        all_vars.extend(q.get("vars", []))
    return {
        "formula": formula_str,
        "quantifiers": quantifiers,
        "valid": is_valid,
        "message": message,
        "statistics": {
            "quantifier_count": len(quantifiers),
            "variable_count": len(all_vars),
            "search_space": 2 ** len(all_vars),
            "handler": "qbf_native",
            "reasoner": "naive_enumeration",
        },
    }


# ── Argumentation-to-QBF conversion ─────────────────────────


def credulous_acceptance_qbf(
    arguments: List[str],
    attacks: List[List[str]],
    target: str,
) -> Dict[str, Any]:
    """Check if an argument is credulously accepted (∃ an admissible set containing it).

    Converts to QBF: ∃x₁...∃xₙ. (conflict_free ∧ defends_all ∧ target_in)

    An argument is credulously accepted iff there exists an admissible extension
    containing it.

    Args:
        arguments: List of argument names.
        attacks: List of [attacker, target] pairs.
        target: The argument to check acceptance for.

    Returns:
        Dict with acceptance result and QBF details.
    """
    if target not in arguments:
        return {
            "target": target,
            "accepted": False,
            "reason": f"Argument '{target}' not in framework",
            "method": "credulous_qbf",
        }

    # Build attack lookup
    attacked_by: Dict[str, Set[str]] = {a: set() for a in arguments}
    for atk in attacks:
        if len(atk) >= 2 and atk[1] in attacked_by:
            attacked_by[atk[1]].add(atk[0])

    # Enumerate all subsets (brute force for small frameworks)
    n = len(arguments)
    if n > 15:
        return {
            "target": target,
            "accepted": None,
            "reason": f"Framework too large ({n} args) for naive enumeration",
            "method": "credulous_qbf",
        }

    for bits in range(1 << n):
        ext = {arguments[i] for i in range(n) if bits & (1 << i)}

        if target not in ext:
            continue

        # Check conflict-free
        conflict_free = True
        for atk in attacks:
            if len(atk) >= 2 and atk[0] in ext and atk[1] in ext:
                conflict_free = False
                break
        if not conflict_free:
            continue

        # Check admissibility: every attacker of a member is counter-attacked
        admissible = True
        for member in ext:
            for attacker in attacked_by.get(member, set()):
                if attacker not in ext:
                    # Must be counter-attacked by someone in ext
                    counter_attacked = any(
                        a[0] in ext and a[1] == attacker
                        for a in attacks
                        if len(a) >= 2
                    )
                    if not counter_attacked:
                        admissible = False
                        break
            if not admissible:
                break

        if admissible:
            return {
                "target": target,
                "accepted": True,
                "witness_extension": sorted(ext),
                "reason": f"Found admissible extension containing {target}",
                "method": "credulous_qbf",
            }

    return {
        "target": target,
        "accepted": False,
        "reason": f"No admissible extension contains {target}",
        "method": "credulous_qbf",
    }


def skeptical_acceptance_qbf(
    arguments: List[str],
    attacks: List[List[str]],
    target: str,
) -> Dict[str, Any]:
    """Check if an argument is skeptically accepted (in ALL preferred extensions).

    An argument is skeptically accepted iff it is in every preferred extension.

    Args:
        arguments: List of argument names.
        attacks: List of [attacker, target] pairs.
        target: The argument to check acceptance for.

    Returns:
        Dict with acceptance result and QBF details.
    """
    if target not in arguments:
        return {
            "target": target,
            "accepted": False,
            "reason": f"Argument '{target}' not in framework",
            "method": "skeptical_qbf",
        }

    # Use the Dung native engine for preferred extensions
    try:
        from argumentation_analysis.agents.core.logic.dung_native import DungFramework

        df = DungFramework.from_args_and_attacks(arguments, attacks)
        preferred = df.preferred_extensions()

        if not preferred:
            return {
                "target": target,
                "accepted": False,
                "reason": "No preferred extensions found",
                "method": "skeptical_qbf",
            }

        in_all = all(target in ext for ext in preferred)
        return {
            "target": target,
            "accepted": in_all,
            "preferred_extensions": [sorted(ext) for ext in preferred],
            "reason": (
                f"{target} is in ALL {len(preferred)} preferred extensions"
                if in_all
                else f"{target} is NOT in all preferred extensions"
            ),
            "method": "skeptical_qbf",
        }
    except ImportError:
        return {
            "target": target,
            "accepted": None,
            "reason": "DungFramework not available for skeptical acceptance",
            "method": "skeptical_qbf",
        }


# ── Classic examples ─────────────────────────────────────────


def example_simple_validity():
    """∀x. (x | !x) — always valid (tautology)."""
    return analyze_qbf(
        [{"type": "forall", "vars": ["x"]}],
        "x | !x",
    )


def example_simple_satisfiability():
    """∃x. (x & !x) — never satisfiable (contradiction)."""
    return analyze_qbf(
        [{"type": "exists", "vars": ["x"]}],
        "x & !x",
    )


def example_mixed_quantifiers():
    """∀x. ∃y. (x => y) — valid: for any x, choose y=True."""
    return analyze_qbf(
        [
            {"type": "forall", "vars": ["x"]},
            {"type": "exists", "vars": ["y"]},
        ],
        "x => y",
    )


def example_argumentation_acceptance():
    """Credulous acceptance in Nixon Diamond framework."""
    return credulous_acceptance_qbf(
        arguments=["a", "b", "c"],
        attacks=[["a", "b"], ["b", "a"]],
        target="a",
    )
