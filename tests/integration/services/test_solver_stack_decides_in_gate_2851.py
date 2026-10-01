"""#2851 — the solver-stack witness the GATE collects.

Why this file exists, measured: the per-backend sentinel
(``tests/integration/argumentation_analysis/.../test_external_provers_wired.py``)
lives in a directory the gate argv does not collect — ``ci.yml`` collects
``tests/integration/{orchestration,services,workers,api}`` only — so the green
``automated-tests`` measured nothing about the provisioned ``pycryptosat``, and
MUS was never exercised either (``test_sat_handler.py::TestMUSAnalysis`` skips
all 3 with "PySAT or Z3 not installed" on main's lock, run 36601189560).

Born-red on ``main``'s lock, which carries neither ``pycryptosat`` nor
``z3-solver``: the first backend raises at construction and ``find_mus``
raises ``ModuleNotFoundError``. Deliberately NO ``skipif``: a skip is exactly
how CI stayed green without Z3, and this file's whole job is to say so out
loud. Both dependencies are declared in ``environment.yml`` since #2851.

The probes are the same both-directions rule the sentinel uses — a backend
that answers wrongly is fabrication (#1019), not a comparison point.
"""

from argumentation_analysis.agents.core.logic.pl_handler import PLHandler
from argumentation_analysis.agents.core.logic.sat_handler import SATHandler


def test_every_pl_comparison_backend_decides_both_ways():
    """Every entry of ``PL_COMPARISON_PYSAT_BACKENDS`` decides a clearly-SAT
    and a clearly-UNSAT KB, in the env the gate installs from the lock.

    Born-red on ``main``'s lock: ``cryptominisat5`` has no ``pycryptosat``
    there (constructor ``AssertionError``) — it was excluded from the set in
    2026-06 for that reason and re-added by #2851 once provisioned.
    """
    undecided: list = []
    for name in PLHandler.PL_COMPARISON_PYSAT_BACKENDS:
        try:
            handler = SATHandler(default_solver=name)
            sat_ok, _, _ = handler.solve_formulas(["p", "q"], name)
            unsat_ok, _, _ = handler.solve_formulas(["p", "!p"], name)
        except Exception as exc:  # noqa: BLE001 — the verdict NAMES the tool
            undecided.append(f"{name}: raised {type(exc).__name__}: {exc}")
            continue
        if sat_ok is not True or unsat_ok is not False:
            undecided.append(f"{name}: SAT KB -> {sat_ok!r}, UNSAT KB -> {unsat_ok!r}")
    assert not undecided, (
        "backends declared in PL_COMPARISON_PYSAT_BACKENDS that do not decide "
        "in the gate env — a backend that cannot decide must not be in the "
        "comparison set (environment.yml provisions their bindings): "
        + "; ".join(undecided)
    )


def test_mus_decides_with_z3_in_the_gate_env():
    """MUS/MARCO decides through Z3, in the gate env.

    Born-red on ``main``'s lock (no ``z3-solver``): ``find_mus`` raises
    ``ModuleNotFoundError``. The expectation is the exact MUS over
    ``["p", "!p"]`` — measured on the seat (projet-is, z3 4.16.0): ``[[0, 1]]``.
    """
    handler = SATHandler()
    mus = handler.find_mus(["p", "!p"], max_mus=2)
    assert mus == [[0, 1]], (
        f"MUS over ['p', '!p'] must be [[0, 1]], got {mus!r} — z3 is declared "
        "in environment.yml (E2 of the paid-run gate): a wrong or empty "
        "answer here means the solver stack is not the one the lock builds"
    )
