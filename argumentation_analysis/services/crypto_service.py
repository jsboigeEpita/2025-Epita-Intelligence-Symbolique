"""
Service de chiffrement pour l'analyse d'argumentation.

Ce module fournit un service centralisé pour le chiffrement et le déchiffrement
des données sensibles, notamment les définitions d'extraits.
"""

import base64
import gzip
import json
import logging
from typing import Optional, Tuple, List, Dict, Any, Union

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidSignature

# Configuration du logging
logger = logging.getLogger("Services.CryptoService")


class CryptoService:
    """Service pour le chiffrement et le déchiffrement des données."""
    
    def __init__(self, encryption_key: Optional[bytes] = None, fixed_salt: Optional[bytes] = None):
        """
        Initialise le service de chiffrement.

        :param encryption_key: Clé de chiffrement binaire. Si None, le chiffrement est désactivé.
        :type encryption_key: Optional[bytes]
        :param fixed_salt: Sel fixe optionnel utilisé pour la dérivation de clé.
                           Un sel par défaut est utilisé si None.
        :type fixed_salt: Optional[bytes]
        """
        self.encryption_key = encryption_key
        self.fixed_salt = fixed_salt or b'q\x8b\t\x97\x8b\xe9\xa3\xf2\xe4\x8e\xea\xf5\xe8\xb7\xd6\x8c'
        self.logger = logger
        
        if not encryption_key:
            self.logger.warning("Service de chiffrement initialisé sans clé. Le chiffrement est désactivé.")
    
    def derive_key_from_passphrase(self, passphrase: str, iterations: int = 480000) -> Optional[bytes]:
        """
        Dérive une clé de chiffrement à partir d'une phrase secrète en utilisant PBKDF2HMAC.

        :param passphrase: La phrase secrète à partir de laquelle dériver la clé.
        :type passphrase: str
        :param iterations: Le nombre d'itérations pour l'algorithme KDF.
        :type iterations: int
        :return: La clé dérivée encodée en base64 URL-safe, ou None si la phrase secrète
                 est vide ou si une erreur survient pendant la dérivation.
        :rtype: Optional[bytes]
        """
        if not passphrase:
            self.logger.error("Phrase secrète vide. Impossible de dériver une clé.")
            return None
        
        try:
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=self.fixed_salt,
                iterations=iterations,
                backend=default_backend()
            )
            derived_key_raw = kdf.derive(passphrase.encode('utf-8'))
            derived_key = base64.urlsafe_b64encode(derived_key_raw)
            
            self.logger.info("Clé de chiffrement dérivée et encodée avec succès.")
            return derived_key
        except Exception as e:
            self.logger.error(f"Erreur lors de la dérivation de la clé: {e}")
            return None
    
    def set_encryption_key(self, key: bytes) -> None:
        """
        Définit la clé de chiffrement à utiliser par l'instance du service.

        :param key: La nouvelle clé de chiffrement binaire.
        :type key: bytes
        :return: None
        :rtype: None
        """
        self.encryption_key = key
        self.logger.info("Clé de chiffrement mise à jour.")
    
    def encrypt_data(self, data: bytes, key: Optional[bytes] = None) -> Optional[bytes]:
        """
        Chiffre des données binaires en utilisant Fernet.

        :param data: Les données binaires (bytes) à chiffrer.
        :type data: bytes
        :param key: Clé de chiffrement optionnelle. Si None, la clé de l'instance
                    (`self.encryption_key`) est utilisée.
        :type key: Optional[bytes]
        :return: Les données chiffrées (bytes), ou None si la clé de chiffrement
                 est manquante ou si une erreur de chiffrement survient.
        :rtype: Optional[bytes]
        """
        # Utiliser la clé fournie ou celle de l'instance
        encryption_key = key if key is not None else self.encryption_key
        
        if not encryption_key:
            self.logger.error("Erreur de chiffrement: Clé de chiffrement manquante.")
            return None
        
        try:
            self.logger.debug(f"CryptoService.encrypt_data using key (first 16 bytes): {encryption_key[:16]}")
            f = Fernet(encryption_key)
            encrypted_data = f.encrypt(data)
            return encrypted_data
        except Exception as e:
            self.logger.error(f"Erreur de chiffrement: {e}")
            return None
    
    def decrypt_data(self, encrypted_data: bytes, key: Optional[bytes] = None) -> Optional[bytes]:
        """
        Déchiffre des données binaires précédemment chiffrées avec Fernet.

        :param encrypted_data: Les données chiffrées (bytes) à déchiffrer.
        :type encrypted_data: bytes
        :param key: Clé de chiffrement optionnelle. Si None, la clé de l'instance
                    (`self.encryption_key`) est utilisée.
        :type key: Optional[bytes]
        :return: Les données déchiffrées (bytes), ou None si la clé de chiffrement
                 est manquante ou si une erreur de déchiffrement survient (par exemple,
                 token invalide).
        :rtype: Optional[bytes]
        """
        # Utiliser la clé fournie ou celle de l'instance
        encryption_key = key if key is not None else self.encryption_key
        
        if not encryption_key:
            self.logger.error("Erreur de déchiffrement: Clé de chiffrement manquante.")
            return None
        
        try:
            self.logger.debug(f"CryptoService.decrypt_data using key (first 16 bytes): {encryption_key[:16]}")
            f = Fernet(encryption_key)
            decrypted_data = f.decrypt(encrypted_data)
            return decrypted_data
        except (InvalidToken, InvalidSignature) as e:
            self.logger.error(f"Erreur de déchiffrement (clé invalide) with key (first 16 bytes): {encryption_key[:16]}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Erreur de déchiffrement (autre) with key (first 16 bytes): {encryption_key[:16]}: {e}")
            return None
    
    def encrypt_and_compress_json(self, data: Union[List, Dict]) -> Optional[bytes]:
        """
        Convertit des données JSON (liste ou dictionnaire) en une chaîne JSON,
        la compresse avec gzip, puis la chiffre.

        :param data: Les données JSON (liste ou dictionnaire) à traiter.
        :type data: Union[List, Dict]
        :return: Les données chiffrées et compressées (bytes), ou None si une erreur
                 survient pendant le processus (sérialisation JSON, compression,
                 ou chiffrement).
        :rtype: Optional[bytes]
        """
        try:
            # Convertir en JSON
            json_data = json.dumps(data, indent=2, ensure_ascii=False).encode('utf-8')
            
            # Compresser
            compressed_data = gzip.compress(json_data)
            
            # Chiffrer
            encrypted_data = self.encrypt_data(compressed_data)
            
            if encrypted_data is None:
                raise ValueError("Échec du chiffrement.")
            
            return encrypted_data
        except Exception as e:
            self.logger.error(f"Erreur lors du chiffrement et de la compression des données JSON: {e}")
            return None
    
    def decrypt_and_decompress_json(self, encrypted_data: bytes) -> Optional[Union[List, Dict]]:
        """
        Déchiffre des données, les décompresse avec gzip, puis les parse en tant que JSON.

        :param encrypted_data: Les données chiffrées et compressées (bytes) à traiter.
        :type encrypted_data: bytes
        :return: Les données JSON déchiffrées et décompressées (liste ou dictionnaire),
                 ou None si une erreur survient pendant le processus (déchiffrement,
                 décompression, ou parsing JSON).
        :rtype: Optional[Union[List, Dict]]
        """
        try:
            # Déchiffrer
            decrypted_compressed_data = self.decrypt_data(encrypted_data)
            
            if decrypted_compressed_data is None:
                raise ValueError("Échec du déchiffrement.")
            
            # Décompresser
            decompressed_data = gzip.decompress(decrypted_compressed_data)
            
            # Charger le JSON
            data = json.loads(decompressed_data.decode('utf-8'))
            
            return data
        except Exception as e:
            self.logger.error(f"Erreur lors du déchiffrement et de la décompression des données JSON: {e}")
            return None
    
    def is_encryption_enabled(self) -> bool:
        """
        Vérifie si une clé de chiffrement est actuellement configurée pour ce service.

        :return: True si `self.encryption_key` n'est pas None, False sinon.
        :rtype: bool
        """
        return self.encryption_key is not None
    
    def generate_key(self) -> bytes:
        """
        Génère une nouvelle clé de chiffrement Fernet.

        :return: Une nouvelle clé de chiffrement binaire.
        :rtype: bytes
        :raises Exception: Si une erreur survient pendant la génération de la clé par Fernet.
        """
        try:
            key = Fernet.generate_key()
            self.logger.info("Nouvelle clé de chiffrement générée avec succès.")
            return key
        except Exception as e:
            self.logger.error(f"Erreur lors de la génération de la clé: {e}")
            raise
    
    def save_key(self, key: bytes, key_file: str) -> bool:
        """
        Sauvegarde une clé de chiffrement binaire dans un fichier spécifié.

        :param key: La clé de chiffrement (bytes) à sauvegarder.
        :type key: bytes
        :param key_file: Le chemin du fichier (str) où sauvegarder la clé.
        :type key_file: str
        :return: True si la sauvegarde a réussi, False sinon.
        :rtype: bool
        """
        try:
            with open(key_file, 'wb') as f:
                f.write(key)
            self.logger.info(f"Clé de chiffrement sauvegardée dans {key_file}")
            return True
        except Exception as e:
            self.logger.error(f"Erreur lors de la sauvegarde de la clé: {e}")
            return False
    
    def load_key(self, key_file: str) -> Optional[bytes]:
        """
        Charge une clé de chiffrement binaire depuis un fichier spécifié.

        :param key_file: Le chemin du fichier (str) contenant la clé.
        :type key_file: str
        :return: La clé de chiffrement (bytes) chargée depuis le fichier,
                 ou None si une erreur survient lors de la lecture.
        :rtype: Optional[bytes]
        """
        try:
            with open(key_file, 'rb') as f:
                key = f.read()
            self.logger.info(f"Clé de chiffrement chargée depuis {key_file}")
            return key
        except Exception as e:
            self.logger.error(f"Erreur lors du chargement de la clé: {e}")
            return None
    
    @staticmethod
    def generate_static_key() -> bytes:
        """
        Génère une nouvelle clé de chiffrement Fernet de manière statique.

        Cette méthode peut être appelée sans instance de `CryptoService`.

        :return: Une nouvelle clé de chiffrement binaire.
        :rtype: bytes
        """
        return Fernet.generate_key()