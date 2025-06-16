import project_core.core_from_scripts.auto_env
import sys
import os
from pathlib import Path
import json
import logging

# Configuration du logger pour ce script
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s', datefmt='%H:%M:%S')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG) # Changé en DEBUG

    # Mettre les loggers des modules concernés en DEBUG aussi
    logging.getLogger("App.UI.Utils").setLevel(logging.DEBUG)
    logging.getLogger("Services.CryptoService").setLevel(logging.DEBUG)

import argparse

def main():
    """
    Script principal pour déchiffrer et inspecter extract_sources.json.gz.enc.
    """
    parser = argparse.ArgumentParser(description="Déchiffre et inspecte le fichier extract_sources.json.gz.enc.")
    parser.add_argument("--source-id", type=str, help="ID de la source spécifique à inspecter.")
    parser.add_argument("--all-french", action="store_true", help="Affiche toutes les sources françaises et leurs extraits.")
    parser.add_argument("--all", action="store_true", help="Affiche toutes les sources et leurs extraits.")
    parser.add_argument("--output-json", type=str, help="Chemin vers lequel sauvegarder le JSON déchiffré.")
    args = parser.parse_args()

    try:
        # 1. Configurer sys.path pour inclure la racine du projet.
        # Ce script est dans scripts/, la racine est un niveau au-dessus.
        current_script_path = Path(__file__).resolve()
        project_root = current_script_path.parent.parent.parent # Remonter à la racine du projet
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))
        logger.info(f"Project root (from debug_inspect_extract_sources.py) added to sys.path: {project_root}")

        # Importer bootstrap après avoir configuré sys.path
        # from project_core.bootstrap import initialize_project_environment, ProjectContext # Non utilisé si on force la clé
        from argumentation_analysis.services.crypto_service import CryptoService # Import direct pour ré-instanciation
        # from dotenv import load_dotenv # Ne pas charger .env pour ce test spécifique
        from argumentation_analysis.ui.config import ENCRYPTION_KEY as CONFIG_UI_ENCRYPTION_KEY # Importer la clé de vérité

        # Initialiser un CryptoService local pour ce script directement avec la clé de ui.config
        key_configured = False
        local_crypto_service = CryptoService() # Instancier sans clé au départ

        if CONFIG_UI_ENCRYPTION_KEY:
            logger.info("Utilisation directe de ENCRYPTION_KEY depuis argumentation_analysis.ui.config pour CryptoService.")
            try:
                # CONFIG_UI_ENCRYPTION_KEY est déjà en bytes
                local_crypto_service.set_encryption_key(CONFIG_UI_ENCRYPTION_KEY)
                if local_crypto_service.is_encryption_enabled():
                    logger.info("CryptoService configuré avec succès avec la clé de ui.config.")
                    key_configured = True
                else:
                    # Cela ne devrait pas arriver si set_encryption_key fonctionne et que la clé est valide
                    logger.error("CryptoService initialisé avec la clé de ui.config, mais le chiffrement n'est pas activé. Problème interne avec la clé ou CryptoService.")
            except Exception as e:
                 logger.error(f"Erreur lors de la configuration de CONFIG_UI_ENCRYPTION_KEY dans CryptoService: {e}")
        else:
            logger.error("ENCRYPTION_KEY de argumentation_analysis.ui.config est None ou non disponible.")
            # local_crypto_service reste sans clé

        if not key_configured:
            logger.error("Impossible de configurer CryptoService avec la clé de ui.config. Arrêt du test de déchiffrement.")
            return

        # Les blocs suivants pour charger depuis env ou fallback sont maintenant redondants pour ce test spécifique
        # et ont été supprimés pour s'assurer que seule la clé de ui.config est testée.

        if not local_crypto_service:
            logger.error("CryptoService n'a pas pu être configuré pour le déchiffrement. Impossible de continuer.")
            return

        # 3. Utiliser le crypto_service local pour déchiffrer le fichier
        encrypted_file_path = project_root / "argumentation_analysis" / "data" / "extract_sources.json.gz.enc"
        logger.info(f"Tentative de déchiffrement de : {encrypted_file_path} avec le service local.")

        if not encrypted_file_path.exists():
            logger.error(f"Le fichier chiffré {encrypted_file_path} n'existe pas.")
            return
        
        # Lire le contenu binaire du fichier avant de le passer au service de déchiffrement
        try:
            logger.debug(f"Lecture du contenu binaire depuis: {encrypted_file_path}")
            encrypted_content_bytes = encrypted_file_path.read_bytes()
            logger.debug(f"Lu {len(encrypted_content_bytes)} bytes depuis {encrypted_file_path}")
        except Exception as e_read:
            logger.error(f"Erreur lors de la lecture du fichier {encrypted_file_path}: {e_read}")
            return

        # Passer les bytes lus à la méthode de déchiffrement
        decrypted_data = local_crypto_service.decrypt_and_decompress_json(encrypted_content_bytes)

        if decrypted_data is None:
            logger.error("Le déchiffrement a échoué ou le fichier est vide après déchiffrement (avec service local).")
            return

        logger.info("Déchiffrement réussi.")
    
        # 4. Utiliser la fonction centralisée pour afficher les détails
        display_extract_sources_details(
            extract_sources_data=decrypted_data if isinstance(decrypted_data, list) else [decrypted_data] if isinstance(decrypted_data, dict) else [],
            source_id_to_inspect=args.source_id,
            show_all_french=args.all_french,
            show_all=args.all,
            output_json_path=args.output_json # La fonction display gère la sauvegarde si le chemin est fourni
        )
        
        # La logique de sauvegarde JSON est maintenant dans display_extract_sources_details
        # (Le bloc commenté ci-dessous est supprimé car la fonction appelée s'en charge)
    
    except ImportError as e:
        logger.error(f"Erreur d'importation: {e}. Assurez-vous que le sys.path est correct et que les dépendances sont installées.", exc_info=True)
    except FileNotFoundError as e:
        logger.error(f"Erreur de fichier non trouvé: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"Une erreur inattendue est survenue: {e}", exc_info=True)

if __name__ == "__main__":
    main()