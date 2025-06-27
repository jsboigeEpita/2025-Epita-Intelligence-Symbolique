# -*- coding: utf-8 -*-
"""
I/O Manager for handling all file read/write operations.
"""
from typing import Optional, Union, List, Dict, Any
import json
import gzip
import logging
from pathlib import Path
from cryptography.fernet import InvalidToken

from argumentation_analysis.core.utils.crypto_utils import encrypt_data_with_fernet, decrypt_data_with_fernet

io_logger = logging.getLogger(__name__)


def load_extract_definitions(
    config_file: Path,
    b64_derived_key: Optional[str],
    app_config: Optional[Dict[str, Any]] = None,
    raise_on_decrypt_error: bool = False,
    fallback_definitions: Optional[List[Dict[str, Any]]] = None
) -> list:
    """Charge, déchiffre et décompresse les définitions depuis le fichier chiffré."""
    if fallback_definitions is None:
        fallback_definitions = []

    if not config_file.exists():
        io_logger.info(f"Fichier config '{config_file}' non trouvé. Utilisation définitions par défaut.")
        return [item.copy() for item in fallback_definitions]

    if b64_derived_key:  # Clé fournie, tenter le déchiffrement
        io_logger.info(f"Chargement et déchiffrement de '{config_file}' avec clé...")
        try:
            with open(config_file, 'rb') as f:
                encrypted_data = f.read()
            decrypted_compressed_data = decrypt_data_with_fernet(encrypted_data, b64_derived_key)

            if not decrypted_compressed_data:
                io_logger.error(f"Échec du déchiffrement pour '{config_file}'. Le token est peut-être invalide.")
                raise InvalidToken(f"Échec du déchiffrement pour '{config_file}'.")

            decompressed_data = gzip.decompress(decrypted_compressed_data)
            definitions = json.loads(decompressed_data.decode('utf-8'))
            io_logger.info("✅ Définitions chargées et déchiffrées.")

        except InvalidToken:
            io_logger.error(f"❌ Token invalide (InvalidToken) lors du déchiffrement de '{config_file}'.", exc_info=True)
            if raise_on_decrypt_error:
                raise
            return [item.copy() for item in fallback_definitions]
        except Exception as e:
            io_logger.error(f"[FAIL] Erreur chargement/dechiffrement '{config_file}': {e}. Utilisation definitions par defaut.", exc_info=True)
            return [item.copy() for item in fallback_definitions]

    else:  # Pas de clé, essayer de lire comme JSON simple
        io_logger.info(f"Aucune clé fournie. Tentative de chargement de '{config_file}' comme JSON simple...")
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                definitions = json.load(f)
            io_logger.info(f"[OK] Définitions chargées comme JSON simple depuis '{config_file}'.")

        except json.JSONDecodeError as e_json:
            io_logger.error(f"[FAIL] Erreur decodage JSON pour '{config_file}': {e_json}. L'exception sera relancee.", exc_info=False)
            raise
        except Exception as e:
            io_logger.error(f"[FAIL] Erreur chargement JSON simple '{config_file}': {e}. Utilisation definitions par defaut.", exc_info=True)
            return [item.copy() for item in fallback_definitions]

    # Validation du format (commun aux deux chemins)
    if not isinstance(definitions, list) or not all(
        isinstance(item, dict) and
        "source_name" in item and "source_type" in item and "schema" in item and
        "host_parts" in item and "path" in item and isinstance(item.get("extracts"), list)
        for item in definitions
    ):
        io_logger.warning(f"[WARN] Format definitions invalide apres chargement de '{config_file}'. Utilisation definitions par defaut.")
        return [item.copy() for item in fallback_definitions]

    io_logger.info(f"-> {len(definitions)} définitions chargées depuis '{config_file}'.")
    return definitions

def save_extract_definitions(
    extract_definitions: List[Dict[str, Any]],
    config_file: Path,
    b64_derived_key: Optional[Union[str, bytes]],
    embed_full_text: bool = False,
    config: Optional[Dict[str, Any]] = None,
    text_retriever: Optional[Any] = None # Fonction pour récupérer le texte
) -> bool:
    """Sauvegarde, compresse et chiffre les définitions dans le fichier.
    Peut optionnellement embarquer le texte complet des sources.
    """
    if not b64_derived_key:
        io_logger.error("Clé chiffrement (b64_derived_key) absente ou vide. Sauvegarde annulée.")
        return False
    if not isinstance(extract_definitions, list):
        io_logger.error("Erreur sauvegarde: définitions non valides (doit être une liste).")
        return False

    io_logger.info(f"Préparation sauvegarde vers '{config_file}'...")

    definitions_to_process = [dict(d) for d in extract_definitions]

    if embed_full_text:
        if not text_retriever:
            io_logger.warning("Option 'embed_full_text' activée mais aucun 'text_retriever' n'est fourni. Impossible de récupérer les textes.")
        else:
            io_logger.info("Option embed_full_text activée. Tentative de récupération des textes complets manquants...")
            for source_info in definitions_to_process:
                if not isinstance(source_info, dict):
                    io_logger.warning(f"Élément non-dictionnaire ignoré dans extract_definitions: {type(source_info)}")
                    continue

                current_full_text = source_info.get("full_text")
                if not current_full_text:
                    source_name = source_info.get('source_name', 'Source inconnue')
                    io_logger.info(f"Texte complet manquant pour '{source_name}'. Récupération...")
                    try:
                        retrieved_text = text_retriever(source_info, app_config=config)
                        if retrieved_text is not None:
                            source_info["full_text"] = retrieved_text
                            io_logger.info(f"Texte complet récupéré et ajouté pour '{source_name}'.")
                        else:
                            io_logger.warning(f"Échec de la récupération du texte complet (texte vide retourné) pour '{source_name}'. Champ 'full_text' non peuplé.")
                            source_info["full_text"] = None
                    except ConnectionError as e_conn:
                        io_logger.warning(f"Erreur de connexion lors de la récupération du texte pour '{source_name}': {e_conn}. Champ 'full_text' non peuplé.")
                        source_info["full_text"] = None
                    except Exception as e_get_text:
                        io_logger.error(f"Erreur inattendue lors de la récupération du texte pour '{source_name}': {e_get_text}. Champ 'full_text' non peuplé.", exc_info=True)
                        source_info["full_text"] = None
    else:
        io_logger.info("Option embed_full_text désactivée. Suppression des textes complets des définitions...")
        for source_info in definitions_to_process:
            if not isinstance(source_info, dict):
                continue
            if "full_text" in source_info:
                source_info.pop("full_text", None)
                io_logger.debug(f"Champ 'full_text' retiré pour '{source_info.get('source_name', 'Source inconnue')}'.")

    try:
        json_data = json.dumps(definitions_to_process, indent=2, ensure_ascii=False).encode('utf-8')
        compressed_data = gzip.compress(json_data)
        encrypted_data_to_save = encrypt_data_with_fernet(compressed_data, b64_derived_key)
        if not encrypted_data_to_save:
            raise ValueError("Échec du chiffrement des données (encrypt_data_with_fernet a retourné None).")

        config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(config_file, 'wb') as f:
            f.write(encrypted_data_to_save)
        io_logger.info(f"[OK] Définitions sauvegardées dans '{config_file}'.")
        return True
    except Exception as e:
        io_logger.error(f"[FAIL] Erreur lors de la sauvegarde chiffrée vers '{config_file}': {e}", exc_info=True)
        return False

io_logger.info("I/O Manager (core) défini.")