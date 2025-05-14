#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script de nettoyage des fichiers sensibles

Ce script supprime tous les fichiers de configuration et documents sources en clair
pour ne laisser sur le dépôt que les fichiers chiffrés, afin d'éviter que du contenu
sensible soit indexé par GitHub.

Il vérifie d'abord que les fichiers peuvent être reconstitués à partir des fichiers
chiffrés avant de les supprimer.
"""

import os
import sys
import json
import logging
import shutil
from pathlib import Path

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("CleanupSensitiveFiles")

# Ajouter le répertoire parent au chemin de recherche des modules
sys.path.append(str(Path(__file__).parent.parent))

# Importer les modules nécessaires
try:
    from argumentiation_analysis.ui import config as ui_config
    from argumentiation_analysis.ui.extract_utils import load_extract_definitions_safely
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

def verify_encrypted_file():
    """
    Vérifie que le fichier chiffré existe et peut être déchiffré correctement.
    
    Returns:
        bool: True si le fichier chiffré peut être déchiffré, False sinon
    """
    logger.info(f"Vérification du fichier chiffré {CONFIG_FILE_ENC}...")
    
    # Vérifier que le fichier chiffré existe
    if not CONFIG_FILE_ENC.exists():
        logger.error(f"Le fichier chiffré {CONFIG_FILE_ENC} n'existe pas.")
        return False
    
    # Vérifier que la clé de chiffrement est disponible
    if not ENCRYPTION_KEY:
        logger.error("La clé de chiffrement n'est pas disponible.")
        return False
    
    # Tenter de charger les définitions d'extraits depuis le fichier chiffré
    extract_definitions, error_message = load_extract_definitions_safely(CONFIG_FILE_ENC, ENCRYPTION_KEY)
    
    if error_message:
        logger.error(f"Erreur lors du chargement des définitions d'extraits: {error_message}")
        return False
    
    # Vérifier que les définitions d'extraits ont été chargées correctement
    if not extract_definitions or not isinstance(extract_definitions, list) or len(extract_definitions) == 0:
        logger.error("Les définitions d'extraits n'ont pas été chargées correctement.")
        return False
    
    logger.info(f"✅ Le fichier chiffré {CONFIG_FILE_ENC} peut être déchiffré correctement.")
    logger.info(f"   - {len(extract_definitions)} sources trouvées.")
    
    return True

def update_gitignore():
    """
    Met à jour le fichier .gitignore pour s'assurer que tous les fichiers sensibles sont ignorés.
    
    Returns:
        bool: True si le fichier .gitignore a été mis à jour, False sinon
    """
    logger.info("Mise à jour du fichier .gitignore...")
    
    # Chemin vers le fichier .gitignore
    gitignore_path = Path(__file__).parent.parent / ".gitignore"
    
    # Vérifier que le fichier .gitignore existe
    if not gitignore_path.exists():
        logger.error(f"Le fichier .gitignore n'existe pas: {gitignore_path}")
        return False
    
    # Lire le contenu du fichier .gitignore
    with open(gitignore_path, 'r', encoding='utf-8') as f:
        gitignore_content = f.read()
    
    # Liste des entrées à ajouter au .gitignore
    entries_to_add = [
        "# Fichiers de configuration sensibles (ajoutés par cleanup_sensitive_files.py)",
        "extract_repair/docs/extract_sources_updated.json",
        "extract_repair/docs/extract_sources_*.json",  # Pour les fichiers temporaires
    ]
    
    # Vérifier si les entrées sont déjà présentes dans le .gitignore
    entries_added = []
    for entry in entries_to_add:
        if entry.startswith("#"):  # Ignorer les commentaires
            continue
        if entry not in gitignore_content:
            entries_added.append(entry)
    
    # Si des entrées doivent être ajoutées, mettre à jour le fichier .gitignore
    if entries_added:
        with open(gitignore_path, 'a', encoding='utf-8') as f:
            f.write("\n\n" + "\n".join(entries_to_add) + "\n")
        
        logger.info(f"✅ Fichier .gitignore mis à jour avec {len(entries_added)} nouvelles entrées:")
        for entry in entries_added:
            logger.info(f"   - {entry}")
    else:
        logger.info("✅ Toutes les entrées nécessaires sont déjà présentes dans le fichier .gitignore.")
    
    return True

def delete_sensitive_files():
    """
    Supprime les fichiers sensibles.
    
    Returns:
        list: Liste des fichiers supprimés
    """
    logger.info("Suppression des fichiers sensibles...")
    
    # Liste des fichiers sensibles à supprimer
    sensitive_files = [
        CONFIG_FILE_JSON,  # data/extract_sources.json
        Path(__file__).parent / "extract_repair" / "docs" / "extract_sources_updated.json",
    ]
    
    # Répertoire du cache de texte
    text_cache_dir = Path(__file__).parent.parent / "text_cache"
    
    # Liste des fichiers supprimés
    deleted_files = []
    
    # Supprimer les fichiers sensibles
    for file_path in sensitive_files:
        if file_path.exists():
            try:
                file_path.unlink()
                logger.info(f"✅ Fichier supprimé: {file_path}")
                deleted_files.append(str(file_path))
            except Exception as e:
                logger.error(f"❌ Erreur lors de la suppression du fichier {file_path}: {e}")
        else:
            logger.info(f"ℹ️ Fichier déjà absent: {file_path}")
    
    # Supprimer les fichiers du cache de texte
    if text_cache_dir.exists() and text_cache_dir.is_dir():
        cache_files = list(text_cache_dir.glob("*.txt"))
        if cache_files:
            for cache_file in cache_files:
                try:
                    cache_file.unlink()
                    logger.info(f"✅ Fichier cache supprimé: {cache_file}")
                    deleted_files.append(str(cache_file))
                except Exception as e:
                    logger.error(f"❌ Erreur lors de la suppression du fichier cache {cache_file}: {e}")
        else:
            logger.info("ℹ️ Aucun fichier trouvé dans le répertoire de cache de texte.")
    else:
        logger.info(f"ℹ️ Répertoire de cache de texte absent: {text_cache_dir}")
    
    return deleted_files

def main():
    """Fonction principale."""
    logger.info("=== Nettoyage des fichiers sensibles ===")
    
    # Vérifier que le fichier chiffré peut être déchiffré
    if not verify_encrypted_file():
        logger.error("❌ Le fichier chiffré ne peut pas être déchiffré. Abandon du nettoyage.")
        sys.exit(1)
    
    # Mettre à jour le fichier .gitignore
    if not update_gitignore():
        logger.error("❌ Impossible de mettre à jour le fichier .gitignore. Abandon du nettoyage.")
        sys.exit(1)
    
    # Supprimer les fichiers sensibles
    deleted_files = delete_sensitive_files()
    
    # Afficher un résumé
    logger.info("\n=== Résumé du nettoyage ===")
    logger.info(f"Nombre de fichiers supprimés: {len(deleted_files)}")
    
    if deleted_files:
        logger.info("Fichiers supprimés:")
        for file in deleted_files:
            logger.info(f"   - {file}")
        
        logger.info("\nPour restaurer les fichiers de configuration, exécutez:")
        logger.info("   python restore_config.py")
    else:
        logger.info("Aucun fichier n'a été supprimé.")
    
    logger.info("\n✅ Nettoyage terminé avec succès.")

if __name__ == "__main__":
    main()