import json
import gzip
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import pathlib

def derive_key(passphrase: str, salt: bytes, key_length: int = 32) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=key_length,
        salt=salt,
        iterations=100000, # Nombre d'itérations standard
        backend=default_backend()
    )
    return kdf.derive(passphrase.encode('utf-8'))

def encrypt_data(data_bytes: bytes, passphrase: str) -> bytes:
    salt = os.urandom(16)  # Générer un nouveau sel pour chaque chiffrement
    key = derive_key(passphrase, salt)
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)  # AES-GCM utilise typiquement un nonce de 12 bytes
    encrypted_data = aesgcm.encrypt(nonce, data_bytes, None) # Pas de données additionnelles authentifiées
    return salt + nonce + encrypted_data # Préfixer avec sel puis nonce

def finalize_and_encrypt():
    input_json_path_str = "_temp/config_final_pre_encryption.json"
    output_encrypted_path_str = "argumentation_analysis/data/extract_sources.json.gz.enc"
    passphrase = "Propaganda"

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
        encrypted_data_with_prefix = encrypt_data(compressed_bytes, passphrase)
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
    finalize_and_encrypt()