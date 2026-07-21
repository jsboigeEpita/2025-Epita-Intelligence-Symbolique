"""Native Python Dung backends (no JVM, no Tweety) for `compare_dung_backends`.

These complement the Tweety-based ``DungAgent`` (sanctuary #893) by providing
a JVM-free cross-check: any disagreement with the Tweety verdicts is reported
verbatim, NEVER auto-reconciled (anti-pendule #1019).

Public entry points (all pure-stdlib, mypy-strict clean):

* :func:`compute_grounded` — Kahn-style fixpoint O(V+E). Returns the unique
  grounded extension as a sorted ``list[str]``.
* :func:`compute_complete_extensions` — backtracking enumeration of all
  complete extensions (subset of admissible ⊇ preferred ⊇ stable).
* :func:`compute_stable_extensions` — subset of complete extensions that are
  also *stable* (attacks every argument outside the set).
* :func:`backend_python` — uniform facade exposing the three semantics with
  the same shape the in-process ``_compare_dung_backends`` expects, so it
  can be wired as a third backend alongside ``tweety`` and ``abs_arg_dung_student``.

Why pure stdlib? Two reasons:

1. Anti-#1019: a multi-backend comparison that relies on shared libraries
   cannot catch bugs in those libraries. A naive Python implementation is a
   *genuine* independent implementation.
2. CI friendliness: tests run JVM-free (cf. ``test_compare_dung_backends.py``
   pattern). Determinism is provable by construction (no floating point, no
   external solver).
"""
from .native import (
    compute_grounded,
    compute_complete_extensions,
    compute_stable_extensions,
    backend_python,
)
from .generators import (
    parse_iccma_af,
    parse_iccma_af_file,
    generate_sbm,
    generate_er,
    generate_classic_examples,
)

__all__ = [
    "compute_grounded",
    "compute_complete_extensions",
    "compute_stable_extensions",
    "backend_python",
    "parse_iccma_af",
    "parse_iccma_af_file",
    "generate_sbm",
    "generate_er",
    "generate_classic_examples",
]