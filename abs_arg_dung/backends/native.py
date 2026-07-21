"""Pure-Python Dung reasoners (no JVM, no Tweety).

This module implements three semantics *from scratch* in standard Python so
that the multi-backend comparison in :mod:`argumentation_analysis.orchestration.invoke_callables`
(``_compare_dung_backends``) can cross-check the Tweety and student-provider
verdicts on identical inputs without sharing any code path with them.

Algorithms:

* :func:`compute_grounded` — Kahn-style fixpoint: iteratively remove
  arguments that are not defended by any surviving argument. O(V+E).
  The unique grounded extension is the set that survives all reductions.
* :func:`compute_complete_extensions` — backtracking enumeration of all
  complete extensions (subset of admissible ⊇ preferred ⊇ stable). A set S
  is *complete* iff S is admissible (S defends itself) AND S contains all
  arguments it defends (fixpoint).
* :func:`compute_stable_extensions` — subset of complete extensions that
  are also *stable* (every argument outside S is attacked by S).

Sanctuary compliance: this file lives under ``abs_arg_dung/backends/`` which
is a NEW subpackage. It does NOT modify ``agent.py`` / ``enhanced_agent.py`` /
``dung_student_provider.py`` (sanctuary #893).
"""
from __future__ import annotations

from typing import Dict, FrozenSet, Iterable, List, Sequence, Set, Tuple, TypedDict


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_attackers(
    arguments: Sequence[str],
    attacks: Iterable[Tuple[str, str]],
) -> Dict[str, FrozenSet[str]]:
    """Build the attacker map: ``target -> frozenset of attackers``."""
    attackers: Dict[str, Set[str]] = {a: set() for a in arguments}
    for src, tgt in attacks:
        # Defensive: ignore attacks on unknown targets, duplicates are no-op.
        if tgt in attackers and src in attackers:
            attackers[tgt].add(src)
    return {a: frozenset(s) for a, s in attackers.items()}


def _is_conflict_free(
    candidates: FrozenSet[str],
    attackers: Dict[str, FrozenSet[str]],
) -> bool:
    """A set is conflict-free iff no element attacks another element of the set."""
    for x in candidates:
        for y in attackers.get(x, frozenset()):
            if y in candidates:
                return False
    return True


def _defends(
    s: FrozenSet[str],
    target: str,
    attackers: Dict[str, FrozenSet[str]],
) -> bool:
    """S defends ``target`` iff every attacker of ``target`` is attacked by some
    element of S."""
    target_attackers = attackers.get(target, frozenset())
    for atk in target_attackers:
        # Find some defender in S that attacks `atk`.
        if not any(d in s for d in attackers.get(atk, frozenset())):
            return False
    return True


def _attacked_by(s: FrozenSet[str], x: str, attackers: Dict[str, FrozenSet[str]]) -> bool:
    """Is x attacked by some element of s? (i.e. is there d ∈ s with (d, x) ∈ attacks?)."""
    for d in s:
        if x in attackers.get(d, frozenset()):
            return True
    return False


# ---------------------------------------------------------------------------
# Grounded semantics (least fixpoint of Dung's characteristic function)
# ---------------------------------------------------------------------------

def compute_grounded(
    arguments: Sequence[str],
    attacks: Iterable[Tuple[str, str]],
) -> List[str]:
    """Compute the unique grounded extension via least fixpoint of Dung's
    characteristic function.

        F(S) = { x : every attacker of x is attacked by some element of S }

    Starting from S = empty, repeatedly add any argument whose attackers are
    all already attacked by S, until a fixpoint is reached. This converges
    in at most |V| iterations, total O(V*(V+E)).

    Reference: Dung 1995, "On the Acceptability of Arguments".
    """
    arg_set: Set[str] = set(arguments)
    attackers = _build_attackers(arguments, attacks)

    grounded: Set[str] = set()
    changed = True
    while changed:
        changed = False
        # Attack range of the current grounded set.
        attack_range: Set[str] = set()
        for s in grounded:
            for tgt in attackers.get(s, frozenset()):
                attack_range.add(tgt)

        for x in arg_set - grounded:
            x_attackers = attackers.get(x, frozenset())
            # `x` can join iff every attacker of x is in attack_range.
            if not x_attackers:
                # Unattacked: trivially defended.
                grounded.add(x)
                changed = True
            elif x_attackers <= attack_range:
                grounded.add(x)
                changed = True

    return sorted(grounded)


# ---------------------------------------------------------------------------
# Complete semantics (backtracking enumeration)
# ---------------------------------------------------------------------------

def compute_complete_extensions(
    arguments: Sequence[str],
    attacks: Iterable[Tuple[str, str]],
) -> List[List[str]]:
    """Enumerate all complete extensions of the AF.

    A set S is *complete* iff:

    1. S is admissible (S is conflict-free AND S defends every element of S).
    2. S contains every argument it defends (Dung's fixpoint condition).

    These extensions are returned sorted (lexicographic) so the comparison
    with Tweety is order-stable.
    """
    arg_list = list(arguments)
    attackers = _build_attackers(arg_list, attacks)
    arg_set: Set[str] = set(arg_list)

    results: List[FrozenSet[str]] = []

    # Backtracking: at each step, decide to include or exclude `a` from S.
    # Pruning rules:
    #   * conflict-free: never include both an attacker and its target.
    #   * admissibility: if `a` is included, all attackers of `a` must be
    #     attacked by S (i.e. defended).
    #   * completeness: if `a` is defended by S, `a` must be included (so we
    #     add it to "must-include" — this is the fixpoint direction).
    #
    # We implement a recursive enumerator that maintains (in_set, excluded).
    # `excluded` is the set of arguments we have explicitly decided NOT to
    # include in S. If any excluded argument is defended by S, the partial
    # assignment is inconsistent (cannot extend to a complete extension) and
    # we backtrack.

    all_extensions: Set[FrozenSet[str]] = set()

    def _defended_by(s: FrozenSet[str], target: str) -> bool:
        return _defends(s, target, attackers)

    # Stable order: sort arguments for reproducibility.
    arg_order = sorted(arg_set)

    def _backtrack(idx: int, in_set: FrozenSet[str], excluded: FrozenSet[str]) -> None:
        if idx == len(arg_order):
            # Terminal check: is the partial assignment a complete extension?
            # - Conflict-free: must hold by construction.
            # - Admissible: for each x in in_set, every attacker of x is attacked
            #   by some element of in_set. This was enforced during inclusion.
            # - Complete: every argument defended by in_set must be in in_set.
            for x in arg_set:
                if x not in in_set and _defended_by(in_set, x):
                    return  # incomplete
            all_extensions.add(in_set)
            return

        a = arg_order[idx]

        # Option 1: exclude `a`.
        _backtrack(idx + 1, in_set, excluded | {a})

        # Option 2: include `a`, provided it's conflict-free with current set.
        if a not in excluded:
            # Conflict-free check (3 conditions):
            #   (i)  no attacker of `a` is in in_set (else in_set attacks a).
            #   (ii) no element of in_set is in attackers of `a` (i.e. a does
            #        not attack anyone in in_set).
            #   (iii) `a` does not attack itself (self-loop a -> a).
            a_attackers = attackers.get(a, frozenset())
            a_attacks = attackers.get(a, frozenset())  # symmetric map not built; build reverse
            conflict = a in a_attackers  # (iii) self-loop
            if not conflict:
                for atk in a_attackers:
                    if atk in in_set:
                        conflict = True
                        break
            if not conflict:
                # (ii) a attacks someone already in in_set?
                for member in in_set:
                    if a in attackers.get(member, frozenset()):
                        conflict = True
                        break
            if not conflict:
                #
                # Admissibility: every attacker of `a` must be attacked by
                # some element of (in_set ∪ {a}).
                new_in = in_set | {a}
                admissible = True
                for atk in attackers.get(a, frozenset()):
                    if atk in excluded:
                        # atk is already fixed as out of S. It can still be
                        # attacked by S (this is fine for admissibility of a).
                        if not _attacked_by(new_in, atk, attackers):
                            admissible = False
                            break
                    else:
                        # atk is not yet decided. It will eventually be in or
                        # out — but to KEEP the option of including atk later,
                        # we can't assume it's in S. Strict admissibility
                        # pruning here is conservative: if atk is undefended
                        # by new_in, including a would force us to exclude
                        # atk without compensating defenders, which may
                        # break completeness later. We only prune when we
                        # KNOW it's impossible.
                        #
                        # The safe check: can we ever defend atk? atk will
                        # either be in S or out. If it's out, it needs an
                        # attacker in S ∪ {a}. If it's in, it needs to be
                        # attacked by S ∪ {a} (i.e. defended, not attacked).
                        # We don't know — be conservative and check only
                        # whether new_in attacks atk now (which is enough
                        # in the standard case where we don't yet know
                        # atk's fate).
                        if not _attacked_by(new_in, atk, attackers):
                            admissible = False
                            break
                if not admissible:
                    return  # cannot include a without breaking admissibility
                _backtrack(idx + 1, new_in, excluded)

    # Empty set: trivially admissible if no self-attacks. But self-attacks
    # don't break admissibility (they only break conflict-freeness). If
    # there are no arguments, empty is complete. We handle this naturally:
    # if `arguments` is empty, idx starts at 0 == len(arg_order), so the
    # empty branch fires.

    _backtrack(0, frozenset(), frozenset())

    # Sort each extension and the list of extensions for determinism.
    return [sorted(list(ext)) for ext in sorted(all_extensions, key=lambda s: sorted(s))]


# ---------------------------------------------------------------------------
# Stable semantics (subset of complete)
# ---------------------------------------------------------------------------

def compute_stable_extensions(
    arguments: Sequence[str],
    attacks: Iterable[Tuple[str, str]],
) -> List[List[str]]:
    """Enumerate all stable extensions: complete extensions S such that every
    argument outside S is attacked by some element of S."""
    arg_set = set(arguments)
    complete = compute_complete_extensions(arguments, attacks)
    attackers = _build_attackers(arguments, attacks)

    stables: List[List[str]] = []
    for ext_list in complete:
        ext = set(ext_list)
        # Stable iff arg_set \ ext is fully attacked by ext.
        outside = arg_set - ext
        all_attacked = True
        for x in outside:
            if not (attackers.get(x, frozenset()) & ext):
                all_attacked = False
                break
        if all_attacked:
            stables.append(sorted(ext_list))
    return stables


# ---------------------------------------------------------------------------
# Facade mirroring `_compare_dung_backends` per-backend contract
# ---------------------------------------------------------------------------

class _BackendExtensions(TypedDict):
    grounded: List[List[str]]
    complete: List[List[str]]
    stable: List[List[str]]


class _BackendResult(TypedDict):
    backend: str
    available: bool
    note: str
    extensions: _BackendExtensions
    elapsed_ms: float


def backend_python(
    arguments: Sequence[str],
    attacks: Iterable[Tuple[str, str]],
) -> _BackendResult:
    """Pure-Python backend exposing the three semantics.

    Shape mirrors the per-backend dict expected by ``_compare_dung_backends``.
    """
    import time

    t0 = time.monotonic()
    grounded = compute_grounded(arguments, attacks)
    complete = compute_complete_extensions(arguments, attacks)
    stable = compute_stable_extensions(arguments, attacks)
    elapsed_ms = (time.monotonic() - t0) * 1000.0

    return {
        "backend": "python",
        "available": True,
        "note": "pure-stdlib, JVM-free (independent implementation)",
        "extensions": {
            "grounded": [grounded],
            "complete": complete,
            "stable": stable,
        },
        "elapsed_ms": round(elapsed_ms, 3),
    }
