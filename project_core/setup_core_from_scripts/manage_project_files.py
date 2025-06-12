import os
import shutil
import re
import logging
import sys # Ajout pour le logger par défaut

# Logger par défaut pour ce module
module_logger_files = logging.getLogger(__name__)
if not module_logger_files.hasHandlers():
    _console_handler_files = logging.StreamHandler(sys.stdout)
    _console_handler_files.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s (module default files)'))
    module_logger_files.addHandler(_console_handler_files)
    module_logger_files.setLevel(logging.INFO)

def _get_logger_files(logger_instance=None):
    """Retourne le logger fourni ou le logger par défaut du module."""
    return logger_instance if logger_instance else module_logger_files

DEFAULT_DIRECTORIES_TO_CLEAN = ["venv", ".venv", ".tools"]
DEFAULT_FILES_TO_CLEAN = [] # Ajouter des fichiers si nécessaire, ex: anciens logs, etc.

def cleanup_old_installations(project_root, logger_instance=None, interactive=False):
    """
    Nettoie les anciens répertoires et fichiers d'installation.
    """
    logger = _get_logger_files(logger_instance)
    logger.info("Début du nettoyage des anciennes installations...")
    items_to_remove = []

    for dir_name in DEFAULT_DIRECTORIES_TO_CLEAN:
        path = os.path.join(project_root, dir_name)
        if os.path.isdir(path):
            items_to_remove.append({"path": path, "type": "dir"})

    for file_name in DEFAULT_FILES_TO_CLEAN:
        path = os.path.join(project_root, file_name)
        if os.path.isfile(path):
            items_to_remove.append({"path": path, "type": "file"})

    # TODO: Identifier d'anciennes versions de JDK/Octave si possible
    # Exemple: si on stocke les JDK dans project_root/portable_jdk/jdk-17 et qu'on installe jdk-21
    # il faudrait lister les sous-répertoires de portable_jdk et supprimer ceux qui ne correspondent pas
    # à la version actuelle (si cette info est disponible ici). Pour l'instant, on se base sur .tools

    if not items_to_remove:
        logger.info("Aucun élément à nettoyer trouvé.")
        return

    logger.info("Éléments identifiés pour le nettoyage :")
    for item in items_to_remove:
        logger.info(f"  - {item['path']} ({item['type']})")

    if interactive:
        try:
            confirm = input("Confirmez-vous la suppression de ces éléments ? (oui/[non]) : ")
            if confirm.lower() != 'oui':
                logger.info("Nettoyage annulé par l'utilisateur.")
                return
        except EOFError:
            logger.warning("input() called in non-interactive context during cleanup. Assuming 'non' for safety.")
            return


    for item in items_to_remove:
        try:
            if item["type"] == "dir":
                shutil.rmtree(item["path"])
                logger.info(f"Répertoire supprimé : {item['path']}")
            elif item["type"] == "file":
                os.remove(item["path"])
                logger.info(f"Fichier supprimé : {item['path']}")
        except OSError as e:
            logger.error(f"Erreur lors de la suppression de {item['path']}: {e}", exc_info=True)
    logger.info("Nettoyage des anciennes installations terminé.")

def setup_env_file(project_root, logger_instance=None, tool_paths=None):
    """
    Crée ou met à jour le fichier .env du projet.
    """
    logger = _get_logger_files(logger_instance)
    logger.info("Configuration du fichier .env...")
    env_file_path = os.path.join(project_root, ".env")
    template_env_path = os.path.join(project_root, ".env.template")
    tool_paths = tool_paths or {}

    if not os.path.exists(template_env_path):
        logger.warning(f"Fichier template .env.template non trouvé à {template_env_path}. Le fichier .env ne sera pas géré.")
        return

    if not os.path.exists(env_file_path):
        try:
            shutil.copy(template_env_path, env_file_path)
            logger.info(f"Fichier .env créé à partir de .env.template: {env_file_path}")
        except OSError as e:
            logger.error(f"Impossible de copier .env.template vers .env: {e}", exc_info=True)
            return

    env_vars = {}
    try:
        with open(env_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    except IOError as e:
        logger.error(f"Impossible de lire le fichier .env: {e}", exc_info=True)
        return

    # Variables à gérer par le script
    pythonpath_parts = set()
    if "PYTHONPATH" in env_vars:
        pass

    pythonpath_parts.add(project_root)
    src_path = os.path.join(project_root, "src")
    if os.path.isdir(src_path):
         pythonpath_parts.add(src_path)

    env_vars["PYTHONPATH"] = os.pathsep.join(sorted(list(pythonpath_parts)))
    logger.debug(f"PYTHONPATH défini à : {env_vars['PYTHONPATH']}")

    if "JAVA_HOME" in tool_paths and tool_paths["JAVA_HOME"]:
        env_vars["JAVA_HOME"] = tool_paths["JAVA_HOME"]
        logger.debug(f"JAVA_HOME défini à : {env_vars['JAVA_HOME']}")
    elif "JAVA_HOME" not in env_vars:
        logger.debug("JAVA_HOME non fourni par tool_paths et non présent dans .env.")

    if "OCTAVE_HOME" in tool_paths and tool_paths["OCTAVE_HOME"]:
        env_vars["OCTAVE_HOME"] = tool_paths["OCTAVE_HOME"]
        if "OCTAVE_EXECUTABLE" in env_vars:
            del env_vars["OCTAVE_EXECUTABLE"]
        logger.debug(f"OCTAVE_HOME défini à : {env_vars['OCTAVE_HOME']}")
    elif "OCTAVE_EXECUTABLE" in tool_paths and tool_paths["OCTAVE_EXECUTABLE"]:
        env_vars["OCTAVE_EXECUTABLE"] = tool_paths["OCTAVE_EXECUTABLE"]
        logger.debug(f"OCTAVE_EXECUTABLE défini à : {env_vars['OCTAVE_EXECUTABLE']}")
    elif "OCTAVE_HOME" not in env_vars and "OCTAVE_EXECUTABLE" not in env_vars:
        logger.debug("Ni OCTAVE_HOME ni OCTAVE_EXECUTABLE fournis par tool_paths ou présents dans .env.")

    if "TEXT_CONFIG_PASSPHRASE" not in env_vars and not os.getenv("TEXT_CONFIG_PASSPHRASE"):
        env_vars["TEXT_CONFIG_PASSPHRASE"] = "YOUR_SECRET_PASSPHRASE_HERE_PLEASE_CHANGE_ME"
        logger.warning("TEXT_CONFIG_PASSPHRASE non trouvé. Un placeholder a été ajouté dans .env. Veuillez le remplacer.")
    elif "TEXT_CONFIG_PASSPHRASE" in env_vars:
        logger.debug("TEXT_CONFIG_PASSPHRASE trouvé dans .env.")
    elif os.getenv("TEXT_CONFIG_PASSPHRASE"):
        logger.debug("TEXT_CONFIG_PASSPHRASE trouvé dans les variables d'environnement système.")


    if "TIKA_SERVER_ENDPOINT" not in env_vars:
        env_vars["TIKA_SERVER_ENDPOINT"] = "http://localhost:9998"
        logger.debug(f"TIKA_SERVER_ENDPOINT défini par défaut à : {env_vars['TIKA_SERVER_ENDPOINT']}")
    else:
        logger.debug(f"TIKA_SERVER_ENDPOINT trouvé dans .env : {env_vars['TIKA_SERVER_ENDPOINT']}")


    output_lines = []
    written_keys = set()

    source_for_structure = template_env_path if os.path.exists(template_env_path) else env_file_path

    try:
        with open(source_for_structure, 'r', encoding='utf-8') as f_template:
            for line in f_template:
                stripped_line = line.strip()
                if not stripped_line or stripped_line.startswith('#'):
                    output_lines.append(line.rstrip('\r\n'))
                    continue
                
                if '=' in stripped_line:
                    key, _ = stripped_line.split('=', 1)
                    key = key.strip()
                    if key in env_vars:
                        output_lines.append(f"{key}={env_vars[key]}")
                        written_keys.add(key)
                    else:
                        output_lines.append(stripped_line)
                else:
                    output_lines.append(stripped_line)


        for key, value in env_vars.items():
            if key not in written_keys:
                output_lines.append(f"{key}={value}")
                written_keys.add(key)

        with open(env_file_path, 'w', encoding='utf-8') as f:
            for line_to_write in output_lines:
                f.write(line_to_write + '\n')
        logger.info(f"Fichier .env mis à jour : {env_file_path}")

    except IOError as e:
        logger.error(f"Erreur lors de l'écriture du fichier .env: {e}", exc_info=True)


def setup_project_structure(project_root, logger_instance=None, tool_paths=None, interactive=False, perform_cleanup=True):
    """
    Fonction principale pour gérer la structure du projet, y compris le nettoyage et le fichier .env.
    """
    logger = _get_logger_files(logger_instance)
    logger.info("Début de la configuration de la structure du projet...")
    if perform_cleanup:
        cleanup_old_installations(project_root, logger_instance=logger, interactive=interactive)
    else:
        logger.info("Nettoyage des anciennes installations ignoré.")

    setup_env_file(project_root, logger_instance=logger, tool_paths=tool_paths)
    logger.info("Configuration de la structure du projet terminée.")

if __name__ == '__main__':
    # Configuration du logger pour les tests locaux directs
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s (main test files)',
                        handlers=[logging.StreamHandler(sys.stdout)])
    logger_main_files = logging.getLogger(__name__)

    logger_main_files.info("Ce script est destiné à être importé et utilisé par main_setup.py.")
    
    # mock_project_root = os.path.join(os.path.dirname(__file__), "..", "..", "tests", "fake_project_root")
    # os.makedirs(mock_project_root, exist_ok=True)
    # with open(os.path.join(mock_project_root, ".env.template"), "w") as f_template:
    #     f_template.write("EXISTING_VAR=original_value\n")
    #     f_template.write("# Commentaire\n")
    #     f_template.write("TIKA_SERVER_ENDPOINT=http://localhost:9999\n")

    # logger_main_files.info(f"Utilisation d'un faux project_root : {mock_project_root}")
    # mock_tool_paths = {
    #     "JAVA_HOME": "/path/to/fake_jdk",
    #     "OCTAVE_HOME": "/path/to/fake_octave"
    # }
    # setup_project_structure(mock_project_root, logger_instance=logger_main_files, tool_paths=mock_tool_paths, interactive=False, perform_cleanup=True)
    # logger_main_files.info(f"Vérifiez le contenu de {os.path.join(mock_project_root, '.env')}")