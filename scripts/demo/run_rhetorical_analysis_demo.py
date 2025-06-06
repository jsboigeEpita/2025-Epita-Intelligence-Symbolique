#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script de démonstration pour le flux d'analyse rhétorique.
"""

import os
import sys
import logging
import asyncio
import json
import gzip
import tempfile
from pathlib import Path
import getpass # Pour demander la passphrase interactivement

# Ajouter la racine du projet au sys.path pour les imports
# Le script est dans scripts/demo/, donc remonter de deux niveaux
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Charger les variables d'environnement depuis .env à la racine du projet
from dotenv import load_dotenv, find_dotenv
env_path = find_dotenv(filename=".env", usecwd=True, raise_error_if_not_found=False)
if env_path:
    print(f"Chargement du fichier .env trouvé à: {env_path}")
    load_dotenv(env_path, override=True)
else:
    print("ATTENTION: Fichier .env non trouvé. Certaines configurations pourraient manquer.")


# Imports des modules du projet
from argumentation_analysis.utils.core_utils.crypto_utils import load_encryption_key, decrypt_data_with_fernet
from argumentation_analysis.models.extract_definition import ExtractDefinitions, SourceDefinition, Extract
from argumentation_analysis.core.jvm_setup import initialize_jvm
from argumentation_analysis.core.llm_service import create_llm_service
from argumentation_analysis.orchestration.analysis_runner import run_analysis_conversation
from argumentation_analysis.paths import LIBS_DIR, DATA_DIR, PROJECT_ROOT_DIR # Pour les chemins standards

# Définition du chemin vers le répertoire des logs
# LOGS_DIR n'est pas exporté directement par paths.py, on le construit depuis PROJECT_ROOT_DIR
LOGS_DIRECTORY = PROJECT_ROOT_DIR / "logs"

# Configuration du logging
LOG_FILE_PATH = LOGS_DIRECTORY / "rhetorical_analysis_demo_conversation.log"

def setup_demo_logging():
    """Configure le logging pour la démo."""
    # S'assurer que le répertoire de logs existe
    LOGS_DIRECTORY.mkdir(parents=True, exist_ok=True)

    # Logger racine (console)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
        datefmt='%H:%M:%S',
        handlers=[logging.StreamHandler(sys.stdout)]
    )

    # Logger spécifique pour la conversation, qui écrit dans un fichier
    # Ce logger capture 'Orchestration.Run' et ses enfants comme 'Orchestration.Run.{run_id}'
    conversation_logger = logging.getLogger("Orchestration.Run")
    conversation_logger.setLevel(logging.DEBUG) # Capturer DEBUG et plus pour le fichier

    # FileHandler pour le fichier de log de la conversation
    file_handler = logging.FileHandler(LOG_FILE_PATH, mode='w', encoding='utf-8')
    file_formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    file_handler.setFormatter(file_formatter)
    
    # Ajouter le handler seulement si pas déjà présent pour éviter duplication
    if not any(isinstance(h, logging.FileHandler) and h.baseFilename == str(LOG_FILE_PATH) for h in conversation_logger.handlers):
        conversation_logger.addHandler(file_handler)

    # S'assurer que les logs de conversation ne sont pas propagés au logger racine
    # pour éviter la double journalisation sur la console si le niveau racine est DEBUG.
    # Cependant, nous voulons que les messages INFO et supérieurs apparaissent sur la console via le logger racine.
    # Le logger "Orchestration.Run" aura son propre handler fichier pour DEBUG.
    # Les messages INFO et supérieurs de "Orchestration.Run" seront aussi gérés par le handler console du root logger.
    # conversation_logger.propagate = False # On laisse la propagation pour que la console reçoive INFO+

    # Réduire la verbosité de certaines bibliothèques pour la console
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    # ... autres bibliothèques si nécessaire

    logging.info(f"Logging configuré. Les logs de conversation détaillés seront dans: {LOG_FILE_PATH}")

def get_passphrase() -> str:
    """
    Récupère la phrase secrète depuis la variable d'environnement ou la demande à l'utilisateur.
    """
    passphrase = os.getenv("TEXT_CONFIG_PASSPHRASE")
    if not passphrase:
        logging.warning("Variable d'environnement TEXT_CONFIG_PASSPHRASE non trouvée.")
        try:
            passphrase = getpass.getpass("Veuillez entrer la phrase secrète pour déchiffrer les sources : ")
        except Exception as e:
            logging.error(f"Impossible de lire la phrase secrète interactivement: {e}")
            sys.exit(1)
    if not passphrase:
        logging.error("Aucune phrase secrète fournie. Impossible de continuer.")
        sys.exit(1)
    return passphrase

async def decrypt_and_select_text(passphrase: str) -> str:
    # Texte par défaut si le chargement/sélection échoue
    default_text_payload = (
        "Le réchauffement climatique est un sujet complexe. Certains affirment qu'il s'agit d'un mythe, "
        "citant par exemple des hivers froids comme preuve. D'autres soutiennent que des mesures "
        "drastiques sont nécessaires immédiatement pour éviter une catastrophe planétaire. Il est "
        "également courant d'entendre que les scientifiques qui alertent sur ce danger sont "
        "financièrement motivés, ce qui mettrait en doute leurs conclusions. Face à ces arguments, "
        "il est crucial d'analyser les faits avec rigueur et de déconstruire les sophismes."
    )

    """
    Déchiffre le fichier extract_sources.json.gz.enc et sélectionne un texte pour la démo.
    Retourne un texte par défaut si la sélection échoue.
    """
    if not passphrase:
        logging.error("Aucune passphrase fournie pour decrypt_and_select_text.")
        # Utilisation du texte par défaut
        logging.warning("Utilisation d'un texte de démonstration par défaut car aucune passphrase n'a été fournie.")
        logging.info(f"Texte par défaut sélectionné (extrait): '{default_text_payload[:50]}'")
        return default_text_payload

    encryption_key = load_encryption_key(passphrase_arg=passphrase)
    if not encryption_key:
        logging.error("Impossible de dériver la clé de chiffrement.")
        # Utilisation du texte par défaut
        logging.warning("Utilisation d'un texte de démonstration par défaut car la clé de chiffrement n'a pu être dérivée.")
        logging.info(f"Texte par défaut sélectionné (extrait): '{default_text_payload[:50]}'")
        return default_text_payload

    encrypted_file_path = DATA_DIR / "extract_sources.json.gz.enc"
    if not encrypted_file_path.exists():
        logging.error(f"Fichier chiffré non trouvé : {encrypted_file_path}")
        # Utilisation du texte par défaut
        logging.warning(f"Utilisation d'un texte de démonstration par défaut car le fichier chiffré {encrypted_file_path} est introuvable.")
        logging.info(f"Texte par défaut sélectionné (extrait): '{default_text_payload[:50]}'")
        return default_text_payload

    try:
        with open(encrypted_file_path, "rb") as f:
            encrypted_data = f.read()
        
        decrypted_gzipped_data = decrypt_data_with_fernet(encrypted_data, encryption_key)
        if not decrypted_gzipped_data:
            logging.error("Échec du déchiffrement des données.")
            # Utilisation du texte par défaut
            logging.warning("Utilisation d'un texte de démonstration par défaut suite à un échec de déchiffrement.")
            logging.info(f"Texte par défaut sélectionné (extrait): '{default_text_payload[:50]}'")
            return default_text_payload

        json_data_bytes = gzip.decompress(decrypted_gzipped_data)
        sources_list_dict = json.loads(json_data_bytes.decode('utf-8'))
        
        extract_definitions = ExtractDefinitions.from_dict_list(sources_list_dict)
        
        # Logs de débogage (conservés et corrigés)
        if not extract_definitions: 
            logging.error("ExtractDefinitions.from_dict_list a résulté en un objet None.")
        elif not extract_definitions.sources:
            logging.info("extract_definitions ne contient aucune source.")
        else: # extract_definitions et extract_definitions.sources existent
            logging.info(f"Nombre de sources dans extract_definitions: {len(extract_definitions.sources)}")
            first_source = extract_definitions.sources[0]
            logging.info(f"Détails de la première source (Nom): '{first_source.source_name}', Type: '{first_source.source_type}'")
            logging.info(f"  Nombre d'extraits pour la première source: {len(first_source.extracts) if first_source.extracts else 0}")
            if first_source.extracts:
                first_extract = first_source.extracts[0]
                logging.info(f"  Détails du premier extrait (Nom): '{first_extract.extract_name}'")
                full_text_present = bool(first_extract.full_text and first_extract.full_text.strip())
                logging.info(f"    Présence de full_text pour le premier extrait: {full_text_present}")
                if full_text_present:
                    logging.info(f"    Début de full_text (premiers 200 caractères): '{first_extract.full_text[:200]}' (tronqué)")
                else:
                    logging.info(f"    full_text est vide ou non défini pour le premier extrait.")
            else:
                logging.info("  La première source n'a pas d'extraits.")
        
        if extract_definitions and extract_definitions.sources:
            # Chercher un extrait avec full_text rempli
            selected_extract_data = None
            for source_idx, source in enumerate(extract_definitions.sources):
                logging.debug(f"Vérification Source {source_idx}: '{source.source_name}'")
                if not source.extracts:
                    logging.debug(f"  Aucun extrait dans la source '{source.source_name}'.")
                    continue
                for extract_idx, extract_item in enumerate(source.extracts):
                    logging.debug(f"  Vérification Extrait {extract_idx}: '{extract_item.extract_name}' - Présence full_text: {bool(extract_item.full_text)}")
                    if extract_item.full_text and extract_item.full_text.strip(): # Ajout de strip() pour être sûr
                        selected_extract_data = {
                            "source": source,
                            "extract": extract_item
                        }
                        logging.info(f"Extrait avec full_text trouvé et sélectionné: '{extract_item.extract_name}' de la source '{source.source_name}'.")
                        break 
                if selected_extract_data:
                    break 
            
            if selected_extract_data:
                selected_source = selected_extract_data["source"]
                selected_extract = selected_extract_data["extract"]
                logging.info(f"Texte sélectionné pour la démo :")
                logging.info(f"  Source : '{selected_source.source_name}' (Type: {selected_source.source_type})")
                logging.info(f"  Extrait: '{selected_extract.extract_name}'")
                logging.info(f"  Début du texte (extrait): '{selected_extract.full_text[:50]}'") 
                return selected_extract.full_text
            else:
                logging.error("Aucun extrait avec 'full_text' pré-rempli n'a été trouvé dans les sources disponibles après la boucle de recherche.")
        # Si extract_definitions est vide ou sans sources, ou si aucun full_text n'est trouvé, on tombe ici vers le fallback.

    except FileNotFoundError:
        logging.error(f"Fichier source chiffré non trouvé : {encrypted_file_path}")
    except gzip.BadGzipFile:
        logging.error("Erreur de décompression Gzip. Les données déchiffrées ne sont peut-être pas au format Gzip.")
    except json.JSONDecodeError:
        logging.error("Erreur de décodage JSON. Les données décompressées ne sont peut-être pas du JSON valide.")
    except Exception as e:
        logging.error(f"Erreur majeure lors du déchiffrement ou de la sélection du texte : {e}", exc_info=True)
    
    # Fallback au texte par défaut
    logging.warning("Utilisation d'un texte de démonstration par défaut car le chargement/sélection depuis les sources a échoué.")
    logging.info(f"Texte par défaut sélectionné (extrait): '{default_text_payload[:50]}'")
    return default_text_payload

async def main_demo():
    """Fonction principale de la démonstration."""
    logging.info("--- Début du script de démonstration d'analyse rhétorique ---")

    passphrase = get_passphrase()
    # get_passphrase gère sys.exit(1) si aucune passphrase n'est fournie

    full_text_to_analyze = await decrypt_and_select_text(passphrase)
    if not full_text_to_analyze: # Devrait toujours retourner default_text_payload si vide avant
        logging.error("Impossible d'obtenir le texte pour l'analyse (même par défaut). Arrêt de la démo.")
        sys.exit(1)

    temp_file_path = None
    try:
        # Sauvegarder le full_text dans un fichier temporaire
        with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8", suffix=".txt") as tmp_file:
            tmp_file.write(full_text_to_analyze)
            temp_file_path = tmp_file.name
        logging.info(f"Texte pour analyse sauvegardé dans le fichier temporaire : {temp_file_path}")

        # Initialisation JVM
        logging.info("Initialisation de la JVM...")
        jvm_ready = initialize_jvm(lib_dir_path=LIBS_DIR)
        if not jvm_ready:
            logging.warning("La JVM n'a pas pu être initialisée. Certaines fonctionnalités pourraient être limitées.")
        else:
            logging.info("JVM initialisée avec succès.")

        # Création du service LLM
        logging.info("Création du service LLM...")
        llm_service = None
        try:
            llm_service = create_llm_service()
            logging.info(f"Service LLM créé avec succès (ID: {llm_service.service_id}).")
        except Exception as e:
            logging.critical(f"Échec de la création du service LLM: {e}", exc_info=True)
            sys.exit(1)

        # Lancement de l'analyse
        if llm_service:
            logging.info("Lancement de l'analyse rhétorique...")
            # Le texte est lu depuis le fichier par run_analysis_conversation si on lui passe un chemin
            # ou directement si on passe le contenu. Ici, on passe le contenu.
            await run_analysis_conversation(
                texte_a_analyser=full_text_to_analyze, # Passer le contenu directement
                llm_service=llm_service
            )
            logging.info("Analyse rhétorique terminée.")
        else:
            logging.error("Service LLM non disponible. Analyse annulée.")

    except Exception as e:
        logging.error(f"Une erreur est survenue pendant la démo : {e}", exc_info=True)
        sys.exit(1) # Sortir avec un code d'erreur si une exception se produit dans le try principal
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
                logging.info(f"Fichier temporaire supprimé : {temp_file_path}")
            except Exception as e_del:
                logging.error(f"Erreur lors de la suppression du fichier temporaire {temp_file_path}: {e_del}")
        
        logging.info("--- Fin du script de démonstration ---")
        logging.info(f"Le log détaillé de la conversation agentique se trouve dans : {LOG_FILE_PATH.resolve()}")
        # L'emplacement des rapports dépend de la configuration de generate_report dans analysis_runner
        # Par défaut, c'est dans le répertoire courant avec un nom comme rapport_analyse_YYYYMMDD_HHMMSS.json
        # Si output_dir est utilisé par une logique appelante (non visible ici), ce sera différent.
        # Pour cette démo, on suppose que analysis_runner les mettra dans le CWD ou un sous-répertoire logs/outputs.
        logging.info("Les rapports d'analyse finaux sont typiquement sauvegardés par le analysis_runner.")
        logging.info("  -> Vérifiez le répertoire courant ou un sous-répertoire comme 'logs/outputs' ou 'reports'.")
        logging.info("  -> Le nom du fichier de rapport inclut généralement un horodatage.")


if __name__ == "__main__":
    # La configuration du logging doit être faite avant toute utilisation de logging
    setup_demo_logging()
    
    # Vérification de la variable d'environnement pour le chemin des libs (pour JPype)
    # Ceci est généralement géré par activate_project_env.ps1 ou équivalent.
    # Mais pour un lancement direct, il faut s'en assurer.
    ld_library_path = os.environ.get('LD_LIBRARY_PATH')
    if sys.platform != "win32" and (not ld_library_path or str(LIBS_DIR.resolve()) not in ld_library_path):
        logging.warning(f"LD_LIBRARY_PATH n'inclut peut-être pas {LIBS_DIR.resolve()}. Problèmes avec JPype possibles.")

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    try:
        asyncio.run(main_demo())
    except KeyboardInterrupt:
        logging.info("Script interrompu par l'utilisateur.")
        sys.exit(0) # Sortie propre en cas d'interruption utilisateur
    except Exception as e_global:
        logging.critical(f"Erreur non gérée au niveau global du script: {e_global}", exc_info=True)
        sys.exit(1)