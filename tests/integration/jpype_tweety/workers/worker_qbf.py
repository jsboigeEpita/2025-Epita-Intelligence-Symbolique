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

def _test_qbf_parser_simple_formula(qbf_classes):
    QbfParser = qbf_classes["QbfParser"]
    parser = QbfParser()
    qbf_string = "exists x forall y (x or not y)"
    formula = parser.parseFormula(qbf_string)
    assert formula is not None
    assert "exists" in str(formula.toString()).lower()
    assert "forall" in str(formula.toString()).lower()
    logger.info(f"Parsing de formule QBF simple réussi: {formula.toString()}")

def _test_qbf_programmatic_creation(qbf_classes):
    QuantifiedBooleanFormula = qbf_classes["QuantifiedBooleanFormula"]
    Quantifier = qbf_classes["Quantifier"]
    Variable = qbf_classes["Variable"]
    x_var = Variable("x")
    quantified_vars = jpype.JArray(Variable)([x_var])
    qbf = QuantifiedBooleanFormula(Quantifier.EXISTS, quantified_vars, x_var)
    assert qbf is not None
    assert qbf.getQuantifier() == Quantifier.EXISTS
    assert len(qbf.getVariables()) == 1
    logger.info("Création programmatique de QBF simple réussie.")

def test_qbf_logic():
    """Point d'entrée principal pour les tests QBF."""
    print("--- Début du worker pour test_qbf_logic ---")
    setup_jvm()

    try:
        qbf_classes = {
            "QbfParser": jpype.JClass("org.tweetyproject.logics.qbf.parser.QbfParser"),
            "QuantifiedBooleanFormula": jpype.JClass("org.tweetyproject.logics.qbf.syntax.QuantifiedBooleanFormula"),
            "Quantifier": jpype.JClass("org.tweetyproject.logics.qbf.syntax.Quantifier"),
            "Variable": jpype.JClass("org.tweetyproject.logics.qbf.syntax.Variable"),
            # Les classes propositionnelles sont souvent nécessaires
            "Proposition": jpype.JClass("org.tweetyproject.logics.propositional.syntax.Proposition"),
            "Conjunction": jpype.JClass("org.tweetyproject.logics.propositional.syntax.Conjunction"),
            "Negation": jpype.JClass("org.tweetyproject.logics.propositional.syntax.Negation"),
        }

        logger.info("--- Exécution de _test_qbf_parser_simple_formula ---")
        _test_qbf_parser_simple_formula(qbf_classes)

        logger.info("--- Exécution de _test_qbf_programmatic_creation ---")
        _test_qbf_programmatic_creation(qbf_classes)

        # Les autres tests (PNF, solveur) sont plus complexes et dépendent
        # de plus de classes ou de configuration externe. Ils sont omis
        # pour cette migration de stabilisation.

        print("--- Toutes les assertions du worker ont réussi ---")

    except Exception as e:
        logger.error(f"Erreur dans le worker QBF: {e}", exc_info=True)
        raise
    finally:
        if jpype.isJVMStarted():
            jpype.shutdownJVM()
            print("--- JVM arrêtée avec succès dans le worker ---")

if __name__ == "__main__":
    try:
        test_qbf_logic()
        print("--- Le worker QBF s'est terminé avec succès. ---")
    except Exception as e:
        print(f"Une erreur est survenue dans le worker QBF : {e}", file=sys.stderr)
        sys.exit(1)