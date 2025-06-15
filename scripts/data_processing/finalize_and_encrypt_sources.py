import project_core.core_from_scripts.auto_env
import json
import gzip
import os
import pathlib
import sys # NOUVEAU: Pour sys.path
from typing import Optional # NOUVEAU: Pour type hinting

# Ajout du répertoire racine du projet au chemin pour permettre l'import des modules
project_root = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from argumentation_analysis.utils.core_utils.crypto_utils import encrypt_data_aesgcm, decrypt_data_aesgcm # MODIFIÉ: Import

# Les fonctions derive_key et encrypt_data ont été déplacées vers crypto_utils.py
# et renommées/adaptées (derive_key_aes, encrypt_data_aesgcm).

def finalize_and_encrypt(passphrase_override: Optional[str] = None): # MODIFIÉ: Ajout d'un override pour la passphrase
    input_json_path_str = "_temp/config_final_pre_encryption.json"
    output_encrypted_path_str = "argumentation_analysis/data/extract_sources.json.gz.enc"
    passphrase = passphrase_override if passphrase_override else "Propaganda" # MODIFIÉ: Utilisation de l'override

    input_json_path = pathlib.Path(input_json_path_str)
    output_encrypted_path = pathlib.Path(output_encrypted_path_str)

    print(f"INFO: Lecture du fichier JSON depuis : {input_json_path}")
    try:
        with open(input_json_path, 'r', encoding='utf-8') as f:
            json_content_str = f.read()
    except Exception as e:
        print(f"ERREUR CRITIQUE: Impossible de lire le fichier JSON '{input_json_path}': {e}")
        return

    # Convertir en bytes et compresser
    json_bytes = json_content_str.encode('utf-8')
    print(f"INFO: Contenu JSON chargé (longueur originale: {len(json_bytes)} bytes).")
    
    try:
        compressed_bytes = gzip.compress(json_bytes)
        print(f"INFO: Données compressées avec gzip (longueur compressée: {len(compressed_bytes)} bytes).")
    except Exception as e:
        print(f"ERREUR CRITIQUE: Échec de la compression gzip: {e}")
        return

    # Chiffrer les données compressées
    try:
        encrypted_data_with_prefix = encrypt_data_aesgcm(compressed_bytes, passphrase) # MODIFIÉ: Appel de la fonction importée
        if encrypted_data_with_prefix is None:
            print(f"ERREUR CRITIQUE: Échec du chiffrement, encrypt_data_aesgcm a retourné None.")
            return
        print(f"INFO: Données chiffrées avec succès (longueur totale avec sel+nonce: {len(encrypted_data_with_prefix)} bytes).")
    except Exception as e:
        print(f"ERREUR CRITIQUE: Échec du chiffrement: {e}")
        return

    # S'assurer que le répertoire de sortie existe
    try:
        output_encrypted_path.parent.mkdir(parents=True, exist_ok=True)
        print(f"INFO: Répertoire de sortie '{output_encrypted_path.parent}' vérifié/créé.")
    except Exception as e:
        print(f"ERREUR CRITIQUE: Impossible de créer le répertoire de sortie '{output_encrypted_path.parent}': {e}")
        return
        
    # Écrire les données chiffrées dans le fichier de sortie
    try:
        with open(output_encrypted_path, 'wb') as f:
            f.write(encrypted_data_with_prefix)
        print(f"SUCCÈS: Fichier chiffré sauvegardé dans : {output_encrypted_path}")
    except Exception as e:
        print(f"ERREUR CRITIQUE: Impossible d'écrire le fichier chiffré '{output_encrypted_path}': {e}")
        return

if __name__ == "__main__":
    # Exemple d'utilisation avec une passphrase spécifique (pourrait être lu depuis un argument CLI ou une variable d'env)
    # passphrase_for_script = os.getenv("YOUR_SCRIPT_PASSPHRASE") or "Propaganda"
    # finalize_and_encrypt(passphrase_override=passphrase_for_script)
    finalize_and_encrypt() # Conserve le comportement original si appelé directement