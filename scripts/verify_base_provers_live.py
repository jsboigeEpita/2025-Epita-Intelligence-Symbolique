"""Firsthand, NO-MOCKS ground-truth probe of the base provers per Tweety logic.

Runs each logic's REAL reasoner through the production path
(``TweetyBridge.check_consistency``) on a known-inconsistent and a
known-consistent minimal KB, and prints exactly what the prover does:
a real verdict (True/False), an honest None (cannot decide), or an error.

Synthetic atoms only — no corpus. Disposable diagnostic (R467 user mandate:
verify the base provers were never silently débranché).
"""

import sys
from argumentation_analysis.core.jvm_setup import initialize_jvm, EXTERNAL_TOOL_PATHS
from argumentation_analysis.core.config import settings
from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge


def probe(bridge, label, logic_type, kb_inconsistent, kb_consistent):
    print(f"\n=== {label}  (logic_type={logic_type!r}) ===")
    for tag, kb in [
        ("INCONSISTENT(expect False)", kb_inconsistent),
        ("CONSISTENT  (expect True) ", kb_consistent),
    ]:
        try:
            verdict, msg = bridge.check_consistency(kb, logic_type)
            print(f"  {tag}: verdict={verdict!r:>7}  | {msg[:120]}")
        except Exception as e:  # noqa: BLE001 — raw ground truth
            print(f"  {tag}: EXCEPTION {type(e).__name__}: {str(e)[:140]}")


def main():
    print("Initializing JVM (real Tweety, no mocks)...")
    initialize_jvm()
    print("External tool binaries registered:")
    for k in ("eprover", "prover9", "spass"):
        print(f"   {k:8} -> {EXTERNAL_TOOL_PATHS.get(k)}")
    print(
        f"Config: solver={settings.solver.value}  modal_solver={settings.modal_solver.value}"
        f"  pl_solver={settings.pl_solver.value}"
    )

    bridge = TweetyBridge()

    # PROPOSITIONAL — PySAT path
    probe(bridge, "PL (propositional)", "propositional", "a\n!a", "a\nb")

    # FIRST-ORDER — EProver / sentinel / fallback
    fol_inc = "Mortal = {socrate}\ntype(Human(Mortal))\nHuman(socrate)\n!Human(socrate)"
    fol_con = "Mortal = {socrate}\ntype(Human(Mortal))\nHuman(socrate)"
    probe(bridge, "FOL (first_order)", "first_order", fol_inc, fol_con)

    # MODAL (ML) — SimpleMlReasoner (default) / SPASS
    probe(bridge, "ML (modal K)", "K", "p\n!p", "p\nq")

    print("\nDONE.")


if __name__ == "__main__":
    sys.exit(main())
