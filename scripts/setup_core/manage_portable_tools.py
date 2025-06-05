# scripts/setup_core/manage_portable_tools.py
import os
import sys
import platform
import requests
import zipfile
import shutil
import re
import time # Ajout pour le timestamp et l'intervalle de log

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

TOOLS_TO_MANAGE = [JDK_CONFIG, OCTAVE_CONFIG] # Peut être utilisé si on boucle sur les outils plus tard

def _download_file(url, dest_folder, file_name, log_interval_seconds=5, force_download=False):
    """
    Télécharge un fichier depuis une URL vers un dossier de destination avec journalisation améliorée.
    Retourne le chemin du fichier et un booléen indiquant si le téléchargement a eu lieu (True) ou si un fichier existant a été utilisé (False).
    """
    print(f"[DEBUG_ROO] _download_file called with: url={url}, dest_folder={dest_folder}, file_name={file_name}, force_download={force_download}")
    os.makedirs(dest_folder, exist_ok=True)
    file_path = os.path.join(dest_folder, file_name)

    if not force_download and os.path.exists(file_path):
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [INFO] Archive {file_name} already exists in {dest_folder}. Using local copy.")
        # Optionnel: Vérifier la taille par rapport à la taille distante si possible
        try:
            response_head = requests.head(url, timeout=10)
            remote_size = int(response_head.headers.get('content-length', 0))
            local_size = os.path.getsize(file_path)
            if remote_size > 0 and local_size != remote_size:
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [WARNING] Local file {file_name} size ({local_size} bytes) differs from remote size ({remote_size} bytes). Consider re-downloading.")
        except requests.exceptions.RequestException:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [WARNING] Could not verify remote size for {file_name}. Proceeding with local copy.")
        return file_path, False # False car fichier existant utilisé

    if force_download and os.path.exists(file_path):
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [INFO] Force download: deleting existing file {file_path}")
        try:
            os.remove(file_path)
        except OSError as e:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] Could not delete existing file {file_path} for forced download: {e}")
            return None, False # Indiquer l'échec

    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Downloading {file_name} from {url}...")
    try:
        with requests.get(url, stream=True, timeout=600) as r: # Timeout de 10 minutes
            r.raise_for_status()
            total_size = int(r.headers.get('content-length', 0))
            
            if total_size > 0:
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [INFO] Total file size: {total_size} bytes ({total_size / (1024*1024):.2f} MB)")
            else:
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [WARNING] Content-Length header not found or is zero. Download progress percentage will not be shown, but byte count will.")
            
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
                            
                            progress_str = f"\r[{time.strftime('%Y-%m-%d %H:%M:%S')}] Downloaded {downloaded_size} bytes"
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
                            
                            sys.stdout.write(progress_str + "...")
                            sys.stdout.flush()
                            last_log_time = current_time

            elapsed_time_total = time.time() - start_time
            speed_bps = downloaded_size / elapsed_time_total if elapsed_time_total > 0 else 0
            speed_kbps = speed_bps / 1024
            final_progress_str = f"\r[{time.strftime('%Y-%m-%d %H:%M:%S')}] Downloaded {downloaded_size} bytes"
            if total_size > 0:
                final_progress_str += f" / {total_size} bytes (100.00%)"
            final_progress_str += f" - Avg Speed: {speed_kbps:.2f} KB/s."
            sys.stdout.write(final_progress_str + " " * 20 + "\n")
            sys.stdout.flush()

        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Download complete for {file_name}.")
        return file_path, True # True car le téléchargement a eu lieu
    except requests.exceptions.Timeout:
        print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] Timeout occurred while downloading {file_name} from {url}.")
        if os.path.exists(file_path):
            os.remove(file_path)
        return None, False # False car échec
    except requests.exceptions.RequestException as e:
        print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] Failed to download {file_name}: {e}")
        if os.path.exists(file_path):
            os.remove(file_path)
        return None, False # False car échec

def _extract_zip(zip_path, extract_to_folder):
    """Extrait une archive ZIP."""
    print(f"[DIAG_EXTRACT] Attempting to extract '{zip_path}' to '{extract_to_folder}'.")
    if not zip_path or not os.path.exists(zip_path):
        print(f"[ERROR_EXTRACT] ZIP file not found or path is invalid: {zip_path}")
        return False
    
    archive_name = os.path.basename(zip_path)
    print(f"[DIAG_EXTRACT] Starting extraction of {archive_name} to {extract_to_folder}...")
    
    # S'assurer que le répertoire de destination existe, sinon le créer.
    # ZipFile.extractall le fait, mais une vérification/création explicite peut aider au débogage.
    if not os.path.exists(extract_to_folder):
        print(f"[DIAG_EXTRACT] Destination folder '{extract_to_folder}' does not exist. Creating it.")
        try:
            os.makedirs(extract_to_folder, exist_ok=True)
        except Exception as e_mkdir:
            print(f"[ERROR_EXTRACT] Could not create destination folder '{extract_to_folder}': {e_mkdir}")
            return False
            
    extracted_files_count = 0
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            members = zip_ref.infolist()
            num_members = len(members)
            print(f"[DIAG_EXTRACT] Opened ZIP file: {archive_name}. Contains {num_members} members.")
            
            # Lister quelques membres pour vérification (peut être verbeux pour de grosses archives)
            # if num_members > 0:
            #     member_list_preview = [m.filename for m in members[:5]]
            #     print(f"[DIAG_EXTRACT] First few members: {member_list_preview}")

            print(f"[DIAG_EXTRACT] Starting member-by-member extraction of {archive_name} to {extract_to_folder}...")
            
            extracted_count = 0
            # Loguer la progression toutes les N étapes, ou au moins une fois au début et à la fin.
            # Pour les très grosses archives, on ne veut pas loguer chaque fichier.
            # Loguer environ toutes les 5% ou tous les 1000 fichiers, selon ce qui est le plus fréquent,
            # mais au moins une fois tous les 5000 fichiers pour ne pas spammer.
            if num_members > 0:
                log_interval = max(1, num_members // 20) # Log environ 20 fois (5%)
                if num_members > 5000: # Pour les très grosses archives, limiter la fréquence
                    log_interval = max(log_interval, 1000)
                if num_members < 100: # Pour les petites archives, loguer plus souvent
                    log_interval = max(1, num_members // 10)


                for i, member in enumerate(members):
                    zip_ref.extract(member, extract_to_folder)
                    extracted_count += 1
                    if (i + 1) % log_interval == 0 or (i + 1) == num_members:
                        print(f"[DIAG_EXTRACT] Extracted {extracted_count}/{num_members} members for {archive_name} ({(extracted_count/num_members*100):.2f}%)...")
            
            print(f"[DIAG_EXTRACT] Member-by-member extraction of {archive_name} complete. Extracted {extracted_count} members.")
            # extracted_files_count est maintenant extracted_count
            extracted_files_count = extracted_count
        
        # Vérification post-extraction
        if os.path.isdir(extract_to_folder):
            extracted_content = os.listdir(extract_to_folder)
            if extracted_content:
                print(f"[DIAG_EXTRACT] Destination folder '{extract_to_folder}' exists and is not empty after extraction. Contains {len(extracted_content)} top-level items.")
                # print(f"[DIAG_EXTRACT] Top-level items: {extracted_content[:10]}") # Aperçu du contenu
            else:
                print(f"[WARNING_EXTRACT] Destination folder '{extract_to_folder}' exists but is EMPTY after extraction of {archive_name}.")
        else:
            print(f"[ERROR_EXTRACT] Destination folder '{extract_to_folder}' DOES NOT EXIST after extraction attempt of {archive_name}.")
            return False # Clairement un échec si le dossier de destination n'est pas là

        # La conservation de l'archive est gérée par la logique d'appel (ne pas supprimer ici)
        print(f"[DEBUG_ROO] Reached end of _extract_zip. zip_path is: {zip_path}.")
        return True
    except zipfile.BadZipFile as e_badzip:
        print(f"[ERROR_EXTRACT] Failed to extract {archive_name}. File might be corrupted or not a valid ZIP file. Error: {e_badzip}")
        return False
    except PermissionError as e_perm:
        print(f"[ERROR_EXTRACT] Permission error during extraction of {archive_name} to {extract_to_folder}. Error: {e_perm}")
        return False
    except Exception as e:
        print(f"[ERROR_EXTRACT] An unexpected error occurred during extraction of {archive_name}. Error: {e}")
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(f"[ERROR_EXTRACT] Exception type: {exc_type}, File: {fname}, Line: {exc_tb.tb_lineno}")
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
        downloaded_archive_path, downloaded_this_run = _download_file(url, temp_download_dir, archive_name)
        
        if not downloaded_archive_path:
            print(f"[ERROR] Failed to download {tool_name}. Aborting setup for this tool.")
            return None

        extraction_successful = _extract_zip(downloaded_archive_path, tools_base_dir)

        if not extraction_successful and not downloaded_this_run:
            # L'extraction a échoué et nous avons utilisé une archive locale.
            print(f"[WARNING] Extraction failed for locally found archive: {downloaded_archive_path}. Deleting it and retrying download.")
            try:
                os.remove(downloaded_archive_path)
                print(f"[INFO] Deleted potentially corrupted local archive: {downloaded_archive_path}")
            except OSError as e:
                print(f"[ERROR] Failed to delete corrupted local archive {downloaded_archive_path}: {e}")
                return None # Ne pas continuer si la suppression échoue.

            # Retenter le téléchargement en forçant
            print(f"[INFO] Retrying download for {tool_name}...")
            downloaded_archive_path, downloaded_this_run = _download_file(url, temp_download_dir, archive_name, force_download=True)
            if not downloaded_archive_path:
                print(f"[ERROR] Failed to re-download {tool_name} after deleting local copy. Aborting setup.")
                return None
            
            print(f"[INFO] Retrying extraction for {tool_name} from newly downloaded archive...")
            extraction_successful = _extract_zip(downloaded_archive_path, tools_base_dir)

        if not extraction_successful:
            print(f"[ERROR_SETUP] Failed to extract {tool_name} (archive: {downloaded_archive_path}) even after potential retry. Aborting setup.")
            if os.path.isdir(tools_base_dir):
                print(f"[DIAG_SETUP] Contents of target base directory '{tools_base_dir}' after failed extraction:")
                try:
                    for item in os.listdir(tools_base_dir):
                        print(f"[DIAG_SETUP]  - {item}")
                except Exception as e_ls:
                    print(f"[DIAG_SETUP]    Could not list contents: {e_ls}")
            else:
                print(f"[DIAG_SETUP] Target base directory '{tools_base_dir}' does not exist or is not a directory.")
            return None
        
        # Après extraction réussie (potentiellement après nouvelle tentative)
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