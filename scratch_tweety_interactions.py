import sys
import os
import glob
import jpype
import jpype.imports

def start_jvm_with_tweety_simplified():
    if jpype.isJVMStarted():
        print("INFO: La JVM est déjà démarrée.")
        return True

    java_home = os.environ.get('JAVA_HOME')
    script_dir = os.path.dirname(os.path.abspath(__file__))
    libs_dir_scratch = os.path.join(script_dir, "libs")
    
    # Vérifier si libs_dir_scratch existe avant de lister les JARs
    if not os.path.isdir(libs_dir_scratch):
        print(f"ERREUR: Le répertoire libs '{libs_dir_scratch}' est introuvable.")
        return False
    classpath_entries_scratch = [os.path.join(libs_dir_scratch, f) for f in os.listdir(libs_dir_scratch) if f.endswith('.jar')]
    if not classpath_entries_scratch:
        print(f"AVERTISSEMENT: Aucun fichier .jar trouvé dans '{libs_dir_scratch}'.")
        # On continue quand même pour voir si JPype peut démarrer, mais Tweety ne fonctionnera pas.
        
    jvm_path_to_use = None
    preferred_jvm_source = "" # Pour le message d'information

    # Priorité 1: JDK Portable
    portable_jdk_base_dir = os.path.join(script_dir, "portable_jdk")
    # Chercher un sous-répertoire jdk-17 (plus flexible que le nom exact)
    jdk_sub_dirs = []
    if os.path.isdir(portable_jdk_base_dir):
        jdk_sub_dirs = [d for d in os.listdir(portable_jdk_base_dir) if os.path.isdir(os.path.join(portable_jdk_base_dir, d)) and d.startswith("jdk-17")]
    
    portable_jdk17_jvm_path = None
    if jdk_sub_dirs:
        # Prendre le premier trouvé (ou le plus récent si on triait)
        portable_jdk17_dir_actual = os.path.join(portable_jdk_base_dir, jdk_sub_dirs[0])
        print(f"INFO: Utilisation du JDK portable trouvé : {portable_jdk17_dir_actual}")
        if sys.platform == "win32":
            portable_jdk17_jvm_path = os.path.join(portable_jdk17_dir_actual, "bin", "server", "jvm.dll")
        elif sys.platform == "darwin":
            portable_jdk17_jvm_path = os.path.join(portable_jdk17_dir_actual, "lib", "server", "libjvm.dylib")
        else: # Linux
            portable_jdk17_jvm_path = os.path.join(portable_jdk17_dir_actual, "lib", "server", "libjvm.so")

    if portable_jdk17_jvm_path and os.path.exists(portable_jdk17_jvm_path):
        jvm_path_to_use = portable_jdk17_jvm_path
        preferred_jvm_source = f"JDK Portable ({jdk_sub_dirs[0]})"
    
    # Priorité 2: JAVA_HOME
    if not jvm_path_to_use and java_home:
        preferred_jvm_source = "JAVA_HOME"
        if sys.platform == "win32":
            cand_path = os.path.join(java_home, 'bin', 'server', 'jvm.dll')
            if not os.path.exists(cand_path): # Essai alternatif
                cand_path = os.path.join(java_home, 'bin', 'jvm.dll')
        elif sys.platform == "darwin":
            cand_path = os.path.join(java_home, 'lib', 'server', 'libjvm.dylib')
        else: # Linux
            cand_path = os.path.join(java_home, 'lib', 'server', 'libjvm.so')
        
        if os.path.exists(cand_path):
            jvm_path_to_use = cand_path
        else:
            print(f"AVERTISSEMENT: Impossible de trouver un fichier JVM valide dans JAVA_HOME ({java_home}) avec les chemins standards.")
            preferred_jvm_source = "" # Réinitialiser si JAVA_HOME n'est pas utilisable

    # Priorité 3: JPype Default
    if not jvm_path_to_use:
        try:
            jvm_path_to_use = jpype.getDefaultJVMPath()
            preferred_jvm_source = "JPype Default"
        except Exception as e_default_jvm:
            print(f"INFO: Impossible d'obtenir le chemin JVM par défaut de JPype: {e_default_jvm}")

    if not jvm_path_to_use:
        print("ERREUR CRITIQUE: Aucun chemin JVM n'a pu être déterminé (Portable, JAVA_HOME, ou JPype par défaut).")
        return False
    
    print(f"INFO: Tentative de démarrage de la JVM avec '{preferred_jvm_source}': {jvm_path_to_use}")
    if classpath_entries_scratch:
        print(f"   Utilisation du classpath: {os.pathsep.join(classpath_entries_scratch)}")
    else:
        print("   AVERTISSEMENT: Aucun JAR dans le classpath. Les imports Tweety échoueront probablement.")

    try:
        jpype.startJVM(jvm_path_to_use, "-ea", classpath=classpath_entries_scratch, convertStrings=False)
        print("INFO: JVM démarrée avec succès.")
        jpype.imports.registerDomain("org")
        print("INFO: Domaine 'org' enregistré pour les imports JPype.")
        return True
    except Exception as e:
        print(f"ERREUR lors du démarrage de la JVM: {e}")
        return False

if not start_jvm_with_tweety_simplified():
    print("Arrêt du script en raison de l'échec du démarrage/configuration de la JVM.")
    sys.exit(1)

# Tenter de charger uniquement les classes qui semblent les plus stables
# Ces variables seront globales pour la fonction main()
_PlSignature = None
_PlParser = None
_PropositionalFormula = None # On va essayer de l'utiliser avec précaution
_SatSolver = None

try:
    print("INFO: Tentative de chargement des classes Tweety via JClass...")
    _PlSignature = jpype.JClass("org.tweetyproject.logics.pl.syntax.PlSignature")
    print("  INFO: PlSignature chargée.")
    _PlParser = jpype.JClass("org.tweetyproject.logics.pl.parser.PlParser")
    print("  INFO: PlParser chargé.")
    
    # On essaie quand même de charger PropositionalFormula et SatSolver, mais les tests seront conditionnels
    try:
        _PropositionalFormula = jpype.JClass("org.tweetyproject.logics.pl.syntax.PropositionalFormula")
        print("  INFO: PropositionalFormula chargée.")
    except TypeError: # L'erreur réelle est TypeError si la classe n'est pas trouvée par JClass
        print("  AVERTISSEMENT: PropositionalFormula n'a pas pu être chargée via JClass.")
    
    try:
        _SatSolver = jpype.JClass("org.tweetyproject.logics.pl.sat.SatSolver")
        print("  INFO: SatSolver chargé.")
    except TypeError:
        print("  AVERTISSEMENT: SatSolver n'a pas pu être chargé via JClass.")
        
    print("INFO: Tentative de chargement des classes Tweety via JClass terminée.")

except TypeError as e_jclass_main: # Attraper TypeError pour les JClass principaux
    print(f"ERREUR CRITIQUE lors du chargement de PlSignature ou PlParser: {e_jclass_main}")
    print("  Cela indique un problème fondamental avec l'accès aux JARs ou la configuration JPype.")
    if jpype.isJVMStarted(): jpype.shutdownJVM()
    sys.exit(1)
except Exception as e_unexpected: # Autres erreurs inattendues
    print(f"ERREUR INATTENDUE lors du chargement des classes: {e_unexpected}")
    if jpype.isJVMStarted(): jpype.shutdownJVM()
    sys.exit(1)


def main():
    print("\nDébut des tests d'interactions fondamentales (simplifiés) avec Tweety...")

    # Test 1: Instanciation de PlSignature
    print("\n--- Test 1: Instanciation de PlSignature ---")
    if _PlSignature:
        try:
            sig = _PlSignature()
            print(f"   PlSignature instanciée: {sig}")
            if _PropositionalFormula:
                p_prop = _PropositionalFormula("p")
                sig.add(p_prop) # Nécessite que _PropositionalFormula soit une classe valide
                print(f"   Proposition 'p' ajoutée à la signature: {sig}")
            else:
                print("   PropositionalFormula non disponible, test d'ajout de proposition sauté.")
            print("   Test 1 Réussi.")
        except Exception as e:
            print(f"   Erreur Test 1: {e}")
            if isinstance(e, jpype.JavaException): print(f"      Exception Java: {e.java_exception()}")
    else:
        print("   PlSignature non disponible, test sauté.")

    # Test 2: Utilisation simple de PlParser
    print("\n--- Test 2: Utilisation simple de PlParser ---")
    if _PlParser:
        try:
            parser = _PlParser()
            print(f"   PlParser instancié: {parser}")
            print(f"   Type de l'objet parser: {type(parser)}")
            print(f"   Attributs de l'objet parser (dir):")
            for attr in dir(parser):
                print(f"     - {attr}")
            
            # Tenter de parser une formule simple
            # Cela dépendra si _PropositionalFormula a pu être chargé et est le type retourné par parse.
            formula_str_ok = "a"
            formula_str_complex = "b && c"
            formula_to_test = "p && q"
            
            print(f"\n   Tentative de parsing de '{formula_to_test}':")
            try:
                # Tentative avec parser.parseFormula()
                print(f"     Tentative 1: parser.parseFormula(\"{formula_to_test}\")")
                parsed_formula = parser.parseFormula(formula_to_test)
                print(f"       Formule '{formula_to_test}' parsée: {parsed_formula}")
                print(f"       Type de l'objet retourné: {type(parsed_formula)}")
                print(f"       Attributs de l'objet retourné (dir):")
                for attr in dir(parsed_formula):
                    print(f"         - {attr}")
                
                # Vérification heuristique du type de retour
                if hasattr(parsed_formula, 'getClass'):
                    class_name = parsed_formula.getClass().getName()
                    print(f"       Nom de la classe Java: {class_name}")
                    if "PropositionalFormula" in class_name or "Conjunction" in class_name or "Disjunction" in class_name or "Negation" in class_name or "Proposition" in class_name:
                        print("         Le type semble correspondre à une formule propositionnelle de Tweety.")
                        print("       Test 2 (PlParser.parseFormula) Réussi.")
                    else:
                        print("         ATTENTION: Le type retourné ne semble pas être une formule propositionnelle standard de Tweety.")
                else:
                    print("         ATTENTION: L'objet retourné n'a pas de méthode getClass(), introspection limitée.")

            except AttributeError as ae:
                print(f"     ERREUR AttributeError: {ae}")
                print(f"       La méthode 'parseFormula' (ou 'parse') n'est pas directement accessible comme attribut.")
                # Ici, on pourrait ajouter d'autres tentatives si parseFormula échoue aussi, mais c'est moins probable.
            except jpype.JException as je:
                print(f"     Erreur Java lors du parsing avec parseFormula: {je}")
                print(f"        Message Java: {je.message()}")
                if hasattr(je, 'stacktrace') and callable(je.stacktrace):
                    print(f"        Stacktrace Java:\n{je.stacktrace()}")
            except Exception as e_parse:
                print(f"     Erreur Python lors du parsing avec parseFormula: {e_parse}")
                import traceback
                print(traceback.format_exc())

        except Exception as e_parser_init:
            print(f"   Erreur lors de l'initialisation/utilisation de PlParser: {e_parser_init}")
            if isinstance(e_parser_init, jpype.JException): print(f"      Exception Java: {e_parser_init.java_exception()}")
    else:
        print("   PlParser non disponible, test sauté.")
        
    # Test 3: Vérification de la satisfiabilité (très conditionnel)
    print("\n--- Test 3: Vérification de la satisfiabilité (conditionnel) ---")
    if _SatSolver and _PlSignature and _PropositionalFormula and _PlParser:
        try:
            sig_sat = _PlSignature()
            a_prop = _PropositionalFormula("a")
            b_prop = _PropositionalFormula("b")
            sig_sat.add(a_prop)
            sig_sat.add(b_prop)

            parser_sat = _PlParser()
            
            formula_satisfiable_str = "a && b"
            formula_satisfiable = parser_sat.parse(formula_satisfiable_str)
            print(f"   Vérification de la satisfiabilité pour : {formula_satisfiable}")
            is_satisfiable = _SatSolver.isSatisfiable(formula_satisfiable, sig_sat)
            print(f"   La formule '{formula_satisfiable}' est satisfiable : {is_satisfiable}")

            formula_unsatisfiable_str = "a && !a"
            formula_unsatisfiable = parser_sat.parse(formula_unsatisfiable_str)
            print(f"   Vérification de la satisfiabilité pour : {formula_unsatisfiable}")
            is_unsatisfiable = _SatSolver.isSatisfiable(formula_unsatisfiable, sig_sat)
            print(f"   La formule '{formula_unsatisfiable}' est satisfiable : {is_unsatisfiable}")
            print("   Test 3 Réussi.")
        except Exception as e:
            print(f"   Erreur Test 3: {e}")
            if isinstance(e, jpype.JException): print(f"      Exception Java: {e.java_exception()}") # Correction: Utiliser JException
    else:
        print("   SatSolver, PlSignature, PropositionalFormula ou PlParser non disponible(s), test de satisfiabilité sauté.")

    print("\nFin des tests simplifiés.")

if __name__ == "__main__":
    main()

if jpype.isJVMStarted():
    print("\nINFO: Tentative d'arrêt de la JVM...")
    try:
        jpype.shutdownJVM()
        print("INFO: JVM arrêtée avec succès.")
    except Exception as e_shutdown:
        print(f"AVERTISSEMENT: Exception lors de l'arrêt de la JVM: {e_shutdown}")