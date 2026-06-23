"""Firsthand proof of the ASP (Clingo) path's honesty (R467 user mandate —
external-component disconnect detection).

The honest invariant is NOT "must be clingo_jvm" — Tweety 1.29's ClingoSolver is
incompatible with clingo >= 5.x (it mis-parses the version banner into fake
atoms), so the genuine path is the official clingo Python package. What matters:
ASP is decided by a GENUINE solver (clingo_jvm OR clingo_python) with a CORRECT
answer set, and NEVER by the fact-echo ``heuristic`` (which ignores rules) or a
silent ``unavailable`` when a real solver is present (anti-théâtre #1019).
"""

import asyncio
from argumentation_analysis.core.jvm_setup import (
    initialize_jvm,
    EXTERNAL_TOOL_PATHS,
    is_jvm_started,
)

initialize_jvm()
print(f"JVM started: {is_jvm_started()}")
print(f"clingo binary registered: {EXTERNAL_TOOL_PATHS.get('clingo')}")

from argumentation_analysis.orchestration.invoke_callables import _invoke_asp_reasoning

res = asyncio.get_event_loop().run_until_complete(
    _invoke_asp_reasoning("a.\nb :- a.", {})
)
solver = res.get("solver")
sets = [set(m) for m in res.get("answer_sets", [])]
print(f"RESULT solver = {solver!r}")
print(f"answer_sets = {res.get('answer_sets')}")

genuine = solver in ("clingo_jvm", "clingo_python")
correct = {"a", "b"} in sets
if genuine and correct:
    print(
        f">>> ASP HONEST: decided by genuine solver {solver!r} with correct model {{a, b}}."
    )
elif solver in ("heuristic", "unavailable"):
    print(
        f">>> ASP DISCONNECTED: no genuine solver ran (solver={solver!r}). If a clingo "
        "binary/package is present this is a silent fallback (#1019 violation)."
    )
else:
    print(
        f">>> ASP SUSPECT: solver={solver!r} returned model {sets!r} (expected {{a, b}})."
    )
