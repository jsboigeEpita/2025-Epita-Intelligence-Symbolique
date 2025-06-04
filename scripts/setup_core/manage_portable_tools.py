# scripts/setup_core/manage_portable_tools.py
import os
import sys
import platform
import requests
import zipfile
import shutil
import re

JDK_CONFIG = {
    "name": "JDK",
    "url_windows": "https://github.com/adoptium/temurin17-binaries/releases/download/jdk-17.0.11%2B9/OpenJDK17U-jdk_x64_windows_hotspot_17.0.11_9.zip",
    # "url_linux": "https://download.oracle.com/java/17/latest/jdk-17_linux-x64_bin.tar.gz", # Exemple
    # "url_macos": "https://download.oracle.com/java/17/latest/jdk-17_macos-x64_bin.tar.gz", # Exemple
    "dir_name_pattern": r"jdk-17.*",  # Regex pour correspondre à des versions comme jdk-17.0.1, jdk-17.0.11
    "home_env_var": "JAVA_HOME"
}
OCTAVE_CONFIG = {
    "name": "Octave",
    "url_windows": "https://ftp.gnu.org/gnu/octave/windows/octave-8.4.0-w64.zip",
    # "url_linux": "...", # Souvent installé via gestionnaire de paquets
    # "url_macos": "...", # Souvent installé via gestionnaire de paquets ou dmg
    "dir_name_pattern": r"octave-8.4.0-w64.*", # Regex pour correspondre au répertoire extrait
    "home_env_var": "OCTAVE_HOME"
}

TOOLS_TO_MANAGE = [JDK_CONFIG, OCTAVE_CONFIG] # Peut être utilisé si on boucle sur les outils plus tard

def _download_file(url, dest_folder, file_name):
    """Télécharge un fichier depuis une URL vers un dossier de destination."""
    print(f"[DEBUG_ROO] _download_file called with: url={url}, dest_folder={dest_folder}, file_name={file_name}")
    os.makedirs(dest_folder, exist_ok=True)
    file_path = os.path.join(dest_folder, file_name)

    # Vérifier si l'archive existe déjà
    if os.path.exists(file_path):
        print(f"[INFO] Archive {file_name} already exists in {dest_folder}. Using local copy.")
        # Une vérification de l'intégrité du fichier (ex: checksum) pourrait être ajoutée ici à l'avenir.
        return file_path
    
    print(f"Downloading {file_name} from {url}...")
    try:
        with requests.get(url, stream=True, timeout=300) as r: # Timeout de 5 minutes
            r.raise_for_status()
            total_size = int(r.headers.get('content-length', 0))
            downloaded_size = 0
            with open(file_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
                    downloaded_size += len(chunk)
                    if total_size > 0:
                        progress = (downloaded_size / total_size) * 100
                        sys.stdout.write(f"\rDownloaded {downloaded_size}/{total_size} bytes ({progress:.2f}%)")
                        sys.stdout.flush()
        sys.stdout.write("\nDownload complete.\n")
        return file_path
    except requests.exceptions.RequestException as e:
        print(f"\n[ERROR] Failed to download {file_name}: {e}")
        if os.path.exists(file_path):
            os.remove(file_path)
        return None

def _extract_zip(zip_path, extract_to_folder):
    """Extrait une archive ZIP et la supprime ensuite."""
    if not zip_path or not os.path.exists(zip_path):
        print(f"[ERROR] ZIP file not found: {zip_path}")
        return False
    
    print(f"Extracting {os.path.basename(zip_path)} to {extract_to_folder}...")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to_folder)
        print("Extraction complete.")
        print(f"[DEBUG_ROO] Reached end of _extract_zip. zip_path is: {zip_path}. os.remove is commented.")
        # os.remove(zip_path) # Conserver l'archive pour réutilisation potentielle
        # print(f"Archive {zip_path} kept for potential reuse.") # L'archive est conservée.
        return True
    except zipfile.BadZipFile:
        print(f"[ERROR] Failed to extract {os.path.basename(zip_path)}. File might be corrupted or not a ZIP file.")
        return False
    except Exception as e:
        print(f"[ERROR] An error occurred during extraction: {e}")
        return False

def _find_tool_dir(base_dir, pattern):
    """Trouve un répertoire correspondant à un pattern regex dans base_dir."""
    if not os.path.isdir(base_dir):
        return None
    for item in os.listdir(base_dir):
        item_path = os.path.join(base_dir, item)
        if os.path.isdir(item_path) and re.fullmatch(pattern, item):
            return item_path
    return None

def setup_single_tool(tool_config, tools_base_dir, temp_download_dir, force_reinstall=False, interactive=False):
    """Gère le téléchargement, l'extraction et la configuration d'un seul outil portable."""
    print(f"--- Managing {tool_config['name']} ---")
    print(f"[DEBUG_ROO] Initial tool_config for {tool_config['name']}: {tool_config}")
    
    tool_name = tool_config['name']
    # Déterminer l'URL en fonction de l'OS (simplifié pour Windows pour l'instant)
    current_os = platform.system().lower()
    url = None
    if current_os == "windows":
        url = tool_config.get("url_windows")
    elif current_os == "linux":
        url = tool_config.get("url_linux")
    elif current_os == "darwin": # macOS
        url = tool_config.get("url_macos")
    
    if not url:
        print(f"[WARNING] No download URL configured for {tool_name} on {current_os}. Skipping.")
        return None

    archive_name = os.path.basename(url)
    
    # Vérifier si l'outil existe déjà
    expected_tool_path = _find_tool_dir(tools_base_dir, tool_config["dir_name_pattern"])

    if expected_tool_path and os.path.isdir(expected_tool_path):
        print(f"[INFO] {tool_name} found at: {expected_tool_path}")
        if force_reinstall:
            print(f"[INFO] Force reinstall is enabled for {tool_name}.")
        elif interactive:
            print(f"[INFO] Interactive mode for {tool_name}.")
            # Demander confirmation avant de supprimer
            # Note: input() ne fonctionnera pas bien dans un script non interactif.
            # Pour une vraie interactivité, argparse ou une bibliothèque dédiée serait mieux.
            # Ici, on simule ou on suppose une réponse.
            # Pour l'instant, si interactif et existe, on ne réinstalle pas sauf si force_reinstall est aussi vrai.
            # Une meilleure logique serait:
            # if interactive and not force_reinstall:
            #     choice = input(f"{tool_name} already exists. Reinstall? (y/N): ").lower()
            #     if choice != 'y':
            #         return expected_tool_path
            # elif not force_reinstall: # Non interactif, non forcé, existe => on garde
            #     return expected_tool_path
            print(f"[INFO] {tool_name} exists. To reinstall, use --force-reinstall.")
            if not force_reinstall: # Si interactif mais pas de force_reinstall, on ne fait rien de plus
                 return expected_tool_path


        if force_reinstall or (interactive and input(f"Reinstall {tool_name}? (y/N): ").lower() == 'y'):
            print(f"Removing existing {tool_name} at {expected_tool_path}...")
            try:
                shutil.rmtree(expected_tool_path)
                print(f"Successfully removed {expected_tool_path}.")
                expected_tool_path = None # Pour forcer le re-téléchargement
            except OSError as e:
                print(f"[ERROR] Failed to remove {expected_tool_path}: {e}")
                return expected_tool_path # Retourner l'ancien chemin si la suppression échoue
        else: # Existe, pas de force_reinstall, ou interactif et l'utilisateur a dit non
            print(f"[INFO] Using existing {tool_name} installation.")
            return expected_tool_path


    # Si l'outil n'existe pas ou a été supprimé
    if not expected_tool_path:
        print(f"[INFO] {tool_name} not found or marked for reinstallation. Proceeding with download and setup.")
        print(f"[DEBUG_ROO] URL to be used for download: {url}")
        print(f"[DEBUG_ROO] Archive name: {archive_name}")
        print(f"[DEBUG_ROO] Temp download dir: {temp_download_dir}")
        downloaded_archive_path = _download_file(url, temp_download_dir, archive_name)
        if not downloaded_archive_path:
            print(f"[ERROR] Failed to download {tool_name}. Aborting setup for this tool.")
            return None

        if not _extract_zip(downloaded_archive_path, tools_base_dir):
            print(f"[ERROR] Failed to extract {tool_name}. Aborting setup for this tool.")
            return None
        
        # Après extraction, trouver le répertoire exact
        expected_tool_path = _find_tool_dir(tools_base_dir, tool_config["dir_name_pattern"])
        if not expected_tool_path:
            print(f"[ERROR] Could not find {tool_name} directory in {tools_base_dir} after extraction using pattern {tool_config['dir_name_pattern']}.")
            print(f"Contents of {tools_base_dir}: {os.listdir(tools_base_dir)}")
            return None
        print(f"[INFO] {tool_name} successfully set up at: {expected_tool_path}")

    return expected_tool_path


def setup_tools(tools_dir_base_path, force_reinstall=False, interactive=False, skip_jdk=False, skip_octave=False):
    """Configure les outils portables (JDK, Octave)."""
    os.makedirs(tools_dir_base_path, exist_ok=True)
    temp_download_dir = os.path.join(tools_dir_base_path, "_temp_downloads")
    # Ne pas créer _temp_downloads ici, _download_file s'en chargera si besoin.

    installed_tool_paths = {}

    if not skip_jdk:
        jdk_home = setup_single_tool(JDK_CONFIG, tools_dir_base_path, temp_download_dir, force_reinstall, interactive)
        if jdk_home:
            installed_tool_paths[JDK_CONFIG["home_env_var"]] = jdk_home
    else:
        print("[INFO] Skipping JDK setup as per request.")

    if not skip_octave:
        octave_home = setup_single_tool(OCTAVE_CONFIG, tools_dir_base_path, temp_download_dir, force_reinstall, interactive)
        if octave_home:
            installed_tool_paths[OCTAVE_CONFIG["home_env_var"]] = octave_home
    else:
        print("[INFO] Skipping Octave setup as per request.")
        
    # Nettoyer le répertoire de téléchargement temporaire
    if os.path.isdir(temp_download_dir):
        # print(f"[INFO] Cleaning up temporary download directory: {temp_download_dir}")
        # shutil.rmtree(temp_download_dir) # Commenté selon les instructions initiales
        print(f"[INFO] Temporary download directory {temp_download_dir} can be cleaned up manually for now.")
    else:
        print(f"[INFO] Temporary download directory {temp_download_dir} was not created or already cleaned up.")

    return installed_tool_paths

if __name__ == '__main__':
    # Pour tests locaux
    # Détermine le répertoire racine du projet (remonte de trois niveaux depuis ce script)
    # scripts/setup_core/manage_portable_tools.py -> scripts/setup_core -> scripts -> project_root
    project_root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    test_tools_dir = os.path.join(project_root_dir, ".test_tools_portable") # Nom différent pour éviter conflits
    
    print(f"--- Testing portable tools setup in: {test_tools_dir} ---")
    print(f"--- Project root detected as: {project_root_dir} ---")

    # Exemple de test:
    # Pour tester, vous pouvez créer un virtualenv, installer requests: pip install requests
    # Puis exécuter: python scripts/setup_core/manage_portable_tools.py
    
    # Test complet (peut prendre du temps à cause des téléchargements)
    # installed = setup_tools(test_tools_dir, interactive=False, force_reinstall=False)
    
    # Test en sautant les outils
    # installed = setup_tools(test_tools_dir, interactive=False, skip_jdk=True, skip_octave=True)

    # Test avec réinstallation forcée (attention, va re-télécharger)
    # installed = setup_tools(test_tools_dir, interactive=False, force_reinstall=True, skip_octave=True) # Test JDK
    # installed = setup_tools(test_tools_dir, interactive=False, force_reinstall=True, skip_jdk=True) # Test Octave

    print("\n--- Test Configuration ---")
    print(f"Test tools directory: {test_tools_dir}")
    print("To run tests, uncomment one of the 'setup_tools' calls above.")
    print("Example test call (downloads JDK if not present, skips Octave):")
    print(f"# installed = setup_tools('{test_tools_dir}', interactive=False, force_reinstall=False, skip_octave=True)")
    
    # Décommentez la ligne suivante pour un test rapide du JDK
    # installed = setup_tools(test_tools_dir, interactive=False, force_reinstall=False, skip_octave=True)
    # if installed.get("JAVA_HOME"):
    #     print(f"JAVA_HOME set to: {installed['JAVA_HOME']}")
    # else:
    #     print("JAVA_HOME not set.")

    print("\nScript finished. Manually inspect the test directory and uncomment test calls to verify functionality.")