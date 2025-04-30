#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script de restauration des fichiers de configuration

Ce script permet de reconstituer les fichiers de configuration en clair
à partir des fichiers chiffrés pour le développement local.
"""

import os
import sys
import json
import logging
from pathlib import Path

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("RestoreConfig")

# Ajouter le répertoire parent au chemin de recherche des modules
sys.path.append(str(Path(__file__).parent.parent))

# Importer les modules nécessaires
try:
    from ui import config as ui_config
    from ui.extract_utils import load_extract_definitions_safely, save_extract_definitions_safely
    logger.info("Import réussi.")
except ImportError as e:
    logger.error(f"Erreur d'importation: {e}")
    logger.error("Vérifiez que les modules nécessaires sont présents dans le projet.")
    sys.exit(1)

# Définir les constantes
ENCRYPTION_KEY = ui_config.ENCRYPTION_KEY
CONFIG_FILE = ui_config.CONFIG_FILE
CONFIG_FILE_JSON = ui_config.CONFIG_FILE_JSON
CONFIG_FILE_ENC = ui_config.CONFIG_FILE_ENC

def restore_config_files():
    """
    Restaure les fichiers de configuration en clair à partir des fichiers chiffrés.
    
    Returns:
        bool: True si la restauration a réussi, False sinon
    """
    logger.info(f"Restauration des fichiers de configuration à partir de {CONFIG_FILE_ENC}...")
    
    # Vérifier que le fichier chiffré existe
    if not CONFIG_FILE_ENC.exists():
        logger.error(f"Le fichier chiffré {CONFIG_FILE_ENC} n'existe pas.")
        return False
    
    # Vérifier que la clé de chiffrement est disponible
    if not ENCRYPTION_KEY:
        logger.error("La clé de chiffrement n'est pas disponible.")
        logger.error(f"Assurez-vous que la variable d'environnement TEXT_CONFIG_PASSPHRASE est définie.")
        return False
    
    # Charger les définitions d'extraits depuis le fichier chiffré
    extract_definitions, error_message = load_extract_definitions_safely(CONFIG_FILE_ENC, ENCRYPTION_KEY)
    
    if error_message:
        logger.error(f"Erreur lors du chargement des définitions d'extraits: {error_message}")
        return False
    
    # Vérifier que les définitions d'extraits ont été chargées correctement
    if not extract_definitions or not isinstance(extract_definitions, list) or len(extract_definitions) == 0:
        logger.error("Les définitions d'extraits n'ont pas été chargées correctement.")
        return False
    
    logger.info(f"✅ Définitions d'extraits chargées avec succès: {len(extract_definitions)} sources trouvées.")
    
    # Sauvegarder les définitions d'extraits dans le fichier JSON en clair
    logger.info(f"Sauvegarde des définitions d'extraits dans {CONFIG_FILE_JSON}...")
    
    # Créer le répertoire parent si nécessaire
    CONFIG_FILE_JSON.parent.mkdir(parents=True, exist_ok=True)
    
    # Sauvegarder les définitions d'extraits
    with open(CONFIG_FILE_JSON, 'w', encoding='utf-8') as f:
        json.dump(extract_definitions, f, indent=4, ensure_ascii=False)
    
    logger.info(f"✅ Définitions d'extraits sauvegardées dans {CONFIG_FILE_JSON}.")
    
    # Sauvegarder également dans le fichier extract_sources_updated.json pour les outils de réparation
    repair_config_path = Path(__file__).parent / "extract_repair" / "docs" / "extract_sources_updated.json"
    
    # Créer le répertoire parent si nécessaire
    repair_config_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Sauvegarder les définitions d'extraits
    with open(repair_config_path, 'w', encoding='utf-8') as f:
        json.dump(extract_definitions, f, indent=4, ensure_ascii=False)
    
    logger.info(f"✅ Définitions d'extraits sauvegardées dans {repair_config_path}.")
    
    return True

def main():
    """Fonction principale."""
    logger.info("=== Restauration des fichiers de configuration ===")
    
    # Restaurer les fichiers de configuration
    if restore_config_files():
        logger.info("\n✅ Restauration terminée avec succès.")
        logger.info("\nFichiers restaurés:")
        logger.info(f"   - {CONFIG_FILE_JSON}")
        logger.info(f"   - {Path(__file__).parent / 'extract_repair' / 'docs' / 'extract_sources_updated.json'}")
        
        logger.info("\nATTENTION: Ces fichiers contiennent des informations sensibles et ne doivent pas être versionnés.")
        logger.info("Pour nettoyer ces fichiers avant de commiter, exécutez:")
        logger.info("   python cleanup_sensitive_files.py")
    else:
        logger.error("\n❌ Échec de la restauration.")
        sys.exit(1)

if __name__ == "__main__":
    main()