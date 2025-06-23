"""
Utilitaires de récupération de contenu (fetch) pour l'interface utilisateur.
"""
import requests
import hashlib
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
from pybreaker import CircuitBreakerError

from argumentation_analysis.config.settings import settings
from argumentation_analysis.core.utils.network_utils import retry_on_network_error, network_breaker
from .cache_utils import load_from_cache, save_to_cache
from .utils import reconstruct_url

fetch_logger = logging.getLogger("App.UI.FetchUtils")
if not fetch_logger.handlers and not fetch_logger.propagate:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s', datefmt='%H:%M:%S')
    handler.setFormatter(formatter)
    fetch_logger.addHandler(handler)
    fetch_logger.setLevel(logging.INFO)

# La fonction reconstruct_url est maintenant importée depuis .utils

@retry_on_network_error
@network_breaker
def fetch_direct_text(source_url: str, timeout: int = 15) -> Optional[str]:
    """Récupère le contenu texte brut d'une URL par téléchargement direct de manière robuste."""
    cached_text = load_from_cache(source_url)
    if cached_text is not None: return cached_text
    fetch_logger.info(f"-> Téléchargement direct depuis : {source_url}...")
    headers = {'User-Agent': 'ArgumentAnalysisApp/1.0'}
    try:
        response = requests.get(source_url, headers=headers, timeout=timeout)
        response.raise_for_status()
        texte_brut = response.content.decode('utf-8', errors='ignore')
        fetch_logger.info(f"   -> Contenu direct récupéré (longueur {len(texte_brut)}).")
        save_to_cache(source_url, texte_brut)
        return texte_brut
    except CircuitBreakerError:
        fetch_logger.error(f"Disjoncteur ouvert pour fetch_direct_text sur {source_url}.")
        raise ConnectionError(f"Le service est temporairement indisponible (disjoncteur ouvert) pour {source_url}.")
    except requests.exceptions.RequestException as e:
        fetch_logger.error(f"Erreur persistante de téléchargement direct pour {source_url}: {e}")
        raise ConnectionError(f"Erreur de téléchargement persistante pour {source_url}") from e

@retry_on_network_error
@network_breaker
def _robust_fetch_jina(jina_url: str, timeout: int, headers: dict) -> requests.Response:
    response = requests.get(jina_url, headers=headers, timeout=timeout)
    response.raise_for_status()
    return response

def fetch_with_jina(
    source_url: str,
    timeout: int = 45,
    jina_reader_prefix_override: Optional[str] = None
) -> Optional[str]:
    """Récupère et extrait le contenu textuel d'une URL via Jina de manière robuste."""
    cached_text = load_from_cache(source_url)
    if cached_text is not None: return cached_text

    _jina_reader_prefix = jina_reader_prefix_override if jina_reader_prefix_override is not None else str(settings.jina.reader_prefix)
    jina_url = f"{_jina_reader_prefix.rstrip('/')}/{source_url}"

    fetch_logger.info(f"-> Récupération via Jina : {jina_url}...")
    headers = {'Accept': 'text/markdown', 'User-Agent': 'ArgumentAnalysisApp/1.0'}
    try:
        response = _robust_fetch_jina(jina_url, timeout, headers)
    except CircuitBreakerError:
        fetch_logger.error(f"Disjoncteur ouvert pour Jina sur {jina_url}.")
        raise ConnectionError(f"Le service Jina est temporairement indisponible (disjoncteur ouvert).")
    except requests.exceptions.RequestException as e:
        fetch_logger.error(f"Erreur Jina persistante pour {jina_url}: {e}")
        raise ConnectionError(f"Erreur Jina persistante pour {jina_url}") from e
    
    content = response.text
    md_start_marker = "Markdown Content:"
    md_start_index = content.find(md_start_marker)
    texte_brut = content[md_start_index + len(md_start_marker):].strip() if md_start_index != -1 else content
    fetch_logger.info(f"   -> Contenu Jina récupéré (longueur {len(texte_brut)}).")
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
    """Traite une source (URL ou contenu binaire) via un serveur Apache Tika. (Version MERGE_HEAD)"""
    _tika_server_url = tika_server_url_override if tika_server_url_override is not None else str(settings.tika.server_endpoint)
    _plaintext_extensions = plaintext_extensions_override if plaintext_extensions_override is not None else settings.ui.plaintext_extensions
    _temp_download_dir = temp_download_dir_override if temp_download_dir_override is not None else settings.ui.temp_download_dir

    cache_key = source_url if source_url else f"file://{file_name}"
    cached_text = load_from_cache(cache_key)
    if cached_text is not None: return cached_text

    content_to_send = None
    
    processing_target_log = ""
    if source_url:
        processing_target_log = f"URL: {source_url}"
        if source_url.startswith("file://"):
            local_file_path = Path(source_url[7:])
            processing_target_log += f" (Chemin local interprété: {local_file_path})"
            if local_file_path.suffix.lower() == ".pdf":
                 fetch_logger.info(f"  [Tika Log] Traitement du fichier PDF local: {local_file_path}")
    elif file_content:
        processing_target_log = f"Fichier fourni: {file_name} (taille: {len(file_content)} bytes)"
        if file_name.lower().endswith(".pdf"):
            fetch_logger.info(f"  [Tika Log] Traitement du contenu PDF fourni pour: {file_name}")
    fetch_logger.info(f"  [Tika Log] Début fetch_with_tika pour: {processing_target_log}")

    if source_url:
        original_filename = Path(source_url).name
        if any(source_url.lower().endswith(ext) for ext in _plaintext_extensions):
            fetch_logger.info(f"   -> URL détectée comme texte simple ({source_url}). Fetch direct.")
            return fetch_direct_text(source_url)

        url_hash = hashlib.sha256(source_url.encode()).hexdigest()
        file_extension = Path(original_filename).suffix if Path(original_filename).suffix else ".download"
        effective_raw_cache_path = Path(raw_file_cache_path) if raw_file_cache_path else _temp_download_dir / f"{url_hash}{file_extension}"
        
        if source_url.startswith("file://"):
            local_path_from_url = Path(source_url[7:])
            if local_path_from_url.exists() and local_path_from_url.is_file():
                fetch_logger.info(f"   -> Lecture directe du fichier local (via file:// URL): {local_path_from_url}")
                try:
                    content_to_send = local_path_from_url.read_bytes()
                except Exception as e_read_local_file:
                    fetch_logger.error(f"   -> Erreur lecture fichier local {local_path_from_url}: {e_read_local_file}. Tentative de téléchargement si c'est aussi une URL HTTP(S)...")
            else:
                fetch_logger.warning(f"   -> Fichier local spécifié via file:// URL non trouvé ou n'est pas un fichier: {local_path_from_url}")

        if content_to_send is None and not source_url.startswith("file://"):
            if effective_raw_cache_path.exists() and effective_raw_cache_path.stat().st_size > 0:
                 try:
                    fetch_logger.info(f"   -> Lecture fichier brut depuis cache local : {effective_raw_cache_path.name}")
                    content_to_send = effective_raw_cache_path.read_bytes()
                 except Exception as e_read_raw:
                    fetch_logger.warning(f"   -> Erreur lecture cache brut {effective_raw_cache_path.name}: {e_read_raw}. Re-téléchargement...")
                    content_to_send = None
            if content_to_send is None:
                 fetch_logger.info(f"-> Téléchargement (pour Tika) depuis : {source_url}...")
                 try:
                     response_dl_res = _robust_get_request(source_url, stream=True, timeout=timeout_dl)
                     if response_dl_res is None: raise ConnectionError(f"Echec du téléchargement robuste de {source_url}")
                     content_to_send = response_dl_res.content
                     fetch_logger.info(f"   -> Doc téléchargé ({len(content_to_send)} bytes).")
                     try:
                         effective_raw_cache_path.parent.mkdir(parents=True, exist_ok=True)
                         effective_raw_cache_path.write_bytes(content_to_send)
                         fetch_logger.info(f"   -> Doc brut sauvegardé: {effective_raw_cache_path.resolve()}")
                     except Exception as e_save:
                         fetch_logger.error(f"   -> Erreur sauvegarde brut: {e_save}")
                 except requests.exceptions.RequestException as e:
                     fetch_logger.error(f"Erreur téléchargement {source_url}: {e}")
                     raise ConnectionError(f"Erreur téléchargement {source_url}: {e}") from e
    elif file_content:
        fetch_logger.info(f"-> Utilisation contenu fichier '{file_name}' ({len(file_content)} bytes)...")
        content_to_send = file_content
        if any(file_name.lower().endswith(ext) for ext in _plaintext_extensions):
            fetch_logger.info("   -> Fichier uploadé détecté comme texte simple. Lecture directe.")
            try:
                texte_brut = file_content.decode('utf-8', errors='ignore')
                save_to_cache(cache_key, texte_brut)
                return texte_brut
            except Exception as e_decode:
                fetch_logger.warning(f"   -> Erreur décodage fichier texte '{file_name}': {e_decode}. Tentative avec Tika...")
    else:
        raise ValueError("fetch_with_tika: Il faut soit source_url soit file_content.")

    if not content_to_send:
        fetch_logger.warning("   -> Contenu brut vide ou non récupéré. Impossible d'envoyer à Tika.")
        save_to_cache(cache_key, "")
        return ""

    fetch_logger.info(f"  [Tika Log] Envoi du contenu à Tika. URL Tika: {_tika_server_url}, Taille contenu: {len(content_to_send)} bytes, Timeout Tika: {timeout_tika}s")
    headers = { 'Accept': 'text/plain', 'Content-Type': 'application/octet-stream', 'X-Tika-OCRLanguage': 'fra+eng' }
    texte_brut_tika = ""
    try:
        response_tika_res = _robust_put_request(str(_tika_server_url), data=content_to_send, headers=headers, timeout=timeout_tika)
        if response_tika_res is None: raise ConnectionError(f"Echec de l'envoi robuste à Tika")
        fetch_logger.info(f"  [Tika Log] Réponse de Tika reçue. Statut: {response_tika_res.status_code}")
        texte_brut_tika = response_tika_res.text
        if not texte_brut_tika:
            fetch_logger.warning(f"  [Tika Log] Tika a retourné un statut {response_tika_res.status_code} mais le texte est vide.")
        else:
            fetch_logger.info(f"  [Tika Log] Texte extrait par Tika. Longueur: {len(texte_brut_tika)}.")
            fetch_logger.debug(f"  [Tika Log] Extrait Tika (premiers 200 chars): {texte_brut_tika[:200]}")
        save_to_cache(cache_key, texte_brut_tika)
        return texte_brut_tika
    except requests.exceptions.Timeout:
        fetch_logger.error(f"  [Tika Log] ❌ Timeout Tika ({timeout_tika}s) pour {processing_target_log}.")
        raise ConnectionError(f"Timeout Tika pour {processing_target_log}")
    except requests.exceptions.HTTPError as e_http:
        fetch_logger.error(f"  [Tika Log] ❌ Erreur HTTP de Tika: {e_http}. Réponse: {e_http.response.text[:500] if e_http.response else 'Pas de réponse textuelle'}")
        save_to_cache(cache_key, "")
        raise ConnectionError(f"Erreur HTTP Tika: {e_http}") from e_http
    except requests.exceptions.RequestException as e_req:
        fetch_logger.error(f"  [Tika Log] ❌ Erreur de requête Tika: {e_req}")
        save_to_cache(cache_key, "")
        raise ConnectionError(f"Erreur de requête Tika: {e_req}") from e_req
    except Exception as e_generic:
        fetch_logger.error(f"  [Tika Log] ❌ Erreur inattendue pendant le traitement Tika: {e_generic}", exc_info=True)
        save_to_cache(cache_key, "")
        raise ConnectionError(f"Erreur inattendue Tika: {e_generic}") from e_generic

def get_full_text_for_source(source_info: Dict[str, Any]) -> Optional[str]:
    """Récupère le texte complet pour une source donnée. (Version fusionnée)"""
    source_name_for_log = source_info.get('source_name', source_info.get('id', 'Source inconnue'))
    fetch_logger.debug(f"get_full_text_for_source appelée pour: {source_name_for_log}")

    fetch_method = source_info.get("fetch_method", source_info.get("source_type"))

    # Logique de HEAD pour fetch_method == "file" (lecture directe de fichier texte)
    if fetch_method == "file":
        file_path_str = source_info.get("path")
        if not file_path_str:
            fetch_logger.error(f"Champ 'path' manquant pour la source locale: {source_name_for_log}")
            return None
        
        absolute_file_path = Path(file_path_str)
        if not absolute_file_path.is_absolute():
             # Essayer de résoudre par rapport à la racine du projet, sinon CWD
            project_root = Path(os.getcwd()) # Fallback
            if 'PROJECT_ROOT' in os.environ:
                project_root = Path(os.environ['PROJECT_ROOT'])
            absolute_file_path = (project_root / file_path_str).resolve()
        
        fetch_logger.info(f"Tentative de lecture du fichier local: {absolute_file_path}")
        if absolute_file_path.exists() and absolute_file_path.is_file():
            try:
                text_content = absolute_file_path.read_text(encoding='utf-8')
                fetch_logger.info(f"Contenu du fichier local '{absolute_file_path.name}' lu avec succès (longueur: {len(text_content)}).")
                # Pas de cache pour les fichiers locaux lus directement via fetch_method: file
                return text_content
            except Exception as e:
                fetch_logger.error(f"Erreur lors de la lecture du fichier local '{absolute_file_path}': {e}")
                return None
        else:
            fetch_logger.error(f"Fichier local non trouvé ou n'est pas un fichier: {absolute_file_path}")
            return None

    # Logique de MERGE_HEAD pour la gestion des URL (priorité à 'url', puis reconstruction)
    target_url = source_info.get("url")
    if not target_url:
        fetch_logger.debug(f"Champ 'url' non trouvé pour {source_name_for_log}, tentative de reconstruction avec schema/host/path.")
        # Utilisation du reconstruct_url défini localement en attendant la refonte
        target_url = reconstruct_url(
            source_info.get("schema"), source_info.get("host_parts", []), source_info.get("path")
        )
    
    if not target_url:
        fetch_logger.error(f"URL non disponible ou invalide pour source: {source_name_for_log} (fetch_method: {fetch_method}) après vérification 'url' et reconstruction.")
        return None
    
    fetch_logger.debug(f"URL cible déterminée pour {source_name_for_log}: {target_url}")

    cached_text = load_from_cache(target_url)
    if cached_text is not None:
        fetch_logger.info(f"Texte chargé depuis cache fichier pour URL '{target_url}' ({source_name_for_log})")
        # Logique "Source_1" de HEAD
        if source_name_for_log == "Source_1":
            fetch_logger.info(f"--- LOGGING SPÉCIFIQUE POUR Source_1 (depuis cache) ---")
            fetch_logger.info(f"Full text length: {len(cached_text)}")
            fetch_logger.info(f"Premiers 500 chars:\n{cached_text[:500]}")
            fetch_logger.info(f"Derniers 500 chars:\n{cached_text[-500:]}")
            fetch_logger.info(f"--- FIN LOGGING SPÉCIFIQUE POUR Source_1 ---")
        return cached_text

    source_type_original = source_info.get("source_type") # Peut différer de fetch_method
    texte_brut_source: Optional[str] = None

    # Les valeurs de configuration sont maintenant lues directement depuis l'objet `settings`
    jina_prefix_val = str(settings.jina.reader_prefix)
    tika_server_url_val = str(settings.tika.server_endpoint)
    plaintext_extensions_val = settings.ui.plaintext_extensions
    temp_download_dir_val = settings.ui.temp_download_dir

    fetch_logger.info(f"Cache texte absent pour '{target_url}' ({source_name_for_log}). Récupération (méthode: {fetch_method}, type original: {source_type_original})...")
    try:
        # La logique de MERGE_HEAD pour la reconstruction d'URL pour Tika (file://) est gérée dans fetch_with_tika
        # et dans la détermination de target_url plus haut si c'est un chemin local pour Tika.
        # Ici, on se base sur fetch_method ou source_type_original.
        
        effective_fetch_strategy = fetch_method if fetch_method else source_type_original

        if effective_fetch_strategy == "jina":
            texte_brut_source = fetch_with_jina(target_url, jina_reader_prefix_override=jina_prefix_val)
        elif effective_fetch_strategy == "tika":
             # Si target_url est déjà un file:// URI, fetch_with_tika le gérera.
            texte_brut_source = fetch_with_tika(
                source_url=target_url,
                tika_server_url_override=tika_server_url_val,
                plaintext_extensions_override=plaintext_extensions_val,
                temp_download_dir_override=temp_download_dir_val
            )
        elif effective_fetch_strategy == "direct_download":
            texte_brut_source = fetch_direct_text(target_url)
        # Fallbacks de HEAD (si fetch_method était manquant et source_type_original est utilisé)
        elif source_type_original == "web" and effective_fetch_strategy != "jina": # Éviter double appel si fetch_method était "jina"
             fetch_logger.info(f"Fallback pour source_type 'web' vers fetch_with_jina pour {target_url}")
             texte_brut_source = fetch_with_jina(target_url, jina_reader_prefix_override=jina_prefix_val)
        elif source_type_original == "pdf" and effective_fetch_strategy != "tika": # Éviter double appel
             fetch_logger.info(f"Fallback pour source_type 'pdf' vers fetch_with_tika pour {target_url}")
             texte_brut_source = fetch_with_tika(source_url=target_url, tika_server_url_override=tika_server_url_val, plaintext_extensions_override=plaintext_extensions_val, temp_download_dir_override=temp_download_dir_val)
        else:
            fetch_logger.warning(f"Méthode de fetch/type de source inconnu ou non géré: '{effective_fetch_strategy}' pour '{target_url}' ({source_name_for_log}). Impossible de récupérer le texte.")
            return None

        if texte_brut_source is not None:
            fetch_logger.info(f"Texte récupéré pour '{target_url}' ({source_name_for_log}), sauvegarde dans le cache...")
            save_to_cache(target_url, texte_brut_source)
        else:
            fetch_logger.warning(f"Aucun texte brut retourné par la fonction fetch pour '{target_url}' ({source_name_for_log}).")

        # Logique "Source_1" de HEAD
        if source_name_for_log == "Source_1" and texte_brut_source is not None:
            fetch_logger.info(f"--- LOGGING SPÉCIFIQUE POUR Source_1 (après fetch) ---")
            fetch_logger.info(f"Full text length: {len(texte_brut_source)}")
            fetch_logger.info(f"Premiers 500 chars:\n{texte_brut_source[:500]}")
            fetch_logger.info(f"Derniers 500 chars:\n{texte_brut_source[-500:]}")
            fetch_logger.info(f"--- FIN LOGGING SPÉCIFIQUE POUR Source_1 ---")
        
        return texte_brut_source

    except ConnectionError as e:
        fetch_logger.error(f"Erreur de connexion lors de la récupération de '{target_url}' ({source_name_for_log}, méthode: {fetch_method}): {e}")
        return None
    except Exception as e:
        fetch_logger.error(f"Erreur inattendue lors de la récupération de '{target_url}' ({source_name_for_log}, méthode: {fetch_method}): {e}", exc_info=True)
        return None

fetch_logger.info("Utilitaires de fetch UI définis.")

# Fonctions robustes internes pour les requêtes
@retry_on_network_error
@network_breaker
def _robust_get_request(url: str, **kwargs) -> Optional[requests.Response]:
    response = requests.get(url, **kwargs)
    response.raise_for_status()
    return response

@retry_on_network_error
@network_breaker
def _robust_put_request(url: str, **kwargs) -> Optional[requests.Response]:
    response = requests.put(url, **kwargs)
    response.raise_for_status()
    return response