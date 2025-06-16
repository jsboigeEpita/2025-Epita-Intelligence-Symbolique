#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour créer un fichier encrypté complet qui embarque les sources avec la configuration des extraits.
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
from argumentation_analysis.ui.utils import reconstruct_url, get_cache_filepath

# Définir les constantes avec le chemin absolu correct
EXTRACT_SOURCES_UPDATED_PATH = current_dir.parent.parent.parent / "utils" / "extract_repair" / "docs" / "extract_sources_updated.json"
TEXT_CACHE_DIR = current_dir.parent.parent.parent / "text_cache"

# Afficher les chemins pour le débogage
print(f"Chemin du fichier de configuration: {EXTRACT_SOURCES_UPDATED_PATH}")
print(f"Chemin du répertoire de cache: {TEXT_CACHE_DIR}")
print(f"Chemin du fichier encrypté: {CONFIG_FILE_ENC}")

def encrypt_data(data, key):
    """Chiffre des données binaires avec une clé Fernet."""
    if not key:
        print("Erreur chiffrement: Clé chiffrement manquante.")
        return None
    try:
        f = Fernet(key)
        return f.encrypt(data)
    except Exception as e:
        print(f"Erreur chiffrement: {e}")
        return None

def create_complete_encrypted_config():
    """Crée un fichier encrypté complet qui embarque les sources avec la configuration des extraits."""
    # Vérifier si la clé de chiffrement est disponible
    if not ENCRYPTION_KEY:
        print(f"❌ Erreur: La clé de chiffrement n'est pas disponible. Vérifiez la variable d'environnement 'TEXT_CONFIG_PASSPHRASE'.")
        return False
    
    # Vérifier si le fichier de configuration existe
    if not EXTRACT_SOURCES_UPDATED_PATH.exists():
        print(f"❌ Erreur: Le fichier de configuration '{EXTRACT_SOURCES_UPDATED_PATH}' n'existe pas.")
        return False
    
    try:
        # Lire le contenu du fichier de configuration
        with open(EXTRACT_SOURCES_UPDATED_PATH, 'r', encoding='utf-8') as f:
            extract_sources = json.load(f)
        
        print(f"[OK] Fichier de configuration '{EXTRACT_SOURCES_UPDATED_PATH}' chargé avec succès.")
        print(f"   - {len(extract_sources)} sources trouvées.")
        
        # Créer un dictionnaire pour stocker les sources et leur contenu
        complete_config = {
            "sources": extract_sources,
            "cache": {}
        }
        
        # Récupérer les fichiers de cache pour chaque source
        for source in extract_sources:
            source_name = source.get("source_name", "Source inconnue")
            source_type = source.get("source_type", "")
            schema = source.get("schema", "")
            host_parts = source.get("host_parts", [])
            path = source.get("path", "")
            
            # Reconstruire l'URL
            url = reconstruct_url(schema, host_parts, path)
            if not url:
                print(f"⚠️ Avertissement: URL invalide pour la source '{source_name}'. Cette source sera ignorée.")
                continue
            
            # Calculer le hash de l'URL pour le nom du fichier de cache
            url_hash = hashlib.sha256(url.encode()).hexdigest()
            cache_filepath = TEXT_CACHE_DIR / f"{url_hash}.txt"
            
            # Vérifier si le fichier de cache existe
            if not cache_filepath.exists():
                print(f"⚠️ Avertissement: Fichier de cache '{cache_filepath.name}' non trouvé pour la source '{source_name}'.")
                print(f"   Cette source sera incluse sans son contenu.")
                continue
            
            # Lire le contenu du fichier de cache
            try:
                cache_content = cache_filepath.read_text(encoding='utf-8')
                print(f"[OK] Fichier de cache '{cache_filepath.name}' chargé pour la source '{source_name}'.")
                print(f"   - Longueur: {len(cache_content)} caractères.")
                
                # Ajouter le contenu du cache au dictionnaire
                complete_config["cache"][url_hash] = cache_content
            except Exception as e:
                print(f"⚠️ Avertissement: Erreur lors de la lecture du fichier de cache '{cache_filepath.name}': {e}")
                print(f"   Cette source sera incluse sans son contenu.")
        
        # Convertir le dictionnaire en JSON
        json_data = json.dumps(complete_config, indent=2, ensure_ascii=False).encode('utf-8')
        
        # Compresser les données
        compressed_data = gzip.compress(json_data)
        print(f"[OK] Données compressées: {len(json_data)} -> {len(compressed_data)} octets.")
        
        # Chiffrer les données
        encrypted_data = encrypt_data(compressed_data, ENCRYPTION_KEY)
        if not encrypted_data:
            print(f"❌ Erreur: Échec du chiffrement des données.")
            return False
        
        # Sauvegarder les données chiffrées dans le fichier
        CONFIG_FILE_ENC.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE_ENC, 'wb') as f:
            f.write(encrypted_data)
        
        print(f"[OK] Fichier chiffré '{CONFIG_FILE_ENC}' créé avec succès.")
        print(f"   - Taille: {CONFIG_FILE_ENC.stat().st_size} octets.")
        
        return True
    
    except Exception as e:
        print(f"❌ Erreur inattendue: {e}")
        return False

def main():
    """Fonction principale."""
    print("\n=== Création du fichier encrypté complet ===\n")
    
    # Vérifier si la variable d'environnement TEXT_CONFIG_PASSPHRASE est définie
    if not os.getenv("TEXT_CONFIG_PASSPHRASE"):
        print(f"⚠️ La variable d'environnement 'TEXT_CONFIG_PASSPHRASE' n'est pas définie.")
        print(f"   Veuillez la définir avant d'exécuter ce script.")
        sys.exit(1)
    
    # Créer le fichier encrypté complet
    success = create_complete_encrypted_config()
    
    if success:
        print("\n[OK] Création du fichier encrypté complet réussie !")
    else:
        print("\n❌ Échec de la création du fichier encrypté complet.")
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
