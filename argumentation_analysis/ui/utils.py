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
    if not schema or not host_parts or not path: return None
    host = ".".join(part for part in host_parts if part)
    path = path if path.startswith('/') or not path else '/' + path
    return f"{schema}//{host}{path}"

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
    except (InvalidToken, InvalidSignature, Exception) as e:
        utils_logger.error(f"Erreur déchiffrement: {e}")
        return None

def load_extract_definitions(config_file: Path, key: bytes) -> list:
    """Charge, déchiffre et décompresse les définitions depuis le fichier chiffré."""
    # Utilise les variables globales du module config
    fallback_definitions = ui_config.EXTRACT_SOURCES if ui_config.EXTRACT_SOURCES else ui_config.DEFAULT_EXTRACT_SOURCES

    if not config_file.exists():
        utils_logger.info(f"Fichier config chiffré '{config_file}' non trouvé. Utilisation définitions par défaut.")
        # Important: retourner une COPIE pour éviter modification accidentelle de l'original
        return [item.copy() for item in fallback_definitions]
    if not key:
        utils_logger.warning("Clé chiffrement absente. Chargement config impossible. Utilisation définitions par défaut.")
        return [item.copy() for item in fallback_definitions]

    utils_logger.info(f"Chargement et déchiffrement de '{config_file}'...")
    try:
        with open(config_file, 'rb') as f: encrypted_data = f.read()
        decrypted_compressed_data = decrypt_data(encrypted_data, key)
        if not decrypted_compressed_data:
            utils_logger.warning("Échec déchiffrement. Utilisation définitions par défaut.")
            return [item.copy() for item in fallback_definitions]
        decompressed_data = gzip.decompress(decrypted_compressed_data)
        definitions = json.loads(decompressed_data.decode('utf-8'))
        utils_logger.info("✅ Définitions chargées et déchiffrées.")

        # Validation (peut être externalisée)
        if not isinstance(definitions, list) or not all(
            isinstance(item, dict) and
            "source_name" in item and "source_type" in item and "schema" in item and
            "host_parts" in item and "path" in item and isinstance(item.get("extracts"), list)
            for item in definitions
        ):
            utils_logger.warning("⚠️ Format définitions invalide après chargement. Utilisation définitions par défaut.")
            return [item.copy() for item in fallback_definitions]

        # Mettre à jour la variable dans ui.config si chargement OK
        # Attention: modifier une variable importée peut avoir des effets de bord inattendus
        # Il serait préférable de retourner les définitions et de les gérer dans app.py
        # ui_config.EXTRACT_SOURCES = definitions # <- Eviter ceci si possible
        utils_logger.info(f"-> {len(definitions)} définitions chargées depuis fichier.")
        # Plutôt retourner les définitions chargées
        return definitions
    except Exception as e:
        utils_logger.error(f"❌ Erreur chargement/traitement '{config_file}': {e}. Utilisation définitions par défaut.", exc_info=True)
        return [item.copy() for item in fallback_definitions]

def save_extract_definitions(definitions: list, config_file: Path, key: bytes) -> bool:
    """Sauvegarde, compresse et chiffre les définitions dans le fichier."""
    if not key:
        utils_logger.error("Clé chiffrement absente. Sauvegarde annulée.")
        return False
    if not isinstance(definitions, list):
        utils_logger.error("Erreur sauvegarde: définitions non valides.")
        return False
    utils_logger.info(f"Préparation sauvegarde vers '{config_file}'...")
    try:
        json_data = json.dumps(definitions, indent=2, ensure_ascii=False).encode('utf-8')
        compressed_data = gzip.compress(json_data)
        encrypted_data = encrypt_data(compressed_data, key)
        if not encrypted_data: raise ValueError("Échec chiffrement.")
        config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(config_file, 'wb') as f: f.write(encrypted_data)
        utils_logger.info(f"✅ Définitions sauvegardées dans '{config_file}'.")
        return True
    except Exception as e:
        utils_logger.error(f"❌ Erreur sauvegarde chiffrée: {e}", exc_info=True)
        return False

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

def fetch_with_jina(source_url: str, timeout: int = 90) -> str:
    """Récupère et extrait via Jina, utilise cache fichier."""
    # Utilise les fonctions de cache de ce module et config JINA_READER_PREFIX
    cached_text = load_from_cache(source_url)
    if cached_text is not None: return cached_text
    jina_url = f"{ui_config.JINA_READER_PREFIX}{source_url}"
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
    timeout_tika: int = 600
    ) -> str:
    """Traite une source via Tika avec gestion cache brut et type texte."""
    # Utilise cache, config (TIKA_SERVER_URL, PLAINTEXT_EXTENSIONS, TEMP_DOWNLOAD_DIR)
    cache_key = source_url if source_url else f"file://{file_name}"
    cached_text = load_from_cache(cache_key)
    if cached_text is not None: return cached_text

    content_to_send = None
    temp_download_dir = ui_config.TEMP_DOWNLOAD_DIR # Utiliser le chemin depuis config

    if source_url:
        original_filename = Path(source_url).name
        if any(source_url.lower().endswith(ext) for ext in ui_config.PLAINTEXT_EXTENSIONS):
            utils_logger.info(f"   -> URL détectée comme texte simple ({source_url}). Fetch direct.")
            return fetch_direct_text(source_url) # Appel fonction de ce module

        # Gestion cache brut
        url_hash = hashlib.sha256(source_url.encode()).hexdigest()
        file_extension = Path(original_filename).suffix if Path(original_filename).suffix else ".download"
        effective_raw_cache_path = Path(raw_file_cache_path) if raw_file_cache_path else temp_download_dir / f"{url_hash}{file_extension}"

        if effective_raw_cache_path.exists() and effective_raw_cache_path.stat().st_size > 0:
             # ... [Code identique pour lire cache brut] ...
             try:
                utils_logger.info(f"   -> Lecture fichier brut depuis cache local : {effective_raw_cache_path.name}")
                content_to_send = effective_raw_cache_path.read_bytes()
             except Exception as e_read_raw:
                utils_logger.warning(f"   -> Erreur lecture cache brut {effective_raw_cache_path.name}: {e_read_raw}. Re-téléchargement...")
                content_to_send = None

        if content_to_send is None:
             # ... [Code identique pour télécharger et sauvegarder cache brut] ...
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
        # ... [Code identique pour gérer file_content] ...
        utils_logger.info(f"-> Utilisation contenu fichier '{file_name}' ({len(file_content)} bytes)...")
        content_to_send = file_content
        if any(file_name.lower().endswith(ext) for ext in ui_config.PLAINTEXT_EXTENSIONS):
            utils_logger.info("   -> Fichier uploadé détecté comme texte simple. Lecture directe.")
            try:
                texte_brut = file_content.decode('utf-8', errors='ignore')
                save_to_cache(cache_key, texte_brut) # Appel fonction de ce module
                return texte_brut
            except Exception as e_decode:
                utils_logger.warning(f"   -> Erreur décodage fichier texte '{file_name}': {e_decode}. Tentative avec Tika...")

    else:
        raise ValueError("fetch_with_tika: Il faut soit source_url soit file_content.")

    # ... [Code identique pour envoyer à Tika et sauvegarder cache texte final] ...
    if not content_to_send:
        utils_logger.warning("   -> Contenu brut vide ou non récupéré. Impossible d'envoyer à Tika.")
        save_to_cache(cache_key, "")
        return ""

    utils_logger.info(f"-> Envoi contenu à Tika ({ui_config.TIKA_SERVER_URL})... (Timeout={timeout_tika}s)")
    headers = { 'Accept': 'text/plain', 'Content-Type': 'application/octet-stream', 'X-Tika-OCRLanguage': 'fra+eng' }
    try:
        response_tika = requests.put(ui_config.TIKA_SERVER_URL, data=content_to_send, headers=headers, timeout=timeout_tika)
        response_tika.raise_for_status()
        texte_brut = response_tika.text
        if not texte_brut: utils_logger.warning(f"   -> Warning: Tika status {response_tika.status_code} sans texte.")
        else: utils_logger.info(f"   -> Texte Tika extrait (longueur {len(texte_brut)}).")
        save_to_cache(cache_key, texte_brut) # Appel fonction de ce module
        return texte_brut
    except requests.exceptions.Timeout:
        utils_logger.error(f"   -> ❌ Timeout Tika ({timeout_tika}s).")
        raise ConnectionError(f"Timeout Tika")
    except requests.exceptions.RequestException as e:
        utils_logger.error(f"Erreur Tika: {e}")
        raise ConnectionError(f"Erreur Tika: {e}") from e


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

    utils_logger.info(f"\n{summary.replace('<br/>', '\n').replace('<li>', '- ').replace('</li>', '').replace('<ul>', '').replace('</ul>', '').replace('<strong>', '').replace('</strong>', '')}")
    return summary


utils_logger.info("Fonctions utilitaires UI définies.")