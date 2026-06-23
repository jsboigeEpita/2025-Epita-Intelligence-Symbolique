"""Firsthand introspection of Tweety ClingoSolver wiring API (R467).

The 029bdf7c disconnect removed the startup ``setPathToClingo`` injection and
no ctor replacement was added (unlike EProver/SPASS). To restore it correctly
we must know what the *current* Tweety build actually exposes:
  - a constructor taking the binary path?  (ClingoSolver(String))
  - an INSTANCE setPathToClingo(String)?
  - a STATIC ClingoSolver.setPathToClingo(String)?
Print the real signatures — no guessing.
"""

import sys
from argumentation_analysis.core.jvm_setup import initialize_jvm, EXTERNAL_TOOL_PATHS


def main():
    initialize_jvm()
    import jpype

    print(f"clingo path registered: {EXTERNAL_TOOL_PATHS.get('clingo')!r}")
    ClingoSolver = jpype.JClass("org.tweetyproject.lp.asp.reasoner.ClingoSolver")

    jclass = ClingoSolver.class_
    print("\n--- Constructors ---")
    for c in jclass.getConstructors():
        params = [str(p.getName()) for p in c.getParameterTypes()]
        print(f"  ClingoSolver({', '.join(params)})")

    print("\n--- Methods mentioning 'ath' (setPathTo*) ---")
    for m in jclass.getMethods():
        name = str(m.getName())
        if "ath" in name or "lingo" in name.lower():
            import java.lang.reflect.Modifier as Mod  # noqa

            mods = m.getModifiers()
            static = "STATIC" if Mod.isStatic(mods) else "instance"
            params = [str(p.getName()) for p in m.getParameterTypes()]
            print(f"  [{static}] {name}({', '.join(params)})")

    # Try the wiring live: construct, set path, run a trivial program.
    path = EXTERNAL_TOOL_PATHS.get("clingo")
    if not path:
        print("\nNo clingo path registered — cannot live-test wiring.")
        return 0

    JString = jpype.JClass("java.lang.String")
    print(f"\n--- Live wiring attempt with path={path!r} ---")
    # Attempt A: ctor-with-path
    try:
        s = ClingoSolver(JString(path))
        print("  ctor ClingoSolver(String): OK")
    except Exception as e:  # noqa: BLE001
        print(f"  ctor ClingoSolver(String): FAILED {type(e).__name__}: {str(e)[:120]}")
    # Attempt B: no-arg ctor + instance setPathToClingo
    try:
        s = ClingoSolver()
        s.setPathToClingo(JString(path))
        print("  instance s.setPathToClingo(String): OK")
    except Exception as e:  # noqa: BLE001
        print(
            f"  instance s.setPathToClingo(String): FAILED {type(e).__name__}: {str(e)[:120]}"
        )
    # Attempt C: static
    try:
        ClingoSolver.setPathToClingo(JString(path))
        print("  static ClingoSolver.setPathToClingo(String): OK")
    except Exception as e:  # noqa: BLE001
        print(
            f"  static ClingoSolver.setPathToClingo(String): FAILED {type(e).__name__}: {str(e)[:120]}"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
