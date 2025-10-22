# -*- coding: utf-8 -*-
# tests/minimal_jpype_tweety_tests/workers/worker_load_theory.py
"""
Worker pour le test de chargement de théorie (test_load_theory).
Exécuté dans un sous-processus avec une JVM dédiée.
"""
import os
import sys
import jpype
import jpype.imports
from jpype.types import JString

# Ajout du chemin racine du projet
project_root = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from tests.fixtures.jvm_session_fixture import jvm_session_unmanaged


def main():
    """
    Fonction principale du worker.
    """
    print("Worker (load_theory): Démarrage...")
    jvm_session_unmanaged()

    try:
        assert jpype.isJVMStarted(), "La JVM n'a pas pu être démarrée."
        print("Worker: JVM démarrée.")

        PlParser = jpype.JClass("org.tweetyproject.logics.pl.parser.PlParser")

        # Le chemin du fichier de théorie est relatif au worker
        theory_file_path = os.path.join(
            os.path.dirname(__file__), "..", "sample_theory.lp"
        )
        print(f"Worker: Chemin du fichier de théorie: {theory_file_path}")

        if not os.path.exists(theory_file_path):
            print(
                f"Erreur: Fichier de théorie introuvable: {theory_file_path}",
                file=sys.stderr,
            )
            sys.exit(1)

        parser = PlParser()
        belief_set = parser.parseBeliefBaseFromFile(theory_file_path)

        assert belief_set is not None, "Le belief set ne devrait pas être null."
        assert belief_set.size() > 0, "Le belief set ne devrait pas être vide."

        print(f"Worker: Théorie chargée. Nombre de formules : {belief_set.size()}")
        print("Worker: Test de chargement de théorie RÉUSSI.")

    except Exception as e:
        print(f"Worker: Le test a échoué: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
