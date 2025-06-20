# -*- coding: utf-8 -*-
# Step 1: Résolution du Conflit de Librairies Natives (torch vs jpype)
try:
    import torch
except ImportError:
    pass # Si torch n'est pas là, on ne peut rien faire.

import jpype
import jpype.imports
import os
from pathlib import Path
import sys

def get_project_root_from_env() -> Path:
    """
    Récupère la racine du projet depuis la variable d'environnement PROJECT_ROOT,
    qui est définie de manière fiable par le script d'activation.
    """
    project_root_str = os.getenv("PROJECT_ROOT")
    if not project_root_str:
        raise RuntimeError("La variable d'environnement PROJECT_ROOT n'est pas définie. "
                           "Assurez-vous d'exécuter ce script via activate_project_env.ps1")
    return Path(project_root_str)

def test_asp_reasoner_consistency_logic():
    """
    Contient la logique de test réelle pour le 'ASP reasoner',
    destinée à être exécutée dans un sous-processus avec une JVM propre.
    """
    print("--- Début du worker pour test_asp_reasoner_consistency_logic ---")
    
    # Construction explicite et robuste du classpath
    project_root = get_project_root_from_env()
    libs_dir = project_root / "libs" / "tweety"
    print(f"Recherche des JARs dans : {libs_dir}")

    if not libs_dir.exists():
        raise FileNotFoundError(f"Le répertoire des bibliothèques Tweety n'existe pas : {libs_dir}")

    # Utiliser uniquement le JAR complet pour éviter les conflits de classpath
    full_jar_path = libs_dir / "org.tweetyproject.tweety-full-1.28-with-dependencies.jar"
    if not full_jar_path.exists():
        raise FileNotFoundError(f"Le JAR complet 'tweety-full' n'a pas été trouvé dans {libs_dir}")

    classpath = str(full_jar_path.resolve())
    print(f"Classpath construit avec un seul JAR : {classpath}")

    # Démarrer la JVM
    try:
        jpype.startJVM(jpype.getDefaultJVMPath(), "-ea", classpath=classpath, convertStrings=False)
        print("--- JVM démarrée avec succès dans le worker ---")
    except Exception as e:
        print(f"ERREUR: Échec du démarrage de la JVM : {e}", file=sys.stderr)
        raise

    # Effectuer les importations nécessaires pour le test
    try:
        from org.tweetyproject.logics.pl.syntax import PropositionalSignature
        from org.tweetyproject.arg.asp.syntax import AspRule, AnswerSet
        from org.tweetyproject.arg.asp.reasoner import AnswerSetSolver
        from java.util import HashSet
    except Exception as e:
        print(f"ERREUR irrécupérable: Échec de l'importation d'une classe Java requise: {e}", file=sys.stderr)
        if jpype.isJVMStarted():
            jpype.shutdownJVM()
        raise

    try:
        print("DEBUG: Tentative d'importation de 'org.tweetyproject.arg.asp.reasoner'")
        from org.tweetyproject.arg.asp import reasoner as asp_reasoner
        print("DEBUG: Importation de 'asp_reasoner' réussie.")
    except Exception as e:
        print(f"ERREUR: Échec de l'importation de asp_reasoner: {e}", file=sys.stderr)
        jpype.shutdownJVM()
        raise

    # Scénario de test
    theory = asp_syntax.AspRuleSet()
    a = pl_syntax.Proposition("a")
    b = pl_syntax.Proposition("b")
    theory.add(asp_syntax.AspRule(a, [b]))
    theory.add(asp_syntax.AspRule(b, []))

    reasoner = asp_reasoner.SimpleAspReasoner()
    
    # Assertions
    assert reasoner.query(theory, a)
    assert not reasoner.query(theory, pl_syntax.Proposition("c"))
    
    print("--- Assertions du worker réussies ---")

    # Arrêt propre de la JVM
    jpype.shutdownJVM()
    print("--- JVM arrêtée avec succès dans le worker ---")


if __name__ == "__main__":
    try:
        test_asp_reasoner_consistency_logic()
        print("--- Le worker s'est terminé avec succès. ---")
    except Exception as e:
        print(f"Une erreur est survenue dans le worker : {e}", file=sys.stderr)
        sys.exit(1)