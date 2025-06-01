#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script de démonstration simple pour interagir avec Tweety via JPype.

Objectif:
1. Initialiser la JVM avec JPype.
2. Charger les classes Tweety pour la logique propositionnelle.
3. Parser une formule propositionnelle simple.
4. Afficher la formule parsée.
"""

import jpype
import jpype.imports
from jpype.types import JString
import os
from pathlib import Path
import glob

def find_portable_jdk_jvm():
    """
    Trouve le chemin vers la JVM dans le JDK portable.
    Adaptez le nom du dossier JDK si nécessaire.
    """
    project_root = Path(__file__).resolve().parent.parent
    jdk_dir_name = "jdk-17.0.15+6" # Nom du dossier JDK, à adapter si la version change
    
    # Chemins possibles pour la JVM en fonction de l'OS
    # Pour Windows, la JVM est typiquement dans bin/server/jvm.dll
    # Pour Linux/macOS, elle est typiquement dans lib/server/libjvm.so ou lib/libjvm.dylib
    
    jvm_path_windows = project_root / "portable_jdk" / jdk_dir_name / "bin" / "server" / "jvm.dll"
    jvm_path_linux = project_root / "portable_jdk" / jdk_dir_name / "lib" / "server" / "libjvm.so"
    jvm_path_macos = project_root / "portable_jdk" / jdk_dir_name / "lib" / "libjvm.dylib" # ou jvm.dylib directement dans lib

    if os.name == 'nt' and jvm_path_windows.exists(): # Windows
        print(f"INFO: JVM trouvée pour Windows : {jvm_path_windows}")
        return str(jvm_path_windows)
    elif jvm_path_linux.exists(): # Linux
        print(f"INFO: JVM trouvée pour Linux : {jvm_path_linux}")
        return str(jvm_path_linux)
    elif jvm_path_macos.exists(): # macOS
        print(f"INFO: JVM trouvée pour macOS : {jvm_path_macos}")
        return str(jvm_path_macos)
    else:
        # Essayer un chemin plus générique pour macOS si le premier échoue
        jvm_path_macos_alt = project_root / "portable_jdk" / jdk_dir_name / "lib" / "jvm.dylib"
        if jvm_path_macos_alt.exists():
            print(f"INFO: JVM trouvée pour macOS (alternative) : {jvm_path_macos_alt}")
            return str(jvm_path_macos_alt)

        print(f"ERREUR: Impossible de trouver la JVM dans {project_root / 'portable_jdk' / jdk_dir_name}")
        print("Vérifiez le nom du dossier JDK et la structure des fichiers.")
        print(f"Tentatives de chemins :")
        print(f"  Windows: {jvm_path_windows} (existe: {jvm_path_windows.exists()})")
        print(f"  Linux:   {jvm_path_linux} (existe: {jvm_path_linux.exists()})")
        print(f"  macOS:   {jvm_path_macos} (existe: {jvm_path_macos.exists()})")
        print(f"  macOS (alt): {jvm_path_macos_alt} (existe: {jvm_path_macos_alt.exists()})")
        return None

def build_tweety_classpath():
    """
    Construit le classpath à partir des JARs Tweety dans le répertoire libs/.
    """
    project_root = Path(__file__).resolve().parent.parent
    libs_dir = project_root / "libs"
    
    if not libs_dir.exists() or not libs_dir.is_dir():
        print(f"ERREUR: Le répertoire des bibliothèques Tweety '{libs_dir}' n'a pas été trouvé.")
        return None

    # Utiliser glob pour obtenir tous les fichiers JAR dans le répertoire libs
    jar_pattern = str(libs_dir / "*.jar")
    jar_files = glob.glob(jar_pattern)

    if not jar_files:
        print(f"ERREUR: Aucun fichier JAR trouvé dans '{libs_dir}' avec le motif '{jar_pattern}'.")
        return None
        
    print(f"INFO: Liste de JARs pour le classpath Tweety construite avec {len(jar_files)} JARs.")
    # Débogage : afficher les JARs trouvés
    # for i, jar_file in enumerate(jar_files):
    #     print(f"  JAR {i+1}: {jar_file}")
    return jar_files # Retourne toujours une liste de tous les JARs

def main():
    """
    Fonction principale pour la démonstration.
    """
    print("--- Début de la démonstration simple d'interaction avec Tweety ---")

    print(f"INFO: Chemin JVM par défaut selon JPype: {jpype.getDefaultJVMPath()}")

    # 1. Initialiser la JVM
    print("\nÉtape 1: Initialisation de la JVM avec JPype...")
    jvm_path = find_portable_jdk_jvm()
    if not jvm_path:
        print("ERREUR: Impossible de continuer sans la JVM. Arrêt du script.")
        return

    tweety_classpath_list = build_tweety_classpath()
    if not tweety_classpath_list: # Maintenant, c'est toujours une liste ou None
        print("ERREUR: Impossible de continuer sans la liste des JARs pour le classpath Tweety. Arrêt du script.")
        return

    try:
        if not jpype.isJVMStarted():
            print(f"INFO: Démarrage de la JVM depuis : {jvm_path}")
            
            # Affichage du classpath utilisé (c'est maintenant toujours une liste)
            log_classpath_display = tweety_classpath_list[:3] if len(tweety_classpath_list) > 3 else tweety_classpath_list
            print(f"INFO: Utilisation de la liste de JARs pour le classpath (premiers éléments) : {log_classpath_display}{'...' if len(tweety_classpath_list) > 3 else ''}")
            
            jpype.startJVM(jvm_path, classpath=tweety_classpath_list, convertStrings=False) # Passer la liste directement
            print("INFO: JVM démarrée avec succès.")
        else:
            print("INFO: La JVM est déjà démarrée.")
    except Exception as e:
        print(f"ERREUR CRITIQUE: Échec du démarrage de la JVM : {e}")
        # import traceback
        # traceback.print_exc()
        return

    # 2. Importer les classes Tweety nécessaires
    print("\nÉtape 2: Importation des classes Tweety...")
    try:
        # Importer la classe PlParser pour la logique propositionnelle
        # Le package Java est net.tweetyproject.logics.pl.parser
        PlParser = jpype.JClass("net.tweetyproject.logics.pl.parser.PlParser")
        # Importer la classe de base pour les formules propositionnelles
        # net.tweetyproject.logics.pl.syntax.PropositionalFormula
        PropositionalFormula = jpype.JClass("net.tweetyproject.logics.pl.syntax.PropositionalFormula")
        
        print("INFO: Classes Tweety (PlParser, PropositionalFormula) chargées avec succès via JClass.")
    except Exception as e:
        print(f"ERREUR: Échec de l'importation des classes Tweety : {e}")
        print("Vérifiez que les JARs Tweety sont corrects et que le classpath est bien configuré.")
        # import traceback
        # traceback.print_exc()
        if jpype.isJVMStarted():
            # jpype.shutdownJVM() # Commenté pour éviter des erreurs si la JVM est utilisée ailleurs
            pass
        return

    # 3. Instancier PlParser
    print("\nÉtape 3: Instanciation de PlParser...")
    try:
        parser = PlParser()
        print(f"INFO: PlParser instancié avec succès : {parser}")
    except Exception as e:
        print(f"ERREUR: Échec de l'instanciation de PlParser : {e}")
        # import traceback
        # traceback.print_exc()
        if jpype.isJVMStarted():
            # jpype.shutdownJVM()
            pass
        return

    # 4. Parser une formule propositionnelle simple
    formula_string = "p && (q || !r)"
    print(f"\nÉtape 4: Parsing de la formule propositionnelle : \"{formula_string}\"...")
    try:
        # La méthode parseFormula attend un JString
        parsed_formula = parser.parseFormula(JString(formula_string))
        print(f"INFO: Formule parsée avec succès.")
    except Exception as e:
        print(f"ERREUR: Échec du parsing de la formule '{formula_string}' : {e}")
        # import traceback
        # traceback.print_exc()
        if jpype.isJVMStarted():
            # jpype.shutdownJVM()
            pass
        return

    # 5. Afficher la formule parsée
    print("\nÉtape 5: Affichage de la formule parsée...")
    try:
        formula_java_type = parsed_formula.getClass().getName()
        formula_to_string = parsed_formula.toString()
        
        print(f"  - Type Java de la formule : {formula_java_type}")
        print(f"  - Représentation en chaîne : {formula_to_string}")
        
        # Vérifier si la formule est une instance de PropositionalFormula (côté Java)
        # Note: isinstance() avec des types Java peut être délicat.
        # Il est plus sûr de vérifier le nom de la classe ou d'utiliser jpype.JInstanceOf
        if jpype.JInstanceOf(parsed_formula, PropositionalFormula):
             print("  - Vérification : La formule est bien une instance de PropositionalFormula (côté Java).")
        else:
             print("  - AVERTISSEMENT : La formule n'est PAS une instance de PropositionalFormula (côté Java), type actuel: " + str(type(parsed_formula)))


    except Exception as e:
        print(f"ERREUR: Échec de l'affichage des détails de la formule parsée : {e}")
        # import traceback
        # traceback.print_exc()

    # 6. (Optionnel) Opération basique sur la formule
    print("\nÉtape 6 (Optionnel): Opération basique sur la formule...")
    try:
        if jpype.JInstanceOf(parsed_formula, PropositionalFormula):
            # Obtenir les atomes (propositions) de la formule
            # La méthode est getAtoms() et retourne un Set<Proposition>
            atoms_set = parsed_formula.getAtoms() # Ceci est un java.util.Set
            
            print(f"  - Atomes (propositions) dans la formule (type Java: {atoms_set.getClass().getName()}):")
            if atoms_set.isEmpty():
                print("    Aucun atome trouvé.")
            else:
                # Itérer sur le Set Java
                py_atoms = []
                for atom in atoms_set: # JPype gère l'itération sur les collections Java
                    py_atoms.append(atom.toString()) # atom est un net.tweetyproject.logics.pl.syntax.Proposition
                print(f"    {py_atoms}")
        else:
            print("  - L'objet n'est pas une PropositionalFormula, impossible d'obtenir les atomes.")

    except Exception as e:
        print(f"ERREUR: Échec de l'opération optionnelle sur la formule : {e}")
        # import traceback
        # traceback.print_exc()

    # Arrêt de la JVM (optionnel, dépend si d'autres scripts l'utilisent)
    # print("\nArrêt de la JVM...")
    # if jpype.isJVMStarted():
    #     jpype.shutdownJVM()
    #     print("INFO: JVM arrêtée.")

    print("\n--- Fin de la démonstration simple d'interaction avec Tweety ---")

if __name__ == "__main__":
    main()