import subprocess
import re
import logging

# Il est important que jpype soit importé là où ces fonctions sont utilisées,
# ou que jpype_instance soit toujours passé et contienne JBoolean, JClass, JInt.
# Pour l'instant, on suppose que jpype_instance fournit tout le nécessaire.

logger = logging.getLogger(__name__)

# --- Fonctions Helper pour contourner les appels ClingoSolver défectueux ---

def check_clingo_installed_python_way(clingo_exe_path, jpype_instance):
    # import subprocess # Déjà importé en haut du module
    logger.info(f"Custom Check: Tentative d'exécution de: {clingo_exe_path} --version")
    try:
        process_result = subprocess.run([clingo_exe_path, "--version"], capture_output=True, text=True, check=False, shell=False, encoding='utf-8')
        if process_result.returncode == 0 and ("clingo version" in process_result.stdout.lower() or "clingo version" in process_result.stderr.lower()):
            logger.info("Custom Check: 'clingo version' TROUVÉ via subprocess.")
            return jpype_instance.JBoolean(True)
        else:
            logger.warning(f"Custom Check: 'clingo version' NON TROUVÉ ou code de retour non nul. stdout: {process_result.stdout}, stderr: {process_result.stderr}")
            return jpype_instance.JBoolean(False)
    except Exception as e_subproc:
        logger.error(f"Custom Check: Erreur lors de l'exécution de la commande version via subprocess: {e_subproc}")
        return jpype_instance.JBoolean(False)

def get_clingo_models_python_way(clingo_exe_path, asp_file_path_str, jpype_instance, context_class_loader, max_models=0):
    # import subprocess # Déjà importé
    # import re # Déjà importé

    logger.info(f"Custom GetModels: Début de la fonction. ClassLoader reçu: {context_class_loader}")
    logger.info(f"Custom GetModels: Type du ClassLoader reçu: {type(context_class_loader)}")
    if hasattr(context_class_loader, 'toString'):
        logger.info(f"Custom GetModels: ClassLoader.toString(): {context_class_loader.toString()}")

    try:
        logger.info("Custom GetModels: Tentative de chargement de org.tweetyproject.lp.asp.syntax.ASPAtom avec le loader fourni...")
        ASPAtom_test_load = jpype_instance.JClass("org.tweetyproject.lp.asp.syntax.ASPAtom", loader=context_class_loader)
        logger.info(f"Custom GetModels: ASPAtom chargé avec succès dans la fonction helper: {ASPAtom_test_load}")
        if hasattr(ASPAtom_test_load, 'class_') and hasattr(ASPAtom_test_load.class_, 'getClassLoader'):
             logger.info(f"Custom GetModels: ClassLoader de ASPAtom_test_load: {ASPAtom_test_load.class_.getClassLoader()}")
    except Exception as e_atom_load:
        logger.error(f"Custom GetModels: ERREUR lors du chargement de ASPAtom dans la fonction helper: {e_atom_load}")
        raise # Propage l'erreur pour arrêter le test ici si ASPAtom ne peut pas être chargé

    # Classes Java nécessaires, chargées avec le classloader fourni
    ASPAtom = ASPAtom_test_load # Utiliser la classe déjà testée
    
    # Tentative d'utiliser le classloader de ASPAtom pour charger AnswerSet
    asp_atom_actual_loader = ASPAtom.class_.getClassLoader()
    logger.info(f"Custom GetModels: Utilisation du loader de ASPAtom ({asp_atom_actual_loader}) pour AnswerSet, qui est le même que context_class_loader ({context_class_loader}).")
    
    logger.info("Custom GetModels: Tentative de chargement de org.tweetyproject.lp.asp.semantics.AnswerSet avec le loader de ASPAtom...")
    AnswerSet = jpype_instance.JClass("org.tweetyproject.lp.asp.semantics.AnswerSet", loader=asp_atom_actual_loader)
    logger.info(f"Custom GetModels: AnswerSet chargé avec succès: {AnswerSet}")
    ArrayList = jpype_instance.JClass("java.util.ArrayList") # Classe standard

    cmd = [clingo_exe_path, asp_file_path_str, str(max_models)]
    logger.info(f"Custom GetModels: Exécution de: {' '.join(cmd)}")
    
    try:
        process_result = subprocess.run(cmd, capture_output=True, text=True, check=False, shell=False, encoding='utf-8')
        
        if process_result.returncode not in [10, 20, 30]:
            logger.error(f"Custom GetModels: Clingo a échoué ou a eu un comportement inattendu. Code: {process_result.returncode}, stdout: {process_result.stdout}, stderr: {process_result.stderr}")
            return ArrayList()

        stdout = process_result.stdout
        logger.debug(f"Custom GetModels: Clingo stdout:\n{stdout}")

        java_answer_sets = ArrayList()
        
        if "UNSATISFIABLE" in stdout:
            logger.info("Custom GetModels: Clingo reported UNSATISFIABLE.")
            return java_answer_sets # Collection vide

        current_atoms_for_set = None 
        
        for line in stdout.splitlines():
            line = line.strip()
            if line.startswith("Answer:"):
                if current_atoms_for_set is not None: 
                    java_atoms_list = ArrayList()
                    for atom_s in current_atoms_for_set:
                        java_atoms_list.add(ASPAtom(atom_s))
                    java_answer_sets.add(AnswerSet(java_atoms_list, jpype_instance.JInt(0), jpype_instance.JInt(0)))
                
                current_atoms_for_set = [] 
                continue

            if current_atoms_for_set is not None and line and not (line.startswith("SATISFIABLE") or line.startswith("OPTIMUM FOUND") or line.startswith("Models") or line.startswith("Calls")):
                current_atoms_for_set.extend(line.split())
                continue
            
            if line.startswith("SATISFIABLE") or line.startswith("OPTIMUM FOUND"):
                if current_atoms_for_set is not None and current_atoms_for_set: 
                    java_atoms_list = ArrayList()
                    for atom_s in current_atoms_for_set:
                        java_atoms_list.add(ASPAtom(atom_s))
                    java_answer_sets.add(AnswerSet(java_atoms_list, jpype_instance.JInt(0), jpype_instance.JInt(0)))
                current_atoms_for_set = None 
                break
        
        if current_atoms_for_set is not None and current_atoms_for_set:
            java_atoms_list = ArrayList()
            for atom_s in current_atoms_for_set:
                java_atoms_list.add(ASPAtom(atom_s))
            java_answer_sets.add(AnswerSet(java_atoms_list, jpype_instance.JInt(0), jpype_instance.JInt(0)))

        logger.info(f"Custom GetModels: Nombre d'AnswerSets Java créés: {java_answer_sets.size()}")
        return java_answer_sets

    except Exception as e:
        logger.error(f"Custom GetModels: Erreur générale lors de l'appel à Clingo ou du parsing: {e}")
        logger.exception("Trace de l'exception dans get_clingo_models_python_way:")
        return ArrayList()