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
        
        Args:
            encryption_key: Clé de chiffrement (si None, le chiffrement est désactivé)
            fixed_salt: Sel fixe pour la dérivation de clé
        """
        self.encryption_key = encryption_key
        self.fixed_salt = fixed_salt or b'q\x8b\t\x97\x8b\xe9\xa3\xf2\xe4\x8e\xea\xf5\xe8\xb7\xd6\x8c'
        self.logger = logger
        
        if not encryption_key:
            self.logger.warning("Service de chiffrement initialisé sans clé. Le chiffrement est désactivé.")
    
    def derive_key_from_passphrase(self, passphrase: str, iterations: int = 480000) -> Optional[bytes]:
        """
        Dérive une clé de chiffrement à partir d'une phrase secrète.
        
        Args:
            passphrase: Phrase secrète
            iterations: Nombre d'itérations pour la dérivation
            
        Returns:
            Clé dérivée ou None en cas d'erreur
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
        Définit la clé de chiffrement.
        
        Args:
            key: Clé de chiffrement
        """
        self.encryption_key = key
        self.logger.info("Clé de chiffrement mise à jour.")
    
    def encrypt_data(self, data: bytes) -> Optional[bytes]:
        """
        Chiffre des données binaires.
        
        Args:
            data: Données à chiffrer
            
        Returns:
            Données chiffrées ou None en cas d'erreur
        """
        if not self.encryption_key:
            self.logger.error("Erreur de chiffrement: Clé de chiffrement manquante.")
            return None
        
        try:
            f = Fernet(self.encryption_key)
            encrypted_data = f.encrypt(data)
            return encrypted_data
        except Exception as e:
            self.logger.error(f"Erreur de chiffrement: {e}")
            return None
    
    def decrypt_data(self, encrypted_data: bytes) -> Optional[bytes]:
        """
        Déchiffre des données binaires.
        
        Args:
            encrypted_data: Données chiffrées
            
        Returns:
            Données déchiffrées ou None en cas d'erreur
        """
        if not self.encryption_key:
            self.logger.error("Erreur de déchiffrement: Clé de chiffrement manquante.")
            return None
        
        try:
            f = Fernet(self.encryption_key)
            decrypted_data = f.decrypt(encrypted_data)
            return decrypted_data
        except (InvalidToken, InvalidSignature) as e:
            self.logger.error(f"Erreur de déchiffrement (clé invalide): {e}")
            return None
        except Exception as e:
            self.logger.error(f"Erreur de déchiffrement: {e}")
            return None
    
    def encrypt_and_compress_json(self, data: Union[List, Dict]) -> Optional[bytes]:
        """
        Chiffre et compresse des données JSON.
        
        Args:
            data: Données JSON à chiffrer
            
        Returns:
            Données chiffrées et compressées ou None en cas d'erreur
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
        Déchiffre et décompresse des données JSON.
        
        Args:
            encrypted_data: Données chiffrées et compressées
            
        Returns:
            Données JSON déchiffrées et décompressées ou None en cas d'erreur
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
        Vérifie si le chiffrement est activé.
        
        Returns:
            True si le chiffrement est activé, False sinon
        """
        return self.encryption_key is not None