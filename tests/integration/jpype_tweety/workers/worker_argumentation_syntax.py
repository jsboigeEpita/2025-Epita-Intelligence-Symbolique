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


# Fonctions de test individuelles
def _test_create_argument(dung_classes):
    Argument = dung_classes["Argument"]
    arg_name = "test_argument"
    arg = Argument(jpype.JString(arg_name))
    assert arg is not None
    assert arg.getName() == arg_name
    logger.info(f"Argument créé: {arg.toString()}")


def _test_create_dung_theory_with_arguments_and_attacks(dung_classes):
    DungTheory, Argument, Attack = (
        dung_classes["DungTheory"],
        dung_classes["Argument"],
        dung_classes["Attack"],
    )
    dung_theory = DungTheory()
    arg_a, arg_b, arg_c = Argument("a"), Argument("b"), Argument("c")
    dung_theory.add(arg_a)
    dung_theory.add(arg_b)
    dung_theory.add(arg_c)
    assert dung_theory.getNodes().size() == 3
    attack_b_a, attack_c_b = Attack(arg_b, arg_a), Attack(arg_c, arg_b)
    dung_theory.add(attack_b_a)
    dung_theory.add(attack_c_b)
    assert dung_theory.getAttacks().size() == 2
    assert dung_theory.isAttackedBy(arg_a, arg_b)
    assert dung_theory.isAttackedBy(arg_b, arg_c)
    logger.info(f"Théorie de Dung créée: {dung_theory.toString()}")


def _test_argument_equality_and_hashcode(dung_classes):
    Argument = dung_classes["Argument"]
    arg1_a, arg2_a, arg_b = Argument("a"), Argument("a"), Argument("b")
    assert arg1_a.equals(arg2_a)
    assert not arg1_a.equals(arg_b)
    assert arg1_a.hashCode() == arg2_a.hashCode()
    HashSet = jpype.JClass("java.util.HashSet")
    java_set = HashSet()
    java_set.add(arg1_a)
    assert java_set.contains(arg2_a)
    java_set.add(arg_b)
    assert java_set.size() == 2
    java_set.add(arg2_a)
    assert java_set.size() == 2
    logger.info("Tests d'égalité et de hashcode pour Argument réussis.")


def _test_attack_equality_and_hashcode(dung_classes):
    Argument, Attack = dung_classes["Argument"], dung_classes["Attack"]
    a, b, c = Argument("a"), Argument("b"), Argument("c")
    attack1_ab = Attack(a, b)
    attack2_ab = Attack(Argument("a"), Argument("b"))
    attack_ac = Attack(a, c)
    assert attack1_ab.equals(attack2_ab)
    assert not attack1_ab.equals(attack_ac)
    assert attack1_ab.hashCode() == attack2_ab.hashCode()
    logger.info("Tests d'égalité et de hashcode pour Attack réussis.")


def _test_stable_reasoner_simple_example(dung_classes):
    DungTheory, Argument, Attack, StableReasoner = (
        dung_classes["DungTheory"],
        dung_classes["Argument"],
        dung_classes["Attack"],
        dung_classes["StableReasoner"],
    )
    dt = DungTheory()
    a, b, c = Argument("a"), Argument("b"), Argument("c")
    dt.add(a)
    dt.add(b)
    dt.add(c)
    dt.add(Attack(a, b))
    dt.add(Attack(b, c))
    reasoner = StableReasoner()
    extensions = reasoner.getModels(dt)
    assert extensions.size() == 1
    # Simplified check
    logger.info(f"Extension stable simple calculée.")


def test_argumentation_syntax_logic():
    """Point d'entrée principal pour la logique de test."""
    print("--- Début du worker pour test_argumentation_syntax_logic ---")
    setup_jvm()

    try:
        # Import des classes Java nécessaires
        dung_classes = {
            "DungTheory": jpype.JClass("org.tweetyproject.arg.dung.syntax.DungTheory"),
            "Argument": jpype.JClass("org.tweetyproject.arg.dung.syntax.Argument"),
            "Attack": jpype.JClass("org.tweetyproject.arg.dung.syntax.Attack"),
            "CompleteReasoner": jpype.JClass(
                "org.tweetyproject.arg.dung.reasoner.SimpleCompleteReasoner"
            ),
            "StableReasoner": jpype.JClass(
                "org.tweetyproject.arg.dung.reasoner.SimpleStableReasoner"
            ),
        }

        # Exécution des tests individuels
        logger.info("--- Exécution de _test_create_argument ---")
        _test_create_argument(dung_classes)

        logger.info(
            "--- Exécution de _test_create_dung_theory_with_arguments_and_attacks ---"
        )
        _test_create_dung_theory_with_arguments_and_attacks(dung_classes)

        logger.info("--- Exécution de _test_argument_equality_and_hashcode ---")
        _test_argument_equality_and_hashcode(dung_classes)

        logger.info("--- Exécution de _test_attack_equality_and_hashcode ---")
        _test_attack_equality_and_hashcode(dung_classes)

        logger.info("--- Exécution de _test_stable_reasoner_simple_example ---")
        _test_stable_reasoner_simple_example(dung_classes)

        print("--- Toutes les assertions du worker ont réussi ---")

    except Exception as e:
        logger.error(
            f"Erreur dans le worker de syntaxe d'argumentation: {e}", exc_info=True
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
        test_argumentation_syntax_logic()
        print("--- Le worker de syntaxe d'argumentation s'est terminé avec succès. ---")
    except Exception as e:
        print(f"Une erreur est survenue dans le worker : {e}", file=sys.stderr)
        sys.exit(1)
