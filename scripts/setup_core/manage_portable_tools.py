# scripts/setup_core/manage_portable_tools.py
import os
import sys
import platform
import requests
import zipfile
import shutil
import re
import time # Ajout pour le timestamp et l'intervalle de log
import logging # Ajout pour le logger

# Logger par défaut pour ce module
module_logger_tools = logging.getLogger(__name__)
if not module_logger_tools.hasHandlers():
    _console_handler_tools = logging.StreamHandler(sys.stdout)
    _console_handler_tools.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s (module default tools)'))
    module_logger_tools.addHandler(_console_handler_tools)
    module_logger_tools.setLevel(logging.INFO)

def _get_logger_tools(logger_instance=None):
    """Retourne le logger fourni ou le logger par défaut du module."""
    return logger_instance if logger_instance else module_logger_tools

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
    "url_windows": "https://mirrors.ocf.berkeley.edu/gnu/octave/windows/octave-8.4.0-w64.zip", # URL de miroir modifiée
    # "url_linux": "...", # Souvent installé via gestionnaire de paquets
    # "url_macos": "...", # Souvent installé via gestionnaire de paquets ou dmg
    "dir_name_pattern": r"octave-8.4.0-w64.*", # Regex pour correspondre au répertoire extrait
    "home_env_var": "OCTAVE_HOME"
}
NODE_CONFIG = {
   "name": "Node.js",
   "url_windows": "https://nodejs.org/dist/v20.14.0/node-v20.14.0-win-x64.zip",
   "dir_name_pattern": r"node-v20\.14\.0-win-x64",
   "home_env_var": "NODE_HOME"
}

TOOLS_TO_MANAGE = [JDK_CONFIG, OCTAVE_CONFIG, NODE_CONFIG]

def _download_file(url, dest_folder, file_name, logger_instance=None, log_interval_seconds=5, force_download=False):
    """
    Télécharge un fichier depuis une URL vers un dossier de destination avec journalisation améliorée.
    Retourne le chemin du fichier et un booléen indiquant si le téléchargement a eu lieu (True) ou si un fichier existant a été utilisé (False).
    """
    logger = _get_logger_tools(logger_instance)
    logger.debug(f"_download_file called with: url={url}, dest_folder={dest_folder}, file_name={file_name}, force_download={force_download}")
    os.makedirs(dest_folder, exist_ok=True)
    file_path = os.path.join(dest_folder, file_name)

    if not force_download and os.path.exists(file_path):
        logger.info(f"Archive {file_name} already exists in {dest_folder}. Using local copy.")
        try:
            response_head = requests.head(url, timeout=10)
            remote_size = int(response_head.headers.get('content-length', 0))
            local_size = os.path.getsize(file_path)
            if remote_size > 0 and local_size != remote_size:
                logger.warning(f"Local file {file_name} size ({local_size} bytes) differs from remote size ({remote_size} bytes). Consider re-downloading.")
        except requests.exceptions.RequestException:
            logger.warning(f"Could not verify remote size for {file_name}. Proceeding with local copy.")
        return file_path, False

    if force_download and os.path.exists(file_path):
        logger.info(f"Force download: deleting existing file {file_path}")
        try:
            os.remove(file_path)
        except OSError as e:
            logger.error(f"Could not delete existing file {file_path} for forced download: {e}", exc_info=True)
            return None, False

    logger.info(f"Downloading {file_name} from {url}...")
    try:
        with requests.get(url, stream=True, timeout=600) as r:
            r.raise_for_status()
            total_size = int(r.headers.get('content-length', 0))
            
            if total_size > 0:
                logger.info(f"Total file size: {total_size} bytes ({total_size / (1024*1024):.2f} MB)")
            else:
                logger.warning("Content-Length header not found or is zero. Download progress percentage will not be shown, but byte count will.")
            
            downloaded_size = 0
            last_log_time = time.time()
            start_time = last_log_time

            with open(file_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        current_time = time.time()
                        
                        if current_time - last_log_time >= log_interval_seconds:
                            elapsed_time_total = current_time - start_time
                            speed_bps = downloaded_size / elapsed_time_total if elapsed_time_total > 0 else 0
                            speed_kbps = speed_bps / 1024
                            
                            progress_str = f"Downloaded {downloaded_size} bytes"
                            if total_size > 0:
                                progress_percentage = (downloaded_size / total_size) * 100
                                progress_str += f" / {total_size} bytes ({progress_percentage:.2f}%)"
                                if speed_bps > 0:
                                    remaining_bytes = total_size - downloaded_size
                                    eta_seconds = remaining_bytes / speed_bps if speed_bps > 0 else float('inf')
                                    eta_str = time.strftime("%H:%M:%S", time.gmtime(eta_seconds)) if eta_seconds != float('inf') else "N/A"
                                    progress_str += f" - Speed: {speed_kbps:.2f} KB/s - ETA: {eta_str}"
                            else:
                                progress_str += f" (total size unknown) - Speed: {speed_kbps:.2f} KB/s"
                            
                            # Utiliser logger.info pour la progression, mais sans \r pour éviter de polluer les logs fichiers.
                            # La console gérera le \r si le handler console le supporte.
                            # Pour les logs fichiers, chaque message sera une nouvelle ligne.
                            logger.info(progress_str + "...")
                            # Pour la console, on peut tenter un print direct avec \r si on veut cet effet
                            # sys.stdout.write("\r" + progress_str + "...")
                            # sys.stdout.flush()
                            last_log_time = current_time

            elapsed_time_total = time.time() - start_time
            speed_bps = downloaded_size / elapsed_time_total if elapsed_time_total > 0 else 0
            speed_kbps = speed_bps / 1024
            final_progress_str = f"Downloaded {downloaded_size} bytes"
            if total_size > 0:
                final_progress_str += f" / {total_size} bytes (100.00%)"
            final_progress_str += f" - Avg Speed: {speed_kbps:.2f} KB/s."
            logger.info(final_progress_str) # Log final sans \r

        logger.info(f"Download complete for {file_name}.")
        return file_path, True
    except requests.exceptions.Timeout:
        logger.error(f"Timeout occurred while downloading {file_name} from {url}.", exc_info=True)
        if os.path.exists(file_path):
            os.remove(file_path)
        return None, False
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to download {file_name}: {e}", exc_info=True)
        if os.path.exists(file_path):
            os.remove(file_path)
        return None, False

def _extract_zip(zip_path, extract_to_folder, logger_instance=None):
    """Extrait une archive ZIP."""
    logger = _get_logger_tools(logger_instance)
    logger.debug(f"Attempting to extract '{zip_path}' to '{extract_to_folder}'.")
    if not zip_path or not os.path.exists(zip_path):
        logger.error(f"ZIP file not found or path is invalid: {zip_path}")
        return False
    
    archive_name = os.path.basename(zip_path)
    logger.info(f"Starting extraction of {archive_name} to {extract_to_folder}...")
    
    if not os.path.exists(extract_to_folder):
        logger.debug(f"Destination folder '{extract_to_folder}' does not exist. Creating it.")
        try:
            os.makedirs(extract_to_folder, exist_ok=True)
        except Exception as e_mkdir:
            logger.error(f"Could not create destination folder '{extract_to_folder}': {e_mkdir}", exc_info=True)
            return False
            
    extracted_files_count = 0
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            members = zip_ref.infolist()
            num_members = len(members)
            logger.info(f"Opened ZIP file: {archive_name}. Contains {num_members} members.")
            
            logger.debug(f"Starting member-by-member extraction of {archive_name} to {extract_to_folder}...")
            
            extracted_count = 0
            if num_members > 0:
                log_interval = max(1, num_members // 20)
                if num_members > 5000:
                    log_interval = max(log_interval, 1000)
                if num_members < 100:
                    log_interval = max(1, num_members // 10)

                for i, member in enumerate(members):
                    zip_ref.extract(member, extract_to_folder)
                    extracted_count += 1
                    if (i + 1) % log_interval == 0 or (i + 1) == num_members:
                        logger.info(f"Extracted {extracted_count}/{num_members} members for {archive_name} ({(extracted_count/num_members*100):.2f}%)...")
            
            logger.info(f"Member-by-member extraction of {archive_name} complete. Extracted {extracted_count} members.")
            extracted_files_count = extracted_count
        
        if os.path.isdir(extract_to_folder):
            extracted_content = os.listdir(extract_to_folder)
            if extracted_content:
                logger.debug(f"Destination folder '{extract_to_folder}' exists and is not empty after extraction. Contains {len(extracted_content)} top-level items.")
            else:
                logger.warning(f"Destination folder '{extract_to_folder}' exists but is EMPTY after extraction of {archive_name}.")
        else:
            logger.error(f"Destination folder '{extract_to_folder}' DOES NOT EXIST after extraction attempt of {archive_name}.")
            return False

        logger.debug(f"Reached end of _extract_zip. zip_path is: {zip_path}.")
        return True
    except zipfile.BadZipFile as e_badzip:
        logger.error(f"Failed to extract {archive_name}. File might be corrupted or not a valid ZIP file. Error: {e_badzip}", exc_info=True)
        return False
    except PermissionError as e_perm:
        logger.error(f"Permission error during extraction of {archive_name} to {extract_to_folder}. Error: {e_perm}", exc_info=True)
        return False
    except Exception as e:
        logger.error(f"An unexpected error occurred during extraction of {archive_name}. Error: {e}", exc_info=True)
        return False

def _find_tool_dir(base_dir, pattern, logger_instance=None):
    """Trouve un répertoire correspondant à un pattern regex dans base_dir."""
    logger = _get_logger_tools(logger_instance)
    if not os.path.isdir(base_dir):
        logger.debug(f"_find_tool_dir: base_dir '{base_dir}' is not a directory.")
        return None
    for item in os.listdir(base_dir):
        item_path = os.path.join(base_dir, item)
        if os.path.isdir(item_path) and re.fullmatch(pattern, item):
            logger.debug(f"_find_tool_dir: Found matching dir '{item_path}' for pattern '{pattern}' in '{base_dir}'.")
            return item_path
    logger.debug(f"_find_tool_dir: No matching dir for pattern '{pattern}' in '{base_dir}'.")
    return None

def setup_single_tool(tool_config, tools_base_dir, temp_download_dir, logger_instance=None, force_reinstall=False, interactive=False):
    """Gère le téléchargement, l'extraction et la configuration d'un seul outil portable."""
    logger = _get_logger_tools(logger_instance)
    logger.info(f"--- Managing {tool_config['name']} ---")
    logger.debug(f"Initial tool_config for {tool_config['name']}: {tool_config}")
    
    tool_name = tool_config['name']
    current_os = platform.system().lower()
    url = None
    if current_os == "windows":
        url = tool_config.get("url_windows")
    elif current_os == "linux":
        url = tool_config.get("url_linux")
    elif current_os == "darwin": # macOS
        url = tool_config.get("url_macos")
    
    if not url:
        logger.warning(f"No download URL configured for {tool_name} on {current_os}. Skipping.")
        return None

    archive_name = os.path.basename(url)
    expected_tool_path = _find_tool_dir(tools_base_dir, tool_config["dir_name_pattern"], logger_instance=logger)

    if expected_tool_path and os.path.isdir(expected_tool_path):
        logger.info(f"{tool_name} found at: {expected_tool_path}")
        if force_reinstall:
            logger.info(f"Force reinstall is enabled for {tool_name}.")
        elif interactive:
            logger.info(f"Interactive mode for {tool_name}.")
            logger.info(f"{tool_name} exists. To reinstall, use --force-reinstall.")
            if not force_reinstall:
                 return expected_tool_path
        
        should_reinstall_existing = False
        if force_reinstall:
            should_reinstall_existing = True
        elif interactive:
            try:
                choice = input(f"Reinstall {tool_name}? (y/N): ").lower()
                if choice == 'y':
                    should_reinstall_existing = True
            except EOFError:
                 logger.warning("input() called in non-interactive context during setup_single_tool. Assuming 'No' for reinstallation.")


        if should_reinstall_existing:
            logger.info(f"Removing existing {tool_name} at {expected_tool_path}...")
            try:
                shutil.rmtree(expected_tool_path)
                logger.info(f"Successfully removed {expected_tool_path}.")
                expected_tool_path = None
            except OSError as e:
                logger.error(f"Failed to remove {expected_tool_path}: {e}", exc_info=True)
                return expected_tool_path
        else:
            logger.info(f"Using existing {tool_name} installation.")
            return expected_tool_path

    if not expected_tool_path:
        logger.info(f"{tool_name} not found or marked for reinstallation. Proceeding with download and setup.")
        logger.debug(f"URL to be used for download: {url}")
        logger.debug(f"Archive name: {archive_name}")
        logger.debug(f"Temp download dir: {temp_download_dir}")
        downloaded_archive_path, downloaded_this_run = _download_file(url, temp_download_dir, archive_name, logger_instance=logger, force_download=force_reinstall or not os.path.exists(os.path.join(temp_download_dir, archive_name))) # force if reinstall or not exists
        
        if not downloaded_archive_path:
            logger.error(f"Failed to download {tool_name}. Aborting setup for this tool.")
            return None

        extraction_successful = _extract_zip(downloaded_archive_path, tools_base_dir, logger_instance=logger)

        if not extraction_successful and not downloaded_this_run:
            logger.warning(f"Extraction failed for locally found archive: {downloaded_archive_path}. Deleting it and retrying download.")
            try:
                os.remove(downloaded_archive_path)
                logger.info(f"Deleted potentially corrupted local archive: {downloaded_archive_path}")
            except OSError as e:
                logger.error(f"Failed to delete corrupted local archive {downloaded_archive_path}: {e}", exc_info=True)
                return None

            logger.info(f"Retrying download for {tool_name}...")
            downloaded_archive_path, downloaded_this_run = _download_file(url, temp_download_dir, archive_name, logger_instance=logger, force_download=True)
            if not downloaded_archive_path:
                logger.error(f"Failed to re-download {tool_name} after deleting local copy. Aborting setup.")
                return None
            
            logger.info(f"Retrying extraction for {tool_name} from newly downloaded archive...")
            extraction_successful = _extract_zip(downloaded_archive_path, tools_base_dir, logger_instance=logger)

        if not extraction_successful:
            logger.error(f"Failed to extract {tool_name} (archive: {downloaded_archive_path}) even after potential retry. Aborting setup.")
            if os.path.isdir(tools_base_dir):
                logger.debug(f"Contents of target base directory '{tools_base_dir}' after failed extraction:")
                try:
                    for item in os.listdir(tools_base_dir):
                        logger.debug(f"  - {item}")
                except Exception as e_ls:
                    logger.debug(f"    Could not list contents: {e_ls}", exc_info=True)
            else:
                logger.debug(f"Target base directory '{tools_base_dir}' does not exist or is not a directory.")
            return None
        
        expected_tool_path = _find_tool_dir(tools_base_dir, tool_config["dir_name_pattern"], logger_instance=logger)
        if not expected_tool_path:
            logger.error(f"Could not find {tool_name} directory in {tools_base_dir} after extraction using pattern {tool_config['dir_name_pattern']}.")
            try:
                logger.error(f"Contents of {tools_base_dir}: {os.listdir(tools_base_dir)}")
            except Exception:
                logger.error(f"Could not list contents of {tools_base_dir}")
            return None
        logger.info(f"{tool_name} successfully set up at: {expected_tool_path}")

    return expected_tool_path


def setup_tools(tools_dir_base_path, logger_instance=None, force_reinstall=False, interactive=False, skip_jdk=False, skip_octave=False, skip_node=False):
    """Configure les outils portables (JDK, Octave, Node.js)."""
    logger = _get_logger_tools(logger_instance)
    logger.debug(f"setup_tools called with: tools_dir_base_path={tools_dir_base_path}, force_reinstall={force_reinstall}, interactive={interactive}, skip_jdk={skip_jdk}, skip_octave={skip_octave}, skip_node={skip_node}")
    os.makedirs(tools_dir_base_path, exist_ok=True)
    temp_download_dir = os.path.join(tools_dir_base_path, "_temp_downloads")

    installed_tool_paths = {}

    if not skip_jdk:
        jdk_home = setup_single_tool(JDK_CONFIG, tools_dir_base_path, temp_download_dir, logger_instance=logger, force_reinstall=force_reinstall, interactive=interactive)
        if jdk_home:
            installed_tool_paths[JDK_CONFIG["home_env_var"]] = jdk_home
    else:
        logger.info("Skipping JDK setup as per request.")

    if not skip_octave:
        octave_home = setup_single_tool(OCTAVE_CONFIG, tools_dir_base_path, temp_download_dir, logger_instance=logger, force_reinstall=force_reinstall, interactive=interactive)
        if octave_home:
            installed_tool_paths[OCTAVE_CONFIG["home_env_var"]] = octave_home
    else:
        logger.info("Skipping Octave setup as per request.")

    if not skip_node:
        node_home = setup_single_tool(NODE_CONFIG, tools_dir_base_path, temp_download_dir, logger_instance=logger, force_reinstall=force_reinstall, interactive=interactive)
        if node_home:
            installed_tool_paths[NODE_CONFIG["home_env_var"]] = node_home
    else:
        logger.info("Skipping Node.js setup as per request.")
        
    if os.path.isdir(temp_download_dir):
        logger.info(f"Temporary download directory {temp_download_dir} can be cleaned up manually for now.")
    else:
        logger.debug(f"Temporary download directory {temp_download_dir} was not created or already cleaned up.")

    return installed_tool_paths

if __name__ == '__main__':
    # Configuration du logger pour les tests locaux directs
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s (main test tools)',
                        handlers=[logging.StreamHandler(sys.stdout)])
    logger_main_tools = logging.getLogger(__name__)

    project_root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    test_tools_dir = os.path.join(project_root_dir, ".test_tools_portable")
    
    logger_main_tools.info(f"--- Testing portable tools setup in: {test_tools_dir} ---")
    logger_main_tools.info(f"--- Project root detected as: {project_root_dir} ---")
    
    # Pour tester, décommentez une des lignes suivantes :
    # installed = setup_tools(test_tools_dir, logger_instance=logger_main_tools, interactive=False, force_reinstall=False)
    # installed = setup_tools(test_tools_dir, logger_instance=logger_main_tools, interactive=False, skip_jdk=True, skip_octave=True)
    # installed = setup_tools(test_tools_dir, logger_instance=logger_main_tools, interactive=False, force_reinstall=True, skip_octave=True) # Test JDK
    
    logger_main_tools.info("\n--- Test Configuration ---")
    logger_main_tools.info(f"Test tools directory: {test_tools_dir}")
    logger_main_tools.info("To run tests, uncomment one of the 'setup_tools' calls above.")
    logger_main_tools.info("Example test call (downloads JDK if not present, skips Octave):")
    logger_main_tools.info(f"# installed = setup_tools('{test_tools_dir}', logger_instance=logger_main_tools, interactive=False, force_reinstall=False, skip_octave=True)")
    
    installed = setup_tools(test_tools_dir, logger_instance=logger_main_tools, interactive=False, force_reinstall=False, skip_octave=True)
    # if installed.get("JAVA_HOME"):
    #     logger_main_tools.info(f"JAVA_HOME set to: {installed['JAVA_HOME']}")
    # else:
    #     logger_main_tools.info("JAVA_HOME not set.")

    logger_main_tools.info("\nScript finished. Manually inspect the test directory and uncomment test calls to verify functionality.")