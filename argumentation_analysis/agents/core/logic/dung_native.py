"""
Pure-Python Dung argumentation framework — JVM-free alternative to Tweety.

Implements 5 classical semantics (grounded, preferred, stable, complete,
admissible) without requiring Java/JPype. Serves as fallback when
TweetyBridge is unavailable.

Integrated from student project 1.2.1 (Da Silva, Badraoui, Jeyakumar),
with algorithms rewritten in pure Python (the original delegated all
computation to Tweety via JPype).

Reference: P.M. Dung, "On the acceptability of arguments and its
fundamental role in nonmonotonic reasoning, logic programming and
n-person games", Artificial Intelligence, 77(2), 1995.
"""

import logging
from itertools import combinations
from typing import Dict, FrozenSet, List, Optional, Set, Tuple

logger = logging.getLogger("DungNative")


class DungFramework:
    """Pure-Python implementation of Dung's argumentation framework.

    Usage:
        fw = DungFramework()
        fw.add_argument("a")
        fw.add_argument("b")
        fw.add_attack("a", "b")
        ext = fw.grounded_extension()  # {"a"}
    """

    def __init__(self) -> None:
        self.arguments: Set[str] = set()
        self.attacks: Set[Tuple[str, str]] = set()

    def add_argument(self, name: str) -> None:
        """Add an argument to the framework."""
        self.arguments.add(name)

    def add_attack(self, source: str, target: str) -> None:
        """Add an attack relation. Both arguments must exist."""
        if source not in self.arguments:
            self.add_argument(source)
        if target not in self.arguments:
            self.add_argument(target)
        self.attacks.add((source, target))

    def attackers_of(self, arg: str) -> Set[str]:
        """Get all arguments that attack the given argument."""
        return {src for src, tgt in self.attacks if tgt == arg}

    def attacked_by(self, arg: str) -> Set[str]:
        """Get all arguments attacked by the given argument."""
        return {tgt for src, tgt in self.attacks if src == arg}

    def is_attacked_by_set(self, arg: str, s: FrozenSet[str]) -> bool:
        """Check if arg is attacked by any member of set s."""
        return bool(self.attackers_of(arg) & s)

    def is_conflict_free(self, s: FrozenSet[str]) -> bool:
        """Check if a set is conflict-free (no internal attacks)."""
        for a in s:
            for b in s:
                if (a, b) in self.attacks:
                    return False
        return True

    def defends(self, s: FrozenSet[str], arg: str) -> bool:
        """Check if set s defends argument arg.

        s defends arg iff every attacker of arg is attacked by some member of s.
        """
        for attacker in self.attackers_of(arg):
            if not self.is_attacked_by_set(attacker, s):
                return False
        return True

    def characteristic_function(self, s: FrozenSet[str]) -> FrozenSet[str]:
        """Dung's characteristic function F(S).

        Returns the set of all arguments defended by S.
        """
        return frozenset(arg for arg in self.arguments if self.defends(s, arg))

    # --- Semantics ---

    def grounded_extension(self) -> FrozenSet[str]:
        """Compute the grounded extension (least fixed point of F).

        Iteratively applies the characteristic function starting from
        the empty set until a fixed point is reached.
        """
        current = frozenset()
        while True:
            next_set = self.characteristic_function(current)
            if next_set == current:
                return current
            current = next_set

    def admissible_sets(self) -> List[FrozenSet[str]]:
        """Compute all admissible sets.

        A set S is admissible iff it is conflict-free and defends all its members.
        """
        result = [frozenset()]  # empty set is always admissible
        args_list = sorted(self.arguments)

        for size in range(1, len(args_list) + 1):
            for combo in combinations(args_list, size):
                s = frozenset(combo)
                if self.is_conflict_free(s) and all(
                    self.defends(s, arg) for arg in s
                ):
                    result.append(s)
        return result

    def complete_extensions(self) -> List[FrozenSet[str]]:
        """Compute all complete extensions.

        A set S is a complete extension iff it is admissible and contains
        every argument it defends (S = F(S)).
        """
        result = []
        for s in self.admissible_sets():
            if self.characteristic_function(s) == s:
                result.append(s)
        return result

    def preferred_extensions(self) -> List[FrozenSet[str]]:
        """Compute all preferred extensions.

        Preferred extensions are maximal (w.r.t. set inclusion) complete extensions.
        """
        complete = self.complete_extensions()
        preferred = []
        for s in complete:
            if not any(s < other for other in complete):
                preferred.append(s)
        return preferred if preferred else [frozenset()]

    def stable_extensions(self) -> List[FrozenSet[str]]:
        """Compute all stable extensions.

        A set S is stable iff it is conflict-free and attacks every argument
        not in S.
        """
        result = []
        args_list = sorted(self.arguments)

        for size in range(len(args_list) + 1):
            for combo in combinations(args_list, size):
                s = frozenset(combo)
                if not self.is_conflict_free(s):
                    continue
                # Check that every arg not in s is attacked by s
                outside = self.arguments - s
                if all(self.is_attacked_by_set(arg, s) for arg in outside):
                    result.append(s)

        return result

    def get_argument_status(self, arg: str) -> Dict[str, bool]:
        """Determine the acceptance status of an argument under all semantics."""
        grounded = self.grounded_extension()
        preferred = self.preferred_extensions()
        stable = self.stable_extensions()

        # Credulous: accepted in at least one preferred extension
        credulously_accepted = any(arg in ext for ext in preferred)
        # Skeptical: accepted in all preferred extensions
        skeptically_accepted = all(arg in ext for ext in preferred) if preferred else False

        return {
            "in_grounded": arg in grounded,
            "credulously_accepted": credulously_accepted,
            "skeptically_accepted": skeptically_accepted,
            "in_stable": any(arg in ext for ext in stable) if stable else False,
        }

    def get_all_extensions(self) -> Dict[str, List[List[str]]]:
        """Compute all semantics and return as a dict of sorted lists."""
        return {
            "grounded": [sorted(self.grounded_extension())],
            "preferred": [sorted(ext) for ext in self.preferred_extensions()],
            "stable": [sorted(ext) for ext in self.stable_extensions()],
            "complete": [sorted(ext) for ext in self.complete_extensions()],
            "admissible": [sorted(ext) for ext in self.admissible_sets()],
        }

    def framework_properties(self) -> Dict:
        """Compute framework properties (pure Python, no JVM)."""
        # Detect cycles using DFS
        has_cycle = False
        visited = set()
        rec_stack = set()

        def _dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            for _, tgt in self.attacks:
                if _ == node:
                    if tgt in rec_stack:
                        return True
                    if tgt not in visited:
                        if _dfs(tgt):
                            return True
            rec_stack.discard(node)
            return False

        for arg in self.arguments:
            if arg not in visited:
                if _dfs(arg):
                    has_cycle = True
                    break

        self_attacking = [a for a in self.arguments if (a, a) in self.attacks]

        return {
            "num_arguments": len(self.arguments),
            "num_attacks": len(self.attacks),
            "has_cycles": has_cycle,
            "self_attacking": self_attacking,
            "unattacked": sorted(
                a for a in self.arguments if not self.attackers_of(a)
            ),
        }

    @classmethod
    def from_args_and_attacks(
        cls,
        arguments: List[str],
        attacks: List[List[str]],
    ) -> "DungFramework":
        """Create a framework from lists of arguments and attack pairs."""
        fw = cls()
        for arg in arguments:
            fw.add_argument(arg)
        for attack in attacks:
            if len(attack) >= 2:
                fw.add_attack(attack[0], attack[1])
        return fw

    # --- Classic test cases ---

    @classmethod
    def triangle(cls) -> "DungFramework":
        """Classic 3-cycle: a->b->c->a."""
        fw = cls()
        for a in ["a", "b", "c"]:
            fw.add_argument(a)
        fw.add_attack("a", "b")
        fw.add_attack("b", "c")
        fw.add_attack("c", "a")
        return fw

    @classmethod
    def nixon_diamond(cls) -> "DungFramework":
        """Nixon Diamond: quaker→not_pacifist, republican→not_hawk."""
        fw = cls()
        for a in ["quaker", "republican", "pacifist", "hawk"]:
            fw.add_argument(a)
        fw.add_attack("quaker", "hawk")
        fw.add_attack("republican", "pacifist")
        fw.add_attack("hawk", "pacifist")
        fw.add_attack("pacifist", "hawk")
        return fw

    @classmethod
    def reinstatement(cls) -> "DungFramework":
        """Reinstatement: a->b->c, a defends c."""
        fw = cls()
        for a in ["a", "b", "c"]:
            fw.add_argument(a)
        fw.add_attack("a", "b")
        fw.add_attack("b", "c")
        return fw
