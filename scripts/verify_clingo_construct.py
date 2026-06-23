"""Firsthand: build ASP objects with the REAL Tweety API and solve (R467).

The invoke_callables JVM path had TWO breaks: ClingoSolver() no-arg ctor
(fixed) and ASPRule(list, list) ctor (does not exist). Determine the correct
fact/rule construction empirically, then solve a trivial program end-to-end.
"""

import sys
from argumentation_analysis.core.jvm_setup import initialize_jvm, EXTERNAL_TOOL_PATHS


def main():
    initialize_jvm()
    import jpype

    JString = jpype.JClass("java.lang.String")
    ClingoSolver = jpype.JClass("org.tweetyproject.lp.asp.reasoner.ClingoSolver")
    Program = jpype.JClass("org.tweetyproject.lp.asp.syntax.Program")
    ASPRule = jpype.JClass("org.tweetyproject.lp.asp.syntax.ASPRule")
    ASPAtom = jpype.JClass("org.tweetyproject.lp.asp.syntax.ASPAtom")

    # Fact "a" via no-arg ctor + getHead().add (the existing :- branch pattern)
    r1 = ASPRule()
    print("ASPRule() ok; getHead() type =", type(r1.getHead()))
    try:
        r1.getHead().add(ASPAtom("a"))
        print("  getHead().add(ASPAtom): OK ; rule =", r1)
    except Exception as e:  # noqa: BLE001
        print("  getHead().add FAILED:", type(e).__name__, str(e)[:160])

    # Rule "b :- a"
    r2 = ASPRule()
    r2.getHead().add(ASPAtom("b"))
    try:
        r2.getBody().add(ASPAtom("a"))
        print("  getBody().add(ASPAtom): OK ; rule =", r2)
    except Exception as e:  # noqa: BLE001
        print("  getBody().add FAILED:", type(e).__name__, str(e)[:160])

    prog = Program()
    prog.add(r1)
    prog.add(r2)
    path = EXTERNAL_TOOL_PATHS.get("clingo")
    print("clingo path:", path)
    solver = ClingoSolver(JString(path))
    aset = solver.getModels(prog, 0)
    print("MODELS size =", aset.size())
    for i in range(aset.size()):
        m = aset.get(i)
        # AnswerSet is a java.util.Set — iterate, don't index.
        print("  model", i, "=", [str(atom) for atom in m])
    return 0


if __name__ == "__main__":
    sys.exit(main())
