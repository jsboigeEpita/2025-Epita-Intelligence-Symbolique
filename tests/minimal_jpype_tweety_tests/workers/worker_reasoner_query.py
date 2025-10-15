# -*- coding: utf-8 -*-
# tests/minimal_jpype_tweety_tests/workers/worker_reasoner_query.py
"""
Worker pour le test de requête sur un raisonneur (test_reasoner_query).
"""
import os
import sys
import jpype
import jpype.imports
from jpype.types import JString

# Ajout du chemin racine
project_root = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from tests.fixtures.jvm_session_fixture import jvm_session_unmanaged


def main():
    print("Worker (reasoner_query): Démarrage...")
    jvm_session_unmanaged()

    try:
        assert jpype.isJVMStarted(), "La JVM n'a pas pu être démarrée."
        print("Worker: JVM démarrée.")

        PlBeliefSet = jpype.JClass("net.sf.tweety.logics.pl.syntax.PlBeliefSet")
        PlParser = jpype.JClass("net.sf.tweety.logics.pl.parser.PlParser")
        SimplePlReasoner = jpype.JClass(
            "net.sf.tweety.logics.pl.reasoner.SimplePlReasoner"
        )

        parser = PlParser()
        belief_set = PlBeliefSet()

        prop_b = parser.parseFormula("b")
        rule_a_if_b = parser.parseFormula("b => a")

        belief_set.add(prop_b)
        belief_set.add(rule_a_if_b)

        print(f"Worker: Théorie construite. Nombre de formules : {belief_set.size()}")

        reasoner = SimplePlReasoner()
        query_formula = parser.parseFormula("a")

        print(f"Worker: Interrogation de la formule : {query_formula.toString()}")
        is_consequence = reasoner.query(belief_set, query_formula)

        assert (
            is_consequence
        ), f"ÉCHEC: La formule '{query_formula.toString()}' devrait être une conséquence."

        print(f"Worker: La formule est une conséquence: {is_consequence}")
        print("Worker: Test de requête sur raisonneur RÉUSSI.")

    except Exception as e:
        print(f"Worker: Le test a échoué: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
