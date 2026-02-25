# -*- coding: utf-8 -*-
# Step 1: Résolution du Conflit de Librairies Natives (torch vs jpype)
try:
    import torch
except ImportError:
    pass  # Si torch n'est pas là, on ne peut rien faire.

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
    """
    Récupère la racine du projet depuis la variable d'environnement PROJECT_ROOT,
    qui est définie de manière fiable par le script d'activation.
    """
    project_root_str = os.getenv("PROJECT_ROOT")
    if not project_root_str:
        raise RuntimeError(
            "La variable d'environnement PROJECT_ROOT n'est pas définie. "
            "Assurez-vous d'exécuter ce script via activate_project_env.ps1"
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


def _test_preferred_reasoner_complex(dung_classes):
    """Test du raisonneur préféré avec un framework complexe (diamant)."""
    DungTheory = dung_classes["DungTheory"]
    Argument = dung_classes["Argument"]
    Attack = dung_classes["Attack"]
    PreferredReasoner = dung_classes["PreferredReasoner"]

    # Diamond framework: a <-> b, c -> a, c -> b
    dt = DungTheory()
    a, b, c, d = Argument("a"), Argument("b"), Argument("c"), Argument("d")
    dt.add(a)
    dt.add(b)
    dt.add(c)
    dt.add(d)
    dt.add(Attack(a, b))
    dt.add(Attack(b, a))
    dt.add(Attack(c, d))

    reasoner = PreferredReasoner()
    extensions = reasoner.getModels(dt)
    # Should have 2 preferred extensions: {a, c} and {b, c}
    assert (
        extensions.size() == 2
    ), f"Expected 2 preferred extensions, got {extensions.size()}"
    logger.info(
        f"Test preferred reasoner complex: {extensions.size()} extensions found."
    )


def _test_complete_reasoner(dung_classes):
    """Test du raisonneur complet."""
    DungTheory = dung_classes["DungTheory"]
    Argument = dung_classes["Argument"]
    Attack = dung_classes["Attack"]
    CompleteReasoner = dung_classes["CompleteReasoner"]

    # Simple chain: a -> b -> c
    dt = DungTheory()
    a, b, c = Argument("a"), Argument("b"), Argument("c")
    dt.add(a)
    dt.add(b)
    dt.add(c)
    dt.add(Attack(a, b))
    dt.add(Attack(b, c))

    reasoner = CompleteReasoner()
    extensions = reasoner.getModels(dt)
    assert (
        extensions.size() >= 1
    ), f"Expected at least 1 complete extension, got {extensions.size()}"
    logger.info(
        f"Test complete reasoner: {extensions.size()} complete extensions found."
    )


def _test_grounded_reasoner(dung_classes):
    """Test du raisonneur fondé."""
    DungTheory = dung_classes["DungTheory"]
    Argument = dung_classes["Argument"]
    Attack = dung_classes["Attack"]
    GroundedReasoner = dung_classes["GroundedReasoner"]

    # Framework: a -> b, c -> b (a and c are unattacked, b is attacked)
    dt = DungTheory()
    a, b, c = Argument("a"), Argument("b"), Argument("c")
    dt.add(a)
    dt.add(b)
    dt.add(c)
    dt.add(Attack(a, b))
    dt.add(Attack(c, b))

    reasoner = GroundedReasoner()
    grounded = reasoner.getModel(dt)
    assert grounded is not None
    py_grounded = {str(arg.getName()) for arg in grounded}
    # a and c are unattacked, b is attacked by both -> grounded = {a, c}
    assert py_grounded == {"a", "c"}, f"Expected {{a, c}}, got {py_grounded}"
    logger.info(f"Test grounded reasoner: grounded extension = {py_grounded}")


def _test_stable_vs_preferred(dung_classes):
    """Compare stable and preferred semantics."""
    DungTheory = dung_classes["DungTheory"]
    Argument = dung_classes["Argument"]
    Attack = dung_classes["Attack"]
    StableReasoner = dung_classes["StableReasoner"]
    PreferredReasoner = dung_classes["PreferredReasoner"]

    # Odd cycle: a -> b -> c -> a (no stable extension, but preferred exists)
    dt = DungTheory()
    a, b, c = Argument("a"), Argument("b"), Argument("c")
    dt.add(a)
    dt.add(b)
    dt.add(c)
    dt.add(Attack(a, b))
    dt.add(Attack(b, c))
    dt.add(Attack(c, a))

    stable = StableReasoner()
    stable_ext = stable.getModels(dt)
    preferred = PreferredReasoner()
    preferred_ext = preferred.getModels(dt)

    # Odd cycle: 0 stable extensions, but preferred extensions exist (empty set)
    logger.info(
        f"Odd cycle: {stable_ext.size()} stable, {preferred_ext.size()} preferred extensions"
    )
    assert (
        stable_ext.size() == 0
    ), f"Odd cycle should have 0 stable extensions, got {stable_ext.size()}"
    assert preferred_ext.size() >= 1, f"Odd cycle should have preferred extensions"


def test_asp_reasoner_consistency_logic():
    """
    Point d'entrée principal. Tests de raisonnement avancé sur les frameworks
    d'argumentation de Dung (preferred, complete, grounded, stable).
    """
    print("--- Début du worker pour test_asp_reasoner_consistency_logic ---")
    setup_jvm()

    try:
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
            "PreferredReasoner": jpype.JClass(
                "org.tweetyproject.arg.dung.reasoner.SimplePreferredReasoner"
            ),
            "GroundedReasoner": jpype.JClass(
                "org.tweetyproject.arg.dung.reasoner.SimpleGroundedReasoner"
            ),
        }

        logger.info("--- Exécution de _test_preferred_reasoner_complex ---")
        _test_preferred_reasoner_complex(dung_classes)

        logger.info("--- Exécution de _test_complete_reasoner ---")
        _test_complete_reasoner(dung_classes)

        logger.info("--- Exécution de _test_grounded_reasoner ---")
        _test_grounded_reasoner(dung_classes)

        logger.info("--- Exécution de _test_stable_vs_preferred ---")
        _test_stable_vs_preferred(dung_classes)

        print("--- Toutes les assertions du worker ont réussi ---")

    except Exception as e:
        logger.error(
            f"Erreur dans le worker de raisonnement avancé: {e}", exc_info=True
        )
        raise
    finally:
        logger.info(
            "--- Le worker a terminé sa tâche. La gestion de l'arrêt de la JVM est laissée au processus principal. ---"
        )


if __name__ == "__main__":
    try:
        test_asp_reasoner_consistency_logic()
        print("--- Le worker s'est terminé avec succès. ---")
    except Exception as e:
        print(f"Une erreur est survenue dans le worker : {e}", file=sys.stderr)
        sys.exit(1)
