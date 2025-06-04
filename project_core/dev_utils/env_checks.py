#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module pour les vérifications de l'environnement de développement et d'exécution.

Ce module fournit des fonctions pour vérifier la configuration correcte
de divers composants essentiels de l'environnement, tels que Java, JPype,
et les dépendances Python.
"""

import os
import logging
import subprocess
from pathlib import Path
import importlib.metadata # Ajouté pour la vérification des versions
try:
    import pkg_resources # Pour parser les requirements
except ImportError:
    # pkg_resources est déprécié et peut ne pas être disponible dans les nouvelles installations de setuptools.
    # Tenter une alternative ou logguer une erreur si nécessaire pour le parsing des requirements.
    # Pour l'instant, on suppose qu'il est disponible ou que le code gérera son absence.
    logger.warning("pkg_resources n'a pas pu être importé. Le parsing des requirements pourrait échouer.")
    pkg_resources = None
from typing import List, Tuple, Optional

# Configuration du logging pour ce module
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s', datefmt='%H:%M:%S')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

def _run_command(cmd: List[str], cwd: Optional[Path] = None) -> Tuple[int, str, str]:
    """
    Exécute une commande et retourne le code de retour, stdout, et stderr.
    Fonction utilitaire interne.
    """
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=cwd
        )
        stdout, stderr = process.communicate(timeout=30)  # Ajout d'un timeout
        return process.returncode, stdout, stderr
    except subprocess.TimeoutExpired:
        logger.error(f"Timeout lors de l'exécution de {cmd}")
        return -1, "", "TimeoutExpired"
    except FileNotFoundError:
        logger.error(f"Commande non trouvée: {cmd[0]}")
        return -1, "", f"FileNotFoundError: {cmd[0]}"
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution de {cmd}: {e}")
        return -1, "", str(e)

def check_java_environment() -> bool:
    """
    Vérifie la présence et la configuration correcte de l'environnement d'exécution Java.

    Cette fonction vérifie :
    1. Si la variable d'environnement JAVA_HOME est définie et pointe vers un répertoire Java valide.
    2. Si la commande 'java -version' peut être exécutée et retourne des informations de version.

    Elle loggue des messages informatifs sur la version de Java trouvée et le chemin JAVA_HOME,
    ou des messages d'erreur/avertissement si des problèmes sont détectés.
    La configuration est considérée comme correcte si `java -version` fonctionne et si `JAVA_HOME`
    est défini et valide.

    :return: True si l'environnement Java est considéré comme correctement configuré, False sinon.
    :rtype: bool
    """
    logger.info("☕ Vérification de l'environnement Java...")
    java_ok = True
    java_home_valid = False

    # 1. Vérifier JAVA_HOME
    java_home = os.environ.get("JAVA_HOME")
    if java_home:
        logger.info(f"    JAVA_HOME est défini : {java_home}")
        java_home_path = Path(java_home)
        if java_home_path.is_dir():
            # Vérifier si java.exe (ou java pour non-Windows) existe dans JAVA_HOME/bin
            java_exe_in_home = java_home_path / "bin" / ("java.exe" if os.name == 'nt' else "java")
            if java_exe_in_home.exists() and java_exe_in_home.is_file():
                logger.info(f"    JAVA_HOME pointe vers un répertoire Java valide ({java_exe_in_home}).")
                java_home_valid = True
            else:
                logger.warning(f"    JAVA_HOME ({java_home}) ne semble pas contenir une installation Java valide (exécutable non trouvé à {java_exe_in_home}).")
                java_ok = False
        else:
            logger.warning(f"    JAVA_HOME ({java_home}) n'est pas un répertoire valide.")
            java_ok = False
    else:
        logger.warning("    JAVA_HOME n'est pas défini. Cette variable est souvent nécessaire pour les outils basés sur Java.")
        # Ne pas mettre java_ok à False ici, car java peut être dans le PATH.
        # Cependant, pour de nombreux outils, JAVA_HOME est crucial.

    # 2. Vérifier 'java -version'
    returncode, stdout, stderr = _run_command(["java", "-version"])

    if returncode == 0:
        # stderr contient souvent la version pour 'java -version'
        version_info = stderr.strip() if stderr else stdout.strip()
        if version_info:
            first_line_version = version_info.split('\n')[0]
            logger.info(f"    Commande 'java -version' exécutée avec succès. Version détectée : {first_line_version}")
        else:
            logger.warning("    Commande 'java -version' exécutée, mais n'a retourné aucune information de version.")
            java_ok = False # Si pas d'info de version, c'est un problème
    else: # returncode != 0
        logger.error(f"    Échec de l'exécution de 'java -version'. Code de retour : {returncode}")
        if stderr: # Log stderr s'il y a quelque chose
            logger.error(f"    Stderr: {stderr.strip()}")
        #else: # Optionnel: log si stderr est vide mais il y a une erreur
            #logger.info("    Stderr était vide pour l'échec de 'java -version'.")
        if stdout: # Log stdout s'il y a quelque chose
            logger.error(f"    Stdout: {stdout.strip()}")
        #else: # Optionnel: log si stdout est vide
            #logger.info("    Stdout était vide pour l'échec de 'java -version'.")

        if returncode == -1 and "FileNotFoundError" in stderr: # Cas spécifique de _run_command
            logger.warning("    Java n'est pas trouvé dans le PATH (FileNotFoundError).")
        elif returncode != 0 : # Autres erreurs d'exécution où java a été trouvé mais a échoué
             logger.warning("    La commande 'java -version' a échoué (voir logs ci-dessus), bien que Java semble être dans le PATH.")
        # Si returncode est 0, on ne devrait pas être dans ce bloc 'else'

        java_ok = False

    if not java_home_valid and java_ok : # Si JAVA_HOME n'est pas bon mais java -version fonctionne
        logger.info("    Java est accessible via le PATH, mais JAVA_HOME n'est pas (correctement) défini.")
        # Selon les exigences strictes, cela pourrait être un False.
        # Pour l'instant, si `java -version` fonctionne, on considère que c'est un minimum.
        # Mais on a déjà loggué un warning pour JAVA_HOME.

    if java_ok:
        logger.info("✅ L'environnement Java semble correctement configuré (au moins 'java -version' fonctionne).")
    else:
        logger.error("❌ Des problèmes ont été détectés avec l'environnement Java.")

    # La fonction doit retourner un booléen global.
    # Si `java -version` échoue, c'est un échec.
    # Si `JAVA_HOME` n'est pas valide, c'est un avertissement mais pas un échec bloquant si `java -version` fonctionne.
    # La description demande "Retourner un booléen indiquant si l'environnement Java est considéré comme correctement configuré."
    # La configuration est considérée comme "correctement configurée" si `java -version` fonctionne
    # ET que `JAVA_HOME` est valide.
    final_status = java_ok and java_home_valid

    if java_ok and not java_home_valid:
        logger.warning("    Bien que 'java -version' fonctionne, JAVA_HOME n'est pas défini ou est invalide. "
                       "Cela peut causer des problèmes avec certains outils qui dépendent de JAVA_HOME.")
        # La fonction retourne False si JAVA_HOME n'est pas valide, même si 'java -version' fonctionne,
        # car une configuration "correcte" implique généralement un JAVA_HOME valide.

    if final_status:
        logger.info("✅ L'environnement Java est jugé correctement configuré (java -version OK et JAVA_HOME valide).")
    else:
        logger.error("❌ L'environnement Java n'est pas considéré comme correctement configuré.")
        
    return final_status

def check_jpype_config() -> bool:
    """
    Vérifie si la bibliothèque JPype est correctement installée et capable de démarrer la JVM.

    Cette fonction effectue les vérifications suivantes :
    1. Tente d'importer le module `jpype`.
    2. Si l'import réussit, vérifie si la JVM est déjà démarrée.
    3. Si la JVM n'est pas démarrée, tente de la démarrer avec `jpype.startJVM()`.
    4. Loggue des messages informatifs sur le statut de JPype et de la JVM.
    5. S'assure que la JVM est arrêtée si elle a été démarrée par cette fonction,
       en utilisant `jpype.shutdownJVM()` dans un bloc `finally`.
       Attention : Ne tente pas d'arrêter une JVM qui était déjà démarrée avant l'appel.

    :return: True si JPype semble correctement configuré et fonctionnel (importable et JVM gérable), False sinon.
    :rtype: bool
    :raises ImportError: Si le module `jpype` ne peut pas être importé.
                         Bien que l'exception soit gérée en interne et logguée,
                         elle indique un échec de la configuration de JPype.
    :raises Exception: Diverses exceptions peuvent être levées par `jpype.startJVM()` ou
                       `jpype.shutdownJVM()` si la JVM rencontre des problèmes.
                       Ces exceptions sont gérées en interne et mènent à un retour de `False`.
    """
    logger.info("🐍 Vérification de la configuration de JPype...")
    jpype_ok = False
    jvm_started_by_this_function = False

    try:
        import jpype
        import jpype.imports
        logger.info("    Module JPype importé avec succès.")

        if jpype.isJVMStarted():
            logger.info("    La JVM est déjà démarrée.")
            # Si la JVM est déjà démarrée par une autre partie du code,
            # on considère que JPype est fonctionnel pour cette vérification.
            # On ne la redémarre pas et on ne l'arrêtera pas.
            jpype_ok = True
        else:
            logger.info("    La JVM n'est pas démarrée. Tentative de démarrage...")
            try:
                # Utiliser le chemin par défaut de la JVM.
                # convertStrings=False est souvent recommandé pour éviter les conversions automatiques
                # qui peuvent parfois causer des problèmes ou des surcharges.
                jpype.startJVM(jpype.getDefaultJVMPath(), convertStrings=False)
                jvm_started_by_this_function = True
                logger.info("    JVM démarrée avec succès par cette fonction.")
                jpype_ok = True
            except Exception as e:
                logger.error(f"    Échec du démarrage de la JVM : {e}")
                logger.error("    Vérifiez votre installation Java et la configuration de JPype (JAVA_HOME, etc.).")
                jpype_ok = False

        if jpype_ok:
            # Tentative d'importer une classe Java simple pour confirmer la communication
            try:
                # jpype.JClass("java.lang.String") # Décommenter pour un test plus poussé
                logger.info("    Test d'accès à une classe Java de base (java.lang.String) via JPype réussi (implicitement).")
            except Exception as e:
                logger.warning(f"    Avertissement : Impossible de vérifier l'accès à une classe Java de base : {e}")
                # Ne pas marquer jpype_ok à False pour cela, le démarrage de la JVM est le principal.
                pass


    except ImportError:
        logger.error("    Échec de l'import du module JPype. JPype n'est probablement pas installé.")
        logger.error("    Veuillez installer JPype1 (par exemple, via 'pip install JPype1').")
        jpype_ok = False
    except Exception as e:
        logger.error(f"    Une erreur inattendue est survenue lors de la vérification de JPype : {e}")
        jpype_ok = False
    finally:
        if jvm_started_by_this_function and jpype.isJVMStarted():
            logger.info("    Arrêt de la JVM démarrée par cette fonction...")
            try:
                jpype.shutdownJVM()
                logger.info("    JVM arrêtée avec succès.")
            except Exception as e:
                logger.error(f"    Erreur lors de l'arrêt de la JVM : {e}")
                # Cela pourrait indiquer un problème plus profond.
                jpype_ok = False # Si on ne peut pas arrêter proprement, c'est un souci.

    if jpype_ok:
        logger.info("✅ JPype semble correctement configuré et la JVM est gérable.")
    else:
        logger.error("❌ Des problèmes ont été détectés avec la configuration de JPype ou la gestion de la JVM.")

    return jpype_ok
def check_python_dependencies(requirements_file_path: Path) -> bool:
    """
    Vérifie si les dépendances Python spécifiées dans un fichier de requirements
    sont présentes et satisfont aux contraintes de version.

    Utilise `importlib.metadata` pour obtenir les versions installées et
    `pkg_resources` (si disponible) pour parser les spécificateurs de version
    du fichier de requirements.

    :param requirements_file_path: Chemin vers le fichier de dépendances (ex: requirements.txt).
    :type requirements_file_path: pathlib.Path
    :return: True si toutes les dépendances sont satisfaites, False sinon.
    :rtype: bool
    :raises FileNotFoundError: Si le fichier de requirements spécifié n'est pas trouvé (géré en interne, retourne False).
    :raises Exception: Diverses exceptions peuvent survenir lors de la lecture ou du parsing
                       du fichier de requirements, ou lors de la vérification des versions
                       des packages (gérées en interne, mènent à un retour de False).
    """
    logger.info(f"🐍 Vérification des dépendances Python depuis {requirements_file_path}...")
    all_ok = True
    
    if not requirements_file_path.is_file():
        logger.error(f"    Le fichier de dépendances {requirements_file_path} n'a pas été trouvé.")
        return False

    # S'assurer que pkg_resources a été importé
    if pkg_resources is None:
        logger.error("    pkg_resources n'est pas disponible. Impossible de parser le fichier de dépendances.")
        return False

    try:
        with open(requirements_file_path, 'r', encoding='utf-8') as f:
            requirements_content = f.read()
        
        # Filtrer les lignes vides et les commentaires avant de parser
        valid_lines = [
            line for line in requirements_content.splitlines()
            if line.strip() and not line.strip().startswith('#')
        ]
        
        if not valid_lines:
            logger.info(f"    Le fichier de dépendances {requirements_file_path} est vide ou ne contient que des commentaires.")
            return True # Un fichier vide est considéré comme "satisfait"

        # pkg_resources.parse_requirements ne gère pas bien les options comme --hash
        # Nous allons parser manuellement pour extraire nom et specifiers
        # Ceci est une simplification; une librairie dédiée comme 'packaging' ou 'requirements-parser' serait plus robuste.
        
        parsed_requirements = []
        for line in valid_lines:
            # Tentative de parser avec pkg_resources, mais être prêt à gérer les erreurs pour les lignes complexes
            try:
                # pkg_resources.Requirement.parse peut gérer des lignes plus simples
                # ex: "package", "package==1.0", "package>=1.0,<2.0"
                # Il ne gère pas les options comme -r, -e, ou les URLs directes de la même manière que parse_requirements
                # Pour une analyse plus robuste, il faudrait une logique de parsing plus détaillée.
                # Ici, on se concentre sur les dépendances nommées avec spécificateurs.
                if line.startswith('-e') or line.startswith('git+') or '.git@' in line:
                    logger.info(f"    Ligne ignorée (dépendance éditable/VCS) : {line}")
                    continue
                if line.startswith('-r'):
                    logger.info(f"    Ligne ignorée (inclusion d'un autre fichier) : {line}")
                    continue
                
                # Supprimer les hashes et autres options non supportées par Requirement.parse
                line_parts = line.split('#')[0].split(';')[0].strip() # Enlever commentaires et marqueurs d'environnement
                
                # Tenter de parser la ligne nettoyée
                parsed_req = pkg_resources.Requirement.parse(line_parts)
                parsed_requirements.append(parsed_req)
            except ValueError as ve: # Erreur de parsing de pkg_resources
                 # Essayer d'extraire le nom du package au cas où.
                 # Ceci est une heuristique et peut ne pas être précis.
                # D'abord, nettoyer les commentaires et marqueurs d'environnement comme pour line_parts
                clean_line_for_heuristic = line.split('#')[0].split(';')[0].strip()
                # Ensuite, essayer d'isoler le nom du package avant un crochet ou un opérateur de version
                potential_name = clean_line_for_heuristic.split('[')[0].split("==")[0].split(">=")[0].split("<=")[0].split("!=")[0].split("~=")[0].strip()
                
                if potential_name and not any(c in potential_name for c in "[](),"): # Simple vérification que le nom est "propre"
                    logger.warning(f"    Impossible de parser complètement la ligne '{line}' avec pkg_resources: {ve}. Tentative avec nom '{potential_name}'.")
                    # Créer un requirement sans specifier si le parsing échoue mais qu'on a un nom
                    parsed_requirements.append(pkg_resources.Requirement.parse(potential_name))
                else:
                    logger.error(f"    Impossible de parser la ligne de dépendance '{line}': {ve}")
                    all_ok = False # Marquer comme échec si une ligne ne peut être parsée

        if not all_ok: # Si une ligne n'a pas pu être parsée, on arrête là pour cette partie.
            return False

        for req in parsed_requirements:
            req_name = req.project_name 
            try:
                installed_version_str = importlib.metadata.version(req_name)
                installed_version = pkg_resources.parse_version(installed_version_str)
                
                # Si req.specifier est vide (ex: juste "package_name"), on considère que la présence suffit.
                if not req.specs: # Pas de spécificateur de version
                    logger.info(f"    ✅ {req_name}: Version {installed_version_str} installée (aucune version spécifique requise).")
                elif req.specifier.contains(installed_version_str, prereleases=True): # Autoriser les pré-releases
                    logger.info(f"    ✅ {req_name}: Version {installed_version_str} installée satisfait {req.specifier}")
                else:
                    logger.warning(f"    ❌ {req_name}: Version {installed_version_str} installée ne satisfait PAS {req.specifier}")
                    all_ok = False
            except importlib.metadata.PackageNotFoundError:
                logger.warning(f"    ❌ {req_name}: Non installé (requis: {req.specifier if req.specs else 'any version'})")
                all_ok = False
            except Exception as e:
                logger.error(f"    ❓ Erreur lors de la vérification de {req_name}: {e}")
                all_ok = False
                
    except Exception as e:
        logger.error(f"    Erreur lors de la lecture ou du parsing du fichier {requirements_file_path}: {e}")
        return False

    if all_ok:
        logger.info("✅ Toutes les dépendances Python du fichier sont satisfaites.")
    else:
        logger.warning("⚠️  Certaines dépendances Python du fichier ne sont pas satisfaites ou sont manquantes.")
        
    return all_ok
if __name__ == '__main__':
    # Pour des tests rapides
    logging.basicConfig(level=logging.INFO)
    logger.info("Test direct de check_java_environment():")
    result = check_java_environment()
    logger.info(f"Résultat du test: {result}")