# project_core/utils/crypto_utils.py
import base64
import logging
import os
from typing import Optional, Union # MODIFIÉ: Ajout de Union
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from cryptography.fernet import Fernet, InvalidToken # NOUVEAU: Pour encrypt/decrypt_data
from cryptography.exceptions import InvalidSignature # NOUVEAU: Pour decrypt_data

# Configuration du logging pour ce module
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s', datefmt='%H:%M:%S')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO) # Ou un autre niveau par défaut souhaité

# Sel fixe, identique à celui utilisé précédemment.
# Pourrait être externalisé dans une configuration si partagé par d'autres modules.
FIXED_SALT = b'q\x8b\t\x97\x8b\xe9\xa3\xf2\xe4\x8e\xea\xf5\xe8\xb7\xd6\x8c'

def derive_encryption_key(passphrase: str) -> Optional[bytes]:
    """
    Dérive une clé de chiffrement Fernet (encodée en base64url) à partir d'une phrase secrète.
    
    Args:
        passphrase: La phrase secrète.
        
    Returns:
        Optional[bytes]: La clé de chiffrement dérivée et encodée en base64url (bytes),
                         ou None en cas d'erreur ou si la passphrase est vide.
    """
    if not passphrase:
        logger.warning("Tentative de dérivation de clé avec une phrase secrète vide. Retour de None.")
        return None
    try:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32, # Produit une clé de 256 bits, adaptée pour Fernet
            salt=FIXED_SALT,
            iterations=480000,
            backend=default_backend()
        )
        derived_key_raw = kdf.derive(passphrase.encode('utf-8'))
        # Fernet attend une clé encodée en base64 URL-safe.
        encryption_key_bytes = base64.urlsafe_b64encode(derived_key_raw)
        
        logger.debug("Clé de chiffrement dérivée avec succès (bytes).")
        return encryption_key_bytes
    except Exception as e:
        logger.error(f"Erreur lors de la dérivation de la clé: {e}", exc_info=True)
        return None

def load_encryption_key(passphrase_arg: Optional[str] = None, env_var_name: str = "TEXT_CONFIG_PASSPHRASE") -> Optional[bytes]:
    """
    Charge la clé de chiffrement en essayant d'abord la phrase secrète fournie,
    puis une variable d'environnement.

    Args:
        passphrase_arg: La phrase secrète fournie en argument (optionnelle).
        env_var_name: Le nom de la variable d'environnement à vérifier pour la phrase secrète.

    Returns:
        Optional[bytes]: La clé de chiffrement dérivée et encodée en base64url (bytes), ou None si non disponible ou en cas d'erreur.
    """
    # Essayer avec la phrase secrète fournie en argument
    if passphrase_arg:
        logger.info("Utilisation de la phrase secrète fournie en argument pour dériver la clé...")
        encryption_key = derive_encryption_key(passphrase_arg)
        if encryption_key:
            logger.info("(OK) Clé de chiffrement dérivée avec succès à partir de l'argument.")
            return encryption_key
        else:
            # L'erreur est déjà loggée par derive_encryption_key
            logger.warning("Échec de la dérivation de la clé à partir de l'argument passphrase.")
            # On continue pour essayer la variable d'environnement au cas où l'argument était invalide mais la variable existe.
    
    # Essayer de charger depuis la variable d'environnement
    env_passphrase = os.getenv(env_var_name)
    if env_passphrase:
        logger.info(f"Phrase secrète trouvée dans la variable d'environnement '{env_var_name}'.")
        encryption_key = derive_encryption_key(env_passphrase)
        if encryption_key:
            logger.info("(OK) Clé de chiffrement dérivée avec succès à partir de la variable d'environnement.")
            return encryption_key
        else:
            # L'erreur est déjà loggée par derive_encryption_key
            logger.error(f"Échec de la dérivation de la clé à partir de la variable d'environnement '{env_var_name}'.")
            return None # Échec définitif si la variable d'env a été trouvée mais la dérivation a échoué
            
    if not passphrase_arg and not env_passphrase:
        logger.warning("Aucune phrase secrète fournie (ni argument, ni variable d'environnement).")
        logger.warning(f"Assurez-vous que la variable d'environnement '{env_var_name}' est définie ou fournissez une phrase secrète.")

    return None # Retourne None si aucune source de passphrase n'a abouti à une clé

# --- Fonctions de chiffrement/déchiffrement Fernet ---

def encrypt_data_with_fernet(data: bytes, b64_encoded_key_str: Union[str, bytes]) -> Optional[bytes]:
    """
    Chiffre des données binaires avec une clé Fernet.
    La clé est la chaîne de caractères encodée en base64url (sortie de derive_encryption_key) ou des bytes.

    Args:
        data: Les données binaires à chiffrer.
        b64_encoded_key_str: La clé de chiffrement Fernet, encodée en base64url (str ou bytes).

    Returns:
        Optional[bytes]: Les données chiffrées, ou None en cas d'erreur.
    """
    if not b64_encoded_key_str:
        logger.error("Erreur chiffrement Fernet: Clé (str b64 ou bytes) manquante.")
        return None
    try:
        # Fernet attend la clé encodée en base64url, mais sous forme de bytes.
        if isinstance(b64_encoded_key_str, str):
            key_bytes = b64_encoded_key_str.encode('utf-8')
        elif isinstance(b64_encoded_key_str, bytes):
            key_bytes = b64_encoded_key_str
        else:
            logger.error(f"Erreur chiffrement Fernet: Type de clé inattendu {type(b64_encoded_key_str)}.")
            return None
        f = Fernet(key_bytes)
        return f.encrypt(data)
    except Exception as e:
        logger.error(f"Erreur chiffrement Fernet: {e}", exc_info=True)
        return None

def decrypt_data_with_fernet(encrypted_data: bytes, b64_encoded_key_str: Union[str, bytes]) -> Optional[bytes]:
    """
    Déchiffre des données binaires avec une clé Fernet.
    La clé est la chaîne de caractères encodée en base64url (sortie de derive_encryption_key) ou des bytes.

    Args:
        encrypted_data: Les données chiffrées.
        b64_encoded_key_str: La clé de chiffrement Fernet, encodée en base64url (str ou bytes).

    Returns:
        Optional[bytes]: Les données déchiffrées, ou None en cas d'erreur ou de token invalide.
    """
    if not b64_encoded_key_str:
        logger.error("Erreur déchiffrement Fernet: Clé (str b64 ou bytes) manquante.")
        return None
    try:
        # Fernet attend la clé encodée en base64url, mais sous forme de bytes.
        if isinstance(b64_encoded_key_str, str):
            key_bytes = b64_encoded_key_str.encode('utf-8')
        elif isinstance(b64_encoded_key_str, bytes):
            key_bytes = b64_encoded_key_str
        else:
            logger.error(f"Erreur déchiffrement Fernet: Type de clé inattendu {type(b64_encoded_key_str)}.")
            return None
        f = Fernet(key_bytes)
        return f.decrypt(encrypted_data)
    except (InvalidToken, InvalidSignature) as e:
        logger.error(f"Erreur déchiffrement Fernet (InvalidToken/Signature): {e}")
        return None
    except Exception as e:
        logger.error(f"Erreur déchiffrement Fernet (Autre): {e}", exc_info=True)
        return None

# --- Fonctions de chiffrement/déchiffrement AESGCM ---

def derive_key_aes(passphrase: str, salt: bytes, key_length: int = 32, iterations: int = 480000) -> bytes:
    """
    Dérive une clé de chiffrement pour AESGCM à partir d'une phrase secrète et d'un sel.
    Utilise PBKDF2HMAC avec SHA256.

    Args:
        passphrase: La phrase secrète.
        salt: Le sel à utiliser pour la dérivation.
        key_length: La longueur souhaitée de la clé en bytes (par défaut 32 pour AES-256).
        iterations: Le nombre d'itérations pour PBKDF2HMAC.

    Returns:
        bytes: La clé dérivée.
    """
    if not passphrase:
        logger.error("Tentative de dérivation de clé AES avec une phrase secrète vide.")
        raise ValueError("La phrase secrète ne peut pas être vide pour la dérivation de clé AES.")
    if not salt:
        logger.error("Tentative de dérivation de clé AES avec un sel vide.")
        raise ValueError("Le sel ne peut pas être vide pour la dérivation de clé AES.")

    try:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=key_length,
            salt=salt,
            iterations=iterations, # Nombre d'itérations standard, peut être augmenté pour plus de sécurité
            backend=default_backend()
        )
        derived_key = kdf.derive(passphrase.encode('utf-8'))
        logger.debug(f"Clé AES dérivée avec succès (longueur: {len(derived_key)} bytes).")
        return derived_key
    except Exception as e:
        logger.error(f"Erreur lors de la dérivation de la clé AES: {e}", exc_info=True)
        raise # Propage l'exception pour que l'appelant puisse la gérer

def encrypt_data_aesgcm(data_bytes: bytes, passphrase: str, salt_len: int = 16, nonce_len: int = 12) -> Optional[bytes]:
    """
    Chiffre des données binaires en utilisant AESGCM.
    Un nouveau sel est généré pour chaque chiffrement et est préfixé au résultat.
    Un nouveau nonce est généré pour chaque chiffrement et est préfixé après le sel.

    Args:
        data_bytes: Les données binaires à chiffrer.
        passphrase: La phrase secrète pour dériver la clé.
        salt_len: Longueur du sel à générer (en bytes).
        nonce_len: Longueur du nonce à générer (en bytes).

    Returns:
        Optional[bytes]: Les données chiffrées (sel + nonce + ciphertext), ou None en cas d'erreur.
    """
    if not passphrase:
        logger.error("Erreur chiffrement AESGCM: Phrase secrète manquante.")
        return None
    try:
        salt = os.urandom(salt_len)
        key = derive_key_aes(passphrase, salt)
        
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM # Ajout import
        aesgcm = AESGCM(key)
        nonce = os.urandom(nonce_len)
        
        encrypted_payload = aesgcm.encrypt(nonce, data_bytes, None)
        
        logger.debug(f"Données chiffrées avec AESGCM (sel: {salt_len}B, nonce: {nonce_len}B, payload: {len(encrypted_payload)}B).")
        return salt + nonce + encrypted_payload
    except ValueError as ve:
        logger.error(f"Erreur de valeur lors du chiffrement AESGCM: {ve}")
        return None
    except Exception as e:
        logger.error(f"Erreur inattendue lors du chiffrement AESGCM: {e}", exc_info=True)
        return None

def decrypt_data_aesgcm(encrypted_data_with_prefix: bytes, passphrase: str, salt_len: int = 16, nonce_len: int = 12) -> Optional[bytes]:
    """
    Déchiffre des données binaires chiffrées avec AESGCM, où le sel et le nonce sont préfixés.

    Args:
        encrypted_data_with_prefix: Les données chiffrées (sel + nonce + ciphertext).
        passphrase: La phrase secrète pour dériver la clé.
        salt_len: Longueur du sel utilisé (en bytes).
        nonce_len: Longueur du nonce utilisé (en bytes).

    Returns:
        Optional[bytes]: Les données déchiffrées, ou None en cas d'erreur (e.g., token invalide, clé incorrecte).
    """
    if not passphrase:
        logger.error("Erreur déchiffrement AESGCM: Phrase secrète manquante.")
        return None
    if not encrypted_data_with_prefix or len(encrypted_data_with_prefix) < salt_len + nonce_len:
        logger.error(f"Erreur déchiffrement AESGCM: Données chiffrées trop courtes (longueur: {len(encrypted_data_with_prefix)}B).")
        return None
        
    try:
        salt = encrypted_data_with_prefix[:salt_len]
        nonce = encrypted_data_with_prefix[salt_len : salt_len + nonce_len]
        encrypted_payload = encrypted_data_with_prefix[salt_len + nonce_len:]
        
        key = derive_key_aes(passphrase, salt)
        
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM # Ajout import
        aesgcm = AESGCM(key)
        
        decrypted_data = aesgcm.decrypt(nonce, encrypted_payload, None)
        logger.debug("Données déchiffrées avec AESGCM avec succès.")
        return decrypted_data
    except (InvalidToken, InvalidSignature) as e:
        logger.error(f"Erreur déchiffrement AESGCM (Token/Signature/Tag invalide): {e}. Cela peut indiquer une mauvaise phrase secrète ou des données corrompues.")
        return None
    except ValueError as ve:
        logger.error(f"Erreur de valeur lors du déchiffrement AESGCM: {ve}")
        return None
    except Exception as e:
        logger.error(f"Erreur inattendue lors du déchiffrement AESGCM: {e}", exc_info=True)
        return None

# --- Section de test pour Fernet (provenant de la branche distante) ---
# Note: Cette section de test est illustrative et pourrait être déplacée dans un module de test dédié.
def _test_fernet_encryption_decryption():
    """Fonction de test interne pour le chiffrement/déchiffrement Fernet."""
    logger.info("\n--- Test Chiffrement/Déchiffrement Fernet ---")
    test_passphrase = "maPhraseSecretePourTests"
    test_data = b"Donnees secretes a chiffrer pour le test."
    
    derived_b64_key = derive_encryption_key(test_passphrase)
    
    if derived_b64_key:
        logger.info(f"Clé dérivée (b64) pour tests Fernet: {derived_b64_key}")
        try:
            encrypted = encrypt_data_with_fernet(test_data, derived_b64_key)
            if encrypted:
                logger.info(f"Données chiffrées: {encrypted}")
                decrypted = decrypt_data_with_fernet(encrypted, derived_b64_key)
                if decrypted:
                    logger.info(f"Données déchiffrées: {decrypted.decode('utf-8', 'ignore')}")
                    if decrypted == test_data:
                        logger.info("(OK) Chiffrement et déchiffrement Fernet réussis!")
                    else:
                        logger.error("(ERROR) Les données déchiffrées ne correspondent pas aux originales.")
                else:
                    logger.error("(ERROR) Échec du déchiffrement Fernet.")
            else:
                logger.error("(ERROR) Échec du chiffrement Fernet.")
        except Exception as e_fernet_test:
            logger.error(f"(ERROR) lors du test Fernet: {e_fernet_test}", exc_info=True)
    else:
        logger.error("(ERROR) Impossible de tester Fernet, la dérivation de clé a échoué.")
    
    logger.info("\n--- Test déchiffrement Fernet avec mauvaise clé ---")
    if derived_b64_key:
        try:
            encrypted = encrypt_data_with_fernet(test_data, derived_b64_key)
            
            bad_b64_key = derive_encryption_key("mauvaisePhraseSecrete")
            if bad_b64_key and bad_b64_key != derived_b64_key:
                logger.info("Tentative de déchiffrement avec une mauvaise clé Fernet...")
                decrypted_with_bad_key = decrypt_data_with_fernet(encrypted, bad_b64_key)
                if decrypted_with_bad_key is None:
                    logger.info("(OK) Échec du déchiffrement avec mauvaise clé, comme attendu (InvalidToken/Signature).")
                else:
                    logger.error(f"(ERROR) Le déchiffrement avec une mauvaise clé aurait dû échouer, mais a retourné: {decrypted_with_bad_key}")
            else:
                logger.warning("Impossible de générer une mauvaise clé distincte pour le test.")
        except Exception as e_bad_key_test:
            logger.error(f"(ERROR) lors du test de mauvaise clé Fernet: {e_bad_key_test}", exc_info=True)

if __name__ == '__main__':
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s', datefmt='%H:%M:%S')
    
    _test_fernet_encryption_decryption()
