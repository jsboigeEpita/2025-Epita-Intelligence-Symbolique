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
    """Démarre la JVM avec le classpath nécessaire, si elle n'est pas déjà démarrée."""
    if jpype.isJVMStarted():
        logger.info("--- La JVM est déjà démarrée (probablement par pytest). Le worker l'utilise. ---")
        return

    project_root = get_project_root_from_env()
    libs_dir = project_root / "libs" / "tweety"
    full_jar_path = libs_dir / "org.tweetyproject.tweety-full-1.28-with-dependencies.jar"
    if not full_jar_path.exists():
        raise FileNotFoundError(f"Le JAR complet 'tweety-full' n'a pas été trouvé dans {libs_dir}")

    classpath = str(full_jar_path.resolve())
    logger.info(f"Démarrage de la JVM avec le classpath: {classpath}")
    try:
        logger.info("--- La JVM n'est pas démarrée. Tentative de démarrage par le worker... ---")
        jpype.startJVM(jpype.getDefaultJVMPath(), "-ea", classpath=classpath, convertStrings=False)
        logger.info("--- JVM démarrée avec succès par le worker ---")
    except Exception as e:
        logger.error(f"ERREUR: Échec du démarrage de la JVM par le worker : {e}", exc_info=True)
        raise

def _test_simple_preferred_reasoner(dung_classes):
    DungTheory, Argument, Attack, SimplePreferredReasoner = dung_classes["DungTheory"], dung_classes["Argument"], dung_classes["Attack"], dung_classes["SimplePreferredReasoner"]
    theory = DungTheory()
    arg_a, arg_b, arg_c = Argument("a"), Argument("b"), Argument("c")
    theory.add(arg_a); theory.add(arg_b); theory.add(arg_c)
    theory.add(Attack(arg_a, arg_b))
    theory.add(Attack(arg_b, arg_c))
    pr = SimplePreferredReasoner()
    preferred_extensions_collection = pr.getModels(theory)
    assert preferred_extensions_collection.size() == 1
    logger.info("Test du raisonneur préféré simple réussi.")

def _test_simple_grounded_reasoner(dung_classes):
    DungTheory, Argument, Attack, GroundedReasoner = dung_classes["DungTheory"], dung_classes["Argument"], dung_classes["Attack"], dung_classes["GroundedReasoner"]
    theory = DungTheory()
    arg_a, arg_b, arg_c = Argument("a"), Argument("b"), Argument("c")
    theory.add(arg_a); theory.add(arg_b); theory.add(arg_c)
    theory.add(Attack(arg_a, arg_b))
    gr = GroundedReasoner()
    grounded_extension_java_set = gr.getModel(theory)
    assert grounded_extension_java_set is not None
    py_grounded_extension = {str(arg.getName()) for arg in grounded_extension_java_set}
    expected_grounded_extension = {"a", "c"}
    assert py_grounded_extension == expected_grounded_extension
    logger.info("Test du raisonneur fondé simple réussi.")


def test_dialogical_argumentation_logic():
    """Point d'entrée principal pour la logique de test dialogique."""
    print("--- Début du worker pour test_dialogical_argumentation_logic ---")
    setup_jvm()

    try:
        # Import des classes Java
        dung_classes = {
            "DungTheory": jpype.JClass("org.tweetyproject.arg.dung.syntax.DungTheory"),
            "Argument": jpype.JClass("org.tweetyproject.arg.dung.syntax.Argument"),
            "Attack": jpype.JClass("org.tweetyproject.arg.dung.syntax.Attack"),
            "SimplePreferredReasoner": jpype.JClass("org.tweetyproject.arg.dung.reasoner.SimplePreferredReasoner"),
            "GroundedReasoner": jpype.JClass("org.tweetyproject.arg.dung.reasoner.GroundedReasoner")
        }
        # Importer d'autres classes si nécessaire...
        
        # L'import de jpype.JString n'est pas nécessaire, il suffit d'utiliser jpype.JString
        
        # Exécution des tests
        logger.info("--- Exécution de _test_simple_preferred_reasoner ---")
        _test_simple_preferred_reasoner(dung_classes)

        logger.info("--- Exécution de _test_simple_grounded_reasoner ---")
        _test_simple_grounded_reasoner(dung_classes)

        # Ajoutez d'autres appels de sous-fonctions de test ici au besoin.
        # Par exemple, pour `test_create_argumentation_agent`, `test_persuasion_protocol_setup`, etc.
        # Ces tests nécessiteraient d'importer plus de classes java (dialogue_classes etc.)

        print("--- Toutes les assertions du worker ont réussi ---")

    except Exception as e:
        logger.error(f"Erreur dans le worker d'argumentation dialogique: {e}", exc_info=True)
        raise
    finally:
        # Ne pas arrêter la JVM ici. La fixture pytest s'en chargera.
        # if jpype.isJVMStarted():
        #     jpype.shutdownJVM()
        #     print("--- JVM arrêtée avec succès dans le worker ---")
        logger.info("--- Le worker a terminé sa tâche. La gestion de l'arrêt de la JVM est laissée au processus principal. ---")

if __name__ == "__main__":
    try:
        test_dialogical_argumentation_logic()
        print("--- Le worker d'argumentation dialogique s'est terminé avec succès. ---")
    except Exception as e:
        print(f"Une erreur est survenue dans le worker : {e}", file=sys.stderr)
        sys.exit(1)