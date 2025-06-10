#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test de déchiffrement des différentes versions du corpus depuis l'historique git.
"""

import os
import sys
from pathlib import Path

# Ajouter le répertoire racine au sys.path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

# Charger .env
from dotenv import load_dotenv
load_dotenv()

def test_decrypt_file(file_path, description):
    """Teste le déchiffrement d'un fichier."""
    
    print(f"\n=== TEST DÉCHIFFREMENT: {description} ===")
    print(f"Fichier: {file_path}")
    
    passphrase = os.getenv("TEXT_CONFIG_PASSPHRASE")
    print(f"Passphrase: '{passphrase}'")
    
    if not os.path.exists(file_path):
        print(f"❌ Fichier inexistant: {file_path}")
        return False
    
    # Afficher la taille du fichier
    file_size = os.path.getsize(file_path)
    print(f"Taille: {file_size} octets")
    
    try:
        # Import des modules de déchiffrement
        from scripts.data_processing.decrypt_extracts import decrypt_and_load_extracts
        
        # Tentative de déchiffrement
        print("Tentative de déchiffrement...")
        extract_definitions, status_message = decrypt_and_load_extracts(passphrase)
        
        if extract_definitions:
            print(f"[OK] SUCCES - {len(extract_definitions)} sources trouvees")
            print(f"Status: {status_message}")
            
            # Afficher un résumé des sources
            for i, source in enumerate(extract_definitions[:3]):  # Limiter à 3 sources
                source_name = source.get("source_name", f"Source_{i}")
                extracts_count = len(source.get("extracts", []))
                print(f"  - {source_name}: {extracts_count} extraits")
            
            return True
        else:
            print(f"[ECHEC] - {status_message}")
            return False
            
    except Exception as e:
        print(f"[ERREUR] - {str(e)[:200]}...")
        return False

def main():
    """Teste les différentes versions du fichier."""
    
    print("=== TEST DES VERSIONS DU CORPUS CHIFFRÉ ===")
    
    # Version actuelle
    current_file = "argumentation_analysis/data/extract_sources.json.gz.enc"
    success_current = test_decrypt_file(current_file, "VERSION ACTUELLE")
    
    # Version du commit 48e08bf
    temp_file = "temp_48e08bf.enc"
    success_48e08bf = test_decrypt_file(temp_file, "VERSION 48e08bf (FINALIZE-ENCRYPTED-SOURCES)")
    
    print(f"\n=== RÉSUMÉ ===")
    print(f"Version actuelle: {'[OK]' if success_current else '[ECHEC]'}")
    print(f"Version 48e08bf: {'[OK]' if success_48e08bf else '[ECHEC]'}")
    
    if not success_current and not success_48e08bf:
        print(f"\n[WARNING] Aucune version ne peut etre dechiffree avec la passphrase actuelle.")
        print(f"Il faut probablement recréer le fichier depuis le source non-chiffré.")
    
    # Nettoyer le fichier temporaire
    if os.path.exists(temp_file):
        os.remove(temp_file)
        print(f"Fichier temporaire supprimé: {temp_file}")
    
    return success_current or success_48e08bf

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)