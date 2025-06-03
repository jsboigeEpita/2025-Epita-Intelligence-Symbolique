#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour charger le fichier encrypté complet et restaurer les fichiers de cache.
"""

import os
import sys
import json
import gzip
import hashlib
from pathlib import Path
from dotenv import load_dotenv
from cryptography.fernet import Fernet

# Ajouter le répertoire parent au chemin de recherche des modules
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
if str(parent_dir) not in sys.path:
    sys.path.append(str(parent_dir))

# Charger les variables d'environnement
load_dotenv(override=True)

# Importer les modules nécessaires
from argumentation_analysis.ui.config import ENCRYPTION_KEY, CONFIG_FILE_ENC

# Définir les constantes
TEXT_CACHE_DIR = parent_dir / "text_cache"

# Afficher les chemins pour le débogage
print(f"Chemin du fichier encrypté: {CONFIG_FILE_ENC}")
print(f"Chemin du répertoire de cache: {TEXT_CACHE_DIR}")

def decrypt_data(encrypted_data, key):
    """Déchiffre des données binaires avec une clé Fernet."""
    if not key:
        print("Erreur déchiffrement: Clé chiffrement manquante.")
        return None
    try:
        f = Fernet(key)
        return f.decrypt(encrypted_data)
    except Exception as e:
        print(f"Erreur déchiffrement: {e}")
        return None

def load_complete_encrypted_config():
    """Charge le fichier encrypté complet et restaure les fichiers de cache."""
    # Vérifier si la clé de chiffrement est disponible
    if not ENCRYPTION_KEY:
        print(f"❌ Erreur: La clé de chiffrement n'est pas disponible. Vérifiez la variable d'environnement 'TEXT_CONFIG_PASSPHRASE'.")
        return False
    
    # Vérifier si le fichier encrypté existe
    if not CONFIG_FILE_ENC.exists():
        print(f"❌ Erreur: Le fichier encrypté '{CONFIG_FILE_ENC}' n'existe pas.")
        return False
    
    try:
        # Lire le contenu du fichier encrypté
        with open(CONFIG_FILE_ENC, 'rb') as f:
            encrypted_data = f.read()
        
        print(f"✅ Fichier encrypté '{CONFIG_FILE_ENC}' chargé avec succès.")
        print(f"   - Taille: {len(encrypted_data)} octets.")
        
        # Déchiffrer les données
        decrypted_compressed_data = decrypt_data(encrypted_data, ENCRYPTION_KEY)
        if not decrypted_compressed_data:
            print(f"❌ Erreur: Échec du déchiffrement des données.")
            return False
        
        # Décompresser les données
        decompressed_data = gzip.decompress(decrypted_compressed_data)
        print(f"✅ Données décompressées: {len(decrypted_compressed_data)} -> {len(decompressed_data)} octets.")
        
        # Charger le JSON
        complete_config = json.loads(decompressed_data.decode('utf-8'))
        
        # Extraire les sources et le cache
        sources = complete_config.get("sources", [])
        cache = complete_config.get("cache", {})
        
        print(f"✅ Configuration chargée avec succès.")
        print(f"   - {len(sources)} sources trouvées.")
        print(f"   - {len(cache)} fichiers de cache trouvés.")
        
        # Créer le répertoire de cache s'il n'existe pas
        TEXT_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        
        # Restaurer les fichiers de cache
        for url_hash, content in cache.items():
            cache_filepath = TEXT_CACHE_DIR / f"{url_hash}.txt"
            
            # Écrire le contenu dans le fichier de cache
            try:
                cache_filepath.write_text(content, encoding='utf-8')
                print(f"✅ Fichier de cache '{cache_filepath.name}' restauré.")
                print(f"   - Longueur: {len(content)} caractères.")
            except Exception as e:
                print(f"⚠️ Avertissement: Erreur lors de l'écriture du fichier de cache '{cache_filepath.name}': {e}")
        
        return True
    
    except Exception as e:
        print(f"❌ Erreur inattendue: {e}")
        return False

def main():
    """Fonction principale."""
    print("\n=== Chargement du fichier encrypté complet ===\n")
    
    # Vérifier si la variable d'environnement TEXT_CONFIG_PASSPHRASE est définie
    if not os.getenv("TEXT_CONFIG_PASSPHRASE"):
        print(f"⚠️ La variable d'environnement 'TEXT_CONFIG_PASSPHRASE' n'est pas définie.")
        print(f"   Veuillez la définir avant d'exécuter ce script.")
        sys.exit(1)
    
    # Charger le fichier encrypté complet
    success = load_complete_encrypted_config()
    
    if success:
        print("\n✅ Chargement du fichier encrypté complet réussi !")
    else:
        print("\n❌ Échec du chargement du fichier encrypté complet.")
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
