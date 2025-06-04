"""
Opérations sur les fichiers pour l'interface utilisateur (UI) de l'analyse d'argumentation.

Ce module fournit des fonctions pour charger et sauvegarder les définitions d'extraits,
en gérant le chiffrement, la décompression et la validation de base du format.
Il interagit avec les modules de configuration et les services de cryptographie.
"""
from typing import Optional, Union, List, Dict, Any
# argumentation_analysis/ui/file_operations.py
import json
import gzip
import logging
import base64 # NOUVEAU: Pour décoder la clé b64 en clé Fernet
from pathlib import Path
from typing import Optional, List, Dict, Any
from cryptography.fernet import InvalidToken # NÉCESSAIRE pour lever l'exception
# cryptography.fernet et exceptions sont maintenant gérés dans project_core.utils.crypto_utils
# et les fonctions encrypt/decrypt sont importées depuis là.
# from cryptography.fernet import Fernet, InvalidToken # SUPPRIMÉ
# from cryptography.exceptions import InvalidSignature # SUPPRIMÉ

# Importer les éléments nécessaires depuis config et utils
# Attention à ne pas recréer de cycle.
# On importe 'config as ui_config_module' pour accéder aux constantes.
from . import config as ui_config_module
# On importe les fonctions de utils qui ne dépendent pas de config de manière cyclique.
# encrypt_data et decrypt_data sont maintenant importées depuis project_core
from .utils import get_full_text_for_source, utils_logger # utils_logger est déjà configuré dans utils.py
from argumentation_analysis.utils.core_utils.crypto_utils import encrypt_data_with_fernet, decrypt_data_with_fernet # NOUVEAU

# Logger spécifique pour les opérations sur fichiers si besoin, ou utiliser utils_logger
file_ops_logger = utils_logger # Ou logging.getLogger("App.UI.FileOps")


def load_extract_definitions(
    config_file: Path,
    b64_derived_key: Optional[str], # MODIFIÉ: La clé reçue est la chaîne b64 dérivée, rendue optionnelle
    # app_config est utilisé par get_full_text_for_source, mais load_extract_definitions
    # lui-même ne l'utilise pas directement pour le chargement/déchiffrement.
    # Cependant, si on voulait que load_extract_definitions peuple les full_text au chargement,
    # il faudrait le passer. Pour l'instant, on le garde optionnel et non utilisé ici.
    app_config: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """Charge, déchiffre (si clé fournie) et décompresse les définitions d'extraits.

    Tente de charger depuis `config_file`. Si `b64_derived_key` est fournie,
    tente de déchiffrer et décompresser. Sinon, tente de lire comme JSON simple.
    Utilise `ui_config_module.DEFAULT_EXTRACT_SOURCES` comme fallback en cas d'erreur.

    :param config_file: Chemin vers le fichier de configuration.
    :type config_file: Path
    :param b64_derived_key: La clé de chiffrement dérivée, encodée en base64 URL-safe.
                            Si None, le fichier est traité comme du JSON non chiffré.
    :type b64_derived_key: Optional[str]
    :param app_config: Configuration de l'application (non utilisée directement ici,
                       mais potentiellement par des fonctions appelées).
    :type app_config: Optional[Dict[str, Any]]
    :return: Une liste de dictionnaires représentant les définitions d'extraits.
             Retourne les définitions par défaut en cas d'échec de chargement/déchiffrement.
    :rtype: List[Dict[str, Any]]
    :raises InvalidToken: Si le déchiffrement échoue avec un token invalide (peut être
                          levée par `decrypt_data_with_fernet` si non attrapée là).
    :raises json.JSONDecodeError: Si le fichier traité comme JSON simple est malformé.
    """
    fallback_definitions = ui_config_module.EXTRACT_SOURCES if ui_config_module.EXTRACT_SOURCES else ui_config_module.DEFAULT_EXTRACT_SOURCES

    if not config_file.exists():
        file_ops_logger.info(f"Fichier config '{config_file}' non trouvé. Utilisation définitions par défaut.")
        return [item.copy() for item in fallback_definitions]

    if b64_derived_key: # Clé fournie, tenter le déchiffrement
        file_ops_logger.info(f"Chargement et déchiffrement de '{config_file}' avec clé...")
        try:
            with open(config_file, 'rb') as f: encrypted_data = f.read()
            decrypted_compressed_data = decrypt_data_with_fernet(encrypted_data, b64_derived_key)
            
            if not decrypted_compressed_data: # decrypt_data_with_fernet retourne None en cas d'InvalidToken ou autre erreur de déchiffrement
                file_ops_logger.warning(f"⚠️ Échec du déchiffrement pour '{config_file}' (decrypt_data_with_fernet a retourné None). Utilisation des définitions par défaut.")
                return [item.copy() for item in fallback_definitions] # MODIFIÉ: Retourner fallback au lieu de lever
            
            decompressed_data = gzip.decompress(decrypted_compressed_data)
            definitions = json.loads(decompressed_data.decode('utf-8'))
            file_ops_logger.info("✅ Définitions chargées et déchiffrées.")

        except InvalidToken: # Attrapé si decrypt_data_with_fernet lève InvalidToken (par ex. mock avec side_effect)
            file_ops_logger.error(f"❌ InvalidToken explicitement levée lors du déchiffrement de '{config_file}'. Utilisation définitions par défaut.", exc_info=True)
            return [item.copy() for item in fallback_definitions] # MODIFIÉ: Retourner fallback
        except Exception as e:
            file_ops_logger.error(f"❌ Erreur chargement/déchiffrement '{config_file}': {e}. Utilisation définitions par défaut.", exc_info=True)
            return [item.copy() for item in fallback_definitions]
    
    else: # Pas de clé, essayer de lire comme JSON simple
        file_ops_logger.info(f"Aucune clé fournie. Tentative de chargement de '{config_file}' comme JSON simple...")
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                definitions = json.load(f)
            file_ops_logger.info(f"✅ Définitions chargées comme JSON simple depuis '{config_file}'.")
        
        except json.JSONDecodeError as e_json:
            file_ops_logger.error(f"❌ Erreur décodage JSON pour '{config_file}': {e_json}. L'exception sera relancée.", exc_info=False)
            raise
        except Exception as e:
            file_ops_logger.error(f"❌ Erreur chargement JSON simple '{config_file}': {e}. Utilisation définitions par défaut.", exc_info=True)
            return [item.copy() for item in fallback_definitions]

    # Validation du format (commun aux deux chemins)
    if not isinstance(definitions, list) or not all(
        isinstance(item, dict) and
        "source_name" in item and "source_type" in item and "schema" in item and
        "host_parts" in item and "path" in item and isinstance(item.get("extracts"), list)
        for item in definitions
    ):
        file_ops_logger.warning(f"⚠️ Format définitions invalide après chargement de '{config_file}'. Utilisation définitions par défaut.")
        return [item.copy() for item in fallback_definitions]

    file_ops_logger.info(f"-> {len(definitions)} définitions chargées depuis '{config_file}'.")
    return definitions

def save_extract_definitions(
    extract_definitions: List[Dict[str, Any]],
    config_file: Path,
    b64_derived_key: Optional[Union[str, bytes]], # MODIFIÉ: Accepte str, bytes ou None
    embed_full_text: bool = False,
    config: Optional[Dict[str, Any]] = None # 'config' est le app_config passé à get_full_text_for_source
) -> bool:
    """Sauvegarde les définitions d'extraits, en les compressant et chiffrant si une clé est fournie.

    Peut optionnellement récupérer et embarquer le texte complet des sources avant la sauvegarde.

    :param extract_definitions: La liste des définitions d'extraits à sauvegarder.
    :type extract_definitions: List[Dict[str, Any]]
    :param config_file: Chemin vers le fichier de configuration de sortie.
    :type config_file: Path
    :param b64_derived_key: La clé de chiffrement dérivée, encodée en base64 URL-safe.
                            Si None ou vide, la sauvegarde chiffrée est annulée.
    :type b64_derived_key: Optional[Union[str, bytes]]
    :param embed_full_text: Si True, tente de récupérer et d'inclure le `full_text`
                            pour chaque source avant la sauvegarde. Par défaut à False.
    :type embed_full_text: bool
    :param config: Configuration de l'application, passée à `get_full_text_for_source`
                   si `embed_full_text` est True.
    :type config: Optional[Dict[str, Any]]
    :return: True si la sauvegarde (potentiellement chiffrée) a réussi, False sinon.
    :rtype: bool
    :raises ValueError: Si le chiffrement échoue après la compression des données
                        (par exemple, `encrypt_data_with_fernet` retourne None).
    """
    if not b64_derived_key: # Vérifie si la clé est None ou une chaîne/bytes vide
        file_ops_logger.error("Clé chiffrement (b64_derived_key) absente ou vide. Sauvegarde annulée.")
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
        # actual_fernet_key = base64.urlsafe_b64decode(b64_derived_key.encode('utf-8')) # SUPPRIMÉ: La fonction attend la str b64
        json_data = json.dumps(definitions_to_process, indent=2, ensure_ascii=False).encode('utf-8') # Utiliser la copie traitée
        compressed_data = gzip.compress(json_data)
        # MODIFIÉ: Utilisation de encrypt_data_with_fernet avec la clé b64_derived_key (str)
        encrypted_data_to_save = encrypt_data_with_fernet(compressed_data, b64_derived_key)
        if not encrypted_data_to_save:
            # encrypt_data_with_fernet logge déjà l'erreur
            raise ValueError("Échec du chiffrement des données (encrypt_data_with_fernet a retourné None).")

        config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(config_file, 'wb') as f:
            f.write(encrypted_data_to_save)
        file_ops_logger.info(f"✅ Définitions sauvegardées dans '{config_file}'.")
        return True
    except Exception as e:
        file_ops_logger.error(f"❌ Erreur lors de la sauvegarde chiffrée vers '{config_file}': {e}", exc_info=True)
        return False

file_ops_logger.info("Fonctions d'opérations sur fichiers UI définies.")