#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour nettoyer les fichiers non nécessaires après avoir créé le fichier encrypté complet.
"""

import os
import sys
import shutil
from pathlib import Path

# Ajouter le répertoire parent au chemin de recherche des modules
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
if str(parent_dir) not in sys.path:
    sys.path.append(str(parent_dir))

# Importer les modules nécessaires
from ui.config import CONFIG_FILE_ENC

# Définir les constantes
TEXT_CACHE_DIR = parent_dir / "text_cache"
TEMP_DOWNLOADS_DIR = parent_dir / "temp_downloads"
EXTRACT_SOURCES_JSON = parent_dir / "data" / "extract_sources.json"

def cleanup_files():
    """Nettoie les fichiers non nécessaires après avoir créé le fichier encrypté complet."""
    # Vérifier si le fichier encrypté existe
    if not CONFIG_FILE_ENC.exists():
        print(f"❌ Erreur: Le fichier encrypté '{CONFIG_FILE_ENC}' n'existe pas.")
        print(f"   Veuillez d'abord créer le fichier encrypté complet.")
        return False
    
    files_removed = 0
    dirs_removed = 0
    
    # Supprimer les fichiers de cache
    if TEXT_CACHE_DIR.exists():
        print(f"Suppression du répertoire de cache '{TEXT_CACHE_DIR}'...")
        try:
            # Compter les fichiers
            cache_files = list(TEXT_CACHE_DIR.glob("*.txt"))
            files_removed += len(cache_files)
            
            # Supprimer le répertoire
            shutil.rmtree(TEXT_CACHE_DIR)
            dirs_removed += 1
            print(f"✅ Répertoire de cache '{TEXT_CACHE_DIR}' supprimé.")
            print(f"   - {len(cache_files)} fichiers de cache supprimés.")
        except Exception as e:
            print(f"⚠️ Avertissement: Erreur lors de la suppression du répertoire de cache '{TEXT_CACHE_DIR}': {e}")
    else:
        print(f"ℹ️ Le répertoire de cache '{TEXT_CACHE_DIR}' n'existe pas.")
    
    # Supprimer les téléchargements temporaires
    if TEMP_DOWNLOADS_DIR.exists():
        print(f"Suppression du répertoire de téléchargements temporaires '{TEMP_DOWNLOADS_DIR}'...")
        try:
            # Compter les fichiers
            temp_files = list(TEMP_DOWNLOADS_DIR.glob("*"))
            files_removed += len(temp_files)
            
            # Supprimer le répertoire
            shutil.rmtree(TEMP_DOWNLOADS_DIR)
            dirs_removed += 1
            print(f"✅ Répertoire de téléchargements temporaires '{TEMP_DOWNLOADS_DIR}' supprimé.")
            print(f"   - {len(temp_files)} fichiers temporaires supprimés.")
        except Exception as e:
            print(f"⚠️ Avertissement: Erreur lors de la suppression du répertoire de téléchargements temporaires '{TEMP_DOWNLOADS_DIR}': {e}")
    else:
        print(f"ℹ️ Le répertoire de téléchargements temporaires '{TEMP_DOWNLOADS_DIR}' n'existe pas.")
    
    # Supprimer le fichier extract_sources.json s'il existe
    if EXTRACT_SOURCES_JSON.exists():
        print(f"Suppression du fichier '{EXTRACT_SOURCES_JSON}'...")
        try:
            EXTRACT_SOURCES_JSON.unlink()
            files_removed += 1
            print(f"✅ Fichier '{EXTRACT_SOURCES_JSON}' supprimé.")
        except Exception as e:
            print(f"⚠️ Avertissement: Erreur lors de la suppression du fichier '{EXTRACT_SOURCES_JSON}': {e}")
    else:
        print(f"ℹ️ Le fichier '{EXTRACT_SOURCES_JSON}' n'existe pas.")
    
    print(f"\nNettoyage terminé:")
    print(f"   - {files_removed} fichiers supprimés.")
    print(f"   - {dirs_removed} répertoires supprimés.")
    
    return True

def main():
    """Fonction principale."""
    print("\n=== Nettoyage des fichiers non nécessaires ===\n")
    
    # Demander confirmation à l'utilisateur
    print("⚠️ ATTENTION: Cette opération va supprimer définitivement les fichiers suivants:")
    print(f"   - Tous les fichiers de cache dans '{TEXT_CACHE_DIR}'")
    print(f"   - Tous les fichiers temporaires dans '{TEMP_DOWNLOADS_DIR}'")
    print(f"   - Le fichier '{EXTRACT_SOURCES_JSON}' s'il existe")
    print("\nAssurez-vous d'avoir d'abord créé le fichier encrypté complet.")
    
    confirmation = input("\nÊtes-vous sûr de vouloir continuer? (o/n): ")
    if confirmation.lower() not in ["o", "oui", "y", "yes"]:
        print("\nOpération annulée.")
        sys.exit(0)
    
    # Nettoyer les fichiers
    success = cleanup_files()
    
    if success:
        print("\n✅ Nettoyage des fichiers non nécessaires réussi !")
    else:
        print("\n❌ Échec du nettoyage des fichiers non nécessaires.")
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
