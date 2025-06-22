import os
from pathlib import Path
from typing import List, Optional
import logging
import sys

# --- Ajout dynamique du chemin pour l'import ---
try:
    from argumentation_analysis.utils.system_utils import get_project_root
    from argumentation_analysis.core.setup.manage_portable_tools import setup_tools
except ImportError:
    project_root = Path(__file__).resolve().parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    from argumentation_analysis.utils.system_utils import get_project_root
    from argumentation_analysis.core.setup.manage_portable_tools import setup_tools

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def ensure_tools_are_installed(
    tools_to_ensure: List[str],
    force_reinstall: bool = False,
    logger_instance: Optional[logging.Logger] = None
) -> bool:
    """
    S'assure que les outils spécifiés sont installés en utilisant le gestionnaire
    d'outils portables restauré.
    """
    local_logger = logger_instance or logger
    project_root_path = Path(get_project_root())
    libs_dir = project_root_path / "libs"
    
    local_logger.info(f"--- Début de la vérification/installation des outils portables ---")
    local_logger.info(f"Les outils seront installés dans le répertoire : {libs_dir}")

    # Création des arguments pour setup_tools. Par défaut, tout est skippé.
    setup_kwargs = {
        "skip_jdk": "jdk" not in tools_to_ensure,
        "skip_octave": "octave" not in tools_to_ensure,
        "skip_node": "node" not in tools_to_ensure
    }

    try:
        installed_tools = setup_tools(
            tools_dir_base_path=str(libs_dir),
            logger_instance=local_logger,
            force_reinstall=force_reinstall,
            **setup_kwargs
        )
        
        # Mettre à jour les variables d'environnement pour la session courante
        all_tools_ok = True
        for tool_name in tools_to_ensure:
            tool_env_var = {"jdk": "JAVA_HOME", "node": "NODE_HOME", "octave": "OCTAVE_HOME"}.get(tool_name)
            if tool_env_var and tool_env_var in installed_tools:
                tool_path = installed_tools[tool_env_var]
                os.environ[tool_env_var] = tool_path
                local_logger.success(f"{tool_name.upper()} est configuré. {tool_env_var}={tool_path}")

                # Ajout au PATH
                path_to_add = Path(tool_path)
                if tool_name == "jdk":
                    path_to_add = path_to_add / "bin"
                
                if str(path_to_add) not in os.environ.get("PATH", ""):
                     os.environ["PATH"] = f"{str(path_to_add)}{os.pathsep}{os.environ.get('PATH', '')}"
                     local_logger.info(f"Ajouté '{path_to_add}' au PATH système.")

            elif tool_env_var:
                local_logger.error(f"L'installation de {tool_name.upper()} a échoué ou n'a pas retourné de chemin.")
                all_tools_ok = False

        return all_tools_ok

    except Exception as e:
        local_logger.error(f"Une erreur critique est survenue lors de l'appel à setup_tools: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    main_logger = logging.getLogger("ToolInstallerDemo")
    main_logger.info("--- Démonstration de l'installation des outils (JDK et Node.js) ---")

    # On ne touche pas aux variables d'environnement existantes pour ce test,
    # setup_tools les vérifiera de lui-même.
    
    success = ensure_tools_are_installed(
        tools_to_ensure=['jdk', 'node'],
        logger_instance=main_logger
    )

    if success:
        main_logger.info("\n--- RÉSULTAT DE LA DÉMONSTRATION ---")
        main_logger.info("Installation/vérification terminée avec succès.")
        if 'JAVA_HOME' in os.environ:
            main_logger.info(f"  JAVA_HOME='{os.environ['JAVA_HOME']}'")
        if 'NODE_HOME' in os.environ:
            main_logger.info(f"  NODE_HOME='{os.environ['NODE_HOME']}'")
    else:
        main_logger.error("\n--- RÉSULTAT DE LA DÉMONSTRATION ---")
        main_logger.error("La démonstration a rencontré des problèmes. Veuillez vérifier les logs.")

    main_logger.info("\n--- Fin de la démonstration ---")