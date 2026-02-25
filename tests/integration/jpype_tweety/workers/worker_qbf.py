# -*- coding: utf-8 -*-
import jpype
import jpype.imports
import os
from pathlib import Path
import sys
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_project_root_from_env() -> Path:
    project_root_str = os.getenv("PROJECT_ROOT")
    if not project_root_str:
        raise RuntimeError(
            "La variable d'environnement PROJECT_ROOT n'est pas définie."
        )
    return Path(project_root_str)


def setup_jvm():
    """Démarre la JVM avec le classpath nécessaire, si elle n'est pas déjà démarrée."""
    if jpype.isJVMStarted():
        logger.info(
            "--- La JVM est déjà démarrée (probablement par pytest). Le worker l'utilise. ---"
        )
        return

    project_root = get_project_root_from_env()
    libs_dir = project_root / "libs" / "tweety"
    full_jar_path = (
        libs_dir / "org.tweetyproject.tweety-full-1.28-with-dependencies.jar"
    )
    if not full_jar_path.exists():
        raise FileNotFoundError(
            f"Le JAR complet 'tweety-full' n'a pas été trouvé dans {libs_dir}"
        )

    classpath = str(full_jar_path.resolve())
    logger.info(f"Démarrage de la JVM avec le classpath: {classpath}")
    try:
        logger.info(
            "--- La JVM n'est pas démarrée. Tentative de démarrage par le worker... ---"
        )
        jpype.startJVM(
            jpype.getDefaultJVMPath(), "-ea", classpath=classpath, convertStrings=False
        )
        logger.info("--- JVM démarrée avec succès par le worker ---")
    except Exception as e:
        logger.error(
            f"ERREUR: Échec du démarrage de la JVM par le worker : {e}", exc_info=True
        )
        raise


def _test_pl_sat_solver(pl_classes):
    """Test SAT solving via propositional logic (available in Tweety 1.28)."""
    PlBeliefSet = pl_classes["PlBeliefSet"]
    PlParser = pl_classes["PlParser"]
    SatReasoner = pl_classes["SatReasoner"]

    parser = PlParser()
    kb = PlBeliefSet()
    kb.add(parser.parseFormula("a || b"))
    kb.add(parser.parseFormula("!a || c"))
    kb.add(parser.parseFormula("!b || c"))

    reasoner = SatReasoner()
    # c should be entailed: (a||b) && (!a||c) && (!b||c) => c
    result = reasoner.query(kb, parser.parseFormula("c"))
    assert result, "Expected c to be entailed"
    logger.info("Test SAT solver: c est bien impliqué par la base de croyances.")


def _test_pl_contradiction_detection(pl_classes):
    """Test contradiction detection in belief sets."""
    PlBeliefSet = pl_classes["PlBeliefSet"]
    PlParser = pl_classes["PlParser"]
    SatReasoner = pl_classes["SatReasoner"]

    parser = PlParser()
    # Consistent KB
    kb_consistent = PlBeliefSet()
    kb_consistent.add(parser.parseFormula("a"))
    kb_consistent.add(parser.parseFormula("b"))

    # Inconsistent KB
    kb_inconsistent = PlBeliefSet()
    kb_inconsistent.add(parser.parseFormula("a"))
    kb_inconsistent.add(parser.parseFormula("!a"))

    reasoner = SatReasoner()
    # Consistent KB should not entail contradiction
    is_consistent_entails_false = reasoner.query(
        kb_consistent, parser.parseFormula("a && !a")
    )
    assert (
        not is_consistent_entails_false
    ), "Consistent KB should not entail contradiction"

    # Inconsistent KB should entail anything (ex falso quodlibet)
    is_inconsistent_entails_anything = reasoner.query(
        kb_inconsistent, parser.parseFormula("b")
    )
    assert is_inconsistent_entails_anything, "Inconsistent KB should entail anything"
    logger.info("Test contradiction detection réussi.")


def _test_pl_tautology_check(pl_classes):
    """Test tautology verification."""
    PlParser = pl_classes["PlParser"]
    PlBeliefSet = pl_classes["PlBeliefSet"]
    SatReasoner = pl_classes["SatReasoner"]

    parser = PlParser()
    empty_kb = PlBeliefSet()
    reasoner = SatReasoner()

    # Tautology: a || !a
    tautology = parser.parseFormula("a || !a")
    assert reasoner.query(empty_kb, tautology), "a || !a should be a tautology"

    # Non-tautology: a
    non_tautology = parser.parseFormula("a")
    assert not reasoner.query(empty_kb, non_tautology), "a alone is not a tautology"
    logger.info("Test tautology check réussi.")


def test_qbf_logic():
    """Point d'entrée principal pour les tests de raisonnement propositionnel avancé."""
    print("--- Début du worker pour test_qbf_logic ---")
    setup_jvm()

    try:
        pl_classes = {
            "PlBeliefSet": jpype.JClass(
                "org.tweetyproject.logics.pl.syntax.PlBeliefSet"
            ),
            "PlParser": jpype.JClass("org.tweetyproject.logics.pl.parser.PlParser"),
            "SatReasoner": jpype.JClass(
                "org.tweetyproject.logics.pl.reasoner.SimplePlReasoner"
            ),
            "Proposition": jpype.JClass(
                "org.tweetyproject.logics.pl.syntax.Proposition"
            ),
        }

        logger.info("--- Exécution de _test_pl_sat_solver ---")
        _test_pl_sat_solver(pl_classes)

        logger.info("--- Exécution de _test_pl_contradiction_detection ---")
        _test_pl_contradiction_detection(pl_classes)

        logger.info("--- Exécution de _test_pl_tautology_check ---")
        _test_pl_tautology_check(pl_classes)

        print("--- Toutes les assertions du worker ont réussi ---")

    except Exception as e:
        logger.error(f"Erreur dans le worker QBF/PL avancé: {e}", exc_info=True)
        raise
    finally:
        logger.info(
            "--- Le worker a terminé sa tâche. La gestion de l'arrêt de la JVM est laissée au processus principal. ---"
        )


if __name__ == "__main__":
    try:
        test_qbf_logic()
        print("--- Le worker QBF/PL avancé s'est terminé avec succès. ---")
    except Exception as e:
        print(f"Une erreur est survenue dans le worker : {e}", file=sys.stderr)
        sys.exit(1)
