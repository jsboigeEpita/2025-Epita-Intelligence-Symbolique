# -*- coding: utf-8 -*-
import jpype
import jpype.imports
import sys
import logging

from _production_jvm import start_jvm

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def _test_belief_set_union(belief_classes):
    PlBeliefSet, PlParser = belief_classes["PlBeliefSet"], belief_classes["PlParser"]
    parser = PlParser()
    kb1 = PlBeliefSet()
    kb1.add(parser.parseFormula("p"))
    kb1.add(parser.parseFormula("q"))
    kb2 = PlBeliefSet()
    kb2.add(parser.parseFormula("q"))
    kb2.add(parser.parseFormula("r"))

    union_kb = PlBeliefSet(kb1)
    union_kb.addAll(kb2)

    assert union_kb.size() == 3
    logger.info("Test d'union de bases de croyances réussi.")


def _test_belief_set_intersection(belief_classes):
    PlBeliefSet, PlParser = belief_classes["PlBeliefSet"], belief_classes["PlParser"]
    parser = PlParser()
    kb1 = PlBeliefSet()
    kb1.add(parser.parseFormula("p"))
    kb1.add(parser.parseFormula("common"))
    kb2 = PlBeliefSet()
    kb2.add(parser.parseFormula("r"))
    kb2.add(parser.parseFormula("common"))

    intersection_kb = PlBeliefSet(kb1)
    intersection_kb.retainAll(kb2)

    assert intersection_kb.size() == 1
    assert str(intersection_kb.iterator().next()) == "common"
    logger.info("Test d'intersection de bases de croyances réussi.")


def test_theory_operations_logic():
    """Point d'entrée principal pour les tests d'opérations sur les théories."""
    print("--- Début du worker pour test_theory_operations_logic ---")
    start_jvm()

    try:
        belief_revision_classes = {
            "PlBeliefSet": jpype.JClass(
                "org.tweetyproject.logics.pl.syntax.PlBeliefSet"
            ),
            "PlParser": jpype.JClass("org.tweetyproject.logics.pl.parser.PlParser"),
            "SimplePlReasoner": jpype.JClass(
                "org.tweetyproject.logics.pl.reasoner.SimplePlReasoner"
            ),
        }

        logger.info("--- Exécution de _test_belief_set_union ---")
        _test_belief_set_union(belief_revision_classes)

        logger.info("--- Exécution de _test_belief_set_intersection ---")
        _test_belief_set_intersection(belief_revision_classes)

        # Les autres tests (différence, subsomption, etc.) peuvent être ajoutés ici
        # de la même manière. Pour la migration, on garde simple.

        print("--- Toutes les assertions du worker ont réussi ---")

    except Exception as e:
        logger.error(
            f"Erreur dans le worker d'opérations sur les théories: {e}", exc_info=True
        )
        raise
    finally:
        # Ne pas arrêter la JVM ici. La fixture pytest s'en chargera.
        # if jpype.isJVMStarted():
        #     jpype.shutdownJVM()
        #     print("--- JVM arrêtée avec succès dans le worker ---")
        logger.info(
            "--- Le worker a terminé sa tâche. La gestion de l'arrêt de la JVM est laissée au processus principal. ---"
        )


if __name__ == "__main__":
    try:
        test_theory_operations_logic()
        print(
            "--- Le worker d'opérations sur les théories s'est terminé avec succès. ---"
        )
    except Exception as e:
        print(f"Une erreur est survenue dans le worker : {e}", file=sys.stderr)
        sys.exit(1)
