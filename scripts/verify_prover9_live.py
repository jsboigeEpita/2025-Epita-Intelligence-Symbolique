"""Firsthand: Prover9 is fully installed (prover9.exe + cygwin1.dll) yet
selecting SolverChoice.PROVER9 silently yields SimpleFolReasoner. Surface the
raw reason (R467 — a present external binary should DECIDE, or we must know why
it doesn't). Synthetic atoms only."""

import sys
from argumentation_analysis.core.jvm_setup import initialize_jvm


def main():
    initialize_jvm()
    import argumentation_analysis.core.prover9_runner as pr

    print(f"PROVER9_EXECUTABLE = {pr.PROVER9_EXECUTABLE}")
    print(f"  exists = {pr.PROVER9_EXECUTABLE.is_file()}")

    # Minimal inconsistent KB in Prover9 syntax: Human(socrate) & -Human(socrate)
    p9_input = (
        "formulas(assumptions).\n"
        "Human(socrate).\n"
        "-Human(socrate).\n"
        "end_of_list.\n\n"
        "formulas(goals).\n"
        "$F.\n"
        "end_of_list."
    )
    try:
        out = pr.run_prover9(p9_input)
        print("--- prover9 raw output (first 700 chars) ---")
        print(out[:700])
        print(
            f"--- 'THEOREM PROVED' present? {'THEOREM PROVED' in out} "
            f"(=> inconsistent if present)"
        )
    except Exception as e:  # noqa: BLE001
        print(f"PROVER9 RAISED: {type(e).__name__}")
        print(str(e)[:600])
    return 0


if __name__ == "__main__":
    sys.exit(main())
