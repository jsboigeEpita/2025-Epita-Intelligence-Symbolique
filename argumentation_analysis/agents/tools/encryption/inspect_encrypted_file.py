#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour inspecter le contenu du fichier encrypté.
"""

import os
import sys
import json
import gzip
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

def inspect_encrypted_file():
    """Inspecte le contenu du fichier encrypté."""
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
        data = json.loads(decompressed_data.decode('utf-8'))
        
        # Afficher le type et la structure des données
        print(f"✅ Type de données: {type(data)}")
        
        if isinstance(data, dict):
            print(f"✅ Structure du dictionnaire:")
            for key, value in data.items():
                if isinstance(value, dict):
                    print(f"   - {key}: dictionnaire avec {len(value)} éléments")
                elif isinstance(value, list):
                    print(f"   - {key}: liste avec {len(value)} éléments")
                else:
                    print(f"   - {key}: {type(value)}")
        elif isinstance(data, list):
            print(f"✅ Structure de la liste:")
            print(f"   - Liste avec {len(data)} éléments")
            if data:
                print(f"   - Premier élément: {type(data[0])}")
                if isinstance(data[0], dict):
                    print(f"     - Clés: {', '.join(data[0].keys())}")
                    
                    # Afficher plus de détails sur les extraits
                    print("\n✅ Détails des sources:")
                    for i, source in enumerate(data):
                        source_name = source.get("source_name", "Source inconnue")
                        extracts = source.get("extracts", [])
                        print(f"   - Source {i+1}: {source_name}")
                        print(f"     - Nombre d'extraits: {len(extracts)}")
                        
                        # Afficher les détails du premier extrait s'il existe
                        if extracts:
                            first_extract = extracts[0]
                            print(f"     - Premier extrait:")
                            for key, value in first_extract.items():
                                if isinstance(value, str) and len(value) > 50:
                                    print(f"       - {key}: {value[:50]}...")
                                else:
                                    print(f"       - {key}: {value}")
        
        return True
    
    except Exception as e:
        print(f"❌ Erreur inattendue: {e}")
        return False

def main():
    """Fonction principale."""
    print("\n=== Inspection du fichier encrypté ===\n")
    
    # Vérifier si la variable d'environnement TEXT_CONFIG_PASSPHRASE est définie
    if not os.getenv("TEXT_CONFIG_PASSPHRASE"):
        print(f"⚠️ La variable d'environnement 'TEXT_CONFIG_PASSPHRASE' n'est pas définie.")
        print(f"   Veuillez la définir avant d'exécuter ce script.")
        sys.exit(1)
    
    # Inspecter le fichier encrypté
    success = inspect_encrypted_file()
    
    if success:
        print("\n✅ Inspection du fichier encrypté réussie !")
    else:
        print("\n❌ Échec de l'inspection du fichier encrypté.")
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()