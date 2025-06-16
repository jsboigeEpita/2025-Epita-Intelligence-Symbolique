# argumentation_analysis/ui/file_operations.py
import json
import gzip
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from cryptography.fernet import Fernet, InvalidToken
from cryptography.exceptions import InvalidSignature

# Importer les éléments nécessaires depuis config et utils
# Attention à ne pas recréer de cycle.
# On importe 'config as ui_config_module' pour accéder aux constantes.
from . import config as ui_config_module
# On importe les fonctions de utils qui ne dépendent pas de config de manière cyclique.
from .utils import encrypt_data, decrypt_data, get_full_text_for_source, utils_logger # utils_logger est déjà configuré dans utils.py

# Logger spécifique pour les opérations sur fichiers si besoin, ou utiliser utils_logger
file_ops_logger = utils_logger # Ou logging.getLogger("App.UI.FileOps")


def load_extract_definitions(
    config_file: Path, 
    key: bytes,
    # app_config est utilisé par get_full_text_for_source, mais load_extract_definitions
    # lui-même ne l'utilise pas directement pour le chargement/déchiffrement.
    # Cependant, si on voulait que load_extract_definitions peuple les full_text au chargement,
    # il faudrait le passer. Pour l'instant, on le garde optionnel et non utilisé ici.
    app_config: Optional[Dict[str, Any]] = None 
) -> list:
    """Charge, déchiffre et décompresse les définitions depuis le fichier chiffré."""
    fallback_definitions = ui_config_module.EXTRACT_SOURCES if ui_config_module.EXTRACT_SOURCES else ui_config_module.DEFAULT_EXTRACT_SOURCES

    if not config_file.exists():
        file_ops_logger.info(f"Fichier config chiffré '{config_file}' non trouvé. Utilisation définitions par défaut.")
        return [item.copy() for item in fallback_definitions]
    if not key:
        file_ops_logger.warning("Clé chiffrement absente. Chargement config impossible. Utilisation définitions par défaut.")
        return [item.copy() for item in fallback_definitions]

    file_ops_logger.info(f"Chargement et déchiffrement de '{config_file}'...")
    try:
        with open(config_file, 'rb') as f: encrypted_data = f.read()
        decrypted_compressed_data = decrypt_data(encrypted_data, key) # Utilise decrypt_data de utils.py
        if not decrypted_compressed_data:
            file_ops_logger.warning("Échec déchiffrement. Utilisation définitions par défaut.")
            return [item.copy() for item in fallback_definitions]
        decompressed_data = gzip.decompress(decrypted_compressed_data)
        definitions = json.loads(decompressed_data.decode('utf-8'))
        file_ops_logger.info("✅ Définitions chargées et déchiffrées.")

        if not isinstance(definitions, list) or not all(
            isinstance(item, dict) and
            "source_name" in item and "source_type" in item and "schema" in item and
            "host_parts" in item and "path" in item and isinstance(item.get("extracts"), list)
            for item in definitions
        ):
            file_ops_logger.warning("⚠️ Format définitions invalide après chargement. Utilisation définitions par défaut.")
            return [item.copy() for item in fallback_definitions]

        file_ops_logger.info(f"-> {len(definitions)} définitions chargées depuis fichier.")
        return definitions
    except (InvalidToken, InvalidSignature) as e: # Intercepter spécifiquement et relancer
        file_ops_logger.error(f"❌ Erreur déchiffrement/validation token pour '{config_file}': {e}. L'exception sera relancée.", exc_info=True)
        raise # Relancer l'exception InvalidToken ou InvalidSignature
    except Exception as e:
        file_ops_logger.error(f"❌ Erreur chargement/traitement général '{config_file}': {e}. Utilisation définitions par défaut.", exc_info=True)
        return [item.copy() for item in fallback_definitions]

def save_extract_definitions(
    extract_definitions: List[Dict[str, Any]],
    config_file: Path, # Renommé de config_path pour correspondre à l'usage dans embed_all_sources.py
    encryption_key: bytes, # Renommé de passphrase pour refléter qu'une clé Fernet est attendue par encrypt_data
    embed_full_text: bool = False,
    config: Optional[Dict[str, Any]] = None # 'config' est le app_config passé à get_full_text_for_source
) -> bool:
    """Sauvegarde, compresse et chiffre les définitions dans le fichier.
    Peut optionnellement embarquer le texte complet des sources.
    """
    if not encryption_key:
        file_ops_logger.error("Clé chiffrement absente. Sauvegarde annulée.")
        return False
    if not isinstance(extract_definitions, list):
        file_ops_logger.error("Erreur sauvegarde: définitions non valides (doit être une liste).")
        return False

    file_ops_logger.info(f"Préparation sauvegarde vers '{config_file}'...")

    # Copie profonde pour éviter de modifier la liste originale en dehors de cette fonction
    # lors du traitement de embed_full_text
    definitions_to_process = [dict(d) for d in extract_definitions]


    if embed_full_text:
        file_ops_logger.info("Option embed_full_text activée. Tentative de récupération des textes complets manquants...")
        for source_info in definitions_to_process: # Utiliser la copie
            if not isinstance(source_info, dict):
                file_ops_logger.warning(f"Élément non-dictionnaire ignoré dans extract_definitions: {type(source_info)}")
                continue

            current_full_text = source_info.get("full_text")
            if not current_full_text:
                source_name = source_info.get('source_name', 'Source inconnue')
                file_ops_logger.info(f"Texte complet manquant pour '{source_name}'. Récupération...")
                try:
                    # Utilise get_full_text_for_source de utils.py
                    retrieved_text = get_full_text_for_source(source_info, app_config=config)
                    if retrieved_text is not None:
                        source_info["full_text"] = retrieved_text
                        file_ops_logger.info(f"Texte complet récupéré et ajouté pour '{source_name}'.")
                    else:
                        file_ops_logger.warning(f"Échec de la récupération du texte complet (texte vide retourné) pour '{source_name}'. Champ 'full_text' non peuplé.")
                        source_info["full_text"] = None
                except ConnectionError as e_conn:
                    file_ops_logger.warning(f"Erreur de connexion lors de la récupération du texte pour '{source_name}': {e_conn}. Champ 'full_text' non peuplé.")
                    source_info["full_text"] = None
                except Exception as e_get_text:
                    file_ops_logger.error(f"Erreur inattendue lors de la récupération du texte pour '{source_name}': {e_get_text}. Champ 'full_text' non peuplé.", exc_info=True)
                    source_info["full_text"] = None
    else:
        file_ops_logger.info("Option embed_full_text désactivée. Suppression des textes complets des définitions...")
        for source_info in definitions_to_process: # Utiliser la copie
            if not isinstance(source_info, dict):
                continue
            if "full_text" in source_info:
                source_info.pop("full_text", None)
                file_ops_logger.debug(f"Champ 'full_text' retiré pour '{source_info.get('source_name', 'Source inconnue')}'.")

    try:
        json_data = json.dumps(definitions_to_process, indent=2, ensure_ascii=False).encode('utf-8') # Utiliser la copie traitée
        compressed_data = gzip.compress(json_data)
        encrypted_data_to_save = encrypt_data(compressed_data, encryption_key) # Utilise encrypt_data de utils.py
        if not encrypted_data_to_save:
            raise ValueError("Échec du chiffrement des données.")

        config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(config_file, 'wb') as f:
            f.write(encrypted_data_to_save)
        file_ops_logger.info(f"✅ Définitions sauvegardées dans '{config_file}'.")
        return True
    except Exception as e:
        file_ops_logger.error(f"❌ Erreur lors de la sauvegarde chiffrée vers '{config_file}': {e}", exc_info=True)
        return False

file_ops_logger.info("Fonctions d'opérations sur fichiers UI définies.")