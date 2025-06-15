import os
import platform
from pathlib import Path
from typing import List, Dict, Optional

# Tentative d'importation des modules nécessaires du projet
# Ces imports pourraient avoir besoin d'être ajustés en fonction de la structure finale
try:
    from project_core.setup_core_from_scripts.manage_portable_tools import setup_tools
    from project_core.core_from_scripts.common_utils import Logger, get_project_root
except ImportError:
    # Fallback si les imports directs échouent (par exemple, lors de tests unitaires ou exécution isolée)
    # Cela suppose que le script est exécuté depuis un endroit où le sys.path est déjà configuré
    # ou que ces modules ne sont pas strictement nécessaires pour une version de base.
    # Pour une solution robuste, il faudrait une meilleure gestion du sys.path ici.
    print("Avertissement: Certains modules de project_core n'ont pas pu être importés. "
          "La fonctionnalité complète de tool_installer pourrait être affectée.")
    # Définitions minimales pour que le reste du code ne plante pas immédiatement
    class Logger:
        def __init__(self, verbose=False): self.verbose = verbose
        def info(self, msg): print(f"INFO: {msg}")
        def warning(self, msg): print(f"WARNING: {msg}")
        def error(self, msg, exc_info=False): print(f"ERROR: {msg}")
        def success(self, msg): print(f"SUCCESS: {msg}")
        def debug(self, msg): print(f"DEBUG: {msg}")

    def get_project_root() -> str:
        # Heuristique simple pour trouver la racine du projet
        # Peut nécessiter d'être ajustée
        current_path = Path(__file__).resolve()
        # Remonter jusqu'à trouver un marqueur de projet (ex: .git, pyproject.toml)
        # ou un nombre fixe de parents
        for _ in range(4): # Ajuster le nombre de parents si nécessaire
            if (current_path / ".git").exists() or (current_path / "pyproject.toml").exists():
                return str(current_path)
            current_path = current_path.parent
        return str(Path(__file__).resolve().parent.parent.parent) # Fallback

    def setup_tools(tools_dir_base_path: str, logger_instance: Logger, 
                    skip_jdk: bool = True, skip_node: bool = True, skip_octave: bool = True) -> Dict[str, str]:
        logger_instance.error("La fonction 'setup_tools' de secours est appelée. "
                              "L'installation des outils ne fonctionnera pas correctement.")
        return {}

# Configuration globale
DEFAULT_PROJECT_ROOT = Path(get_project_root())
DEFAULT_LIBS_DIR = DEFAULT_PROJECT_ROOT / "libs"
DEFAULT_PORTABLE_TOOLS_DIR = DEFAULT_LIBS_DIR / "portable_tools" # Un sous-dossier pour plus de clarté

# Mappage des noms d'outils aux variables d'environnement et options de skip pour setup_tools
TOOL_CONFIG = {
    "jdk": {
        "env_var": "JAVA_HOME",
        "skip_flag_true_means_skip": "skip_jdk", # Le flag dans setup_tools pour sauter cet outil
        "install_subdir": "jdk", # Sous-dossier suggéré dans DEFAULT_PORTABLE_TOOLS_DIR
        "bin_subdir": "bin" # Sous-dossier contenant les exécutables
    },
    "node": {
        "env_var": "NODE_HOME",
        "skip_flag_true_means_skip": "skip_node",
        "install_subdir": "nodejs",
        "bin_subdir": "" # Node.js ajoute souvent son dossier racine au PATH
    }
    # Ajouter d'autres outils ici si nécessaire (ex: Octave)
}

def ensure_tools_are_installed(
    tools_to_ensure: List[str],
    logger: Optional[Logger] = None,
    tools_install_dir: Optional[Path] = None,
    project_root_path: Optional[Path] = None
) -> bool:
    """
    S'assure que les outils spécifiés sont installés et que leurs variables
    d'environnement sont configurées.

    Args:
        tools_to_ensure: Liste des noms d'outils à vérifier/installer (ex: ['jdk', 'node']).
        logger: Instance de Logger pour les messages.
        tools_install_dir: Répertoire de base pour l'installation des outils portables.
                           Par défaut: <project_root>/libs/portable_tools.
        project_root_path: Chemin vers la racine du projet.
                           Par défaut: déterminé par get_project_root().

    Returns:
        True si tous les outils demandés sont configurés avec succès, False sinon.
    """
    local_logger = logger or Logger()
    current_project_root = project_root_path or DEFAULT_PROJECT_ROOT
    base_install_dir = tools_install_dir or DEFAULT_PORTABLE_TOOLS_DIR

    base_install_dir.mkdir(parents=True, exist_ok=True)
    local_logger.info(f"Répertoire de base pour les outils portables : {base_install_dir}")

    all_tools_ok = True

    for tool_name in tools_to_ensure:
        if tool_name.lower() not in TOOL_CONFIG:
            local_logger.warning(f"Configuration pour l'outil '{tool_name}' non trouvée. Ignoré.")
            all_tools_ok = False
            continue

        config = TOOL_CONFIG[tool_name.lower()]
        env_var_name = config["env_var"]
        tool_specific_install_dir = base_install_dir / config["install_subdir"]
        tool_specific_install_dir.mkdir(parents=True, exist_ok=True)


        local_logger.info(f"Vérification de l'outil : {tool_name.upper()} (Variable: {env_var_name})")

        # 1. Vérifier si la variable d'environnement est déjà définie et valide
        env_var_value = os.environ.get(env_var_name)
        is_env_var_valid = False
        if env_var_value:
            tool_path = Path(env_var_value)
            if not tool_path.is_absolute():
                # Tenter de résoudre par rapport à la racine du projet si relatif
                potential_path = (current_project_root / env_var_value).resolve()
                if potential_path.is_dir():
                    local_logger.info(f"{env_var_name} ('{env_var_value}') résolu en chemin absolu: {potential_path}")
                    os.environ[env_var_name] = str(potential_path)
                    env_var_value = str(potential_path) # Mettre à jour pour la suite
                    tool_path = potential_path # Mettre à jour pour la suite
                else:
                    local_logger.warning(f"{env_var_name} ('{env_var_value}') est relatif et non résoluble depuis la racine du projet.")
            
            if tool_path.is_dir():
                is_env_var_valid = True
                local_logger.info(f"{env_var_name} est déjà défini et valide : {tool_path}")
            else:
                local_logger.warning(f"{env_var_name} ('{env_var_value}') est défini mais pointe vers un chemin invalide.")
        else:
            local_logger.info(f"{env_var_name} n'est pas défini dans l'environnement.")

        # 2. Si non valide ou non défini, tenter l'installation/configuration
        if not is_env_var_valid:
            local_logger.info(f"Tentative d'installation/configuration pour {tool_name.upper()} dans {tool_specific_install_dir}...")
            
            # Préparer les arguments pour setup_tools
            # Par défaut, on skip tous les outils, puis on active celui qu'on veut installer
            setup_tools_args = {
                "tools_dir_base_path": str(tool_specific_install_dir.parent), # setup_tools s'attend au parent du dossier spécifique de l'outil
                "logger_instance": local_logger,
                "skip_jdk": True,
                "skip_node": True,
                "skip_octave": True # Assumons qu'on gère Octave aussi, même si pas demandé explicitement
            }
            # Activer l'installation pour l'outil courant
            setup_tools_args[config["skip_flag_true_means_skip"]] = False
            
            try:
                installed_tools_paths = setup_tools(**setup_tools_args)

                if env_var_name in installed_tools_paths and Path(installed_tools_paths[env_var_name]).exists():
                    new_tool_path_str = installed_tools_paths[env_var_name]
                    os.environ[env_var_name] = new_tool_path_str
                    local_logger.success(f"{tool_name.upper()} auto-installé/configuré avec succès. {env_var_name} = {new_tool_path_str}")
                    env_var_value = new_tool_path_str # Mettre à jour pour la gestion du PATH
                else:
                    local_logger.error(f"L'auto-installation de {tool_name.upper()} a échoué ou n'a pas retourné de chemin valide pour {env_var_name}.")
                    all_tools_ok = False
                    continue # Passer à l'outil suivant
            except Exception as e:
                local_logger.error(f"Une erreur est survenue durant l'auto-installation de {tool_name.upper()}: {e}", exc_info=True)
                all_tools_ok = False
                continue # Passer à l'outil suivant
        
        # 3. S'assurer que le sous-répertoire 'bin' (si applicable) est dans le PATH système
        # Cette étape est cruciale, surtout pour JAVA_HOME et JPype.
        if os.environ.get(env_var_name): # Si la variable est maintenant définie (soit initialement, soit après install)
            tool_home_path = Path(os.environ[env_var_name])
            bin_subdir_name = config.get("bin_subdir")

            if bin_subdir_name: # Certains outils comme Node n'ont pas de sous-dossier 'bin' distinct dans leur HOME pour le PATH
                tool_bin_path = tool_home_path / bin_subdir_name
                if tool_bin_path.is_dir():
                    current_system_path = os.environ.get('PATH', '')
                    if str(tool_bin_path) not in current_system_path.split(os.pathsep):
                        os.environ['PATH'] = f"{str(tool_bin_path)}{os.pathsep}{current_system_path}"
                        local_logger.info(f"Ajouté {tool_bin_path} au PATH système.")
                    else:
                        local_logger.info(f"{tool_bin_path} est déjà dans le PATH système.")
                else:
                    local_logger.warning(f"Le sous-répertoire 'bin' ('{tool_bin_path}') pour {tool_name.upper()} n'a pas été trouvé. Le PATH n'a pas été mis à jour pour ce sous-répertoire.")
            elif tool_name.lower() == "node": # Cas spécial pour Node.js: NODE_HOME lui-même est souvent ajouté au PATH
                current_system_path = os.environ.get('PATH', '')
                if str(tool_home_path) not in current_system_path.split(os.pathsep):
                    os.environ['PATH'] = f"{str(tool_home_path)}{os.pathsep}{current_system_path}"
                    local_logger.info(f"Ajouté {tool_home_path} (NODE_HOME) au PATH système.")
                else:
                    local_logger.info(f"{tool_home_path} (NODE_HOME) est déjà dans le PATH système.")


    if all_tools_ok:
        local_logger.success("Tous les outils demandés ont été vérifiés/configurés.")
    else:
        local_logger.error("Certains outils n'ont pas pu être configurés correctement.")
        
    return all_tools_ok

if __name__ == "__main__":
    # Exemple d'utilisation
    logger = Logger(verbose=True)
    logger.info("Démonstration de ensure_tools_are_installed...")
    
    # Créer des répertoires de test pour simuler une installation
    test_project_root = Path(__file__).parent.parent / "test_tool_installer_project"
    test_project_root.mkdir(exist_ok=True)
    test_libs_dir = test_project_root / "libs"
    test_libs_dir.mkdir(exist_ok=True)
    test_portable_tools_dir = test_libs_dir / "portable_tools"
    test_portable_tools_dir.mkdir(exist_ok=True)

    logger.info(f"Utilisation du répertoire de test pour les outils : {test_portable_tools_dir}")

    # Simuler que JAVA_HOME et NODE_HOME ne sont pas définis initialement
    original_java_home = os.environ.pop('JAVA_HOME', None)
    original_node_home = os.environ.pop('NODE_HOME', None)
    original_path = os.environ.get('PATH')

    try:
        success = ensure_tools_are_installed(
            tools_to_ensure=['jdk', 'node'], 
            logger=logger,
            tools_install_dir=test_portable_tools_dir,
            project_root_path=test_project_root
        )
        
        if success:
            logger.success("Démonstration terminée avec succès.")
            if 'JAVA_HOME' in os.environ:
                logger.info(f"JAVA_HOME après exécution: {os.environ['JAVA_HOME']}")
            if 'NODE_HOME' in os.environ:
                logger.info(f"NODE_HOME après exécution: {os.environ['NODE_HOME']}")
            logger.info(f"PATH après exécution (peut être long): {os.environ.get('PATH')[:200]}...")
        else:
            logger.error("La démonstration a rencontré des problèmes.")

    finally:
        # Restaurer l'environnement
        if original_java_home: os.environ['JAVA_HOME'] = original_java_home
        if original_node_home: os.environ['NODE_HOME'] = original_node_home
        if original_path: os.environ['PATH'] = original_path
        
        # Nettoyage (optionnel, pour ne pas polluer)
        # import shutil
        # if test_project_root.exists():
        #     logger.info(f"Nettoyage du répertoire de test : {test_project_root}")
        #     shutil.rmtree(test_project_root)

    logger.info("Fin de la démonstration.")