import sys
import pathlib

# Ajout pour insérer le répertoire racine du projet dans sys.path
# Cela permet de s'assurer que le module 'argumentation_analysis' est trouvable
# __file__ est le chemin du script actuel (localize_source_contents.py)
# .parent est le répertoire 'scripts'
# .parent.parent est le répertoire racine du projet
PROJECT_ROOT_DIR_FOR_SCRIPT = pathlib.Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT_DIR_FOR_SCRIPT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT_DIR_FOR_SCRIPT))

import json
import logging
# pathlib est déjà importé ci-dessus
import shutil
import requests # Gardé pour l'instant, FetchService l'utilise en interne mais on pourrait le supprimer si plus d'appels directs

# Imports depuis argumentation_analysis
from argumentation_analysis.services.fetch_service import FetchService
from argumentation_analysis.services.cache_service import CacheService
from argumentation_analysis.utils.data_loader import load_results_from_json
from argumentation_analysis.paths import TEMP_DIR_FROM_PATHS, PROJECT_ROOT_DIR # PROJECT_ROOT_DIR pour CacheService si besoin

# Configuration du logging
def setup_logging():
    logging.basicConfig(
        level=logging.DEBUG, # Changé à DEBUG
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", # Ajout de %(name)s pour plus de détails
        handlers=[
            logging.StreamHandler(sys.stdout) # S'assurer que ça va vers stdout
        ],
        force=True # Assure que cette configuration est appliquée
    )

# Constantes de chemins
# Utilisation de TEMP_DIR_FROM_PATHS pour la cohérence
CONFIG_FILE_PATH = TEMP_DIR_FROM_PATHS / "reconstituted_config_base.json"
DEST_DIR_NAME = "downloaded_texts"
DEST_DIR = TEMP_DIR_FROM_PATHS / DEST_DIR_NAME
OUTPUT_CONFIG_FILE_PATH = TEMP_DIR_FROM_PATHS / "config_sources_localized.json"

# S'assurer que le répertoire _temp existe (sera fait par paths.py à l'import, mais redondance ici pour clarté)
TEMP_DIR_FROM_PATHS.mkdir(parents=True, exist_ok=True)


# Chemins sources spécifiques
ATTAL_SOURCE_ID = "assemblee_nationale_2024_pg_attal"
ATTAL_ORIGINAL_FILENAME = "Déclaration de politique générale Gabiel Attal 2024.txt"
ATTAL_SOURCE_PATH_ORIGINAL = pathlib.Path("argumentation_analysis/temp_downloads") / ATTAL_ORIGINAL_FILENAME
ATTAL_DEST_FILENAME = "discours_attal_20240130.txt"

RAPPORT_IA_SOURCE_ID = "rapport_ia_commission_2024"
RAPPORT_IA_ORIGINAL_FILENAME = "rapport_ia_2024.txt" # Supposé à la racine
RAPPORT_IA_SOURCE_PATH_ORIGINAL = pathlib.Path(RAPPORT_IA_ORIGINAL_FILENAME)
RAPPORT_IA_DEST_FILENAME = "rapport_ia_2024.txt"


def prepare_destination_directory(dir_path: pathlib.Path):
    """Prépare le répertoire de destination (le crée ou le vide)."""
    if dir_path.exists():
        logging.info(f"Le répertoire de destination '{dir_path}' existe. Vidage en cours...")
        try:
            shutil.rmtree(dir_path)
        except OSError as e:
            logging.exception(f"Erreur lors de la suppression du répertoire '{dir_path}'")
            raise
    try:
        dir_path.mkdir(parents=True, exist_ok=True)
        logging.info(f"Répertoire de destination '{dir_path}' créé/préparé.")
    except OSError as e:
        logging.exception(f"Erreur lors de la création du répertoire '{dir_path}'")
        raise

def save_updated_config(sources: list, output_file_path: pathlib.Path):
    """Sauvegarde la configuration mise à jour dans un fichier JSON."""
    try:
        output_file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file_path, 'w', encoding='utf-8') as f:
            json.dump(sources, f, indent=2, ensure_ascii=False)
        logging.info(f"Configuration mise à jour sauvegardée dans '{output_file_path}'.")
    except IOError as e:
        logging.exception(f"Erreur lors de la sauvegarde de la configuration dans '{output_file_path}'")
        raise

def get_destination_filename(source_id: str, url: str, fetch_method: str) -> str:
    """Détermine le nom du fichier de destination."""
    if fetch_method == "tika":
        if url and url.lower().endswith(".pdf"):
            return f"{source_id}.pdf"
        if url and ".pdf" in url.lower(): 
             return f"{source_id}.pdf"
    return f"{source_id}.txt"


def process_source(source: dict, dest_dir: pathlib.Path, fetch_service: FetchService):
    """Traite une source individuelle."""
    source_id = source.get("id")
    fetch_method = source.get("fetch_method")
    original_path_str = source.get("path") 

    logging.info(f"Traitement de la source ID: '{source_id}', fetch_method: '{fetch_method}'")

    if source_id == ATTAL_SOURCE_ID:
        dest_file = dest_dir / ATTAL_DEST_FILENAME
        try:
            if not ATTAL_SOURCE_PATH_ORIGINAL.exists():
                logging.error(f"Fichier source pour Attal '{ATTAL_SOURCE_PATH_ORIGINAL}' non trouvé.")
                return
            shutil.copy2(ATTAL_SOURCE_PATH_ORIGINAL, dest_file)
            source["fetch_method"] = "file"
            source["path"] = f"{DEST_DIR_NAME}/{ATTAL_DEST_FILENAME}"
            logging.info(f"Copié '{ATTAL_SOURCE_PATH_ORIGINAL}' vers '{dest_file}'. Mis à jour config pour ID '{source_id}'.")
        except Exception:
            logging.exception(f"Erreur lors de la copie du fichier pour Attal (ID '{source_id}')")
        return

    if source_id == RAPPORT_IA_SOURCE_ID:
        dest_file = dest_dir / RAPPORT_IA_DEST_FILENAME
        try:
            if not RAPPORT_IA_SOURCE_PATH_ORIGINAL.exists():
                logging.error(f"Fichier source pour Rapport IA '{RAPPORT_IA_SOURCE_PATH_ORIGINAL}' non trouvé à la racine du projet.")
                return
            shutil.copy2(RAPPORT_IA_SOURCE_PATH_ORIGINAL, dest_file)
            source["fetch_method"] = "file"
            source["path"] = f"{DEST_DIR_NAME}/{RAPPORT_IA_DEST_FILENAME}"
            logging.info(f"Copié '{RAPPORT_IA_SOURCE_PATH_ORIGINAL}' vers '{dest_file}'. Mis à jour config pour ID '{source_id}'.")
        except Exception:
            logging.exception(f"Erreur lors de la copie du fichier pour Rapport IA (ID '{source_id}')")
        return

    if fetch_method in ["jina", "tika", "direct_download"]:
        url = source.get("url") # Privilégier la clé "url" si elle existe

        # Logique de validation et de construction d'URL
        if url: # Si une URL est directement fournie
            if not (url.startswith("http://") or url.startswith("https://")):
                # L'URL n'a pas de schéma, essayons de le préfixer si source.schema existe
                schema_from_source = source.get("schema")
                if schema_from_source and schema_from_source in ["http", "https"]:
                    url = f"{schema_from_source}://{url}"
                    logging.info(f"URL pour source ID '{source_id}' préfixée avec schema: {url}")
                else:
                    # Pas de schéma valide dans la source non plus, ou URL toujours invalide
                    logging.error(f"URL invalide pour source ID '{source_id}': '{url}'. Schéma manquant ou invalide et non corrigeable via source.schema. Abandon.")
                    return
        else: # Pas d'URL directe, tenter de reconstruire
            logging.debug(f"Tentative de reconstruction d'URL pour source ID '{source_id}' avec schema: {source.get('schema')}, host_parts: {source.get('host_parts')}, path: {source.get('path')}")
            url = fetch_service.reconstruct_url(source.get("schema"), source.get("host_parts"), source.get("path"))
            logging.debug(f"URL reconstruite pour source ID '{source_id}': {url}")
        
        # Correction pour les URLs mal formées par reconstruct_url (manque de ':')
        if url and (url.startswith("http//") or url.startswith("https//")):
            original_malformed_url = url
            parts = url.split("//", 1)
            if len(parts) == 2:
                scheme = parts[0]
                rest = parts[1]
                url = f"{scheme}://{rest}"
                logging.info(f"URL corrigée pour ID '{source_id}': de '{original_malformed_url}' à '{url}'")


        if not url:
            logging.error(f"URL non construite ou non fournie pour la source ID '{source_id}'. Téléchargement annulé.")
            return
        
        # Vérification finale du schéma après reconstruction ou correction potentielle
        if not (url.startswith("http://") or url.startswith("https://")):
            logging.error(f"URL finale invalide pour source ID '{source_id}': '{url}'. Schéma manquant après toutes les tentatives. Abandon.")
            return

        dest_filename = get_destination_filename(source_id, url, fetch_method)
        dest_file_path = dest_dir / dest_filename
        
        logging.info(f"Tentative de récupération de '{url}' pour la source ID '{source_id}' via fetch_method '{fetch_method}'...")
        
        text_content: str | None = None
        binary_content: bytes | None = None

        try:
            if fetch_method == "jina":
                logging.debug(f"Avant appel de fetch_with_jina pour source ID '{source_id}' avec URL: {url}")
                text_content = fetch_service.fetch_with_jina(url)
                logging.debug(f"Après appel de fetch_with_jina pour source ID '{source_id}'. Contenu reçu: {'Oui' if text_content else 'Non'}")
            elif fetch_method == "tika":
                logging.debug(f"Avant appel de fetch_with_tika pour source ID '{source_id}' avec URL: {url}, fichier: {dest_filename}")
                text_content = fetch_service.fetch_with_tika(url=url, file_name=dest_filename)
                logging.debug(f"Après appel de fetch_with_tika pour source ID '{source_id}'. Contenu reçu: {'Oui' if text_content else 'Non'}")
                if text_content is None and dest_filename.endswith(".pdf"):
                    logging.warning(f"Tika n'a pas retourné de texte pour {url}. Le fichier PDF brut (si téléchargé par Tika) devrait être dans son cache.")
            elif fetch_method == "direct_download":
                is_pdf_url = url.lower().endswith(".pdf") or ".pdf" in url.lower()
                if is_pdf_url and not dest_filename.endswith(".pdf"): 
                    dest_filename = f"{source_id}.pdf"
                    dest_file_path = dest_dir / dest_filename
                
                if is_pdf_url: 
                    logging.info(f"Téléchargement binaire direct de PDF: {url}")
                    logging.debug(f"Avant appel requests.get pour PDF: {url}")
                    response = requests.get(url, timeout=60)
                    response.raise_for_status()
                    binary_content = response.content
                    logging.debug(f"Après appel requests.get pour PDF. Contenu binaire reçu: {'Oui' if binary_content else 'Non'}")
                else: 
                    logging.debug(f"Avant appel de fetch_direct_text pour source ID '{source_id}' avec URL: {url}")
                    text_content = fetch_service.fetch_direct_text(url)
                    logging.debug(f"Après appel de fetch_direct_text pour source ID '{source_id}'. Contenu reçu: {'Oui' if text_content else 'Non'}")

            if text_content is not None:
                with open(dest_file_path, 'w', encoding='utf-8') as f:
                    f.write(text_content)
                logging.info(f"Contenu texte de '{url}' sauvegardé dans '{dest_file_path}'.")
            elif binary_content is not None:
                with open(dest_file_path, 'wb') as f:
                    f.write(binary_content)
                logging.info(f"Contenu binaire de '{url}' sauvegardé dans '{dest_file_path}'.")
            else:
                logging.warning(f"Aucun contenu (texte ou binaire) n'a été récupéré pour '{url}' (ID '{source_id}').")
                return 

            source["fetch_method"] = "file"
            source["path"] = f"{DEST_DIR_NAME}/{dest_filename}"
            source.pop("schema", None)
            source.pop("host_parts", None)
            source.pop("url", None)

        except requests.exceptions.RequestException:
            logging.exception(f"Erreur de téléchargement (requests) pour '{url}' (ID '{source_id}')")
        except Exception:
            logging.exception(f"Erreur inattendue lors de la récupération via FetchService ou traitement pour '{url}' (ID '{source_id}')")
        return

    if fetch_method == "file":
        if not original_path_str:
            logging.warning(f"Source ID '{source_id}' est 'file' mais n'a pas de 'path' défini. Ignoré.")
            return

        original_file_path = pathlib.Path(original_path_str)
        
        is_already_in_dest_dir_format = original_file_path.parts[0] == DEST_DIR_NAME if original_file_path.parts else False

        if is_already_in_dest_dir_format:
            if (TEMP_DIR_FROM_PATHS / original_file_path).exists():
                 logging.info(f"Source ID '{source_id}' est 'file' et son chemin '{original_path_str}' semble correct et le fichier existe. Aucune action.")
                 return 
            else:
                logging.warning(f"Source ID '{source_id}' a le chemin '{original_path_str}' qui semble correct, mais le fichier '{TEMP_DIR_FROM_PATHS / original_file_path}' n'existe pas. Aucune copie ne sera tentée.")
                return

        source_file_to_copy = original_file_path 
        
        if not source_file_to_copy.exists():
            if not source_file_to_copy.is_absolute():
                potential_path_project_root = PROJECT_ROOT_DIR / source_file_to_copy
                if potential_path_project_root.exists():
                    source_file_to_copy = potential_path_project_root
                    logging.info(f"Fichier source '{original_path_str}' trouvé à la racine du projet: {source_file_to_copy}")
                else:
                    logging.warning(f"Source ID '{source_id}' est 'file', chemin '{original_path_str}', mais le fichier source '{source_file_to_copy.resolve()}' et '{potential_path_project_root.resolve()}' n'existent pas. Copie annulée.")
                    return
            else:
                logging.warning(f"Source ID '{source_id}' est 'file', chemin '{original_path_str}', mais le fichier source '{source_file_to_copy.resolve()}' n'existe pas. Copie annulée.")
                return

        final_filename_in_dest = source_file_to_copy.name
        dest_file_path_to_copy = dest_dir / final_filename_in_dest

        try:
            shutil.copy2(source_file_to_copy, dest_file_path_to_copy)
            new_path_in_config = f"{DEST_DIR_NAME}/{final_filename_in_dest}"
            logging.info(f"Copié '{source_file_to_copy}' vers '{dest_file_path_to_copy}'. Mis à jour path pour ID '{source_id}' vers '{new_path_in_config}'.")
            source["path"] = new_path_in_config
        except Exception:
            logging.exception(f"Erreur lors de la copie du fichier '{source_file_to_copy}' vers '{dest_file_path_to_copy}' pour ID '{source_id}'")
        return
    
    logging.warning(f"Fetch_method '{fetch_method}' non reconnu pour la source ID '{source_id}'.")


def main():
    """Fonction principale du script."""
    setup_logging()
    
    # Test log
    logging.debug("Logging DEBUG configuré.")
    logging.info("Logging INFO configuré.")

    cache_base_dir = TEMP_DIR_FROM_PATHS / "services_cache"
    text_cache_dir = cache_base_dir / "text_cache"
    raw_files_cache_dir = cache_base_dir / "raw_files_tika" 
    
    try:
        text_cache_dir.mkdir(parents=True, exist_ok=True)
        raw_files_cache_dir.mkdir(parents=True, exist_ok=True)
        logging.info(f"Répertoires de cache préparés: {text_cache_dir}, {raw_files_cache_dir}")
    except Exception:
        logging.critical(f"Impossible de créer les répertoires de cache. Arrêt du script.", exc_info=True)
        return

    cache_service = CacheService(cache_dir=text_cache_dir)
    fetch_service = FetchService(cache_service=cache_service, temp_download_dir=raw_files_cache_dir)
    
    logging.info("Services CacheService et FetchService initialisés.")

    try:
        sources = load_results_from_json(CONFIG_FILE_PATH)
        if not sources: 
             logging.critical("Impossible de charger la configuration initiale ou fichier vide. Arrêt du script.")
             return
    except Exception: 
        logging.critical(f"Erreur critique lors du chargement de la configuration. Arrêt du script.", exc_info=True)
        return

    try:
        prepare_destination_directory(DEST_DIR)
    except Exception:
        logging.critical(f"Impossible de préparer le répertoire de destination '{DEST_DIR}'. Arrêt du script.", exc_info=True)
        return

    if not isinstance(sources, list): 
        logging.critical("La configuration chargée n'est pas une liste valide. Arrêt du script.")
        return

    processed_sources = []
    for source_obj in sources:
        if not isinstance(source_obj, dict):
            logging.warning(f"Élément de configuration non dictionnaire ignoré: {source_obj}")
            processed_sources.append(source_obj) # Conserver l'élément original si ce n'est pas un dict
            continue
        
        current_source_copy = source_obj.copy() # Travailler sur une copie
        try:
            process_source(current_source_copy, DEST_DIR, fetch_service)
        except Exception:
            logging.exception(f"Erreur non interceptée lors du traitement de la source ID '{current_source_copy.get('id', 'ID_INCONNU')}'")
            # Conserver la source originale (non modifiée) en cas d'erreur grave dans process_source
            # pour ne pas perdre l'entrée dans la config de sortie.
            # Les modifications partielles dans current_source_copy avant l'erreur seront perdues,
            # ce qui est préférable à une config de sortie corrompue ou incomplète.
            processed_sources.append(source_obj) 
            continue

        processed_sources.append(current_source_copy)
    
    try:
        save_updated_config(processed_sources, OUTPUT_CONFIG_FILE_PATH)
    except Exception:
        logging.critical("Impossible de sauvegarder la configuration mise à jour. Les modifications pourraient être perdues.", exc_info=True)

    logging.info("Script terminé.")

if __name__ == "__main__":
    main()