#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour vérifier le fichier de configuration encrypté.
"""

import os
import sys
from pathlib import Path
import logging

# Configurer le logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger("VerifyEncryptedConfig")

# Ajouter le répertoire parent au chemin de recherche des modules
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
if str(parent_dir) not in sys.path:
    sys.path.append(str(parent_dir))


# Importer les modules nécessaires
from argumentation_analysis.config.settings import settings
from argumentation_analysis.services.crypto_service import CryptoService
from argumentation_analysis.services.definition_service import DefinitionService
from argumentation_analysis.models.extract_definition import ExtractDefinitions

from argumentation_analysis.paths import DATA_DIR


def verify_encrypted_config():
    """Vérifie le fichier de configuration encrypté."""
    # Vérifier si la passphrase est définie dans la configuration
    if not settings.passphrase:
        logger.error("❌ La variable d'environnement 'TEXT_CONFIG_PASSPHRASE' n'est pas définie dans votre .env ou configuration.")
        return False
    passphrase = settings.passphrase.get_secret_value()
    
    # Initialiser le service de chiffrement
    crypto_service = CryptoService()
    encryption_key = crypto_service.derive_key_from_passphrase(passphrase)
    if not encryption_key:
        logger.error("❌ Échec de la dérivation de la clé de chiffrement.")
        return False
    
    crypto_service.set_encryption_key(encryption_key)
    logger.info("[OK] Service de chiffrement initialisé avec succès.")
    
    # Définir les chemins des fichiers
    config_file = current_dir / DATA_DIR / "extract_sources.json.gz.enc"
    
    # Vérifier si le fichier existe
    if not config_file.exists():
        logger.error(f"❌ Le fichier '{config_file}' n'existe pas.")
        return False
    
    logger.info(f"[OK] Fichier '{config_file}' trouvé.")
    
    # Initialiser le service de définition
    definition_service = DefinitionService(
        crypto_service=crypto_service,
        config_file=config_file
    )
    
    # Charger les définitions
    extract_definitions, error_message = definition_service.load_definitions()
    
    if error_message:
        logger.error(f"❌ Erreur lors du chargement des définitions: {error_message}")
        return False
    
    logger.info(f"[OK] Définitions chargées avec succès.")
    logger.info(f"   - {len(extract_definitions.sources)} sources trouvées.")
    
    # Afficher les détails des sources
    for i, source in enumerate(extract_definitions.sources):
        logger.info(f"   - Source {i+1}: {source.source_name}")
        logger.info(f"     - Type: {source.source_type}")
        logger.info(f"     - URL: {source.schema}://{'.'.join(source.host_parts)}{source.path}")
        logger.info(f"     - Nombre d'extraits: {len(source.extracts)}")
        
        # Afficher les détails du premier extrait s'il existe
        if source.extracts:
            first_extract = source.extracts[0]
            logger.info(f"     - Premier extrait: {first_extract.extract_name}")
            logger.info(f"       - Marqueur de début: {first_extract.start_marker[:50]}...")
            logger.info(f"       - Marqueur de fin: {first_extract.end_marker[:50]}...")
    
    # Valider les définitions
    is_valid, validation_errors = definition_service.validate_definitions(extract_definitions)
    
    if not is_valid:
        logger.error(f"❌ Les définitions ne sont pas valides:")
        for error in validation_errors:
            logger.error(f"   - {error}")
        return False
    
    logger.info(f"[OK] Les définitions sont valides.")
    
    return True

def main():
    """Fonction principale."""
    print("\n=== Vérification du fichier de configuration encrypté ===\n")
    
    success = verify_encrypted_config()
    
    if success:
        print("\n[OK] Vérification du fichier de configuration encrypté réussie !")
        print("   Le fichier est correctement formaté et contient des définitions d'extraits valides.")
    else:
        print("\n❌ Échec de la vérification du fichier de configuration encrypté.")
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()