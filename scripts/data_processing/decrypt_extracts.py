import project_core.core_from_scripts.auto_env
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script pour déchiffrer et charger les extraits du fichier extract_sources.json.gz.enc.

Ce script:
1. Utilise les fonctions appropriées de argumentation_analysis/ui/extract_utils.py
2. Charge la clé de chiffrement depuis les variables d'environnement
3. Affiche un résumé des sources et extraits disponibles
4. Sauvegarde les extraits déchiffrés dans un format temporaire pour les tests
"""

import os
import sys
import json
import logging
import tempfile
import argparse
import base64
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional
from dotenv import load_dotenv

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("DecryptExtracts")

# Ajout du répertoire parent au chemin pour permettre l'import des modules du projet
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent)) # MODIFIÉ: Ajout de .parent pour pointer vers la racine

# Charger les variables d'environnement depuis .env s'il existe
dotenv_path = Path(__file__).resolve().parent.parent.parent / '.env' # MODIFIÉ: Ajout de .parent pour pointer vers la racine
if dotenv_path.exists():
    logger.info(f"Chargement des variables d'environnement depuis {dotenv_path}")
    load_dotenv(dotenv_path)
else:
    logger.warning(f"Fichier .env non trouvé à {dotenv_path}")

# Variables globales qui seront définies après l'import
CONFIG_FILE = None
ENCRYPTION_KEY = None
DATA_DIR = None

try:
    # Import des modules nécessaires
    from argumentation_analysis.paths import DATA_DIR
    # MODIFIÉ: Import des deux fonctions déplacées
    from argumentation_analysis.utils.core_utils.crypto_utils import load_encryption_key, decrypt_data_aesgcm
    
    # Chemin vers le fichier chiffré
    CONFIG_FILE = Path(DATA_DIR) / "extract_sources.json.gz.enc"
    
    logger.info(f"Modules importés avec succès")
    logger.info(f"DATA_DIR: {DATA_DIR}")
    logger.info(f"CONFIG_FILE: {CONFIG_FILE}")
except ImportError as e:
    logger.error(f"Erreur d'importation: {e}")
    logger.error("Assurez-vous que le package argumentation_analysis et project_core sont installés ou accessibles.") # MODIFIÉ: Message d'erreur
    sys.exit(1)
except Exception as e:
    logger.error(f"Erreur inattendue lors de l'initialisation: {e}")
    sys.exit(1)

# Les fonctions derive_encryption_key et load_encryption_key ont été déplacées vers project_core.utils.crypto_utils

def decrypt_and_load_extracts(encryption_key: Optional[str]) -> Tuple[List[Dict[str, Any]], str]: # MODIFIÉ: Annotation de bytes à str
    """
    Déchiffre et charge les extraits du fichier chiffré.
    
    Args:
        encryption_key: La clé de chiffrement
        
    Returns:
        Tuple[List[Dict[str, Any]], str]: Les définitions d'extraits et un message de statut
    """
    logger.info(f"Tentative de chargement du fichier: {CONFIG_FILE}")
    
    if not encryption_key:
        logger.error("Clé de chiffrement manquante.")
        return [], "Clé de chiffrement manquante"
    
    if not CONFIG_FILE.exists():
        logger.error(f"Fichier {CONFIG_FILE} introuvable.")
        return [], f"Fichier {CONFIG_FILE} introuvable"
    
    try:
        with open(CONFIG_FILE, 'rb') as f:
            encrypted_data = f.read()

        decrypted_gzipped_data = decrypt_data_aesgcm(encrypted_data, encryption_key)

        if not decrypted_gzipped_data:
            return [], "Échec du déchiffrement des données."

        import gzip
        json_data = gzip.decompress(decrypted_gzipped_data)
        extract_definitions = json.loads(json_data.decode('utf-8'))

        if extract_definitions:
            message = f"Définitions chargées et déchiffrées depuis {CONFIG_FILE}"
            return extract_definitions, message
        else:
            return [], "Échec du chargement des définitions après déchiffrement."
    except Exception as e:
        logger.error(f"Erreur lors du chargement des définitions: {e}")
        return [], f"Erreur: {str(e)}"

def summarize_extracts(extract_definitions: List[Dict[str, Any]]) -> None:
    """
    Affiche un résumé des sources et extraits disponibles.
    
    Args:
        extract_definitions: Les définitions d'extraits
    """
    if not extract_definitions:
        logger.warning("Aucune définition d'extrait trouvée.")
        return
    
    logger.info(f"Nombre total de sources: {len(extract_definitions)}")
    
    total_extracts = 0
    for i, source in enumerate(extract_definitions, 1):
        source_name = source.get("source_name", "Source sans nom")
        source_type = source.get("source_type", "Type inconnu")
        source_url = source.get("source_url", "URL inconnue")
        extracts = source.get("extracts", [])
        
        logger.info(f"\nSource {i}: {source_name}")
        logger.info(f"  Type: {source_type}")
        logger.info(f"  URL: {source_url}")
        logger.info(f"  Nombre d'extraits: {len(extracts)}")
        
        for j, extract in enumerate(extracts, 1):
            extract_name = extract.get("extract_name", "Extrait sans nom")
            start_marker = extract.get("start_marker", "")
            end_marker = extract.get("end_marker", "")
            
            # Tronquer les marqueurs s'ils sont trop longs pour l'affichage
            if len(start_marker) > 50:
                start_marker = start_marker[:47] + "..."
            if len(end_marker) > 50:
                end_marker = end_marker[:47] + "..."
            
            logger.info(f"    Extrait {j}: {extract_name}")
            logger.info(f"      Début: {start_marker}")
            logger.info(f"      Fin: {end_marker}")
        
        total_extracts += len(extracts)
    
    logger.info(f"\nRésumé global:")
    logger.info(f"  Nombre total de sources: {len(extract_definitions)}")
    logger.info(f"  Nombre total d'extraits: {total_extracts}")

def save_temp_extracts(extract_definitions: List[Dict[str, Any]]) -> str:
    """
    Sauvegarde les extraits déchiffrés dans un format temporaire pour les tests.
    
    Args:
        extract_definitions: Les définitions d'extraits
        
    Returns:
        str: Le chemin du fichier temporaire
    """
    # Créer un répertoire temporaire dans le répertoire du projet
    temp_dir = Path("temp_extracts")
    temp_dir.mkdir(exist_ok=True)
    
    # Créer un nom de fichier avec horodatage
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    temp_file = temp_dir / f"extracts_decrypted_{timestamp}.json"
    
    try:
        # Convertir en JSON
        json_data = json.dumps(extract_definitions, ensure_ascii=False, indent=2)
        
        # Sauvegarder dans le fichier
        temp_file.parent.mkdir(parents=True, exist_ok=True)
        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write(json_data)
        
        logger.info(f"✅ Définitions exportées avec succès vers {temp_file}")
        return str(temp_file)
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'exportation: {e}")
        return ""

def parse_arguments():
    """
    Parse les arguments de ligne de commande.
    
    Returns:
        argparse.Namespace: Les arguments parsés
    """
    parser = argparse.ArgumentParser(description="Déchiffre et charge les extraits du fichier extract_sources.json.gz.enc")
    
    parser.add_argument(
        "--passphrase", "-p",
        help="Phrase secrète pour dériver la clé de chiffrement (alternative à la variable d'environnement)"
    )
    
    parser.add_argument(
        "--output", "-o",
        help="Chemin du fichier de sortie pour les extraits déchiffrés (par défaut: temp_extracts/extracts_decrypted_TIMESTAMP.json)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Affiche des informations de débogage supplémentaires"
    )
    
    return parser.parse_args()

def main():
    """Fonction principale du script."""
    # Analyser les arguments
    args = parse_arguments()
    
    # Configurer le niveau de logging
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logger.debug("Mode verbeux activé")
    
    logger.info("Démarrage du script de déchiffrement des extraits...")
    
    # 1. Charger la clé de chiffrement
    # MODIFIÉ: Appel à la fonction importée avec la nouvelle signature
    encryption_key = args.passphrase or os.getenv("TEXT_CONFIG_PASSPHRASE")
    if encryption_key is None:
        logger.error("Impossible de continuer sans clé de chiffrement.")
        sys.exit(1)
    
    # 2. Déchiffrer et charger les extraits
    try:
        extract_definitions, message = decrypt_and_load_extracts(encryption_key)
        logger.info(f"Résultat du chargement: {message}")
        
        if not extract_definitions:
            logger.error("Aucune définition d'extrait n'a pu être chargée.")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Erreur lors du déchiffrement et du chargement des extraits: {e}")
        sys.exit(1)
    
    # 3. Afficher un résumé des sources et extraits
    summarize_extracts(extract_definitions) # Utilisation de la fonction importée
    
    # 4. Sauvegarder les extraits dans un format temporaire
    try:
        if args.output:
            output_path = Path(args.output)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(extract_definitions, f, ensure_ascii=False, indent=2)
            logger.info(f"✅ Définitions exportées avec succès vers {output_path}")
        else:
            # Utiliser la fonction importée. Elle retourne un Path ou None.
            temp_file_path = save_temp_extracts_json(extract_definitions)
            if temp_file_path:
                logger.info(f"Les extraits déchiffrés ont été sauvegardés dans: {temp_file_path.resolve()}")
            else:
                logger.error("Échec de la sauvegarde des extraits temporaires.")
    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde des extraits: {e}")
        sys.exit(1)
    
    logger.info("Script terminé avec succès.")

if __name__ == "__main__":
    main()