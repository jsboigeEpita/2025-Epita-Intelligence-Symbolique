# ui/utils.py
import requests
import json
import gzip
import hashlib
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
from cryptography.fernet import Fernet, InvalidToken
from cryptography.exceptions import InvalidSignature

# Le reste des imports et du code...

# Import config depuis le même package ui
from . import config as ui_config

utils_logger = logging.getLogger("App.UI.Utils")
if not utils_logger.handlers and not utils_logger.propagate:
     handler = logging.StreamHandler(); formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s', datefmt='%H:%M:%S'); handler.setFormatter(formatter); utils_logger.addHandler(handler); utils_logger.setLevel(logging.INFO)

# --- Fonctions Utilitaires (Cache, Crypto, Fetch, Verify) ---

def reconstruct_url(schema: str, host_parts: list, path: str) -> Optional[str]:
    """Reconstruit une URL à partir de schema, host_parts, et path."""
    if not schema or not host_parts: return None # Path peut être vide et géré ci-dessous
    host = ".".join(part for part in host_parts if part)
    # Si path est None, on le traite comme une chaîne vide pour la logique suivante
    current_path = path if path is not None else ""
    current_path = current_path if current_path.startswith('/') or not current_path else '/' + current_path
    # S'assurer qu'un path vide après traitement devienne au moins "/"
    if not current_path:
        current_path = "/"
    return f"{schema}://{host}{current_path}"

def get_cache_filepath(url: str) -> Path:
    """Génère le chemin du fichier cache pour une URL."""
    url_hash = hashlib.sha256(url.encode()).hexdigest()
    # Utilise CACHE_DIR importé depuis config
    return ui_config.CACHE_DIR / f"{url_hash}.txt"

def load_from_cache(url: str) -> Optional[str]:
    """Charge le contenu textuel depuis le cache si disponible."""
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

def save_to_cache(url: str, text: str):
    """Sauvegarde le contenu textuel dans le cache."""
    if not text:
        utils_logger.info("   -> Texte vide, non sauvegardé.")
        return
    filepath = get_cache_filepath(url)
    try:
        # S'assurer que le dossier cache existe
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(text, encoding='utf-8')
        utils_logger.info(f"   -> Texte sauvegardé : {filepath.name}")
    except Exception as e:
        utils_logger.error(f"   -> Erreur sauvegarde cache {filepath.name}: {e}")

def encrypt_data(data: bytes, key: bytes) -> Optional[bytes]:
    """Chiffre des données binaires avec une clé Fernet."""
    if not key:
        utils_logger.error("Erreur chiffrement: Clé chiffrement manquante.")
        return None
    try:
        f = Fernet(key)
        return f.encrypt(data)
    except Exception as e:
        utils_logger.error(f"Erreur chiffrement: {e}")
        return None

def decrypt_data(encrypted_data: bytes, key: bytes) -> Optional[bytes]:
    """Déchiffre des données binaires avec une clé Fernet."""
    if not key:
        utils_logger.error("Erreur déchiffrement: Clé chiffrement manquante.")
        return None
    try:
        f = Fernet(key)
        return f.decrypt(encrypted_data)
    except (InvalidToken, InvalidSignature) as e: # Intercepter spécifiquement et relancer
        utils_logger.error(f"Erreur déchiffrement (InvalidToken/Signature): {e}")
        raise # Relancer l'exception capturée (InvalidToken ou InvalidSignature)
    except Exception as e: # Intercepter les autres exceptions
        utils_logger.error(f"Erreur déchiffrement (Autre): {e}")
        return None

# Les fonctions load_extract_definitions et save_extract_definitions ont été déplacées
# vers argumentation_analysis/ui/file_operations.py pour éviter les imports circulaires.
def fetch_direct_text(source_url: str, timeout: int = 60) -> str:
    """Récupère contenu texte brut d'URL, utilise cache fichier."""
    # Utilise les fonctions de cache de ce module
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
) -> str:
    """Récupère et extrait via Jina, utilise cache fichier."""
    # Utilise les fonctions de cache de ce module
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
    ) -> str:
    """Traite une source via Tika avec gestion cache brut et type texte."""
    _tika_server_url = tika_server_url_override if tika_server_url_override is not None else ui_config.TIKA_SERVER_URL
    _plaintext_extensions = plaintext_extensions_override if plaintext_extensions_override is not None else ui_config.PLAINTEXT_EXTENSIONS
    _temp_download_dir = temp_download_dir_override if temp_download_dir_override is not None else ui_config.TEMP_DOWNLOAD_DIR

    cache_key = source_url if source_url else f"file://{file_name}"
    cached_text = load_from_cache(cache_key)
    if cached_text is not None: return cached_text

    content_to_send = None
    # temp_download_dir = ui_config.TEMP_DOWNLOAD_DIR # Utiliser le chemin depuis config
    # Remplacé par _temp_download_dir
    
    # --- LOGS DÉTAILLÉS ---
    processing_target_log = ""
    if source_url:
        processing_target_log = f"URL: {source_url}"
        # Si l'URL est un chemin de fichier local (commence par file://), extraire le chemin
        if source_url.startswith("file://"):
            local_file_path = Path(source_url[7:])
            processing_target_log += f" (Chemin local interprété: {local_file_path})"
            # Si raw_file_cache_path est fourni, il est prioritaire pour le cache brut
            # Sinon, on utilise le chemin local directement si c'est un fichier PDF
            # (ou un autre type binaire que Tika devrait traiter)
            # Note: la logique de cache brut existante avec _temp_download_dir est conservée pour les URL HTTP(S)
            if local_file_path.suffix.lower() == ".pdf": # Exemple pour PDF
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
        
        # Si c'est une URL file:// et que le fichier existe, on le lit directement
        # au lieu de passer par le cache de téléchargement brut (qui est plus pour HTTP)
        if source_url.startswith("file://"):
            local_path_from_url = Path(source_url[7:])
            if local_path_from_url.exists() and local_path_from_url.is_file():
                utils_logger.info(f"   -> Lecture directe du fichier local (via file:// URL): {local_path_from_url}")
                try:
                    content_to_send = local_path_from_url.read_bytes()
                except Exception as e_read_local_file:
                    utils_logger.error(f"   -> Erreur lecture fichier local {local_path_from_url}: {e_read_local_file}. Tentative de téléchargement si c'est aussi une URL HTTP(S)...")
                    # Si la lecture échoue, on laisse la logique de téléchargement HTTP(S) ci-dessous prendre le relais si applicable
                    # ou si c'était *uniquement* un file://, alors content_to_send restera None.
            else:
                utils_logger.warning(f"   -> Fichier local spécifié via file:// URL non trouvé ou n'est pas un fichier: {local_path_from_url}")


        if content_to_send is None and not source_url.startswith("file://"): # Ne pas re-télécharger si c'était un file:// qui a échoué
            if effective_raw_cache_path.exists() and effective_raw_cache_path.stat().st_size > 0:
                 try:
                    utils_logger.info(f"   -> Lecture fichier brut depuis cache local : {effective_raw_cache_path.name}")
                    content_to_send = effective_raw_cache_path.read_bytes()
                 except Exception as e_read_raw:
                    utils_logger.warning(f"   -> Erreur lecture cache brut {effective_raw_cache_path.name}: {e_read_raw}. Re-téléchargement...")
                    content_to_send = None # Assurer que content_to_send est None pour forcer le re-téléchargement

            if content_to_send is None: # Si toujours None après tentative de cache brut
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
        save_to_cache(cache_key, "") # Sauvegarder une chaîne vide pour éviter re-fetch inutile
        return ""

    utils_logger.info(f"  [Tika Log] Envoi du contenu à Tika. URL Tika: {_tika_server_url}, Taille contenu: {len(content_to_send)} bytes, Timeout Tika: {timeout_tika}s")
    headers = { 'Accept': 'text/plain', 'Content-Type': 'application/octet-stream', 'X-Tika-OCRLanguage': 'fra+eng' }
    texte_brut_tika = "" # Initialiser
    try:
        response_tika = requests.put(_tika_server_url, data=content_to_send, headers=headers, timeout=timeout_tika)
        utils_logger.info(f"  [Tika Log] Réponse de Tika reçue. Statut: {response_tika.status_code}")
        response_tika.raise_for_status() # Lèvera une exception pour les codes d'erreur HTTP
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
        # Sauvegarder une chaîne vide pour éviter les re-tentatives sur des erreurs persistantes de Tika
        save_to_cache(cache_key, "")
        raise ConnectionError(f"Erreur HTTP Tika: {e_http}") from e_http
    except requests.exceptions.RequestException as e_req:
        utils_logger.error(f"  [Tika Log] ❌ Erreur de requête Tika: {e_req}")
        save_to_cache(cache_key, "")
        raise ConnectionError(f"Erreur de requête Tika: {e_req}") from e_req
    except Exception as e_generic:
        utils_logger.error(f"  [Tika Log] ❌ Erreur inattendue pendant le traitement Tika: {e_generic}", exc_info=True)
        save_to_cache(cache_key, "") # Sauvegarder une chaîne vide en cas d'erreur inconnue
        raise ConnectionError(f"Erreur inattendue Tika: {e_generic}") from e_generic


        if not texte_brut: utils_logger.warning(f"   -> Warning: Tika status {response_tika.status_code} sans texte.")
        else: utils_logger.info(f"   -> Texte Tika extrait (longueur {len(texte_brut)}).")
        save_to_cache(cache_key, texte_brut)
        return texte_brut
    except requests.exceptions.Timeout:
        utils_logger.error(f"   -> ❌ Timeout Tika ({timeout_tika}s).")
        raise ConnectionError(f"Timeout Tika ({timeout_tika}s)") # Renvoyer une erreur plus spécifique
    except requests.exceptions.RequestException as e:
        utils_logger.error(f"Erreur Tika: {e}")
        raise ConnectionError(f"Erreur Tika: {e}") from e


def get_full_text_for_source(source_info: Dict[str, Any], app_config: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """
    Récupère le texte complet pour une source donnée, en utilisant le cache et les configurations appropriées.
    Centralise la logique de récupération de texte (Jina, Tika, téléchargement direct).

    Args:
        source_info: Dictionnaire contenant les informations de la source.
                     Doit contenir "schema", "host_parts", "path", et "source_type".
        app_config: Dictionnaire optionnel de configuration de l'application.
                    Peut contenir des surcharges pour JINA_READER_PREFIX, TIKA_SERVER_URL,
                    PLAINTEXT_EXTENSIONS, TEMP_DOWNLOAD_DIR.

    Returns:
        Le texte complet de la source, ou None en cas d'erreur.
    """
    source_name_for_log = source_info.get('source_name', 'Source inconnue')
    utils_logger.debug(f"get_full_text_for_source appelée pour: {source_name_for_log}")

    source_type = source_info.get("source_type") # Déplacé ici pour être défini avant utilisation
    source_path_str = source_info.get("path")
    reconstructed_url = None # Initialiser

    # NOUVELLE LOGIQUE: Si un champ 'url' est explicitement fourni, l'utiliser en priorité.
    # Ceci est particulièrement pertinent pour fetch_method: 'url' ou lorsque l'URL complète est déjà connue.
    explicit_url = source_info.get("url")
    if explicit_url:
        utils_logger.debug(f"Champ 'url' explicite trouvé et utilisé pour '{source_name_for_log}': {explicit_url}")
        reconstructed_url = explicit_url
    
    if reconstructed_url is None: # Si l'URL explicite n'a pas été fournie ou n'a pas été utilisée
        utils_logger.debug(f"Aucune URL explicite fournie ou utilisée pour '{source_name_for_log}'. Passage à la logique de reconstruction.")
        # Logique spécifique pour les sources Tika locales
        # Si c'est une source 'tika', qu'elle a un 'path', et qu'elle n'a pas de 'schema'/'host_parts' (typique d'un fichier local)
        if source_type == "tika" and source_path_str and not source_info.get("schema") and not source_info.get("host_parts"):
            utils_logger.debug(f"Source Tika avec path local détectée: {source_path_str} pour '{source_name_for_log}'")
            local_file_path = Path(source_path_str)
            if not local_file_path.is_absolute():
                # Utiliser ui_config.PROJECT_ROOT (qui est _project_root de config.py)
                if hasattr(ui_config, 'PROJECT_ROOT') and isinstance(ui_config.PROJECT_ROOT, Path):
                    utils_logger.debug(f"DEBUG: ui_config.PROJECT_ROOT utilisé dans get_full_text_for_source: {ui_config.PROJECT_ROOT}")
                    local_file_path = (ui_config.PROJECT_ROOT / local_file_path).resolve()
                    utils_logger.debug(f"Chemin local résolu en: {local_file_path} pour '{source_name_for_log}'")
                else:
                    utils_logger.warning(f"ui_config.PROJECT_ROOT non disponible ou mal configuré. Tentative de résolution de '{source_path_str}' par rapport au CWD pour '{source_name_for_log}'.")
                    local_file_path = (Path.cwd() / local_file_path).resolve() # Fallback, peut être moins fiable
            
            if local_file_path.exists() and local_file_path.is_file():
                reconstructed_url = local_file_path.as_uri() # ex: file:///D:/path/to/file.pdf
                utils_logger.info(f"Source Tika locale: Utilisation de l'URI de fichier '{reconstructed_url}' pour '{source_name_for_log}'.")
            else:
                utils_logger.error(f"Fichier local pour source Tika '{source_name_for_log}' non trouvé ou n'est pas un fichier: {local_file_path} (path original: '{source_path_str}')")
                # Laisser reconstructed_url à None pour la suite

        # Logique de reconstruction d'URL standard si toujours None
        if reconstructed_url is None:
            utils_logger.debug(f"Tentative de reconstruction d'URL standard pour '{source_name_for_log}' (schema: {source_info.get('schema')}, host_parts: {source_info.get('host_parts', [])}, path: {source_info.get('path')})")
            reconstructed_url = reconstruct_url(
                source_info.get("schema"), source_info.get("host_parts", []), source_info.get("path")
            )

    if not reconstructed_url:
        utils_logger.error(f"URL invalide ou impossible à construire pour source: {source_name_for_log}")
        return None

    # Essayer de charger depuis le cache fichier d'abord
    cached_text = load_from_cache(reconstructed_url)
    if cached_text is not None:
        utils_logger.info(f"Texte chargé depuis cache fichier pour URL '{reconstructed_url}' ({source_name_for_log})")
        return cached_text

    # source_type est maintenant défini plus haut
    texte_brut_source: Optional[str] = None

    # Récupérer les configurations, en privilégiant app_config si fourni
    jina_prefix_val = ui_config.JINA_READER_PREFIX
    tika_server_url_val = ui_config.TIKA_SERVER_URL
    plaintext_extensions_val = ui_config.PLAINTEXT_EXTENSIONS
    temp_download_dir_val = ui_config.TEMP_DOWNLOAD_DIR

    if app_config:
        jina_prefix_val = app_config.get('JINA_READER_PREFIX', jina_prefix_val)
        tika_server_url_val = app_config.get('TIKA_SERVER_URL', tika_server_url_val)
        plaintext_extensions_val = app_config.get('PLAINTEXT_EXTENSIONS', plaintext_extensions_val)
        # Pour TEMP_DOWNLOAD_DIR, s'assurer que c'est un objet Path si surchargé
        temp_download_dir_str_or_path = app_config.get('TEMP_DOWNLOAD_DIR')
        if temp_download_dir_str_or_path is not None:
            temp_download_dir_val = Path(temp_download_dir_str_or_path)


    utils_logger.info(f"Cache texte absent pour '{reconstructed_url}' ({source_name_for_log}). Récupération (type: {source_type})...")
    try:
        if source_type == "jina":
            texte_brut_source = fetch_with_jina(
                reconstructed_url,
                jina_reader_prefix_override=jina_prefix_val
            )
        elif source_type == "direct_download":
            # fetch_direct_text n'a pas de config spécifique à surcharger via app_config pour l'instant
            texte_brut_source = fetch_direct_text(reconstructed_url)
        elif source_type == "tika":
            # fetch_with_tika gère déjà la logique plaintext vs binaire en interne
            # On passe les configs potentiellement surchargées
            texte_brut_source = fetch_with_tika(
                source_url=reconstructed_url,
                tika_server_url_override=tika_server_url_val,
                plaintext_extensions_override=plaintext_extensions_val,
                temp_download_dir_override=temp_download_dir_val
                # raw_file_cache_path n'est pas géré par app_config ici, fetch_with_tika le déduit si besoin
            )
        else:
            utils_logger.warning(f"Type de source inconnu '{source_type}' pour '{reconstructed_url}' ({source_name_for_log}). Impossible de récupérer le texte.")
            return None

        if texte_brut_source is not None:
            utils_logger.info(f"Texte récupéré pour '{reconstructed_url}' ({source_name_for_log}), sauvegarde dans le cache...")
            save_to_cache(reconstructed_url, texte_brut_source)
        else:
            utils_logger.warning(f"Aucun texte brut retourné par la fonction fetch pour '{reconstructed_url}' ({source_name_for_log}).")


        return texte_brut_source

    except ConnectionError as e: # Erreurs spécifiques levées par les fetch_*
        utils_logger.error(f"Erreur de connexion lors de la récupération de '{reconstructed_url}' ({source_name_for_log}, type: {source_type}): {e}")
        return None
    except Exception as e:
        utils_logger.error(f"Erreur inattendue lors de la récupération de '{reconstructed_url}' ({source_name_for_log}, type: {source_type}): {e}", exc_info=True)
        return None

def verify_extract_definitions(definitions_list: list) -> str:
    """Vérifie la présence des marqueurs start/end pour chaque extrait défini."""
    # Utilise les fonctions reconstruct_url, load_from_cache, fetch_* de ce module
    # Et les constantes de ui.config
    utils_logger.info("\n🔬 Lancement de la vérification des marqueurs d'extraits...")
    results = []
    total_checks = 0
    total_errors = 0

    # Utilise la constante depuis config
    if not definitions_list or definitions_list == ui_config.DEFAULT_EXTRACT_SOURCES:
        return "Aucune définition valide à vérifier."

    for source_idx, source_info in enumerate(definitions_list):
        source_name = source_info.get("source_name", f"Source Inconnue #{source_idx+1}")
        utils_logger.info(f"\n--- Vérification Source: '{source_name}' ---")
        source_errors = 0
        source_checks = 0
        texte_brut_source = None
        reconstructed_url = None

        try:
            reconstructed_url = reconstruct_url(
                source_info.get("schema"), source_info.get("host_parts", []), source_info.get("path")
            )
            if not reconstructed_url:
                utils_logger.error("   -> ❌ Erreur: URL Invalide.")
                results.append(f"<li>{source_name}: URL invalide</li>")
                num_extracts = len(source_info.get("extracts", []))
                total_errors += num_extracts
                total_checks += num_extracts
                continue

            source_type = source_info.get("source_type")
            cache_key = reconstructed_url
            texte_brut_source = load_from_cache(cache_key)

            if texte_brut_source is None:
                utils_logger.info(f"   -> Cache texte absent. Récupération (type: {source_type})...")
                try:
                    if source_type == "jina": texte_brut_source = fetch_with_jina(reconstructed_url)
                    elif source_type == "direct_download": texte_brut_source = fetch_direct_text(reconstructed_url)
                    elif source_type == "tika":
                        is_plaintext = any(source_info.get("path", "").lower().endswith(ext) for ext in ui_config.PLAINTEXT_EXTENSIONS)
                        if is_plaintext: texte_brut_source = fetch_direct_text(reconstructed_url)
                        else:
                            utils_logger.warning("   -> ⚠️ Vérification marqueurs sautée pour source Tika binaire.")
                            texte_brut_source = None
                    else:
                        utils_logger.warning(f"   -> ⚠️ Type source inconnu '{source_type}'. Vérification impossible.")
                        texte_brut_source = None
                except Exception as e_fetch_verify:
                     utils_logger.error(f"   -> ❌ Erreur fetch pendant vérification pour '{source_name}': {e_fetch_verify}")
                     texte_brut_source = None

            # ... [Reste de la logique de vérification des marqueurs - IDENTIQUE A AVANT] ...
            if texte_brut_source is not None:
                utils_logger.info(f"   -> Texte complet récupéré (longueur: {len(texte_brut_source)}). Vérification des extraits...")
                extracts = source_info.get("extracts", [])
                if not extracts: utils_logger.info("      -> Aucun extrait défini.")

                for extract_idx, extract_info in enumerate(extracts):
                    extract_name = extract_info.get("extract_name", f"Extrait #{extract_idx+1}")
                    start_marker = extract_info.get("start_marker")
                    end_marker = extract_info.get("end_marker")
                    total_checks += 1
                    source_checks += 1
                    marker_errors = []

                    if not start_marker or not end_marker:
                        marker_errors.append("Marqueur(s) Manquant(s)")
                    else:
                        start_found = start_marker in texte_brut_source
                        end_found_after_start = False
                        if start_found:
                            try:
                                start_pos = texte_brut_source.index(start_marker)
                                end_found_after_start = end_marker in texte_brut_source[start_pos + len(start_marker):]
                            except ValueError: start_found = False
                        if not start_found: marker_errors.append("Début NON TROUVÉ")
                        if not end_found_after_start: marker_errors.append("Fin NON TROUVÉE (après début)")

                    if marker_errors:
                        utils_logger.warning(f"      -> ❌ Problème Extrait '{extract_name}': {', '.join(marker_errors)}")
                        results.append(f"<li>{source_name} -> {extract_name}: <strong style='color:red;'>{', '.join(marker_errors)}</strong></li>")
                        source_errors += 1
                        total_errors += 1
                    else:
                        utils_logger.info(f"      -> ✅ OK: Extrait '{extract_name}'")

            else:
                num_extracts = len(source_info.get("extracts",[]))
                if source_type != 'tika' or is_plaintext:
                    results.append(f"<li>{source_name}: Vérification impossible (texte source non obtenu)</li>")
                    total_errors += num_extracts
                else:
                     results.append(f"<li>{source_name}: Vérification marqueurs sautée (source Tika binaire)</li>")
                total_checks += num_extracts

        except Exception as e_verify_global:
            utils_logger.error(f"   -> ❌ Erreur inattendue vérification source '{source_name}': {e_verify_global}", exc_info=True)
            num_extracts = len(source_info.get("extracts",[]))
            results.append(f"<li>{source_name}: Erreur Vérification Générale ({type(e_verify_global).__name__})</li>")
            total_errors += num_extracts
            total_checks += num_extracts

    # ... [Reste de la logique de formatage du résumé - IDENTIQUE A AVANT] ...
    summary = f"--- Résultat Vérification ---<br/>{total_checks} extraits vérifiés. <strong style='color: {'red' if total_errors > 0 else 'green'};'>{total_errors} erreur(s) trouvée(s).</strong>"
    if results:
        summary += "<br/>Détails :<ul>" + "".join(results) + "</ul>"
    else:
         if total_checks > 0: summary += "<br/>Tous les marqueurs semblent corrects."
         else: summary += "<br/>Aucun extrait n'a pu être vérifié."

    utils_logger.info("\n" + f"{summary.replace('<br/>', chr(10)).replace('<li>', '- ').replace('</li>', '').replace('<ul>', '').replace('</ul>', '').replace('<strong>', '').replace('</strong>', '')}")
    return summary


utils_logger.info("Fonctions utilitaires UI définies.")