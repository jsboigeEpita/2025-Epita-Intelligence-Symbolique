# -*- coding: utf-8 -*-
# tests/minimal_jpype_tweety_tests/workers/worker_list_models.py
"""
Worker pour le test de listage de modèles (test_list_models).
Ce script est exécuté dans un sous-processus avec une JVM dédiée.
"""

import os
import sys
import jpype
import jpype.imports
from jpype.types import JString

# Ajout du chemin racine du projet pour permettre les imports relatifs
# depuis argumentation_analysis, etc.
project_root = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import de la fixture qui gère la JVM.
# Cet import est nécessaire pour que le worker puisse démarrer la JVM lui-même.
# Le test lanceur ne passe plus la session.
from tests.fixtures.jvm_session_fixture import jvm_session_unmanaged


def main():
    """
    Fonction principale du worker. Contient la logique du test original.
    """
    print("Worker (list_models): Démarrage...")

    # Démarrage manuel de la JVM à l'intérieur du worker
    # C'est la responsabilité de la fixture run_in_jvm_subprocess
    # mais ici on utilise une version simplifiée pour ce test minimal.
    # Dans un vrai scénario, le lanceur passerait les arguments de la JVM.
    jvm_session_unmanaged()  # Démarre et configure la JVM

    try:
        assert jpype.isJVMStarted(), "La JVM n'a pas pu être démarrée dans le worker."
        print("Worker: JVM démarrée avec succès.")

        # === Logique du test original ===
        PlBeliefSet = jpype.JClass("org.tweetyproject.logics.pl.syntax.PlBeliefSet")
        PlParser = jpype.JClass("org.tweetyproject.logics.pl.parser.PlParser")
        Proposition = jpype.JClass("org.tweetyproject.logics.pl.syntax.Proposition")
        Implication = jpype.JClass("org.tweetyproject.logics.pl.syntax.Implication")
        Negation = jpype.JClass("org.tweetyproject.logics.pl.syntax.Negation")
        PossibleWorld = jpype.JClass(
            "org.tweetyproject.logics.pl.semantics.PossibleWorld"
        )
        SatSolver = jpype.JClass("org.tweetyproject.logics.pl.sat.SatSolver")
        Sat4jSolver = jpype.JClass("org.tweetyproject.logics.pl.sat.Sat4jSolver")
        SimpleModelEnumerator = jpype.JClass(
            "org.tweetyproject.logics.pl.sat.SimpleModelEnumerator"
        )

        if not SatSolver.hasDefaultSolver():
            SatSolver.setDefaultSolver(Sat4jSolver())
            print("Worker: Sat4jSolver configuré comme solveur par défaut.")

        belief_set = PlBeliefSet()
        p_a = Proposition(JString("a"))
        p_b = Proposition(JString("b"))
        p_c = Proposition(JString("c"))
        p_d = Proposition(JString("d"))

        belief_set.add(p_b)
        belief_set.add(Implication(p_b, p_a))
        belief_set.add(Implication(Negation(p_d), p_c))
        belief_set.add(Implication(Negation(p_c), p_d))

        model_enumerator = SimpleModelEnumerator()
        java_models_set = model_enumerator.getModels(belief_set)
        model_count = java_models_set.size()

        print(f"Worker: Nombre de modèles trouvés : {model_count}")

        expected_models = 3
        assert (
            model_count == expected_models
        ), f"ÉCHEC: Nombre de modèles incorrect. Attendu: {expected_models}, Trouvé: {model_count}"

        print("Worker: Test de listage des modèles RÉUSSI.")
        # === Fin de la logique du test ===

    except Exception as e:
        print(f"Worker: Le test a échoué avec une exception: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc(file=sys.stderr)
        sys.exit(1)  # Quitter avec un code d'erreur pour faire échouer le test parent


if __name__ == "__main__":
    main()
