"""Firsthand, NO-MOCKS sweep of EVERY external solver path — not just Clingo
(R467 follow-up: "tu as vérifié tous les autres composants externes?").

For each external-binary path we run a known-INCONSISTENT and known-CONSISTENT
synthetic KB through the production code and print exactly what it does:
a real verdict (True/False), an honest None/raise (cannot decide), or — the
thing we hunt — a FABRICATED verdict from a silent fallback (theatre #1019).

Covers: EProver (FOL default), Prover9 (FOL alt), the Tweety FOL fallback that
both fall back to, PySAT (PL), SAT handler (_invoke_sat), Clingo (ASP).
Modal/SPASS is po-2025's — probed read-only for completeness.

Synthetic atoms only — no corpus.
"""

import asyncio
import sys
from pathlib import Path

from argumentation_analysis.core.jvm_setup import initialize_jvm, EXTERNAL_TOOL_PATHS
from argumentation_analysis.core.config import settings, SolverChoice
from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge

FOL_INC = "Mortal = {socrate}\ntype(Human(Mortal))\nHuman(socrate)\n!Human(socrate)"
FOL_CON = "Mortal = {socrate}\ntype(Human(Mortal))\nHuman(socrate)"


def line(label, verdict, detail=""):
    print(f"  {label:<34} verdict={verdict!r:>7}  | {detail[:90]}")


def fol_under(bridge, solver_choice):
    prev = settings.solver
    settings.solver = solver_choice
    try:
        vi, mi = bridge.check_consistency(FOL_INC, "first_order")
        vc, mc = bridge.check_consistency(FOL_CON, "first_order")
        line(f"FOL[{solver_choice.value}] INCONSISTENT", vi, mi)
        line(f"FOL[{solver_choice.value}] CONSISTENT", vc, mc)
        # Honest contract: inconsistent KB must NOT come back True.
        if vi is True:
            print(
                "    >>> THEATRE: a contradiction was reported CONSISTENT (fabrication)."
            )
        elif vi is False:
            print("    >>> OK: contradiction decided inconsistent.")
        else:
            print("    >>> fail-loud (None) — honest, no fabrication.")
    except Exception as e:  # noqa: BLE001
        print(
            f"    FOL[{solver_choice.value}] raised {type(e).__name__}: {str(e)[:120]}"
        )
    finally:
        settings.solver = prev


def main():
    initialize_jvm()
    print("\n=== External binary inventory (firsthand) ===")
    for k in ("eprover", "spass", "clingo"):
        print(f"  EXTERNAL_TOOL_PATHS[{k:8}] = {EXTERNAL_TOOL_PATHS.get(k)}")
    p9 = Path("libs/prover9/bin/prover9.bat")
    print(f"  prover9.bat present       = {p9.is_file()}  ({p9})")
    try:
        import pysat  # noqa

        print("  pysat package             = present")
    except ImportError:
        print("  pysat package             = ABSENT")
    try:
        import clingo  # noqa

        print("  clingo python package     = present")
    except ImportError:
        print("  clingo python package     = ABSENT")

    bridge = TweetyBridge()

    print("\n=== FOL — EProver (default) ===")
    fol_under(bridge, SolverChoice.EPROVER)

    print("\n=== FOL — Prover9 (alt; binary absent => fallback path) ===")
    fol_under(bridge, SolverChoice.PROVER9)

    print("\n=== FOL — Tweety fallback (the path both fall back to) ===")
    fol_under(bridge, SolverChoice.TWEETY)

    print("\n=== PL — PySAT (production path) ===")
    try:
        vi, mi = bridge.check_consistency("a\n!a", "propositional")
        vc, mc = bridge.check_consistency("a\nb", "propositional")
        line("PL INCONSISTENT", vi, mi)
        line("PL CONSISTENT", vc, mc)
    except Exception as e:  # noqa: BLE001
        print(f"  PL raised {type(e).__name__}: {str(e)[:120]}")

    print("\n=== SAT — _invoke_sat (PySAT-backed) ===")
    try:
        from argumentation_analysis.orchestration.invoke_callables import _invoke_sat

        loop = asyncio.new_event_loop()
        res = loop.run_until_complete(_invoke_sat("a & !a", {}))
        print(f"  _invoke_sat('a & !a') -> {str(res)[:160]}")
    except Exception as e:  # noqa: BLE001
        print(f"  _invoke_sat raised {type(e).__name__}: {str(e)[:120]}")

    print("\n=== ASP — Clingo (already fixed; re-confirm genuine) ===")
    try:
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_asp_reasoning,
        )

        loop = asyncio.new_event_loop()
        res = loop.run_until_complete(_invoke_asp_reasoning("a.\nb :- a.", {}))
        sets = [set(m) for m in res.get("answer_sets", [])]
        print(
            f"  ASP solver={res.get('solver')!r}  sets={sets}  "
            f"{'OK' if {'a','b'} in sets else 'SUSPECT'}"
        )
    except Exception as e:  # noqa: BLE001
        print(f"  ASP raised {type(e).__name__}: {str(e)[:120]}")

    print("\nDONE.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
