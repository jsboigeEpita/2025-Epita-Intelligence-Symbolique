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

def _test_load_logic_theory_from_file(logic_classes, base_dir):
    PlParser = logic_classes["PlParser"]
    theory_file_path = base_dir / "sample_theory.lp"
    assert theory_file_path.exists(), f"Le fichier de théorie {theory_file_path} n'existe pas."
    parser = PlParser()
    belief_set = parser.parseBeliefBaseFromFile(str(theory_file_path))
    assert belief_set is not None
    assert belief_set.size() == 2
    logger.info("Chargement de la théorie depuis un fichier réussi.")

def _test_simple_pl_reasoner_queries(logic_classes, base_dir):
    PlParser, Proposition, SimplePlReasoner = logic_classes["PlParser"], logic_classes["Proposition"], logic_classes["SimplePlReasoner"]
    theory_file_path = base_dir / "sample_theory.lp"
    parser = PlParser()
    belief_set = parser.parseBeliefBaseFromFile(str(theory_file_path))
    reasoner = SimplePlReasoner()
    prop_b_formula = parser.parseFormula("b.")
    assert reasoner.query(belief_set, prop_b_formula)
    assert not reasoner.query(belief_set, Proposition("c"))
    logger.info("Tests de requêtes simples sur SimplePlReasoner réussis.")

def _test_formula_syntax_and_semantics(logic_classes):
    PlParser, Proposition, Negation, Conjunction, Implication = logic_classes["PlParser"], logic_classes["Proposition"], logic_classes["Negation"], logic_classes["Conjunction"], logic_classes["Implication"]
    parser = PlParser()
    formula_str1 = "p && q"
    parsed_formula1 = parser.parseFormula(formula_str1)
    assert isinstance(parsed_formula1, Conjunction)
    prop_x, prop_y = Proposition("x"), Proposition("y")
    formula_neg_x = Negation(prop_x)
    assert formula_neg_x.getFormula().equals(prop_x)
    logger.info("Tests de syntaxe et sémantique des formules réussis.")


def test_logic_operations_logic():
    """Point d'entrée principal pour les tests d'opérations logiques."""
    print("--- Début du worker pour test_logic_operations_logic ---")
    setup_jvm()
    
    # Le répertoire du worker pour trouver les fichiers de données
    worker_dir = Path(__file__).parent.parent

    try:
        logic_classes = {
            "PlBeliefSet": jpype.JClass("org.tweetyproject.logics.pl.syntax.PlBeliefSet"),
            "PlParser": jpype.JClass("org.tweetyproject.logics.pl.parser.PlParser"),
            "Proposition": jpype.JClass("org.tweetyproject.logics.pl.syntax.Proposition"),
            "SimplePlReasoner": jpype.JClass("org.tweetyproject.logics.pl.reasoner.SimplePlReasoner"),
            "Negation": jpype.JClass("org.tweetyproject.logics.pl.syntax.Negation"),
            "Conjunction": jpype.JClass("org.tweetyproject.logics.pl.syntax.Conjunction"),
            "Disjunction": jpype.JClass("org.tweetyproject.logics.pl.syntax.Disjunction"),
            "Implication": jpype.JClass("org.tweetyproject.logics.pl.syntax.Implication"),
            "Equivalence": jpype.JClass("org.tweetyproject.logics.pl.syntax.Equivalence"),
            "PlFormula": jpype.JClass("org.tweetyproject.logics.pl.syntax.PlFormula"),
            "PossibleWorldIterator": jpype.JClass("org.tweetyproject.logics.pl.util.PossibleWorldIterator"),
            "PlSignature": jpype.JClass("org.tweetyproject.logics.pl.syntax.PlSignature"),
        }

        logger.info("--- Exécution de _test_load_logic_theory_from_file ---")
        _test_load_logic_theory_from_file(logic_classes, worker_dir)

        logger.info("--- Exécution de _test_simple_pl_reasoner_queries ---")
        _test_simple_pl_reasoner_queries(logic_classes, worker_dir)
        
        logger.info("--- Exécution de _test_formula_syntax_and_semantics ---")
        _test_formula_syntax_and_semantics(logic_classes)

        print("--- Toutes les assertions du worker ont réussi ---")

    except Exception as e:
        logger.error(f"Erreur dans le worker d'opérations logiques: {e}", exc_info=True)
        raise
    finally:
        if jpype.isJVMStarted():
            jpype.shutdownJVM()
            print("--- JVM arrêtée avec succès dans le worker ---")


if __name__ == "__main__":
    try:
        test_logic_operations_logic()
        print("--- Le worker d'opérations logiques s'est terminé avec succès. ---")
    except Exception as e:
        print(f"Une erreur est survenue dans le worker : {e}", file=sys.stderr)
        sys.exit(1)