#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script principal pour créer, vérifier et archiver le fichier encrypté complet.
"""

import os
import sys
import time
import shutil
from pathlib import Path
from dotenv import load_dotenv

# Ajouter le répertoire parent au chemin de recherche des modules
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
if str(parent_dir) not in sys.path:
    sys.path.append(str(parent_dir))

# Charger les variables d'environnement
load_dotenv(override=True)

# Importer les modules nécessaires
from argumentation_analysis.ui.config import CONFIG_FILE_ENC
from argumentation_analysis.paths import DATA_DIR

# Afficher les chemins pour le débogage
print(f"Chemin du fichier encrypté: {CONFIG_FILE_ENC}")

# Importer les fonctions des autres scripts
from create_complete_encrypted_config import create_complete_encrypted_config
from load_complete_encrypted_config import load_complete_encrypted_config

def main():
    """Fonction principale."""
    print("\n=== Création, vérification et archivage du fichier encrypté complet ===\n")
    
    # Vérifier si la variable d'environnement TEXT_CONFIG_PASSPHRASE est définie
    if not os.getenv("TEXT_CONFIG_PASSPHRASE"):
        print(f"⚠️ La variable d'environnement 'TEXT_CONFIG_PASSPHRASE' n'est pas définie.")
        print(f"   Veuillez la définir avant d'exécuter ce script.")
        sys.exit(1)
    
    # Étape 1: Créer le fichier encrypté complet
    print("\n--- Étape 1: Création du fichier encrypté complet ---\n")
    success_create = create_complete_encrypted_config()
    
    if not success_create:
        print("\n❌ Échec de la création du fichier encrypté complet. Arrêt du processus.")
        sys.exit(1)
    
    print("\n[OK] Création du fichier encrypté complet réussie !")
    print(f"   Fichier créé: '{CONFIG_FILE_ENC}'")
    print(f"   Taille: {CONFIG_FILE_ENC.stat().st_size} octets.")
    
    # Étape 2: Vérifier le fichier encrypté complet
    print("\n--- Étape 2: Vérification du fichier encrypté complet ---\n")
    print("Pour vérifier que le fichier encrypté complet est valide, nous allons le charger")
    print("et restaurer les fichiers de cache dans un répertoire temporaire.")
    
    # Attendre un peu pour que l'utilisateur puisse lire les messages
    time.sleep(2)
    
    # Créer un répertoire temporaire pour la vérification
    temp_cache_dir = parent_dir / "text_cache"
    
    # Sauvegarder le répertoire de cache original
    original_cache_dir = parent_dir / "text_cache_original"
    if temp_cache_dir.exists():
        if original_cache_dir.exists():
            print(f"⚠️ Le répertoire '{original_cache_dir}' existe déjà. Il ne sera pas écrasé.")
        else:
            try:
                temp_cache_dir.rename(original_cache_dir)
                print(f"[OK] Répertoire de cache original sauvegardé dans '{original_cache_dir}'.")
            except Exception as e:
                print(f"⚠️ Erreur lors de la sauvegarde du répertoire de cache original: {e}")
    
    # Charger le fichier encrypté complet
    success_load = load_complete_encrypted_config()
    
    if not success_load:
        print("\n❌ Échec de la vérification du fichier encrypté complet. Arrêt du processus.")
        
        # Restaurer le répertoire de cache original
        if original_cache_dir.exists():
            if temp_cache_dir.exists():
                try:
                    shutil.rmtree(temp_cache_dir)
                except Exception:
                    pass
            try:
                original_cache_dir.rename(temp_cache_dir)
                print(f"[OK] Répertoire de cache original restauré.")
            except Exception as e:
                print(f"⚠️ Erreur lors de la restauration du répertoire de cache original: {e}")
        
        sys.exit(1)
    
    print("\n[OK] Vérification du fichier encrypté complet réussie !")
    
    # Étape 3: Demander à l'utilisateur s'il souhaite nettoyer les fichiers non nécessaires
    print("\n--- Étape 3: Nettoyage des fichiers non nécessaires ---\n")
    print("Le fichier encrypté complet a été créé et vérifié avec succès.")
    print("Vous pouvez maintenant nettoyer les fichiers non nécessaires.")
    print("\nATTENTION: Cette opération va supprimer définitivement les fichiers suivants:")
    print(f"   - Tous les fichiers de cache dans '{temp_cache_dir}'")
    print(f"   - Le répertoire de cache original '{original_cache_dir}' s'il existe")
    print(f"   - Le fichier DATA_DIR / 'extract_sources.json' s'il existe")
    
    confirmation = input("\nSouhaitez-vous nettoyer les fichiers non nécessaires? (o/n): ")
    if confirmation.lower() in ["o", "oui", "y", "yes"]:
        # Supprimer les fichiers non nécessaires
        print("\nNettoyage des fichiers non nécessaires...")
        
        # Supprimer le répertoire de cache
        if temp_cache_dir.exists():
            try:
                shutil.rmtree(temp_cache_dir)
                print(f"[OK] Répertoire de cache '{temp_cache_dir}' supprimé.")
            except Exception as e:
                print(f"⚠️ Erreur lors de la suppression du répertoire de cache: {e}")
        
        # Supprimer le répertoire de cache original
        if original_cache_dir.exists():
            try:
                shutil.rmtree(original_cache_dir)
                print(f"[OK] Répertoire de cache original '{original_cache_dir}' supprimé.")
            except Exception as e:
                print(f"⚠️ Erreur lors de la suppression du répertoire de cache original: {e}")
        
        # Supprimer le fichier extract_sources.json
        extract_sources_json = parent_dir / DATA_DIR / "extract_sources.json"
        if extract_sources_json.exists():
            try:
                extract_sources_json.unlink()
                print(f"[OK] Fichier '{extract_sources_json}' supprimé.")
            except Exception as e:
                print(f"⚠️ Erreur lors de la suppression du fichier '{extract_sources_json}': {e}")
        
        print("\n[OK] Nettoyage des fichiers non nécessaires terminé.")
    else:
        print("\nLes fichiers non nécessaires n'ont pas été supprimés.")
        
        # Restaurer le répertoire de cache original
        if original_cache_dir.exists():
            if temp_cache_dir.exists():
                try:
                    shutil.rmtree(temp_cache_dir)
                except Exception:
                    pass
            try:
                original_cache_dir.rename(temp_cache_dir)
                print(f"[OK] Répertoire de cache original restauré.")
            except Exception as e:
                print(f"⚠️ Erreur lors de la restauration du répertoire de cache original: {e}")
    
    print("\n=== Processus terminé ===\n")
    print(f"Le fichier encrypté complet a été créé et vérifié avec succès:")
    print(f"   - Fichier: '{CONFIG_FILE_ENC}'")
    print(f"   - Taille: {CONFIG_FILE_ENC.stat().st_size} octets.")
    print("\nVous pouvez maintenant archiver ce fichier sur GitHub et supprimer les autres fichiers.")
    print("Pour restaurer les fichiers de cache à partir du fichier encrypté, utilisez le script:")
    print("   load_complete_encrypted_config.py")
    
    sys.exit(0)

if __name__ == "__main__":
    main()
