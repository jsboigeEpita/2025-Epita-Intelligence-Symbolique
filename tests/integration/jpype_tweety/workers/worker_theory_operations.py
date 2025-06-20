# -*- coding: utf-8 -*-
import jpype
import jpype.imports
import os
from pathlib import Path
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_project_root_from_env() -> Path:
    project_root_str = os.getenv("PROJECT_ROOT")
    if not project_root_str:
        raise RuntimeError("La variable d'environnement PROJECT_ROOT n'est pas définie.")
    return Path(project_root_str)

def setup_jvm():
    """Démarre la JVM avec le classpath nécessaire."""
    if jpype.isJVMStarted():
        return

    project_root = get_project_root_from_env()
    libs_dir = project_root / "libs" / "tweety"
    full_jar_path = libs_dir / "org.tweetyproject.tweety-full-1.28-with-dependencies.jar"
    if not full_jar_path.exists():
        raise FileNotFoundError(f"Le JAR complet 'tweety-full' n'a pas été trouvé dans {libs_dir}")

    classpath = str(full_jar_path.resolve())
    logger.info(f"Démarrage de la JVM avec le classpath: {classpath}")
    try:
        jpype.startJVM(jpype.getDefaultJVMPath(), "-ea", classpath=classpath, convertStrings=False)
        logger.info("--- JVM démarrée avec succès dans le worker ---")
    except Exception as e:
        logger.error(f"ERREUR: Échec du démarrage de la JVM : {e}", exc_info=True)
        raise

def _test_belief_set_union(belief_classes):
    PlBeliefSet, PlParser = belief_classes["PlBeliefSet"], belief_classes["PlParser"]
    parser = PlParser()
    kb1 = PlBeliefSet()
    kb1.add(parser.parseFormula("p")); kb1.add(parser.parseFormula("q"))
    kb2 = PlBeliefSet()
    kb2.add(parser.parseFormula("q")); kb2.add(parser.parseFormula("r"))
    
    union_kb = PlBeliefSet(kb1)
    union_kb.addAll(kb2)

    assert union_kb.size() == 3
    logger.info("Test d'union de bases de croyances réussi.")

def _test_belief_set_intersection(belief_classes):
    PlBeliefSet, PlParser = belief_classes["PlBeliefSet"], belief_classes["PlParser"]
    parser = PlParser()
    kb1 = PlBeliefSet()
    kb1.add(parser.parseFormula("p")); kb1.add(parser.parseFormula("common"))
    kb2 = PlBeliefSet()
    kb2.add(parser.parseFormula("r")); kb2.add(parser.parseFormula("common"))
    
    intersection_kb = PlBeliefSet(kb1)
    intersection_kb.retainAll(kb2)
    
    assert intersection_kb.size() == 1
    assert str(intersection_kb.iterator().next()) == "common"
    logger.info("Test d'intersection de bases de croyances réussi.")

def test_theory_operations_logic():
    """Point d'entrée principal pour les tests d'opérations sur les théories."""
    print("--- Début du worker pour test_theory_operations_logic ---")
    setup_jvm()

    try:
        belief_revision_classes = {
            "PlBeliefSet": jpype.JClass("org.tweetyproject.logics.pl.syntax.PlBeliefSet"),
            "PlParser": jpype.JClass("org.tweetyproject.logics.pl.parser.PlParser"),
            "SimplePlReasoner": jpype.JClass("org.tweetyproject.logics.pl.reasoner.SimplePlReasoner")
        }

        logger.info("--- Exécution de _test_belief_set_union ---")
        _test_belief_set_union(belief_revision_classes)

        logger.info("--- Exécution de _test_belief_set_intersection ---")
        _test_belief_set_intersection(belief_revision_classes)

        # Les autres tests (différence, subsomption, etc.) peuvent être ajoutés ici
        # de la même manière. Pour la migration, on garde simple.

        print("--- Toutes les assertions du worker ont réussi ---")

    except Exception as e:
        logger.error(f"Erreur dans le worker d'opérations sur les théories: {e}", exc_info=True)
        raise
    finally:
        if jpype.isJVMStarted():
            jpype.shutdownJVM()
            print("--- JVM arrêtée avec succès dans le worker ---")

if __name__ == "__main__":
    try:
        test_theory_operations_logic()
        print("--- Le worker d'opérations sur les théories s'est terminé avec succès. ---")
    except Exception as e:
        print(f"Une erreur est survenue dans le worker : {e}", file=sys.stderr)
        sys.exit(1)