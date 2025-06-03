# ui/utils.py
"""
Utilitaires pour l'interface utilisateur (UI) de l'analyse d'argumentation.

Ce module regroupe diverses fonctions d'assistance utilisées par les composants
de l'interface utilisateur, telles que la reconstruction d'URL, la gestion
d'un cache de fichiers simple, la récupération de contenu textuel depuis
différentes sources (direct, Jina, Tika), et la vérification des
définitions d'extraits.
"""
import requests
import json
import gzip
import hashlib
import logging
import base64 # NOUVEAU: Pour décoder la clé avant de l'utiliser avec Fernet
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
# cryptography.fernet et exceptions sont maintenant gérés dans project_core.utils.crypto_utils
# from cryptography.fernet import Fernet, InvalidToken # SUPPRIMÉ
# from cryptography.exceptions import InvalidSignature # SUPPRIMÉ

# Import config depuis le même package ui
from . import config as ui_config

utils_logger = logging.getLogger("App.UI.Utils")
if not utils_logger.handlers and not utils_logger.propagate:
     handler = logging.StreamHandler(); formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s', datefmt='%H:%M:%S'); handler.setFormatter(formatter); utils_logger.addHandler(handler); utils_logger.setLevel(logging.INFO)

# Import des fonctions de chiffrement déplacées
from project_core.utils.crypto_utils import encrypt_data_with_fernet, decrypt_data_with_fernet

# --- Fonctions Utilitaires (Cache, Crypto, Fetch, Verify) ---

def reconstruct_url(schema: str, host_parts: List[str], path: Optional[str]) -> Optional[str]:
    """Reconstruit une URL complète à partir de ses composants.

    :param schema: Le schéma de l'URL (par exemple, "http", "https").
    :type schema: str
    :param host_parts: Une liste des parties composant le nom d'hôte.
    :type host_parts: List[str]
    :param path: Le chemin de la ressource sur le serveur. Peut être None ou vide.
    :type path: Optional[str]
    :return: L'URL reconstruite, ou None si `schema` ou `host_parts` sont invalides.
    :rtype: Optional[str]
    """
    if not schema or not host_parts: return None
    host = ".".join(part for part in host_parts if part)
    current_path = path if path is not None else ""
    current_path = current_path if current_path.startswith('/') or not current_path else '/' + current_path
    if not current_path:
        current_path = "/"
    return f"{schema}://{host}{current_path}"

def get_cache_filepath(url: str) -> Path:
    """Génère le chemin du fichier cache pour une URL donnée.

    Le nom du fichier est un hachage SHA256 de l'URL, stocké dans `ui_config.CACHE_DIR`.

    :param url: L'URL pour laquelle générer le chemin du fichier cache.
    :type url: str
    :return: Le chemin (objet Path) vers le fichier cache.
    :rtype: Path
    """
    url_hash = hashlib.sha256(url.encode()).hexdigest()
    return ui_config.CACHE_DIR / f"{url_hash}.txt"

def load_from_cache(url: str) -> Optional[str]:
    """Charge le contenu textuel depuis le cache fichier si disponible pour une URL donnée.

    :param url: L'URL à rechercher dans le cache.
    :type url: str
    :return: Le contenu textuel en tant que chaîne si trouvé, sinon None.
    :rtype: Optional[str]
    """
    filepath = get_cache_filepath(url)
    if filepath.exists():
        try:
            utils_logger.info(f"   -> Lecture depuis cache : {filepath.name}")
            return filepath.read_text(encoding='utf-8')
        except Exception as e:
            utils_logger.warning(f"   -> Erreur lecture cache {filepath.name}: {e}")
            return None
    utils_logger.debug(f"Cache miss pour URL: {url}")
    return None

def save_to_cache(url: str, text: str) -> None:
    """Sauvegarde le contenu textuel dans le cache fichier pour une URL donnée.

    Ne fait rien si le texte est vide. Crée le répertoire de cache si nécessaire.

    :param url: L'URL associée au contenu.
    :type url: str
    :param text: Le contenu textuel à sauvegarder.
    :type text: str
    :return: None
    :rtype: None
    """
    if not text:
        utils_logger.info("   -> Texte vide, non sauvegardé.")
        return
    filepath = get_cache_filepath(url)
    try:
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(text, encoding='utf-8')
        utils_logger.info(f"   -> Texte sauvegardé : {filepath.name}")
    except Exception as e:
        utils_logger.error(f"   -> Erreur sauvegarde cache {filepath.name}: {e}")

# Les fonctions encrypt_data et decrypt_data ont été déplacées vers project_core.utils.crypto_utils
# et renommées en encrypt_data_with_fernet et decrypt_data_with_fernet.
# Les appels dans file_operations.py devront être mis à jour.

# Les fonctions load_extract_definitions et save_extract_definitions ont été déplacées
# vers argumentation_analysis/ui/file_operations.py pour éviter les imports circulaires.

def fetch_direct_text(source_url: str, timeout: int = 60) -> Optional[str]:
    """Récupère le contenu texte brut d'une URL par téléchargement direct.

    Utilise le cache fichier (`load_from_cache`, `save_to_cache`).

    :param source_url: L'URL à partir de laquelle récupérer le texte.
    :type source_url: str
    :param timeout: Le délai d'attente en secondes pour la requête HTTP.
    :type timeout: int
    :return: Le contenu textuel de la réponse, ou None en cas d'erreur.
    :rtype: Optional[str]
    :raises ConnectionError: Si une erreur de requête HTTP survient.
    """
    cached_text = load_from_cache(source_url)
    if cached_text is not None: return cached_text
    utils_logger.info(f"-> Téléchargement direct depuis : {source_url}...")
    headers = {'User-Agent': 'ArgumentAnalysisApp/1.0'}
    try:
        response = requests.get(source_url, headers=headers, timeout=timeout)
        response.raise_for_status()
        texte_brut = response.content.decode('utf-8', errors='ignore')
        utils_logger.info(f"   -> Contenu direct récupéré (longueur {len(texte_brut)}).")
        save_to_cache(source_url, texte_brut)
        return texte_brut
    except requests.exceptions.RequestException as e:
        utils_logger.error(f"Erreur téléchargement direct ({source_url}): {e}")
        raise ConnectionError(f"Erreur téléchargement direct ({source_url}): {e}") from e

def fetch_with_jina(
    source_url: str,
    timeout: int = 90,
    jina_reader_prefix_override: Optional[str] = None
) -> Optional[str]:
    """Récupère et extrait le contenu textuel d'une URL via le service Jina Reader.

    Utilise le cache fichier. Le préfixe Jina peut être surchargé.

    :param source_url: L'URL originale à traiter.
    :type source_url: str
    :param timeout: Le délai d'attente pour la requête HTTP vers Jina.
    :type timeout: int
    :param jina_reader_prefix_override: Préfixe optionnel pour surcharger celui de `ui_config`.
    :type jina_reader_prefix_override: Optional[str]
    :return: Le contenu textuel extrait (potentiellement Markdown), ou None en cas d'erreur.
    :rtype: Optional[str]
    :raises ConnectionError: Si une erreur de requête HTTP survient avec Jina.
    """
    cached_text = load_from_cache(source_url)
    if cached_text is not None: return cached_text

    _jina_reader_prefix = jina_reader_prefix_override if jina_reader_prefix_override is not None else ui_config.JINA_READER_PREFIX
    jina_url = f"{_jina_reader_prefix}{source_url}"

    utils_logger.info(f"-> Récupération via Jina : {jina_url}...")
    headers = {'Accept': 'text/markdown', 'User-Agent': 'ArgumentAnalysisApp/1.0'}
    try:
        response = requests.get(jina_url, headers=headers, timeout=timeout)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        utils_logger.error(f"Erreur Jina ({jina_url}): {e}")
        raise ConnectionError(f"Erreur Jina ({jina_url}): {e}") from e
    content = response.text
    md_start_marker = "Markdown Content:"
    md_start_index = content.find(md_start_marker)
    texte_brut = content[md_start_index + len(md_start_marker):].strip() if md_start_index != -1 else content
    utils_logger.info(f"   -> Contenu Jina récupéré (longueur {len(texte_brut)}).")
    save_to_cache(source_url, texte_brut)
    return texte_brut
def fetch_with_tika(
    source_url: Optional[str] = None,
    file_content: Optional[bytes] = None,
    file_name: str = "fichier",
    raw_file_cache_path: Optional[Union[Path, str]] = None,
    timeout_dl: int = 60,
    timeout_tika: int = 600,
    tika_server_url_override: Optional[str] = None,
    plaintext_extensions_override: Optional[List[str]] = None,
    temp_download_dir_override: Optional[Path] = None
    ) -> Optional[str]:
    """Traite une source (URL ou contenu binaire) via un serveur Apache Tika.

    Gère le cache du texte extrait et optionnellement un cache pour le fichier brut téléchargé.
    Tente un fetch direct pour les types de fichiers texte simple reconnus.

    :param source_url: URL optionnelle du fichier à traiter.
    :type source_url: Optional[str]
    :param file_content: Contenu binaire optionnel du fichier.
    :type file_content: Optional[bytes]
    :param file_name: Nom du fichier (utilisé si `file_content` est fourni).
    :type file_name: str
    :param raw_file_cache_path: Chemin optionnel pour le cache du fichier brut.
    :type raw_file_cache_path: Optional[Union[Path, str]]
    :param timeout_dl: Timeout pour le téléchargement si `source_url` est utilisé.
    :type timeout_dl: int
    :param timeout_tika: Timeout pour la requête au serveur Tika.
    :type timeout_tika: int
    :param tika_server_url_override: URL optionnelle pour surcharger celle de `ui_config`.
    :type tika_server_url_override: Optional[str]
    :param plaintext_extensions_override: Liste optionnelle pour surcharger celles de `ui_config`.
    :type plaintext_extensions_override: Optional[List[str]]
    :param temp_download_dir_override: Chemin optionnel pour surcharger celui de `ui_config`.
    :type temp_download_dir_override: Optional[Path]
    :return: Le texte extrait par Tika, ou une chaîne vide si Tika ne retourne rien,
             ou None en cas d'erreur majeure.
    :rtype: Optional[str]
    :raises ValueError: Si ni `source_url` ni `file_content` ne sont fournis.
    :raises ConnectionError: Si une erreur de téléchargement ou de communication Tika survient.
    """
    _tika_server_url = tika_server_url_override if tika_server_url_override is not None else ui_config.TIKA_SERVER_URL
    _plaintext_extensions = plaintext_extensions_override if plaintext_extensions_override is not None else ui_config.PLAINTEXT_EXTENSIONS
    _temp_download_dir = temp_download_dir_override if temp_download_dir_override is not None else ui_config.TEMP_DOWNLOAD_DIR

    cache_key = source_url if source_url else f"file://{file_name}"
    cached_text = load_from_cache(cache_key)
    if cached_text is not None: return cached_text

    content_to_send = None
    
    # --- LOGS DÉTAILLÉS (depuis origin/main) ---
    processing_target_log = ""
    if source_url:
        processing_target_log = f"URL: {source_url}"
        if source_url.startswith("file://"):
            local_file_path = Path(source_url[7:])
            processing_target_log += f" (Chemin local interprété: {local_file_path})"
            # Exemple pour PDF, à adapter/généraliser si besoin pour d'autres types gérés par Tika localement
            if local_file_path.suffix.lower() == ".pdf": 
                 utils_logger.info(f"  [Tika Log] Traitement du fichier PDF local: {local_file_path}")
    elif file_content:
        processing_target_log = f"Fichier fourni: {file_name} (taille: {len(file_content)} bytes)"
        if file_name.lower().endswith(".pdf"): # Exemple pour PDF
            utils_logger.info(f"  [Tika Log] Traitement du contenu PDF fourni pour: {file_name}")
    utils_logger.info(f"  [Tika Log] Début fetch_with_tika pour: {processing_target_log}")
    # --- FIN LOGS DÉTAILLÉS ---

    if source_url:
        original_filename = Path(source_url).name
        if any(source_url.lower().endswith(ext) for ext in _plaintext_extensions):
            utils_logger.info(f"   -> URL détectée comme texte simple ({source_url}). Fetch direct.")
            return fetch_direct_text(source_url)

        url_hash = hashlib.sha256(source_url.encode()).hexdigest()
        file_extension = Path(original_filename).suffix if Path(original_filename).suffix else ".download"
        effective_raw_cache_path = Path(raw_file_cache_path) if raw_file_cache_path else _temp_download_dir / f"{url_hash}{file_extension}"
        
        if source_url.startswith("file://"):
            local_path_from_url = Path(source_url[7:])
            if local_path_from_url.exists() and local_path_from_url.is_file():
                utils_logger.info(f"   -> Lecture directe du fichier local (via file:// URL): {local_path_from_url}")
                try:
                    content_to_send = local_path_from_url.read_bytes()
                except Exception as e_read_local_file:
                    utils_logger.error(f"   -> Erreur lecture fichier local {local_path_from_url}: {e_read_local_file}. Tentative de téléchargement si c'est aussi une URL HTTP(S)...")
            else:
                utils_logger.warning(f"   -> Fichier local spécifié via file:// URL non trouvé ou n'est pas un fichier: {local_path_from_url}")

        if content_to_send is None and not source_url.startswith("file://"): 
            if effective_raw_cache_path.exists() and effective_raw_cache_path.stat().st_size > 0:
                 try:
                    utils_logger.info(f"   -> Lecture fichier brut depuis cache local : {effective_raw_cache_path.name}")
                    content_to_send = effective_raw_cache_path.read_bytes()
                 except Exception as e_read_raw:
                    utils_logger.warning(f"   -> Erreur lecture cache brut {effective_raw_cache_path.name}: {e_read_raw}. Re-téléchargement...")
                    content_to_send = None 
            if content_to_send is None: 
                 utils_logger.info(f"-> Téléchargement (pour Tika) depuis : {source_url}...")
                 try:
                     response_dl = requests.get(source_url, stream=True, timeout=timeout_dl)
                     response_dl.raise_for_status()
                     content_to_send = response_dl.content
                     utils_logger.info(f"   -> Doc téléchargé ({len(content_to_send)} bytes).")
                     try:
                         effective_raw_cache_path.parent.mkdir(parents=True, exist_ok=True)
                         effective_raw_cache_path.write_bytes(content_to_send)
                         utils_logger.info(f"   -> Doc brut sauvegardé: {effective_raw_cache_path.resolve()}")
                     except Exception as e_save:
                         utils_logger.error(f"   -> Erreur sauvegarde brut: {e_save}")
                 except requests.exceptions.RequestException as e:
                     utils_logger.error(f"Erreur téléchargement {source_url}: {e}")
                     raise ConnectionError(f"Erreur téléchargement {source_url}: {e}") from e

    elif file_content:
        utils_logger.info(f"-> Utilisation contenu fichier '{file_name}' ({len(file_content)} bytes)...")
        content_to_send = file_content
        if any(file_name.lower().endswith(ext) for ext in _plaintext_extensions):
            utils_logger.info("   -> Fichier uploadé détecté comme texte simple. Lecture directe.")
            try:
                texte_brut = file_content.decode('utf-8', errors='ignore')
                save_to_cache(cache_key, texte_brut)
                return texte_brut
            except Exception as e_decode:
                utils_logger.warning(f"   -> Erreur décodage fichier texte '{file_name}': {e_decode}. Tentative avec Tika...")
    else:
        raise ValueError("fetch_with_tika: Il faut soit source_url soit file_content.")

    if not content_to_send:
        utils_logger.warning("   -> Contenu brut vide ou non récupéré. Impossible d'envoyer à Tika.")
        save_to_cache(cache_key, "") 
        return ""

    utils_logger.info(f"  [Tika Log] Envoi du contenu à Tika. URL Tika: {_tika_server_url}, Taille contenu: {len(content_to_send)} bytes, Timeout Tika: {timeout_tika}s")
    headers = { 'Accept': 'text/plain', 'Content-Type': 'application/octet-stream', 'X-Tika-OCRLanguage': 'fra+eng' }
    texte_brut_tika = "" 
    try:
        response_tika = requests.put(_tika_server_url, data=content_to_send, headers=headers, timeout=timeout_tika)
        utils_logger.info(f"  [Tika Log] Réponse de Tika reçue. Statut: {response_tika.status_code}")
        response_tika.raise_for_status() 
        texte_brut_tika = response_tika.text
        if not texte_brut_tika:
            utils_logger.warning(f"  [Tika Log] Tika a retourné un statut {response_tika.status_code} mais le texte est vide.")
        else:
            utils_logger.info(f"  [Tika Log] Texte extrait par Tika. Longueur: {len(texte_brut_tika)}.")
            utils_logger.debug(f"  [Tika Log] Extrait Tika (premiers 200 chars): {texte_brut_tika[:200]}")
        save_to_cache(cache_key, texte_brut_tika)
        return texte_brut_tika
    except requests.exceptions.Timeout:
        utils_logger.error(f"  [Tika Log] ❌ Timeout Tika ({timeout_tika}s) pour {processing_target_log}.")
        raise ConnectionError(f"Timeout Tika pour {processing_target_log}")
    except requests.exceptions.HTTPError as e_http:
        utils_logger.error(f"  [Tika Log] ❌ Erreur HTTP de Tika: {e_http}. Réponse: {e_http.response.text[:500] if e_http.response else 'Pas de réponse textuelle'}")
        save_to_cache(cache_key, "")
        raise ConnectionError(f"Erreur HTTP Tika: {e_http}") from e_http
    except requests.exceptions.RequestException as e_req:
        utils_logger.error(f"  [Tika Log] ❌ Erreur de requête Tika: {e_req}")
        save_to_cache(cache_key, "")
        raise ConnectionError(f"Erreur de requête Tika: {e_req}") from e_req
    except Exception as e_generic:
        utils_logger.error(f"  [Tika Log] ❌ Erreur inattendue pendant le traitement Tika: {e_generic}", exc_info=True)
        save_to_cache(cache_key, "") 
        raise ConnectionError(f"Erreur inattendue Tika: {e_generic}") from e_generic
def get_full_text_for_source(source_info: Dict[str, Any], app_config: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """
    Récupère le texte complet pour une source donnée, en utilisant le cache et les configurations appropriées.

    Centralise la logique de récupération de texte en utilisant `fetch_direct_text`,
    `fetch_with_jina`, ou `fetch_with_tika` en fonction de `source_info`.
    Gère également la lecture de fichiers locaux si `fetch_method` est "file" (logique de HEAD)
    ou si source_type est "tika" avec un chemin local (logique de origin/main).

    :param source_info: Dictionnaire contenant les informations de la source.
                        Doit contenir des clés comme "source_type", et optionnellement
                        "schema", "host_parts", "path", "fetch_method", ou "url".
    :type source_info: Dict[str, Any]
    :param app_config: Dictionnaire optionnel de configuration de l'application,
                       utilisé pour surcharger les configurations globales de Jina, Tika, etc.
    :type app_config: Optional[Dict[str, Any]]
    :return: Le texte complet de la source (str), ou None en cas d'erreur de récupération
             ou si l'URL/chemin est invalide.
    :rtype: Optional[str]
    """
    source_name_for_log = source_info.get('source_name', source_info.get('id', 'Source inconnue'))
    utils_logger.debug(f"get_full_text_for_source appelée pour: {source_name_for_log}")

    fetch_method = source_info.get("fetch_method", source_info.get("source_type"))
    source_type_original = source_info.get("source_type") 

    if fetch_method == "file":
        file_path_str = source_info.get("path")
        if not file_path_str:
            utils_logger.error(f"Champ 'path' manquant pour la source locale (fetch_method='file'): {source_name_for_log}")
            return None
        
        absolute_file_path = Path(file_path_str).resolve()
        utils_logger.info(f"Tentative de lecture du fichier local (fetch_method='file'): {absolute_file_path}")
        if absolute_file_path.exists() and absolute_file_path.is_file():
            try:
                text_content = absolute_file_path.read_text(encoding='utf-8')
                utils_logger.info(f"Contenu du fichier local '{absolute_file_path.name}' lu avec succès (longueur: {len(text_content)}).")
                return text_content
            except Exception as e:
                utils_logger.error(f"Erreur lors de la lecture du fichier local '{absolute_file_path}': {e}")
                return None
        else:
            utils_logger.error(f"Fichier local non trouvé ou n'est pas un fichier: {absolute_file_path}")
            return None

    target_url = source_info.get("url")
    if not target_url:
        utils_logger.debug(f"Champ 'url' non trouvé pour {source_name_for_log}, évaluation pour reconstruction.")
        if source_type_original == "tika" and source_info.get("path") and not source_info.get("schema") and not source_info.get("host_parts"):
            source_path_str_tika = source_info.get("path")
            utils_logger.debug(f"Source Tika avec path local détectée: {source_path_str_tika} pour '{source_name_for_log}'")
            local_file_path_tika = Path(source_path_str_tika)
            if not local_file_path_tika.is_absolute():
                if hasattr(ui_config, 'PROJECT_ROOT') and isinstance(ui_config.PROJECT_ROOT, Path):
                    local_file_path_tika = (ui_config.PROJECT_ROOT / local_file_path_tika).resolve()
                    utils_logger.debug(f"Chemin Tika local résolu avec PROJECT_ROOT: {local_file_path_tika}")
                else:
                    utils_logger.warning(f"ui_config.PROJECT_ROOT non dispo. Résolution de '{source_path_str_tika}' vs CWD.")
                    local_file_path_tika = (Path.cwd() / local_file_path_tika).resolve()
            
            if local_file_path_tika.exists() and local_file_path_tika.is_file():
                target_url = local_file_path_tika.as_uri()
                utils_logger.info(f"Source Tika locale: Utilisation de l'URI '{target_url}' pour '{source_name_for_log}'.")
            else:
                utils_logger.error(f"Fichier Tika local non trouvé: {local_file_path_tika} (path original: '{source_path_str_tika}')")
        
        if not target_url: 
            utils_logger.debug(f"Tentative de reconstruction d'URL standard pour {source_name_for_log}.")
            target_url = reconstruct_url(
                source_info.get("schema"), source_info.get("host_parts", []), source_info.get("path")
            )
    else:
        utils_logger.debug(f"URL explicite utilisée pour {source_name_for_log}: {target_url}")
            
    if not target_url:
        utils_logger.error(f"URL non disponible ou invalide pour source: {source_name_for_log} (fetch_method: {fetch_method}, type: {source_type_original}).")
        return None
    
    utils_logger.debug(f"URL cible déterminée pour {source_name_for_log}: {target_url}")

    cached_text = load_from_cache(target_url)
    if cached_text is not None:
        utils_logger.info(f"Texte chargé depuis cache fichier pour URL '{target_url}' ({source_name_for_log})")
        if source_name_for_log == "Source_1": 
            utils_logger.info(f"--- LOGGING SPÉCIFIQUE POUR Source_1 (depuis cache) ---")
            utils_logger.info(f"Full text length: {len(cached_text)}")
            utils_logger.info(f"Premiers 500 chars:\n{cached_text[:500]}")
            utils_logger.info(f"Derniers 500 chars:\n{cached_text[-500:]}")
            utils_logger.info(f"--- FIN LOGGING SPÉCIFIQUE POUR Source_1 ---")
        return cached_text

    jina_prefix_val = ui_config.JINA_READER_PREFIX
    tika_server_url_val = ui_config.TIKA_SERVER_URL
    plaintext_extensions_val = ui_config.PLAINTEXT_EXTENSIONS
    temp_download_dir_val = ui_config.TEMP_DOWNLOAD_DIR

    if app_config:
        jina_prefix_val = app_config.get('JINA_READER_PREFIX', jina_prefix_val)
        tika_server_url_val = app_config.get('TIKA_SERVER_URL', tika_server_url_val)
        plaintext_extensions_val = app_config.get('PLAINTEXT_EXTENSIONS', plaintext_extensions_val)
        temp_download_dir_str_or_path = app_config.get('TEMP_DOWNLOAD_DIR')
        if temp_download_dir_str_or_path is not None:
            temp_download_dir_val = Path(temp_download_dir_str_or_path)

    utils_logger.info(f"Cache texte absent pour '{target_url}' ({source_name_for_log}). Récupération (méthode: {fetch_method}, type original: {source_type_original})...")
    texte_brut_source: Optional[str] = None
    try:
        effective_fetch_type = fetch_method if fetch_method else source_type_original

        if effective_fetch_type == "jina":
            texte_brut_source = fetch_with_jina(
                target_url,
                jina_reader_prefix_override=jina_prefix_val
            )
        elif effective_fetch_type == "tika":
            texte_brut_source = fetch_with_tika(
                source_url=target_url, 
                tika_server_url_override=tika_server_url_val,
                plaintext_extensions_override=plaintext_extensions_val,
                temp_download_dir_override=temp_download_dir_val
            )
        elif effective_fetch_type == "direct_download":
            texte_brut_source = fetch_direct_text(target_url)
        elif source_type_original == "web": 
             utils_logger.info(f"Fallback pour source_type 'web' vers fetch_with_jina pour {target_url}")
             texte_brut_source = fetch_with_jina(target_url, jina_reader_prefix_override=jina_prefix_val)
        elif source_type_original == "pdf": 
             utils_logger.info(f"Fallback pour source_type 'pdf' vers fetch_with_tika pour {target_url}")
             texte_brut_source = fetch_with_tika(source_url=target_url, tika_server_url_override=tika_server_url_val, plaintext_extensions_override=plaintext_extensions_val, temp_download_dir_override=temp_download_dir_val)
        else:
            utils_logger.warning(f"Méthode de fetch/type de source inconnu ou non géré: '{effective_fetch_type}' / '{source_type_original}' pour '{target_url}' ({source_name_for_log}).")
            return None

        if texte_brut_source is not None:
            utils_logger.info(f"Texte récupéré pour '{target_url}' ({source_name_for_log}), sauvegarde dans le cache...")
            save_to_cache(target_url, texte_brut_source)
        else:
            utils_logger.warning(f"Aucun texte brut retourné par la fonction fetch pour '{target_url}' ({source_name_for_log}).")

        if source_name_for_log == "Source_1" and texte_brut_source is not None: 
            utils_logger.info(f"--- LOGGING SPÉCIFIQUE POUR Source_1 (après fetch) ---")
            utils_logger.info(f"Full text length: {len(texte_brut_source)}")
            utils_logger.info(f"Premiers 500 chars:\n{texte_brut_source[:500]}")
            utils_logger.info(f"Derniers 500 chars:\n{texte_brut_source[-500:]}")
            utils_logger.info(f"--- FIN LOGGING SPÉCIFIQUE POUR Source_1 ---")
        
        return texte_brut_source

    except ConnectionError as e:
        utils_logger.error(f"Erreur de connexion lors de la récupération de '{target_url}' ({source_name_for_log}, méthode: {fetch_method}): {e}")
        return None
    except Exception as e:
        utils_logger.error(f"Erreur inattendue lors de la récupération de '{target_url}' ({source_name_for_log}, méthode: {fetch_method}): {e}", exc_info=True)
        return None
def verify_extract_definitions(definitions_list: List[Dict[str, Any]]) -> str:
    """Vérifie la présence des marqueurs de début et de fin pour chaque extrait défini.

    Pour chaque source dans `definitions_list`, récupère le texte complet (en utilisant
    le cache ou les fonctions fetch), puis vérifie si les `start_marker` et `end_marker`
    de chaque extrait sont présents dans le texte source.

    :param definitions_list: Une liste de dictionnaires, chaque dictionnaire
                             représentant une définition de source avec ses extraits.
    :type definitions_list: List[Dict[str, Any]]
    :return: Une chaîne HTML résumant les résultats de la vérification, indiquant
             le nombre d'erreurs et listant les problèmes spécifiques.
    :rtype: str
    """
    utils_logger.info("\n🔬 Lancement de la vérification des marqueurs d'extraits...")
    results = []
    total_checks = 0
    total_errors = 0

    if not definitions_list or definitions_list == ui_config.DEFAULT_EXTRACT_SOURCES:
        return "Aucune définition valide à vérifier."

    for source_idx, source_info in enumerate(definitions_list):
        source_name = source_info.get("source_name", f"Source Inconnue #{source_idx+1}")
        utils_logger.info(f"\n--- Vérification Source: '{source_name}' ---")
        # source_errors = 0 # Non utilisé
        # source_checks = 0 # Non utilisé
        texte_brut_source = None

        try:
            # Utiliser get_full_text_for_source pour centraliser la récupération de texte
            texte_brut_source = get_full_text_for_source(source_info)

            if texte_brut_source is not None:
                utils_logger.info(f"   -> Texte complet récupéré pour '{source_name}' (longueur: {len(texte_brut_source)}). Vérification des extraits...")
                extracts = source_info.get("extracts", [])
                if not extracts: utils_logger.info("      -> Aucun extrait défini.")

                for extract_idx, extract_info in enumerate(extracts):
                    extract_name = extract_info.get("extract_name", f"Extrait #{extract_idx+1}")
                    start_marker = extract_info.get("start_marker")
                    end_marker = extract_info.get("end_marker")

                    is_target_extract = source_name == "Source_1" and extract_name == "1. DAcbat Complet (Ottawa, 1858)"

                    if is_target_extract:
                        utils_logger.info(f"[LOGGING DIAGNOSTIC POUR {source_name} -> {extract_name}]")
                        utils_logger.info(f"  extract_name: {extract_name}")
                        utils_logger.info(f"  start_marker (reçu): '{start_marker}'")
                        utils_logger.info(f"  end_marker (reçu): '{end_marker}'")

                    current_start_index = -1 
                    current_end_index = -1   

                    if start_marker: # Assurer que start_marker n'est pas None ou vide
                        actual_start_marker_log = start_marker
                        if is_target_extract:
                            utils_logger.info(f"  AVANT RECHERCHE start_marker:")
                            utils_logger.info(f"    actual_start_marker: '{actual_start_marker_log}'")
                            approx_start_pos = texte_brut_source.find(actual_start_marker_log)
                            if approx_start_pos != -1:
                                context_window = 200 
                                start_slice = max(0, approx_start_pos - context_window)
                                end_slice = approx_start_pos + len(actual_start_marker_log) + context_window
                                context_text_start = texte_brut_source[start_slice:end_slice]
                                utils_logger.info(f"    contexte source_text (autour de pos {approx_start_pos}, fenetre +/-{context_window}):\n'''{context_text_start}'''")
                            else:
                                utils_logger.info(f"    start_marker non trouvé (estimation), contexte source_text (début):\n'''{texte_brut_source[:500]}'''")
                        try:
                            found_pos = texte_brut_source.index(actual_start_marker_log)
                            current_start_index = found_pos 
                            if is_target_extract:
                                utils_logger.info(f"  start_index TROUVÉ: {current_start_index}")
                        except ValueError:
                            if is_target_extract:
                                utils_logger.info(f"  start_index NON TROUVÉ pour '{actual_start_marker_log}'")
                            current_start_index = -1
                    
                    if end_marker and current_start_index != -1: # Assurer que end_marker n'est pas None ou vide
                        actual_end_marker_log = end_marker
                        search_area_start_for_end_marker = current_start_index + len(start_marker)
                        if is_target_extract:
                            utils_logger.info(f"  AVANT RECHERCHE end_marker (recherche à partir de position {search_area_start_for_end_marker}):")
                            utils_logger.info(f"    actual_end_marker: '{actual_end_marker_log}'")
                            approx_end_pos_in_search_area = texte_brut_source[search_area_start_for_end_marker:].find(actual_end_marker_log)
                            if approx_end_pos_in_search_area != -1:
                                approx_end_pos_global = search_area_start_for_end_marker + approx_end_pos_in_search_area
                                context_window = 200 
                                start_slice = max(0, approx_end_pos_global - context_window)
                                end_slice = approx_end_pos_global + len(actual_end_marker_log) + context_window
                                context_text_end = texte_brut_source[start_slice:end_slice]
                                utils_logger.info(f"    contexte source_text (autour de pos globale {approx_end_pos_global}, fenetre +/-{context_window}):\n'''{context_text_end}'''")
                            else:
                                utils_logger.info(f"    end_marker non trouvé (estimation) dans la zone, contexte source_text (zone de recherche concernée):\n'''{texte_brut_source[search_area_start_for_end_marker : search_area_start_for_end_marker + 500]}'''")
                        try:
                            found_pos_end = texte_brut_source.find(actual_end_marker_log, search_area_start_for_end_marker)
                            if found_pos_end != -1:
                                current_end_index = found_pos_end + len(actual_end_marker_log)
                                if is_target_extract:
                                    utils_logger.info(f"  end_index TROUVÉ (marqueur trouvé à {found_pos_end}, fin du segment à {current_end_index})")
                            else:
                                if is_target_extract:
                                    utils_logger.info(f"  end_index NON TROUVÉ pour '{actual_end_marker_log}' après start_marker.")
                                current_end_index = -1
                        except Exception as e_find_end: 
                            if is_target_extract:
                                utils_logger.error(f"  Erreur inattendue recherche end_marker: {e_find_end}")
                            current_end_index = -1
                    
                    if is_target_extract: 
                        utils_logger.info(f"  Valeurs finales pour {extract_name}: current_start_index = {current_start_index}, current_end_index = {current_end_index}")

                    total_checks += 1
                    # source_checks += 1 # Non utilisé
                    marker_errors = []

                    if not start_marker or not end_marker:
                        marker_errors.append("Marqueur(s) Manquant(s)")
                    else:
                        if current_start_index == -1 : marker_errors.append("Début NON TROUVÉ")
                        # Vérifier end_marker seulement si start_marker a été trouvé
                        if current_start_index != -1 and current_end_index == -1 : marker_errors.append("Fin NON TROUVÉE (après début)")
                        
                    if marker_errors:
                        utils_logger.warning(f"      -> ❌ Problème Extrait '{extract_name}': {', '.join(marker_errors)}")
                        results.append(f"<li>{source_name} -> {extract_name}: <strong style='color:red;'>{', '.join(marker_errors)}</strong></li>")
                        # source_errors += 1 # Non utilisé
                        total_errors += 1
                    else:
                        utils_logger.info(f"      -> ✅ OK: Extrait '{extract_name}'")
            else: 
                num_extracts = len(source_info.get("extracts",[]))
                results.append(f"<li>{source_name}: Vérification impossible (texte source non obtenu via get_full_text_for_source)</li>")
                total_errors += num_extracts 
                total_checks += num_extracts

        except Exception as e_verify_global:
            utils_logger.error(f"   -> ❌ Erreur inattendue vérification source '{source_name}': {e_verify_global}", exc_info=True)
            num_extracts = len(source_info.get("extracts",[]))
            results.append(f"<li>{source_name}: Erreur Vérification Générale ({type(e_verify_global).__name__})</li>")
            total_errors += num_extracts
            total_checks += num_extracts

    summary = f"--- Résultat Vérification ---<br/>{total_checks} extraits vérifiés. <strong style='color: {'red' if total_errors > 0 else 'green'};'>{total_errors} erreur(s) trouvée(s).</strong>"
    if results:
        summary += "<br/>Détails :<ul>" + "".join(results) + "</ul>"
    else:
         if total_checks > 0: summary += "<br/>Tous les marqueurs semblent corrects."
         else: summary += "<br/>Aucun extrait n'a pu être vérifié."

    utils_logger.info("\n" + f"{summary.replace('<br/>', chr(10)).replace('<li>', '- ').replace('</li>', '').replace('<ul>', '').replace('</ul>', '').replace('<strong>', '').replace('</strong>', '')}")
    return summary
utils_logger.info("Fonctions utilitaires UI définies.")
