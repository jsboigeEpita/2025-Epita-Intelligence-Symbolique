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
        project_root = current_script_path.parent.parent
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
    
        # 4. Afficher la structure des données JSON
        if isinstance(decrypted_data, list):
            logger.info(f"Le fichier contient une liste de {len(decrypted_data)} éléments.")
            
            if args.source_id:
                found_source = False
                for item in decrypted_data:
                    if isinstance(item, dict) and item.get("id") == args.source_id:
                        logger.info(f"\n--- Détails pour la source ID: {args.source_id} ---")
                        logger.info(json.dumps(item, indent=2, ensure_ascii=False))
                        if "full_text" in item:
                            logger.info(f"\n--- Full Text pour source ID: {args.source_id} ---")
                            logger.info(item["full_text"] if item["full_text"] else "[VIDE]")
                            logger.info(f"--- Fin Full Text pour source ID: {args.source_id} ---")
                        else:
                            logger.info(f"Pas de champ 'full_text' pour la source ID: {args.source_id}")
                        found_source = True
                        break
                if not found_source:
                    logger.warning(f"Source avec ID '{args.source_id}' non trouvée dans les données déchiffrées.")
            elif args.all_french or args.all:
                logger.info(f"\n--- Inspection de {'toutes les sources françaises (filtrées)' if args.all_french else 'toutes les sources'} ---")
                keywords_fr = ["lemonde", "assemblee-nationale", "vie-publique", "conseil-constitutionnel", "elysee", ".fr/"]
                # Ajout de ".fr/" pour mieux cibler les domaines français.
                
                displayed_count = 0
                for i, item in enumerate(decrypted_data):
                    if not isinstance(item, dict):
                        logger.warning(f"Élément {i} n'est pas un dictionnaire, ignoré.")
                        continue

                    source_name = item.get("source_name", "").lower()
                    source_path = item.get("path", "").lower() # path peut être une URL complète
                    source_id_val = item.get("id", f"N/A_{i}")
                    host_parts = item.get("host_parts", [])
                    
                    # Construire une chaîne de domaine pour la recherche de ".fr"
                    domain_str = ".".join(host_parts).lower()

                    is_french_by_keyword = any(keyword in source_name for keyword in keywords_fr) or \
                                       any(keyword in source_path for keyword in keywords_fr) or \
                                       any(keyword in domain_str for keyword in keywords_fr)


                    if args.all or (args.all_french and is_french_by_keyword):
                        displayed_count += 1
                        logger.info(f"\n--- Source {i+1}/{len(decrypted_data)} (ID: {source_id_val}, Nom: {item.get('source_name', 'N/A')}) {'[FRANÇAISE]' if is_french_by_keyword else ''} ---")
                        logger.info(f"  Path: {item.get('path', 'N/A')}")
                        logger.info(f"  Host Parts: {host_parts}")
                        logger.info(f"  Type: {item.get('source_type', 'N/A')}, Fetch: {item.get('fetch_method', 'N/A')}")
                        
                        extracts = item.get("extracts", [])
                        if extracts:
                            logger.info(f"  Extraits ({len(extracts)}):")
                            for j, extract in enumerate(extracts):
                                logger.info(f"    {j+1}. Nom: {extract.get('extract_name', 'N/A')}")
                                logger.info(f"       Start: {extract.get('start_marker', 'N/A')}")
                                logger.info(f"       End:   {extract.get('end_marker', 'N/A')}")
                        else:
                            logger.info("  Aucun extrait défini pour cette source.")
                        
                        if "full_text" in item:
                            full_text_preview = item['full_text'][:200] + "..." if item['full_text'] else "[VIDE]"
                            logger.info(f"  Aperçu Full Text (200 premiers caractères): {full_text_preview}")
                        else:
                            logger.info("  Pas de champ 'full_text' pour cette source.")
                
                if displayed_count == 0:
                    if args.all_french:
                        logger.info("Aucune source française identifiée par les mots-clés actuels.")
                    else: # args.all mais la liste était vide
                        logger.info("Aucune source à afficher (la liste est peut-être vide).")

            else:
                # Comportement par défaut: afficher les deux premiers éléments
                if len(decrypted_data) > 0:
                    logger.info(f"\n--- Structure du premier élément ---")
                    first_item = decrypted_data[0]
                    logger.info(json.dumps(first_item, indent=2, ensure_ascii=False))
                    logger.info(f"Champs présents dans le premier élément: {list(first_item.keys())}")
                    if "full_text" in first_item and first_item["full_text"]:
                         logger.info(f"Aperçu Full Text (1er élément, 500 premiers caractères): {first_item['full_text'][:500]}")
                    logger.info(f"--- Fin de la structure du premier élément ---\n")
    
                if len(decrypted_data) > 1:
                    logger.info(f"\n--- Structure du deuxième élément ---")
                    second_item = decrypted_data[1]
                    logger.info(json.dumps(second_item, indent=2, ensure_ascii=False))
                    logger.info(f"Champs présents dans le deuxième élément: {list(second_item.keys())}")
                    if "full_text" in second_item and second_item["full_text"]:
                         logger.info(f"Aperçu Full Text (2ème élément, 500 premiers caractères): {second_item['full_text'][:500]}")
                    logger.info(f"--- Fin de la structure du deuxième élément ---\n")
                elif len(decrypted_data) == 1:
                    logger.info("Il n'y a qu'un seul élément dans la liste (déjà affiché).")
    
        elif isinstance(decrypted_data, dict):
            logger.info("Le fichier contient un dictionnaire (objet JSON).")
            logger.info(f"\n--- Structure des données (dictionnaire) ---")
            logger.info(json.dumps(decrypted_data, indent=2, ensure_ascii=False))
            logger.info(f"--- Fin de la structure des données (dictionnaire) ---\n")
        else:
            logger.warning(f"Les données déchiffrées ne sont ni une liste ni un dictionnaire (type: {type(decrypted_data)}).")
            logger.info(f"Aperçu des données: {str(decrypted_data)[:500]}")

        if args.output_json:
            output_file_path = Path(args.output_json)
            try:
                with open(output_file_path, 'w', encoding='utf-8') as f:
                    json.dump(decrypted_data, f, indent=2, ensure_ascii=False)
                logger.info(f"Données déchiffrées sauvegardées dans : {output_file_path.resolve()}")
            except Exception as e_write:
                logger.error(f"Erreur lors de la sauvegarde du JSON déchiffré dans {output_file_path}: {e_write}")
    
    except ImportError as e:
        logger.error(f"Erreur d'importation: {e}. Assurez-vous que le sys.path est correct et que les dépendances sont installées.", exc_info=True)
    except FileNotFoundError as e:
        logger.error(f"Erreur de fichier non trouvé: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"Une erreur inattendue est survenue: {e}", exc_info=True)

if __name__ == "__main__":
    main()