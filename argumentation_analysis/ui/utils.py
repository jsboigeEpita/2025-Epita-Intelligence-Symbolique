# ui/utils.py
import requests
import json
import gzip
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
from cryptography.fernet import Fernet, InvalidToken
from cryptography.exceptions import InvalidSignature
from pybreaker import CircuitBreakerError
from tenacity import RetryError

# Le reste des imports et du code...

# Import config depuis le même package ui
from . import config as ui_config

# #2344: the cache and the fetchers of this module were a parallel copy of
# services/cache_service and services/fetch_service (same directory, same file
# names), without their repairs. They delegate to the services now.
# get_cache_filepath is re-exported: agents/initialize_cache.py and ui/app.py
# import it from here.
from .cache_utils import (  # noqa: F401
    cache_service,
    get_cache_filepath,
    load_from_cache,
    save_to_cache,
)
from ..services.fetch_service import FetchService

utils_logger = logging.getLogger("App.UI.Utils")
if not utils_logger.handlers and not utils_logger.propagate:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] [%(name)s] %(message)s", datefmt="%H:%M:%S"
    )
    handler.setFormatter(formatter)
    utils_logger.addHandler(handler)
    utils_logger.setLevel(logging.INFO)

# --- Fonctions Utilitaires (Cache, Crypto, Fetch, Verify) ---


def reconstruct_url(schema: str, host_parts: list, path: str) -> Optional[str]:
    """Reconstruit une URL à partir de schema, host_parts, et path."""
    if not schema or not host_parts:
        return None  # Path peut être vide et géré ci-dessous
    host = ".".join(part for part in host_parts if part)
    # Si path est None, on le traite comme une chaîne vide pour la logique suivante
    current_path = path if path is not None else ""
    current_path = (
        current_path
        if current_path.startswith("/") or not current_path
        else "/" + current_path
    )
    # S'assurer qu'un path vide après traitement devienne au moins "/"
    if not current_path:
        current_path = "/"
    return f"{schema}://{host}{current_path}"


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
    except (
        InvalidToken,
        InvalidSignature,
    ) as e:  # Intercepter spécifiquement et relancer
        utils_logger.error(f"Erreur déchiffrement (InvalidToken/Signature): {e}")
        raise  # Relancer l'exception capturée (InvalidToken ou InvalidSignature)
    except Exception as e:  # Intercepter les autres exceptions
        utils_logger.error(f"Erreur déchiffrement (Autre): {e}")
        return None


# Les fonctions load_extract_definitions et save_extract_definitions ont été déplacées
# vers argumentation_analysis/ui/file_operations.py pour éviter les imports circulaires.

# What FetchService lets through when nothing could be fetched: the network
# error once its retries are spent, or its circuit breaker when open.
_FETCH_FAILURES = (
    requests.exceptions.RequestException,
    RetryError,
    CircuitBreakerError,
)


def _fetch_service(
    jina_reader_prefix: Optional[str] = None,
    tika_server_url: Optional[str] = None,
    plaintext_extensions: Optional[List[str]] = None,
    temp_download_dir: Optional[Path] = None,
) -> FetchService:
    """A FetchService on the UI cache (#2344).

    The fetchers below keep this module's contract (cache first, a
    ``ConnectionError`` when nothing could be fetched) and leave the fetching,
    the decoding and the caching to the service.
    """
    return FetchService(
        cache_service(),
        jina_reader_prefix=(
            ui_config.JINA_READER_PREFIX
            if jina_reader_prefix is None
            else jina_reader_prefix
        ),
        tika_server_url=tika_server_url,
        temp_download_dir=temp_download_dir,
        plaintext_extensions=plaintext_extensions,
    )


def fetch_direct_text(source_url: str, timeout: int = 60) -> str:
    """Récupère contenu texte brut d'URL, utilise cache fichier."""
    cached_text = load_from_cache(source_url)
    if cached_text is not None:
        return cached_text
    utils_logger.info(f"-> Téléchargement direct depuis : {source_url}...")
    try:
        texte_brut = _fetch_service().fetch_direct_text(source_url, timeout=timeout)
    except _FETCH_FAILURES as e:
        utils_logger.error(f"Erreur téléchargement direct ({source_url}): {e}")
        raise ConnectionError(
            f"Erreur téléchargement direct ({source_url}): {e}"
        ) from e
    if texte_brut is None:
        raise ConnectionError(
            f"Téléchargement direct ({source_url}) : aucun contenu (disjoncteur ouvert)."
        )
    return texte_brut


def fetch_with_jina(
    source_url: str,
    timeout: int = 90,
    jina_reader_prefix_override: Optional[str] = None,
) -> str:
    """Récupère et extrait via Jina, utilise cache fichier."""
    cached_text = load_from_cache(source_url)
    if cached_text is not None:
        return cached_text

    _jina_reader_prefix = (
        jina_reader_prefix_override
        if jina_reader_prefix_override is not None
        else ui_config.JINA_READER_PREFIX
    )
    jina_url = f"{_jina_reader_prefix}{source_url}"

    utils_logger.info(f"-> Récupération via Jina : {jina_url}...")
    try:
        texte_brut = _fetch_service(_jina_reader_prefix).fetch_with_jina(
            source_url, timeout=timeout
        )
    except _FETCH_FAILURES as e:
        utils_logger.error(f"Erreur Jina ({jina_url}): {e}")
        raise ConnectionError(f"Erreur Jina ({jina_url}): {e}") from e
    if texte_brut is None:
        raise ConnectionError(
            f"Jina ({jina_url}) : aucun contenu (disjoncteur ouvert)."
        )
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
    temp_download_dir_override: Optional[Path] = None,
) -> str:
    """Traite une source via Tika avec gestion cache brut et type texte."""
    if not source_url and not file_content:
        raise ValueError("fetch_with_tika: Il faut soit source_url soit file_content.")
    _tika_server_url = (
        tika_server_url_override
        if tika_server_url_override is not None
        else ui_config.TIKA_SERVER_URL
    )
    _plaintext_extensions = (
        plaintext_extensions_override
        if plaintext_extensions_override is not None
        else ui_config.PLAINTEXT_EXTENSIONS
    )
    _temp_download_dir = (
        temp_download_dir_override
        if temp_download_dir_override is not None
        else ui_config.TEMP_DOWNLOAD_DIR
    )

    cache_key = source_url if source_url else f"file://{file_name}"
    cached_text = load_from_cache(cache_key)
    if cached_text is not None:
        return cached_text

    service = _fetch_service(
        tika_server_url=_tika_server_url,
        plaintext_extensions=_plaintext_extensions,
        temp_download_dir=_temp_download_dir,
    )
    try:
        texte_brut = service.fetch_with_tika(
            url=source_url,
            file_content=file_content,
            file_name=file_name,
            raw_file_cache_path=raw_file_cache_path,
            timeout_dl=timeout_dl,
            timeout_tika=timeout_tika,
        )
    except _FETCH_FAILURES as e:
        utils_logger.error(f"Erreur Tika ({cache_key}): {e}")
        raise ConnectionError(f"Erreur Tika ({cache_key}): {e}") from e
    if texte_brut is None:
        raise ConnectionError(
            f"Tika ({cache_key}) : aucun texte extrait, "
            "cause dans le journal Services.FetchService."
        )
    return texte_brut


def get_full_text_for_source(
    source_info: Dict[str, Any], app_config: Optional[Dict[str, Any]] = None
) -> Optional[str]:
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
    source_name_for_log = source_info.get("source_name", "Source inconnue")
    utils_logger.debug(f"get_full_text_for_source appelée pour: {source_name_for_log}")

    reconstructed_url = reconstruct_url(
        source_info.get("schema"),
        source_info.get("host_parts", []),
        source_info.get("path"),
    )
    if not reconstructed_url:
        utils_logger.error(f"URL invalide pour source: {source_name_for_log}")
        return None

    # Essayer de charger depuis le cache fichier d'abord
    cached_text = load_from_cache(reconstructed_url)
    if cached_text is not None:
        utils_logger.info(
            f"Texte chargé depuis cache fichier pour URL '{reconstructed_url}' ({source_name_for_log})"
        )
        return cached_text

    source_type = source_info.get("source_type")
    texte_brut_source: Optional[str] = None

    # Récupérer les configurations, en privilégiant app_config si fourni
    jina_prefix_val = ui_config.JINA_READER_PREFIX
    tika_server_url_val = ui_config.TIKA_SERVER_URL
    plaintext_extensions_val = ui_config.PLAINTEXT_EXTENSIONS
    temp_download_dir_val = ui_config.TEMP_DOWNLOAD_DIR

    if app_config:
        jina_prefix_val = app_config.get("JINA_READER_PREFIX", jina_prefix_val)
        tika_server_url_val = app_config.get("TIKA_SERVER_URL", tika_server_url_val)
        plaintext_extensions_val = app_config.get(
            "PLAINTEXT_EXTENSIONS", plaintext_extensions_val
        )
        # Pour TEMP_DOWNLOAD_DIR, s'assurer que c'est un objet Path si surchargé
        temp_download_dir_str_or_path = app_config.get("TEMP_DOWNLOAD_DIR")
        if temp_download_dir_str_or_path is not None:
            temp_download_dir_val = Path(temp_download_dir_str_or_path)

    utils_logger.info(
        f"Cache texte absent pour '{reconstructed_url}' ({source_name_for_log}). Récupération (type: {source_type})..."
    )
    try:
        if source_type == "jina":
            texte_brut_source = fetch_with_jina(
                reconstructed_url, jina_reader_prefix_override=jina_prefix_val
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
                temp_download_dir_override=temp_download_dir_val,
                # raw_file_cache_path n'est pas géré par app_config ici, fetch_with_tika le déduit si besoin
            )
        else:
            utils_logger.warning(
                f"Type de source inconnu '{source_type}' pour '{reconstructed_url}' ({source_name_for_log}). Impossible de récupérer le texte."
            )
            return None

        if texte_brut_source is not None:
            utils_logger.info(
                f"Texte récupéré pour '{reconstructed_url}' ({source_name_for_log}), sauvegarde dans le cache..."
            )
            save_to_cache(reconstructed_url, texte_brut_source)
        else:
            utils_logger.warning(
                f"Aucun texte brut retourné par la fonction fetch pour '{reconstructed_url}' ({source_name_for_log})."
            )

        return texte_brut_source

    except ConnectionError as e:  # Erreurs spécifiques levées par les fetch_*
        utils_logger.error(
            f"Erreur de connexion lors de la récupération de '{reconstructed_url}' ({source_name_for_log}, type: {source_type}): {e}"
        )
        return None
    except Exception as e:
        utils_logger.error(
            f"Erreur inattendue lors de la récupération de '{reconstructed_url}' ({source_name_for_log}, type: {source_type}): {e}",
            exc_info=True,
        )
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
                source_info.get("schema"),
                source_info.get("host_parts", []),
                source_info.get("path"),
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
                utils_logger.info(
                    f"   -> Cache texte absent. Récupération (type: {source_type})..."
                )
                try:
                    if source_type == "jina":
                        texte_brut_source = fetch_with_jina(reconstructed_url)
                    elif source_type == "direct_download":
                        texte_brut_source = fetch_direct_text(reconstructed_url)
                    elif source_type == "tika":
                        is_plaintext = any(
                            source_info.get("path", "").lower().endswith(ext)
                            for ext in ui_config.PLAINTEXT_EXTENSIONS
                        )
                        if is_plaintext:
                            texte_brut_source = fetch_direct_text(reconstructed_url)
                        else:
                            utils_logger.warning(
                                "   -> ⚠️ Vérification marqueurs sautée pour source Tika binaire."
                            )
                            texte_brut_source = None
                    else:
                        utils_logger.warning(
                            f"   -> ⚠️ Type source inconnu '{source_type}'. Vérification impossible."
                        )
                        texte_brut_source = None
                except Exception as e_fetch_verify:
                    utils_logger.error(
                        f"   -> ❌ Erreur fetch pendant vérification pour '{source_name}': {e_fetch_verify}"
                    )
                    texte_brut_source = None

            # ... [Reste de la logique de vérification des marqueurs - IDENTIQUE A AVANT] ...
            if texte_brut_source is not None:
                utils_logger.info(
                    f"   -> Texte complet récupéré (longueur: {len(texte_brut_source)}). Vérification des extraits..."
                )
                extracts = source_info.get("extracts", [])
                if not extracts:
                    utils_logger.info("      -> Aucun extrait défini.")

                for extract_idx, extract_info in enumerate(extracts):
                    extract_name = extract_info.get(
                        "extract_name", f"Extrait #{extract_idx+1}"
                    )
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
                                end_found_after_start = (
                                    end_marker
                                    in texte_brut_source[
                                        start_pos + len(start_marker) :
                                    ]
                                )
                            except ValueError:
                                start_found = False
                        if not start_found:
                            marker_errors.append("Début NON TROUVÉ")
                        if not end_found_after_start:
                            marker_errors.append("Fin NON TROUVÉE (après début)")

                    if marker_errors:
                        utils_logger.warning(
                            f"      -> ❌ Problème Extrait '{extract_name}': {', '.join(marker_errors)}"
                        )
                        results.append(
                            f"<li>{source_name} -> {extract_name}: <strong style='color:red;'>{', '.join(marker_errors)}</strong></li>"
                        )
                        source_errors += 1
                        total_errors += 1
                    else:
                        utils_logger.info(f"      -> ✅ OK: Extrait '{extract_name}'")

            else:
                num_extracts = len(source_info.get("extracts", []))
                if source_type != "tika" or is_plaintext:
                    results.append(
                        f"<li>{source_name}: Vérification impossible (texte source non obtenu)</li>"
                    )
                    total_errors += num_extracts
                else:
                    results.append(
                        f"<li>{source_name}: Vérification marqueurs sautée (source Tika binaire)</li>"
                    )
                total_checks += num_extracts

        except Exception as e_verify_global:
            utils_logger.error(
                f"   -> ❌ Erreur inattendue vérification source '{source_name}': {e_verify_global}",
                exc_info=True,
            )
            num_extracts = len(source_info.get("extracts", []))
            results.append(
                f"<li>{source_name}: Erreur Vérification Générale ({type(e_verify_global).__name__})</li>"
            )
            total_errors += num_extracts
            total_checks += num_extracts

    # ... [Reste de la logique de formatage du résumé - IDENTIQUE A AVANT] ...
    summary = f"--- Résultat Vérification ---<br/>{total_checks} extraits vérifiés. <strong style='color: {'red' if total_errors > 0 else 'green'};'>{total_errors} erreur(s) trouvée(s).</strong>"
    if results:
        summary += "<br/>Détails :<ul>" + "".join(results) + "</ul>"
    else:
        if total_checks > 0:
            summary += "<br/>Tous les marqueurs semblent corrects."
        else:
            summary += "<br/>Aucun extrait n'a pu être vérifié."

    utils_logger.info(
        "\n"
        + f"{summary.replace('<br/>', chr(10)).replace('<li>', '- ').replace('</li>', '').replace('<ul>', '').replace('</ul>', '').replace('<strong>', '').replace('</strong>', '')}"
    )
    return summary


utils_logger.info("Fonctions utilitaires UI définies.")
