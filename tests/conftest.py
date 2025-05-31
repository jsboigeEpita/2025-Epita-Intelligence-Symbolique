print("INFO: conftest.py: Fichier en cours de lecture par pytest (version minimale pour débogage JVM).")

import sys
import os
import atexit
import importlib
import logging
# Note: Autres imports comme pytest, unittest.mock sont omis car les mocks/fixtures sont désactivés.

# Ajout du répertoire des mocks au sys.path
mocks_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mocks')
if mocks_dir not in sys.path:
    sys.path.insert(0, mocks_dir)
    print(f"INFO: tests/conftest.py: Ajout de {mocks_dir} à sys.path.")

# Configuration du logger
logger = logging.getLogger(__name__)
# Pour activer les logs pendant l'exécution des tests, décommenter les lignes suivantes :
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)
print("INFO: conftest.py: Logger configuré pour pytest hooks jpype.") # Log de confirmation

# Ajout précoce du chemin pour trouver argumentation_analysis
# Cela doit se faire avant d'importer initialize_jvm si jvm_setup est dans ce package
current_script_dir_for_path = os.path.dirname(os.path.abspath(__file__))
project_root_for_path = os.path.dirname(current_script_dir_for_path) # tests -> project root
if project_root_for_path not in sys.path:
    sys.path.insert(0, project_root_for_path)
    print(f"INFO: conftest.py: Ajout de {project_root_for_path} à sys.path.")

# La logique d'initialisation de la JVM est maintenant gérée
# uniquement par le conftest.py à la racine du projet pour éviter les conflits.
print("INFO: tests/conftest.py: Logique d'initialisation JVM désactivée dans ce fichier.")
# S'assurer que la variable d'environnement est lue si elle a été définie par le conftest parent,
# ou qu'elle a une valeur par défaut si ce conftest est exécuté isolément (moins probable).
# Cependant, pour éviter de masquer des problèmes, il est préférable de ne pas la redéfinir ici.
# Si le conftest racine ne s'exécute pas avant, JPYPE_REAL_JVM_INITIALIZED pourrait ne pas être défini.
# Pour l'instant, on suppose que le conftest racine s'exécute toujours en premier.

# Le reste du fichier original est neutralisé pour ce test.
print("INFO: conftest.py: Reste du contenu original (mocks, fixtures) neutralisé pour le débogage JVM.")

# Conserver l'ajout du parent_dir au sys.path qui était à la fin du fichier original,
# au cas où il serait nécessaire pour pytest lui-même ou d'autres découvertes de tests.
# Bien que nous l'ayons déjà fait pour argumentation_analysis, cela ne fait pas de mal de le répéter
# si la structure originale du fichier l'avait à un endroit spécifique pour une raison.
# Cependant, pour la version minimale, celui du début devrait suffire.
# parent_dir_original_placement = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# if parent_dir_original_placement not in sys.path:
#    sys.path.insert(0, parent_dir_original_placement)

def pytest_sessionstart(session):
    """
    Au début de la session de test, essaie de sauvegarder la fonction
    de nettoyage originale de jpype si le vrai module est chargé.
    """
    print("DEBUG CONTEST.PY: pytest_sessionstart HOOK IS FIRING")
    logger.info("pytest_sessionstart: Début de la routine de sauvegarde de jpype._core._JTerminate.")
    session._original_jpype_jterminate = None
    try:
        jpype_real = None
        # Vérifier d'abord si 'jpype' est dans sys.modules
        if 'jpype' in sys.modules:
            existing_jpype = sys.modules['jpype']
            module_path = getattr(existing_jpype, '__file__', None)
            # Si c'est déjà le mock, ne rien faire.
            if module_path and 'mocks' in module_path and 'jpype_mock.py' in module_path:
                logger.info(f"pytest_sessionstart: jpype ({module_path}) est déjà mocké au démarrage. Aucune action de sauvegarde.")
                return
            # Sinon, on suppose que c'est le vrai ou un état non mocké pertinent
            jpype_real = existing_jpype
            logger.info(f"pytest_sessionstart: jpype trouvé dans sys.modules. Chemin: {module_path if module_path else 'N/A'}")

        if jpype_real is None:
            # Si non trouvé ou si on veut forcer un import frais (attention aux effets de bord)
            # Pour ce cas, on se contente d'importer s'il n'est pas déjà là ou s'il n'est pas le mock.
            try:
                logger.info("pytest_sessionstart: Tentative d'import de 'jpype' via importlib.")
                jpype_real = importlib.import_module('jpype')
                logger.info(f"pytest_sessionstart: jpype importé via importlib. Chemin: {getattr(jpype_real, '__file__', 'N/A')}")
            except ModuleNotFoundError:
                logger.warning("pytest_sessionstart: Le module jpype réel n'a pas pu être importé (ModuleNotFoundError). Il n'est peut-être pas installé.")
                return
            except Exception as e:
                logger.error(f"pytest_sessionstart: Exception lors de l'import de jpype via importlib: {e}")
                return
        
        # Vérification finale que ce n'est pas le mock (si importlib l'a ramené)
        module_path_after_import = getattr(jpype_real, '__file__', None)
        if module_path_after_import and 'mocks' in module_path_after_import and 'jpype_mock.py' in module_path_after_import:
            logger.info(f"pytest_sessionstart: jpype ({module_path_after_import}) est le mock après import. Aucune action de sauvegarde.")
            return

        if hasattr(jpype_real, '_core') and hasattr(jpype_real._core, '_JTerminate'):
            session._original_jpype_jterminate = jpype_real._core._JTerminate
            logger.info(f"pytest_sessionstart: jpype._core._JTerminate original sauvegardé: {session._original_jpype_jterminate}")
        else:
            logger.warning(f"pytest_sessionstart: jpype._core._JTerminate non trouvé dans le module jpype ({module_path_after_import if module_path_after_import else 'N/A'}). Le module est-il complet/correctement initialisé?")

    except AttributeError as e:
        logger.error(f"pytest_sessionstart: AttributeError lors de l'accès à jpype._core._JTerminate: {e}")
    except Exception as e:
        logger.error(f"pytest_sessionstart: Erreur générale inattendue dans pytest_sessionstart: {e}")
    finally:
        logger.info("pytest_sessionstart: Fin de la routine.")


def pytest_sessionfinish(session, exitstatus):
    """
    À la fin de la session de test, si jpype a été mocké et que nous avions
    sauvegardé une fonction de nettoyage originale, la désenregistre d'atexit.
    """
    print("DEBUG CONTEST.PY: pytest_sessionfinish HOOK IS FIRING")
    logger.info("pytest_sessionfinish: Début de la routine de désinscription de jpype._core._JTerminate.")
    original_jterminate = getattr(session, '_original_jpype_jterminate', None)

    if not original_jterminate:
        logger.info("pytest_sessionfinish: Aucune fonction _JTerminate originale n'a été sauvegardée. Aucune action.")
        logger.info("pytest_sessionfinish: Fin de la routine.")
        return

    logger.info(f"pytest_sessionfinish: Fonction _JTerminate originale trouvée: {original_jterminate}")
    current_jpype_module = sys.modules.get('jpype')

    if not current_jpype_module:
        logger.info("pytest_sessionfinish: Le module 'jpype' n'est pas dans sys.modules à la fin de la session. Aucune action de désinscription.")
        logger.info("pytest_sessionfinish: Fin de la routine.")
        return
        
    logger.info(f"pytest_sessionfinish: Module jpype actuel trouvé dans sys.modules.")
    is_mock = False
    try:
        module_path = getattr(current_jpype_module, '__file__', None)
        if module_path and 'mocks' in module_path and 'jpype_mock.py' in module_path:
            is_mock = True
            logger.info(f"pytest_sessionfinish: Le module jpype actuel ({module_path}) est identifié comme le mock.")
        else:
            logger.info(f"pytest_sessionfinish: Le module jpype actuel ({module_path if module_path else 'N/A, pas d attribut __file__'}) n'est PAS le mock.")
    except Exception as e:
        # Ne pas planter si la vérification échoue, mais logguer l'erreur.
        logger.error(f"pytest_sessionfinish: Erreur lors de la vérification du fichier du module jpype: {e}. On suppose que ce n'est pas le mock.")

    if is_mock:
        try:
            atexit.unregister(original_jterminate)
            logger.info(f"pytest_sessionfinish: Désinscription de {original_jterminate} de atexit réussie.")
        except ValueError:
            logger.warning(f"pytest_sessionfinish: {original_jterminate} n'était pas enregistrée avec atexit (ou déjà désinscrite). Désinscription ignorée.")
        except Exception as e:
            logger.error(f"pytest_sessionfinish: Exception lors de la tentative de désinscription de {original_jterminate}: {e}")
    else:
        logger.info("pytest_sessionfinish: jpype n'est pas le mock à la fin de la session, aucune désinscription de la fonction originale n'est tentée.")
    
    logger.info("pytest_sessionfinish: Fin de la routine.")
